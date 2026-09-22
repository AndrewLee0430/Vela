# -*- coding: utf-8 -*-
"""/history Explain LEGACY (pre-wrap) rows render the server-supplied
`item.disclaimer`, requested in the UI language; no frontend copy of the
Explain disclaimer strings exists (HISTORY RENDER LEFTOVERS car, segment 2).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails): a legacy
Explain row redisplayed on /history is a medical explanation; without the
caption the row misleads by omission (TECH_DEBT [HONESTY][P3], 2026-09-09).
The caption's ONE source is Python (api/i18n/explain_strings.py) — option (i),
a frontend copy, was DECLINED 2026-09-11 because two sources drift (the
2026-05 share/explore disclaimer drift is the precedent, 14 of 16 locales).

The checks live in tests/history_explain_disclaimer_guard.mjs (the page and
the Python source are checked as source), run inside the pytest count here —
same split as tests/test_history_research_disclaimer.py.
"""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_explain_disclaimer_guard_passes():
    """Hard failure if node is missing (Rule 18): a broken verification
    environment, not a skippable test."""
    result = subprocess.run(
        ["node", str(_ROOT / "tests" / "history_explain_disclaimer_guard.mjs")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        shell=(sys.platform == "win32"),
    )
    assert result.returncode == 0, (
        "history_explain_disclaimer_guard.mjs FAILED under pytest:\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )
