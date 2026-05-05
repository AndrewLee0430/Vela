# Decision 002: Documentation Reorganization

**Status**: Accepted (2026-04-30 solo founder review)
**Date**: 2026-04-30
**Version**: 0.1
**Author**: andre (solo founder) + Claude Opus 4.7 (assistant)
**Supersedes**: (none — first ADR on docs structure)
**Superseded by**: (none — this is current)

---

## TL;DR

Vela's documentation drifted into a context-pollution problem: CLAUDE.md grew from ~400 lines (2026-04-21 baseline) to **574 lines** mixing 5 different content roles, and TODO.md grew to **750 lines** with no clear single role. This ADR records the decision to reorganize docs into 5 purpose-specific files following a context-engineering philosophy adapted from the Claude_md.docx pattern.

**Key changes**:
- CLAUDE.md → 111 lines (active rules + workflow + commands only)
- New: STATE.md (current focus), ARCHIVE.md (chronological log), TECH_DEBT.md (gaps), docs/architecture.md (system reference)
- Renamed: TODO.md → BACKLOG.md (idea buffer role)
- PRD.md gained inline status markers (✅ SHIPPED / ❌ PENDING / 🔬 PARTIAL / 🧊 OUT OF SCOPE)

**Closes**: `[P1] CLAUDE.md 結構性精簡` tech-debt entry logged 2026-04-21.

---

## 1. Context(背景脈絡)

### 1.1 現況 — by 2026-04-30 post § 2.7 結案

After § 2.7 Steps 1-8 + Path 1 + M06 fix shipped, project documentation showed clear drift symptoms:

- **CLAUDE.md = 574 lines** (started ~400 at 2026-04-21 baseline, grew +43% in 9 days)
  - Mixed 5 content roles: collaboration principles + active rules + Current Development Status + Tech Debt + Architecture + File Paths + Important Rules
  - Architecture details (request flow, pipelines, payments, security, DB schema, env vars, deployment, frontend notes) bloated the file with reference material that violated Progressive Disclosure
  - Discovered Gaps (G1) + Phase 1A polish history were duplicates of FEATURE_AUDIT.md/decision docs

- **TODO.md = 750 lines** mixing:
  - Open future work (Round 3 follow-ups, Phase 1A polish, §4.5/§4.6 queue)
  - Completed acceptance protocols (§ 2.7 Step 8 protocol, 60 lines, no longer relevant after dffd015)
  - §2.7 Step 4 follow-up (7 entries, half resolved by Step 8 work, half still open — never re-evaluated)
  - Stale Roadmap section duplicating CLAUDE.md "Next task"

- **No single source of "current focus"**: state was scattered across CLAUDE.md "Current Development Status" + TODO.md Roadmap + chat conversation. New Claude sessions had to read 1300+ lines just to know what was being worked on.

- **No archive of shipped work**: CLAUDE.md "Completed" list duplicated FEATURE_AUDIT.md's table without git-level traceability (no commit SHAs, no chronology).

### 1.2 Drift symptoms (objective evidence)

Captured during Stage 1 read-only audit (2026-04-30):

- **PRD version drift**: CLAUDE.md said "PRD v1.2" while docs/PRD.md was at v1.3 (bumped 06a9605 2026-04-28)
- **Phase 0 stale**: CLAUDE.md "Remaining Phase 0: 2.7 finish (Steps 3-8) → ..." even though Step 8 was about to ship same day. FEATURE_AUDIT.md had matching stale paragraph.
- **Tech debt rot**: L122 Landing Page 收尾 (logged 2026-04-20, partially resolved a22ce9f 2026-04-21) and L190 Anonymous quota (Round 3 24b1d79 2026-04-22) — neither marked as resolved. No mechanism existed for closing them.
- **§2.7 Step 4 follow-up rot**: 7 entries deferred "until Step 8 data" — but Step 8 was now done and no one had re-evaluated trigger conditions.

### 1.3 Anticipated, then deferred

This problem was anticipated. A `[P1] CLAUDE.md 結構性精簡` tech-debt entry was logged 2026-04-21 in CLAUDE.md L147 with a pre-designed split plan:

> 拆 CLAUDE.md 成三份:CLAUDE.md (~150-180 lines, active instructions only) / TECH_DEBT.md / docs/architecture.md
> Phase 0 Retrospective 本來就要 review code health,重構 CLAUDE.md 在那時 sync 最自然

