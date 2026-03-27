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
- **Logging**: All server-side output uses `logging.getLogger("vela")` — never `print()`. Levels: `logger.info` (normal flow), `logger.warning` (degraded but non-fatal), `logger.error` (failures).
- **Shared AsyncOpenAI client**: One module-level `openai_async_client = AsyncOpenAI()` instance reused across all endpoints — never instantiate per-request.

### Security Hardening Patterns

This section documents every hardening decision applied to Vela. Reuse these patterns in future products.

#### Rate Limiting (in-memory, per-IP)
`api/server.py` — `RATE_LIMITS` dict maps path → `(limit, window_seconds)`. The middleware:
- Covers **all** sensitive endpoints: feature APIs, checkout, webhooks, admin
- Defaults: feature endpoints 20–30 req/min, checkout 5/min, webhooks 30/min, admin 10/min
- Uses `defaultdict(list)` storing timestamps; slides the window each request
- **Cleanup**: every 5 minutes, keys whose last timestamp is older than `max_window` are deleted to prevent unbounded memory growth
- `TEST_MODE` never bypasses rate limiting (auth-only bypass)

#### CORS
- `ALLOWED_ORIGINS` env var — comma-separated list (e.g., `https://vela.an-tho.com`)
- Fallback when unset: `["http://localhost:3000"]` — **never `["*"]`** (wildcard + `allow_credentials=True` is a security violation)
- Methods: `GET`, `POST` only. Headers: `Authorization`, `Content-Type` only.

#### Webhook Signature Verification

**Dodo Payments (Standard Webhooks spec)**:
- Reject immediately if `DODO_WEBHOOK_SECRET` is unset (500, not silently accept)
- Three headers: `webhook-id`, `webhook-timestamp`, `webhook-signature`
- Signed payload: `f"{webhook_id}.{webhook_timestamp}.{raw_body}"`
- HMAC-SHA256 with base64-decoded secret (strip `whsec_` prefix first), digest is base64-encoded
- Replay protection: reject if `webhook-timestamp` is older than 5 minutes
- Idempotency: check `WebhookEvent` table before processing, insert after

**LemonSqueezy**:
- Reject immediately if `LEMON_SQUEEZY_SIGNING_SECRET` is empty
- Single `X-Signature` header, HMAC-SHA256 hex digest
- Parse body from already-read `body_bytes` (not `await request.json()` again — body stream is consumed)

#### Path Traversal Prevention
When serving static files via FastAPI `FileResponse`, always validate the resolved path:
```python
resolved_root = Path("./static").resolve()

def _safe(p: Path) -> bool:
    try:
        return str(p.resolve()).startswith(str(resolved_root))
    except (OSError, ValueError):
        return False
```
Blocklist approaches (checking for `..`) are insufficient — always use `resolve()` + `startswith`.

#### Error Message Sanitization
- Never expose `str(e)` in API responses — leak internal details
- Return generic messages: `{"detail": "Internal server error"}`
- Log full error internally with `logger.error()`

