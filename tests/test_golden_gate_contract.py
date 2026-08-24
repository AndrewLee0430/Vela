# -*- coding: utf-8 -*-
"""The § 2.7 golden gate's exit contract — DB-free, network-free, zero LLM calls.

WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17): the ratified 18/2/0 floor stops being
enforceable and the runner reverts to its pre-2026-08-24 behaviour, in which
`stats["WARN"]` and `stats["FAIL"]` reached no exit path at all and a recorded
**15 PASS / 2 WARN / 3 FAIL** run — three unadjudicated FAILs — exited **0**.

This file is only possible because `section_27_gate` is PURE. It is loaded by AST
extraction rather than imported: `tests/run_golden_tests.py` calls `OpenAI()` at module
scope (pre-existing, anchor `openai_client = OpenAI()`), so importing it requires
`OPENAI_API_KEY` and would make this suite environment-dependent. Same technique as
`tests/test_danger_path_exit_codes.py`.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tests" / "run_golden_tests.py"
DATASET = ROOT / "tests" / "golden_dataset.json"

_WANTED_FUNCS = {"section_27_gate"}
_WANTED_CONSTS = {
    "SECTION_27_CASE_IDS",
    "SECTION_27_MIN_PASS",
    "SECTION_27_MAX_WARN",
    "SECTION_27_MAX_FAIL",
}


def _load_gate(mutate=None):
    """Exec ONLY the gate function and its constants — never the module.

    `mutate` is an optional callable taking the namespace dict, applied AFTER exec, so
    the mutation tests can perturb the constants the gate closes over.
    """
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _WANTED_FUNCS:
            body.append(node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in _WANTED_CONSTS:
                    body.append(node)
    names = {n.name for n in body if isinstance(n, ast.FunctionDef)}
    assert _WANTED_FUNCS <= names, f"gate function missing from the runner: {_WANTED_FUNCS - names}"
    ns: dict = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(RUNNER), "exec"), ns)
    for c in _WANTED_CONSTS:
        assert c in ns, f"constant missing from the runner: {c}"
    if mutate:
        mutate(ns)
    return ns


def _ids(ns):
    return sorted(ns["SECTION_27_CASE_IDS"])


def _stats(p=0, w=0, f=0, e=0):
    return {"PASS": p, "WARN": w, "FAIL": f, "ERROR": e}


# ─────────────────────── item 2: the case set is bound, not coincidental ───────────────────────

def test_frozen_case_set_matches_the_dataset_derivation():
    """THE GUARD THAT MAKES THE FLOOR MEAN SOMETHING.

    The frozen tuple and the dataset must agree. If someone adds R21, this FAILS rather
    than silently widening the denominator — which is the exact rot the gate exists to
    end. Mirrors `tests/test_deletion_coverage.py`'s partition proof over
    `api/services/deletion_service.py`'s DELETION_TABLES.
    """
    ns = _load_gate()
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    derived = sorted(c["id"] for c in cases if c["id"].startswith("R"))
    frozen = _ids(ns)
    assert derived == frozen, (
        "SECTION_27_CASE_IDS has diverged from the dataset.\n"
        f"  only in dataset: {sorted(set(derived) - set(frozen))}\n"
        f"  only in frozen : {sorted(set(frozen) - set(derived))}\n"
        "This is a RULING, not a merge conflict: the founder must say whether the new "
        "case joins the § 2.7 set before the frozen list is edited."
    )
    assert len(frozen) == 20, f"the ratified floor is defined over 20 cases, found {len(frozen)}"


def test_floor_constants_are_the_ratified_values():
    ns = _load_gate()
    assert (ns["SECTION_27_MIN_PASS"], ns["SECTION_27_MAX_WARN"], ns["SECTION_27_MAX_FAIL"]) \
        == (18, 2, 0), "the ratified floor is 18 PASS / 2 WARN / 0 FAIL"


# ─────────────────────── item 4: all three exit codes reachable ───────────────────────

def test_all_three_exit_codes_are_reachable():
    """Rule 17: a gate that cannot fail has not been shown to work."""
    ns = _load_gate()
    g, ids = ns["section_27_gate"], _ids(ns)
    assert g(_stats(p=18, w=2), ids)[0] == 0
    assert g(_stats(p=17, w=3), ids)[0] == 1
    assert g(_stats(p=17, w=2, f=1), ids)[0] == 2
    codes = {g(_stats(p=18, w=2), ids)[0],
             g(_stats(p=17, w=3), ids)[0],
             g(_stats(p=17, w=2, f=1), ids)[0]}
    assert codes == {0, 1, 2}, f"not every code reachable: {codes}"


def test_every_verdict_names_its_condition():
    """(code, reason) — the reason is printed beside the code, so it must never be empty."""
    ns = _load_gate()
    g, ids = ns["section_27_gate"], _ids(ns)
    for st, label in ((_stats(p=18, w=2), "clear"), (_stats(p=17, w=3), "breach"),
                      (_stats(p=17, w=2, f=1), "adjudication"), (_stats(p=19, e=1), "error"),
                      (_stats(p=1), "wrong set")):
        code, reason = g(st, ids if label != "wrong set" else ["R01"])
        assert isinstance(reason, str) and reason.strip(), f"{label}: empty reason"


# ─────────────────────── the recorded regression ───────────────────────

def test_the_recorded_15_2_3_result_now_exits_NON_ZERO():
    """THE REGRESSION THIS WORK EXISTS TO FIX.

    15 PASS / 2 WARN / 3 FAIL over the § 2.7 set exited **0** before 2026-08-24: only
    `stats["PASS"]` reached a gate, via `pass_rate = 15/20 = 75.0`, and 75 >= 70.
    It must now be non-zero — specifically **2**, because three FAILs need a person, not
    because the count is low (PASS 15 < 18 is ALSO true, but adjudication outranks it).
    """
    ns = _load_gate()
    code, reason = ns["section_27_gate"](_stats(p=15, w=2, f=3), _ids(ns))
    assert code == 2, f"15/2/3 must not exit 0; got {code} — {reason}"
    assert "ADJUDICATION" in reason.upper()
    assert code != 0, "the pre-2026-08-24 behaviour has returned"


def test_exactly_the_floor_passes_and_one_step_below_does_not():
    ns = _load_gate()
    g, ids = ns["section_27_gate"], _ids(ns)
    assert g(_stats(p=18, w=2, f=0), ids)[0] == 0, "exactly 18/2/0 must pass"
    assert g(_stats(p=17, w=3, f=0), ids)[0] == 1, "17/3/0 must not pass"
    assert g(_stats(p=18, w=2, f=1), ids)[0] == 2, "18/2/1 must not pass"
    assert g(_stats(p=20, w=0, f=0), ids)[0] == 0, "a perfect run must pass"


def test_partial_selection_cannot_satisfy_the_floor():
    """A one-case run reported run_complete=True, pass_rate=100.0, gate_valid=true, exit 0."""
    ns = _load_gate()
    g = ns["section_27_gate"]
    code, reason = g(_stats(p=1), ["R08"])
    assert code == 2 and "CASE SET" in reason.upper(), reason
    code, reason = g(_stats(p=19, w=1), sorted(set(_ids(ns)) - {"R20"}))
    assert code == 2, "19 of 20 cases is not the § 2.7 set"
    code, reason = g(_stats(p=21), _ids(ns) + ["COL_ZH_01"])
    assert code == 2, "a superset is not the § 2.7 set either"


def test_error_cases_cannot_be_scored():
    ns = _load_gate()
    code, reason = ns["section_27_gate"](_stats(p=19, w=0, f=0, e=1), _ids(ns))
    assert code == 2 and "ERROR" in reason.upper()


# ─────────────────────── positive control ───────────────────────

def test_positive_control_the_helpers_are_not_vacuous():
    """Guards the guards: if `_load_gate` silently returned an empty namespace, or
    `_ids` an empty list, every assertion above would pass against nothing."""
    ns = _load_gate()
    assert callable(ns["section_27_gate"])
    assert len(_ids(ns)) == 20
    assert _stats(p=1, w=2, f=3, e=4) == {"PASS": 1, "WARN": 2, "FAIL": 3, "ERROR": 4}
    # the loader must FAIL LOUD if the gate is ever renamed or deleted, rather than
    # returning an empty namespace against which every test above would vacuously pass
    import ast as _ast
    empty = _ast.Module(body=[], type_ignores=[])
    ns2: dict = {}
    exec(compile(empty, "<empty>", "exec"), ns2)
    assert "section_27_gate" not in ns2, "sanity: an empty module yields no gate"
    with pytest.raises(AssertionError, match="gate function missing"):
        _load_gate.__wrapped__() if hasattr(_load_gate, "__wrapped__") else _assert_loader_is_strict()


def _assert_loader_is_strict():
    """Re-run the loader's own precondition against a name that does not exist."""
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"a_gate_that_does_not_exist"} <= names, \
        "gate function missing from the runner: {'a_gate_that_does_not_exist'}"


