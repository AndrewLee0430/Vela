"""Server-side renderer for PRD § 4.6 SEO Explore Pages.

Team-curated public pages at /explore/{slug}. Reuses § 4.5 PHASE A's
public-page renderer helpers from `api/services/share_renderer.py`:
- parse_research_sections() for evidence-strength card splitting
- _augment_citations() for citation chrome (source label, cred pill)
- _markdown_to_html() for markdown → HTML
- _MARKER_BORDER_COLORS for evidence card left-border colors
- _base_url() for canonical URL building
- _truncate() for OG meta sizing
- resolve_locale() for locale fallback

Templates are SEPARATE (api/templates/q_explore.jinja2 +
explore_base.jinja2) because the team-content surface differs from
the user-shared-answer surface (no revoke / report affordances,
breadcrumb + related-queries slots for PHASE D, hreflang siblings in
<head>).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image

from api.services.share_renderer import (
    _MARKER_BORDER_COLORS,
    _augment_citations,
    _base_url,
    _markdown_to_html,
    _truncate,
    parse_research_sections,
)

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "jinja2", "xml"]),
)

# Slug pattern per PRD § 4.6 需求 1: lowercase + hyphens + ASCII
# alphanumeric, ≤ 80 chars. Chinese/punycode deferred to post-Phase 1B
# based on GSC data.
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MAX_LEN = 80

_HTML_LANG_MAP = {
    "en": "en", "zh-TW": "zh-Hant", "zh-CN": "zh-Hans",
    "ja": "ja", "ko": "ko", "es": "es", "fr": "fr", "de": "de",
    "it": "it", "pt": "pt", "th": "th", "ar": "ar", "hi": "hi",
    "bn": "bn", "he": "he", "vi": "vi",
}

_OG_EXPLORE_DIR = Path("static") / "og" / "explore"


def validate_slug(slug: str) -> None:
    """Raise HTTPException(400) if slug doesn't match PRD pattern."""
    if not slug or len(slug) > _SLUG_MAX_LEN or not _SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug.")


def _resolve_explore_locale(requested: str | None) -> str:
    """Fall back to 'en' for any locale not in the html-lang map."""
    if requested and requested in _HTML_LANG_MAP:
        return requested
    return "en"


def _generate_explore_og(slug: str, locale: str, query_text: str) -> Path | None:
    """Generate the OG image for an explore page at
    static/og/explore/{slug}-{locale}.png. Idempotent: skip if exists.

    Standalone implementation (rather than calling og_image.generate_og_png
    directly) because that helper hardcodes static/og/{share_id}.png.
    Same rendering pipeline (Pillow placeholder) — wraps with the
    explore-specific path.
    """
    try:
        _OG_EXPLORE_DIR.mkdir(parents=True, exist_ok=True)
        target = _OG_EXPLORE_DIR / f"{slug}-{locale}.png"
        if target.exists():
            return target

        # Reuse the share OG drawing function via internal import. Keeps
        # the visual identical between /q and /explore pages.
        from api.services.og_image import _draw_card, _has_cjk
        img: Image.Image = _draw_card(query_text or slug, query_is_cjk=_has_cjk(query_text or ""))
        img.save(target, format="PNG", optimize=True)
        return target
    except Exception as e:
        logger.warning("[explore-og] failed to generate %s-%s: %s", slug, locale, e)
        return None


def _explore_og_public_url(slug: str, locale: str) -> str:
    base = _base_url()
    return f"{base}/static/og/explore/{slug}-{locale}.png"


def _hreflang_alternates(db, page, current_locale: str) -> list[dict[str, str]]:
    """Return list of {locale, html_lang, url} for published siblings
    that share `page.hreflang_group`. Empty list if no group or no
    published siblings.
    """
    if not getattr(page, "hreflang_group", None):
        return []

    # Local import to avoid circular dependency at module load
    from api.models.sql_models import ExplorePage as _ExplorePage

    siblings = (
        db.query(_ExplorePage)
        .filter(
            _ExplorePage.hreflang_group == page.hreflang_group,
            _ExplorePage.status == "published",
        )
        .all()
    )
    # Skip emission if only self is in the group — self-only hreflang
    # carries no signal value and clutters head.
    if len(siblings) <= 1:
        return []

    base = _base_url()
    out: list[dict[str, str]] = []
    for s in siblings:
        loc = s.locale
        out.append({
            "locale": loc,
            "html_lang": _HTML_LANG_MAP.get(loc, loc),
            "url": f"{base}/explore/{s.slug}?locale={loc}" if loc != current_locale else f"{base}/explore/{s.slug}",
        })
    return out


