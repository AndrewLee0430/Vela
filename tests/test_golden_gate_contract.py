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

THE GATE TAKES PER-CASE RECORDS, NOT `stats` — so every test here feeds records, via
`_recs`. That signature is the 2026-08-24 correction: a global `stats` would let three
COL_* FAILs on a full 133-case run be attributed to § 2.7 adjudication.
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


def _load_gate(mutate=None, source: str | None = None):
    """Exec ONLY the gate function and its constants — never the module.

    `source` overrides the runner's own text, so `_load_gate`'s STRICTNESS can be tested
    against a source that genuinely lacks the gate (see
    `test_load_gate_raises_when_its_preconditions_are_unmet`) rather than against a copy
    of its logic. `mutate` is an optional callable taking the namespace dict, applied
    AFTER exec, so the mutation tests can perturb the constants the gate closes over.
    """
    src = RUNNER.read_text(encoding="utf-8") if source is None else source
    origin = str(RUNNER) if source is None else "<alternative-source>"
    tree = ast.parse(src)
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
    exec(compile(ast.Module(body=body, type_ignores=[]), origin, "exec"), ns)
    for c in _WANTED_CONSTS:
        assert c in ns, f"constant missing from the runner: {c}"
    if mutate:
        mutate(ns)
    return ns


def _ids(ns):
    return sorted(ns["SECTION_27_CASE_IDS"])


def _recs(p=0, w=0, f=0, e=0, ids=None):
    """Per-case result records — the shape `results` actually holds in the runner.

    Anchored on the two `results.append({...})` sites, which both carry `id` and
    `status`. Asserts the verdict mix covers the ids exactly, so a test cannot silently
    build a set whose size it did not intend.
    """
    ids = list(_ids(_load_gate()) if ids is None else ids)
    statuses = ["PASS"] * p + ["WARN"] * w + ["FAIL"] * f + ["ERROR"] * e
    assert len(statuses) == len(ids), (
        f"_recs given {len(statuses)} verdicts for {len(ids)} ids — the test means "
        f"something other than what it wrote")
    return [{"id": i, "status": s} for i, s in zip(ids, statuses)]


def _non_s27(n, status="PASS"):
    """Filler records OUTSIDE the § 2.7 set — the other 113 cases of a full run."""
    return [{"id": f"COL_ZH_{i:02d}", "status": status} for i in range(1, n + 1)]


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


# ─────────────────────── all three exit codes reachable ───────────────────────

def test_all_three_exit_codes_are_reachable():
    """Rule 17: a gate that cannot fail has not been shown to work."""
    ns = _load_gate()
    g = ns["section_27_gate"]
    assert g(_recs(p=18, w=2))[0] == 0
    assert g(_recs(p=17, w=3))[0] == 1
    assert g(_recs(p=17, w=2, f=1))[0] == 2
    codes = {g(_recs(p=18, w=2))[0], g(_recs(p=17, w=3))[0], g(_recs(p=17, w=2, f=1))[0]}
    assert codes == {0, 1, 2}, f"not every code reachable: {codes}"


def test_every_verdict_names_its_condition():
    """(code, reason, verdict) — the reason is printed beside the code and stored in the
    JSON, so it must never be empty, and the verdict must always be complete data."""
    ns = _load_gate()
    g = ns["section_27_gate"]
    cases = [
        (_recs(p=18, w=2), "clear"),
        (_recs(p=17, w=3), "breach"),
        (_recs(p=17, w=2, f=1), "adjudication"),
        (_recs(p=19, e=1), "error"),
        (_recs(p=1, ids=["R08"]), "not a § 2.7 run"),
    ]
    for recs, label in cases:
        code, reason, verdict = g(recs)
        assert isinstance(reason, str) and reason.strip(), f"{label}: empty reason"
        assert verdict["reason"] == reason, f"{label}: verdict.reason diverges from the returned reason"
        assert verdict["exit_code"] == code, f"{label}: verdict.exit_code diverges from the returned code"
        for key in ("scored", "floor_met", "case_ids_scored", "missing", "counts", "floor"):
            assert key in verdict, f"{label}: verdict missing {key}"


