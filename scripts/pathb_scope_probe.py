#!/usr/bin/env python
"""Path B STAGE 2 — scope-mapping for B1 term-expansion. Maps the CEILING of Path B: B1's recovery
coverage across DIFFERENT miss-types (not just the clean-synonym kind obesity exemplifies). Standalone
diagnostic — NO build, no flags, no server changes, no production synonym table.

Frozen candidate set (miss-type labelled BEFORE running):
  T-A clean-synonym (lay->measurement; the anchor uses a measurement/technical term) — EXPECT B1 recover:
    obesity (37290898, "Body mass index..."), sodium/salt (25119607, "Urinary sodium...").
  T-B non-synonym (missed for a reason OTHER than terminology — minority/harm side, named-trial) —
    EXPECT B1 struggle: intensive-glucose/ACCORD (18539917), antiarrhythmics/CAST (1900101).
Clean controls (retrieve correctly at baseline) for the over-expansion FP-analog:
    polypharmacy (35268461), beta-blockers-HFrEF (29040525), peanut-LEAP (25705822).

STEP 0 gates each case: a miss-case is only valid if its anchor is actually MISSED at baseline; a
clean control only if its anchor is IN final at baseline. Reuses scripts/pathb_recall_probe._pipeline.
Token-instrumented (stage-1 gap). Dev-only.
"""
import asyncio, sys, json, time
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

# --- token instrumentation (monkeypatch the provider before any retriever is built) ---
import api.providers.openai_provider as _op
from api.providers.base import CompletionRequest
from api.providers.factory import get_lightweight_provider
from api.services.cost_tracker import MODEL_COSTS
_EMBED_COST = {"input": 0.02, "output": 0.0}  # text-embedding-3-small, per 1M tokens
_TOK = {"by_model": {}, "embed_tokens": 0}
_oc = _op.OpenAIProvider.complete
async def _tc(self, req):
    r = await _oc(self, req)
    m = _TOK["by_model"].setdefault(req.model, {"in": 0, "out": 0})
    m["in"] += r.input_tokens or 0; m["out"] += r.output_tokens or 0
    return r
_op.OpenAIProvider.complete = _tc
_oe = _op.OpenAIProvider.embed
async def _te(self, req):
    r = await _oe(self, req); _TOK["embed_tokens"] += r.input_tokens or 0; return r
_op.OpenAIProvider.embed = _te

from api.data_sources.pubmed import PubMedClient
from api.rag.retriever import HybridRetriever
from scripts.pathb_recall_probe import _pipeline, _pmid

RESULTS_DIR = _REPO / "tests" / "results"
REPS = 2

