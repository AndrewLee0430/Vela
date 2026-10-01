"""CLOSEOUT readback (NOT a gate) — ONE anonymous Research call on PROD with the hero-chip question.

Costs ~1 Research credit on the anon budget (founder-authorized, 2026-10-01 closeout paste). Sends the
production SSE request exactly as the landing page would for an L0 user (X-Anon-Fingerprint header), reads
the stream, and records: whether a DailyMed 34073-7 section is among the citations, and whether the answer
names thiazide/hypercalcemia (regex + the answer text saved for hand-read). Pure HTTP client; imports
nothing from api/. The fingerprint is a fixed probe string that passes validate_fingerprint's shape rule.

Usage: python step8_prod_smoke.py https://vela.an-tho.com <fingerprint>
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY = "Can elderly patients take BP meds with calcium?"


def main():
    base, fp = sys.argv[1].rstrip("/"), sys.argv[2]
    req = urllib.request.Request(
        base + "/api/research",
        data=json.dumps({"question": QUERY, "response_language": "en"}).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream",
                 "X-Anon-Fingerprint": fp}, method="POST")
    t0 = time.time()
    answer, citations, events, status_msgs, fallback = "", [], [], [], None
    with urllib.request.urlopen(req, timeout=240) as r:
        http = r.status
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if not line.startswith("data: "):
                continue
            try:
                ev = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            events.append(ev.get("type"))
            if ev.get("type") == "answer":
                answer += ev.get("content") or ""
            elif ev.get("type") == "citations":
                citations = ev.get("content") or []
            elif ev.get("type") == "status":
                status_msgs.append(ev.get("content"))
            elif ev.get("type") == "fallback":
                fallback = ev.get("content")
    cited = [c.get("source_id") for c in citations]
    res = {"base": base, "http": http, "seconds": round(time.time() - t0, 1), "events": sorted(set(e for e in events if e)),
           "status_msgs": status_msgs, "fallback": fallback,
           "citations": [{"source_id": c.get("source_id"), "title": (c.get("title") or "")[:100]} for c in citations],
           "dailymed_34073_7_cited": any(s and s.startswith("DailyMed:") and "#34073-7" in s for s in cited),
           "any_dailymed_cited": any(s and s.startswith("DailyMed:") for s in cited),
           "answer_names_thiazide_or_hypercalcemia": bool(re.search(r"thiazide|hydrochlorothiazide|hypercalc", answer, re.I)),
           "answer_chars": len(answer), "answer": answer}
    json.dump(res, open(HERE / "step8_prod_smoke.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (HERE / "step8_prod_smoke_answer.md").write_text(answer, encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("http", "seconds", "events", "fallback", "citations",
                                          "dailymed_34073_7_cited", "answer_names_thiazide_or_hypercalcemia")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
