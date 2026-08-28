#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Landing i18n reviewer-dispatch CSV — the 2026-08-28 landing build car set.

Baton ruling #7 (recon_20260827_landing.md, ruled 2026-08-27/28): the reviewer
round dispatches AFTER the landing build car, in ONE send, over the set that
exists at car end. This generator derives that set fresh from utils/i18n.ts:

    eligible = every landingContent key EXCEPT subtitle + scrollHint
               (the only two byte-identical to fly 232, which STATE's fly-233
               entry records as carrying no new review debt)

At this car's HEAD that is 10 keys x 15 non-en locales = 150 rows. zh-TW IS a
reviewer locale here (unlike the legal FINAL CSV, whose zh-TW was
hand-authored): every non-en landing cell in this set is machine-baseline,
written by the fly-227-convention MT pass of B4.1d or of this car.

Format: column-identical to deliverables/vela_legal_i18n_review_FINAL_20260811
(scripts/gen_review_csv.py); q1-q3 left EMPTY per the fly-227 addendum
precedent (the main CSV already collected one answer per language).

STANDING RULE (fly-227 rescue): deliverables NEVER live in out/ — they live in
deliverables/ (gitignored via the global *.csv rule); this script is the
durable method. DO NOT SEND — the founder dispatches.

Usage:
    python scripts/gen_landing_review_csv.py            # generate + validate
"""
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_review_csv import (  # noqa: E402
    COLUMNS, LANDING_CONST, LOCALES, TS_MAIN, parse_ts_blocks, validate,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "deliverables", "vela_landing_i18n_review_20260828.csv")

# Byte-identical to fly 232 => no review debt (STATE fly-233 entry). Everything
# else in landingContent is in the dispatch set BY DERIVATION, not by list.
NOT_ELIGIBLE = {"subtitle", "scrollHint"}

# Page order (hero -> panel -> band), used within each locale block.
PAGE_ORDER = ["tagline", "panelHeadline", "panelSub", "panelDemoAlt",
              "tryResearch", "tryVerify", "tryVela", "verifyHeadline",
              "verifySub", "verifyDemoAlt"]

SURFACES = {
    "tagline": "landing-hero",
    "panelHeadline": "landing-panel", "panelSub": "landing-panel",
    "panelDemoAlt": "landing-panel", "tryResearch": "landing-panel",
    "tryVerify": "landing-verify-band", "tryVela": "landing-nav",
    "verifyHeadline": "landing-verify-band", "verifySub": "landing-verify-band",
    "verifyDemoAlt": "landing-verify-band",
}

OFFICIAL_SCOPED_PROMPT = (
    '[Required: "official" here is SCOPED TO DRUG LABELS (FDA labeling) - '
    'state the exact word you used for "official" and confirm it reads as '
    '"issued by the regulator", not government-endorsement of Vela. Also '
    'confirm the two closing clauses survive translation accurately: '
    '"answers in the language you asked in" and "flags where local guidance '
    'may differ" (a pointer, not a promise of local data).]')
VERIFYSUB_PROMPT = (
    '[Required: confirm the final clause keeps its meaning - an assessment '
    'can come from Vela rather than the label, and the UI says so. It must '
    'NOT read as "Vela verifies the label" or drop the distinction.]')
VERIFYHEADLINE_PROMPT = (
    '[Check: must read as "checked against the label" (method), never as a '
    'safety verdict ("safe to combine").]')
TRYVELA_PROMPT = '[Check: "Vela" must stay in English in every locale.]'

NOTES = {
    "panelSub": OFFICIAL_SCOPED_PROMPT,
    "verifySub": VERIFYSUB_PROMPT,
    "verifyHeadline": VERIFYHEADLINE_PROMPT,
    "tryVela": TRYVELA_PROMPT,
}


def main():
    landing = parse_ts_blocks(
        TS_MAIN, r"^const landing(\w+): LandingContent = \{", LANDING_CONST)

    # Derive the key set from the interface itself (Rule 25: derive, compare).
    src = io.open(TS_MAIN, encoding="utf-8").read()
    iface = src[src.index("export interface LandingContent {"):]
    iface = iface[:iface.index("}")]
    declared = re.findall(r"^  (\w+): string;", iface, re.M)
    eligible = [k for k in declared if k not in NOT_ELIGIBLE]
    assert sorted(eligible) == sorted(PAGE_ORDER), (
        "eligible set drifted vs PAGE_ORDER:\n  derived: %s\n  listed:  %s"
        % (sorted(eligible), sorted(PAGE_ORDER)))

    review_locales = [l for l in LOCALES if l != "en"]
    rows = []
    for loc in review_locales:
        for key in PAGE_ORDER:
            cur = landing[loc][key]
            rows.append({
                "row_id": "",
                "surfaces": SURFACES[key],
                "file": "utils/i18n.ts",
                "key": "landingContent." + key,
                "locale": loc,
                "source_en": landing["en"][key],
                "source_zh_TW": landing["zh-TW"][key],
                "current_text": cur,
                "char_count": len(cur),
                "has_placeholders": " ".join(re.findall(r"\{[^{}]*\}", cur)),
                "verdict": "", "corrected_text": "",
                "notes": NOTES.get(key, ""), "reviewer": "",
                "q1_legal_phrasing": "", "q2_consent_requirements": "",
                "q3_public_url_understanding": "",
            })
    for n, r in enumerate(rows, 1):
        r["row_id"] = "%03d" % n

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    # Round-trip validate. The shared validator asserts the legal CSV's
    # q-prefill layout (first row per locale non-empty); this set ships q1-q3
    # EMPTY by design, so that one finding is expected and asserted AS the
    # correct outcome rather than ignored wholesale.
    ok, detail, back = validate(OUT, expected_rows=len(rows))
    real_problems = [p for p in detail if p != "OK"
                     and not p.startswith("q-prefill misplaced")]
    assert not real_problems, real_problems
    assert all(not r["q1_legal_phrasing"] for r in back)
    print("OUTPUT   :", OUT)
    print("KEYS     : %d (derived from interface minus %s)"
          % (len(eligible), sorted(NOT_ELIGIBLE)))
    print("ROWS     : %d = %d keys x %d locales (MT cells, unit: key-locale)"
          % (len(rows), len(eligible), len(review_locales)))
    print("DO NOT SEND - founder dispatches (baton ruling #7).")


if __name__ == "__main__":
    main()