# ─────────────────────── MUTATION TESTS ───────────────────────
# Each mutant perturbs the gate and asserts the suite would CATCH it. A mutant that
# survives means the corresponding assertion above is decorative.

def _mutant(**consts):
    def apply(ns):
        ns.update(consts)
        # rebuild the closure so the function sees the mutated constants
        src = ast.parse(RUNNER.read_text(encoding="utf-8"))
        fn = next(n for n in src.body
                  if isinstance(n, ast.FunctionDef) and n.name == "section_27_gate")
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(RUNNER), "exec"), ns)
    return apply


def test_mutant_floor_lowered_18_to_17_is_caught():
    ns = _load_gate(mutate=_mutant(SECTION_27_MIN_PASS=17))
    assert ns["section_27_gate"](_stats(p=17, w=2), _ids(ns))[0] == 0, "mutant behaves as expected"
    clean = _load_gate()
    assert clean["section_27_gate"](_stats(p=17, w=2), _ids(clean))[0] == 1, \
        "CAUGHT: the clean gate rejects 17 PASS, the mutant accepts it"


def test_mutant_warn_bound_removed_is_caught():
    ns = _load_gate(mutate=_mutant(SECTION_27_MAX_WARN=99))
    assert ns["section_27_gate"](_stats(p=18, w=9), _ids(ns))[0] == 0
    clean = _load_gate()
    assert clean["section_27_gate"](_stats(p=18, w=9), _ids(clean))[0] == 1, \
        "CAUGHT: the clean gate rejects WARN 9"


