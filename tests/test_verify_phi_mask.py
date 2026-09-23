# -*- coding: utf-8 -*-
"""Verify storage mask — the six raw Verify write sites pass through sanitize_for_log.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
Research and Explain mask their stored question / query_content with
`PHIDetector.sanitize_for_log` (api/server.py Research :979/:1015, Explain
:1762/:1768 at 2805f8c). Until the phi-boundary car (E2, founder ruling R1
2026-09-23) Verify wrote the user's drug list RAW at six sites:
ChatHistory.question (fallback-success, fallback-failure, main) and
AuditLog.query_content (defer-ambiguous, fallback, main). The input gate
(`_check_phi` → `PHIDetector.detect`) deliberately EXCLUDES the two broad
MEDICAL_RECORD_PATTERNS (api/middleware/phi_handler.py:147-154 — too broad to
block on), so a record-number-shaped token passes the gate and reaches storage;
the mask is the only layer that catches it. If these tests fail, a
record-number-shaped identifier typed into Verify is persisted verbatim in
chat_history / audit_logs while the same token typed into Research is masked.

Method: the REAL endpoint through the shared `_run_verify` harness
(tests/test_verify_history_payload.py — reused by import, not copied). Two
seams are added here without editing the harness:
  * the request body — the harness posts a fixed body; `_client_with_body`
    swaps `fastapi.testclient.TestClient` (which the harness imports at call
    time) for a subclass that overlays this test's `drugs`;
  * AuditLog.query_content — the harness returns only AuditLog actions, so a
    pass-through spy on `server._safe_db_write` records each written object's
    column values at the moment of the write (the real helper still runs, and
    ChatHistory.question is ALSO read back from the DB by the harness).

Run: python -m pytest tests/test_verify_phi_mask.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tests.test_verify_history_payload import _run_verify  # noqa: E402  (sets TEST_MODE env first)

# Record-number-shaped: matches MEDICAL_RECORD_PATTERNS[0] `\b[A-Z]{2,3}\d{6,10}\b`
# (mask-only), and NO detect() pattern — asserted as a precondition below.
MASK_ONLY_TOKEN = "AB1234567"

_MAIN_ANALYSIS = json.dumps({
    "interactions": [{
        "drugs": [MASK_ONLY_TOKEN, "warfarin"],
        "severity": "Moderate",
        "description": "Stub interaction.",
        "recommendation": "Monitor.",
    }],
    "risk_level": "Moderate",
})


def _client_with_body(monkeypatch, **overlay):
    """Make the harness's TestClient post `overlay` merged over its fixed body."""
    import fastapi.testclient as ftc

    base = ftc.TestClient

    class _OverlayClient(base):
        def post(self, url, *args, json=None, **kwargs):
            if url == "/api/verify" and json is not None:
                json = {**json, **overlay}
            return super().post(url, *args, json=json, **kwargs)

    monkeypatch.setattr(ftc, "TestClient", _OverlayClient)


def _spy_writes(monkeypatch):
    """Pass-through spy on server._safe_db_write; returns the capture list of
    (table_name, {column: value}) for every object handed to the helper."""
    import api.server as server

    real = server._safe_db_write
    captured = []

    def _spy(db, *objs, **kwargs):
        for o in objs:
            cols = {c.name: getattr(o, c.name, None) for c in o.__table__.columns}
            captured.append((o.__tablename__, cols))
        return real(db, *objs, **kwargs)

    monkeypatch.setattr(server, "_safe_db_write", _spy)
    return captured


def _assert_masked(value, where):
    assert value is not None, f"{where}: nothing written"
    assert MASK_ONLY_TOKEN not in value, f"{where} stored the raw token: {value!r}"
    assert "***" in value, f"{where} carries no mask marker: {value!r}"


def test_precondition_token_passes_gate_but_is_masked():
    """If detect() flagged the token, the gate would block and the storage
    tests below would test nothing — fail loud (Rule 18)."""
    from api.middleware.phi_handler import PHIDetector
    assert PHIDetector.detect(MASK_ONLY_TOKEN) is None, \
        "test setup wrong: token is gate-blocked, so it never reaches storage"
    assert PHIDetector.sanitize_for_log(MASK_ONLY_TOKEN) == "***"


