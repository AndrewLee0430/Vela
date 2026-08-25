"""The Explain acceptance floor's exit contract (PRD § 2.7) — DB-free, network-free,
zero LLM calls.

Created 2026-08-25 with the defect-2 fix. The floor was previously an inline block in
`run_tests()` whose `acceptance_pass` verdict was computed, printed, and DISCARDED —
the fourth `computed → printed → never returned` gate in this repo, and the last (the
defect-2 TECH_DEBT entry). It is now the pure `explain_floor()`, and this file proves
every path reachable via constructed fixtures without running the suite (CLAUDE.md
Rule 17) — the same discipline as `tests/test_golden_gate_contract.py`, whose AST
loader this file mirrors (the runner's module scope instantiates `OpenAI()`, so the
module must never be imported here).

Authority, per the 2026-08-25 founder rulings (TECH_DEBT defect-2 entry):
  BINDING      no_fabricated_citations — founder ruling 2026-08-25 (NOT PRD § 2.7:
               the recon found no § 2.7 requirement line for fabrication).
  REPORT-ONLY  explain_rate vs EXPLAIN_THRESHOLD (95.0) — demoted 2026-08-25.
  REPORT-ONLY  citation_source_types_valid — demoted, supplemental ruling 2026-08-25.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tests" / "run_golden_tests.py"

_WANTED_FUNCS = {"explain_floor"}
_WANTED_CONSTS = {
    "EXPLAIN_THRESHOLD",
    "BINDING_EXPLAIN_DIMENSIONS",
    "REPORT_ONLY_EXPLAIN_DIMENSIONS",
}


def _load_floor(mutate=None, source: str | None = None):
    """Exec ONLY the floor function and its constants — never the module.

    Same loader shape as `test_golden_gate_contract._load_gate`, same loud
    preconditions: a rename of the function or a constant fails HERE, not silently.
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
    assert _WANTED_FUNCS <= names, f"floor function missing from the runner: {_WANTED_FUNCS - names}"
    ns: dict = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), origin, "exec"), ns)
    for c in _WANTED_CONSTS:
        assert c in ns, f"constant missing from the runner: {c}"
    if mutate:
        mutate(ns)
    return ns


def _dims(fabricated="pass", source_types="pass"):
    """A judge-dimension dict holding exactly the two floor-relevant dimensions."""
    return {"no_fabricated_citations": fabricated,
            "citation_source_types_valid": source_types}


def _case(cid, status="PASS", dims=None, skipped=False, category="explain"):
    """One per-case record shaped like the runner's `results.append` sites: `id`,
    `category`, `status`, and judge output under `eval.explain_judge_dimensions`."""
    rec = {"id": cid, "category": category, "status": status, "eval": {}}
    if dims is not None:
        rec["eval"]["explain_judge_dimensions"] = dims
    if skipped:
        rec["eval"]["explain_judge_skipped"] = True
    return rec


def _explain_run(n=20, n_pass=None, dims=None):
    """`n` explain cases, the first `n_pass` with status PASS, all carrying `dims`."""
    n_pass = n if n_pass is None else n_pass
    dims = _dims() if dims is None else dims
    return [_case(f"E{i:02d}", status="PASS" if i <= n_pass else "FAIL", dims=dims)
            for i in range(1, n + 1)]


# ─────────────────────── constants are the ruled values ───────────────────────

def test_constants_are_the_ruled_values():
    """The 2026-08-25 rulings, pinned. Changing any of these is a NEW founder ruling,
    not a refactor — same stance as the golden floor's 18/2/0 pin."""
    ns = _load_floor()
    assert ns["EXPLAIN_THRESHOLD"] == 95.0, \
        "EXPLAIN_THRESHOLD is REPORT-ONLY at 95.0 (demoted, founder ruling 2026-08-25)"
    assert ns["BINDING_EXPLAIN_DIMENSIONS"] == ["no_fabricated_citations"], \
        "the ONLY binding dimension is no_fabricated_citations (founder ruling 2026-08-25)"
    assert ns["REPORT_ONLY_EXPLAIN_DIMENSIONS"] == ["citation_source_types_valid"], \
        "citation_source_types_valid is report-only (supplemental ruling 2026-08-25)"


# ─────────────────────── path (a): clean pass ───────────────────────

