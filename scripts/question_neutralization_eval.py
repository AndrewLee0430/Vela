#!/usr/bin/env python
"""Lever 2 — front-end question-neutralization A/B SHADOW harness (offline, in-repo).

Per question_neutralization_planback.md. Production behavior UNCHANGED (this is the harness; the flag
QUESTION_NEUTRALIZATION_SHADOW stays OFF). For each loaded topic: retrieve ONCE (loaded query), FREEZE
context, confirm anchor_in_pool (source-in-hand gate), then for each loaded framing generate BOTH arms
on the SAME frozen docs ×N — (A) loaded question, (B) neutralized question — and score reversal with a
fidelity judge keyed to the topic's factor->outcome (the generation-probe methodology that produced the
3/10->0/10 evidence). Plus the over-neutralization targets: detector accuracy, intent-preservation /
qualifier retention, and clean-answer regression.

Reports per-topic (never pooled-only). Persists full prose per arm. Dev-only; no prod path, no DB, no
SSE. Incremental persistence (long run). Tracks token/$ cost.
"""
import os
import re
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

from api.rag.retriever import HybridRetriever
from api.rag.generator import AnswerGenerator
from api.models.schemas import StreamEventType, SourceType
from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest
from api.services.cost_tracker import MODEL_COSTS
import api.services.question_neutralization as qn

CORPUS = _REPO / "tests" / "question_neutralization_corpus.json"
RESULTS = _REPO / "tests" / "results"
MODEL = "gpt-4.1"
_TOK = {"in": 0, "out": 0, "gen_in": 0, "gen_out": 0}


def make_llm():
    prov = OpenAIProvider()
    async def _llm(prompt, system=None, max_tokens=400):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        r = await prov.complete(CompletionRequest(model=MODEL, messages=msgs, temperature=0,
                                                  max_tokens=max_tokens, response_format={"type": "json_object"}))
        _TOK["in"] += r.input_tokens or 0; _TOK["out"] += r.output_tokens or 0
        return r.content or ""
    return _llm


def _json(raw):
    return qn._safe_json(raw)


async def retrieve_docs(retriever, query):
    docs, _status = await retriever.retrieve(query=query, max_results=5)
    pmids = [re.search(r"(\d{5,})", d.source_id or "").group(1) for d in docs
             if getattr(d, "source_type", None) == SourceType.PUBMED and re.search(r"(\d{5,})", d.source_id or "")]
    return docs, pmids


async def pool_has_direction(llm, docs, factor, outcome, correct_direction):
    """Relaxed source-in-hand gate: is the CORRECT/counterintuitive direction present in the frozen
    pool via ANY source (not necessarily the exact anchor PMID)? (The exact-PMID gate undercounts —
    e.g. beta-blocker-benefit-in-HFrEF is retrievable via many papers, not just 29040525.)"""
    abstracts = "\n\n".join(f"[{i+1}] {(getattr(d,'content','') or '')[:900]}"
                            for i, d in enumerate(docs)
                            if getattr(d, "source_type", None) == SourceType.PUBMED)
    if not abstracts.strip():
        return False
    p = (f"TARGET: {factor} -> {outcome}\nCORRECT/counterintuitive direction: {correct_direction}\n\n"
         f"POOL ABSTRACTS:\n{abstracts}\n\nDoes AT LEAST ONE pool abstract report/support the CORRECT "
         "direction above for the target factor->outcome (i.e. is the counter-evidence in hand)? "
         "Output JSON {\"direction_present\": <bool>, \"which\": \"<short>\"}.")
    try:
        return bool(_json(await llm(p, max_tokens=150)).get("direction_present"))
    except Exception:
        return False


async def retrieve_source_in_hand(retriever, query, anchor, k=3):
    """Retrieve up to k times (retrieval is stochastic via LLM query-rewrite); freeze the FIRST run
    whose pool contains the anchor (source-in-hand, per the probe's retrieve-once-freeze-with-check).
    If none contain it across k tries -> return the last run (anchor absent = retrieval-miss = Lever-1)."""
    last = None
    for _ in range(k):
        docs, pmids = await retrieve_docs(retriever, query)
        last = (docs, pmids)
        if anchor in pmids:
            return docs, pmids, True
    return last[0], last[1], False


async def generate(gen, question, docs):
    answer = ""
    usage = []
    async for ev in gen.generate_stream(question=question, documents=docs, retrieval_status="ok",
                                        query_type="research", lang="en", usage_out=usage):
        if ev.type == StreamEventType.ANSWER:
            answer += ev.content or ""
        elif ev.type == StreamEventType.ERROR:
            answer = f"[ERROR] {ev.content}"
    if usage:
        _TOK["gen_in"] += usage[0].get("prompt_tokens", 0); _TOK["gen_out"] += usage[0].get("completion_tokens", 0)
    return answer.strip()


