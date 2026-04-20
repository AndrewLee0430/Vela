# Vela Feature Audit

**Generated:** 2026-04-18 (updated 2026-04-18 after PRD 2.2 + 2.3 sprint lands)
**Scope:** Code-only review against PRD v1.2 (Phase 0 / 1A / 1B / 1C).
**Methodology:** grep / glob over current working tree. Does not trust historical audits.

---

## Discovered Gaps

> 記錄在 PRD 之外發現的產品落差。每一項 gap 建立對應的 Decision Record 後,此區塊僅保留 pointer 和 status,不重複決策細節。

### G1. Anonymous Trial Flow

- **Severity**: High — Phase 1A LinkedIn launch blocker
- **Discovered**: 2026-04-18 by andre(無痕視窗測試)
- **Problem**: Landing Page 承諾「No account required to try」(PRD § 0.3),但實際上點 "Try it for free" 被 Clerk sign-in 擋住
- **Decision Record**: [`docs/decisions/001-anonymous-trial-flow.md`](docs/decisions/001-anonymous-trial-flow.md)
- **PRD Section**: § 2.8(新增)
- **Status**: Accepted (solo founder review, 2026-04-19)
- **Next Action**: Team review of Decision 001,決議後 schedule 進 Phase 0 workplan

---

## Status key

- ✅ 已完成 — 實作與 PRD 驗收條件對齊
- ⚠️ 部分完成 — 核心 primitive 存在但缺少驗收條件內的某些項目
- ❌ 未開始 — 找不到對應檔案/函式/事件
- ⛔ 不適用 — 已被取代或 deprecate

---

## Phase 0 — 基礎建設 + SEO 止血

### 2.0 PostHog wrapper — ✅ 已完成

- `utils/analytics.ts:106-151` export `track()` / `identify()` / `reset()`
- `utils/analytics.ts:94-104` `buildCommonProps()` 自動注入 `query_id / session_id / user_context_hash / locale / plan_type / work_language`
- `pages/_app.tsx:26-44` `AnalyticsAuthBridge` 在 Clerk signedIn → signedOut 轉換時呼叫 `resetAnalytics()`(commit 3876239 / v143)
- SDK 未初始化時 `isPosthogReady()` 擋掉 `posthog.capture()`,符合 degrade-gracefully
- 生產環境 PostHog Dashboard 已人工驗收(2026-04-17)

**尚未消化的餘項(不屬於 2.0 Round A 驗收):**
- `getQueryId()` 固定回傳 null,待 2.2 串接
- 無 caller 呼叫 `identify()`,等 Clerk sign-in hook 在 Round B 補上
- 現存 `posthog.capture('$pageview')`(`pages/_app.tsx:50`)尚未改走 `track()`;Round B 再統一

---

### 2.1 Model Provider 抽象層 — ❌ 未開始

- `api/providers/` 目錄不存在
- `from openai import (OpenAI | AsyncOpenAI)` 散佈於 10 個檔案(未變):
  - `api/server.py:47`
  - `api/database/vector_store.py:11`
  - `api/rag/generator.py:12`
  - `api/rag/retriever.py:14`
  - `api/rag/reranker.py:14`
  - `api/utils/llm_judge.py:13`
  - `api/services/explain_service.py:12`
  - `api/services/entity_extractor.py:8`
  - `api/middleware/guards.py:16` (+ L149、L237 兩個 sync `OpenAI()`)
- 模型名仍硬編碼:`RAG_MODEL = "gpt-4.1"`(generator.py:24),guard model `"gpt-4.1-mini"` 字面量(guards.py)
- 無 `GENERATOR_PROVIDER` / `GUARD_MODEL` 等環境變數在 `.env.example` 內

---

### 2.2 query_id 串接 — ✅ 已完成

- Backend:
  - Research SSE:`api/server.py:423, 426` 在 `event_stream()` 頂端產生 `audit_id = res_<hex16>`,第一個 SSE event 即 `{type:'query_id', query_id}`;citation 段落 `:462-470` 直接沿用同一 `audit_id` 寫 AuditLog
  - Verify:`api/server.py:530` 端點入口一次產生 `audit_id = ver_<hex16>`,fallback / main 兩處 AuditLog 與三個 VerifyResponse 全部引用同一 id(`:617, :659, :670, :743, :773`)
  - Explain SSE:`api/server.py:807, 815` 同一模式;`done` 時寫入 AuditLog `id=exp_<hex16>`
  - `VerifyResponse.query_id: Optional[str]` 加在 `api/models/schemas.py:216`
