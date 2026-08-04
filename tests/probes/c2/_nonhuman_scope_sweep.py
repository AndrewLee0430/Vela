# -*- coding: utf-8 -*-
"""Item 1.1 — is the "15 non-human references" figure a FLOOR or the TOTAL?

The 15 were found by SPL **document type** (neither 34391-3 nor 34390-5). That misses any
veterinary / non-drug product carrying a HUMAN doctype. This sweeps all 1036 pinned
references by TITLE and SECTION TEXT for species / animal-dosage-form / supplement evidence,
then reports what is found OUTSIDE the original 15.

READ-ONLY, offline, zero cost. Sources:
  tests/results/c2_ea_fetch.json   (1036 pinned refs, all sections, doctype)
  data/dailymed/label_docs.json    (what is actually INDEXED and citable today)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\andre\projects\Vela")
FETCH = ROOT / "tests/results/c2_ea_fetch.json"
SHIP = ROOT / "data/dailymed/label_docs.json"
OUT = ROOT / "tests/results/nonhuman_scope.json"
WHITELIST = {"34073-7", "34070-3", "43685-7", "34066-1"}
HUMAN_DOCTYPES = {"34391-3", "34390-5"}

# ── evidence markers. Deliberately conservative: each is a phrase that does not occur in
# ordinary human-label prose. Species words are required in an ANIMAL-USE context, because
# "canine" etc. appear in human labels (e.g. "canine studies") — so species alone is NOT used.
# ⚠️ MARKERS TIGHTENED after a first pass produced obvious false positives. REJECTED markers,
# recorded so they are not re-added: `bolus` (standard HUMAN IV dosing — matched 40+ human
# oncology/anaesthesia labels), `drinking water` (human "take with water" prose), and
# `premix` (LEVAQUIN / moxifloxacin "premix" = a premixed IV bag, NOT medicated feed).
# Only phrases that do not occur in ordinary human-label prose are kept.
VET_STRONG = [
    r"\bfor animal use only\b", r"\bnot for human use\b",
    r"restricts this drug to use by or on the order of a licensed veterinarian",
    r"\bfor use in animals\b", r"\bconsult your veterinarian\b", r"\bveterinary use\b",
    r"\bdrench\b", r"\bmedicated feed\b", r"\btype [abc] medicated\b",
    r"\bfor oral use in (cattle|swine|horses|dogs|cats|poultry|sheep|calves)\b",
    r"\bin (cattle|swine|horses|dogs|cats|poultry|sheep|calves|broiler chickens)\b",
    r"\b(equine|bovine|porcine|canine|feline|avian) (use|species)\b",
    r"\bmilk withdrawal\b", r"\bslaughter withdrawal\b", r"\bwithdrawal period\b",
]
VET_WEAK = [r"\bveterinarian\b", r"\bcattle\b", r"\bswine\b", r"\bpoultry\b",
            r"\bbroiler\b", r"\bheifer", r"\bfoal\b", r"\bmare\b", r"\bstallion\b"]
SUPP = [r"\bdietary supplement\b", r"\bthese statements have not been evaluated\b",
        r"\bnot intended to diagnose, treat, cure\b", r"\bmedical food\b",
        r"\bfor the dietary management of\b"]


def hits(pats, text):
    return sorted({p for p in pats if re.search(p, text, re.I)})


def main():
    if not FETCH.exists():
        print("⚠️ c2_ea_fetch.json ABSENT — cannot run. Rule 18: sweep NOT performed.")
        sys.exit(1)
    fetch = json.loads(FETCH.read_text(encoding="utf-8"))
    ship = json.loads(SHIP.read_text(encoding="utf-8"))["documents"]
    ship_by_setid = defaultdict(list)
    for d in ship:
        ship_by_setid[d["setid"]].append(d)

    rows = []
    for lab in fetch["labels"]:
        docs = lab.get("docs") or []
        title = ""
        for d in docs:
            title = d.get("title", "")
            break
        # search the label's own text: title + indications + dosage (where use-context lives)
        body = " ".join((d.get("content") or "")[:4000] for d in docs
                        if d.get("loinc") in ("34067-9", "34068-7"))
        hay = f"{title} {body}"
        vs_, vw, sp = hits(VET_STRONG, hay), hits(VET_WEAK, hay), hits(SUPP, hay)
        if not (vs_ or vw or sp):
            continue
        indexed = ship_by_setid.get(lab["setid"], [])
        secs = sorted({x["loinc"] for x in indexed})
        rows.append({
            "moiety": lab["moiety"], "setid": lab["setid"], "title": title,
            "doctype_code": lab["doctype_code"], "doctype": lab["doctype"],
            "human_doctype": lab["doctype_code"] in HUMAN_DOCTYPES,
            "indexed_sections": secs,
            "safety_sections": sorted(set(secs) & WHITELIST),
            "citable_as_safety": bool(set(secs) & WHITELIST),
            "vet_strong": vs_, "vet_weak": vw, "supplement": sp,
        })

    orig15 = [l["setid"] for l in fetch["labels"] if l["doctype_code"] not in HUMAN_DOCTYPES]
    print("=" * 104)
    print("ITEM 1.1 — non-human / non-drug scope sweep over %d pinned references" % len(fetch["labels"]))
    print("=" * 104)
    print(f"original doctype-based set (the '15'): {len(orig15)}")
    print(f"flagged by TITLE/TEXT evidence      : {len(rows)}")
    print()

    strong = [r for r in rows if r["vet_strong"]]
    outside = [r for r in rows if r["setid"] not in orig15]
    out_strong = [r for r in strong if r["setid"] not in orig15]
    print(f"  with STRONG veterinary evidence            : {len(strong)}")
    print(f"  flagged OUTSIDE the original 15            : {len(outside)}")
    print(f"  ...of those, STRONG veterinary evidence    : {len(out_strong)}   <<< the key number")
    print()

    def show(title, items):
        print("-" * 104)
        print(title)
        print("-" * 104)
        if not items:
            print("   (none)")
            return
        for r in sorted(items, key=lambda x: (not x["citable_as_safety"], x["moiety"] or "")):
            flag = "🔴 CITABLE-SAFETY" if r["citable_as_safety"] else "   indexed-only "
            hd = "human-doctype" if r["human_doctype"] else f"doctype {r['doctype_code']}"
            print(f" {flag} {(r['moiety'] or '')[:26]:<26} {hd:<15} {r['title'][:44]:<44} "
                  f"safety={r['safety_sections'] or '-'}")
            ev = (r["vet_strong"] or r["vet_weak"] or r["supplement"])[:3]
            print(f"      evidence: {ev}")

    show("A. OUTSIDE the original 15, STRONG veterinary evidence", out_strong)
    show("B. OUTSIDE the original 15, weak/supplement evidence only", [r for r in outside if r not in out_strong])
    show("C. INSIDE the original 15 (doctype-flagged), with title/text evidence",
         [r for r in rows if r["setid"] in orig15])

    OUT.write_text(json.dumps({"pinned": len(fetch["labels"]), "doctype_set": len(orig15),
                               "flagged": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


main()
