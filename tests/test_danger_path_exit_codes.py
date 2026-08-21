"""All three danger-path gate exit codes must be REACHABLE (CLAUDE.md Rule 17).

What breaks if this fails: the gate's exit contract silently regresses to the
pre-2026-08-21 shape, where `rechecks` was computed and printed but never entered
the return — so a run with 0 violations and outstanding mandatory founder rechecks
exited 0 and read as a pass to any automated caller. That is the defect the
ratification commit fixed; this test is what keeps it fixed.

Criterion ratified 2026-08-21 — TECH_DEBT.md:242 (entry) / :245 (ratification).

DB-free and network-free: `gate_exit_code` is pure, and the module is loaded by
file path so no `scripts/` package import is required.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dailymed_danger_path_verify.py"


def _gate_exit_code():
    """Load ONLY the pure function, without executing the script's pipeline.

    The module imports the api stack at import time, so we compile the source and
    exec just the function definition rather than the whole module.
    """
    import ast

    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next((n for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name == "gate_exit_code"), None)
    assert fn is not None, "gate_exit_code() is missing from the danger-path script"
    ns: dict = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SCRIPT), "exec"), ns)
    return ns["gate_exit_code"]


@pytest.mark.parametrize(
    "violations,rechecks,expected",
    [
        (0, 0, 0),   # clean
        (1, 0, 1),   # hard violation
        (0, 1, 2),   # founder eye required, NOT a failure  <- the leg that used to be ignored
    ],
)
def test_three_exit_codes_are_reachable(violations, rechecks, expected):
    code, condition = _gate_exit_code()(violations, rechecks)
    assert code == expected, (
        f"({violations} violations, {rechecks} rechecks) -> exit {code}, expected {expected}")
    assert condition, "every exit must name the condition that produced it"


def test_violation_outranks_recheck():
    """Both present -> the caller must see the FAILURE, not the softer signal."""
    code, condition = _gate_exit_code()(2, 3)
    assert code == 1
    assert "VIOLATION" in condition


def test_recheck_alone_is_not_a_silent_pass():
    """THE REGRESSION GUARD: rechecks with zero violations must NOT exit 0.

    This is the exact pre-2026-08-21 behaviour — `return 0 if not violations else 1`
    would return 0 here.
    """
    code, _ = _gate_exit_code()(0, 3)
    assert code != 0, ("0 violations + 3 mandatory rechecks exited 0 — the pre-ratification "
                       "defect has returned")
    assert code == 2
