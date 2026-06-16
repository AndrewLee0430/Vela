#!/usr/bin/env python
"""Retrieval-recall stability diagnostic (NO generation).

Runs the Research RETRIEVAL stage only (HybridRetriever: query-rewrite -> PubMed/local/FDA
search -> dedup -> year-boost -> relevance-filter -> rerank), N times per query, and records
the ranked PMIDs at each pipeline stage. Lets us measure how often a target "anchor" PMID is
actually retrieved, and distinguish:
  - recall-miss   : anchor never enters the PubMed candidate POOL (query-rewrite / PubMed recall)
  - rerank-drop   : anchor in the pool but dropped by relevance-filter or rerank (ordering)

No answer generation, no judge -> only cheap rewrite/filter/rerank (mini models) + embeddings +
PubMed API. Dev-only.
"""
import asyncio, json, re, sys, time
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

from api.rag.retriever import HybridRetriever
from api.models.schemas import SourceType

RESULTS_DIR = _REPO / "tests" / "results"
N = 10
MAXR = 5  # matches /api/research default (body.max_results or 5)

QUERIES = [
    ("P-L0",  "35268461", "What are the clinical outcomes of polypharmacy in elderly patients with atrial fibrillation?"),
    ("P-L1",  "35268461", "Is polypharmacy associated with worse survival in elderly patients with atrial fibrillation?"),
    ("P-L2",  "35268461", "Why is polypharmacy a serious problem in elderly Asian patients?"),
    ("OB-L0", "37290898", "What are the clinical outcomes of higher body weight (overweight or obesity) in patients with heart failure?"),
    ("OB-L1", "37290898", "Is overweight or obesity associated with worse survival in patients with heart failure?"),
    ("OB-L2", "37290898", "Why is obesity a serious problem that worsens survival in patients with heart failure?"),
]


def _pmid(doc) -> str | None:
    sid = getattr(doc, "source_id", "") or ""
    m = re.search(r"(\d{5,})", sid)
    return m.group(1) if m else None


async def _one_run(r: HybridRetriever, query: str) -> dict:
    """Replicate HybridRetriever.retrieve() stages, capturing PMIDs at each."""
    rewritten = await r._rewrite_query(query)
    tasks = []
    for rq in rewritten:
        tasks.append(r._search_local(rq, MAXR))
        tasks.append(r._search_pubmed(rq, MAXR))
        tasks.append(r._search_fda(rq, MAXR))
    res = await asyncio.gather(*tasks, return_exceptions=True)
    alldocs = [d for x in res if isinstance(x, list) for d in x]

    pubmed_pool = [p for p in (_pmid(d) for d in alldocs
                   if getattr(d, "source_type", None) == SourceType.PUBMED) if p]

    # dedup by source_id (keep highest relevance_score) — mirrors retrieve()
    best = {}
    for i, d in enumerate(alldocs):
        prev = best.get(d.source_id)
        if prev is None or d.relevance_score > alldocs[prev].relevance_score:
            best[d.source_id] = i
    uniq = [alldocs[i] for i in sorted(best.values())]
    uniq = r._apply_year_boost(uniq)
    uniq.sort(key=lambda x: x.relevance_score, reverse=True)
    candidates = uniq[:MAXR * 4]
    cand_pmids = [(p, round(d.relevance_score, 3)) for d in candidates if (p := _pmid(d))]

    relevant = await r._filter_by_relevance(query, candidates)
    rel_pmids = [p for d in relevant if (p := _pmid(d))]

    try:
        final = await r.reranker.rerank(query, relevant)
    except Exception:
        final = relevant
    final = final[:MAXR]
    final_pmids = [p for d in final if (p := _pmid(d))]

    return {
        "rewritten": rewritten,
        "pubmed_pool": sorted(set(pubmed_pool)),
        "candidates": cand_pmids,          # (pmid, score) top-20 pre-filter
        "relevant": rel_pmids,             # post relevance-filter, pre-rerank
        "final": final_pmids,              # post-rerank top-5 (what generation sees)
    }


async def main():
    r = HybridRetriever()  # default flags: local + pubmed + fda (same as /api/research)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "N": N, "max_results": MAXR, "queries": []}

    for qid, anchor, query in QUERIES:
        print(f"\n=== {qid} (anchor {anchor}) — {N} runs ===")
        runs = []
        for n in range(1, N + 1):
            try:
                rec = await _one_run(r, query)
            except Exception as e:
                rec = {"error": f"{type(e).__name__}: {e}", "rewritten": [], "pubmed_pool": [],
                       "candidates": [], "relevant": [], "final": []}
            in_pool = anchor in rec["pubmed_pool"]
            in_cand = anchor in [p for p, _ in rec["candidates"]]
            in_final = anchor in rec["final"]
            final_rank = (rec["final"].index(anchor) + 1) if in_final else None
            runs.append({"run": n, **rec, "anchor_in_pool": in_pool,
                         "anchor_in_candidates": in_cand, "anchor_in_final": in_final,
                         "anchor_final_rank": final_rank})
            print(f"  run{n}: pool={'Y' if in_pool else '-'} cand={'Y' if in_cand else '-'} "
                  f"final={'Y@'+str(final_rank) if in_final else '-'}  final_pmids={rec['final']}")
            time.sleep(1.0)  # gentle on PubMed
        pool_freq = sum(x["anchor_in_pool"] for x in runs)
        final_freq = sum(x["anchor_in_final"] for x in runs)
        out["queries"].append({"id": qid, "anchor": anchor, "query": query,
                               "pool_recall": f"{pool_freq}/{N}", "final_recall": f"{final_freq}/{N}",
                               "runs": runs})
        print(f"  --> anchor in POOL {pool_freq}/{N} | in FINAL {final_freq}/{N}")

    ts = out["timestamp"]
    fp = RESULTS_DIR / f"retrieval_recall_{ts}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSaved -> {fp}")


if __name__ == "__main__":
    asyncio.run(main())
