"""SEGMENT 1 gate (b) — golden CONTROL vs TREATMENT with pool_identity adjudication (offline).

Reads the two `run_golden_tests.py --filter R` result files copied into this directory
and, per case, compares status AND the FINAL top_k pool identity (`pool_identity.pool_ids`,
captured by the runner from the SSE citations event). Rule from the build prompt: a verdict
that moves on an IDENTICAL pool is judge variance, not attributable to the edit. A verdict
that moves on a DIFFERENT pool is attributable-by-pool and is listed for adjudication.

Also re-applies the ratified floor (18 PASS / 2 WARN / 0 FAIL over R01-R20) to each arm
by importing `research_golden_floor` from the runner itself — never re-typed.
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
import sys as _sys  # noqa: E402
# usage: step6_compare_golden.py [<prefix>]   default prefix "step6" (Segment 1); Segment 1d uses "step10"
_PFX = _sys.argv[1] if len(_sys.argv) > 1 else "step6"
OUT = HERE / f"{_PFX}_golden_compare.json"

spec = importlib.util.spec_from_file_location("rgt", ROOT / "tests" / "run_golden_tests.py")
rgt = importlib.util.module_from_spec(spec)
_keep = [sys.stdout]
spec.loader.exec_module(rgt)
_keep.append(sys.stdout)
sys.stdout = _keep[0]


def load(name):
    r = json.load(open(HERE / name, encoding="utf-8"))
    return r, {x["id"]: x for x in r["results"]}


def main():
    c_raw, c = load(f"{_PFX}_golden_control.json")
    t_raw, t = load(f"{_PFX}_golden_treatment.json")
    c_code, c_reason, c_v = rgt.research_golden_floor(c_raw["results"])
    t_code, t_reason, t_v = rgt.research_golden_floor(t_raw["results"])
    rows, moved_same, moved_diff = [], [], []
    for cid in sorted(set(c) | set(t)):
        cc, tt = c.get(cid), t.get(cid)
        cp = (cc or {}).get("pool_identity", {}).get("pool_ids", [])
        tp = (tt or {}).get("pool_identity", {}).get("pool_ids", [])
        same_pool = cp == tp
        same_set = set(cp) == set(tp)
        row = {"id": cid, "control": (cc or {}).get("status"), "treatment": (tt or {}).get("status"),
               "pool_identical": same_pool, "pool_same_set_reordered": (same_set and not same_pool),
               "control_pool": cp, "treatment_pool": tp,
               "only_control": sorted(set(cp) - set(tp)), "only_treatment": sorted(set(tp) - set(cp))}
        if row["control"] != row["treatment"]:
            row["control_missing"] = (cc or {}).get("eval", {}).get("missing_concepts")
            row["treatment_missing"] = (tt or {}).get("eval", {}).get("missing_concepts")
            (moved_same if same_set else moved_diff).append(cid)
        rows.append(row)
        flag = "" if row["control"] == row["treatment"] else ("  <-- moved, SAME pool set (judge variance)" if same_set else "  <-- moved, DIFFERENT pool (adjudicate)")
        print(f"{cid} {row['control']:<4} -> {row['treatment']:<4} pool_identical={same_pool} "
              f"same_set={same_set} -ctrl={len(row['only_control'])} +treat={len(row['only_treatment'])}{flag}")
    n_ident = sum(r["pool_identical"] for r in rows)
    n_same_set = sum(set(r["control_pool"]) == set(r["treatment_pool"]) for r in rows)
    res = {"control": {"summary": c_raw["summary"], "floor_met": c_v["floor_met"], "reason": c_reason,
                       "file": c_raw["timestamp"]},
           "treatment": {"summary": t_raw["summary"], "floor_met": t_v["floor_met"], "reason": t_reason,
                         "file": t_raw["timestamp"]},
           "cases": rows, "n_cases": len(rows), "pools_identical": n_ident, "pools_same_set": n_same_set,
           "verdict_moved_on_same_pool_set (judge variance, NOT attributable)": moved_same,
           "verdict_moved_on_different_pool (attributable-by-pool, adjudicate)": moved_diff,
           "note": "pool = FINAL top_k handed to the generator (runner capture scope); PubMed is live, so a "
                   "different pool can be PubMed drift as well as the edit — the rewrite strings are not "
                   "captured by the runner, so drift vs edit is NOT separable here beyond the pool diff"}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\ncontrol   {c_raw['summary']} floor_met={c_v['floor_met']}")
    print(f"treatment {t_raw['summary']} floor_met={t_v['floor_met']}")
    print(f"pools identical {n_ident}/{len(rows)} · same set {n_same_set}/{len(rows)}")
    print("moved on same pool set:", moved_same, "| moved on different pool:", moved_diff)


if __name__ == "__main__":
    main()
