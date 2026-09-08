# -*- coding: utf-8 -*-
"""/history research rows render the Research disclaimer from the ONE shared
source /research renders (HISTORY HONESTY car segment 4a, item (b)).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails): a Research
answer redisplayed on /history is a medical answer; without the informational-
use line the row misleads by omission (TECH_DEBT [HONESTY][P2], 2026-09-07).
And the line must come from ONE module — two page-local copies drift (the
2026-05 share/explore disclaimer drift is the precedent, 14 of 16 locales).

The checks live in tests/history_research_disclaimer_guard.mjs (the shared
module is transpiled and EXECUTED; the two pages are checked as source), run
inside the pytest count here — same split as tests/test_history_render_fallback.py.
"""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_disclaimer_guard_passes():
    """Hard failure if node is missing (Rule 18): a broken verification
    environment, not a skippable test."""
    result = subprocess.run(
        ["node", str(_ROOT / "tests" / "history_research_disclaimer_guard.mjs")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        shell=(sys.platform == "win32"),
    )
    assert result.returncode == 0, (
        "history_research_disclaimer_guard.mjs FAILED under pytest:\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )
