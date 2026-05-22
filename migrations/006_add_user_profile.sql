-- Migration: Add user_profile table for PRD § 3.1 User Context (v1.6)
-- Date: 2026-05-22
-- Run: psql $DATABASE_URL -f migrations/006_add_user_profile.sql
--
-- PRD § 3.1 v1.6. Pro-only server-side hash store for cross-device
-- preference verification. Stores ONLY user_context_hash + locale; the
-- raw workplace/role/work_language fields stay in localStorage and
-- never leave the device (Privacy-first, §0.3).
--
-- POST /api/user/context/hash UPSERTs into this table, bumping
-- updated_at as "last verified" semantic per E3. GET reads back hash
-- + locale + updated_at for the dual-trigger restore flow (§4.3 需求 5).
--
-- VARCHAR widths per spec; the hash is the leading 16 chars of a
-- client-computed SHA-256 over (workplace, role, work_language)
-- joined by '|' with nulls filtered.

CREATE TABLE IF NOT EXISTS user_profile (
    user_id            VARCHAR(64)  PRIMARY KEY,
    user_context_hash  VARCHAR(16)  NOT NULL,
    locale             VARCHAR(8),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
