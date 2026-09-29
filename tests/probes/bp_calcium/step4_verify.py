"""STEP 4 (E7) — does VERIFY already carry the thiazide + calcium -> hypercalcemia capability?

3 POST /api/verify calls against a LOCAL TEST_MODE server on the Dev DB (no auth header
-> TEST_USER_ID L1 path; writes AuditLog/ChatHistory rows to the DEV branch only):
  hydrochlorothiazide + calcium carbonate  x2
  chlorthalidone      + calcium carbonate  x1

Records verification_status, each interaction's attribution_kind (dailymed_grounded vs
openfda_analysis vs no_label) + source, and whether 'hypercalc' appears in any
interaction description. Pure HTTP client — imports nothing from api/.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "step4_verify.json"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
CALLS = [["hydrochlorothiazide", "calcium carbonate"],
         ["hydrochlorothiazide", "calcium carbonate"],
         ["chlorthalidone", "calcium carbonate"]]
HYPER = re.compile(r"hypercalc", re.I)


def post(drugs):
    req = urllib.request.Request(BASE + "/api/verify", data=json.dumps({"drugs": drugs}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def main():
    rows = []
    for drugs in CALLS:
        status, body = post(drugs)
        ints = body.get("interactions") or []
        row = {"drugs": drugs, "http": status, "verification_status": body.get("verification_status"),
               "risk_level": body.get("risk_level"), "summary": body.get("summary"),
               "interactions": [{"drugs": i.get("drug_pair") or i.get("drugs"),
                                 "severity": i.get("severity"),
                                 "attribution_kind": i.get("attribution_kind"),
                                 "source": i.get("source"), "source_url": i.get("source_url"),
                                 "description": i.get("description"),
                                 "hypercalcemia": bool(HYPER.search(json.dumps(i, ensure_ascii=False)))}
                                for i in ints],
               "hypercalcemia_anywhere": bool(HYPER.search(json.dumps(body, ensure_ascii=False)))}
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("drugs", "verification_status", "risk_level",
                                              "hypercalcemia_anywhere")}),
              [(i["attribution_kind"], i["severity"]) for i in row["interactions"]], flush=True)
    cap = any(r["hypercalcemia_anywhere"] for r in rows)
    res = {"base": BASE, "calls": rows,
           "verdict": f"capability exists in Verify: {'YES' if cap else 'NO'} "
                      f"({sum(r['hypercalcemia_anywhere'] for r in rows)}/{len(rows)} calls name hypercalcemia)"}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res["verdict"])


if __name__ == "__main__":
    main()
