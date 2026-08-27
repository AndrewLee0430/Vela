# Vela docs/ Navigation

This folder contains spec, architecture, decisions, and historical references for Vela.

## Living docs (read regularly)

| File | When to read |
|---|---|
| **PRD.md** | Read for any feature spec / acceptance criteria. Section status markers (✅/❌/🧊) reflect current ship state. |
| **architecture.md** | Read when needing system architecture / pipelines / payments / DB / security context. |

## Historical reference (read for archeology only)

| File | Why kept |
|---|---|
| **business-overview.md** | Vela narrative + market positioning. Read for GTM/strategy context, not for spec. |

## Decision records

| Folder | Content |
|---|---|
| **decisions/** | ADRs (Architecture Decision Records). Read when work item references "see ADR XXX". Each ADR is short (~50 lines), self-contained. Some reference advisor discussion notes preserved in git history. |

## Reference layer

| File | When to read |
|---|---|
| **CONTEXT_MODEL.md** | When confused about which file holds what info, or why doc structure is this way. Quick-lookup tables + rationale for design decisions. |

## Diagrams

| File | Subject |
|---|---|
| **architecture-overview.mermaid** | High-level system architecture |
| **architecture-rag.mermaid** | RAG pipeline detail |
| **architecture-security.mermaid** | Guard chain + PHI defense |
| **user-flow.mermaid** | User journey |

## Navigation rules

If you need to know:
- **What spec to implement?** → PRD.md (relevant § section)
- **What's the system architecture?** → architecture.md
- **Why was decision X made?** → decisions/ (ADR XXX)
- **What's the next task to ship?** → ../STATE.md "Next Up" (top of queue)
- **What strategy decisions / candidate work are on record?** → ../BACKLOG.md — a decision archive, not an execution queue; entries are discharged at car closeout by write-back from STATE *(re-worded from "What's the open backlog?" — founder ruling A 2026-08-26, batons/positioning_audit_20260823.md §3)*
- **What's the tech debt?** → ../TECH_DEBT.md
- **What's already shipped?** → `git log` (recent window in ../STATE.md Recently Shipped)
- **Where did an archived ledger entry go?** → archive/ (`state_shipped_2026.md` · `tech_debt_done.md`) — full text VERBATIM; the tombstones in ../STATE.md and ../TECH_DEBT.md point here (ledger slimming, founder ruling 2026-08-27)
- **What's the actual codebase state?** → grep / ls / `git log` (no static snapshot file)

For active rules + workflow, see [../CLAUDE.md](../CLAUDE.md).
