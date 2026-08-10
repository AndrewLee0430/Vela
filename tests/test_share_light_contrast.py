# -*- coding: utf-8 -*-
"""fly 220 — a public page's LIGHT scheme must be legible. WCAG AA, computed.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
Text on a public medical page must be readable. Not "styled reasonably" —
readable, at WCAG AA (4.5:1 for body text).

What broke, and why a test exists at all: fly 219 shipped `prefers-color-scheme`
by theming the `--vela-*` VARIABLES, but four rules held **hardcoded** white
outside that system (`.vela-citation-abstract`, `.vela-citation-meta`,
`.vela-footer-copy`, `.vela-evidence-title`). Theming never reached them, so in
light they rendered white-on-white at **1.00–1.11:1** — the citation snippet and
the PubMed author/journal line were invisible on a live public page. A fifth
token, `--vela-text-subtle`, was defined in light but at 2.92:1 — below AA, and
it carries the **medical short-disclaimer**.

None of that was caught, because a whole new colour scheme shipped with no
legibility check in that scheme.

WHY THIS TEST COMPUTES RATHER THAN ASSERTS A LIST
-------------------------------------------------
A hardcoded "these values are fine" list would have passed at fly 219 too — the
values were fine, they just were not reaching the elements. This parses the real
template, composites each token over the background it is actually painted on,
and computes the contrast ratio. A new colour that fails AA fails this test even
if nobody remembers to add it to a list. A rule that stops using the variable
system is caught by `test_no_hardcoded_colours_outside_the_variable_system`.
"""
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TEMPLATES = Path(__file__).resolve().parents[1] / "api" / "templates"
_BASES = ("q_base.jinja2", "explore_base.jinja2")

# WCAG 2.1 SC 1.4.3
_AA_BODY = 4.5


def _srgb(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgb) -> float:
    r, g, b = (_srgb(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def composite(fg, alpha: float, bg):
    """Paint `fg` at `alpha` over opaque `bg` — what the eye actually sees."""
    return tuple(round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


def _parse(value: str):
    """'rgba(23,23,23,0.75)' | '#1f2937' -> ((r,g,b), alpha)."""
    value = value.split("/*")[0].strip().rstrip(";").strip()
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", value)
    if m:
        a = float(m.group(4)) if m.group(4) else 1.0
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))), a
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), 1.0
    return None


def light_tokens(base: str) -> dict[str, str]:
    """The DEFAULT :root block — everything before the dark media query."""
    css = (_TEMPLATES / base).read_text(encoding="utf-8")
    head = css[: css.index("@media (prefers-color-scheme: dark)")]
    return dict(re.findall(r"(--vela-[a-z0-9-]+):\s*([^;]+);", head))


# Each text token, and the element background it is ACTUALLY painted on.
# `page` = the light gradient's lightest stop (#ffffff) — the worst case for ink.
_SURFACES = {
    "page": ("--vela-bg-1", None),
    "card": ("--vela-card-bg-hover", "page"),   # .vela-citation-card
    "evidence": ("--vela-section-bg", "page"),  # .vela-evidence-card
}

_TEXT_ON = [
    ("--vela-text-body", "page"),                 # body, .vela-prose
    ("--vela-text-muted", "page"),                # tagline, citations title, chips
    ("--vela-text-subtle", "page"),               # footer links, SHORT DISCLAIMER
    ("--vela-text-primary", "card"),              # citation source name
    ("--vela-citation-abstract-fg", "card"),      # the snippet — fly-219 defect
    ("--vela-citation-meta-fg", "card"),          # authors/journal — fly-219 defect
    ("--vela-footer-copy-fg", "page"),            # fly-219 defect
    ("--vela-evidence-title-fg", "evidence"),     # fly-219 defect
    ("--vela-prose-headings", "page"),
    ("--vela-prose-bold", "page"),
]


def _resolve_bg(tokens: dict, name: str):
    var, over_name = _SURFACES[name]
    rgb, alpha = _parse(tokens[var])
    if over_name is None:
        return rgb
    return composite(rgb, alpha, _resolve_bg(tokens, over_name))


