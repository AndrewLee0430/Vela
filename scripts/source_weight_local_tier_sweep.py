# -*- coding: utf-8 -*-
"""Local-corpus tier DECISION sweep (offline, read-only). — v199 analysis slot

Extends the v198 shadow (api/services/source_weight_shadow.py) WITHOUT changing its
logic: captures each query's reranked pool ONCE via retrieve(shadow_sink=), then
recomputes build_shadow_record() over that captured pool under a sweep of the
local-corpus tier config value (and the PubMed "Review"→tier value). The sweep varies
ONLY module CONFIG CONSTANTS (LOCAL_DEFAULT_TIER, _PUBTYPE_TIER['review']) — save/set/
restore around each call — so the scorer's v198 math is reused verbatim; no re-retrieval,
no added LLM calls, no production-path edit.

Produces the founder decision report: for each local-tier value, the top-5 citation-set
change rate, local promotion/demotion by category, the DANGER-PATH invariant (must be 0
violations under EVERY candidate weight), and label-vs-study inversion counts.

Output: tests/results/local_tier_sweep_<ts>.json  + human summary to stdout.
Usage: python scripts/source_weight_local_tier_sweep.py   (needs OPENAI/PubMed keys)
"""
import asyncio
import io
import json
import os
import sys
import time
from collections import defaultdict
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

TOP_K = 5
LOCAL_TIER_SWEEP = [1, 2, 3, 4, 5]          # local tier → weight {2.0,1.5,1.2,1.0,0.7}
TIER_TO_WEIGHT = sws.TIER_WEIGHTS
REVIEW_SWEEP = [4, 2]                        # PubMed "Review" → Tier 4 (default) vs Tier 2
FOCUS_VARIANT = "V1"                         # V1 = rerank×source×tier (the full composite)


def _load_battery():
    data = json.load(open(ROOT / "scripts" / "source_weight_battery.json", encoding="utf-8"))
    return data["queries"]


async def _capture_pools(retriever, battery):
    """One retrieve() per query → captured pool + category + safety flag."""
    captured = []
    for i, item in enumerate(battery):
        q, cat = item["q"], item["cat"]
        safety = bool(item.get("safety"))
        try:
            sink = []
            await retriever.retrieve(query=_annotate_research_question(q), max_results=TOP_K, shadow_sink=sink)
            captured.append({"q": q, "cat": cat, "safety": safety, "pool": sink})
            pool_src = [sws._source_key(d) for d, _ in sink]
            print(f"  [{i+1:02d}/{len(battery)}] {cat:22} pool={len(sink):2} "
                  f"local={pool_src.count('local')} tfda={pool_src.count('tfda')} | {q[:30]}")
        except Exception as e:
            captured.append({"q": q, "cat": cat, "safety": safety, "pool": [], "error": str(e)})
            print(f"  [{i+1:02d}] ERROR {type(e).__name__}: {e} | {q[:30]}")
    return captured


def _record_under_config(pool, local_tier, review_tier):
    """Reuse build_shadow_record VERBATIM; sweep local-tier + review-tier via CONFIG
    values only (save/set/restore). No scorer logic touched."""
    orig_local = sws.LOCAL_DEFAULT_TIER
    orig_review = sws._PUBTYPE_TIER.get("review")
    try:
        sws.LOCAL_DEFAULT_TIER = local_tier
        sws._PUBTYPE_TIER["review"] = review_tier
        return sws.build_shadow_record(pool, top_k=TOP_K)
    finally:
        sws.LOCAL_DEFAULT_TIER = orig_local
        if orig_review is not None:
            sws._PUBTYPE_TIER["review"] = orig_review


def _local_in_topk(rec, rank_key):
    return any(d["source_type"] == "local" and d[rank_key] < TOP_K for d in rec["per_doc"])


def _sweep(captured, review_tier):
    """For each local-tier value, aggregate decision metrics over the battery."""
    rows = {}
    per_query_detail = defaultdict(list)
    for lt in LOCAL_TIER_SWEEP:
        set_changed = 0
        with_pool = 0
        local_entered = defaultdict(int)   # by category
        local_left = defaultdict(int)
        inversions = 0
        tfda_safety_violations = []        # HARD (v193 constitution)
        local_safety_promotions = []       # SOFT flag (FDA label on a safety query)
        for c in captured:
            if not c["pool"]:
                continue
            with_pool += 1
            rec = _record_under_config(c["pool"], lt, review_tier)
            s = rec["summary"]
            if s.get(f"top_k_changed_under_{FOCUS_VARIANT}"):
                set_changed += 1
            # local promotion/demotion into/out of top-k under V1
            cur_local = _local_in_topk(rec, "current_rank")
            v1_local = _local_in_topk(rec, f"{FOCUS_VARIANT}_rank")
            if v1_local and not cur_local:
                local_entered[c["cat"]] += 1
            if cur_local and not v1_local:
                local_left[c["cat"]] += 1
            inversions += len(rec["inversion_flags"])
            # DANGER-PATH invariant (safety queries only)
            if c["safety"]:
                if rec.get("tfda_promoted_into_topk"):
                    tfda_safety_violations.append({"q": c["q"], "docs": rec["tfda_promoted_into_topk"]})
                # local promoted into a safety top-k (soft — FDA label has safety content)
                for d in rec["per_doc"]:
                    if (d["source_type"] == "local" and d["current_rank"] >= TOP_K
                            and d[f"{FOCUS_VARIANT}_rank"] < TOP_K):
                        local_safety_promotions.append({"q": c["q"], "doc": d["source_id"], "tier": d["tier"]})
            per_query_detail[lt].append({
                "q": c["q"], "cat": c["cat"], "safety": c["safety"],
                "top_k_changed": s.get(f"top_k_changed_under_{FOCUS_VARIANT}"),
                "entered": s.get(f"{FOCUS_VARIANT}_entered_topk"),
                "left": s.get(f"{FOCUS_VARIANT}_left_topk"),
                "inversions": len(rec["inversion_flags"]),
            })
        rows[lt] = {
            "local_tier": lt,
            "local_tier_weight": TIER_TO_WEIGHT[lt],
            "with_pool": with_pool,
            "set_change_count": set_changed,
            "set_change_rate": round(set_changed / with_pool, 3) if with_pool else None,
            "local_entered_topk_by_cat": dict(local_entered),
            "local_left_topk_by_cat": dict(local_left),
            "inversions_total": inversions,
            "danger_tfda_violations": tfda_safety_violations,          # MUST be 0
            "danger_local_promotions_soft": local_safety_promotions,   # report-only
        }
    return rows, per_query_detail


