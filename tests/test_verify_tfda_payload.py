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


# ── v196: failed_no_data enum (TECH_DEBT honesty/display — total failure ≠ ok) ──
# Pins the third verification_status value. Path: no FDA labels found AND the
# fallback LLM call fails. The LLM is stubbed to RAISE (never produces medical
# output); fda_client is stubbed to return no labels; deduct_credits is stubbed
# no-op only because the test DB has no tables (the fail paths — sites 2 and 3,
# the latter since HISTORY HONESTY segment 2b — never deduct; the ok path does).


class _StubProvider:
    def __init__(self, behavior):
        self._behavior = behavior

    async def complete(self, req):
        return self._behavior()


class _StubBinding:
    def __init__(self, behavior):
        self.model = "stub-model"
        self.provider = _StubProvider(behavior)


class _StubFDA:
    async def search_drug_labels(self, drug, limit=1):
        return []


class _StubDailyMedEmpty:
    """DailyMed (now the PRIMARY tier) returns nothing → forces the openFDA fallback
    tier (or, if that also misses, the no-label path). Keeps these tests network-free
    and deterministic now that Verify tries DailyMed first."""
    async def search_drug_labels(self, drug, limit=1):
        return []


def _run_verify_with_stubs(behavior):
    import api.middleware.guards as guards
    import api.server as server
    from fastapi.testclient import TestClient

    async def _always_medical(text):
        return True, ""

    async def _no_deduct(db, user_id, feature):
        return None

    orig = (guards.check_medical_intent, server._verify_binding,
            server.fda_client, server.dailymed_client, server.deduct_credits)
    guards.check_medical_intent = _always_medical
    server._verify_binding = _StubBinding(behavior)
    server.fda_client = _StubFDA()
    server.dailymed_client = _StubDailyMedEmpty()
    server.deduct_credits = _no_deduct
    try:
        client = TestClient(server.app)
        resp = client.post("/api/verify", json={
            "drugs": ["zzdrugalpha", "zzdrugbeta"],   # no FDA label, no spell-correct match
            "patient_context": None,
            "response_language": "en",
        })
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        (guards.check_medical_intent, server._verify_binding,
         server.fda_client, server.dailymed_client, server.deduct_credits) = orig


def test_fallback_fail_yields_failed_no_data():
    def _raise():
        raise RuntimeError("stub LLM failure")
    data = _run_verify_with_stubs(_raise)
    assert data["verification_status"] == "failed_no_data"
    assert data["interactions"] == [], "a failed run must never carry interactions"
    assert data["risk_level"] == "Unknown"


def test_fallback_success_yields_ok():
    class _Fake:
        content = '{"interactions": [], "summary": "No interaction data.", "risk_level": "Unknown"}'
        input_tokens = 1
        output_tokens = 1
    data = _run_verify_with_stubs(lambda: _Fake())
    assert data["verification_status"] == "ok"
    assert data["interactions"] == []
    # (deferred_ambiguous_brand is pinned by the endpoint test above — all 3 enum
    # values are now covered: ok / deferred_ambiguous_brand / failed_no_data.)


# ── v199: honest source relabel (P1 "FDA Label Analysis" fake-authority) ──────────
# The FDA label WAS consulted (main path retrieves real openFDA labels), but the
# interaction statement is the model's inference — it must NOT be labeled as if FDA
# stated it. These pin the honest wording at the schema default AND the real main-path
# emission, and prove the fallback path's already-honest label is untouched.

# Post-DailyMed (v2.4): the schema DEFAULT is source-agnostic; the openFDA-FALLBACK
# tier keeps the v199 "AI analysis of FDA label" emission (the main-path tests below
# stub DailyMed empty → they exercise the openFDA fallback).
HONEST_SCHEMA_DEFAULT = "AI analysis of drug label"
HONEST_MAIN_SOURCE = "AI analysis of FDA label"
BANNED_SOURCE_STRINGS = ("FDA Label Analysis", "FDA Label / AI Analysis")


class _FakeLabel:
    generic_name = "warfarin"
    brand_name = "Coumadin"
    source_id = "FDA:stub"
    url = "https://example/label"
    manufacturer = "StubCo"

    def to_text(self):
        return "WARFARIN label. Interactions: aspirin increases bleeding risk."


class _StubFDAWithLabel:
    async def search_drug_labels(self, drug, limit=1):
        return [_FakeLabel()]


def _run_verify_main_path(interactions_json):
    """Drive the MAIN Verify path (FDA labels present → LLM analysis over real label
    text). fda_client returns a stub label so drug_labels is non-empty; the LLM is
    stubbed to return a fixed interactions JSON so the DrugInteraction.source our code
    assigns is what we assert."""
    import api.middleware.guards as guards
    import api.server as server
    from fastapi.testclient import TestClient

    async def _always_medical(text):
        return True, ""

    async def _no_deduct(db, user_id, feature):
        return None

    class _Resp:
        def __init__(self, content):
            self.content = content
            self.input_tokens = 1
            self.output_tokens = 1

    orig = (guards.check_medical_intent, server._verify_binding,
            server.fda_client, server.dailymed_client, server.deduct_credits)
    guards.check_medical_intent = _always_medical
    server._verify_binding = _StubBinding(lambda: _Resp(interactions_json))
    server.fda_client = _StubFDAWithLabel()
    server.dailymed_client = _StubDailyMedEmpty()  # DailyMed miss → openFDA fallback tier
    server.deduct_credits = _no_deduct
    try:
        client = TestClient(server.app)
        resp = client.post("/api/verify", json={
            "drugs": ["warfarin", "aspirin"], "patient_context": None, "response_language": "en",
        })
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        (guards.check_medical_intent, server._verify_binding,
         server.fda_client, server.dailymed_client, server.deduct_credits) = orig


def test_schema_default_source_is_honest():
    from api.models.schemas import DrugInteraction
    di = DrugInteraction(drug_pair=("a", "b"), severity="Minor",
                         description="d", clinical_recommendation="r")
    assert di.source == HONEST_SCHEMA_DEFAULT
    assert di.source not in BANNED_SOURCE_STRINGS


def test_main_path_interaction_carries_honest_source():
    payload = ('{"interactions": [{"drugs": ["warfarin", "aspirin"], "severity": "Major", '
               '"description": "Increased bleeding risk.", "recommendation": "Monitor INR."}], '
               '"summary": "1 interaction", "risk_level": "Major"}')
    data = _run_verify_main_path(payload)
    assert data["interactions"], "main path should return the stubbed interaction"
    src = data["interactions"][0]["source"]
    assert src == HONEST_MAIN_SOURCE, f"expected honest source, got {src!r}"
    assert src not in BANNED_SOURCE_STRINGS, "the fake-authority wording must not return"


def test_old_fake_authority_strings_absent_from_source():
    """Anti-regression: the banned strings must not be emitted anywhere in the Verify
    source-label code path (both are inline literals — pin them by source inspection)."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("api/server.py", "api/models/schemas.py"):
        text = open(os.path.join(root, rel), encoding="utf-8").read()
        for banned in BANNED_SOURCE_STRINGS:
            assert banned not in text, f"{banned!r} still present in {rel}"


def test_fallback_no_label_source_still_honest():
    """The no-FDA-label path already labeled honestly — must stay unchanged."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    text = open(os.path.join(root, "api/server.py"), encoding="utf-8").read()
    assert "Clinical Knowledge (No FDA label available)" in text


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
