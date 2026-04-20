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

### Current Development Status

**Phase**: Phase 0 — in progress (started 2026-04-17)

**Completed** (do not re-implement):
- 2.0 PostHog wrapper (`utils/analytics.ts` + `AnalyticsAuthBridge`, v143)
- 2.2 query_id via SSE (all 3 features emit query_id as first event, v144)
- 2.3 CitationPanel click tracking + FeedbackBar events (source_type lowercase canonical)
- 2.5 Landing Page SEO (isLoaded gate removed, JSON-LD in place)
- 2.6 i18n hreflang (Strategy A, 16 languages + x-default)
- 2.4 Bug 回報浮動按鈕 (`BugReportButton` FAB + `/api/bug-report` + PHI cleaning + rate limit 5/hour, production verified 2026-04-20 user_id=user_3BQM...)

**Next task** (choose one):
- 2.8 Anonymous Trial Flow (1.5-2d, Decision 001 v0.2 Accepted)
- 2.9 Verify 輸出語言對齊 user locale (1d, PRD § 2.9 Accepted)
- 2.7 Explain 臨床推理強化 (1-2d)
- 2.1 Model Provider Refactor (5-7d, 8 檔案)

### Phase 0 End Action (required before Phase 1A)

Before starting Phase 1A, conduct Phase 0 Retrospective:
- **Cost review**: actual OpenAI spend vs Decision 001 estimates; calibrate L0/L1 credit config if needed
- **Code health**: Sentry error rate, tech debt scan, Provider refactor regression check
- **Product health**: anonymous trial flow validation, PostHog funnel integrity, SEO verification
- **Deliverable**: create `docs/decisions/002-phase-0-retrospective.md` documenting findings and action items
- **Estimated effort**: 2.5-3 days

### Tech Debt (tracked for future resolution)

- **[P0 — Must resolve in 2.8]** localhost Clerk sign-in flow missing
  - Root cause: `_app.tsx` ClerkProvider 使用 Clerk Hosted mode (no `signInUrl` / `signUpUrl` props), localhost 無法登入建立 session
  - Evidence: 2.4 localhost testing 時,前端無法登入;curl 用 production `await Clerk.session.getToken()` 取新鮮 JWT 測試後端,user_id 正確寫入 DB (user_3BQM...) → 證明 code 正確,只是環境限制
  - Resolution in 2.8:
    1. 加 `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx`
    2. `_app.tsx` ClerkProvider 加 `signInUrl="/sign-in"` / `signUpUrl="/sign-up"` / fallback redirect URLs
    3. Rewrite `_optional_user_id()` as `require_auth_or_anonymous()` with explicit 3-tier handling for L0/L1/L2 (per Decision 001 v0.2 § 3.1)
    4. 補 AUTHORIZED_PARTIES config if Clerk SDK 要求

