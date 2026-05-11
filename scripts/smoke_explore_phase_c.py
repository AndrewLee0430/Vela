"""PRD § 4.6 PHASE C — explore_cli smoke driver.

Tests the markdown → DB sync workflow + status transition commands
against a temp SQLite DB. No backend uvicorn required.

The `from-vela` command is NOT smoke-tested here (requires LLM API key
+ vector store + full pipeline — manual editorial test only).
"""

from __future__ import annotations

import os
import subprocess
import sys
import pathlib
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Set TEST_MODE + temp SQLite BEFORE any api.* imports
os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./tmp_explore_phase_c.db"
os.environ["SHARE_CREATED_BY_SALT"] = "smoke_salt_v1"
os.environ["VELA_PUBLIC_BASE_URL"] = "https://vela.an-tho.com"
os.environ["PYTHONIOENCODING"] = "utf-8"

db_path = pathlib.Path("tmp_explore_phase_c.db")
if db_path.exists():
    db_path.unlink()

# Ensure explore_page table exists in the temp SQLite
from api.database.sql_db import Base, engine, SessionLocal  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402

Base.metadata.create_all(bind=engine)

# Test fixture dir — use a sub-dir so we don't pollute real content/explore/
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_ROOT / "content" / "explore"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

FIXTURE_SLUG = "test-cli-fixture"
FIXTURE_LOCALE = "en"
FIXTURE_PATH = FIXTURE_DIR / f"{FIXTURE_SLUG}.{FIXTURE_LOCALE}.md"


def cleanup():
    """Remove fixture files + DB rows. Sweep any _test- or test- prefixed
    leftovers from prior failed runs."""
    for p in FIXTURE_DIR.glob("test-cli-fixture*.md"):
        p.unlink()
    for p in FIXTURE_DIR.glob("_test-cli-fixture*.md"):
        p.unlink()
    for p in FIXTURE_DIR.glob("wrong-name*.md"):
        p.unlink()
    for p in FIXTURE_DIR.glob("_BAD-SLUG*.md"):
        p.unlink()
    with SessionLocal() as db:
        rows = db.query(ExplorePage).filter(
            ExplorePage.slug.in_([FIXTURE_SLUG, "_test-cli-fixture", "_BAD-SLUG"])
        ).all()
        for r in rows:
            db.delete(r)
        db.commit()


def write_fixture(status: str = "draft", body_suffix: str = ""):
    """Write a valid fixture markdown file."""
    content = (
        f"---\n"
        f"slug: {FIXTURE_SLUG}\n"
        f"locale: {FIXTURE_LOCALE}\n"
        f"query: \"Test query for CLI smoke?\"\n"
        f"meta_title: \"Test CLI Fixture | Vela\"\n"
        f"meta_description: \"Fixture for explore_cli smoke testing.\"\n"
        f"category: dose-adjustment\n"
        f"hreflang_group: test-cli-fixture\n"
        f"status: {status}\n"
        f"citations:\n"
        f"  - source_type: pubmed\n"
        f"    title: \"Test citation\"\n"
        f"    url: \"https://pubmed.ncbi.nlm.nih.gov/test\"\n"
        f"    credibility: peer-reviewed\n"
        f"---\n\n"
        f"## Overview \U0001F7E2 — English\n"
        f"Fixture body for CLI smoke test.{body_suffix}\n"
    )
    FIXTURE_PATH.write_text(content, encoding="utf-8")


