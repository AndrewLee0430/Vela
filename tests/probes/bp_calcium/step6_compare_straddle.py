"""SEGMENT 1b — apply the PRE-REGISTERED rule to the N=8 straddle arms (offline).

Rule (verbatim, baton §3b, written 2026-09-30 03:15 UTC before any run):
  PASS iff treatment_total(40) >= control_total(40) - 2 AND no single query drops by more than 2 runs vs control.
  FAIL otherwise -> the revert stands, record, STOP.

Also separates edit-vs-drift on each query from the captured rewrite strings: for every run, the set of distinct
rewrite strings (K=1 call + k=3 union) is recorded; per query the arms' string sets are compared, and a per-run
"safety section in FINAL" is joined to whether that run's rewrites contained a thiazide/supplement/class term.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "step6_straddle_compare8.json"
NEW_CLAUSE_TERMS = re.compile(r"supplement|thiazide|class|mechanism|hypercalc", re.I)


def load(arm):
    return json.load(open(HERE / f"step6_straddle_{arm}.json", encoding="utf-8"))


def main():
    c, t = load("control8"), load("treatment8")
    n = c["n_per_query"]
    assert n == t["n_per_query"] == 8, (c["n_per_query"], t["n_per_query"])
    cr = {x["id"]: x for x in c["rows"]}
    tr = {x["id"]: x for x in t["rows"]}
    rows, c_tot, t_tot, worst = [], 0, 0, 0
    for qid in cr:
        cc, tt = cr[qid]["runs_with_safety_in_final"], tr[qid]["runs_with_safety_in_final"]
        c_tot += cc
        t_tot += tt
        drop = cc - tt
        worst = max(worst, drop)
        c_strings = sorted({s for r in cr[qid]["runs"] for call in r["rewrite_calls"] for s in call})
        t_strings = sorted({s for r in tr[qid]["runs"] for call in r["rewrite_calls"] for s in call})
        rows.append({"id": qid, "query": cr[qid]["query"], "control": f"{cc}/{n}", "treatment": f"{tt}/{n}",
                     "drop": drop,
                     "control_unusable": sum(1 for r in cr[qid]["runs"] if r["status"] in ("no_results", "error")),
                     "treatment_unusable": sum(1 for r in tr[qid]["runs"] if r["status"] in ("no_results", "error")),
                     "control_distinct_rewrites": c_strings, "treatment_distinct_rewrites": t_strings,
                     "rewrites_only_in_treatment": sorted(set(t_strings) - set(c_strings)),
                     "rewrites_only_in_control": sorted(set(c_strings) - set(t_strings)),
                     "treatment_runs_with_new_clause_term": sum(
                         1 for r in tr[qid]["runs"] if any(NEW_CLAUSE_TERMS.search(s) for call in r["rewrite_calls"] for s in call)),
                     "control_runs_with_new_clause_term": sum(
                         1 for r in cr[qid]["runs"] if any(NEW_CLAUSE_TERMS.search(s) for call in r["rewrite_calls"] for s in call))})
    cond_total = t_tot >= c_tot - 2
    cond_query = worst <= 2
    verdict = "PASS" if (cond_total and cond_query) else "FAIL"
    res = {"rule": "PASS iff treatment_total(40) >= control_total(40) - 2 AND no single query drops by more than 2 runs vs control",
           "control": {"started_utc": c.get("started_utc"), "finished_utc": c.get("finished_utc"), "total": f"{c_tot}/40"},
           "treatment": {"started_utc": t.get("started_utc"), "finished_utc": t.get("finished_utc"), "total": f"{t_tot}/40"},
           "condition_total": {"treatment_total": t_tot, "control_total_minus_2": c_tot - 2, "met": cond_total},
           "condition_per_query": {"worst_drop": worst, "met": cond_query},
           "verdict": verdict, "rows": rows}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{'query':<20} {'control':>8} {'treatment':>10} {'drop':>5}  unusable(c/t)")
    for r in rows:
        print(f"{r['id']:<20} {r['control']:>8} {r['treatment']:>10} {r['drop']:>5}  {r['control_unusable']}/{r['treatment_unusable']}")
    print(f"{'TOTAL':<20} {c_tot:>5}/40 {t_tot:>7}/40")
    print(f"condition_total: {t_tot} >= {c_tot - 2} -> {cond_total} | condition_per_query: worst drop {worst} <= 2 -> {cond_query}")
    print("VERDICT:", verdict)
    for r in rows:
        if r["rewrites_only_in_treatment"] or r["rewrites_only_in_control"]:
            print(f"  [{r['id']}] rewrites only in treatment: {r['rewrites_only_in_treatment']}")
            print(f"  [{r['id']}] rewrites only in control:   {r['rewrites_only_in_control']}")


if __name__ == "__main__":
    main()