def test_unit_mask_reaches_inside_list_repr():
    """Sites :1295 / :1429 / :1651 interpolate the Python list repr
    (`['AB1234567']`) — the quotes/brackets must not shield the token from the
    `\\b` word-boundary patterns."""
    from api.middleware.phi_handler import PHIDetector
    for text in (f"Checked: {[MASK_ONLY_TOKEN]}",
                 f"LLM fallback: {[MASK_ONLY_TOKEN, 'warfarin']}",
                 f"Ambiguous TFDA brand(s): {[MASK_ONLY_TOKEN]}"):
        _assert_masked(PHIDetector.sanitize_for_log(text), "unit")


def test_main_path_masks_question_and_audit(monkeypatch):
    """MAIN path (labels found): ChatHistory.question + AuditLog 'verify'."""
    _client_with_body(monkeypatch, drugs=[MASK_ONLY_TOKEN, "warfarin"])
    writes = _spy_writes(monkeypatch)
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_MAIN_ANALYSIS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert len(r["stored"]) == 1
    _assert_masked(r["stored"][0][1], "ChatHistory.question (main, DB read-back)")
    audits = [c for t, c in writes if t == "audit_logs"]
    assert [a["action"] for a in audits] == ["verify"]
    _assert_masked(audits[0]["query_content"], "AuditLog.query_content (main)")


def test_fallback_path_masks_question_and_audit(monkeypatch):
    """No-label FALLBACK success: ChatHistory.question + AuditLog 'verify_fallback'."""
    fb = json.dumps({"interactions": [], "summary": "stub", "risk_level": "Unknown"})
    _client_with_body(monkeypatch, drugs=[MASK_ONLY_TOKEN, "warfarin"])
    writes = _spy_writes(monkeypatch)
    r = _run_verify(monkeypatch, dailymed_hits=False, llm_content=fb)
    assert r["resp"].status_code == 200, r["resp"].text
    assert len(r["stored"]) == 1
    _assert_masked(r["stored"][0][1], "ChatHistory.question (fallback, DB read-back)")
    audits = [c for t, c in writes if t == "audit_logs"]
    assert [a["action"] for a in audits] == ["verify_fallback"]
    _assert_masked(audits[0]["query_content"], "AuditLog.query_content (fallback)")


def test_fallback_failure_path_masks_question(monkeypatch):
    """No-label FALLBACK failure (LLM raises): the second ChatHistory site."""
    _client_with_body(monkeypatch, drugs=[MASK_ONLY_TOKEN, "warfarin"])
    r = _run_verify(monkeypatch, dailymed_hits=False, llm_content=None, llm_raises=True)
    assert r["resp"].status_code == 200, r["resp"].text
    assert len(r["stored"]) == 1
    _assert_masked(r["stored"][0][1], "ChatHistory.question (fallback failure, DB read-back)")


def test_defer_ambiguous_path_masks_audit(monkeypatch):
    """TFDA AMBIGUOUS defer: AuditLog 'verify_defer_ambiguous', no history row."""
    import api.services.tfda_lookup as tfda
    real_resolve = tfda.resolve_brand

    def _resolve(name):
        if name == MASK_ONLY_TOKEN:
            return tfda.Resolution(status="ambiguous", query=name,
                                   candidate_products=["P1", "P2"])
        return real_resolve(name)

    monkeypatch.setattr(tfda, "resolve_brand", _resolve)
    _client_with_body(monkeypatch, drugs=[MASK_ONLY_TOKEN, "warfarin"])
    writes = _spy_writes(monkeypatch)
    r = _run_verify(monkeypatch, dailymed_hits=True, llm_content=_MAIN_ANALYSIS)
    assert r["resp"].status_code == 200, r["resp"].text
    assert r["resp"].json()["risk_level"] == "Unknown", "defer path not reached"
    audits = [c for t, c in writes if t == "audit_logs"]
    assert [a["action"] for a in audits] == ["verify_defer_ambiguous"]
    _assert_masked(audits[0]["query_content"], "AuditLog.query_content (defer)")


# CONTROL (not duplicated here): a PHI-free drug list is stored byte-identical —
# tests/test_verify_history_payload.py:233 asserts
# `question == "Drugs: aspirin, warfarin"` on the main path and stays GREEN.
