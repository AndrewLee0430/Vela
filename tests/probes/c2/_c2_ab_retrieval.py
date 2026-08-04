# -*- coding: utf-8 -*-
"""c2 Phase-1b Part 3b — CONTROL (shipped index) vs TREATMENT (E-A scratch index).

Both arms run IN ONE PROCESS against the same PubMed/TFDA/local wiring, so the only
difference is which DailyMed index the store holds. The treatment index is injected by
constructing DailyMedCorpusStore with scratch paths and setting the module singleton —
DailyMedCorpusStore.__init__ already accepts corpus_path/emb_path, so NO product code is
modified.

Captures the FULL pre-cut pool via the retriever's existing `shadow_sink` out-param, so
"never retrieved" can be distinguished from "retrieved but ranked out".

⚠️ Reads only. Writes only to tests/results/.
"""
import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"
from dotenv import load_dotenv                     # noqa: E402
load_dotenv(ROOT / ".env", override=True)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from api.database import vector_store as vs        # noqa: E402
from api.rag.retriever import HybridRetriever      # noqa: E402
from api.server import _annotate_research_question # noqa: E402

N = int(os.environ.get("C2_N", "3"))
SCRATCH = ROOT / "tests/results/c2_ea_index"
OUT = ROOT / "tests/results/c2_ab_retrieval.json"

# (id, query, own-drug tokens, the WRONG drug observed pre-c2)
CASES = [
    ("aspirin",     "aspirin contraindications and who should not take it",
     ["ASPIRIN", "ACETYLSALICYLIC"], "ACECLOFENAC"),
    ("ibuprofen",   "ibuprofen warnings and precautions",
     ["IBUPROFEN"], "PIROXICAM|MEFENAMIC"),
    ("naproxen",    "naproxen drug interactions and safety",
     ["NAPROXEN"], "NABUMETONE"),
    ("omeprazole",  "omeprazole contraindications and warnings",
     ["OMEPRAZOLE"], "PANTOPRAZOLE"),
    ("cimetidine",  "cimetidine drug interactions and safety",
     ["CIMETIDINE"], "COBIMETINIB"),
]


def load_store(docs_path, emb_path):
    vs._dailymed_store = vs.DailyMedCorpusStore(corpus_path=str(docs_path), emb_path=str(emb_path))
    return vs._dailymed_store


def classify(doc, own_tokens, wrong_pat):
    sid = (getattr(doc, "source_id", "") or "")
    title = (getattr(doc, "title", "") or "").upper()
    content = (getattr(doc, "content", "") or "").upper()
    hay = title + " " + content
    own = any(t in hay for t in own_tokens)
    wrong = any(w and w in hay for w in wrong_pat.split("|"))
    loinc = sid.split("#", 1)[1].split("~", 1)[0] if "#" in sid else None
    return own, wrong, loinc


