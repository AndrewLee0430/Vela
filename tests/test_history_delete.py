# -*- coding: utf-8 -*-
"""Per-entry history delete + explicit GET response model (HISTORY car,
delete segment, founder rulings 2026-09-01/02).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
/privacy §4 represents to users that they can delete their chat history.
For that representation to be true the delete must be REAL — the row gone
from the DB, read back, not just a 200 — and OWNER-SCOPED: no caller may
delete, or even probe the existence of, another user's rows. Founder ruling
#4 requires absent-id and non-owned-id to be INDISTINGUISHABLE 404s (no
existence leak). And the GET listing must stop serializing user_id (recon
§7-D1 over-exposure). Every test here reads the DB back after the call:
a handler that returns 200 without deleting, deletes the wrong row, or
distinguishes "exists but not yours" from "does not exist" fails.

Harness: same isolation pattern as tests/test_verify_history_payload.py —
TEST_MODE + in-memory StaticPool DB via dependency_overrides; requests go
through the real FastAPI handlers.

Run: python -m pytest tests/test_history_delete.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk; the DATABASE_URL
# default keeps module init off any real DB (all reads/writes in these tests
# go through a dependency-overridden StaticPool engine below).
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


def _fresh_db(server_module):
    """Per-test in-memory DB shared across connections (StaticPool), with the
    real schema, wired into the app via dependency_overrides on get_db."""
    from api.database.sql_db import Base, get_db

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    server_module.app.dependency_overrides[get_db] = _override_get_db
    return engine, TestSession, get_db


def _seed(TestSession, rows):
    """Insert (user_id, session_type, question, answer) tuples; return ids in
    insertion order."""
    from api.models.sql_models import ChatHistory

    with TestSession() as db:
        objs = [
            ChatHistory(user_id=u, session_type=s, question=q, answer=a)
            for (u, s, q, a) in rows
        ]
        db.add_all(objs)
        db.commit()
        return [o.id for o in objs]


def _client_and_db(monkeypatch, owner="hist_owner"):
    import api.server as server
    from fastapi.testclient import TestClient

    # Pin the TEST_MODE identity so ownership is deterministic regardless of
    # what other test files set (get_user_id reads the env at call time).
    monkeypatch.setenv("TEST_USER_ID", owner)
    engine, TestSession, get_db = _fresh_db(server)
    client = TestClient(server.app)  # no context manager → no lifespan tasks
    return server, client, engine, TestSession, get_db


def _cleanup(server, engine, get_db):
    server.app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_owner_delete_removes_only_that_row(monkeypatch):
    """Owner deletes own row → 200, the row is GONE from the DB (read back),
    and the owner's other row survives — a handler that 200s without deleting,
    or deletes more than the one row, fails here."""
    from api.models.sql_models import ChatHistory

    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        target_id, keeper_id = _seed(TestSession, [
            ("hist_owner", "verify", "Drugs: a, b", "summary one"),
            ("hist_owner", "research", "question two", "answer two"),
        ])
        resp = client.delete(f"/api/history/{target_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "deleted", "id": target_id}

        with TestSession() as db:
            remaining = {r.id for r in db.query(ChatHistory).all()}
        assert target_id not in remaining, "row must actually be deleted"
        assert keeper_id in remaining, "only the targeted row may be deleted"
    finally:
        _cleanup(server, engine, get_db)


def test_non_owner_and_absent_id_are_identical_404s(monkeypatch):
    """Non-owned id → 404 AND the row survives (read back); absent id → 404;
    and the two 404 responses are byte-identical (founder ruling #4 — the
    endpoint must not leak whether a row exists under another user)."""
    from api.models.sql_models import ChatHistory

    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        (other_id,) = _seed(TestSession, [
            ("someone_else", "verify", "Drugs: x, y", "their summary"),
        ])
        resp_foreign = client.delete(f"/api/history/{other_id}")
        assert resp_foreign.status_code == 404, resp_foreign.text

        with TestSession() as db:
            survivor = db.query(ChatHistory).filter(
                ChatHistory.id == other_id).one_or_none()
        assert survivor is not None, "non-owner 404 must leave the row intact"
        assert survivor.answer == "their summary"

        resp_absent = client.delete("/api/history/999999")
        assert resp_absent.status_code == 404, resp_absent.text
        assert resp_absent.json() == resp_foreign.json(), \
            "absent and non-owned ids must be indistinguishable (no existence leak)"
    finally:
        _cleanup(server, engine, get_db)


def test_unauthenticated_delete_fails_exactly_like_get(monkeypatch):
    """With real auth on (TEST_MODE off), a token-less DELETE fails with the
    same status and body as a token-less GET — the delete route must not be a
    softer target than the listing it deletes from."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        monkeypatch.setattr(server, "TEST_MODE", False)  # require_auth real path
        resp_get = client.get("/api/history")
        resp_del = client.delete("/api/history/1")
        assert resp_get.status_code == 403, resp_get.text
        assert resp_del.status_code == resp_get.status_code
        assert resp_del.json() == resp_get.json()
    finally:
        _cleanup(server, engine, get_db)


