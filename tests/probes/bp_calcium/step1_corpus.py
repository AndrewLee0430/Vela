"""STEP 1 (H8) — does the shipped corpus contain thiazide-class label text naming calcium?

Corpus-only, zero LLM / network calls. Reads data/dailymed/label_docs.json and
data/tfda/indication_corpus.json exactly as shipped at the probe HEAD.

Key set (Rule 23): the moiety set is derived, NOT typed — every doc whose `moiety`
starts with one of the thiazide-class INN bases below, PLUS every doc whose `title`
names one (catches a label keyed under a different moiety string). The full derived
key set is written to the result so the conclusion can be checked against it.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "step1_corpus.json"

BASES = ["HYDROCHLOROTHIAZIDE", "CHLORTHALIDONE", "CHLORTALIDONE", "INDAPAMIDE",
         "METOLAZONE", "CHLOROTHIAZIDE", "BENDROFLUMETHIAZIDE", "METHYCLOTHIAZIDE",
         "TRICHLORMETHIAZIDE", "POLYTHIAZIDE", "HYDROFLUMETHIAZIDE", "CYCLOPENTHIAZIDE"]
SAFETY = {"34073-7", "43685-7", "34070-3", "34066-1"}
PAT = re.compile(r"calcium|hypercalc|vitamin\s*d", re.I)


def sentences_with(text, n=3):
    out = []
    for s in re.split(r"(?<=[.;])\s+", text):
        if PAT.search(s):
            out.append(s.strip()[:500])
            if len(out) >= n:
                break
    return out


def main():
    docs = json.load(open(ROOT / "data/dailymed/label_docs.json", encoding="utf-8"))["documents"]
    all_moieties = sorted({d.get("moiety", "") for d in docs})
    # Rule 23: derived key set — moiety prefix-match on the INN base (word-boundary, so
    # CHLOROTHIAZIDE does not match HYDROCHLOROTHIAZIDE) + a title sweep.
    key_re = re.compile(r"^(" + "|".join(BASES) + r")\b")
    title_re = re.compile(r"\b(" + "|".join(BASES) + r")\b", re.I)
    moiety_keys = [m for m in all_moieties if key_re.search(m)]
    title_hit_moieties = sorted({d["moiety"] for d in docs if title_re.search(d.get("title", ""))})
    key_set = sorted(set(moiety_keys) | set(title_hit_moieties))
    absent_bases = [b for b in BASES if not any(k.startswith(b) for k in key_set)]

    rows = []
    for d in docs:
        if d.get("moiety") not in key_set:
            continue
        loinc = d.get("loinc")
        row = {"moiety": d["moiety"], "source_id": d["source_id"], "title": d["title"],
               "loinc": loinc, "marketing_category": d.get("marketing_category"),
               "content_chars": len(d["content"])}
        if loinc in SAFETY:
            row["calcium_sentences"] = sentences_with(d["content"])
        rows.append(row)

    # TFDA indication corpus — calcium is not expected in an indication text.
    tf = json.load(open(ROOT / "data/tfda/indication_corpus.json", encoding="utf-8"))
    tdocs = tf["documents"] if isinstance(tf, dict) and "documents" in tf else tf
    tfda_thiazide = [t for t in tdocs if title_re.search(json.dumps(t, ensure_ascii=False))]
    tfda_hits = []
    for t in tfda_thiazide:
        c = t.get("content", "")
        ss = sentences_with(c)
        if ss:
            tfda_hits.append({"source_id": t.get("source_id"), "title": t.get("title"), "sentences": ss})

    # REVERSE SIDE (not in the brief; added because the thiazide side came back empty):
    # calcium / vitamin-D labels that name thiazides. Key set = every moiety containing
    # CALCIUM or a vitamin-D INN, listed in the result. Word "CALCIUM" as a SALT suffix
    # (ROSUVASTATIN CALCIUM, LEUCOVORIN CALCIUM, ...) is EXCLUDED by requiring the moiety
    # to START with CALCIUM or be a vitamin-D analogue — the rejected-marker list is in
    # the result (Rule 21).
    vitd = ("CHOLECALCIFEROL", "ERGOCALCIFEROL", "CALCITRIOL", "PARICALCITOL", "CALCIFEDIOL",
            "DOXERCALCIFEROL", "ALFACALCIDOL")
    ca_keys = [m for m in all_moieties if m.startswith("CALCIUM") or m.startswith(vitd)]
    rejected_ca = [m for m in all_moieties if "CALC" in m and m not in ca_keys]
    thz = re.compile(r"thiazide", re.I)
    reverse = []
    for d in docs:
        if d.get("moiety") not in ca_keys:
            continue
        ss = [s.strip()[:400] for s in re.split(r"(?<=[.;])\s+", d["content"]) if thz.search(s)]
        reverse.append({"moiety": d["moiety"], "source_id": d["source_id"], "title": d["title"],
                        "loinc": d.get("loinc"), "marketing_category": d.get("marketing_category"),
                        "content_chars": len(d["content"]), "thiazide_sentences": ss[:3]})

    n_with = sum(1 for r in rows if r.get("calcium_sentences"))
    n_rev = sum(1 for r in reverse if r["thiazide_sentences"])
    verdict = (f"H8 (thiazide side): {'EXISTS (%d docs)' % n_with if n_with else 'ABSENT'} — "
               f"H8 (calcium/vit-D side): thiazide named in {n_rev} docs")
    res = {"key_set_used": key_set, "bases_searched": BASES, "bases_absent_as_moiety": absent_bases,
           "title_hit_moieties": title_hit_moieties, "dailymed_docs": rows,
           "tfda_thiazide_docs": len(tfda_thiazide), "tfda_calcium_hits": tfda_hits,
           "reverse_key_set": ca_keys, "reverse_rejected_moieties": rejected_ca,
           "reverse_side_docs": reverse, "verdict": verdict}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
