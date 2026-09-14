# -*- coding: utf-8 -*-
"""Retention sweep — it must EXECUTE, and it must be OBSERVABLE.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if these fail):
`pages/privacy.tsx:46` tells every signed-in user, unconditionally, that
"Data is automatically deleted after 6 months." `_cleanup_pass()` is the only
thing in this repo that implements that sentence. Two properties have to hold
for the sentence to be true AND checkable:

  1. IT RUNS. Until 2026-09-14 the loop did `await asyncio.sleep(86400)` at the
     TOP of its body, so a process had to live a full day before deleting
     anything — and the timer is per-process, in-memory, with no persisted
     marker, so every deploy reset it to zero. Prod shipped 8+ releases between
     2026-08-11 and 2026-09-14. If the sleep drifts back above the pass, the
     promise silently stops being executed and nothing anywhere says so.

  2. IT SAYS SO. The success log used to be guarded by
     `if deleted_audit or deleted_chat:`, so a pass that deleted zero rows was
     COMPLETELY SILENT. That is why the six months before 2026-09-14 are
     unverifiable: "never ran" and "ran and deleted nothing" are
     indistinguishable from both the database and the logs. THAT
     INDISTINGUISHABILITY IS THE DEFECT. The unconditional log line is the
     deliverable — it is what makes a future "has retention run?" answerable.

Measured prod context (founder-run read-only SELECT, 2026-09-14, transcribed —
Claude Code did not run it and did not view the screenshots): the oldest
`chat_history` row is 2026-03-19 02:43:19 UTC, so the first row becomes eligible
at 2026-09-15 02:43:19 UTC. Zero rows were over 180 days at measurement time,
which is exactly why a zero-delete pass must still be loud: before that instant
a correct pass and a dead task look identical.

T3 is the positive control. Without it, T1 and T2 would both pass against a
`_cleanup_pass` that opens a session, logs, and deletes nothing.

Harness: in-memory SQLite via StaticPool, the same isolation pattern as
tests/test_history_delete.py. `api.server.SessionLocal` is monkeypatched, so the
real function under test runs against the real schema.

Run: uv run python -m pytest tests/test_cleanup_retention.py -q
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk; the DATABASE_URL
# default keeps module init off any real DB. Every DB touch in this file goes
# through the monkeypatched StaticPool sessionmaker below — no engine created at
# import time is ever used.
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import api.server as server  # noqa: E402
from api.models.sql_models import AuditLog, ChatHistory  # noqa: E402


# ── harness ──────────────────────────────────────────────────────────────────

def _fresh_sessionmaker():
    """In-memory DB shared across connections (StaticPool), real schema.

    ⚠️ DIALECT CAVEAT: this is SQLite, not the Postgres/Neon that runs in prod.
    What is being asserted here is the CUTOFF COMPARISON and the COMMIT, both of
    which SQLAlchemy emits identically for both dialects (`WHERE col < :cutoff`
    + `COMMIT`). What SQLite does NOT exercise is Postgres-specific DELETE
    behaviour (row-level locks, cascade timing, statement timeouts). Those are
    out of scope for this segment and are noted rather than silently assumed.
    """
    from api.database.sql_db import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _seed(TestSession, audit_rows, chat_rows):
    """Insert (id, timestamp) AuditLogs and (created_at,) ChatHistorys."""
    with TestSession() as db:
        for aid, ts in audit_rows:
            db.add(AuditLog(id=aid, user_id="u", action="research",
                            query_content="q", ip_address="0.0.0.0", timestamp=ts))
        for created in chat_rows:
            db.add(ChatHistory(user_id="u", session_type="research",
                               question="q", answer="a", created_at=created))
        db.commit()


class _RecordingSession:
    """Minimal Session stand-in that records commit/close and returns fixed
    delete counts, so T2 and T4 assert on the pass's own behaviour rather than
    on the database's."""

    def __init__(self, delete_counts):
        self._counts = list(delete_counts)
        self.commits = 0
        self.closes = 0
        self.deletes = 0

    def query(self, _model):
        return self

    def filter(self, *_a, **_kw):
        return self

    def delete(self, *_a, **_kw):
        self.deletes += 1
        return self._counts.pop(0) if self._counts else 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        self.closes += 1


# ── T1 — ORDER (behavioural, not a source grep) ──────────────────────────────

