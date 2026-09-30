"""STEP 3 — full Research pipeline trace, N=5 real retrieve() calls + ONE generation.

ZERO api/ change. Observation is by INSTANCE-level wrappers installed on this harness's
own HybridRetriever object (each wrapper calls the original and records its args/return
— behaviour is unchanged) plus a logging.Handler on `api.rag.retriever` for the
[CutExempt] / [FilterExempt] lines production already emits.

Per run it records: rewrites · DailyMed union set · every source call's returned docs ·
merged pool (pre-cut, deduped, year-boosted) · the [:max_results*4] cut · filter in /
LLM-kept / FilterExempt re-adds / dropped · rerank output · final top_k.

Sub-threshold cosines: each DailyMed query embedding is captured at the store's
`_get_embedding` (no extra API call) and scored locally against the shipped
label_emb.npy, so WATCH docs that never cleared the 0.6 floor still get a score + rank.

Generation (run 1 only): the real AnswerGenerator.generate_stream on run 1's documents,
authenticated path (model_override=None — an anonymous L0 request would use the
generator's fallback model instead; the incident's tier is not known). The exact
system + user prompt is rebuilt with the generator's own helpers and saved.
"""
import asyncio
import json
import logging
import re
import time
from pathlib import Path

import numpy as np

from _harness import QUERY, assert_dev_db, production_retriever

HERE = Path(__file__).resolve().parent
# Defaults reproduce the probe-1 artifact names. The Segment-1 TREATMENT run passes
# `--n 2 --prefix step6_treatment` so the committed control (step3_trace.json) is never
# overwritten.
import argparse  # noqa: E402
_ap = argparse.ArgumentParser()
_ap.add_argument("--n", type=int, default=5)
_ap.add_argument("--prefix", default="step3")
# Segment 1b STEP A (2026-09-30): generate for EVERY run, not only run 1; per-run answers are written
# as {prefix}_answer_run{i}.md and per-run veto regexes recorded (hand-read stays the instrument for veto i).
_ap.add_argument("--gen-all", action="store_true")
_ARGS = _ap.parse_args()
N = _ARGS.n
OUT = HERE / f"{_ARGS.prefix}_trace.json"
ANSWER_OUT = HERE / f"{_ARGS.prefix}_answer_run1.md"

WATCH_MOIETY = {
    # thiazide side (derived key set, step1)
    "HYDROCHLOROTHIAZIDE": "thiazide", "INDAPAMIDE": "thiazide", "METOLAZONE": "thiazide",
    # calcium / vit-D side (step1 reverse key set, minus CALCIUM SENNOSIDES — a laxative)
    "CALCIUM": "calcium", "CALCIUM ACETATE": "calcium", "CALCIUM CARBONATE": "calcium",
    "CALCIUM CHLORIDE DIHYDRATE": "calcium", "CALCIUM GLUCONATE": "calcium",
    "CHOLECALCIFEROL": "vitD", "CALCITRIOL": "vitD", "PARICALCITOL": "vitD",
    # the WRONG reading: calcium-channel blockers
    "AMLODIPINE": "ccb", "NIFEDIPINE": "ccb", "DILTIAZEM": "ccb", "VERAPAMIL HCL": "ccb",
    "FELODIPINE": "ccb",
}
SAFETY = {"34073-7", "43685-7", "34070-3", "34066-1"}


def d2(doc, score=None):
    st = getattr(doc.source_type, "value", doc.source_type)
    return {"source_id": doc.source_id, "source_type": st, "title": (doc.title or "")[:140],
            "score": round(float(doc.relevance_score if score is None else score), 4)}


class Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, rec):
        if isinstance(rec.msg, str) and rec.msg.startswith(("[CutExempt]", "[FilterExempt]",
                                                             "Relevance filter", "[SOURCE_WEIGHT",
                                                             "Rerank failed", "Retrieved ")):
            self.lines.append(rec.getMessage())


