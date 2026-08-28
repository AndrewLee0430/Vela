# -*- coding: utf-8 -*-
"""fly 222 — the visitor-facing medical disclaimer must be ONE text, not three.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
`publicDisclaimer` and `publicShortDisclaimer` are the medical disclaimer a
visitor reads on a public page. They are legal-weighted copy: counsel signs off
on a wording, and every surface that shows it must show *that* wording. Today
the same text is duplicated by hand across three files:

    utils/i18n-share.ts            -> the React share modal + settings (16 locales)
    api/i18n/explore_strings.py    -> /explore + blog, server-rendered (16 locales)
    api/services/share_renderer.py -> the /q/ public query page (en + zh-TW)

Nothing joins them. On 2026-08-11 a read-only audit found all three still
byte-identical — by luck, not by construction. This test converts that luck
into a guard: edit one file and the other two fail here, loudly, before deploy.

A FOURTH file, utils/i18n.ts (the 16-locale landing + app copy), joined this
module at B4.1e. It carries NONE of the legal parity keys, so it adds no parity
obligation — it is here for the zh-TW punctuation RULE below, which had been
sampling three files while the largest locale file in the repo went unchecked.
Extending it immediately found 3 ASCII "?" adjacent to CJK, in example-chip
strings no one had looked at since they were written.

WHY THIS IS THE RULE-19 FAILURE CLASS
-------------------------------------
Rule 19 ("when extending a data path to a SECOND surface, carry its mitigations
across") has been paid for twice in this repo — b1 country-keyed the authority
data but not the label strings, and DailyMed reached Research without Verify's
openFDA fall-through. This is the same shape one step earlier: three copies of
one legal string, no mechanism holding them equal. A correction applied to one
file would silently leave two surfaces showing superseded legal copy, and the
divergence would be invisible until someone diffed three files by hand.

WHY IT COMPARES BYTES AND NOT "MEANING"
---------------------------------------
The 2026-08-11 finding that motivated the accompanying fix was punctuation:
zh-TW carried ASCII commas (U+002C) where Traditional Chinese typography wants
fullwidth (U+FF0C). A normalising comparison would have called those equal and
would call a future half-applied fix equal too. Equality here is exact.
"""
import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_TS = _ROOT / "utils" / "i18n-share.ts"
_EXPLORE = _ROOT / "api" / "i18n" / "explore_strings.py"
_RENDERER = _ROOT / "api" / "services" / "share_renderer.py"
_I18N = _ROOT / "utils" / "i18n.ts"          # landing copy — added to the RULE at B4.1e

# Keys under parity. The other two legal-weighted share keys
# (modalConsentCheckbox, settingsRevokeConfirm) live only in the .ts file and
# so have no parity obligation.
#
# Widened at fly 224 from the two disclaimers × en+zh-TW to every key below ×
# every locale that carries it. Each key is compared across whichever sources
# actually hold it — the .ts and explore files carry 16 locales, share_renderer
# carries en + zh-TW, so the comparison set is computed, not assumed.
SHARED_KEYS = ("publicDisclaimer", "publicShortDisclaimer",
               "publicRevoked", "publicFlagged", "headerTagline")

ALL_LOCALES = ("en", "zh-TW", "zh-CN", "ja", "ko", "es", "fr", "de",
               "it", "pt", "th", "ar", "hi", "bn", "he", "vi")

# ✅ EMPTY as of fly 225. headerTagline was the last exclusion — it diverged in
# 10 of 16 locales, and in Bengali the explore copy escalated "official sources"
# to "সরকারি" (GOVERNMENT sources), a stronger claim than the English makes on a
# medical product. Converged and brought under parity, so every key duplicated
# across the two 16-locale files is now guarded.
#
# Keep this empty. A new entry here is a decision to let a duplicated key drift,
# and needs a written reason next to it.
_KNOWN_UNGUARDED_DUPLICATES: set[str] = set()

_TS_CONST_TO_LOCALE = {"en": "en", "zhTW": "zh-TW", "zhCN": "zh-CN",
                       "ja": "ja", "ko": "ko", "es": "es", "fr": "fr",
                       "de": "de", "it": "it", "pt": "pt", "th": "th",
                       "ar": "ar", "hi": "hi", "bn": "bn", "he": "he",
                       "vi": "vi"}


