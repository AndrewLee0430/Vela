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
- 2.7 Explain 臨床推理強化 — ✅ DONE (Steps 1-8 + Path 1 RAG defense + M06 fix). Steps 1-6 shipped 2026-04-27 (19 commits). Steps 7-8 acceptance complete 2026-04-30 (commits c5b3a09 ExplainJudge class, 64c72f2 TEST_MODE rate-limit bypass, fa80ff9 acceptance integration, a52bf9f M06 fix). Acceptance run: 121/127 (95.3%) overall, hard floor 100%, 0 regressions. Path 1 RAG defense layers (post Step 8 + M06): Layer 1 prompt v5 (verified-only citations), Layer 2 schema (PUBMED enum disabled), Layer 3 _filter_citations_in_dict (drop fabricated URLs), Layer 4 _normalize_explain_items (null value coercion — Bug M06).
- 2.0 PostHog wrapper (`utils/analytics.ts` + `AnalyticsAuthBridge`, v143)
- 2.2 query_id via SSE (all 3 features emit query_id as first event, v144)
- 2.3 CitationPanel click tracking + FeedbackBar events (source_type lowercase canonical)
- 2.5 Landing Page SEO (isLoaded gate removed, JSON-LD in place)
- 2.6 i18n hreflang (Strategy A, 16 languages + x-default)
- 2.4 Bug 回報浮動按鈕 (`BugReportButton` FAB + `/api/bug-report` + PHI cleaning + rate limit 5/hour, production verified 2026-04-20 user_id=user_3BQM...)
- 2.9 Verify 輸出語言對齊 user locale (response_language variable + prompt v2.1 + 7 languages i18n + UX polish + Chinese variant handling spread) — 2026-04-20 production verified
- 2.8 Anonymous Trial Flow (Rounds 1-3 shipped 2026-04-22, prod verified) — sign-in/sign-up pages + AnonymousUpgradeCTA + ExplainLockedForAnonymous + tier super-property + anonymous_to_registered alias

**Phase 1A polish pre-shipped** (during § 2.7 Step 6 Phase 6B unified rollout, 2026-04-27):
- Research completion-event telemetry (6a53dfc — research_completed + research_failed events with citation_count, evidence_distribution, used_fallback, elapsed_ms, backend_query_time_ms)
- Verify completion-event telemetry (dd128e2 — verify_completed + verify_failed events with interaction_count, severity_distribution, response_language, elapsed_ms; input_language intentionally omitted per language-agnostic input nature)
- TODO follow-ups logged: SSE payload type contract, Verify spelling_corrections structured field (in TODO.md "Phase 1A polish — telemetry & SSE contract follow-ups")

**Next task** (choose one):
- 2.1 Model Provider Refactor (5-7d, 9 檔案 — largest remaining Phase 0 block)
- 3.1 User Context schema (NOT_STARTED, blocks Phase 1A)

### Phase 0 End Action (required before Phase 1A)

Before starting Phase 1A, conduct Phase 0 Retrospective:
- **Cost review**: actual OpenAI spend vs Decision 001 estimates; calibrate L0/L1 credit config if needed
- **Code health**: Sentry error rate, tech debt scan, Provider refactor regression check
- **Product health**: anonymous trial flow validation, PostHog funnel integrity, SEO verification
- **Deliverable**: create `docs/decisions/002-phase-0-retrospective.md` documenting findings and action items
- **Estimated effort**: 2.5-3 days

### Tech Debt (tracked for future resolution)

- **[P0 — Must resolve in 2.8]** localhost Clerk sign-in flow missing
  - **Partial progress**: Auth split (require_auth + require_auth_or_anonymous) completed in Round 1 (7a8c5a8). Remaining 3 items for Round 2 (frontend sign-in pages + ClerkProvider config + Clerk SDK config verification).
  - Root cause: `_app.tsx` ClerkProvider 使用 Clerk Hosted mode (no `signInUrl` / `signUpUrl` props), localhost 無法登入建立 session
  - Evidence: 2.4 localhost testing 時,前端無法登入;curl 用 production `await Clerk.session.getToken()` 取新鮮 JWT 測試後端,user_id 正確寫入 DB (user_3BQM...) → 證明 code 正確,只是環境限制
  - Resolution in 2.8:
    1. 加 `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx`
    2. `_app.tsx` ClerkProvider 加 `signInUrl="/sign-in"` / `signUpUrl="/sign-up"` / fallback redirect URLs
    3. 補 AUTHORIZED_PARTIES config if Clerk SDK 要求