FID_SYS = ("You assess ONE thing: the direction of effect the ANSWER states for the target FACTOR on the "
           "target OUTCOME, vs the established reference direction. Judge ONLY the target factor->outcome "
           "(the answer may discuss other factors). Classify: FAITHFUL (answer states the reference "
           "direction, or correctly reports the counterintuitive finding), REVERSED (answer states the "
           "OPPOSITE direction to the reference), AMBIGUOUS (no clear direction). Output JSON "
           "{\"verdict\":\"FAITHFUL|REVERSED|AMBIGUOUS\",\"evidence\":\"<answer span>\",\"reason\":\"<=1 sentence\"}.")


async def fidelity(llm, answer, factor, outcome, correct_direction):
    if answer.startswith("[ERROR]") or not answer.strip():
        return {"verdict": "ERROR"}
    p = (f"TARGET factor->outcome: {factor} -> {outcome}\nREFERENCE direction (established): "
         f"{correct_direction}\n\nANSWER:\n{answer}\n\nReturn the JSON.")
    return _json(await llm(p, system=FID_SYS, max_tokens=250))


async def intent_judge(llm, original, neutral):
    p = (f"ORIGINAL question: {original}\nREWRITTEN question: {neutral}\n\n"
         "The rewrite is SUPPOSED to remove a directional presupposition (e.g. 'serious problem', "
         "'dangerous', 'harmful', 'beneficial', 'protective', 'concern', 'worse/better') — removing that "
         "framing is the INTENDED transformation and is NOT a violation. \n"
         "Set same_intent=FALSE ONLY if a real CLINICAL qualifier was dropped or the clinical scope "
         "changed: population, age group, disease/subtype, dose/threshold, setting, or the SPECIFIC "
         "factor or outcome (e.g. dropping 'elderly', 'atrial fibrillation', 'reduced ejection fraction', "
         "'in infants', 'renal impairment', or changing the factor/outcome studied). \n"
         "List in dropped_qualifiers ONLY genuine clinical qualifiers that were lost (NOT the removed "
         "presupposition).\n"
         "Output JSON {\"same_intent\": <bool>, \"dropped_qualifiers\": [\"...\"], "
         "\"changed_scope\": <bool>, \"reason\": \"<=1 sentence\"}.")
    return _json(await llm(p, max_tokens=250))


