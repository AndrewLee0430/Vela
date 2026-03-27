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
- GPT-4.1-mini severity analysis via AsyncOpenAI (non-blocking)

**Explain** (`api/services/explain_service.py`):
- Stage 1: GPT-4.1-mini extracts lab values / drug names as JSON
- Stage 2: Parallel lookups (LOINC, RxNorm, MedlinePlus)
- Stage 3: GPT-4.1 generates plain-language explanation with source badges

### Payments — Dodo Payments

**Checkout** (`POST /api/checkout/dodo`):
- Fetches user email + name from Clerk API, then calls `https://live.dodopayments.com/subscriptions`
- Returns a `payment_link` URL; frontend redirects the user there
- Required payload fields: `product_id`, `quantity`, `customer` (with `email` + `name`), `billing` (with `country`)

**Webhook** (`POST /api/webhook/dodo`):
- Implements [Standard Webhooks](https://www.standardwebhooks.com/) signature verification (MANDATORY — rejects if `DODO_WEBHOOK_SECRET` is unset)
- Three headers required: `webhook-id`, `webhook-timestamp`, `webhook-signature`
- Signed payload: `{webhook-id}.{webhook-timestamp}.{raw_body}`, HMAC-SHA256, base64-encoded
- Secret: base64-decode after stripping `whsec_` prefix
- Replay protection: rejects `webhook-timestamp` older than 5 minutes
- Handled events: `subscription.active` (→ pro), `subscription.cancelled`, `subscription.expired` (→ free)
- Uses `WebhookEvent` table for idempotency

### Error Monitoring — Sentry

**Frontend** (`sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`):
- Initialized via `withSentryConfig` in `next.config.ts`
- `tracesSampleRate: 0.2`, enabled only in production
- DSN from `NEXT_PUBLIC_SENTRY_DSN` (build-time arg in `fly.toml [build.args]`)
- Note: `tunnelRoute` is omitted — incompatible with `output: 'export'`

**Backend** (`api/server.py` top-level):
- `sentry_sdk.init()` with `FastApiIntegration` + `StarletteIntegration`
- `environment` set to `FLY_APP_NAME`, `send_default_pii=False`
- Gracefully disabled when `SENTRY_DSN` is unset

### Key Design Decisions
- **Language-aware everywhere**: `api/utils/language_detector.py` supports 10 languages (Unicode CJK/Hangul/Thai + keyword heuristics); answers are generated in the detected query language
- **Static export**: Next.js is configured with `output: 'export'` — no server-side rendering, all pages are statically generated
- **TEST_MODE**: Set `TEST_MODE=true` to bypass Clerk JWT validation during development. Does NOT bypass rate limiting.
- **Data flywheel**: `UserFeedback` table (PostgreSQL) collects ratings for future fine-tuning; `is_vectorized` flag tracks which feedback has been incorporated
- **Audit log IDs**: Use `uuid4().hex[:16]` prefix format (e.g., `res_<hex>`, `ver_<hex>`, `fb_<hex>`)

### Database Schema (`api/database/sql_models.py`)
- `AuditLog`: Every API call logged (user_id, action, query, IP)
- `ChatHistory`: Query/response pairs per user session
- `UserFeedback`: Ratings + text feedback with `is_reviewed`/`is_vectorized` flags
- `UserUsage`: Per-user plan type (`free`/`pro`), credit counts, subscription IDs
- `WebhookEvent`: Idempotency log for Dodo and LemonSqueezy webhooks (keyed by `event_id`)

### Environment Variables
See `.env.example`. Required:

**AI / Core**
- `OPENAI_API_KEY` — GPT-4.1 and GPT-4.1-mini

**Auth**
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY` + `CLERK_JWKS_URL` — Clerk auth
- `ADMIN_USER_ID` — Clerk user ID that can access `/api/admin/costs`

**Database**
- `DATABASE_URL` — PostgreSQL connection string

**Networking**
- `ALLOWED_ORIGINS` — CORS (e.g., `https://vela.an-tho.com`)

**Payments**
- `DODO_API_KEY` — Dodo Payments live API key
- `DODO_WEBHOOK_SECRET` — Standard Webhooks secret (`whsec_...`), used for HMAC-SHA256 verification

**Monitoring**
- `SENTRY_DSN` — Backend Sentry DSN (runtime, set as Fly secret)
- `NEXT_PUBLIC_SENTRY_DSN` — Frontend Sentry DSN (build-time, set in `fly.toml [build.args]`)

**Optional**
- `FDA_API_KEY`, `PUBMED_API_KEY`, `NCBI_EMAIL` — Data source APIs
- `NEXT_PUBLIC_POSTHOG_KEY` + `NEXT_PUBLIC_POSTHOG_HOST` — Analytics

## Frontend Notes

Pages live in `pages/` (Next.js pages router). Components in `components/`. The `@/` path alias maps to the project root.

Streaming responses use `@microsoft/fetch-event-source` on the frontend, `sse-starlette` on the backend.

### Key Components

| Component | Description |
|---|---|
| `components/Navbar.tsx` | Shared top navigation bar used by all authenticated pages (research, verify, explain, history). Highlights the active page. |
| `components/PlanBadge.tsx` | Displays PRO badge or Upgrade button. Reads plan from `localStorage` cache (`vela_plan_cache`, 5-min TTL) synchronously on mount to prevent flash. Fetches fresh from `/api/user/status` in background. Exports `clearPlanCache()` for use after plan changes. |
| `components/CitationPanel.tsx` | Citation cards for Research results. Credibility badges (Peer Reviewed / Official / Internal) show custom hover tooltips (white card + checkmark). |
| `components/OnboardingOverlay.tsx` | 4-step spotlight onboarding shown once to new users (tracked via `localStorage.hasSeenOnboarding`). Uses SVG mask cutout to highlight dashboard cards. Steps: Welcome → Research → Verify → Explain. Step 1 body adapts based on `plan_type` from `/api/user/status`. |
| `components/MarkdownRenderer.tsx` | Renders streamed LLM output with syntax highlighting. |
| `components/UpgradeModal.tsx` | Upgrade CTA modal with plan comparison and Dodo Payments checkout integration. |
| `components/FeedbackBar.tsx` | Thumbs up/down + text feedback, posts to `/api/feedback`. |
