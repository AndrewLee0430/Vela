"""ROUTE-MISMATCH car, STEP 3 — the FilterExempt / CutExempt door, from SAVED traces (OFFLINE, zero LLM).

For every traced run under tests/probes/bp_calcium/ (the `runs`-format traces written by step3_trace.py), each DailyMed
SAFETY section (34073-7 / 34070-3 / 43685-7 / 34066-1) in FINAL is attributed to the door it came through:
  LLM_KEPT       — the gpt-4.1-mini relevance filter kept it
  FILTER_EXEMPT  — the filter dropped it; [FilterExempt] re-added it (api/rag/retriever.py:532-543)
  + CUT_EXEMPT   — flag: it had fallen below the candidates[:max_results*4] cut and [CutExempt] re-added it (:65-77)
Route per setid = step1 census route with the step1_hand_verification overrides applied.
The E6 json files (step9 / step10_e6_*) record only FINAL + dm_safety_in_final — no stage data — so they are counted for
FINAL presence only. step10_0b_pairs.json replays step8_l0's pools (no new retrieval) and is skipped.

Usage: python tests/probes/route_mismatch/step3_exempt_door.py   → step3_exempt_door.json (same dir)
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SRC = ROOT / "tests/probes/bp_calcium"
SAFETY = {"34073-7", "34070-3", "43685-7", "34066-1"}


def routes():
    census = json.load(open(HERE / "step1_corpus_route_census.json", encoding="utf-8"))["label_routes"]
    over = json.load(open(HERE / "step1_hand_verification.json", encoding="utf-8"))["route_overrides_by_setid_title"]
    out = {}
    for sid, v in census.items():
        r = v["route"]
        for t, hand in over.items():
            if v["title"].startswith(t):
                r = "HAND:" + hand
        out[sid] = (r, v["title"])
    return out


def parse_sid(source_id):
    m = re.match(r"DailyMed:([0-9a-f-]+)#([0-9-]+)", source_id or "")
    return (m.group(1), m.group(2)) if m else (None, None)


def main():
    R = routes()
    inj = lambda r: r in ("INJ_ONLY", "MIXED_INJ_DOMINANT", "HAND:INJECTION")
    per_section = collections.defaultdict(lambda: collections.Counter())
    per_file = {}
    for f in sorted(SRC.glob("*trace*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if not isinstance(d, dict) or "runs" not in d:
            continue
        fc = collections.Counter()
        for run in d["runs"]:
            fex = set(run.get("filter_exempt_readded") or [])
            kept = {x["source_id"] for x in run.get("filter_llm_kept") or []}
            cutex = set()
            for ln in run.get("log_lines") or []:
                if ln.startswith("[CutExempt]"):
                    cutex |= set(re.findall(r"'([^']+)'", ln))
            for doc in run.get("final") or []:
                setid, loinc = parse_sid(doc.get("source_id"))
                if not setid or loinc not in SAFETY:
                    continue
                door = "FILTER_EXEMPT" if doc["source_id"] in fex else ("LLM_KEPT" if doc["source_id"] in kept else "UNATTRIBUTED")
                key = doc["source_id"]
                per_section[key]["final"] += 1
                per_section[key][door] += 1
                if doc["source_id"] in cutex:
                    per_section[key]["CUT_EXEMPT"] += 1
                fc["final_safety"] += 1
                fc[door] += 1
                if inj(R.get(setid, ("?", ""))[0]):
                    fc["final_safety_injection_route"] += 1
                    fc["inj_" + door] += 1
                    if doc["source_id"] in cutex:
                        fc["inj_CUT_EXEMPT"] += 1
            fc["runs"] += 1
        per_file[f.name] = dict(fc)
    e6 = collections.Counter()
    for f in ("step9_e6_mini.json", "step10_e6_ctl.json", "step10_e6_trt.json"):
        d = json.load(open(SRC / f, encoding="utf-8"))
        for row in d["rows"]:
            for run in row["runs"]:
                for doc in run.get("final") or []:
                    setid, loinc = parse_sid(doc.get("source_id"))
                    if setid and loinc in SAFETY:
                        e6[(row["id"], doc["source_id"], R.get(setid, ("?", ""))[0], R.get(setid, ("", "?"))[1])] += 1
    sections = []
    for sid, c in sorted(per_section.items(), key=lambda kv: -kv[1]["final"]):
        setid, loinc = parse_sid(sid)
        r, title = R.get(setid, ("?", "?"))
        sections.append({"source_id": sid, "title": title, "loinc": loinc, "route": r, **dict(c)})
    tot = collections.Counter()
    for v in per_file.values():
        tot.update(v)
    out = {"_how": __doc__.strip().splitlines()[0], "totals_runs_format": dict(tot), "per_file": per_file,
           "per_section": sections,
           "e6_final_safety": [{"q": q, "source_id": s, "route": r, "title": t, "n_runs": n} for (q, s, r, t), n in sorted(e6.items())]}
    json.dump(out, open(HERE / "step3_exempt_door.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["totals_runs_format"], indent=1))
    for s in sections:
        print(f"  {s['title'][:42]:42} {s['loinc']} {s['route'][:14]:14} final={s.get('final',0):3} llm={s.get('LLM_KEPT',0):3} "
              f"fex={s.get('FILTER_EXEMPT',0):3} cutex={s.get('CUT_EXEMPT',0):3} unattr={s.get('UNATTRIBUTED',0)}")
    print("E6 FINAL safety sections:")
    for x in out["e6_final_safety"]:
        print(f"  {x['q']:4} {x['title'][:40]:40} {x['source_id'][-8:]} {x['route'][:14]:14} n={x['n_runs']}")


if __name__ == "__main__":
    main()