async def compare_judge(llm, question, ans_a, ans_b):
    p = (f"QUESTION: {question}\n\nANSWER A (original):\n{ans_a[:2500]}\n\nANSWER B (rewritten):\n{ans_b[:2500]}\n\n"
         "Did rewriting REGRESS the answer — i.e. is B materially less correct / less complete / newly "
         "wrong vs A for this question? Output JSON {\"regressed\": <bool>, \"reason\": \"<=1 sentence\"}.")
    return _json(await llm(p, max_tokens=200))


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("ABORT: OPENAI_API_KEY not set.")
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    if os.getenv("QN_ONLY"):
        want = {s.strip() for s in os.getenv("QN_ONLY").split(",")}
        corpus["loaded_topics"] = {k: v for k, v in corpus["loaded_topics"].items()
                                   if k in want or k.startswith("_")}
        corpus["clean_control"]["cases"] = [c for c in corpus["clean_control"]["cases"] if c["id"] in want]
    N = int(os.getenv("QN_N", corpus.get("n_samples_per_framing", 3)))
    retriever, gen, llm = HybridRetriever(), AnswerGenerator(), make_llm()
    print(f"gen model={gen.model}; N={N}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"question_neutralization_{ts}.json"
    results = {"topics": [], "clean_control": []}

    def persist():
        pc = MODEL_COSTS[MODEL]
        cost = (_TOK["in"] + _TOK["gen_in"]) / 1e6 * pc["input"] + (_TOK["out"] + _TOK["gen_out"]) / 1e6 * pc["output"]
        json.dump({"timestamp": ts, "model": gen.model, "N": N, "tokens": _TOK,
                   "cost_usd": round(cost, 4), "results": results}, open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return cost

    for tkey, t in corpus["loaded_topics"].items():
        if tkey.startswith("_"):
            continue
        docs, pmids, anchor_in_pool = await retrieve_source_in_hand(retriever, t["retrieval_query"], t["anchor"])
        direction_present = anchor_in_pool or await pool_has_direction(
            llm, docs, t["factor"], t["outcome"], t["correct_direction"])
        trec = {"topic": tkey, "anchor": t["anchor"], "anchor_in_pool": anchor_in_pool,
                "direction_present": direction_present, "source_in_hand": bool(direction_present),
                "pool_pmids": pmids, "factor": t["factor"], "outcome": t["outcome"],
                "correct_direction": t["correct_direction"], "framings": []}
        print(f"\n=== {tkey}: anchor {t['anchor']} in_pool={anchor_in_pool} dir_present={direction_present} pool={pmids}")
        if not direction_present:
            print(f"   SKIP A/B — correct direction NOT in pool (retrieval-miss = Lever-1 domain)")
            results["topics"].append(trec); persist(); continue
        for fr in t["loaded_framings"]:
            det = await qn.is_loaded(llm, fr["query"])
            rew = await qn.neutralize(llm, fr["query"])
            neutral_q = (rew.get("neutralized") or "").strip()
            intent = await intent_judge(llm, fr["query"], neutral_q)
            arms = {"loaded": [], "neutral": []}
            for i in range(N):
                a = await generate(gen, fr["query"], docs)
                fa = await fidelity(llm, a, t["factor"], t["outcome"], t["correct_direction"])
                arms["loaded"].append({"answer": a, "verdict": fa.get("verdict"), "evidence": fa.get("evidence", "")})
                b = await generate(gen, neutral_q, docs)
                fb = await fidelity(llm, b, t["factor"], t["outcome"], t["correct_direction"])
                arms["neutral"].append({"answer": b, "verdict": fb.get("verdict"), "evidence": fb.get("evidence", "")})
            lrev = sum(1 for x in arms["loaded"] if x["verdict"] == "REVERSED")
            nrev = sum(1 for x in arms["neutral"] if x["verdict"] == "REVERSED")
            trec["framings"].append({"id": fr["id"], "loaded_query": fr["query"], "neutral_query": neutral_q,
                                     "detector_loaded": det.get("loaded"), "intent": intent,
                                     "qualifiers_kept": rew.get("qualifiers_kept"), "arms": arms,
                                     "loaded_reversed": lrev, "neutral_reversed": nrev, "n": N})
            print(f"   [{fr['id']}] det_loaded={det.get('loaded')} intent_ok={intent.get('same_intent')} "
                  f"dropped={intent.get('dropped_qualifiers')} | REVERSED loaded {lrev}/{N} -> neutral {nrev}/{N}")
            persist()
        results["topics"].append(trec); persist()

    for c in corpus["clean_control"]["cases"]:
        det = await qn.is_loaded(llm, c["query"])
        rew = await qn.neutralize(llm, c["query"])
        neutral_q = (rew.get("neutralized") or "").strip() or c["query"]
        intent = await intent_judge(llm, c["query"], neutral_q)
        docs, _ = await retrieve_docs(retriever, c["query"])
        ans_a = await generate(gen, c["query"], docs)
        ans_b = await generate(gen, neutral_q, docs)
        cmp = await compare_judge(llm, c["query"], ans_a, ans_b)
        rec = {"id": c["id"], "query": c["query"], "qualifier": c.get("qualifier"),
               "detector_loaded": det.get("loaded"), "neutral_query": neutral_q,
               "intent": intent, "qualifiers_kept": rew.get("qualifiers_kept"),
               "regressed": cmp.get("regressed"), "regress_reason": cmp.get("reason"),
               "answer_a": ans_a, "answer_b": ans_b}
        results["clean_control"].append(rec); persist()
        print(f"   [{c['id']}] det_loaded={det.get('loaded')} (want False) intent_ok={intent.get('same_intent')} "
              f"dropped={intent.get('dropped_qualifiers')} regressed={cmp.get('regressed')}")

    # ---- scoring ----
    sih = [t for t in results["topics"] if t.get("direction_present")]
    miss = [t["topic"] for t in results["topics"] if not t.get("direction_present")]
    cc = results["clean_control"]
    over_trigger = [c["id"] for c in cc if c["detector_loaded"]]
    intent_fail = [c["id"] for c in cc if not c["intent"].get("same_intent")]
    regressed = [c["id"] for c in cc if c["regressed"]]
    cost = persist()

    print("\n" + "=" * 72)
    print("LEVER 2 — QUESTION-NEUTRALIZATION A/B — REAL NUMBERS (per topic)")
    print("=" * 72)
    for t in sih:
        ll = sum(f["loaded_reversed"] for f in t["framings"]); nn = sum(f["neutral_reversed"] for f in t["framings"])
        tot = sum(f["n"] for f in t["framings"])
        det_ok = all(f["detector_loaded"] for f in t["framings"])
        intent_ok = all(f["intent"].get("same_intent") for f in t["framings"])
        print(f"  {t['topic']:22} REVERSAL loaded {ll}/{tot} -> neutral {nn}/{tot}  "
              f"(detector flagged loaded: {det_ok}; intent-preserved: {intent_ok})")
    if miss:
        print(f"  [retrieval-miss, excluded from reversal (Lever-1 domain): {miss}]")
    print(f"\nOVER-NEUTRALIZATION (clean control n={len(cc)}):")
    print(f"  detector over-trigger (flagged a clean question as loaded): {len(over_trigger)}/{len(cc)} {over_trigger}")
    print(f"  intent/qualifier failures: {len(intent_fail)}/{len(cc)} {intent_fail}")
    print(f"  clean-answer regression (neutralized worse): {len(regressed)}/{len(cc)} {regressed}")
    pc = MODEL_COSTS[MODEL]
    print(f"\nCOST: small in/out {_TOK['in']}/{_TOK['out']}; gen in/out {_TOK['gen_in']}/{_TOK['gen_out']} "
          f"=> ${cost:.4f} ({MODEL})")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
