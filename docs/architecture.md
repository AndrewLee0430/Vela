# Vela Architecture

This document describes Vela's system architecture, deployed on Fly.io as a single Dockerized app combining Next.js (frontend, static export) + FastAPI (backend) + PostgreSQL (single source of truth).

## Quick Reference

- **Repo root**: see CLAUDE.md for build/test/deploy commands
- **Spec**: see docs/PRD.md for product requirements
- **State**: see STATE.md for current focus, BACKLOG.md for open work, ARCHIVE.md for shipped log
- **ADRs**: see docs/decisions/ for major decisions

## Sections

1. Product Overview (what this project is)
2. Request Flow (frontend → backend → external APIs)
3. Guard Chain (5-layer defense)
4. Feature Pipelines (Research / Verify / Explain)
5. Payments & Subscriptions (Dodo Payments)
6. Error Monitoring (Sentry)
7. Database Schema
8. Cost Tracking
9. Security Hardening
10. Multilingual Disclaimer Strategy
11. Research Evidence Strength
12. Free vs Pro Feature Gating
13. Frontend Notes
14. Environment Variables
15. Deployment (Fly.io)
16. Key Design Decisions

---

## 1. Product Overview

Vela is a medical AI SaaS (Next.js 15 + FastAPI) deployed on Fly.io with three core features:
- **Research**: Query PubMed 36M+ articles with cited, streamed answers (GPT-4.1)
- **Verify**: Check drug interactions using FDA data with severity ratings (GPT-4.1-mini)
- **Explain**: Parse medical reports + PDF/image uploads into plain language via LOINC/RxNorm/MedlinePlus (GPT-4.1)

Pricing: $9.99/month or $89.99/year via Dodo Payments. Credit costs: Research=3, Verify=1, Explain=2.

## 2. Request Flow

Every API call goes through: **Clerk JWT auth -> rate limiter -> 5-layer guard chain -> feature pipeline -> PostgreSQL audit log -> SSE stream**.

## 3. Guard Chain (fail-close, cheapest-first)

`api/middleware/guards.py` — if any guard throws an exception, the request is **blocked** (fail-close), not allowed through.
1. Input length (5k char limit)
2. Regex injection patterns (EN/ZH/JA/AR + Base64 decode)
3. LLM indirect injection scan on retrieved content
4. Intent classification via GPT-4.1-mini (blocks non-medical queries)
5. PHI detection (Taiwan ID, Japan My Number, US SSN/MRN, email, phone)

PHI detection runs in the **route handler layer**, not middleware — moving it to middleware breaks SSE streaming.

## 4. Feature Pipelines

**Research** (`api/rag/`):
- Query -> language detection -> rewrite to 3 medical English queries (GPT-4.1-mini)
- Parallel retrieval: 3 queries x 3 sources = 9 concurrent tasks via `asyncio.gather`
  - Sources: NumPy vector store (191 drugs) + PubMed API + FDA drug labels
- Deduplication + year-weighted scoring -> relevance filter (LLM) -> reranking (top_k=8)
- GPT-4.1 streaming generation with citations via SSE

**Verify** (`api/server.py` verify endpoint):
- Drug name parsing -> Levenshtein spell correction (custom impl, no external lib)
- Parallel FDA API lookups via `asyncio.gather` (initial + correction batches)
- GPT-4.1-mini severity analysis via AsyncOpenAI

**Explain** (`api/services/explain_service.py`):
- Stage 1: GPT-4.1-mini extracts lab values / drug names as JSON
- Stage 2: Parallel lookups (LOINC, RxNorm, MedlinePlus)
- Stage 3: GPT-4.1 generates plain-language explanation with source badges
- Supports PDF and image upload (client-side PDF.js + server-side GPT-4.1-mini OCR)
- LOINC source badges: not clickable, hover shows tooltip popover with per-item explanation
- RxNorm source badges: clickable, links to DailyMed

