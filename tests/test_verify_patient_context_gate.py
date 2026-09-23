# -*- coding: utf-8 -*-
"""Verify PHI gate — `patient_context` is inspected, not only `drugs`.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
PRD §6.4 (docs/PRD.md:2222) promises that patient identifiers are blocked at
the request boundary and never reach storage. Until the phi-boundary car (E3,
founder ruling R2 2026-09-23) POST /api/verify fed `_check_phi` only
`" ".join(body.drugs)`; `patient_context` went to run_guards and into the LLM
prompt WITHOUT the PHI gate. A phone number typed as patient context was
therefore sent to the model provider, the request was charged, and rows were
written. After the fix the whole request is rejected with the UNCHANGED
`_phi_blocked_response` (400, type "phi_blocked") before anything is charged
or written.

Rule 19 proof (no frontend change): the blocked body is asserted to carry
exactly the keys pages/verify.tsx:235-245 reads on a 400 — `type` ==
"phi_blocked" at the top level (the branch unwraps `detail` only when it is an
object; here it is a string), plus `detail` and `suggestion` for setPhiError.

Harness: `_run_verify` from tests/test_verify_history_payload.py (reused by
import). Its `credits` is a real DB read of UserUsage.credits_used_today for
the seeded TEST_MODE user; `audit_actions` / `stored` are real DB reads.

Run: python -m pytest tests/test_verify_patient_context_gate.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_verify_history_payload import (  # noqa: E402  (sets TEST_MODE env first)
    SEED_USER_CREDITS,
    _run_verify,
)
from tests.test_verify_phi_mask import _client_with_body  # noqa: E402

# A contiguous Taiwan mobile — the first positive in tests/test_phi_taiwan_phone.py:24.
TW_PHONE = "0912345678"

_ANALYSIS = json.dumps({
    "interactions": [{
        "drugs": ["aspirin", "warfarin"],
        "severity": "Major",
        "description": "Increased bleeding risk.",
        "recommendation": "Avoid.",
    }],
    "risk_level": "Major",
})


def _post(monkeypatch, patient_context):
    _client_with_body(monkeypatch, patient_context=patient_context)
    return _run_verify(monkeypatch, dailymed_hits=True, llm_content=_ANALYSIS,
                       seed_credits=SEED_USER_CREDITS)


def test_precondition_phone_is_gate_detected():
    from api.middleware.phi_handler import PHIDetector
    assert PHIDetector.detect(TW_PHONE) is not None, \
        "test setup wrong: the phone is not a gate pattern, so no block is expected"


def test_phi_in_patient_context_is_blocked_before_charge_and_write(monkeypatch):
    r = _post(monkeypatch, f"patient phone {TW_PHONE}")
    assert r["resp"].status_code == 400, r["resp"].text
    body = r["resp"].json()
    # The exact shape pages/verify.tsx:235-245 consumes.
    assert body["type"] == "phi_blocked"
    assert isinstance(body["detail"], str) and body["detail"]
    assert isinstance(body["suggestion"], str) and body["suggestion"]
    assert r["stored"] == [], "a ChatHistory row was written for a PHI-blocked request"
    assert r["audit_actions"] == [], "an AuditLog row was written for a PHI-blocked request"
    assert r["credits"] == SEED_USER_CREDITS, "a PHI-blocked request was charged"


def test_control_clinical_context_not_blocked(monkeypatch):
    """Age + condition is clinical context, not an identifier — must still run."""
    r = _post(monkeypatch, "65歲男性，糖尿病")
    assert r["resp"].status_code == 200, r["resp"].text
    assert len(r["stored"]) == 1
    assert r["audit_actions"] == ["verify"]
    assert r["credits"] == SEED_USER_CREDITS + 1


# CONTROL 2 (not duplicated here): patient_context = None is the harness default;
# tests/test_verify_history_payload.py:233 (main path, 200, question stored)
# stays GREEN.
