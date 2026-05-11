"""PRD § 4.6 PHASE A — Explore page smoke driver.

Renders /explore/{slug} via FastAPI TestClient against a temp SQLite DB.
Seeds 1 published + 1 draft fixture row + 1 published hreflang sibling.

For dev environment live testing (uvicorn against Neon Postgres),
use scripts/seed_explore_dev.py instead — that script targets the
real DATABASE_URL and is idempotent.
"""
from __future__ import annotations

import os
import sys
import pathlib
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_explore_phase_a.db")
os.environ.setdefault("SHARE_CREATED_BY_SALT", "smoke_salt_v1")
os.environ.setdefault("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

db_path = pathlib.Path("tmp_explore_phase_a.db")
if db_path.exists():
    db_path.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from api.server import app  # noqa: E402
from api.database.sql_db import Base, engine, SessionLocal  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ANSWER = (
    "## Overview \U0001F7E2 — English\n"
    "Metformin is generally safe in mild-to-moderate renal impairment but "
    "requires dose adjustment when eGFR declines.\n\n"
    "## Dose Adjustment \U0001F7E1 — English\n"
    "Reduce dose at eGFR 30-45 mL/min/1.73m²; discontinue below 30.\n\n"
    "## Risks \U0001F534 — English\n"
    "Lactic acidosis risk rises with advanced CKD; rare but serious.\n"
)

CITATIONS = [
    {
        "id": 1,
        "title": "Metformin Renal Dosing Guidelines",
        "url": "https://pubmed.ncbi.nlm.nih.gov/22334455",
        "source_type": "pubmed",
        "source_id": "PMID:22334455",
        "authors": "Inzucchi SE",
        "journal": "JAMA",
        "year": "2014",
        "snippet": (
            "## Abstract\n"
            "Review of metformin renal dosing recommendations updated "
            "after the 2016 FDA label change permitting use at eGFR ≥30."
        ),
        "credibility": "peer-reviewed",
    },
]

now_dt = datetime.utcnow()

with SessionLocal() as db:
    # 1 published row (primary test target)
    db.add(ExplorePage(
        slug="metformin-renal-dose-adjustment",
        locale="en",
        query_text="How should metformin be dose-adjusted for patients with renal impairment?",
        answer_text=ANSWER,
        citations=CITATIONS,
        meta_title="Metformin Renal Dose Adjustment | Vela",
        meta_description="Evidence-based dose adjustment of metformin for patients with renal impairment.",
        category="dose-adjustment",
        hreflang_group="metformin-renal",
        status="published",
        published_at=now_dt,
        last_updated_at=now_dt,
        view_count=0,
    ))
    # 1 draft row (must return 404)
    db.add(ExplorePage(
        slug="some-draft-page",
        locale="en",
        query_text="Draft page",
        answer_text="## Draft \U0001F7E2 — English\nDraft content.",
        citations=[],
        meta_title="Draft",
        meta_description="Draft",
        category="dose-adjustment",
        hreflang_group=None,
        status="draft",
        published_at=None,
        last_updated_at=now_dt,
        view_count=0,
    ))
    db.commit()


def case(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


all_ok = True

# 1. GET published page returns 200
r = client.get("/explore/metformin-renal-dose-adjustment")
all_ok &= case("HTTP 200 published", r.status_code == 200, f"status={r.status_code}")
html = r.text

out_dir = pathlib.Path("artifacts")
out_dir.mkdir(exist_ok=True)
(out_dir / "explore_metformin.html").write_text(html, encoding="utf-8")

# 2. HTML contains query_text, answer_text, citation
all_ok &= case("Query title rendered", "How should metformin be dose-adjusted" in html)
all_ok &= case("Section content rendered", "Lactic acidosis" in html)
all_ok &= case("Citation title rendered", "Metformin Renal Dosing Guidelines" in html)

# 3. Canonical URL
all_ok &= case("Canonical URL", '<link rel="canonical" href="https://vela.an-tho.com/explore/metformin-renal-dose-adjustment">' in html)

# 4. OG meta tags
all_ok &= case("og:title", '<meta property="og:title"' in html)
all_ok &= case("og:description", '<meta property="og:description"' in html)
all_ok &= case("og:image (explore folder)", '/static/og/explore/metformin-renal-dose-adjustment-en.png' in html)

# 5. JSON-LD QAPage schema
all_ok &= case("JSON-LD QAPage", '"@type": "QAPage"' in html)
all_ok &= case("JSON-LD acceptedAnswer", '"acceptedAnswer"' in html)

# 6. No share-only affordances
all_ok &= case("No 'Shared by'", "Shared by" not in html)
all_ok &= case("No revoke text", "revoked" not in html.lower())
all_ok &= case("No report-content text", "Report content" not in html)

# 7. CTA links to /?from_explore=...
all_ok &= case("CTA from_explore link", '/?from_explore=metformin-renal-dose-adjustment' in html)
all_ok &= case("CTA banner text en", "Want to ask your own version?" in html)

# 8. Nonexistent slug → 404
r404 = client.get("/explore/this-slug-does-not-exist")
all_ok &= case("404 missing slug", r404.status_code == 404, f"status={r404.status_code}")

# 9. Invalid slug pattern → 400
r400 = client.get("/explore/INVALID_SLUG_UPPERCASE")
all_ok &= case("400 invalid slug (uppercase)", r400.status_code == 400, f"status={r400.status_code}")

r400b = client.get("/explore/has--double-hyphen")
# `has--double-hyphen` fails the (a-z0-9)+(-(a-z0-9)+)* pattern → 400
all_ok &= case("400 invalid slug (double hyphen)", r400b.status_code == 400, f"status={r400b.status_code}")

# 10. Draft page → 404 (not 403)
r_draft = client.get("/explore/some-draft-page")
all_ok &= case("404 draft (not 403)", r_draft.status_code == 404, f"status={r_draft.status_code}")

# 11. hreflang absent when no published sibling exists (this group only has 1 row)
all_ok &= case("No hreflang alternates (single-row group)",
               'rel="alternate" hreflang=' not in html)

# 12. view_count increments after GET
with SessionLocal() as db:
    refreshed = db.query(ExplorePage).filter(
        ExplorePage.slug == "metformin-renal-dose-adjustment",
        ExplorePage.locale == "en",
    ).first()
    all_ok &= case("view_count incremented",
                   (refreshed.view_count or 0) >= 1,
                   f"view_count={refreshed.view_count}")

# Bonus: hreflang sibling case — add a zh-TW row in the same group and re-fetch
with SessionLocal() as db:
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

r2 = client.get("/explore/metformin-renal-dose-adjustment")
all_ok &= case("Bonus: hreflang alt en present",
               'rel="alternate" hreflang="en"' in r2.text)
all_ok &= case("Bonus: hreflang alt zh-TW present",
               'rel="alternate" hreflang="zh-TW"' in r2.text)

print("=" * 50)
print(f"Saved artifacts: {out_dir.resolve()}")
print("PASS" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
