# Manual Data-Deletion SOP (interim operator runbook — design E)

> **INTERIM manual process** until **deletion-feature C** (in-app *Delete account & data*
> button + Clerk `user.deleted` webhook) ships — see `BACKLOG.md` → *Deletion-feature C*.
> This runbook is how the **30-day deletion promise** in the deployed Privacy Policy (§4)
> is honored **by hand** in the meantime. It is a runbook, **not** executable product code.

**Design E (lawyer-confirmed):** personal data is hard-deleted; the statutory billing/usage
record (`user_usage`) is **RETAINED IN ITS ORIGINAL FORM but FROZEN** (`deleted_at` set) —
**not** pseudonymized, **not** deleted. The freeze (PIECE 1, `deleted_at`) hides the row from
ALL product logic (`get_active_usage` / `get_or_create_usage` raise `403 account_deleted`)
while it is retained for the statutory obligation. Lawful basis: **TW Business Accounting Act
Art. 38 / GDPR Art. 6(1)(c)** — retained, restricted from any operational/marketing use,
auto-purged at 5 years. This mirrors the deployed Policy §4.

**Trigger:** a user emails `support@an-tho.com` requesting account / data deletion.
**SLA:** complete within **30 days** of the request (per the deployed Policy §4).
**Database:** Neon Postgres (**prod** branch) for a real request.
**Authority:** founder/operator with prod DB access + `fly ssh` to the `vela-ai-medical` app
(for the prod `DODO_API_KEY` and `SHARE_CREATED_BY_SALT` secrets).

Column/table names below are verbatim from `api/models/sql_models.py`. Throughout,
`:user_id` = the **Clerk user id** string (e.g. `user_2abc...`). The same value is stored in
the `user_id` columns of most tables **and** in `user_usage.clerk_user_id`.

---

## Step 0 — Identify the user (email → Clerk user_id)

There is **no reverse email→id lookup in our code** (only the forward `user_id → email` at
`server.py:1448`). Resolve via Clerk directly:

- **Clerk Dashboard** → Users → search the requester's email → copy the `user_...` id, **or**
- **Clerk API** (`CLERK_SECRET_KEY` bearer):
  ```bash
  curl -s "https://api.clerk.com/v1/users?email_address=REQUESTER_EMAIL" \
       -H "Authorization: Bearer $CLERK_SECRET_KEY" | jq '.[].id'
  ```

**Confirm identity** before acting: verify the requesting email is the user's primary email on
the Clerk record. Record the resolved `:user_id` and the requester email.

---

## Step 1 — CANCEL the Dodo subscription FIRST (billing must stop before the freeze)

A Pro user's subscription must be cancelled at the processor **before** freezing the row,
otherwise billing continues against a frozen account. Check, then cancel:

```sql
SELECT plan_type, dodo_subscription_id, dodo_customer_id
FROM user_usage WHERE clerk_user_id = :user_id;
```

If `dodo_subscription_id` is present, run the same call the app uses (`cancel_subscription`,
`server.py:1819`) with the **prod** key (`fly ssh console -a vela-ai-medical → echo $DODO_API_KEY`):

```bash
curl -X PATCH "https://live.dodopayments.com/subscriptions/<dodo_subscription_id>" \
     -H "Authorization: Bearer $DODO_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"status":"cancelled"}'
```

**VERIFY no active subscription remains** before proceeding: re-`GET` the subscription shows
`cancelled`, **or** confirm the Dodo webhook fired (`subscription_cancelled` → `plan_type`
flips to `free`, `server.py:1605-1606`). **Do not freeze until cancellation is confirmed.**

---

## Step 2 — Pre-flight: compute the `shared_query` hash + snapshot counts

`shared_query.created_by` is a salted hash — you cannot match on the raw `user_id`. Retrieve
the prod salt and compute the hash:

