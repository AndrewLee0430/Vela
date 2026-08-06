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
| Pre-gate human-eye checklist (blank FORM — fill per gate, incl. per-row EXPECTED OWNER) | docs/human_eye_gate_checklist.md |
| Open future tasks | BACKLOG.md |
| Completed/shipped work log (chronological) | `git log` (recent window in STATE "Recently Shipped") |
| Tech debt entries (active gaps) | TECH_DEBT.md |
| System architecture (request flow / pipelines / payments / DB / env / frontend / deploy) | docs/architecture.md |
| Master spec | docs/PRD.md (v1.5) |
| Decision records (ADRs) | docs/decisions/ |

### Workflow for a new task

**Step 0 — Identify the task** (work-source priority):

1. Read `STATE.md` → top of "Next Up" queue is your task
2. Find that task in `BACKLOG.md` → read short description + phase + estimated time
3. If task references PRD §X.Y → read `docs/PRD.md` § section (requirements + acceptance + "not in scope")
4. If task references ADR(s) → read `docs/decisions/00X-*.md` for decision context
5. Grep codebase to verify partial implementation — `git grep "<feature_keyword>"` + `ls pages/<feature>` etc. Don't re-implement existing code.

**Step 1 — Implement**:

6. Build per spec
7. Verify against PRD acceptance criteria, item by item
8. **If task is part of an acceptance protocol checkpoint** (e.g., § 2.7 Step 8), execute full protocol checklist — not just "X cases done"

**Step 2 — Ship cleanup ritual** (explicit document update sequence):

9. Update 3 docs:
   - `STATE.md`: move task from "Next Up" → "Recently Shipped" (with commit SHA)
   - `BACKLOG.md`: remove entry or mark done
   - `docs/PRD.md` status marker: update §X.Y if section-level change (❌ → ✅ SHIPPED `<date>`)
   - (the chronological shipped entry is auto-recorded by `git log` on commit — no manual append)
10. **Commit message format — conventional commits by default; `[PRD X.Y]` only where it is true.**
    - **Default:** `type(scope): brief description` — e.g. `docs(gate): …`, `test(wrongdrug): …`, `feat(verify): …`.
    - **`[PRD X.Y]` is REQUIRED when, and only when, the commit changes product code implementing a PRD section.** The two combine: `feat(verify): [PRD 3.1] add DailyMed attribution enum`.
    - **CHECK: does this commit change product code that implements a PRD section? If YES the PRD reference is mandatory; if NO it must not be invented.**
    - *Basis (decided 2026-08-06):* `[PRD X.Y]` was used **30 times in 562 commits**, last on `8499495` (2026-07-22), and **28 of the last 30 commits touched no product code** — the format assumed feature work, and much of this line of work is not feature work.

**Solo-founder STATE discipline**: At minimum, at the end of each task segment, update STATE.md (Next Up + Recently Shipped) even if other docs (PRD marker, BACKLOG removal) are intentionally skipped. STATE.md is the single entry point for "where am I next session"; a stale STATE is the highest-cost drift because it misleads the next work session about what's done vs pending. PRD-marker / BACKLOG updates may be batched or skipped at the founder's discretion, but STATE should never silently lag reality.

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
17. **Tests must verify intent, not just behavior** — every test should answer "what business rule breaks if this fails?" A test that passes against hardcoded return values or stubbed calls without observing real effect is dead weight. Applies especially to §2.7 acceptance baseline, golden eval rubric design (`tests/golden_dataset.json`), and TECH_DEBT regression coverage (e.g. 5 dogfooding nuance issues + Research WARN pattern).
18. **Fail loud, not silent** — if a multi-step task cannot be fully verified, surface it. Never report "completed" / "tests pass" / "migration applied" / "webhook handled" if any sub-step was skipped, exception-swallowed, or unverified. Reference incident: Phase 0 OG image fix 2026-05-19 — `_generate_og_png()` exception was correctly caught in `try/except` but masked the real wiring bug (StaticFiles mount double-prefix at `api/server.py`) for weeks until external LinkedIn validator surfaced it. Applies especially to: Clerk webhook handlers, Dodo subscription path, `analytics.ts` fire-and-forget calls, migration runners.
19. **When extending an existing data source, prompt, or data path to a SECOND surface, carry its MITIGATIONS across — not just its data.** A compensating behaviour written for surface #1 (a fallback, a normalization, a guard, a language-specific string) does not travel automatically, and its absence on surface #2 is silent. Before shipping the extension, list what surface #1 does *around* the data and confirm each item is either carried across or explicitly declined in writing. Reference incidents, both 2026-07: **(a)** b1 country-keyed the authority DATA but not the label STRINGS, so a Taiwan-only-era i18n string leaked "NHI reimbursement" to every country; **(b)** DailyMed was extended from Verify to Research, but Verify's openFDA fall-through for OTC Drug-Facts labels lacking 34073-7 (`api/server.py:1202-1204`) was not carried across, leaving Research with no fallback.

