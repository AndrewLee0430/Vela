-- Migration: Add Dodo Payments fields + free plan daily reset
-- Date: 2026-03-30
-- Run: psql $DATABASE_URL -f migrations/002_add_dodo_and_free_reset.sql

ALTER TABLE user_usage ADD COLUMN IF NOT EXISTS dodo_customer_id VARCHAR;
ALTER TABLE user_usage ADD COLUMN IF NOT EXISTS dodo_subscription_id VARCHAR;
ALTER TABLE user_usage ADD COLUMN IF NOT EXISTS last_free_reset DATE;