```bash
# prod salt (Fly secret values aren't shown by `fly secrets list`):
fly ssh console -a vela-ai-medical -C 'printenv SHARE_CREATED_BY_SALT'
```
```python
# created_by = sha256(f"{SHARE_CREATED_BY_SALT}:{user_id}")[:16]
# (verbatim from _hash_created_by(), server.py:2934-2938 — note the ':' separator)
import hashlib
salt = "<the PROD value from above>"
user_id = "user_2abc..."
created_by_hash = hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]
print(created_by_hash)
```

Baseline counts (record in the ops log):
```sql
SELECT 'chat_history'  AS tbl, count(*) FROM chat_history  WHERE user_id = :user_id
UNION ALL SELECT 'audit_logs',    count(*) FROM audit_logs    WHERE user_id = :user_id
UNION ALL SELECT 'user_feedback', count(*) FROM user_feedback WHERE user_id = :user_id
UNION ALL SELECT 'user_profile',  count(*) FROM user_profile  WHERE user_id = :user_id
UNION ALL SELECT 'bug_reports',   count(*) FROM bug_reports   WHERE user_id = :user_id
UNION ALL SELECT 'user_usage',    count(*) FROM user_usage    WHERE clerk_user_id = :user_id
UNION ALL SELECT 'api_cost_log',  count(*) FROM api_cost_log  WHERE user_id = :user_id
UNION ALL SELECT 'shared_query',  count(*) FROM shared_query  WHERE created_by = :created_by_hash;
```

---

## Step 3 — Erase + freeze + de-identify (one transaction)

```sql
BEGIN;

-- HARD DELETE (personal data, removed outright)
DELETE FROM chat_history  WHERE user_id = :user_id;   -- question + answer history
DELETE FROM audit_logs    WHERE user_id = :user_id;   -- query_content audit trail
DELETE FROM user_feedback WHERE user_id = :user_id;   -- raw query + response + edits
DELETE FROM user_profile  WHERE user_id = :user_id;   -- Pro context hash + locale (PK = user_id)
DELETE FROM bug_reports   WHERE user_id = :user_id;   -- signed-in bug reports
-- Optional: scrub anon reports the same person filed by email (keep non-identifying tech fields):
-- UPDATE bug_reports SET email = NULL WHERE email = :requester_email AND user_id IS NULL;

-- DE-IDENTIFY + RETAIN: api_cost_log user link severed, rows kept (plain nullable column)
UPDATE api_cost_log SET user_id = NULL WHERE user_id = :user_id;

-- DESIGN E FREEZE: user_usage RETAINED IN ORIGINAL FORM, frozen from all product logic.
-- NOT pseudonymized, NOT deleted. Retained under TW Business Accounting Act Art. 38 /
-- GDPR Art. 6(1)(c); restricted from operational/marketing use; auto-purged at 5 years.
UPDATE user_usage SET deleted_at = now() WHERE clerk_user_id = :user_id;

-- shared_query: sever authorship, KEEP the public page (Policy §8)
UPDATE shared_query SET created_by = NULL WHERE created_by = :created_by_hash;

-- ... run Step 4 verification, then COMMIT (or ROLLBACK if anything is off) ...
COMMIT;
```

---

## Step 4 — Verify (before COMMIT)

| table | expected post-state for the user |
|---|---|
| `chat_history`, `audit_logs`, `user_feedback`, `user_profile`, `bug_reports` | **count = 0** (hard-deleted) |
| `api_cost_log` WHERE `user_id = :user_id` | **count = 0** (now NULL; rows retained, unlinked) |
| `user_usage` WHERE `clerk_user_id = :user_id AND deleted_at IS NULL` | **count = 0** (the raw row still EXISTS in original form, but is now FROZEN — `deleted_at` set) |
| `user_usage` WHERE `clerk_user_id = :user_id` | **count = 1** (retained, original `clerk_user_id` + `dodo_*` intact — design E) |
| `shared_query` WHERE `created_by = :created_by_hash` | **count = 0** (now NULL; page retained) |

If every row matches, `COMMIT;`. Otherwise `ROLLBACK;` and investigate.

---

