# tests/test_verify_write_ordering.py
"""Verify write-ordering guard — the persisted answer must be the MUTATED summary.

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
In POST /api/verify, `summary` is mutated twice after analysis — the spelling-
correction note ("Note: …. Please verify.") and the TFDA grounding prefix
("TFDA grounding — …"). From the initial wiring until 2026-08-19 the
`_safe_db_write(... answer=summary ...)` ran BEFORE those mutations, so
`chat_history.answer` stored the un-corrected, un-grounded text. That row is
what `/history` renders and what `ShareButton` publishes to a PUBLIC page when
a share is created from the history view — i.e. the degraded copy is the copy
strangers read. If the write drifts back above the mutations, that defect
returns and NOTHING ELSE catches it: the live response path uses the local
variable and stays correct either way, so every response-level test passes.

Source-level assertion, DB-free, in the tests/test_deletion_coverage.py style:
comments are STRIPPED before matching, because this repo has been bitten four
times by prose in comments/docstrings satisfying a substring check — and the
fix itself carries an explanatory comment containing these very words.
"""
import re
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "api" / "server.py"

# Markers, all matched against COMMENT-STRIPPED source:
WRITE_MARKER = "answer=summary"                    # the persisting write
MUT_SPELLING = 'summary = "Note: "'                # mutation 1
MUT_TFDA = 'summary = "TFDA grounding'             # mutation 2
# A string that exists ONLY inside the fix's explanatory comment — proves the
# stripper works (if stripping silently breaks, this fails loudly rather than
# letting comment prose satisfy the real assertions).
COMMENT_ONLY_MARKER = "Write ordering (fixed 2026-08-19)"


def _handler_source(stripped: bool = True) -> str:
    """The verify handler's source, comment-stripped by default."""
    raw = SERVER.read_text(encoding="utf-8")
    start = raw.index("async def verify_drug_interaction")
    # Handler ends at the next top-level decorator.
    end = raw.index("@app.post", start)
    body = raw[start:end]
    if not stripped:
        return body
    # Strip full-line and trailing # comments (string literals in this handler
    # contain no '#', verified; keep the strip simple and auditable).
    return re.sub(r"#.*", "", body)


def test_persisted_answer_write_is_after_both_mutations():
    src = _handler_source()
    write_pos = src.rindex(WRITE_MARKER)           # the ChatHistory kwarg
    assert write_pos > src.index(MUT_SPELLING), (
        "REGRESSION: the answer=summary write appears BEFORE the spelling-"
        "correction mutation — chat_history would store the un-corrected text."
    )
    assert write_pos > src.index(MUT_TFDA), (
        "REGRESSION: the answer=summary write appears BEFORE the TFDA-grounding "
        "mutation — chat_history would store the un-grounded text."
    )


def test_positive_controls_markers_exist():
    """The order assertions above cannot pass vacuously: every marker must be
    PRESENT in the stripped handler source. An emptied or refactored handler
    fails here instead of silently passing the ordering test."""
    src = _handler_source()
    assert WRITE_MARKER in src, "persisting write not found — update the guard"
    assert MUT_SPELLING in src, "spelling mutation not found — update the guard"
    assert MUT_TFDA in src, "TFDA mutation not found — update the guard"


def test_comment_stripping_actually_works():
    raw = _handler_source(stripped=False)
    src = _handler_source()
    assert COMMENT_ONLY_MARKER in raw, (
        "comment-only control marker missing from source — update this control"
    )
    assert COMMENT_ONLY_MARKER not in src, (
        "stripper failed: comment prose leaked into the matched source"
    )
