# ARCHIVE.md — Vela Completed Work Log

Chronological log of shipped work. Newest first.

**Format**: `YYYY-MM-DD [TAG] Title — one-line summary (commit SHA)`

**Tags**:
- `[PRD §X.Y]` — feature work tied to PRD section
- `[bug]` — production bug fix
- `[tech-debt]` — pre-existing gap closure
- `[refactor]` — code health
- `[docs]` — documentation
- `[Phase 1A polish]` — pre-shipped Phase 1A items
- `[acceptance]` — acceptance protocol completion

When new entries are added: keep one-liner format, no detail. For full context, consult the commit message.

---

## 2026-05-11

- `[PRD §4.6]` PHASE B — sitemap-explore.xml + hreflang missing-locale skip rule. New api/services/sitemap_explore.py (sitemaps.org-compliant XML generator with xhtml hreflang alternates per published sibling, draft/archived skipped). /sitemap-explore.xml FastAPI route registered (no rate limit, crawler-friendly). public/sitemap.xml converted from flat urlset to sitemapindex referencing public/sitemap-main.xml (original 6 static routes) + sitemap-explore.xml (dynamic). next.config.ts dev rewrites add /sitemap-explore.xml → backend. Sitemap <loc> uses ?locale={locale} uniformly so each <url> has unique loc aligned with xhtml:link href. scripts/smoke_explore_phase_b.py — 23 assertions PASS covering well-formed XML, namespaces, hreflang published-pair vs draft-sibling, HTML hreflang regression. robots.txt confirmed healthy (no /explore disallow, Sitemap directive intact).
- `[bug]` Dev seed script for §4.6 PHASE A — scripts/seed_explore_dev.py connects to DATABASE_URL (Neon Postgres) and idempotently UPSERTs 2 sample rows (en + zh-TW in hreflang_group='metformin-renal'). Required because the PHASE A smoke test seeded only its own temp SQLite, so live dev environment had no data. (ce2225a)
- `[bug]` Next.js dev rewrites — add /explore/:slug + /static/og/explore/ proxies for §4.6 PHASE A live testing. (d324389)
- `[PRD §4.6]` PHASE A — ExplorePage schema + /explore/{slug} routing (reuses §4.5 renderer). New migrations/005_add_explore_page.sql + ExplorePage SQLAlchemy model with composite PK (slug, locale) + api/services/explore_renderer.py reusing share_renderer helpers (parse_research_sections / _augment_citations / _markdown_to_html / _MARKER_BORDER_COLORS) + api/templates/explore_base.jinja2 + q_explore.jinja2 (team-content semantics: no "shared by" framing, breadcrumb + related-queries slots for PHASE D, hreflang siblings in <head>) + api/i18n/explore_strings.py (16 locales, en + zh-TW first-class) + /explore/{slug} route registered before Next.js catch-all with in-handler rate limit (60/min). 23 smoke assertions PASS. (bc171a1)

## 2026-05-08

- `[docs]` PRD §2.10.6 evidence tier classification (within-source 5-tier model — international guideline / systematic review / RCT / observational / survey) + BACKLOG dogfooding follow-ups (DailyMed entry sub-task / Citation ranking 5th test / Phase 1C Guideline ingestion entry) + TECH_DEBT [P3] components/Untitled stale backup file (9834d85)
- `[bug]` CitationPanel — remove credibility 5-star UI per external advisor dogfooding feedback (2026-05-08). 5-star + "Credibility:" label removed from frontend CitationPanel + server-side share_renderer.py / q_public.jinja2 / q_base.jinja2. Backend Citation.credibility field preserved for Phase 1B evidence-tier classification repurpose. (211d9f7)
- `[PRD §4.5]` PHASE E.1 — Documentation closeout (pre-production-deploy): PRD §4.5 status marker bumped to 🟡 IMPLEMENTATION COMPLETE — DEPLOY PENDING (2026-05-08); new "Production Deploy Checklist (PHASE E.2)" subsection (14 checkboxes across 3 groups); STATE.md / BACKLOG.md sync. PHASE E.2 deferred to post-production-deploy. (f495a41)
- `[PRD §4.5]` PHASE D — Share clauses (en-only) added to /terms § 8 Public Sharing + /privacy § 7 Public Sharing per 需求 9 spec. Navbar gear-dropdown menu item label "Settings / 設定" → "Manage shares / 管理分享" (16-locale rename in `utils/i18n-share.ts`: `settingsNavLink` → `navbarManageSharesMenuItem`). PRD §4.5 (2026-05-08 修訂) inline note documenting the menu label decision. New P2 TECH_DEBT entry: /terms + /privacy en-only — 16-locale i18n retrofit pending before non-en GTM expansion. "Last updated" bumped to 2026-05-08 in both legal pages.
- `[PRD §4.5]` PHASE C — Settings 「我的分享」 tab — new `pages/settings.tsx` + tab nav scaffolding (extensible) + `components/MySharesTab.tsx` (list / copy / revoke with optimistic UI / PostHog events) + Navbar gear-dropdown Settings entry + 7 new i18n keys × 16 locales. Pure frontend; consumes existing PHASE B endpoints. Intl.RelativeTimeFormat for time-ago (no custom i18n). (6f7a154)