# ─────────────────────── the recorded regression ───────────────────────

def test_the_recorded_15_2_3_result_now_exits_NON_ZERO():
    """THE REGRESSION THIS WORK EXISTS TO FIX — and must-not-regress #4.

    15 PASS / 2 WARN / 3 FAIL over the § 2.7 set exited **0** before 2026-08-24: only
    `stats["PASS"]` reached a gate, via `pass_rate = 15/20 = 75.0`, and 75 >= 70.
    It must be **2**, because three FAILs need a person — not 1, even though PASS 15 < 18
    is ALSO true. That C-outranks-D ordering is the whole reason rank C exists.
    """
    ns = _load_gate()
    code, reason, verdict = ns["section_27_gate"](_recs(p=15, w=2, f=3))
    assert code == 2, f"15/2/3 must not exit 0; got {code} — {reason}"
    assert "ADJUDICATION" in reason.upper()
    assert "FLOOR BREACH" not in reason.upper(), \
        "a FAIL run must not be reported as a scored breach — that is rank D's verdict"
    assert verdict["scored"] is True, "the § 2.7 set DID run; it just needs a person"
    assert verdict["floor_met"] is None, "an unadjudicated run has no floor verdict"


def test_exactly_the_floor_passes_and_one_step_below_does_not():
    """⚠️ Every mix here sums to 20 — `_recs` enforces it, and that is not pedantry.

    Under the record-taking signature the counts are no longer free-floating: they are a
    partition of the 20 § 2.7 cases. "18/2/1" is not a possible run at all (21 cases);
    the nearest real thing is 18 PASS / 1 WARN / 1 FAIL, which is what a single FAIL
    inside an otherwise-clean floor actually looks like.
    """
    ns = _load_gate()
    g = ns["section_27_gate"]
    assert g(_recs(p=18, w=2, f=0))[0] == 0, "exactly 18/2/0 must pass"
    assert g(_recs(p=17, w=3, f=0))[0] == 1, "17/3/0 must not pass"
    assert g(_recs(p=18, w=1, f=1))[0] == 2, "one FAIL blocks an otherwise-clean floor"
    assert g(_recs(p=18, w=1, f=1))[2]["floor_met"] is not True
    assert g(_recs(p=20))[0] == 0, "a perfect run must pass"
    assert g(_recs(p=20))[2]["floor_met"] is True


def test_the_two_floor_clauses_are_ARITHMETICALLY_THE_SAME_at_20_cases():
    """🔴 A PROPERTY OF THE RATIFIED FLOOR, found while writing the mutants — recorded
    here rather than left implicit, because it changes what the mutation tests can prove.

    Reaching rank D requires FAIL == 0, ERROR == 0, no duplicates and no unknown status
    (ranks B and C fire first). So PASS + WARN == 20, and therefore

        PASS < 18   ⟺   WARN > 2

    are the SAME condition. The ratified floor's two numbers are one constraint stated
    twice. Consequence, stated plainly: LOOSENING either constant cannot change any exit
    code, so those mutants are caught on the REASON TEXT, not the exit — see
    `test_mutant_floor_lowered_18_to_17_is_caught`. Both clauses are kept because each
    names its own half in the message, and because the identity dissolves the moment the
    denominator is not 20 (which the frozen-set guard forces a ruling on).
    """
    ns = _load_gate()
    g = ns["section_27_gate"]
    for p in range(0, 21):
        code, reason, v = g(_recs(p=p, w=20 - p))
        pass_low, warn_high = p < 18, (20 - p) > 2
        assert pass_low == warn_high, f"the identity broke at PASS={p}"
        assert code == (1 if pass_low else 0), f"PASS={p} exited {code}: {reason}"
        assert v["counts"]["PASS"] + v["counts"]["WARN"] == 20


def test_error_cases_cannot_be_scored():
    ns = _load_gate()
    code, reason, verdict = ns["section_27_gate"](_recs(p=19, e=1))
    assert code == 2 and "ERROR" in reason.upper()
    assert verdict["floor_met"] is None