async def run_arm(tag, r, cases, n):
    res = {}
    for cid, q, own_tokens, wrong in cases:
        runs = []
        for i in range(n):
            sink = []
            try:
                docs, status = await r.retrieve(query=_annotate_research_question(q),
                                                max_results=5, shadow_sink=sink,
                                                source_weight_active=True)
            except Exception as e:
                runs.append({"run": i, "error": f"{type(e).__name__}: {e}"})
                continue
            final = []
            for rank, d in enumerate(docs):
                own, wr, loinc = classify(d, own_tokens, wrong)
                final.append({"rank": rank, "source_id": d.source_id,
                              "title": (d.title or "")[:80], "own_drug": own,
                              "wrong_drug": wr, "loinc": loinc})
            # shadow_sink items are (doc, rerank_score_0_1) tuples in reranker order
            # (retriever.py:258-263 <- source_weight_shadow.rank_by_composite_v1 :158).
            # ⚠️ This is the POST-RERANK pool, i.e. after the relevance filter. A document
            # absent here was EITHER never retrieved (below the 0.6 cosine threshold) OR
            # dropped by the relevance filter — the store probe below disambiguates.
            pool = []
            for rank, item in enumerate(sink or []):
                d, score = (item if isinstance(item, (tuple, list)) and len(item) >= 2
                            else (item, None))
                if d is None or not hasattr(d, "source_id"):
                    continue
                own, wr, loinc = classify(d, own_tokens, wrong)
                pool.append({"rerank_rank": rank, "rerank_score": score,
                             "source_id": getattr(d, "source_id", None),
                             "title": (getattr(d, "title", "") or "")[:80],
                             "own_drug": own, "wrong_drug": wr, "loinc": loinc})
            runs.append({"run": i, "status": status, "final": final,
                         "precut_pool_size": len(pool), "precut_pool": pool})
        res[cid] = {"query": q, "runs": runs}
        ok = [x for x in runs if "error" not in x]
        cited_own = sum(1 for x in ok if any(f["own_drug"] for f in x["final"]))
        cited_wrong = sum(1 for x in ok if any(f["wrong_drug"] for f in x["final"]))
        pool_own = sum(1 for x in ok if any(p["own_drug"] for p in x["precut_pool"]))
        print(f"  [{tag}] {cid:11} own-in-pool {pool_own}/{len(ok)}  "
              f"own-CITED {cited_own}/{len(ok)}  WRONG-cited {cited_wrong}/{len(ok)}", flush=True)
    return res


async def store_probe(tag, store, cases):
    """Isolate the RETRIEVAL-THRESHOLD question from the LLM relevance filter: ask the
    DailyMed store directly whether the drug's OWN 34071-1 doc clears min_score on the
    raw query. This is what tests the baton's vocabulary-mismatch hypothesis."""
    res = {}
    for cid, q, own_tokens, _wrong in cases:
        try:
            docs = await store.search(query=q, n_results=25, min_score=0.6)
        except Exception as e:
            res[cid] = {"error": f"{type(e).__name__}: {e}"}
            print(f"  [{tag}] {cid:11} STORE PROBE ERROR {type(e).__name__}", flush=True)
            continue
        hits = []
        for rank, d in enumerate(docs):
            sid = d.source_id or ""
            loinc = sid.split("#", 1)[1].split("~", 1)[0] if "#" in sid else None
            hay = ((d.title or "") + " " + (d.content or "")).upper()
            hits.append({"rank": rank, "source_id": sid, "loinc": loinc,
                         "own_drug": any(t in hay for t in own_tokens),
                         "score": getattr(d, "relevance_score", None)})
        own34071 = [h for h in hits if h["own_drug"] and h["loinc"] == "34071-1"]
        res[cid] = {"n": len(hits), "own_34071_1_hits": own34071, "hits": hits[:12]}
        print(f"  [{tag}] {cid:11} store hits {len(hits):2d} | own 34071-1 above threshold: "
              f"{'YES rank ' + str(own34071[0]['rank']) if own34071 else 'NO'}", flush=True)
    return res


async def main():
    out = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "N": N, "arms": {}, "store_probe": {}}

    print("=== CONTROL (shipped DailyMed index) ===", flush=True)
    load_store(ROOT / "data/dailymed/label_docs.json", ROOT / "data/dailymed/label_emb.npy")
    r = HybridRetriever(local_threshold=0.6, enable_local=False, enable_pubmed=True,
                        enable_fda=True, enable_tfda=True)
    out["arms"]["control"] = await run_arm("CTL", r, CASES, N)

    print("\n=== TREATMENT (E-A scratch index: +34071-1) ===", flush=True)
    tstore = load_store(SCRATCH / "label_docs.json", SCRATCH / "label_emb.npy")
    r2 = HybridRetriever(local_threshold=0.6, enable_local=False, enable_pubmed=True,
                         enable_fda=True, enable_tfda=True)
    out["arms"]["treatment"] = await run_arm("EA ", r2, CASES, N)

    print("\n=== STORE PROBE (treatment index, threshold isolation) ===", flush=True)
    out["store_probe"]["treatment"] = await store_probe("EA ", tstore, CASES)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)


asyncio.run(main())