---

## 2026-05-07

- `[PRD §4.5]` UX polish 3/3 — PRD §4.5 inline (2026-05-06 修訂) notes + TECH_DEBT entries (Arial body font / native-speaker review / cost_report_7d / dotenv loader); priority-tier ladder extended with P3 (768dc0b)
- `[PRD §4.5]` UX polish 2.5 — Navbar ShareButton color tone-down (coral → neutral) + i18n full 16-locale rollout (b378659)
- `[PRD §4.5]` UX polish 2/3 — ShareButton to Navbar via new ShareContext + ShareModal QR removal + qrcode.react dep dropped + toast color brand-aligned (ca571ce)
- `[PRD §4.5]` UX polish 1/3 — public page visual alignment to main site (dark gradient, evidence cards, hand-rolled CitationPanel HTML, coral CTA, dual disclaimer); parseResearchSections() Python port; markdown==3.6 dep added (a5da1c5)
- `[bug]` Verify short disclaimer missing i18n — backend `get_verify_disclaimer()` helper + 16-locale dict + handler wires localized string into all 3 VerifyResponse return points (30bd0b5)
- `[PRD §4.5]` Dev quality-of-life — Next.js rewrites for /q/* and /api/share/* (e042efc)
- `[docs]` BACKLOG WHO API integration entry → Phase 1C (4fe0d7b)
- `[docs]` PRD §2.10 source strategy + BACKLOG dogfooding/source-weight sub-tasks (92dbe9b)

---

## 2026-05-06

- `[PRD §4.5]` PHASE B Share API + Modal + sensitive detection + history button — 3 endpoints (create/revoke/list) + track-visit, PHIDetector mode='share' (NHI + name+age combos for zh-TW/en/ja), ShareButton/ShareModal mounted on research/verify/explain/history, /?from_share handler in pages/index.tsx, qrcode.react dep added, SHARE_CREATED_BY_SALT env var introduced

---

## 2026-04-30

- `[docs]` Doc reorganization Stage 2 structural — STATE.md / BACKLOG.md / ARCHIVE.md / TECH_DEBT.md split out from CLAUDE.md (this commit)
- `[docs]` Architecture extract from CLAUDE.md → docs/architecture.md (59002d1)
- `[docs]` Drift sync post § 2.7 結案 — PRD v1.2→v1.3, Phase 0 remaining (3fdeddc)
- `[docs]` § 2.7 結案 + M06 in Phase 0 status (dffd015)
- `[bug]` M06 ja schema_validation_failed — null value coercion via Layer 4 cleaner (a52bf9f)
- `[PRD §2.7 Step 8]` ExplainJudge integration into golden_dataset (Plan B-Modified) + 5 acceptance fixes + E29-E33 — 95.3% pass, hard floor 100% (fa80ff9)
- `[tech-debt]` TEST_MODE bypass for rate limit middleware — closes pre-existing infra gap surfaced during § 2.7 Step 8 (64c72f2)
- `[PRD §2.7 Step 7]` ExplainJudge class + explain_judge.md prompt — 7-dim structured evaluator, gpt-4.1, acceptance-only (c5b3a09)
- `[PRD §2.7 Step 4 follow-up]` Body language vs disclaimer language drift — resolved via Bug C fix (explain_system.md v3→v4 body_language_correct dim, integrated in Step 8 acceptance)
- `[PRD §2.7 Step 4 follow-up]` Risk tier conservative skew evaluation — Step 8 acceptance found no systematic bias (yellow >70% trigger condition not met)

## 2026-04-29

- `[PRD §2.7 Path 1 phase 2]` Banner + tooltip Bug 2 fix for limited-evidence sources (daaf4be)
- `[bug]` Path 1 RAG citation hallucination — 3-layer defense + Bug X1/X2/X3 fixes (bebf099)
- `[PRD §2.7 Step 4 follow-up]` Generic error UX — 6 error codes (empty_input, no_values_in_input, input_too_long, openai_api_error, schema_validation_failed, generic) (a8eb6e8)

## 2026-04-28

- `[PRD]` Bump v1.2 → v1.3 — added § 4.5 Share Answer + § 4.6 SEO Explore (06a9605)

## 2026-04-27

- `[PRD §2.7 Steps 1-6]` Explain 臨床推理強化 — 19 commits cd697d1..dd128e2 (production deploy)
- `[Phase 1A polish]` Verify completion-event telemetry — verify_completed/verify_failed events with severity_distribution + interaction_count (dd128e2)
- `[Phase 1A polish]` Research completion-event telemetry — research_completed/research_failed events with citation_count + evidence_distribution + used_fallback (6a53dfc)
- `[PRD §2.7 Step 6]` Explain completion-event telemetry — explain_completed/explain_failed events (e63c231)

## 2026-04-25

- `[docs]` CLAUDE.md align with FEATURE_AUDIT.md 2026-04-25 reality (05aa2bb)
- `[docs]` Refresh FEATURE_AUDIT.md to 2026-04-25 reality (389c05c)

## 2026-04-22

- `[PRD §2.8]` Anonymous Trial Flow Round 3 — AnonymousUpgradeCTA + tier super-property + alias on first signIn (24b1d79)
- `[PRD §2.8]` Round 2B — frontend anonymous dispatch for Research + Verify (a8877e9)
- `[PRD §2.8]` Round 2A — Clerk localhost sign-in pages + Navbar refactor (cc1e1c7)
- `[PRD §2.8]` Round 1 — backend infrastructure + integration (7a8c5a8)
- **Discovered Gap G1 resolved**: Anonymous Trial Flow gap (Landing Page promised "No account required to try" but Try-it-free redirected to Clerk sign-in). Decision Record `docs/decisions/001-anonymous-trial-flow.md`.

## 2026-04-21

- `[PRD §2.5 polish]` Landing Page i18n 16-language expansion (a22ce9f)
- `[docs]` Record Landing Page polish tech debt — placeholder i18n + Privacy simplification (1101dcc)

## 2026-04-20

- `[PRD §2.4]` Bug 回報浮動按鈕 — BugReportButton FAB + /api/bug-report + PHI cleaning + rate limit 5/hour, production verified user_id=user_3BQM... (380d11f, dfdef25, 11270a9)
- `[PRD §2.9]` Verify 輸出語言對齊 user locale — response_language variable + verify_system.md v2.1 + 7 languages i18n + UX polish + Chinese variant handling spread (b2250ca, ee055d4, f2533f4, c621e3b, e718ec8)

## 2026-04-19

- `[PRD §2.2 + §2.3]` Wire query_id to analytics + citation/feedback tracking (04aae40)
- `[PRD §2.2]` Emit query_id as first SSE event across research/verify/explain (1737683)

## 2026-04-18

- `[docs]` ADR 001 — Anonymous Trial Flow decision record (f7fd8aa, 1e22f0a)
- `[docs]` Convert PRD v1.2 to markdown (539586d)
- `[PRD §2.0]` PostHog analytics wrapper — utils/analytics.ts + AnalyticsAuthBridge, sign-out reset (dd210b9, 3876239)

## 2026-04-17

- `[PRD §2.5]` Landing Page SEO fix — isLoaded gate removed, JSON-LD in place, og-image v1.1 (e00d8ac)
- **Phase 0 started.**

---

For pre-2026-04-17 work (Phase pre-0 / project init / Pre-PRD-v1.2 era), consult `git log --before=2026-04-17` and the original commit messages.
