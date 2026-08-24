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

# A "digit-run" pattern: a bare run of N-or-more digits with no surrounding key. This is the
# mis-resolution mechanism. Key-anchored patterns (e.g. r"DailyMed:([0-9a-f-]+)#") are NOT
# digit-runs and are NOT flagged — they identify the entity rather than scraping it, which
# is what CLAUDE.md Rule 21 asks for ("where an exact key exists, use the key, not the text").
_DIGIT_RUN = re.compile(r"(?:\\d|\[0-9\])\{\d+,\d*\}")

_RE_FUNCS = {"search", "match", "fullmatch", "findall", "finditer"}


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


def _tainted_locals(fn: ast.AST) -> set[str]:
    """Local names bound from an expression that mentions source_id — ONE level, no more.

    `sid = getattr(doc, "source_id", "")` then `re.search(pat, sid)` is the shape used by
    both `_pmid` helpers and by `extract_pmid`. This is deliberately not a dataflow
    analysis; one level is what the real code needs, and a deeper one would be untestable.
    """
    tainted: set[str] = set()
    for sub in ast.walk(fn):
        if isinstance(sub, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            value = sub.value
            targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
            if value is not None and _mentions_source_id(value):
                for t in targets:
                    if isinstance(t, ast.Name):
                        tainted.add(t.id)
    return tainted


def _compiled_digit_run_names(tree: ast.Module) -> set[str]:
    """Module-level `X = re.compile(<digit-run literal>)` names.

    Without this, moving the pattern into a module constant would evade the rule. The
    in-test injection below exercises this branch so it is not dead code.
    """
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "compile"):
            continue
        if not (call.args and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)):
            continue
        if _DIGIT_RUN.search(call.args[0].value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def _is_digit_run_scrape(call: ast.Call, compiled: set[str]) -> ast.AST | None:
    """-> the SUBJECT expression if this call scrapes a digit run, else None.

    Two forms: `re.search(r"(\\d{5,})", subject)` and `_RE.search(subject)` where `_RE` is
    a module-level compiled digit-run pattern.
    """
    if not isinstance(call.func, ast.Attribute) or call.func.attr not in _RE_FUNCS:
        return None

    # form 1 — re.<func>(<literal>, <subject>)
    if (isinstance(call.func.value, ast.Name) and call.func.value.id == "re"
            and len(call.args) >= 2
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
            and _DIGIT_RUN.search(call.args[0].value)):
        return call.args[1]

    # form 2 — <COMPILED>.<func>(<subject>)
    if (isinstance(call.func.value, ast.Name) and call.func.value.id in compiled
            and len(call.args) >= 1):
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
    """-> ["file:line  <src>", ...] for every UNGUARDED source_id digit scrape."""
    tree = ast.parse(text)
    compiled = _compiled_digit_run_names(tree)

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
        subject = _is_digit_run_scrape(node, compiled)
        if subject is None:
            continue
        fn = enclosing.get(id(node))
        tainted = _tainted_locals(fn) if fn is not None else set()
        subject_is_source_id = _mentions_source_id(subject) or any(
            isinstance(s, ast.Name) and s.id in tainted for s in ast.walk(subject))
        if not subject_is_source_id:
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
            f"{len(violations)} source_id digit-scrape(s) with no source_type guard in the "
            f"enclosing function:\n" + "\n".join(f"  {v}" for v in violations) +
            "\n\nTHE INVARIANT: digits may be scraped from a source_id ONLY when source_type "
            "is PubMed. A DailyMed source_id yields PMID 84432, a TFDA one yields 057803 — "
            "both real-looking, both wrong.\nFIX: guard inside the function that scrapes, so "
            "callers that IMPORT it cannot inherit the defect."
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


def test_the_rule_ignores_key_anchored_extraction():
    """Rule 21 shape — `source_id.split('#')` and key-anchored regexes are CORRECT.

    Flagging these would be a false positive on the pattern CLAUDE.md Rule 21 asks for.
    """
    src = (
        "import re\n"
        "def loinc(source_id):\n"
        "    if not source_id.startswith('DailyMed:') or '#' not in source_id:\n"
        "        return None\n"
        "    return source_id.split('#', 1)[1].split('~', 1)[0]\n"
    )
    assert _scan_source(src, "injected.py") == []


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