# ─────────────────────── MUST-NOT-REGRESS (founder-specified, 2026-08-24) ───────────────────────

def test_single_case_selection_is_NOT_SCORED_and_exits_zero():
    """MUST-NOT-REGRESS #1 — `--filter R08`, one case, passing.

    Before subset scoring this exited 2, which is what made the documented full-suite and
    --smoke invocations unusable. It must now be exit 0 AND `scored: false`, and NOTHING
    in the verdict may be mistakable for a floor pass.
    """
    ns = _load_gate()
    code, reason, v = ns["section_27_gate"](_recs(p=1, ids=["R08"]))
    assert code == 0, f"a one-case selection is not a failure; got {code} — {reason}"
    assert v["scored"] is False
    assert v["floor_met"] is None, "null, never true — there is no floor verdict here"
    assert v["counts"] is None, "a partial tally could be misread as a floor result"
    assert v["case_ids_scored"] == []
    assert len(v["missing"]) == 19 and "R01" in v["missing"] and "R08" not in v["missing"]
    assert "FLOOR MET" not in reason.upper(), "the reason must not read as a pass"
    assert "NOT SCORED" in reason.upper()
    # and the JSON payload as a whole carries no true-ish pass signal
    assert True not in (v["scored"], v["floor_met"])


def test_wrong_twenty_cases_are_the_same_class_as_a_one_case_run():
    """MUST-NOT-REGRESS #3 — 20 cases that are the WRONG 20.

    Counts alone cannot tell this from a real § 2.7 run: 18/2/0 satisfies every
    threshold. Only the case set can. Under subset scoring the verdict is NOT SCORED /
    exit 0, identical in class to the one-case run — both simply are not § 2.7 runs.
    """
    ns = _load_gate()
    wrong_20 = [f"COL_ZH_{i:02d}" for i in range(1, 21)]
    code, reason, v = ns["section_27_gate"](_recs(p=18, w=2, ids=wrong_20))
    assert code == 0, f"the wrong 20 is not a § 2.7 failure, it is not a § 2.7 run; got {code}"
    assert v["scored"] is False and v["floor_met"] is None
    assert v["counts"] is None
    assert len(v["missing"]) == 20, "every § 2.7 case is missing from this run"
    assert v["non_section_27_cases_ignored"] == 20
    one_case = ns["section_27_gate"](_recs(p=1, ids=["R08"]))[2]
    assert (v["scored"], v["floor_met"], v["counts"]) == \
           (one_case["scored"], one_case["floor_met"], one_case["counts"]), \
        "the wrong-20 run and the one-case run must be the same class"


def test_full_133_case_run_yields_a_real_verdict_and_leaves_pass_rate_reachable():
    """MUST-NOT-REGRESS #2 — a full run must be SCORED, and must still reach rank 3.

    Two halves, because either alone is insufficient:
      (a) BEHAVIOURAL — the 20 R cases at 18/2/0 inside a 133-case run produce a REAL
          § 2.7 verdict (scored, floor_met true) and exit 0 from this gate;
      (b) STRUCTURAL — exit 0 only keeps `pass_rate < 70` reachable if that check still
          sits AFTER the § 2.7 exit in `run_tests` and the § 2.7 exit is CONDITIONAL.
          Asserted over the runner's AST, since `run_tests` cannot be called here.
    """
    ns = _load_gate()
    full = _recs(p=18, w=2) + _non_s27(113)
    assert len(full) == 133, "the full dataset is 133 cases"
    code, reason, v = ns["section_27_gate"](full)
    assert code == 0 and v["scored"] is True and v["floor_met"] is True, reason
    assert v["counts"] == {"PASS": 18, "WARN": 2, "FAIL": 0, "ERROR": 0}
    assert v["non_section_27_cases_ignored"] == 113
    assert sorted(v["case_ids_scored"]) == _ids(ns)

    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "run_tests")
    dumps = [ast.unparse(st) for st in fn.body]
    s27_exit = [i for i, s in enumerate(dumps) if "_s27_code" in s and "sys.exit" in s]
    rate_gate = [i for i, s in enumerate(dumps) if "pass_rate < 70" in s]
    assert len(s27_exit) == 1, f"expected exactly one § 2.7 exit statement, found {len(s27_exit)}"
    assert len(rate_gate) == 1, f"expected exactly one `pass_rate < 70` gate, found {len(rate_gate)}"
    assert s27_exit[0] < rate_gate[0], "the § 2.7 gate must be composed BEFORE the 70% gate"
    stmt = fn.body[s27_exit[0]]
    assert isinstance(stmt, ast.If), \
        "the § 2.7 exit must be CONDITIONAL — an unconditional sys.exit would make " \
        "`pass_rate < 70` dead code, which is exactly the 838d0e6 defect"


