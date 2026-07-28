# -*- coding: utf-8 -*-
"""Tasks 2-4 — validate the candidate fix discriminator OFFLINE against ALL pooled data.

DISCRIMINATOR UNDER TEST: does the cited section's TEXT mention a drug named in the query?
Precedent in this project: POTASSIUM CHLORIDE's interactions section named spironolactone
(legitimate counterpart citation) while POTASSIUM ACETATE's contraindications did not
(intrusion). The pair-aware bilateral finding DEPENDS on counterpart sections being KEPT,
so a discriminator that drops them is wrong.

Data reused (zero API cost):
  - pair-aware M1            tests/results/pairaware_m1_*.json        (10 queries x N=8)
  - Phase-1 single-drug      tests/results/otc_singledrug_*.json      (6 queries x N=3)
  - severity probe           tests/results/severity_probe*.json       (6 queries, full answers)
  - today's §2.7 gate        tests/results/golden_results_20260728_114818.json (20 cases, pool_identity)

READ-ONLY.
"""
import io, json, re, sys, glob
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
OUT = ROOT / "tests" / "results" / "discriminator_validation.json"
SAFETY = {"34073-7", "34070-3", "34066-1", "43685-7"}

_c = json.load(open(ROOT / "data" / "dailymed" / "label_docs.json", encoding="utf-8"))["documents"]
BY_SID = {d["source_id"].split("~")[0]: d for d in _c}
SETID2MOIETY = {d["setid"]: d["moiety"] for d in _c if d.get("setid")}
MOIETIES = sorted({d["moiety"] for d in _c if d.get("moiety")})
NO_SAFETY = {m for m in MOIETIES
             if not ({d.get("loinc") for d in _c if d.get("moiety") == m} & SAFETY)}

SALT = {"SODIUM","POTASSIUM","CALCIUM","HYDROCHLORIDE","HCL","SULFATE","MALEATE","ACETATE",
        "CITRATE","TARTRATE","SUCCINATE","FUMARATE","MESYLATE","BESYLATE","PHOSPHATE",
        "CARBONATE","OXALATE","HYDROBROMIDE","BROMIDE","CHLORIDE","LYSINE","HEMIFUMARATE",
        "HEMIHYDRATE","DIHYDRATE","MONOHYDRATE","ACID","ANHYDROUS","GEL","EXTRACT"}


def query_drugs(q):
    """Drug tokens named in the query (>=5 chars, matched against the moiety index)."""
    ql = " " + q.lower() + " "
    found = set()
    for m in MOIETIES:
        for part in re.split(r"[^A-Z0-9]+", m):
            if len(part) >= 5 and part not in SALT:
                if re.search(r"(?<![a-z])" + re.escape(part.lower()) + r"(?![a-z])", ql):
                    found.add(part)
    return found


def dm_safety(sid):
    return sid.startswith("DailyMed:") and "#" in sid and \
        sid.split("#", 1)[1].split("~", 1)[0] in SAFETY


def classify(sid, qdrugs):
    """-> (verdict, moiety). Verdicts:
       ON-TARGET      section's own moiety is a query drug
       MENTIONS-QUERY section is another drug's BUT its text names a query drug (counterpart)
       INTRUSION      neither
    """
    setid = sid.split("DailyMed:", 1)[1].split("#", 1)[0]
    mo = SETID2MOIETY.get(setid, "")
    if any(d in mo for d in qdrugs):
        return "ON-TARGET", mo
    text = (BY_SID.get(sid.split("~")[0]) or {}).get("content", "").lower()
    if any(d.lower() in text for d in qdrugs):
        return "MENTIONS-QUERY", mo
    return "INTRUSION", mo