- **[P1 → Round 2B + 3 完成後一起 E2E 測試]** Clerk email sign-up/sign-in end-to-end 驗證
  - **背景**: 2026-04-22 localhost /sign-in 已確認 Clerk Development instance 有 email input(切 Dev instance + 啟用 email code verification 後解決)。Production instance email 設定也已確認 ON。
  - **尚未驗證**:
    - Email code 能否真的發到使用者信箱(依賴 Clerk email 發送能力)
    - 新使用者透過 email 註冊 → Clerk user 建立 → backend JWT 驗證成功 → /research 能載入
    - Email 與 SSO Google 同一 email 時,Clerk 如何處理(期待:同一 Clerk user)
  - **測試順序**(Round 2B + 3 完成後一起做):
    1. 無痕視窗 /sign-up → 輸入全新 email → 收 code → 輸入 → 完成註冊 → redirect /research
    2. 無痕視窗 /sign-in → 輸入 #1 註冊的 email → 收 code → 登入成功
    3. 新 email 註冊 → logout → 改用同 email Google SSO → 看 Clerk 是否合併 user
  - **Priority**: P1(2.8 完整驗收一部分),軟啟動前必須通過
  - **Discovered**: 2026-04-22 during Clerk Dev/Prod instance diagnostic

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

- **[P0 → 明天(2026-04-21) 優先]** Landing Page 收尾
  - 發現 2026-04-20(2.9 ship 後)
  - **兩個問題:**
    1. **Hero placeholder 硬寫英文**
       - 當前:"Verify Warfarin + Aspirin — is it..." 等 rotating examples 全英文
       - 問題:UI 切繁中後仍顯示英文 placeholder,違反 "Ask in any language" 品牌承諾
       - 範圍:輪播多個 examples × 7 語言 = N × 7 translations
       - 依賴:需先 enumerate 目前有幾條 placeholder examples,再做 i18n 擴充
    2. **Privacy section 過長**
       - 當前:5 條「我們承諾」+ 3 條「它不代表什麼」,共 8 個 bullet
       - 問題:Landing Page 應為 conversion page,列限制 = anti-conversion;5 條承諾也偏多
       - 決策(solo founder 2026-04-20 review):
         - **刪除**:3 條「它不代表什麼」全部(移至 Privacy Policy 處理,該頁為 Phase 1A i18n mop-up)
         - **壓縮**:5 條承諾 → 3 條(採下列版本):
           - ✓ 不需驗證身分或執照
           - ✓ 預設匿名,不要求真實姓名
           - ✓ 資料不外流、不訓練 AI 模型
         - **移除**的 2 條(偏好設定本地儲存、不販售資料第 4 條)其實併到第 3 條
  - **執行預期工期:**
    - Landing Page placeholder i18n 化:30-60 分鐘(輪播 N 條 × 7 語言)
    - Privacy section 簡化 + i18n:30-40 分鐘
    - 總計:約 1-2 小時
  - **依賴與阻塞:** 無外部依賴,可於 2.8 開工前插入;建議排序:明天(2026-04-21)開工 2.8 前完成 Landing Page 修復
  - **備註:** 本條 tech debt 屬「Phase 0 收尾 polish」性質,非新 PRD 需求。工時小可直接執行,不需單獨 ADR

- **[P1 → Phase 0 Retrospective]** CLAUDE.md 結構性精簡
  - 問題:
    - 當前 ~400 行,違反 LLM instruction budget 最佳實踐(社群共識 < 300 行)
    - 多處內容為 reference material 而非 instruction(architecture 詳細、env vars、file paths),違反 Progressive Disclosure pattern
    - Current Development Status / Discovered Gaps 與 FEATURE_AUDIT.md / decision docs 有 drift 風險
  - 不現在做的理由:
    - Claude Code 在當前 CLAUDE.md 長度下仍能交付 staff-engineer level 品質(2.4 / 2.9 / Landing Page 已驗證)
    - 重構會花 3-4 小時,與 2.8 / 2.7 / 2.1 GTM 排程衝突
    - Phase 0 Retrospective 本來就要 review code health,重構 CLAUDE.md 在那時 sync 最自然(可併入 "code health" section)
  - 解法(Phase 0 Retrospective 執行):
    1. 拆 CLAUDE.md 成三份:
       - CLAUDE.md (~150-180 lines, active instructions only)
       - TECH_DEBT.md (new, historical + open items, CLAUDE.md 只指 active items)
       - docs/architecture.md (new, 5-layer guards / pipelines / payments / DB / env / deploy / frontend)
    2. 保留項:Collaboration Principles 含 Examples(few-shot anchoring 效果,不是歷史紀錄)、Important Rules 16 條、Commands、Workflow
    3. 刪除項:Key File Paths(Claude 自己 grep)、Current Development Status(由 FEATURE_AUDIT 取代)、Discovered Gaps(由 decision docs 取代)
    4. Active Tech Debt 變動態區塊:只列「下個 task 要看的 1-3 條」,其他移 TECH_DEBT.md
  - 驗收:開新 Claude Code session 問它 "project structure",能正確描述 + 知道去哪看細節
  - Discovered: 2026-04-21(Landing Page ship 後 solo founder 討論 instruction budget best practice 時識別)

