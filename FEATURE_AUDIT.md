# Vela Feature Audit

**Generated:** 2026-04-17
**Scope:** Code-only review. No changes made.

---

## 1. `user_usage` 表結構 — specialty / role / workplace / work_language 欄位

**狀態：** ❌ 未實作

**證據：**

`api/models/sql_models.py:45-61` (SQLAlchemy model):
```python
class UserUsage(Base):
    __tablename__ = "user_usage"
    clerk_user_id = Column(String, primary_key=True)
    plan_type = Column(String, default="free")
    credits_used = Column(Integer, default=0)
    credits_used_today = Column(Integer, default=0)
    last_daily_reset = Column(DateTime, default=datetime.utcnow)
    last_free_reset = Column(Date, nullable=True)
    lemon_customer_id = Column(String, nullable=True)
    lemon_subscription_id = Column(String, nullable=True)
    lemon_variant_id = Column(String, nullable=True)
    dodo_customer_id = Column(String, nullable=True)
    dodo_subscription_id = Column(String, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
```

`migrations/002_add_dodo_and_free_reset.sql` 是目前唯一的 migration，只加了 Dodo / free reset 欄位。

Repo-wide grep `specialty|role|workplace|work_language|medical_specialty|user_profile` 無匹配。

**缺什麼：**
- SQLAlchemy model 沒有 `specialty`, `role`, `workplace`, `work_language` 欄位
- 沒有對應的 migration 檔（預期會是 `003_add_user_profile.sql`）
- 沒有對應的 Pydantic schema / API endpoint 寫入這些欄位
- 全新功能，需要完整 schema + migration + endpoint + 前端 UI

---

## 2. OnboardingOverlay 現況

**狀態：** 🟡 部分實作（只有 4 步導覽，無個人化欄位收集）

**證據：**

`components/OnboardingOverlay.tsx:13-18`:
```tsx
const STEP_DEFS: Step[] = [
  { target: null, titleKey: 'onboardingWelcome', bodyKey: 'onboardingProBody', usePlanBody: true },
  { target: '[data-onboarding="research"]', titleKey: 'onboardingResearch', bodyKey: 'onboardingResearchBody' },
  { target: '[data-onboarding="verify"]', titleKey: 'onboardingVerify', bodyKey: 'onboardingVerifyBody' },
  { target: '[data-onboarding="explain"]', titleKey: 'onboardingExplain', bodyKey: 'onboardingExplainBody' },
];
```

**目前 4 步：** Welcome → Research → Verify → Explain（每步只有標題 + body，目標是 spotlight 導覽列按鈕）。

**「略過」按鈕：** 只在第一步出現，點擊執行 `finish()` → 寫入 `localStorage.hasSeenOnboarding`，不送到 backend。
`components/OnboardingOverlay.tsx:76-79`:
```tsx
const finish = () => {
  localStorage.setItem('hasSeenOnboarding', '1');
  setVisible(false);
};
```

**可重用的 dropdown / select 元件：**
- `components/LanguageSwitcher.tsx` — 下拉選單，可作為 select 元件參考（但邏輯耦合 `useLang` context）
- 無通用 `<Select />` 或 `<Dropdown />` 元件

**i18n key 命名慣例：** `onboarding` 前綴 + 駝峰（如 `onboardingWelcome`, `onboardingProBody`, `onboardingNext`, `onboardingSkip`）
`utils/i18n-ui.ts:98-111` 定義了 TypeScript 型別，所有 key 都要加到 16 種語言的翻譯物件。

**缺什麼：**
- 沒有任何表單輸入 step（都是純展示 popover）
- 沒有「收集 specialty / role / workplace / work_language」的 step
- 沒有 save-to-backend 邏輯（`finish()` 只寫 localStorage）
- 沒有跳步邏輯（目前是線性 Back / Next）
- 沒有可重用的 `<Select>` / `<RadioGroup>` 元件

---

## 3. CitationPanel

**狀態：** ✅ 完整實作（但無 PostHog 追蹤、無當前 query 存取）

**證據：**

