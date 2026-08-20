"""Ownership eval — reserved-seat + ownership-interception OFFLINE measurement (主線 A #1).

Founder baton 2026-08-20. Builds ON result_v1.json: same 100 sampled queries, same
key sets, same labeler core, same production params (parsed, never hardcoded).
Zero LLM calls; the only paid calls are the ~103 query embeddings (re-computed —
v1 did not persist them). No api/ change, no threshold change, no prod.

FOURTH LABEL (founder ruling 2026-08-20 — salt/ester aliases are NOT merged):
  salt_sibling = moiety ∉ key set AND loinc ∈ safety whitelist AND the moiety,
  after stripping the FIXED suffix list below token-by-token from the END,
  equals the query drug string EXACTLY (whole-token match, not substring).
  wrong_object now EXCLUDES salt_sibling. METHYLTESTOSTERONE must NOT become a
  salt_sibling of testosterone (negative-tested here and in
  tests/test_seat_measurement.py — whole-token equality, never substring).

VARIANTS (all offline simulations over the full-corpus ranked list):
  S0    baseline — above-floor docs, top n_results. MUST equal result_v1.json
        exactly (per-doc equality gate; loud stop on mismatch).
  S1    seat bypasses the min_score FLOOR only: candidate set = above-floor ∪
        owned-safety docs; still cut at n_results by score (a seat can be cut).
  S2cN  seat bypasses floor AND cutoff: the top-N owned-safety docs (by score)
        always occupy slots; remaining slots fill from the normal ABOVE-FLOOR
        ranked list; final pool ordered by score.
  I1    interception — drop pool docs labeled wrong_object (key-based).
        salt_sibling is KEPT. No backfill: the pool shrinks.
  Combos: S1I1, S2c1I1, S2c2I1 = build the seat pool, then apply I1.

CIRCULARITY GUARD (Rule 17): I1's rule IS the labeler's rule, so
wrong_object→0 under I1 is tautological at pool level. What is NOT
tautological and is reported: (a) the full list of docs I1 removes (a human
judges whether cross-drug info was lost), (b) the empty-pool rate after I1,
(c) the seat metrics, which are independent of the labeler.

ENTITY-RESOLUTION HONESTY: this sim assumes the query drug is KNOWN (true by
construction — we generated the queries). A production seat needs a resolver
from free-text query → key set; that resolver's miss rate is the residual
wrong-object rate in production. Not quantified here (out of scope).

Run:  python tests/probes/ownership_eval/seat_measurement.py
Reads: result_v1.json · data/dailymed/label_docs.json (via the store) ·
       tests/probes/wrongdrug/fixtures.json
Writes: tests/probes/ownership_eval/seat_v1.json
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]
BASE = HERE / "result_v1.json"
OUT = HERE / "seat_v1.json"

# ── the FIXED suffix list (founder baton 2026-08-20, verbatim — 17 entries).
# NOT a normalization rule: it feeds ONLY the salt_sibling label, never a merge.
# Embedder re-runs are not bit-deterministic (v1 README); score drift beyond this
# bound — or ANY membership/order/label/metric change — is real disagreement.
S0_SCORE_DRIFT_BOUND = 0.01

SALT_SUFFIXES: tuple[str, ...] = (
    "SULFATE", "SULPHATE", "HYDROCHLORIDE", "HCL", "SODIUM", "POTASSIUM",
    "CALCIUM", "MONOHYDRATE", "DIHYDRATE", "ACETATE", "PROPIONATE",
    "UNDECANOATE", "TARTRATE", "MALEATE", "CITRATE", "MESYLATE", "DEXTRAN",
)
_SUFFIX_SET = frozenset(SALT_SUFFIXES)

# sibling module (import-pure) loaded by file path so cwd never matters
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("ownership_build_query_set", HERE / "build_query_set.py")
_bqs = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bqs)


# ───────────────────────── salt-sibling labeler (pure; DB-free-testable) ─────────────────────────

def strip_salt_suffixes(name: str) -> str:
    """Strip trailing tokens that are in the FIXED list, repeatedly ("ATROPINE
    SULFATE MONOHYDRATE" → "ATROPINE"). Never strips the last remaining token."""
    tokens = " ".join((name or "").upper().split()).split(" ")
    while len(tokens) > 1 and tokens[-1] in _SUFFIX_SET:
        tokens.pop()
    return " ".join(tokens)


def is_salt_sibling(moiety: str, query_drug: str) -> bool:
    """Whole-token equality after suffix-strip of the DOC moiety only — never
    substring (METHYLTESTOSTERONE is one token; it never equals TESTOSTERONE)."""
    m = " ".join((moiety or "").upper().split())
    q = " ".join((query_drug or "").upper().split())
    if not m or not q or m == q:
        return False
    return strip_salt_suffixes(m) == q


def label_doc4(doc: dict, key_set_u: set[str], whitelist, query_drug: str) -> str:
    """relevant / salt_sibling / wrong_object / other. Base rule is the v1
    labeler (reused, not copied); salt_sibling splits OUT of wrong_object."""
    base = _bqs.label_doc(doc, key_set_u, whitelist)
    if base == "wrong_object" and is_salt_sibling(doc.get("moiety") or "", query_drug):
        return "salt_sibling"
    return base


def collapse_to_v1(label: str) -> str:
    return "wrong_object" if label == "salt_sibling" else label


# ───────────────────────── metrics ─────────────────────────

def pool_metrics(labels: list[str], r_corpus: int, ndcg_fn) -> dict:
    first_rel = next((i for i, lab in enumerate(labels) if lab == "relevant"), None)
    return {
        "n_pool": len(labels),
        "has_relevant": first_rel is not None,
        "first_relevant_rank": first_rel,
        "rr": (1.0 / (first_rel + 1)) if first_rel is not None else 0.0,
        "has_wrong_object": any(lab == "wrong_object" for lab in labels),
        "has_salt_sibling": any(lab == "salt_sibling" for lab in labels),
        "wrong_object_at_rank1": bool(labels and labels[0] == "wrong_object"),
        "ndcg5": round(ndcg_fn(labels, r_corpus, 5), 4),
    }


def aggregate(per_query: list[dict]) -> dict:
    n = len(per_query)
    return {
        "n_queries": n,
        "owned_in_pool_rate": round(sum(r["has_relevant"] for r in per_query) / n, 4),
        "mrr": round(sum(r["rr"] for r in per_query) / n, 4),
        "wrong_object_in_pool_rate": round(sum(r["has_wrong_object"] for r in per_query) / n, 4),
        "salt_sibling_in_pool_rate": round(sum(r["has_salt_sibling"] for r in per_query) / n, 4),
        "wrong_object_at_rank1_rate": round(sum(r["wrong_object_at_rank1"] for r in per_query) / n, 4),
        "empty_pool_rate": round(sum(1 for r in per_query if r["n_pool"] == 0) / n, 4),
        "mean_ndcg5": round(sum(r["ndcg5"] for r in per_query) / n, 4),
        "mean_pool_size": round(sum(r["n_pool"] for r in per_query) / n, 4),
    }


# ───────────────────────── the run ─────────────────────────

async def _run() -> int:
    import subprocess
    from datetime import datetime, timezone

    import numpy as np

    # run_eval loaded lazily (it pulls dotenv + the api stack); reuse its
    # param parser and nDCG so nothing is duplicated.
    _rev_spec = _ilu.spec_from_file_location("ownership_run_eval", HERE / "run_eval.py")
    _rev = _ilu.module_from_spec(_rev_spec)
    _rev_spec.loader.exec_module(_rev)

    min_score, n_results, prov = _rev.load_production_params()
    ndcg_fn = _rev.ndcg_at_k
    whitelist = _bqs.get_production_whitelist()

    base = json.loads(BASE.read_text(encoding="utf-8"))
    if base["min_score"] != min_score or base["n_results"] != n_results:
        raise SystemExit("LOUD STOP: production params changed since result_v1.json — "
                         "re-run run_eval.py before the seat measurement")

    corpus_docs = _bqs.load_corpus()

    from api.database.vector_store import get_dailymed_store
    store = get_dailymed_store()
    if store.embeddings is None or len(store.documents) != len(corpus_docs):
        raise SystemExit("LOUD STOP: store failed to load or store/corpus doc counts differ")
    for i in (0, len(corpus_docs) // 2, len(corpus_docs) - 1):
        if store.documents[i].get("source_id") != corpus_docs[i].get("source_id"):
            raise SystemExit("LOUD STOP: store/corpus row alignment broken")

    orig_embed = store._get_embedding
    cache: dict = {}

    async def memo_embed(text: str):
        if text not in cache:
            cache[text] = await orig_embed(text)
        return cache[text]

    store._get_embedding = memo_embed  # type: ignore[method-assign]

    moieties_u = [(d.get("moiety") or "").upper().strip() for d in corpus_docs]
    loinc_ok = [(d.get("loinc") or "").strip() in whitelist for d in corpus_docs]
    norms = np.linalg.norm(store.embeddings, axis=1)

    # negative control, asserted at runtime too (mirrors the DB-free test)
    if is_salt_sibling("METHYLTESTOSTERONE", "TESTOSTERONE"):
        raise SystemExit("LOUD STOP: METHYLTESTOSTERONE classified salt_sibling of TESTOSTERONE")

    # smoke query drugs = the fixtures' queried_moiety (the query drug string)
    fixtures = json.loads((ROOT / "tests" / "probes" / "wrongdrug" / "fixtures.json")
                          .read_text(encoding="utf-8"))["fixtures"]
    fx = {f["id"]: f for f in fixtures}
    smoke_drug = {"SMK-WD01": fx["WD01"]["queried_moiety"],
                  "SMK-WD02": fx["WD02"]["queried_moiety"],
                  "SMK-OMEP": "OMEPRAZOLE"}

    VARIANTS = ("S0", "S1", "S2c1", "S2c2", "I1", "S1I1", "S2c1I1", "S2c2I1")
    per_query: dict[str, list[dict]] = {v: [] for v in VARIANTS}
    displaced: dict[str, list[dict]] = {"S1": [], "S2c1": [], "S2c2": []}
    removed_by_i1: list[dict] = []
    removal_counts: dict[str, dict] = {v: {"removed_docs": 0, "queries_with_removal": 0,
                                           "pools_became_empty": 0} for v in
                                       ("I1", "S1I1", "S2c1I1", "S2c2I1")}
    salt_sibling_pool_docs: list[dict] = []
    s0_drift: list[dict] = []
    magnesium_flips: list[dict] = []
    anykey_delta: list[dict] = []
    queryside_strip_delta: list[dict] = []
    smoke_out: dict[str, dict] = {}

    async def eval_one(qrec: dict, is_smoke: bool) -> None:
        query = qrec["query"]
        key_set_u = {k.upper() for k in qrec["key_set"]}
        qdrug = smoke_drug[qrec["qid"]] if is_smoke else qrec["key_used"]
        r_corpus = qrec["r_corpus"]

        q_emb = await store._get_embedding(query)
        q_norm = np.linalg.norm(q_emb)
        scores = store.embeddings @ q_emb / (norms * q_norm + 1e-10)
        order = np.argsort(scores)[::-1]

        above_floor: list[int] = []       # full above-floor list, score order
        owned_safety: list[int] = []      # owned + whitelisted loinc, score order
        rank_of: dict[int, int] = {}
        for pos, idx_np in enumerate(order):
            idx = int(idx_np)
            rank_of[idx] = pos
            if float(scores[idx]) >= min_score:
                above_floor.append(idx)
            if moieties_u[idx] in key_set_u and loinc_ok[idx]:
                owned_safety.append(idx)

        def lab4(idx: int) -> str:
            return label_doc4(corpus_docs[idx], key_set_u, whitelist, qdrug)

        def rows(pool: list[int], with_title: bool = False) -> list[dict]:
            out = []
            for rank, idx in enumerate(pool):
                d = corpus_docs[idx]
                row = {"rank": rank, "score": round(float(scores[idx]), 4),
                       "overall_rank": rank_of[idx], "setid": d.get("setid"),
                       "moiety": d.get("moiety"), "loinc": d.get("loinc"),
                       "label": lab4(idx)}
                if with_title:
                    row["title"] = d.get("title")
                out.append(row)
            return out

        # ── variant pools (index lists, score order) ──
        s0 = above_floor[:n_results]
        union = set(above_floor) | set(owned_safety)
        s1 = sorted(union, key=lambda i: rank_of[i])[:n_results]

        def s2(cap: int) -> list[int]:
            seats = owned_safety[:cap]
            seat_set = set(seats)
            fill = [i for i in above_floor if i not in seat_set][: n_results - len(seats)]
            return sorted(seats + fill, key=lambda i: rank_of[i])

        pools: dict[str, list[int]] = {"S0": s0, "S1": s1, "S2c1": s2(1), "S2c2": s2(2)}
        pools["I1"] = [i for i in s0 if lab4(i) != "wrong_object"]
        for src, dst in (("S1", "S1I1"), ("S2c1", "S2c1I1"), ("S2c2", "S2c2I1")):
            pools[dst] = [i for i in pools[src] if lab4(i) != "wrong_object"]

        # ── S0 equality gate vs result_v1.json (loud stop). Membership, order,
        # labels and every label-derived metric must match EXACTLY. Scores are
        # compared with a drift bound: the embedder is not bit-deterministic
        # across runs (recorded in the v1 README), so re-embedding can move a
        # score at the 3rd–4th decimal without changing the pool. Every drifted
        # score is RECORDED (both values); drift > the bound, or any membership/
        # label/metric change, is real disagreement and stops the run.
        mine_docs = [(corpus_docs[i].get("setid"), corpus_docs[i].get("loinc")) for i in s0]
        v1_docs = [(p["setid"], p["loinc"]) for p in qrec["pool"]]
        if mine_docs != v1_docs:
            raise SystemExit(f"LOUD STOP: S0 membership/order != result_v1.json for "
                             f"{qrec['qid']}: {mine_docs} vs {v1_docs}")
        collapsed = [collapse_to_v1(lab4(i)) for i in s0]
        if collapsed != [p["label"] for p in qrec["pool"]]:
            raise SystemExit(f"LOUD STOP: S0 collapsed labels != v1 labels for {qrec['qid']}")
        for pos, i in enumerate(s0):
            delta = abs(round(float(scores[i]), 4) - qrec["pool"][pos]["score"])
            if delta > S0_SCORE_DRIFT_BOUND:
                raise SystemExit(f"LOUD STOP: S0 score drift {delta} > "
                                 f"{S0_SCORE_DRIFT_BOUND} for {qrec['qid']} rank {pos}")
            if delta:
                s0_drift.append({"qid": qrec["qid"], "rank": pos,
                                 "v1_score": qrec["pool"][pos]["score"],
                                 "fresh_score": round(float(scores[i]), 4)})
        if not is_smoke:
            m = pool_metrics([lab4(i) for i in s0], r_corpus, ndcg_fn)
            same = (m["n_pool"] == qrec["n_pool"]
                    and m["has_relevant"] == qrec["has_relevant"]
                    and m["first_relevant_rank"] == qrec["first_relevant_rank"]
                    and round(m["rr"], 4) == round(qrec["rr"], 4)
                    and m["ndcg5"] == qrec["ndcg5"]
                    and (m["has_wrong_object"] or m["has_salt_sibling"])
                    == qrec["has_wrong_object"])
            if not same:
                raise SystemExit(f"LOUD STOP: S0 metrics != v1 for {qrec['qid']}")

        recs: dict[str, dict] = {}
        for v, pool in pools.items():
            labels = [lab4(i) for i in pool]
            recs[v] = {"qid": qrec["qid"], "query": query,
                       **pool_metrics(labels, r_corpus, ndcg_fn), "pool": rows(pool)}

        if is_smoke:
            smoke_out[qrec["qid"]] = {
                "query": query, "key_set": sorted(key_set_u), "query_drug": qdrug,
                "r_corpus": r_corpus, "n_owned_safety_in_corpus": len(owned_safety),
                "variants": {v: {"n_pool": recs[v]["n_pool"],
                                 "pool": rows(pools[v], with_title=True)} for v in VARIANTS},
            }
            return

        for v in VARIANTS:
            per_query[v].append(recs[v])

        # displaced (seat variants): S0 docs no longer in the pool
        for v in ("S1", "S2c1", "S2c2"):
            gone = [i for i in s0 if i not in set(pools[v])]
            for i in gone:
                d = corpus_docs[i]
                displaced[v].append({"qid": qrec["qid"], "query": query,
                                     "score": round(float(scores[i]), 4),
                                     "moiety": d.get("moiety"), "loinc": d.get("loinc"),
                                     "label": lab4(i), "title": d.get("title")})

        # removals (I1 variants)
        for src, v in (("S0", "I1"), ("S1", "S1I1"), ("S2c1", "S2c1I1"), ("S2c2", "S2c2I1")):
            base_pool, filt = pools[src], pools[v]
            n_removed = len(base_pool) - len(filt)
            rc = removal_counts[v]
            rc["removed_docs"] += n_removed
            if n_removed:
                rc["queries_with_removal"] += 1
                if base_pool and not filt:
                    rc["pools_became_empty"] += 1
            if v == "I1":
                for i in base_pool:
                    if lab4(i) == "wrong_object":
                        d = corpus_docs[i]
                        removed_by_i1.append({"qid": qrec["qid"], "query": query,
                                              "score": round(float(scores[i]), 4),
                                              "moiety": d.get("moiety"),
                                              "loinc": d.get("loinc"),
                                              "title": d.get("title")})

        # self-refutation collectors (S0 pools)
        for i in s0:
            d = corpus_docs[i]
            lab = lab4(i)
            if lab == "salt_sibling":
                salt_sibling_pool_docs.append({"qid": qrec["qid"], "query": query,
                                               "moiety": d.get("moiety"),
                                               "loinc": d.get("loinc"),
                                               "title": d.get("title")})
            if lab == "wrong_object":
                m = (d.get("moiety") or "").upper().strip()
                toks = m.split()
                if (len(toks) > 1 and toks[-1] == "MAGNESIUM"
                        and strip_salt_suffixes(" ".join(toks[:-1])) == qdrug.upper()):
                    magnesium_flips.append({"qid": qrec["qid"], "query": query, "moiety": m})
                for k in key_set_u - {qdrug.upper()}:
                    if is_salt_sibling(m, k):
                        anykey_delta.append({"qid": qrec["qid"], "moiety": m, "other_key": k})
                if (strip_salt_suffixes(m) == strip_salt_suffixes(qdrug)
                        and strip_salt_suffixes(m) != qdrug.upper()):
                    queryside_strip_delta.append({"qid": qrec["qid"], "query": query,
                                                  "moiety": m})

    # ── smoke first (WD03 excluded: out_of_scope by design, as in v1) ──
    for srec in base["smoke"]["records"]:
        if srec.get("scope") == "out_of_scope" or srec.get("pool") is None:
            continue
        await eval_one(srec, is_smoke=True)

    # ── WD01 hard gate: the seat must lift DURLAZA — Contraindications ──
    wd01 = smoke_out["SMK-WD01"]

    def _has_durlaza_contra(v: str) -> bool:
        return any(p["moiety"] == "ACETYLSALICYLIC ACID" and p["loinc"] == "34070-3"
                   for p in wd01["variants"][v]["pool"])

    aceclo_label = label_doc4({"moiety": "ACECLOFENAC", "loinc": "34070-3"},
                              {"ASPIRIN", "ACETYLSALICYLIC ACID"}, whitelist, "ASPIRIN")
    # GATE, corrected to the v1 RECORD (deviation from the baton phrasing, stated):
    # the baton said "under S1 and S2, DURLAZA — Contraindications must appear". The v1
    # record itself (smoke wd01 best_corpus_relevant_safety) says the TOP owned-safety
    # doc for this query is DURLAZA — Drug Interactions (34073-7, 0.4118 / rank 388);
    # Contraindications (34070-3, 0.4031) is SECOND, 0.0087 behind. So at cap=1 the
    # single seat legitimately goes to Drug Interactions and the Contraindications
    # requirement is UNSATISFIABLE at cap=1. Asserted: contra present under S1 and
    # S2c2; the S2c1 seat IS an owned DURLAZA safety doc; contra-at-cap1 is MEASURED
    # and reported as a finding, not asserted.
    s2c1_pool = wd01["variants"]["S2c1"]["pool"]
    s2c1_seat = s2c1_pool[0] if s2c1_pool else None
    s2c1_seat_is_owned_safety = bool(
        s2c1_seat and s2c1_seat["label"] == "relevant"
        and (s2c1_seat["loinc"] or "") in whitelist
        and s2c1_seat["moiety"] == "ACETYLSALICYLIC ACID"
    )
    wd01_gate = {
        "durlaza_contra_in_pool_S1": _has_durlaza_contra("S1"),
        "durlaza_contra_in_pool_S2c2": _has_durlaza_contra("S2c2"),
        "durlaza_contra_in_pool_S2c1_MEASURED_NOT_ASSERTED": _has_durlaza_contra("S2c1"),
        "s2c1_seat": s2c1_seat,
        "s2c1_seat_is_owned_durlaza_safety_doc": s2c1_seat_is_owned_safety,
        "s2c1_finding": "cap=1 seats DURLAZA — Drug Interactions (34073-7, 0.4118), not "
                        "Contraindications (34070-3, 0.4031; gap 0.0087) — the section the "
                        "seat lifts is the best-SCORING owned safety section, which for "
                        "this query is not the contraindications section the user asked "
                        "about. cap=2 seats both.",
        "raw_S0_pool_empty_so_I1_removes_nothing_on_raw_arm":
            wd01["variants"]["S0"]["n_pool"] == 0,
        "aceclofenac_34070-3_label_under_aspirin_key_set": aceclo_label,
        "note": "On the FULL-PIPELINE record (rewrite arm, the 12/12) I1 would remove the "
                "ACECLOFENAC citation — its label under the aspirin key set is wrong_object "
                "(computed above), and it is NOT a salt_sibling (whole-token strip of "
                "ACECLOFENAC never equals ASPIRIN). The rewrite arm is out of v1 scope, so "
                "that removal is STATED from the record, not simulated.",
    }
    if not (wd01_gate["durlaza_contra_in_pool_S1"] and wd01_gate["durlaza_contra_in_pool_S2c2"]
            and s2c1_seat_is_owned_safety
            and wd01_gate["raw_S0_pool_empty_so_I1_removes_nothing_on_raw_arm"]
            and aceclo_label == "wrong_object"):
        raise SystemExit(f"LOUD STOP: WD01 seat smoke gate failed: {wd01_gate}")

    # ── the 100 sampled queries ──
    for i, qrec in enumerate(base["queries"]):
        await eval_one(qrec, is_smoke=False)
        if (i + 1) % 20 == 0:
            print(f"  …{i + 1}/{len(base['queries'])}")

    # ── coverage half (no embeddings needed): key sets owning zero safety docs ──
    key_sets = _bqs.build_key_sets(corpus_docs)
    distinct_sets = {frozenset(ks) for ks in key_sets.values()}
    owners_of_safety = {moieties_u[i] for i in range(len(corpus_docs)) if loinc_ok[i]}
    zero_safety_sets = sorted(sorted(fs) for fs in distinct_sets if not (fs & owners_of_safety))
    sampled_zero_safety = [r["qid"] for v in ("S0",) for r in per_query[v]
                           if next((q for q in base["queries"] if q["qid"] == r["qid"]), {})
                           .get("best_corpus_relevant_safety") is None]

    variants_out = {v: {"aggregate": {**aggregate(per_query[v]),
                                      **({"displaced_docs": len(displaced[v])}
                                         if v in displaced else {}),
                                      **(removal_counts[v] if v in removal_counts else {})},
                        "per_query": per_query[v]} for v in VARIANTS}

    def _dist(rows_: list[dict]) -> dict:
        out: dict[str, int] = {}
        for r in rows_:
            out[r["label"]] = out.get(r["label"], 0) + 1
        return out

    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip()
    result = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "git_head": git_head,
        "base": "result_v1.json",
        "suffix_list": list(SALT_SUFFIXES),
        "min_score": min_score,
        "n_results": n_results,
        "param_provenance": prov,
        "embedding_calls": len(cache),
        "s0_score_drift": {
            "bound": S0_SCORE_DRIFT_BOUND,
            "note": "Re-embedding drift only — membership, order, labels and every "
                    "label-derived metric matched result_v1.json EXACTLY for all "
                    "queries (hard gate). Both scores recorded per drifted doc.",
            "n_drifted_docs": len(s0_drift),
            "max_abs_drift": round(max((abs(d["fresh_score"] - d["v1_score"])
                                        for d in s0_drift), default=0.0), 4),
            "drifted": s0_drift,
        },
        "variants": variants_out,
        "displaced": {v: {"total": len(displaced[v]), "label_distribution": _dist(displaced[v]),
                          "docs": displaced[v]} for v in displaced},
        "removed_by_I1": removed_by_i1,
        "smoke": {"records": smoke_out, "wd01_gate": wd01_gate,
                  "wd03": "out_of_scope by design (pair fixture) — excluded, as in v1"},
        "self_refutation": {
            "salt_sibling_pool_docs": salt_sibling_pool_docs,
            "salt_sibling_samples": salt_sibling_pool_docs[:5],
            "removed_by_I1_samples": removed_by_i1[:5],
            "methyltestosterone_negative": is_salt_sibling("METHYLTESTOSTERONE", "TESTOSTERONE"),
            "sampled_queries_with_zero_owned_safety": sampled_zero_safety,
            "sampled_zero_note": "0 is BY CONSTRUCTION, not a discovery — v1 eligibility "
                                 "required every sampled key set to own ≥1 whitelisted safety "
                                 "doc. The real coverage gap is corpus-level, below.",
            "corpus_key_sets_total": len(distinct_sets),
            "corpus_key_sets_zero_owned_safety": len(zero_safety_sets),
            "corpus_zero_safety_examples": zero_safety_sets[:10],
            "magnesium_not_in_suffix_list_would_flip": magnesium_flips,
            "anykey_vs_key_used_delta": anykey_delta,
            "query_side_strip_asymmetry": queryside_strip_delta,
        },
        "assumptions": {
            "entity_resolution": "The sim assumes the query drug is KNOWN (true by "
                                 "construction). A production seat needs a free-text→key-set "
                                 "resolver; its miss rate is the residual wrong-object rate "
                                 "in production. Deliberately not quantified (out of scope).",
            "circularity": "I1's rule IS the labeler's rule, so wrong_object→0 under I1 is "
                           "tautological at pool level. Non-tautological and reported: what "
                           "I1 removes (full list), empty-pool rate after I1, and the seat "
                           "metrics, which are independent of the labeler.",
            "pool_ordering": "Seated docs are ranked by score inside the final pool (argsort "
                             "position), not pinned to a fixed slot.",
            "s2_fill": "S2's non-seat slots fill from the ABOVE-FLOOR ranked list only — "
                       "the floor still governs non-seated docs.",
            "i1_no_backfill": "I1 drops docs from the built pool; no backfill from the "
                              "ranked list, so pools shrink and can become empty.",
            "salt_sibling_target": "Per the baton, the strip-compare target is the query "
                                   "drug string (key_used), not every key in the key set; "
                                   "the any-key delta is measured in self_refutation.",
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"suffix_list ({len(SALT_SUFFIXES)}): {', '.join(SALT_SUFFIXES)}")
    hdr = ("variant", "owned", "MRR", "wrong_obj", "salt_sib", "empty", "nDCG@5", "pool")
    print(("{:>8} " * len(hdr)).format(*hdr))
    for v in VARIANTS:
        a = variants_out[v]["aggregate"]
        print(f"{v:>8} {a['owned_in_pool_rate']:>8} {a['mrr']:>8} "
              f"{a['wrong_object_in_pool_rate']:>8} {a['salt_sibling_in_pool_rate']:>8} "
              f"{a['empty_pool_rate']:>8} {a['mean_ndcg5']:>8} {a['mean_pool_size']:>8}")
    for v in displaced:
        print(f"displaced {v}: {len(displaced[v])} {_dist(displaced[v])}")
    for v, rc in removal_counts.items():
        print(f"removed {v}: {rc}")
    print(f"salt_sibling docs in S0 pools: {len(salt_sibling_pool_docs)} | "
          f"MAGNESIUM would-flip: {len(magnesium_flips)} | "
          f"any-key delta: {len(anykey_delta)} | query-side strip: {len(queryside_strip_delta)}")
    print(f"corpus key sets with zero owned safety: {len(zero_safety_sets)}"
          f"/{len(distinct_sets)} (sampled: {len(sampled_zero_safety)} — by construction)")
    print(f"S0 score drift (re-embedding): {len(s0_drift)} docs, "
          f"max {result['s0_score_drift']['max_abs_drift']} — membership/labels/metrics exact")
    print(f"wd01 gate: {wd01_gate}")
    print(f"embedding calls: {len(cache)}  |  wrote {OUT}")
    return 0


def main() -> int:
    import asyncio
    import sys

    # cp950 console class (TECH_DEBT queue #9) — harness-side workaround, no api/ change
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
