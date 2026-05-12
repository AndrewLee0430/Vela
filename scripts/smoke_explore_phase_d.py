"""PRD § 4.6 PHASE D — smoke driver (lean, ≤20 assertions).

Tests breadcrumb + category listing + related queries + PostHog event
script injection. Fixture: 3 published rows in 'contraindications'
category (en) + 1 zh-TW hreflang sibling of one of them + 1 archived.

Run external PHASE A/B/C smokes separately for regression.
"""
from __future__ import annotations

import os
import sys
import pathlib
from datetime import datetime

# Reconfigure stdout to UTF-8 BEFORE any api.* imports — vector_store.py
# prints a checkmark glyph at import time which fails under Windows CP950.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_explore_phase_d.db")
os.environ.setdefault("SHARE_CREATED_BY_SALT", "smoke_salt_v1")
os.environ.setdefault("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

db_path = pathlib.Path("tmp_explore_phase_d.db")
if db_path.exists():
    db_path.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from api.server import app  # noqa: E402
from api.database.sql_db import Base, engine, SessionLocal  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

now_dt = datetime.utcnow()
ANS = "## Overview \U0001F7E2 — English\nBody.\n"

with SessionLocal() as db:
    # 3 published rows in 'contraindications' (en)
    for s in ("metformin-contraindications-renal", "warfarin-contraindications-pregnancy", "statin-contraindications-liver"):
        db.add(ExplorePage(
            slug=s, locale="en",
            query_text=f"Test query for {s}",
            answer_text=ANS, citations=[],
            meta_title=f"{s} | Vela",
            meta_description=f"Meta description for {s}.",
            category="contraindications",
            hreflang_group=("metformin-contra" if "metformin" in s else None),
            status="published", published_at=now_dt, last_updated_at=now_dt, view_count=0,
        ))
    # 1 zh-TW hreflang sibling of metformin
    db.add(ExplorePage(
        slug="metformin-contraindications-renal", locale="zh-TW",
        query_text="Metformin 在腎功能不全的禁忌症",
        answer_text="## 概述 \U0001F7E2 — Chinese\n暫定。",
        citations=[], meta_title="t", meta_description="d",
        category="contraindications", hreflang_group="metformin-contra",
        status="published", published_at=now_dt, last_updated_at=now_dt, view_count=0,
    ))
    # 1 archived row in same category — must NOT appear in listing
    db.add(ExplorePage(
        slug="some-archived-page", locale="en",
        query_text="Archived", answer_text=ANS, citations=[],
        meta_title="x", meta_description="x", category="contraindications",
        hreflang_group=None, status="archived",
        published_at=None, last_updated_at=now_dt, view_count=0,
    ))
    # 1 isolated published row in DIFFERENT category (for "no related" test)
    db.add(ExplorePage(
        slug="isolated-page", locale="en",
        query_text="Isolated", answer_text=ANS, citations=[],
        meta_title="i", meta_description="i", category="dose-adjustment",
        hreflang_group=None, status="published",
        published_at=now_dt, last_updated_at=now_dt, view_count=0,
    ))
    db.commit()


def case(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


all_ok = True

# ---- Page with related queries (metformin: has hreflang + category siblings) ----
r = client.get("/explore/metformin-contraindications-renal")
all_ok &= case("page 200", r.status_code == 200, f"status={r.status_code}")
html = r.text

# Breadcrumb (4)
all_ok &= case("breadcrumb nav present", '<nav class="vela-breadcrumb"' in html)
all_ok &= case("breadcrumb 4 segments (category set)",
               '/explore/category/contraindications' in html)
all_ok &= case("breadcrumb category label rendered", '>contraindications<' in html)
all_ok &= case("breadcrumb-current span present", 'vela-breadcrumb-current' in html)

# Related queries (5)
all_ok &= case("related section rendered", '<section class="vela-related-queries"' in html)
all_ok &= case("Tier 1 hreflang link_type",
               'data-link-type="hreflang"' in html)
all_ok &= case("Tier 2 category link_type",
               'data-link-type="category"' in html)
all_ok &= case("locale badge for zh-TW sibling",
               'vela-related-card-locale' in html and 'zh-TW' in html)
# Cap test — re-count: with our fixture there are 3 related (1 hreflang + 2 category).
# Cap is 8; just assert no more than 8 cards.
card_count = html.count('class="vela-related-card"')
all_ok &= case("cards ≤ 8", card_count <= 8, f"cards={card_count}")

# Page with NO related (isolated-page is the only row in its category, no hreflang group)
r_iso = client.get("/explore/isolated-page")
all_ok &= case("isolated page 200", r_iso.status_code == 200)
all_ok &= case("section hidden when 0 related",
               '<section class="vela-related-queries"' not in r_iso.text)

# ---- Category listing (5) ----
rc = client.get("/explore/category/contraindications")
all_ok &= case("category listing 200", rc.status_code == 200, f"status={rc.status_code}")
chtml = rc.text
all_ok &= case("listing lists published rows",
               "metformin-contraindications-renal" in chtml
               and "warfarin-contraindications-pregnancy" in chtml
               and "statin-contraindications-liver" in chtml)
all_ok &= case("archived row excluded",
               "some-archived-page" not in chtml)

rc404 = client.get("/explore/category/nonexistent-category")
all_ok &= case("listing 404 when empty", rc404.status_code == 404, f"status={rc404.status_code}")

rc400 = client.get("/explore/category/INVALID_UPPERCASE")
all_ok &= case("listing 400 invalid slug", rc400.status_code == 400, f"status={rc400.status_code}")

# ---- PostHog script presence (3) ----
all_ok &= case("script: explore_page_visited", "explore_page_visited" in html)
all_ok &= case("script: explore_to_query_clicked", "explore_to_query_clicked" in html)
all_ok &= case("script: explore_related_clicked", "explore_related_clicked" in html)

out_dir = pathlib.Path("artifacts")
out_dir.mkdir(exist_ok=True)
(out_dir / "explore_phase_d_page.html").write_text(html, encoding="utf-8")
(out_dir / "explore_phase_d_category.html").write_text(chtml, encoding="utf-8")

print("=" * 50)
print(f"Saved artifacts: {out_dir.resolve()}")
print("PASS" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
