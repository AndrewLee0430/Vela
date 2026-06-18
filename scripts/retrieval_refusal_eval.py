#!/usr/bin/env python
"""Retrieval-recall REFUSAL detector (H1) — SHADOW validation harness (offline, in-repo).

Per retrieval_refusal_planback.md §Corpus + §gating-risk. Reuses captured FINAL pools (no
re-retrieval): detection set = OB-L*/P-L* finals from retrieval_recall; over-refusal control =
direction_shadow doc_pmids. Re-fetches full abstracts by PMID (invariant: full text the generator
saw). Runs H1 (gpt-4.1): factor->outcome + per-source pool-direction + counter-prior + trigger.

Measures BOTH (the C1 lesson):
  - DETECTION: fires on the real retrieval-miss cases (OB-L*, protective source absent)?
  - OVER-REFUSAL: fires on complete-pool (P-L*) or genuinely one-directional / counterintuitive-but-
    settled controls (the FP-analog)? Frozen denominator + criterion.

Dev-only; reads dev .env; no prod path, no DB, no SSE. Reports actual token/$ cost.
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

from api.data_sources.pubmed import PubMedClient
from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest
from api.services.cost_tracker import MODEL_COSTS
import api.services.retrieval_refusal as rr

CORPUS = _REPO / "tests" / "retrieval_refusal_corpus.json"
MODEL = rr.STRONG_MODEL
_TOK = {"in": 0, "out": 0}


def make_tracking_llm():
    prov = OpenAIProvider()
    async def _llm(prompt: str) -> str:
        resp = await prov.complete(CompletionRequest(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=500, response_format={"type": "json_object"}))
        _TOK["in"] += resp.input_tokens or 0
        _TOK["out"] += resp.output_tokens or 0
        return resp.content or ""
    return _llm


async def assess_pool(llm, query, pmids, abstracts, fo_cache, prior_cache, key):
    """H1 on one pool, caching factor/outcome + prior per case-key (same query across runs)."""
    if key not in fo_cache:
        fo_cache[key] = await rr._factor_outcome(llm, query)
    fo = fo_cache[key]
    factor, outcome = fo.get("factor", ""), fo.get("outcome", "")
    if key not in prior_cache:
        prior_cache[key] = await rr._counter_prior(llm, factor, outcome)
    prior = prior_cache[key]
    dirs = {}
    for p in pmids:
        ab = abstracts.get(p)
        if not ab:
            continue
        sd = await rr._source_direction(llm, ab, factor, outcome, p)
        dirs[p] = (sd.get("stance") or "not_relevant").strip().lower()
    spread = rr._spread(list(dirs.values()))
    counter = bool(prior.get("counter_plausible"))
    refuse = bool(spread["one_sided"] and counter)
    return {"factor": factor, "outcome": outcome, "dirs": dirs, "spread": spread,
            "counter_plausible": counter, "prior": prior, "refuse": refuse}


async def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    import os
    if os.getenv("RR_ONLY"):  # smoke: comma-separated IDs
        want = {s.strip() for s in os.getenv("RR_ONLY").split(",")}
        for sec in ("detection_set", "complete_pool_controls", "over_refusal_control"):
            corpus[sec]["cases"] = {k: v for k, v in corpus[sec]["cases"].items() if k in want}
    pubmed = PubMedClient()
    llm = make_tracking_llm()

    # collect all PMIDs across the frozen corpus, fetch full abstracts once
    pmids = set()
    for c in corpus["detection_set"]["cases"].values():
        for r in c["runs"]:
            pmids.update(r["final"])
    for c in corpus["complete_pool_controls"]["cases"].values():
        for r in c["runs"]:
            pmids.update(r["final"])
    for c in corpus["over_refusal_control"]["cases"].values():
        pmids.update(c["doc_pmids"])
    pmids = sorted(pmids)
    abstracts = {}
    for i in range(0, len(pmids), 20):
        for a in await pubmed.fetch_details(pmids[i:i + 20]):
            if (a.abstract or "").strip():
                abstracts[a.pmid] = a.abstract
    print(f"model={MODEL}; fetched {len(abstracts)}/{len(pmids)} abstracts\n")

    fo_cache, prior_cache = {}, {}
    results = {"detection": [], "complete_pool": [], "over_refusal_control": []}

    async def run_multi(cid, c, bucket):
        fired = 0
        runs_out = []
        for r in c["runs"]:
            a = await assess_pool(llm, c["query"], r["final"], abstracts, fo_cache, prior_cache, cid)
            fired += int(a["refuse"])
            runs_out.append({"run": r["run"], **a})
        rec = {"id": cid, "expect": c["expect"], "n_runs": len(c["runs"]), "fired": fired,
               "factor": runs_out[0]["factor"], "outcome": runs_out[0]["outcome"],
               "counter_plausible": runs_out[0]["counter_plausible"], "runs": runs_out}
        results[bucket].append(rec)
        print(f"  [{cid:7}] {bucket:16} fired {fired}/{len(c['runs'])}  counter={rec['counter_plausible']} "
              f"factor={rec['factor'][:34]!r}")

    for cid, c in corpus["detection_set"]["cases"].items():
        await run_multi(cid, c, "detection")
    for cid, c in corpus["complete_pool_controls"]["cases"].items():
        await run_multi(cid, c, "complete_pool")
    for cid, c in corpus["over_refusal_control"]["cases"].items():
        a = await assess_pool(llm, c["query"], c["doc_pmids"], abstracts, fo_cache, prior_cache, cid)
        rec = {"id": cid, "topic": c["topic"], "expect": c["expect"],
               "one_sided": a["spread"]["one_sided"], "counter_plausible": a["counter_plausible"],
               "refuse": a["refuse"], "factor": a["factor"], "outcome": a["outcome"],
               "dirs": a["dirs"], "spread": a["spread"], "prior": a["prior"]}
        results["over_refusal_control"].append(rec)
        print(f"  [{cid:7}] over_refusal      refuse={a['refuse']}  one_sided={a['spread']['one_sided']} "
              f"counter={a['counter_plausible']}  factor={a['factor'][:30]!r}")

    # ---- scoring ----
    det = results["detection"]
    det_fire = [r for r in det if r["fired"] > 0]
    det_runs_total = sum(r["n_runs"] for r in det)
    det_runs_fired = sum(r["fired"] for r in det)
    cp = results["complete_pool"]
    cp_overfire = [r for r in cp if r["fired"] > 0]
    ctrl = results["over_refusal_control"]
    ctrl_fire = [r for r in ctrl if r["refuse"]]
    ctrl_onesided = [r for r in ctrl if r["one_sided"]]

    pc = MODEL_COSTS[MODEL]
    cost = _TOK["in"] / 1e6 * pc["input"] + _TOK["out"] / 1e6 * pc["output"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _REPO / "tests" / "results" / f"retrieval_refusal_{ts}.json"
    json.dump({"timestamp": ts, "model": MODEL, "tokens": _TOK, "cost_usd": round(cost, 4),
               "results": results}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n" + "=" * 70)
    print("RETRIEVAL-RECALL REFUSAL (H1) — SHADOW VALIDATION — REAL NUMBERS")
    print("=" * 70)
    print(f"DETECTION (should refuse): {len(det_fire)}/{len(det)} retrieval-miss cases fired at least once; "
          f"by run {det_runs_fired}/{det_runs_total}.  fired={[r['id'] for r in det_fire]} "
          f"missed={[r['id'] for r in det if r['fired']==0]}")
    print(f"COMPLETE-POOL controls (should NOT refuse): {len(cp_overfire)}/{len(cp)} over-fired  "
          f"{[r['id'] for r in cp_overfire]}")
    print(f"OVER-REFUSAL control (should NOT refuse): {len(ctrl_fire)}/{len(ctrl)} fired  "
          f"(of which {len(ctrl_onesided)}/{len(ctrl)} had a one-sided pool = actually stressed the prior leg)")
    print(f"   over-refused = {[r['id'] for r in ctrl_fire]}")
    print(f"   one-sided controls (prior-leg stress) = {[r['id'] for r in ctrl_onesided]}")
    print(f"\nCOST: in={_TOK['in']} out={_TOK['out']} tokens => ${cost:.4f} ({MODEL} @ ${pc['input']}/${pc['output']} per 1M)")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