**`source_type` 欄位：** 有。
`components/CitationPanel.tsx:7-18`:
```tsx
export interface Citation {
    id: number;
    source_type: 'pubmed' | 'fda' | 'local';
    source_id: string;
    title: string;
    snippet: string;
    url: string;
    credibility: 'peer-reviewed' | 'official' | 'internal';
    ...
}
```
Backend 側：`api/models/schemas.py:66` 也是 `source_type: SourceType`（列舉包含 PUBMED, FDA, LOINC, RXNORM, MEDLINEPLUS — 比前端型別多）。

**「View source」實作：** 純 `<a>`，無 onClick。
`components/CitationPanel.tsx:159-171`:
```tsx
<a
    href={citation.url}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-flex items-center gap-1 text-sm hover:underline mt-3"
    style={{ color: "#ff8e6e" }}
>
    {ui.viewSource}
    ...
</a>
```

**PostHog capture：** ❌ 完全沒有。整個檔案無 `posthog` import。

**當前 query 存取：** ❌ 無法直接拿到。`CitationPanelProps` 只有 `citations` + `isLoading`，沒有 query prop 或 context。
`pages/research.tsx:529`: `<CitationPanel citations={citations} isLoading={...} />` — 呼叫端有 query 但沒傳進來。

**缺什麼（若要加「點擊追蹤 + 關聯 query」）：**
- `CitationPanelProps` 需加 `query?: string` 或 `queryId?: string`
- `<a onClick>` 上加 `posthog.capture('citation_clicked', { ... })`
- 前端目前完全沒有 query_id 的概念（見 §4）

---

## 4. PostHog event 體系

**狀態：** ❌ 幾乎未實作（只有 pageview）

**證據：**

全專案 `posthog.capture()` 呼叫 grep 結果：**只有 1 處。**
`pages/_app.tsx:21-24`:
```tsx
useEffect(() => {
  const handleRouteChange = () => posthog.capture('$pageview');
  router.events.on('routeChangeComplete', handleRouteChange);
  return () => router.events.off('routeChangeComplete', handleRouteChange);
}, [router.events]);
```

初始化：`pages/_app.tsx:11-16`
```tsx
posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
  api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
  capture_pageview: false,
});
```

**Payload 結構：** 只有 `$pageview`（PostHog 內建）。無自訂 payload schema。

**query_id / session_id：**
- Frontend：❌ 無 `query_id` / `trace_id` / `session_id`（repo-wide grep 無匹配）
- Backend：audit log 有 `audit_id`（格式 `res_<hex16>`, `ver_<hex16>`, `exp_<hex>`），但從未透過 SSE 傳回前端
  - `api/server.py:449`: `audit_id = f"res_{uuid.uuid4().hex[:16]}"`
  - `api/models/sql_models.py:22`: `ChatHistory.session_type`（只是分類字串 "research"/"verify"/"explain"，不是 session ID）

**缺什麼：**
- 幾乎整套 event 體系（`query_submitted`, `query_completed`, `citation_clicked`, `feedback_given`, `upgrade_clicked`, `onboarding_completed` 等）
- `query_id` 從 backend 回傳到前端的機制（SSE event 或 response header）
- 無統一 event payload schema（如 `{ query_id, feature, lang, plan, ... }`）

---

## 5. LLM Provider 架構

**狀態：** ❌ 未抽象，全部 hardcode OpenAI

**證據：**

`generator.py` 和 `guards.py` 直接 import openai：
- `api/rag/generator.py:12`: `from openai import AsyncOpenAI`
- `api/rag/generator.py:94`: `self.client = AsyncOpenAI()`
- `api/middleware/guards.py:16`: `from openai import OpenAI`
- `api/middleware/guards.py:149`: `client = OpenAI()`
- `api/middleware/guards.py:237`: `client = OpenAI()` (medical intent check)

還有 `api/rag/retriever.py:14`, `api/rag/reranker.py:14`, `api/services/explain_service.py:12`, `api/services/entity_extractor.py:8`, `api/utils/llm_judge.py:13`, `api/database/vector_store.py:11`, `api/server.py:47` 全都直接 import OpenAI。

**Provider 抽象層：** ❌ 無。grep `provider|LLMProvider|llm_provider|model_provider` 無匹配。