def instrument(r, rec):
    """Install observation-only wrappers on THIS retriever instance."""
    orig_rw = r._rewrite_query

    async def rw(q):
        out = await orig_rw(q)
        rec["rewrite_calls"].append(out)
        return out
    r._rewrite_query = rw

    for name in ("_search_pubmed", "_search_fda", "_search_dailymed", "_search_tfda"):
        orig = getattr(r, name)

        def mk(orig, name):
            async def w(q, n):
                out = await orig(q, n)
                rec["source_calls"].append({"fn": name, "query": q, "docs": [d2(d) for d in out]})
                return out
            return w
        setattr(r, name, mk(orig, name))

    # The DailyMed store is a process SINGLETON (get_dailymed_store), so it must be
    # wrapped ONCE; the wrapper records into whichever rec is CURRENT. The first
    # version re-wrapped it per run and runs 2-5 hit the previous run's popped key
    # ("DailyMed search error: '_dm_emb'") — documented in README "Harness defect".
    store = r.dailymed_store
    if not getattr(store, "_bp_wrapped", False):
        orig_emb = store._get_embedding

        async def emb(text):
            e = await orig_emb(text)
            store._bp_current["_dm_emb"].append((text, e))
            return e
        store._get_embedding = emb
        store._bp_wrapped = True
    store._bp_current = rec

    orig_f = r._filter_by_relevance

    async def filt(q, docs):
        rec["filter_in"] = [d2(d) for d in docs]
        out = await orig_f(q, docs)
        rec["filter_out"] = [d2(d) for d in out]
        return out
    r._filter_by_relevance = filt

    orig_rr = r.reranker.rerank

    async def rr(q, docs, score_sink=None):
        out = await orig_rr(q, docs, score_sink=score_sink)
        rec["rerank_out"] = [d2(d) for d in out]
        rec["rerank_pool"] = [d2(d, s) for d, s in (score_sink or [])]
        return out
    r.reranker.rerank = rr


def cosine_table(store, embs):
    """WATCH docs: cosine per DailyMed query + best rank, from the shipped embeddings."""
    E = store.embeddings
    En = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-10)
    docs = store.documents
    watch_idx = [i for i, d in enumerate(docs) if d.get("moiety") in WATCH_MOIETY]
    per_q = []
    for text, e in embs:
        s = En @ (e / (np.linalg.norm(e) + 1e-10))
        order = np.argsort(-s)
        rank = np.empty_like(order)
        rank[order] = np.arange(len(order))
        per_q.append({"query": text,
                      "n_above_0.6": int((s >= 0.6).sum()),
                      "top5": [{"source_id": docs[i]["source_id"], "title": docs[i]["title"][:90],
                                "cos": round(float(s[i]), 4)} for i in order[:5]],
                      "watch": sorted([{"source_id": docs[i]["source_id"], "moiety": docs[i]["moiety"],
                                        "class": WATCH_MOIETY[docs[i]["moiety"]],
                                        "loinc": docs[i]["loinc"], "cos": round(float(s[i]), 4),
                                        "rank": int(rank[i])} for i in watch_idx],
                                      key=lambda x: -x["cos"])})
    return per_q


