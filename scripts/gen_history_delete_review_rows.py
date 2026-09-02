#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Append the history-delete i18n keys to the UNSENT landing reviewer CSV.

Delete-segment closeout, 2026-09-02. The 4 keys shipped in `74df707`
(historyDeleteBtn / historyDeleting / historyDeleteConfirm /
historyDeleteError, utils/i18n-ui.ts) are machine-baseline in every non-en
locale except zh-TW, which the founder reviewed natively (recon baton §9
sign-off, 2026-09-02). They ride the SAME unsent dispatch as the landing set
(baton ruling #7: ONE send, founder dispatches) — so this script APPENDS to
deliverables/vela_landing_i18n_review_20260828.csv rather than regenerating
it: the existing file carries the founder's 15 signed zh-TW verdict cells,
which a regeneration would blank. Pre-existing rows are asserted
byte-identical after the rewrite.

Derivation (Rule 25): review locales = LOCALES(16) − en (source) − zh-TW
(founder-reviewed) = 14; rows appended = 4 keys × 14 locales = 56;
row_ids continue from the existing maximum. The bn / hi / he
historyDeleteConfirm cells are flagged HIGH PRIORITY (irreversibility
sentence — the build session's least-certain registers).

STANDING RULE (fly-227 rescue): deliverables live in deliverables/
(gitignored); this script is the durable method. DO NOT SEND — the founder
dispatches once.

Usage:
    python scripts/gen_history_delete_review_rows.py    # append + validate
"""
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_review_csv import COLUMNS, LOCALES, validate, _read_js_string  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO, "deliverables", "vela_landing_i18n_review_20260828.csv")
TS_UI = os.path.join(REPO, "utils", "i18n-ui.ts")

KEYS = ["historyDeleteBtn", "historyDeleting",
        "historyDeleteConfirm", "historyDeleteError"]
SURFACES = {
    "historyDeleteBtn": "history-row + delete-modal",
    "historyDeleting": "history-delete-modal",
    "historyDeleteConfirm": "history-delete-modal",
    "historyDeleteError": "history-delete-modal",
}
CONFIRM_PROMPT = (
    '[Required: this is the DELETE-CONFIRM text - it must state the deletion '
    'is PERMANENT / IRREVERSIBLE in natural formal register (counsel '
    'requirement 1), and must NOT soften to "remove from view/list". Confirm '
    'the irreversibility clause survives translation.]')
HIGH_PRIORITY = {"bn", "hi", "he"}


def parse_ui_locales():
    """{locale: {key: value}} for the 4 delete keys, from utils/i18n-ui.ts
    (top-level `const en` block + the uiTranslations Record members — the
    shared parse_ts_blocks only matches standalone consts, and the LOINC
    Record further down reuses the same locale headers, so bounds matter)."""
    src = io.open(TS_UI, encoding="utf-8").read()
    blocks = {"en": src[src.index("const en: UITranslations = {"):
                       src.index("export const uiTranslations")]}
    body = src[src.index("export const uiTranslations"):
               src.index("export function getUI")]
    headers = [(m.group(1) or m.group(2), m.start()) for m in
               re.finditer(r"^  (?:'([\w-]+)'|(\w+)): \{", body, re.M)]
    for i, (loc, pos) in enumerate(headers):
        end = headers[i + 1][1] if i + 1 < len(headers) else len(body)
        blocks[loc] = body[pos:end]
    out = {}
    for loc, block in blocks.items():
        vals = {}
        for k in KEYS:
            m = re.search(r"^\s+%s:\s*" % k, block, re.M)
            assert m, "key %s missing in locale %s" % (k, loc)
            vals[k], _ = _read_js_string(block, m.end())
        out[loc] = vals
    return out


def main():
    ui = parse_ui_locales()
    assert sorted(ui.keys()) == sorted(LOCALES), sorted(ui.keys())
    review_locales = [l for l in LOCALES if l not in ("en", "zh-TW")]
    assert len(review_locales) == 14, review_locales

    with io.open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        existing = list(csv.DictReader(fh))
    assert not any(r["key"].startswith("uiTranslations.historyDelete")
                   for r in existing), "history-delete rows already appended"
    base = len(existing)

    new_rows = []
    for loc in review_locales:
        for key in KEYS:
            cur = ui[loc][key]
            notes = ""
            if key == "historyDeleteConfirm":
                notes = CONFIRM_PROMPT
                if loc in HIGH_PRIORITY:
                    notes = "[HIGH PRIORITY] " + notes
            new_rows.append({
                "row_id": "%03d" % (base + len(new_rows) + 1),
                "surfaces": SURFACES[key],
                "file": "utils/i18n-ui.ts",
                "key": "uiTranslations." + key,
                "locale": loc,
                "source_en": ui["en"][key],
                "source_zh_TW": ui["zh-TW"][key],
                "current_text": cur,
                "char_count": len(cur),
                "has_placeholders": " ".join(re.findall(r"\{[^{}]*\}", cur)),
                "verdict": "", "corrected_text": "",
                "notes": notes, "reviewer": "",
                "q1_legal_phrasing": "", "q2_consent_requirements": "",
                "q3_public_url_understanding": "",
            })
    assert len(new_rows) == 4 * 14, len(new_rows)

    all_rows = existing + new_rows
    with io.open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(all_rows)

    # Round-trip validate. Like the landing generator: q1-q3 are EMPTY by
    # design here, so the shared validator's q-prefill finding is the expected
    # outcome, asserted as such rather than ignored wholesale.
    ok, detail, back = validate(CSV_PATH, expected_rows=len(all_rows))
    real_problems = [p for p in detail if p != "OK"
                     and not p.startswith("q-prefill misplaced")]
    assert not real_problems, real_problems
    # Byte-fidelity of every pre-existing row — including the founder's
    # signed zh-TW verdict cells, the reason this appends instead of
    # regenerating.
    for i, r in enumerate(existing):
        for c in COLUMNS:
            assert back[i][c] == r[c], ("pre-existing row mutated", i, c)
    zh_verdicts = sum(1 for r in back
                      if r["locale"] == "zh-TW" and r["verdict"])
    print("CSV      :", CSV_PATH)
    print("EXISTING : %d rows (byte-identical after rewrite)" % base)
    print("APPENDED : %d = 4 keys x %d locales (unit: key-locale cells)"
          % (len(new_rows), len(review_locales)))
    print("TOTAL    : %d rows; HIGH PRIORITY: %s historyDeleteConfirm"
          % (len(all_rows), "/".join(sorted(HIGH_PRIORITY))))
    print("zh-TW founder verdict cells preserved:", zh_verdicts)
    print("DO NOT SEND - the founder dispatches once (baton ruling #7).")


if __name__ == "__main__":
    main()
