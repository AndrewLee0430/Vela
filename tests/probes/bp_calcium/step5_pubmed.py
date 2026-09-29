"""PROBE 2 · STEP 3 — would a DISAMBIGUATED rewrite retrieve on-target PubMed docs?

3 hand-written strings through the retriever's OWN `_search_pubmed(q, max_results=5)`
(production max_results) — i.e. PubMedClient.search_and_fetch = esearch + EFETCH (the
brief said esummary; production uses efetch, so efetch is what this measures). 0 LLM calls.
Title + the doc content production builds (article.to_text(), abstract included) are saved,
so the Rule 21 hand-read is at ABSTRACT level here, unlike step5_census (titles only).

Regex pre-mark (then hand-read, all 15): INTERACTION = a thiazide/diuretic term AND a
calcium/hypercalcemia term in title+abstract.
"""
import asyncio
import json
import re
from pathlib import Path

from _harness import production_retriever

HERE = Path(__file__).resolve().parent
OUT = HERE / "step5_pubmed.json"
STRINGS = ["thiazide diuretic calcium supplement hypercalcemia",
           "calcium supplement antihypertensive drug interaction older adults",
           "hydrochlorothiazide calcium carbonate interaction"]
DIUR = re.compile(r"thiazide|hydrochlorothiazide|chlorthalidone|indapamide|diuretic", re.I)
CALC = re.compile(r"calcium|hypercalc", re.I)
CCB = re.compile(r"calcium channel|calcium antagonist|\bCCB\b|dihydropyridine|amlodipine|nifedipine|verapamil|diltiazem", re.I)


async def main():
    r, cfg = production_retriever()
    out = []
    for q in STRINGS:
        docs = await r._search_pubmed(q, cfg["max_results"])
        rows = []
        for d in docs:
            text = f"{d.title} {d.content}"
            rows.append({"source_id": d.source_id, "title": d.title, "year": d.year,
                         "rank_score": round(d.relevance_score, 4),
                         "regex_interaction": bool(DIUR.search(text) and CALC.search(text)),
                         "regex_ccb": bool(CCB.search(text)),
                         "content": d.content[:2500]})
        out.append({"query": q, "docs": rows})
        print(f"\n## {q}  ({len(rows)} docs)")
        for x in rows:
            print(f"   {'INT' if x['regex_interaction'] else '   '} {'CCB' if x['regex_ccb'] else '   '} "
                  f"{x['source_id']:<14} {x['year']} {x['title'][:100]}")
    json.dump({"max_results": cfg["max_results"], "call_path": "HybridRetriever._search_pubmed -> "
               "PubMedClient.search_and_fetch (esearch + efetch)", "strings": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
