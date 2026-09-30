"""STEP 2 (E0 / H1) — the rewrite arm only, no retrieval.

5 x _rewrite_query + 1 x _dailymed_union_queries(k=3) on the exact hero-chip query.
(The union call makes 3 more rewrite LLM calls internally; they are reported as the
union set, not counted as extra samples.)

Classification is by STRING MARKERS over the emitted rewrite (Rule 21 — the markers,
and what they deliberately do not match, are listed in the result).
"""
import asyncio
import json
import re
from collections import Counter
from pathlib import Path

from _harness import QUERY, assert_dev_db, production_retriever

import sys  # noqa: E402
# Default reproduces the probe-1 artifact; the Segment-1 TREATMENT run passes a prefix
# (`step6_treatment`) so the committed control is never overwritten.
_PREFIX = sys.argv[1] if len(sys.argv) > 1 else "step2"
OUT = Path(__file__).resolve().parent / f"{_PREFIX}_rewrite.json"

MARKERS = {
    "ccb": re.compile(r"calcium channel|\bCCB\b|amlodipine|nifedipine|diltiazem|verapamil|felodipine|dihydropyridine", re.I),
    "supplement": re.compile(r"supplement|calcium carbonate|calcium citrate|dietary calcium|calcium intake|vitamin d", re.I),
    "thiazide": re.compile(r"thiazide|hydrochlorothiazide|chlorthalidone|indapamide|diuretic", re.I),
    "hypercalcemia": re.compile(r"hypercalc", re.I),
}
REJECTED = ("bare 'calcium' (ambiguous by construction — it is the query's own word)",
            "'antihypertensive' (names the class of BP meds, not either reading)")


def classify(s):
    return {k: bool(p.search(s)) for k, p in MARKERS.items()}


async def main():
    dev = assert_dev_db()
    r, cfg = production_retriever()
    samples = []
    for i in range(5):
        qs = await r._rewrite_query(QUERY)
        samples.append({"run": i + 1, "rewrites": qs, "class": [classify(q) for q in qs]})
        print(f"[{i+1}]", qs, flush=True)
    union = await r._dailymed_union_queries(QUERY, k=3)
    print("[union]", union, flush=True)

    per_run = Counter()
    for s in samples:
        for k in MARKERS:
            if any(c[k] for c in s["class"]):
                per_run[k] += 1
    strings = [q for s in samples for q in s["rewrites"]]
    per_string = Counter(k for q in strings for k, v in classify(q).items() if v)
    res = {"query": QUERY, "db_branch": dev, "model": r._model,
           "config": {k: v for k, v in cfg.items() if k != "provenance"},
           "samples": samples, "union_k3": union,
           "union_class": [classify(q) for q in union],
           "distribution_runs_with_marker_of_5": dict(per_run),
           "distribution_strings_with_marker": {"n_strings": len(strings), **dict(per_string)},
           "markers": {k: p.pattern for k, p in MARKERS.items()},
           "markers_rejected": REJECTED}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("distribution_runs_with_marker_of_5",
                                          "distribution_strings_with_marker")}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
