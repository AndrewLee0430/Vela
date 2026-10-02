"""ROUTE-MISMATCH car, Segment 1 STEP 3 — validate the route KEY sidecar (data/dailymed/label_routes.json). OFFLINE.

(a) coverage: setids with >= 1 routeCode / corpus setids (failures and no-route setids listed, never defaulted).
(b) agreement of the KEY with the STEP-1 text classifier (step1_corpus_route_census.json) on the 2,544 whitelisted safety
    sections — confusion table (unit: safety-section docs, and labels); every disagreement listed for hand-read.
(c) the probe's numbers RE-DERIVED ON THE KEY: injection-route safety sections (classifier: 770 = INJ_ONLY 573 +
    MIXED_INJ_DOMINANT 197), and the moieties whose every safety-bearing label is injection-route while TFDA licenses an oral
    mono product (classifier + hand: 67 raw → 49 after the same reductions) — like-for-like, with the delta and the members.
(d) setids whose CURRENT SPL version differs from the corpus build's (report only).

Route vocabulary → class is an EXPLICIT map (ROUTE_CLASS); a route not in it is reported as UNMAPPED, never defaulted.
Usage: python tests/probes/route_mismatch/seg1_route_key_validation.py   → seg1_route_key_validation.json (same dir)
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from step1_corpus_route_census import tfda_forms, tfda_bucket  # noqa: E402

SAFETY = {"34073-7", "34070-3", "43685-7", "34066-1"}
PARENTERAL = {"INTRAVENOUS", "INTRAMUSCULAR", "SUBCUTANEOUS", "INTRADERMAL", "INTRATHECAL", "EPIDURAL", "INTRAVITREAL",
              "INTRA-ARTICULAR", "INTRALESIONAL", "INTRACAVERNOUS", "PERINEURAL", "INFILTRATION", "INTRAVENTRICULAR",
              "INTRACARDIAC", "INTRAOSSEOUS", "INTRA-ARTERIAL", "INTRAPERITONEAL", "INTRAPLEURAL", "INTRACAVITARY",
              "SUBMUCOSAL", "INTRAOCULAR", "RETROBULBAR", "PARENTERAL", "INTRACAMERAL", "INTRATUMORAL", "SUBARACHNOID",
              "INTRASPINAL", "INTRABURSAL", "SOFT TISSUE", "INTRADISCAL", "INTRASYNOVIAL", "INTRAVASCULAR", "INTRACORONARY",
              "INTRAVENOUS DRIP", "INTRAVENOUS BOLUS", "INTRACAUDAL", "INTRALYMPHATIC", "PERIARTICULAR", "INTRAMEDULLARY",
              "SUBCONJUNCTIVAL", "INTRASINAL", "INTRACISTERNAL", "INTRAEPIDERMAL", "INTRAEPICARDIAL", "INTRAPERICARDIAL",
              "SUBRETINAL", "SUPRACHOROIDAL", "INTRATYMPANIC", "INTRAPROSTATIC", "INTRAGLANDULAR", "INTRAMUCOSAL",
              "PERCUTANEOUS", "INTRAVESICAL ", "INTRA-AMNIOTIC", "INTRACORPORUS CAVERNOSUM", "INTRAVENOUS INFUSION"}
ORAL = {"ORAL", "ENTERAL", "NASOGASTRIC", "GASTROSTOMY", "JEJUNOSTOMY"}
ORAL_MUCOSAL = {"SUBLINGUAL", "BUCCAL", "OROMUCOSAL", "OROPHARYNGEAL", "DENTAL", "PERIODONTAL", "GINGIVAL"}
OTHER = {"TOPICAL", "OPHTHALMIC", "NASAL", "RESPIRATORY (INHALATION)", "TRANSDERMAL", "VAGINAL", "RECTAL", "OTIC", "CUTANEOUS",
         "INTRAVESICAL", "URETHRAL", "INTRAUTERINE", "EXTRACORPOREAL", "INHALATION", "AURICULAR (OTIC)", "INTRABRONCHIAL",
         "ENDOTRACHEAL", "INTRAPULMONARY", "IRRIGATION", "HEMODIALYSIS", "PERCUTANEOUS ", "TRANSMUCOSAL", "INTRAVAGINAL",
         "CONJUNCTIVAL", "INTRACANALICULAR", "MUCOSAL", "SUBGINGIVAL", "INTRAORAL", "ENDOSINUSIAL", "INTERSTITIAL",
         "INTRALUMINAL", "URETERAL", "INTRADUCTAL", "INTRAGASTRIC", "INTRAPERIODONTAL", "INTRASINAL ", "TRANSTRACHEAL",
         "PERFUSION, CARDIAC", "INTRACAVITARY ", "NOT APPLICABLE", "ENDOCERVICAL", "INTESTINAL", "TRANSPLACENTAL",
         "INTRAPERIODONTAL POCKET", "INTRATUBULAR", "INTRAESOPHAGEAL", "INTRACORONAL", "INTRAMENINGEAL"}


def route_class(r):
    r = (r or "").strip().upper()
    if r in PARENTERAL:
        return "PARENTERAL"
    if r in ORAL:
        return "ORAL"
    if r in ORAL_MUCOSAL:
        return "ORAL_MUCOSAL"
    if r in OTHER:
        return "OTHER"
    return "UNMAPPED"


def key_class(routes):
    if not routes:
        return "NO_KEY"
    cl = {route_class(r) for r in routes}
    if "UNMAPPED" in cl:
        return "UNMAPPED"
    if cl == {"PARENTERAL"}:
        return "KEY_INJ_ONLY"
    if "PARENTERAL" in cl and ("ORAL" in cl or "ORAL_MUCOSAL" in cl):
        return "KEY_INJ_AND_ORAL"
    if "PARENTERAL" in cl:
        return "KEY_INJ_AND_OTHER"
    if cl <= {"ORAL", "ORAL_MUCOSAL"}:
        return "KEY_ORAL_ONLY"
    if "ORAL" in cl or "ORAL_MUCOSAL" in cl:
        return "KEY_ORAL_AND_OTHER"
    return "KEY_OTHER_ONLY"


def main():
    side = json.load(open(ROOT / "data/dailymed/label_routes.json", encoding="utf-8"))
    labels, meta = side["labels"], side["_meta"]
    census = json.load(open(HERE / "step1_corpus_route_census.json", encoding="utf-8"))
    croute = census["label_routes"]
    docs = json.load(open(ROOT / "data/dailymed/label_docs.json", encoding="utf-8"))["documents"]
    corpus_setids = sorted({d["setid"] for d in docs})

    # vocabulary
    vocab = collections.Counter(r for v in labels.values() for r in v["routes"])
    unmapped = sorted(r for r in vocab if route_class(r) == "UNMAPPED")
    kcls = {sid: key_class(labels[sid]["routes"]) if sid in labels else "NO_KEY" for sid in corpus_setids}

    # (a) coverage
    with_route = sum(1 for s in corpus_setids if s in labels and labels[s]["routes"])
    cov = {"corpus_setids": len(corpus_setids), "with_route": with_route, "coverage": round(with_route / len(corpus_setids), 4),
           "fetch_failures": meta["failures"], "no_route": meta["no_route"]}

    # (b) confusion on safety sections
    safety = [d for d in docs if d["loinc"] in SAFETY]
    conf_docs = collections.Counter((croute[d["setid"]]["route"], kcls[d["setid"]]) for d in safety)
    conf_labels = collections.Counter((croute[s]["route"], kcls[s]) for s in corpus_setids
                                      if croute[s]["safety_loincs"])
    inj_like = {"INJ_ONLY", "MIXED_INJ_DOMINANT"}
    disagree = []
    for s in corpus_setids:
        if not croute[s]["safety_loincs"]:
            continue
        c, k = croute[s]["route"], kcls[s]
        if (c in inj_like) != (k == "KEY_INJ_ONLY"):
            disagree.append({"setid": s, "title": croute[s]["title"], "moiety": croute[s]["moiety"], "classifier": c, "key": k,
                             "key_routes": labels.get(s, {}).get("routes"), "key_forms": labels.get(s, {}).get("forms"),
                             "n_safety_docs": sum(1 for d in safety if d["setid"] == s)})

    agree_docs = sum(1 for d in safety if (croute[d["setid"]]["route"] in inj_like) == (kcls[d["setid"]] == "KEY_INJ_ONLY"))
    n_lab = sum(1 for s in corpus_setids if croute[s]["safety_loincs"])
    agreement = {"injection_axis": "classifier INJ_ONLY|MIXED_INJ_DOMINANT vs KEY_INJ_ONLY",
                 "safety_docs_agree": agree_docs, "safety_docs": len(safety), "safety_docs_rate": round(agree_docs / len(safety), 4),
                 "labels_with_safety": n_lab, "labels_disagree": len(disagree),
                 "labels_rate": round(1 - len(disagree) / n_lab, 4)}
    nonhuman = sorted((croute[s]["moiety"], labels[s]["document_type"]) for s in labels
                      if "HUMAN" not in (labels[s]["document_type"] or "").upper())

    # (c) re-derived counts
    inj_key_docs = sum(1 for d in safety if kcls[d["setid"]] == "KEY_INJ_ONLY")
    any_par_docs = sum(1 for d in safety if kcls[d["setid"]] in ("KEY_INJ_ONLY", "KEY_INJ_AND_ORAL", "KEY_INJ_AND_OTHER"))
    tf = tfda_forms()
    by_m = collections.defaultdict(list)
    for s in corpus_setids:
        by_m[croute[s]["moiety"]].append(s)
    raw = []
    for m, sids in sorted(by_m.items()):
        ss = [s for s in sids if croute[s]["safety_loincs"]]
        if not ss or not all(kcls[s] == "KEY_INJ_ONLY" for s in ss):
            continue
        oral_n, inj_n = tfda_bucket(tf.get(m.upper(), collections.Counter()))
        if oral_n > 0:
            raw.append(m)
    # same reductions as the probe: sibling key (same first token) with a NON-injection safety label (by KEY), and the
    # entity rule for keys whose substance has oral safety text under a different first token (IRON→FERRIC CITRATE,
    # ZINC→ZINC ACETATE DIHYDRATE — the probe's hand-verified pair; applied only if still present)
    ORAL_CLASSES = ("KEY_ORAL_ONLY", "KEY_INJ_AND_ORAL", "KEY_ORAL_AND_OTHER")   # the probe removed only for an ORAL sibling
    SALT = {"SODIUM", "CALCIUM", "POTASSIUM", "MAGNESIUM", "ZINC", "IRON", "DISODIUM"}
    reduced, removed = [], {}
    for m in raw:
        tok = m.split()[0]
        sib = [o for o in by_m if o != m and o.split()[0] == tok and tok not in SALT
               and any(croute[s]["safety_loincs"] and kcls[s] in ORAL_CLASSES for s in by_m[o])]
        if sib:
            removed[m] = "sibling key with an ORAL-route safety label (by KEY): " + ", ".join(sib)
        elif m in ("IRON", "ZINC"):
            removed[m] = "entity has oral safety text under another key (probe hand-verification)"
        else:
            reduced.append(m)
    probe = json.load(open(HERE / "step1_hand_verification.json", encoding="utf-8"))["others_surfaced"]
    probe49 = {x.split(" (")[0] for x in probe["injection_only_with_tfda_oral"]}
    out = {
        "_how": __doc__.strip().splitlines()[0],
        "route_vocabulary": dict(vocab.most_common()), "route_class_map_unmapped": unmapped,
        "a_coverage": cov,
        "b_confusion_safety_docs": {f"{c}|{k}": n for (c, k), n in sorted(conf_docs.items())},
        "b_confusion_labels_with_safety": {f"{c}|{k}": n for (c, k), n in sorted(conf_labels.items())},
        "b_agreement": agreement,
        "b_disagreements": disagree,
        "c_injection_route_safety_docs_on_key": {"KEY_INJ_ONLY": inj_key_docs, "any_parenteral_route": any_par_docs,
                                                 "classifier_inj_like_was": 770, "of": len(safety)},
        "c_moieties_raw_on_key": raw, "c_moieties_raw_on_key_n": len(raw), "classifier_raw_was": 67,
        "c_moieties_reduced_on_key": reduced, "c_moieties_reduced_on_key_n": len(reduced), "probe_reduced_was": 49,
        "c_reductions": removed,
        "c_vs_probe49": {"added_on_key": sorted(set(reduced) - probe49), "dropped_on_key": sorted(probe49 - set(reduced))},
        "d_spl_version_mismatch": sum(1 for s in corpus_setids if s in labels and labels[s]["corpus_spl_version_match"] is False),
        "d_document_types": dict(collections.Counter(v["document_type"] for v in labels.values())),
        "d_non_human_document_type": nonhuman,
    }
    json.dump(out, open(HERE / "seg1_route_key_validation.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("a_coverage",)}, ensure_ascii=False, indent=1)[:900])
    print("UNMAPPED routes:", unmapped)
    print("vocab:", dict(vocab.most_common()))
    print("(b) confusion, safety docs:")
    for k, n in out["b_confusion_safety_docs"].items():
        print(f"   {k:45} {n}")
    print("(b) disagreements (labels with safety):", len(disagree), "| agreement", agreement)
    print("(c)", out["c_injection_route_safety_docs_on_key"], "| raw", len(raw), "| reduced", len(reduced), "| vs probe49", out["c_vs_probe49"])
    print("(d) version mismatch", out["d_spl_version_mismatch"], "| doc types", out["d_document_types"])


if __name__ == "__main__":
    main()