MISS_CASES = [
    {"id": "obesity", "miss_type": "clean-synonym", "anchor": "37290898",
     "query": "Why is obesity a serious problem that worsens survival in patients with heart failure?",
     "b1": ["body mass index survival heart failure", "obesity overweight BMI mortality prognosis heart failure",
            "body mass index outcomes patients heart failure"]},
    {"id": "sodium", "miss_type": "clean-synonym", "anchor": "25119607",
     "query": "Is very low salt intake good for the heart?",
     "b1": ["dietary sodium urinary sodium excretion cardiovascular mortality",
            "low sodium salt intake cardiovascular events mortality",
            "urinary sodium potassium excretion cardiovascular outcomes"]},
    {"id": "glucose_accord", "miss_type": "non-synonym", "anchor": "18539917",
     "query": "What are the benefits of intensive glucose control in type 2 diabetes?",
     "b1": ["intensive glycemic control HbA1c tight glucose lowering mortality type 2 diabetes",
            "intensive glucose lowering cardiovascular mortality diabetes",
            "glycemic control HbA1c targets all-cause mortality diabetes"]},
    {"id": "cast", "miss_type": "non-synonym", "anchor": "1900101",
     "query": "Why is suppressing PVCs with antiarrhythmic drugs after a heart attack beneficial?",
     "b1": ["encainide flecainide cardiac arrhythmia suppression mortality myocardial infarction",
            "class I antiarrhythmic drugs premature ventricular contractions mortality myocardial infarction",
            "antiarrhythmic ventricular arrhythmia suppression mortality after MI"]},
]
CLEAN_CONTROLS = [
    {"id": "polypharmacy", "anchor": "35268461",
     "query": "What are the clinical outcomes of polypharmacy in elderly patients with atrial fibrillation?",
     "b1": ["polypharmacy multiple medications five or more drugs elderly atrial fibrillation",
            "medication count elderly atrial fibrillation clinical outcomes mortality",
            "polypharmacy concurrent medications elderly AF outcomes"]},
    {"id": "beta_blockers_hfref", "anchor": "29040525",
     "query": "What is the effect of beta-blockers on mortality in heart failure with reduced ejection fraction?",
     "b1": ["beta-blockers beta adrenergic antagonists mortality heart failure reduced ejection fraction",
            "beta blocker therapy HFrEF all-cause mortality randomized trials",
            "beta-adrenergic blockade reduced ejection fraction heart failure survival"]},
    {"id": "peanut_leap", "anchor": "25705822",
     "query": "What is the effect of early dietary peanut introduction on the risk of peanut allergy in infants?",
     "b1": ["early peanut introduction consumption infants peanut allergy prevention",
            "dietary peanut exposure infancy peanut hypersensitivity risk",
            "early allergen introduction peanut allergy infants"]},
]
SELECTION_CRITERION = ("Span miss-TYPES, not more clean-synonym topics: T-A clean-synonym (lay->measurement, "
                       "anchor uses the measurement term) as positive control; T-B non-synonym (missed for a "
                       "reason other than terminology). Each anchor verified to the correct paper; each case "
                       "gated by a CONFIRMED baseline miss (STEP 0). B1 expansion = lay concept -> measurement/"
                       "MeSH/clinical synonyms, same rule each case.")


def _cost():
    c = 0.0
    for model, t in _TOK["by_model"].items():
        pc = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        c += t["in"] / 1e6 * pc["input"] + t["out"] / 1e6 * pc["output"]
    c += _TOK["embed_tokens"] / 1e6 * _EMBED_COST["input"]
    return c


async def reps(r, query, rewritten_fn, anchor):
    pool_hits = final_hits = 0
    runs = []
    for _ in range(REPS):
        rewritten = await rewritten_fn()
        pool, final = await _pipeline(r, query, rewritten)
        ip, ifi = anchor in pool, anchor in final
        pool_hits += ip; final_hits += ifi
        runs.append({"rewritten": rewritten, "in_pool": ip, "in_final": ifi, "pool_size": len(pool)})
        time.sleep(0.4)
    return {"pool": f"{pool_hits}/{REPS}", "final": f"{final_hits}/{REPS}",
            "pool_hits": pool_hits, "final_hits": final_hits, "runs": runs}


async def gate1():
    b = get_lightweight_provider()
    try:
        rr = await b.provider.complete(CompletionRequest(model=b.model,
            messages=[{"role": "user", "content": "ping"}], temperature=0, max_tokens=5))
    except Exception as e:
        print(f"GATE1 DEAD: {type(e).__name__}: {str(e)[:160]}"); sys.exit(2)
    if not (rr.content or "").strip() or (rr.content or "").startswith("[ERROR]"):
        print("GATE1 DEAD"); sys.exit(3)
    print(f"GATE1 HEALTHY: {b.model} -> {rr.content.strip()!r}\n")


