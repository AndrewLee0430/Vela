# STATE.md — Vela Current Development Focus

**Last updated**: 2026-04-30 (post § 2.7 Step 8 結案 + doc reorg)

## Phase

Phase 0 — in progress (started 2026-04-17)

## Current Focus

None active. Awaiting next-task selection per Path B execution order (user-confirmed 2026-04-30: §4.5 → §4.6 → §2.1 → Phase 0 Retrospective).

## Next Up (Phase 0 remaining, Path B execution order)

1. **§ 4.5 Share Answer 公開連結** — PRD v1.3 Phase 0 末段. User-triggered anonymous public URL for a single query result. Aligns GTM_V1 § 5.4 L3 word-of-mouth.
2. **§ 4.6 SEO Explore Pages** — PRD v1.3 Phase 0 末段, shares §4.5 Public Query Page renderer (SSR + OG + JSON-LD pipeline).
3. **§ 2.1 Model Provider Refactor** — 5-7 days, 9 files, largest remaining Phase 0 block.
4. **§ 3.1 User Context schema** — blocks Phase 1A.
5. **Phase 0 Retrospective** — final gate before Phase 1A; produces `docs/decisions/003-phase-0-retrospective.md` (002 claimed by doc reorg ADR — see docs/decisions/002-doc-reorganization.md).

## Active Acceptance Protocols

None active. § 2.7 Step 8 acceptance protocol completed 2026-04-30 (commits c5b3a09, 64c72f2, fa80ff9, a52bf9f, dffd015).

## Blockers

None known.

## Recently Shipped (last 7 days)

- **2026-04-30** Doc reorganization Stage 2 — drift sync (3fdeddc), architecture extract (59002d1), structural reorg (this commit)
- **2026-04-30** § 2.7 Steps 7-8 acceptance protocol + M06 fix + docs sync (c5b3a09 ExplainJudge class, 64c72f2 TEST_MODE rate-limit bypass, fa80ff9 acceptance integration, a52bf9f M06, dffd015 docs)
- **2026-04-29** Path 1 RAG defense (3-layer + UX banner + tooltip Bug X1/X2/X3, bebf099, daaf4be)
- **2026-04-29** Generic error UX 6-codes (a8eb6e8)
- **2026-04-28** PRD bump v1.2 → v1.3 — added § 4.5 Share Answer + § 4.6 SEO Explore (06a9605)
- **2026-04-27** § 2.7 Steps 1-6 Explain 臨床推理強化 + Phase 1A polish completion-event telemetry (cd697d1..dd128e2, 19 commits)

For older work see ARCHIVE.md.

## Pointer to Other Docs

- **Active rules + workflow**: CLAUDE.md
- **Open future tasks**: BACKLOG.md
- **Completed work log**: ARCHIVE.md
- **Tech debt entries**: TECH_DEBT.md
- **Spec**: docs/PRD.md (v1.3)
- **Code state vs PRD**: FEATURE_AUDIT.md
- **Architecture**: docs/architecture.md
- **ADRs**: docs/decisions/