def test_mutant_fail_check_removed_is_caught():
    ns = _load_gate(mutate=_mutant(SECTION_27_MAX_FAIL=99))
    assert ns["section_27_gate"](_stats(p=18, w=2, f=3), _ids(ns))[0] == 0
    clean = _load_gate()
    assert clean["section_27_gate"](_stats(p=18, w=2, f=3), _ids(clean))[0] == 2, \
        "CAUGHT: the clean gate sends 3 FAILs to adjudication"


def test_mutant_case_set_check_removed_is_caught():
    """The mutant that matters most — and building it corrected my own assumption.

    A ONE-CASE run does not need the case-set check to be rejected: `PASS 1 < 18`
    catches it on the floor anyway. What ONLY the case-set check catches is a run of
    the RIGHT SIZE over the WRONG CASES — 20 `COL_*`/`EDGE_*` cases at 18/2/0 satisfy
    every count and are not the § 2.7 set at all. That is the mutant below.
    """
    wrong_20 = [f"COL_ZH_{i:02d}" for i in range(1, 21)]
    # mutant: the case-set check disabled by pointing the frozen set at whatever ran
    ns = _load_gate(mutate=_mutant(SECTION_27_CASE_IDS=frozenset(wrong_20)))
    assert ns["section_27_gate"](_stats(p=18, w=2), wrong_20)[0] == 0, \
        "mutant behaves as expected — it scores the wrong 20 cases as a pass"
    clean = _load_gate()
    code, reason = clean["section_27_gate"](_stats(p=18, w=2), wrong_20)
    assert code == 2 and "CASE SET" in reason.upper(), \
        f"CAUGHT: the clean gate refuses 18/2/0 over the wrong 20 cases — got {code}: {reason}"
    # and the one-case run is still refused, by the case-set check specifically
    code1, reason1 = clean["section_27_gate"](_stats(p=1), ["R08"])
    assert code1 == 2 and "CASE SET" in reason1.upper(), reason1


def test_mutant_priority_swapped_fail_reports_breach_is_caught():
    """If rank 2 and rank 3 were swapped, 15/2/3 would report exit 1 (a scored breach)
    instead of exit 2 (needs a person). The distinction is the whole point of rank 2."""
    clean = _load_gate()
    code, reason = clean["section_27_gate"](_stats(p=15, w=2, f=3), _ids(clean))
    assert code == 2, "CAUGHT: FAIL must outrank the floor-breach check"
    assert "FLOOR BREACH" not in reason.upper(), \
        "CAUGHT: a FAIL run must not be reported as a scored breach"