**模型名稱：** **Hardcoded**（字串字面量，非 env var）。
- `api/rag/generator.py:24-25`:
  ```python
  RAG_MODEL      = "gpt-4.1"
  FALLBACK_MODEL = "gpt-4.1-mini"
  ```
- `api/middleware/guards.py:151,239`: `model="gpt-4.1-mini"` 字面量
- `api/rag/reranker.py:31`: `model: str = "gpt-4o-mini"` 預設
- `api/server.py:908`: `model="gpt-4o"` 字面量

唯一半結構化的地方：`api/services/cost_tracker.py:11-16` 的 `MODEL_COSTS` dict（只是定價表，不是 provider abstraction）。

**缺什麼：**
- Provider interface（`BaseLLMProvider` 抽象類別或 protocol）
- 環境變數讀取（`OPENAI_MODEL_RAG`, `OPENAI_MODEL_CLASSIFIER` 等）
- 不同 provider 的 adapter（Anthropic、Azure OpenAI、Gemini）

---

## 6. Settings 頁面

**狀態：** 🟡 部分實作（僅 Navbar dropdown，無 `/settings` 專頁）

**證據：**

無 `pages/settings.tsx`（`ls pages/` 結果：`_app, _document, explain, faq, history, index, pricing, privacy, refund, research, terms, verify`）。

Settings UI 在 Navbar 齒輪 dropdown 中：
`components/Navbar.tsx:215-302`（width 280px）包含：
- 語言切換（`<LanguageSwitcher compact />`）
- Plan label (Free / Pro)
- 今日 credits 使用進度條（`{creditsUsed} / {dailyLimit}`）
- Pro 用戶：Manage Subscription / Cancel Subscription 按鈕
- Free 用戶：Upgrade to Pro 按鈕

**可調整項目：** 只有「語言」+ 「訂閱管理」。

**「個人化」區塊：** ❌ 無。沒有 specialty / role / theme / notification 等設定。

**語言切換：** ✅ 已在 Navbar settings dropdown 內（`Navbar.tsx:238-240`）。

**缺什麼：**
- 獨立 `/settings` 頁面（目前所有邏輯擠在 280px dropdown）
- 個人化欄位（specialty / role / workplace / preferred response language）
- 通知 / 資料管理 / 匯出 / 刪除帳號等 section

---

## 7. 首頁範例查詢

**狀態：** ✅ 實作（全部 hardcoded，無使用者屬性切換）

**證據：**

**Landing 首頁 (signed-out)：**
`pages/index.tsx:21-25`（typewriter prompt，3 個，英文 hardcode）：
```tsx
const PROMPTS = [
  { text: 'Research Metformin interactions in renal impairment', color: '#ff8e6e' },
  { text: 'Verify Warfarin + Aspirin — is it safe?',            color: '#63b3ed' },
  { text: 'Explain my blood test results in plain language',    color: '#68d391' },
];
```

**Research 頁面範例：**
`pages/research.tsx:81-92`（10 個固定的多語言範例）：
```tsx
const defaultSuggestions = [
    "小孩發燒幾度需要看醫生？",
    "What are the common side effects of Metformin?",
    "ワルファリンの副作用は何ですか？",
    "老人血壓藥可以跟鈣片一起吃嗎？",
    "¿Es seguro usar antibióticos durante el embarazo?",
    "DOACs vs Warfarin — key differences?",
    ...
];
```
註解明確寫：`Fixed multilingual sample queries ... Intentionally NOT translated: the mix of languages itself is the message.`

**是否根據使用者屬性切換：** ❌ 完全沒有。兩處都是 module-level const。無 `useUser()` / `specialty` / plan-based 切換邏輯。

**缺什麼（若要做個人化範例）：**
- 依 specialty 切換範例的邏輯（需先有 §1 的 user profile 欄位）
- 依目前語言切換範例的邏輯

---

## 8. Bug 回報入口

**狀態：** 🟡 部分實作（只有 mailto，無內建表單）

**證據：**

**無內建「回報問題」按鈕 / 表單。** grep `bug.report|bugReport|Report.*issue|report.*bug` 無匹配。