- Frontend:
  - `utils/analytics.ts:25, 94-101, 147` `moduleQueryId` state + `setQueryId()` export;`getQueryId()` 改讀模組內狀態;`reset()` 一併清空
  - `pages/research.tsx:272-274` / `pages/explain.tsx:358-360` 新增 `data.type === 'query_id'` 分支,呼叫 `setQueryId(data.query_id)`;`handleReset` + 查詢開始時清空
  - `pages/verify.tsx:106` 在 `setResult(data)` 後將 `data.query_id` 寫入 analytics 模組
- Acceptance:所有後續 `track()` 事件(透過 `buildCommonProps()`)自動帶 `query_id`,可在 PostHog 以同一 id 串聯 query → citation_clicked → feedback

---

### 2.3 CitationPanel 點擊追蹤 — ✅ 已完成

- `components/CitationPanel.tsx:5, 11` 新增 `track` import + `CitationSourceType` enum(含 PRD 規定 10 種 + `localauthority` + `other`)
- `detectSourceType()`(`:35-62`)先讀 `citation.source_type`,白名單比對;不在名單再用 URL hostname fallback(pubmed.ncbi.nlm.nih.gov / fda.gov / loinc.org / medlineplus.gov / dailymed / rxnav / who.int / nice.org.uk / ema.europa.eu / cochrane)
- `CitationCard`(`:102-166`)新增 `position` prop + `handleSourceClick` 觸發 `track('citation_clicked', { source_type, url, citation_position })`,`onClick` + `onAuxClick` 同時綁定,fire-and-forget(try/catch 包住,絕不阻斷 `<a>` 跳轉)
- `CitationPanel` map 改傳 `position={idx + 1}`(`:237`)避免 closure trap — 每張卡片持有自己的 citation 與 index
- `queryId` 不再經由 prop 注入,改由 `utils/analytics.ts` 模組狀態自動帶入 → 所有 components 不需感知 query_id
- Enum 與 PRD § 2.3 對齊:`pubmed / fda / loinc / medlineplus / rxnorm / who / nice / ema / cochrane / local / localauthority / other`

---

### 2.3a Feedback 按讚 / 按爛事件 — ✅ 已完成(伴隨 2.3 lands)

- `components/FeedbackBar.tsx:8, 39, 46` `handleLike` / `handleDislike` 新增 `track('feedback_thumbs_up' | 'feedback_thumbs_down', { category })`,呼叫順序是「setStatus → track → sendFeedback」,track 用 try/catch 包住
- `category` 欄位值為 `'research' | 'verify' | 'explain'`;`query_id` 透過 `buildCommonProps()` 自動注入
- Acceptance:PostHog funnel「query → citation_clicked → feedback_thumbs_up」可由 `query_id` join

---

### 2.4 Bug 回報機制 — ✅ Resolved 2026-04-19

- **Status**: ✅ Resolved 2026-04-19
- **Resolution**:
  - New `BugReportButton` FAB component in PageShell (authenticated pages)
  - New backend `POST /api/bug-report` endpoint
  - New `bug_reports` table (auto-created via `Base.metadata.create_all()`)
  - PHI sanitization via `PHIDetector.sanitize_for_log()` before DB write
  - Rate limit 5 requests/hour per IP via existing `rate_limiter`
  - PostHog events: `bug_report_opened`, `bug_report_submitted` (via `analytics.track()`)
  - i18n: en + zh-TW complete, other locales fallback to en
  - Auth handling: `_optional_user_id()` accepts both authenticated (writes user_id) and anonymous submissions
- **Production verification**: ✅ 2026-04-20, user_id writes correctly
- **Known issues handed to Tech Debt (see CLAUDE.md)**:
  - `_optional_user_id()` localhost limitation — not code bug; Clerk Hosted + missing `/sign-in` page (resolved in 2.8)
  - `print()` violations in api/ (9 prod + 45 test harness) — resolved in Phase 0 Retrospective
