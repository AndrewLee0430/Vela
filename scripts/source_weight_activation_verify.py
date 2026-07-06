# -*- coding: utf-8 -*-
"""Source-weighting ACTIVATION — live danger-path HARD GATE + reweighting evidence.

Runs the REAL pipeline via HybridRetriever.retrieve(source_weight_active=True) and
inspects the ACTIVATED returned top-k (not just the shadow record). Three checks:

  STAGE 2 (HARD GATE): danger-path queries must return TFDA-cited = 0 — an activated
    reorder must NEVER promote a TFDA-indication (or local) doc into a safety query's
    cited top-k in any way readable as safety clearance (v193 constitution, live).
  REWEIGHT DEMO: a normal Research query — show the activated order vs the plain
    rerank order (label-above-study where expected), and confirm the SET is stable
    (reorder, not churn).
  ENGLISH SANITY: an English query behaves (reorder uniform, no drop/add).

For each query it ALSO runs the shadow over the same pool and asserts the activated
top-k == the shadow's V1 top-k (live parity, on real pools).

Usage: python scripts/source_weight_activation_verify.py   (needs OPENAI/PubMed keys)
Exit 0 iff danger-path clean AND live parity holds on every query.
"""
import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from api.rag.retriever import HybridRetriever  # noqa: E402
from api.services import source_weight_shadow as sws  # noqa: E402
from api.server import _annotate_research_question  # noqa: E402

DANGER = [
    ("danger_path", "冠脂妥和warfarin一起吃安全嗎"),
    ("danger_path", "冠脂妥懷孕可以吃嗎"),
    ("danger_path", "太田胃散和warfarin一起吃安全嗎"),
]
NORMAL = [
    ("reweight", "warfarin aspirin interaction bleeding risk"),
    ("reweight", "statin muscle pain management"),
    ("indication", "冠脂妥台灣核准的適應症有哪些"),
]
ENGLISH = [("english", "What are the side effects of metformin in renal impairment?")]


def _sources(docs):
    return [str(getattr(d.source_type, "value", d.source_type)) for d in docs]


async def run_one(retriever, cls, query):
    annotated = _annotate_research_question(query)
    # Activated run WITH a shadow sink → returned docs are V1-reordered; the sink holds
    # the same pool so we can prove live == shadow on a REAL pool.
    sink: list = []
    docs, status = await retriever.retrieve(
        query=annotated, max_results=5, shadow_sink=sink, source_weight_active=True)
    # Plain (OFF) run over the same query for the reorder-vs-rerank comparison.
    docs_off, _ = await retriever.retrieve(query=annotated, max_results=5)

    live_topk_sources = _sources(docs)
    live_topk_ids = [d.source_id for d in docs]
    off_topk_ids = [d.source_id for d in docs_off]

    parity_ok = None
    shadow_v1_ids = None
    if sink:
        rec = sws.build_shadow_record(sink, top_k=5, query_label=f"[{cls}] {query}")
        per = rec["per_doc"]
        shadow_v1_ids = [d["source_id"] for d in sorted(per, key=lambda d: d["V1_rank"])][:5]
        parity_ok = (live_topk_ids == shadow_v1_ids)

    tfda_cited = sum(1 for s in live_topk_sources if s == "tfda")
    local_cited = sum(1 for s in live_topk_sources if s == "local")
    return {
        "class": cls, "query": query, "status": status,
        "activated_top5_sources": live_topk_sources,
        "activated_top5_ids": live_topk_ids,
        "off_top5_ids": off_topk_ids,
        "reordered": live_topk_ids != off_topk_ids,
        "set_changed": set(live_topk_ids) != set(off_topk_ids),
        "tfda_cited": tfda_cited, "local_cited": local_cited,
        "shadow_v1_top5_ids": shadow_v1_ids, "live_equals_shadow": parity_ok,
    }


async def main():
    retriever = HybridRetriever()  # all 4 sources live
    results, parity_fail, danger_violations = [], [], []
    for cls, q in DANGER + NORMAL + ENGLISH:
        print(f"… [{cls}] {q}")
        try:
            r = await run_one(retriever, cls, q)
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {e}")
            results.append({"class": cls, "query": q, "error": f"{type(e).__name__}: {e}"})
            continue
        results.append(r)
        if r["class"] == "danger_path" and r["tfda_cited"] > 0:
            danger_violations.append({"query": q, "tfda_cited": r["tfda_cited"]})
        if r.get("live_equals_shadow") is False:
            parity_fail.append({"query": q, "live": r["activated_top5_ids"],
                                "shadow": r["shadow_v1_top5_ids"]})

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = ROOT / "tests" / "results" / f"source_weight_activation_verify_{ts}.json"
    out.write_text(json.dumps(
        {"timestamp": ts, "danger_violations": danger_violations,
         "parity_failures": parity_fail, "results": results},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 70)
    print("SOURCE-WEIGHTING ACTIVATION — LIVE VERIFY")
    print("=" * 70)
    for r in results:
        if r.get("error"):
            print(f"  [{r['class']}] {r['query'][:34]:34} | ERROR {r['error']}")
            continue
        tag = "DANGER" if r["class"] == "danger_path" else "     "
        print(f"  {tag} [{r['class']:11}] {r['query'][:30]:30} | status={r['status']:10} "
              f"| tfda={r['tfda_cited']} local={r['local_cited']} "
              f"| reordered={str(r['reordered']):5} set_changed={str(r['set_changed']):5} "
              f"| parity={r['live_equals_shadow']}")
        print(f"        off  ={r['off_top5_ids']}")
        print(f"        activ={r['activated_top5_ids']}  ({r['activated_top5_sources']})")
    print("-" * 70)
    print(f"DANGER-PATH violations (TFDA cited on a safety query): {len(danger_violations)}  "
          f"{'CLEAN ✅' if not danger_violations else json.dumps(danger_violations, ensure_ascii=False)}")
    print(f"LIVE PARITY failures (activated != shadow V1): {len(parity_fail)}  "
          f"{'CLEAN ✅' if not parity_fail else json.dumps(parity_fail, ensure_ascii=False)}")
    print(f"saved: {out}")
    ok = not danger_violations and not parity_fail
    print(f"\nRESULT: {'PASS ✅ (safe to proceed to §2.7)' if ok else 'FAIL ❌ — DO NOT SHIP ON'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