只有 `mailto:support@an-tho.com`，遍布多處：
- `pages/index.tsx:408, 525`（landing footer）
- `pages/faq.tsx:149`
- `pages/pricing.tsx:151`
- `pages/privacy.tsx:68, 73`
- `pages/terms.tsx:49, 69`
- `pages/refund.tsx:29, 54`
- `components/UpgradeModal.tsx:47`（付款錯誤時顯示）
- `utils/i18n-ui.ts` faqCta 在 16 種語言都是 mailto

**FeedbackBar (👍👎)** 是針對「答案品質」的 inline 反饋，不是 bug report（見 §10）。

**缺什麼：**
- 內建 bug report modal / page
- 截圖上傳 / 重現步驟欄位
- Bug 相關的 DB 表（目前 `UserFeedback` 綁定 query/response，不適合 bug report）

---

## 9. 隱私相關 UI

**狀態：** 🟡 部分實作（有專頁 + footer 連結，但 landing / onboarding / settings 無內嵌訊息）

**證據：**

**Privacy Policy 頁：** `pages/privacy.tsx`
- Last updated：`pages/privacy.tsx:18`: `"Last updated: March 2026"`
- 8 sections：Data We Collect / No PHI Storage / No AI Training / Data Retention / Third-Party Services / Cookies / Data Deletion / Contact
- 只有英文（無 i18n）

**Footer 連結（Privacy Policy）：**
- `pages/index.tsx:405, 522`: `<Link href="/privacy">{extra.privacyLabel}</Link>`（landing 雙入口，`privacyLabel` 有 i18n）

**Landing / Onboarding / Settings 中的隱私訊息：** ❌ 無直接的「我們不存你的資料」訊息。
- `pages/index.tsx` grep `privacy|PHI|no.*store` 只有 footer link
- `OnboardingOverlay.tsx` 無隱私文案
- Navbar settings dropdown 無隱私連結

**PHI 保護的展示：** 有 `components/PHIWarning.tsx`，但只在使用者輸入 PHI 時出現（Research/Verify/Explain 頁），屬於錯誤訊息，不是事前的隱私承諾。

**缺什麼：**
- Landing / pricing 增加 trust section（「Your data never trains AI」、「No PHI stored」）
- Onboarding 中的隱私一句話
- Settings 裡的「Data & Privacy」區塊（下載資料、刪除帳號）
- Privacy Policy 翻譯（目前只有英文）

---

## 10. FeedbackBar 現況

**狀態：** 🟡 部分實作（只寫入 DB，無後續動作、無分析追蹤）

**證據：**

完整實作 `components/FeedbackBar.tsx`：

**👍👎 實作：**
```tsx
// FeedbackBar.tsx:20-34
const sendFeedback = async (rating: number) => {
    try {
        const token = await getToken({ skipCache: true });
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ query, response, rating, feedback_text: null, category }),
        });
    } catch (err) { console.error('Feedback failed:', err); }
};
// rating: 1 = like, -1 = dislike
```

UI state：`idle | liked | disliked`，按鈕點擊後鎖住（`disabled={status !== 'idle'}`）。

**按下 👎 的後續動作：** ❌ **完全沒有。** 和 👍 走同一個 `sendFeedback()`，只是 rating=-1。不會彈「為什麼不滿意」表單，不會記 reason，不會 trigger retry。

**Payload：**
```json
{
  "query": "...",
  "response": "...",
  "rating": 1,         // or -1
  "feedback_text": null,  // 目前永遠是 null
  "category": "research" // or "verify" / "explain"
}
```

**後端：** `api/server.py:944-965` `create_feedback()` 寫入 `UserFeedback` 表（`id=fb_<hex>`）。

**PostHog 追蹤：** ❌ `sendFeedback()` 內無 `posthog.capture()`。

**缺什麼：**
- 👎 後的 follow-up（原因選項、自由文字輸入）— `feedback_text` 欄位已存在但從未被使用
- PostHog `feedback_given` event
- 無「編輯回應」(rating=2) 的 UI，但 DB 已定義 (`sql_models.py:37` comment: `2=Edited`)

---

## 11. 處方解析 / 交互作用功能

**狀態：** 🟡 Verify 已實作 drug interaction，但無「處方解析」功能

**證據：**

