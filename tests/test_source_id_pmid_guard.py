# -*- coding: utf-8 -*-
"""The source_id digit-scrape invariant — a RULE over the repo, not a list of known sites.

THE INVARIANT: digits may be scraped out of a document's `source_id` ONLY when that
document's `source_type` is PubMed.

WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17): non-PubMed `source_id`s contain 5+ digit
runs and mis-resolve to REAL-BUT-UNRELATED PMIDs. Measured 2026-08-23: a DailyMed
`source_id` yields PMID `84432`, a TFDA one yields `057803`. PMID 84432 exists, so the
harness fetches a genuine 1970s abstract and judges a drug-label claim against it — the
run prints `N/N resolve` and looks clean. A wrong answer that reports itself as right.

WHY A RULE AND NOT A LIST — this is the zh-TW punctuation precedent
(`tests/test_disclaimer_source_parity.py:259`), and it is here for a measured reason.
THREE successive counts of these sites were published and ALL THREE were wrong:
  · report #2 body                  -> 5 guarded / 5 unguarded  (miscounted its own list)
  · the efb39d4 addendum header     -> 4 / 6  (fixed the arithmetic, inherited the
                                       misclassification of direction_shadow_eval.py)
  · derived at HEAD 2026-08-24      -> 7 / 3 BY LITERAL; 16 extraction points, 7/9,
                                       once helper CALL SITES are counted
A list encodes whichever count was believed on the day it was written. A rule cannot be
wrong about its own denominator, and it covers sites added after today.

WHY THE RULE IS FUNCTION-SCOPED, which is the load-bearing design choice: the guard must
live inside the SAME FUNCTION as the scrape. That is what makes an imported scraper safe.
`scripts/direction_shadow_eval.py` guards all three of its own extractions (`:96-97`,
`:142`) and then imports `claim_pairs` from `citation_truth_check` (`:37`), which calls the
UNGUARDED `extract_pmid` internally. That file greps clean and inherits the defect anyway.
A statement-scoped rule would have passed it. A function-scoped rule fixes it at the
source, because the helper itself must check.

KNOWN LIMIT, stated rather than overclaimed: function scope does not prove the guard
DOMINATES the scrape on every path. A function containing both a guard and an unguarded
scrape in a different branch would pass this rule. That is why the behavioural tests below
exist — textual presence of a guard is not proof that it works.

AST, not import: several scanned files call `OpenAI()` / open network clients at module
scope, so importing them would need `OPENAI_API_KEY` and make this suite
environment-dependent. Same technique as `tests/test_golden_gate_contract.py` and
`tests/test_danger_path_exit_codes.py`.
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

from api.models.schemas import CredibilityLevel, RetrievedDocument, SourceType

ROOT = Path(__file__).resolve().parent.parent

# WHAT THE RULE KEYS ON: the SUBJECT, never the pattern.
#
# ⚠️ THIS IS THE 2026-08-24 SECOND-PASS CORRECTION, and the reason is worth keeping. The
# first version of this rule required the pattern to be a recognisable digit-run literal
# (or a module-level `re.compile` of one). It fired on the two shapes in the repo and on a
# module-level compile — and MISSED all of:
#     · re.compile() INSIDE the function
#     · the pattern held in a plain str variable:  _P = r"(\d{5,})" ; re.search(_P, sid)
#     · a compiled pattern IMPORTED from another module
# The middle two are the most natural refactor anyone would apply to these scripts. A rule
# that hard-codes the expected SHAPE is the same defect as the grep that hard-coded the
# guard's shape and produced two wrong reports — just relocated into the rule. Keying on
# the subject removes pattern provenance from the question entirely.
#
# FOUNDER RULING 2026-08-24, recorded as a JUDGMENT a future reader may overturn: a regex
# over a `source_id` is NOT correct even when key-anchored (e.g. r"DailyMed:([0-9a-f-]+)#"),
# so firing on it is CORRECT BEHAVIOUR rather than a false positive. CLAUDE.md Rule 21 says
# use the key, not the text — and every key parse in this repo uses `.split` / `.startswith`
# and ZERO use regex (verified by running this rule at HEAD: zero flags). If a future reader
# has a genuine need for a key-anchored regex over a source_id, this is the line to revisit;
# the reasoning is here rather than in a commit message so the trade-off is visible.
#
# `re.split` IS included for the `re.<func>(pattern, subject)` form (it can extract), but
# `split` is deliberately EXCLUDED from the bound-method form below, because `str.split`
# collides with it and every key parse in the repo is exactly `sid.split("#", 1)`.
_RE_FUNCS_BOUND = {"search", "match", "fullmatch", "findall", "finditer"}
_RE_FUNCS_MODULE = _RE_FUNCS_BOUND | {"split"}


def _tracked_py_files() -> list[Path]:
    """Every tracked .py file. Tracked, because untracked scratch is not the repo."""
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    return [ROOT / line for line in out.stdout.splitlines() if line.strip()]


def _mentions_source_id(node: ast.AST) -> bool:
    """Does this expression reference a source_id, directly?

    Covers `d.source_id`, `getattr(d, "source_id", "")` and `citation.get("source_id")` —
    an Attribute named source_id, or the literal string "source_id" used as a key.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr == "source_id":
            return True
        if isinstance(sub, ast.Name) and sub.id == "source_id":
            return True
        if isinstance(sub, ast.Constant) and sub.value == "source_id":
            return True
    return False


