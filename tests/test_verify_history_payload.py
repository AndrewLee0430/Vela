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

Site numbering (aligned 2026-09-08 with the car baton §3.2 / TECH_DEBT — the
docs numbering wins; earlier revisions of this file numbered the sites 1/2/3 in
SOURCE order): site 1 = no-label fallback SUCCESS · site 2 = no-label fallback
FAILURE · site 3 = MAIN path (labels found).

HISTORY HONESTY car segment 2b (founder rulings R1–R6, 2026-09-07): site 3 with
BOTH LLM attempts failing stores `failed_analysis` (summary "", no interactions),
answers HTTP 200 with the same status, keeps its AuditLog row, and charges
NOTHING on either tier — the two `_double_failure_` tests below were RED first.

Run: python -m pytest tests/test_verify_history_payload.py -q
"""
import json
import logging
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


# TEST_MODE resolves a request with no Authorization header to this user
# (api/server.py require_auth_or_anonymous); an X-Anon-Fingerprint header makes
# the SAME handler take the L0 anonymous branch instead (segment-2 precedent:
# tests/test_research_history_payload.py).
USER_ID = os.getenv("TEST_USER_ID", "test_user")
ANON_FP = "seg2b-anon-fingerprint-0001"  # 16-128 chars, URL-safe base64 alphabet
SEED_USER_CREDITS = 5
SEED_ANON_CREDITS = 2


def _anon_id():
    """The anon_id the handler derives for TestClient (client host 'testclient',
    no X-Forwarded-For) — computed with the production helper so the seeded
    AnonymousUsage row is the one the handler touches."""
    from api.services.anonymous_identity import derive_anon_id
    return derive_anon_id("testclient", ANON_FP)


def _run_verify(monkeypatch, *, dailymed_hits, llm_content, llm_raises=False,
                anonymous=False, seed_credits=None):
    """Drive POST /api/verify through a real handler run with stubbed edges.
    Optionally seeds a usage row with a NON-ZERO credit count first (authed:
    UserUsage for USER_ID; anonymous: AnonymousUsage for the derived anon_id) so
    "unchanged" is a real reading, not a default. Returns a dict:
      resp           — the HTTP response
      stored         — [(user_id, question, answer)] verify ChatHistory rows
      audit_actions  — [AuditLog.action] rows written by the request
      credits        — credits_used_today of the seeded row after the request
                       (None when nothing was seeded / no row exists)."""
    import api.middleware.guards as guards
    import api.server as server
    from api.models.sql_models import AnonymousUsage, AuditLog, ChatHistory, UserUsage
    from api.services.anonymous_identity import today_utc
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
        if seed_credits is not None:
            with TestSession() as db:
                if anonymous:
                    db.add(AnonymousUsage(anon_id=_anon_id(),
                                          credits_used_today=seed_credits,
                                          last_reset_date=today_utc()))
                else:
                    db.add(UserUsage(clerk_user_id=USER_ID, plan_type="free",
                                     credits_used_today=seed_credits))
                db.commit()

        headers = {"X-Anon-Fingerprint": ANON_FP} if anonymous else {}
        client = TestClient(server.app)  # no context manager → no lifespan side effects
        resp = client.post("/api/verify", json={
            "drugs": ["aspirin", "warfarin"],
            "patient_context": None,
            "response_language": "en",
        }, headers=headers)
        with TestSession() as db:
            rows = db.query(ChatHistory).filter(
                ChatHistory.session_type == "verify").all()
            # Detach the values we assert on before the session closes.
            stored = [(r.user_id, r.question, r.answer) for r in rows]
            audit_actions = [a.action for a in db.query(AuditLog).all()]
            if anonymous:
                urow = db.query(AnonymousUsage).filter(
                    AnonymousUsage.anon_id == _anon_id()).first()
            else:
                urow = db.query(UserUsage).filter(
                    UserUsage.clerk_user_id == USER_ID).first()
            credits = urow.credits_used_today if urow is not None else None
        return {"resp": resp, "stored": stored, "audit_actions": audit_actions,
                "credits": credits}
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _post_verify(monkeypatch, *, dailymed_hits, llm_content, llm_raises=False):
    """Drive POST /api/verify through a real handler run with stubbed edges;
    return (response, stored ChatHistory rows). Thin wrapper kept for the three
    segment-1 tests below."""
    r = _run_verify(monkeypatch, dailymed_hits=dailymed_hits,
                    llm_content=llm_content, llm_raises=llm_raises)
    return r["resp"], r["stored"]


def test_main_site_stores_full_structure(monkeypatch):
    """(site 3 = MAIN path, `answer=_verify_history_payload(... summary=summary ...)`):
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
    """(site 1 = no-label fallback SUCCESS, `summary=fb_summary`): no labels anywhere → LLM-knowledge
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
    """(site 2 = no-label fallback FAILURE, `summary=fallback_summary`): no labels AND the fallback LLM
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