The decision was deferred to Phase 0 Retrospective. § 2.7 結案 (2026-04-30) created a natural break point earlier than Retrospective: significant work to archive, drift to clean up, and Path B (§4.5 / §4.6 / §2.1 / Retrospective) about to start with new docs. **Reorganizing structure before adding new content was more efficient than reorganizing after.**

### 1.4 Why now and not Phase 0 Retrospective

- **Lower fatigue cost**: § 2.7 結案 momentum carries into reorg work (cognitive state assessed as good enough by user 2026-04-30)
- **Earlier ROI**: §4.5/§4.6 work starts with clean docs, not 574-line CLAUDE.md to navigate
- **Audit findings still fresh**: Stage 1 read-only audit's drift catalog is most actionable when memory is hot
- **Phase 0 Retrospective stays focused**: keeps Retrospective scoped to "Phase 0 outcome assessment" rather than "doc cleanup + outcome assessment"

---

## 2. Decision

Reorganize Vela's documentation into purpose-specific files following a context-engineering philosophy. Each file has one clear lifecycle and audience.

### 2.1 New file structure

| File | Role | Lifecycle | Approx lines |
|---|---|---|---|
| `CLAUDE.md` | Active rules + collaboration principles + workflow + commands | Stable (rules change rarely) | 111 |
| `STATE.md` | Current focus + next-up + active acceptance protocols + blockers | Highly dynamic (per-commit) | ~50 |
| `BACKLOG.md` (was `TODO.md`) | Open future tasks (idea buffer) | Dynamic (capture + reclassify) | ~650 |
| `ARCHIVE.md` | Chronological completed work log (newest first) | Append-only | ~90 (initial) |
| `TECH_DEBT.md` | [P0]/[P1]/[P2] gaps with diagnosis context | Dynamic (resolution + add) | ~155 |
| `docs/architecture.md` | System architecture reference (16 sections) | Stable (architecture changes rarely) | ~270 |
| `docs/PRD.md` | Spec with inline status markers | Stable spec + dynamic markers | ~2125 |
| `docs/decisions/*.md` | ADRs (this file pattern) | Append-only | varies |
| `FEATURE_AUDIT.md` | Code state vs PRD diagnostic | Updated post-ship | ~440 |

### 2.2 Marker scheme on PRD.md

Per Q4=C decision: status markers added inline to feature section headings; spec body preserved verbatim. Markers are status overlay, not spec change.

| Marker | Meaning |
|---|---|
| ✅ SHIPPED `<date>` (commits) | Fully implemented + production-verified |
| 🔧 IN PROGRESS | Actively being worked |
| 🔬 PARTIAL `<date>` | Partial, see FEATURE_AUDIT.md for breakdown |
| ❌ PENDING (phase) | Not yet started |
| 🧊 OUT OF SCOPE | Explicitly deferred per phase-gate |

### 2.3 Archive tag taxonomy

ARCHIVE.md entries use one tag from this set:

| Tag | Use case |
|---|---|
| `[PRD §X.Y]` | Feature work tied to PRD section |
| `[bug]` | Production bug fix |
| `[tech-debt]` | Pre-existing gap closure |
| `[refactor]` | Code health |
| `[docs]` | Documentation |
| `[Phase 1A polish]` | Pre-shipped Phase 1A items |
| `[acceptance]` | Acceptance protocol completion |

---

## 3. Consequences

### 3.1 Positive

- **Context budget**: CLAUDE.md down from 574 → 111 lines (-81%), well under the < 300 lines best-practice ceiling. AI sessions get focused active-rules instruction without status/architecture pollution.
- **Single source of truth per concern**: status questions go to STATE.md; "did we ship X?" goes to ARCHIVE.md; "what tech debt is open?" goes to TECH_DEBT.md.
- **Drift resistance**: smaller per-file scope means easier to keep each file in sync with reality. Each file has one update trigger (commit / per-shipping / per-discovery).
- **Onboarding**: future readers (or future Claude sessions) navigate by intent (rules / state / spec / arch / decisions) without reading 750-line monoliths.
- **Closes [P1] tech-debt entry** logged 2026-04-21 — the planned work in that entry IS this reorg.
- **Cleaned 5 stale references** (drift sync commit 3fdeddc): PRD v1.2 → v1.3 in 5 places, Phase 0 remaining lines updated.
- **Audited + reclassified 6 follow-up entries** in §2.7 Step 4 follow-up section (2 → ARCHIVE, 4 stayed BACKLOG).

### 3.2 Negative

