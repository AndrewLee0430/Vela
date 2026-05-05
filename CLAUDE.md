# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

### Claude Code Collaboration Principles

- 發現跨文件 drift 或指令模糊時,先提出選項讓使用者決定,不要擅自判斷
- 執行前先 read 實際 code 驗證 spec 的假設,發現 mismatch 就停下
- 醫療 / 法律 / 多語等專業領域不確定時,flag 而不是靜默做出 best guess
- 順手發現的可修改項目(drift / dead code / consistency issues)flag 給使用者選擇,不要擅自擴張 scope

Examples from 2026-04-19 to 2026-04-20 sessions:
- Rule #4 print() check across CLAUDE.md / FEATURE_AUDIT
- Decision 001 Status drift 跨 5 個檔案
- Phase 0 執行順序表同步
- verify_system.md zh-TW severity vs dict 衝突 flag
- api/rag/generator.py dead code discovery before spec-blind edit

### Project Doc Map

| What you need | Where to look |
|---|---|
| Active rules + workflow (this file) | CLAUDE.md |
| Current focus + next-up + active acceptance protocols | STATE.md |
| Open future tasks | BACKLOG.md |
| Completed work log (chronological) | ARCHIVE.md |
| Tech debt entries (active gaps) | TECH_DEBT.md |
| System architecture (request flow / pipelines / payments / DB / env / frontend / deploy) | docs/architecture.md |
| Master spec | docs/PRD.md (v1.3) |
| Code state vs PRD | FEATURE_AUDIT.md |
| Decision records (ADRs) | docs/decisions/ |

### Workflow for a new task

**Step 0 — Identify the task** (work-source priority):

1. Read `STATE.md` → top of "Next Up" queue is your task
2. Find that task in `BACKLOG.md` → read short description + phase + estimated time
3. If task references PRD §X.Y → read `docs/PRD.md` § section (requirements + acceptance + "not in scope")
4. If task references ADR(s) → read `docs/decisions/00X-*.md` for decision context
5. Check `FEATURE_AUDIT.md` for current state — **do not re-implement what's already done**

**Step 1 — Implement**:

6. Build per spec
7. Verify against PRD acceptance criteria, item by item
8. **If task is part of an acceptance protocol checkpoint** (e.g., § 2.7 Step 8), execute full protocol checklist — not just "X cases done"

**Step 2 — Ship cleanup ritual** (explicit document update sequence):

9. Update 4-5 docs:
   - `STATE.md`: move task from "Next Up" → "Recently Shipped" (with commit SHA)
   - `ARCHIVE.md`: append entry with `YYYY-MM-DD [TAG] Title — summary (SHA)`
   - `BACKLOG.md`: remove entry or mark done
   - `FEATURE_AUDIT.md`: sync if codebase state changed
   - `docs/PRD.md` status marker: update §X.Y if section-level change (❌ → ✅ SHIPPED `<date>`)
10. Commit message format: `[PRD X.Y] brief description` (e.g. `[PRD 2.0] Remove temp window.__vela_analytics exposure`)

**Source-of-truth priority**:

- `STATE.md` is the authoritative "what to do now" — not PRD, not BACKLOG
- `BACKLOG.md` organizes work by phase; STATE.md "Next Up" is curated execution order
- `docs/PRD.md` defines WHAT each item does; not an execution queue
- `TECH_DEBT.md` is opportunistic side-channel; not a primary work source
- `docs/decisions/` ADRs are decision context; not work sources themselves

## What This Project Is

Vela is a medical AI SaaS (Next.js 15 + FastAPI) on Fly.io. Three features: Research, Verify, Explain. Pricing $9.99/month or $89.99/year via Dodo Payments. Credit costs: Research=3, Verify=1, Explain=2.

For full architecture, request flow, guard chain, feature pipelines, payments, security hardening, database schema, env vars, deployment, frontend notes, and key design decisions, see [docs/architecture.md](docs/architecture.md).

## Commands

### Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8000       # Dev server
TEST_MODE=true uvicorn api.server:app --reload     # Skip Clerk auth for local testing
```

### Frontend (Next.js)
```bash
npm install
npm run dev        # Dev server on :3000
npm run build      # Production static export
npm run lint       # ESLint
```

### First-Time Setup
```bash
python scripts/build_drug_vectordb.py    # Build NumPy vector index (required)
python scripts/build_explain_cache.py    # Pre-warm LOINC/RxNorm/MedlinePlus cache
```

### Tests
```bash
uv run python tests/run_golden_tests.py --smoke              # Smoke test (37 cases, ~10 min)
uv run python tests/run_golden_tests.py                       # Full regression (127 golden cases)
uv run python tests/run_golden_tests.py --filter LANG         # Filter by ID prefix (e.g. LANG, RES, VER)
```

### Deployment
Always use `.\deploy.ps1` instead of `fly deploy` directly.
This script automatically restarts any stopped machines after deployment.

```powershell
.\deploy.ps1
```

### Docker
```bash
docker build -t vela .
docker run -p 8000:8000 vela
```

## Important Rules

1. **Never change guard chain to fail-open** — if a guard throws, block the request
2. **Never move PHI detection to middleware** — breaks SSE streaming
3. **Never use sync `OpenAI()` in async code** — use `AsyncOpenAI()` + `await`
4. **Never use `print()`** — use `logging.getLogger()`
5. **Never expose `str(e)` in API responses** — use generic error messages
6. **Never use `["*"]` for CORS origins**
7. **Always use `_safe_db_write()` for DB writes** in server.py
8. **`fda_cached.py` is dead code** — do not import or use it
9. **`/api/consultation` was removed** — do not reference it
10. **Disclaimers are frontend-rendered** — never instruct LLM to generate disclaimers; `generator.py` says "Do NOT add any disclaimer"
11. **ProFeatureOverlay is a popover** — not a full-area overlay; uses `w-full` wrapper for layout
12. **Evidence section format** — LLM must output `## [SectionName 🟢 — Language]` for `parseResearchSections()` to work
13. **Cost tracking must not block** — all `log_api_cost_standalone()` calls wrapped in `try/except pass`
14. **All PostHog events go through `utils/analytics.ts` `track()`** — never call `posthog.capture()` directly. See PRD 2.0.
15. **All LLM calls go through Provider interface** (`api/providers/`) after Phase 0 2.1 lands — no direct `OpenAI()` or `AsyncOpenAI()` instantiation outside `api/providers/`.
16. **i18n-first** — every user-visible string needs an i18n key in all 16 languages. Proper nouns (Vela, PubMed, FDA) stay in English.