async def main():
    battery = _load_battery()
    print(f"BATTERY: {len(battery)} queries")
    by_cat = defaultdict(int)
    for it in battery:
        by_cat[it["cat"]] += 1
    print("  by category:", dict(by_cat))
    print("\ncapturing pools (one retrieve() per query)…")
    retriever = HybridRetriever()
    captured = await _capture_pools(retriever, battery)

    n_with_pool = sum(1 for c in captured if c["pool"])
    n_local_appears = sum(1 for c in captured if any(sws._source_key(d) == "local" for d, _ in c["pool"]))
    print(f"\npools captured: {n_with_pool}/{len(captured)} non-empty; "
          f"local doc appears in {n_local_appears} pools")

    # Primary sweep at Review=T4 (default); secondary at Review=T2 for the 2nd decision.
    sweep_main, detail = _sweep(captured, review_tier=4)
    sweep_reviewT2, _ = _sweep(captured, review_tier=2)

    # local-as-study coherent alternative (tier 4 + source_weight dropped to 1.0)
    # computed by ALSO overriding SOURCE_WEIGHTS['local'] — still config-only.
    orig_sw = sws.SOURCE_WEIGHTS["local"]
    local_as_study = {}
    try:
        sws.SOURCE_WEIGHTS["local"] = 1.0
        las, _ = _sweep(captured, review_tier=4)
        local_as_study = las[4]  # tier 4 row under source_weight 1.0
    finally:
        sws.SOURCE_WEIGHTS["local"] = orig_sw

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = {
        "timestamp": ts, "battery_size": len(battery), "by_category": dict(by_cat),
        "pools_non_empty": n_with_pool, "local_appears_in_pools": n_local_appears,
        "sweep_review_T4": sweep_main, "sweep_review_T2": sweep_reviewT2,
        "local_as_study_alt": local_as_study,
    }
    out_path = ROOT / "tests" / "results" / f"local_tier_sweep_{ts}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── Human report ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 74)
    print("LOCAL-CORPUS TIER — DECISION REPORT (V1, Review=T4)")
    print("=" * 74)
    print(f"battery {len(battery)} | pools non-empty {n_with_pool} | local appears in {n_local_appears} pools")
    total_tfda_viol = sum(len(r["danger_tfda_violations"]) for r in sweep_main.values())
    print(f"\n⚠️ DANGER-PATH INVARIANT (TFDA-indication → safety top-5) across ALL local-tier "
          f"weights: {total_tfda_viol} violations  {'✅ HOLDS' if total_tfda_viol == 0 else '❌ VIOLATED'}")
    print(f"\n{'local_tier':>10} {'weight':>7} {'set_chg_rate':>13} {'inversions':>11} "
          f"{'local→topk':>11} {'local←topk':>11} {'tfda_viol':>10}")
    for lt in LOCAL_TIER_SWEEP:
        r = sweep_main[lt]
        ent = sum(r["local_entered_topk_by_cat"].values())
        lft = sum(r["local_left_topk_by_cat"].values())
        print(f"{('T'+str(lt)):>10} {r['local_tier_weight']:>7} {str(r['set_change_rate']):>13} "
              f"{r['inversions_total']:>11} {ent:>11} {lft:>11} {len(r['danger_tfda_violations']):>10}")
    print("\nlocal-as-study alt (tier 4 + source_weight 1.0):")
    if local_as_study:
        ent = sum(local_as_study["local_entered_topk_by_cat"].values())
        lft = sum(local_as_study["local_left_topk_by_cat"].values())
        print(f"  set_chg_rate={local_as_study['set_change_rate']} inversions={local_as_study['inversions_total']} "
              f"local→topk={ent} local←topk={lft} tfda_viol={len(local_as_study['danger_tfda_violations'])}")
    print("\nReview→tier sensitivity (does Review=T2 vs T4 change anything at local=T2?):")
    for rt, sw in (("T4", sweep_main), ("T2", sweep_reviewT2)):
        r = sw[2]
        print(f"  Review={rt}: set_chg_rate={r['set_change_rate']} inversions={r['inversions_total']}")
    print(f"\nsaved: {out_path}")
    return 0 if total_tfda_viol == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