def _refs_tainted(node: ast.AST, tainted: set[str]) -> bool:
    return any(isinstance(s, ast.Name) and s.id in tainted for s in ast.walk(node))


def _tainted_locals(fn: ast.AST) -> set[str]:
    """Local names carrying a source_id value, to a FIXPOINT.

    `sid = getattr(doc, "source_id", "")` then `re.search(pat, sid)` is the shape used by
    all three helpers. The fixpoint loop (rather than the single pass this had until
    2026-08-24) is what makes `sid2 = sid` — trivial to write, invisible to one level —
    still count as tainted.

    Still NOT a dataflow analysis: it does not follow taint across function boundaries,
    through containers, or through attribute assignment. Those are real gaps; they are
    named here rather than implied to be covered.
    """
    tainted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for sub in ast.walk(fn):
            if not isinstance(sub, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                continue
            value = sub.value
            if value is None:
                continue
            targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
            if _mentions_source_id(value) or _refs_tainted(value, tainted):
                for t in targets:
                    if isinstance(t, ast.Name) and t.id not in tainted:
                        tainted.add(t.id)
                        changed = True
    return tainted


def _regex_subject(call: ast.Call) -> ast.AST | None:
    """-> the SUBJECT expression of a regex operation, else None. Pattern provenance is
    deliberately NOT considered — see the ruling recorded at the top of this file.

    Two forms:
      `re.<func>(pattern, subject)`  -> subject is arg 1   (module form; includes `split`)
      `<anything>.<func>(subject)`   -> subject is arg 0   (bound form; excludes `split`,
                                        because `str.split` collides and every key parse in
                                        this repo is exactly `sid.split("#", 1)`)
    """
    if not isinstance(call.func, ast.Attribute):
        return None
    func = call.func

    if isinstance(func.value, ast.Name) and func.value.id == "re":
        if func.attr in _RE_FUNCS_MODULE and len(call.args) >= 2:
            return call.args[1]
        return None

    if func.attr in _RE_FUNCS_BOUND and len(call.args) >= 1:
        return call.args[0]
    return None


def _has_source_type_guard(fn: ast.AST) -> bool:
    """Does this function check source_type against PubMed, in EITHER supported shape?

    Shape A (preceding-line, the one an earlier same-line grep was blind to):
        if getattr(d, "source_type", None) != SourceType.PUBMED:
            continue
    Shape B (inline comprehension filter):
        [... for d in docs if getattr(d, "source_type", None) == SourceType.PUBMED ...]

    Both are just Compare nodes somewhere in the function body, so one walk covers both.
    A rule that recognised only one shape would reproduce the exact blind spot that
    produced two wrong reports.
    """
    for sub in ast.walk(fn):
        if not isinstance(sub, ast.Compare):
            continue
        if not _mentions_source_type(sub.left):
            continue
        for comp in sub.comparators:
            if _is_pubmed(comp):
                return True
    return False


def _mentions_source_type(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr == "source_type":
            return True
        if isinstance(sub, ast.Name) and sub.id == "source_type":
            return True
        if isinstance(sub, ast.Constant) and sub.value == "source_type":
            return True
    return False


def _is_pubmed(node: ast.AST) -> bool:
    """`SourceType.PUBMED` or the bare string "pubmed" (SourceType is a str Enum)."""
    if isinstance(node, ast.Attribute) and node.attr == "PUBMED":
        return True
    if isinstance(node, ast.Constant) and node.value == "pubmed":
        return True
    return False


def _scan_source(text: str, label: str) -> list[str]:
    """-> ["file:line  <src>", ...] for every UNGUARDED regex operation over a source_id."""
    tree = ast.parse(text)

    # innermost enclosing function for every node
    enclosing: dict[int, ast.AST] = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(fn):
                enclosing[id(sub)] = fn

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        subject = _regex_subject(node)
        if subject is None:
            continue
        fn = enclosing.get(id(node))
        tainted = _tainted_locals(fn) if fn is not None else set()
        if not (_mentions_source_id(subject) or _refs_tainted(subject, tainted)):
            continue
        if fn is None:
            violations.append(f"{label}:{node.lineno}  (module level — no enclosing function)")
        elif not _has_source_type_guard(fn):
            violations.append(f"{label}:{node.lineno}  in {fn.name}()")
    return violations


# --------------------------------------------------------------------------
# THE RULE
# --------------------------------------------------------------------------

def test_every_source_id_digit_scrape_is_source_type_guarded():
    """EVERY site in the repo, including ones added after this was written."""
    violations: list[str] = []
    for path in _tracked_py_files():
        if path.resolve() == Path(__file__).resolve():
            continue  # this file's own injection fixtures are strings, but be explicit
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            violations += _scan_source(text, path.relative_to(ROOT).as_posix())
        except SyntaxError:
            continue

    if violations:
        pytest.fail(
            f"{len(violations)} regex operation(s) over a source_id with no source_type "
            f"guard in the enclosing function:\n" + "\n".join(f"  {v}" for v in violations) +
            "\n\nTHE INVARIANT: a source_id may be read by regex ONLY when source_type is "
            "PubMed. A DailyMed source_id yields PMID 84432, a TFDA one yields 057803 — "
            "both real-looking, both wrong.\nFIX: guard inside the function that scrapes, so "
            "callers that IMPORT it cannot inherit the defect.\nIf you are parsing a KEY out "
            "of a source_id, use `.split` / `.startswith` (CLAUDE.md Rule 21) — every key "
            "parse in this repo already does, and none uses regex."
        )


def test_the_rule_has_no_false_positives_on_unrelated_digit_patterns():
    """The 8 unrelated \\d{N,} sites at HEAD must not trip the rule.

    False positives train people to ignore a test — the reason `.` and `:` are excluded
    from the zh-TW punctuation guard. Each of these is a real digit-run pattern that has
    nothing to do with source_id; all are single-argument `re.compile` with no subject.
    """
    unrelated = [
        "api/middleware/phi_handler.py",      # MRN / national-id PHI redaction (7 patterns)
        "scripts/build_dailymed_label_corpus.py",  # _DEVCODE_RE title-prefix stripper
        "tests/probes/baton_check/check_baton.py",  # FIGURE
        "tests/run_golden_tests.py",          # _CITE_MARKER_RE
    ]
    for rel in unrelated:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert _scan_source(text, rel) == [], (
            f"{rel} tripped the source_id rule — it contains digit-run patterns that have "
            f"nothing to do with source_id. A false positive here makes the rule ignorable."
        )


def test_the_rule_fires_on_an_unguarded_scrape():
    """A rule that cannot fail is dead weight. Inject a violation, prove it is caught."""
    src = (
        "import re\n"
        "def harvest(doc):\n"
        "    return re.search(r'(\\d{5,})', doc.source_id or '')\n"
    )
    found = _scan_source(src, "injected.py")
    assert len(found) == 1, found
    assert "injected.py:3" in found[0] and "harvest()" in found[0]


def test_the_rule_fires_on_a_precompiled_pattern():
    """Moving the pattern into a module constant must not evade the rule."""
    src = (
        "import re\n"
        "_ID = re.compile(r'(\\d{5,})')\n"
        "def harvest(doc):\n"
        "    return _ID.search(doc.source_id or '')\n"
    )
    found = _scan_source(src, "injected.py")
    assert len(found) == 1, found
    assert "injected.py:4" in found[0]


def test_the_rule_accepts_the_preceding_line_continue_shape():
    """Shape A. This is the form an earlier same-line grep was blind to, twice."""
    src = (
        "import re\n"
        "from api.models.schemas import SourceType\n"
        "def harvest(docs):\n"
        "    for d in docs:\n"
        "        if getattr(d, 'source_type', None) != SourceType.PUBMED:\n"
        "            continue\n"
        "        yield re.search(r'(\\d{5,})', getattr(d, 'source_id', '') or '')\n"
    )
    assert _scan_source(src, "injected.py") == []


def test_the_rule_accepts_the_inline_comprehension_shape():
    """Shape B."""
    src = (
        "import re\n"
        "from api.models.schemas import SourceType\n"
        "def harvest(docs):\n"
        "    return [re.search(r'(\\d{5,})', d.source_id or '') for d in docs\n"
        "            if getattr(d, 'source_type', None) == SourceType.PUBMED]\n"
    )
    assert _scan_source(src, "injected.py") == []


def test_the_rule_is_silent_on_split_and_startswith_key_parsing():
    """Rule 21's shape — `.startswith` + `.split` — is CORRECT and must stay silent.

    This is the real shape of every key parse in the repo: retriever.py:58-61,
    dailymed_danger_path_verify.py:130-133, canary_gate.py:293-305, owner_assertion.py,
    seat_v2.py. Flagging it would make the rule ignorable, which is the zh-TW precedent's
    stated reason for excluding ambiguous cases.
    """
    src = (
        "def loinc(source_id):\n"
        "    if not source_id.startswith('DailyMed:') or '#' not in source_id:\n"
        "        return None\n"
        "    return source_id.split('#', 1)[1].split('~', 1)[0]\n"
    )
    assert _scan_source(src, "injected.py") == []


def test_the_rule_fires_on_a_key_anchored_regex_which_is_a_judgment_not_a_bug():
    """⚖️ FOUNDER RULING 2026-08-24 — a JUDGMENT a future reader may overturn.

    A key-anchored regex over a source_id — r"DailyMed:([0-9a-f-]+)#" — FIRES, and that is
    intended. It is not a false positive:
      · CLAUDE.md Rule 21 says use the KEY, not the text. A regex is the text shape.
      · EVERY key parse in this repo uses `.split` / `.startswith`; ZERO use regex. Verified
        by running this rule over all 157 tracked .py files at HEAD: ZERO flags. So this
        ruling costs nothing today — it is a fence, not a migration.
      · Keying on the SUBJECT rather than the pattern is what closed the four evasions the
        pattern-provenance version missed (function-scope compile, pattern-in-a-variable,
        imported compiled pattern, two-level taint). Re-admitting pattern inspection to
        exempt key-anchored regexes would reopen all four.

    TO OVERTURN: if a genuine need for a key-anchored regex over a source_id appears, the
    honest change is to guard THAT function with a source_type check anyway, or to narrow
    `_regex_subject`. Do not silently special-case a pattern shape — that is precisely the
    hard-coded-shape defect this rule was rewritten to remove.
    """
    src = (
        "import re\n"
        "def setid(source_id):\n"
        "    return re.search(r'DailyMed:([0-9a-f-]+)#', source_id)\n"
    )
    found = _scan_source(src, "injected.py")
    assert len(found) == 1 and "injected.py:3" in found[0], found


# --------------------------------------------------------------------------
# THE FOUR EVASIONS the pattern-provenance version missed (2026-08-24 second pass).
# Each of these silently passed the first rule. B and C are the most natural refactor
# anyone would apply to these scripts, which is why the rule stopped inspecting patterns.
# --------------------------------------------------------------------------

def test_evasion_b_compile_inside_the_function():
    src = ("import re\n"
           "def f(d):\n"
           "    p = re.compile(r'(\\d{5,})')\n"
           "    return p.search(getattr(d, 'source_id', '') or '')\n")
    assert len(_scan_source(src, "x.py")) == 1, _scan_source(src, "x.py")


def test_evasion_c_pattern_held_in_a_plain_string_variable():
    src = ("import re\n"
           "_P = r'(\\d{5,})'\n"
           "def f(d):\n"
           "    return re.search(_P, getattr(d, 'source_id', '') or '')\n")
    assert len(_scan_source(src, "x.py")) == 1, _scan_source(src, "x.py")


def test_evasion_d_compiled_pattern_imported_from_another_module():
    src = ("from othermod import _P\n"
           "def f(d):\n"
           "    return _P.search(getattr(d, 'source_id', '') or '')\n")
    assert len(_scan_source(src, "x.py")) == 1, _scan_source(src, "x.py")


def test_evasion_e_two_level_taint():
    """`sid2 = sid` — trivial to write, invisible to a single-pass taint. Needs the fixpoint."""
    src = ("import re\n"
           "def f(d):\n"
           "    sid = getattr(d, 'source_id', '') or ''\n"
           "    sid2 = sid\n"
           "    return re.search(r'(\\d{5,})', sid2)\n")
    assert len(_scan_source(src, "x.py")) == 1, _scan_source(src, "x.py")


def test_re_split_over_a_source_id_also_fires():
    """`re.split` can extract too; `str.split` (the Rule 21 shape) must not be confused with it."""
    src = ("import re\n"
           "def f(d):\n"
           "    return re.split(r'(\\d{5,})', d.source_id or '')\n")
    assert len(_scan_source(src, "x.py")) == 1, _scan_source(src, "x.py")


# --------------------------------------------------------------------------
# BEHAVIOURAL — textual presence of a guard is not proof that it works.
# --------------------------------------------------------------------------

def _doc(source_type: SourceType, source_id: str) -> RetrievedDocument:
    return RetrievedDocument(
        content="Body text long enough to be a real abstract for the purposes of this test.",
        source_type=source_type,
        source_id=source_id,
        title="t",
        url="u",
        credibility=CredibilityLevel.OFFICIAL,
    )


# Real shapes, not invented ones:
#   DailyMed  — scripts/build_dailymed_label_corpus.py:288  f"DailyMed:{setid}#{loinc}~{i}"
#   TFDA      — scripts/build_tfda_indication_corpus.py:124 source_id = the 許可證字號
#   PubMed    — api/data_sources/pubmed.py:37               f"PMID:{pmid}"
_DAILYMED = _doc(SourceType.DAILYMED, "DailyMed:a1b2c3d4-5678-90ab-cdef-1234567890ab#34073-7~0")
_TFDA = _doc(SourceType.TFDA, "057803")
_PUBMED = _doc(SourceType.PUBMED, "PMID:29421936")


def test_direction_checker_excludes_dailymed_and_tfda():
    from api.services.direction_checker import cited_sources_from_documents
    out = cited_sources_from_documents([_DAILYMED, _TFDA, _PUBMED])
    pmids = [s.pmid for s in out]
    assert pmids == ["29421936"], (
        f"expected only the PubMed doc; got {pmids}. A DailyMed setid scrapes to a "
        f"real-but-unrelated PMID (measured: 84432), a TFDA licence number to 057803."
    )


def test_retrieval_refusal_excludes_dailymed_and_tfda():
    from api.services.retrieval_refusal import pool_sources_from_documents
    out = pool_sources_from_documents([_DAILYMED, _TFDA, _PUBMED])
    assert [p for p, _ in out] == ["29421936"], out


def test_a_pubmed_doc_with_no_extractable_id_is_not_silently_counted():
    """NOT-APPLICABLE (non-PubMed) and FAILED (PubMed, no id) are different.

    Excluding a non-PubMed doc is correct. Excluding a PubMed doc whose id will not parse
    is a real extraction failure that must not vanish into a shrinking denominator.
    """
    from api.services.direction_checker import cited_sources_from_documents
    broken = _doc(SourceType.PUBMED, "PMID:")          # PubMed, no digits
    out = cited_sources_from_documents([broken, _PUBMED])
    assert [s.pmid for s in out] == ["29421936"], out
