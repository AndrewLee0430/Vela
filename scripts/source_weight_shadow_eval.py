# -*- coding: utf-8 -*-
"""Source-weighting SHADOW — day-one offline battery + first data report (v198).

Drives the REAL retrieval pipeline (rewrite → 4-source search → dedup → year-boost →
relevance-filter → rerank) via HybridRetriever.retrieve(shadow_sink=[]), then runs the
deterministic §2.10.3/§2.10.6 shadow over the captured pool. NO endpoint, NO answer
generation, NO writeback — pure measurement. Produces:
  tests/results/source_weight_shadow_report_<ts>.json  (full per-query records)
  + a human-readable summary to stdout.

Battery (per task Stage 4a): R01–R20-style + TB + CJK-brand + danger-path + English.
Usage: python scripts/source_weight_shadow_eval.py   (needs OPENAI/PubMed keys via .env)
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
from api.server import _annotate_research_question  # noqa: E402 (v195 CJK annotation, real path)

# ── Battery (labeled by class for the report) ───────────────────────────────────────
BATTERY = [
    # class, query
    ("english", "What are the side effects of metformin in renal impairment?"),
    ("english", "warfarin aspirin interaction bleeding risk"),
    ("english", "statin muscle pain management"),
    ("english", "ACE inhibitor use in pregnancy"),
    ("english", "digoxin toxicity symptoms"),
    ("cjk_brand", "冠脂妥高血脂可以吃嗎"),
    ("cjk_brand", "保栓通要吃多久"),
    ("cjk_brand", "太田胃散和warfarin一起吃安全嗎"),
    ("danger_path", "冠脂妥和warfarin一起吃安全嗎"),
    ("danger_path", "冠脂妥懷孕可以吃嗎"),
    ("indication", "冠脂妥台灣核准的適應症有哪些"),
    ("research", "polypharmacy risks in elderly Asian patients"),
    ("research", "SGLT2 inhibitor cardiovascular benefit"),
]
SAFETY_CLASSES = {"danger_path"}   # TFDA-cited-0 invariant applies here


async def run_one(retriever, cls, query):
    annotated = _annotate_research_question(query)
    sink: list = []
    docs, status = await retriever.retrieve(query=annotated, max_results=5, shadow_sink=sink)
    rec = sws.build_shadow_record(sink, top_k=5, query_label=f"[{cls}] {query}") if sink else None
    returned_sources = [str(getattr(d.source_type, "value", d.source_type)) for d in docs]
    tfda_in_topk = any(s == "tfda" for s in returned_sources)
    return {
        "class": cls, "query": query, "status": status,
        "returned_top5_sources": returned_sources,
        "tfda_in_current_top5": tfda_in_topk,
        "record": rec,
    }


async def main():
    retriever = HybridRetriever()   # all 4 sources live
    results = []
    for cls, q in BATTERY:
        print(f"… [{cls}] {q}")
        try:
            results.append(await run_one(retriever, cls, q))
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {e}")
            results.append({"class": cls, "query": q, "error": f"{type(e).__name__}: {e}"})

    # ── Aggregate report ────────────────────────────────────────────────────────────
    agg = {"n_queries": len(results), "by_variant": {}, "safety": {}, "tier_dist_total": {}}
    for v in ("V1", "V2", "V3"):
        changed = sum(1 for r in results
                      if r.get("record") and r["record"]["summary"].get(f"top_k_changed_under_{v}"))
        agg["by_variant"][v] = {"top_k_changed_count": changed}
    inversion_total = sum(len(r["record"]["inversion_flags"]) for r in results if r.get("record"))
    agg["label_vs_study_inversions_total"] = inversion_total
    # tier distribution across all retrieved pools
    for r in results:
        if r.get("record"):
            for t, c in r["record"]["tier_distribution"].items():
                agg["tier_dist_total"][t] = agg["tier_dist_total"].get(t, 0) + c
    # SAFETY: danger-path must never have TFDA in top-5 today, AND V1 must not PROMOTE
    # a TFDA doc into a safety query's top-5 (the v193 constitution under weighting).
    safety_violations = []
    for r in results:
        if r["class"] in SAFETY_CLASSES and r.get("record"):
            if r["tfda_in_current_top5"]:
                safety_violations.append({"query": r["query"], "kind": "tfda_already_in_top5"})
            promoted = r["record"].get("tfda_promoted_into_topk") or []
            if promoted:
                safety_violations.append({"query": r["query"], "kind": "V1_promotes_tfda_into_top5",
                                          "docs": promoted})
    agg["safety"]["danger_path_violations"] = safety_violations
    agg["safety"]["danger_path_clean"] = (len(safety_violations) == 0)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = ROOT / "tests" / "results" / f"source_weight_shadow_report_{ts}.json"
    out_path.write_text(json.dumps({"timestamp": ts, "aggregate": agg, "results": results},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    # ── Human summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 66)
    print("SOURCE-WEIGHTING SHADOW — FIRST DATA REPORT")
    print("=" * 66)
    print(f"queries: {agg['n_queries']}")
    for v in ("V1", "V2", "V3"):
        print(f"  {v} top-k set changed: {agg['by_variant'][v]['top_k_changed_count']}/{agg['n_queries']}")
    print(f"  label-vs-study inversions (V1, total): {inversion_total}")
    print(f"  tier distribution (all retrieved pools): {agg['tier_dist_total']}")
    print(f"  DANGER-PATH clean (no TFDA in/promoted-into safety top-5): {agg['safety']['danger_path_clean']}")
    if safety_violations:
        print(f"  ⚠️ SAFETY VIOLATIONS: {json.dumps(safety_violations, ensure_ascii=False)}")
    print("\nper-query top-k change (V1) + inversions:")
    for r in results:
        if r.get("record"):
            s = r["record"]["summary"]
            print(f"  [{r['class']}] {r['query'][:38]:38} | status={r['status']:10} | "
                  f"V1chg={str(s.get('top_k_changed_under_V1')):5} | "
                  f"inv={len(r['record']['inversion_flags'])} | "
                  f"top5={r['returned_top5_sources']}")
        else:
            print(f"  [{r['class']}] {r['query'][:38]:38} | {r.get('status') or r.get('error')}")
    print(f"\nsaved: {out_path}")
    return 0 if agg["safety"]["danger_path_clean"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
