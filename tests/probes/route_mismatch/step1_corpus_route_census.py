"""ROUTE-MISMATCH car, STEP 1 — corpus route census (OFFLINE, zero LLM, zero network).

Question: which whitelisted safety sections (34073-7 / 34070-3 / 43685-7 / 34066-1) in data/dailymed/label_docs.json
come from an INJECTION-route reference label, and which substances that are commonly taken ORALLY have ONLY
injection-route safety text in the corpus?

KEYS vs TEXT (Rule 21):
  - The corpus docs carry NO route / dosage-form field (keys: content, source_id, title, url, moiety, setid, loinc, ...).
    The SPL XML carries the key (manufacturedProduct/formCode, consumedIn/substanceAdministration/routeCode), but
    scripts/build_dailymed_label_corpus.py `_section_docs_from_spl` does not extract it and no SPL cache exists locally,
    so the LABEL route here is a TEXT classifier (below) — hand-sampled, see the baton.
  - The ORAL-availability side uses a KEY: data/tfda/brand_ingredient.json `form` (劑型) of TFDA-licensed MONO
    products whose ingredient set is exactly the corpus moiety (the corpus moiety IS the TFDA backbone drug_name).

Label-route classifier (per setid): marker counts in the label's Dosage & Administration section (34068-7) if the
label has one, else across all its sections. INJ-only = injection markers > 0 and oral markers == 0; ORAL-only =
the reverse; MIXED = both; NONE = neither. MIXED is split by dominance (inj >= 3 x oral → MIXED_INJ_DOMINANT).

Usage: python tests/probes/route_mismatch/step1_corpus_route_census.py   → step1_corpus_route_census.json (same dir)
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SAFETY = {"34073-7": "interactions", "34070-3": "contraindications", "43685-7": "warnings", "34066-1": "boxed"}

INJ = re.compile(r"\b(inject(?:ion|ions|ed|able)?|intravenous(?:ly)?|infus(?:ion|ions|ed|e)|intramuscular(?:ly)?|"
                 r"subcutaneous(?:ly)?|parenteral(?:ly)?|vials?|intrathecal(?:ly)?|bolus)\b", re.I)
INJ_CS = re.compile(r"\b(IV|I\.V\.|IM|SC)\b")            # case-sensitive abbreviations
ORAL = re.compile(r"\b(oral(?:ly)?|tablets?|capsules?|by mouth|chewable|caplets?|syrup|"
                  r"granules|swallow(?:ed)?|with food|with meals)\b", re.I)
OTHER = re.compile(r"\b(topical(?:ly)?|ophthalmic|eye drops?|inhal(?:ation|ed|er)|nebuliz(?:er|ed|ation)|nasal(?:ly)?|"
                   r"transdermal|patch(?:es)?|vaginal(?:ly)?|rectal(?:ly)?|suppositor(?:y|ies)|otic|cream|ointment|lotion|gel)\b", re.I)

# TFDA 劑型 → route bucket (KEY side). Local-mouth forms (口含錠 lozenge, 口內膏, 口腔噴液劑, 漱口劑) are NOT counted as oral intake.
ORAL_FORM = re.compile(r"錠|膠囊|內服|口服|糖漿|顆粒|散劑|丸|懸液劑$|懸液用粉劑|舌下|發泡")
NOT_ORAL_FORM = re.compile(r"陰道|口含|口內膏|口腔噴|漱口|點眼|眼用|外用|注射|栓|鼻|吸入|貼|膏劑|凝膠|洗|透析")
INJ_FORM = re.compile(r"注射|點滴")


def label_route(sections):
    by_loinc = {}
    for d in sections:
        by_loinc.setdefault(d["loinc"], []).append(d["content"])
    basis = "34068-7" if "34068-7" in by_loinc else "all"
    text = "\n".join(by_loinc["34068-7"]) if basis == "34068-7" else "\n".join(c for v in by_loinc.values() for c in v)
    inj = len(INJ.findall(text)) + len(INJ_CS.findall(text))
    oral = len(ORAL.findall(text))
    other = len(OTHER.findall(text))
    if inj and not oral:
        r = "INJ_ONLY"
    elif oral and not inj:
        r = "ORAL_ONLY"
    elif inj and oral:
        r = "MIXED_INJ_DOMINANT" if inj >= 3 * oral else ("MIXED_ORAL_DOMINANT" if oral >= 3 * inj else "MIXED")
    else:
        r = "OTHER_ROUTE" if other else "NONE"
    return r, basis, {"inj": inj, "oral": oral, "other": other}


def tfda_forms():
    d = json.load(open(ROOT / "data/tfda/brand_ingredient.json", encoding="utf-8"))
    forms = collections.defaultdict(collections.Counter)
    for v in d["by_name"].values():
        sets = v.get("ingredient_sets") or []
        if v.get("is_combo") or len(sets) != 1 or len(sets[0]) != 1:
            continue
        forms[sets[0][0].strip().upper()][v.get("form") or "?"] += 1
    return forms


def tfda_bucket(counter):
    oral = sum(n for f, n in counter.items() if ORAL_FORM.search(f) and not NOT_ORAL_FORM.search(f))
    inj = sum(n for f, n in counter.items() if INJ_FORM.search(f))
    return oral, inj


def main():
    docs = json.load(open(ROOT / "data/dailymed/label_docs.json", encoding="utf-8"))["documents"]
    by_setid = collections.defaultdict(list)
    for d in docs:
        by_setid[d["setid"]].append(d)
    routes = {}
    for sid, secs in by_setid.items():
        r, basis, cnt = label_route(secs)
        routes[sid] = {"route": r, "basis": basis, "counts": cnt, "moiety": secs[0]["moiety"],
                       "title": secs[0]["title"].split(" — ")[0], "safety_loincs": sorted({s["loinc"] for s in secs if s["loinc"] in SAFETY})}
    tf = tfda_forms()
    safety_docs = [d for d in docs if d["loinc"] in SAFETY]
    sec_by_route = collections.Counter(routes[d["setid"]]["route"] for d in safety_docs)
    sec_by_route_loinc = collections.Counter((routes[d["setid"]]["route"], SAFETY[d["loinc"]]) for d in safety_docs)
    labels_by_route = collections.Counter(v["route"] for v in routes.values())
    # moiety → its labels (a moiety normally has ONE reference label; Rule 23 key sets are assembled in the baton)
    moiety_labels = collections.defaultdict(list)
    for sid, v in routes.items():
        moiety_labels[v["moiety"]].append(sid)
    inj_like = {"INJ_ONLY", "MIXED_INJ_DOMINANT"}
    mismatch = []
    for m, sids in sorted(moiety_labels.items()):
        safety_sids = [s for s in sids if routes[s]["safety_loincs"]]
        if not safety_sids or not all(routes[s]["route"] in inj_like for s in safety_sids):
            continue
        oral_n, inj_n = tfda_bucket(tf.get(m.upper(), collections.Counter()))
        mismatch.append({"moiety": m, "labels": [{"setid": s, "title": routes[s]["title"], "route": routes[s]["route"],
                                                  "counts": routes[s]["counts"], "safety": routes[s]["safety_loincs"]} for s in safety_sids],
                         "tfda_mono_oral_products": oral_n, "tfda_mono_injection_products": inj_n,
                         "tfda_forms": dict(tf.get(m.upper(), {}))})
    out = {
        "_how": __doc__.strip().splitlines()[0],
        "corpus": {"docs": len(docs), "labels": len(by_setid), "safety_section_docs": len(safety_docs)},
        "labels_by_route": dict(labels_by_route),
        "safety_section_docs_by_route": dict(sec_by_route),
        "safety_section_docs_by_route_and_type": {f"{a}|{b}": n for (a, b), n in sorted(sec_by_route_loinc.items())},
        "inj_like_safety_moieties_n": len(mismatch),
        "inj_like_safety_moieties_with_tfda_oral_mono": sum(1 for x in mismatch if x["tfda_mono_oral_products"] > 0),
        "inj_like_safety_moieties": mismatch,
        "label_routes": routes,
    }
    json.dump(out, open(HERE / "step1_corpus_route_census.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("corpus", "labels_by_route", "safety_section_docs_by_route",
                                          "inj_like_safety_moieties_n", "inj_like_safety_moieties_with_tfda_oral_mono")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
