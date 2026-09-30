"""SEGMENT 1 gate (e) — the K-union STRADDLE set, N=2 per query, control vs treatment.

The committed repo has NO harness for the straddle queries: `tests/results/_kunion_gate.py`
(untracked, gitignored, N=8) is the only one, so this file re-measures the ONE metric the
rewrite edit could regress — "a whitelisted DailyMed SAFETY section is in the FINAL
top_k" (Lever 1 / K-union recall) — through the production-parity retriever from
_harness.py. The 5 query strings are copied VERBATIM from _kunion_gate.py STRADDLES.

Usage: python step6_straddle.py --arm control|treatment [--n 2]   (writes step6_straddle_<arm>.json)
Budget: 5 × N retrieve() calls per arm, 0 generations.

Segment 1b (2026-09-30): `--n 8` arms `control8` / `treatment8`; every `_rewrite_query` output per run is
captured (observation-only wrapper on THIS retriever instance) so edit-vs-drift is separable.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

from _harness import assert_dev_db, production_retriever

HERE = Path(__file__).resolve().parent
STRADDLES = [
    ("warfarin_aspirin", "warfarin aspirin bleeding risk interaction"),
    ("spironolactone", "spironolactone potassium hyperkalemia contraindication"),
    ("warfarin_nsaid", "warfarin NSAID bleeding interaction"),
    ("lithium_ibuprofen", "lithium ibuprofen interaction toxicity"),
    ("r07_betablocker", "What are the contraindications for using beta-blockers?"),
]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["control", "treatment", "control8", "treatment8"])
    ap.add_argument("--n", type=int, default=2)
    args = ap.parse_args()
    N = args.n
    dev = assert_dev_db()
    from api.rag.retriever import _is_whitelisted_safety_section
    from api.server import _annotate_research_question
    r, cfg = production_retriever()
    # observation-only: record every rewrite output (K=1 call + the k=3 union calls) of the current run
    captured: list = []
    orig_rw = r._rewrite_query

    async def rw(q):
        out = await orig_rw(q)
        captured.append(list(out))
        return out
    r._rewrite_query = rw
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = []
    for label, q in STRADDLES:
        runs = []
        for i in range(N):
            captured.clear()
            t0 = time.perf_counter()
            docs, status = await r.retrieve(query=_annotate_research_question(q),
                                            max_results=cfg["max_results"],
                                            source_weight_active=cfg["source_weight_active"])
            safety = [d.source_id for d in docs if _is_whitelisted_safety_section(d)]
            runs.append({"run": i + 1, "status": status, "seconds": round(time.perf_counter() - t0, 1),
                         "final": [d.source_id for d in docs], "dm_safety_in_final": safety,
                         "rewrite_calls": [list(c) for c in captured]})
            print(f"[{label}] run {i+1} {status} safety={len(safety)} {safety}", flush=True)
        rows.append({"id": label, "query": q, "runs": runs,
                     "runs_with_safety_in_final": sum(1 for x in runs if x["dm_safety_in_final"])})
    res = {"arm": args.arm, "n_per_query": N, "db_branch": dev, "started_utc": started,
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config": {k: v for k, v in cfg.items() if k != "provenance"},
           "metric": "count of runs (of N) whose FINAL top_k contains >=1 whitelisted DailyMed safety section",
           "rows": rows,
           "summary": {x["id"]: f"{x['runs_with_safety_in_final']}/{N}" for x in rows}}
    out = HERE / f"step6_straddle_{args.arm}.json"
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(args.arm, res["summary"])


if __name__ == "__main__":
    asyncio.run(main())
