"""PRD § 4.6 PHASE B — sitemap-explore.xml generator.

Builds a sitemaps.org-compliant XML document listing every published
ExplorePage row. Each <url> entry includes <xhtml:link rel="alternate"
hreflang="..."> children for every PUBLISHED sibling in the same
hreflang_group (the "missing-locale skip rule" — draft/archived
siblings are NEVER referenced in the sitemap, matching the runtime
behavior in `explore_renderer._hreflang_alternates`).

Notes:
- Single-page sitemap, no pagination. sitemaps.org allows ≤50,000 URLs
  per file; expansion to sitemap-explore-1.xml / -2.xml is a PHASE C+
  concern.
- All URLs are absolute (VELA_PUBLIC_BASE_URL). For locale-specific
  URLs we use ?locale=zh-TW etc, matching the runtime canonical
  convention (canonical URL has no querystring; siblings carry
  ?locale=).
- changefreq=monthly + priority=0.7 — content pages, lower than
  homepage (1.0) but higher than legal pages (0.5).
- xhtml namespace declaration is mandatory per Google docs for
  hreflang in sitemaps.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.etree.ElementTree import register_namespace

logger = logging.getLogger(__name__)

# Namespace constants
_NS_SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"
_NS_XHTML = "http://www.w3.org/1999/xhtml"

register_namespace("", _NS_SITEMAP)
register_namespace("xhtml", _NS_XHTML)


def _base_url() -> str:
    return os.getenv("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com").rstrip("/")


def _explore_url(slug: str, locale: str) -> str:
    """Sitemap URLs use ?locale=... for ALL rows uniformly.

    Google requires each <url>'s <loc> to be unique and to MATCH one of
    its xhtml:link hreflang href values. Using ?locale= for every row
    makes en + zh-TW + ... distinct loc values, all alignable with
    hreflang alternates. (The runtime HTML canonical tag still uses
    the bare /explore/{slug} URL for en default — Google consolidates
    the two via the hreflang signal.)
    """
    base = _base_url()
    return f"{base}/explore/{slug}?locale={locale}"


def generate_explore_sitemap(db) -> str:
    """Render the full sitemap-explore.xml document as a UTF-8 string.

    db is a SQLAlchemy Session. Returns a `<?xml ... ?><urlset>...</urlset>`
    bytestring decoded to str. Caller wraps in a FastAPI Response with
    media_type='application/xml'.
    """
    from api.models.sql_models import ExplorePage as _ExplorePage

    rows = (
        db.query(_ExplorePage)
        .filter(_ExplorePage.status == "published")
        .order_by(_ExplorePage.last_updated_at.desc())
        .all()
    )

    # Group published siblings by hreflang_group for fast lookup
    by_group: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        if r.hreflang_group:
            by_group[r.hreflang_group].append(r)

    # ElementTree auto-emits `xmlns:xhtml="..."` on the root element
    # when any descendant uses the {xhtml} namespace (register_namespace
    # call above provides the prefix mapping). Don't add it manually or
    # the attr appears twice → "duplicate attribute" parse error.
    urlset = Element(f"{{{_NS_SITEMAP}}}urlset")

    for r in rows:
        url_el = SubElement(urlset, f"{{{_NS_SITEMAP}}}url")

        loc = SubElement(url_el, f"{{{_NS_SITEMAP}}}loc")
        loc.text = _explore_url(r.slug, r.locale)

        if r.last_updated_at:
            lastmod = SubElement(url_el, f"{{{_NS_SITEMAP}}}lastmod")
            # ISO 8601 with date (sitemap spec accepts date or full
            # date-time). Using date-only keeps consistency across
            # row updates that don't change content materially.
            lastmod.text = r.last_updated_at.strftime("%Y-%m-%d")

        changefreq = SubElement(url_el, f"{{{_NS_SITEMAP}}}changefreq")
        changefreq.text = "monthly"

        priority = SubElement(url_el, f"{{{_NS_SITEMAP}}}priority")
        priority.text = "0.7"

        # xhtml hreflang alternates: only published siblings in the
        # same group, only if group has 2+ members (single-row groups
        # carry no hreflang signal). Mirrors explore_renderer.py rules.
        if r.hreflang_group:
            siblings = by_group.get(r.hreflang_group, [])
            if len(siblings) >= 2:
                for s in siblings:
                    SubElement(url_el, f"{{{_NS_XHTML}}}link", {
                        "rel": "alternate",
                        "hreflang": s.locale,
                        "href": _explore_url(s.slug, s.locale),
                    })

    # ElementTree's default serialization picks "ns0:" prefixes for the
    # default namespace when we register both ns + xhtml. We've
    # registered "" → sitemap and "xhtml" → xhtml above, which yields
    # the expected sitemap.org formatting.
    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
