"""B4.5 A — the Research answer pane must land on the Summary when a stream ends.

WHAT BREAKS IF THESE FAIL: the answer pane auto-follows incoming tokens, so at
the end of generation the user is parked at the BOTTOM of a long answer and has
to scroll up to find the Summary — the payoff of the query. Founder-reported on
/research.

⚠️ SCOPE, STATED HONESTLY. These are SOURCE assertions, not behavioural ones.
The completion path only runs against a live SSE stream, so the end-to-end
behaviour ("query finishes → pane shows the Summary") is NOT verified here and
cannot be at unit level in this repo — there is no JS test runner, and the page
needs the FastAPI backend plus a real credit-costing query to reach the code at
all. What these tests DO pin is the structure the fix depends on, including the
one premise that can break silently from a distance (see the ordering test).

Same idiom as tests/test_landing_sections_tokens.py: read the TSX, assert on it,
and negative-control the patterns so a regex that matches nothing cannot pass.
"""

import re
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1] / "pages" / "research.tsx"


def _src() -> str:
    return _RESEARCH.read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """JS block + line comments removed.

    Load-bearing: this fix is documented by a ~30-line comment that NAMES every
    identifier asserted below ('loading', 'scrollTo', 'prefers-reduced-motion',
    'wasLoadingRef'). Without stripping, deleting the entire implementation and
    keeping the comment would leave every test here green. This repo has been
    bitten by prose satisfying a check twice already.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def test_pane_scrolls_to_top_on_completion():
    code = _strip_comments(_src())
    assert re.search(r"scrollTo\(\s*\{\s*top:\s*0", code), (
        "no scroll-to-top on the answer pane — the user is left parked at the "
        "bottom of the answer when generation finishes"
    )


def test_scroll_to_top_fires_only_on_the_loading_edge():
    """A premature scroll that later tokens undo is WORSE than the defect.

    The trigger must be the `loading` true→false EDGE, not `loading === false`
    (which is also true before the query starts and on every unrelated re-render
    afterwards, so the pane would fight the user's own scrolling).
    """
    code = _strip_comments(_src())
    assert "wasLoadingRef" in code, (
        "no edge-tracking ref — scroll-to-top cannot distinguish 'generation "
        "just finished' from 'not currently generating'"
    )
    # The early-return that makes it an edge: bail unless we WERE loading and
    # are no longer.
    assert re.search(r"if\s*\(\s*!wasLoading\s*\|\|\s*loading\s*\)\s*return", code), (
        "the loading-edge guard is missing or reshaped — scroll-to-top may now "
        "fire on renders that are not the end of a stream"
    )


def test_scroll_respects_reduced_motion():
    code = _strip_comments(_src())
    assert "prefers-reduced-motion" in code, (
        "the completion scroll does not consult prefers-reduced-motion"
    )
    assert re.search(r"behavior:\s*\w+\s*\?\s*['\"]auto['\"]\s*:\s*['\"]smooth['\"]", code), (
        "reduced motion must get an INSTANT jump ('auto') and everyone else the "
        "smooth travel; the conditional is gone or inverted"
    )


def test_stream_following_is_still_intact():
    """The fix must not have replaced the follow-the-stream behaviour.

    Landing on the Summary is what happens AFTER generation; during generation
    the pane should still track incoming tokens.
    """
    code = _strip_comments(_src())
    assert re.search(r"scrollTop\s*=\s*\w+\.current\.scrollHeight", code), (
        "the answer pane no longer follows the stream while it is generating"
    )


def test_composed_render_is_still_gated_on_loading():
    """THE PREMISE OF THE WHOLE FIX, and the one that can break from a distance.

    `loading` going false is simultaneously (a) the completion signal this fix
    triggers on and (b) what swaps the raw stream for the composed render
    (ProvenanceLine + parseResearchSections → <ResearchSection> cards). Because
    both come from the SAME state change, React commits the composed DOM before
    the effect runs, so the scroll lands on the finished Summary.

    If someone later drives the composed render from a different trigger — a
    separate state flag, a timeout, an async parse — that ordering guarantee
    dissolves SILENTLY: the scroll would fire against the raw stream and the
    re-render would follow it. Nothing else in the codebase would complain.
    """
    code = _strip_comments(_src())
    assert re.search(r"const\s+sections\s*=\s*!loading\s*\?\s*parseResearchSections", code), (
        "the composed Summary/Clinical-Notes render is no longer gated on "
        "`!loading` — the completion scroll can no longer be relied on to land "
        "AFTER it. Re-check the ordering before changing this test."
    )


def test_the_guards_actually_fire():
    """Negative controls: every pattern above must reject a plausible wrong
    version, otherwise a passing suite proves nothing."""
    # Comment stripping really removes the documentation that names everything.
    doc_only = "// wasLoadingRef scrollTo({ top: 0 }) prefers-reduced-motion\n"
    assert "wasLoadingRef" not in _strip_comments(doc_only)
    assert "prefers-reduced-motion" not in _strip_comments("/* prefers-reduced-motion */")

    # The edge guard must not be satisfied by the naive form.
    naive = "if (loading) return;"
    assert not re.search(r"if\s*\(\s*!wasLoading\s*\|\|\s*loading\s*\)\s*return", naive)

    # scroll-to-top must not be satisfied by the scroll-to-bottom that already
    # existed — the exact regression this file exists to prevent.
    follow_only = "el.scrollTop = ref.current.scrollHeight;"
    assert not re.search(r"scrollTo\(\s*\{\s*top:\s*0", follow_only)

    # Reduced motion must not be satisfied by an unconditional smooth scroll.
    unconditional = "el.scrollTo({ top: 0, behavior: 'smooth' });"
    assert not re.search(
        r"behavior:\s*\w+\s*\?\s*['\"]auto['\"]\s*:\s*['\"]smooth['\"]", unconditional
    )
