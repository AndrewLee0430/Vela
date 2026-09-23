# -*- coding: utf-8 -*-
"""`_check_phi` fails CLOSED — a PHI-detector exception blocks the request.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
CLAUDE.md Rule 1 — "Never change guard chain to fail-open; if a guard throws,
block the request" — was RULED on 2026-09-23 (E4, founder ruling R3) to cover
route-level gates, not only the run_guards chain. Until then `_check_phi`
logged a detector exception and returned None, so a broken detector silently
let EVERY request through unchecked: the gate that keeps identifiers out of
the LLM provider and out of storage failed open. After the fix the exception
goes to the log only (Rule 5: never into the body) and the request gets the
run_guards fail-closed precedent (api/middleware/guards.py:180-184 /
:271-275): the same fixed string, in the same status + body shape the Verify
route uses for a run_guards block (api/server.py, `JSONResponse(status_code=400,
content={"detail": guard_error})`) — no new user-visible string (Rule 16).

BLAST RADIUS — `_check_phi` has exactly 4 callers, all `if phi_resp: return
phi_resp`, so a detector failure blocks all four uniformly:
  /api/feedback (audit_middleware) · /api/research · /api/verify · /api/explain.
(i) pins the helper, (ii) Verify end-to-end with no rows written, (iii)
Research end-to-end, (iv) the control: an un-patched detector still answers 200.

Run: python -m pytest tests/test_check_phi_fail_closed.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_verify_history_payload import (  # noqa: E402  (sets TEST_MODE env first)
    SEED_USER_CREDITS,
    _fresh_db,
    _run_verify,
)

PRECEDENT = "Security check temporarily unavailable. Please try again."

_ANALYSIS = json.dumps({
    "interactions": [{
        "drugs": ["aspirin", "warfarin"],
        "severity": "Major",
        "description": "Increased bleeding risk.",
        "recommendation": "Avoid.",
    }],
    "risk_level": "Major",
})


def _break_detector(monkeypatch):
    from api.middleware.phi_handler import PHIDetector

    def _boom(*args, **kwargs):
        raise RuntimeError("stubbed detector failure SECRET-INTERNAL-DETAIL")

    monkeypatch.setattr(PHIDetector, "detect", _boom)


def _assert_blocked(resp):
    assert resp.status_code == 400, resp.text
    assert resp.json() == {"detail": PRECEDENT}
    assert "SECRET-INTERNAL-DETAIL" not in resp.text, "exception text leaked (Rule 5)"


def test_unit_detector_exception_returns_block(monkeypatch):
    """(i) the helper itself returns a response, not None."""
    import api.server as server
    from starlette.requests import Request

    _break_detector(monkeypatch)
    req = Request({"type": "http", "method": "POST", "path": "/x", "headers": [],
                   "client": ("testclient", 0)})
    resp = server._check_phi("aspirin warfarin", "/api/verify", req)
    assert resp is not None, "detector exception fell OPEN (returned None)"
    assert resp.status_code == 400
    assert json.loads(resp.body) == {"detail": PRECEDENT}


def test_verify_blocks_on_detector_exception_no_rows_no_charge(monkeypatch):
    """(ii) POST /api/verify with a raising detector → blocked, nothing written or charged."""
    _break_detector(monkeypatch)
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_ANALYSIS,
                    seed_credits=SEED_USER_CREDITS)
    _assert_blocked(r["resp"])
    assert r["stored"] == []
    assert r["audit_actions"] == []
    assert r["credits"] == SEED_USER_CREDITS


def test_research_blocks_on_detector_exception(monkeypatch):
    """(iii) POST /api/research → blocked before the stream opens. run_guards is
    stubbed to fail fast so that, pre-fix, the request finishes as a 200 SSE
    stream instead of reaching the network."""
    import api.server as server
    from fastapi.testclient import TestClient

    async def _guard_block(*args, **kwargs):
        return False, "stub guard block"

    monkeypatch.setattr(server, "run_guards", _guard_block)
    _break_detector(monkeypatch)
    engine, _TestSession, get_db = _fresh_db(server)
    try:
        resp = TestClient(server.app).post("/api/research", json={
            "question": "aspirin and warfarin", "response_language": "en"})
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()
    _assert_blocked(resp)


def test_control_detector_working_verify_unchanged(monkeypatch):
    """(iv) CONTROL — detector NOT patched: today's 200, row written, charged 1."""
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_ANALYSIS,
                    seed_credits=SEED_USER_CREDITS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert len(r["stored"]) == 1
    assert r["credits"] == SEED_USER_CREDITS + 1
