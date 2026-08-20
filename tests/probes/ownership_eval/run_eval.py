"""Ownership-anchored retrieval eval harness v1 — runner.

Scope (founder ruling 2026-08-20): DailyMed store ONLY · raw arm ONLY (no LLM
rewrite) · pool-level metrics ONLY. Zero LLM calls; the only paid call is the
query embedding inside the store's own search().

SCOPE GUARDS (hard):
- Does NOT construct HybridRetriever. Calls the production store function
  directly: `await get_dailymed_store().search(q, n_results, min_score)`
  (api/database/vector_store.py:60-123) — the real pool-construction code path
  (embed → cosine → sort → min_score break → n_results cutoff), not a mirror.
- min_score / n_results are READ FROM THE PRODUCTION SOURCE at runtime
  (api/server.py HybridRetriever(local_threshold=…) and retrieve(max_results=
  body.max_results or N), cross-checked against api/rag/retriever.py's
  retrieve() default). NO literals here; parse failure or mismatch = loud stop.
- One embedding per query: the store's `_get_embedding` is memo-wrapped so
  search() and the full-corpus scan use THE SAME vector. The full-corpus scan
  reuses the store's in-memory matrix (label_emb.npy as loaded by the store,
  float16→float32) with search()'s exact cosine formula — same numbers.

SMOKE GATE (Rule 21): WD01 must reproduce ACECLOFENAC in-pool with the owned
DURLAZA doc ABSENT and its best-in-corpus score ≈0.40 (recorded raw-arm value
0.4031, TECH_DEBT "#13 probe" note). Disagreement with the recorded 12/12 stops
the run — the harness would be wrong, not the record.

Run:  python tests/probes/ownership_eval/run_eval.py
Reads: query_set_v1.json · data/dailymed/label_docs.json (via the store)
Writes: tests/probes/ownership_eval/result_v1.json
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The store's load-status print()s carry emoji (vector_store.py:235/:237 — the
# recorded cp950 console class, TECH_DEBT queue #9). Reconfigure THIS process's
# stdio to UTF-8 so the harness survives on a cp950 console; no api/ change.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Provider credentials — same convention as tests/probes/c2/_c2_ab_retrieval.py:27-28.
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

# sibling module loaded by file path so cwd never matters
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("ownership_build_query_set", HERE / "build_query_set.py")
_bqs = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bqs)

QUERY_SET = HERE / "query_set_v1.json"
OUT = HERE / "result_v1.json"
WRONGDRUG_FIXTURES = ROOT / "tests" / "probes" / "wrongdrug" / "fixtures.json"

# The c2-recorded omeprazole query, verbatim (tests/probes/c2/c2_ab_retrieval.json:597).
C2_OMEPRAZOLE_QUERY = "omeprazole contraindications and warnings"


# ─────────────────── production parameters: parsed, never hardcoded ───────────────────

def load_production_params() -> tuple[float, int, dict]:
    """(min_score, n_results, provenance). Loud failure on parse miss or mismatch."""
    server_src = (ROOT / "api" / "server.py").read_text(encoding="utf-8")
    retriever_src = (ROOT / "api" / "rag" / "retriever.py").read_text(encoding="utf-8")

    m_thr = re.search(r"HybridRetriever\(\s*\n?\s*local_threshold=([0-9.]+)", server_src)
    if not m_thr:
        raise SystemExit("LOUD STOP: could not parse local_threshold from api/server.py")
    min_score = float(m_thr.group(1))

    m_thr_def = re.search(r"local_threshold:\s*float\s*=\s*([0-9.]+)", retriever_src)
    if not m_thr_def:
        raise SystemExit("LOUD STOP: could not parse local_threshold default from api/rag/retriever.py")
    if float(m_thr_def.group(1)) != min_score:
        raise SystemExit(
            f"LOUD STOP: local_threshold mismatch — server.py {min_score} vs "
            f"retriever.py default {m_thr_def.group(1)}; re-derive before trusting the harness"
        )

    m_n_srv = re.search(r"max_results=body\.max_results\s+or\s+(\d+)", server_src)
    m_n_def = re.search(r"max_results:\s*int\s*=\s*(\d+)", retriever_src)
    if not (m_n_srv and m_n_def):
        raise SystemExit("LOUD STOP: could not parse production max_results (server.py / retriever.py)")
    if m_n_srv.group(1) != m_n_def.group(1):
        raise SystemExit(
            f"LOUD STOP: max_results mismatch — server.py fallback {m_n_srv.group(1)} vs "
            f"retrieve() default {m_n_def.group(1)}"
        )
    n_results = int(m_n_srv.group(1))
    prov = {
        "min_score_source": "api/server.py HybridRetriever(local_threshold=…), cross-checked retriever.py default",
        "n_results_source": "api/server.py retrieve(max_results=body.max_results or N), cross-checked retrieve() default",
    }
    return min_score, n_results, prov


# ─────────────────── metrics helpers ───────────────────

def ndcg_at_k(labels: list[str], r_corpus: int, k: int) -> float:
    """Two-level gain (relevant=1, else 0). IDCG over min(k, R_corpus) ideal hits."""
    dcg = sum(1.0 / math.log2(i + 2) for i, lab in enumerate(labels[:k]) if lab == "relevant")
    ideal_hits = min(k, r_corpus)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return (dcg / idcg) if idcg > 0 else 0.0


# ─────────────────── the run ───────────────────

async def evaluate_query(store, sid_to_doc, q, key_set, whitelist, min_score, n_results,
                         corpus_docs) -> dict:
    query = q["query"]
    # ONE embedding per query: memo-wrapped _get_embedding (set up in main()).
    q_emb = await store._get_embedding(query)
    pool = await store.search(query=query, n_results=n_results, min_score=min_score)

    # full-corpus cosine, search()'s exact formula over the store's own matrix
    import numpy as np
    norms = np.linalg.norm(store.embeddings, axis=1)
    q_norm = np.linalg.norm(q_emb)
    scores = store.embeddings @ q_emb / (norms * q_norm + 1e-10)
    order = np.argsort(scores)[::-1]

    key_set_u = {k.upper() for k in key_set}
    r_corpus = sum(1 for d in corpus_docs
                   if (d.get("moiety") or "").upper().strip() in key_set_u)

    best_rel = None
    best_rel_safety = None
    for rank_all, idx in enumerate(order):
        d = corpus_docs[int(idx)]
        if (d.get("moiety") or "").upper().strip() in key_set_u:
            s = float(scores[int(idx)])
            row = {
                "score": round(s, 4),
                "overall_rank": int(rank_all),
                "setid": d.get("setid"),
                "loinc": d.get("loinc"),
                "title": d.get("title"),
                "shortfall_vs_min_score": round(min_score - s, 4),
            }
            if best_rel is None:
                best_rel = row
            if best_rel_safety is None and (d.get("loinc") or "").strip() in whitelist:
                best_rel_safety = row
            if best_rel is not None and best_rel_safety is not None:
                break

    top_idx = int(order[0])
    top_doc = corpus_docs[top_idx]
    corpus_top1 = {
        "score": round(float(scores[top_idx]), 4),
        "moiety": top_doc.get("moiety"),
        "loinc": top_doc.get("loinc"),
        "title": top_doc.get("title"),
    }

    pool_rows, labels = [], []
    for rank, rd in enumerate(pool):
        doc = sid_to_doc.get(rd.source_id)
        if doc is None:
            lab, moiety, setid, loinc, title = "unresolved", None, None, None, rd.title
        else:
            lab = _bqs.label_doc(doc, key_set_u, whitelist)
            moiety, setid = doc.get("moiety"), doc.get("setid")
            loinc, title = doc.get("loinc"), doc.get("title")
        labels.append(lab)
        pool_rows.append({
            "rank": rank, "score": round(float(rd.relevance_score), 4),
            "setid": setid, "moiety": moiety, "loinc": loinc,
            "title": title, "label": lab,
        })

    first_rel = next((i for i, lab in enumerate(labels) if lab == "relevant"), None)
    return {
        **{k: q[k] for k in ("qid", "drug_id", "key_set", "key_used", "template", "query", "scope") if k in q},
        "pool": pool_rows,
        "n_pool": len(pool_rows),
        "r_corpus": r_corpus,
        "has_relevant": first_rel is not None,
        "first_relevant_rank": first_rel,
        "rr": (1.0 / (first_rel + 1)) if first_rel is not None else 0.0,
        "has_wrong_object": any(lab == "wrong_object" for lab in labels),
        "wrong_object_at_rank1": bool(labels and labels[0] == "wrong_object"),
        "ndcg5": round(ndcg_at_k(labels, r_corpus, 5), 4),
        "best_corpus_relevant": best_rel,
        "best_corpus_relevant_safety": best_rel_safety,
        "corpus_top1": corpus_top1,
    }


def aggregate(records: list[dict]) -> dict:
    n = len(records)
    return {
        "n_queries": n,
        "owned_in_pool_rate": round(sum(r["has_relevant"] for r in records) / n, 4),
        "mrr": round(sum(r["rr"] for r in records) / n, 4),
        "wrong_object_in_pool_rate": round(sum(r["has_wrong_object"] for r in records) / n, 4),
        "wrong_object_at_rank1_rate": round(sum(r["wrong_object_at_rank1"] for r in records) / n, 4),
        "empty_pool_rate": round(sum(1 for r in records if r["n_pool"] == 0) / n, 4),
        "mean_ndcg5": round(sum(r["ndcg5"] for r in records) / n, 4),
    }


def self_refutation(records: list[dict], key_sets_by_qid: dict) -> dict:
    rel_samples, wo_samples, contains_but_wrong = [], [], []
    empty_key_sets = [r["qid"] for r in records if not r.get("key_set")]
    for r in records:
        for row in r["pool"]:
            if row["label"] == "relevant" and len(rel_samples) < 5:
                rel_samples.append({"qid": r["qid"], "query": r["query"],
                                    "moiety": row["moiety"], "title": row["title"]})
            if row["label"] == "wrong_object":
                if len(wo_samples) < 5:
                    wo_samples.append({"qid": r["qid"], "query": r["query"],
                                       "moiety": row["moiety"], "title": row["title"]})
                key = (r.get("key_used") or "").upper()
                if key and key in (row["moiety"] or "").upper():
                    contains_but_wrong.append({
                        "qid": r["qid"], "key_used": r["key_used"],
                        "moiety": row["moiety"], "title": row["title"],
                        "note": "expected salt/combination case — listed, NOT relabeled",
                    })
    return {
        "relevant_samples": rel_samples,
        "wrong_object_samples": wo_samples,
        "empty_key_set_queries": empty_key_sets,
        "moiety_contains_key_but_wrong_object": contains_but_wrong,
    }


async def main() -> int:
    min_score, n_results, prov = load_production_params()
    whitelist = _bqs.get_production_whitelist()
    qs = json.loads(QUERY_SET.read_text(encoding="utf-8"))
    corpus_docs = _bqs.load_corpus()
    key_sets = _bqs.build_key_sets(corpus_docs)

    from api.database.vector_store import get_dailymed_store
    store = get_dailymed_store()
    if store.embeddings is None or len(store.documents) != len(corpus_docs):
        raise SystemExit("LOUD STOP: store failed to load or store/corpus doc counts differ")

    # ONE embedding per query — memo-wrap the store's own embedder so search()
    # and the full-corpus scan share the identical vector. In-memory only.
    orig_embed = store._get_embedding
    cache: dict = {}

    async def memo_embed(text: str):
        if text not in cache:
            cache[text] = await orig_embed(text)
        return cache[text]

    store._get_embedding = memo_embed  # type: ignore[method-assign]

    sid_to_doc = {}
    for d in store.documents:
        sid = d.get("source_id")
        if sid in sid_to_doc:
            raise SystemExit(f"LOUD STOP: duplicate source_id in corpus: {sid}")
        sid_to_doc[sid] = d

    # ── smoke set (separate from the 100; WD03 out_of_scope by design) ──
    fixtures = json.loads(WRONGDRUG_FIXTURES.read_text(encoding="utf-8"))["fixtures"]
    fx = {f["id"]: f for f in fixtures}
    smoke_defs = [
        {"qid": "SMK-WD01", "query": fx["WD01"]["query"],
         "key_set": fx["WD01"]["owner_moieties"], "scope": "smoke"},
        {"qid": "SMK-WD02", "query": fx["WD02"]["query"],
         "key_set": fx["WD02"]["owner_moieties"], "scope": "smoke"},
        {"qid": "SMK-OMEP", "query": C2_OMEPRAZOLE_QUERY,
         "key_set": sorted(key_sets.get("OMEPRAZOLE", set())), "scope": "smoke"},
        {"qid": "SMK-WD03", "query": fx["WD03"]["query"],
         "key_set": fx["WD03"]["owner_moieties"], "scope": "out_of_scope",
         "out_of_scope_reason": "pair/interaction fixture — unclassified by design "
                                "(owner_assertion decision (b)-i); excluded from every rate"},
    ]
    smoke_records = []
    for sd in smoke_defs:
        if sd["scope"] == "out_of_scope":
            smoke_records.append({**sd, "pool": None, "note": "not run against rates"})
            continue
        if not sd["key_set"]:
            raise SystemExit(f"LOUD STOP: smoke {sd['qid']} has an EMPTY key set")
        rec = await evaluate_query(store, sid_to_doc, sd, set(sd["key_set"]),
                                   whitelist, min_score, n_results, corpus_docs)
        smoke_records.append(rec)

    # ── SMOKE GATE, encoding the recorded RAW-ARM facts (gate corrected 2026-08-20).
    # The baton phrased the gate as "ACECLOFENAC in pool" — that is the FULL-PIPELINE
    # observation (rewrite arm + rerank; the 12/12). On the RAW arm the record says the
    # opposite and the harness must agree with THAT record:
    #   · "0 hits above min_score=0.6 for the whole DailyMed store" — 0/4608
    #     (docs/c2_phase1b_measurement_20260804.md:214, independently confirmed
    #     2026-08-06, TECH_DEBT '#13 probe' note) → the raw WD01 pool is EMPTY;
    #   · ACECLOFENAC — Contraindications is the corpus TOP-1 overall for the query,
    #     BELOW the floor (0.5787) — the doc the rewrite arm lifts into the pool 12/12;
    #   · the owned DURLAZA — Contraindications (34070-3) sits at ≈0.4031 / rank 500
    #     (TECH_DEBT:935) — the shortfall the reserved-seat measurement needs.
    # Diagnostic verified before this encoding: all three reproduced to 4 decimals.
    wd01 = next(r for r in smoke_records if r["qid"] == "SMK-WD01")
    top1 = wd01["corpus_top1"]
    safety = wd01["best_corpus_relevant_safety"]
    gate = {
        "raw_pool_empty_as_recorded_0_of_4608": wd01["n_pool"] == 0,
        "corpus_top1_is_aceclofenac_contraindications_below_floor": (
            top1["moiety"] == "ACECLOFENAC" and top1["loinc"] == "34070-3"
            and top1["score"] < min_score
        ),
        "corpus_top1_score": top1["score"],
        "owned_safety_doc": (safety or {}).get("title"),
        "owned_safety_score": (safety or {}).get("score"),
        "owned_safety_score_in_band_0.35_0.45": (
            safety is not None and 0.35 <= safety["score"] <= 0.45
        ),
        "best_any_section_owned_score": (wd01["best_corpus_relevant"] or {}).get("score"),
    }
    if not (gate["raw_pool_empty_as_recorded_0_of_4608"]
            and gate["corpus_top1_is_aceclofenac_contraindications_below_floor"]
            and gate["owned_safety_score_in_band_0.35_0.45"]):
        OUT.write_text(json.dumps({"SMOKE_GATE_FAILED": gate, "wd01": wd01},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        raise SystemExit(f"LOUD STOP: smoke gate failed — the harness disagrees with "
                         f"the recorded raw-arm evidence: {gate}")

    # ── the 100-pair sampled set ──
    records = []
    for q in qs["queries"]:
        rec = await evaluate_query(store, sid_to_doc, q, set(q["key_set"]),
                                   whitelist, min_score, n_results, corpus_docs)
        records.append(rec)
        if len(records) % 20 == 0:
            print(f"  …{len(records)}/{len(qs['queries'])}")

    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip()
    result = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "git_head": git_head,
        "seed": qs["seed"],
        "store": "dailymed",
        "arm": "raw",
        "level": "pool",
        "min_score": min_score,
        "n_results": n_results,
        "param_provenance": prov,
        "corpus_docs": len(corpus_docs),
        "eligible_drugs": qs["eligible_drugs"],
        "multi_key_sets": qs["multi_key_sets"],
        "embedding_calls": len(cache),
        "queries": records,
        "aggregate": aggregate(records),
        "smoke": {"records": smoke_records, "wd01_gate": gate},
        "self_refutation": self_refutation(records, {}),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    agg = result["aggregate"]
    print(json.dumps(agg, indent=2))
    print(f"smoke WD01 gate: {gate}")
    sr = result["self_refutation"]
    print(f"self-refutation: {len(sr['relevant_samples'])} relevant + "
          f"{len(sr['wrong_object_samples'])} wrong_object samples; "
          f"empty key sets: {sr['empty_key_set_queries']}; "
          f"contains-but-wrong: {len(sr['moiety_contains_key_but_wrong_object'])}")
    print(f"embedding calls: {len(cache)}  |  wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
