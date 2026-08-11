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