# ── HISTORY HONESTY car segment 2b — site 3 (MAIN path), BOTH LLM attempts fail ──
# Founder rulings 2026-09-07: R1 value `failed_analysis` · R2 the row IS written
# (AuditLog + ChatHistory, one _safe_db_write, honest status) · R3 NO deduct on
# either tier · R5 stored summary "" (no prefix-only residue) · R6 HTTP 200.
# Business rule (Rule 17): a run that produced NO analysis may never read as a
# clean "ok" on /verify or /history, and may never cost a credit. Before this
# segment the path wrote `ok` with summary "" AND charged 1 (TECH_DEBT
# [HONESTY][P2], surfaced by the segment-2 recon Probe B).

_MAIN_ANALYSIS_OK = json.dumps({
    "interactions": [{
        "drugs": ["aspirin", "warfarin"],
        "severity": "Major",
        "description": "Increased bleeding risk.",
        "recommendation": "Avoid combination; monitor INR.",
    }],
    "risk_level": "Major",
})


def test_main_site_llm_double_failure_stores_failed_analysis_and_no_charge(monkeypatch, caplog):
    """Site 3, authed: labels FOUND, both LLM attempts raise → response AND stored
    row say `failed_analysis`, summary "", interactions [], risk Unknown; the
    AuditLog row stays (an attempted verify IS an auditable event, R2); the
    seeded credit count is UNCHANGED (R3); the prod-verification INFO line is
    emitted (segment-2 precedent — the §8 gate row 7 greps for it)."""
    caplog.set_level(logging.INFO, logger="vela")
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=None,
                    llm_raises=True, seed_credits=SEED_USER_CREDITS)
    resp = r["resp"]
    assert resp.status_code == 200, resp.text          # R6
    body = resp.json()
    assert body["verification_status"] == "failed_analysis"   # R1
    assert body["interactions"] == []
    assert body["summary"] == ""                        # R5 (response side)
    assert len(r["stored"]) == 1, "R2: the row IS written, with the honest status"
    parsed = json.loads(r["stored"][0][2])
    assert parsed["verification_status"] == "failed_analysis"
    assert parsed["summary"] == "", "R5: no prefix-only residue may be persisted"
    assert parsed["interactions"] == []
    assert parsed["risk_level"] == "Unknown"
    assert r["audit_actions"] == ["verify"], "R2: AuditLog(action='verify') stays"
    assert r["credits"] == SEED_USER_CREDITS, "R3: no charge for a run that produced nothing"
    assert any("failed_analysis row, no charge (anon=False)" in rec.getMessage()
               for rec in caplog.records), "the INFO verification hook must be emitted"


def test_main_site_llm_double_failure_anon_no_row_no_charge(monkeypatch):
    """Rule 19 — the anon (L0) branch of site 3: the same double failure with an
    X-Anon-Fingerprint → `failed_analysis` response, NO ChatHistory row and NO
    AuditLog (anon never persists), and AnonymousUsage.credits_used_today
    UNCHANGED (R3 carried across to the second tier)."""
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=None,
                    llm_raises=True, anonymous=True, seed_credits=SEED_ANON_CREDITS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert r["resp"].json()["verification_status"] == "failed_analysis"
    assert r["stored"] == [], "anon tier never writes ChatHistory"
    assert r["audit_actions"] == [], "anon tier never writes AuditLog"
    assert r["credits"] == SEED_ANON_CREDITS, "R3 on the anon tier: no charge"


def test_control_main_site_llm_success_stores_ok_and_charges_one(monkeypatch):
    """Rule-17 POSITIVE CONTROL for the two tests above (passes before AND
    after segment 2b — it proves the harness OBSERVES charging, so an
    "unchanged" reading is real): same seeded row, LLM succeeds → `ok`,
    exactly +1 credit, AuditLog(action='verify')."""
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_MAIN_ANALYSIS_OK,
                    seed_credits=SEED_USER_CREDITS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert r["resp"].json()["verification_status"] == "ok"
    assert json.loads(r["stored"][0][2])["verification_status"] == "ok"
    assert r["audit_actions"] == ["verify"]
    assert r["credits"] == SEED_USER_CREDITS + 1, "the ok path charges exactly 1"


def test_control_anon_llm_success_charges_one_no_row(monkeypatch):
    """Rule-17 POSITIVE CONTROL, anon tier: LLM succeeds → `ok`, exactly +1 on
    AnonymousUsage, still no ChatHistory / AuditLog (anon never persists)."""
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_MAIN_ANALYSIS_OK,
                    anonymous=True, seed_credits=SEED_ANON_CREDITS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert r["resp"].json()["verification_status"] == "ok"
    assert r["stored"] == [] and r["audit_actions"] == []
    assert r["credits"] == SEED_ANON_CREDITS + 1, "the anon ok path charges exactly 1"