def test_non_section_27_failures_are_never_attributed_to_section_27():
    """THE SIGNATURE CHANGE ITSELF — the correction subset scoring needed.

    A full run whose 20 R cases are a clean 18/2/0 but whose COL_* cases hold 3 FAILs.
    Reading a global `stats` here would count FAIL=3 and send a clean § 2.7 result to
    founder adjudication. Deriving counts from the § 2.7 records cannot do that.
    """
    ns = _load_gate()
    full = _recs(p=18, w=2) + _non_s27(110) + _non_s27(3, status="FAIL")
    code, reason, v = ns["section_27_gate"](full)
    assert v["counts"]["FAIL"] == 0, \
        f"COL_* FAILs leaked into the § 2.7 tally: {v['counts']}"
    assert code == 0 and v["floor_met"] is True, \
        f"a clean § 2.7 subset must not be failed by non-§ 2.7 cases — got {code}: {reason}"
    # and the converse: § 2.7 FAILs are still caught inside a full run
    dirty = _recs(p=15, w=2, f=3) + _non_s27(113)
    assert ns["section_27_gate"](dirty)[0] == 2, "§ 2.7 FAILs must still fire inside a full run"


# ─────────────────────── positive control + loader strictness ───────────────────────

def test_positive_control_the_helpers_are_not_vacuous():
    """Guards the guards: if `_load_gate` silently returned an empty namespace, or
    `_ids` an empty list, every assertion above would pass against nothing."""
    ns = _load_gate()
    assert callable(ns["section_27_gate"])
    assert len(_ids(ns)) == 20
    recs = _recs(p=1, w=2, f=3, e=14)
    assert len(recs) == 20 and {r["status"] for r in recs} == {"PASS", "WARN", "FAIL", "ERROR"}
    with pytest.raises(AssertionError, match="verdicts for"):
        _recs(p=5, ids=["R01", "R02"])  # the mix-vs-ids guard must itself be live


