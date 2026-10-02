"""ROUTE-MISMATCH car, STEP 2 — HAND grades for every saved answer under tests/probes/bp_calcium/, tabulated (OFFLINE).

The grades below were assigned BY HAND (Claude Code, 2026-10-02) from step2_answer_markers.py output plus full reads of
every ambiguous answer and of a negatives sample; this script only stores and tabulates them.
  A — route-transferred advice: injection-only label content (Calcium Chloride Injection's CCB-antagonism / digoxin
      "during administration" / ECG items) forms advice to an ORAL question. A caveat ("the context does not address oral
      supplements") does NOT lift an answer out of A — the founder's 2026-10-02 13:52 re-grade of the fly-262 prod row 1
      (which carried that caveat) is the precedent; `caveat` marks those answers.
  B — injection framing stated and FENCED: the injection content is explicitly limited to IV / injectable calcium and the
      oral answer does not rest on it.
  C — none. (Potassium Chloride 34073-7 in FINAL is noted; the first version of this note called it an injection label —
      the Segment-1 SPL route key shows it is an ORAL solution label, so those potassium answers were route-MATCHED.)
Usage: python tests/probes/route_mismatch/step2_grades.py → step2_grades.json (same dir)
"""
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from step2_answer_markers import SRC, query_for  # noqa: E402

A = {
    "step10_0b_answer_run3_gpt41.md": "caveat", "step10_0b_answer_run6_gpt41.md": "", "step10_0b_answer_run7_gpt41.md": "caveat",
    "step10_0b_answer_run8_gpt41.md": "",
    **{f"step11_2b_en_l0_answer_run{i}.md": c for i, c in ((1, "caveat"), (2, ""), (3, ""), (5, ""), (6, "caveat"), (7, ""), (8, ""))},
    "step11_2b_zh_l0_answer_run3.md": "",
    "step10_ctl_en_l1_answer_run1.md": "", "step10_ctl_en_l1_answer_run2.md": "caveat", "step10_ctl_en_l1_answer_run4.md": "",
    "step10_ctl_zh_l0_answer_run1.md": "",
    **{f"step10_trt_en_l0_answer_run{i}.md": c for i, c in ((1, "caveat"), (3, ""), (4, "caveat"), (5, "caveat"), (6, ""), (7, ""), (8, ""))},
    **{f"step10_trt_en_l1_answer_run{i}.md": c for i, c in ((1, ""), (2, "caveat"), (3, ""), (4, "caveat"))},
    **{f"step7b_answer_run{i}.md": c for i, c in ((1, ""), (5, "caveat"), (6, ""), (7, ""), (8, ""))},
    **{f"step8_l0_answer_run{i}.md": "" for i in (6, 7, 8)},
    "step8_prod_smoke_answer.md": "borderline (no oral fence; 'no direct contraindication to BP medications themselves')",
    "step8_prod_smoke_answer_fly262.md": "caveat",
    "step8_zh_l0_answer_run3.md": "",
    **{f"step8_zh_l1_answer_run{i}.md": c for i, c in ((1, "caveat"), (2, ""), (3, "caveat"), (4, ""))},
}
B = {
    "step11_2b_zh_l0_answer_run1.md": "靜脈注射鈣劑 fenced; oral answer = can combine",
    "step11_2b_zh_l0_answer_run4.md": "鈣注射劑 fenced; 'oral calcium + oral CCB interaction not stated'",
    "step6_treatment_answer_run1.md": "'caution is needed if the calcium is administered intravenously'",
    "step7b_answer_run3.md": "'intravenous calcium chloride should be avoided with CCBs' — fenced",
    "step8_l0_answer_run3.md": "borderline: 'no direct contraindication ... calcium supplements in general, but ... calcium chloride require caution'",
}
C_NOTES = {"step10_ctl_en_l1_answer_run3.md": "[1] = PMID:16199918 (CCB review), not the injection label — CCB-antagonism claim for supplements is NOT route-sourced"}


def arm_of(name):
    m = re.match(r"(.*?)_answer", name)
    base = m.group(1) if m else name
    if "prod_smoke" in name:
        return "prod_smoke_fly262" if "fly262" in name else "prod_smoke_fly261"
    return base