## 5. Payments — Dodo Payments

**Checkout** (`POST /api/checkout/dodo`):
- Fetches user email + name from Clerk API, then calls `https://live.dodopayments.com/subscriptions`
- Returns a `payment_link` URL; frontend redirects the user there

**Webhook** (`POST /api/webhook/dodo`):
- Standard Webhooks signature verification (MANDATORY — rejects if `DODO_WEBHOOK_SECRET` is unset)
- HMAC-SHA256 with base64-decoded secret (strip `whsec_` prefix), replay protection (5 min)
- Handled events: `subscription.active` (-> pro), `subscription.cancelled`, `subscription.expired` (-> free)
- `WebhookEvent` table for idempotency

## 6. Error Monitoring — Sentry

**Frontend**: `sentry.client.config.ts` — initialized via `withSentryConfig` in `next.config.ts`, `tracesSampleRate: 0.2`, production only. `tunnelRoute` omitted (incompatible with `output: 'export'`).

**Backend**: `api/server.py` top-level — `sentry_sdk.init()` with `FastApiIntegration` + `StarletteIntegration`, `send_default_pii=False`. Gracefully disabled when `SENTRY_DSN` is unset.

## 7. Database Schema (`api/database/sql_models.py`)

- `AuditLog`: Every API call (user_id, action, query, IP)
- `ChatHistory`: Query/response pairs per session
- `UserFeedback`: Ratings + text with `is_reviewed`/`is_vectorized` flags
- `UserUsage`: Plan type (free/pro), credit counts, subscription IDs
- `WebhookEvent`: Idempotency log (keyed by `event_id`)

## 8. Cost Tracking

`api/services/cost_tracker.py` — `log_api_cost_standalone()` creates its own `SessionLocal()` for pipeline components without request-scoped DB access.

5 tracking points (all wrapped in `try/except pass`):
1. `research/rewrite_query` — `api/rag/retriever.py`
2. `research/relevance_filter` — `api/rag/retriever.py`
3. `research/rerank` — `api/rag/reranker.py`
4. `research/llm_judge` — `api/utils/llm_judge.py`
5. `explain/entity_extraction` — `api/services/entity_extractor.py`

## 9. Security Hardening Patterns

### Rate Limiting (in-memory, per-IP)
- `RATE_LIMITS` dict maps path -> `(limit, window_seconds)`
- Feature endpoints 20-30 req/min, checkout 5/min, webhooks 30/min, admin 10/min
- Cleanup every 5 min to prevent unbounded memory growth
- `TEST_MODE` bypasses rate limiting (test runner makes 40+ requests in <5 min). Production guard at server.py:305-308 prevents `TEST_MODE=true` from running in prod.

### CORS
- `ALLOWED_ORIGINS` env var (comma-separated), fallback `["http://localhost:3000"]` — never `["*"]`
- Methods: GET, POST only. Headers: Authorization, Content-Type only.

### Webhook Signature Verification
- Dodo: Standard Webhooks spec, reject if secret unset, HMAC-SHA256, 5-min replay protection, idempotency table
- LemonSqueezy (legacy): X-Signature header, HMAC-SHA256 hex digest

### Other
- Path traversal prevention: `resolve()` + `startswith` for static file serving
- Error message sanitization: never expose `str(e)` in API responses
- JWKS cache with 6-hour TTL
- Admin endpoint: `ADMIN_USER_ID` from env var, 403 if mismatch

## 10. Multilingual Disclaimer

Disclaimers are NOT generated by the LLM — they are rendered by the frontend based on detected language.

**Flow**: Backend `detect_language()` → SSE `{ type: 'language', lang: 'zh-TW' }` → frontend `DISCLAIMERS[detectedLang]`

- `generator.py` prompts explicitly say "Do NOT add any disclaimer"
- `stripLlmDisclaimer()` regex filters residual LLM disclaimers in all 16 languages (also applied in Explain responses)
- `DISCLAIMERS` map in `research.tsx` has entries for all 16 language codes matching `language_detector.py`
- All three features (Research, Verify, Explain) show disclaimer only after response completes (consistent behavior)