def harvest():
    """-> list of (dataset, case, query, kind, sid) for every cited DailyMed safety section."""
    rows = []
    # pair-aware M1 (PAIR queries)
    for f in glob.glob(str(ROOT / "tests/results/pairaware_m1_*.json")):
        if "content_audit" in f:
            continue
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("complete"):
            continue
        for cid, e in d.get("queries", {}).items():
            for r in e["runs"]:
                for c in r.get("cited_safety", []):
                    rows.append(("pairaware", cid, e["query"], "PAIR", c["source_id"]))
    # Phase-1 single-drug
    for f in glob.glob(str(ROOT / "tests/results/otc_singledrug_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for cid, e in d.get("cases", {}).items():
            for r in e["runs"]:
                for sid in r.get("dailymed_safety_docs", []):
                    rows.append(("otc", cid, e["query"], "SINGLE", sid))
    # severity probe
    for f in glob.glob(str(ROOT / "tests/results/severity_probe*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for cid, e in d.get("cases", {}).items():
            for p in e.get("pool", []):
                if p.get("source_id") and dm_safety(p["source_id"]):
                    rows.append(("severity", cid, e["query"], "SINGLE", p["source_id"]))
    # today's §2.7 gate (mixed)
    g = ROOT / "tests/results/golden_results_20260728_114818.json"
    if g.exists():
        d = json.load(open(g, encoding="utf-8"))
        for r in d.get("results", []):
            pi = r.get("pool_identity")
            if not pi:
                continue
            for sid in pi["pool_ids"]:
                if dm_safety(sid):
                    rows.append(("gate", r["id"], "", "GATE", sid))
    return rows


def main():
    # queries per case (gate rows have no query text in the JSON — pull from the dataset)
    gd = json.load(open(ROOT / "tests/golden_dataset.json", encoding="utf-8"))
    gcases = {c["id"]: c.get("query", "") for c in (gd if isinstance(gd, list) else gd.get("cases", []))}

    rows = harvest()
    out, tally = [], Counter()
    for ds, cid, q, kind, sid in rows:
        q = q or gcases.get(cid, "")
        qd = query_drugs(q)
        verdict, mo = classify(sid, qd)
        keep = verdict in ("ON-TARGET", "MENTIONS-QUERY")   # discriminator decision
        out.append({"dataset": ds, "case": cid, "kind": kind, "query": q[:70],
                    "query_drugs": sorted(qd), "moiety": mo, "verdict": verdict,
                    "discriminator_keeps": keep, "source_id": sid,
                    "moiety_lacks_safety": mo in NO_SAFETY})
        tally[(kind, verdict)] += 1

    print(f"cited DailyMed safety sections analysed: {len(out)}\n")
    print(f"{'query kind':10} {'ON-TARGET':>10} {'MENTIONS-QUERY':>15} {'INTRUSION':>10}")
    print("-" * 50)
    for kind in ("PAIR", "SINGLE", "GATE"):
        print(f"{kind:10} {tally[(kind,'ON-TARGET')]:>10} {tally[(kind,'MENTIONS-QUERY')]:>15} "
              f"{tally[(kind,'INTRUSION')]:>10}")

    print("\n=== TASK 2: discriminator behaviour ===")
    pair_rows = [r for r in out if r["kind"] == "PAIR"]
    pair_drop = [r for r in pair_rows if not r["discriminator_keeps"]]
    print(f"PAIR sections kept:    {sum(1 for r in pair_rows if r['discriminator_keeps'])}/{len(pair_rows)}"
          f"   (must be high — bilateral finding depends on it)")
    print(f"PAIR sections DROPPED: {len(pair_drop)}  <- false positives if these were legitimate")
    for r in pair_drop[:8]:
        print(f"    {r['case']:20} {r['moiety']:28} qdrugs={r['query_drugs']}")
    sing = [r for r in out if r["kind"] == "SINGLE"]
    sing_rej = [r for r in sing if not r["discriminator_keeps"]]
    print(f"\nSINGLE-drug sections REJECTED: {len(sing_rej)}/{len(sing)}  (the defect it must catch)")
    for r in sing_rej[:10]:
        print(f"    {r['case']:20} {r['moiety']:28} qdrugs={r['query_drugs']}")
    sing_keep = [r for r in sing if r["discriminator_keeps"]]
    print(f"\nSINGLE-drug sections KEPT: {len(sing_keep)}  <- check each is genuinely on/near target")
    for r in sing_keep[:10]:
        print(f"    {r['case']:20} {r['verdict']:15} {r['moiety']:28}")

    print("\n=== TASK 4: do intrusions concentrate on no-safety-section moieties? ===")
    intr = [r for r in out if r["verdict"] == "INTRUSION"]
    q_nosafe = sum(1 for r in intr if any(d in NO_SAFETY or any(d in m for m in NO_SAFETY)
                                          for d in r["query_drugs"]))
    print(f"INTRUSION rows: {len(intr)}")
    print(f"  ...where a QUERY drug is among the 128 no-safety moieties: {q_nosafe}")
    print(f"  (128/1038 = 12.3% of moieties lack any safety section)")

    print("\n=== CJK / mixed-script degradation (M5 cross-ref) ===")
    cjk = [r for r in out if re.search(r"[\u4e00-\u9fff]", r["query"] or "")]
    print(f"rows with CJK in the query: {len(cjk)}; of these, query_drugs EMPTY: "
          f"{sum(1 for r in cjk if not r['query_drugs'])}")
    for r in cjk[:5]:
        print(f"    {r['case']:10} qdrugs={r['query_drugs']}  {r['query'][:44]}")

    OUT.write_text(json.dumps({"rows": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