## Step 5 — Clerk reconciliation (closes the no-webhook orphan gap, by hand)

There is **no `/api/webhooks/clerk` `user.deleted` handler** today, so deletion must be
reconciled manually: in the **Clerk Dashboard**, confirm the user account is **deleted** (or
delete it there). This is the manual stand-in for the absent webhook until feature C ships.

---

## Step 6 — Backups / residual copies (no manual action)

Residual copies in Neon's automated backups expire on their own via the **PITR window**
(currently the Neon **Free** tier window; the Policy states copies are overwritten **within
24 hours**). No manual backup scrub is needed or possible on managed PITR.
> If the Neon plan changes such that PITR retention exceeds 24h, the Policy §4 "within 24
> hours" claim must be revisited (TECH_DEBT R5(d) — Neon-paid backup wording).

---

## Step 7 — Log the action (operator audit trail)

Record, in the ops deletion log (a private doc/sheet — **not** a user-facing table):

- date/time of request and of completion (confirm ≤ 30 days)
- requester email + resolved Clerk `:user_id` + the computed `:created_by_hash`
- per-table row counts **before** and **after**
- **Dodo cancellation confirmed** (Step 1)
- **Clerk account deletion confirmed** (Step 5)
- operator name

Then send the completion email (Appendix A).

---

## ⚠️ FLAGS / notes

**FLAG #2 — `shared_query.created_by` is a salted hash, needs the PROD salt.** Step 2 requires
the production `SHARE_CREATED_BY_SALT` (`fly ssh … printenv`). The wrong/test salt matches
**zero** rows and silently leaves authorship links intact — confirm the Step-2 count is
non-zero if the user is known to have shared anything.

**FLAG #3 — out-of-scope tables (confirmed n/a).** `anonymous_usage` (anon-keyed),
`webhook_events`, `blog_post`, `explore_page` carry no per-user identity → no action.

*(The former FLAG #1 — pseudonymize `user_usage` — is superseded by design E: the row is
retained in original form and FROZEN via `deleted_at`. No pseudonymization.)*

---

## Validating this runbook safely

Before trusting the SOP against prod, prove it on the **dev branch** with
`scripts/deletion_dryrun.py` (allow-list dev-only guard + `DELETION_DRYRUN_ALLOW=1`;
`--plan` read-trace by default; `--execute` is rollback-only — zero residue). The dry-run
asserts the design-E post-state, including that `get_active_usage(target)` raises
`AccountDeleted` (the freeze hides the retained row from product logic).

---

## Appendix A — deletion-complete email to the requester (zh-TW, lawyer-confirmed master)

> 您好，我們已收到您的資料刪除請求，並已於 30 天內完成以下處置：
> - 您的 Vela 帳號已永久關閉，所有線上查詢紀錄（Chat history）及偏好設定已完全刪除。
> - （若為付費會員）我們已同步於金流商端取消您的付費訂閱，未來不會再產生任何扣款。
> - 依據《商業會計法》第 38 條規定，您過去已發生的交易明細與金流憑證依法須加密保存 5 年
>   以供稅務稽核，期間我們不會將此資料用於任何商業用途，五年期滿後系統將自動銷毀。
> 感謝您的使用。

*(zh-TW is the lawyer-confirmed master. An English version can be added later for non-zh
requesters.)*

---

*When deletion-feature C ships, this manual SOP is superseded by
`_hard_delete_user(db, user_id, *, created_by_hash)`
(`api/services/deletion_service.py`, reused by the in-app button + the Clerk `user.deleted`
webhook). `created_by_hash` is **required and keyword-only on purpose**: FLAG #2 above means a
missing or wrong hash matches ZERO rows and silently leaves authorship links intact, so
forgetting it must be a `TypeError` at the call site rather than a quiet no-op. The helper
implements **Step 3 only** — it does NOT cancel the Dodo subscription (Step 1) and does NOT
reconcile Clerk (Step 5). Until feature C ships, this runbook is the binding process.*