## 11. Research Evidence Strength

**Backend** (`api/rag/generator.py`): System prompt instructs LLM to place evidence emoji in each section header:
- Format: `## [SectionName 🟢 — Language]`
- Levels: 🟢 Strong (RCT/meta-analysis/guideline), 🟡 Moderate (observational/conditional), 🔴 Limited (case report/expert opinion)
- Each section judged independently — no separate Evidence section

**Frontend** (`pages/research.tsx`):
- `parseResearchSections()` regex extracts section name, emoji, and content
- `ResearchSection` component renders each section as a card with left color border (green/yellow/red)
- Falls back to plain ReactMarkdown for non-section responses (Verify, Explain, old format)
- Bottom legend with hover tooltips (desktop) and expandable info panel (mobile)

## 12. Free vs Pro Feature Gating

| Feature | Free | Pro |
|---|---|---|
| Credits | 10/day | 100/day |
| History | Last 7 days | Last 365 days + search |
| Explain upload | Text only | PDF + image (OCR) |
| Export | Locked | PDF with Vancouver citations |

Credit costs per query: Research=3, Verify=1, Explain=2.

**Pro detection pattern** (consistent across all feature pages):
1. `useState` initializer reads `vela_plan_cache` from localStorage (5-min TTL) for anti-flash
2. `useEffect` fetches `/api/user/status` for ground truth, calls `setPlan()`
3. `PlanBadge` (in Navbar) is the only component that writes `vela_plan_cache`
4. `ProFeatureOverlay` receives `isLocked` prop — never reads plan itself

**ProFeatureOverlay** (`components/ProFeatureOverlay.tsx`):
- Hover-triggered tooltip popover (desktop), click-triggered (mobile)
- Children rendered at `opacity-50 cursor-not-allowed`, `pointerEvents: none`
- Wrapper is `w-full` (important for History search box and Explain upload alignment)
- 200ms enter delay / 150ms leave delay to prevent flicker
- Not an overlay — no backdrop blur, no full-area coverage

**Backend enforcement**:
- `/api/history`: Free=7 days, Pro=365 days via `UserUsage.plan_type` DB query
- `/api/explain/extract-image`: Returns 403 `{ type: "pro_required" }` for free users
- Export is frontend-only gating (no backend endpoint)

## 13. Frontend Notes

Pages router (`pages/`), components in `components/`, `@/` alias maps to project root.

Streaming: `@microsoft/fetch-event-source` (frontend) + `sse-starlette` (backend).

Markdown: `react-markdown` + `remark-gfm` + `remark-breaks` + `rehype-raw` (for HTML passthrough in evidence sections).

PDF export: `html2pdf.js` (dynamic import, fallback to `window.print()`).

### Shared Patterns
- **PageShell** (`components/PageShell.tsx`): All authenticated pages use this wrapper (gradient bg + Navbar + auth + MobileNav). Accepts `activePage` and optional `extraHead`.
- **SSE utilities** (`utils/sse.ts`): `FatalError`, `makeOnOpen()` (handles 400/403/429), `sseOnError()` — shared by research.tsx and explain.tsx.
- **PlanBadge anti-flash**: Synchronous `localStorage` read in `useState` initializer prevents "Upgrade" flash on navigation.
- **OnboardingOverlay**: SVG mask spotlight, shown once via `localStorage.hasSeenOnboarding`.

### SEO
- `public/robots.txt` + `public/sitemap.xml` (static pages)
- Meta tags in `pages/_app.tsx` via `next/head`
- `og:image` at `public/og-image.png` (1200x630)

