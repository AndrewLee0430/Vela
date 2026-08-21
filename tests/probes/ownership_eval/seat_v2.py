"""Seat SURVIVAL measurement (v2) — does a seated document reach the answer?

seat_v1 measured POOL MEMBERSHIP only. Every stage after the pool can drop a
seated doc. This measures where it dies.

⚠️ WHY THIS CANNOT BE SIMULATED FROM seat_v1.json ALONE (stated up front):
seat_v1 is DailyMed-ONLY, raw-arm (`result_v1.json`: store=dailymed, arm=raw,
level=pool). The post-pool stages in `retrieve()` operate on the MULTI-SOURCE
merged pool (PubMed + FDA + TFDA + DailyMed). Replaying stages over a
DailyMed-only pool would mean the `[:max_results*4]` = `[:20]` cut NEVER BINDS
(that pool is <=5 docs), producing a trivially optimistic "the seat always
survives". That would be a false result, so this harness performs REAL
multi-source retrieval per query.

METHOD — option (a) of the baton, declared: stages 3 and 4 are REAL model
calls, not simulated, on a RULE-BASED SUBSET (every 5th query by qid over the
sorted 100: Q000, Q005, ... Q095 -> N=20; zero-seat queries are RETAINED as
controls). Retrieval is executed ONCE per query and reused across all
protection variants, so the variants differ only where they are supposed to.

STAGE MIRROR (retriever.py:208-292). Every stage that has a real function
CALLS THAT FUNCTION — `_apply_year_boost`, `_cut_exemption`,
`_filter_by_relevance`, `reranker.rerank`, `rank_by_composite_v1`,
`_collapse_subchunks` are all imported and invoked, never reimplemented. Only
the dedup/sort/slice ARITHMETIC is mirrored, line-for-line, from :218-232 and
:292. ⚠️ THIS IS A MIRROR OF retrieve(), NOT retrieve() ITSELF — the same
instrument-blindness class as TECH_DEBT #8. It is unavoidable without
instrumenting api/ (out of scope), and it is declared here rather than hidden.

Run:  python tests/probes/ownership_eval/seat_v2.py
Writes: seat_v2.json
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util as _ilu
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)


def _load(name: str, path: Path):
    spec = _ilu.spec_from_file_location(name, path)
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_bqs = _load("ownership_build_query_set", HERE / "build_query_set.py")
_seat = _load("ownership_seat_measurement", HERE / "seat_measurement.py")
_canary = _load("canary_gate_cfg", ROOT / "tests" / "probes" / "canary" / "canary_gate.py")

SEAT_V1 = HERE / "seat_v1.json"
OUT = HERE / "seat_v2.json"
SUBSET_STRIDE = 5           # every 5th query by qid — rule-based, not cherry-picked
PROTECTIONS = ("P0", "P1", "P2", "P3")
P2_SEAT_CAP = 1             # P2 guarantees at most this many slots


# ── labeling (reuses v1/v2 labelers; non-corpus docs are "other") ──

def make_labeler(corpus_by_sid, key_set_u, whitelist, query_drug):
    def label(doc) -> str:
        sid = getattr(doc, "source_id", "") or ""
        if not sid.startswith("DailyMed:") or "#" not in sid:
            return "other"
        setid = sid.split("DailyMed:", 1)[1].split("#", 1)[0]
        loinc = sid.split("#", 1)[1].split("~", 1)[0]
        cdoc = corpus_by_sid.get((setid, loinc))
        if cdoc is None:
            return "other"
        return _seat.label_doc4(cdoc, key_set_u, whitelist, query_drug)
    return label


def pool_stats(docs, label, seat_ids) -> dict:
    labels = [label(d) for d in docs]
    ids = {getattr(d, "source_id", "") for d in docs}
    return {
        "size": len(docs),
        "owned_in_pool": any(x == "relevant" for x in labels),
        "wrong_object": any(x == "wrong_object" for x in labels),
        "salt_sibling": any(x == "salt_sibling" for x in labels),
        "empty": len(docs) == 0,
        "seated_surviving": len(seat_ids & ids),
    }


def agg_stage(rows: list[dict], n_seats_total: int) -> dict:
    n = len(rows) or 1
    surviving = sum(r["seated_surviving"] for r in rows)
    return {
        "queries": len(rows),
        "owned_in_pool_rate": round(sum(r["owned_in_pool"] for r in rows) / n, 4),
        "wrong_object_rate": round(sum(r["wrong_object"] for r in rows) / n, 4),
        "salt_sibling_rate": round(sum(r["salt_sibling"] for r in rows) / n, 4),
        "empty_rate": round(sum(r["empty"] for r in rows) / n, 4),
        "mean_size": round(sum(r["size"] for r in rows) / n, 4),
        "seated_surviving": surviving,
        "seated_total": n_seats_total,
        "seated_survival_rate": round(surviving / n_seats_total, 4) if n_seats_total else None,
    }


# ── the stage pipeline, mirroring retriever.py:208-292 ──

async def run_stages(r, query, base_docs, seats, protection, label, whitelist,
                     max_results, llm_counter) -> dict:
    """Returns {stage_name: (docs, stats)} for one (query, protection) pair."""
    from api.services.source_weight_shadow import rank_by_composite_v1

    seat_ids = {d.source_id for d in seats}
    stages: dict[str, list] = {}

    # ── P3 normalization, applied BEFORE the sort. It rewrites the SEATED docs'
    # relevance_score only; no non-seated doc is touched and min_score/local_threshold
    # are unchanged — this is a sort-position change, not a threshold change.
    working_seats = [copy.copy(s) for s in seats]
    p3_note = None
    if protection == "P3" and working_seats:
        above = [d.relevance_score for d in base_docs if d.relevance_score >= r.local_threshold]
        if above:
            tie = min(above)
            ordered = sorted(working_seats, key=lambda d: -d.relevance_score)
            for i, d in enumerate(ordered):
                d.relevance_score = tie - (1e-6 * (i + 1))
            p3_note = (f"seated scores rewritten to min(above-floor pool score)={round(tie, 4)} "
                       f"minus 1e-6*rank, preserving order among seats")
        else:
            p3_note = "no above-floor doc in the pool — P3 left scores unchanged"

    # stage 0 — the seeded pool (pool membership; the seat_v1 anchor)
    all_documents = list(base_docs) + list(working_seats)
    stages["stage0_seeded_pool"] = all_documents

    # stage 1 — dedup (:218-223) + year boost (:228) + sort (:231) + cut (:232)
    best: dict[str, int] = {}
    for i, doc in enumerate(all_documents):
        prev = best.get(doc.source_id)
        if prev is None or doc.relevance_score > all_documents[prev].relevance_score:
            best[doc.source_id] = i
    unique_docs = [all_documents[i] for i in sorted(best.values())]
    unique_docs = r._apply_year_boost(unique_docs)
    unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
    cut = unique_docs[:max_results * 4]
    if protection in ("P1", "P2"):
        # seats exempt from the [:max_results*4] cut — additive, mirrors _cut_exemption's shape
        in_cut = {d.source_id for d in cut}
        cut = cut + [d for d in unique_docs if d.source_id in seat_ids and d.source_id not in in_cut]
    stages["stage1_dedup_boost_sort_cut"] = cut

    # stage 2 — _cut_exemption (:237), IMPORTED from production, not reimplemented
    from api.rag.retriever import _cut_exemption
    candidates = _cut_exemption(cut, unique_docs)
    stages["stage2_cut_exemption"] = candidates

    # stage 3 — the LLM relevance filter (:244). REAL CALL.
    llm_counter["filter"] += 1
    relevant = await r._filter_by_relevance(query, candidates)
    stages["stage3_relevance_filter"] = relevant

    # stage 4 — rerank (:258) + composite (:279-281) + sub-chunk collapse (:289). REAL CALL.
    sink: list = []
    if relevant:
        llm_counter["rerank"] += 1
        try:
            documents = await r.reranker.rerank(query, relevant, score_sink=sink)
        except Exception:
            documents = relevant
        if sink:
            documents = rank_by_composite_v1(sink)
        documents = r._collapse_subchunks(documents)
    else:
        documents = []
    stages["stage4_rerank_composite_collapse"] = documents

    # stage 5 — the final slice (:292)
    final = documents[:max_results]
    if protection == "P2":
        # guarantee up to P2_SEAT_CAP seat slots: if a seat survived to stage 4 but fell
        # outside the slice, promote it, evicting the lowest-ranked non-seated doc.
        kept_ids = {d.source_id for d in final}
        promot = [d for d in documents if d.source_id in seat_ids and d.source_id not in kept_ids]
        for d in promot[:P2_SEAT_CAP]:
            non_seat = [x for x in final if x.source_id not in seat_ids]
            if non_seat:
                final = [x for x in final if x.source_id != non_seat[-1].source_id]
            final = final + [d]
    stages["stage5_final_slice"] = final

    return {"stages": stages, "seat_ids": seat_ids, "p3_note": p3_note}


async def main() -> int:
    cfg = _canary.load_production_config()
    max_results = cfg["max_results"]
    floor = cfg["local_threshold"]
    whitelist = _bqs.get_production_whitelist()

    v1 = json.loads(SEAT_V1.read_text(encoding="utf-8"))
    corpus = _bqs.load_corpus()
    corpus_by_sid = {}
    for d in corpus:
        sid = (d.get("setid") or "").strip()
        lo = (d.get("loinc") or "").strip()
        if sid:
            corpus_by_sid[(sid, lo)] = d

    qs = json.loads((HERE / "query_set_v1.json").read_text(encoding="utf-8"))
    by_qid = {q["qid"]: q for q in qs["queries"]}
    s1_by_qid = {r["qid"]: r for r in v1["variants"]["S1"]["per_query"]}

    all_qids = sorted(s1_by_qid)
    subset = [q for i, q in enumerate(all_qids) if i % SUBSET_STRIDE == 0]
    print(f"subset rule: every {SUBSET_STRIDE}th qid of {len(all_qids)} -> N={len(subset)}", flush=True)

    from api.rag.retriever import HybridRetriever
    from api.database.vector_store import get_dailymed_store
    from api.server import _annotate_research_question

    r = HybridRetriever(
        local_threshold=cfg["local_threshold"], enable_local=cfg["enable_local"],
        enable_pubmed=cfg["enable_pubmed"], enable_fda=cfg["enable_fda"],
        enable_tfda=cfg["enable_tfda"], enable_dailymed=cfg["enable_dailymed"],
    )
    store = get_dailymed_store()
    llm_counter = {"rewrite": 0, "filter": 0, "rerank": 0}
    t0 = time.perf_counter()

    from api.models.schemas import SourceType

    async def real_pool(query_text: str):
        """Mirror of retrieve() Steps 1-2 (retriever.py:176-215) -> flat all_documents."""
        rewritten = await r._rewrite_query(query_text)
        llm_counter["rewrite"] += 1
        dm_queries = await r._dailymed_union_queries(query_text, k=3)
        llm_counter["rewrite"] += 3
        tasks = []
        for rq in rewritten:
            if r.enable_pubmed:
                tasks.append(r._search_pubmed(rq, max_results))
            if r.enable_fda:
                tasks.append(r._search_fda(rq, max_results))
            if r.enable_tfda and r.tfda_store:
                tasks.append(r._search_tfda(rq, max_results))
        for dq in dm_queries:
            if r.enable_dailymed and r.dailymed_store:
                tasks.append(r._search_dailymed(dq, max_results))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        docs = []
        for res in results:
            if isinstance(res, list):
                docs.extend(res)
        return docs

    async def seats_for(query_text: str, key_set_u: set) -> list:
        """The S1 seat: OWNED whitelisted-safety docs BELOW the floor, top-K by cosine,
        built by the store's own code path (search with min_score=0.0)."""
        wide = await store.search(query=query_text, n_results=200, min_score=0.0)
        out = []
        for d in wide:
            sid = d.source_id or ""
            if "#" not in sid:
                continue
            setid = sid.split("DailyMed:", 1)[-1].split("#", 1)[0]
            lo = sid.split("#", 1)[1].split("~", 1)[0]
            cdoc = corpus_by_sid.get((setid, lo))
            if cdoc is None:
                continue
            moi = (cdoc.get("moiety") or "").upper().strip()
            if moi in key_set_u and lo in whitelist and d.relevance_score < floor:
                out.append(d)
        return out[:max_results]

    stage_names = ["stage0_seeded_pool", "stage1_dedup_boost_sort_cut", "stage2_cut_exemption",
                   "stage3_relevance_filter", "stage4_rerank_composite_collapse",
                   "stage5_final_slice"]
    per_stage = {p: {s: [] for s in stage_names} for p in PROTECTIONS}
    per_stage_i1 = {p: {s: [] for s in stage_names} for p in PROTECTIONS}
    seats_total = {p: 0 for p in PROTECTIONS}
    seats_total_i1 = {p: 0 for p in PROTECTIONS}
    cut_detail, displaced, per_query_out = [], {p: [] for p in PROTECTIONS}, []

    for n, qid in enumerate(subset, 1):
        q = by_qid[qid]
        query_text = q["query"]
        key_set_u = {k.upper() for k in q["key_set"]}
        qdrug = q["key_used"]
        label = make_labeler(corpus_by_sid, key_set_u, whitelist, qdrug)

        annotated = _annotate_research_question(query_text)
        base_docs = await real_pool(annotated)
        seats = await seats_for(query_text, key_set_u)
        print(f"  [{n}/{len(subset)}] {qid} pool={len(base_docs)} seats={len(seats)}", flush=True)

        # THE :292 QUESTION — measured on the honest P0 ordering
        merged = list(base_docs) + list(seats)
        merged_sorted = sorted(merged, key=lambda d: -d.relevance_score)
        seat_ids = {d.source_id for d in seats}
        positions = [i for i, d in enumerate(merged_sorted) if d.source_id in seat_ids]
        cut_detail.append({
            "qid": qid, "pool_size_before_seat": len(base_docs), "n_seats": len(seats),
            "seat_sort_positions": positions,
            "seats_outside_cut_20": sum(1 for p in positions if p >= max_results * 4),
            "seats_outside_final_5": sum(1 for p in positions if p >= max_results),
        })

        qrec = {"qid": qid, "query": query_text, "n_seats": len(seats),
                "pool_size": len(base_docs), "protections": {}}

        for i1 in (False, True):
            pool_in = base_docs
            if i1:
                pool_in = [d for d in base_docs if label(d) != "wrong_object"]
            for p in PROTECTIONS:
                res = await run_stages(r, annotated, pool_in, seats, p, label, whitelist,
                                       max_results, llm_counter)
                tgt = per_stage_i1 if i1 else per_stage
                tot = seats_total_i1 if i1 else seats_total
                tot[p] += len(seats)
                for sname in stage_names:
                    tgt[p][sname].append(pool_stats(res["stages"][sname], label, res["seat_ids"]))
                if not i1:
                    fin = res["stages"]["stage5_final_slice"]
                    s4 = res["stages"]["stage4_rerank_composite_collapse"]
                    fin_ids = {d.source_id for d in fin}
                    for d in s4:
                        if d.source_id not in fin_ids:
                            displaced[p].append({"qid": qid, "label": label(d),
                                                 "source_id_kind": ("dailymed" if
                                                 (d.source_id or "").startswith("DailyMed:")
                                                 else "other-source")})
                    qrec["protections"][p] = {
                        "stage5_size": len(fin),
                        "seated_surviving_stage5": len(res["seat_ids"] & fin_ids),
                        "p3_note": res["p3_note"],
                    }
        per_query_out.append(qrec)

    # ── canary tension ──
    canary_rows = []
    moieties = sorted({(d.get("moiety") or "").upper().strip() for d in corpus} - {""})
    import re as _re
    pats = {m: _re.compile(r"(?<![a-z0-9])" + _re.escape(m.lower()) + r"(?![a-z0-9])")
            for m in moieties}
    for cid, cq in _canary.CANARIES:
        hits = [m for m in moieties if pats[m].search(cq.lower())]
        hits = [h for h in hits if not any(h != o and pats[h].search(o.lower()) for o in hits)]
        row = {"id": cid, "query": cq, "resolver_hits": hits, "resolves": bool(hits)}
        if hits:
            ks = set(hits)
            owned_safety = [d for d in corpus
                            if (d.get("moiety") or "").upper().strip() in ks
                            and (d.get("loinc") or "").strip() in whitelist]
            row["owned_safety_docs_in_corpus"] = len(owned_safety)
            seats = await seats_for(cq, ks)
            row["seat_would_inject"] = len(seats)
            row["seat_docs"] = [{"moiety": corpus_by_sid.get(
                ((d.source_id or "").split("DailyMed:", 1)[-1].split("#", 1)[0],
                 (d.source_id or "").split("#", 1)[1].split("~", 1)[0]), {}).get("moiety"),
                "loinc": (d.source_id or "").split("#", 1)[1].split("~", 1)[0],
                "score": round(d.relevance_score, 4)} for d in seats]
            row["BREAKS_CANARY"] = len(seats) > 0
        else:
            row["owned_safety_docs_in_corpus"] = 0
            row["seat_would_inject"] = 0
            row["seat_docs"] = []
            row["BREAKS_CANARY"] = False
        canary_rows.append(row)
        print(f"  canary {cid}: resolves={row['resolves']} hits={row['resolver_hits']} "
              f"seat_would_inject={row['seat_would_inject']}", flush=True)

    wall = round(time.perf_counter() - t0, 1)
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip()

    def _dist(rows_):
        out = {}
        for x in rows_:
            out[x["label"]] = out.get(x["label"], 0) + 1
        return out

    result = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "git_head": git_head,
        "base": "seat_v1.json (query set + seat definition); MULTI-SOURCE pools retrieved fresh",
        "scope_note": (
            "seat_v1 is DailyMed-ONLY / raw-arm. The post-pool stages operate on the "
            "MULTI-SOURCE merged pool, so replaying stages over seat_v1's pools would make "
            "the [:max_results*4] cut never bind and would report a false 'always survives'. "
            "This harness therefore performs REAL multi-source retrieval per query."),
        "config": cfg,
        "subset": {"rule": f"every {SUBSET_STRIDE}th qid of the sorted 100 "
                           f"(zero-seat queries RETAINED as controls)",
                   "n": len(subset), "qids": subset},
        "method_per_stage": {
            "stage3": {"mode": "REAL", "detail": "api/rag/retriever._filter_by_relevance called "
                                                 "for real (one LLM call per query per variant)"},
            "stage4": {"mode": "REAL", "detail": "Reranker.rerank called for real, then "
                                                 "rank_by_composite_v1 + _collapse_subchunks"},
            "mirror_caveat": (
                "Stages are a MIRROR of retrieve():208-292, not retrieve() itself. Every stage "
                "with a real function calls it (_apply_year_boost, _cut_exemption, "
                "_filter_by_relevance, rerank, rank_by_composite_v1, _collapse_subchunks); only "
                "the dedup/sort/slice arithmetic is mirrored line-for-line. This is the "
                "instrument-blindness class of TECH_DEBT #8, unavoidable without instrumenting "
                "api/ (out of scope), and declared rather than hidden."),
            "reranker_on_below_floor_docs": (
                "NOT derivable from code: Reranker.rerank OVERWRITES relevance_score with its "
                "own 0-100/100 score (api/rag/reranker.py:248) and sorts by it, so a seated "
                "doc's below-floor cosine is ERASED at stage 4. Whether the LLM reranker scores "
                "a seated safety section highly is a model behaviour, measured here, not "
                "predicted."),
        },
        "stages": {p: {s: agg_stage(per_stage[p][s], seats_total[p]) for s in stage_names}
                   for p in PROTECTIONS},
        "protections": {p: {"stage5": agg_stage(per_stage[p]["stage5_final_slice"], seats_total[p]),
                            "displaced_from_stage4_to_5": {"total": len(displaced[p]),
                                                           "label_distribution": _dist(displaced[p])}}
                        for p in PROTECTIONS},
        "combined_with_I1_stage5": {
            p: agg_stage(per_stage_i1[p]["stage5_final_slice"], seats_total_i1[p])
            for p in PROTECTIONS},
        "cut_question": {
            "note": "the :232 [:max_results*4] cut and the :292 [:max_results] slice, measured "
                    "on the honest P0 ordering over the REAL multi-source pool",
            "per_query": cut_detail,
            "totals": {
                "seats": sum(c["n_seats"] for c in cut_detail),
                "seats_outside_cut_20": sum(c["seats_outside_cut_20"] for c in cut_detail),
                "seats_outside_final_5": sum(c["seats_outside_final_5"] for c in cut_detail),
            },
        },
        "canary_tension": canary_rows,
        "per_query": per_query_out,
        "self_refutation": {
            "i1_circularity": ("wrong_object -> 0 under I1 is TAUTOLOGICAL at EVERY stage, "
                               "because I1's rule IS the labeler's rule. Only the seat metrics "
                               "and what I1 removes are non-tautological."),
            "p3_is_not_a_threshold_change": (
                "P3 rewrites the relevance_score of SEATED docs only, to min(above-floor pool "
                "score) - 1e-6*rank. No non-seated doc is touched; min_score/local_threshold "
                "are unchanged; the store still returns exactly what it returned."),
            "non_dailymed_docs_are_other": (
                "PubMed/FDA/TFDA docs carry no moiety and label as 'other'; they are never "
                "counted as owned or wrong_object."),
        },
        "cost": {"wall_clock_s": wall, "llm_calls": dict(llm_counter),
                 "llm_calls_total": sum(llm_counter.values()),
                 "note": "rewrite calls include the k=3 DailyMed union fan-out per query"},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 78)
    hdr = ("stage", "owned", "wrong", "salt", "empty", "size", "seats")
    for p in PROTECTIONS:
        print(f"\n--- {p} ---")
        print(("{:>34}" + "{:>9}" * 6).format(*hdr))
        for s in stage_names:
            a = result["stages"][p][s]
            print(f"{s:>34}{a['owned_in_pool_rate']:>9}{a['wrong_object_rate']:>9}"
                  f"{a['salt_sibling_rate']:>9}{a['empty_rate']:>9}{a['mean_size']:>9}"
                  f"{str(a['seated_surviving']) + '/' + str(a['seated_total']):>9}")
    t = result["cut_question"]["totals"]
    print(f"\n:292 QUESTION — seats={t['seats']} · outside [:20]={t['seats_outside_cut_20']} "
          f"· outside [:5]={t['seats_outside_final_5']}")
    print(f"CANARY: {[ (c['id'], c['BREAKS_CANARY']) for c in canary_rows ]}")
    print(f"cost: {wall}s, {sum(llm_counter.values())} LLM calls {llm_counter}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
