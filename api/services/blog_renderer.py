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
    cover_image_url: str | None = None
    if post.cover_image:
        # Frontmatter override path. PHASE C will generate the auto path
        # at static/og/blog/{slug}-{locale}.png; PHASE A only honors the
        # explicit override.
        cover_image_url = post.cover_image if str(post.cover_image).startswith("http") else f"{base}{post.cover_image}"

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