async def main():
    dev = assert_dev_db()
    r, cfg = production_retriever()
    from api.server import _annotate_research_question
    question = _annotate_research_question(QUERY)
    assert question == QUERY, "English query must pass through the CJK-gated annotator unchanged"

    cap = Cap()
    logging.getLogger("api.rag.retriever").addHandler(cap)
    logging.getLogger("api.rag.retriever").setLevel(logging.DEBUG)

    # A fresh production-config retriever per run, so each run's wrappers record into
    # their own dict (the wrappers close over `rec`).
    runs = []
    run_docs = []
    first_docs = first_status = None
    for i in range(N):
        r, _ = production_retriever()
        rec = {"run": i + 1, "rewrite_calls": [], "source_calls": [], "_dm_emb": []}
        instrument(r, rec)
        cap.lines = []
        t0 = time.perf_counter()
        docs, status = await r.retrieve(query=question, max_results=cfg["max_results"],
                                        source_filter=None,
                                        source_weight_active=cfg["source_weight_active"])
        rec["seconds"] = round(time.perf_counter() - t0, 1)
        rec["status"] = status
        rec["final"] = [d2(d) for d in docs]
        rec["log_lines"] = list(cap.lines)
        rec["cosines"] = cosine_table(r.dailymed_store, rec.pop("_dm_emb"))

        # stage accounting
        pool = {}
        for c in rec["source_calls"]:
            for d in c["docs"]:
                if d["source_id"] not in pool or d["score"] > pool[d["source_id"]]["score"]:
                    pool[d["source_id"]] = d
        rec["pool_unique"] = sorted(pool.values(), key=lambda x: -x["score"])
        fin = {d["source_id"] for d in rec.get("filter_in", [])}
        fout = {d["source_id"] for d in rec.get("filter_out", [])}
        fex = []
        for ln in cap.lines:
            if ln.startswith("[FilterExempt]"):
                fex += re.findall(r"'([^']+)'", ln)
        rec["cut_dropped"] = [d for d in rec["pool_unique"] if d["source_id"] not in fin]
        rec["filter_dropped"] = [d for d in rec.get("filter_in", []) if d["source_id"] not in fout]
        rec["filter_exempt_readded"] = fex
        rec["filter_llm_kept"] = [d for d in rec.get("filter_out", []) if d["source_id"] not in fex]
        rrids = {d["source_id"] for d in rec.get("rerank_out", [])}
        rec["rerank_dropped"] = [d for d in rec.get("filter_out", []) if d["source_id"] not in rrids]
        finids = {d["source_id"] for d in rec["final"]}
        rec["topk_dropped"] = [d for d in rec.get("rerank_out", []) if d["source_id"] not in finids]

        dm_any = [d for d in rec["pool_unique"] if d["source_type"] == "dailymed"]
        by_type = {}
        for d in rec["final"]:
            by_type[d["source_type"]] = by_type.get(d["source_type"], 0) + 1
        print(f"[run {i+1}] {rec['seconds']}s status={status} pool={len(pool)} "
              f"dailymed_in_pool={len(dm_any)} filter {len(fin)}->{len(fout)} (exempt {len(fex)}) "
              f"final={by_type}", flush=True)
        for d in rec["final"]:
            print("      FINAL", d["source_type"], d["source_id"], "|", d["title"][:80], flush=True)
        if i == 0:
            first_docs, first_status = docs, status
        run_docs.append((docs, status))
        runs.append(rec)

    # ── generation: run 1 only by default; every run with --gen-all ──
    from api.rag.generator import AnswerGenerator
    from api.models.schemas import SourceType
    gen = AnswerGenerator()

    async def generate_once(docs, status):
        gen_rec = {"retrieval_status": status, "n_docs": len(docs), "lang": "en",
                   "model_override": None, "model": gen.model}
        if docs:
            context = gen._build_context(docs)
            has_tfda = any(getattr(d, "source_type", None) == SourceType.TFDA for d in docs)
            gen_rec["path"] = "GROUNDED (documents present)"
            gen_rec["system_prompt"] = gen._get_system_prompt("research")
            gen_rec["user_prompt"] = gen._build_user_prompt(question, context, "research", "en", has_tfda)
        else:
            gen_rec["path"] = "FALLBACK (no documents) — FALLBACK_PROMPTS['research']"
        answer, events = "", []
        async for ev in gen.generate_stream(question=question, documents=docs,
                                            retrieval_status=status, query_type="research",
                                            lang="en", usage_out=[], model_override=None):
            t = getattr(ev.type, "value", str(ev.type))
            events.append(t)
            if t == "answer":
                answer += ev.content or ""
        gen_rec["events"] = sorted(set(events))
        gen_rec["answer"] = answer
        gen_rec["veto_i_calcium_read_as_ccb"] = bool(re.search(r"calcium[- ]channel", answer, re.I))
        gen_rec["veto_ii_mentions_thiazide_or_hypercalcemia"] = bool(
            re.search(r"thiazide|hydrochlorothiazide|chlorthalidone|hypercalc", answer, re.I))
        return gen_rec

    gen_rec = await generate_once(first_docs, first_status)
    ANSWER_OUT.write_text(gen_rec["answer"], encoding="utf-8")
    if _ARGS.gen_all:
        runs[0]["generation"] = gen_rec
        for k in range(1, len(run_docs)):
            g = await generate_once(*run_docs[k])
            runs[k]["generation"] = g
            (HERE / f"{_ARGS.prefix}_answer_run{k + 1}.md").write_text(g["answer"], encoding="utf-8")
            print(f"[gen run {k+1}] {g['path'][:9]} veto(i)regex={g['veto_i_calcium_read_as_ccb']} "
                  f"veto(ii)={g['veto_ii_mentions_thiazide_or_hypercalcemia']}", flush=True)

    res = {"query": QUERY, "db_branch": dev, "n_runs": N, "gen_all": _ARGS.gen_all,
           "config": {k: v for k, v in cfg.items() if k != "provenance"},
           "config_provenance": cfg.get("provenance"),
           "watch_moieties": WATCH_MOIETY, "runs": runs, "generation_run1": gen_rec}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("veto(i) CCB:", gen_rec["veto_i_calcium_read_as_ccb"],
          "| veto(ii) thiazide/hypercalcemia:", gen_rec["veto_ii_mentions_thiazide_or_hypercalcemia"])


if __name__ == "__main__":
    asyncio.run(main())
