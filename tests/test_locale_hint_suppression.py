# -*- coding: utf-8 -*-
"""ADR-007 (d) option (ii) — grounded answers must suppress the integrated authority's pointer row.

WHAT BREAKS IF THESE FAIL: the 在地差異 panel renders localeHintNote — "Vela has not integrated
data from these authorities" — under a TFDA pointer row on a screen whose ONLY cited source IS the
integrated 10,941-doc TFDA corpus (fly-214 gate Finding 3; TECH_DEBT [P2 · honesty / user-visible
contradiction]). Or, inverted: the protective pointer disappears from un-grounded answers, where it
is the only safeguard.

⚠️ SCOPE, STATED HONESTLY (the test_research_answer_scroll.py idiom). There is no JS test runner,
so the tests here are SOURCE assertions plus one subprocess hop: the BEHAVIORAL half — the filter's
actual remove/keep/pass-through semantics over the transpiled TS — lives in
tests/locale_hint_data_guard.mjs §9, and test_behavioral_guard_passes executes it under pytest so
"the guard exists but nothing runs it" cannot happen (the four-times-recorded prose hazard). The
source assertions pin the WIRING the behavioral guard cannot see: that the render site actually
calls the filter and that the mount site feeds it fresh citation source types.

Comments are stripped before matching — the explanatory comments at every one of these sites name
the exact identifiers asserted below, so an implementation deleted with its comment kept would
otherwise stay green.
"""

import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LOCALE_HINT = _ROOT / "utils" / "localeHint.ts"
_PANEL = _ROOT / "components" / "LocaleHintPanel.tsx"
_RESEARCH = _ROOT / "pages" / "research.tsx"


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _src(path: Path) -> str:
    return _strip_comments(path.read_text(encoding="utf-8"))


def test_filter_helper_exists_and_is_exported():
    """(i) The mechanism: a pure, exported helper + the plural-by-construction key set (Rule 23)."""
    code = _src(_LOCALE_HINT)
    assert re.search(r"export\s+function\s+filterUngroundedAuthorities\s*\(", code), (
        "filterUngroundedAuthorities is not exported from utils/localeHint.ts — the suppression "
        "mechanism is gone or hidden from the data guard"
    )
    assert re.search(r"export\s+const\s+INTEGRATED_AUTHORITY_KEYS\s*:\s*ReadonlySet<string>\s*=\s*new\s+Set\(", code), (
        "INTEGRATED_AUTHORITY_KEYS is not an exported ReadonlySet — b2 ingests must extend a SET, "
        "not rewrite a mechanism (Rule 23: plural by construction)"
    )
    assert re.search(r"new\s+Set\(\s*\[\s*'tfda'", code), (
        "the integrated set no longer holds 'tfda' — the v193 TFDA corpus is integrated and "
        "retrieved; an empty/wrong set silently re-opens the fly-214 contradiction"
    )
    assert re.search(r"integrated_source:\s*'tfda'", code), (
        "TW_TFDA no longer carries integrated_source 'tfda' — the authority→source_type mapping is "
        "the key the filter matches on; without it TFDA can never be suppressed"
    )


def test_render_site_calls_the_filter():
    """(iv) The panel must actually CALL the filter where authorities are computed.

    An exported-but-uncalled helper is the exact shape of the prose hazard: the mechanism exists,
    the render path bypasses it, everything reads as done.
    """
    code = _src(_PANEL)
    assert re.search(
        r"filterUngroundedAuthorities\s*\(\s*getAuthoritiesForCategories\s*\(", code
    ), (
        "LocaleHintPanel no longer routes its authority rows through filterUngroundedAuthorities — "
        "the grounded-answer suppression is bypassed at the render site"
    )
    assert re.search(r"citationSourceTypes\s*,?\s*\)", code) and "citationSourceTypes" in code, (
        "the panel does not consume a citationSourceTypes prop — the filter has nothing fresh to "
        "match against"
    )
    # The TFDA-only collapse path: the existing empty-authorities guard must still exist, because
    # it is the INTENDED way a fully-suppressed panel disappears (no second mechanism).
    assert re.search(r"!authorities\.length\s*\)\s*return\s+null", code), (
        "the `!authorities.length → return null` guard is gone — the ADR-007 (d) design relies on "
        "it as the collapse path when the filter empties the list"
    )


