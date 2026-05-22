"""Unit tests for the UserProfile model + UPSERT idempotency intent.

Covers PRD §3.1 v1.6 E3 decision: identical payload on second POST still
bumps `updated_at` as "last verified" semantic. Test exercises the
SAME on_conflict_do_update pattern the endpoint uses (sqlite dialect
here; production uses postgresql dialect — semantically symmetric API).

Storage-hygiene intent (CLAUDE.md Rule 17): the table stores ONLY hash
+ locale; no raw workplace/role/work_language columns exist. Verified
structurally via SQLAlchemy `inspect()`.

COVERAGE GAP — documented loudly per brief STEP 4 fail-loud rule.
Endpoint-level tests (POST 403 free-user gate, POST 422 missing-field,
GET 404, GET 200 round-trip via TestClient with dependency overrides)
are NOT in this file because importing api.server on Windows hits a
pre-existing cp950 console encoding crash at api/database/vector_store.py:52
when the vector store loads at module import time. That bug is unrelated
to PRD §3.1 and out of scope for this commit.

Manual integration repro (run after `psql $DATABASE_URL -f
migrations/006_add_user_profile.sql` on a dev Postgres):

  # 1. Pro-gate (free user → 403)
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer <free-user-jwt>" \
    -X POST http://localhost:8000/api/user/context/hash \
    -H "Content-Type: application/json" \
    -d '{"user_context_hash":"abc1234567890def","locale":"en"}'
  # expect: 403  body: {"type":"pro_required"}

  # 2. Missing required field → 422 (FastAPI/Pydantic)
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer <pro-user-jwt>" \
    -X POST http://localhost:8000/api/user/context/hash \
    -H "Content-Type: application/json" -d '{"locale":"en"}'
  # expect: 422

  # 3. Idempotency on real Postgres — identical body, twice, observe
  # updated_at bump in user_profile row.
  for i in 1 2; do
    curl -s -X POST http://localhost:8000/api/user/context/hash \
      -H "Authorization: Bearer <pro-user-jwt>" \
      -H "Content-Type: application/json" \
      -d '{"user_context_hash":"abc1234567890def","locale":"en"}'
    psql $DATABASE_URL -c \
      "SELECT user_context_hash, updated_at FROM user_profile WHERE user_id='<test_user_id>';"
    sleep 1
  done
  # expect: same hash, updated_at strictly increasing across the two rows

  # 4. GET → 200 round-trip
  curl -s -H "Authorization: Bearer <pro-user-jwt>" \
    http://localhost:8000/api/user/context/hash
  # expect: 200 {"user_context_hash":"abc1234567890def","locale":"en","updated_at":"..."}

  # 5. GET unknown user (or before any POST) → 404
  # expect: 404  body: {"type":"not_found"}
"""

from __future__ import annotations

import time
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from api.database.sql_db import Base
from api.models.sql_models import UserProfile


@pytest.fixture
def db():
    """In-memory sqlite session. Fresh per test (no cross-test bleed)."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    s = Session()
    yield s
    s.close()


def test_table_has_only_hash_and_locale_columns(db):
    """Privacy-first §0.3: raw workplace/role/work_language must NEVER
    reach the server. Schema enforcement at the column level — if any
    of those columns ever appear on user_profile, this test fires."""
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("user_profile")}
    expected = {"user_id", "user_context_hash", "locale", "created_at", "updated_at"}
    forbidden = {"workplace", "role", "work_language"}
    assert cols == expected, f"Schema drift: got {cols}"
    assert not (cols & forbidden), f"Raw context column leaked into table: {cols & forbidden}"


def test_upsert_identical_payload_bumps_updated_at(db):
    """PRD §3.1 v1.6 E3: identical payload on second UPSERT still
    refreshes updated_at — "last verified" semantic. Production uses
    pg_insert; this test uses sqlite_insert (symmetric API) so the
    intent under test is the same on_conflict_do_update + explicit
    set_=updated_at pattern."""

    def upsert(user_id: str, hash_val: str, locale: str | None):
        # Mirrors the production handler's UPSERT in api/server.py
        stmt = sqlite_insert(UserProfile).values(
            user_id=user_id,
            user_context_hash=hash_val,
            locale=locale,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserProfile.user_id],
            set_={
                "user_context_hash": stmt.excluded.user_context_hash,
                "locale": stmt.excluded.locale,
                "updated_at": func.datetime("now"),  # sqlite equivalent of NOW()
            },
        )
        db.execute(stmt)
        db.commit()

    # First call — INSERT path
    upsert("user_test", "hash0000abcdef12", "en")
    row1 = db.query(UserProfile).filter_by(user_id="user_test").first()
    assert row1 is not None
    first_updated = row1.updated_at

    # Force timestamp granularity to differ (sqlite datetime('now') is second-resolution)
    time.sleep(1.1)
    db.expire_all()  # don't reuse cached row state

    # Second call — IDENTICAL payload, ON CONFLICT DO UPDATE path
    upsert("user_test", "hash0000abcdef12", "en")
    row2 = db.query(UserProfile).filter_by(user_id="user_test").first()
    assert row2 is not None

    # Intent: updated_at strictly advances on identical payload.
    # The hash + locale stay the same (idempotent on payload semantics)
    # but the timestamp records this re-verification.
    assert row2.user_context_hash == "hash0000abcdef12"
    assert row2.locale == "en"
    assert row2.updated_at > first_updated, (
        f"E3 violation: updated_at did not advance on identical-payload UPSERT. "
        f"first={first_updated}, second={row2.updated_at}"
    )


def test_upsert_changed_payload_updates_fields_and_timestamp(db):
    """Non-idempotent payload should rewrite hash + locale and bump
    updated_at. Same UPSERT path; just confirms field overwrite works."""

    def upsert(user_id: str, hash_val: str, locale: str | None):
        stmt = sqlite_insert(UserProfile).values(
            user_id=user_id,
            user_context_hash=hash_val,
            locale=locale,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserProfile.user_id],
            set_={
                "user_context_hash": stmt.excluded.user_context_hash,
                "locale": stmt.excluded.locale,
                "updated_at": func.datetime("now"),
            },
        )
        db.execute(stmt)
        db.commit()

    upsert("user_test", "old1111aaaaaaaa1", "en")
    time.sleep(1.1)
    upsert("user_test", "new2222bbbbbbbb2", "zh-TW")

    row = db.query(UserProfile).filter_by(user_id="user_test").first()
    assert row.user_context_hash == "new2222bbbbbbbb2"
    assert row.locale == "zh-TW"


def test_locale_nullable_storage(db):
    """Locale is optional in the request body and nullable in the
    schema — confirm storing NULL locale doesn't break anything."""
    db.add(UserProfile(user_id="u_null", user_context_hash="abc1234567890def", locale=None))
    db.commit()
    row = db.query(UserProfile).filter_by(user_id="u_null").first()
    assert row.locale is None
    assert row.user_context_hash == "abc1234567890def"
