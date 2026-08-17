# api/services/deletion_service.py
"""Account-deletion helper — SOP Step 3 ONLY (design E).

Implements `docs/manual-deletion-sop.md` **Step 3** ("Erase + freeze +
de-identify (one transaction)") as a callable, so the in-app deletion feature
and the manual runbook cannot drift apart. Behaviour is taken verbatim from the
SOP at HEAD, not from memory.

NOTHING IN THE CODEBASE CALLS THIS YET. It is deliberately unreachable from any
route: the endpoint that will call it is a later piece of Deletion-feature C.

────────────────────────────────────────────────────────────────────────────
CONTRACT
────────────────────────────────────────────────────────────────────────────

1.  **IT DOES NOT COMMIT. The caller owns the transaction.** Required twice
    over. (i) By the ratified WRITTEN EXCEPTION to CLAUDE.md Rule 7: the whole
    routine is ONE transaction, so `_safe_db_write()` is not used — that helper
    commits on every call, which would turn eight statements into eight
    transactions and destroy the Step-3 atomicity the lawyer sign-off rests on.
    (ii) By `scripts/deletion_dryrun.py`, whose zero-residue guarantee IS the
    outer `db.rollback()`; a helper that committed internally would write to the
    dev branch and defeat that guard.

2.  **IT DOES NOT SWALLOW EXCEPTIONS. They propagate.** That is the other half
    of the Rule 7 exception, and CLAUDE.md Rule 18: `_safe_db_write()` catches,
    logs and returns `False`, so a partial deletion would be reported by return
    value. For deletion that is the worst possible failure mode — the caller
    must be able to let the transaction abort.

3.  🔴 **IT IMPLEMENTS SOP STEP 3 ONLY.** It does **NOT** do Step 1 (cancel the
    Dodo subscription) and does **NOT** do Step 5 (Clerk reconciliation).
    Design E puts cancel-Dodo FIRST deliberately: billing must stop before the
    freeze. **A future caller that invokes this helper and nothing else would
    erase the user's data while they keep getting billed.** That is the most
    expensive way this helper can be misused. Any endpoint wiring this in must
    perform Step 1 first and Step 5 after, and must confirm the cancellation
    before calling (SOP Step 1: "Do not freeze until cancellation is confirmed").

4.  **IT RETURNS per-table row counts BEFORE and AFTER**, because SOP Step 7
    (the operator audit trail, an ops document OUTSIDE the database) requires
    them. Returning them now costs one dict; retrofitting them later is an
    interface change.

────────────────────────────────────────────────────────────────────────────
WHAT IT DOES (SOP Step 3, verbatim)
────────────────────────────────────────────────────────────────────────────
  HARD DELETE      chat_history, audit_logs, user_feedback, user_profile,
                   bug_reports                       (personal data, removed)
  DE-IDENTIFY      api_cost_log.user_id -> NULL      (rows RETAINED, unlinked)
  DESIGN E FREEZE  user_usage.deleted_at = now()     (row RETAINED IN ORIGINAL
                   FORM — **NOT** pseudonymized, **NOT** deleted; the retired
                   FLAG #1 is superseded at the SOP's own L192-193)
  SEVER AUTHORSHIP shared_query.created_by -> NULL   (public page KEPT, Policy §8)

`user_usage` is retained under TW Business Accounting Act Art. 38 / GDPR
Art. 6(1)(c) and hidden from all product logic by the freeze — see
`api/services/usage_service.py::_resolve_usage`, which raises `AccountDeleted`
(403) for any row with `deleted_at` set.

This module intentionally does no logging: the deletion record is SOP Step 7,
an ops document outside the database (ratified decision (b)). The counts this
returns are what the operator records there.
"""

import re
from typing import Dict
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.sql_models import (
    ChatHistory,
    AuditLog,
    UserFeedback,
    UserProfile,
    BugReport,
    ApiCostLog,
    UserUsage,
    SharedQuery,
)