- **Original state** (for reference): 僅 mailto link, 需浮動按鈕

---

### 2.5 Landing Page SEO 修復 — ✅ 已完成

- `pages/index.tsx:678-682` `Home()` 只依 `isSignedIn` 切 Dashboard / LandingPage,無 `isLoaded` spinner gate(L675-677 有註解說明為何如此)
- `pages/index.tsx:260-302` 完整 meta tags:`<title>`、description、robots、canonical、og:*(type/site_name/url/title/description/image/image:width/image:height)、twitter:*(card/title/description/image)
- L303-402 兩個 JSON-LD(`SoftwareApplication` + `Organization`)
- `/research`(L567)、`/verify`(L368)、`/explain`(L668)、`/history`(L398)皆有 `<meta name="robots" content="noindex, nofollow" />`
- `public/sitemap.xml` 涵蓋 `/`、`/pricing`、`/faq`

---

### 2.6 i18n hreflang (Strategy A) — ✅ 已完成

- `pages/_app.tsx:71-74` 對所有頁面輸出 16 語言 hreflang + x-default
- `public/sitemap.xml` 對 `/` 與 `/pricing` 每個 URL 都列 16 個 hreflang + x-default(L8-24, L30-46)
- `pages/_app.tsx:56-57` 每頁都有 canonical URL 組出
- Strategy B(per-locale URL)是 Phase 2 評估

---

### 2.7 Explain 臨床推理強化 — ❌ 未開始

- `api/services/explain_service.py:30-45` system prompt 仍是「解釋報告數值」版本:
  - 無「臨床組合推理」段落指令
  - 無 hedging 禁用詞清單(「您有…」「您需要…」)
  - 無 LOINC 僅限代碼對照、不得作為臨床判斷引用的指令
- `api/services/explain_service.py:66-70` LOINC 仍是 lab test 的主要 citation 來源(未按 PRD 5 分層)
- `api/models/explain_schemas.py` 無 `risk_tier` / `clinical_correlations` / `risk_label` 欄位
- 前端 `pages/explain.tsx` 無 🟢🟡🔴 render;無 correlations 區塊;無固定 disclaimer 渲染(現有 stripLlmDisclaimer 是另一回事)
- 注意:repo 裡出現的 🟢🟡🔴 全部在 `api/rag/generator.py:288-300` 的 **Research** evidence strength,不是 Explain 的 risk tier,不可混淆
- `api/utils/llm_judge.py` 無 Explain 專用評估 prompt

---

## Phase 1A — 定位落地

### 3.1 user_context schema — ❌ 未開始

- `api/models/sql_models.py` `UserUsage` 無 `specialty` / `role_category` / `workplace_category` / `work_language` / `locale`
- 無 `user_profile` 新表;無 `003_add_user_profile.sql` migration
- 無 `POST /api/user/context/hash` 與 `GET /api/user/context/hash` endpoints
- localStorage key `vela_user_context` 只在 `utils/analytics.ts:63-87` 被「讀」,沒有任何地方「寫」(等 3.2 Onboarding 寫入)

---

### 3.2 Onboarding 三問(workplace → role → work_language)— ❌ 未開始

- `components/OnboardingOverlay.tsx:13-18` 是 4-step spotlight 產品導覽(Welcome/Research/Verify/Explain),**非** PRD 的三步 Wizard
- 無任何 `<input>` / `<select>` / `<RadioGroup>` step
- 無誠實提示文案(「你選擇了醫學中心,UpToDate 可能更適合你」)
- 無 Step 4 隱私聲明卡
- `finish()` 僅寫 `localStorage.hasSeenOnboarding`,不寫 `vela_user_context`
- 無 `onboarding_step_completed` / `onboarding_completed` PostHog event

---

### 3.3 首頁動態範例查詢 — ⚠️ 部分完成

- `pages/index.tsx:21-25` 有 3 個 hardcoded typewriter prompts(Research/Verify/Explain),皆為英文字面量
- 無根據 `vela_user_context.role` 切換範例池的邏輯
- 無「藥師 / 護理師 / 社區醫師 / 醫學生 / 通用」5 個範例池(共 25-40 條 query)
- 無「點擊範例自動填入 + 送出」互動(目前只是裝飾 typewriter)
- 無 `example_query_clicked` event

