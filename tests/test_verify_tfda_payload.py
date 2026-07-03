# -*- coding: utf-8 -*-
"""Verify payload shape — ADR 007 T2a structured transparency fields (v194).

Business rule pinned (CLAUDE.md Rule 17): the deterministic TFDA brand→ingredient
resolution and the ambiguous-brand DEFER must reach the client as STRUCTURED fields
(`tfda_groundings` / `verification_status` / `deferred_brands`), because the frontend
deliberately never renders `summary` prose (enum-authority design). If these tests
fail, either (a) the grounding-transparency note silently disappears from the Verify
UI again (the v191 T2a gap), or (b) a REFUSED verification renders as a clean
"No interactions found" result (the safety gap fixed in v194).

Three cases per the acceptance spec:
  (i)   resolvable brand  → tfda_groundings carries the correct INN + 許可證字號
  (ii)  ambiguous brand   → verification_status="deferred_ambiguous_brand",
                            deferred_brands names it, interactions=[] (real endpoint)
  (iii) no-TFDA-match     → fields absent/None; response otherwise unchanged

All three use the deterministic lookup path — no LLM/FDA network calls (the defer
branch returns before either; cases i/iii pin the exact production helper + schema).
The only patch is guards.check_medical_intent (an LLM guard upstream of the branch
under test) — production guard code is NOT modified (Rule 1: no fail-open changes).

Run: python tests/test_verify_tfda_payload.py   (or via pytest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk/credits; an in-memory
# sqlite guarantees no dev/prod DB is touched (defer-path audit writes are
# _safe_db_write fail-soft, so missing tables are fine).
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from api.services.tfda_lookup import resolve_brand  # noqa: E402

# Deterministic fixtures (pinned id=37 snapshot, verified 2026-07-03):
RESOLVABLE = "冠脂妥"      # → ROSUVASTATIN CALCIUM (single ingredient, 3 licenses)
AMBIGUOUS = "太田胃散"     # → multiple distinct TFDA products → must DEFER
MISS_EN = "warfarin"       # English INN → status="miss", untouched


def test_resolvable_brand_yields_grounding_with_inn_and_license():
    """(i) The T2a mapping reaches the payload with INN + 許可證字號 intact."""
    from api.server import _build_tfda_groundings
    drugs = [RESOLVABLE, MISS_EN]
    groundings = _build_tfda_groundings(drugs, [resolve_brand(d) for d in drugs])
    assert groundings is not None and len(groundings) == 1, "exactly the resolved brand"
    g = groundings[0]
    assert g.query == RESOLVABLE, "query must stay verbatim (display/audit contract)"
    assert g.ingredients == ["ROSUVASTATIN CALCIUM"], f"wrong INN: {g.ingredients}"
    assert g.is_combo is False
    assert g.licenses and all("號" in lic for lic in g.licenses), \
        f"許可證字號 citation anchors missing: {g.licenses}"


def test_no_tfda_match_yields_fields_absent_and_shape_backward_compatible():
    """(iii) English INNs → no groundings; omitted fields serialize as None."""
    from api.server import _build_tfda_groundings
    from api.models.schemas import VerifyResponse
    drugs = [MISS_EN, "aspirin"]
    assert _build_tfda_groundings(drugs, [resolve_brand(d) for d in drugs]) is None

    # Backward compat: a response built WITHOUT the new fields (old call sites,
    # cached responses) must expose them as None — old clients see no change.
    r = VerifyResponse(drugs_analyzed=drugs, interactions=[], summary="s",
                       risk_level="Low", query_time_ms=1)
    d = r.model_dump() if hasattr(r, "model_dump") else r.dict()
    assert d["tfda_groundings"] is None
    assert d["verification_status"] is None
    assert d["deferred_brands"] is None


def test_ambiguous_brand_defers_with_structured_status_via_endpoint():
    """(ii) Real /api/verify: ambiguous brand → structured DEFER, no interactions.

    The defer branch returns BEFORE any FDA/LLM call, so this exercises the true
    HTTP payload with zero network. check_medical_intent (LLM guard upstream of
    the branch under test) is stubbed pass-through for isolation and restored.
    """
    import api.middleware.guards as guards
    from fastapi.testclient import TestClient
    import api.server as server

    async def _always_medical(text):
        return True, ""

    orig = guards.check_medical_intent
    guards.check_medical_intent = _always_medical
    try:
        client = TestClient(server.app)  # no context manager → no lifespan side effects
        resp = client.post("/api/verify", json={
            "drugs": [AMBIGUOUS, MISS_EN],
            "patient_context": None,
            "response_language": "zh-TW",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["verification_status"] == "deferred_ambiguous_brand"
        assert data["deferred_brands"] == [AMBIGUOUS]
        assert data["interactions"] == [], "a DEFER must never carry interactions"
        assert data["risk_level"] == "Unknown"
        assert data["tfda_groundings"] is None, "warfarin is a miss → no groundings"
        assert data["drugs_analyzed"] == [AMBIGUOUS, MISS_EN], "inputs stay verbatim"
    finally:
        guards.check_medical_intent = orig


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
