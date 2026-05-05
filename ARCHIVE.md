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
