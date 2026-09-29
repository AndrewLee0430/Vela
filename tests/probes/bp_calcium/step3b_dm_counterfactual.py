"""STEP 3b — DailyMed counterfactual for step-3 runs 2-5 (EMBEDDING calls only).

WHY THIS EXISTS: step3_trace.py re-wrapped the SINGLETON DailyMed store's
`_get_embedding` once per run; from run 2 the wrapper chain hit run 1's already-popped
`_dm_emb` key, raised KeyError, and production's fail-soft (`DailyMed search error`)
returned [] — so DailyMed contributed NOTHING to runs 2-5 BECAUSE OF THE HARNESS.

DailyMed retrieval is a pure function of the query string (cosine over the shipped
label_emb.npy, floor = the production local_threshold). So this script re-embeds every
DISTINCT DailyMed query string those runs issued (recorded in step3_trace.json as the
union rewrite calls + the raw query) and reports how many docs would have cleared the
floor. If the answer is 0 for every string, the harness bug did not change any run's
outcome. No retrieval, no rewrite, no completion call is made.
"""
import asyncio
import json
from pathlib import Path

import numpy as np

from _harness import QUERY, production_retriever

HERE = Path(__file__).resolve().parent
OUT = HERE / "step3b_dm_counterfactual.json"


async def main():
    tr = json.load(open(HERE / "step3_trace.json", encoding="utf-8"))
    r, cfg = production_retriever()
    floor = cfg["local_threshold"]
    store = r.dailymed_store
    assert store.embeddings is not None and len(store.documents) == 4608, "DailyMed store not loaded"
    E = store.embeddings / (np.linalg.norm(store.embeddings, axis=1, keepdims=True) + 1e-10)

    per_run = {}
    strings = []
    for run in tr["runs"]:
        # the retriever issues 1 K=1 rewrite call then k=3 union calls; DailyMed uses the union + raw query
        union = []
        for batch in run["rewrite_calls"][1:4]:
            for s in batch:
                if s not in union:
                    union.append(s)
        if QUERY not in union:
            union.append(QUERY)
        per_run[run["run"]] = union
        strings += [s for s in union if s not in strings]

    rows = []
    for s in strings:
        e = await store._get_embedding(s)
        sc = E @ (e / (np.linalg.norm(e) + 1e-10))
        top = int(np.argmax(sc))
        rows.append({"query": s, "n_at_or_above_floor": int((sc >= floor).sum()),
                     "max_cos": round(float(sc[top]), 4),
                     "max_doc": store.documents[top]["source_id"],
                     "max_title": store.documents[top]["title"][:90]})
        print(rows[-1], flush=True)
    res = {"floor": floor, "distinct_dailymed_queries": len(strings), "per_run_union": per_run,
           "rows": rows,
           "any_string_clears_floor": any(x["n_at_or_above_floor"] for x in rows),
           "global_max": max(rows, key=lambda x: x["max_cos"])}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ANY clears floor:", res["any_string_clears_floor"], "| global max:", res["global_max"])


if __name__ == "__main__":
    asyncio.run(main())
