-- Migration: Add user_usage.deleted_at FREEZE marker (account-deletion design E)
-- Date: 2026-06-12
-- Run: psql $DATABASE_URL -f migrations/008_add_user_usage_deleted_at.sql
--
-- Account-deletion design E (manual-deletion SOP / deletion-feature C):
-- on a deletion request, user_usage is RETAINED for the statutory 5-year
-- billing/audit obligation but FROZEN from all product logic. `deleted_at`
-- is the freeze marker: NULL = active, set = frozen.
--
-- Every product-gating read of user_usage excludes frozen rows
-- (get_active_usage / get_or_create_usage raise 403 account_deleted);
-- billing/audit WRITES (payment webhooks) keep updating the retained row.
--
-- Additive + nullable: all existing rows default to NULL = active, so this
-- is a zero-behavior-change migration until a row is explicitly frozen.
-- No backfill needed. Apply to the DEV branch first, then prod.

ALTER TABLE user_usage ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
