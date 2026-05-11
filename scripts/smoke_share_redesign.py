"""PRD § 4.5 UX polish 1 — public page redesign smoke driver.

Renders /q/{share_id} via FastAPI TestClient against a temp SQLite DB.
Asserts the new design system markers are present in the HTML.
"""
from __future__ import annotations

import os
import sys
import pathlib
import json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_share_redesign.db")
os.environ.setdefault("SHARE_CREATED_BY_SALT", "smoke_salt_v1")
os.environ.setdefault("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Reset state for determinism
db_path = pathlib.Path("tmp_share_redesign.db")
if db_path.exists():
    db_path.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.server import app  # noqa: E402
from api.database.sql_db import Base, engine, SessionLocal  # noqa: E402
from api.models.sql_models import SharedQuery  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ANSWER = (
    "## Summary \U0001F7E2 — English\n"
    "Metformin is the first-line oral agent for type 2 diabetes.\n\n"
    "## Mechanism \U0001F7E1 — English\n"
    "It decreases hepatic glucose production and improves insulin sensitivity.\n\n"
    "## Risks \U0001F534 — English\n"
    "Rare lactic acidosis; contraindicated in advanced CKD.\n"
)

CITATIONS = [
    {
        "id": 1,
        "title": "Metformin in 2024: A comprehensive review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
        "source_type": "pubmed",
        "source_id": "PMID:12345678",
        "authors": "Smith J, Doe A",
        "journal": "NEJM",
        "year": "2024",
        "snippet": (
            "## Abstract\n"
            "This review covers metformin pharmacology, dosing, and contraindications "
            "across multiple populations. We summarize the most recent randomized trials "
            "and meta-analyses on long-term cardiovascular outcomes, renal safety, and "
            "comparative effectiveness against newer agents."
        ),
        "credibility": "peer-reviewed",
    },
    {
        "id": 2,
        "title": "Metformin Hydrochloride — Drug Label",
        "url": "https://accessdata.fda.gov/drugsatfda_docs/label/2024/metformin.pdf",
        "source_type": "fda",
        "source_id": "FDA:metformin",
        "authors": None,
        "journal": "FDA",
        "year": "2024",
        "snippet": "Official FDA prescribing information.",
        "credibility": "official",
    },
]

with SessionLocal() as db:
    db.add(SharedQuery(
        share_id="design01",
        query_id="q_test1",
        query_text="What is metformin used for?",
        answer_text=ANSWER,
        citations=CITATIONS,
        created_by="smoketest_user_hash",
        is_public=True,
        flagged=False,
        view_count=0,
        locale="en",
    ))
    db.add(SharedQuery(
        share_id="design02_revoked",
        query_id="q_test2",
        query_text="Sample revoked",
        answer_text="...",
        citations=[],
        created_by="smoketest_user_hash",
        is_public=False,
        flagged=False,
        view_count=0,
        locale="en",
    ))
    db.add(SharedQuery(
        share_id="design03_flagged",
        query_id="q_test3",
        query_text="Sample flagged",
        answer_text="...",
        citations=[],
        created_by="smoketest_user_hash",
        is_public=True,
        flagged=True,
        view_count=0,
        locale="en",
    ))
    db.commit()


def case(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


all_ok = True

# 1. Public render
r = client.get("/q/design01")
all_ok &= case("HTTP 200 public", r.status_code == 200, f"status={r.status_code}")
html = r.text

# Save the rendered page so the user can open in a browser
out_dir = pathlib.Path("artifacts")
out_dir.mkdir(exist_ok=True)
(out_dir / "q_design01.html").write_text(html, encoding="utf-8")

# 2. Header / OG
all_ok &= case("OG title meta", '<meta property="og:title"' in html)
all_ok &= case("noindex robots", '<meta name="robots" content="noindex, follow">' in html)
all_ok &= case("Coral logo PNG", '/coral_logo.png' in html and 'alt="Vela"' in html)
all_ok &= case("Header tagline (en)", "Ask in your language" in html)

# 3. Body gradient + design tokens
all_ok &= case("Body gradient var", '--vela-bg-1: #0a1628' in html)
all_ok &= case("Coral CTA button class", 'vela-cta-button' in html)
all_ok &= case("CTA gradient", 'linear-gradient(135deg, var(--vela-coral-dark), var(--vela-coral))' in html)

# 4. Evidence cards
_ev_marker = 'class="vela-evidence-card"'
all_ok &= case("3 evidence cards", html.count(_ev_marker) == 3,
               f"count={html.count(_ev_marker)}")
all_ok &= case("Strong border #22c55e", 'border-left-color: #22c55e' in html)
all_ok &= case("Moderate border #eab308", 'border-left-color: #eab308' in html)
all_ok &= case("Limited border #ef4444", 'border-left-color: #ef4444' in html)
all_ok &= case("Marker title rendered", '🟢 Summary' in html or '\U0001F7E2 Summary' in html)

# 5. Citations
all_ok &= case("PubMed source label color", 'color: #68d391' in html)
all_ok &= case("FDA source label color", 'color: #63b3ed' in html)
all_ok &= case("Peer reviewed pill bg", 'rgba(255,142,110,0.15)' in html)
all_ok &= case("Official pill bg", 'rgba(99,179,237,0.15)' in html)
all_ok &= case("No star SVG (dogfooding fix 2026-05-08)",
               'fill="#facc15"' not in html and 'vela-citation-stars' not in html)
all_ok &= case("Truncated abstract …", '…' in html)
all_ok &= case("Citation link with data-source",
               'data-citation-source="pubmed"' in html and 'data-citation-source="fda"' in html)
all_ok &= case("Source chip PubMed:1", 'PubMed: 1' in html)
all_ok &= case("Source chip FDA:1", 'FDA: 1' in html)

# 6. Inline ⚠️ disclaimer
all_ok &= case("Inline ⚠️ short disclaimer", '⚠️ For informational purposes' in html)

# 7. Citation tracking script
all_ok &= case("track-citation-click in script", '/api/share/track-citation-click' in html)
all_ok &= case("share_link_visited preserved", '/api/share/track-visit' in html)

# 8. Footer
all_ok &= case("Footer disclaimer", 'This content is generated by AI' in html)
all_ok &= case("Footer privacy/terms",
               '>Privacy</a>' in html and '>Terms</a>' in html)
all_ok &= case("Footer copyright", '© 2026 Vela' in html)

# 9. Not present (regressions to avoid)
all_ok &= case("No old --accent #2563eb", '#2563eb' not in html)
all_ok &= case("No old .cta-button class without vela- prefix",
               'class="cta-button"' not in html)
all_ok &= case("No old .query class", 'class="query"' not in html)

# 10. Revoked
r = client.get("/q/design02_revoked")
all_ok &= case("Revoked HTTP 200", r.status_code == 200)
all_ok &= case("Revoked uses vela-notice", 'vela-notice' in r.text)
all_ok &= case("Revoked text", 'has been revoked' in r.text)
(out_dir / "q_revoked.html").write_text(r.text, encoding="utf-8")

# 11. Flagged
r = client.get("/q/design03_flagged")
all_ok &= case("Flagged HTTP 200", r.status_code == 200)
all_ok &= case("Flagged uses vela-notice", 'vela-notice' in r.text)
all_ok &= case("Flagged text", 'violating the terms' in r.text)
(out_dir / "q_flagged.html").write_text(r.text, encoding="utf-8")

# 12. track-citation-click endpoint smoke
r = client.post("/api/share/track-citation-click", json={
    "share_id": "design01",
    "source_type": "pubmed",
    "citation_id": "1",
    "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
})
all_ok &= case("track-citation-click 204", r.status_code == 204)

print()
print("=" * 50)
print("Saved artifacts:", out_dir.resolve())
print("PASS" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
