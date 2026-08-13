# -*- coding: utf-8 -*-
"""B1 — the below-fold landing sections must use TOKEN colors only.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
The landing renders in both .light and .dark via the CSS variable system. A
color hardcoded outside that system is invisible to theming — exactly how the
share pages shipped white-on-white at fly 219 (four rules held hardcoded white
the theme never reached) and needed the fly 220 legibility fix.

SCOPE: components/LandingSections.tsx only — the file this baton adds. The
fly-220 test pattern (parse Jinja, composite tokens, compute WCAG ratios) does
NOT transfer to client-rendered TSX (Tailwind classes resolve at build, there
is no rendered stylesheet to composite here); what DOES transfer cleanly is
its companion check, test_no_hardcoded_colours_outside_the_variable_system —
this file is that check for the new component. index.tsx is deliberately NOT
scanned: its pre-existing Dashboard has a hardcoded gradient (bg-gradient-to-r
from-[#ff6b6b]...) that predates this rule and is not this baton's to fix.
"""
import re
from pathlib import Path

_COMPONENT = Path(__file__).resolve().parents[1] / "components" / "LandingSections.tsx"

# Forbidden: raw hex colors, rgba()/hsl(), and numeric rgb() NOT going through
# the variable system. Allowed: rgb(var(--...)) in any form.
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGBA_OR_HSL = re.compile(r"\b(?:rgba|hsla?)\(")
_NUMERIC_RGB = re.compile(r"\brgb\(\s*\d")   # rgb(255 … / rgb(255, … — not rgb(var(


def test_no_hardcoded_colors_in_landing_sections():
    src = _COMPONENT.read_text(encoding="utf-8")
    problems = []
    for name, pat in (("hex literal", _HEX), ("rgba()/hsl()", _RGBA_OR_HSL),
                      ("numeric rgb()", _NUMERIC_RGB)):
        for m in pat.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            problems.append(f"  line {line}: {name}: {src[m.start():m.start()+40]!r}")
    assert not problems, (
        "hardcoded color literals in LandingSections.tsx — theming cannot reach these "
        "(the fly 219/220 regression class):\n" + "\n".join(problems)
    )


def test_every_color_reference_uses_the_variable_system():
    """Positive check: the color styles that DO exist all go through var()."""
    src = _COMPONENT.read_text(encoding="utf-8")
    color_styles = re.findall(r"(?:color|background)\s*:\s*'([^']+)'", src)
    assert color_styles, "no inline color styles found — did the component shape change?"
    bad = [c for c in color_styles if "var(--color-" not in c]
    assert not bad, f"inline color styles bypassing the token system: {bad}"


def test_the_guard_actually_fires():
    """A guard that cannot fail is dead weight."""
    assert _HEX.search("style={{ color: '#a0aec0' }}")
    assert _RGBA_OR_HSL.search("background: rgba(255,255,255,0.4)")
    assert _NUMERIC_RGB.search("color: rgb(255 142 110)")
    assert not _NUMERIC_RGB.search("color: rgb(var(--color-text) / 0.6)")


# ── B4.1d — the panel headline gradient ──────────────────────────────────────
# The gradient lives in globals.css, not in the component, because a class is
# the only way to attach the forced-colors fallback. That move must NOT become
# a loophole in the rule above: the same token discipline is asserted here, at
# the gradient's new home, plus the fallback that makes it safe.

_GLOBALS = Path(__file__).resolve().parents[1] / "styles" / "globals.css"
_GRADIENT_CLASS = ".panel-gradient-text"
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _css() -> str:
    """globals.css with comments stripped.

    Comments are stripped because they discuss the very declarations these
    tests assert on. Verbatim: removing `background-clip: text` from the rule
    still satisfied a search of the raw file, because the comment above it
    contains the words "`background-clip: text` with a transparent fill". The
    same file's token guard has twice failed on colors written in its OWN
    comments; this is that hazard in the opposite direction — prose making a
    check pass. Assertions must read the CSS, not the commentary.
    """
    return _CSS_COMMENT.sub("", _GLOBALS.read_text(encoding="utf-8"))


def _gradient_block() -> str:
    """The FIRST .panel-gradient-text rule body (the base rule, not the
    forced-colors override, which is nested inside its own @media)."""
    css = _css()
    i = css.index(_GRADIENT_CLASS)
    return css[i:css.index("}", i) + 1]


def test_panel_gradient_uses_tokens_only():
    """The gradient must be theme-reachable — same rule as the component."""
    block = _gradient_block()
    assert "var(--color-paper)" in block, (
        "the panel headline gradient does not reference the paper token — "
        "theming cannot reach it (the fly 219/220 regression class)"
    )
    for name, pat in (("hex literal", _HEX), ("rgba()/hsl()", _RGBA_OR_HSL),
                      ("numeric rgb()", _NUMERIC_RGB)):
        assert not pat.search(block), f"{name} in the panel gradient: {block!r}"


def test_panel_gradient_has_a_forced_colors_fallback():
    """WHAT BREAKS IF THIS FAILS: `background-clip: text` with a transparent
    fill renders the panel headline COMPLETELY INVISIBLE in Windows High
    Contrast mode — the largest claim on the page, gone, for exactly the users
    who need contrast most."""
    css = _css()
    # Negative lookbehind: a bare `in css` check is satisfied by the sibling
    # `-webkit-background-clip: text`, so it would keep reporting "still
    # clipping" after the standard property was removed.
    assert re.search(r"(?<!-webkit-)background-clip:\s*text", css), (
        "gradient no longer clips to text — is this test stale?"
    )
    at = css.find("@media (forced-colors: active)")
    assert at != -1, "no forced-colors block in globals.css"
    block = css[at:css.index("}\n}", at) + 3] if "}\n}" in css[at:] else css[at:]
    assert _GRADIENT_CLASS in block, (
        f"{_GRADIENT_CLASS} has no forced-colors fallback — the headline would be "
        "invisible in Windows High Contrast mode"
    )
    # BOTH declarations, not just one. The base rule blanks the text twice —
    # `color: transparent` AND `-webkit-text-fill-color: transparent` — and
    # forced-colors mode does not override -webkit-text-fill-color, so a
    # fallback that restores only `color` still renders an invisible headline
    # in Chromium/Edge. A single "CanvasText" grep would pass that half-fix.
    assert re.search(r"(?<!-webkit-text-fill-)color:\s*CanvasText", block), (
        "forced-colors fallback does not restore `color` to a system text color"
    )
    assert re.search(r"-webkit-text-fill-color:\s*CanvasText", block), (
        "forced-colors fallback restores `color` but leaves "
        "`-webkit-text-fill-color: transparent` from the base rule in effect — "
        "the headline is still invisible in Chromium/Edge High Contrast mode"
    )
