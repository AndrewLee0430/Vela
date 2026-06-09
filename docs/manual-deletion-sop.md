# Manual Data-Deletion SOP (interim operator runbook)

> **INTERIM manual process** until **deletion-feature C** (in-app *Delete account & data*
> button + Clerk `user.deleted` webhook) ships — see `BACKLOG.md` → *Deletion-feature C*.
> This runbook is how the **30-day deletion promise** in the deployed Privacy Policy (§4)
> is honored **by hand** in the meantime. It is a runbook, **not** executable product code.

**Trigger:** a user emails `support@an-tho.com` requesting account / data deletion.
**SLA:** complete within **30 days** of the request (per the deployed Policy §4).
**Database:** Neon Postgres (prod). Run all SQL against the **prod** branch.
**Authority:** founder/operator with prod DB access + the prod `SHARE_CREATED_BY_SALT` secret.

Column/table names below are verbatim from `api/models/sql_models.py` (verified, not guessed).
Throughout, `:user_id` = the **Clerk user id** string (e.g. `user_2abc...`). The same value
is stored in the `user_id` columns of most tables **and** in `user_usage.clerk_user_id`.

---

## Step 0 — Identify the user (email → Clerk user_id)

The codebase only has the **forward** lookup (user_id → email, `server.py:1448`, a
`GET https://api.clerk.com/v1/users/{user_id}` with `Authorization: Bearer $CLERK_SECRET_KEY`).
There is **no reverse email→id endpoint in our code**, so resolve it via Clerk directly:

- **Clerk Dashboard** → Users → search the requester's email → copy the `user_...` id, **or**
- **Clerk API** (same `CLERK_SECRET_KEY` bearer as `server.py:1449`):
  ```bash
  curl -s "https://api.clerk.com/v1/users?email_address=REQUESTER_EMAIL" \
       -H "Authorization: Bearer $CLERK_SECRET_KEY" | jq '.[].id'
  ```

**Confirm identity** before acting: verify the requesting email is the user's primary email on
the Clerk record. Record the resolved `:user_id` and the requester email.

---

## Step 1 — Pre-flight: snapshot affected row counts

Compute the `shared_query` hash first (Step 4 needs it), then take a baseline count.

```python
# shared_query.created_by = sha256(f"{SHARE_CREATED_BY_SALT}:{user_id}")[:16]
# (verbatim from _hash_created_by(), server.py:2370-2374 — note the ':' separator)
import hashlib, os
salt = os.environ["SHARE_CREATED_BY_SALT"]      # PROD value (Fly secret), NOT the test default
user_id = "user_2abc..."                         # from Step 0
created_by_hash = hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]
print(created_by_hash)
```

```sql
-- Baseline (record these numbers in the ops log):
SELECT 'chat_history'  AS tbl, count(*) FROM chat_history  WHERE user_id = :user_id
UNION ALL SELECT 'audit_logs',    count(*) FROM audit_logs    WHERE user_id = :user_id
UNION ALL SELECT 'user_feedback', count(*) FROM user_feedback WHERE user_id = :user_id
UNION ALL SELECT 'user_profile',  count(*) FROM user_profile  WHERE user_id = :user_id
UNION ALL SELECT 'bug_reports',   count(*) FROM bug_reports   WHERE user_id = :user_id
UNION ALL SELECT 'user_usage',    count(*) FROM user_usage    WHERE clerk_user_id = :user_id
UNION ALL SELECT 'api_cost_log',  count(*) FROM api_cost_log  WHERE user_id = :user_id
UNION ALL SELECT 'shared_query',  count(*) FROM shared_query  WHERE created_by = :created_by_hash;
```

Run Steps 2–4 inside a single transaction so a bad count can be rolled back:

```sql
BEGIN;
-- ... Step 2, 3, 4 statements ...
-- ... Step 5 verification ...
COMMIT;   -- or ROLLBACK; if anything looks wrong
```

---

## Step 2 — HARD DELETE (remove rows entirely)

These hold query/answer content, audit trails, feedback, the Pro context hash, and bug
reports — all deleted outright.

```sql
DELETE FROM chat_history  WHERE user_id = :user_id;   -- question + answer history
DELETE FROM audit_logs    WHERE user_id = :user_id;   -- query_content audit trail
DELETE FROM user_feedback WHERE user_id = :user_id;   -- raw query + response + edits
DELETE FROM user_profile  WHERE user_id = :user_id;   -- PK = user_id; Pro context hash + locale
DELETE FROM bug_reports   WHERE user_id = :user_id;   -- the user's signed-in bug reports
```

**Optional (anon reports they filed by email):** `bug_reports` also has an `email` column and
its `user_id` is nullable. To scrub anonymous reports the same person filed without being
signed in, either delete or de-identify by email — keeping the non-identifying tech fields
(`issue_type`, `description`, `page_url`, `user_agent`, `locale`):

```sql
UPDATE bug_reports SET email = NULL WHERE email = :requester_email AND user_id IS NULL;
```

---

## Step 3 — DE-IDENTIFY + RETAIN (statutory billing/usage, 5 yr — do NOT delete)

Per the lawyer spec, transactional/billing/usage metadata is kept up to 5 years for
statutory tax/accounting obligations, but the **user link** is severed.

