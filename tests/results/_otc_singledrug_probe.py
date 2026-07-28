# -*- coding: utf-8 -*-
"""Phase-1 Task 4 — does Research ALREADY cover single-drug OTC safety queries?

The [P2] entry assumes Research needs Verify's openFDA fall-through. But the two surfaces
retrieve differently:
  Verify   : queries DailyMed BY DRUG NAME; if that label lacks LOINC 34073-7 there is
             nothing else, hence the Tier-2 openFDA fallback (api/server.py:1218-1225).
  Research : fans out to FIVE sources IN PARALLEL every query — local, PubMed, FDA(openFDA),
             TFDA, DailyMed (api/rag/retriever.py:178-190). openFDA is ALWAYS queried.

So the exposure may already be covered by an existing source rather than needing a new
fallback. This measures it on the OTC drugs that have NO DailyMed safety section.

READ-ONLY.
"""
import asyncio, io, json, os, sys, time
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"
from dotenv import load_dotenv                      # noqa: E402
load_dotenv(ROOT / ".env", override=True)
from api.rag.retriever import HybridRetriever       # noqa: E402
from api.server import _annotate_research_question  # noqa: E402

N = int(os.environ.get("OTC_N", "3"))
OUT = ROOT / "tests" / "results" / f"otc_singledrug_{time.strftime('%Y%m%d_%H%M%S')}.json"

# Single-drug SAFETY queries on drugs whose DailyMed moiety has NO safety section.
QUERIES = [
    ("aspirin_contra",   "aspirin contraindications and who should not take it"),
    ("ibuprofen_warn",   "ibuprofen warnings and precautions"),
    ("naproxen_inter",   "naproxen drug interactions"),
    ("cimetidine_inter", "cimetidine drug interactions"),
    ("omeprazole_contra","omeprazole contraindications"),
    ("loperamide_warn",  "loperamide warnings and safety"),
]
SAFETY_LOINC = {"34073-7", "34070-3", "34066-1", "43685-7"}


def classify(doc):
    st = str(getattr(doc.source_type, "value", doc.source_type) or "").lower()
    sid = doc.source_id or ""
    dm_safety = sid.startswith("DailyMed:") and "#" in sid and \
        sid.split("#", 1)[1].split("~", 1)[0] in SAFETY_LOINC
    return st, dm_safety


async def main():
    r = HybridRetriever()
    rep = {"N": N, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "cases": {}}
    print(f"=== single-drug OTC safety queries, N={N} ===\n", flush=True)
    for cid, q in QUERIES:
        runs = []
        for i in range(N):
            try:
                docs, status = await r.retrieve(query=_annotate_research_question(q),
                                                max_results=5, source_weight_active=True)
                types = Counter()
                fda_ids, dm_safety_ids = [], []
                for d in docs:
                    st, dms = classify(d)
                    types[st] += 1
                    if st == "fda":
                        fda_ids.append(d.source_id)
                    if dms:
                        dm_safety_ids.append(d.source_id)
                runs.append({"run": i, "status": status, "pool_size": len(docs),
                             "source_types": dict(types),
                             "fda_docs": fda_ids, "dailymed_safety_docs": dm_safety_ids,
                             "ids": [d.source_id for d in docs]})
            except Exception as e:
                runs.append({"run": i, "error": f"{type(e).__name__}: {e}"})
        ok = [x for x in runs if "error" not in x and x.get("status") not in ("no_results", "error")]
        any_fda = sum(1 for x in ok if x["fda_docs"])
        any_dms = sum(1 for x in ok if x["dailymed_safety_docs"])
        rep["cases"][cid] = {"query": q, "runs": runs, "usable": len(ok),
                             "runs_with_openFDA_doc": any_fda,
                             "runs_with_dailymed_safety": any_dms}
        OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {cid:19} openFDA-doc-cited {any_fda}/{len(ok)}   "
              f"DailyMed-safety-cited {any_dms}/{len(ok)}   "
              f"types={[dict(x['source_types']) for x in ok]}", flush=True)
    rep["complete"] = True
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