- **More files**: 6 new top-level Markdown files (STATE / ARCHIVE / TECH_DEBT / docs/architecture.md / docs/decisions/002 / + BACKLOG rename) vs prior 4 active (CLAUDE / TODO / FEATURE_AUDIT / docs/PRD).
- **Cross-reference maintenance**: pointers between files must be kept synced when files are renamed or sections moved. Mitigation: pointers are stable references (not commit SHAs or version numbers).
- **Initial migration cost**: ~6 hours of reorg work (5 commits over 2026-04-30 evening). Future reorgs may be smaller.
- **Multiple sources for "what's done"**: ARCHIVE.md (chronological) + FEATURE_AUDIT.md (PRD-aligned table) + git log overlap. Resolution: each serves different reading style — chronological vs spec-aligned vs raw-history. Acceptable redundancy.

### 3.3 Net assessment

Net positive. The 81% CLAUDE.md reduction alone justifies the reorg cost; downstream context-engineering wins (faster Claude sessions, less drift) compound.

---

## 4. Alternatives Considered

### 4.1 Status quo + spot fixes

Continue with 574-line CLAUDE.md + 750-line TODO.md, just clean drift on each commit.

**Rejected because**: drift will recur. CLAUDE.md grew 43% in 9 days under spot-fix discipline. Every new feature adds entries to "Completed" + "Tech Debt" + "Discovered Gaps" without ever pruning. Linear decay.

### 4.2 CLAUDE.md split only (3 files: CLAUDE / TECH_DEBT / docs/architecture.md)

The original 2026-04-21 plan in the [P1] tech-debt entry. Split CLAUDE.md into 3 files. TODO.md stays as-is.

**Rejected because**:
- TODO.md was the bigger problem (750 lines vs 574). Leaving it untouched would close half the drift.
- "Current Development Status" in CLAUDE.md → going to TECH_DEBT.md or docs/architecture.md doesn't fit either role. Needs its own file (STATE.md).
- Acceptance protocols (§ 2.7 Step 8 pattern) need a home that's neither rules-stable (CLAUDE.md) nor spec (PRD.md). STATE.md fits.

### 4.3 Single mega-commit vs split commits

User initially asked: 1 mega-commit or 5 split commits?

**Chose 5-commit split**: drift sync / architecture extract / structural reorg / PRD markers / ADR. Each commit is atomic and reviewable in isolation; future `git blame` distinguishes intent ("drift sync" vs "architectural reorg"). Mega-commit's only advantage is fewer SHAs in `git log` — outweighed by review-cost savings.

### 4.4 Today vs Phase 0 Retrospective

Original [P1] entry deferred this work to Phase 0 Retrospective.

**Chose today** (post § 2.7 結案) because:
- Lower fatigue cost (momentum + audit findings fresh)
- Earlier ROI (§4.5/§4.6 starts with clean docs)
- Phase 0 Retrospective stays focused on outcomes, not docs cleanup

User assessed cognitive state was good. Acknowledged risk of fatigue but proceeded.

### 4.5 STATE.md vs Claude_md.docx model

User shared Claude_md.docx (Context Engineering reference) which proposed CLAUDE / STATE / BACKLOG / CHANGELOG.

