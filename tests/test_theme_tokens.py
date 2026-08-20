# -*- coding: utf-8 -*-
"""Theme-token discipline on the standalone token-background pages.

Generalized 2026-08-20 from test_faq_theme_tokens.py (git mv — history preserved)
when the /faq fix's family grep found the same defect on terms/privacy/refund/
pricing. WHAT BREAKS IF THESE FAIL: headings, emphasis spans, and link hovers
render white-on-white in the LIGHT scheme — the DEFAULT theme (globals.css
`.light`, live since 0d7df96) — illegible without selection. Founder-observed
on prod fly 238 (/faq); root cause on every page is the same dark-only-era
authoring whose bare `text-white` survived the C2a/C2b/C3 token migrations.

THE RULE: these five pages sit on the `bg-app-bg` TOKEN background, so a
hardcoded white TEXT CLASS on them is wrong in exactly one scheme — always —
UNLESS the element sits on a constant (scheme-invariant) background. Those
exceptions are ALLOW-LISTED BY EXACT LOCATION below so the list cannot grow
silently: each allow-listed snippet must occur EXACTLY ONCE, or the test fails
in the other direction.

Same idiom as tests/test_research_answer_scroll.py: read source, strip
comments, assert, negative-control every pattern. The rendered-page half is
the founder's one light-scheme eye row per page (STATE entry).
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_I18N_UI = _ROOT / "utils" / "i18n-ui.ts"
_I18N_FAQ = _ROOT / "utils" / "i18n-faq.ts"

# Legitimate white, pinned by exact source text (constant-background elements).
# faq/pricing nav buttons + the pricing badge use INLINE `color: '#fff'` on the
# brand background — inline styles are not matched by the class scan, so they
# need no listing. The ONE class-level exception:
_ALLOWED = {
    "pricing.tsx": [
        # The Pro CTA: text-white on the CONSTANT brand background (ACCENT).
        'className="mt-8 block text-center text-sm font-medium py-2.5 rounded-lg '
        'transition-opacity hover:opacity-90 text-white"',
    ],
}

_PAGES = ["faq.tsx", "terms.tsx", "privacy.tsx", "refund.tsx", "pricing.tsx"]

_WHITE_CLASS = re.compile(r"[\s\"':]text-white")


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _page(name: str) -> str:
    return _strip_comments((_ROOT / "pages" / name).read_text(encoding="utf-8"))


def test_no_hardcoded_white_text_class_on_token_pages():
    """No `text-white` (plain or hover:) outside the pinned allow-list."""
    for name in _PAGES:
        code = _page(name)
        for allowed in _ALLOWED.get(name, []):
            count = code.count(allowed)
            assert count == 1, (
                f"{name}: the allow-listed constant-background snippet occurs "
                f"{count}x, expected exactly 1 — the allow-list has rotted or "
                "silently grown; re-adjudicate before touching this test"
            )
            code = code.replace(allowed, " ")
        assert not _WHITE_CLASS.search(code), (
            f"{name}: a hardcoded text-white class is back on this bg-app-bg "
            "token-background page — illegible in one scheme (the fly-238 "
            "founder-observed light-scheme defect family)"
        )


def test_headings_carry_the_text_token():
    """Every page's h1 and section h2 color via the `text-text` token."""
    for name in _PAGES:
        code = _page(name)
        assert re.search(r"<h1[^>]*className=\"[^\"]*\btext-text\b", code), (
            f"{name}: the h1 no longer carries the text-text token"
        )
        assert re.search(r"<h2[^>]*className=\"[^\"]*\btext-text\b", code), (
            f"{name}: the section h2 headings no longer carry the text-text token"
        )


def test_no_white_alpha_inline_on_token_pages():
    """No rgba(255,255,255,…) inline values — the C2b white-alpha class these
    pages missed (pricing's Free-CTA hover background was the live instance)."""
    for name in _PAGES:
        code = _page(name)
        assert "rgba(255,255,255" not in code and "rgba(255, 255, 255" not in code, (
            f"{name}: a white-alpha inline value is back — invisible in the "
            "light scheme; use rgb(var(--color-text) / a)"
        )


def test_faq_cta_string_carries_no_hardcoded_white():
    """The faqCta i18n HTML (×16 locales) embeds its own styling — it must be
    token-based, not rgba(255,255,255,…) / hover:text-white."""
    src = _I18N_UI.read_text(encoding="utf-8")
    cta_lines = [l for l in src.split("\n") if re.search(r"\bfaqCta:\s*'", l)]
    assert len(cta_lines) >= 16, (
        f"expected >=16 faqCta cells (one per locale), got {len(cta_lines)} — "
        "the positive control for the assertions below"
    )
    for line in cta_lines:
        assert "rgba(255,255,255" not in line and "hover:text-white" not in line, (
            "a faqCta cell re-acquired hardcoded white styling: " + line.strip()[:120]
        )
        assert "var(--color-text)" in line, (
            "a faqCta cell no longer colors via the text token: " + line.strip()[:120]
        )


def test_i18n_strings_carry_no_hardcoded_white():
    """The i18n files these pages consume must embed no white styling anywhere
    (the faqCta class of defect — white hiding inside translated HTML cells)."""
    for f in (_I18N_UI, _I18N_FAQ):
        src = f.read_text(encoding="utf-8")
        assert "text-white" not in src and "rgba(255,255,255" not in src, (
            f"{f.name}: an i18n string embeds hardcoded white styling — the "
            "faqCta defect class is back"
        )


def test_the_guards_actually_fire():
    """Negative controls: each pattern must reject the pre-fix forms."""
    assert "text-white" not in _strip_comments("// never text-white here\n")
    assert "text-white" not in _strip_comments("{/* text-white KEPT deliberately */}")

    pre_fix_h2 = '<h2 className="text-lg font-semibold text-white mb-3">'
    assert _WHITE_CLASS.search(pre_fix_h2)
    assert not re.search(r"<h2[^>]*className=\"[^\"]*\btext-text\b", pre_fix_h2)

    pre_fix_hover = 'className="hover:text-white transition-colors"'
    assert _WHITE_CLASS.search(pre_fix_hover)

    pre_fix_alpha = ".style.background = 'rgba(255,255,255,0.1)';"
    assert "rgba(255,255,255" in pre_fix_alpha

    pre_fix_cta = "  faqCta: 'x <a class=\"hover:text-white\" style=\"color:rgba(255,255,255,0.6)\">y</a>',"
    assert "rgba(255,255,255" in pre_fix_cta and "hover:text-white" in pre_fix_cta

    # The class scan must NOT fire on the legitimate inline constant-bg whites:
    nav_button_inline = "style={{ background: ACCENT, color: '#fff' }}"
    assert not _WHITE_CLASS.search(nav_button_inline)
