# -*- coding: utf-8 -*-
"""c2 Phase-1c Part 1 — is the cimetidine 0/3 -> 3/3 regression REAL, or within-arm noise?

Direct precedent for the trap: c1's `ibuprofen_warn safety 9->4` was ruled NOT attributable
because the ON arm's own runs ranged 4/4/1 — within-arm spread already covered the
between-arm difference. This measures the CONTROL arm's own spread.

CONTROL uses the SHIPPED index -> no rebuild, no embedding, no cost beyond retrieval LLM calls.
TREATMENT is a bonus (the scratch index from Phase 1b is still on disk; nothing is rebuilt).

⚠️ Classification is setid -> moiety (EXACT) from the start. The Phase-1b harness used a
lexical `own_drug` flag which false-positived because the ACECLOFENAC label literally contains
"acetylsalicylic acid". Never classify by text here.
"""
import asyncio
import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"
from dotenv import load_dotenv                      # noqa: E402
load_dotenv(ROOT / ".env", override=True)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from api.database import vector_store as vs         # noqa: E402
from api.rag.retriever import HybridRetriever       # noqa: E402
from api.server import _annotate_research_question  # noqa: E402

N = int(os.environ.get("C2_N", "6"))
SHIP = (ROOT / "data/dailymed/label_docs.json", ROOT / "data/dailymed/label_emb.npy")
SCRATCH = (ROOT / "tests/results/c2_ea_index/label_docs.json",
           ROOT / "tests/results/c2_ea_index/label_emb.npy")
OUT = ROOT / "tests/results/c2_variance.json"

CASES = [
    ("cimetidine", "cimetidine drug interactions and safety", {"CIMETIDINE"}),
    ("aspirin",    "aspirin contraindications and who should not take it",
     {"ASPIRIN", "ACETYLSALICYLIC ACID"}),
]

# setid -> moiety, from BOTH indexes (scratch is a superset of shipped)
SETID2MOIETY = {}
for p in (SHIP[0], SCRATCH[0]):
    if p.exists():
        for d in json.loads(p.read_text(encoding="utf-8"))["documents"]:
            SETID2MOIETY[d["setid"]] = (d.get("moiety") or "").upper()


def moiety_of(sid):
    if not sid or not sid.startswith("DailyMed:"):
        return None
    return SETID2MOIETY.get(sid.split("DailyMed:")[1].split("#")[0])


async def arm(tag, docs_path, emb_path, n):
    vs._dailymed_store = vs.DailyMedCorpusStore(corpus_path=str(docs_path), emb_path=str(emb_path))
    r = HybridRetriever(local_threshold=0.6, enable_local=False, enable_pubmed=True,
                        enable_fda=True, enable_tfda=True)
    res = {}
    for cid, q, own in CASES:
        runs = []
        for i in range(n):
            try:
                got, status = await r.retrieve(query=_annotate_research_question(q),
                                               max_results=5, source_weight_active=True)
            except Exception as e:
                runs.append({"run": i, "error": f"{type(e).__name__}: {e}"})
                continue
            cited = []
            for d in got:
                m = moiety_of(d.source_id)
                cited.append({"source_id": d.source_id, "moiety": m,
                              "own": bool(m and m in own),
                              "other_drug": bool(m and m not in own)})
            runs.append({"run": i, "status": status,
                         "n_docs": len(got), "cited": cited})
        ok = [x for x in runs if "error" not in x]
        wrong = sum(1 for x in ok if any(c["other_drug"] for c in x["cited"]))
        ownc = sum(1 for x in ok if any(c["own"] for c in x["cited"]))
        ident = Counter(c["moiety"] for x in ok for c in x["cited"] if c["other_drug"])
        res[cid] = {"query": q, "runs": runs, "n_ok": len(ok),
                    "wrong_drug_cited": wrong, "own_cited": ownc,
                    "wrong_identities": dict(ident)}
        print(f"  [{tag}] {cid:11} n={len(ok)}  WRONG-drug cited {wrong}/{len(ok)}  "
              f"own cited {ownc}/{len(ok)}  {dict(ident)}", flush=True)
    return res


async def main():
    out = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "N": N, "arms": {}}
    print(f"=== CONTROL (shipped index) x{N} ===", flush=True)
    out["arms"]["control"] = await arm("CTL", *SHIP, N)
    if SCRATCH[0].exists():
        print(f"\n=== TREATMENT (existing E-A scratch index, NOT rebuilt) x{N} ===", flush=True)
        out["arms"]["treatment"] = await arm("EA ", *SCRATCH, N)
    else:
        print("\n⚠️ scratch E-A index absent — treatment arm SKIPPED (not rebuilt, per baton)",
              flush=True)
        out["arms"]["treatment"] = {"skipped": "scratch index absent; deliberately not rebuilt"}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)


asyncio.run(main())