**Adopted partially**:
- ✅ STATE / BACKLOG / ARCHIVE pattern (Vela's `ARCHIVE.md` plays the role of `CHANGELOG.md`)
- ✅ "Current focus + Next Up" structure
- ✅ Lifecycle separation (stable rules vs dynamic state)

**Did NOT adopt**:
- ❌ Claude_md.docx CHANGELOG.md naming (chose ARCHIVE.md — same role, "archive" reads better as "completed work log")
- ❌ Claude_md.docx didn't address ADR system (we already have docs/decisions/, kept it)
- ❌ Claude_md.docx didn't address spec-vs-state separation (Vela's PRD.md / FEATURE_AUDIT.md pattern is preserved — it's a Vela-specific drift-discipline mechanism that predates this reorg)

**Vela-specific extensions**:
- "Active Acceptance Protocols" section in STATE.md — Vela's pattern from § 2.7 Step 8 protocol
- TECH_DEBT.md as separate file — Claude_md.docx kept tech debt in BACKLOG; Vela's tech debt is dense diagnosis-context entries that don't compress to BACKLOG's task-line style

### 4.6 docs/architecture.md single file vs subdirectory

**Chose single file** (267 lines, 16 numbered sections). Will revisit and split when crosses ~500 lines (target: per-domain split — pipelines / security / payments).

### 4.7 PRD status markers vs separate overlay file

**Chose inline markers** per Q4=C. Spec body preserved verbatim. Alternative was a separate `docs/PRD-status.md` overlay, but: (a) markers are short — clutter cost is low; (b) overlay file would drift; (c) inline keeps reader's attention on current status while reading spec.

### 4.8 SEO_AUDIT.md placement

**Deferred**. SEO_AUDIT.md (217 lines, dated 2026-04-17) is a one-time audit. Should probably move to `docs/audits/seo-2026-04-17.md`. Out of scope for this reorg — scheduled as a separate optional cleanup commit.

---

## 5. Implementation

5 commits on `main` (2026-04-30):

| # | SHA | Description |
|---|---|---|
| 1 | 3fdeddc | docs: sync stale references post § 2.7 結案 (drift sync) |
| 2 | 59002d1 | docs: extract architecture from CLAUDE.md → docs/architecture.md |
| 3 | 5ced91a | docs: structural reorg — STATE.md / BACKLOG.md / ARCHIVE.md / TECH_DEBT.md |
| 4 | aaa95de | docs(prd): add status markers to feature section headings (Q4=C) |
| 5 | (this commit) | docs(decisions): ADR 002 documenting reorg rationale |

### 5.1 Audit findings applied (Q3 + Q4)

**Q3 (stale tech debt)**: L122 Landing Page (a22ce9f partially resolved) + L190 Anonymous quota (Round 3 24b1d79 partially resolved) — both kept in TECH_DEBT.md with annotations rather than archived. Phase 0 Retrospective will formally close.

**Q4 (§ 2.7 Step 4 follow-up)**: 6 entries reclassified — 2 → ARCHIVE.md (resolved by Step 8 work: risk tier conservative skew evaluation, body language drift Bug C fix), 4 → BACKLOG.md (still deferred: SourceBadge click tracking, Copy-to-clipboard serializer, RiskBadge hover tooltip, SourceBadge upgrade).

### 5.2 Net change

- CLAUDE.md: 574 → 111 lines (-81%)
- BACKLOG.md (was TODO.md): 750 → 654 lines (-13%, with redundant content removed)
- 4 new top-level files (STATE.md / ARCHIVE.md / TECH_DEBT.md / docs/architecture.md)
- 1 new ADR (this file)

---

## 6. Maintenance protocol

For future contributors / future Claude sessions:

- **STATE.md**: update at the start/end of each work session. The 1-3 "Current Focus" items should match what's actively being touched in commits. "Recently Shipped" auto-grows; trim to last 7 days when entries fall out of relevance.
- **ARCHIVE.md**: append entry within commit message workflow. Tag taxonomy: `[PRD §X.Y]` / `[bug]` / `[tech-debt]` / `[refactor]` / `[docs]` / `[Phase 1A polish]` / `[acceptance]`. One-line summaries only — full context belongs in commit messages.
- **BACKLOG.md**: capture new items as they surface. Re-evaluate trigger conditions when blocking work completes (e.g. after § 2.7 Step 8 ships, re-check entries that say "deferred until Step 8 data").
- **TECH_DEBT.md**: add when discovered. Mark resolved with commit SHA when closed; archive to ARCHIVE.md if you want chronological resolution log. Keep verbose form — entries are dense diagnosis contexts that lose value when compressed.
- **CLAUDE.md**: stable rules. Only edit when collaboration patterns or commands change. Architecture moves go to docs/architecture.md.
- **PRD.md status markers**: update when status transitions (PENDING → IN PROGRESS → SHIPPED). Keep in sync with FEATURE_AUDIT.md and ARCHIVE.md. Spec body stays verbatim — only headings change.
- **docs/architecture.md**: stable architecture reference. Update when system architecture meaningfully changes (new pipeline, new external service, schema changes). Not a per-commit doc.

### 6.1 Drift detection

Symptoms that suggest the reorg is degrading:
- CLAUDE.md crosses 250 lines → re-extract content
- BACKLOG.md grows acceptance-protocol sections → move to STATE.md
- TECH_DEBT.md entries older than 60 days without status update → audit
- STATE.md "Recently Shipped" stales (older than 7 days dominates list) → trim
- ARCHIVE.md tag taxonomy drifts (new tags not in this ADR) → either accept (update this ADR) or normalize

---

## References

- User-shared reference: `Claude_md.docx` (Context Engineering pattern, partially adopted — see § 4.5)
- Original [P1] tech-debt entry: pre-reorg CLAUDE.md L147 (logged 2026-04-21, now superseded by this ADR)
- Stage 1 read-only audit: 2026-04-30 session (output captured in this ADR's Context + Trade-offs sections)
- Stage 2 implementation: this ADR + 4 prior commits in batch
- Decision 001 (Anonymous Trial Flow) — reference ADR pattern for this file's structure