def test_t1_pass_runs_before_the_first_sleep(monkeypatch):
    """BUSINESS RULE: the retention promise must be EXECUTED on every boot.

    If `asyncio.sleep` runs before `_cleanup_pass`, a process must survive a
    full 24 h before it deletes anything — and since the timer is per-process
    with no persisted marker, a deploy cadence under 24 h means the promise in
    `pages/privacy.tsx:46` is never executed at all, silently. This asserts the
    ORDER of real calls in the real loop, not the presence of a source line.
    """
    events = []

    monkeypatch.setattr(server, "_cleanup_pass", lambda: events.append("pass"))

    async def _fake_sleep(_secs):
        events.append("sleep")
        raise asyncio.CancelledError  # terminate the infinite loop

    monkeypatch.setattr(server.asyncio, "sleep", _fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(server._cleanup_old_records())

    assert events, "the loop neither ran a pass nor slept"
    assert events[0] == "pass", (
        "the first thing the loop did was %r — a pass must run BEFORE the first "
        "sleep, or a process that lives under 24 h never deletes anything" % events[0]
    )
    assert events[:2] == ["pass", "sleep"]


# ── T2 — the log fires on a ZERO-delete pass ─────────────────────────────────

def test_t2_log_emitted_on_zero_delete_pass(monkeypatch, caplog):
    """BUSINESS RULE: "retention ran" must be ANSWERABLE from the logs.

    A pass that deletes zero rows is CORRECT behaviour before 2026-09-15
    02:43 UTC (no row is 180 days old yet). If it logs nothing, a correct pass
    and a task that never started are indistinguishable — which is precisely
    why the six months before 2026-09-14 cannot be audited. The line must also
    carry the CUTOFF it used, so a wrong cutoff is visible without a redeploy.
    """
    rec = _RecordingSession([0, 0])
    monkeypatch.setattr(server, "SessionLocal", lambda: rec)

    with caplog.at_level(logging.INFO, logger="vela"):
        server._cleanup_pass()

    lines = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    cleanup = [m for m in lines if "cleanup" in m.lower()]
    assert cleanup, (
        "a zero-delete pass emitted no INFO line; logs: %r" % lines
    )
    msg = cleanup[0]
    assert "0" in msg, "the line must carry both counts, got %r" % msg
    # The cutoff must appear as a real timestamp, not a bare "180 days" phrase.
    assert str(datetime.utcnow().year) in msg, (
        "the line must carry the CUTOFF TIMESTAMP it used, got %r" % msg
    )


# ── T3 — POSITIVE CONTROL: the pass actually deletes, on the boundary ────────

def test_t3_deletes_across_the_180_day_boundary_for_both_tables(monkeypatch, caplog):
    """BUSINESS RULE: the promise is DELETION, not logging.

    Without this, T1 and T2 both pass against a `_cleanup_pass` that opens a
    session, logs, and does no work. Rows are placed either side of the 180-day
    line for BOTH tables the sweep owns; old must go, new must stay.
    """
    TestSession = _fresh_sessionmaker()
    now = datetime.utcnow()
    old = now - timedelta(days=181)
    new = now - timedelta(days=179)

    _seed(
        TestSession,
        audit_rows=[("aud_old", old), ("aud_new", new)],
        chat_rows=[old, new],
    )
    monkeypatch.setattr(server, "SessionLocal", TestSession)

    with caplog.at_level(logging.INFO, logger="vela"):
        server._cleanup_pass()

    # Read back through a FRESH session — this is also what proves the commit
    # landed, since an uncommitted delete would roll back on close.
    with TestSession() as db:
        audit_ids = {r.id for r in db.query(AuditLog).all()}
        chat_dates = [r.created_at for r in db.query(ChatHistory).all()]

    assert "aud_old" not in audit_ids, "the 181-day-old audit log survived the sweep"
    assert "aud_new" in audit_ids, "the 179-day-old audit log was deleted too early"
    assert len(chat_dates) == 1, "expected exactly the 179-day chat row to remain"
    assert chat_dates[0] > old, "the wrong chat_history row survived"


# ── T4 — no commit-less delete ───────────────────────────────────────────────

def test_t4_pass_commits_and_closes(monkeypatch):
    """BUSINESS RULE: an uncommitted DELETE deletes nothing.

    `Session.close()` rolls back an open transaction, so a pass that deletes
    but never commits logs plausible non-zero counts and leaves every row in
    place — the worst shape available, because the log would then ASSERT that
    retention happened when it did not.
    """
    rec = _RecordingSession([3, 7])
    monkeypatch.setattr(server, "SessionLocal", lambda: rec)

    server._cleanup_pass()

    assert rec.deletes == 2, "expected exactly two bulk deletes (audit + chat)"
    assert rec.commits == 1, "the pass must commit, or the deletes are discarded"
    assert rec.closes == 1, "the session must be closed (Rule 19 carry-across)"


# ── carry-across: an exception must not kill the loop ────────────────────────

def test_t5_pass_exception_does_not_kill_the_loop(monkeypatch, caplog):
    """BUSINESS RULE (Rule 19 carry-across): one bad night must not end retention.

    The try/except sits INSIDE the `while True:` body at `9b24c19`, so a failed
    pass is logged and the loop retries the next day. If the extraction moved it
    around the loop, a single transient DB error would silently end retention
    for the life of the process — strictly worse than the defect being fixed.
    """
    calls = []

    def _boom():
        calls.append("pass")
        raise RuntimeError("db exploded")

    monkeypatch.setattr(server, "_cleanup_pass", _boom)

    sleeps = []

    async def _fake_sleep(_secs):
        sleeps.append(1)
        if len(sleeps) >= 2:
            raise asyncio.CancelledError
        return None

    monkeypatch.setattr(server.asyncio, "sleep", _fake_sleep)

    with caplog.at_level(logging.ERROR, logger="vela"):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(server._cleanup_old_records())

    assert len(calls) == 2, (
        "the loop stopped after a failing pass — one exception must not end "
        "retention for the process lifetime; got %d pass(es)" % len(calls)
    )
    assert any("cleanup" in r.getMessage().lower() for r in caplog.records), (
        "a failed pass must be logged at ERROR"
    )
