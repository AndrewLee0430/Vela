#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Native-speaker review CSV generator — the committed, reusable version.

Closes the trigger condition of the TECH_DEBT `[P3 · reviewer-CSV generator
never committed]` entry ("next time the CSV format is touched, commit a
generator"): the fly-226 70-row CSV and its fly-227 addendum were built by
uncommitted session scratch, and the fly-227 rescue had to regenerate both
after `npm run build` wiped `out/` — this file is the durable method.

Produces ONE merged file (default):
    deliverables/vela_legal_i18n_review_FINAL_20260811.csv
84 rows x 17 columns = 5 share/explore keys + the landing tagline, x 14
reviewer locales (en + zh-TW are hand-authored and excluded).

Layout rules (coordinator-ratified 2026-08-11):
  - sort by locale; within a locale the original fly-226 row order, with the
    tagline row LAST — so each locale's original FIRST row keeps the
    once-per-language q1-q3 prefill;
  - row_id renumbered 001..084 sequentially;
  - headerTagline + tagline rows carry the REQUIRED name-the-word-for-
    "official" notes prompt; the bn tagline note additionally records the
    আধিকারিক history; es/de tagline notes carry the measured register note.

STANDING RULE (from the fly-227 rescue): deliverables NEVER live in out/ —
it is a build target. They live in deliverables/ (gitignored via the global
*.csv rule).

Usage:
    python scripts/gen_review_csv.py              # generate + validate
    python scripts/gen_review_csv.py --validate P # round-trip an existing file
"""
import argparse
import codecs
import csv
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS_SHARE = os.path.join(REPO, "utils", "i18n-share.ts")
TS_MAIN = os.path.join(REPO, "utils", "i18n.ts")
PY_EXPLORE = os.path.join(REPO, "api", "i18n", "explore_strings.py")
PY_RENDERER = os.path.join(REPO, "api", "services", "share_renderer.py")
OUT_DEFAULT = os.path.join(REPO, "deliverables",
                           "vela_legal_i18n_review_FINAL_20260811.csv")

LOCALES = ["en", "zh-TW", "zh-CN", "ja", "ko", "es", "fr", "de", "it", "pt",
           "th", "ar", "hi", "bn", "he", "vi"]
REVIEW_LOCALES = [l for l in LOCALES if l not in ("en", "zh-TW")]
SHARE_CONST = {"en": "en", "zh-TW": "zhTW", "zh-CN": "zhCN", "ja": "ja",
               "ko": "ko", "es": "es", "fr": "fr", "de": "de", "it": "it",
               "pt": "pt", "th": "th", "ar": "ar", "hi": "hi", "bn": "bn",
               "he": "he", "vi": "vi"}
LANDING_CONST = {"en": "En", "zh-TW": "ZhTW", "zh-CN": "ZhCN", "ja": "Ja",
                 "ko": "Ko", "es": "Es", "fr": "Fr", "de": "De", "it": "It",
                 "pt": "Pt", "th": "Th", "ar": "Ar", "hi": "Hi", "bn": "Bn",
                 "he": "He", "vi": "Vi"}

# Per-locale row order = the fly-226 (locale, surfaces, key) sort, tagline last.
KEY_ORDER = [
    ("modalConsentCheckbox", "share-modal", "utils/i18n-share.ts"),
    ("settingsRevokeConfirm", "share-modal", "utils/i18n-share.ts"),
    ("publicDisclaimer", "share-modal + public-page",
     "utils/i18n-share.ts + api/i18n/explore_strings.py"),
    ("publicShortDisclaimer", "share-modal + public-page",
     "utils/i18n-share.ts + api/i18n/explore_strings.py"),
    ("headerTagline", "share-modal + public-page + share-header",
     "utils/i18n-share.ts + api/i18n/explore_strings.py + api/services/share_renderer.py"),
    ("landingContent.tagline", "landing-hero", "utils/i18n.ts"),
]

COLUMNS = ["row_id", "surfaces", "file", "key", "locale", "source_en",
           "source_zh_TW", "current_text", "char_count", "has_placeholders",
           "verdict", "corrected_text", "notes", "reviewer",
           "q1_legal_phrasing", "q2_consent_requirements",
           "q3_public_url_understanding"]

OFFICIAL_PROMPT = ('[Required: state the exact word you used for "official", '
                   'and confirm it does not mean government / state / '
                   'certified / approved / endorsed.]')
BN_TAGLINE_PROMPT = (
    '[Required: state the exact word you used for "official", and confirm it '
    'does not mean government / state / certified / approved / endorsed. '
    'NOTE: the shipped baseline used "আধিকারিক", flagged as carrying '
    'governmental connotation — do not keep it; choose a neutral term '
    '(candidates: স্বীকৃত / মান্য) and state your choice.]')
# Register notes: the "currently" clause is MEASURED (see the B2.1 report),
# not asserted — re-measure before editing these.
ES_REGISTER_NOTE = (
    " Ensure the tagline's register matches the product's in-app register "
    "(currently: mixed — usted predominates in body copy including the share "
    "tagline 'Pregunte en su idioma'; the landing hero tagline uses tú). "
    "Clinical tools conventionally prefer usted/Sie.")
DE_REGISTER_NOTE = (
    " Ensure the tagline's register matches the product's in-app register "
    "(currently: uniformly Sie — 95 formal hits, 0 du-forms). Clinical tools "
    "conventionally prefer usted/Sie.")
Q_PROMPT = "[Answer here for this language]"


# ---------------------------------------------------------------- parsers
def _read_js_string(src, i):
    q = src[i]
    assert q in "'\"`", f"not a string literal at {i}"
    i += 1
    out = []
    while i < len(src):
        c = src[i]
        if c == "\\":
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(src[i + 1], src[i + 1]))
            i += 2
            continue
        if c == q:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("unterminated string")


def parse_ts_blocks(path, header_re, const_map):
    """{locale: {key: value}} for every string key in each matched const block."""
    src = io.open(path, encoding="utf-8").read()
    starts = [(m.group(1), m.start()) for m in re.finditer(header_re, src, re.M)]
    inv = {v: k for k, v in const_map.items()}
    out = {}
    for idx, (name, pos) in enumerate(starts):
        loc = inv.get(name)
        if loc is None:
            continue
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(src)
        block = src[pos:end]
        vals = {}
        for m in re.finditer(r"^\s{2}(\w+):\s*", block, re.M):
            j = m.end()
            while j < len(block) and block[j] in " \t\r\n":
                j += 1
            if j < len(block) and block[j] in "'\"`":
                vals[m.group(1)], _ = _read_js_string(block, j)
        out[loc] = vals
    return out


def parse_py_dict(path, varname):
    import ast
    tree = ast.parse(io.open(path, encoding="utf-8").read(), filename=path)
    for node in tree.body:
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == varname:
                return ast.literal_eval(node.value)
    raise KeyError(varname)


# ---------------------------------------------------------------- build
def build_rows():
    share = parse_ts_blocks(TS_SHARE, r"^const (\w+): ShareTranslations = \{", SHARE_CONST)
    landing = parse_ts_blocks(TS_MAIN, r"^const landing(\w+): LandingContent = \{", LANDING_CONST)
    explore = parse_py_dict(PY_EXPLORE, "EXPLORE_STRINGS")
    renderer = parse_py_dict(PY_RENDERER, "_STRINGS")

    def value(key, loc):
        if key == "landingContent.tagline":
            return landing[loc]["tagline"]
        return share[loc][key]

    # Convergence assertion: a one-row-per-key CSV is only honest if every
    # source carrying the key agrees (the fly-224 rule).
    for loc in LOCALES:
        for key, _, files in KEY_ORDER:
            if key == "landingContent.tagline":
                continue
            v = share[loc][key]
            if "explore_strings" in files:
                assert explore[loc][key] == v, f"NOT CONVERGED: {loc}.{key} (explore)"
            if "share_renderer" in files and loc in renderer and key in renderer[loc]:
                assert renderer[loc][key] == v, f"NOT CONVERGED: {loc}.{key} (renderer)"

    rows = []
    for loc in REVIEW_LOCALES:
        first_in_locale = True
        for key, surfaces, files in KEY_ORDER:
            cur = value(key, loc)
            notes = ""
            if key == "headerTagline":
                notes = OFFICIAL_PROMPT
            elif key == "landingContent.tagline":
                notes = BN_TAGLINE_PROMPT if loc == "bn" else OFFICIAL_PROMPT
                if loc == "es":
                    notes += ES_REGISTER_NOTE
                elif loc == "de":
                    notes += DE_REGISTER_NOTE
            rows.append({
                "row_id": "",  # renumbered below
                "surfaces": surfaces,
                "file": files,
                "key": key,
                "locale": loc,
                "source_en": value(key, "en"),
                "source_zh_TW": value(key, "zh-TW"),
                "current_text": cur,
                "char_count": len(cur),
                "has_placeholders": " ".join(re.findall(r"\{[^{}]*\}", cur)),
                "verdict": "", "corrected_text": "", "notes": notes, "reviewer": "",
                "q1_legal_phrasing": Q_PROMPT if first_in_locale else "",
                "q2_consent_requirements": Q_PROMPT if first_in_locale else "",
                "q3_public_url_understanding": Q_PROMPT if first_in_locale else "",
            })
            first_in_locale = False
    for n, r in enumerate(rows, 1):
        r["row_id"] = f"{n:03d}"
    return rows


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


def validate(path, expected_rows=None):
    """Round-trip: every cell must survive a parse; returns (ok, detail)."""
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    bom = io.open(path, "rb").read(3) == codecs.BOM_UTF8
    problems = []
    if not bom:
        problems.append("missing UTF-8 BOM")
    if list(back[0].keys()) != COLUMNS:
        problems.append("column mismatch")
    if expected_rows is not None and len(back) != expected_rows:
        problems.append(f"row count {len(back)} != {expected_rows}")
    # per-locale q-prefill: exactly the first row of each locale block
    seen = {}
    for r in back:
        seen.setdefault(r["locale"], []).append(r)
    for loc, rs in seen.items():
        flags = [bool(r["q1_legal_phrasing"]) for r in rs]
        if flags != [True] + [False] * (len(rs) - 1):
            problems.append(f"q-prefill misplaced for {loc}")
    return (not problems), (problems or ["OK"]), back


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", metavar="PATH",
                    help="round-trip validate an existing CSV and exit")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    if args.validate:
        ok, detail, back = validate(args.validate)
        print(f"{args.validate}: rows={len(back)} -> {'PASS' if ok else 'FAIL'} {detail}")
        sys.exit(0 if ok else 1)

    rows = build_rows()
    write_csv(rows, args.out)
    ok, detail, back = validate(args.out, expected_rows=len(rows))
    identical = all(back[i][c] == str(rows[i][c])
                    for i in range(len(rows)) for c in COLUMNS)
    print(f"OUTPUT     : {args.out}")
    print(f"ROWS       : {len(rows)} written / {len(back)} re-parsed / "
          f"cells identical: {identical}")
    print(f"VALIDATE   : {'PASS' if ok and identical else 'FAIL'} {detail}")
    sys.exit(0 if ok and identical else 1)


if __name__ == "__main__":
    main()