def test_load_gate_raises_when_its_preconditions_are_unmet():
    """THE LOADER'S OWN STRICTNESS, exercised against the REAL loader.

    Replaces a test that could not fail: it asserted a deliberately-nonexistent name was
    present, so it raised unconditionally and the enclosing `pytest.raises` passed no
    matter what `_load_gate` did. This feeds `_load_gate` a source that genuinely lacks
    the gate — and one that genuinely lacks a constant — and requires the real loader to
    raise. Both `.replace(...)` results are asserted to differ from the original, so a
    rename cannot silently turn the mutation into a no-op and the test back into a
    tautology.

    NEGATIVE CONTROL, observed 2026-08-24: deleting the `assert _WANTED_FUNCS <= names`
    line from `_load_gate` makes this test FAIL with `DID NOT RAISE <class
    'AssertionError'>`. A guard that has not been observed failing has not been observed.
    """
    src = RUNNER.read_text(encoding="utf-8")

    no_func = src.replace("def section_27_gate(", "def section_27_gate_RENAMED(", 1)
    assert no_func != src, "the gate was renamed — this mutation no longer removes it"
    with pytest.raises(AssertionError, match="gate function missing"):
        _load_gate(source=no_func)

    no_const = src.replace("SECTION_27_MIN_PASS = 18", "SECTION_27_MIN_PASS_RENAMED = 18", 1)
    assert no_const != src, "the constant was renamed — this mutation no longer removes it"
    with pytest.raises(AssertionError, match="constant missing"):
        _load_gate(source=no_const)

    # positive half: the real source loads cleanly through the same code path
    assert callable(_load_gate(source=src)["section_27_gate"])


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
    """⚠️ CATCH MECHANISM CHANGED on 2026-08-24, and it is honest to say so.

    Before the record-taking signature this mutant was caught on the EXIT CODE. It no
    longer can be: by the identity in
    `test_the_two_floor_clauses_are_ARITHMETICALLY_THE_SAME_at_20_cases`, any run that
    reaches rank D breaches on WARN too, so lowering MIN_PASS changes no exit. It is
    caught on the REASON — the clean gate names `PASS 17 < 18`, the mutant cannot — and
    MIN_PASS is separately proved load-bearing by TIGHTENING it, which does move an exit.
    """
    clean = _load_gate()
    lowered = _load_gate(mutate=_mutant(SECTION_27_MIN_PASS=17))
    c_code, c_reason, _ = clean["section_27_gate"](_recs(p=17, w=3))
    m_code, m_reason, _ = lowered["section_27_gate"](_recs(p=17, w=3))
    assert c_code == m_code == 1, "both breach — the exit cannot discriminate here"
    assert "PASS 17 < 18" in c_reason, c_reason
    assert "PASS 17 <" not in m_reason, f"mutant behaves as expected: {m_reason}"
    assert c_reason != m_reason, "CAUGHT: the clean gate names the PASS clause; the mutant drops it"
    # MIN_PASS is genuinely read: tightening it flips a passing run to a breach
    tightened = _load_gate(mutate=_mutant(SECTION_27_MIN_PASS=19))
    assert clean["section_27_gate"](_recs(p=18, w=2))[0] == 0
    assert tightened["section_27_gate"](_recs(p=18, w=2))[0] == 1, \
        "CAUGHT: MIN_PASS is load-bearing, not decorative"


def test_mutant_warn_bound_removed_is_caught():
    """Same changed mechanism as the MIN_PASS mutant, for the same arithmetic reason."""
    clean = _load_gate()
    loosened = _load_gate(mutate=_mutant(SECTION_27_MAX_WARN=99))
    c_code, c_reason, _ = clean["section_27_gate"](_recs(p=11, w=9))
    m_code, m_reason, _ = loosened["section_27_gate"](_recs(p=11, w=9))
    assert c_code == m_code == 1, "both breach on PASS — the exit cannot discriminate"
    assert "WARN 9 > 2" in c_reason, c_reason
    assert "WARN 9 >" not in m_reason, f"mutant behaves as expected: {m_reason}"
    assert c_reason != m_reason, "CAUGHT: the clean gate names the WARN clause; the mutant drops it"
    # MAX_WARN is genuinely read: tightening it flips the exact floor to a breach
    tightened = _load_gate(mutate=_mutant(SECTION_27_MAX_WARN=1))
    assert clean["section_27_gate"](_recs(p=18, w=2))[0] == 0
    assert tightened["section_27_gate"](_recs(p=18, w=2))[0] == 1, \
        "CAUGHT: MAX_WARN is load-bearing, not decorative"


def test_mutant_fail_check_removed_is_caught():
    ns = _load_gate(mutate=_mutant(SECTION_27_MAX_FAIL=99))
    assert ns["section_27_gate"](_recs(p=18, f=2))[0] == 0
    clean = _load_gate()
    assert clean["section_27_gate"](_recs(p=18, f=2))[0] == 2, \
        "CAUGHT: the clean gate sends FAILs to adjudication"


