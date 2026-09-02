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
