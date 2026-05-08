# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-08 (post §4.5 PHASE E.1 closeout — implementation complete, deploy pending)

## Phase

Phase 0 — in progress (started 2026-04-17)

## Current Focus

None active. §4.5 Share Answer implementation (PHASE A-D) shipped; PHASE E (acceptance + validators) deferred until production deploy. Next active task = §4.6 SEO Explore Pages.

## Next Up (Phase 0 remaining, Path B execution order)

1. **§ 4.6 SEO Explore Pages** — PRD v1.3 Phase 0 末段, shares §4.5 Public Query Page renderer (SSR + OG + JSON-LD pipeline).
2. **§ 2.1 Model Provider Refactor** — 5-7 days, 9 files, largest remaining Phase 0 block.
3. **§ 3.1 User Context schema** — blocks Phase 1A.
4. **Phase 0 Retrospective** — final gate before Phase 1A; produces `docs/decisions/005-phase-0-retrospective.md` (003+004 claimed by advisor roadmap integration — see ADR 003 + ADR 004).
5. **§ 4.5 PHASE E** — DEFERRED. Execute immediately after Phase 0 末段 production deploy, NOT in main critical path. Tasks: SHARE_CREATED_BY_SALT secret setup, real anon 403 verification, LinkedIn / Twitter / Google validators, OG image production render check, PostHog 6-event verification, revocation flow on production. Detailed checklist in PRD §4.5 "Production Deploy Checklist (PHASE E.2)".

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

- **2026-05-08** § 4.5 PHASE E.1 — Documentation closeout: PRD status marker 🟡 IMPL COMPLETE / DEPLOY PENDING + Production Deploy Checklist subsection + STATE/BACKLOG sync (this commit)
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