- **[P2]** Clerk JWT authorized_parties (azp) claim 未驗證
  - **現況**: `api/server.py` 使用 hand-rolled `jose_jwt.decode` with `options={"verify_aud": False}`,依賴 JWKS RS256 簽名驗證 + issuer 隱式信任。未檢查 `azp` claim。
  - **風險**: 理論上若攻擊者能取得 Clerk 公開 JWKS 並知道 issuer,可能能 forge token 通過 signature verify。實務上極難(需拿到使用者 session token 或攻破 Clerk infra),但 defense-in-depth 標準作業應驗證 authorized_parties。
  - **Resolution**:
    - 新建 `CLERK_AUTHORIZED_PARTIES` env var(allowlist of origin URLs)
    - `api/server.py` JWT decode 後手動檢查 `azp` claim 在 allowlist 中
    - 或:改用 `fastapi_clerk_auth` 套件的完整驗證鏈(當前 import 未使用)
  - **Priority**: P2(未有明確攻擊 vector 但屬 best practice);排入 Phase 0 Retrospective 或 Phase 1A 安全 review
  - **Discovered**: 2026-04-22 during 2.8 Round 2A Clerk config diagnose

- **[P2 → Round 3 或 Phase 1A]** 阻止 signed-in user 訪問 `/sign-in` 和 `/sign-up`
  - **現況**: logged-in user 打 `/sign-in` 會看到 Clerk SignIn card,可能困惑
  - **解法**: `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx` 頂部加 `<SignedIn><RedirectToResearch /></SignedIn>` wrapper(或 useEffect + router.push('/research'))
  - **Priority**: P2 UX polish
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P2 → Phase 1A]** Backend error response shape 不統一
  - **現況**: pre-Round 1B endpoints 回 `{error: "code"}`,Round 1B 新 `api/errors.py` 回 `{type: "code", ...}`
  - **Round 2B frontend 處理**: dual-read pattern 兼容 `const code = data.type ?? data.error`
  - **解法**: Phase 1A 統一 endpoint error shape(建議走 `{type, message}` 新 shape),frontend 簡化掉 dual-read
  - **Priority**: P2 consistency
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P1 → Round 3 AnonymousUpgradeCTA 一起做]** Anonymous quota message 不 surface 正確 type
  - **現況**: E2E Test 4 發現 anon daily quota 耗盡時,前端顯示通用 "Too many requests. Please wait a moment and try again.",而非 Round 2B 預期的 "Daily free limit reached. Sign up to continue."
  - **Root cause 假設**: FastAPI `HTTPException(status_code=429, detail={type: "anonymous_quota_exceeded", ...})` 序列化後 response body 是 `{detail: {type: ...}}` 而非 `{type: ...}` → `utils/sse.ts` 的 dual-read `data.type ?? data.error` 抓不到(真實路徑應為 `data.detail?.type ?? data.type ?? data.error`)
  - **驗證步驟**: curl anon endpoint 耗盡 quota,印出 raw response body shape 確認
  - **解法 (Round 3 一起處理)**:
    1. 後端改用 `api/errors.py` 的 `JSONResponse` 路徑回 `{type, message}` 而非 `HTTPException(detail=...)` — 同時 resolve 上面 P2 error shape 統一
    2. 或 frontend `utils/sse.ts` 加 `data.detail?.type` fallback(hacky,不建議)
    3. 搭配 Round 3 `AnonymousUpgradeCTA` 元件實作,確保 message + CTA 一起 surface
  - **Priority**: P1(軟啟動前必須 fix,影響 anon-to-signup 轉換訊息)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 4 E2E