def run_cli(*args: str) -> tuple[int, str, str]:
    """Run scripts/explore_cli.py with the temp DB env. Returns (rc, stdout, stderr).

    Explicit encoding='utf-8' on subprocess avoids Windows CP950 decode
    failures on '→' / emoji / CJK characters in the CLI output.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "explore_cli.py"), *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def case(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────

cleanup()
all_ok = True

# 1. Empty sync (no fixture present)
rc, out, err = run_cli("sync")
all_ok &= case("sync on empty dir", rc == 0 and ("No markdown files" in out or "Inserted=0" in out),
               f"rc={rc}")

# 2. Insert: create fixture, sync, row appears
write_fixture(status="draft")
rc, out, err = run_cli("sync")
all_ok &= case("sync INSERT (rc=0)", rc == 0, f"rc={rc} err={err[:200]}")
all_ok &= case("sync INSERT (output)", "INSERT" in out and FIXTURE_SLUG in out)

with SessionLocal() as db:
    row = db.query(ExplorePage).filter_by(slug=FIXTURE_SLUG, locale=FIXTURE_LOCALE).first()
    all_ok &= case("INSERT row in DB", row is not None)
    if row:
        all_ok &= case("INSERT status=draft", row.status == "draft", f"status={row.status}")
        all_ok &= case("INSERT no published_at", row.published_at is None)
        all_ok &= case("INSERT citations count", len(row.citations or []) == 1,
                       f"len={len(row.citations or [])}")

# 3. Idempotent re-sync: no change
rc, out, err = run_cli("sync")
all_ok &= case("sync Unchanged=1", "Unchanged=1" in out, f"out={out[:200]}")
all_ok &= case("sync no UPDATE on re-run", "UPDATE" not in out)

# 4. Body change → UPDATE
write_fixture(status="draft", body_suffix=" (modified)")
rc, out, err = run_cli("sync")
all_ok &= case("sync UPDATE after body change", "UPDATE" in out)

# 5. Status change → published, published_at set
write_fixture(status="published", body_suffix=" (modified)")
rc, out, err = run_cli("sync")
all_ok &= case("sync UPDATE to published", "UPDATE" in out and "published" in out)

with SessionLocal() as db:
    row = db.query(ExplorePage).filter_by(slug=FIXTURE_SLUG, locale=FIXTURE_LOCALE).first()
    all_ok &= case("published status persisted", row.status == "published")
    all_ok &= case("published_at set", row.published_at is not None)

# 6. list command shows fixture
rc, out, err = run_cli("list")
all_ok &= case("list shows fixture", FIXTURE_SLUG in out and "published" in out)

# 7. unpublish → draft
rc, out, err = run_cli("unpublish", FIXTURE_SLUG, "--locale", FIXTURE_LOCALE)
all_ok &= case("unpublish rc=0", rc == 0)
all_ok &= case("unpublish: published → draft", "published" in out and "draft" in out)

with SessionLocal() as db:
    row = db.query(ExplorePage).filter_by(slug=FIXTURE_SLUG, locale=FIXTURE_LOCALE).first()
    all_ok &= case("status now draft", row.status == "draft")

# 8. archive
rc, out, err = run_cli("archive", FIXTURE_SLUG, "--locale", FIXTURE_LOCALE)
all_ok &= case("archive rc=0", rc == 0)
all_ok &= case("archive: draft → archived", "draft" in out and "archived" in out)

with SessionLocal() as db:
    row = db.query(ExplorePage).filter_by(slug=FIXTURE_SLUG, locale=FIXTURE_LOCALE).first()
    all_ok &= case("status now archived", row.status == "archived")

# 9. Missing required field → error
FIXTURE_PATH.write_text(
    f"---\n"
    f"slug: {FIXTURE_SLUG}\n"
    f"locale: {FIXTURE_LOCALE}\n"
    f"query: \"Missing meta_title and meta_description\"\n"
    f"status: draft\n"
    f"---\n\nBody.\n",
    encoding="utf-8",
)
rc, out, err = run_cli("sync")
all_ok &= case("sync errors on missing field (rc=1)", rc == 1, f"rc={rc}")
all_ok &= case("sync ERROR mentions missing field",
               "ERROR" in err and "meta_title" in err)

# 10. Invalid slug pattern (uppercase) → error
FIXTURE_BAD_NAME = FIXTURE_DIR / "_BAD-SLUG.en.md"
FIXTURE_BAD_NAME.write_text(
    f"---\n"
    f"slug: _BAD-SLUG\n"
    f"locale: en\n"
    f"query: \"test\"\n"
    f"meta_title: \"x\"\n"
    f"meta_description: \"x\"\n"
    f"status: draft\n"
    f"---\n\nBody.\n",
    encoding="utf-8",
)
rc, out, err = run_cli("sync")
all_ok &= case("sync errors on invalid slug (uppercase)", rc == 1)
all_ok &= case("sync ERROR mentions invalid slug",
               "invalid slug" in err.lower() or "must match" in err.lower())
FIXTURE_BAD_NAME.unlink()

# 11. Filename mismatch → error (filename doesn't match frontmatter slug)
FIXTURE_MISMATCH = FIXTURE_DIR / "wrong-name.en.md"
FIXTURE_MISMATCH.write_text(
    f"---\n"
    f"slug: {FIXTURE_SLUG}\n"
    f"locale: en\n"
    f"query: \"test\"\n"
    f"meta_title: \"x\"\n"
    f"meta_description: \"x\"\n"
    f"status: draft\n"
    f"---\n\nBody.\n",
    encoding="utf-8",
)
rc, out, err = run_cli("sync")
all_ok &= case("sync errors on filename mismatch", rc == 1)
all_ok &= case("sync ERROR mentions filename mismatch",
               "filename" in err.lower() or "doesn't match" in err.lower())
FIXTURE_MISMATCH.unlink()

# Cleanup
cleanup()

print("=" * 50)
print("PASS" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
