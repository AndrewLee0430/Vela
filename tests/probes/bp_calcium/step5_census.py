"""PROBE 2 · STEP 1 — dropped-vs-kept census, OFFLINE from step3_trace.json (0 API calls).

For every doc that entered each run's merged pool: its fate (cut / filter-dropped /
rank-cut / topk-cut / final) and a TITLE-ONLY classification — step3_trace.json recorded
source_id + title + score, NOT abstracts, so an on-target abstract under an off-target
title is invisible here (stated in the result).

Markers (Rule 21): ON-TARGET and CCB below. Rejected markers are listed in the result.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "step5_census.json"

ON = re.compile(r"thiazide|hydrochlorothiazide|chlorthalidone|indapamide|hypercalc|"
                r"calcium supplement|calcium carbonate|vitamin d", re.I)
CCB = re.compile(r"calcium channel|\bCCB\b|dihydropyridine|amlodipine|nifedipine|verapamil|diltiazem", re.I)
REJECTED = [
    "bare 'calcium' — matches both readings and the CCB titles (e.g. 'Calcium channel antagonists')",
    "'diuretic' — matches loop / K-sparing diuretics; the brief's set names thiazides only "
    "(the one diuretic-titled doc is flagged separately as a near-miss)",
    "'antihypertensive' / 'hypertension' — names the drug class, not either calcium reading",
]
NEAR = re.compile(r"diuretic|calcium", re.I)

# Rule 21 HAND GRADES — TITLE-LEVEL (abstracts not recorded). "interaction" = the doc's
# title addresses thiazide/antihypertensive + calcium/vit-D co-use risk (the answer the
# query needs); "topic" = calcium/vit-D supplement subject matter without that interaction.
HAND_MARKED = {
    "PMID:36902110": "topic — vitamin D AS a BP therapy; not the interaction",
    "PMID:39534319": "topic — vitamin D RCT on BP; not the interaction",
    "PMID:27287826": "topic — vitamin D3 meta-analysis on BP; not the interaction",
    "PMID:38721870": "topic — calcium supplementation in obesity; no BP-drug co-use",
    "PMID:3415787": "topic — calcium supplements used AS antihypertensives, trace-metal (dolomite) contamination; not the interaction",
}
# 3 unmarked negatives per run, title-read. None addresses the interaction BY TITLE;
# two could plausibly discuss thiazides in the abstract and are flagged, not cleared.
HAND_NEGATIVES = {
    1: {"PMID:28267687": "kidney pharmacology in HTN — may cover thiazides in abstract; FLAG, unread",
        "PMID:39539878": "magnesium review — off-target",
        "PMID:9397294": "antihypertensive x NSAID interaction — off-target"},
    2: {"PMID:3306212": "diuretics in HTN management — may cover thiazide hypercalcemia in abstract; FLAG, unread",
        "PMID:24352797": "JNC8 guideline — off-target for the interaction",
        "PMID:7598302": "nursing-home drug use — off-target"},
    3: {"PMID:39661905": "resistant-HTN pharmacology — off-target",
        "PMID:25341854": "antihypertensive PK — off-target",
        "PMID:29449338": "China HTN survey — off-target"},
    4: {"PMID:36007633": "CYP3A4 / istradefylline — off-target",
        "PMID:26764327": "garlic and heart disease — off-target",
        "PMID:9397294": "antihypertensive x NSAID interaction — off-target"},
    5: {"PMID:24352797": "JNC8 guideline — off-target for the interaction",
        "PMID:39661905": "resistant-HTN pharmacology — off-target",
        "PMID:15927106": "antihypertensive DDI review — off-target by title (the run-1 cited doc)"},
}


def main():
    tr = json.load(open(HERE / "step3_trace.json", encoding="utf-8"))
    runs = []
    for run in tr["runs"]:
        fin = {d["source_id"] for d in run.get("filter_in", [])}
        fout = {d["source_id"] for d in run.get("filter_out", [])}
        rr = {d["source_id"] for d in run.get("rerank_out", [])}
        final = {d["source_id"] for d in run["final"]}
        docs = []
        for d in run["pool_unique"]:
            sid = d["source_id"]
            if sid in final:
                fate = "final"
            elif sid not in fin:
                fate = "cut"
            elif sid not in fout:
                fate = "filter-dropped"
            elif sid not in rr:
                fate = "rank-cut"
            else:
                fate = "topk-cut"
            docs.append({**d, "fate": fate, "on_target": bool(ON.search(d["title"])),
                         "ccb": bool(CCB.search(d["title"])),
                         "near_miss": bool(NEAR.search(d["title"])) and not ON.search(d["title"])
                         and not CCB.search(d["title"])})
        on = [d for d in docs if d["on_target"]]
        cc = [d for d in docs if d["ccb"]]
        summ = {"run": run["run"], "status": run["status"], "pool": len(docs),
                "on_target_entered": len(on),
                "on_target_dropped": sum(d["fate"] != "final" for d in on),
                "on_target_kept": sum(d["fate"] == "final" for d in on),
                "ccb_entered": len(cc), "ccb_kept": sum(d["fate"] == "final" for d in cc),
                "docs": docs}
        runs.append(summ)
        print(f"run {summ['run']} ({summ['status']}) pool={summ['pool']} on-target "
              f"entered/dropped/kept={summ['on_target_entered']}/{summ['on_target_dropped']}/"
              f"{summ['on_target_kept']}  CCB entered/kept={summ['ccb_entered']}/{summ['ccb_kept']}")
        for d in docs:
            tag = "ON " if d["on_target"] else "CCB" if d["ccb"] else "~  " if d["near_miss"] else "   "
            print(f"   {tag} {d['fate']:<15} {d['score']:<6} {d['source_type']:<7} {d['source_id']:<16} {d['title'][:88]}")
    n_on = sum(r["on_target_entered"] > 0 for r in runs)
    marked = sorted({d["source_id"] for r in runs for d in r["docs"] if d["on_target"]})
    n_interaction = sum(1 for p in marked if not HAND_MARKED.get(p, "").startswith("topic"))
    inst = [(r["run"], d) for r in runs for d in r["docs"] if d["on_target"]]
    verdict_a = (f"A: NO interaction-on-target doc ever entered the pool (retrieval-side) — 0/5 runs by "
                 f"title-level hand-read. Supplement-TOPIC docs (regex-marked) entered in {n_on}/5 runs "
                 f"({len(inst)} instances, {len(marked)} distinct PMIDs); the relevance filter dropped "
                 f"{sum(d['fate'] == 'filter-dropped' for _, d in inst)}/{len(inst)} and kept "
                 f"{sum(d['fate'] == 'final' for _, d in inst)} (PMID:3415787, the dolomite paper, both times)")
    res = {"input": "step3_trace.json (5 recorded runs, HEAD 13e56fb)",
           "classification_basis": "TITLE ONLY — abstracts were not recorded by step3_trace.py",
           "markers_on_target": ON.pattern, "markers_ccb": CCB.pattern,
           "markers_rejected": REJECTED, "runs": runs,
           "runs_with_on_target_entered": n_on,
           "hand_marked": HAND_MARKED, "hand_negatives": HAND_NEGATIVES,
           "marked_that_are_interaction_on_target": n_interaction,
           "verdict_A": verdict_a}
    print(verdict_a)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("runs with an on-target doc in the pool:", n_on, "/ 5")


if __name__ == "__main__":
    main()