@pytest.mark.parametrize("base", _BASES)
@pytest.mark.parametrize("token,surface", _TEXT_ON)
def test_light_text_token_meets_wcag_aa(base, token, surface):
    """Every light-scheme text token, composited over its real background."""
    tokens = light_tokens(base)
    assert token in tokens, f"{base}: {token} missing from the light block"
    parsed = _parse(tokens[token])
    assert parsed, f"{base}: could not parse {token} = {tokens[token]!r}"
    fg, alpha = parsed
    bg = _resolve_bg(tokens, surface)
    seen = composite(fg, alpha, bg)
    ratio = contrast(seen, bg)
    assert ratio >= _AA_BODY, (
        f"{base}: {token} renders at {ratio:.2f}:1 on the {surface} background "
        f"(rgb{bg}) — below WCAG AA {_AA_BODY}:1. This is the fly-219 class of "
        f"defect: a scheme shipped without a legibility check in that scheme."
    )


@pytest.mark.parametrize("base", _BASES)
def test_no_hardcoded_colours_outside_the_variable_system(base):
    """The fly-219 ROOT CAUSE guard.

    fly 219's light values were correct and still invisible, because four rules
    never consumed them. Any colour literal in the CSS body — outside the two
    :root blocks — is unreachable by the theme and will be wrong in one scheme.
    """
    ACHROMATIC_TOLERANCE = 8   # max-min channel spread still counted as grey

    def _achromatic_literals(line: str):
        """Only ACHROMATIC literals (white / black / grey) must be themed.

        A chromatic BRAND colour is legitimately scheme-invariant: coral
        (#ff8e6e / rgba(255,142,110,…) / rgba(255,107,107,…)) is the same in
        light and dark by design — see styles/globals.css, where --color-brand
        is identical in .light and .dark. Greys are the opposite: they encode
        "near the background", so they MUST flip. That is exactly what the
        fly-219 defect was.
        """
        out = []
        for m in re.finditer(r"#([0-9a-fA-F]{6})|rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", line):
            if m.group(1):
                h = m.group(1)
                rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            else:
                rgb = tuple(int(m.group(i)) for i in (2, 3, 4))
            if max(rgb) - min(rgb) <= ACHROMATIC_TOLERANCE:
                out.append(m.group(0))
        return out

    # Documented exception: white text sits on the coral CTA button, whose
    # background is brand-coloured and scheme-invariant, so white is correct in
    # both schemes. Scoped to that one declaration, not a blanket allowance.
    EXCEPT_SELECTORS = {".vela-cta-button"}

    css = (_TEMPLATES / base).read_text(encoding="utf-8")
    body = css[css.index("@media (prefers-color-scheme: dark)"):]
    body = body[body.index("}\n}") + 3:]          # everything after the dark block

    offenders, selector = [], ""
    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"^\.?[a-zA-Z.#][^{]*\{", stripped):
            selector = stripped.split("{")[0].strip()
        if stripped.startswith(("*", "/*", "//")) or "var(--vela-" in line:
            continue
        if selector in EXCEPT_SELECTORS:
            continue
        for lit in _achromatic_literals(line):
            offenders.append(f"{selector} -> {stripped}   [{lit}]")

    assert not offenders, (
        f"{base}: {len(offenders)} ACHROMATIC colour literal(s) outside the variable "
        f"system — the theme cannot reach them, so they will be wrong in one scheme "
        f"(this is the fly-219 defect):\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("base", _BASES)
def test_dark_block_still_defines_every_token_light_defines(base):
    """A token added to one scheme and forgotten in the other falls back to the
    other scheme's value — the same silent-wrongness shape as the fly-219 bug."""
    css = (_TEMPLATES / base).read_text(encoding="utf-8")
    i = css.index("@media (prefers-color-scheme: dark)")
    light = set(re.findall(r"(--vela-[a-z0-9-]+):", css[:i]))
    dark = set(re.findall(r"(--vela-[a-z0-9-]+):", css[i:]))
    assert light == dark, (
        f"{base}: schemes define different token sets.\n"
        f"  light only: {sorted(light - dark)}\n  dark only: {sorted(dark - light)}"
    )