def render_explore_page(db, slug: str, requested_locale: str | None) -> tuple[str, "Any"]:
    """Validate slug, query published row, render HTML.

    Returns (html, page_model). Raises HTTPException(400) for bad slug,
    HTTPException(404) for missing/unpublished page. Caller (server.py
    route handler) is responsible for the 200 Response wrap and
    view_count commit (see /q/{share_id} pattern at server.py:1894).
    """
    validate_slug(slug)
    locale = _resolve_explore_locale(requested_locale)

    from api.i18n.explore_strings import get_explore_strings
    from api.models.sql_models import ExplorePage as _ExplorePage

    page = (
        db.query(_ExplorePage)
        .filter(
            _ExplorePage.slug == slug,
            _ExplorePage.locale == locale,
            _ExplorePage.status == "published",
        )
        .first()
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Not found.")

    s = get_explore_strings(locale)
    base = _base_url()

    parsed = parse_research_sections(page.answer_text or "")
    sections: list[dict[str, Any]] = []
    for sec in parsed:
        sections.append({
            "title": sec["title"],
            "marker": sec["marker"],
            "border_color": _MARKER_BORDER_COLORS.get(sec["marker"], _MARKER_BORDER_COLORS[None]),
            "html": Markup(_markdown_to_html(sec["content"])),
        })

    augmented, source_chips = _augment_citations(page.citations or [], _share_renderer_locale(locale))

    # OG image (non-fatal — placeholder served if generation fails)
    _generate_explore_og(slug, locale, page.query_text or "")

    hreflang_alternates = _hreflang_alternates(db, page, locale)

    related_queries = get_related_queries(
        db, slug, locale,
        getattr(page, "category", None),
        getattr(page, "hreflang_group", None),
    )

    ctx = {
        "html_lang": _HTML_LANG_MAP.get(locale, "en"),
        "s": s,
        "slug": slug,
        "locale": locale,
        "category": getattr(page, "category", None) or "",
        "query_text": page.query_text or "",
        "answer_text": page.answer_text or "",
        "meta_title": page.meta_title or page.query_text or "Vela",
        "meta_description": page.meta_description or _truncate(page.answer_text or "", 160),
        "og_title": _truncate(page.meta_title or page.query_text or "", 80) + " · Vela",
        "og_description": _truncate(page.meta_description or page.answer_text or "", 160),
        "og_image": _explore_og_public_url(slug, locale),
        "canonical_url": f"{base}/explore/{slug}",
        "sections": sections,
        "citations": augmented,
        "source_chips": source_chips,
        "hreflang_alternates": hreflang_alternates,
        "related_queries": related_queries,
        "from_explore_link": f"/?from_explore={slug}",
    }

    html = _env.get_template("q_explore.jinja2").render(**ctx)
    return html, page


def _share_renderer_locale(locale: str) -> str:
    """share_renderer._augment_citations expects a locale that is a key
    of its _STRINGS dict (only 'en' and 'zh-TW' shipped in PHASE A).
    Map anything else to 'en' for citation chrome string lookups —
    the explore page-level strings still localize via explore_strings.
    """
    return "zh-TW" if locale == "zh-TW" else "en"


_RELATED_QUERIES_CAP = 8


def get_related_queries(db, current_slug: str, current_locale: str,
                        category: str | None, hreflang_group: str | None) -> list[dict]:
    """PRD § 4.6 PHASE D — pick up to 8 related ExplorePage rows.

    3-tier priority:
      Tier 1 (link_type='hreflang'): same hreflang_group, different locale.
      Tier 2 (link_type='category'): same category, different slug, current locale.
      Tier 3 (link_type='category'): same category, different slug, any locale
                                     (fallback when Tier 2 is sparse).

    Returns list of dicts ready for the template:
      {slug, locale, query_text, meta_description, link_type}
    """
    from api.models.sql_models import ExplorePage as _ExplorePage

    out: list[dict] = []
    seen: set[tuple[str, str]] = {(current_slug, current_locale)}

    # Tier 1 — hreflang siblings (cross-locale).
    if hreflang_group:
        tier1 = (
            db.query(_ExplorePage)
            .filter(
                _ExplorePage.hreflang_group == hreflang_group,
                _ExplorePage.status == "published",
                _ExplorePage.locale != current_locale,
            )
            .all()
        )
        for r in tier1:
            key = (r.slug, r.locale)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "slug": r.slug,
                "locale": r.locale,
                "query_text": r.query_text or "",
                "meta_description": r.meta_description or "",
                "link_type": "hreflang",
            })
            if len(out) >= _RELATED_QUERIES_CAP:
                return out

    # Tier 2 — same category, current locale.
    if category:
        tier2 = (
            db.query(_ExplorePage)
            .filter(
                _ExplorePage.category == category,
                _ExplorePage.locale == current_locale,
                _ExplorePage.status == "published",
                _ExplorePage.slug != current_slug,
            )
            .order_by(_ExplorePage.last_updated_at.desc())
            .all()
        )
        for r in tier2:
            key = (r.slug, r.locale)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "slug": r.slug,
                "locale": r.locale,
                "query_text": r.query_text or "",
                "meta_description": r.meta_description or "",
                "link_type": "category",
            })
            if len(out) >= _RELATED_QUERIES_CAP:
                return out

        # Tier 3 — same category, any locale (fallback if Tier 2 sparse).
        tier3 = (
            db.query(_ExplorePage)
            .filter(
                _ExplorePage.category == category,
                _ExplorePage.status == "published",
                _ExplorePage.slug != current_slug,
            )
            .order_by(_ExplorePage.last_updated_at.desc())
            .all()
        )
        for r in tier3:
            key = (r.slug, r.locale)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "slug": r.slug,
                "locale": r.locale,
                "query_text": r.query_text or "",
                "meta_description": r.meta_description or "",
                "link_type": "category",
            })
            if len(out) >= _RELATED_QUERIES_CAP:
                return out

    return out