**可以快速補:**framework 已在位(PROMPTS 陣列 + TypewriterPrompt),只需加 role 選擇層 + 範例池內容 + click handler。

---

### 3.4 Privacy 四接觸點 + 16 語言 Privacy Policy — ⚠️ 部分完成

| 接觸點 | 狀態 | 證據 |
|---|---|---|
| 1. Landing Page | ✅ | `pages/index.tsx` + `utils/i18n.ts` 有 Anonymous by Default pillar 與 Privacy-first 敘述 |
| 2. Onboarding 隱私卡 | ❌ | 依賴 3.2,3.2 未做 |
| 3. Settings 隱私狀態 | ❌ | 無 `/settings` 頁;Navbar dropdown 無「✓ 我們沒有記錄你的身份」區塊 |
| 4. Footer privacy 連結 | ✅ | `pages/index.tsx` Footer + `utils/i18n-extra.ts` `privacyLabel` 16 語言 |
| Privacy Policy 16 語言 | ❌ | `pages/privacy.tsx` 全英文 hardcode,未讀 `useLang()`;`utils/i18n-extra.ts` 只有 `privacyLabel`(link 字),沒有 policy 內文 |

---

## Phase 1B — 差異化功能

### 4.1 FeedbackBar 👎 原因 chip — ❌ 未開始

- `components/FeedbackBar.tsx:42-46` 按 👎 直接 `sendFeedback(-1)`,`feedback_text: null`(L29)
- 無 reason chip UI(6 個 value:citation_insufficient / answer_incorrect / not_relevant / too_vague / not_applicable_region / other)
- 無 "Other" 展開 textarea
- 無 `feedback_thumbs_down` / `feedback_reason_text` PostHog event
- **後端欄位已就緒**:`UserFeedback.feedback_text` 存在(見 FEATURE_AUDIT 原第 8 節),前端補完即可;無需 migration

---

### 4.2 Citation ⓘ hover/tap tooltip — ❌ 未開始

- `components/CitationPanel.tsx:105-119` 現有 tooltip 是 **credibility 等級**(peer-reviewed / official / internal 3 種),**不是** PRD 要的「10 個 source_type 一句話說明 + 在地差異」
- 10 個 source_type 文案(PubMed/FDA/WHO/NICE/EMA/Cochrane/LOINC/MedlinePlus/RxNorm/LocalAuthority)無處儲存
- 無 `citation_info_viewed` PostHog event

---

### 4.3 Settings user_context 可修改 — ❌ 未開始

- 無 `pages/settings.tsx`
- Navbar dropdown(`components/Navbar.tsx`)僅有語言切換 + 訂閱管理,無 My Context 區塊
- 無「第 10 次查詢後再問一次 banner」機制
- 無「匯出偏好 JSON」、「清除偏好」按鈕

---

### 4.4 處方解析 MVP — ❌ 未開始

- 無 `pages/prescription*.tsx`
- `pages/verify.tsx` 是既有藥物交互作用功能(藥名對 + FDA),非處方解析 pipeline
- 無 Stage 1/2/3/4 LLM parsing + RxNorm 查詢 + 交互作用矩陣生成邏輯
- 無 `prescription_analysis_started` event
- 無 Pro-gating(每日 2 次 free / Pro 不限次)

---

## Phase 1C — 護城河啟動

### 5.1 在地差異提示(機制層 + 資料層)— ❌ 未開始

- `api/rag/generator.py` system prompt 無「若答案涉及在地敏感議題,附加 ⚠️ Regional Differences Notice」指令
- 前端無 locale hint 元件(背景微黃 + ⚠️ 圖示 + 收合記住)
- 無 `locale_hint_displayed` / `locale_hint_clicked` / `locale_hint_dismissed` PostHog event
- 無 locale 偵測 chain(`user_context.locale` → work_language → timezone → IP)

---

### 5.1.1 YAML 知識庫(config/locale_authorities/ 6 國)— ❌ 未開始