# The shape `_hash_created_by()` produces: sha256(...).hexdigest()[:16] — 16
# LOWERCASE hex characters (api/server.py:2934-2938). Shape only; see the
# FLAG #2 note in _hard_delete_user's docstring for what this cannot catch.
_CREATED_BY_HASH_RE = re.compile(r"^[0-9a-f]{16}$")

# The eight tables SOP Step 3 touches. Exposed as data (not a hand-typed list in
# a test) so `tests/test_deletion_table_coverage.py` can prove that every table
# in the model is either covered here or explicitly declared out of scope below.
DELETION_TABLES = frozenset({
    "chat_history",
    "audit_logs",
    "user_feedback",
    "user_profile",
    "bug_reports",
    "api_cost_log",
    "user_usage",
    "shared_query",
})

# SOP FLAG #3 — "out-of-scope tables (confirmed n/a)": these carry no per-user
# identity, so deletion takes no action on them. Declaring them explicitly is
# what lets the coverage guard fail loudly when a NEW table appears: an unknown
# table is neither deleted nor consciously exempted, and that is a compliance
# breach nothing else would catch.
OUT_OF_SCOPE_TABLES = frozenset({
    "anonymous_usage",
    "webhook_events",
    "blog_post",
    "explore_page",
})


def _scope_counts(db: Session, user_id: str, created_by_hash: str) -> Dict[str, int]:
    """Per-table row counts for this user, in SOP Step-2 baseline shape.

    `user_usage` is reported as TWO numbers on purpose:
      * ``user_usage_total``  — before 1, after 1. The row is RETAINED.
      * ``user_usage_active`` — before 1, after 0. The row is FROZEN.
    A single ``user_usage: 1 -> 0`` line in the Step 7 log would read as "the
    billing row was deleted", which is precisely the design-E misreading the
    freeze exists to prevent.
    """
    return {
        "chat_history": db.query(ChatHistory).filter(ChatHistory.user_id == user_id).count(),
        "audit_logs": db.query(AuditLog).filter(AuditLog.user_id == user_id).count(),
        "user_feedback": db.query(UserFeedback).filter(UserFeedback.user_id == user_id).count(),
        "user_profile": db.query(UserProfile).filter(UserProfile.user_id == user_id).count(),
        "bug_reports": db.query(BugReport).filter(BugReport.user_id == user_id).count(),
        "api_cost_log": db.query(ApiCostLog).filter(ApiCostLog.user_id == user_id).count(),
        "user_usage_total": db.query(UserUsage).filter(
            UserUsage.clerk_user_id == user_id).count(),
        "user_usage_active": db.query(UserUsage).filter(
            UserUsage.clerk_user_id == user_id, UserUsage.deleted_at.is_(None)).count(),
        "shared_query": db.query(SharedQuery).filter(
            SharedQuery.created_by == created_by_hash).count(),
    }