#### JWT / JWKS
- Cache JWKS with a 6-hour TTL (`_jwks_cache_ts`) — prevents hammering Clerk on every request, handles key rotation without restart
- Verify with `python-jose`, `algorithms=["RS256"]`, `verify_aud=False` (Clerk doesn't set aud)

#### Input Guard Chain (`api/middleware/guards.py`)
Ordered cheapest-first to minimize LLM cost:
1. Input length check (5k char limit)
2. Regex injection scan (EN/ZH/JA/AR + Base64 decode)
3. LLM indirect injection scan on retrieved content
4. Intent classification via GPT-4.1-mini (blocks non-medical)
5. PHI detection (Taiwan ID, Japan My Number, US SSN/MRN)

#### Admin Endpoint Protection
- `ADMIN_USER_ID` from env var — never hardcoded
- Rate-limited to 10 req/min
- Returns 403 if caller's `sub` ≠ `ADMIN_USER_ID`

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

### Deployment — Fly.io

- Two machines, rolling deploy strategy (`flyctl deploy`)
- Frontend built at Docker build time: `npm run build` → `/app/out` → `COPY --from=frontend-builder /app/out ./static`
- `NEXT_PUBLIC_*` vars are **build-time** → go in `fly.toml [build.args]`, not `[env]`
- Runtime secrets (`OPENAI_API_KEY`, `SENTRY_DSN`, etc.) → `fly secrets set KEY=value`
- FastAPI serves the Next.js static export via a catch-all file handler (`serve_nextjs_pages`)
- `FLY_APP_NAME` env var is injected automatically — used as Sentry `environment`

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

### Frontend Anti-Flash Patterns

**PlanBadge (plan state)**: Read `localStorage` synchronously in `useState` initializer to avoid "Upgrade" flash on navigation:
```typescript
const [plan, setPlan] = useState<'free' | 'pro' | null>(() => {
    if (typeof window === 'undefined') return null;
    return readCache(); // localStorage read
});
```
Return `null` while loading — render nothing until state is known.

**OnboardingOverlay (spotlight)**: SVG mask with a transparent cutout over the highlighted element:
```svg
<mask id="spotlight-mask">
  <rect width="100%" height="100%" fill="white" />
  <rect x={...} y={...} width={...} height={...} rx="12" fill="black" />
</mask>
```
Track `hasSeenOnboarding` in `localStorage` so it shows only once.

### SEO Baseline

- `public/robots.txt` — allow all crawlers, points to `/sitemap.xml`
- `public/sitemap.xml` — static pages: `/`, `/terms`, `/privacy`, `/refund`
- Meta tags in `pages/_app.tsx` via `next/head` — **not** next-seo (v7 removed `DefaultSeo`/`NextSeo`, now JSON-LD only)
- `og:image` at `public/og-image.png` (1200×630)

## Reusable Stack for New Products

This is the full proven stack from Vela. Copy as a starting point:

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js 15 (pages router, `output: 'export'`) | Static export — no SSR needed for most SaaS |
| Backend | FastAPI + uvicorn | Python async, easy streaming with `sse-starlette` |
| Auth | Clerk | JWT via JWKS, `TEST_MODE` for local dev |
| Database | PostgreSQL + SQLAlchemy | Fly Postgres or Supabase |
| Payments | Dodo Payments | Standard Webhooks spec, `whsec_` HMAC-SHA256 |
| Error Monitoring | Sentry | `FastApiIntegration` backend, `withSentryConfig` frontend |
| Analytics | PostHog | `NEXT_PUBLIC_POSTHOG_KEY` env var |
| Hosting | Fly.io | 2 machines, rolling deploy, `fly secrets` for runtime env |
| AI | OpenAI GPT-4.1 + GPT-4.1-mini | 4.1 for generation, 4.1-mini for classification/extraction |
| Streaming | `@microsoft/fetch-event-source` (FE) + `sse-starlette` (BE) | Token-by-token SSE |

### Checklist When Starting a New Product

Security baseline (copy from Vela):
- [ ] Rate limiting middleware covering all endpoints
- [ ] CORS with explicit `ALLOWED_ORIGINS` env var (fallback to localhost only)
- [ ] Webhook signature verification with mandatory secret check
- [ ] Path traversal prevention for any file serving
- [ ] Generic error messages (never expose `str(e)`)
- [ ] `logging` module instead of `print()`
- [ ] JWKS cache with TTL
- [ ] Audit log table (user_id, action, query, IP)
- [ ] `WebhookEvent` idempotency table
- [ ] `ADMIN_USER_ID` from env var

Frontend baseline:
- [ ] `PlanBadge` with synchronous localStorage read to prevent flash
- [ ] SEO: robots.txt + sitemap.xml + meta tags in `_app.tsx`
- [ ] `OnboardingOverlay` shown once via localStorage flag
- [ ] `Navbar` with active page highlight
- [ ] `UpgradeModal` wired to checkout endpoint
