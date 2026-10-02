"""ROUTE-MISMATCH car, STEP 2 — saved-answer marker pass (OFFLINE, zero LLM). AIDS the hand-read; it does not grade.

For every *answer*.md under tests/probes/bp_calcium/ it prints the query family + the sentences that hit a ROUTE marker
(injection vocabulary, injection-only product names) or a CALCIUM-CHLORIDE-LABEL content marker (CCB antagonism, digoxin /
arrhythmia, PTH / teriparatide / calcipotriene, ceftriaxone, ECG / during-administration monitoring). The grade per answer —
(A) route-transferred advice · (B) injection framing stated without transferring advice · (C) none — is assigned BY HAND from
these sentences (and the full answer where they are ambiguous) and recorded in step2_grades.json.

Usage: python tests/probes/route_mismatch/step2_answer_markers.py [glob-substring]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "tests/probes/bp_calcium"

E6 = {"Q1": ("calcium", "鈣片和降血壓藥可以一起吃嗎"), "Q2": ("potassium", "Can I take potassium with my BP pills?"),
      "Q3": ("calcium", "Calcium with amlodipine?"), "Q4": ("iron", "iron supplements with blood pressure medication"),
      "Q5": ("magnesium", "magnesium and diuretics elderly"), "Q6": ("vitamin D", "Can elderly take vitamin D with water pills?"),
      "Q7": ("potassium", "降血壓藥和鉀離子補充劑"), "Q8": ("other", "sugar pills with BP meds"),
      "Q9": ("other", "aspirin with BP medication elderly"), "Q10": ("other", "BP meds with grapefruit"),
      "Q11": ("calcium", "calcium and lisinopril"), "Q12": ("potassium", "potassium with spironolactone")}
EN_CHIP = ("calcium", "Can elderly patients take BP meds with calcium?")
ZH_CHIP = ("calcium", "老人血壓藥可以跟鈣片一起吃嗎？")
PAIR = ("calcium", "calcium and lisinopril")

ROUTE = re.compile(r"inject|intraven|\bI\.?V\.?\b|infus|parenteral|\bvials?\b|\bbolus\b|during administration|"
                   r"calcium chloride|calcium gluconate|iron sucrose|venofer|iron dextran|infed|magnesium sulfate|"
                   r"potassium (?:chloride|acetate) injection|dilut|注射|靜脈|點滴|氯化鈣|葡萄糖酸鈣", re.I)
CONTENT = re.compile(r"digoxin|digitalis|arrhythmi|\bECG\b|teriparatide|parathyroid|calcipotriene|ceftriaxone|"
                     r"(?:reduce|blunt|antagoni[sz]e|diminish|decrease)\w*[^.。]{0,60}(?:effect|response)|毛地黃|心律|心電圖", re.I)


def query_for(name: str):
    m = re.search(r"_(Q\d+)_", name)
    if m:
        return E6[m.group(1)]
    if "pair" in name:
        return PAIR
    if "_zh_" in name:
        return ZH_CHIP
    return EN_CHIP


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.。!?！？])\s+|\n+", text) if s.strip()]


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted(p for p in SRC.glob("*answer*.md") if flt in p.name)
    for p in files:
        fam, q = query_for(p.name)
        t = p.read_text(encoding="utf-8")
        hits = [s for s in sentences(t) if ROUTE.search(s) or CONTENT.search(s)]
        print(f"### {p.name} | {fam} | {q} | chars={len(t)} | hits={len(hits)}")
        for s in hits:
            print("   -", re.sub(r"\s+", " ", s)[:230])
    print(f"\nFILES {len(files)}")


if __name__ == "__main__":
    main()
