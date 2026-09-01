# -*- coding: utf-8 -*-
"""Verify history fidelity — ALL THREE write sites persist the FULL structure.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
Until 2026-09-01 (HISTORY car segment 1) the three Verify ChatHistory INSERT
sites stored ONLY the roll-up summary line, so the per-interaction detail
(drug pairs, severities, per-finding attribution) was destroyed at write time —
unbackfillable, which is why /history could only ever show
"Found 1 interaction(s): 1 Major". These tests exercise each REAL endpoint path
(main / LLM-fallback / fallback-failure) against an in-memory DB and assert the
STORED answer parses as JSON carrying the exact structural fields the /history
renderer keys on: the canonical `severity` enum, the stable `attribution_kind`
enum, `summary`, `risk_level`, `verification_status`. A test asserting only
"a row was written" would pass against the old summary-string writes — these
fail against them.

Each test observes real effect end-to-end: HTTP request → handler → DB row,
with only the NETWORK edges stubbed (DailyMed/openFDA label search, the LLM
provider, and the LLM medical-intent guard — same isolation pattern as
tests/test_verify_tfda_payload.py; production guard code is NOT modified).

Also pinned: the STORED summary equals the RESPONSE summary — the JSON payload
must embed the post-mutation summary (the 2026-08-19 write-ordering rule,
carried into the payload era; see tests/test_verify_write_ordering.py).

Run: python -m pytest tests/test_verify_history_payload.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk/credits checks; the
# DATABASE_URL default keeps module init off any real DB (all reads/writes in
# these tests go through a dependency-overridden StaticPool engine below).
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


class _FakeDailyMedLabel:
    """Minimal label the handler's DailyMed tier accepts (34073-7 present)."""
    setid = "fake-setid-0000"
    generic_name = "aspirin"
    brand_name = "Aspirin"
    drug_interactions = "Aspirin interacts with warfarin."

    def to_text(self):
        return "ASPIRIN LABEL TEXT (drug interactions: warfarin)"


class _FakeCompletion:
    def __init__(self, content):
        self.content = content
        self.input_tokens = 10
        self.output_tokens = 20


class _FakeProvider:
    def __init__(self, content=None, raise_exc=False):
        self._content = content
        self._raise = raise_exc

    async def complete(self, req):
        if self._raise:
            raise RuntimeError("stubbed LLM failure")
        return _FakeCompletion(self._content)


class _FakeBinding:
    def __init__(self, provider):
        self.model = "test-model"
        self.provider = provider


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


