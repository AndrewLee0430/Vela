"""Deletion-routine guards — DB-FREE. Complements, does not duplicate, the harness.

`scripts/deletion_dryrun.py` proves the routine's BEHAVIOUR against a real dev
database (14 asserts, both --impl paths). It cannot run in CI and it cannot see
the future. These two guards cover what it structurally cannot:

1. TABLE COVERAGE — the business rule (CLAUDE.md Rule 17):
   **someone adds a new table holding user data, and the deletion routine
   silently fails to cover it.** That is a compliance breach — the deployed
   Privacy Policy §4 promises deletion within 30 days — and NOTHING else in the
   repo would catch it. The dry-run would still pass 14/14, because it only
   asserts on the tables it already knows about. The SOP would still read as
   correct. The new table would simply retain personal data forever.

   The sets are DERIVED (from SQLAlchemy's metadata and from the deletion
   module), never hand-typed here — a hand-typed list would rot the moment
   either side changed, which is the failure mode this guard exists to prevent.

2. NO-COMMIT CONTRACT — `_hard_delete_user` must not commit. This is load-
   bearing twice: the ratified WRITTEN EXCEPTION to Rule 7 (one transaction, so
   the caller owns it) and the dry-run harness, whose zero-residue guarantee IS
   the outer `db.rollback()`. A helper that committed internally would write to
   the dev branch and defeat the allow-list guard.

DB-free by construction: importing the models builds SQLAlchemy metadata and a
lazy Engine; no connection is opened. The contract test drives a mock session.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

import api.models.sql_models  # noqa: F401 — imported for its side effect on Base.metadata
from api.database.sql_db import Base
from api.services.deletion_service import (
    DELETION_TABLES,
    OUT_OF_SCOPE_TABLES,
    _hard_delete_user,
)

SERVER_PY = Path(__file__).resolve().parents[1] / "api" / "server.py"


def _model_tables() -> set:
    """Every table SQLAlchemy knows about — derived, not listed."""
    return set(Base.metadata.tables.keys())


def test_every_model_table_is_either_deleted_or_declared_out_of_scope():
    """WHAT BREAKS IF THIS FAILS: a table exists that the deletion routine
    neither clears nor consciously exempts, so a user who asks to be deleted
    keeps personal data in it — against the deployed Policy §4 promise."""
    model = _model_tables()
    classified = DELETION_TABLES | OUT_OF_SCOPE_TABLES

    unclassified = model - classified
    assert not unclassified, (
        f"table(s) in sql_models.py that the deletion routine neither touches nor "
        f"declares out of scope: {sorted(unclassified)}. Decide explicitly: add to "
        f"DELETION_TABLES (and to _hard_delete_user) or to OUT_OF_SCOPE_TABLES "
        f"(and to the SOP's FLAG #3). Do NOT silence this by editing the test."
    )

    phantom = classified - model
    assert not phantom, (
        f"deletion_service names table(s) that no longer exist in sql_models.py: "
        f"{sorted(phantom)} — the routine is targeting something that is gone"
    )


def test_the_two_sets_are_disjoint():
    """A table cannot be both cleared and exempt; that would mean the SOP and the
    code disagree about the same table."""
    overlap = DELETION_TABLES & OUT_OF_SCOPE_TABLES
    assert not overlap, f"table(s) both deleted and declared out of scope: {sorted(overlap)}"


def test_partition_is_exact_and_matches_the_sop_shape():
    """The SOP touches 8 tables (Step 3) and declares 4 out of scope (FLAG #3).
    Asserted as a partition of the DERIVED model set, not as magic numbers on
    their own — the counts are a readability check on top of the set equality."""
    assert DELETION_TABLES | OUT_OF_SCOPE_TABLES == _model_tables()
    assert len(DELETION_TABLES) == 8, sorted(DELETION_TABLES)
    assert len(OUT_OF_SCOPE_TABLES) == 4, sorted(OUT_OF_SCOPE_TABLES)


def test_hard_delete_user_does_not_commit_and_does_not_rollback():
    """WHAT BREAKS IF THIS FAILS: the helper takes the transaction away from its
    caller. In the dry-run that means real writes land on the dev branch despite
    the rollback-only design; in production it means the eight statements stop
    being atomic and a partial deletion can be left committed."""
    db = MagicMock()

    _hard_delete_user(db, "user_TEST", created_by_hash="deadbeefdeadbeef")

    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.close.assert_not_called()


def test_hard_delete_user_actually_issues_the_sop_mutations():
    """Negative control for the test above: a helper that did NOTHING would also
    never commit. Pin the shape of the work — 5 hard deletes, 3 updates, and the
    before/after count pairs — so 'no commit' cannot be satisfied by 'no work'."""
    db = MagicMock()
    q = db.query.return_value.filter.return_value

    result = _hard_delete_user(db, "user_TEST", created_by_hash="deadbeefdeadbeef")

    assert q.delete.call_count == 5, (
        f"expected 5 hard DELETEs (SOP Step 3 names exactly 5 tables), got {q.delete.call_count}")
    assert q.update.call_count == 3, (
        f"expected 3 UPDATEs (api_cost_log SET NULL, user_usage freeze, "
        f"shared_query SET NULL), got {q.update.call_count}")
    # 9 counted scopes, taken twice (before + after)
    assert q.count.call_count == 18, f"expected 18 count() calls, got {q.count.call_count}"

    assert set(result) == {"user_id", "created_by_hash", "before", "after"}
    assert set(result["before"]) == set(result["after"])
    # The design-E distinction must be reportable to SOP Step 7: the billing row
    # is RETAINED (total) while being FROZEN (active). One combined number would
    # read as "the row was deleted" — the exact misreading the freeze prevents.
    assert "user_usage_total" in result["before"]
    assert "user_usage_active" in result["before"]


def _clerk_handler_code() -> str:
    """The `/api/webhooks/clerk` handler body with DOCSTRINGS STRIPPED.

    Stripping matters: the handler's docstring says, in prose, that it does not
    call `_hard_delete_user()` and does not touch `user_usage`. A naive substring
    search over the raw source therefore finds those names and 'passes' for
    exactly the wrong reason — the same prose-satisfies-the-check hazard this
    repo has hit before.
    """
    src = SERVER_PY.read_text(encoding="utf-8", errors="replace")
    lines = src.split("\n")
    start = next(i for i, l in enumerate(lines) if '@app.post("/api/webhooks/clerk")' in l)
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("@app."))
    body = "\n".join(lines[start:end])
    return re.sub(r'"""[\s\S]*?"""', "", body)


def test_clerk_webhook_stays_non_destructive():
    """WHAT BREAKS IF THIS FAILS: the Clerk webhook stops being a recording
    surface and starts deleting user data on an inbound event.

    🔴 THIS GUARD IS NOT HERE TO BLOCK THAT WIRING. Connecting `user.deleted` to
    `_hard_delete_user()` is a planned, wanted step of Deletion-feature C. The
    guard exists so that whoever does it must **DELETE THIS TEST DELIBERATELY**,
    in the same commit, with the reasoning written down — rather than the
    endpoint drifting from non-destructive to destructive as a side effect of
    some other change, on a surface whose whole documented claim is that it only
    writes `webhook_events`.

    Removing this test IS the decision point. That is its entire job.
    """
    code = _clerk_handler_code()

    assert "_hard_delete_user" not in code, (
        "the Clerk webhook now calls the deletion helper in CODE. If that is "
        "intended, delete this test in the same commit and say so — do not "
        "weaken it."
    )
    for name in ("UserUsage", "user_usage"):
        assert name not in code, (
            f"the Clerk webhook now references {name} in CODE; it is documented "
            f"as writing webhook_events ONLY (it must not touch the billing row, "
            f"including the deleted_at freeze marker)"
        )
    assert "deleted_at" not in code, "the Clerk webhook now touches the freeze marker"

    # Positive control: the slice really is the handler, so the assertions above
    # are not passing because we accidentally isolated an empty string.
    assert "webhook_events" in code or "WebhookEvent" in code, (
        "handler slice does not contain its own WebhookEvent write — the "
        "isolation is wrong and every assertion above is vacuous"
    )
    assert "CLERK_WEBHOOK_SECRET" in code


def test_created_by_hash_shape_is_validated():
    """Shape only — 16 lowercase hex, matching `_hash_created_by`.

    🔴 Deliberately NOT a claim that SOP FLAG #2 is handled. A well-formed hash
    computed with the WRONG SALT passes every assertion here, matches zero
    `shared_query` rows, and leaves authorship silently intact. That gap cannot
    be closed inside the helper — the salt lives in the caller's environment.
    """
    db = MagicMock()
    good = "0123456789abcdef"

    for bad in ("", "not-a-hash", "ABCDEF0123456789", "0123456789abcde",
                "0123456789abcdef0", None, 12345):
        try:
            _hard_delete_user(db, "user_TEST", created_by_hash=bad)  # type: ignore[arg-type]
            raise AssertionError(f"accepted malformed created_by_hash {bad!r}")
        except ValueError:
            pass

    # A malformed call must delete NOTHING — the guard runs before any statement.
    assert db.query.call_count == 0, "statements ran before the shape check"

    # And the valid shape is accepted.
    _hard_delete_user(db, "user_TEST", created_by_hash=good)
    assert db.query.call_count > 0

    # Empty user_id is refused too, and again before any statement.
    db2 = MagicMock()
    try:
        _hard_delete_user(db2, "", created_by_hash=good)
        raise AssertionError("accepted an empty user_id")
    except ValueError:
        pass
    assert db2.query.call_count == 0


def test_created_by_hash_is_required_and_keyword_only():
    """SOP FLAG #2: the wrong or missing salt matches ZERO shared_query rows and
    silently leaves authorship links intact. A default would make that silent
    failure the easy path, so the parameter is required and keyword-only —
    forgetting it must be a TypeError at the call site, not a quiet no-op."""
    db = MagicMock()

    try:
        _hard_delete_user(db, "user_TEST")           # type: ignore[call-arg]
        raise AssertionError("created_by_hash is not required — it must be")
    except TypeError:
        pass

    try:
        _hard_delete_user(db, "user_TEST", "deadbeefdeadbeef")  # type: ignore[misc]
        raise AssertionError("created_by_hash accepted positionally — it must be keyword-only")
    except TypeError:
        pass