**Verify 功能（已存在）：** `pages/verify.tsx` — 使用者手動輸入藥物列表（多行）。
`pages/verify.tsx:55-71`:
```tsx
const drugList = drugs.split('\n').map(d => d.trim()).filter(Boolean);
if (drugList.length < 2) { ... }
body: JSON.stringify({ drugs: drugList, patient_context: null }),
```
後端呼叫 FDA DailyMed，用 Levenshtein 做拼字修正（`api/server.py` verify endpoint）。

**處方解析（prescription parsing）：** ❌ **未實作。**
- 無 `pages/prescription.tsx`
- 無 `api/services/prescription_service.py`
- grep `prescription|prescribing` 僅匹配 `UpgradeModal` 文案、`guards.py` 注釋詞彙、README

**Research / Verify / Explain 之外的第四個功能：** ❌ 無。`pages/` 目錄的主功能頁就這三個（加 history、pricing、faq、privacy、terms、refund 輔助頁）。

**Explain 功能中的處方：** `pages/explain.tsx` 會從醫療報告裡用 LLM 抽取藥物名（`api/services/entity_extractor.py`），但那是「報告解讀」用途，不是「處方解析 → 自動查交互作用」的端到端流程。

**缺什麼（若要做「處方解析 → 自動丟進 Verify」）：**
- OCR / 結構化抽取 prescription 的 endpoint（可重用 `entity_extractor.py`）
- 解析結果自動轉成 Verify input 的 UI flow
- 全新的 `pages/prescription.tsx` 或整合進 Explain

---

## 12. 在地差異提示相關

**狀態：** ❌ 未實作

**證據：**

**LLM prompt 中的「地區」「在地」：** ❌ 無。
`api/rag/generator.py` 系統 prompt（`_get_system_prompt`, `FALLBACK_PROMPTS`）完全不提 region/locale/country。

`api/services/explain_service.py:36` 只有一行通用模板：
```
"Reference ranges may vary by laboratory and region."
```
— 要求 LLM 在沒 reference range 時加這句話，並非「依使用者地區調整回答」。

**Hardcoded 官方網站連結 map：** ❌ 無。grep `衛福部|MOHW|cdc\.|health\.gov|official.*website` 無匹配。
程式碼中的「官方」只有：
- `api/models/schemas.py:24`: `OFFICIAL = "official"  # FDA 官方` — credibility 列舉標籤
- `utils/i18n-extra.ts:88,92`: `dashVerifySub: 'FDA 官方'` — 首頁 mockup 文案
- 沒有任何 `const OFFICIAL_SITES = { 'zh-TW': '...', 'ja': '...' }` 的結構

**語言偵測：** `api/utils/language_detector.py` 做的是「回答用哪個語言」（16 語），不是「使用者在哪個國家」。

**缺什麼：**
- Prompt-level region awareness（傳 `user_region` 進 system prompt）
- Region → 官方連結 map（如 TW 衛福部、JP PMDA、KR MFDS、EU EMA）
- Citation UI 針對非 PubMed/FDA 來源時顯示地區來源
- 需要先有 §1 的 user profile (workplace / region) 或 IP geolocation

---

## 總結

| # | 項目 | 狀態 |
|---|------|------|
| 1  | user_usage 個人化欄位             | ❌ |
| 2  | OnboardingOverlay（含個人化 step）| 🟡 只有導覽，無表單 |
| 3  | CitationPanel                      | ✅ / 無追蹤 |
| 4  | PostHog event 體系                 | ❌ 只有 pageview |
| 5  | LLM Provider 抽象                  | ❌ hardcode OpenAI |
| 6  | Settings 頁面                      | 🟡 只有 Navbar dropdown |
| 7  | 首頁範例查詢                       | ✅ hardcoded，無個人化 |
| 8  | Bug 回報入口                       | 🟡 只有 mailto |
| 9  | 隱私 UI                            | 🟡 有專頁，無內嵌訊息 |
| 10 | FeedbackBar                        | 🟡 👎 無後續動作 |
| 11 | 處方解析                           | ❌ 只有手動 Verify |
| 12 | 在地差異提示                       | ❌ |

**常見前置依賴：** §2 (onboarding 表單) / §7 (個人化範例) / §12 (在地化) 都依賴 §1 的 user profile 欄位先建起來。§3 (citation 追蹤) 依賴 §4 的 PostHog event 體系。