def _post_verify(monkeypatch, *, dailymed_hits, llm_content, llm_raises=False):
    """Drive POST /api/verify through a real handler run with stubbed edges;
    return (response, stored ChatHistory rows)."""
    import api.middleware.guards as guards
    import api.server as server
    from api.models.sql_models import ChatHistory
    from fastapi.testclient import TestClient

    async def _always_medical(text):
        return True, ""

    async def _dm_search(drug, limit=1):
        return [_FakeDailyMedLabel()] if dailymed_hits else []

    async def _fda_search(drug, limit=1):
        return []

    monkeypatch.setattr(guards, "check_medical_intent", _always_medical)
    monkeypatch.setattr(server.dailymed_client, "search_drug_labels", _dm_search)
    monkeypatch.setattr(server.fda_client, "search_drug_labels", _fda_search)
    monkeypatch.setattr(
        server, "_get_verify",
        lambda: _FakeBinding(_FakeProvider(content=llm_content, raise_exc=llm_raises)),
    )

    engine, TestSession, get_db = _fresh_db(server)
    try:
        client = TestClient(server.app)  # no context manager → no lifespan side effects
        resp = client.post("/api/verify", json={
            "drugs": ["aspirin", "warfarin"],
            "patient_context": None,
            "response_language": "en",
        })
        with TestSession() as db:
            rows = db.query(ChatHistory).filter(
                ChatHistory.session_type == "verify").all()
            # Detach the values we assert on before the session closes.
            stored = [(r.user_id, r.question, r.answer) for r in rows]
        return resp, stored
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_main_site_stores_full_structure(monkeypatch):
    """(site 1, `answer=_verify_history_payload(... summary=summary ...)`):
    DailyMed-grounded analysis → stored JSON carries interactions with canonical
    severity + attribution_kind, the post-mutation summary, and status ok."""
    main_analysis = json.dumps({
        "interactions": [{
            "drugs": ["aspirin", "warfarin"],
            "severity": "Major",
            "severity_label": "嚴重",
            "description": "Increased bleeding risk.",
            "recommendation": "Avoid combination; monitor INR.",
        }],
        "risk_level": "Major",
        "risk_level_label": "重大",
    })
    resp, stored = _post_verify(monkeypatch, dailymed_hits=True, llm_content=main_analysis)
    assert resp.status_code == 200, resp.text
    assert len(stored) == 1, f"expected exactly one verify history row, got {len(stored)}"
    _, question, answer = stored[0]
    assert question == "Drugs: aspirin, warfarin"

    parsed = json.loads(answer)  # raises → summary-string regression
    assert parsed["verification_status"] == "ok"
    assert parsed["risk_level"] == "Major"
    assert parsed["drugs_analyzed"] == ["aspirin", "warfarin"]
    assert parsed["disclaimer"], "localized disclaimer must be embedded"
    inter = parsed["interactions"]
    assert len(inter) == 1
    assert inter[0]["severity"] == "Major", "canonical enum — the /history badge key"
    assert inter[0]["drug_pair"] == ["aspirin", "warfarin"]
    assert inter[0]["attribution_kind"] == "dailymed_grounded", \
        "stable Option-C key — the /history attribution-caption key"
    assert inter[0]["description"] == "Increased bleeding risk."
    # Stored summary == response summary (post-mutation; write-ordering rule).
    assert parsed["summary"] == resp.json()["summary"]
    assert "1 Major" in parsed["summary"]


def test_llm_fallback_site_stores_full_structure(monkeypatch):
    """(site 2, `summary=fb_summary`): no labels anywhere → LLM-knowledge
    fallback → stored JSON carries no_label-attributed interactions and the
    ⚠️-prefixed fallback summary."""
    fb_analysis = json.dumps({
        "interactions": [{
            "drugs": ["aspirin", "warfarin"],
            "severity": "Moderate",
            "description": "Possible additive bleeding effect.",
            "recommendation": "Monitor.",
        }],
        "summary": "Possible interaction.",
        "risk_level": "Moderate",
    })
    resp, stored = _post_verify(monkeypatch, dailymed_hits=False, llm_content=fb_analysis)
    assert resp.status_code == 200, resp.text
    assert len(stored) == 1
    parsed = json.loads(stored[0][2])
    assert parsed["verification_status"] == "ok"
    assert parsed["summary"].startswith("⚠️ No FDA label data found."), \
        "the fb_summary prefix must survive inside the JSON"
    inter = parsed["interactions"]
    assert len(inter) == 1
    assert inter[0]["severity"] == "Moderate"
    assert inter[0]["attribution_kind"] == "no_label", \
        "fallback path must keep its honest no-label attribution"
    assert parsed["summary"] == resp.json()["summary"]


def test_fallback_failure_site_stores_failed_status(monkeypatch):
    """(site 3, `summary=fallback_summary`): no labels AND the fallback LLM
    fails → stored JSON must say failed_no_data with zero interactions, so
    /history can never render a total failure as a clean result."""
    resp, stored = _post_verify(monkeypatch, dailymed_hits=False,
                                llm_content=None, llm_raises=True)
    assert resp.status_code == 200, resp.text
    assert len(stored) == 1
    parsed = json.loads(stored[0][2])
    assert parsed["verification_status"] == "failed_no_data"
    assert parsed["interactions"] == []
    assert parsed["risk_level"] == "Unknown"
    assert parsed["summary"] == "No FDA label data found. Please use specific drug names."
    assert resp.json()["verification_status"] == "failed_no_data"
