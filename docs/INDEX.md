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
- **What's the open backlog?** → ../BACKLOG.md
- **What's the tech debt?** → ../TECH_DEBT.md
- **What's already shipped?** → ../ARCHIVE.md
- **What's the actual codebase state?** → grep / ls / `git log` (no static snapshot file)

For active rules + workflow, see [../CLAUDE.md](../CLAUDE.md).