### Landing Page (`pages/index.tsx`)
- **Multilingual switcher**: 16 languages via `utils/i18n.ts` translation map, RTL support for Arabic/Hebrew
- **Typewriter prompt**: Cycles through Research/Verify/Explain example prompts
- **Product showcase**: Three mockup cards (Research/Verify/Explain) with unified structure: query + badge + source label + CTA. No duplicate feature cards below.
- **Social proof bar**: "Every answer cited" tagline below CTA
- **Footer**: "© 2026 Vela. All rights reserved. · an-tho.com"
- **Auth-aware**: Shows `LandingPage` when signed out, `Dashboard` when signed in

### FAQ Page (`pages/faq.tsx`)
- Public page, no auth required
- 15 Q&A items in accordion format, English only
- Covers product features, pricing, privacy, and technical questions

## 14. Environment Variables

See `.env.example`. Required:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | GPT-4.1 and GPT-4.1-mini |
| `CLERK_SECRET_KEY` | Clerk backend auth |
| `CLERK_JWKS_URL` | JWKS endpoint for JWT verification |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk frontend (build-time) |
| `DATABASE_URL` | PostgreSQL connection string |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) |
| `DODO_API_KEY` | Dodo Payments live API key |
| `DODO_WEBHOOK_SECRET` | Standard Webhooks secret (`whsec_...`) |
| `ADMIN_USER_ID` | Clerk user ID for admin access |

Optional: `FDA_API_KEY`, `PUBMED_API_KEY`, `NCBI_EMAIL`, `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`, `NEXT_PUBLIC_API_URL`.

Dev-only: `TEST_MODE` (bypass auth), `TEST_USER_ID` (mock user ID).

**Local `.env.local`**: Contains `NEXT_PUBLIC_API_URL=https://vela-ai-medical.fly.dev` for deploy builds. For local testing, change to `http://localhost:8000`, but Clerk auth issues make it easier to just deploy and test in production.

## 15. Deployment — Fly.io

- Two machines, rolling deploy, primary region `nrt` (Tokyo)
- Frontend built at Docker build time: `npm run build` -> `/app/out` -> `COPY --from=frontend-builder /app/out ./static`
- `NEXT_PUBLIC_*` vars are **build-time** -> go in `fly.toml [build.args]`, not `[env]`
- Runtime secrets -> `fly secrets set KEY=value`
- FastAPI serves the static export via a catch-all file handler (`serve_nextjs_pages`)
- `FLY_APP_NAME` is injected automatically by Fly — used as Sentry `environment`

## 16. Key Design Decisions

- **All OpenAI calls use AsyncOpenAI** — never sync `OpenAI()` in async code (blocks event loop). One module-level `openai_async_client = AsyncOpenAI()` in server.py, plus per-class instances in retriever/reranker/generator.
- **DB writes use `_safe_db_write()` helper** — handles add, commit, rollback, and error logging in one place. Never write raw try/except/commit blocks.
- **Language-aware everywhere**: `api/utils/language_detector.py` supports 16 languages (EN, ZH-TW, ZH-CN, JA, KO, ES, FR, DE, IT, PT, TH, AR, HI, BN, HE, VI); answers are generated in the detected query language.
- **Static export**: Next.js with `output: 'export'` — no SSR, all pages statically generated.
- **TEST_MODE**: Bypasses both auth (returns hardcoded `test_user` via `require_auth`) and rate limiting. Production guard at backend startup raises `RuntimeError` if `TEST_MODE=true` with `FLY_APP_NAME` set — process won't start.
- **Data flywheel**: `UserFeedback` table collects ratings; `is_vectorized` flag tracks incorporation.
- **Audit log IDs**: `uuid4().hex[:16]` prefix format (e.g., `res_<hex>`, `ver_<hex>`, `fb_<hex>`).
- **Logging**: All server-side output uses `logging.getLogger()` — never `print()`.
- **Data cleanup**: Background task deletes AuditLog/ChatHistory older than 180 days (runs daily).
- **Connection pooling**: QueuePool with `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300` for Neon serverless PostgreSQL.
