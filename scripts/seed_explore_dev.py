"""Dev DB seed for §4.6 PHASE A.

Connects to whatever DATABASE_URL points to (typically Neon Postgres
in dev), ensures the `explore_page` table exists via
Base.metadata.create_all, and idempotently UPSERTs the sample rows
used for /explore/* live testing.

Usage:
    python scripts/seed_explore_dev.py

Idempotent — safe to run multiple times. Re-running refreshes the
content fields but preserves the row identity (slug, locale).

NOT a migration replacement. Production deploy still uses
migrations/005_add_explore_page.sql via the formal track. This is a
dev convenience tool. Schema-drift risk bounded: migration 005 and
the SQLAlchemy ExplorePage model live in the same commit (bc171a1)
with identical structure.

Seed data mirrors scripts/smoke_explore_phase_a.py so a dev manual
test reproduces the smoke-test environment 1:1.
"""

from __future__ import annotations

import sys
import pathlib
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from api.database.sql_db import engine, SessionLocal, Base  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402


# Fixed timestamp so repeated runs don't churn the value on UPDATE.
_PUBLISHED_AT = datetime(2026, 5, 11, tzinfo=timezone.utc)

_ANSWER_EN = (
    "## Overview \U0001F7E2 — English\n"
    "Metformin is generally safe in mild-to-moderate renal impairment but "
    "requires dose adjustment when eGFR declines.\n\n"
    "## Dose Adjustment \U0001F7E1 — English\n"
    "Reduce dose at eGFR 30-45 mL/min/1.73m²; discontinue below 30.\n\n"
    "## Risks \U0001F534 — English\n"
    "Lactic acidosis risk rises with advanced CKD; rare but serious.\n"
)

_CITATIONS_EN = [
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

SAMPLE_ROWS: list[dict] = [
    {
        "slug": "metformin-renal-dose-adjustment",
        "locale": "en",
        "query_text": "How should metformin be dose-adjusted for patients with renal impairment?",
        "answer_text": _ANSWER_EN,
        "citations": _CITATIONS_EN,
        "meta_title": "Metformin Renal Dose Adjustment | Vela",
        "meta_description": "Evidence-based dose adjustment of metformin for patients with renal impairment.",
        "category": "dose-adjustment",
        "hreflang_group": "metformin-renal",
        "status": "published",
        "published_at": _PUBLISHED_AT,
    },
    # zh-TW sibling — provides a way to manually verify hreflang
    # alternates render in dev (single-row groups skip emission).
    {
        "slug": "metformin-renal-dose-adjustment",
        "locale": "zh-TW",
        "query_text": "腎功能不全患者如何調整 metformin 劑量？",
        "answer_text": "## 概述 \U0001F7E2 — Chinese\n暫定文字。",
        "citations": [],
        "meta_title": "Metformin 腎功能調整",
        "meta_description": "證據導向的劑量調整指引。",
        "category": "dose-adjustment",
        "hreflang_group": "metformin-renal",
        "status": "published",
        "published_at": _PUBLISHED_AT,
    },
]


def main() -> int:
    print("Ensuring explore_page table exists...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for row_data in SAMPLE_ROWS:
            slug = row_data["slug"]
            locale = row_data["locale"]
            existing = (
                session.query(ExplorePage)
                .filter_by(slug=slug, locale=locale)
                .first()
            )

            if existing:
                print(f"  UPDATE {slug} ({locale})")
                for key, value in row_data.items():
                    setattr(existing, key, value)
                existing.last_updated_at = datetime.utcnow()
            else:
                print(f"  INSERT {slug} ({locale})")
                row = ExplorePage(**row_data, last_updated_at=datetime.utcnow())
                session.add(row)

        session.commit()

        count = session.query(ExplorePage).filter_by(status="published").count()
        print(f"\nDone. explore_page has {count} published row(s).")
        print("\nTest with:")
        print("  curl http://localhost:8000/explore/metformin-renal-dose-adjustment")
        print("  or open http://localhost:3000/explore/metformin-renal-dose-adjustment")
        print("  hreflang test: http://localhost:3000/explore/metformin-renal-dose-adjustment?locale=zh-TW")
        return 0
    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
