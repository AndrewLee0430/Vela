# -*- coding: utf-8 -*-
"""fly-238 founder finding — /faq must use theme TOKENS, never hardcoded white.

WHAT BREAKS IF THESE FAIL: the FAQ section headings (關於 Vela / 功能 / 隱私與安全)
and the page h1 render white-on-white in the LIGHT scheme — which is the DEFAULT
theme (globals.css `.light`, live since 0d7df96) — illegible without selection.
Founder-observed on prod fly 238. Root cause: the page was authored in the
dark-only era (fef4436, 2026-04-08) with `text-white`, and the C2a/C2b/C3 theme
migrations tokenized backgrounds and white/NN ALPHA consumers but not bare
`text-white`.

THE RULE THESE TESTS PIN: pages/faq.tsx has a token background (`bg-app-bg`),
so a hardcoded white TEXT CLASS on it is wrong in exactly one scheme — always.
The one legitimate white on the page is the nav sign-up button's inline
`color: '#fff'`, which sits on the CONSTANT brand background (scheme-invariant),
not on a token background; the assertions below are scoped to classes so that
stays out of scope.

Same idiom as tests/test_research_answer_scroll.py: read the source, strip
comments, assert, and negative-control every pattern so a regex that matches
nothing cannot pass. The human-eye half (does the light page actually read?) is
the one-row render check recorded in the STATE entry — a source test cannot see
a rendered page.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_FAQ = _ROOT / "pages" / "faq.tsx"
_I18N_UI = _ROOT / "utils" / "i18n-ui.ts"


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def test_faq_has_no_hardcoded_white_text_class():
    """No `text-white` (plain or hover:) may survive on the theme-aware page."""
    code = _strip_comments(_FAQ.read_text(encoding="utf-8"))
    assert not re.search(r"[\s\"':]text-white", code), (
        "a hardcoded text-white class is back on pages/faq.tsx — on the "
        "bg-app-bg token background this is illegible in one scheme (the "
        "founder-observed fly-238 light-scheme defect)"
    )


def test_faq_headings_carry_the_text_token():
    """The h1 and the section h2 must color via the `text-text` token."""
    code = _strip_comments(_FAQ.read_text(encoding="utf-8"))
    assert re.search(r"<h1[^>]*className=\"[^\"]*\btext-text\b", code), (
        "the FAQ h1 no longer carries the text-text token"
    )
    assert re.search(r"<h2[^>]*className=\"[^\"]*\btext-text\b", code), (
        "the FAQ section h2 (the founder-observed headings) no longer carries "
        "the text-text token"
    )


def test_faq_cta_string_carries_no_hardcoded_white():
    """The faqCta i18n HTML (×16 locales) embeds its own styling — it must be
    token-based, not rgba(255,255,255,…) / hover:text-white."""
    src = _I18N_UI.read_text(encoding="utf-8")
    cta_lines = [l for l in src.split("\n") if re.search(r"\bfaqCta:\s*'", l)]
    assert len(cta_lines) >= 16, (
        f"expected >=16 faqCta cells (one per locale), got {len(cta_lines)} — "
        "the positive control for the two assertions below"
    )
    for line in cta_lines:
        assert "rgba(255,255,255" not in line and "hover:text-white" not in line, (
            "a faqCta cell re-acquired hardcoded white styling: " + line.strip()[:120]
        )
        assert "var(--color-text)" in line, (
            "a faqCta cell no longer colors via the text token: " + line.strip()[:120]
        )


def test_the_guards_actually_fire():
    """Negative controls: each pattern must reject the pre-fix form."""
    # Comment stripping really strips the explanatory comment that names text-white.
    assert "text-white" not in _strip_comments("// never text-white here\n")

    pre_fix_h2 = '<h2 className="text-lg font-semibold text-white mb-2">'
    assert re.search(r"[\s\"':]text-white", pre_fix_h2)
    assert not re.search(r"<h2[^>]*className=\"[^\"]*\btext-text\b", pre_fix_h2)

    pre_fix_hover = 'className="cursor-pointer transition-colors hover:text-white"'
    assert re.search(r"[\s\"':]text-white", pre_fix_hover)

    pre_fix_cta = "  faqCta: 'x <a class=\"hover:text-white transition-colors\" style=\"color:rgba(255,255,255,0.6)\">y</a>',"
    assert "rgba(255,255,255" in pre_fix_cta and "hover:text-white" in pre_fix_cta

    # The scoped class pattern must NOT fire on the legitimate constant-bg white:
    nav_button_inline = "style={{ background: 'rgb(var(--color-brand))', color: '#fff' }}"
    assert not re.search(r"[\s\"':]text-white", nav_button_inline)