def test_clean_pass_exits_zero():
    ns = _load_floor()
    code, reason, v = ns["explain_floor"](_explain_run())
    assert code == 0, f"a clean run must contribute exit 0; got {code} — {reason}"
    assert v["scored"] is True and v["floor_met"] is True
    assert v["binding_breaches"] == [] and v["report_only_failures"] == []
    assert v["threshold_met"] is True and v["explain_rate"] == 100.0
    assert v["judged_cases"] == 20
    assert v["reason"] == reason and v["exit_code"] == code, \
        "verdict must carry the same reason and code that were returned"
    for key in ("scored", "floor_met", "explain_pass", "explain_total", "explain_rate",
                "threshold", "threshold_met", "binding_breaches",
                "report_only_failures", "floor"):
        assert key in v, f"verdict missing {key}"


# ─────────────────────── path (b): BINDING breach → exit 1 ───────────────────────

def test_binding_breach_exits_one_and_reason_names_everything():
    """The ⑥ precedent: the reason text is proven load-bearing, not decorative —
    it must name the floor, the dimension, and the breaching case ids."""
    ns = _load_floor()
    recs = _explain_run(n=20)
    recs[4] = _case("E05", dims=_dims(fabricated="fail"))
    code, reason, v = ns["explain_floor"](recs)
    assert code == 1, f"a binding breach must exit 1; got {code} — {reason}"
    assert v["floor_met"] is False and v["scored"] is True
    assert v["binding_breaches"] == [
        {"case_id": "E05", "dimension": "no_fabricated_citations", "result": "fail"}]
    assert "EXPLAIN ACCEPTANCE FLOOR" in reason, "reason must name the floor"
    assert "no_fabricated_citations" in reason, "reason must name the dimension"
    assert "E05" in reason, "reason must name the breaching case id"
    assert "founder ruling 2026-08-25" in reason, \
        "the binding authority is the founder ruling, NOT PRD § 2.7 — the label must say so"


def test_missing_binding_dimension_on_a_judged_case_is_a_breach():
    """A judged case whose dims dict LACKS the binding dimension reads as 'missing',
    which is not 'pass' — silence must not be scored as clearance."""
    ns = _load_floor()
    recs = _explain_run(n=3)
    recs[0] = _case("E01", dims={"citation_source_types_valid": "pass"})
    code, _, v = ns["explain_floor"](recs)
    assert code == 1
    assert v["binding_breaches"][0]["result"] == "missing"


# ─────────────────────── path (c): threshold breach ALONE → exit 0 ───────────────────────

def test_threshold_breach_alone_exits_zero_and_is_reported():
    """THE DEMOTION, proven: a run failing the 95% rate on clean dimensions exits 0,
    and the rate is still fully present in the verdict for the JSON artifact.
    (Before 2026-08-25 this printed ❌ and exited 0 with NOTHING in the JSON; the fix
    keeps exit 0 — per the demotion ruling — and repairs the artifact half.)"""
    ns = _load_floor()
    code, reason, v = ns["explain_floor"](_explain_run(n=10, n_pass=5))
    assert code == 0, f"the rate is REPORT-ONLY and must not gate; got {code} — {reason}"
    assert v["floor_met"] is True, "floor_met reflects the BINDING dimension only"
    assert v["threshold_met"] is False and v["explain_rate"] == 50.0
    assert v["explain_pass"] == 5 and v["explain_total"] == 10
    assert v["threshold"] == 95.0


# ─────────────────────── path (d): source-types breach ALONE → exit 0 ───────────────────────

def test_source_types_breach_alone_exits_zero_and_is_reported():
    """citation_source_types_valid is report-only (supplemental ruling 2026-08-25):
    recorded in the verdict, never in the exit code."""
    ns = _load_floor()
    recs = _explain_run(n=20)
    recs[0] = _case("E01", dims=_dims(source_types="fail"))
    code, reason, v = ns["explain_floor"](recs)
    assert code == 0, f"a report-only failure must not gate; got {code} — {reason}"
    assert v["floor_met"] is True
    assert v["report_only_failures"] == [
        {"case_id": "E01", "dimension": "citation_source_types_valid", "result": "fail"}]