*(Rules 20–22 RECORD PRACTICE THAT ALREADY EXISTS in the repo. Rule 23 is a PROMOTION — a lesson raised to a rule after it was measured to cost five batons. Each states a CHECK, because prose alone has twice failed to prevent recurrence: SOP line 4 was written 2026-08-03 and ignored the same day; TECH_DEBT.md:264 was written 2026-07-27 and unapplied across five c2 batons.)*

20. **`tests/probes/` is committed evidence; `tests/results/` is gitignored scratch** — if a `docs/` report states a number, the probe **script and its small result JSON** belong in `tests/probes/<topic>/`. Re-running a probe against a **live external API** produces a *new* snapshot, not the one a finding was based on: the JSON is the evidence, the script is the method, both are needed. Bulk regenerable intermediates stay in `tests/results/` (e.g. the 15.8 MB `c2_ea_fetch.json`, the 31 MB scratch index). **CHECK: every number in a `docs/` report resolves to a committed artifact, or the report says the artifact is not retained and why.** Reference incident: BACKLOG cites `tests/results/_pairaware_m1_content_audit.py` as a reusable method — it is **untracked and exists on one machine only**, so the findings built on it are unverifiable by anyone else. See `tests/probes/README.md`.

21. **Self-refute string heuristics over drug data before reporting** — drug labels legitimately name *other* drugs (cross-sensitivity), share vocabulary across species and routes, and mix container terms with dosage forms. Where an exact key exists (`setid`, `moiety`, `doctype`), **use the key, not the text**. **CHECK: the report hand-samples BOTH positives and negatives, states the sample size, and lists the rejected markers so they are not re-added. A text-derived classification lacking all three is unverified — say so rather than reporting the number.** Reference incidents: instrument-blind 8–11 (2026-08-04) — four false findings in one work line, all self-caught: `own_drug` read ACECLOFENAC as aspirin; a non-human sweep flagged 69 and collapsed to 3; a route/form classifier reported 22% and was 13%; a drift check compared a value to itself.

22. **Ranking / weighting / tier ratifications must inspect CONTENT, not only rank position** — print N sampled documents' *text* alongside the rank deltas. **CHECK: the sweep output contains document text. A sweep showing only ranks, IDs and citation membership has ratified nothing.** This is **Rule 17 at the measurement layer** — a ranking sweep that never reads a document is the same dead weight as a test that never observes real effect. Reference incident: instrument-blind #4 — the local-tier sweep reweighted **690 empty stubs** and could not see it, and **its null result read as reassurance**.

23. **A lookup keyed on ONE identifier string is not a lookup on the entity — enumerate every key** — the DailyMed corpus key is the TFDA backbone `drug_name` **verbatim** (`scripts/build_dailymed_label_corpus.py:99-105`), so one substance can occupy two `moiety` keys with different reference labels and different coverage: `ASPIRIN` → VAZALORE (**no** whitelisted safety sections) and `ACETYLSALICYLIC ACID` → DURLAZA (**34070-3 / 34073-7 / 43685-7**). **CHECK: any per-drug conclusion states the full key set it used; a conclusion citing one key is unverified. Owner / expected-drug fields are PLURAL BY CONSTRUCTION** — see `docs/human_eye_gate_checklist.md`, where this rule is already implemented. ⚠️ **Do not derive the key set by substring** — a `STATIN` search returns **NYSTATIN**, an antifungal. Reference incident: a single-key lookup produced *"in 6 of 6 adjudicated cases the drug's own reference label has no safety section"* — **false for the flagship case** (DURLAZA — Contraindications is row 57 of the shipped index, embedded and row-aligned), and it stood **across five c2 batons** even though `TECH_DEBT.md:264` had recorded the dual-key fact on 2026-07-27.
