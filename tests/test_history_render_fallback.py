# -*- coding: utf-8 -*-
"""/history render fidelity — fallback wiring + behavioral guard (segments 1 + 3).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
Old history rows CANNOT be backfilled (the verify detail was never written; the
research citations were never written), so the page carries two renderers per
mode: structured cards for new-format rows, and the pre-segment plain-text
rendering for legacy rows. If the fallback branches disappear, every
pre-2026-09-01 verify row and every pre-segment-3 research row renders blank
or crashes; if the ShareButton reads the raw stored JSON, a share created from
a new-format verify OR research row publishes the payload verbatim to a PUBLIC
page (segment 3: a research_v1 row must share its MARKDOWN, never the JSON).

Source assertions here pin the wiring in pages/history.tsx; the behavioral half
(the parsers executed against legacy and new-format fixtures) lives in
tests/history_render_fallback_guard.mjs, run inside the pytest count below —
same split as tests/test_locale_hint_suppression.py.
"""
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PAGE = _ROOT / "pages" / "history.tsx"


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*[\s\S]*?\*/", " ", src)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _page_source() -> str:
    return _strip_comments(_PAGE.read_text(encoding="utf-8"))


SHARE_TEXT_RE = (
    r"answerText=\{verifyParsed\?\.summary\s*\?\?\s*"
    r"researchParsed\?\.answer\s*\?\?\s*item\.answer\}"
)


def test_share_text_never_the_raw_json():
    """The ShareButton must read the summary out of a new-format verify row
    and the MARKDOWN out of a new-format research row — publishing item.answer
    verbatim would put either JSON payload on a public share page."""
    code = _page_source()
    assert re.search(SHARE_TEXT_RE, code), (
        "ShareButton no longer prefers verifyParsed.summary ?? researchParsed.answer "
        "— a share from a new-format verify or research row would publish the raw "
        "stored JSON"
    )


def test_all_fallback_branches_are_wired():
    """Each mode keeps its legacy rendering reachable: verify's plain box and
    research's pre-wrap paragraph must still exist alongside the cards path;
    research_v1 rows must reach the shared CitationPanel."""
    code = _page_source()
    assert "parseVerifyAnswer" in code, "verify safe-parse helper missing"
    assert "parseResearchAnswer" in code, "research_v1 safe-parse helper missing"
    assert "parseResearchSections" in code, "research section parser not used"
    # The legacy verify plain box (pre-segment-1 markup) is still present.
    assert code.count("whitespace-pre-wrap") >= 1, (
        "the research pre-wrap fallback rendering disappeared"
    )
    assert re.search(r"VerifyInteractionCard", code), (
        "the shared verify card is no longer rendered on /history"
    )
    assert re.search(r"<CitationPanel\s+citations=\{researchParsed\.citations\}", code), (
        "research_v1 citations no longer render through the shared CitationPanel"
    )


def test_behavioral_guard_passes():
    """The parsers executed against legacy + new-format fixtures — not just
    written. Hard failure if node is missing (Rule 18): that is a broken
    verification environment, not a skippable test."""
    result = subprocess.run(
        ["node", str(_ROOT / "tests" / "history_render_fallback_guard.mjs")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        shell=(sys.platform == "win32"),
    )
    assert result.returncode == 0, (
        "history_render_fallback_guard.mjs FAILED under pytest:\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )


def test_the_guards_actually_fire():
    """Negative controls: the patterns above reject plausible wrong versions."""
    # Comment stripping removes prose naming the identifiers.
    assert "parseVerifyAnswer" not in _strip_comments("// parseVerifyAnswer in prose\n")
    assert "parseResearchAnswer" not in _strip_comments("/* parseResearchAnswer */\n")
    # The share pattern is NOT satisfied by the pre-segment-1 raw form, nor by
    # the segment-1 form (which would publish a research_v1 row's raw JSON).
    assert not re.search(SHARE_TEXT_RE, "answerText={item.answer}")
    assert not re.search(SHARE_TEXT_RE, "answerText={verifyParsed?.summary ?? item.answer}")
