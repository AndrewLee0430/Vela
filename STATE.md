# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-20 (§3.1 PRD v1.6 patch shipped — 603917f, ahead of PHASE B)

## Phase

Phase 0 — production shipped 2026-05-19 (started 2026-04-17, deploy commit a63b304, v164)

## Current Focus

Phase 0 production deployed 2026-05-19 (v164, commit a63b304). All 🔴 CRITICAL ship gates passed: server health, vector store (690 docs), Clerk auth, anon share 403, §2.7 Explain canonical (K=6.8 case), §2.8 anon trial quota (6/8 modal), §2.9 multilingual response, §2.0 PostHog events. One 🟡 HIGH fix-forward landed: OG image URL/path mismatch in StaticFiles mount (commit a63b304).

Next focus: Phase 1A §3.1 implementation (PHASE B backend → C frontend → D OnboardingWizard → E Settings). §3.1 PRD v1.5 revision shipped 2026-05-20 (bf446e3) integrating all 8 audit decisions + 5 findings + self-repair rule. §4.6 PHASE E 4-week GSC indexing window running in background.

Last shipped: §2.1 Model Provider Refactor (2026-05-13) + Phase 0 production deploy (2026-05-19).

## Next Up (Phase 1A start)

1. **§4.6 PHASE E 4-week GSC indexing window** — passive, monitored weekly. Started 2026-05-19 with production deploy. `/explore` index page follow-up can land during this window.
2. **§3.1 implementation + §3.2 Onboarding Wizard (Phase 1A start)** — sequence: PHASE B (backend schema + migration 006 + endpoints) → PHASE C (frontend hook + LangContext write-through + analytics.ts writer) → PHASE D (`OnboardingWizard.tsx` = §3.2, distinct from existing `OnboardingOverlay.tsx`) → PHASE E (Settings §4.3 tab including 需求 5 dual-trigger restore + role_category + §3.3 basic examples). Spec reference: PRD §3.1 v1.5 (bf446e3). Estimated 4d.
3. **Phase 0 Retrospective integration into Phase 1A planning** — retrospective.md complete (de4e7d4); surface findings (Clerk publicMetadata dormant, user.deleted webhook gap, OG image ephemeral fs, 5 dogfooding nuance issues) during #2 implementation. No standalone deliverable, embedded in PHASE B/C/D/E work.

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

- **2026-05-20** [docs] PRD §3.1 v1.5 → v1.6 — POST 403 pro_required (overrides E1) + POST body hash-only (raw never leaves device). Ahead of §3.1 PHASE B. (603917f)
- **2026-05-20** [docs] PRD §3.1 v1.5 — User Context Schema audit integration (bf446e3). Integrates 8 audit decisions (E1–E4, F1, G3, G4, G7) + 5 findings (A, F1, G2, G3, G6) + self-repair derivation rule into §3.1 spec. Cross-section additions: §2.0.2 reciprocity pointer, §3.2 Step 3 dual-write spec, §4.3 需求 5 dual-trigger restore. +100/-13 lines, scope-tight to §3.1 ecosystem.
- **2026-05-19** [docs] CLAUDE.md Rule 17 (test intent) + Rule 18 (fail loud) appended (27572c8)
- **2026-05-19** [docs] TECH_DEBT — Research WARN pattern from 2026-05-19 golden eval (69e2cd0)
- **2026-05-19** [docs] STATE.md drift fix — Next Up #1 removed, #2-5 renumbered (bd7b22f)
- **2026-05-19** [docs] TECH_DEBT + BACKLOG — Phase 0 deploy retrospective follow-ups (a155c4a)
- **2026-05-19** [docs] PRD §4.5 + §4.6 status → ✅ SHIPPED (3c48433)
- **2026-05-19** [docs] docs/retrospectives/phase-0-2026-05.md — 346 lines (de4e7d4)
- **2026-05-19** [docs] ARCHIVE.md Phase 0 entries + 2026-05-14 audit-planning (07b2c0a)
- **2026-05-19** [docs] STATE.md Phase 0 production shipped marker (49309eb)
- **2026-05-19** [deploy] Phase 0 production deploy completed — v164 from a63b304 ✅ SHIPPED
- **2026-05-19** [fix 4.5] OG image URL/path mismatch in StaticFiles mount (a63b304)

For older work see ARCHIVE.md.

## Pointer to Other Docs

- **Active rules + workflow**: CLAUDE.md
- **Open future tasks**: BACKLOG.md
- **Completed work log**: ARCHIVE.md
- **Tech debt entries**: TECH_DEBT.md
- **Spec**: docs/PRD.md (v1.3)
- **Architecture**: docs/architecture.md
- **ADRs**: docs/decisions/
