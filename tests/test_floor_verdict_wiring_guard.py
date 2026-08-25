"""NAMED REGRESSION GUARDS for the `computed → printed → never returned` gate class.

The class (fourth occurrence closed by the 2026-08-25 defect-2 fix, TECH_DEBT entry):
a verdict computed and printed inside `tests/run_golden_tests.py` that reaches neither
the process exit code nor the result-JSON artifact — so a failing run prints ❌ and
still exits 0. The pattern sentence from that entry: A GATE THAT COMPUTES A VERDICT
MUST RETURN IT.

Two guard shapes, per the 2026-08-25 recon's item F:

Shape 1 (per-floor, DATAFLOW-keyed): for each floor call in `run_tests()`, the tuple
target that receives the verdict must appear as a VALUE in the dict literal passed to
`json.dump`, and the tuple target that receives the exit code must reach a
`sys.exit(...)` call. The three names are READ OFF the assignment — renaming the
variables cannot silently disarm the guard; renaming or removing a floor function
fails the applicability asserts LOUDLY (the mutated-!=-src idiom of
`test_golden_gate_contract.py`).

Shape 2 (the CLASS guard): verdict-producing calls are DETECTED structurally — every
3-name tuple-unpack of a module-level function call inside `run_tests()` — and each
one must satisfy Shape 1's wiring. A floor added later is checked automatically; a
refactor that breaks the detection anchors fails the applicability asserts rather
than passing silently.

Scope, stated honestly: the guard enforces "floor logic lives in a pure function
whose (code, reason, verdict) is unpacked in run_tests, and every such verdict is
wired to exit + artifact". It cannot see a NEW inline verdict that never became a
function — that is what review and the TECH_DEBT pattern note are for. What it
guarantees is that the floors that exist cannot regress to print-only under any
variable renaming.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tests" / "run_golden_tests.py"

# The floors known today. Shape 2 asserts these are both DETECTED (applicability) but
# checks the wiring of EVERYTHING detected, so a properly wired third floor passes
# without editing this file, and a renamed floor fails here loudly.
KNOWN_FLOORS = {"research_golden_floor", "explain_floor"}


def _src():
    return RUNNER.read_text(encoding="utf-8")


def _run_tests_fn(tree):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run_tests":
            return node
    raise AssertionError("run_tests not found in the runner — update this guard")


def _floor_calls(fn, module_fn_names):
    """Every `a, b, c = some_module_level_fn(...)` inside run_tests."""
    calls = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Tuple)
                and len(node.targets[0].elts) == 3
                and all(isinstance(e, ast.Name) for e in node.targets[0].elts)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in module_fn_names):
            calls.append((node.value.func.id,
                          [e.id for e in node.targets[0].elts]))
    return calls


def _dump_dict(fn):
    dumps = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "dump" and isinstance(n.func.value, ast.Name)
             and n.func.value.id == "json"]
    assert len(dumps) == 1, \
        f"expected exactly one json.dump in run_tests, found {len(dumps)} — update this guard"
    d = dumps[0].args[0]
    assert isinstance(d, ast.Dict), \
        "json.dump's first argument is no longer a dict literal — update this guard"
    return d


def _exit_arg_names(fn):
    out = set()
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "exit" and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "sys" and len(n.args) == 1
                and isinstance(n.args[0], ast.Name)):
            out.add(n.args[0].id)
    return out


def _wiring(source: str):
    """Returns (floor_calls, violations). A violation is one floor whose verdict or
    exit code does not reach where it must."""
    tree = ast.parse(source)
    module_fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    fn = _run_tests_fn(tree)
    calls = _floor_calls(fn, module_fns)
    d = _dump_dict(fn)
    dict_value_names = {v.id for v in d.values if isinstance(v, ast.Name)}
    exit_names = _exit_arg_names(fn)
    violations = []
    for fname, (code_n, _reason_n, verdict_n) in calls:
        if verdict_n not in dict_value_names:
            violations.append(f"{fname}: verdict `{verdict_n}` never enters the json.dump payload")
        if code_n not in exit_names:
            violations.append(f"{fname}: exit code `{code_n}` never reaches sys.exit")
    return calls, violations


def _artifact_key_for(source: str, floor_name: str):
    """The JSON key under which `floor_name`'s verdict is stored — found by DATAFLOW
    (the dict value that is the Name bound by the floor's tuple-unpack)."""
    tree = ast.parse(source)
    module_fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    fn = _run_tests_fn(tree)
    calls = dict((f, names) for f, names in _floor_calls(fn, module_fns))
    assert floor_name in calls, \
        f"{floor_name} is not called (3-tuple-unpacked) in run_tests — update this guard"
    verdict_n = calls[floor_name][2]
    d = _dump_dict(fn)
    for k, v in zip(d.keys, d.values):
        if isinstance(v, ast.Name) and v.id == verdict_n and isinstance(k, ast.Constant):
            return k.value, calls[floor_name]
    raise AssertionError(
        f"{floor_name}: verdict `{verdict_n}` not found among json.dump's dict values")


def _conditional_exit_stmt(source: str, code_name: str):
    """The single top-level statement of run_tests that both mentions `code_name` and
    contains a sys.exit — it must be an `if` (an unconditional exit would make the
    later gates dead code, the 838d0e6 defect)."""
    tree = ast.parse(source)
    fn = _run_tests_fn(tree)
    hits = [st for st in fn.body
            if code_name in ast.unparse(st) and "sys.exit" in ast.unparse(st)]
    assert len(hits) == 1, \
        f"expected exactly one exit statement over `{code_name}`, found {len(hits)}"
    return hits[0]


# ─────────────────────── Shape 1 — per-floor, dataflow-keyed ───────────────────────

def test_research_golden_floor_verdict_reaches_artifact_and_exit():
    src = _src()
    key, (code_n, _r, verdict_n) = _artifact_key_for(src, "research_golden_floor")
    assert key == "research_golden_floor", \
        f"the artifact key is a public contract; got {key!r}"
    _, violations = _wiring(src)
    assert not [v for v in violations if v.startswith("research_golden_floor")], violations
    stmt = _conditional_exit_stmt(src, code_n)
    assert isinstance(stmt, ast.If), \
        "the research floor's exit must be CONDITIONAL — an unconditional sys.exit " \
        "makes the later gates dead code (the 838d0e6 defect)"


def test_explain_floor_verdict_reaches_artifact_and_exit():
    """THE NAMED GUARD the defect-2 fix owes: the Explain verdict now reaches both the
    result JSON and the composed exit, keyed on dataflow rather than variable names —
    renaming `_ef_*` in a refactor cannot disarm this."""
    src = _src()
    key, (code_n, _r, verdict_n) = _artifact_key_for(src, "explain_floor")
    assert key == "explain_floor", f"the artifact key is a public contract; got {key!r}"
    _, violations = _wiring(src)
    assert not [v for v in violations if v.startswith("explain_floor")], violations
    stmt = _conditional_exit_stmt(src, code_n)
    assert isinstance(stmt, ast.If), \
        "the explain floor's exit must be CONDITIONAL — report-only demotion means a " \
        "clean-binding run must fall through to the 70% gate"


# ─────────────────────── Shape 2 — the class guard ───────────────────────

def test_no_print_only_verdicts_in_the_runner():
    """THE CLASS, closed and kept closed: every verdict-producing call detected in
    run_tests is wired to BOTH the artifact and the exit path. Fourth occurrence
    (`acceptance_pass`) is also pinned dead by name below — comments may cite it as
    history, but no Name node may bind it again."""
    src = _src()
    calls, violations = _wiring(src)
    found = {f for f, _ in calls}
    assert KNOWN_FLOORS <= found, \
        f"floors missing from detection: {KNOWN_FLOORS - found} — a rename must update " \
        f"this guard DELIBERATELY, not disarm it"
    assert not violations, "print-only verdict(s) found:\n  " + "\n  ".join(violations)
    tree = ast.parse(src)
    revived = [n for n in ast.walk(tree)
               if isinstance(n, ast.Name) and n.id == "acceptance_pass"]
    assert not revived, \
        "`acceptance_pass` is the retired print-only verdict (defect-2 TECH_DEBT " \
        "entry); it must not come back as a binding"


# ─────────────────────── fires-proofs (Rule 17: a guard that has not been ───────────
# ─────────────────────── observed failing has not been observed) ────────────────────

def test_guard_fires_when_verdict_dropped_from_artifact():
    src = _src()
    mutated = src.replace('            "explain_floor": _ef_verdict,\n', "", 1)
    assert mutated != src, "the artifact line moved — this fires-proof no longer applies"
    _, violations = _wiring(mutated)
    assert any("explain_floor" in v and "json.dump" in v for v in violations), \
        f"the guard failed to fire on a dropped artifact verdict: {violations}"


def test_guard_fires_when_exit_dropped():
    src = _src()
    mutated = src.replace("        sys.exit(_ef_code)\n",
                          "        pass  # MUTANT: exit deleted\n", 1)
    assert mutated != src, "the exit line moved — this fires-proof no longer applies"
    _, violations = _wiring(mutated)
    assert any("explain_floor" in v and "sys.exit" in v for v in violations), \
        f"the guard failed to fire on a dropped exit: {violations}"
