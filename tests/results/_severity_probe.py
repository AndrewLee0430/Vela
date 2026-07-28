# -*- coding: utf-8 -*-
"""Task 1 — SEVERITY: does the ANSWER assert off-target content, or only mis-cite?

Phase 1 measured which drug the CITED SECTION belongs to. It did NOT measure whether the
generated ANSWER is wrong. That distinction sets the severity class:
  - answer ASSERTS content about the queried drug that is sourced from ANOTHER drug's label
    -> live medical misinformation (🔴 incident)
  - answer correctly ignores the off-target doc, leaving a misattributed source chip only
    -> citation-integrity defect (serious, different class)

Captures the FULL answer text + the citation pool + the off-target docs' actual content so a
human can adjudicate with both sides quoted. Deliberately does NOT auto-classify: inferring
severity from the citation alone would repeat the fly-211 any-drug metric failure (Rule 17).

READ-ONLY: talks to a local TEST_MODE server over HTTP; changes nothing.
"""
import io, json, os, sys, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

BASE = os.environ.get("SEV_BASE", "http://127.0.0.1:8001")
OUT = ROOT / "tests" / "results" / f"severity_probe_{time.strftime('%Y%m%d_%H%M%S')}.json"
SAFETY_LOINC = {"34073-7", "34070-3", "34066-1", "43685-7"}

_corpus = json.load(open(ROOT / "data" / "dailymed" / "label_docs.json", encoding="utf-8"))["documents"]
BY_SID = {d["source_id"].split("~")[0]: d for d in _corpus}
SETID2MOIETY = {d["setid"]: d["moiety"] for d in _corpus if d.get("setid")}

QUERIES = [
    ("aspirin_contra",    "aspirin contraindications and who should not take it", ["ASPIRIN", "ACETYLSALICYLIC"]),
    ("ibuprofen_warn",    "ibuprofen warnings and precautions",                   ["IBUPROFEN"]),
    ("naproxen_inter",    "naproxen drug interactions",                           ["NAPROXEN"]),
    ("cimetidine_inter",  "cimetidine drug interactions",                         ["CIMETIDINE"]),
    ("omeprazole_contra", "omeprazole contraindications",                         ["OMEPRAZOLE", "ESOMEPRAZOLE"]),
    ("loperamide_warn",   "loperamide warnings and safety",                       ["LOPERAMIDE"]),
]


def call(q):
    """POST /api/research, return (answer_text, citations[])."""
    answer, cites = "", []
    with httpx.Client(timeout=900.0) as c:
        r = c.post(f"{BASE}/api/research", json={"question": q},
                   headers={"Content-Type": "application/json"})
        r.raise_for_status()
        for line in r.text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "answer":
                answer += ev.get("content", "")
            elif ev.get("type") == "citations":
                cites = ev.get("content") or []
    return answer.strip(), cites


def dm_safety(sid):
    return sid.startswith("DailyMed:") and "#" in sid and \
        sid.split("#", 1)[1].split("~", 1)[0] in SAFETY_LOINC


def main():
    rep = {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "cases": {}}
    for cid, q, targets in QUERIES:
        print(f"\n{'='*100}\n### {cid} — {q}\n{'='*100}", flush=True)
        try:
            answer, cites = call(q)
        except Exception as e:
            print(f"  ERROR {type(e).__name__}: {e}", flush=True)
            rep["cases"][cid] = {"query": q, "error": f"{type(e).__name__}: {e}"}
            continue

        pool = []
        for c in cites:
            sid = c.get("source_id", "")
            entry = {"id": c.get("id"), "source_id": sid, "source_type": c.get("source_type"),
                     "title": (c.get("title") or "")[:110]}
            if dm_safety(sid):
                setid = sid.split("DailyMed:", 1)[1].split("#", 1)[0]
                mo = SETID2MOIETY.get(setid)
                entry["moiety"] = mo
                entry["on_target"] = bool(mo and any(t in mo for t in targets))
                doc = BY_SID.get(sid.split("~")[0])
                entry["section_text"] = (doc or {}).get("content", "")[:1500]
            pool.append(entry)

        rep["cases"][cid] = {"query": q, "targets": targets, "answer": answer, "pool": pool}
        OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")

        print("--- POOL ---", flush=True)
        for e in pool:
            tag = ("" if "on_target" not in e else
                   ("  [ON-TARGET]" if e["on_target"] else "  [OFF-TARGET]"))
            print(f"  [{e['id']}] {e['source_type']:9} {e['source_id'][:52]}{tag}", flush=True)
            if e.get("moiety"):
                print(f"        moiety={e['moiety']}", flush=True)
        print("\n--- ANSWER (full) ---", flush=True)
        print(answer, flush=True)
        for e in pool:
            if e.get("on_target") is False:
                print(f"\n--- OFF-TARGET SECTION TEXT ({e['moiety']}) ---", flush=True)
                print(e["section_text"][:900], flush=True)

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)


if __name__ == "__main__":
    main()