def test_mount_site_passes_fresh_citation_source_types():
    """(iv-b) research.tsx must derive the source types FROM citations and pass them to the panel.

    Freshness comes from React's render model (setCitations → re-render → new prop), NOT from the
    trigger memo's dep array — the recon's stale-deps hazard is closed by never reading citations
    inside that memo at all. These assertions pin that wiring.
    """
    code = _src(_RESEARCH)
    assert re.search(
        r"new\s+Set<string>\(\s*citations\.map\(\s*c\s*=>\s*detectSourceType\(\s*c\s*\)", code
    ), (
        "citationSourceTypes is no longer derived from `citations` via detectSourceType — the "
        "filter would match raw/un-normalized source_type strings, or nothing at all"
    )
    assert re.search(r"\[\s*citations\s*\]\s*,?\s*\)", code), (
        "the citationSourceTypes memo is no longer keyed on [citations] — a stale set could "
        "outlive the citations on screen"
    )
    assert re.search(r"<LocaleHintPanel[^>]*citationSourceTypes=\{citationSourceTypes\}", code, flags=re.S), (
        "the LocaleHintPanel mount site no longer passes citationSourceTypes — the panel would "
        "filter against an empty/undefined set on every answer"
    )
    # The trigger memo's dep array must stay citation-free — that is the wiring decision. If
    # someone adds `citations` there, this test forces them to re-derive the freshness argument.
    memo_deps = re.search(
        r"return\s*\{\s*categories,\s*country,\s*level\s*\};\s*\},\s*\[([^\]]*)\]", code
    )
    assert memo_deps, "the localeHint trigger memo (categories/country/level) was not found"
    assert "citations" not in memo_deps.group(1), (
        "`citations` entered the trigger memo's deps — the ratified wiring keeps the filter on the "
        "panel-prop path; if this moved into the memo, re-verify freshness end to end before "
        "changing this test"
    )


def test_behavioral_guard_passes():
    """(i)(ii)(iii)(v) The behavioral semantics, executed — not just written.

    tests/locale_hint_data_guard.mjs §9 transpiles utils/localeHint.ts and asserts: removes-when-
    grounded, keeps-when-un-grounded, non-set authorities pass through, positive controls. Running
    it here puts those assertions inside the pytest count instead of relying on someone remembering
    the node command. Hard failure by design (Rule 18) — if node is missing, that is a broken
    verification environment, not a skippable test.
    """
    # encoding pinned: the guard prints UTF-8 (CJK + em-dashes); the Windows default cp950 decode
    # raises in the capture thread — the recorded cp950 console-encoding TECH_DEBT class.
    result = subprocess.run(
        ["node", str(_ROOT / "tests" / "locale_hint_data_guard.mjs")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        shell=(sys.platform == "win32"),
    )
    assert result.returncode == 0, (
        "locale_hint_data_guard.mjs FAILED under pytest:\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )


def test_the_guards_actually_fire():
    """(v) Negative controls: every pattern above must reject a plausible wrong version."""
    # Comment stripping really removes prose that names the identifiers.
    doc_only = "// filterUngroundedAuthorities(getAuthoritiesForCategories( citationSourceTypes\n"
    assert "filterUngroundedAuthorities" not in _strip_comments(doc_only)
    assert "citationSourceTypes" not in _strip_comments("/* citationSourceTypes={citationSourceTypes} */")

    # The render-site pattern must not be satisfied by the UNFILTERED pre-change form.
    pre_change = "const authorities = getAuthoritiesForCategories(authoritySet, matchedCategories);"
    assert not re.search(r"filterUngroundedAuthorities\s*\(\s*getAuthoritiesForCategories\s*\(", pre_change)

    # The mount-site pattern must not be satisfied by a panel that drops the prop.
    bare_mount = "<LocaleHintPanel matchedCategories={localeHint.categories} lang={lang} />"
    assert not re.search(r"<LocaleHintPanel[^>]*citationSourceTypes=\{citationSourceTypes\}", bare_mount)

    # The derivation pattern must not be satisfied by passing RAW source_type strings.
    raw_types = "new Set<string>(citations.map(c => c.source_type))"
    assert not re.search(r"new\s+Set<string>\(\s*citations\.map\(\s*c\s*=>\s*detectSourceType\(\s*c\s*\)", raw_types)

    # The exported-set pattern must not be satisfied by a non-exported or non-Set registry.
    private_set = "const INTEGRATED_AUTHORITY_KEYS = ['tfda']"
    assert not re.search(
        r"export\s+const\s+INTEGRATED_AUTHORITY_KEYS\s*:\s*ReadonlySet<string>\s*=\s*new\s+Set\(", private_set
    )
