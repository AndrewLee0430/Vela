"""DB-free guards for the seat measurement (tests/probes/ownership_eval/seat_measurement.py).

Rule 17 — what breaks if these fail:
1) The salt_sibling label silently becomes substring-based (the Rule-23 hazard:
   METHYLTESTOSTERONE merging into testosterone) or the FIXED suffix list
   silently grows (OMEPRAZOLE MAGNESIUM flipping without a founder ruling).
2) seat_v1.json's S0 baseline stops being anchored to result_v1.json — the
   committed evidence chain breaks (one file regenerated without the other).

No DB, no store, no network: the module under test is import-pure and the
equality test reads only the two committed JSONs.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "tests" / "probes" / "ownership_eval"


def _seat_module():
    spec = importlib.util.spec_from_file_location(
        "seat_measurement_under_test", EVAL_DIR / "seat_measurement.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_methyltestosterone_is_not_a_salt_sibling_of_testosterone():
    sm = _seat_module()
    # THE negative the founder ruling names: whole-token equality, never substring
    assert sm.is_salt_sibling("METHYLTESTOSTERONE", "TESTOSTERONE") is False
    # positive controls — the label exists for exactly these shapes
    assert sm.is_salt_sibling("TESTOSTERONE PROPIONATE", "TESTOSTERONE") is True
    assert sm.is_salt_sibling("ATROPINE SULFATE MONOHYDRATE", "ATROPINE") is True
    assert sm.is_salt_sibling("IRON DEXTRAN", "IRON") is True
    # Rule 23's canonical counter-example stays out
    assert sm.is_salt_sibling("NYSTATIN", "STATIN") is False
    # the suffix list is FIXED — MAGNESIUM is not on it; adding it is a founder ruling
    assert sm.is_salt_sibling("OMEPRAZOLE MAGNESIUM", "OMEPRAZOLE") is False
    # a doc identical to the query drug is relevant, never a sibling
    assert sm.is_salt_sibling("TESTOSTERONE", "TESTOSTERONE") is False


def test_seat_s0_baseline_equals_result_v1():
    seat = json.loads((EVAL_DIR / "seat_v1.json").read_text(encoding="utf-8"))
    v1 = json.loads((EVAL_DIR / "result_v1.json").read_text(encoding="utf-8"))
    assert seat["base"] == "result_v1.json"
    bound = seat["s0_score_drift"]["bound"]

    v1_by_qid = {q["qid"]: q for q in v1["queries"]}
    s0 = seat["variants"]["S0"]["per_query"]
    assert len(s0) == len(v1["queries"]) == 100
    for rec in s0:
        ref = v1_by_qid[rec["qid"]]
        # membership + order exact
        assert [(p["setid"], p["loinc"]) for p in rec["pool"]] == \
            [(p["setid"], p["loinc"]) for p in ref["pool"]], rec["qid"]
        # 4-label collapses onto the v1 3-label exactly
        collapsed = ["wrong_object" if p["label"] == "salt_sibling" else p["label"]
                     for p in rec["pool"]]
        assert collapsed == [p["label"] for p in ref["pool"]], rec["qid"]
        # scores within the recorded re-embedding drift bound
        for mine, theirs in zip(rec["pool"], ref["pool"]):
            assert abs(mine["score"] - theirs["score"]) <= bound, rec["qid"]
        # label-derived metrics exact (drift-immune)
        assert rec["n_pool"] == ref["n_pool"], rec["qid"]
        assert rec["has_relevant"] == ref["has_relevant"], rec["qid"]
        assert rec["first_relevant_rank"] == ref["first_relevant_rank"], rec["qid"]
        assert round(rec["rr"], 4) == round(ref["rr"], 4), rec["qid"]
        assert rec["ndcg5"] == ref["ndcg5"], rec["qid"]
        assert (rec["has_wrong_object"] or rec["has_salt_sibling"]) == \
            ref["has_wrong_object"], rec["qid"]

    sa, va = seat["variants"]["S0"]["aggregate"], v1["aggregate"]
    for k in ("owned_in_pool_rate", "mrr", "empty_pool_rate", "mean_ndcg5"):
        assert sa[k] == va[k], k
