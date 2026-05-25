"""sitemap-blog.xml generator (Blog PHASE C).

Mirrors api/services/sitemap_explore.py structure. Lists every published
BlogPost row with per-locale hreflang siblings: when the same slug exists
in multiple published locales (en + zh-TW per MVP), each row carries
<xhtml:link rel="alternate" hreflang="..."> entries pointing at every
sibling. Single-locale slugs carry no hreflang (no signal value).

Wired in api/server.py as GET /sitemap-blog.xml (no rate limit,
crawler-friendly). Referenced from public/sitemap.xml index alongside
sitemap-explore.xml.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.etree.ElementTree import register_namespace

logger = logging.getLogger(__name__)

_NS_SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"
_NS_XHTML = "http://www.w3.org/1999/xhtml"

# Same prefix mapping sitemap_explore.py registers — re-registering with
# identical values is a no-op. Defensive against import order.
register_namespace("", _NS_SITEMAP)
register_namespace("xhtml", _NS_XHTML)


def _base_url() -> str:
    return os.getenv("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com").rstrip("/")


def _blog_url(slug: str, locale: str) -> str:
    """Sitemap URLs use ?locale=... for all rows uniformly (matches
    sitemap_explore convention; Google requires <loc> to be unique +
    aligned with hreflang href values)."""
    base = _base_url()
    return f"{base}/blog/{slug}?locale={locale}"


def generate_blog_sitemap(db) -> str:
    """Render the full sitemap-blog.xml document as a UTF-8 string.

    Hreflang strategy: BlogPost has no hreflang_group column (en + zh-TW
    MVP doesn't need explore's 3-tier related-queries logic). Instead,
    group by slug — if the SAME slug exists in multiple published
    locales, emit hreflang siblings linking them. Single-locale slugs
    emit no hreflang.
    """
    from api.models.sql_models import BlogPost as _BlogPost

    rows = (
        db.query(_BlogPost)
        .filter(_BlogPost.status == "published")
        .order_by(_BlogPost.published_at.desc())
        .all()
    )

    # Group published rows by slug → list of (locale, row).
    by_slug: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_slug[r.slug].append(r)

    urlset = Element(f"{{{_NS_SITEMAP}}}urlset")

    for r in rows:
        url_el = SubElement(urlset, f"{{{_NS_SITEMAP}}}url")

        loc = SubElement(url_el, f"{{{_NS_SITEMAP}}}loc")
        loc.text = _blog_url(r.slug, r.locale)

        # Prefer published_at for blog lastmod (editorial intent); fall
        # back to updated_at. Date-only ISO per sitemap_explore convention.
        lastmod_dt = r.published_at or r.updated_at
        if lastmod_dt:
            lastmod = SubElement(url_el, f"{{{_NS_SITEMAP}}}lastmod")
            lastmod.text = lastmod_dt.strftime("%Y-%m-%d")

        changefreq = SubElement(url_el, f"{{{_NS_SITEMAP}}}changefreq")
        changefreq.text = "monthly"

        priority = SubElement(url_el, f"{{{_NS_SITEMAP}}}priority")
        priority.text = "0.7"

        # hreflang siblings — only when ≥2 published locales share this slug.
        siblings = by_slug.get(r.slug, [])
        if len(siblings) >= 2:
            for s in siblings:
                SubElement(url_el, f"{{{_NS_XHTML}}}link", {
                    "rel": "alternate",
                    "hreflang": s.locale,
                    "href": _blog_url(s.slug, s.locale),
                })

    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