- **[P1] print() violations in api/** (54 處, audited 2026-04-19)
  - 生產路徑 9 處(影響 Sentry + log aggregation):
    - `fda.py:149/152/177` — FDA 請求失敗用 print 而非 logger
    - `simple_cache.py:90/111/179/183` — cache 事件(179/183 每次 cached call 都吵)
    - `vector_store.py:38/46` — 啟動 log;L46 含 ✅ emoji 在 Windows CP950 會爆
  - Test harness (`if __name__ == "__main__":`) 45 處,低優先
  - `fda_cached.py` 整檔為 dead code (CLAUDE.md 已標),可順手刪除
  - Resolution: 排入 Phase 0 Retrospective 一次清理

- **[P2] PowerShell 運行 `.env` parse warning**
  - `python-dotenv` 啟動時 warn `could not parse statement starting at line 1/2`
  - 不影響功能但 log 很吵
  - 可能原因:`.env` 檔 UTF-8 BOM,或前兩行有 shell export 語法
  - Resolution: Phase 0 Retrospective 清 .env 編碼

- **[P2] Chinese variant handling 已 spread(2026-04-20 完成),但 {response_language} pattern 仍不一致**
  - Verify 2.9 用 `{response_language}` 變數注入 system prompt
  - Research / Explain 用 `get_language_instruction()` append 到 user message
  - 兩套都 work,但 pattern 不一致,未來擴充語言 feature 要同步改兩處
  - Resolution: Phase 1A i18n mop-up 時統一 pattern(建議走 Verify 2.9 的 `{response_language}` 路線,同步 extract Research/Explain prompt to api/prompts/)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread

- **[P2] zh-TW / zh-CN severity Critical/Major 邊界 drift**
  - zh-TW dict: Critical=危急, Major=嚴重
  - zh-CN dict: Critical=严重, Major=重度
  - 兩套設計:zh-TW 是 Taiwan 醫療 triage 4 級視覺語彙,zh-CN 是結構對稱
  - Bilingual user 可能困惑(同字不同 severity)
  - Resolution: Phase 1A 找台灣 + 大陸母語醫療人員 review,決定統一或保留 drift

- **[P1] Research/Explain prompt 仍 inline 在 Python files(PRD § 6.5 違規)**
  - `generator.py` 有 4 個 inline prompt string(`_get_system_prompt` + `FALLBACK_PROMPTS` × 3)
  - `explain_service.py` 有 1 個 inline prompt(`EXPLAIN_GENERATION_PROMPT`)
  - 違反 PRD § 6.5 "All system prompts 在 api/prompts/ 目錄下獨立檔案"
  - 2.9 當下為了 scope 保護選擇 inline 編輯,未抽檔
  - Resolution: 2.7 Explain 臨床推理強化時順便 extract `explain_service.py`;Research 的 prompt extract 排 Phase 1A
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread diagnostic

- **[P2] Dead code in `api/rag/generator.py`**
  - `FALLBACK_PROMPTS["verify"]` (dict entry at line ~34): Verify 走 `api/prompts/verify_system.md` 不經 `generator.generate_stream`,此 key 從未被呼叫
  - `FALLBACK_PROMPTS["document"]` (dict entry at line ~34): 舊 patient-letter / consultation feature,全 codebase grep 無 caller
  - `_get_system_prompt()` `query_type == "verify"` branch (line ~263): 同上
  - Verification method: grep `query_type` + `FALLBACK_PROMPTS\[` 確認無活 caller,或 trace 從 /api endpoints 哪些 route 到 `generator.generate_stream`
  - Resolution: Phase 1A i18n mop-up 或 2.7 Explain 抽檔時順手 sweep dead code
  - Risk if kept: wasted maintenance attention, false impression for future readers, ~150-300 prompt tokens wasted per call (dead FALLBACK entries not triggered but pollute code)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread (diagnostic flagged)


### Discovered Gaps (action required)

- **G1. Anonymous Trial Flow** — Landing Page promises "No account required to try" but "Try it for free" redirects to Clerk sign-in. Must resolve before Phase 1A Week 1 LinkedIn launch (privacy-first manifesto post).
  - Full decision record: `docs/decisions/001-anonymous-trial-flow.md`
  - PRD section: § 2.8 (new)
  - Discovered: 2026-04-18
  - Status: Accepted (solo founder review, 2026-04-19)

**Remaining Phase 0**: 2.8 (1.5-2d) → 2.9 (1d) → 2.7 (1-2d) → 2.1 (5-7d, largest)

**Always consult `FEATURE_AUDIT.md` for latest codebase state before starting any task.**

## Planning Documents (READ FIRST)

When given a feature task, always consult these documents **before** touching code:

| Document | Purpose | Location |
|---|---|---|
| `docs/PRD.md` | Master PRD v1.2 — all functional specs, Phase 0/1A/1B/1C, acceptance criteria | `docs/PRD.md` |
| `FEATURE_AUDIT.md` | Codebase current state — what's built, what's partial, what's missing | `FEATURE_AUDIT.md` |

### Workflow for a new task

1. Read the relevant PRD section (requirements + acceptance + "not in scope")
2. Check `FEATURE_AUDIT.md` for current state — **do not re-implement what's already done**
3. Implement
4. Verify against PRD acceptance criteria, item by item
5. If implementation changed codebase state, update `FEATURE_AUDIT.md`
6. Commit message format: `[PRD X.Y] brief description` (e.g. `[PRD 2.0] Remove temp window.__vela_analytics exposure`)

## What This Project Is

Vela is a medical AI SaaS (Next.js 15 + FastAPI) deployed on Fly.io with three core features:
- **Research**: Query PubMed 36M+ articles with cited, streamed answers (GPT-4.1)
- **Verify**: Check drug interactions using FDA data with severity ratings (GPT-4.1-mini)
- **Explain**: Parse medical reports + PDF/image uploads into plain language via LOINC/RxNorm/MedlinePlus (GPT-4.1)

Pricing: $9.99/month or $89.99/year via Dodo Payments. Credit costs: Research=3, Verify=1, Explain=2.

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

## Architecture

### Request Flow
Every API call goes through: **Clerk JWT auth -> rate limiter -> 5-layer guard chain -> feature pipeline -> PostgreSQL audit log -> SSE stream**.

### 5-Layer Guard Chain (fail-close, cheapest-first)
`api/middleware/guards.py` — if any guard throws an exception, the request is **blocked** (fail-close), not allowed through.
1. Input length (5k char limit)
2. Regex injection patterns (EN/ZH/JA/AR + Base64 decode)
3. LLM indirect injection scan on retrieved content
4. Intent classification via GPT-4.1-mini (blocks non-medical queries)
5. PHI detection (Taiwan ID, Japan My Number, US SSN/MRN, email, phone)

PHI detection runs in the **route handler layer**, not middleware — moving it to middleware breaks SSE streaming.

### Three Pipelines

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

### Payments — Dodo Payments

**Checkout** (`POST /api/checkout/dodo`):
- Fetches user email + name from Clerk API, then calls `https://live.dodopayments.com/subscriptions`
- Returns a `payment_link` URL; frontend redirects the user there

**Webhook** (`POST /api/webhook/dodo`):
- Standard Webhooks signature verification (MANDATORY — rejects if `DODO_WEBHOOK_SECRET` is unset)
- HMAC-SHA256 with base64-decoded secret (strip `whsec_` prefix), replay protection (5 min)
- Handled events: `subscription.active` (-> pro), `subscription.cancelled`, `subscription.expired` (-> free)
- `WebhookEvent` table for idempotency

### Error Monitoring — Sentry

**Frontend**: `sentry.client.config.ts` — initialized via `withSentryConfig` in `next.config.ts`, `tracesSampleRate: 0.2`, production only. `tunnelRoute` omitted (incompatible with `output: 'export'`).

**Backend**: `api/server.py` top-level — `sentry_sdk.init()` with `FastApiIntegration` + `StarletteIntegration`, `send_default_pii=False`. Gracefully disabled when `SENTRY_DSN` is unset.

### Key Design Decisions
- **All OpenAI calls use AsyncOpenAI** — never sync `OpenAI()` in async code (blocks event loop). One module-level `openai_async_client = AsyncOpenAI()` in server.py, plus per-class instances in retriever/reranker/generator.
- **DB writes use `_safe_db_write()` helper** — handles add, commit, rollback, and error logging in one place. Never write raw try/except/commit blocks.
- **Language-aware everywhere**: `api/utils/language_detector.py` supports 16 languages (EN, ZH-TW, ZH-CN, JA, KO, ES, FR, DE, IT, PT, TH, AR, HI, BN, HE, VI); answers are generated in the detected query language.
- **Static export**: Next.js with `output: 'export'` — no SSR, all pages statically generated.
- **TEST_MODE**: Bypasses Clerk JWT validation. Blocked in production (when `FLY_APP_NAME` is set). Does NOT bypass rate limiting.
- **Data flywheel**: `UserFeedback` table collects ratings; `is_vectorized` flag tracks incorporation.
- **Audit log IDs**: `uuid4().hex[:16]` prefix format (e.g., `res_<hex>`, `ver_<hex>`, `fb_<hex>`).
- **Logging**: All server-side output uses `logging.getLogger()` — never `print()`.
- **Data cleanup**: Background task deletes AuditLog/ChatHistory older than 180 days (runs daily).
- **Connection pooling**: QueuePool with `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300` for Neon serverless PostgreSQL.

### Free vs Pro Feature Gating

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

### Research Evidence Strength

**Backend** (`api/rag/generator.py`): System prompt instructs LLM to place evidence emoji in each section header:
- Format: `## [SectionName 🟢 — Language]`
- Levels: 🟢 Strong (RCT/meta-analysis/guideline), 🟡 Moderate (observational/conditional), 🔴 Limited (case report/expert opinion)
- Each section judged independently — no separate Evidence section

**Frontend** (`pages/research.tsx`):
- `parseResearchSections()` regex extracts section name, emoji, and content
- `ResearchSection` component renders each section as a card with left color border (green/yellow/red)
- Falls back to plain ReactMarkdown for non-section responses (Verify, Explain, old format)
- Bottom legend with hover tooltips (desktop) and expandable info panel (mobile)

### Multilingual Disclaimer

Disclaimers are NOT generated by the LLM — they are rendered by the frontend based on detected language.

**Flow**: Backend `detect_language()` → SSE `{ type: 'language', lang: 'zh-TW' }` → frontend `DISCLAIMERS[detectedLang]`

- `generator.py` prompts explicitly say "Do NOT add any disclaimer"
- `stripLlmDisclaimer()` regex filters residual LLM disclaimers in all 16 languages (also applied in Explain responses)
- `DISCLAIMERS` map in `research.tsx` has entries for all 16 language codes matching `language_detector.py`
- All three features (Research, Verify, Explain) show disclaimer only after response completes (consistent behavior)

### Cost Tracking

`api/services/cost_tracker.py` — `log_api_cost_standalone()` creates its own `SessionLocal()` for pipeline components without request-scoped DB access.

5 tracking points (all wrapped in `try/except pass`):
1. `research/rewrite_query` — `api/rag/retriever.py`
2. `research/relevance_filter` — `api/rag/retriever.py`
3. `research/rerank` — `api/rag/reranker.py`
4. `research/llm_judge` — `api/utils/llm_judge.py`
5. `explain/entity_extraction` — `api/services/entity_extractor.py`

### Security Hardening Patterns

#### Rate Limiting (in-memory, per-IP)
- `RATE_LIMITS` dict maps path -> `(limit, window_seconds)`
- Feature endpoints 20-30 req/min, checkout 5/min, webhooks 30/min, admin 10/min
- Cleanup every 5 min to prevent unbounded memory growth
- `TEST_MODE` never bypasses rate limiting

#### CORS
- `ALLOWED_ORIGINS` env var (comma-separated), fallback `["http://localhost:3000"]` — never `["*"]`
- Methods: GET, POST only. Headers: Authorization, Content-Type only.

#### Webhook Signature Verification
- Dodo: Standard Webhooks spec, reject if secret unset, HMAC-SHA256, 5-min replay protection, idempotency table
- LemonSqueezy (legacy): X-Signature header, HMAC-SHA256 hex digest

#### Other
- Path traversal prevention: `resolve()` + `startswith` for static file serving
- Error message sanitization: never expose `str(e)` in API responses
- JWKS cache with 6-hour TTL
- Admin endpoint: `ADMIN_USER_ID` from env var, 403 if mismatch

### Database Schema (`api/database/sql_models.py`)
- `AuditLog`: Every API call (user_id, action, query, IP)
- `ChatHistory`: Query/response pairs per session
- `UserFeedback`: Ratings + text with `is_reviewed`/`is_vectorized` flags
- `UserUsage`: Plan type (free/pro), credit counts, subscription IDs
- `WebhookEvent`: Idempotency log (keyed by `event_id`)

### Key File Paths

**Backend**
- Main server: `api/server.py`
- Guard chain: `api/middleware/guards.py`
- PHI detection: `api/middleware/phi_handler.py`
- RAG pipeline: `api/rag/retriever.py`, `api/rag/generator.py`, `api/rag/reranker.py`
- FDA client: `api/data_sources/fda.py`
- PubMed client: `api/data_sources/pubmed.py`
- Explain service: `api/services/explain_service.py`
- Credit system: `api/services/usage_service.py`
- Cost tracker: `api/services/cost_tracker.py`
- Language detection: `api/utils/language_detector.py`
- LLM Judge: `api/utils/llm_judge.py`
- DB connection: `api/database/sql_db.py`
- DB models: `api/models/sql_models.py`

**Frontend**
- Page shell: `components/PageShell.tsx` (gradient + Navbar + auth wrapper + MobileNav)
- SSE utilities: `utils/sse.ts` (FatalError, makeOnOpen, sseOnError)
- Pages: `pages/research.tsx`, `pages/verify.tsx`, `pages/explain.tsx`, `pages/history.tsx`, `pages/pricing.tsx`, `pages/faq.tsx`
- Key components: `Navbar.tsx`, `PlanBadge.tsx`, `CitationPanel.tsx`, `OnboardingOverlay.tsx`, `UpgradeModal.tsx`, `FeedbackBar.tsx`, `PHIWarning.tsx`, `ProFeatureOverlay.tsx`, `ResearchSection.tsx`
- Export utility: `utils/exportPdf.ts` (html2pdf.js with window.print fallback)
- i18n translations: `utils/i18n.ts` (landing page translation map for 16 languages)

**Tests**
- Golden test runner: `tests/run_golden_tests.py`
- Golden dataset: `tests/golden_dataset.json` (127 cases)

**Dead files (kept for reference, not imported)**
- `api/data_sources/fda_cached.py` — old 3-layer cache, replaced by direct FDA calls
- `components/MarkdownRenderer.tsx` — unused, pages use ReactMarkdown directly

### Environment Variables

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

### Deployment — Fly.io

- Two machines, rolling deploy, primary region `nrt` (Tokyo)
- Frontend built at Docker build time: `npm run build` -> `/app/out` -> `COPY --from=frontend-builder /app/out ./static`
- `NEXT_PUBLIC_*` vars are **build-time** -> go in `fly.toml [build.args]`, not `[env]`
- Runtime secrets -> `fly secrets set KEY=value`
- FastAPI serves the static export via a catch-all file handler (`serve_nextjs_pages`)
- `FLY_APP_NAME` is injected automatically by Fly — used as Sentry `environment`

## Frontend Notes

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
