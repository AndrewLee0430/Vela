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

# Keys carried by all three files. The other two legal-weighted share keys
# (modalConsentCheckbox, settingsRevokeConfirm) live only in the .ts file and
# so have no parity obligation.
SHARED_KEYS = ("publicDisclaimer", "publicShortDisclaimer")

# share_renderer.py ships en + zh-TW only, so those are the locales all three
# files have in common — the full set over which parity is even defined.
SHARED_LOCALES = ("en", "zh-TW")

_TS_CONST_TO_LOCALE = {"en": "en", "zhTW": "zh-TW"}


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
    """{locale: {key: value}} from the `const <x>: ShareTranslations = {...}` blocks."""
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
        for key in SHARED_KEYS:
            m = re.search(r"(?<![\w])" + key + r"\s*:\s*", block)
            if not m:
                continue
            j = m.end()
            while block[j] in " \t\r\n":
                j += 1
            vals[key] = _read_js_string(block, j)
        out[locale] = vals
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
    }


@pytest.mark.parametrize("locale", SHARED_LOCALES)
@pytest.mark.parametrize("key", SHARED_KEYS)
def test_disclaimer_is_byte_identical_across_all_three_sources(sources, key, locale):
    """One legal string, three files. Any drift between them fails here."""
    texts = {}
    for fname, store in sources.items():
        assert locale in store, f"{fname} is missing locale {locale!r}"
        assert key in store[locale], f"{fname} [{locale}] is missing key {key!r}"
        texts[fname] = store[locale][key]

    distinct = set(texts.values())
    if len(distinct) != 1:
        detail = "\n".join(f"  {fname}:\n    {text!r}" for fname, text in texts.items())
        pytest.fail(
            f"{key} [{locale}] has diverged across surfaces — "
            f"{len(distinct)} distinct texts:\n{detail}\n"
            "A visitor-facing legal string must be identical everywhere it renders. "
            "Apply the correction to ALL THREE files."
        )


@pytest.mark.parametrize("key", SHARED_KEYS)
def test_zh_tw_disclaimer_uses_fullwidth_punctuation(sources, key):
    """zh-TW is Traditional Chinese copy: the comma is 「，」 (U+FF0C), not ASCII.

    Fixed in fly 222 after a 2026-08-11 audit found ASCII commas in the
    hand-authored zh-TW disclaimer — the reference text every machine-translated
    locale was derived from. Pinned so it cannot regress in any of the three files.
    """
    for fname, store in sources.items():
        text = store["zh-TW"][key]
        assert "," not in text, (
            f"{fname} [{key}] zh-TW contains an ASCII comma (U+002C); "
            f"Traditional Chinese requires the fullwidth comma U+FF0C: {text!r}"
        )


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


def test_all_three_sources_were_actually_parsed(sources):
    """Guard the guard: a parser that silently returns {} would pass everything above."""
    for fname, store in sources.items():
        for locale in SHARED_LOCALES:
            for key in SHARED_KEYS:
                text = store.get(locale, {}).get(key)
                assert text, f"{fname} [{locale}][{key}] parsed as empty — parser is broken"
                assert len(text) > 20, f"{fname} [{locale}][{key}] suspiciously short: {text!r}"