def _read_js_string(src: str, i: int) -> str:
    """Read the JS string literal starting at src[i], honouring backslash escapes."""
    quote = src[i]
    assert quote in "'\"`", f"expected a string literal at offset {i}"
    i += 1
    out = []
    while i < len(src):
        c = src[i]
        if c == "\\":
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(src[i + 1], src[i + 1]))
            i += 2
            continue
        if c == quote:
            return "".join(out)
        out.append(c)
        i += 1
    raise ValueError("unterminated string literal")


def _parse_ts() -> dict:
    """{locale: {key: value}} for EVERY key in each `const <x>: ShareTranslations` block.

    Every key, not a named subset: the punctuation rule below has to see keys
    nobody thought to list, which is the whole point of a rule over a list.
    """
    src = _TS.read_text(encoding="utf-8")
    starts = [(m.group(1), m.start())
              for m in re.finditer(r"^const (\w+): ShareTranslations = \{", src, re.M)]
    assert starts, "no ShareTranslations blocks found — did the file shape change?"
    out = {}
    for idx, (const_name, pos) in enumerate(starts):
        locale = _TS_CONST_TO_LOCALE.get(const_name)
        if locale is None:
            continue
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(src)
        block = src[pos:end]
        vals = {}
        for m in re.finditer(r"^\s{2}(\w+):\s*", block, re.M):
            j = m.end()
            while j < len(block) and block[j] in " \t\r\n":
                j += 1
            if j < len(block) and block[j] in "'\"`":
                vals[m.group(1)] = _read_js_string(block, j)
        out[locale] = vals
    return out


_LANDING_CONST_TO_LOCALE = {
    "landingEn": "en", "landingZhTW": "zh-TW", "landingZhCN": "zh-CN",
    "landingJa": "ja", "landingKo": "ko", "landingEs": "es", "landingFr": "fr",
    "landingDe": "de", "landingIt": "it", "landingPt": "pt", "landingTh": "th",
    "landingAr": "ar", "landingHi": "hi", "landingBn": "bn", "landingHe": "he",
    "landingVi": "vi",
}


def _kv_at_indent(block: str, indent: int) -> dict:
    """`key: '…'` pairs at exactly `indent` spaces. Same indent-based approach
    _parse_ts uses — these files are Prettier-formatted, so indent is reliable
    and a brace-depth parser would be more machinery for no more coverage."""
    vals = {}
    for m in re.finditer(r"^ {%d}(\w+):\s*" % indent, block, re.M):
        j = m.end()
        while j < len(block) and block[j] in " \t\r\n":
            j += 1
        if j < len(block) and block[j] in "'\"`":
            vals[m.group(1)] = _read_js_string(block, j)
    return vals


def _parse_i18n() -> dict:
    """{locale: {key: value}} for utils/i18n.ts — the LANDING copy file.

    Brought under the punctuation rule at B4.1e. This file holds the 16-locale
    landing + app strings and was NOT covered by the fly-223 rule, even though
    that rule's whole lesson was that a rule must not sample. It has exactly two
    string containers and BOTH are parsed:
      * `const landing<X>: LandingContent = {…}`  → prefix "landingContent."
      * `translations['xx'] = {…}` (and the `en,` shorthand referencing
        `const en: Translations`) → prefix "translations."
    Keys are PREFIXED so the two containers cannot shadow each other, and so no
    key here can collide with SHARED_KEYS — this file carries none of the legal
    parity strings, and prefixing keeps it that way structurally.
    """
    src = _I18N.read_text(encoding="utf-8")
    out: dict[str, dict] = {}

    # (1) landing<Locale> consts
    starts = [(m.group(1), m.start())
              for m in re.finditer(r"^const (landing\w+): LandingContent = \{", src, re.M)]
    assert starts, "no LandingContent blocks found — did utils/i18n.ts change shape?"
    for const_name, pos in starts:
        locale = _LANDING_CONST_TO_LOCALE.get(const_name)
        assert locale, f"unmapped LandingContent const {const_name!r} — add it to the map"
        end = src.index("\n};", pos)
        for k, v in _kv_at_indent(src[pos:end], 2).items():
            out.setdefault(locale, {})[f"landingContent.{k}"] = v

    # (2) the translations record: inline `'xx': {` blocks plus the `en,` shorthand
    t_pos = src.index("export const translations: Record<LangCode, Translations> = {")
    t_block = src[t_pos:]
    # [A-Za-z-]: the locale keys are 'zh-TW' / 'zh-CN', not lowercase-only.
    inline = [(m.group(1), m.start()) for m in re.finditer(r"^  '([A-Za-z-]+)': \{", t_block, re.M)]
    assert inline, "no inline locale blocks in `translations` — did the shape change?"
    for idx, (locale, pos) in enumerate(inline):
        end = inline[idx + 1][1] if idx + 1 < len(inline) else len(t_block)
        for k, v in _kv_at_indent(t_block[pos:end], 4).items():
            out.setdefault(locale, {})[f"translations.{k}"] = v
    if re.search(r"^  en,$", t_block, re.M):          # shorthand → `const en: Translations`
        en_pos = src.index("const en: Translations = {")
        for k, v in _kv_at_indent(src[en_pos:src.index("\n};", en_pos)], 2).items():
            out.setdefault("en", {})[f"translations.{k}"] = v

    return out