def test_get_history_excludes_user_id(monkeypatch):
    """GET /api/history serializes exactly the five fields the frontend
    consumes — user_id must NOT appear (recon §7-D1: the raw-ORM response
    exposed all 6 columns). Fails against the pre-response_model handler."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed(TestSession, [
            ("hist_owner", "explain", "report text", '{"items": []}'),
        ])
        resp = client.get("/api/history")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 1, "seeded row must be listed"
        assert set(data[0].keys()) == {
            "id", "session_type", "question", "answer", "created_at"
        }, f"unexpected field set: {sorted(data[0].keys())}"
        assert "user_id" not in data[0]
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# created_at timezone honesty (HISTORY HONESTY car, segment 1, 2026-09-03 —
# TECH_DEBT [HONESTY][P2] "timestamps shown in the wrong timezone").
#
# THE BUSINESS RULE: the time a user sees next to their own record must be the
# instant the record was written. Storage is naive-UTC (sql_models.py
# `default=datetime.utcnow`, a `timestamp` column). A naive value serialized as
# "2026-09-03T03:21:37" carries no offset, and pages/history.tsx
# `new Date(...)` / MySharesTab.tsx `Date.parse(...)` parse an offset-less
# date-time string as LOCAL time — every row reads 8 h wrong in Asia/Taipei.
# The fix is at the response layer (Rule 19: once per field, not per page):
# the wire value must carry a UTC designator and parse back to the DB instant.
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone  # noqa: E402


def _naive_utc_now(**replace):
    """Naive UTC 'now' — exactly the shape the utcnow column default stores,
    without the py3.12 utcnow() deprecation warning."""
    return datetime.now(timezone.utc).replace(tzinfo=None, **replace)


def _parse_wire(wire: str) -> datetime:
    """The wire string must carry an explicit UTC designator; parse strictly."""
    assert wire.endswith("+00:00") or wire.endswith("Z"), \
        f"created_at left the API without a UTC offset: {wire!r}"
    return datetime.fromisoformat(wire.replace("Z", "+00:00"))


def test_get_history_created_at_carries_utc_offset(monkeypatch):
    """GET /api/history emits created_at WITH a UTC designator, and the wire
    value parses back to the exact instant stored (read back from the DB, which
    stays naive — the storage contract is untouched). Fails against the plain
    `datetime` field, which serializes the naive value with no offset."""
    from api.models.sql_models import ChatHistory

    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        # Recent enough to clear the free-tier 7-day window; microseconds set
        # so the round-trip proves sub-second fidelity too.
        stored = _naive_utc_now(microsecond=726010) - timedelta(hours=3)
        with TestSession() as db:
            row = ChatHistory(user_id="hist_owner", session_type="verify",
                              question="Drugs: a, b", answer="summary",
                              created_at=stored)
            db.add(row)
            db.commit()
            row_id = row.id

        resp = client.get("/api/history")
        assert resp.status_code == 200, resp.text
        [item] = resp.json()
        parsed = _parse_wire(item["created_at"])

        with TestSession() as db:
            db_value = db.get(ChatHistory, row_id).created_at
        assert db_value.tzinfo is None, "storage must stay naive-UTC (not this car)"
        assert parsed == db_value.replace(tzinfo=timezone.utc), \
            f"wire {item['created_at']!r} is not the stored instant {db_value!r} (UTC)"
    finally:
        _cleanup(server, engine, get_db)


def test_history_entry_naive_created_at_serializes_as_utc():
    """Unit twin of the endpoint test, pinning the exact wire string: the
    BEFORE shape was "2026-09-03T03:21:37" (no offset); AFTER is
    "2026-09-03T03:21:37Z" — the serializer returns an AWARE datetime and
    Pydantic 2.8 writes UTC as `Z` (88ddde5 emitted "+00:00" from a str
    serializer; the fixup restored `format: date-time` and the designator
    changed with it — both are RFC 3339 UTC)."""
    import api.server as server

    out = server.ChatHistoryEntry(
        id=1, created_at=datetime(2026, 9, 3, 3, 21, 37)).model_dump(mode="json")
    assert out["created_at"] == "2026-09-03T03:21:37Z"


def test_history_entry_aware_created_at_is_not_shifted():
    """Pass-through guard for the fix's design: an ALREADY-aware value (what a
    future timestamptz column returns) keeps its own offset and instant. A
    serializer that stamps UTC unconditionally would relabel 11:21+08:00 as
    11:21+00:00 — a silent 8 h double-shift. Passes before the fix (pydantic
    already emits aware offsets) and must keep passing after it."""
    import api.server as server

    taipei = timezone(timedelta(hours=8))
    aware = datetime(2026, 9, 3, 11, 21, 37, tzinfo=taipei)
    out = server.ChatHistoryEntry(id=1, created_at=aware).model_dump(mode="json")
    assert out["created_at"] == "2026-09-03T11:21:37+08:00"
    assert datetime.fromisoformat(out["created_at"]) == aware


def test_share_list_created_at_carries_utc_offset(monkeypatch):
    """GET /api/share/list — same defect, second surface: MySharesTab.tsx
    relativeTime()/daysSince() Date.parse() the string, so a naive value makes
    a share created a minute ago read as ~8 h old in Taipei. No share/list
    harness existed; this is the smallest one on this file's pattern."""
    from api.models.sql_models import SharedQuery

    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        stored = _naive_utc_now(microsecond=0) - timedelta(minutes=1)
        with TestSession() as db:
            db.add(SharedQuery(
                share_id="tzprobe00001", query_text="q", answer_text="a",
                citations=[], created_by=server._hash_created_by("hist_owner"),
                created_at=stored))
            db.commit()

        resp = client.get("/api/share/list")
        assert resp.status_code == 200, resp.text
        [share] = resp.json()["shares"]
        parsed = _parse_wire(share["created_at"])
        assert parsed == stored.replace(tzinfo=timezone.utc), \
            f"wire {share['created_at']!r} is not the stored instant {stored!r} (UTC)"
    finally:
        _cleanup(server, engine, get_db)


def test_openapi_keeps_date_time_format_on_created_at():
    """The public /openapi.json must keep typing created_at as an RFC 3339
    date-time (`type: string, format: date-time`), not a bare string. The
    timezone serializer changes the VALUE (it gains a UTC offset), not the
    contract — a serializer that returns `str` silently downgrades the
    published schema to `{"type": "string"}` (seen at 88ddde5)."""
    import api.server as server
    from fastapi.testclient import TestClient

    resp = TestClient(server.app).get("/openapi.json")
    assert resp.status_code == 200, resp.text
    prop = resp.json()["components"]["schemas"]["ChatHistoryEntry"]["properties"]["created_at"]
    assert {"type": "string", "format": "date-time"} in prop["anyOf"], prop
    assert {"type": "null"} in prop["anyOf"], prop
