# Vela Doc-System Mental Model

**Purpose**: Reference for solo founder + Claude.
**When to read**: When confused about which file holds what info.
**Last updated**: 2026-05-05 (post FEATURE_AUDIT.md deprecation)

---

## The 4-Doc Architecture (Living Status)

```
┌─────────────────────────────────────────────────────┐
│ STATE.md = "What we're doing RIGHT NOW + NEXT"      │
│   - Current Focus                                   │
│   - Next Up (queue, in execution order)             │
│   - Recently Shipped (last 7 days)                  │
└─────────────────────────────────────────────────────┘
                       ↑ for §-level status & navigation

┌─────────────────────────────────────────────────────┐
│ ARCHIVE.md = "What's been shipped (chronological)"  │
│   - 2026-04-30: §2.7 Steps 7-8 + M06                │
│   - 2026-05-04: v0.4 integration                    │
│   - 2026-05-05: Doc reorg                           │
└─────────────────────────────────────────────────────┘
                       ↑ for historical record

┌─────────────────────────────────────────────────────┐
│ PRD.md = "Spec + § status markers"                  │
│   - § 2.7 ✅ SHIPPED 2026-04-30                     │
│   - § 4.5 ❌ PENDING                                │
│   - § 4.4 🧊 OUT OF SCOPE                           │
└─────────────────────────────────────────────────────┘
                       ↑ for spec alignment + intent vs ship

┌─────────────────────────────────────────────────────┐
│ Codebase itself = "What's actually implemented"     │
│   git grep / ls / git log / git show                │
└─────────────────────────────────────────────────────┘
                       ↑ for verification (replaced FEATURE_AUDIT.md)
```

---

## Workflow Mapping (per CLAUDE.md Step 0/1/2)

When starting a new task (e.g. § 4.5 Share Answer):

| Step | Action | File / Source |
|------|--------|---------------|
| 0.1 | Identify task | STATE.md "Next Up" |
| 0.2 | Read short description + estimate | BACKLOG.md |
| 0.3 | Read full spec | PRD.md § X.Y |
| 0.4 | Read decision context (if relevant) | docs/decisions/ |
| 0.5 | Verify partial implementation | `git grep` / `ls` (NOT FEATURE_AUDIT) |
| 1 | Implement | code |
| 2.1 | Move task Next Up → Recently Shipped | STATE.md |
| 2.2 | Append shipped entry | ARCHIVE.md |
| 2.3 | Remove or mark done | BACKLOG.md |
| 2.4 | Update § status marker | PRD.md |

---

## "Where do I find this?" — Quick Lookup

| Question | Answer source |
|---|---|
| What am I working on **now**? | STATE.md → Current Focus |
| What's **next**? | STATE.md → Next Up (top of queue) |
| What did I ship **recently** (last 7 days)? | STATE.md → Recently Shipped |
| What did I ship **historically**? | ARCHIVE.md |
| What does § X.Y spec say? | PRD.md → § X.Y |
| Is § X.Y shipped? | PRD.md status marker (✅/❌/🧊) |
| What's open in the backlog? | BACKLOG.md |
| Why did we decide X? | docs/decisions/ (ADR XXX) |
| What tech debt is open? | TECH_DEBT.md |
| Does this file/function exist in codebase? | `git grep` / `ls` |
| What's the system architecture? | docs/architecture.md |
| What was historical context (e.g. v0.4)? | git log + git show + commit history |
| What's the docs/ folder structure? | docs/INDEX.md |

---

## Why This Architecture (Rationale)

### Why STATE.md as entry point?

Without STATE.md, "what to do now" is scattered across PRD section markers + BACKLOG queue + chat conversation. Single source of truth eliminates ambiguity.

### Why FEATURE_AUDIT.md was deprecated (2026-05-05)?

FEATURE_AUDIT.md tried to mirror codebase reality in markdown. Two problems:

1. **Maintenance discipline didn't execute** — § 2.7 結案 + M06 + Path 1 work (5+ commits) wasn't reflected in FEATURE_AUDIT detail.
2. **Stale snapshot risk** — readers might trust outdated info and miss recent changes.

Replacement: codebase itself (grep/ls) is source of truth. PRD markers + STATE/ARCHIVE cover § level.

### Why ADRs are short (~50 lines)?

ADRs record **decision + reason**, not content replay. Detail context lives in source materials (e.g., advisor discussion preserved in git commit). This avoids:
- Duplicate maintenance (ADR vs source)
- Decision drift over time (ADR is frozen, source can update)

### Why `docs/decisions/` separate from PRD?

PRD = spec (what to build)
ADRs = decisions (why we built it this way)

Separation means PRD spec is stable; decision context preserved without polluting spec body.

### Why TECH_DEBT.md vs BACKLOG.md 分開?

| | BACKLOG.md | TECH_DEBT.md |
|---|---|---|
| 性質 | New features / phase work | Pre-existing codebase gaps |
| Trigger | PRD spec / GTM need | Discovery during shipping |
| Lifecycle | Phase-scheduled | Opportunistic fix |
| Example | "§ 4.5 Share Answer" | "print() 違反 54 處" |

Mixing them confuses prioritization (new feature vs cleanup are different decisions).

---

## Common Pitfalls

### Don't write status in two places (without all)

If § 2.7 is shipped, update **PRD.md marker AND STATE.md Recently Shipped AND ARCHIVE.md** — all three. They serve different lookup paths.

### Don't reference docs that don't exist

When archiving / deleting a doc (e.g., FEATURE_AUDIT.md or roadmap-discussion-v0.4.md), grep for references first:

```bash
git grep "FEATURE_AUDIT" -- '*.md'
git grep "roadmap-discussion" -- '*.md'
```

Replace dangling references before commit.

### Don't conflate "intent" with "reality"

PRD says ✅ SHIPPED but you can't find the file? → grep codebase. PRD might be drifted. Codebase = source of truth.

### Don't make ADRs into long content dumps

If decision detail is long (e.g., 40-題 LLM test report), put detail in source material (git commit / advisor doc / external file). ADR is the **decision pointer**, not the content.

---

## When to Update This File

- New doc added/removed → update Architecture diagram + Quick Lookup
- New workflow step → update Workflow Mapping
- New rationale to capture → add to "Why This Architecture"

---

## See Also

- [CLAUDE.md](../CLAUDE.md) — Active rules + workflow steps (procedural)
- [docs/INDEX.md](INDEX.md) — docs/ folder navigation (where each file lives)
- [docs/decisions/](decisions/) — ADRs (why we made specific decisions)