def test_binding_breach_wins_when_both_kinds_fail():
    """Report-only values must not change the code in EITHER direction: with a binding
    breach AND a threshold breach AND a source-types failure, the exit is exactly 1."""
    ns = _load_floor()
    recs = _explain_run(n=10, n_pass=4, dims=_dims(source_types="fail"))
    recs[0] = _case("E01", status="FAIL", dims=_dims(fabricated="fail", source_types="fail"))
    code, _, v = ns["explain_floor"](recs)
    assert code == 1 and v["floor_met"] is False
    assert v["threshold_met"] is False and v["report_only_failures"]


# ─────────────────────── path (e): not scored ───────────────────────

def test_not_scored_when_no_explain_cases():
    """Mirror of the golden floor's leg A: no explain cases → fall through, exit 0,
    and NOTHING in the verdict may read as a pass."""
    ns = _load_floor()
    research_only = [{"id": f"R{i:02d}", "category": "research", "status": "PASS"}
                     for i in range(1, 21)]
    for recs in ([], research_only):
        code, reason, v = ns["explain_floor"](recs)
        assert code == 0
        assert v["scored"] is False and v["floor_met"] is None
        assert "NOT SCORED" in reason.upper()
        assert v["binding_breaches"] == [] and v["judged_cases"] == 0


def test_skipped_or_absent_judge_cases_are_excluded():
    """Unchanged from the inline block's behavior: a case whose judge was skipped or
    absent is excluded from dimension checks — even if it carries failing dims."""
    ns = _load_floor()
    recs = [
        _case("E01", dims=_dims()),
        _case("E02", dims=_dims(fabricated="fail"), skipped=True),
        _case("E03", dims=None),
    ]
    code, _, v = ns["explain_floor"](recs)
    assert code == 0, "a skipped judge run must not produce a binding breach"
    assert v["judged_cases"] == 1
    assert v["binding_breaches"] == []


# ─────────────────────── reachability + mutation ───────────────────────

def test_every_exit_code_reachable_without_running_the_suite():
    """The floor's whole contract is {0, 1} — both reachable from fixtures alone."""
    ns = _load_floor()
    clean = ns["explain_floor"](_explain_run())[0]
    breach = ns["explain_floor"]([_case("E01", dims=_dims(fabricated="fail"))])[0]
    assert {clean, breach} == {0, 1}, f"not every code reachable: {{{clean}, {breach}}}"


def test_mutant_binding_demoted_to_report_only_is_caught():
    """Delete the binding wiring (code = 1 → code = 0) and the breach run exits 0 —
    the exact defect-2 shape, resurrected. The clean floor catches it with exit 1.
    Both replaces assert applicability (the :436/:441 idiom of the golden contract),
    so a refactor cannot silently turn this mutant into a no-op."""
    src = RUNNER.read_text(encoding="utf-8")
    mutated = src.replace("    code = 1 if binding_breaches else 0\n",
                          "    code = 0  # MUTANT: binding wiring deleted\n", 1)
    assert mutated != src, "the binding wiring was refactored — this mutant no longer applies"
    breach_run = [_case("E01", dims=_dims(fabricated="fail"))]
    m_code, _, m_v = _load_floor(source=mutated)["explain_floor"](breach_run)
    assert m_code == 0, "mutant behaves as expected — it computes the breach and discards it"
    assert m_v["binding_breaches"], "the mutant still SEES the breach; it just stops returning it"
    c_code, c_reason, _ = _load_floor()["explain_floor"](breach_run)
    assert c_code == 1, f"CAUGHT: the clean floor returns the verdict it computes — {c_reason}"


def test_loader_raises_when_its_preconditions_are_unmet():
    """Positive+negative control for the loader itself, mirroring the golden
    contract's loader-strictness test: a source genuinely lacking the floor or a
    constant must raise, and the real source must load cleanly."""
    src = RUNNER.read_text(encoding="utf-8")
    no_func = src.replace("def explain_floor(", "def explain_floor_RENAMED(", 1)
    assert no_func != src, "the floor was renamed — this mutation no longer removes it"
    with pytest.raises(AssertionError, match="floor function missing"):
        _load_floor(source=no_func)
    no_const = src.replace("BINDING_EXPLAIN_DIMENSIONS = ", "BINDING_EXPLAIN_DIMENSIONS_RENAMED = ", 1)
    assert no_const != src, "the constant was renamed — this mutation no longer removes it"
    with pytest.raises(AssertionError, match="constant missing"):
        _load_floor(source=no_const)
    assert callable(_load_floor(source=src)["explain_floor"])
