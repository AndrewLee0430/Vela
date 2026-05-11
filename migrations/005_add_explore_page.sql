-- Migration: Add explore_page table for PRD § 4.6 SEO Explore Pages
-- Date: 2026-05-08
-- Run: psql $DATABASE_URL -f migrations/005_add_explore_page.sql
--
-- PRD § 4.6. Team-curated public pages at /explore/{slug}. Reuses the
-- § 4.5 PHASE A public-page renderer infrastructure. Composite PK
-- (slug, locale) allows the same slug to ship in multiple languages
-- linked via hreflang_group.

CREATE TABLE IF NOT EXISTS explore_page (
    slug              TEXT NOT NULL,
    locale            TEXT NOT NULL,
    query_text        TEXT NOT NULL,
    answer_text       TEXT NOT NULL,
    citations         JSONB NOT NULL,
    meta_title        TEXT NOT NULL,
    meta_description  TEXT NOT NULL,
    category          TEXT,
    hreflang_group    TEXT,
    status            TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    published_at      TIMESTAMPTZ,
    last_updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    view_count        INT NOT NULL DEFAULT 0,
    PRIMARY KEY (slug, locale)
);

CREATE INDEX IF NOT EXISTS idx_explore_status ON explore_page(status);
CREATE INDEX IF NOT EXISTS idx_explore_hreflang ON explore_page(hreflang_group);
CREATE INDEX IF NOT EXISTS idx_explore_category ON explore_page(category);
