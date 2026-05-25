"""Server-side renderer for the Vela Blog (PHASE A).

Single-post route /blog/{slug} only at this phase. List page, sitemap,
content CLI, and Pillow cover-image generation come in PHASES B-C.

Architecture mirrors §4.6 explore_renderer.py: validate slug → query
DB row filtered by status='published' → build template context →
render Jinja2. Reuses ONLY `_markdown_to_html` from share_renderer
(blog has no medical citations, so `_augment_citations` is intentionally
NOT imported).

Theme color system: 7-key dict is this module's authoritative source
for blog. Three values (research / verify / explain) match existing UI
literals in pages/index.tsx + components/Navbar.tsx + pages/history.tsx.
Four are net-new for blog (privacy / allied-health / strategy + asia
which aliases coral); they may be reconciled into a shared design-token
source during the landing redesign — for now they live here.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image, ImageDraw, ImageFont

from api.services.share_renderer import _markdown_to_html, _base_url, _truncate

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "jinja2", "xml"]),
)

# Slug pattern: lowercase + hyphens + ASCII alphanumeric, ≤80 chars.
# Mirrors §4.6 explore slug rules for cross-feature consistency.
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MAX_LEN = 80

# MVP locales per spec: en + zh-TW only.
_BLOG_LOCALES = {"en", "zh-TW"}
_HTML_LANG_MAP = {"en": "en", "zh-TW": "zh-Hant"}


# ─────────────────────────────────────────────────────────────────
# Theme color system — blog-local single source of truth (PHASE A).
# ─────────────────────────────────────────────────────────────────
# `theme` frontmatter value → background/badge hex. Reconciled with the
# landing redesign later; until then duplicating these here is
# acknowledged in the spec.
BLOG_THEME_COLORS: dict[str, str] = {
    # Existing brand colors (verified at pages/index.tsx:580–595,
    # components/Navbar.tsx:19–24, pages/history.tsx:17–39):
    "research":      "#ff8e6e",  # warm orange / coral
    "verify":        "#63b3ed",  # light blue
    "explain":       "#68d391",  # bright green
    "asia":          "#ff8e6e",  # coral (aliases research per spec line 52)
    # Net-new for blog (provisional):
    "privacy":       "#b794f4",  # lavender
    "allied-health": "#9ae6b4",  # sage green
    "strategy":      "#e2e8f0",  # neutral light gray (default fallback)
}

_DEFAULT_THEME = "strategy"


# Cover image output dir. Mirrors §4.6 explore's static/og/explore/ layout.
# gitignored (.gitignore:157 `static/og/`). Generated render-time, ephemeral
# on Fly's machine fs — same limitation as explore's covers (deferred infra
# task, tracked in BACKLOG / TECH_DEBT under §4.5 OG persistence).
_OG_BLOG_DIR = Path("static") / "og" / "blog"
_COVER_WIDTH = 1200
_COVER_HEIGHT = 630
# Dark text color used on all 7 light-themed backgrounds. All BLOG_THEME_COLORS
# values are light enough that #1a1628 (matches the brand dark bg) reads cleanly.
_COVER_TEXT_RGB = (26, 22, 40)


def validate_slug(slug: str) -> None:
    """Raise HTTPException(400) if slug doesn't match the blog pattern."""
    if not slug or len(slug) > _SLUG_MAX_LEN or not _SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug.")


def _resolve_blog_locale(requested: str | None) -> str:
    """Fall back to 'en' for any locale outside the blog MVP set."""
    if requested and requested in _BLOG_LOCALES:
        return requested
    return "en"


def _resolve_theme_color(theme: str | None) -> tuple[str, str]:
    """Return (theme_key, hex_color). Unknown themes log + fallback to 'strategy'."""
    if not theme:
        return _DEFAULT_THEME, BLOG_THEME_COLORS[_DEFAULT_THEME]
    if theme not in BLOG_THEME_COLORS:
        logger.warning("[blog] unknown theme %r, falling back to %r", theme, _DEFAULT_THEME)
        return _DEFAULT_THEME, BLOG_THEME_COLORS[_DEFAULT_THEME]
    return theme, BLOG_THEME_COLORS[theme]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' (or 'rrggbb') to an (R, G, B) tuple for Pillow."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _draw_blog_card(title: str, theme_color: str, theme_key: str, title_is_cjk: bool) -> Image.Image:
    """Pillow cover for blog posts. Theme color background + dark title +
    bottom footer 'Vela for Work · {theme}'. Imports og_image's private
    font helpers per the convention established by explore_renderer.py:97.
    Isolated from share/explore OG drawing (no shared mutation)."""
    from api.services.og_image import _load_font, _wrap_text

    bg = _hex_to_rgb(theme_color)
    img = Image.new("RGB", (_COVER_WIDTH, _COVER_HEIGHT), color=bg)
    draw = ImageDraw.Draw(img)

    # Top-left "Vela" wordmark
    brand_font = _load_font(48, prefer_cjk=False)
    if brand_font:
        draw.text((60, 56), "Vela", font=brand_font, fill=_COVER_TEXT_RGB)

    # Title — CJK-aware wrap (22 CJK chars / 42 Latin), max 5 lines
    title_font = _load_font(64, prefer_cjk=title_is_cjk)
    max_chars = 22 if title_is_cjk else 42
    lines = _wrap_text(title or "Vela Blog", max_chars=max_chars, max_lines=5)

    if title_font is None:
        # Last-resort fallback — never silently render the wrong font on CJK
        logger.warning("[blog-og] no usable font for theme=%s; emitting placeholder", theme_key)
        fallback = ImageFont.load_default()
        draw.text((60, 220), (title or "Vela Blog")[:80], font=fallback, fill=_COVER_TEXT_RGB)
    else:
        line_height = 78
        y = 200
        for ln in lines:
            draw.text((60, y), ln, font=title_font, fill=_COVER_TEXT_RGB)
            y += line_height

    # Bottom footer per spec line 75 verbatim
    foot_font = _load_font(28, prefer_cjk=False)
    if foot_font:
        footer = f"Vela for Work · {theme_key}"
        draw.text((60, _COVER_HEIGHT - 70), footer, font=foot_font, fill=_COVER_TEXT_RGB)

    return img


