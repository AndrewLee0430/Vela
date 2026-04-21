-- Migration: Add anonymous_usage table for Decision 001 L0 anonymous tier
-- Date: 2026-04-21
-- Run: psql $DATABASE_URL -f migrations/003_add_anonymous_usage.sql

CREATE TABLE IF NOT EXISTS anonymous_usage (
    anon_id VARCHAR(64) PRIMARY KEY,
    credits_used_today INTEGER NOT NULL DEFAULT 0,
    last_reset_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anon_usage_last_active ON anonymous_usage(last_active_at);
