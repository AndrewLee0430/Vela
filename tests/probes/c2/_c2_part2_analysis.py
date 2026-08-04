# -*- coding: utf-8 -*-
"""c2 Phase-1b Part 2 — E-A's true blast radius. OFFLINE, from tests/results/c2_ea_fetch.json."""
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\andre\projects\Vela")
FETCH = ROOT / "tests/results/c2_ea_fetch.json"
SHIPPED = ROOT / "data/dailymed/label_docs.json"
L = "34071-1"
WHITELIST = {"34073-7", "34070-3", "43685-7", "34066-1"}

f = json.loads(FETCH.read_text(encoding="utf-8"))
labels = f["labels"]
shipped = json.loads(SHIPPED.read_text(encoding="utf-8"))["documents"]

print("=" * 92)
print("PART 2 — E-A blast radius (offline)")
print("=" * 92)
print(f"pinned setids fetched OK : {f['ok']} / {f['pinned_setids']}   FAILED: {f['failed']}")
if f["failed"]:
    print(f"  ⚠️ FAILURES ({f['failed']}): {json.dumps(f['failures'][:8], ensure_ascii=False)}")
print()

# ── how many labels carry 34071-1, and the char distribution
have, chars, by_dt = [], [], defaultdict(list)
for lab in labels:
    n1 = [d for d in lab["docs"] if d["loinc"] == L]
    if not n1:
        continue
    c = sum(len(d["content"]) for d in n1)   # sum over chunks of that section
    have.append(lab)
    chars.append(c)
    by_dt[lab["doctype"]].append(c)

n_lab = len(labels)
print(f"--- labels carrying a {L} section: {len(have)} / {n_lab}  ({100*len(have)/n_lab:.1f}%) ---")
if chars:
    cs = sorted(chars)
    print(f"    chars  min {cs[0]}  median {int(st.median(cs))}  "
          f"p90 {cs[int(.9*len(cs))-1]}  max {cs[-1]}  TOTAL {sum(cs):,}")
    print()
    print("    histogram (chars):")
    buckets = [(0, 249), (250, 499), (500, 999), (1000, 1999), (2000, 3999), (4000, 9999), (10000, 10**9)]
    for lo, hi in buckets:
        k = sum(1 for c in cs if lo <= c <= hi)
        lab = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        bar = "█" * max(0, round(40 * k / max(1, len(cs))))
        print(f"      {lab:>12} {k:4d}  {bar}")
print()

print("--- SPLIT BY DOCTYPE (the independent finding) ---")
tot_dt = Counter(l["doctype"] for l in labels)
for dt in ("Rx", "OTC", "?"):
    if dt not in tot_dt and dt not in by_dt:
        continue
    n = len(by_dt.get(dt, []))
    print(f"    {dt:<3}  labels total {tot_dt.get(dt,0):4d} | carrying {L}: {n:4d} "
          f"({100*n/max(1,tot_dt.get(dt,0)):.1f}%) | chars total {sum(by_dt.get(dt,[])):,}")
rx = by_dt.get("Rx", [])
if rx:
    rs = sorted(rx)
    print(f"\n    🔴 PRESCRIPTION labels silently dropping warnings TODAY: {len(rs)}")
    print(f"       chars min {rs[0]} median {int(st.median(rs))} max {rs[-1]} TOTAL {sum(rs):,}")
print()

# ── documents + chars E-A would ADD
new_docs = [d for lab in labels for d in lab["docs"] if d["loinc"] == L]
print(f"--- E-A would ADD: {len(new_docs)} documents, {sum(len(d['content']) for d in new_docs):,} chars ---")
print(f"    (shipped corpus today: {len(shipped)} docs) -> "
      f"{len(shipped)+len(new_docs)} docs, +{100*len(new_docs)/len(shipped):.1f}%")
print()

# ── moieties gaining their FIRST safety section
ship_by_moiety = defaultdict(set)
for d in shipped:
    ship_by_moiety[(d.get("moiety") or "").upper()].add(d["loinc"])
zero = {m for m, ls in ship_by_moiety.items() if not (ls & WHITELIST)}
gain = set()
for lab in labels:
    m = (lab["moiety"] or "").upper()
    if m in zero and any(d["loinc"] == L for d in lab["docs"]):
        gain.add(m)
print(f"--- moieties with ZERO whitelisted safety sections today: {len(zero)} ---")
print(f"    ...of which would GAIN their first via {L}: {len(gain)}  "
      f"({100*len(gain)/max(1,len(zero)):.1f}%)")
print(f"    ...still zero after E-A: {len(zero-gain)}")
print()

# ── staleness signal: do re-parsed non-34071-1 docs match the shipped ones?
reparsed = {(d["source_id"]): d["content"] for lab in labels for d in lab["docs"] if d["loinc"] != L}
shipmap = {d["source_id"]: d["content"] for d in shipped}
only_ship = set(shipmap) - set(reparsed)
only_new = set(reparsed) - set(shipmap)
diff = [k for k in (set(shipmap) & set(reparsed)) if shipmap[k] != reparsed[k]]
print("--- SNAPSHOT STALENESS (re-parse of the SAME pinned setids vs the shipped corpus) ---")
print(f"    shipped-only source_ids : {len(only_ship)}")
print(f"    new-only source_ids     : {len(only_new)}")
print(f"    same id, CONTENT DIFFERS: {len(diff)}")
print("    ⚠️ non-zero => DailyMed changed those labels since the pinned snapshot "
      "(a staleness finding, independent of c2)")

out = {
    "labels_total": n_lab, "labels_with_34071_1": len(have),
    "chars_total": sum(chars), "by_doctype": {k: {"n": len(v), "chars": sum(v)} for k, v in by_dt.items()},
    "doctype_totals": dict(tot_dt),
    "new_docs": len(new_docs), "new_chars": sum(len(d["content"]) for d in new_docs),
    "shipped_docs": len(shipped),
    "moieties_zero_safety": len(zero), "moieties_gaining_first": len(gain),
    "staleness": {"shipped_only": len(only_ship), "new_only": len(only_new), "content_differs": len(diff)},
}
(ROOT / "tests/results/c2_part2_summary.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n-> tests/results/c2_part2_summary.json")
