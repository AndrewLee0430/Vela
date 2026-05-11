# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-11 (post §4.6 PHASE C — Content import CLI shipped)

## Phase

Phase 0 — in progress (started 2026-04-17)

## Current Focus

§4.6 SEO Explore Pages — PHASE A + B + C shipped. Next active task = §4.6 PHASE D (Related queries + breadcrumb UI + 3 PostHog events).

## Next Up (Phase 0 remaining, Path B execution order)

1. **§ 4.6 PHASE D** — Related queries + breadcrumb UI (PRD §4.6 需求 4) + 3 PostHog events wired (explore_page_viewed / explore_cta_clicked / explore_citation_clicked).
2. **§ 4.6 PHASE E** — integration test (Google Rich Results Test / robots.txt / hreflang validator).
3. **§ 2.1 Model Provider Refactor** — 5-7 days, 9 files, largest remaining Phase 0 block.
4. **§ 3.1 User Context schema** — blocks Phase 1A.
5. **Phase 0 Retrospective** — final gate before Phase 1A; produces `docs/decisions/005-phase-0-retrospective.md` (003+004 claimed by advisor roadmap integration — see ADR 003 + ADR 004).
6. **§ 4.5 PHASE E** — DEFERRED. Execute immediately after Phase 0 末段 production deploy, NOT in main critical path. Tasks: SHARE_CREATED_BY_SALT secret setup, real anon 403 verification, LinkedIn / Twitter / Google validators, OG image production render check, PostHog 6-event verification, revocation flow on production. Detailed checklist in PRD §4.5 "Production Deploy Checklist (PHASE E.2)".

## Phase 1B preview (per advisor discussion + ADR 003+004)

Week 4-8 work queue (post Phase 0 Retrospective):

- **Week 4**: Verify 強制英文 (ADR 003) + system prompt polish — 2-2.5 days
- **Week 4-5**: DailyMed API — 2-3 days
- **Week 5-6**: 在地差異提示 Tier 1 6國 — 6-7 days
- **Week 7**: Anonymous Trial Flow polish — 2 days
- **Week 7-8**: Phase 1B integration test + polish + citation retrieval ranking evaluation — 2-3 days

Detail: see BACKLOG.md Phase 1B section.

## Active Acceptance Protocols

None active. § 2.7 Step 8 acceptance protocol completed 2026-04-30 (commits c5b3a09, 64c72f2, fa80ff9, a52bf9f, dffd015).

## Blockers

None known.

## Recently Shipped (last 7 days)

- **2026-05-11** § 4.6 PHASE C — Content import CLI (scripts/explore_cli.py: sync/list/publish/unpublish/archive/from-vela) + content/explore/ scaffolding (this commit)
- **2026-05-11** § 4.6 PHASE B — sitemap-explore.xml + hreflang missing-locale skip rule + sitemap index conversion (8fb10ca)
- **2026-05-11** [bug] Dev seed script for §4.6 PHASE A explore_page table (ce2225a)
- **2026-05-11** [bug] Next.js dev rewrites — add /explore/:slug + /static/og/explore/ proxies (d324389)
- **2026-05-11** § 4.6 PHASE A — ExplorePage schema + /explore/{slug} routing reusing §4.5 renderer (bc171a1)
- **2026-05-08** [docs] PRD §2.10.6 evidence tier classification + BACKLOG dogfooding follow-ups (9834d85)
- **2026-05-08** [bug] CitationPanel — remove credibility 5-star UI per advisor dogfooding feedback (211d9f7)
- **2026-05-08** § 4.5 PHASE E.1 — Documentation closeout: PRD status marker 🟡 IMPL COMPLETE / DEPLOY PENDING + Production Deploy Checklist subsection + STATE/BACKLOG sync (f495a41)
- **2026-05-08** § 4.5 PHASE D — Share clauses (en) added to /terms + /privacy + Navbar dropdown menu label "Settings" → "Manage shares" (16 locales) + PRD inline note + P2 TECH_DEBT for legal-page i18n retrofit (ad506db)
- **2026-05-08** § 4.5 PHASE C — Settings 「我的分享」 tab — /settings page + tab nav + MyShares list/revoke + Navbar dropdown entry + 16-locale i18n (6f7a154)
- **2026-05-07** PRD §2.10 source strategy + BACKLOG dogfooding/source-weight sub-tasks (92dbe9b)
- **2026-05-07** BACKLOG WHO API integration entry → Phase 1C (4fe0d7b)
- **2026-05-07** § 4.5 UX polish 3/3 — PRD inline notes + TECH_DEBT entries (768dc0b)
- **2026-05-07** § 4.5 UX polish 2.5 — Navbar ShareButton tone-down + i18n 16-locale rollout (b378659)
- **2026-05-07** § 4.5 UX polish 2/3 — ShareButton to Navbar via ShareContext + QR removal (ca571ce)
- **2026-05-07** § 4.5 UX polish 1/3 — public page visual alignment to main site (a5da1c5)
- **2026-05-07** [bug] Verify short disclaimer i18n alignment (30bd0b5)
- **2026-05-07** Next.js dev rewrites for /q/* + /api/share/* + /static/og/* (e042efc)
- **2026-05-06** § 4.5 PHASE B — Share API + PHIDetector mode='share' + ShareButton/ShareModal + 4 mount surfaces + /?from_share handler (f04068d)
- **2026-05-05** § 4.5 PHASE A — Public Query Page renderer + SharedQuery DB migration (ef0d375)

For older work see ARCHIVE.md.

## Pointer to Other Docs

- **Active rules + workflow**: CLAUDE.md
- **Open future tasks**: BACKLOG.md
- **Completed work log**: ARCHIVE.md
- **Tech debt entries**: TECH_DEBT.md
- **Spec**: docs/PRD.md (v1.3)
- **Architecture**: docs/architecture.md
- **ADRs**: docs/decisions/
