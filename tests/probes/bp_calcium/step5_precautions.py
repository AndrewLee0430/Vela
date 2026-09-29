"""PROBE 2 · STEP 2 — would a PRECAUTIONS (LOINC 42232-9) section clear the 0.6 floor?

Budget: 3 live DailyMed fetches, 2 embedding calls (both BATCHED — the embedder takes
`input: list[str]`), 0 completions.
  fetch 1  GET v2/spls/{HCTZ pinned setid}.xml          (setid from the shipped corpus)
  fetch 2  GET v2/spls.json?drug_name=chlorthalidone    (NOT a corpus moiety)
  fetch 3  GET v2/spls/{picked chlorthalidone setid}.xml
  embed 1  the 9 DailyMed query strings recorded in step3b_dm_counterfactual.json
  embed 2  the section texts (see below)

Section text is built EXACTLY as scripts/build_dailymed_label_corpus.py would build a doc:
its own `_find_section` (first match) + DailyMedClient `_collect_prose` + `_flatten_tables`
+ its own `_chunks`. `_collect_prose` is RECURSIVE, so a 42232-9 doc carries every nested
subsection (General, Drug Interactions, Pregnancy, ...) — that full doc is the REALISTIC
arm. The calcium-bearing subsection alone is embedded too, as an UPPER BOUND (a doc the
builder would never produce).

Rank = 1 + the number of shipped label_emb.npy rows scoring strictly higher on that query
(the would-be in-store rank; 0.6 is the store floor, api/server.py local_threshold).
"""
import asyncio
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import numpy as np

from _harness import ROOT, production_retriever

HERE = Path(__file__).resolve().parent
OUT = HERE / "step5_precautions.json"
PRECAUTIONS = "42232-9"
CA = re.compile(r"calcium|hypercalc|vitamin\s*d", re.I)

spec = importlib.util.spec_from_file_location("bdl", ROOT / "scripts" / "build_dailymed_label_corpus.py")
bdl = importlib.util.module_from_spec(spec)
# The builder re-wraps sys.stdout at import; an orphaned TextIOWrapper is GC-closed and takes
# the shared buffer with it ("I/O operation on closed file"). Keep BOTH alive, restore ours.
import sys  # noqa: E402
_STDOUT_KEEPALIVE = [sys.stdout]
spec.loader.exec_module(bdl)
_STDOUT_KEEPALIVE.append(sys.stdout)
sys.stdout = _STDOUT_KEEPALIVE[0]


def sentences(text, pat=CA, n=5):
    return [s.strip()[:500] for s in re.split(r"(?<=[.;])\s+", text) if pat.search(s)][:n]


def doc_code(root):
    c = root.find(f"{bdl._NS}code")
    return None if c is None else {"code": c.get("code"), "displayName": c.get("displayName")}


def subsection_with_calcium(dm, sec):
    """The smallest nested <section> under PRECAUTIONS whose own prose names calcium."""
    best = None
    for sub in sec.iter(f"{bdl._NS}section"):
        if sub is sec:
            continue
        t = dm._collect_prose(sub)
        if CA.search(t) and (best is None or len(t) < len(best[1])):
            title = sub.find(f"{bdl._NS}title")
            best = ("".join(title.itertext()).strip() if title is not None else "", t)
    return best


def build(dm, xml, label):
    root = ET.fromstring(xml)
    sec = bdl._find_section(root, PRECAUTIONS)
    rec = {"label": label, "doctype": doc_code(root), "title": None, "precautions_found": sec is not None}
    t = root.find(f"{bdl._NS}title")
    rec["title"] = " ".join("".join(t.itertext()).split())[:200] if t is not None else None
    if sec is None:
        return rec, []
    prose = dm._collect_prose(sec)
    tables = dm._flatten_tables(sec)
    combined = "\n".join(p for p in (prose, tables) if p).strip()
    chunks = bdl._chunks(combined)
    rec.update({"precautions_chars": len(combined), "chunks": len(chunks),
                "calcium_sentences": sentences(combined)})
    texts = [(f"{label} · FULL 42232-9" + (f" chunk {i}" if len(chunks) > 1 else ""), c)
             for i, c in enumerate(chunks)]
    sub = subsection_with_calcium(dm, sec)
    if sub:
        rec["calcium_subsection"] = {"title": sub[0], "chars": len(sub[1])}
        texts.append((f"{label} · SUBSECTION '{sub[0]}' only (upper bound)", sub[1]))
    return rec, texts


