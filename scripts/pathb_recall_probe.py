#!/usr/bin/env python
"""Path B feasibility PROBE (go/no-go) — can a smarter retrieval ACTION recover the MISSED protective
anchor for the obesity retrieval-miss cases? Standalone diagnostic. NOT a build, NO flags, NO server
changes. Does NOT reuse captured pools — issues REAL new retrieval actions.

Two methods vs baseline, on OB-L0/1/2 (anchor 37290898 = "Body mass index and survival in people with
heart failure", provably missed by the standard pipeline: OB-L2 0/10 pool, OB-L0 7/10 pool but 0/10
final = rerank burial — retrieval_recall_20260616_133331.json):
  baseline : standard pipeline (r._rewrite_query) — reproduce the miss.
  (M1) TERM-EXPANSION : retrieve with hardcoded obesity->BMI measurement-synonym queries (bypass the
       LLM rewrite). Does the anchor enter the pool / final?
  (M2) TWO-SIDED : baseline rewrite + counter-framed (obesity-paradox / BMI-survival-benefit) queries,
       MERGED. Does the anchor enter the merged pool / final?

Reuses the real HybridRetriever stages (search -> dedup -> year-boost -> relevance-filter -> rerank),
mirroring scripts/retrieval_recall_check.py::_one_run. Dev-only. Reports anchor in POOL and in FINAL.
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
from api.providers.factory import get_lightweight_provider
from api.providers.base import CompletionRequest

RESULTS_DIR = _REPO / "tests" / "results"
MAXR = 5          # production /api/research default (per rewritten query)
REPS = 2          # baseline + M2 have stochastic rewrite/rerank; M1 search is deterministic
ANCHOR = "37290898"

OB_CASES = [
    ("OB-L0", "What are the clinical outcomes of higher body weight (overweight or obesity) in patients with heart failure?"),
    ("OB-L1", "Is overweight or obesity associated with worse survival in patients with heart failure?"),
    ("OB-L2", "Why is obesity a serious problem that worsens survival in patients with heart failure?"),
]
# (M1) lay term -> measurement/MeSH synonyms (hardcoded inline for the probe; a durable synonym table
# is the stage-2 build decision, NOT built here).
M1_REWRITES = [
    "body mass index survival heart failure",
    "obesity overweight BMI mortality prognosis heart failure",
    "body mass index outcomes patients heart failure",
]
# (M2) counter-framed queries seeking the PROTECTIVE/paradox side (merged with the baseline rewrite).
M2_COUNTER = [
    "obesity paradox heart failure survival",
    "body mass index survival benefit heart failure",
    "higher BMI lower mortality heart failure",
]


def _pmid(doc):
    m = re.search(r"(\d{5,})", getattr(doc, "source_id", "") or "")
    return m.group(1) if m else None


async def _pipeline(r, scoring_query, rewritten):
    """Mirror HybridRetriever.retrieve() stages for a given `rewritten` query list."""
    tasks = []
    for rq in rewritten:
        tasks += [r._search_local(rq, MAXR), r._search_pubmed(rq, MAXR), r._search_fda(rq, MAXR)]
    res = await asyncio.gather(*tasks, return_exceptions=True)
    alldocs = [d for x in res if isinstance(x, list) for d in x]
    pool = sorted({p for p in (_pmid(d) for d in alldocs
                   if getattr(d, "source_type", None) == SourceType.PUBMED) if p})
    best = {}
    for i, d in enumerate(alldocs):
        prev = best.get(d.source_id)
        if prev is None or d.relevance_score > alldocs[prev].relevance_score:
            best[d.source_id] = i
    uniq = [alldocs[i] for i in sorted(best.values())]
    uniq = r._apply_year_boost(uniq)
    uniq.sort(key=lambda x: x.relevance_score, reverse=True)
    candidates = uniq[:MAXR * 4]
    relevant = await r._filter_by_relevance(scoring_query, candidates)
    try:
        final = (await r.reranker.rerank(scoring_query, relevant))[:MAXR]
    except Exception:
        final = relevant[:MAXR]
    return pool, [p for d in final if (p := _pmid(d))]


async def gate1():
    b = get_lightweight_provider()
    try:
        r = await b.provider.complete(CompletionRequest(model=b.model,
            messages=[{"role": "user", "content": "ping"}], temperature=0, max_tokens=5))
    except Exception as e:
        print(f"GATE1 DEAD: {type(e).__name__}: {str(e)[:160]}"); sys.exit(2)
    c = (r.content or "").strip()
    if not c or c.startswith("[ERROR]"):
        print("GATE1 DEAD: empty/[ERROR]"); sys.exit(3)
    print(f"GATE1 HEALTHY: {b.model} -> {c!r}\n")


async def main():
    await gate1()
    r = HybridRetriever()
    RESULTS_DIR.mkdir(exist_ok=True)
    out = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "anchor": ANCHOR,
           "max_results": MAXR, "reps": REPS, "cases": []}

    def agg(runs):
        return {"pool": f"{sum(x['in_pool'] for x in runs)}/{len(runs)}",
                "final": f"{sum(x['in_final'] for x in runs)}/{len(runs)}"}

    for cid, query in OB_CASES:
        print(f"=== {cid} (anchor {ANCHOR}) — {query}")
        methods = {"baseline": [], "M1_term_expansion": [], "M2_two_sided": []}
        for rep in range(1, REPS + 1):
            base_rw = await r._rewrite_query(query)
            for name, rewritten in (("baseline", base_rw),
                                    ("M1_term_expansion", M1_REWRITES),
                                    ("M2_two_sided", base_rw + M2_COUNTER)):
                pool, final = await _pipeline(r, query, rewritten)
                rec = {"rep": rep, "rewritten": rewritten, "pool": pool, "final": final,
                       "in_pool": ANCHOR in pool, "in_final": ANCHOR in final}
                methods[name].append(rec)
                print(f"   rep{rep} {name:18} pool={'Y' if rec['in_pool'] else '-'} "
                      f"final={'Y' if rec['in_final'] else '-'}  (|pool|={len(pool)})")
                time.sleep(0.5)
        case = {"id": cid, "query": query,
                "baseline": agg(methods["baseline"]),
                "M1_term_expansion": agg(methods["M1_term_expansion"]),
                "M2_two_sided": agg(methods["M2_two_sided"]),
                "runs": methods}
        out["cases"].append(case)
        print(f"   --> baseline pool {case['baseline']['pool']} final {case['baseline']['final']} | "
              f"M1 pool {case['M1_term_expansion']['pool']} final {case['M1_term_expansion']['final']} | "
              f"M2 pool {case['M2_two_sided']['pool']} final {case['M2_two_sided']['final']}\n")

    fp = RESULTS_DIR / f"pathb_recall_probe_{out['timestamp']}.json"
    json.dump(out, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("=" * 66)
    print("PATH B RECALL PROBE — REAL NUMBERS (anchor in POOL / in FINAL, /reps)")
    print("=" * 66)
    for c in out["cases"]:
        print(f"  {c['id']}: baseline P {c['baseline']['pool']} F {c['baseline']['final']} | "
              f"M1 P {c['M1_term_expansion']['pool']} F {c['M1_term_expansion']['final']} | "
              f"M2 P {c['M2_two_sided']['pool']} F {c['M2_two_sided']['final']}")
    print(f"\nSaved -> {fp}")


if __name__ == "__main__":
    asyncio.run(main())
