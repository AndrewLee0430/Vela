#!/usr/bin/env python
"""Dev-only dry-run for the manual-deletion SOP (design E).

Proves the SOP's SQL executes and lands the correct design-E post-state, WITHOUT
ever touching prod and WITHOUT leaving residue on dev.

Safety (triple-guard):
  1. ALLOW-LIST: DATABASE_URL must CONTAIN the dev-branch substring; anything else
     is refused before any connection. The prod host is never named.
  2. Explicit DELETION_DRYRUN_ALLOW=1 env flag required for --execute.
  3. --execute runs the whole thing in ONE transaction that ALWAYS ROLLS BACK.

Modes:
  (default) --plan : read-trace only — prints the exact SQL a real run would
                     execute, opens NO database connection.
  --execute        : run on the dev branch, assert the design-E post-state,
                     then ROLLBACK (zero residue).

Design E: user_usage is RETAINED IN ORIGINAL FORM but FROZEN (deleted_at set) —
NOT pseudonymized, NOT deleted. The decisive proof is that get_active_usage(target)
raises AccountDeleted (the freeze hides the retained row from all product logic).
"""

import os
import sys
import time
import hashlib
import argparse
from datetime import datetime, timezone

# Make the `api` package importable regardless of CWD — this script lives in
# scripts/, so the repo root (one level up) must be on sys.path. Self-sufficient:
# the deletion tool must not depend on the operator setting PYTHONPATH. (Used only
# by run_execute's api imports; harmless to plan mode, which imports no api.)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Read .env (DATABASE_URL = dev branch) — the same source the app + the 008 dev
# migration use. load_dotenv only reads the FILE into os.environ; it opens no
# connection and does NOT weaken the allow-list guard below (the substring check
# is still applied to whatever URL results — a prod .env would still abort).
load_dotenv()

# Allow-list: the dev Neon branch substring (covers both pooler + direct hosts).
DEV_SUBSTR = "ep-spring-voice-a127ye10"
# A KNOWN test salt for the synthetic shared_query.created_by — NEVER the prod salt.
TEST_SALT = "dryrun_test_salt"

# The SOP's Step-3 statements (one transaction in a real run). Parameterized.
SOP_SQL = [
    ("HARD DELETE chat_history",  "DELETE FROM chat_history  WHERE user_id = :user_id"),
    ("HARD DELETE audit_logs",    "DELETE FROM audit_logs    WHERE user_id = :user_id"),
    ("HARD DELETE user_feedback", "DELETE FROM user_feedback WHERE user_id = :user_id"),
    ("HARD DELETE user_profile",  "DELETE FROM user_profile  WHERE user_id = :user_id"),
    ("HARD DELETE bug_reports",   "DELETE FROM bug_reports   WHERE user_id = :user_id"),
    ("DE-IDENTIFY api_cost_log",  "UPDATE api_cost_log SET user_id = NULL WHERE user_id = :user_id"),
    ("FREEZE user_usage (design E)", "UPDATE user_usage SET deleted_at = now() WHERE clerk_user_id = :user_id"),
    ("SET NULL shared_query.created_by", "UPDATE shared_query SET created_by = NULL WHERE created_by = :created_by_hash"),
]


def created_by_hash(salt: str, user_id: str) -> str:
    """sha256(f'{salt}:{user_id}')[:16] — mirrors _hash_created_by (server.py:2370-2374)."""
    return hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]


def _parse_host_db(url: str):
    host = url.split("@", 1)[-1].split("/", 1)[0] if "@" in url else "?"
    dbname = url.rsplit("/", 1)[-1].split("?", 1)[0] if "/" in url else "?"
    return host, dbname


def guard() -> str:
    """Refuse to run unless DATABASE_URL is the dev branch AND the flag is set."""
    url = os.environ.get("DATABASE_URL", "")
    if DEV_SUBSTR not in url:
        sys.exit(f"ABORT: DATABASE_URL does not contain the dev-branch marker "
                 f"'{DEV_SUBSTR}'. Refusing to connect (allow-list guard).")
    if os.environ.get("DELETION_DRYRUN_ALLOW") != "1":
        sys.exit("ABORT: set DELETION_DRYRUN_ALLOW=1 to permit the dry-run.")
    host, dbname = _parse_host_db(url)
    print(f"[guard] dev branch OK | host={host} | db={dbname}")
    return url