async def main():
    r, cfg = production_retriever()
    floor = cfg["local_threshold"]
    store = r.dailymed_store
    docs = store.documents
    assert len(docs) == 4608
    E = store.embeddings / (np.linalg.norm(store.embeddings, axis=1, keepdims=True) + 1e-10)
    dm = bdl.DailyMedClient()

    hctz = sorted({d["setid"] for d in docs if d.get("moiety") == "HYDROCHLOROTHIAZIDE"})
    assert len(hctz) == 1, hctz
    fetches = []
    async with httpx.AsyncClient(timeout=30.0) as http:
        x1 = await http.get(f"{bdl.V2}/spls/{hctz[0]}.xml"); x1.raise_for_status()
        fetches.append(f"GET v2/spls/{hctz[0]}.xml -> {x1.status_code}")
        j = await http.get(f"{bdl.V2}/spls.json", params={"drug_name": "chlorthalidone", "pagesize": "50"})
        j.raise_for_status()
        fetches.append(f"GET v2/spls.json?drug_name=chlorthalidone -> {j.status_code}")
        cands = [(x["setid"], x.get("title", ""), int(x.get("spl_version") or 0))
                 for x in j.json().get("data", []) if x.get("setid")]
        # the builder's ORIGINAL-path picker (head-word in title, fewest ' and ', newest version);
        # no marketing_category filter (the builder loops NDA>ANDA>... codes — one call here).
        pick = bdl._pick_reference(cands, "CHLORTHALIDONE")
        x2 = await http.get(f"{bdl.V2}/spls/{pick[0]}.xml"); x2.raise_for_status()
        fetches.append(f"GET v2/spls/{pick[0]}.xml -> {x2.status_code}")

    h_rec, h_texts = build(dm, x1.content, "HCTZ")
    h_rec["setid"] = hctz[0]
    c_rec, c_texts = build(dm, x2.content, "CHLORTHALIDONE")
    c_rec.update({"setid": pick[0], "spls_json_title": pick[1], "spl_version": pick[2],
                  "candidates_returned": len(cands),
                  "picker": "bdl._pick_reference (original path, no marketing-category filter)"})

    cf = json.load(open(HERE / "step3b_dm_counterfactual.json", encoding="utf-8"))
    queries = [row["query"] for row in cf["rows"]]
    qe = await store._embedder.embed(bdl_req(store, queries))            # embed call 1
    texts = h_texts + c_texts
    te = await store._embedder.embed(bdl_req(store, [t for _, t in texts]))  # embed call 2
    Q = np.array(qe.embeddings, dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    T = np.array(te.embeddings, dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True)

    scored = []
    for ti, (name, txt) in enumerate(texts):
        per_q = []
        for qi, q in enumerate(queries):
            cos = float(T[ti] @ Q[qi])
            store_scores = E @ Q[qi]
            per_q.append({"query": q, "cos": round(cos, 4), "clears_floor": cos >= floor,
                          "would_be_rank": int((store_scores > cos).sum()) + 1,
                          "store_max": round(float(store_scores.max()), 4)})
        best = max(per_q, key=lambda x: x["cos"])
        scored.append({"text": name, "chars": len(txt),
                       "n_clear_floor": sum(x["clears_floor"] for x in per_q),
                       "best": best, "per_query": per_q})
        print(f"{name:<60} chars={len(txt):<6} clears {sum(x['clears_floor'] for x in per_q)}/"
              f"{len(queries)}  best={best['cos']} (rank {best['would_be_rank']}) on {best['query']!r}")

    h_full = [s for s in scored if s["text"].startswith("HCTZ · FULL")]
    hb = max(h_full, key=lambda s: s["best"]["cos"]) if h_full else None
    verdict_b = ("B: if 42232-9 were in the corpus, HCTZ PRECAUTIONS clears 0.6 on "
                 f"{hb['n_clear_floor']}/{len(queries)} strings (best {hb['best']['cos']})"
                 if hb else "B: HCTZ label has NO 42232-9 section")
    res = {"floor": floor, "fetches": fetches, "embedding_calls": 2,
           "n_query_strings": len(queries),
           "query_count_note": "the brief said 10 (9 rewrites + raw); step3b recorded 9 DISTINCT strings, raw included",
           "hctz": h_rec, "chlorthalidone": c_rec, "scored": scored, "verdict_B": verdict_b}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(verdict_b)
    for rec in (h_rec, c_rec):
        print(rec["label"], rec.get("doctype"), rec.get("title"), "| calcium sentences:")
        for s in rec.get("calcium_sentences", []):
            print("    ", s)


def bdl_req(store, inputs):
    from api.providers.base import EmbeddingRequest
    return EmbeddingRequest(model=store._embedder_model, input=inputs)


if __name__ == "__main__":
    asyncio.run(main())
