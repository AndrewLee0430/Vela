# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Vela is an evidence-based medical research assistant (Next.js frontend + FastAPI backend) with three features:
- **Research**: Query PubMed (36M+ articles) with cited, streamed answers
- **Verify**: Check drug interactions using FDA data with severity ratings
- **Explain**: Parse medical reports into plain language via LOINC/RxNorm/MedlinePlus

## Commands

### Frontend (Next.js)
```bash
npm install
npm run dev        # Dev server on :3000
npm run build      # Production static export
npm run lint       # ESLint
```

### Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn api.server:app --reload                          # Dev server on :8000
TEST_MODE=true uvicorn api.server:app --reload           # Skip Clerk auth for local testing
```

### First-Time Setup
```bash
python scripts/build_drug_vectordb.py    # Build NumPy vector index (required)
python scripts/build_explain_cache.py   # Pre-warm LOINC/RxNorm/MedlinePlus cache
```

### Tests
```bash
uv run python tests/run_golden_tests.py --smoke   # Smoke test (15 of 17 cases, ~80% cheaper)
uv run python tests/run_golden_tests.py           # Full regression (17 golden cases)
```

### Docker
```bash
docker build -t vela .
docker run -p 8000:8000 vela
```

## Architecture

### Request Flow
Every API call goes through: **Clerk JWT auth → rate limiter → 5-layer guard chain → feature pipeline → PostgreSQL audit log → SSE stream**.

The guard chain (`api/middleware/guards.py`) orders checks cheapest-first:
1. Input length (5k char limit)
2. Regex injection patterns (EN/ZH/JA/AR + Base64 decode)
3. LLM indirect injection scan on retrieved content
4. Intent classification via GPT-4.1-mini (blocks non-medical queries)
5. PHI detection (Taiwan ID, Japan My Number, US SSN/MRN)

### Three Pipelines

**Research** (`api/rag/`):
- Query → language detection → rewrite to 3 medical English queries
- Parallel retrieval: NumPy vector store (191 drugs) + PubMed API + FDA drug labels
- Deduplication + year-weighted scoring → reranking (top_k=8)
- GPT-4.1 generation with streaming SSE + citations

**Verify** (`api/data_sources/fda_cached.py`, `api/cache/simple_cache.py`):
- Drug name parsing → Levenshtein spell correction → 3-layer cache (memory L1 → SQLite L2 → FDA API L3)
- GPT-4.1 severity analysis (Critical/Moderate/Minor)

**Explain** (`api/services/explain_service.py`):
- Stage 1: GPT-4.1-mini extracts lab values / drug names as JSON
- Stage 2: Parallel lookups (LOINC, RxNorm, MedlinePlus)
- Stage 3: GPT-4.1 generates plain-language explanation with source badges

### Key Design Decisions
- **Language-aware everywhere**: `api/utils/language_detector.py` supports 10 languages (Unicode CJK/Hangul/Thai + keyword heuristics); answers are generated in the detected query language
- **Static export**: Next.js is configured with `output: 'export'` — no server-side rendering, all pages are statically generated
- **TEST_MODE**: Set `TEST_MODE=true` to bypass Clerk JWT validation during development
- **Data flywheel**: `UserFeedback` table (PostgreSQL) collects ratings for future fine-tuning; `is_vectorized` flag tracks which feedback has been incorporated

### Database Schema (`api/database/sql_models.py`)
- `AuditLog`: Every API call logged (user_id, action, query, IP)
- `ChatHistory`: Query/response pairs per user session
- `UserFeedback`: Ratings + text feedback with `is_reviewed`/`is_vectorized` flags

### Environment Variables
See `.env.example`. Required:
- `OPENAI_API_KEY` — GPT-4.1 and GPT-4.1-mini
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY` + `CLERK_JWKS_URL` — auth
- `DATABASE_URL` — PostgreSQL connection string
- `ALLOWED_ORIGINS` — CORS (e.g., `http://localhost:3000`)

## Frontend Notes

Pages live in `pages/` (Next.js pages router). Components in `components/`. The `@/` path alias maps to the project root.

Streaming responses use `@microsoft/fetch-event-source` on the frontend, `sse-starlette` on the backend.

The `CitationPanel` component handles citation display from Research responses; `MarkdownRenderer` renders streamed LLM output.