def print_trace(user_id: str, h: str) -> None:
    print("\n=== READ-TRACE: SQL a real run would execute (Step 3, one transaction) ===")
    print(f"-- :user_id = '{user_id}'   :created_by_hash = '{h}'\n")
    for label, sql in SOP_SQL:
        filled = sql.replace(":user_id", f"'{user_id}'").replace(":created_by_hash", f"'{h}'")
        print(f"-- {label}\n{filled};\n")
    print("-- (a real run wraps these in BEGIN…COMMIT; the dry-run wraps them in a "
          "ROLLBACK-only transaction)")


def run_execute(url: str) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from api.models.sql_models import (
        AuditLog, ChatHistory, UserFeedback, UserProfile,
        BugReport, UserUsage, ApiCostLog, SharedQuery,
    )
    from api.services.usage_service import get_active_usage
    from api.errors import AccountDeleted

    ts = int(time.time())
    target = f"user_DRYRUN_{ts}"
    control = f"user_DRYRUN_CONTROL_{ts}"
    h_t = created_by_hash(TEST_SALT, target)
    h_c = created_by_hash(TEST_SALT, control)

    print_trace(target, h_t)

    engine = create_engine(url)
    db = sessionmaker(bind=engine)()
    results = []

    def ck(name, cond):
        results.append(bool(cond))
        print(("PASS" if cond else "FAIL"), "|", name)

    def seed(uid: str, h: str) -> None:
        db.add(AuditLog(id=f"aud_{uid}", user_id=uid, action="research",
                        query_content="x", resource_ids=[], ip_address="0.0.0.0"))
        db.add(ChatHistory(user_id=uid, session_type="research", question="q", answer="a"))
        db.add(UserFeedback(id=f"fb_{uid}", user_id=uid, query="q", response="a",
                            rating=1, category="research"))
        db.add(UserProfile(user_id=uid, user_context_hash="deadbeefdeadbeef", locale="en"))
        db.add(BugReport(id=f"bug_{uid}", issue_type="other", description="d", user_id=uid))
        db.add(UserUsage(clerk_user_id=uid, plan_type="pro",
                         dodo_customer_id=f"cust_{uid}", dodo_subscription_id=f"sub_{uid}"))
        db.add(ApiCostLog(user_id=uid, feature="research", model="gpt-4.1",
                          prompt_tokens=10, completion_tokens=20, estimated_cost_usd=0.01))
        db.add(SharedQuery(share_id=f"sq_{uid}", query_text="qt", answer_text="at",
                           citations=[], created_by=h, is_public=True, view_count=0, flagged=False))

    print(f"\n=== EXECUTE (rollback-only) | target={target} control={control} ===")
    try:
        seed(target, h_t)
        seed(control, h_c)
        db.flush()
        cost_before = db.execute(text("SELECT count(*) FROM api_cost_log")).scalar()

        # --- run the SOP's literal SQL within the uncommitted transaction ---
        params = {"user_id": target, "created_by_hash": h_t}
        for _, sql in SOP_SQL:
            db.execute(text(sql), params)
        db.flush()
        db.expire_all()   # force ORM reads (get_active_usage) to re-fetch post-SOP state

        # --- E-specific asserts: TARGET ---
        for tbl in ("chat_history", "audit_logs", "user_feedback", "user_profile", "bug_reports"):
            n = db.execute(text(f"SELECT count(*) FROM {tbl} WHERE user_id=:u"), {"u": target}).scalar()
            ck(f"hard-delete {tbl} -> 0", n == 0)

        n_link = db.execute(text("SELECT count(*) FROM api_cost_log WHERE user_id=:u"), {"u": target}).scalar()
        cost_after = db.execute(text("SELECT count(*) FROM api_cost_log")).scalar()
        ck("api_cost_log target user_id NULLed", n_link == 0)
        ck("api_cost_log rows RETAINED (no deletion)", cost_after == cost_before)

        uu = db.execute(text(
            "SELECT clerk_user_id, dodo_customer_id, dodo_subscription_id, deleted_at "
            "FROM user_usage WHERE clerk_user_id=:u"), {"u": target}).first()
        ck("user_usage RETAINED (row exists, original clerk_user_id)", uu is not None and uu[0] == target)
        ck("user_usage NOT pseudonymized (dodo_* intact)",
           uu is not None and uu[1] == f"cust_{target}" and uu[2] == f"sub_{target}")
        ck("user_usage FROZEN (deleted_at SET)", uu is not None and uu[3] is not None)

        # decisive design-E proof: product logic can no longer see the frozen row
        try:
            get_active_usage(db, target)
            ck("get_active_usage(target) raises AccountDeleted", False)
        except AccountDeleted:
            ck("get_active_usage(target) raises AccountDeleted", True)

        sq = db.execute(text(
            "SELECT created_by, query_text, answer_text FROM shared_query WHERE share_id=:s"),
            {"s": f"sq_{target}"}).first()
        ck("shared_query created_by NULLed", sq is not None and sq[0] is None)
        ck("shared_query page KEPT (text preserved)", sq is not None and sq[1] == "qt" and sq[2] == "at")

        # --- CONTROL untouched (no over-deletion) ---
        ctl_rows = 0
        for tbl in ("chat_history", "audit_logs", "user_feedback", "user_profile", "bug_reports", "api_cost_log"):
            ctl_rows += db.execute(text(f"SELECT count(*) FROM {tbl} WHERE user_id=:u"), {"u": control}).scalar()
        ctl_uu = db.execute(text("SELECT count(*) FROM user_usage WHERE clerk_user_id=:u AND deleted_at IS NULL"),
                            {"u": control}).scalar()
        ctl_sq = db.execute(text("SELECT count(*) FROM shared_query WHERE created_by=:h"), {"h": h_c}).scalar()
        ck("CONTROL user untouched (6 rows present, not frozen, share intact)",
           ctl_rows == 6 and ctl_uu == 1 and ctl_sq == 1)

    finally:
        db.rollback()   # ALWAYS — zero residue on the dev branch
        db.close()
        print("\n[txn] ROLLED BACK — no residue on dev.")

    ok = all(results) and len(results) > 0
    print(f"\n{sum(results)}/{len(results)} asserts passed — "
          f"{'ALL PASS' if ok else '*** SOME FAILED ***'}")
    sys.exit(0 if ok else 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dev-only deletion-SOP dry-run (design E).")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true",
                      help="read-trace only, opens NO DB connection (DEFAULT)")
    mode.add_argument("--execute", action="store_true",
                      help="run on the dev branch (rollback-only); allow-list guarded")
    args = ap.parse_args()

    if args.execute:
        # Guard runs AFTER load_dotenv (module level): allow-list is the absolute
        # last line of defense before any connection.
        url = guard()
        run_execute(url)
        return

    # no-arg OR --plan: pure read-trace. Opens NO database connection.
    url = os.environ.get("DATABASE_URL", "")
    host, dbname = _parse_host_db(url) if url else ("(unset)", "(unset)")
    if DEV_SUBSTR in url:
        print(f"[plan] DATABASE_URL → host={host} | db={dbname} (dev branch — --execute would run here)")
    else:
        print(f"[plan] NOTE: DATABASE_URL host={host} does not contain '{DEV_SUBSTR}' — "
              f"--execute would ABORT (allow-list guard).")
    ex = "user_DRYRUN_<ts>"
    print_trace(ex, created_by_hash(TEST_SALT, ex))
    print("\n[plan] read-trace only — nothing executed, no DB connection opened.")
    print("[plan] to run for real on dev:")
    print("       DELETION_DRYRUN_ALLOW=1 python scripts/deletion_dryrun.py --execute")


if __name__ == "__main__":
    main()
