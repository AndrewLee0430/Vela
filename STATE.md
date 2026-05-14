# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-14 (Next Up retighten — Phase 0 production deploy promoted to #1 per PRD v1.3 ship gate sequence; §3.1 moved to Phase 1A entry; Retrospective moved post-verification per session decision)

## Phase

Phase 0 — code-complete, awaiting production deploy (started 2026-04-17)

## Current Focus

Phase 0 production deploy + post-deploy verification + Phase 0 Retrospective. Ship gate sequence per PRD v1.3 §二 NOTE: `§2.7 → §4.5 → §4.6 → [DEPLOY] → §4.5/§4.6 PHASE E verification → Phase 0 Retrospective`.

§3.1 audit completed 2026-05-14 (report in chat); §3.1 PRD v1.5 revision + implementation deferred to Phase 1A entry per PRD §3.1 marker (Phase 1A scope, not Phase 0 closeout).

Last shipped: §2.1 Model Provider Refactor (2026-05-13) — see Completed section below + ARCHIVE.md.

## Next Up (Phase 0 production ship → Phase 1A entry, retightened to PRD v1.3 spec)

1. **Production deploy** — ACTIVE. Pre-deploy checklist generation pending (separate prompt). Phase 0 code-complete state: §2.0 / §2.1 / §2.2 / §2.3 / §2.4 / §2.5 / §2.6 / §2.7 / §2.8 / §2.9 + §4.5 PHASE A–D + §4.6 PHASE A–D all shipped.
2. **§4.5 PHASE E.2 + §4.6 PHASE E post-deploy verification** — immediate post-deploy. §4.5: PRD §4.5 "Production Deploy Checklist PHASE E.2" (real anon 403 + LinkedIn / Twitter / Google validators + OG image production render + PostHog 6-event verification + revocation flow). §4.6: Google Rich Results Test + robots.txt + hreflang validator + `/explore` index page build (breadcrumb 'Explore' link gap follow-up). Estimated 0.5–1d.
3. **§4.6 PHASE E 4-week GSC indexing window** — passive, parallel-running with #4 and #5. Monitored weekly. Starts on deploy.
4. **Phase 0 Retrospective** — write `docs/retrospectives/phase-0-2026-05.md` covering 2026-04-17 → deploy date period. MUST include deploy process lessons + §4.5/§4.6 PHASE E verification findings (reason this is post-verification, not pre-deploy). NOT ADR — ADR 007 reserved for actual architecture decisions. Estimated 0.5d.
5. **§3.1 PRD revision (v1.4 → v1.5)** — can parallel with #4. Docs commit only. Integrates 10 revisions from §3.1 audit Section H + decisions on Open Questions (E1–E4, F1, G3, G4, G7). No ADR. Estimated 0.5d.
6. **§3.1 implementation + §3.2 Onboarding Wizard (Phase 1A start)** — sequence: PHASE B (backend) → PHASE C (frontend hook + LangContext write-through) → PHASE D (`OnboardingWizard.tsx` = §3.2, distinct from existing `OnboardingOverlay.tsx`) → PHASE E (Settings §4.3 tab + role_category + §3.3 basic examples). Estimated 4d.

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
