# -*- coding: utf-8 -*-
"""Markdown lists render as LISTS on /research and /history (HISTORY HONESTY
car segment 4b — founder ruling 2026-09-09 = Option B, narrow list rules).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails): the
`prose` classes on both pages generate NO CSS (`@tailwindcss/typography` was
never registered — `tailwind.config.js` `plugins: []`), so Tailwind preflight
flattens every markdown `- ` / `1. ` list into plain lines while the share
page shows bullets for the same markdown (TECH_DEBT [OTHER][P3], 2026-09-03).
The fix is ONE narrow class (`.vela-md-list`: ul / ol / li / li::marker only)
on the three live ReactMarkdown wrappers. Lose the class on a wrapper and that
surface goes flat again; widen the rule set and the "narrow" ruling is broken;
register the plugin and both pages change everywhere `prose` is written; let
the compiled bundle drop the rules (content glob / @layer tree-shaking — what
emptied `.markdown-content`, since deleted) and the class is a no-op exactly like
`prose`. HISTORY RENDER LEFTOVERS car segment 1 (2026-09-11) extends the guard: both
/history research paths now render through <ReactMarkdown> (the no-section path used
to print stored markdown RAW), and the dead MarkdownRenderer component + the orphan
`.markdown-content` block are asserted GONE rather than merely unaltered.

The checks live in tests/research_list_render_guard.mjs (source checks with
comments stripped; the markdown pipeline EXECUTED with the pages' plugin set;
the compiled bundle under out/ READ — a missing build FAILS, Rule 18), run
inside the pytest count here — same split as tests/test_history_research_disclaimer.py.
"""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_research_list_render_guard_passes():
    """Hard failure if node is missing (Rule 18): a broken verification
    environment, not a skippable test."""
    result = subprocess.run(
        ["node", str(_ROOT / "tests" / "research_list_render_guard.mjs")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        shell=(sys.platform == "win32"),
    )
    assert result.returncode == 0, (
        "research_list_render_guard.mjs FAILED under pytest:\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )
