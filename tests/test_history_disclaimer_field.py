# -*- coding: utf-8 -*-
"""GET /api/history fills `disclaimer` on Explain rows at READ time
(HISTORY RENDER LEFTOVERS car, segment 2 — TECH_DEBT [HONESTY][P3] "Explain
LEGACY rows … redisplay a stored medical explanation WITHOUT any disclaimer";
transport ruled (ii) 2026-09-11, R1/R2 2026-09-22).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails): a legacy
Explain row (pre-§2.7, non-JSON `answer`) redisplayed on /history is a medical
explanation with no stored caption; the ONE source of the 16 Explain
disclaimer strings is Python (api/i18n/explain_strings.py), so the caption
must arrive on the wire from the server, keyed by the request's language
(R1: `?locale=` explicit → Accept-Language → "en", through the EXISTING
_resolve_response_language so the BCP-47 normalizer travels — Rule 19).
R2: every explain row carries it (the frontend ignores it on JSON rows);
every other row carries null. The read path writes NOTHING.

Every assertion here is on res.json() — the WIRE BODY — never on the model
object, because `response_model=list[ChatHistoryEntry]` silently DROPS any
attribute absent from the model (baton §3b): a handler that sets the field
but a model that lacks it returns 200 with a well-formed body and no
disclaimer. Only a round-trip catches that.

Harness: same isolation pattern as tests/test_history_delete.py — TEST_MODE +
in-memory StaticPool DB via dependency_overrides; requests go through the real
FastAPI handlers.

Run: python -m pytest tests/test_history_disclaimer_field.py -q
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk; the DATABASE_URL
# default keeps module init off any real DB.
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from api.i18n.explain_strings import EXPLAIN_DISCLAIMERS  # noqa: E402

LEGACY_ANSWER = "Hemoglobin 11.2 g/dL is slightly below the reference range."
JSON_ANSWER = (
    '{"items": [], "clinical_correlations": [], '
    '"disclaimer": "' + EXPLAIN_DISCLAIMERS["en"] + '"}'
)


def _fresh_db(server_module):
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


def _client_and_db(monkeypatch, owner="hist_owner"):
    import api.server as server
    from fastapi.testclient import TestClient

    monkeypatch.setenv("TEST_USER_ID", owner)
    engine, TestSession, get_db = _fresh_db(server)
    client = TestClient(server.app)  # no context manager → no lifespan tasks
    return server, client, engine, TestSession, get_db


def _cleanup(server, engine, get_db):
    server.app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def _naive_utc_now(**replace):
    return datetime.now(timezone.utc).replace(tzinfo=None, **replace)


def _seed(TestSession, rows):
    """Insert (session_type, question, answer, created_at) for hist_owner;
    return {question: id} so assertions can address rows by content."""
    from api.models.sql_models import ChatHistory

    with TestSession() as db:
        objs = [
            ChatHistory(user_id="hist_owner", session_type=s, question=q,
                        answer=a, created_at=c)
            for (s, q, a, c) in rows
        ]
        db.add_all(objs)
        db.commit()
        return {o.question: o.id for o in objs}


def _seed_three(TestSession):
    """One LEGACY explain row (non-JSON answer), one JSON-shaped explain row,
    one research row — all inside the free 7-day window."""
    recent = _naive_utc_now(microsecond=0) - timedelta(hours=2)
    return _seed(TestSession, [
        ("explain", "legacy report", LEGACY_ANSWER, recent),
        ("explain", "json report", JSON_ANSWER, recent - timedelta(minutes=1)),
        ("research", "warfarin question", "## Summary — x\n\ntext", recent - timedelta(minutes=2)),
    ])


def _by_question(body):
    return {item["question"]: item for item in body}


# ---------------------------------------------------------------------------
# (i) explicit ?locale= → both explain rows filled, research row null
# ---------------------------------------------------------------------------
def test_explicit_locale_fills_explain_rows_and_nulls_others(monkeypatch):
    """R2 on the wire: BOTH explain rows (legacy AND JSON-shaped) carry the
    zh-TW string — the server does not parse `answer` to decide — and the
    research row carries null. A handler that fills every row, or that fills
    only the legacy one by sniffing JSON, fails here."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        resp = client.get("/api/history?locale=zh-TW")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) == 3, body
        rows = _by_question(body)
        for item in body:
            assert "disclaimer" in item, f"key missing on the wire: {sorted(item)}"
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["zh-TW"]
        assert rows["json report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["zh-TW"]
        assert rows["warfarin question"]["disclaimer"] is None
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# (ii) lowercase explicit locale → normalized (R5 / Rule 19: the normalizer
#      travelled with the data, not just the fallback)
# ---------------------------------------------------------------------------
def test_lowercase_explicit_locale_is_normalized_not_english(monkeypatch):
    """`?locale=zh-tw` must yield the zh-TW caption, NOT the en fallback.
    get_disclaimer has no normalizer of its own (explain_strings.py:92-94 is a
    bare .get); the /explain surface is only safe because its value passed
    through _resolve_response_language first (server.py:156). A read path that
    calls get_disclaimer(locale) directly returns English on a Chinese page —
    silently, because the en fallback makes the wrong answer look right."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        resp = client.get("/api/history?locale=zh-tw")
        assert resp.status_code == 200, resp.text
        rows = _by_question(resp.json())
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["zh-TW"]
        assert rows["legacy report"]["disclaimer"] != EXPLAIN_DISCLAIMERS["en"]
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# (iii) no ?locale= + Accept-Language → the header path (also normalized:
#       _resolve_response_language runs _normalize on the first tag, :164)
# ---------------------------------------------------------------------------
def test_accept_language_header_selects_caption_when_no_query(monkeypatch):
    """Without `?locale=`, the FIRST Accept-Language tag decides. Asserted with
    a lowercase, q-weighted header so the derived behaviour (first tag,
    normalized at server.py:163-164) is what is pinned, not a guess."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        resp = client.get("/api/history", headers={"Accept-Language": "ja,en;q=0.8"})
        assert resp.status_code == 200, resp.text
        rows = _by_question(resp.json())
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["ja"]

        resp2 = client.get("/api/history", headers={"Accept-Language": "zh-tw;q=0.9,en"})
        rows2 = _by_question(resp2.json())
        assert rows2["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["zh-TW"], \
            "the Accept-Language path must normalize exactly as the explicit path does (server.py:164)"
    finally:
        _cleanup(server, engine, get_db)


def test_explicit_locale_wins_over_accept_language(monkeypatch):
    """R1 order: explicit value FIRST, header second (server.py:156-166)."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        resp = client.get("/api/history?locale=ko", headers={"Accept-Language": "ja"})
        rows = _by_question(resp.json())
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["ko"]
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# (iv) neither → "en"
# ---------------------------------------------------------------------------
def test_no_locale_and_no_header_falls_back_to_english(monkeypatch):
    """The chain's terminal default (server.py:168) and get_disclaimer's own
    en fallback agree: no language input of any kind → the English caption,
    never null on an explain row."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        # TestClient sends no Accept-Language unless asked; make that explicit.
        resp = client.get("/api/history", headers={"Accept-Language": ""})
        assert resp.status_code == 200, resp.text
        rows = _by_question(resp.json())
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["en"]
        assert rows["json report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["en"]
    finally:
        _cleanup(server, engine, get_db)


def test_unknown_locale_falls_back_to_english_not_null(monkeypatch):
    """An unmapped explicit value (`?locale=xx-QQ`) must still caption the
    explain row in English — the Rule 19 mitigation that must not be lost on
    the second surface. Null here would redisplay the medical text uncaptioned."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        _seed_three(TestSession)
        resp = client.get("/api/history?locale=xx-QQ", headers={"Accept-Language": ""})
        rows = _by_question(resp.json())
        assert rows["legacy report"]["disclaimer"] == EXPLAIN_DISCLAIMERS["en"]
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# (v) the free 7-day cutoff is untouched by the read-time fill
# ---------------------------------------------------------------------------
def test_free_user_cutoff_unchanged_by_disclaimer_fill(monkeypatch):
    """A free user (no user_usage row → not pro) still sees ONLY the last 7
    days: an 8-day-old explain row is absent from the listing. The fill must
    ride on the existing query, not replace it."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        ids = _seed_three(TestSession)
        old = _naive_utc_now(microsecond=0) - timedelta(days=8)
        ids.update(_seed(TestSession, [("explain", "stale report", LEGACY_ANSWER, old)]))
        resp = client.get("/api/history?locale=en")
        assert resp.status_code == 200, resp.text
        questions = {item["question"] for item in resp.json()}
        assert "stale report" not in questions, "8-day-old row leaked past the free 7-day cutoff"
        assert questions == {"legacy report", "json report", "warfarin question"}
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# (vi) the read path issues NO UPDATE / INSERT / DELETE — read back + statement capture
# ---------------------------------------------------------------------------
def test_read_path_writes_nothing(monkeypatch):
    """Rule 7 does not apply here because nothing is written — and this test
    is how that claim is verified rather than asserted: every SQL statement
    the GET issues is captured at the engine and none may be a write; the
    stored `answer` read back afterwards is byte-identical to what was seeded."""
    from api.models.sql_models import ChatHistory

    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        ids = _seed_three(TestSession)
        statements = []

        @event.listens_for(engine, "before_cursor_execute")
        def _capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement.strip().upper())

        try:
            resp = client.get("/api/history?locale=zh-TW")
        finally:
            event.remove(engine, "before_cursor_execute", _capture)
        assert resp.status_code == 200, resp.text
        assert statements, "no SQL captured — the listener did not observe the request"
        writes = [s for s in statements if s.startswith(("UPDATE", "INSERT", "DELETE"))]
        assert writes == [], f"the read path issued writes: {writes}"

        with TestSession() as db:
            legacy = db.get(ChatHistory, ids["legacy report"])
            assert legacy.answer == LEGACY_ANSWER, "stored answer changed on a GET"
            assert not hasattr(ChatHistory, "disclaimer"), \
                "disclaimer must not become a column — it is a read-time field"
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# NEGATIVE CONTROL — proves the assertion can fail: a verify row gets null
# ---------------------------------------------------------------------------
def test_negative_control_verify_row_carries_null(monkeypatch):
    """Same wire shape, non-explain row → null. A fill applied to every row
    (the simplest wrong implementation) makes this fail."""
    server, client, engine, TestSession, get_db = _client_and_db(monkeypatch)
    try:
        recent = _naive_utc_now(microsecond=0) - timedelta(hours=1)
        _seed(TestSession, [("verify", "Drugs: a, b", "summary", recent)])
        resp = client.get("/api/history?locale=zh-TW")
        assert resp.status_code == 200, resp.text
        [item] = resp.json()
        assert "disclaimer" in item
        assert item["disclaimer"] is None
    finally:
        _cleanup(server, engine, get_db)


# ---------------------------------------------------------------------------
# /openapi.json — founder ruling #5 (2026-09-02): no internals leak
# ---------------------------------------------------------------------------
def test_openapi_disclaimer_field_has_no_description_and_no_internal_names():
    """The new field must publish as a nullable string with NO description,
    and the ChatHistoryEntry schema block must name no internal symbol."""
    import json
    import api.server as server
    from fastapi.testclient import TestClient

    resp = TestClient(server.app).get("/openapi.json")
    assert resp.status_code == 200, resp.text
    schema = resp.json()["components"]["schemas"]["ChatHistoryEntry"]
    prop = schema["properties"]["disclaimer"]
    assert "description" not in prop, prop
    assert {"type": "string"} in prop["anyOf"] and {"type": "null"} in prop["anyOf"], prop
    text = json.dumps(schema)
    for banned in ("get_disclaimer", "explain_strings", "_resolve_response_language",
                   "EXPLAIN_DISCLAIMERS", "ChatHistory(", "sql_models"):
        assert banned not in text, f"internal name leaked to /openapi.json: {banned}"