def render_category_listing(db, category: str, requested_locale: str | None) -> str:
    """PRD § 4.6 PHASE D — list all published pages in a category.

    Returns HTML. Raises HTTPException(400) for invalid category slug,
    HTTPException(404) when no published rows match.

    Category slug uses the SAME pattern as explore page slug
    (lowercase + hyphens, ≤80 chars) — content authors are expected
    to enter URL-safe categories at import time.
    """
    validate_slug(category)
    locale = _resolve_explore_locale(requested_locale)

    from api.i18n.explore_strings import get_explore_strings
    from api.models.sql_models import ExplorePage as _ExplorePage

    rows = (
        db.query(_ExplorePage)
        .filter(
            _ExplorePage.category == category,
            _ExplorePage.status == "published",
        )
        .order_by(_ExplorePage.last_updated_at.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Not found.")

    s = get_explore_strings(locale)
    base = _base_url()

    pages: list[dict[str, Any]] = []
    for r in rows:
        pages.append({
            "slug": r.slug,
            "locale": r.locale,
            "query_text": r.query_text or "",
            "meta_description": _truncate(r.meta_description or "", 160),
            "last_updated_at": r.last_updated_at.strftime("%Y-%m-%d") if r.last_updated_at else "",
        })

    title = s.get("category_listing_title", "{category} pages").format(category=category)

    ctx = {
        "html_lang": _HTML_LANG_MAP.get(locale, "en"),
        "s": s,
        "category": category,
        "locale": locale,
        "pages": pages,
        "meta_title": f"{title} | Vela",
        "meta_description": _truncate(title, 160),
        "og_title": _truncate(title, 80) + " · Vela",
        "og_description": _truncate(title, 160),
        # Category listings reuse the explore-folder placeholder OG; no
        # per-category OG image in PHASE D.
        "og_image": f"{base}/static/og/explore/default.png",
        "canonical_url": f"{base}/explore/category/{category}",
        # Category listings have no multi-locale siblings to advertise.
        "hreflang_alternates": [],
        "category_title": title,
    }

    return _env.get_template("category_listing.jinja2").render(**ctx)
