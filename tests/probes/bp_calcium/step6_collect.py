"""SEGMENT 1 — assemble step6_treatment.json from the control + treatment artifacts (offline).

Reads (all in this directory): step2_rewrite.json (control rewrites) · step6_treatment_rewrite.json ·
step3_trace.json (control trace, probe 1) · step6_treatment_trace.json · step6_golden_compare.json ·
step6_canary_{control,treatment}.json · step6_danger_{control,treatment}.json ·
step6_straddle_{control,treatment}.json · step6_spend_final.json (if present).
Every number below is DERIVED here from those files; nothing is typed in.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "step6_treatment.json"
ON = re.compile(r"thiazide|hydrochlorothiazide|chlorthalidone|indapamide|hypercalc|calcium supplement|"
                r"calcium carbonate|calcium citrate|vitamin d", re.I)
SAFETY = {"34073-7", "43685-7", "34070-3", "34066-1"}


def J(name):
    p = HERE / name
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def rewrite_stats(r):
    d = r["distribution_runs_with_marker_of_5"]
    s = r["distribution_strings_with_marker"]
    return {"runs_naming_thiazide": f"{d.get('thiazide', 0)}/5", "runs_naming_supplement": f"{d.get('supplement', 0)}/5",
            "runs_naming_hypercalcemia": f"{d.get('hypercalcemia', 0)}/5", "runs_naming_ccb": f"{d.get('ccb', 0)}/5",
            "strings_naming_thiazide": f"{s.get('thiazide', 0)}/{s['n_strings']}",
            "strings_naming_supplement": f"{s.get('supplement', 0)}/{s['n_strings']}"}


def trace_stats(t):
    runs = []
    for run in t["runs"]:
        fin = {d["source_id"] for d in run.get("filter_in", [])}
        fout = {d["source_id"] for d in run.get("filter_out", [])}
        final = {d["source_id"] for d in run["final"]}
        pool = run["pool_unique"]
        dm = [d for d in pool if d["source_type"] == "dailymed"]
        on = [d for d in pool if ON.search(d["title"])]
        runs.append({"run": run["run"], "status": run["status"], "pool": len(pool),
                     "dailymed_in_pool": [d["source_id"] for d in dm],
                     "dailymed_safety_in_final": [d["source_id"] for d in run["final"]
                                                  if d["source_type"] == "dailymed"
                                                  and d["source_id"].split("#", 1)[1].split("~")[0] in SAFETY],
                     "on_target_title_entered": len(on),
                     "on_target_title_kept_by_filter": sum(1 for d in on if d["source_id"] in fout),
                     "on_target_title_final": sum(1 for d in on if d["source_id"] in final),
                     "filter": f"{len(fin)}->{len(fout)}", "final": [f"{d['source_id']} | {d['title'][:70]}" for d in run["final"]]})
    g = t["generation_run1"]
    return {"runs": runs, "generation_run1": {"model": g["model"], "n_docs": g["n_docs"],
                                              "veto_i_regex": g["veto_i_calcium_read_as_ccb"],
                                              "veto_ii_regex": g["veto_ii_mentions_thiazide_or_hypercalcemia"]}}


def canary_stats(c):
    # shape (read from the file, not assumed): top-level `aggregate` + `queries[]` with
    # id / safety_cited (OLD criterion) / wrong_object_cited (the gate) / usable_runs / errored
    rows = {x["id"]: {k: x.get(k) for k in ("wrong_object_cited", "safety_cited", "usable_runs", "errored")}
            for x in c["queries"]}
    return {"verdict": c.get("aggregate"), "git_head": c.get("git_head"), "started": c.get("started"),
            "per_query": rows, "keys_seen": sorted(c.keys())}


def danger_stats(d):
    return {"violations": len(d.get("violations", [])),
            "rechecks": [r["query"] for r in d.get("results", []) if r.get("founder_recheck_required")],
            "timestamp": d.get("timestamp")}


def main():
    res = {
        "car": "bp_calcium Segment 1 — _rewrite_query prompt edit, ONE variable",
        "base": "0b210da04fa168a74efde0585a3d256f888fe3a1",
        "killed_partial_runs": "2026-09-29 golden treatment (18/20 done) + canary treatment (3.4/6 queries) were stopped by "
                               "Claude Code for host memory pressure; their logs are scratch only and are NOT evidence. "
                               "All treatment numbers below come from the 2026-09-30 SERIAL re-runs.",
        "bp_query": {
            "rewrites_control": rewrite_stats(J("step2_rewrite.json")),
            "rewrites_treatment": rewrite_stats(J("step6_treatment_rewrite.json")),
            "trace_control_probe1": trace_stats(J("step3_trace.json")),
            "trace_treatment": trace_stats(J("step6_treatment_trace.json")),
            "veto_i_hand_read_treatment_run1": "FALSE — the answer opens 'blood pressure (BP) medications with calcium "
                                               "supplements'; its only CCB mentions are CCBs as a BP-drug CLASS whose "
                                               "effect IV calcium chloride may blunt (from the cited label). The regex "
                                               "`calcium[- ]channel` fires on that and is too coarse for veto (i).",
            "veto_ii_hand_read_treatment_run1": "TRUE — 'Hypercalcemia Risk: For patients on drugs that increase "
                                                "hypercalcemia risk (e.g., thiazide diuretics, vitamin D, lithium) ... "
                                                "increase the frequency of serum calcium monitoring' [1]",
        },
        "golden": J("step6_golden_compare.json") and {
            k: J("step6_golden_compare.json")[k] for k in
            ("control", "treatment", "pools_identical", "pools_same_set",
             "verdict_moved_on_same_pool_set (judge variance, NOT attributable)",
             "verdict_moved_on_different_pool (attributable-by-pool, adjudicate)")},
        "canary": {"control": canary_stats(J("step6_canary_control.json")),
                   "treatment": canary_stats(J("step6_canary_treatment.json"))},
        "danger": {"control": danger_stats(J("step6_danger_control.json")),
                   "treatment": danger_stats(J("step6_danger_treatment.json"))},
        "straddle": {"control": (J("step6_straddle_control.json") or {}).get("summary"),
                     "treatment": (J("step6_straddle_treatment.json") or {}).get("summary")},
        "spend": J("step6_spend_final.json"),
    }
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("golden", "danger", "straddle")}, ensure_ascii=False, indent=1))
    print("canary:", res["canary"]["control"]["verdict"], "->", res["canary"]["treatment"]["verdict"],
          "| keys:", res["canary"]["treatment"]["keys_seen"])
    print("bp rewrites:", res["bp_query"]["rewrites_control"], "->", res["bp_query"]["rewrites_treatment"])


if __name__ == "__main__":
    main()
