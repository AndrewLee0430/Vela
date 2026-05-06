-- Migration: Add shared_query table for PRD § 4.5 Share Answer
-- Date: 2026-05-06
-- Run: psql $DATABASE_URL -f migrations/004_add_shared_query.sql
--
-- PRD § 4.5. Snapshot semantics — does NOT participate in 180-day
-- ChatHistory cleanup. query_text / answer_text / citations are copied
-- into this table at share-creation time so a share survives parent
-- ChatHistory expiry.

CREATE TABLE IF NOT EXISTS shared_query (
    share_id        TEXT PRIMARY KEY,
    query_id        TEXT,                                  -- nullable; PHASE B uses for idempotency
    query_text      TEXT NOT NULL,
    answer_text     TEXT NOT NULL,
    citations       JSONB NOT NULL,
    created_by      TEXT,                                  -- sha256(salt + user_id)[:16] in PHASE B
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_public       BOOLEAN NOT NULL DEFAULT TRUE,
    view_count      INTEGER NOT NULL DEFAULT 0,
    last_viewed_at  TIMESTAMPTZ,
    flagged         BOOLEAN NOT NULL DEFAULT FALSE,
    locale          TEXT                                   -- renderer i18n hint
);

CREATE INDEX IF NOT EXISTS idx_shared_query_created_by ON shared_query(created_by);
CREATE INDEX IF NOT EXISTS idx_shared_query_flagged ON shared_query(flagged);

-- Idempotency: same user can only share the same source query once.
-- Partial index because query_id is nullable in PHASE A; PHASE B writes
-- query_id at /api/share/create time and relies on this constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_shared_query_query_creator
    ON shared_query(query_id, created_by)
    WHERE query_id IS NOT NULL;
