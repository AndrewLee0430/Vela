-- Migration: Add blog_post table for the Vela Blog feature (PHASE A)
-- Date: 2026-05-25
-- Run: psql $DATABASE_URL -f migrations/007_add_blog_post.sql
--
-- Mirrors the §4.6 Explore pattern (migrations/005_add_explore_page.sql):
-- DB-backed markdown content rendered server-side via FastAPI Jinja2;
-- content updates flow through scripts/blog_cli.py (PHASE B) — never
-- requires a Next.js redeploy. Composite PK (slug, locale) allows the
-- same post to ship in multiple languages (MVP: en + zh-TW only).
--
-- PHASE A scope: schema + single-post route + BlogPosting+FAQPage
-- JSON-LD. List page, sitemap, content CLI, and Pillow cover image
-- generation come in PHASES B-C.
--
-- `faqs` and `tags` are JSONB so Postgres can index/query them later;
-- in dev sqlite they round-trip as TEXT (blog_renderer normalizes the
-- str → list on read).

CREATE TABLE IF NOT EXISTS blog_post (
    slug             TEXT NOT NULL,
    locale           TEXT NOT NULL,
    title            TEXT NOT NULL,
    summary          TEXT,
    body_markdown    TEXT NOT NULL,
    theme            TEXT NOT NULL DEFAULT 'strategy',
    cover_image      TEXT,
    faqs             JSONB,
    tags             JSONB,
    status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
    published_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (slug, locale)
);

CREATE INDEX IF NOT EXISTS idx_blog_status ON blog_post(status);
