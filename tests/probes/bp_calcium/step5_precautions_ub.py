"""PROBE 2 · STEP 2b — UPPER BOUND for verdict B (1 embedding call, 0 fetches).

step5_precautions.py intended to embed the calcium-bearing SUBSECTION of HCTZ PRECAUTIONS
as an upper bound, but "Parathyroid Disease" is a PARAGRAPH inside 42232-9, not a nested
<section>, so no subsection was found. This embeds the calcium sentence ALONE (read back
from step5_precautions.json — no refetch): the most query-like text the label could ever
contribute. A doc the builder would never produce; a ceiling, not a candidate.
"""
import asyncio
import json
from pathlib import Path

import numpy as np

from _harness import production_retriever

HERE = Path(__file__).resolve().parent
OUT = HERE / "step5_precautions_ub.json"


async def main():
    from api.providers.base import EmbeddingRequest
    r, cfg = production_retriever()
    store = r.dailymed_store
    E = store.embeddings / (np.linalg.norm(store.embeddings, axis=1, keepdims=True) + 1e-10)
    pre = json.load(open(HERE / "step5_precautions.json", encoding="utf-8"))
    sentence = pre["hctz"]["calcium_sentences"][0]
    queries = [q["query"] for q in pre["scored"][0]["per_query"]]
    # ONE call: the sentence + the 9 queries batched together (queries re-embedded so this
    # file stands alone; text-embedding-3-small is deterministic enough for a ceiling)
    resp = await store._embedder.embed(EmbeddingRequest(model=store._embedder_model,
                                                        input=[sentence] + queries))
    V = np.array(resp.embeddings, dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    s, Q = V[0], V[1:]
    rows = []
    for q, qv in zip(queries, Q):
        cos = float(s @ qv)
        rows.append({"query": q, "cos": round(cos, 4), "clears_floor": cos >= cfg["local_threshold"],
                     "would_be_rank": int(((E @ qv) > cos).sum()) + 1})
        print(rows[-1])
    best = max(rows, key=lambda x: x["cos"])
    res = {"text": sentence, "embedding_calls": 1, "rows": rows,
           "n_clear_floor": sum(x["clears_floor"] for x in rows), "best": best,
           "verdict_B_upper_bound": f"UPPER BOUND: the calcium sentence ALONE clears 0.6 on "
                                    f"{sum(x['clears_floor'] for x in rows)}/{len(rows)} strings (best {best['cos']})"}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res["verdict_B_upper_bound"])


if __name__ == "__main__":
    asyncio.run(main())