def final_for(name):
    """FINAL DailyMed source_ids for the run behind an answer, when a trace records it."""
    m = re.match(r"(step\d+\w*?)_answer_run(\d+)", name)
    if "prod_smoke" in name:
        j = json.load(open(SRC / name.replace("_answer", "").replace(".md", ".json"), encoding="utf-8"))
        return [c["source_id"] for c in j.get("citations", []) if c["source_id"].startswith("DailyMed:")]
    if name.startswith("step10_0b"):
        run = int(re.search(r"run(\d+)", name).group(1))
        pairs = json.load(open(SRC / "step10_0b_pairs.json", encoding="utf-8"))["pairs"]
        p = [x for x in pairs if x["run"] == run]
        ids = [d if isinstance(d, str) else d["source_id"] for d in (p[0]["final"] if p else [])]
        return [s for s in ids if s.startswith("DailyMed:")]
    if m:
        f = SRC / f"{m.group(1)}_trace.json"
        if f.exists():
            runs = json.load(open(f, encoding="utf-8"))["runs"]
            r = [x for x in runs if x["run"] == int(m.group(2))]
            return [d["source_id"] for d in (r[0]["final"] if r else []) if d["source_id"].startswith("DailyMed:")]
    m = re.match(r"(step9|step10_e6_ctl|step10_e6_trt)_answer_(Q\d+)_r(\d+)", name)
    if m:
        src = {"step9": "step9_e6_mini.json", "step10_e6_ctl": "step10_e6_ctl.json", "step10_e6_trt": "step10_e6_trt.json"}[m.group(1)]
        rows = json.load(open(SRC / src, encoding="utf-8"))["rows"]
        row = [x for x in rows if x["id"] == m.group(2)]
        runs = [r for r in (row[0]["runs"] if row else []) if r["run"] == int(m.group(3))]
        return [d["source_id"] for d in (runs[0]["final"] if runs else []) if d["source_id"].startswith("DailyMed:")]
    return None


def main():
    rows = []
    for p in sorted(SRC.glob("*answer*.md")):
        fam, q = query_for(p.name)
        g = "A" if p.name in A else ("B" if p.name in B else "C")
        note = A.get(p.name) or B.get(p.name) or C_NOTES.get(p.name, "")
        fin = final_for(p.name)
        if g == "C" and fin and any("14cd12ee-a4a3-465a-9550-58c9ef0e4f21" in s for s in fin):
            note = (note + "; " if note else "") + "Potassium Chloride 34073-7 in FINAL — an ORAL solution label by the SPL key (seg1); the STEP-1 note called it an injection label, wrongly"
        rows.append({"file": p.name, "arm": arm_of(p.name), "family": fam, "query": q, "grade": g, "note": note, "final_dailymed": fin})
    table = collections.defaultdict(collections.Counter)
    fam_tot = collections.defaultdict(collections.Counter)
    for r in rows:
        table[(r["query"], r["arm"])][r["grade"]] += 1
        fam_tot[r["family"]][r["grade"]] += 1
    carried = collections.Counter()
    for r in rows:
        if r["grade"] == "A":
            for s in r["final_dailymed"] or ["(no trace)"]:
                carried[s] += 1
    out = {"_how": __doc__.strip().splitlines()[0], "n_answers": len(rows),
           "by_grade": dict(collections.Counter(r["grade"] for r in rows)),
           "by_family": {k: dict(v) for k, v in fam_tot.items()},
           "by_query_arm": [{"query": q, "arm": a, **dict(c)} for (q, a), c in sorted(table.items())],
           "dailymed_in_final_of_A_answers": dict(carried), "rows": rows}
    json.dump(out, open(HERE / "step2_grades.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("n_answers", "by_grade", "by_family", "dailymed_in_final_of_A_answers")}, ensure_ascii=False, indent=1))
    for x in out["by_query_arm"]:
        print(f"  {x['query'][:40]:40} {x['arm']:22} A={x.get('A',0)} B={x.get('B',0)} C={x.get('C',0)}")


if __name__ == "__main__":
    main()