def _generate_blog_cover(slug: str, locale: str, title: str, theme_key: str, theme_color: str) -> Path | None:
    """Generate the cover image at static/og/blog/{slug}-{locale}.png.

    Idempotent (skip if exists). Non-fatal on Pillow failure (caller
    falls back to landing /og-image.png). Mirrors explore_renderer's
    _generate_explore_og safety contract. Ephemeral on Fly — same
    inherited limitation as explore covers.
    """
    try:
        _OG_BLOG_DIR.mkdir(parents=True, exist_ok=True)
        target = _OG_BLOG_DIR / f"{slug}-{locale}.png"
        if target.exists():
            return target

        from api.services.og_image import _has_cjk
        img = _draw_blog_card(
            title=title or slug,
            theme_color=theme_color,
            theme_key=theme_key,
            title_is_cjk=_has_cjk(title or ""),
        )
        img.save(target, format="PNG", optimize=True)
        return target
    except Exception as e:
        logger.warning("[blog-og] failed to generate %s-%s: %s", slug, locale, e)
        return None


def _blog_cover_public_url(slug: str, locale: str) -> str:
    base = _base_url()
    return f"{base}/static/og/blog/{slug}-{locale}.png"


def _normalize_jsonish(value: Any) -> Any:
    """Round-trip protection for sqlite vs Postgres JSONB.

    Under Postgres JSONB, SQLAlchemy returns list/dict directly.
    Under sqlite, the same Column(JSON) round-trips as a TEXT string.
    This normalizer guarantees the template always sees a real Python
    list/dict (or [] for missing/empty), so iteration never fails on
    "passed in dev, broke in prod" surprises.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("[blog] malformed JSON in DB column: %r", value[:80])
            return None
    return value


def render_blog_post(db, slug: str, requested_locale: str | None) -> tuple[str, Any]:
    """Validate slug, query published row, render HTML.

    Returns (html, post_model). Raises HTTPException(400) for bad slug,
    HTTPException(404) for missing/unpublished post. Caller (server.py
    route handler) wraps in Response.
    """
    validate_slug(slug)
    locale = _resolve_blog_locale(requested_locale)

    from api.models.sql_models import BlogPost as _BlogPost

    post = (
        db.query(_BlogPost)
        .filter(
            _BlogPost.slug == slug,
            _BlogPost.locale == locale,
            _BlogPost.status == "published",
        )
        .first()
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Not found.")

    base = _base_url()
    theme_key, theme_color = _resolve_theme_color(post.theme)
    faqs = _normalize_jsonish(post.faqs) or []
    tags = _normalize_jsonish(post.tags) or []

    body_html = Markup(_markdown_to_html(post.body_markdown or ""))

    title = post.title or slug
    summary = post.summary or ""

    # Cover image: frontmatter override beats auto-generated. Auto path is
    # static/og/blog/{slug}-{locale}.png (PHASE C). Generation is render-time,
    # idempotent, non-fatal — same inherited ephemeral-fs caveat as explore.
    if post.cover_image:
        cover_image_url: str | None = (
            post.cover_image if str(post.cover_image).startswith("http") else f"{base}{post.cover_image}"
        )
    else:
        _generate_blog_cover(slug, locale, title, theme_key, theme_color)
        cover_image_url = _blog_cover_public_url(slug, locale)

    published_at_iso: str | None = None
    updated_at_iso: str | None = None
    if post.published_at:
        published_at_iso = post.published_at.isoformat()
    if post.updated_at:
        updated_at_iso = post.updated_at.isoformat()

    ctx = {
        "html_lang": _HTML_LANG_MAP.get(locale, "en"),
        "slug": slug,
        "locale": locale,
        "title": title,
        "summary": summary,
        "body_html": body_html,
        "theme": theme_key,
        "theme_color": theme_color,
        "tags": tags,
        "faqs": faqs,
        "cover_image_url": cover_image_url,
        "published_at_iso": published_at_iso,
        "updated_at_iso": updated_at_iso,
        # Header/footer/meta — mirror the shape explore_base.jinja2 expects.
        "meta_title": title + " | Vela",
        "meta_description": _truncate(summary, 160) if summary else _truncate(title, 160),
        "og_title": _truncate(title, 80) + " · Vela",
        "og_description": _truncate(summary or title, 160),
        "og_image": cover_image_url or f"{base}/og-image.png",  # fallback to landing OG
        "canonical_url": f"{base}/blog/{slug}",
        # Slots explore_base.jinja2 expects but blog doesn't use yet:
        "hreflang_alternates": [],
        # `s` strings dict — explore_base footer/header reference s.headerTagline,
        # s.publicDisclaimer, s.privacyLink, s.termsLink. Pass minimal en
        # fallback for PHASE A; PHASES C+ will add a real blog_strings dict.
        "s": _phase_a_strings(locale),
    }

    html = _env.get_template("blog_post.jinja2").render(**ctx)
    return html, post


def render_blog_list(db, requested_locale: str | None) -> str:
    """Render the /blog list page — card grid of published posts for the locale.

    Ordering: published_at DESC (most recent first). NULL published_at can't
    occur because status='published' rows always carry one (auto-stamped if
    frontmatter omitted, per blog_cli.py sync logic).

    Cover images are generated render-time per card (idempotent) — first
    request is slowest, subsequent requests skip the Pillow work.
    """
    locale = _resolve_blog_locale(requested_locale)

    from api.models.sql_models import BlogPost as _BlogPost

    rows = (
        db.query(_BlogPost)
        .filter(
            _BlogPost.locale == locale,
            _BlogPost.status == "published",
        )
        .order_by(_BlogPost.published_at.desc())
        .all()
    )

    base = _base_url()
    posts: list[dict[str, Any]] = []
    for r in rows:
        theme_key, theme_color = _resolve_theme_color(r.theme)
        title = r.title or r.slug
        # Cover: frontmatter override beats auto. Generation idempotent, non-fatal.
        if r.cover_image:
            cover_url = (
                r.cover_image if str(r.cover_image).startswith("http") else f"{base}{r.cover_image}"
            )
        else:
            _generate_blog_cover(r.slug, locale, title, theme_key, theme_color)
            cover_url = _blog_cover_public_url(r.slug, locale)
        posts.append({
            "slug": r.slug,
            "locale": r.locale,
            "title": title,
            "summary": r.summary or "",
            "theme": theme_key,
            "theme_color": theme_color,
            "cover_image_url": cover_url,
            "published_at_iso": r.published_at.isoformat() if r.published_at else None,
            "published_at_date": r.published_at.strftime("%Y-%m-%d") if r.published_at else "",
            "url": f"/blog/{r.slug}",
        })

    ctx = {
        "html_lang": _HTML_LANG_MAP.get(locale, "en"),
        "locale": locale,
        "posts": posts,
        "meta_title": "Blog | Vela" if locale != "zh-TW" else "部落格 | Vela",
        "meta_description": (
            "Articles on multilingual medical AI, Asian healthcare markets, and clinical workflows."
            if locale != "zh-TW"
            else "多語醫療 AI、亞洲健康照護市場與臨床流程的觀點文章。"
        ),
        "og_title": "Vela Blog" if locale != "zh-TW" else "Vela 部落格",
        "og_description": (
            "Articles on multilingual medical AI, Asian healthcare markets, and clinical workflows."
            if locale != "zh-TW"
            else "多語醫療 AI、亞洲健康照護市場與臨床流程的觀點文章。"
        ),
        "og_image": f"{base}/og-image.png",  # landing OG; list page uses landing card
        "canonical_url": f"{base}/blog",
        "hreflang_alternates": [],
        "s": _phase_a_strings(locale),
    }

    return _env.get_template("blog_list.jinja2").render(**ctx)


def _phase_a_strings(locale: str) -> dict[str, str]:
    """Minimal i18n strings the explore_base.jinja2 chrome expects.

    PHASE A ships only what the template touches. PHASES C+ add a
    proper utils/i18n-ui.ts-style blog_strings dict (~10 keys × en +
    zh-TW). Keep this list synced with explore_base.jinja2 references.
    """
    if locale == "zh-TW":
        return {
            "headerTagline": "用您的語言提問醫療文獻",
            "publicDisclaimer": "本文僅供參考,不構成醫療建議。",
            "privacyLink": "隱私",
            "termsLink": "條款",
        }
    return {
        "headerTagline": "Medical literature in your language",
        "publicDisclaimer": "For informational purposes only; not medical advice.",
        "privacyLink": "Privacy",
        "termsLink": "Terms",
    }
