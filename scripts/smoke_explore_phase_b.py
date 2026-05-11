"""PRD § 4.6 PHASE B — sitemap-explore.xml + hreflang missing-locale skip rule smoke driver.

Renders /sitemap-explore.xml + /explore/{slug} via FastAPI TestClient
against a temp SQLite DB. Asserts:
- Sitemap is well-formed XML with sitemaps.org + xhtml namespaces
- Published-pair: both URLs in sitemap, both have hreflang alternates
- Drafted sibling: dropped from sitemap, dropped from HTML hreflang
- Restored: emission resumes

For dev environment live testing (uvicorn against Neon Postgres),
use scripts/seed_explore_dev.py.
"""
from __future__ import annotations

import os
import sys
import pathlib
from datetime import datetime
from xml.etree.ElementTree import fromstring

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_explore_phase_b.db")
os.environ.setdefault("SHARE_CREATED_BY_SALT", "smoke_salt_v1")
os.environ.setdefault("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

db_path = pathlib.Path("tmp_explore_phase_b.db")
if db_path.exists():
    db_path.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from api.server import app  # noqa: E402
from api.database.sql_db import Base, engine, SessionLocal  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def _seed_pair_published():
    """Seed metformin-renal-dose-adjustment in en + zh-TW, both published."""
    now_dt = datetime.utcnow()
    with SessionLocal() as db:
        # Clear any previous state
        db.query(ExplorePage).delete()
        db.commit()
        db.add(ExplorePage(
            slug="metformin-renal-dose-adjustment",
            locale="en",
            query_text="How should metformin be dose-adjusted for patients with renal impairment?",
            answer_text="## Overview \U0001F7E2 — English\nMetformin is generally safe...\n",
            citations=[],
            meta_title="Metformin Renal Dose Adjustment | Vela",
            meta_description="Evidence-based dose adjustment of metformin.",
            category="dose-adjustment",
            hreflang_group="metformin-renal",
            status="published",
            published_at=now_dt,
            last_updated_at=now_dt,
            view_count=0,
        ))
        db.add(ExplorePage(
            slug="metformin-renal-dose-adjustment",
            locale="zh-TW",
            query_text="腎功能不全患者如何調整 metformin 劑量？",
            answer_text="## 概述 \U0001F7E2 — Chinese\n暫定文字。",
            citations=[],
            meta_title="Metformin 腎功能調整",
            meta_description="證據導向的劑量調整指引。",
            category="dose-adjustment",
            hreflang_group="metformin-renal",
            status="published",
            published_at=now_dt,
            last_updated_at=now_dt,
            view_count=0,
        ))
        db.commit()


def _set_zh_status(status: str):
    with SessionLocal() as db:
        row = db.query(ExplorePage).filter(
            ExplorePage.slug == "metformin-renal-dose-adjustment",
            ExplorePage.locale == "zh-TW",
        ).first()
        row.status = status
        db.commit()


def case(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


all_ok = True

# Initial seed: both published
_seed_pair_published()

# ── 1. Sitemap basic shape ──────────────────────────────────────
r = client.get("/sitemap-explore.xml")
all_ok &= case("HTTP 200 sitemap", r.status_code == 200, f"status={r.status_code}")
all_ok &= case("Content-Type application/xml",
               "application/xml" in r.headers.get("content-type", ""),
               r.headers.get("content-type", ""))

xml_text = r.text

out_dir = pathlib.Path("artifacts")
out_dir.mkdir(exist_ok=True)
(out_dir / "sitemap-explore.xml").write_text(xml_text, encoding="utf-8")

# ── 2. XML well-formed ──────────────────────────────────────────
try:
    root = fromstring(xml_text)
    well_formed = True
except Exception as e:
    well_formed = False
    print(f"  parse error: {e}")
all_ok &= case("XML well-formed", well_formed)

# ── 3. Required namespaces ──────────────────────────────────────
all_ok &= case("sitemaps.org namespace", 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml_text)
all_ok &= case("xhtml namespace", 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in xml_text)

# ── 4. Two <url> entries (en + zh-TW both published) ────────────
NS_SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
NS_XHTML = "{http://www.w3.org/1999/xhtml}"
url_els = root.findall(f"{NS_SM}url")
all_ok &= case("Two <url> entries (published-pair)", len(url_els) == 2, f"count={len(url_els)}")

# ── 5. Each <url> has unique <loc> + lastmod/changefreq/priority ──
en_url = next((u for u in url_els if (u.findtext(f"{NS_SM}loc") or "").endswith("?locale=en")), None)
zh_url = next((u for u in url_els if (u.findtext(f"{NS_SM}loc") or "").endswith("?locale=zh-TW")), None)
all_ok &= case("en <url> has <loc> ending ?locale=en", en_url is not None)
all_ok &= case("zh-TW <url> has <loc> ending ?locale=zh-TW", zh_url is not None)
if en_url is not None:
    all_ok &= case("en <url> has <lastmod>", en_url.find(f"{NS_SM}lastmod") is not None)
    all_ok &= case("en <url> has <changefreq>",
                   en_url.findtext(f"{NS_SM}changefreq") == "monthly")
    all_ok &= case("en <url> has <priority>",
                   en_url.findtext(f"{NS_SM}priority") == "0.7")

# ── 6. en page references zh-TW sibling via xhtml:link ─────────
if en_url is not None:
    alts = en_url.findall(f"{NS_XHTML}link")
    zh_alt = [a for a in alts if a.get("hreflang") == "zh-TW"]
    all_ok &= case("en <url> has xhtml:link hreflang=zh-TW",
                   len(zh_alt) == 1,
                   f"zh-TW alts={len(zh_alt)}, total alts={len(alts)}")

# ── 7. zh-TW page references en sibling via xhtml:link ─────────
if zh_url is not None:
    alts = zh_url.findall(f"{NS_XHTML}link")
    en_alt = [a for a in alts if a.get("hreflang") == "en"]
    all_ok &= case("zh-TW <url> has xhtml:link hreflang=en",
                   len(en_alt) == 1,
                   f"en alts={len(en_alt)}, total alts={len(alts)}")

# ── 8. Draft zh-TW: only 1 <url>, en has 0 xhtml:link ──────────
_set_zh_status("draft")
r2 = client.get("/sitemap-explore.xml")
all_ok &= case("HTTP 200 sitemap (after draft)", r2.status_code == 200)
root2 = fromstring(r2.text)
url_els2 = root2.findall(f"{NS_SM}url")
all_ok &= case("One <url> entry (draft sibling dropped)", len(url_els2) == 1, f"count={len(url_els2)}")
if len(url_els2) == 1:
    alts2 = url_els2[0].findall(f"{NS_XHTML}link")
    all_ok &= case("en <url> has 0 xhtml:link (only self in group)",
                   len(alts2) == 0,
                   f"alts={len(alts2)}")

# ── 9. Restore + check /explore/ HTML (zh-TW restored) ─────────
_set_zh_status("published")
r3 = client.get("/explore/metformin-renal-dose-adjustment?locale=zh-TW")
all_ok &= case("HTTP 200 zh-TW explore (after restore)", r3.status_code == 200)
all_ok &= case("zh-TW HTML has hreflang en", 'hreflang="en"' in r3.text)

# ── 10. Draft zh-TW: en HTML has NO hreflang tags ──────────────
_set_zh_status("draft")
r4 = client.get("/explore/metformin-renal-dose-adjustment")
all_ok &= case("HTTP 200 en explore (draft sibling)", r4.status_code == 200)
all_ok &= case("en HTML has NO hreflang tag (draft sibling skipped)",
               'rel="alternate" hreflang=' not in r4.text)

# ── 11. /sitemap.xml index references sitemap-explore.xml ──────
# Note: in dev /sitemap.xml is served by Next.js static (public/sitemap.xml).
# This smoke test runs against FastAPI only, so we check public/ file directly.
sitemap_index_path = pathlib.Path("public") / "sitemap.xml"
if sitemap_index_path.exists():
    idx_text = sitemap_index_path.read_text(encoding="utf-8")
    all_ok &= case("sitemap.xml is sitemapindex", "<sitemapindex" in idx_text)
    all_ok &= case("sitemap.xml references sitemap-explore.xml",
                   "sitemap-explore.xml" in idx_text)
    all_ok &= case("sitemap.xml references sitemap-main.xml",
                   "sitemap-main.xml" in idx_text)
else:
    all_ok &= case("public/sitemap.xml exists", False, "missing")

# ── 12. Cleanup: restore zh-TW so any subsequent runs reuse DB cleanly ──
_set_zh_status("published")

print("=" * 50)
print(f"Saved artifacts: {out_dir.resolve()}")
print("PASS" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
