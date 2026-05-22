# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-22 (§3.1 PHASE B deployed to production — v167)

## Phase

Phase 0 — production shipped 2026-05-19 (started 2026-04-17, deploy commit a63b304, v164)

## Current Focus

Phase 0 production deployed 2026-05-19 (v164, commit a63b304). All 🔴 CRITICAL ship gates passed: server health, vector store (690 docs), Clerk auth, anon share 403, §2.7 Explain canonical (K=6.8 case), §2.8 anon trial quota (6/8 modal), §2.9 multilingual response, §2.0 PostHog events. One 🟡 HIGH fix-forward landed: OG image URL/path mismatch in StaticFiles mount (commit a63b304).

Next focus: §3.1 PHASE C (frontend) → PHASE D (OnboardingWizard) → PHASE E (Settings). §3.1 PHASE B backend is **DEPLOYED to production** 2026-05-22 (v167; commits 21645dd migration + UserProfile model + 2d714fd POST/GET /api/user/context/hash endpoints + tests). Migration 006 applied to Neon prod (`neondb` production branch) via Neon SQL Editor — schema verified (5 columns, user_id PK, hash NOT NULL, locale nullable, both timestamptz default now()); server startup clean in fly logs. Endpoints are live but **dormant** — no frontend caller until PHASE C wires the writer + GET dual-trigger restore. §4.6 PHASE E 4-week GSC indexing window running in background.

Last shipped: §2.1 Model Provider Refactor (2026-05-13) + Phase 0 production deploy (2026-05-19).

## Next Up (Phase 1A — PHASE C onward)

1. **§4.6 PHASE E 4-week GSC indexing window** — passive, monitored weekly. Started 2026-05-19 with production deploy. `/explore` index page follow-up can land during this window.
2. **§3.1 PHASE C — frontend hook + LangContext write-through + analytics.ts writer** — wire the writer for `user_context_hash` localStorage (resolves §2.0 silent-loss Finding A from retrospective.md § 2), the §3.2-Step-3 dual-write to `vela_lang` + `vela_user_context.work_language` (G3 decision), and the POST call to `/api/user/context/hash` for Pro users on context change. Spec: PRD §3.1 v1.5+v1.6 (bf446e3 + 603917f). Estimated ~1d.
3. **§3.1 PHASE D — `OnboardingWizard.tsx` (§3.2 three-step flow)** — distinct from existing `OnboardingOverlay.tsx`. Spec: PRD §3.2. Estimated ~1.5d.
4. **§3.1 PHASE E — Settings §4.3 tab** — including 需求 5 dual-trigger restore (sign-in passive + Settings button), role_category derivation in PostHog identify, §3.3 basic examples. Spec: PRD §4.3 v1.5. Estimated ~1d.
5. **Deploy batch for §3.1 C/D/E** — single prod deploy after PHASE E lands. PHASE B already deployed (v167, 2026-05-22, migration 006 applied); future §3.1 migrations (007 schema_versions per TECH_DEBT, any user_profile schema extension) still need manual `psql -f` before their deploy — no auto-migrate runner.
6. **Phase 0 Retrospective integration into Phase 1A planning** — retrospective.md complete (de4e7d4); surface findings (Clerk publicMetadata dormant, user.deleted webhook gap, OG image ephemeral fs, 5 dogfooding nuance issues) during #2–#4 implementation. No standalone deliverable, embedded in PHASE C/D/E work.

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

- **2026-05-22** [PRD 3.1] PHASE B — **DEPLOYED to production v167 2026-05-22** (migration 006 applied to Neon prod via Neon SQL Editor; 21645dd + 2d714fd; endpoints live, dormant until PHASE C wires the frontend). Two commits: migration 006 + UserProfile model (21645dd), and POST/GET /api/user/context/hash endpoints + tests (2d714fd). Pro-gated via user_usage.plan_type (G4); atomic UPSERT via pg_insert.on_conflict_do_update with explicit server-side func.now() at both INSERT and on-conflict paths (E3 "last verified"). Rate-limited 10/hour/IP (POST + GET share the bucket per review decision). 31/31 unit tests green (4 new model tests + 27 existing). Endpoint-level TestClient tests deferred per the cp950 import-crash workaround documented in `tests/models/test_user_profile.py`. Schema verified post-deploy: 5 columns, user_id PK, hash NOT NULL, locale nullable, both timestamptz default now(). Server startup clean in fly logs.
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