async def main():
    await gate1()
    r = HybridRetriever()
    pubmed = PubMedClient()
    RESULTS_DIR.mkdir(exist_ok=True)
    out = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "reps": REPS,
           "selection_criterion": SELECTION_CRITERION, "miss_cases": [], "clean_controls": []}

    # verify anchor titles (STEP 0 prerequisite)
    allp = [c["anchor"] for c in MISS_CASES + CLEAN_CONTROLS]
    titles = {a.pmid: a.title for a in await pubmed.fetch_details(allp)}

    print("=== MISS CASES (STEP 0: confirm baseline miss, then B1) ===")
    for c in MISS_CASES:
        base = await reps(r, c["query"], lambda c=c: r._rewrite_query(c["query"]), c["anchor"])
        confirmed_miss = base["final_hits"] == 0      # anchor not in final at baseline
        rec = {**c, "anchor_title": titles.get(c["anchor"], "?"), "baseline": base,
               "confirmed_miss": confirmed_miss}
        if confirmed_miss:
            b1 = await reps(r, c["query"], lambda c=c: _const(c["b1"]), c["anchor"])
            rec["B1"] = b1
            rec["recovered"] = b1["final_hits"] > 0
            print(f"  [{c['id']:14}] {c['miss_type']:14} MISS-confirmed | baseline F {base['final']} "
                  f"-> B1 pool {b1['pool']} F {b1['final']}  recovered={rec['recovered']}")
        else:
            rec["B1"] = None; rec["recovered"] = None
            print(f"  [{c['id']:14}] {c['miss_type']:14} NOT-missed at baseline (F {base['final']}) -> DROPPED")
        out["miss_cases"].append(rec); _persist(out)

    print("\n=== CLEAN CONTROLS (over-expansion FP-analog) ===")
    for c in CLEAN_CONTROLS:
        base = await reps(r, c["query"], lambda c=c: r._rewrite_query(c["query"]), c["anchor"])
        valid = base["final_hits"] > 0                # retrieves correctly at baseline
        rec = {**c, "anchor_title": titles.get(c["anchor"], "?"), "baseline": base, "valid_control": valid}
        if valid:
            b1 = await reps(r, c["query"], lambda c=c: _const(c["b1"]), c["anchor"])
            rec["B1"] = b1
            rec["degraded"] = b1["final_hits"] < base["final_hits"]   # B1 pushed the good anchor out
            print(f"  [{c['id']:18}] baseline F {base['final']} -> B1 F {b1['final']}  degraded={rec['degraded']}")
        else:
            rec["B1"] = None; rec["degraded"] = None
            print(f"  [{c['id']:18}] NOT in final at baseline (F {base['final']}) -> invalid control, DROPPED")
        out["clean_controls"].append(rec); _persist(out)

    # ---- aggregate by miss-type ----
    confirmed = [c for c in out["miss_cases"] if c["confirmed_miss"]]
    by_type = {}
    for c in confirmed:
        b = by_type.setdefault(c["miss_type"], {"n": 0, "recovered": 0, "ids": []})
        b["n"] += 1; b["recovered"] += int(bool(c["recovered"])); b["ids"].append(c["id"])
    valid_ctrls = [c for c in out["clean_controls"] if c["valid_control"]]
    degraded = [c["id"] for c in valid_ctrls if c["degraded"]]
    out["summary"] = {"by_miss_type": by_type,
                      "dropped_not_missed": [c["id"] for c in out["miss_cases"] if not c["confirmed_miss"]],
                      "over_expansion": {"degraded": len(degraded), "valid_controls": len(valid_ctrls), "ids": degraded}}
    cost = _cost(); out["cost_usd"] = round(cost, 4); out["tokens"] = _TOK
    _persist(out)

    print("\n" + "=" * 70)
    print("PATH B SCOPE — B1 RECOVERY BY MISS-TYPE (the headline)")
    print("=" * 70)
    for mt, b in by_type.items():
        print(f"  {mt:16}: recovered {b['recovered']}/{b['n']}  {b['ids']}")
    if out["summary"]["dropped_not_missed"]:
        print(f"  (dropped — no baseline miss: {out['summary']['dropped_not_missed']})")
    print(f"OVER-EXPANSION (clean controls): degraded {len(degraded)}/{len(valid_ctrls)} {degraded}")
    print(f"COST: ${cost:.4f}  (by_model={ {m: (t['in'],t['out']) for m,t in _TOK['by_model'].items()} }, "
          f"embed_tokens={_TOK['embed_tokens']})")
    fp = RESULTS_DIR / f"pathb_scope_probe_{out['timestamp']}.json"
    json.dump(out, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Saved -> {fp}")


async def _const(lst):
    return lst


def _persist(out):
    fp = RESULTS_DIR / f"pathb_scope_probe_{out['timestamp']}.json"
    json.dump(out, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