def _parse_py(path: Path, varname: str) -> dict:
    """literal_eval a module-level dict without importing the module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for t in targets:
            if isinstance(t, ast.Name) and t.id == varname:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{varname} not found in {path}")


@pytest.fixture(scope="module")
def sources():
    return {
        "utils/i18n-share.ts": _parse_ts(),
        "api/i18n/explore_strings.py": _parse_py(_EXPLORE, "EXPLORE_STRINGS"),
        "api/services/share_renderer.py": _parse_py(_RENDERER, "_STRINGS"),
        # Carries none of SHARED_KEYS, so it adds no parity obligation; it is
        # here so the zh-TW punctuation RULE below reaches the landing copy.
        "utils/i18n.ts": _parse_i18n(),
    }


@pytest.mark.parametrize("locale", ALL_LOCALES)
@pytest.mark.parametrize("key", SHARED_KEYS)
def test_disclaimer_is_byte_identical_across_all_three_sources(sources, key, locale):
    """One legal string, N files. Any drift between them fails here.

    Compares across exactly those sources that carry this key in this locale.
    A key present in only one source is skipped — parity is undefined for it —
    but a key present in two or more must match exactly.
    """
    texts = {fname: store[locale][key]
             for fname, store in sources.items()
             if locale in store and key in store[locale]}

    if len(texts) < 2:
        pytest.skip(f"{key} [{locale}] exists in {len(texts)} source(s) — parity undefined")

    distinct = set(texts.values())
    if len(distinct) != 1:
        detail = "\n".join(f"  {fname}:\n    {text!r}" for fname, text in texts.items())
        pytest.fail(
            f"{key} [{locale}] has diverged across surfaces — "
            f"{len(distinct)} distinct texts:\n{detail}\n"
            "A visitor-facing legal string must be identical everywhere it renders. "
            "Apply the correction to ALL THREE files."
        )


# --------------------------------------------------------------------------
# zh-TW fullwidth punctuation — a RULE over every string, not a list of known
# strings. A list passes again the moment someone adds a key it does not name,
# which is exactly how fly 222 shipped a partial fix.
# --------------------------------------------------------------------------

# Deliberately NOT included: ASCII "." and ":".
#   "." is legitimate in URLs, decimals and version numbers ("fda.gov.tw", "2.0")
#   ":" is legitimate in "Label: value" constructions and in times.
# Both would produce false positives that train people to ignore this test.
# "," "?" "!" ";" are sentence punctuation with no such legitimate use between
# Chinese characters.
_MUST_BE_FULLWIDTH = {",": "，", "?": "？", "!": "！", ";": "；"}


def _is_cjk(ch: str) -> bool:
    """CJK ideograph or CJK punctuation — the signal that we are inside Chinese text."""
    if not ch:
        return False
    return ("一" <= ch <= "鿿"      # CJK Unified Ideographs
            or "　" <= ch <= "〿"   # CJK symbols and punctuation (、。「」)
            or "＀" <= ch <= "￯")  # Fullwidth forms (，？！；)


def _punctuation_violations(text: str):
    """ASCII sentence punctuation sitting next to a CJK character.

    Adjacency is the test, not mere presence: ASCII punctuation is CORRECT
    inside Latin fragments embedded in a Chinese string ("Vela, Inc.", a URL,
    a numeric range). Only punctuation touching Chinese on either side is wrong.
    """
    out = []
    for i, ch in enumerate(text):
        if ch not in _MUST_BE_FULLWIDTH:
            continue
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if _is_cjk(prev) or _is_cjk(nxt):
            out.append((i, ch, _MUST_BE_FULLWIDTH[ch], text[max(0, i - 12):i + 13]))
    return out


@pytest.mark.parametrize("fname", ["utils/i18n-share.ts",
                                   "api/i18n/explore_strings.py",
                                   "api/services/share_renderer.py",
                                   "utils/i18n.ts"])
def test_no_ascii_sentence_punctuation_in_any_zh_tw_string(sources, fname):
    """EVERY zh-TW string in this file, including keys added after this was written.

    fly 222 fixed 3 ASCII commas in the two disclaimer keys and left 14 more in
    place across 11 other keys, because the count came from sampling one key.
    A rule cannot sample.
    """
    store = sources[fname]["zh-TW"]
    assert store, f"{fname} produced no zh-TW strings — parser is broken"

    failures = []
    for key in sorted(store):
        for idx, ch, want, ctx in _punctuation_violations(store[key]):
            failures.append(f"  {key} [idx {idx}]: {ch!r} should be {want!r} — …{ctx}…")

    if failures:
        pytest.fail(
            f"{fname} has {len(failures)} ASCII sentence-punctuation character(s) "
            f"adjacent to CJK in zh-TW:\n" + "\n".join(failures) +
            "\nTraditional Chinese uses fullwidth punctuation. If a case is a Latin "
            "fragment, a URL or a number, it will not be reported here — adjacency is "
            "checked, not presence."
        )


def test_the_punctuation_rule_actually_fires(sources):
    """A rule that cannot fail is dead weight. Inject a violation, prove it is caught."""
    clean = sources["utils/i18n-share.ts"]["zh-TW"]["publicDisclaimer"]
    assert _punctuation_violations(clean) == [], "real string should be clean"

    # Same string with ONE fullwidth comma reverted to ASCII.
    tampered = clean.replace("，", ",", 1)
    found = _punctuation_violations(tampered)
    assert len(found) == 1, f"injected violation not caught: {found}"
    assert found[0][1] == "," and found[0][2] == "，"

    # And the rule does NOT fire on ASCII punctuation inside a Latin fragment.
    assert _punctuation_violations("請參考 Vela, Inc. 的說明") == []
    assert _punctuation_violations("詳見 https://mcp.fda.gov.tw/a?b=1 的頁面") == []


@pytest.mark.parametrize("key", SHARED_KEYS)
def test_zh_tw_disclaimer_uses_fullwidth_punctuation(sources, key):
    """zh-TW is Traditional Chinese copy: the comma is 「，」 (U+FF0C), not ASCII.

    Fixed in fly 222 after a 2026-08-11 audit found ASCII commas in the
    hand-authored zh-TW disclaimer — the reference text every machine-translated
    locale was derived from. Pinned so it cannot regress in any of the three files.
    """
    checked = 0
    for fname, store in sources.items():
        if key not in store.get("zh-TW", {}):
            continue          # not every source carries every key
        text = store["zh-TW"][key]
        checked += 1
        assert "," not in text, (
            f"{fname} [{key}] zh-TW contains an ASCII comma (U+002C); "
            f"Traditional Chinese requires the fullwidth comma U+FF0C: {text!r}"
        )
    assert checked, f"{key} was not found in any source's zh-TW — nothing was checked"


def test_the_guard_actually_fires_on_divergence(sources):
    """A parity test that cannot fail is dead weight. Prove this one fails.

    Feeds the real comparison a set of sources in which ONE file's zh-TW long
    disclaimer differs by a single character, and asserts the check rejects it.
    """
    import copy

    tampered = copy.deepcopy(sources)
    victim = "api/services/share_renderer.py"
    tampered[victim]["zh-TW"]["publicDisclaimer"] += "。"

    with pytest.raises(BaseException) as excinfo:
        test_disclaimer_is_byte_identical_across_all_three_sources(
            tampered, "publicDisclaimer", "zh-TW"
        )
    assert "diverged across surfaces" in str(excinfo.value)

    # ...and the untampered real sources still pass, so the guard is not just noisy.
    test_disclaimer_is_byte_identical_across_all_three_sources(
        sources, "publicDisclaimer", "zh-TW"
    )


def test_no_duplicated_key_is_left_unguarded(sources):
    """Every key duplicated across the two 16-locale files must be under parity.

    THE BUSINESS RULE: the trap is structural — two files independently machine-
    translated the same English source and nothing compared them. Converging the
    keys that exist today does not stop a NEW shared key being added tomorrow and
    drifting the same way.

    This computes the overlap set live, so adding a key to both files fails here
    until you either put it under parity (add it to SHARED_KEYS) or record a
    deliberate exclusion in _KNOWN_UNGUARDED_DUPLICATES with a reason.

    As of fly 225 the exclusion set is EMPTY and this test expects zero unguarded
    duplicates. That is the point: there is no longer a "known bad" list to hide in.
    """
    ts_keys = set(sources["utils/i18n-share.ts"]["en"])
    ex_keys = set(sources["api/i18n/explore_strings.py"]["en"])
    overlap = ts_keys & ex_keys

    unguarded = overlap - set(SHARED_KEYS)
    assert unguarded == _KNOWN_UNGUARDED_DUPLICATES, (
        f"the set of duplicated-but-unguarded keys changed.\n"
        f"  expected: {sorted(_KNOWN_UNGUARDED_DUPLICATES)}\n"
        f"  actual:   {sorted(unguarded)}\n"
        "A key duplicated across both 16-locale files will drift. Either add it to "
        "SHARED_KEYS (after converging it) or add it to _KNOWN_UNGUARDED_DUPLICATES "
        "with a reason."
    )


# Per source: how many locales it must yield, and two canary keys that must
# parse non-empty in BOTH en and zh-TW. Canaries are per-source because
# utils/i18n.ts carries none of the legal disclaimer keys.
_PARSE_EXPECTATIONS = {
    "utils/i18n-share.ts": (16, ("publicDisclaimer", "publicShortDisclaimer")),
    "api/i18n/explore_strings.py": (16, ("publicDisclaimer", "publicShortDisclaimer")),
    "api/services/share_renderer.py": (2, ("publicDisclaimer", "publicShortDisclaimer")),
    # canary swapped cardDescResearch -> tagline 2026-08-28: the landing build car
    # retires the features-card section and deletes cardDesc* from all 16 locales;
    # tagline is a surviving landingContent key (>20 chars in en and zh-TW).
    "utils/i18n.ts": (16, ("landingContent.panelSub", "landingContent.tagline")),
}


def test_every_source_was_actually_parsed(sources):
    """Guard the guard: a parser that silently returns {} would pass everything above."""
    assert set(sources) == set(_PARSE_EXPECTATIONS), (
        "a source was added to the fixture without an expectation here — "
        f"fixture={sorted(sources)} expectations={sorted(_PARSE_EXPECTATIONS)}"
    )
    for fname, store in sources.items():
        n_locales, canaries = _PARSE_EXPECTATIONS[fname]
        assert len(store) == n_locales, (
            f"{fname} parsed {len(store)} locales, expected {n_locales}")
        for locale in ("en", "zh-TW"):
            for key in canaries:
                text = store.get(locale, {}).get(key)
                assert text, f"{fname} [{locale}][{key}] parsed as empty — parser is broken"
                assert len(text) > 20, f"{fname} [{locale}][{key}] suspiciously short: {text!r}"


def test_i18n_parser_covers_both_string_containers():
    """utils/i18n.ts holds its zh-TW copy in TWO places. A parser that found only
    one would report "clean" over half the file — the fly-222 sampling failure
    wearing a parser costume, which is precisely what this file exists to stop."""
    zh = _parse_i18n()["zh-TW"]
    landing = [k for k in zh if k.startswith("landingContent.")]
    app = [k for k in zh if k.startswith("translations.")]
    assert len(landing) >= 10, f"landingContent block under-parsed: {len(landing)} keys"
    assert len(app) >= 30, f"translations block under-parsed: {len(app)} keys"
    # The two containers must not silently merge into one namespace.
    assert not (set(landing) & set(app))
