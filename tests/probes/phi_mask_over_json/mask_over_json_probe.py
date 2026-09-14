#!/usr/bin/env python
"""PHI mask-over-JSON probe — what `PHIDetector.sanitize_for_log` does to a
`ChatHistory.answer` that is a JSON blob rather than prose.

WHY THIS EXISTS
---------------
The `[COMPLIANCE][P2 · R5 privacy] ChatHistory.answer stored unsanitized` entry in
TECH_DEBT.md proposes, as optional hardening, running `PHIDetector.sanitize_for_log`
over `answer` at the five write sites "exactly as `question` already is". That bullet
was written 2026-06-08, when `answer` was PROSE. Since the HISTORY car (segments 1
and 3, 2026-09-01/02) every mode stores a JSON blob. A regex mask over prose and a
regex mask over `json.dumps(...)` output are not the same operation, and nobody had
measured the difference.

WHAT IT MEASURES
----------------
For each payload shape, it serializes with `json.dumps(..., ensure_ascii=False)` —
the same call the production helpers make — runs the REAL `PHIDetector.sanitize_for_log`
over the resulting string, and reports:
  * whether the string changed at all;
  * whether the masked string still parses as JSON (i.e. whether `/history`'s
    `parseResearchAnswer` / `parseVerifyAnswer` safe-parse would still succeed);
  * the surviving context around every `***` the mask inserted.

⚠️ INPUTS ARE SYNTHETIC. Every payload below is constructed BY HAND from the shape of
the real helpers (`_research_history_payload`, `_verify_history_payload`, and Explain's
inline `json.dumps`). NO DATABASE WAS READ — not prod, not the Dev branch. These are
representative shapes, not rows. See README.md.

NEGATIVE CONTROL
----------------
The fourth case, `HYPOTHETICAL_bare_int`, is the NEGATIVE CONTROL and is not a shape any
current payload has. It exists so the probe has a case it can FAIL: it adds bare integer
fields (a unix timestamp, an integer PMID), which `MEDICAL_RECORD_PATTERNS[1]`
(`\\b\\d{8,12}\\b`) masks to a bare `***`, producing invalid JSON. A probe with no failing
case has demonstrated nothing — if this case ever reports PARSES OK, the probe is broken
and its other results mean nothing.

RUN
---
    uv run python tests/probes/phi_mask_over_json/mask_over_json_probe.py

Writes `result.json` beside this file. No network, no database, no API credit.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.middleware.phi_handler import PHIDetector  # noqa: E402

RESULT_PATH = os.path.join(_HERE, "result.json")


# ── Payload shapes, mirrored by hand from the production helpers ──────────────

# `_research_history_payload` (api/server.py:1087-1112) —
# {"kind": "research_v1", "answer": <markdown>, "citations": [Citation.model_dump()…],
#  "fallback": bool}. Citation fields from api/models/schemas.py:70-81.
# Four citations chosen to span the mask's boundary conditions:
#   [1] 8-digit PMID   — at the floor of \b\d{8,12}\b        → expected MASKED
#   [2] 7-digit PMID   — one digit below the floor           → expected SURVIVES
#   [3] NCT id         — matches \b[A-Z]{2,3}\d{6,10}\b      → expected MASKED
#   [4] DailyMed setid — lowercase hex UUID, matches neither → expected SURVIVES
RESEARCH_V1 = {
    "kind": "research_v1",
    "answer": "## Summary\nMetformin and warfarin [1].",
    "citations": [
        {"id": 1, "source_type": "pubmed", "source_id": "PMID:12345678",
         "title": "A trial", "snippet": "text",
         "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
         "credibility": "high", "year": "2021", "authors": None, "journal": "NEJM"},
        {"id": 2, "source_type": "pubmed", "source_id": "PMID:9876543",
         "title": "Older trial", "snippet": "text",
         "url": "https://pubmed.ncbi.nlm.nih.gov/9876543/",
         "credibility": "high", "year": "1998", "authors": None, "journal": "BMJ"},
        {"id": 3, "source_type": "fda", "source_id": "NCT01234567",
         "title": "Reg trial", "snippet": "text",
         "url": "https://clinicaltrials.gov/study/NCT01234567",
         "credibility": "high", "year": "2020", "authors": None, "journal": None},
        {"id": 4, "source_type": "dailymed",
         "source_id": "e1c1b8a2-1f3d-4a0b-9f2e-7b3c5d6e7f80",
         "title": "DURLAZA label", "snippet": "text",
         "url": ("https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
                 "?setid=e1c1b8a2-1f3d-4a0b-9f2e-7b3c5d6e7f80"),
         "credibility": "high", "year": None, "authors": None, "journal": None},
    ],
    "fallback": False,
}

# `_verify_history_payload` (api/server.py:1114-1145) — all three Verify write sites
# (:1421, :1472, :1604) serialize through this one helper. DrugInteraction fields from
# api/models/schemas.py:214-236; TfdaGrounding from :238-246.
VERIFY = {
    "drugs_analyzed": ["Metformin", "Warfarin"],
    "interactions": [{
        "drug_pair": ["Metformin", "Warfarin"], "severity": "Moderate",
        "severity_label": None, "description": "d", "mechanism": None,
        "clinical_recommendation": "r", "source": "AI analysis of drug label",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc",
        "attribution_kind": "dailymed_grounded",
    }],
    "summary": "s", "risk_level": "Moderate", "risk_level_label": None,
    "response_language": "en", "disclaimer": "d",
    "tfda_groundings": [{
        "query": "冠脂妥",
        "ingredients": ["ROSUVASTATIN CALCIUM"],
        "is_combo": False,
        "licenses": ["衛署藥輸字第024567號"],
    }],
    "verification_status": "ok",
}

# Explain — no helper; `full_answer = json.dumps(event.get("content", {}),
# ensure_ascii=False)` inline at api/server.py:1707, written at :1717-1722.
# Content keys confirmed at api/services/explain_service.py:453-457.
EXPLAIN = {
    "items": [{
        "term": "eGFR", "value": "45 mL/min/1.73m2", "explanation": "e",
        "risk_tier": "yellow",
        "citations": [{"source_type": "loinc", "label": "LOINC 62238-1",
                       "url": "https://loinc.org/62238-1", "description": None}],
    }],
    "clinical_correlations": [],
    "disclaimer": "d",
}

# ⚠️ NEGATIVE CONTROL — not a shape any current payload has. See the module docstring.
HYPOTHETICAL_BARE_INT = {
    "kind": "research_v1", "answer": "a", "citations": [],
    "written_at": 1757808000,
    "pmid_int": 12345678,
}

CASES = [
    ("research_v1", RESEARCH_V1, "live payload shape", False),
    ("verify", VERIFY, "live payload shape", False),
    ("explain", EXPLAIN, "live payload shape", False),
    ("HYPOTHETICAL_bare_int", HYPOTHETICAL_BARE_INT,
     "NEGATIVE CONTROL — must FAIL to parse; if it passes, the probe is broken", True),
]

_CTX = re.compile(r".{0,28}\*\*\*.{0,18}")


def run_case(name, obj, role, expect_parse_failure):
    blob = json.dumps(obj, ensure_ascii=False)
    masked = PHIDetector.sanitize_for_log(blob)
    try:
        json.loads(masked)
        parses, parse_error = True, None
    except Exception as e:  # noqa: BLE001 — the failure text IS the measurement
        parses, parse_error = False, "%s: %s" % (type(e).__name__, e)
    return {
        "case": name,
        "role": role,
        "expect_parse_failure": expect_parse_failure,
        "bytes_before": len(blob),
        "bytes_after": len(masked),
        "changed": blob != masked,
        "masked_json_parses": parses,
        "parse_error": parse_error,
        "control_behaved_as_expected": (not parses) if expect_parse_failure else parses,
        "mask_contexts": _CTX.findall(masked) if blob != masked else [],
    }


def main():
    results = [run_case(*c) for c in CASES]
    control = next(r for r in results if r["expect_parse_failure"])
    payload = {
        "probe": "phi_mask_over_json",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "measures": ("PHIDetector.sanitize_for_log applied to json.dumps() output of "
                     "the three ChatHistory.answer payload shapes"),
        "inputs": "SYNTHETIC representative payloads; NO database was read",
        "sanitizer_patterns_applied_in_order": [
            "TAIWAN_ID_PATTERN", "TAIWAN_PHONE_PATTERN", "JAPAN_MY_NUMBER_FORMAT",
            "JAPAN_PHONE_PATTERN", "USA_SSN_WITH_DASH", "USA_MRN_PATTERN",
            "USA_PHONE_PATTERN", "EMAIL_PATTERN", "CREDIT_CARD_PATTERN",
            "MEDICAL_RECORD_PATTERNS[0] = \\b[A-Z]{2,3}\\d{6,10}\\b",
            "MEDICAL_RECORD_PATTERNS[1] = \\b\\d{8,12}\\b",
        ],
        "negative_control_valid": control["control_behaved_as_expected"],
        "results": results,
    }
    with open(RESULT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for r in results:
        print("=== %s === (%s)" % (r["case"], r["role"]))
        print("  bytes %d -> %d | changed=%s | %s"
              % (r["bytes_before"], r["bytes_after"], r["changed"],
                 "PARSES OK" if r["masked_json_parses"]
                 else "JSON.parse WOULD FAIL: %s" % r["parse_error"]))
        for c in r["mask_contexts"]:
            print("    ...%s..." % c)
    print()
    print("negative control valid: %s" % payload["negative_control_valid"])
    print("wrote %s" % RESULT_PATH)
    return 0 if payload["negative_control_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