**`api_cost_log`** — `user_id` is a plain nullable column → straightforward SET NULL:
```sql
UPDATE api_cost_log SET user_id = NULL WHERE user_id = :user_id;
-- Retains: feature, model, prompt_tokens, completion_tokens, estimated_cost_usd, created_at.
```

**`user_usage`** — ⚠️ **see FLAG #1 below**: `clerk_user_id` is the **PRIMARY KEY**, so
`SET NULL` is impossible. Interim approach = pseudonymize the PK in place, keeping the
payment-provider IDs + plan + counters (the actual statutory records):
```sql
UPDATE user_usage
   SET clerk_user_id = 'deleted:' || substr(md5(clerk_user_id), 1, 16)
 WHERE clerk_user_id = :user_id;
-- Retains: plan_type, credits_used, credits_used_today, lemon_*_id,
--          dodo_customer_id, dodo_subscription_id, current_period_end, timestamps.
```
> Do **not** run this until the FLAG #1 decision below is confirmed for the request at hand.

---

## Step 4 — `shared_query`: SET NULL on `created_by`, KEEP the page

Locked decision (2026-06-09, Policy §8): public shared pages survive account deletion; only
the authorship link is severed. `created_by` is the **salted hash** from Step 1 — you cannot
match on raw `user_id`.

```sql
UPDATE shared_query SET created_by = NULL WHERE created_by = :created_by_hash;
-- query_text / answer_text / citations / view_count / is_public are intentionally KEPT.
```

---

## Step 5 — Verify (before COMMIT)

Re-run the Step 1 count query. Expected after the statements:

| table | expected post-count for the user |
|---|---|
| `chat_history`, `audit_logs`, `user_feedback`, `user_profile`, `bug_reports` | **0** (hard-deleted) |
| `api_cost_log` WHERE `user_id = :user_id` | **0** (now NULL; rows retained, unlinked) |
| `user_usage` WHERE `clerk_user_id = :user_id` | **0** (row retained under the pseudonymized key) |
| `shared_query` WHERE `created_by = :created_by_hash` | **0** (now NULL; page retained) |

If every row matches, `COMMIT;`. Otherwise `ROLLBACK;` and investigate.

---

## Step 6 — Backups / residual copies (no manual action)

Residual copies in Neon's automated backups expire on their own via the **PITR window**
(currently the Neon **Free** tier window; the Policy states copies are overwritten **within
24 hours**). No manual backup scrub is needed or possible on managed PITR.
> If the Neon plan changes such that the PITR retention exceeds 24h, the Policy §4 "within 24
> hours" claim must be revisited (tracked as TECH_DEBT R5(d) — Neon-paid backup wording).

---

## Step 7 — Log the action (operator audit trail)

Record, in the ops deletion log (e.g. a private doc / sheet — **not** a user-facing table):

- date/time of request and of completion (confirm ≤ 30 days)
- requester email + resolved Clerk `:user_id` + the computed `:created_by_hash`
- per-table row counts **before** and **after**
- operator name
- any FLAG decisions taken (esp. FLAG #1)

Then reply to the requester confirming completion.

---

## ⚠️ FLAGS / open decisions (resolve before first real run)

**FLAG #1 — `user_usage.clerk_user_id` is the PRIMARY KEY (schema ≠ lawyer "SET NULL" spec).**
The lawyer spec says "sever user_id (SET NULL or truncate)" for the billing/usage tables. That
works for `api_cost_log` (plain column) but **not** for `user_usage`, where the user id *is*
the PK and cannot be nulled. `user_usage` holds **no name/email** — its only identity fields
are the Clerk id (PK) and the payment-provider IDs (which are the records we must keep). Decide:
- **(A) Pseudonymize the PK in place** (the Step-3 SQL above) — severs the Clerk-id linkage,
  keeps billing IDs + numbers. *Recommended.* Caveat: `dodo_customer_id` / `dodo_subscription_id`
  still tie to a real payment identity at the processor — but that linkage is the statutory
  record we are required to retain, so this is consistent with the 5-yr retention basis.
- **(B) Leave the row keyed as-is** (no change) on the theory that `user_usage` contains no
  direct PII beyond the Clerk id. Weaker de-identification; not recommended given the Policy
  promises the *user link* is severed.

**FLAG #2 — `shared_query.created_by` is a salted hash, needs the PROD salt.**
Step 4 requires the **production** `SHARE_CREATED_BY_SALT` (Fly secret) to compute the hash.
Using the wrong/test salt will match **zero** rows and silently leave authorship links intact.
Always compute the hash with the prod salt and confirm the Step-1 count is non-zero if the
user is known to have shared anything.

**FLAG #3 — out-of-scope tables (confirmed n/a, listed for completeness).**
`anonymous_usage` (keyed by `anon_id`, never account-linked), `webhook_events`,
`blog_post`, `explore_page` (editorial/system content) carry no per-user identity → no action.

---

*When deletion-feature C ships, this manual SOP is superseded by `_hard_delete_user(db, user_id)`
(the shared helper reused by the in-app button, the history-only option, and the Clerk
`user.deleted` webhook). Until then, this runbook is the binding process.*