- **[P2 → Dodo 付費啟用前]** `CLERK_SECRET_KEY` 仍是 `sk_live_` 對 Dev instance user checkout 會 500
  - **現況**: Round 2B JWT Dev/Prod mismatch fix 只改 `CLERK_JWKS_URL` 指向 Dev instance (`joint-guppy-23.clerk.accounts.dev`);`CLERK_SECRET_KEY` 仍為 Prod `sk_live_NhG...`
  - **影響範圍**: Dodo checkout path 會用 `CLERK_SECRET_KEY` call Clerk Backend API 取 user email/name;Dev instance user ID 對 Prod secret key 查不到 → 500 error
  - **現行不爆的原因**: Round 2B 測試只跑 Research + Verify,沒動到 Dodo checkout;Dodo 付費要到 Phase 1A 才啟用
  - **解法** (Dodo 付費啟用前):
    - 改用 Dev instance secret key(`sk_test_...`)for localhost + Dev user 測試
    - 或將 Prod env 與 Dev env 的 Clerk 設定徹底分離(`fly secrets` vs `.env`)
    - 驗證 `/api/checkout/dodo` + `/api/webhook/dodo` 路徑對 Dev user 能順利 create subscription
  - **Priority**: P2(不 block 當前軟啟動;Dodo 付費啟用是 Phase 1A scope)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 5 Clerk JWT Dev/Prod mismatch fix


### Discovered Gaps (history)

- **G1. Anonymous Trial Flow** — Landing Page promises "No account required to try" but "Try it for free" redirects to Clerk sign-in. Must resolve before Phase 1A Week 1 LinkedIn launch (privacy-first manifesto post).
  - Full decision record: `docs/decisions/001-anonymous-trial-flow.md`
  - PRD section: § 2.8 (new)
  - Discovered: 2026-04-18
  - Status: ✅ Resolved 2026-04-22 by Round 2B production verification (see FEATURE_AUDIT.md § 2.8)

**Remaining Phase 0**: 2.1 Model Provider (5-7d) → 3.1 User Context schema → § 4.5 Share Answer → § 4.6 SEO Explore Pages → Phase 0 Retrospective

**Always consult `FEATURE_AUDIT.md` for latest codebase state before starting any task.**

## Planning Documents (READ FIRST)

When given a feature task, always consult these documents **before** touching code:

| Document | Purpose | Location |
|---|---|---|
| `docs/PRD.md` | Master PRD v1.3 — all functional specs, Phase 0/1A/1B/1C, acceptance criteria | `docs/PRD.md` |
| `FEATURE_AUDIT.md` | Codebase current state — what's built, what's partial, what's missing | `FEATURE_AUDIT.md` |
| `TODO.md` | Lightweight tracker for current-round follow-up bugs + roadmap pointers. Consult alongside FEATURE_AUDIT.md when starting a new task. Full tech debt log remains in CLAUDE.md until Phase 0 Retrospective. | `TODO.md` |

### Workflow for a new task

1. Read the relevant PRD section (requirements + acceptance + "not in scope")
2. Check `FEATURE_AUDIT.md` for current state — **do not re-implement what's already done**
3. **Check `TODO.md` for any acceptance protocols or trigger conditions tied to this task** (e.g. § 2.7 Step 8 acceptance protocol gates prompt-tuning decisions; deferred items in § 2.7 Step 4 follow-up wait on Step 8 data)
4. Implement
5. Verify against PRD acceptance criteria, item by item
6. **If the task is part of an acceptance protocol checkpoint, execute the protocol items** (e.g. completing Step 8 means running the full 5-point checklist in TODO.md, not just "20 cases done")
7. If implementation changed codebase state, update `FEATURE_AUDIT.md`
8. Commit message format: `[PRD X.Y] brief description` (e.g. `[PRD 2.0] Remove temp window.__vela_analytics exposure`)

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
- **TEST_MODE**: Bypasses both auth (returns hardcoded `test_user` via `require_auth`) and rate limiting. Production guard at backend startup raises `RuntimeError` if `TEST_MODE=true` with `FLY_APP_NAME` set — process won't start.
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
- `TEST_MODE` bypasses rate limiting (test runner makes 40+ requests in <5 min). Production guard at server.py:305-308 prevents `TEST_MODE=true` from running in prod.

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