def _hard_delete_user(db: Session, user_id: str, *, created_by_hash: str) -> Dict[str, object]:
    """Execute SOP Step 3 for one user. Does NOT commit. Does NOT catch.

    Args:
        db:   an open Session. **The caller owns the transaction** — this
              function neither commits nor rolls back.
        user_id: the Clerk user id (``user_2abc...``). Stored in the ``user_id``
              column of most tables and in ``user_usage.clerk_user_id``.
        created_by_hash: the salted ``shared_query.created_by`` hash for this
              user, ``sha256(f"{SHARE_CREATED_BY_SALT}:{user_id}")[:16]``.
              **Required, keyword-only, no default — on purpose.** SOP FLAG #2:
              the wrong salt matches ZERO rows and silently leaves authorship
              links intact. A defaulted or optional parameter would make that
              silent failure the easy path; a required one makes forgetting it a
              TypeError at the call site. The caller computes it because doing
              so here would mean importing ``api.server`` for
              ``_hash_created_by`` — and that import runs ``sentry_sdk.init``,
              builds the FastAPI app, adds middleware and calls
              ``Path("static/og").mkdir()``. A deletion helper must not drag
              that in.

              **Its SHAPE is validated (16 lowercase hex chars, matching
              ``_hash_created_by`` at ``api/server.py:2934-2938``), which catches
              an empty string, ``None``, a truncated paste and an obvious typo.**

              🔴 **The shape check does NOT and CANNOT catch the failure SOP
              FLAG #2 actually describes: a WELL-FORMED hash computed with the
              WRONG SALT.** That value passes every check here, matches ZERO
              ``shared_query`` rows, and leaves the authorship links silently
              intact — deletion reports success while the public pages remain
              attributed. Nothing inside this helper can close that gap: the
              salt lives in the caller's environment and the helper has no way
              to know which one was used. **The only defence is the SOP's own
              Step 2 instruction — confirm the pre-flight count is non-zero for
              a user known to have shared something — and it is a HUMAN check.**
              Do not read the shape assertion as FLAG #2 being handled.

    Returns:
        ``{"user_id", "created_by_hash", "before": {...}, "after": {...}}`` —
        the per-table counts SOP Step 7 requires the operator to record.

    Raises:
        ValueError: if ``user_id`` is empty or ``created_by_hash`` is not the
            16-lowercase-hex shape ``_hash_created_by`` produces. Raised BEFORE
            any statement runs, so a malformed call deletes nothing.
        Otherwise: whatever the database raises. By design (contract point 2).
    """
    # Fail before touching anything. A ValueError (not an `assert`) because
    # asserts vanish under `python -O` and this is a data-destruction guard.
    if not user_id:
        raise ValueError("user_id is required")
    if not isinstance(created_by_hash, str) or not _CREATED_BY_HASH_RE.match(created_by_hash):
        raise ValueError(
            "created_by_hash must be 16 lowercase hex characters, as produced by "
            "_hash_created_by(). NOTE: this only checks SHAPE — a well-formed hash "
            "computed with the WRONG SALT passes here and silently matches zero "
            "shared_query rows (SOP FLAG #2)."
        )

    before = _scope_counts(db, user_id, created_by_hash)

    # ---- HARD DELETE: personal data, removed outright (SOP L110-114) --------
    # synchronize_session=False: bulk DML, no in-session object fixup. The
    # caller re-reads via db.expire_all() if it holds stale ORM objects.
    db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(synchronize_session=False)
    db.query(UserFeedback).filter(UserFeedback.user_id == user_id).delete(synchronize_session=False)
    db.query(UserProfile).filter(UserProfile.user_id == user_id).delete(synchronize_session=False)
    db.query(BugReport).filter(BugReport.user_id == user_id).delete(synchronize_session=False)

    # ---- DE-IDENTIFY + RETAIN: sever the link, keep the rows (SOP L119) -----
    db.query(ApiCostLog).filter(ApiCostLog.user_id == user_id).update(
        {ApiCostLog.user_id: None}, synchronize_session=False)

    # ---- DESIGN E FREEZE: retained in original form, hidden from product ----
    # NOT pseudonymized, NOT deleted (SOP L121-124). DB-side now() to match the
    # SOP's `now()` exactly rather than sending a client clock.
    db.query(UserUsage).filter(UserUsage.clerk_user_id == user_id).update(
        {UserUsage.deleted_at: func.now()}, synchronize_session=False)

    # ---- shared_query: sever authorship, KEEP the public page (SOP L126-127) -
    db.query(SharedQuery).filter(SharedQuery.created_by == created_by_hash).update(
        {SharedQuery.created_by: None}, synchronize_session=False)

    after = _scope_counts(db, user_id, created_by_hash)

    return {
        "user_id": user_id,
        "created_by_hash": created_by_hash,
        "before": before,
        "after": after,
    }
