# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-14 (Next Up reorder — §3.1 audit promoted to active, §4.6 PHASE E marked deferred-parallel)

## Phase

Phase 0 — in progress (started 2026-04-17)

## Current Focus

§3.1 User Context Schema audit — Phase 0 closeout → Phase 1A bridge task. Audit-first per CLAUDE.md #2 (verify codebase before acting on spec assumptions). Blocks Phase 1A. Audit output → PRD §3.1 修訂 + phasing plan + ADR 007 (if needed); audit report stays in chat (precedent: §2.1 audit, no repo artifact).

Last shipped: §2.1 Model Provider Refactor (2026-05-13) — see Completed section below + ARCHIVE.md.

## Next Up (Phase 0 closeout + Phase 1A bridge, Path B execution order)

1. **§ 3.1 User Context Schema audit** — ACTIVE. Audit-only first pass (no production code); produces PRD §3.1 修訂建議 + draft phasing plan. Schema spec: localStorage key `vela_user_context` (workplace / role / work_language / locale / onboarding_completed / version) + Pro-only server table `user_profile` storing SHA-256(context)[:16] hash + locale. Blocks Phase 1A.
2. **§ 4.6 PHASE E** — DEFERRED-PARALLEL: wall-clock gated until production deploy + 4-week GSC indexing window. Pre-deploy work (Google Rich Results Test / robots.txt / hreflang validator) can run locally anytime; post-deploy work (4-week GSC monitoring) requires production deploy first. Includes follow-up: build /explore index page (breadcrumb 'Explore' link gap from PHASE D). Can run in parallel with §3.1 + §3.2 engineering.
3. **§ 3.2 Onboarding 三問改版** — depends on §3.1 schema landing. Frontend 3-step flow (workplace → role → work_language) + 隱私聲明卡, writes to `vela_user_context` localStorage. Existing OnboardingOverlay (4-step SVG mask tour) is an independent component and unaffected — see §3.1 audit checklist C for naming boundary check.
4. **Phase 0 Retrospective** — final gate before Phase 1A bulk. ADR number TBD (005 taken by 2.1 Groq decision, 006 taken by Phase 1B activation checklist, 007 reserved if §3.1 audit produces a decision-worthy outcome).
5. **Production deploy** — Phase 0 末段 production push. Triggers §4.5 PHASE E execution window + §4.6 PHASE E 4-week GSC monitoring window.
6. **§ 4.5 PHASE E** — DEFERRED to post-deploy, NOT in main critical path. Tasks: SHARE_CREATED_BY_SALT secret setup, real anon 403 verification, LinkedIn / Twitter / Google validators, OG image production render check, PostHog 6-event verification, revocation flow on production. Detailed checklist in PRD §4.5 "Production Deploy Checklist (PHASE E.2)".

## Completed: §2.1 Model Provider Refactor (2026-05-13)

✅ **COMPLETE** — 7 commits, 1 day, 4-5d v1.4 estimate hit.

- 9/9 backend files migrated through Provider abstraction
- 21/21 unit tests green (tests/providers/test_factory_swap.py)
- Live smoke verified all 3 production surfaces in PHASE D
  (Research SSE 519 chunks 23s / Verify 7.9s / Explain 20.6s)
- Phase 0 ship state: 100% OpenAI defaults preserved
- Groq framework-ready; activation procedure in ADR 006
- §2.7 acceptance baseline (gpt-4.1 ExplainJudge) preserved

See ARCHIVE.md 2026-05-13 entry for full commit list + acceptance.

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

- **2026-05-12** § 4.6 PHASE D — Breadcrumb + Category listing (/explore/category/{category}) + Related queries (3-tier hreflang/category) + 3 PostHog events (explore_page_visited / explore_to_query_clicked / explore_related_clicked) wired inline in Jinja2 with window.posthog guard (PHASE E follow-up: posthog init for public pages) (SHA pending)
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