def test_mutant_case_set_check_removed_is_caught():
    """The mutant that matters most — and its CATCH MECHANISM CHANGED on 2026-08-24.

    Under the 838d0e6 shape the discriminator was the EXIT CODE: the clean gate exited 2
    on the wrong 20. Under subset scoring both the clean gate and the mutant exit **0**,
    so the exit code discriminates nothing here. The discriminator is now the VERDICT:
    the mutant reports `scored: true, floor_met: true` — a floor pass over cases that are
    not the § 2.7 set — while the clean gate reports `scored: false, floor_met: null`.
    That is precisely why `floor_met` exists as a three-state key and why the JSON must
    be read on it rather than on `exit_code`.
    """
    wrong_20 = [f"COL_ZH_{i:02d}" for i in range(1, 21)]
    ns = _load_gate(mutate=_mutant(SECTION_27_CASE_IDS=frozenset(wrong_20)))
    m_code, _, m_v = ns["section_27_gate"](_recs(p=18, w=2, ids=wrong_20))
    assert (m_code, m_v["scored"], m_v["floor_met"]) == (0, True, True), \
        "mutant behaves as expected — it scores the wrong 20 cases as a floor PASS"
    clean = _load_gate()
    c_code, c_reason, c_v = clean["section_27_gate"](_recs(p=18, w=2, ids=wrong_20))
    assert (c_v["scored"], c_v["floor_met"]) == (False, None), \
        f"CAUGHT: the clean gate refuses to score the wrong 20 — got {c_code}: {c_reason}"
    assert m_v["floor_met"] != c_v["floor_met"], \
        "the mutant and the clean gate must be distinguishable — on floor_met, not exit code"


def test_mutant_priority_swapped_fail_reports_breach_is_caught():
    """If ranks C and D were swapped, 15/2/3 would report exit 1 (a scored breach)
    instead of exit 2 (needs a person). The distinction is the whole point of rank C."""
    clean = _load_gate()
    code, reason, v = clean["section_27_gate"](_recs(p=15, w=2, f=3))
    assert code == 2, "CAUGHT: FAIL must outrank the floor-breach check"
    assert "FLOOR BREACH" not in reason.upper(), \
        "CAUGHT: a FAIL run must not be reported as a scored breach"
    assert v["floor_met"] is None, "CAUGHT: an unadjudicated run must claim no floor verdict"


def test_mutant_counts_read_from_all_results_is_caught():
    """NEW LEG, and the one the signature change exists for.

    Mutates the SOURCE, not a constant: the count loop iterates every result instead of
    the § 2.7 records — the exact bug a `stats`-taking gate would have had. On a full run
    with 3 COL_* FAILs the mutant sends a clean § 2.7 subset to adjudication (exit 2);
    the clean gate exits 0. The replacement is asserted to have applied, so a refactor
    cannot turn this mutant into a no-op.
    """
    src = RUNNER.read_text(encoding="utf-8")
    mutated = src.replace("    for r in scored_records:\n",
                          "    for r in results:\n", 1)
    assert mutated != src, "the count loop was refactored — this mutant no longer applies"
    full = _recs(p=18, w=2) + _non_s27(110) + _non_s27(3, status="FAIL")
    m_code, _, m_v = _load_gate(source=mutated)["section_27_gate"](full)
    assert m_code == 2 and m_v["counts"]["FAIL"] == 3, \
        "mutant behaves as expected — it counts COL_* FAILs against § 2.7"
    c_code, _, c_v = _load_gate()["section_27_gate"](full)
    assert c_code == 0 and c_v["counts"]["FAIL"] == 0, \
        "CAUGHT: the clean gate derives its counts over the § 2.7 records only"


def test_mutant_not_a_section_27_run_exits_two_is_caught():
    """NEW LEG — the 838d0e6 defect itself, pinned as a mutant so it cannot come back.

    Mutates leg A's return code from 0 to 2. That mutant is the shipped-then-reverted
    behaviour: it makes `--smoke` and the full documented invocation exit 2 and leaves
    `pass_rate < 70` unreachable.
    """
    src = RUNNER.read_text(encoding="utf-8")
    mutated = src.replace('        return 0, reason, {\n            "scored":     False,',
                          '        return 2, reason, {\n            "scored":     False,', 1)
    assert mutated != src, "leg A's return was refactored — this mutant no longer applies"
    smoke = _recs(p=1, ids=["R08"])
    assert _load_gate(source=mutated)["section_27_gate"](smoke)[0] == 2, \
        "mutant behaves as expected — it is the 838d0e6 behaviour"
    assert _load_gate()["section_27_gate"](smoke)[0] == 0, \
        "CAUGHT: a non-§ 2.7 selection must exit 0 and defer to the 70% gate"