- `config/locale_authorities/` 整個目錄不存在
- 無 `tw.yaml` / `jp.yaml` / `kr.yaml` / `sg.yaml` / `my.yaml` / `th.yaml`
- 無 `global_fallback.yaml`(Tier 2 fallback: WHO / NICE / EMA / Cochrane)
- 無 `api/models/locale_authorities.py` Pydantic schema
- 無 `get_authorities(locale)` loader
- `requirements.txt` 未列 PyYAML

---

### 5.2 跨語言橋接面板 — ❌ 未開始

- grep `language_bridge_expanded|key_english_terms` 只命中 PRD.md
- `api/rag/generator.py` 回傳無 `key_english_terms[]` JSON 欄位
- `api/rag/retriever.py` 的 query rewrite 結果(3 個英文查詢)未透過 SSE 傳到前端
- 前端無側邊收合面板 component(`components/LanguageBridge*.tsx` 不存在)
- 無 `work_language !== 'en'` 才顯示的條件渲染

---

## Cross-cutting observations

### PostHog event 體系現況

- **wrapper 已有三個業務事件**(2026-04-18):`citation_clicked`(CitationPanel)、`feedback_thumbs_up` / `feedback_thumbs_down`(FeedbackBar)。全部 query_id 由 `buildCommonProps()` 自動帶入
- `pages/_app.tsx:50` 仍用 `posthog.capture('$pageview')` 直接發 pageview,未走 wrapper。PRD 6.1 / Round B 會處理
- 尚未建立 `query_submitted` / `query_completed` / `export_pdf_clicked` 等 Round B 事件

### `request.client.host` → `_get_client_ip` 修正(歷史紀錄)

- `api/server.py:159-167` 已有 `_get_client_ip()` helper(X-Forwarded-For 優先)
- rate limiter(L178)、`_check_phi`(L351)、Dodo webhook audit(L1340)皆已改用
- `fly.toml [http_service.concurrency]` 有 `hard_limit=100 / soft_limit=50`
- 非 PRD 範圍,記此以備日後查閱

### Planning doc 狀態

- `docs/PRD.md`(v1.2)已從 docx 轉 md
- `FEATURE_AUDIT.md`(本檔)已於 2026-04-18 以 PRD v1.2 重掃
- CLAUDE.md Planning Documents 區塊只保留 PRD.md + FEATURE_AUDIT.md 兩條

---

## Phase 0 完成度總結

| 項目 | 狀態 | 備註 |
|---|---|---|
| 2.0 PostHog wrapper | ✅ | Round A 完成,生產驗收過 |
| 2.1 Model Provider | ❌ | 10 檔案待 refactor,5-7 天工程 |
| 2.2 query_id | ✅ | 2026-04-18 lands;research / verify / explain 共用 audit_id,前端模組狀態自動注入 |
| 2.3 Citation 追蹤 | ✅ | 2026-04-18 lands;`citation_clicked` 送出 `{query_id, source_type, url, citation_position}` |
| 2.3a Feedback 事件 | ✅ | 伴隨 2.3 lands;`feedback_thumbs_up` / `feedback_thumbs_down` 帶 category + query_id |
| 2.4 Bug 回報 | ✅ | 2026-04-19 lands;FAB + `/api/bug-report` + PHI cleaning + rate limit 5/hour |
| 2.5 Landing SEO | ✅ | 完整 meta + JSON-LD + noindex 子頁 |
| 2.6 i18n hreflang | ✅ | Strategy A 完成 |
| 2.7 Explain 臨床推理 | ❌ | Prompt + JSON schema + frontend 1-2 天 |
| 2.8 Anonymous Trial Flow | ⏳ 未開始 | discovered gap,Decision 001 v0.2 Accepted;兩層 UX / 三層資料設計,1.5-2 天 |
| 2.9 Verify 輸出語言對齊 user locale | ✅ 已完成 2026-04-20 | response_language variable + verify_system.md v2.1 + 7 languages i18n-verify.ts + UX polish + Chinese variant handling spread to Research/Explain |

Phase 0 還剩 2 項(2.7 / 2.1)+ 1 個發現的 gap(2.8 Decision 001 v0.2 Accepted);2.1 仍是最大塊工程,2.7 / 2.8 合計 2.5-4 天。
