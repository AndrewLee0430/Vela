#!/usr/bin/env python
"""Counterfactual re-score of a C1 shadow run with the STRUCTURAL trigger DISABLED.

The full run found the invariant-4 structural detector over-fires on real multi-source retrievals
(rubber-stamps ">=2 opposite counterintuitive sources" -> 86% of answers flagged, 75% FP). This
re-scores the SAME captured answers (no re-generation) with `enable_structural=False` to isolate the
PRIMARY whole-answer-vs-anchor path's detection/FP. Full abstracts are re-fetched by PMID
(PubMedClient.fetch_details -> article.abstract; the full abstract, invariant 2).

Usage: python scripts/direction_shadow_rescore.py tests/results/direction_shadow_<ts>.json
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

from api.data_sources.pubmed import PubMedClient
import api.services.direction_checker as dc

RESULTS_DIR = _REPO / "tests" / "results"


async def main(src_path: str):
    src = json.load(open(src_path, encoding="utf-8"))
    rows = [r for r in src["results"] if r.get("status") == "ok"]
    pubmed = PubMedClient()
    llm = dc.make_lightweight_llm()
    print(f"re-scoring {len(rows)} ok cases from {src_path} (structural DISABLED)")

    # batch-fetch all PMIDs once
    all_pmids = sorted({p for r in rows for p in (r.get("doc_pmids") or [])})
    arts = {}
    for i in range(0, len(all_pmids), 20):
        chunk = all_pmids[i:i + 20]
        try:
            for a in await pubmed.fetch_details(chunk):
                arts[a.pmid] = a
        except Exception as e:
            print(f"  fetch error for {chunk}: {e}")
    print(f"  fetched {len(arts)}/{len(all_pmids)} abstracts")

    out_rows = []
    for r in rows:
        sources = [dc.CitedSource(pmid=p, abstract=arts[p].abstract)
                   for p in (r.get("doc_pmids") or [])
                   if p in arts and (arts[p].abstract or "").strip()]
        rec = {"id": r["id"], "group": r["group"], "subgroup": r["subgroup"],
               "gt_reversed": r.get("gt_reversed"), "n_sources": len(sources)}
        try:
            flag = await dc.check(llm, answer=r["answer"], question=r["query"],
                                  cited_sources=sources, enable_structural=False)
            rec["c1_flagged"] = flag.flagged
            rec["verdict"] = flag.verdict
            rec["reason"] = flag.reason
            rec["anchor"] = flag.selected_anchor_pmid
        except Exception as e:
            rec["c1_flagged"] = None
            rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        out_rows.append(rec)
        print(f"  {rec['id']:9} {rec['group']:8} gt_rev={rec['gt_reversed']} "
              f"c1_flag={rec.get('c1_flagged')} verdict={rec.get('verdict','')}")

    targeted = [r for r in out_rows if r["group"] == "targeted"]
    clean = [r for r in out_rows if r["group"] == "clean"]
    tgt_rev = [r for r in targeted if r["gt_reversed"]]
    detected = [r for r in tgt_rev if r.get("c1_flagged")]
    missed = [r for r in tgt_rev if r.get("c1_flagged") is False]
    clean_faithful = [r for r in clean if r["gt_reversed"] is False]
    fp = [r for r in clean_faithful if r.get("c1_flagged")]

    summary = {
        "detection": {"denominator": len(tgt_rev), "detected": len(detected), "missed": len(missed),
                      "detected_ids": [r["id"] for r in detected], "missed_ids": [r["id"] for r in missed]},
        "false_positive": {"denominator": len(clean_faithful), "fp": len(fp),
                           "fp_ids": [r["id"] for r in fp]},
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"direction_shadow_rescore_nostruct_{ts}.json"
    json.dump({"timestamp": ts, "source": src_path, "structural": False,
               "summary": summary, "rows": out_rows}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    from collections import Counter
    print("\n" + "=" * 64)
    print("C1 RE-SCORE — STRUCTURAL DISABLED (primary whole-answer-vs-anchor only)")
    print("=" * 64)
    print("verdict dist:", dict(Counter(r.get("verdict") for r in out_rows)))
    print(f"DETECTION: {len(detected)}/{len(tgt_rev)} actual reversals flagged  "
          f"detected={summary['detection']['detected_ids']}  MISSED={summary['detection']['missed_ids']}")
    print(f"FALSE-POSITIVE: {len(fp)}/{len(clean_faithful)} clean-faithful flagged  "
          f"FP={summary['false_positive']['fp_ids']}")
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/direction_shadow_rescore.py <direction_shadow_*.json>")
    asyncio.run(main(sys.argv[1]))
