#!/usr/bin/env python
"""C1 (③ direction-checker) SHADOW validation harness (offline, in-repo).

Per C1_shadow_build_planback.md §4 + C1_inrepo_planback.md. Generates the FROZEN live subset
(tests/direction_shadow_corpus.json) IN-PROCESS via the prod code path (retriever.retrieve ->
generator.generate_stream, gpt-4.1, 96806b5 in HEAD), then for each case:
  - ground truth: reuse the gpt-4.1 direction judge (citation_truth_check.judge_direction) over the
    answer's claim-citation pairs -> ground_truth_reversed.
  - C1: run api.services.direction_checker.check() on the FULL abstracts the generator saw
    (RetrievedDocument.content; invariant 2, no re-fetch).
SHADOW: nothing is surfaced; this only logs + persists. Full prose persisted (no counts-only).

Scoring:
  - detection = of TARGETED cases whose answer ACTUALLY reversed (judge), how many C1 flagged.
  - false-positive = of CLEAN-FAITHFUL cases whose answer is faithful (judge), how many C1 flagged.

Dev-only: reads dev .env (OPENAI_API_KEY). No prod, no DB writes, no SSE. Persists after each case.
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

from openai import OpenAI
from api.rag.retriever import HybridRetriever
from api.rag.generator import AnswerGenerator
from api.models.schemas import StreamEventType, SourceType
import api.services.direction_checker as dc
from scripts.citation_truth_check import judge_direction, claim_pairs, ADVERSARIAL

RESULTS_DIR = _REPO / "tests" / "results"
CORPUS = _REPO / "tests" / "direction_shadow_corpus.json"
MAX_PAIRS = 10
MAX_RESULTS = 5


def build_cases() -> list[dict]:
    """Resolve the frozen live-subset IDs -> (id, group, subgroup, query, note)."""
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    live = corpus["live_run_2026-06-17"]
    adv = {c[0]: (c[2], c[3]) for c in ADVERSARIAL}             # id -> (query, note)
    golden = {c["id"]: c for c in json.load(open(_REPO / "tests" / "golden_dataset.json", encoding="utf-8"))}
    lf = json.load(open(_REPO / "tests" / "eval_sets" / "loaded_framing_set.json", encoding="utf-8"))
    lf_clean = {c["id"]: c for t in lf["clean_topics"] for c in t["cases"]}
    lf_hold = {c["id"]: c for c in lf["holdouts"]["cases"]}

    cases: list[dict] = []
    t = live["targeted_detection"]
    for cid in t["adversarial_famous_cohort"]:
        q, note = adv[cid]
        cases.append({"id": cid, "group": "targeted", "subgroup": "adversarial", "query": q, "note": note})
    for cid in t["loaded_framing_clean"]:
        cases.append({"id": cid, "group": "targeted", "subgroup": "lf_clean",
                      "query": lf_clean[cid]["query"], "note": "loaded-framing clean (protective anchor)"})
    c = live["clean_faithful_FP"]
    for cid in c["adversarial_holdout"]:
        q, note = adv[cid]
        cases.append({"id": cid, "group": "clean", "subgroup": "adversarial_holdout", "query": q, "note": note})
    for cid in c["loaded_framing_holdout"]:
        cases.append({"id": cid, "group": "clean", "subgroup": "lf_holdout",
                      "query": lf_hold[cid]["query"], "note": "holdout (intuitive direction)"})
    for cid in c["golden_research_first10"]:
        cases.append({"id": cid, "group": "clean", "subgroup": "golden_research",
                      "query": golden[cid]["query"], "note": "golden research (intuitive clinical)"})
    return cases


async def generate(retriever, gen, query: str):
    """In-process prod path: retrieve -> generate. Returns (answer, citations[dict], documents)."""
    docs, status = await retriever.retrieve(query=query, max_results=MAX_RESULTS)
    answer, citations = "", []
    async for ev in gen.generate_stream(question=query, documents=docs,
                                        retrieval_status=status, query_type="research",
                                        lang="en", usage_out=[]):
        if ev.type == StreamEventType.ANSWER:
            answer += ev.content or ""
        elif ev.type == StreamEventType.CITATIONS:
            citations = [c.model_dump() for c in (ev.content or [])]
        elif ev.type == StreamEventType.ERROR:
            answer = f"[ERROR] {ev.content}"
    return answer.strip(), citations, docs


def ground_truth(oai, query, answer, citations, docs) -> dict:
    """Reuse the gpt-4.1 direction judge over claim-citation pairs (FULL abstract = doc.content)."""
    pmid2 = {}
    for d in docs:
        if getattr(d, "source_type", None) != SourceType.PUBMED:
            continue
        m = re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")
        if m:
            pmid2[m.group(1)] = (d.title, d.content)
    cit_by_id = {int(c["id"]): c for c in citations if "id" in c}
    judged = []
    for pr in claim_pairs(answer, cit_by_id)[:MAX_PAIRS]:
        if pr["pmid"] not in pmid2:
            continue
        title, abstract = pmid2[pr["pmid"]]
        jd = judge_direction(oai, query, pr["claim"], pr["pmid"], title, abstract)
        judged.append({**pr, **jd})
    return {"reversed": any(j.get("direction") == "reversed" for j in judged), "pairs": judged}


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("ABORT: OPENAI_API_KEY not set.")
    RESULTS_DIR.mkdir(exist_ok=True)
    cases = build_cases()
    if os.getenv("DSE_ONLY"):  # smoke: comma-separated IDs
        want = {s.strip() for s in os.getenv("DSE_ONLY").split(",")}
        cases = [c for c in cases if c["id"] in want]
    retriever, gen, oai = HybridRetriever(), AnswerGenerator(), OpenAI()
    llm = dc.make_lightweight_llm()
    print(f"generator model = {gen.model}  | cases = {len(cases)}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"direction_shadow_{ts}.json"
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    results = []

    def persist():
        json.dump({"timestamp": ts, "generator_model": gen.model,
                   "corpus_freeze": "tests/direction_shadow_corpus.json",
                   "live_run": corpus["live_run_2026-06-17"], "results": results},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for i, case in enumerate(cases, 1):
        rec = {**case}
        try:
            answer, citations, docs = await generate(retriever, gen, case["query"])
            rec["answer"] = answer
            rec["citations"] = citations
            rec["doc_pmids"] = [re.search(r"(\d{5,})", d.source_id or "").group(1)
                                for d in docs if getattr(d, "source_type", None) == SourceType.PUBMED
                                and re.search(r"(\d{5,})", d.source_id or "")]
            if answer.startswith("[ERROR]") or not answer:
                rec["status"] = "gen_error"
                results.append(rec); persist()
                print(f"  [{i}/{len(cases)}] {case['id']:9} GEN-ERROR"); continue

            gt = ground_truth(oai, case["query"], answer, citations, docs)
            rec["gt_reversed"] = gt["reversed"]
            rec["gt_pairs"] = gt["pairs"]

            sources = dc.cited_sources_from_documents(docs)
            try:
                flag = await dc.check(llm, answer=answer, question=case["query"], cited_sources=sources)
                rec["c1"] = flag.to_sink_dict()
                rec["c1_flagged"] = flag.flagged
            except Exception as e:
                rec["c1_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                rec["c1_flagged"] = None
            rec["status"] = "ok"
            print(f"  [{i}/{len(cases)}] {case['id']:9} {case['group']:8} "
                  f"gt_rev={rec.get('gt_reversed')} c1_flag={rec.get('c1_flagged')} "
                  f"verdict={rec.get('c1',{}).get('verdict','')}")
        except Exception as e:
            rec["status"] = "harness_error"
            rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  [{i}/{len(cases)}] {case['id']:9} HARNESS-ERROR {rec['error']}")
        results.append(rec); persist()

    # ---- scoring ----
    def sub(group):
        return [r for r in results if r.get("group") == group and r.get("status") == "ok"]
    targeted = sub("targeted")
    clean = sub("clean")
    tgt_rev = [r for r in targeted if r.get("gt_reversed")]            # detection opportunities
    detected = [r for r in tgt_rev if r.get("c1_flagged")]
    missed = [r for r in tgt_rev if r.get("c1_flagged") is False]
    clean_faithful = [r for r in clean if r.get("gt_reversed") is False]  # FP denominator
    fp = [r for r in clean_faithful if r.get("c1_flagged")]

    summary = {
        "n_cases_run": len(results),
        "n_ok": len([r for r in results if r.get("status") == "ok"]),
        "n_gen_error": len([r for r in results if r.get("status") == "gen_error"]),
        "detection": {
            "denominator_gt_reversed_targeted": len(tgt_rev),
            "detected": len(detected), "missed": len(missed),
            "detected_ids": [r["id"] for r in detected],
            "missed_ids": [r["id"] for r in missed],
            "targeted_not_reversed_ids": [r["id"] for r in targeted if not r.get("gt_reversed")],
        },
        "false_positive": {
            "denominator_clean_faithful": len(clean_faithful),
            "fp": len(fp), "fp_ids": [r["id"] for r in fp],
            "clean_excluded_because_judge_reversed": [r["id"] for r in clean if r.get("gt_reversed")],
        },
    }
    json.dump({"timestamp": ts, "generator_model": gen.model,
               "corpus_freeze": "tests/direction_shadow_corpus.json",
               "live_run": corpus["live_run_2026-06-17"], "summary": summary, "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n" + "=" * 64)
    print("C1 SHADOW VALIDATION — REAL NUMBERS (direction-relevant + FP sample)")
    print("=" * 64)
    print(f"DETECTION: C1 flagged {len(detected)}/{len(tgt_rev)} of targeted answers that ACTUALLY "
          f"reversed (judge).  detected={summary['detection']['detected_ids']}  "
          f"MISSED={summary['detection']['missed_ids']}")
    print(f"  (targeted cases that did NOT reverse, no detection opportunity: "
          f"{summary['detection']['targeted_not_reversed_ids']})")
    print(f"FALSE-POSITIVE: C1 flagged {len(fp)}/{len(clean_faithful)} ground-truth-faithful "
          f"clean cases.  FP={summary['false_positive']['fp_ids']}")
    if summary['false_positive']['clean_excluded_because_judge_reversed']:
        print(f"  (clean cases EXCLUDED from FP denom because the judge called them reversed: "
              f"{summary['false_positive']['clean_excluded_because_judge_reversed']})")
    print("\nSCOPE CAVEAT: FP is on a direction-ADJACENT sample (C1's mis-fire rate on the answers it "
          "acts on), NOT a site-wide FP rate. Site-wide needs C1 in shadow over real traffic.")
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
