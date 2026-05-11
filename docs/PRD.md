**Vela Master PRD v1.3**

*Ask in your language. Verified by official sources. Answered in yours. · Updated 2026-04-28*

**Status marker legend** (added 2026-04-30 doc reorg, applied to feature section headings only):

| Marker | Meaning |
|---|---|
| ✅ SHIPPED <date> (commits) | Fully implemented + production-verified. See ARCHIVE.md for full log. |
| 🔧 IN PROGRESS | Actively being worked. See STATE.md for current focus. |
| 🔬 PARTIAL <date> | Partial implementation. See ARCHIVE.md for what shipped + codebase grep for what remains. |
| ❌ PENDING (phase) | Not yet started. See STATE.md for sequence + BACKLOG.md for queue. |
| 🧊 OUT OF SCOPE | Explicitly deferred per phase-gate or design decision. |

Markers are inline annotations on section headings. Spec body text below each heading is preserved verbatim from prior PRD versions — markers are status overlay only, not spec change.

**v1.3 重點變更:v1.2 所有章節 + § 4.5 公開分享連結 + § 4.6 SEO Explore Pages(spec 編號維持 Phase 1B 4.x 與其他 4.1-4.4 cohere,執行順序覆寫至 Phase 0 末段,§ 2.7 Step 8 acceptance 通過後、Phase 0 Retrospective 之前)**

本版本為 v1.2 → v1.3 增補版,新增 soft launch(= Phase 0 ship gate)所需的 word-of-mouth 與 organic discovery 兩項基礎機制,並對應調整 § 4.3 / § 3.4 / § 6.2 章節(詳見 § 10.1):

- § 4.5 公開分享連結(使用者觸發,把單一查詢結果產生匿名公開 URL,對齊 GTM_V1 § 5.4 L3 word-of-mouth)
- § 4.6 SEO Explore Pages(團隊預先建立的長尾 SEO 頁面,共用 4.5 基礎設施,對齊 GTM_V1 § 5.4 L3 organic discovery)

兩功能共用 Public Query Page renderer(SSR + OG + JSON-LD pipeline)。決策依據與完整變更清單見 § 10.1。

**v1.2 重點變更:v1.1 所有章節 + Explain 臨床推理強化(2.7) + 在地知識 YAML 實作規範(5.1.1)**

本版本為 v1.1 → v1.2 增補版。延續 v1.1 的 Phase 0 / 1A / 1B / 1C 規格,針對兩個實作重點做強化:Explain 臨床推理品質的 system prompt 改造(Phase 0 新增 2.7),以及 Phase 1C 在地差異提示的知識庫工程化規範(5.1.1)。

v1.1 → v1.2 主要變更(詳見章節末更新記錄):

- 新增 2.7 節:Explain 臨床推理強化(Phase 0,排在 2.1 之前)
- 新增 5.1.1 節:在地知識 YAML 實作規範(Phase 1C 在地差異提示的執行細節)
- 調整:Phase 0 時程從 2-2.5 週延長為 2.5-3 週
- 調整:Phase 1A 起始點順延對應
**零、產品定位與核心原則**

**0.1 定位聲明**

**Vela 是為「不在大醫院工作 × 工作語言非英語 × Allied Health 角色」的醫療專業人員打造的隱私優先 AI 查詢工具。**

核心使用者:

- 社區藥師、居家護理師、開業診所醫師、醫學生、住院醫師、allied health 治療師
- 主要工作語言為繁體中文、簡體中文、日文、韓文、泰文、越南文、阿拉伯文等非英語
- 需要跨語言檢索英文醫學文獻,但希望以母語得到回答
- 不在大型醫學中心工作,沒有 UpToDate 機構訂閱
不主打的客群(但不拒絕使用):

- 美國 NPI 驗證執業醫師(OpenEvidence 的核心客群)
- 大型醫學中心內有完整 CDS 工具訂閱的醫師
**0.2 Tagline 與訊息層級**

**主 Tagline**

英文:Ask in your language. Verified by official sources. Answered in yours.

中文:用你的語言問,官方來源驗證,用你的語言答。

**副訊息**

英文:The AI medical search for healthcare professionals who work beyond English.

中文:為跨越英語工作的醫療專業人員打造的 AI 查詢工具。

**三大支柱(Value Props)**

| **支柱** | **英文** | **中文** |
| --- | --- | --- |
| 🌐 Your Language | Works in 16 languages. Retrieves from 28M+ English articles. | 支援 16 種語言,檢索 2800 萬+ 英文文獻 |
| 📚 Official Sources | Every answer cited. PubMed, FDA, and your local authorities. | 每個答案有引用。PubMed、FDA、在地權威機構 |
| 🔒 Anonymous by Default | No identity verification. No account required to try. | 預設匿名。不驗證身份、不需註冊即可試用 |

**0.3 Privacy-first 定義**

Vela 採用 Privacy-first 定位,採取「透明定義」做法。以下清單應出現在 Landing Page、About、Privacy Policy,所有地方一致。

**What 'Privacy-first' means at Vela**

- We don't verify your identity or license(不驗證身份或執照)
- We don't require your real name(不要求真實姓名)
- Your preferences (role, workplace, language) stay on your device, not our servers(個人偏好存在你的裝置,不在我們伺服器)
- We don't sell or share any data with third parties(不販售或分享資料給第三方)
- We don't use your queries to train AI models without consent(未經同意不使用查詢資料訓練 AI)
**What it doesn't mean**

- We're not end-to-end encrypted(非端對端加密;查詢會經過伺服器到 LLM 提供商)
- We collect anonymous analytics to improve the product(收集匿名使用數據以改進產品)
- Payment requires an email for receipts, not linked to your queries(訂閱需要 email 作為收據,不與查詢關聯)
**0.4 開發原則(Engineering Principles)**

- **Local-first 偏好儲存:**使用者偏好預設存於 localStorage,不存入伺服器。伺服器端只看到匿名 hash 或 session-level metadata。
- **Stateless 查詢處理:**每次查詢是獨立 session。伺服器處理完後不保留查詢內容。PostHog 只收匿名事件,不收查詢全文。
- **Provider-agnostic 架構:**所有 LLM 呼叫透過 Provider interface,可隨時切換。Generator 和 Guard 可獨立切換 provider。
- **i18n-first:**所有使用者可見字串透過 i18n key 處理,16 語言同步。新增功能必須同時加入 i18n key。
- **Citation-mandatory:**所有醫療回答必須包含引用來源。無引用不輸出。
- **Degrade-gracefully:**非關鍵 API 失敗不 block 使用者流程(specialty 送出失敗、PostHog 失敗)。但關鍵查詢失敗需要明確錯誤提示。
**一、開發 Phase 總覽**

本 PRD 涵蓋四個 Phase,依順序執行。每個 Phase 都有明確的目標與驗收標準。

| **Phase** | **時程** | **目標** | **代表性任務** |
| --- | --- | --- | --- |
| Phase 0 | Week 0-3 | 基礎建設 + SEO 止血 + Explain 強化 | Landing Page SEO 修復、i18n hreflang、PostHog wrapper、Explain 臨床推理強化、Model Provider 抽象層、query_id、Citation 追蹤、Bug 回報 |
| Phase 1A | Week 3-4.5 | 定位落地 | Onboarding 三問、首頁動態範例、user_context、隱私聲明 |
| Phase 1B | Week 5-8 | 差異化功能 | 處方解析 MVP、FeedbackBar 原因 chip、Citation ⓘ、Settings |
| Phase 1C | Week 9-12 | 護城河啟動 | 在地差異提示(YAML 知識庫 + Tier 1 6 國 + Tier 2)、跨語言橋接面板 |

**Phase 0 的執行優先級(v1.2 更新):**

- P0(最優先,Day 1 就做):2.5 Landing Page SEO 修復 — GTM 啟動前必須先止血
- P0(同樣優先,Day 1-2):2.6 i18n SEO 最小版本(hreflang)
- P1(Week 0-3 主力):2.0 PostHog 基礎建設、2.7 Explain 臨床推理強化(v1.2 新增)、2.1 Model Provider 抽象層、2.2 query_id、2.3 Citation 追蹤、2.4 Bug 回報
**為什麼 SEO 修復是 P0?**

你 Phase 1A Week 1-2 要發第一篇 LinkedIn「隱私優先宣言」post。如果那時 Landing Page 還是 spinner shell,LinkedIn preview 會沒有 title,分享效果大打折扣。這個流血問題 3-5 小時就能修好,不修整個 GTM 前期投入效果腰斬。

**為什麼 Explain 強化排在 Model Provider 之前?(v1.2 新增)**

Explain 目前的 output 只是把數值翻譯成白話,沒有體現「AI 做得比 Google 好」的專業推理價值。Model Provider refactor(2.1)是大工程(5-7 天),若先做 refactor 再改 Explain,Explain 的 system prompt 會在兩個 provider 上重測一遍;反過來先把 prompt 定型,refactor 時就只需要驗證「輸出一致」。順序 2.7 → 2.1 省一次 regression 測試。

**二、Phase 0 — 基礎建設 + SEO 止血**

Phase 0 的任務都是看不見的技術基礎,但決定後續所有功能的擴展性。必須在 Phase 1A 之前完成。

**v1.2 重大變更:**Phase 0 從 v1.1 的 2-2.5 週延長為 2.5-3 週(13-15 個工作天)。原因:新增 2.7 Explain 臨床推理強化(1-2 天)。2.7 排在 2.1 Model Provider 之前執行,原因見上節最後一段。

**post-v1.2 調整(2026-04-20):**再新增 2.8 Anonymous Trial Flow(1.5-2d)與 2.9 Verify 輸出語言對齊 user locale(1d)兩個 discovered gaps,Phase 0 總工時調整為 3-3.7 週(加 2.8 + 2.9 兩個 post-v1.2 discovered gaps 合計 2.5-3 天)。

**v1.3 變更(2026-04-28):**§ 4.5 公開分享連結 + § 4.6 SEO Explore Pages 雖然 spec 編號為 4.x(與 Phase 1B 其他 4.1-4.4 features cohere),執行順序插入 Phase 0 末段,於 § 2.7 Step 8 acceptance 通過後、Phase 0 Retrospective 之前。理由:soft launch(= Phase 0 ship gate)需要 share + SEO 機制 day-1 在位;GTM_V1 § 5.4 L3 mechanics 已假設兩者存在,缺一會使 soft launch L3 traction(paid acquisition cost / organic discovery)訊號失真。執行順序:§ 2.7 Step 7 → § 2.7 Step 8 → § 4.5 → § 4.6 → Phase 0 Retrospective。Phase 0 Retrospective 順延對應(時程影響不在本 PRD 估算)。

**Phase 0 執行順序建議**

| **順序** | **任務** | **說明** | **工期** |
| --- | --- | --- | --- |
| Day 0 | 2.5 Landing SEO 修復 + 2.6 hreflang | P0 最優先,GTM 前置 | 4-7h |
| Day 1-1.5 | 2.0 PostHog 基礎建設 | 其他追蹤任務依賴此 | 1-1.5d |
| Day 2 | 2.2 query_id + 2.3 Citation 追蹤 | 可並行,依賴 2.0 | 0.5d |
| Day 2.5-3.5 | 3.1 user_context schema(前移) | Onboarding 改版依賴此 | 1-2d |
| Day 3.5-4.5 | 2.4 Bug 回報入口 | 相對獨立可最後做(✅ 已完成 2026-04-19, production verified 2026-04-20) | 1d |
| Day 4.5-6 | 2.8 Anonymous Trial Flow(discovered gap,Decision 001 v0.2 Accepted) | 兩層 UX / 三層資料設計 | 1.5-2d |
| Day 6-7 | 2.9 Verify 輸出語言對齊 user locale(discovered gap,Accepted) | 傳 response_language,改 verify system prompt | 1d |
| Day 7-8.5 | 2.7 Explain 臨床推理強化(v1.2 新增) | 改 explain_service.py prompt,1-2 天 | 1-2d |
| Day 8.5-14.5 | 2.1 Model Provider 全面 refactor | 最大工作量,8 檔案 | 5-7d |
| Day 15-16.5 | Regression 測試 + buffer | 統一驗收 | 2d |

**2.0 PostHog 事件基礎建設(v1.1 新增)** ✅ SHIPPED 2026-04-18 (dd210b9, 3876239)

**背景**

FEATURE_AUDIT.md 第 4 節發現:整個 repo 只有 1 處 posthog.capture(),就是 _app.tsx 的 $pageview。v1.0 PRD 的 2.2(query_id)、2.3(Citation 追蹤)都假設 event 體系已存在,但實際上該體系根本沒建。

必須先建統一 analytics wrapper + event schema,後續所有追蹤任務都用這個 wrapper。

**2.0.1 統一 Analytics Wrapper**

*目標*

所有 PostHog event 透過單一 wrapper 發送,自動帶上共通欄位,降低呼叫端心智負擔。

*功能需求*

**需求 1:Wrapper 位置與 API**

- 檔案位置:utils/analytics.ts
- 對外 API:track(eventName: string, properties?: Record<string, any>)
- 自動注入共通欄位(見 2.0.2):呼叫端只傳 event 特有 properties
- Fire-and-forget:不 await,不 block 使用者流程
**需求 2:Degrade Gracefully**

- PostHog 失敗(網路錯誤、quota 滿、SDK 未初始化)不拋出例外
- failure 時 console.warn(dev 模式)或 silent(production)
- SDK 未初始化時呼叫 track() 不崩潰,靜默忽略
**需求 3:Identify 與 Super Properties**

- 使用者登入時呼叫 identify() 綁定 PostHog distinct_id 與 clerk_user_id
- Super properties 在 identify 後設定:plan_type、workplace_category、role_category、work_language、locale
- 未登入使用者仍可發 event,用匿名 distinct_id
**需求 4:Reset 機制**

- 使用者登出時呼叫 reset(),清空 distinct_id 與 super properties
- Settings 點「清除我的偏好」時也呼叫 reset()
**2.0.2 Event Payload 共通欄位**

| **欄位** | **型別** | **來源** | **說明** |
| --- | --- | --- | --- |
| query_id | string │ null | session memory | 當前查詢的 ID(backend 產生,SSE 傳回,見 2.2) |
| session_id | string | session storage | 整個瀏覽器 session 的 UUID |
| user_context_hash | string │ null | localStorage | workplace + role + work_language 的 SHA-256 前 16 字元 |
| locale | string │ null | localStorage | TW、JP、KR 等國家代碼 |
| plan_type | string | Clerk / backend | free │ pro |
| work_language | string │ null | localStorage | zh-TW、ja、ko 等 |

**2.0.3 驗收標準**

- utils/analytics.ts 存在,exports track()、identify()、reset()
- 任何呼叫 track() 的地方都不直接呼叫 posthog.capture()
- PostHog Dashboard 可以看到 event 自動帶上 6 個共通欄位
- PostHog SDK 未初始化時 track() 不崩潰
- 使用者登出後 distinct_id 正確 reset
工期:1-1.5 天。

**2.1 Model Provider 抽象層(v1.1 擴充)** ❌ PENDING (Phase 0 remaining, largest block)

**目標**

將目前綁定 OpenAI 的 API 呼叫改為透過 Provider interface,可切換到 Anthropic 或其他供應商。

**v1.1 策略決策:**做完整版抽象層,但預設 Provider 維持 OpenAI、模型名維持現有。測試過品質可以,不改現況。架構彈性與品質穩定兩者兼得。

**背景(v1.1 更新)**

- 目前 Generator 和 Guard 都綁定 OpenAI API,供應商風險高
- FEATURE_AUDIT.md 發現 OpenAI hardcode 散在 8 個檔案,不是 2 個
- 輕量版(只抽 env var)不解決「未來可以快速換 provider」,之後還是要做完整 refactor。兩次 refactor 比一次貴且 regression 風險加倍
**功能需求**

**需求 1:Provider Interface**

- 統一 Provider interface,至少包含 generate() 和 stream()
- 統一 input/output schema
- 各供應商特有參數透過 provider-specific config 傳入
**需求 2:實作兩個 Provider**

- OpenAIProvider:現有邏輯重構進這個類別
- AnthropicProvider:支援 Claude Haiku / Sonnet / Opus
- 兩個 provider 的錯誤處理一致
**需求 3:環境變數切換**

- 應用啟動時讀取環境變數,決定實例化哪個 provider
- Generator 和 Guard 可用不同 provider
**需求 4:Token 計費統一化**

- Provider response 包含 token usage(input_tokens, output_tokens)
**需求 5(v1.1 新增):全面 Refactor 清單**

Provider 抽象層 refactor 必須涵蓋以下所有檔案:

| **檔案** | **使用類型** | **需要改動** |
| --- | --- | --- |
| api/rag/generator.py | 主要 LLM(RAG) | from openai import AsyncOpenAI → Provider.get_generator(). RAG_MODEL 改 env var |
| api/middleware/guards.py | Guard + medical intent | 兩處 client = OpenAI() 改 Provider.get_guard(). model 字面量改 env var |
| api/rag/retriever.py | 檢索相關 LLM | 改 Provider.get_retriever() 或 get_generator() |
| api/rag/reranker.py | Reranking | 預設 model="gpt-4o-mini" 改 env var RERANKER_MODEL |
| api/services/explain_service.py | Explain 功能 | 改 Provider.get_generator() |
| api/services/entity_extractor.py | 實體抽取 | 改 Provider.get_lightweight() |
| api/utils/llm_judge.py | LLM 品質判斷 | 改 Provider.get_judge() |
| api/database/vector_store.py | 向量存儲 | Embedding 透過 Provider,可能需獨立 get_embedder() |
| api/server.py | 主 server | model="gpt-4o" 字面量改 env var,審視整個 server.py |

**需求 6(v1.1 新增):環境變數清單**

| **環境變數** | **預設值** | **用途** |
| --- | --- | --- |
| GENERATOR_PROVIDER | openai | RAG Generator provider |
| GENERATOR_MODEL | gpt-4.1 | RAG Generator 主要模型 |
| GENERATOR_FALLBACK_MODEL | gpt-4.1-mini | RAG Generator 降級模型 |
| GUARD_PROVIDER | openai | Guard provider |
| GUARD_MODEL | gpt-4.1-mini | Guard 模型 |
| RERANKER_PROVIDER | openai | Reranker provider |
| RERANKER_MODEL | gpt-4o-mini | Reranker 模型 |
| LIGHTWEIGHT_PROVIDER | openai | 輕量呼叫 |
| LIGHTWEIGHT_MODEL | gpt-4o-mini | 輕量呼叫模型 |
| JUDGE_PROVIDER | openai | LLM judge provider |
| JUDGE_MODEL | gpt-4o | LLM judge 模型 |
| EMBEDDER_PROVIDER | openai | Embedding provider |
| EMBEDDER_MODEL | text-embedding-3-small | Embedding 模型 |

**需求 7(v1.1 新增):Regression 測試清單**

Refactor 後必須逐項驗證:

- Research 查詢:送已知 query,比較 refactor 前後答案相似度
- Verify 查詢:送已知交互作用(Warfarin + Amoxicillin),確認 severity 一致
- Explain 功能:送已知醫療報告,確認 entity 抽取結果一致(v1.2 補充:同時驗證 2.7 風險分層標籤一致)
- Guard 邊界:送醫療 vs 非醫療 query,確認 classification 一致
- Streaming:SSE 串流沒中斷、不漏字
- 錯誤處理:mock provider 失敗,確認降級邏輯正常
- Token usage:cost_tracker 紀錄 input/output tokens 正確
**需求 8(v1.1 新增):共通錯誤物件格式**

對外統一成 6.3 節定義的 VelaError:

- rate limit → VelaError code='LLM_RATE_LIMITED', retryable=true
- timeout → VelaError code='LLM_TIMEOUT', retryable=true
- invalid request → VelaError code='LLM_INVALID_REQUEST', retryable=false
- auth failure → VelaError code='LLM_AUTH_FAILED', severity='critical'
- service unavailable → VelaError code='LLM_PROVIDER_UNAVAILABLE', severity='critical'
**驗收標準**

- 環境變數切換 openai ↔ anthropic,同一查詢拿到正常回應
- Generator 用 OpenAI、Guard 用 Anthropic,混合模式正常
- 現有測試全部通過(無 regression)
- Provider 錯誤正確轉換為 VelaError
- 8 個 backend 檔案都不直接 import openai,改透過 Provider
**不做什麼**

- 不做本地模型(Llama、Mistral)支援
- 不做動態 provider 切換(運行時切換)
- 不做 cost tracking dashboard
**工期(v1.1 校準)**

- Provider Interface 設計:0.5 天
- OpenAIProvider 實作(8 檔案 refactor):2-3 天
- AnthropicProvider 實作:1 天
- 錯誤處理統一:1 天
- Regression 測試:1-1.5 天
- 總計:5-7 天
**2.2 query_id 關聯系統(v1.1 修正)** ✅ SHIPPED 2026-04-19 (1737683, 04aae40)

**目標**

每個查詢產生全域 query_id,所有相關 PostHog 事件帶這個 ID,讓後續分析可以 join 出「查詢 → 引用點擊 → 反饋」鏈路。

**v1.1 修正**

**v1.0 原需求:**「前端生成 UUID v4 作為 query_id」

**v1.1 修正:**沿用 backend 現有 audit_id,不另外生 UUID。避免兩套 ID 混用。

理由:FEATURE_AUDIT 發現 backend api/server.py:449 已經產生 audit_id(格式 res_<hex16> / ver_<hex16> / exp_<hex>)。實作方式:backend 透過 SSE event 的第一個封包傳回 audit_id,前端收到當作 query_id 使用。

**功能需求**

**需求 1:query_id 來源**

- 使用者送出查詢,backend 產生 audit_id(現有邏輯)
- SSE 串流第一個 event 帶 query_id(即 audit_id)
- 前端收到後存入 session memory,綁定當前查詢
- 切換到新查詢時,新 query_id 產生
**需求 2:事件 payload 統一欄位**

所有以下事件都帶 query_id:

- query_submitted
- query_completed
- citation_clicked
- feedback_thumbs_up / feedback_thumbs_down
- feedback_reason_selected(Phase 1B 新增)
- locale_hint_clicked(Phase 1C 新增)
- language_bridge_expanded(Phase 1C 新增)
**需求 3:額外 anonymous context**

每個事件除了 query_id,還帶:

- session_id(整個瀏覽器 session)
- user_context_hash(角色 + 場域 + 語言 SHA-256 前 16 字元)
- locale(使用者選擇的地區)
**驗收標準**

- 使用者送出查詢 → 點擊引用 → 按讚,PostHog 可用 query_id join 出完整鏈路
- PostHog Insights 可依 user_context_hash 切分「藥師 vs 醫師 vs 醫學生」
- 切換查詢後,新 query_id 產生,舊不再綁定
工期:0.5 天。

**2.3 CitationPanel 引用點擊追蹤** ✅ SHIPPED 2026-04-19 (04aae40)

**目標**

在 CitationPanel 的「View source」連結加 PostHog 追蹤,得知哪些引用來源最被信任。

**功能需求**

**需求 1:點擊事件**

點擊任何引用連結時發送 citation_clicked,包含:

- query_id(見 2.2)
- source_type(見下方 enum)
- url(連結本身)
- citation_position(答案中第幾個引用)
**需求 2:source_type 判定**

source_type 必須是以下 enum 之一:

- 'PubMed' (學術文獻) | 'FDA' / 'DailyMed' (藥品仿單) | 'LOINC' | 'MedlinePlus' | 'RxNorm'
- 'WHO' | 'NICE' | 'EMA' | 'Cochrane'
- 'LocalAuthority'(Phase 1C 加)| 'Other'
- **(2026-05-06 新增)** 'DailyMed' enum value 預定 Phase 1B Week 4-5 ship 時啟用 (per BACKLOG [P0] DailyMed API integration)。詳見新增 §2.10 資料來源策略。

判定邏輯:

- 若 citation object 已有 source_type,直接用
- 否則從 URL 判斷(pubmed.ncbi.nlm.nih.gov → PubMed 等)
- 判斷邏輯抽成獨立 helper
**v1.1 更新:**FEATURE_AUDIT 確認 frontend CitationPanel 已有 source_type 欄位,backend schemas.py enum 更完整。建議擴充 frontend 型別與 backend 對齊。URL 判斷作為 fallback 保留。

**需求 3:不 block 連結跳轉**

- PostHog capture 是 fire-and-forget,不 await
- 原本的 target、rel、樣式不變
**驗收標準**

- 點擊 Citation 連結,Network tab 看到 PostHog event,payload 正確
- 多個 citation 各自的 source_type 和 url 正確(無 closure 陷阱)
- PostHog Dashboard 能 breakdown by source_type
工期:0.5 天。

**2.4 Bug 回報內建入口** ✅ SHIPPED 2026-04-20 (380d11f, dfdef25, 11270a9)

**目標**

右下角浮動「💬 回報問題」按鈕,降低使用者回報門檻。Sentry 只能抓 JS 錯誤,抓不到「答案很爛」這種體驗問題。

**功能需求**

**需求 1:浮動按鈕**

- 位置:右下角固定(手機時左下,避開其他元素)
- 樣式:圓形,對話泡泡圖示,hover tooltip「回報問題 / Report an issue」
- 所有頁面顯示,但 Onboarding 期間不顯示
**需求 2:回報表單**

點擊後彈出 Modal,包含:

- 問題類型下拉:「答案不準確」「UI 錯誤」「功能建議」「其他」
- 描述欄位(textarea,最多 2000 字,必填)
- 選填 email 欄位
- 自動附加資訊(使用者不需填):當前 URL、最近一次 query_id、user_context_hash、瀏覽器資訊
**需求 3:送出行為**

- 送到 support@an-tho.com,標題包含問題類型
- 同時發 PostHog event: bug_report_submitted
- 顯示「已送出,感謝回報」,2 秒後自動關閉
**需求 4:i18n**

- 所有字串透過 i18n,16 語言
- i18n keys 前綴:bug_report.*
**驗收標準**

- 送出後 support@an-tho.com 收到郵件
- PostHog 有對應事件
- 16 語言翻譯品質過關
工期:1 天。

**2.5 Landing Page SEO 修復(v1.1 新增,P0 最高優先)** ✅ SHIPPED 2026-04-17 (e00d8ac, i18n a22ce9f)

**目標**

修復 Landing Page 的 SEO 盲點,確保 Google、LinkedIn、AI 爬蟲能完整看到 Vela 的定位訊息。這是 GTM 啟動前的必做任務。

**背景**

SEO 體檢發現 pages/index.tsx 的 Home component 有 isLoaded spinner gate,導致 Next.js SSG 預渲染時 Clerk 的 useUser() 回 isLoaded=false,整個 LandingPage 和它的 <Head> 都被擋在 spinner 後面。

結果:out/index.html 只有 2.9KB 的 spinner shell,所有 meta tags 都缺失,LinkedIn preview、Google SERP 都拿不到內容。

**功能需求**

**需求 1:修 isLoaded gate**

- 用 Clerk 的 <SignedIn> / <SignedOut> pattern 取代 isLoaded 條件渲染
- SSG build 時預渲染 <LandingPage /> 為預設內容
- Client hydrate 後,Clerk 認證狀態決定是否切換到 Dashboard
**需求 2:更新 Landing Page 為新定位**

- Tagline:Ask in your language. Verified by official sources. Answered in yours.
- Subtitle:The AI medical search for healthcare professionals who work beyond English.
- 三大 Value Props:Your Language / Official Sources / Anonymous by Default(見 0.2)
- 新 Privacy-first 透明定義區塊(見 0.3)
- 所有文字 i18n(至少英文 + 繁中完整,其他 14 語言可延後)
**需求 3:Meta Tags 完整化**

新 Landing Page 的 <Head> 必須包含:

- <title>:"Vela — Privacy-first AI medical search for healthcare professionals"
- <meta name="description">:跨語言 AI 搜尋 + Privacy-first 敘述
- og:title, og:description, og:url, og:image, og:type, og:site_name
- twitter:card, twitter:title, twitter:description, twitter:image
- <link rel="canonical" href="https://vela.an-tho.com/">
- <meta name="robots" content="index, follow">
**需求 4:JSON-LD Structured Data**

Landing Page 底部加入兩個 schema.org JSON-LD:

- SoftwareApplication schema(產品類別、定價、描述)
- Organization schema(品牌資訊)
**需求 5:Sitemap 補全**

public/sitemap.xml 加入目前缺的 public 頁面:

- /pricing
- /faq(20KB 內容最豐富,long-tail SEO 核心)
- 之後 Phase 1A 新增 /about 時也要加
**需求 6:App 頁面加 noindex**

對不該被 index 的 auth-gated 頁面加 <meta name="robots" content="noindex">:

- /research
- /verify
- /explain
- /history
**驗收標準**

- npm run build 後 out/index.html 從 2.9KB 變成 10KB+
- <title>、og:title、canonical 都在初始 HTML 裡
- 禁用 JavaScript 的瀏覽器能看到 hero section 和三 value props
- JSON-LD 通過 validator.schema.org 驗證
- LinkedIn Post Inspector 顯示正確 title + description + image
- GSC URL Inspection 顯示 Landing Page 可被 index
- /research 等 app 頁面顯示 noindex
**工期**

約 3-5 小時(含驗證),Phase 0 Day 1 做掉。

**不做什麼(延後)**

- 16 語言 i18n 的 hreflang 處理 — 見 2.6
- Onboarding 三問 — Phase 1A 3.2
- 首頁動態範例 — Phase 1A 3.3
**2.6 i18n SEO(hreflang,v1.1 新增,P0 次高優先)** ✅ SHIPPED 2026-04-17

**目標**

讓 Vela 的 16 語言內容對 Google 可見,解決「SSG 只產出英文版 HTML,其他 15 語言 SEO 等於零」的問題。

**背景**

目前 utils/LangContext.tsx 用 localStorage 存語言偏好,前端 JS 執行後才切換文字。SSG 產出的 HTML 永遠是英文。Google 只能 index 英文版本。

repo-wide grep hreflang|rel=.alternate 無任何匹配。<html> tag 也沒有 lang 屬性。

**兩個可選策略**

*策略 A:Hybrid(推薦,最小成本)*

- 保留現有 JS 切換行為(不破壞既有 UX)
- 加 <link rel="alternate" hreflang="x-default" href="https://vela.an-tho.com/"> 作為預設
- Landing Page 的初始 HTML 保持英文(Google 的預設 index 版本)
- Landing Page 的 <Head> 動態加 hreflang,列出所有支援語言的 URL
**Pros:**實作最簡單,1-2 小時可完成

**Cons:**Google 仍主要 index 英文版本,中文 / 日文 SEO 效果有限但至少存在

*策略 B:獨立 URL per locale(完整,工期長)*

- 用 Next.js getStaticPaths 為每個主要語言產生獨立 URL:/zh-TW、/ja、/en
- 每個 locale URL 的 SSG HTML 就是該語言的完整內容
- hreflang 指向實際不同的 URL
- Google 可分別 index 每個語言版本
**Pros:**SEO 效果最完整,中文 / 日文市場能拿到真實 search traffic

**Cons:**工期 3-5 小時,需要重構 routing 和 LangContext

**建議做法**

**Phase 0 先做策略 A(1-2 小時),Phase 2 根據 traffic 決定是否升級到策略 B。**

理由:

- 策略 A 立刻解決「完全沒有 i18n SEO」的 0→1 問題
- 策略 B 的效益要看實際 search traffic,沒數據前不值得重構
- Phase 2 時會有 PostHog 的 locale 分布數據,能精準決定優先支援哪幾個語言做獨立 URL
**驗收標準(策略 A)**

- Landing Page 初始 HTML 有 <link rel="alternate" hreflang="..." href="..."> 至少 5 個(英文 + 主要亞洲語言)
- <html lang="en"> 作為預設(或根據 Accept-Language header 動態設)
- GSC International Targeting 不報錯
**工期**

- 策略 A:1-2 小時(Phase 0 內完成)
- 策略 B:3-5 小時(Phase 2 評估後再做)
**2.7 Explain 臨床推理強化(v1.2 新增,P1)** ✅ SHIPPED 2026-04-30 (Steps 1-8 + Path 1 + M06; commits cd697d1..dffd015)

**目標**

將 Explain 功能從「翻譯者」升級為「臨床推理助手」。目前 Explain 只是把醫療報告數值翻成白話,使用者看了沒有「這是 AI 才做得到」的感受;強化後要體現出組合推理、風險分層、在地脈絡,這些是 Google 搜尋與一般通用 AI 都做不到的專業價值。

**v1.2 決策:排在 2.1 Model Provider 之前執行**

- 2.1 是大工程(5-7 天),若先 refactor 再改 prompt,prompt 要在兩個 provider 各測一次
- 反過來先把 2.7 prompt 與輸出格式定型,2.1 refactor 時只需驗證「輸出一致」
- 順序 2.7 → 2.1 省一次 regression 測試,整體工期反而更短
**背景**

目前 explain_service.py 的 system prompt 要求 LLM 解釋每個醫療術語與數值。問題:

- 輸出像醫學辭典查詢,沒有跨項目的組合推理(例如 eGFR 45 + 糖尿病用藥,應該提示劑量調整風險)
- 沒有風險分層(所有項目看起來一樣重要,使用者不知道哪些要立即處理)
- 引用來源混用 LOINC(LOINC 是代碼對照表,不是臨床判斷來源)
- 用字過於肯定,缺乏 hedging,醫療專業人員對「AI 斬釘截鐵」有戒心
**功能需求**

**需求 1:System Prompt 改造 — 臨床組合推理**

改寫 api/prompts/explain_system.md(若未獨立則一併抽出,對齊 6.5 節 Prompt 管理規範)。核心指令:

- 先列出報告關鍵項目與數值(現有行為保留)
- **加入一個「臨床關聯」段落:辨識兩個以上項目之間的臨床意義**。範例:「eGFR 下降 + Metformin 使用」應觸發「腎功能與用藥劑量關聯」的組合提示
- 輸出不只是翻譯,而是「這些數字放在一起代表什麼」
- 組合推理最多展開 3 個關聯,避免過度推論
**需求 2:Hedging Language 強制**

Prompt 明確要求使用 hedging 語言,禁用斷言式表達:

- 可用:「可能提示...」「常見於...」「建議與臨床表現合併判讀」「需要進一步評估」「若伴隨 X 症狀,考慮 Y」
- 禁用:「您有...」「您的診斷是...」「您需要...」「這表示您得了...」
- Output 最後必須包含一句「本工具提供一般性解讀,不取代臨床判斷或主治醫師建議」
**需求 3:Citation 策略 — LOINC 禁用於臨床判斷**

Explain 的引用來源策略分兩類:

- **代碼對照類(可用 LOINC、RxNorm):**當使用者問「這個檢驗項目代碼是什麼」,LOINC 是正確來源
- **臨床判斷類(必須用 PubMed、FDA、NICE、Cochrane、國家指引):**當回答涉及「這個數值代表什麼 / 需要怎麼處置」,LOINC 不可作為主要引用
實作:Prompt 中明確指示 LLM 區分這兩類情境。Citation 階段在 post-processing 檢查:若 citation 只有 LOINC 來源但回答內容屬於臨床判斷類,強制要求補上 PubMed / FDA / 指引來源,否則降級輸出(見需求 5)。

**需求 4:風險分層標籤 🟢🟡🔴**

每個解釋項目或關聯提示後面加上風險分層 emoji + 短標籤:

| **Tag** | **Emoji** | **意義** | **範例** |
| --- | --- | --- | --- |
| 一般資訊 | 🟢 | 數值落在常規範圍,或僅為衛教性說明 | 「空腹血糖 92 mg/dL 🟢 一般資訊」 |
| 需要留意 | 🟡 | 邊緣值、輕微異常、或需搭配其他項目判讀 | 「LDL 145 mg/dL 🟡 需要留意」 |
| 建議立即諮詢 | 🔴 | 明顯異常、可能緊急、或多項目組合提示高風險 | 「eGFR 28 + 使用 NSAIDs 🔴 建議立即諮詢」 |

Prompt 要求 LLM 對每個項目判定等級。判定原則:

- 單一項目明顯異常 → 🟡 起跳,跨過臨床閾值 → 🔴
- 兩個以上項目組合推理觸發警訊 → 🔴
- 缺乏判定依據時,保守用 🟢 並附註「建議請教主治醫師」
**需求 5:輸出結構**

Explain response 對前端的 JSON schema 擴充:

- items: [{ term, value, explanation, risk_tier: 'green' | 'yellow' | 'red', risk_label, citations: [...] }]
- clinical_correlations: [{ items_referenced: [...], insight, risk_tier, citations: [...] }]
- disclaimer: 固定字串(需求 2 定義的免責宣告)
前端渲染:

- items 區塊每條後面顯示對應 emoji + label(透過 i18n key)
- clinical_correlations 放在 items 之後,有明顯視覺分隔
- disclaimer 固定在最下方,灰色小字
**需求 6:i18n**

- risk_label 透過 i18n key 處理:explain.risk.green / yellow / red
- disclaimer 透過 i18n:explain.disclaimer
- 16 語言同步
**需求 7:PostHog 事件擴充**

explain_completed 事件加入:

- correlations_count(本次回答產生幾條 clinical_correlations)
- risk_tier_distribution({ green: N, yellow: N, red: N })
- 用於後續分析:LLM 給 🔴 的比例是否過高/過低,與 FeedbackBar 回饋交叉驗證
**驗收標準**

- 針對「糖尿病 + 腎功能報告」測試,輸出必須有至少 1 條 clinical_correlations
- 針對「單純健檢正常值」測試,輸出沒有過度創造 clinical_correlations(false positive)
- 所有涉及臨床判斷的項目,citation 不只有 LOINC
- 所有項目都有 risk_tier 欄位
- 輸出最後一段包含 disclaimer 固定文字
- Hedging 檢查:抽 20 個真實 case,無任何「您有 X 病」「您需要 X 藥」的斷言
- Phase 0 LLM judge(api/utils/llm_judge.py)加 Explain 專用評估 prompt,判定輸出是否符合上述四項特徵
**不做什麼**

- 不給具體診斷建議
- 不給具體用藥劑量
- 不取代處方解析(見 4.4,處方解析有獨立流程)
- 不支援上傳病歷 PDF(Phase 1C 後評估 OCR)
**工期**

- Prompt 改寫與 JSON schema 擴充:0.5 天
- 前端渲染 risk tier + correlations + disclaimer:0.5 天
- 16 語言 i18n key 與翻譯:0.25 天
- LLM judge 評估 prompt + 真實 case 驗證:0.25-0.5 天
- 總計:1-2 天

## 2.8 Anonymous Trial Flow(Phase 0,P1,新增) ✅ SHIPPED 2026-04-22 (Rounds 1-3, commits 7a8c5a8, cc1e1c7, a8877e9, 24b1d79)

**Status**:Accepted(solo founder review, 2026-04-19)· detailed design in Decision 001 v0.2
**Full design**:[`docs/decisions/001-anonymous-trial-flow.md`](decisions/001-anonymous-trial-flow.md)
**發現日期**:2026-04-18(post-v1.2 discovered gap,not in original v1.2 scope)

### 背景

Landing Page 承諾 "No account required to try"(§ 0.3),但實際上點 "Try it for free" 被 Clerk sign-in 擋住。這是 Phase 1A LinkedIn 第一篇 post 的前置 blocker。

### 目標

兌現 § 0.3 Privacy-first 承諾,消除 GTM credibility gap,同時對齊維運計畫 v3 § 8.3 的 10 credits/day 成本預算。

### 設計摘要(完整規格見 Decision 001 v0.2)

**兩層 UX / 三層資料**:
- 對使用者感知:Try free / Pro
- 內部資料:L0 匿名 / L1 註冊免費 ("Vela for Work") / L2 Pro

**Credit 配置(對齊維運計畫 10 credits/day 上限)**:

| | Research | Verify | Explain | Model | 總 credits |
|---|---|---|---|---|---|
| L0 匿名 | 2/day | 2/day | **❌ 不開放** | GPT-4.1-mini | — |
| L1 "Vela for Work" | 2/day | 2/day | 1/day | GPT-4.1 | **10 credits** ✅ |
| L2 Pro | ~30/day | ~100/day | ~50/day | GPT-4.1 | 100 credits cap |

**L1 升級感來源(不靠量,靠解鎖 + 品質)**:
1. ⭐ Explain 從 L0 完全不開放 → L1 1/day(新功能解鎖)
2. ⭐ 7 天 history(stateless → persistent)
3. ⭐ 跨裝置同步
4. ⭐ Role-based 個人化範例
5. ✅ Model 品質升級(mini → GPT-4.1,對使用者包裝為「Enhanced clinical reasoning」)

**L1 對外 brand naming**:"Vela for Work"(註冊帳號版)
**對外絕不使用的技術語言**:"GPT-4.1-mini"、"upgraded model"、"LLM"
**對外使用的價值語言**:"Enhanced clinical reasoning"、"Deeper answers"、"Richer citation depth"

**Daily budget cap**:$2 USD/day($60/月 hard ceiling,保護成本失控)

**UX 升級路徑**:
1. Landing Page 點 "Try it free" 直接進 /research,不經過 Clerk
2. 第 3 次查詢完成後,顯示可關閉 soft CTA(「Sign up free — get deeper answers, saved history, and Explain」)
3. Quota 用完顯示 modal,含三選項:Sign up free / Continue tomorrow / Go Pro($9.99/月)
4. L0 嘗試使用 Explain 時,顯示「Explain is a free feature — sign up to unlock」

### 驗收標準(摘要,完整見 Decision 001 v0.2 § 2)

1. 無痕視窗打開 vela.an-tho.com → 點 "Try it free" → 直接送查詢不被 Clerk 擋
2. L0 使用者送出 Research 查詢 → 正常拿到 citations + disclaimer,FeedbackBar thumbs 點擊後顯示登入提示(不送 event)
3. L0 使用者 **進入 /explain 頁面 → 顯示 sign-up CTA 而非表單**(L0 完全無法用 Explain)
4. L0 第 3 次查詢完成後,答案下方顯示可關閉 soft CTA
5. L0 quota 用完(Research 或 Verify 任一項達上限)→ 顯示 modal 含「免費註冊 / 明天再來 / 升級 Pro」三選項,「明天再來」選項絕對保留
6. Daily budget 觸發 $2 cap 後,新匿名請求返回 429 + 明確錯誤訊息
7. 已註冊 L1/L2 使用者不受 anonymous cap 影響
8. L1 使用者的 Research / Verify / Explain 走 GPT-4.1(非 mini),延遲 / 品質符合既有 L2 行為
9. L0 使用者的 Research / Verify 走 GPT-4.1-mini
10. PostHog 可追蹤 L0 → L1 轉換 funnel(event: `anonymous_to_registered`)
11. 新 event `explain_locked_viewed` 可追蹤多少 L0 使用者試圖進入 Explain(重要:Phase 1A Week 4 review 的核心指標)

### Out of Scope(Phase 0 不做)

- 匿名使用者的 FeedbackBar 送出(以 tooltip 提示註冊即可)
- 匿名使用者的 history(stateless by design)
- 匿名使用者 user_context 個人化(通用範例池即可)
- 手機 / email 驗證(違反 privacy-first)
- reCAPTCHA(違反 privacy-first,見 Decision 001 § 4.2)
- 匿名使用者的 Explain(完全不開放,作為 L1 解鎖誘因)

### 工期

1.5-2 工作天,排入 Phase 0 位於 § 2.4 Bug 回報 之後、§ 2.7 Explain 強化 之前。

### 依賴

- 既有 `api/middleware/rate_limiter.py`(擴充 `RATE_LIMITS`)
- 既有 `api/services/usage_service.py`(加 anonymous branch,Explain 明確 reject)
- 既有 `utils/analytics.ts`(加匿名 event)
- 既有 Clerk `<SignedOut>` 組件(Landing Page CTA 改走 /research)
- 既有 `api/providers/factory.py`(加 `is_anonymous` 參數,routing 到 mini vs 4.1)

### Notes

- Credit 數字為 **Phase 0 initial values**。Phase 1A Week 4 根據 PostHog metrics 校準(trigger points 見 Decision 001 v0.2 § 6.3)
- Quota 限制**建議透過 env var 設定**,避免調整時要 redeploy(見 Decision 001 v0.2 § 3.4)
- **L1 credit 總和嚴格不超過 10 credits/day**,對齊維運計畫 v3 § 8.3 的 Free tier 成本預算承諾
- L0 不開放 Explain 是策略選擇,Phase 1A Week 4 若發現 `explain_locked_viewed` < 20% → Explain 解鎖誘因弱,考慮 L0 開放 1 次 Explain

## 2.9 Verify 輸出語言對齊 user locale(Phase 0,P1,新增) ✅ SHIPPED 2026-04-20 (c621e3b, ee055d4, b2250ca)

**Status**: Accepted (solo founder review, 2026-04-20)
**發現日期**: 2026-04-20(post-2.4 production smoke test)

### 背景

Vela 核心承諾 "Ask in any language, answered in yours"(§ 0.2)對 Verify 服務失效。使用者把介面切換為繁中、點選英文藥名標籤(例如 Warfarin + Aspirin),/verify endpoint 回傳英文交互作用分析,違反承諾。

根本原因:Verify input 是結構化藥名 tokens(不是自然語言),LLM 無法從 input 推論使用者期待輸出語言。Research / Explain 輸入是自然語言,LLM 可從輸入語言推論輸出語言,所以運作正常。

### 目標

- 把「使用者期待輸出語言」訊號明確傳入 Verify 的 LLM prompt
- 保留藥名 canonical 英文格式(安全性 + 可搜尋性)
- 翻譯所有描述性內容(severity label、description、recommendation)

### 設計原則

**保留英文**:
- 藥名 canonical(e.g., `Warfarin`、`Aspirin`)
- FDA Label Source 引用標示

**翻譯成 user locale**:
- 交互作用嚴重度 tag(Major → 嚴重)
- 機制描述
- 建議與監測事項
- Hedging 語言

### 技術實作

**前端 (pages/verify.tsx)**:
- fetch /api/verify 時帶 `response_language` 參數,取自 LangContext
- 語言來源 fallback 順序:user_context.work_language → UI language → browser Accept-Language → "en"

**後端 (api/services/verify_service.py 或 api/prompts/verify_system.md)**:
- System prompt 接受 `{response_language}` 變數
- 明確指示 LLM:「回覆用 {response_language},藥名保留英文 canonical,嚴重度使用對應語言」

### 驗收標準

1. UI 切繁中 → 點 Warfarin + Aspirin → 送出 → severity tag 顯示「嚴重」不是「Major」
2. UI 切繁中 → 描述內容、建議都是繁中
3. UI 切繁中 → 藥名仍顯示為 `Warfarin, Aspirin`(英文 canonical 保留)
4. UI 切日文 → 同樣邏輯(日文描述 + 英文藥名)
5. UI 切其他語言 → fallback 可運作(至少英文)

### 不做什麼

- 不把藥名翻譯成當地語言(保留 English canonical)
- 不做靜態預翻譯庫(維護成本過高)
- 不做多層翻譯(先英文再翻),直接用 LLM 一次輸出目標語言

### 工期

1 個工作天

### 依賴

- 既有 `utils/LangContext.tsx`(已存在,提供當前 UI locale)
- 既有 `api/services/verify_service.py`
- 既有 `api/prompts/verify_*.md`(若存在)

### Notes

本節是 post-v1.2 discovered gap,發現於 2.4 production smoke test 時的多語測試。

**2.10 資料來源策略 (2026-05-06 新增)**

> **背景:** 截至 v1.3,Vela 整合 PubMed + FDA + LOINC + RxNorm + MedlinePlus 5 個 source。Phase 1B 加入 DailyMed,Phase 1C 加入 WHO ICD-11 (術語 anchor) 和 WHO 內容 ingestion。本節定義各 source 在產品中的職責邊界,避免重複工作或誤用。

**2.10.1 Source 分層模型**

四層醫療權威 source,藥師在不同情境跨層使用屬正常行為:

| Layer | Source | 內容性質 | 回答的問題類型 |
| --- | --- | --- | --- |
| 1 學術文獻 | PubMed | 全球生醫期刊論文索引 (36M+ 篇) | 「最新研究怎麼說」「meta-analysis 結論」「罕見副作用 case report」 |
| 2 官方藥品仿單 | FDA OpenFDA → DailyMed | 美國核准藥品 official label | 「official 適應症」「禁忌症 list」「黑框警告內容」 |
| 3 全球指引 | WHO 全球指引 (Phase 1C) | 全球公衛 baseline (Essential Medicines List, treatment guidelines, GHO 統計) | 「WHO 對 X 疾病的全球建議」「東亞地區 X 盛行率」 |
| 4 術語 anchor (內部用) | WHO ICD-11 (Phase 1C) | 跨語言疾病分類碼 (14 官方語言) | 跨語言 query alignment (內部 retrieval 機制,使用者不直接看) |

**FDA → DailyMed 升級說明 (Phase 1B Week 4-5):**
- FDA OpenFDA: 結構化品質不一,常缺最新版本欄位
- DailyMed: NIH 維護的同 label master copy,結構化品質高 1-2 個量級,免費,無 API key,無 rate limit
- Phase 1B 後 Verify pipeline 切換 DailyMed 為主、FDA OpenFDA 為 fallback;Research 將 DailyMed 作為第 4 個並行 retrieval source

**2.10.2 Source × Feature 矩陣**

| Source | Research (探索性問答) | Verify (藥物安全 / 交互作用) | Explain (報告 / 檢驗值解讀) |
| --- | --- | --- | --- |
| PubMed | ✅ 主力 — 文獻 evidence | ⚠️ 輔助 — 罕見交互作用 case report | ❌ 不直接用 |
| FDA OpenFDA (現有) | ✅ 部分 — 藥品基本資訊 | ✅ 主力 — 官方禁忌 / 交互作用 | ❌ 不直接用 |
| DailyMed (Phase 1B 取代 FDA 主力) | ✅ 升級 — 完整 label content | ✅ 主力 (取代 FDA) | ⚠️ 可選 — label 內「臨床用法」段落 |
| WHO ICD-11 (Phase 1C anchor) | 🔧 內部用 — 跨語言 query alignment | 🔧 內部用 — 藥品國際分類對齊 | 🔧 內部用 — 疾病名跨語言 |
| WHO 內容 RAG (Phase 1C) | ✅ 補充 — 全球 baseline | ⚠️ 邊緣 — 全球禁忌 baseline | ❌ 不直接用 |
| LOINC / RxNorm / MedlinePlus (現有) | ❌ | ❌ | ✅ Explain 主力 |

✅ 主力使用 / ⚠️ 輔助或可選 / 🔧 內部機制 / ❌ 不使用

**2.10.3 設計原則**

1. **Vela 自動跨 source 整合,不讓使用者選 source**
   - 與 UpToDate / OpenEvidence 一致 — 使用者不需要 「source filter」 UI
   - 違反此原則等於把 「整合 sources」 這個 Vela 核心價值還給使用者做
   - **例外觸發條件:** 若 PostHog 數據顯示 ≥10% query 包含 explicit source 偏好 (e.g. 「給我 WHO 觀點」),再考慮加 filter UI
2. **每條 citation 透明顯示來源層級**
   - CitationPanel source_type chip 顏色已實作 (PRD §2.3)
   - Citation ⓘ tooltip 補上 「這個 source 是什麼」 1-2 句說明 (Phase 1B Week 4-5 整合 DailyMed 時順手做,16 語言)
3. **權威性差異需在 retrieval ranking 反映 (Phase 1B Week 7-8 evaluate)**
   - 預設假設: DailyMed/FDA × 1.5,WHO 全球指引 × 1.3,PubMed × 1.0,個別 case report × 0.7
   - 風險: 純 semantic similarity 排序可能讓 PubMed individual studies 淹沒 DailyMed 官方 label
   - 評估方法見 BACKLOG [P2] Citation retrieval ranking evaluation
4. **新增 source 不需新 feature / 新 UI**
   - 4 source 整合進 RAG pipeline 後,使用者答案品質升級為 silent quality upgrade
   - 例外:Phase 1C 跨語言橋接面板 (PRD §5.X 待補) — 那是新 UI,不是 source 整合的 by-product

**2.10.4 RAG pipeline 影響 (Phase 1B Week 7-8 evaluate)**

並行 retrieval:
- 當前 (v1.3): 3 queries × 3 sources = 9 並行 task
- Phase 1B 後: 3 queries × 4 sources = 12 並行 task (加 DailyMed)
- Phase 1C 後: 3 queries × 5 sources = 15 並行 task (加 WHO 內容)

Latency 影響可忽略 (asyncio.gather 並行)。Top-K=8 不變,LLM 看到的 evidence 數量不變,僅 candidate pool 擴大。

**待 Phase 1B Week 7-8 evaluate 後決定的事項:**
- Reranker 是否需要 source-weighted scoring (見 BACKLOG [P2])
- BM25 / hybrid search 是否引入 (傾向 Phase 1C 才考慮)
- Source weight 具體數值 (上述 1.5/1.3/1.0/0.7 為 hypothesis,需 dogfooding 驗證)

**2.10.5 為什麼不在 v1.3 spec 動 RAG**

§2.1 Model Provider refactor 是 Phase 0 末段最大 block,先抽乾淨 provider 介面,再動 retrieval / ranking。順序反了會重做兩遍。
真實 candidate pool 變大的數據還沒有 (DailyMed/WHO 都還沒接),現在動 reranker 是猜。
原則:**先量再動,別先動再量。**

**2.10.6 證據分層 (Evidence Tier Classification, 2026-05-08 補充)**

> **背景**: §2.10.1-2.10.5 處理「不同 source 之間」的權威分層 (PubMed / DailyMed / WHO 等)。但**同一 source 內**也有權威差異 — PubMed 收錄的論文,從 international clinical practice guideline 到 single-country survey research 都在,權威性差 1-2 個量級。2026-05-08 外部顧問 dogfooding feedback 揭示此問題:Vela retrieval 把以色列 Avidana 2025 observational study (Tier 4) 與 Wright 2014 JADA systematic review (Tier 2) 視為等同證據,且 5 顆星 credibility UI 強化了這個錯誤等同性(該 UI 已於 commit 211d9f7 移除)。

**證據分層 (5 Tier)**

| Tier | 證據類型 | 範例 | 適用情境 |
| --- | --- | --- | --- |
| 1 | International clinical practice guideline | AAPD / ADA / NHS / SDCEP / EAPD / WHO | 「現行國際共識」、「主流臨床指引」 |
| 2 | Systematic review / meta-analysis | Cochrane review / JAMA systematic review | 「現有證據綜合結論」、量化結論 |
| 3 | RCT / large prospective cohort study | NEJM RCT / large registry study | 「個別介入效果」、新療法評估 |
| 4 | Observational study / commentary review | Cross-sectional / case-control / 雜誌 commentary | 「方向性 association」、背景脈絡 |
| 5 | Survey / knowledge-attitude research | 醫師 / 家長認知調查 | 「人群認知現況」,非建議本身依據 |

**Retrieval ranking weights (per Tier, hypothesis)**

```
Tier 1 (guideline)         × 2.0
Tier 2 (systematic review) × 1.5
Tier 3 (RCT / cohort)      × 1.2
Tier 4 (observational)     × 1.0  (baseline)
Tier 5 (survey)            × 0.7
```

複合 weight: 最終 ranking score = `semantic_similarity × source_weight × tier_weight × recency_factor`

其中 `source_weight` 來自 §2.10.3 (DailyMed/FDA × 1.5, WHO 全球指引 × 1.3, PubMed × 1.0),`tier_weight` 為本節新增層級。

**設計原則 (2.10.6 補)**

1. **Tier classification 必須在 retrieve-time 完成,不在 generation time** — LLM 在看到 candidate 之前就已經 reranked,確保 Tier 1 evidence 真正進入 top 8 context。
2. **跨 Tier divergence 須在答案中明示** — 當 retrieve 結果同時包含 Tier 1 (例如 AAPD ≥1000 ppm) 與 Tier 4 (例如以色列 < 500 ppm),system prompt 須要求 LLM **explicitly 列出國際分歧**,而非取 majority。對齊 ADR 003 system prompt polish。
3. **Citation card 顯示 Tier label,移除 credibility 星等** — `Tier 1 / Clinical Guideline`、`Tier 2 / Systematic Review` 等取代之前的 5 星 UI(已於 commit 211d9f7 移除)。Tier label 在 Phase 1B 實作。
4. **Tier classification 來源**: PubMed publication_type metadata (e.g. `Practice Guideline`, `Systematic Review`, `Randomized Controlled Trial`) + journal metadata (Cochrane Library, JAMA, NEJM) + 標題 keyword fallback (e.g. "systematic review", "meta-analysis")。具體實作見 BACKLOG [P0] DailyMed entry sub-task。
5. **不適用於非-PubMed source**: DailyMed (Tier 2 by default, official label)、FDA OpenFDA (Tier 2)、WHO 全球指引 (Tier 1)、LOINC/RxNorm (參考資料,不參與 tier 排序)。

**2.10.6 對 §2.10.3-2.10.5 的影響**

§2.10.3 設計原則 #3 「權威性差異需在 retrieval ranking 反映」 範圍擴大:不只 source weight,還包含 tier weight。完整 ranking 公式如上。

§2.10.5 「為什麼不在 v1.3 動 RAG」 仍適用 — Phase 1B Week 7-8 evaluate 階段同時驗證 source weight + tier weight 兩層,先看 dogfooding 數據,再決定具體 weight 數值。

**三、Phase 1A — 定位落地**

Phase 1A 不做新功能,只做「感知層」——讓使用者進來的前 30 秒立刻感覺「這個產品為我設計」。

**3.1 User Context 資料模型** ❌ PENDING (Phase 1A — blocks Phase 1A)

**核心設計**

- Local-first 儲存:user_context 預設存在 localStorage
- 伺服器端只存 hash(若訂閱 Pro)
**Schema(前端 localStorage)**

Key: 'vela_user_context',結構:

- workplace: 'community' | 'hospital' | 'student' | 'research' | 'other' | null
- role: Role | null(根據 workplace 動態)
- work_language: LanguageCode | null
- locale: CountryCode | null
- onboarding_completed: boolean
- onboarding_completed_at: ISO datetime
- version: schema 版本(目前為 1)
**Role enum**

根據 workplace 動態:

- community: physician / pharmacist / nurse / therapist / other_clinical
- hospital: hospital_physician / hospital_pharmacist / hospital_nurse / other_hospital
- student: medical_student / resident / intern / other_student
- research: researcher / other_research
- fallback: other
**後端 Schema(選填,只有訂閱使用者)**

Table: user_profile(新表,不混在 user_usage 裡):

- user_id VARCHAR(64) PRIMARY KEY
- user_context_hash VARCHAR(16) — SHA-256 前 16 字元
- locale VARCHAR(8) — 用於推送在地提示
- created_at, updated_at
只存 hash,不存原始 context。原始只在 localStorage。

**API Endpoints**

只有訂閱使用者才需要:

- POST /api/user/context/hash:UPSERT into user_profile,回 { ok: true }
- GET /api/user/context/hash:讀取 user_context_hash 和 locale(跨裝置恢復用)
**3.2 Onboarding 三問改版** ❌ PENDING (Phase 1A)

取代「單一專科 dropdown」,改為三步驟:工作場域 → 角色 → 工作語言。每一步可略過,結束時顯示隱私聲明卡。

**關鍵設計原則**

- 可略過但不強迫:每步都有「略過」,但選擇會改善體驗
- 誠實定位:選「醫學中心」時顯示誠實提示
- 儲存在本地:所有選擇寫入 localStorage,PostHog 只收匿名 hash
**Step 1:你主要在哪裡工作?**

| **選項 value** | **顯示文字** | **圖示** | **特殊行為** |
| --- | --- | --- | --- |
| community | 診所 / 藥局 / 居家 / 社區醫療 | 🏥 | 正常流程 |
| hospital | 醫學中心 / 大型醫院 | 🏩 | 顯示誠實提示 |
| student | 醫學生 / 住院醫師 / 實習生 | 🎓 | 正常流程 |
| research | 研究 / 其他 | 🔬 | 正常流程 |

誠實提示文案(選 hospital 後):

繁中:我們最擅長服務社區醫療。如果你的醫院已訂閱 UpToDate 或類似工具,可能更適合你。但你仍然歡迎試用 Vela——特別是當你需要多語言支援或在地規範提示時。

**Step 2:你的角色?(根據 Step 1 動態)**

| **Step 1 選項** | **Step 2 顯示的角色選項** |
| --- | --- |
| community | 醫師 / 藥師 / 護理師 / 物理治療師 / 職能治療師 / 語言治療師 / 其他醫療人員 |
| hospital | 醫師 / 藥師 / 護理師 / 其他(較少選項,強化定位訊號) |
| student | 醫學生 / 藥學生 / 護理系學生 / 住院醫師 / 實習生 / 其他 |
| research | 研究員 / 其他 |

**Step 3:你的工作語言?**

- UI:dropdown,16 種語言
- 補充提示:「我們會用這個語言回答,但會幫你檢索英文文獻」
- 預設值:根據瀏覽器 Accept-Language
**Step 4:隱私聲明卡**

三步完成後顯示:

- ✓ 你的選擇只存在這個裝置上
- ✓ 我們不會記錄你是誰
- ✓ 你隨時可以在設定中修改這些偏好
- ✓ 不需要帳號、不需要 email 就能開始使用
**PostHog 事件**

- onboarding_step_completed: { step, skipped, user_context_hash }
- onboarding_completed: { total_steps_completed, user_context_hash, workplace_category }
**驗收標準**

- 三步流程可順利完成,可在任一步「略過」
- 選擇寫入 localStorage,重新打開瀏覽器仍在
- 選「醫學中心」正確顯示誠實提示
- Step 2 選項根據 Step 1 正確動態變化
- PostHog 事件正確,不含 PII
- 16 語言翻譯完整
**3.3 首頁動態範例查詢** ❌ PENDING (Phase 1A)

**功能需求**

- 首頁載入時從 localStorage 讀 user_context
- 根據 role 選擇對應範例查詢組
- 若 user_context 為空或 role null,顯示通用範例
**範例查詢內容(各角色 5-8 個)**

**社區藥師:**

- Metformin 腎功能不全怎麼調整?
- 這張處方有交互作用嗎?
- NOAC 各種藥物的差異
- 懷孕婦女可以用哪些抗組織胺?
- 糖尿病患者的流感疫苗建議
**居家護理師:**

- 糖尿病足潰瘍的居家照護重點
- 失能長者跌倒風險評估
- 為家屬準備的高血壓衛教要點
- 壓瘡分級與處置
- 居家鼻胃管照護常見問題
**社區醫師:**

- 上呼吸道感染抗生素選擇
- 高血壓用藥 2024 最新指引
- 兒童發燒處理
- 糖尿病初診病人的衛教步驟
- 什麼狀況該轉診專科?
**醫學生 / 住院醫師:**

- ARDS 的 Berlin criteria 是什麼?
- 抗生素 spectrum 比較表
- 急性胸痛的 differential diagnosis
- 心電圖常見異常模式
- USMLE Step 1 高頻考點:藥理學
**通用:**

- Metformin 是什麼?
- 糖尿病最新治療進展
- COVID-19 長新冠症狀
- 常見藥物交互作用
**UI**

- 範例查詢以「卡片」或「chip」形式顯示在搜尋框下方
- 點擊範例自動填入搜尋框並送出
- 每次首頁載入隨機打亂順序(同一角色池內)
**PostHog 事件**

- example_query_clicked: { example_text, role, position }
**3.4 隱私聲明 UI 元素(v1.1 補充工期)** ❌ PENDING (Phase 1A)

讓「Privacy-first」不只是口號,每個接觸點都能看到具體承諾。

**v1.1 補充:**FEATURE_AUDIT 發現 Privacy Policy 只有英文。Phase 1A 實作時必須同步完成 Privacy Policy 16 語言翻譯,工期追加 0.5 天。

**四個接觸點**

**接觸點 1:Landing Page**

- Hero 三支柱之一明確寫「Anonymous by Default」
- 獨立段落「What 'Privacy-first' means at Vela」
- 「無需註冊即可試用」CTA
**接觸點 2:Onboarding 結束的隱私聲明卡**

見 3.2 Step 4。

**接觸點 3:Settings 頁**

「隱私狀態」區塊:

- ✓ 我們沒有記錄你的身份
- ✓ 你的偏好儲存在這個裝置上
- └ [匯出我的偏好] [清除我的偏好]
- ✓ 你的查詢不用來訓練 AI
訂閱狀態(若 Pro):✓ email 只用於收據,不與查詢關聯,└ [更改訂閱 email] [取消訂閱]

**接觸點 4:Footer**

- 「Anonymous by Default」小字
- 連結到 Privacy Policy
- 連結到 About / Privacy-first 定義頁
**四、Phase 1B — 差異化功能**

Phase 1A 讓使用者感覺「這個產品為我設計」,Phase 1B 真正做出「只有 Vela 有的功能」。核心是藥師的處方解析 MVP。

*註:§ 4.5 + § 4.6 為 v1.3 新增 spec。雖編號 Phase 1B 4.x 維持章節 cohere,執行順序覆寫至 Phase 0 末段。詳見二章 v1.3 變更 NOTE。*

**4.1 FeedbackBar 👎 原因 Chip(v1.1 補充實作細節)** ❌ PENDING (Phase 1A)

**v1.1 補充:**FEATURE_AUDIT 確認 backend UserFeedback 表已有 feedback_text 欄位(目前永遠是 null)。實作時重用該欄位存 reason chip value 或「其他」補充文字,不用新 migration。

**功能需求**

**需求 1:倒讚後的互動**

- 按 👎 後按鈕不變色不立刻送出,展開原因 chip
- 點 chip 才真正送 feedback_thumbs_down + 原因 code
- 不選直接關閉,送出無原因的 feedback_thumbs_down
**需求 2:原因選項清單**

| **value** | **中文** | **英文** | **說明** |
| --- | --- | --- | --- |
| citation_insufficient | 引用不夠 | Not enough citations | 答案沒有足夠佐證 |
| answer_incorrect | 答案不準確 | Answer is incorrect | 答案內容錯誤 |
| not_relevant | 不相關 | Not relevant | 答案不切題 |
| too_vague | 太籠統 | Too vague | 答案不夠具體 |
| not_applicable_region | 不適用我的地區 | Doesn't apply to my region | 餵養 Phase 1C 在地差異提示 |
| other | 其他 | Other | 可選填文字補充 |

**需求 3:PostHog 事件**

- feedback_thumbs_down: { query_id, reason, user_context_hash, locale }
- feedback_reason_text: { query_id, text(前 500 字)}
**需求 4:UI 細節**

- 原因 chip 橫向排列,mobile 可換行
- 選擇後 chip 高亮一瞬後收起,顯示「感謝回饋」
- 「其他」展開 textarea(最多 500 字)
- fire-and-forget,不 block
**需求 5:👍 保持不變**

- 正面 feedback 不詢問原因(提高送出率)
- feedback_thumbs_up 事件仍送,無 reason 欄位
**驗收標準**

- 按 👎 展開原因 chip,選一個正確送 PostHog
- 選「其他」展開 textarea
- 不選直接關閉,送出無 reason 事件
- PostHog Dashboard 可 breakdown by reason
- 👍 行為不變
**4.2 Citation ⓘ Icon + 來源說明** ❌ PENDING (Phase 1A)

每個引用來源旁加 ⓘ icon,hover / tap 顯示一句話說明。對「PubMed 是什麼」「FDA 跟 TFDA 差異」有困惑的非英語使用者幫助極大。

**功能需求**

**需求 1:icon 與互動**

- 每個 citation 旁顯示 ⓘ icon(inline)
- 桌面:hover 顯示 tooltip
- Mobile:tap 顯示 popover
- 內容為「一句話說明」+「在地差異一句話」
**需求 2:各來源說明(繁中範例)**

| **來源** | **一句話說明** | **在地差異** |
| --- | --- | --- |
| PubMed | 美國國家醫學圖書館的同儕審查文獻資料庫 | 全球醫學研究標準,但非針對特定國家規範 |
| FDA | 美國食品藥物管理局的官方藥物資訊 | 台灣對應 TFDA,給付條件可能有差異 |
| WHO | 世界衛生組織的國際指引 | 各國政府可能有更具體在地規範 |
| NICE | 英國國家健康與照護卓越研究院的指引 | 美國、台灣可能有不同建議 |
| EMA | 歐洲藥品管理局的法規資訊 | 歐盟標準,亞洲各國有各自監管機構 |
| Cochrane | 實證醫學的系統性回顧資料庫 | 國際公認證據等級最高來源之一 |
| LOINC | 實驗室檢驗項目的國際標準代碼 | 台灣健保使用 LOINC 但有部分本地代碼 |
| MedlinePlus | 美國國立醫學圖書館的病人衛教資源 | 以英文為主,台灣衛教可參考健康九九 |
| RxNorm | 美國藥物命名的標準資料庫 | 台灣使用 TFDA 許可的藥物中英文對照 |
| LocalAuthority | 你所在地區的官方衛生機構 | 此連結指向官方來源,建議核對 |

**需求 3:PostHog 事件**

- citation_info_viewed: { query_id, source_type, viewed_on: 'desktop_hover' | 'mobile_tap' }
**驗收標準**

- 每個 citation 有 ⓘ icon
- 桌面 hover、mobile tap 正確顯示
- 10 個 source_type 都有對應文案
- 16 語言翻譯完整
**4.3 Settings 加 user_context 可修改** ❌ PENDING (Phase 1A)

**功能需求**

**需求 1:My Context 區塊**

- Workplace 可重選
- Role 根據 Workplace 動態顯示
- Work Language 可重選(16 語言)
- Locale(Phase 1C 啟用 UI)
**需求 2:儲存行為**

- 修改後立即寫 localStorage
- 若 Pro,同步更新 user_profile.user_context_hash
- 顯示「已儲存」提示
- 首頁範例查詢立即反映
**需求 3:「再問一次」機制**

- 使用者第 10 次查詢後,FeedbackBar 旁顯示小 banner
- 點 banner 跳出小 modal 直接選 role
- 可關閉,記錄 dismissed_prompts
**需求 4:隱私控制**

- 「匯出我的偏好」→ 下載 JSON
- 「清除我的偏好」→ 確認後清空 localStorage
- 若訂閱,「清除訂閱關聯資料」
**4.4 處方解析 MVP(藥師殺手級功能)** 🧊 OUT OF SCOPE (per ADR 004, 2026-05-04)

> **Status update 2026-05-04**: This feature is permanently removed from the active roadmap per [ADR 004](decisions/004-prescription-parser-deferral.md). No Phase 2 candidate spec; spec body below preserved as historical reference. If future market/competitive conditions warrant revisit, the feature will be re-designed from scratch — not resurrected from this spec. Source: ADR 004 + advisor discussion notes (git commit 394545e § 0, § 3).

**戰略定位:**這是 Phase 1B 的核心功能,Vela product-market fit 的試金石。UpToDate 做不到(它是知識庫)、OpenEvidence 做不到(沒有在地健保資料)、ChatGPT 可以模仿但不可靠(藥師不敢拿病人安全賭注)。目標:直接對應台灣社區藥師的 core job-to-be-done「確認處方安全」。

**MVP 範圍**

**MVP 做什麼:**

- 文字輸入處方(學名/商品名/縮寫都接受)
- 自動解析藥名、劑量、頻次、天數
- 產出交互作用矩陣(視覺化紅黃綠)
- 每個藥的資訊卡(適應症、禁忌、常見副作用)
- 「需要特別注意」清單
**MVP 不做:**

- OCR(V2 再加)
- 腎肝功能調整(V2 再加)
- 健保給付條件檢查(V3 再加)
- 病人衛教單生成(V2 再加)
- 存檔、歷史紀錄(違反 Privacy-first)
**UI**

- 入口:主導航或首頁加「處方分析」。Role = pharmacist 時在首頁突顯
- 輸入區:大 textarea,placeholder 示範格式,範例填入按鈕
- 輸出區三區塊:交互作用矩陣、每個藥的資訊卡、「需要特別注意」清單
**技術實作**

解析流程(Pipeline):

- Stage 1:LLM-based parsing(自由格式 → 結構化 JSON)
- Stage 2:藥物資訊查詢(RxNorm / PubMed)
- Stage 3:交互作用查詢(現有 RAG)
- Stage 4:綜合分析,生成「需要特別注意」清單
**隱私與安全**

- 處方文字絕不儲存於伺服器(stateless)
- 輸入欄位加提示:「請勿輸入病人姓名、身份證字號、病歷號」
- 輸出下方免責:「本工具僅供臨床人員參考,不取代專業判斷」
- PostHog 只收事件和 metadata(藥物數、嚴重交互作用數),不收原始文字
**PostHog 事件**

- prescription_analysis_started
- prescription_analysis_completed
- prescription_drug_info_expanded
- prescription_interaction_expanded
**驗收標準**

- 4 種不同藥物,AI 正確解析 ≥ 3 種(≥75% 準確)
- 已知嚴重交互作用(Warfarin + Amoxicillin)正確標紅
- 每個藥至少 3 個引用來源
- 整個分析 20 秒內完成
- Mobile 矩陣可橫向捲動
- 伺服器端沒有儲存處方原文
**Pro-gating**

- Free:每天 2 次處方分析
- Pro:不限次數
- 這是 Free → Pro 主要轉換驅動
**PMF 驗證指標**

| **指標** | **目標** | **判讀** |
| --- | --- | --- |
| pharmacist 試用過處方分析比例 | > 60% | 低於此代表入口太隱蔽 |
| 試用後 7 天內再次使用比例 | > 40% | 低於此代表實用度不夠 |
| pharmacist Free → Pro 轉換率 | ≥ 其他角色 2 倍 | 達成即 PMF 訊號 |
| 處方分析後 thumbs_up 率 | > 70% | 低於此代表輸出品質需提升 |

**4.5 Share Answer 公開連結(v1.3 新增)** 🟡 IMPLEMENTATION COMPLETE — DEPLOY PENDING (2026-05-08)

**(2026-05-08 status)** PHASE A-D shipped (commits ef0d375 / f04068d / e042efc / 30bd0b5 / a5da1c5 / ca571ce / b378659 / 768dc0b / 4fe0d7b / 92dbe9b / 6f7a154 / ad506db plus UX polish run). PHASE E (acceptance criteria validation via LinkedIn Post Inspector / Twitter Card Validator / Google Rich Results Test, real anon 403 verification, OG image production render check, PostHog 6-event verification) deferred — blocked on production deploy. See **Production Deploy Checklist (PHASE E.2)** below.

讓使用者把自己得到的查詢結果產生一組公開可訪問 URL,分享給同行或社群。對齊 GTM_V1 § 5.4 L3 word-of-mouth 機制,把「使用者得到答案」這個原本封閉於登入後的事件轉成可被 forward 的公開資產。

**v1.3 新增背景:**Vela 目前無任何「把答案帶離 Vela」的機制。L3 word-of-mouth 假設「種子使用者在 LINE / FB / m3.com 推薦」,但產品端缺乏 low-friction 推薦工具。藥師目前只能用文字打答案、截圖、或貼 PubMed 連結,三者均高摩擦,word-of-mouth 不會自然發生。本功能與 4.6 共用基礎設施(Public Query Page renderer),屬於同一 ChangeSet。

**功能需求**

**需求 1:Share Answer 觸發**

- 答案產生後,在 answer block 下方加「Share」按鈕(圖示 + 文字,i18n key)
- **(2026-05-05 修訂)** Share button 對未登入使用者 (anonymous L0) disabled,顯示 tooltip + AnonymousUpgradeCTA 風格的 sign-up prompt;只有 L1/L2 已登入使用者才能建立分享。**理由:**(1) ADR 001 anonymous tier 規範 Research 2/day + Verify 2/day,單日上限 4 個答案,本需求 §4.5 需求 6「anon 10/day share 配額」永遠不會 bind,實作意義為 0;(2) Share 是 GTM § 5.4 L3 word-of-mouth 機制,假設「signed-in 種子使用者推薦」,anon 在沒建立任何使用者關係即發布 PHI 風險內容反而失去 abuse 追溯能力;(3) defense-in-depth — 即便前端 sign-in gate 被 bypass,後端 `require_auth` 會擋下 anon 對 `/api/share/create` 的呼叫。
- **(2026-05-06 修訂)** Share button 從原 spec「answer block 下方」relocated 至 Navbar,透過 `contexts/ShareContext.tsx` provider + `useShareContext()` hook 跨頁協調。Visibility gate:當前頁面為 `/research` / `/verify` / `/explain` **且** streaming 已完成 (`shareData != null`) 才渲染。其他 routes(`/dashboard`, `/pricing`, `/settings`, `/history` 等)Navbar 完全不顯示按鈕。`pages/history.tsx` 維持原 spec inline ShareButton(per-row,因 history 一頁多答案,Navbar 共享 slot 在語意上不適用)。Anonymous L0 在 navbar variant 與 inline variant 行為一致(disabled 樣式 + redirect `/sign-up`)。
- 點擊後彈出 Share Modal,需明確同意才生成 share link(隱私 gate)
- Modal 內容:
  - 標題:「公開分享這個答案」(i18n)
  - 警語:「分享後,任何人不需登入即可看到你的問題與答案。請確認問題不含病患個資或可識別資訊。」
  - 預覽:顯示即將被分享的 query 全文(讓使用者有最後一次檢查機會)
  - 確認鈕:「產生公開連結」/ 取消鈕
- 使用者按「產生公開連結」後,系統:
  - 生成 share_id(短碼,9-12 字元,URL-safe)
  - 寫入 SharedQuery 資料表(schema 見需求 4)
  - 顯示產生後的 modal:複製連結按鈕、QR code、社群分享 icons(LinkedIn / X / Facebook / LINE / WhatsApp,locale 自動排序)
- 使用者已分享過的 query,再按 Share 不重新生成,重用既有 share_id
- **(2026-05-06 修訂)** QR code 已從 done-state modal 移除,`qrcode.react` 依賴一併拔除。理由:Vela TA(藥師)主要 desktop 使用,QR code 在桌面情境下價值低於視覺成本。`Copy link` + 5 個社群 icon (LinkedIn / X / Facebook / WhatsApp / LINE) 已涵蓋實用分享路徑。Toast「Link copied」配色從綠色改為品牌一致的中性白色表面。

**需求 2:URL 結構與公開頁面**

- URL 格式:`vela.an-tho.com/q/{share_id}`(短、易輸入、SEO-neutral)
- 任何人(含未登入、含搜尋引擎爬蟲)直接訪問不被擋
- 頁面結構:
  - Header:Vela logo + 主視覺,點擊回首頁
  - Body:原始 query 全文 + 答案 + 完整 citation list
  - 答案下方 CTA banner:「想問你自己的版本?」按鈕導向 `/?from_share={share_id}`(帶 UTM 等同 anonymous trial flow)
  - Footer:免責聲明 + Privacy 連結 + ToS 連結
- 不顯示原始使用者資訊(連 anonymous_id 都不顯示,完全與發起者解耦)
- 不顯示 user_context(role / workplace / locale 等偏好絕不洩漏)
- **(2026-05-06 修訂)** 公開頁面視覺對齊主站完整設計系統 (commit a5da1c5)。原 spec 僅描述功能性結構;shipped 版本含:dark gradient body (matches PageShell)、evidence-strength card splits (🟢🟡🔴 markers,server-side parsed via Python `parse_research_sections()` ported from `pages/research.tsx`)、hand-rolled CitationPanel HTML (source-type 顏色、credibility pill、5 顆星、abstract 200 字硬截斷)、coral gradient CTA button (與 landing page hero 同 styling)、inline ⚠️ 短免責 + footer 長免責雙層。GTM L3 word-of-mouth 第一印象品質 → 訪客 click-through 較原 minimal 設計顯著提升。

**需求 3:SEO 與社群 preview**

- **(2026-05-05 修訂)** SSR 渲染採 **FastAPI Python Jinja2 server-side rendering**,**不**用 Next.js SSR(現有 `next.config.ts` 已 `output: 'export'`,build pipeline 完全靜態,無 Node runtime 在 production;改用 SSR 需 Dockerfile + next.config 重構,風險高於 §4.5 scope)。Public Query Page 路由註冊於 `api/server.py` 的 `serve_nextjs_pages` catch-all 之前,先 match `/q/{share_id}`。
- **(2026-05-06 修訂)** `pages/research.tsx::parseResearchSections()` 已 port 至 `api/services/share_renderer.py::parse_research_sections()` (Python regex 同邏輯),public page 在 server-side 切 sections 後送進 Jinja2 render,避免客戶端 splitting 影響 SEO crawler 對 sectioned content 的索引。
- 動態 OG meta tags:
  - `og:title`:取 query 前 80 字 + 「· Vela」
  - `og:description`:取答案首段前 160 字
  - **(2026-05-05 修訂)** `og:image`:Pillow Python backend,於 share 建立時同步生成 PNG,儲存至 `static/og/{share_id}.png`,由 FastAPI 既有 static mount 服務。**不**用 `@vercel/og`(Vercel-hosted edge function,與 Fly.io 自託架構不相容)。
  - `og:url`:canonical URL
  - `og:type`:article
- Twitter Card:`summary_large_image`
- JSON-LD schema:`QAPage`(Google rich result)
- **(2026-05-05 修訂)** `/q/*` **不**進 `sitemap.xml`(內容由使用者產生,品質不可控,進 sitemap 會降低整站 SEO 信任度);改採每頁 `<meta name="robots" content="noindex, follow">` — 仍允許 link juice 流向 `/`,但不被 indexing。**§4.6 SEO Explore Pages 才會進 sitemap**(團隊 curated 內容,品質可控)。

**需求 4:資料模型(SharedQuery 表)**

新增 Postgres 表:

```
table: SharedQuery
  share_id        text PK             -- short URL-safe code, 9-12 chars
  query_text      text NOT NULL       -- 原始 query 全文
  answer_text     text NOT NULL       -- 答案 markdown
  citations       jsonb NOT NULL      -- citation 陣列(同 PRD 既有 schema)
  created_by      text                -- anonymous_id 或 user_id hash(僅供反 abuse 統計,公開頁面不顯示)
  created_at      timestamptz NOT NULL DEFAULT now()
  is_public       bool NOT NULL DEFAULT true  -- 預設公開,使用者可日後撤回
  view_count      int NOT NULL DEFAULT 0      -- 累計訪問次數(僅統計,不顯示在頁面)
  last_viewed_at  timestamptz
  flagged         bool NOT NULL DEFAULT false -- 內容違規 flag,true 時頁面顯示「此分享已下架」
```

索引:`share_id`(PK)、`created_by`(per-user rate limit)、`flagged`(後台審核 query)。

**需求 5:隱私 gate 與內容篩選**

- 使用者在 Share Modal **必須勾選**「我已確認此問題不含病患個資或可識別資訊」才能產生連結
- 若 query 文字符合「敏感模式偵測」(預先定義 regex / keyword:身分證字號、健保號、姓名+年齡組合等),Share 按鈕 disabled,顯示提示:「此問題可能含個資,無法公開分享」
  - 偵測規則寫成 i18n / locale-aware 模組(初版只覆蓋繁中、英文、日文,其餘 locale fallback 為「不偵測,但顯示更強烈警告」)
  - **(2026-05-05 修訂)** 實作:擴充既有 `api/middleware/phi_handler.py` 的 `PHIDetector.detect(text, mode='guard'|'share')`。預設 `mode='guard'` 保留所有現有 caller 行為(Research / Verify / Explain / feedback / bug-report PHI gate);新模式 `mode='share'` 在現有 10 個 PHI 模式之上加 NHI(健保號)+ 姓名+年齡 combo patterns,locale-aware 套用範圍同上。**不**新建獨立 module,避免 PHI 偵測邏輯散落兩處。
- Share 後使用者可在 Settings 新增頁籤「我的分享」(列表 + 撤回按鈕),撤回後 `is_public = false`,公開頁顯示「此分享已被撤回」
- Settings 頁籤 v1.3 範圍只做「列表 + 撤回」,「我的分享」分析(view_count 等)推遲至後續版本
- **(2026-05-08 修訂)** Navbar gear-dropdown menu item label 從原 spec 隱含的「設定」改為「管理分享」(en: "Manage shares")。理由:dropdown 內既有 「管理訂閱」「取消訂閱」 等 menu items 皆為動詞+受詞精準描述「點下去做什麼」,「設定」此抽象詞不符合該命名慣例,使用者需多一步認知才能定位。Settings page H1 與路由名稱維持「設定 / Settings」(預期未來 §4.3 Phase 1A user_context tab 將加入,屆時 menu item 拆為 「管理分享」+「個人偏好」 兩條)。

**需求 6:防 abuse**

- Per-user rate limit:已登入使用者每日最多生成 50 個 share_id;匿名使用者每日 10 個(by anonymous_id + IP)
  - **(2026-05-05 修訂)** 與 §4.5 修訂 1 保持一致:anonymous user 不能建立分享,故「每日 10 個 anonymous」實際上是 0 個。本條保留 anon 限制邏輯為 defense-in-depth(若 sign-in gate bypass)。
  - **(2026-05-05 修訂)** 實作:Postgres COUNT 在 handler 內檢查(`SELECT COUNT(*) FROM shared_query WHERE created_by=? AND created_at > NOW()-INTERVAL '1 day'`),**不**透過 rate limit middleware。理由:現有 middleware 只支援 IP-keyed bucket,per-user_id keying 需重構;且 rate limit middleware 是 in-memory,Fly.io 多機部署狀態不共享,daily quota 不能用 in-memory 算。
- Per-IP page view rate limit:同一 IP 每分鐘最多訪問 60 個 share page,超過回 429
  - **(2026-05-05 修訂)** 實作:加入既有 `RATE_LIMITS` dict (`api/server.py:226`),per-IP keyed,middleware 自然處理。但要注意 path matching:現有 middleware 是 exact path match (`if path not in RATE_LIMITS`),`/q/{share_id}` 是動態路徑,需在 middleware 加 prefix-match 邏輯,或在 route handler 內手動檢查。
- ~~若 query 含被偵測為攻擊性內容(LLM Guard 已有的 unsafe content classifier,重用),Share 按鈕 disabled~~ **(2026-05-05 修訂 — 移除)** 此條取消。Recon 確認 codebase 中**不存在** "unsafe content classifier" — 既有 LLM Guard layers 為 (1) injection regex (2) base64 decode (3) indirect injection LLM scan (4) medical intent classifier (5) PHI detector,皆非通用「攻擊性內容」分類器。本 §4.5 不為此功能新建 classifier(成本與收益不對稱);PHI 偵測 + consent gate + admin manual flagged 機制視為足夠。若日後需要,另開 ADR 處理。
- 後台 admin 可手動 `flagged = true`,公開頁顯示「此分享因違反使用條款已下架」

**需求 7:PostHog 事件**

- `share_modal_opened`: { query_id, source: 'answer_block' | 'history' }
- `share_link_generated`: { query_id, share_id, locale }
- `share_link_copied`: { share_id, method: 'copy_button' | 'qr' | 'social_{platform}' }
- `share_link_visited`: { share_id, referrer_domain, is_first_view: bool }
  - **(2026-05-05 修訂)** 從 frontend 發送(non-bot view only),非 backend。理由:Vela backend 目前無 PostHog client(見 TECH_DEBT.md),為了一個 event 接整套 server-side 分析架構成本不對稱。Side effect:LinkedIn / X / Facebook bot 抓 OG 卡片不會計入 view 事件 — 此為設計意圖(bot view 不該污染 PMF 訊號),`view_count` 欄位仍由 backend 在 `GET /q/{share_id}` 中以 `_safe_db_write` 累加(包含 bot),兩個指標分別表達「真人 reach」與「總 traffic」。
  - **Implementation note**: frontend 在 `/q/{share_id}` 公開頁載入時 fire(透過內嵌的 small JS snippet — 公開頁是 server-side rendered Jinja2,故需在 template 加入 PostHog snippet + analytics.ts 的最小子集,或改用 fetch beacon 直接打 PostHog ingest endpoint)。`is_first_view` 的判定改為 frontend 端 localStorage flag(`vela_visited_shares` set),取代原 backend `last_viewed_at IS NULL` 邏輯。
- `share_to_query_clicked`: { share_id, time_on_page_sec }(訪問者按 CTA 進首頁)
- `share_revoked`: { share_id, days_since_created }

**需求 8:i18n**

- 16 語言全覆蓋
- 新增 i18n keys:
  - `share.button`:「分享」
  - `share.modal.title`:「公開分享這個答案」
  - `share.modal.warning`:警語全文
  - `share.modal.confirm`:「產生公開連結」
  - `share.modal.cancel`:「取消」
  - `share.modal.consent_checkbox`:「我已確認此問題不含病患個資或可識別資訊」
  - `share.modal.sensitive_blocked`:「此問題可能含個資,無法公開分享」
  - `share.public.cta_title`:「想問你自己的版本?」
  - `share.public.cta_button`:「在 Vela 試試」
  - `share.public.disclaimer`:免責聲明
  - `share.public.revoked`:「此分享已被撤回」
  - `share.public.flagged`:「此分享因違反使用條款已下架」
  - `share.settings.tab_title`:「我的分享」
  - `share.settings.revoke_button`:「撤回」

**需求 9:法律與 ToS 對應**

- ToS 新增條款:「分享公開連結即代表使用者授權 Vela 在公開頁面顯示該 query 與答案。Vela 保留下架不當內容權利。」
- Privacy Policy 新增段落:「公開分享的 query 不視為個人資訊,但仍受『不含個資』規範約束。Vela 不主動審核所有公開內容。」
- 此兩處文字需法律 review,review 完成才能上線。建議 review 與工程平行,不阻塞工程進度。

**Production Deploy Checklist (PHASE E.2)**

Execute IMMEDIATELY AFTER Phase 0 末段 production deploy. Tasks:

**Pre-deploy secret setup**

- [ ] Generate `SHARE_CREATED_BY_SALT` via `python -c "import secrets; print(secrets.token_urlsafe(32))"` — store value securely
- [ ] `fly secrets set SHARE_CREATED_BY_SALT=<value>` on production app
- [ ] Verify `SENTRY_DSN` production set (existing requirement, paranoid double-check pre-deploy)

**Post-deploy verification**

- [ ] `curl -X POST https://vela.an-tho.com/api/share/create -H "Content-Type: application/json" -d '{...}'` WITHOUT Clerk JWT — expect HTTP 403 (real anon gating active per ADR scope, NOT just localhost dev rewrites)
- [ ] Sign in to production, create one real share via /research → /verify → /explain (one each, 3 total). Note the 3 share URLs.
- [ ] Visit each share URL in incognito window — verify Public Query Page renders correctly with: dark gradient body, evidence cards (research only), citation panel, coral CTA, footer disclaimer in correct locale, OG meta tags in HTML source.
- [ ] LinkedIn Post Inspector (https://linkedin.com/post-inspector/) — paste a production share URL, verify: title (query text), description, image (OG), no warnings.
- [ ] Twitter Card Validator (https://cards-dev.twitter.com/validator) — paste production share URL, verify `summary_large_image` renders with title + description + image.
- [ ] Google Rich Results Test (https://search.google.com/test/rich-results) — paste production share URL, verify QAPage schema detected and validates without errors.
- [ ] Verify OG image PNG actually loads from production (`curl https://vela.an-tho.com/static/og/<share_id>.png` returns 200 + 1200×630 image).
- [ ] Revoke one of the 3 test shares via Settings → Manage shares. Verify revoked URL displays 「已撤回」 / "share has been revoked" page.
- [ ] PostHog dashboard — verify 6 share events firing in production: `share_modal_opened` / `share_link_generated` / `share_link_copied` / `share_link_visited` / `share_to_query_clicked` / `share_revoked`.

**Closeout**

- [ ] Update PRD §4.5 status: 🟡 → ✅ SHIPPED `<deploy_date>`
- [ ] Update STATE.md: §4.5 PHASE E moves from "Deferred" → Recently Shipped
- [ ] Update ARCHIVE.md: append PHASE E entry
- [ ] Append `docs/decisions/` ADR if any of the validator runs surface unexpected gaps requiring design changes (not expected — but possible)

**Failure modes**

- 403 fail (e.g. anon CAN create share) → CRITICAL, block §4.5 launch, hotfix Clerk gate before exposing publicly
- LinkedIn / Twitter / Google validator warnings → assess severity, possible follow-up commit
- OG image fails to load → likely Pillow / font pipeline regression in prod, urgent fix
- PostHog events missing → likely env var or analytics.ts wiring issue, fixable post-launch

**Why deferred**: Phase 0 末段 deploys §4.5 + §4.6 + §2.1 + §3.1 together in a single production push (avoids multiple Phase 0 deploy cycles). User may revise to standalone §4.5 deploy if GTM L3 word-of-mouth validation desired sooner — in that case, run this checklist immediately post-deploy regardless of whether other Phase 0 work has shipped.

**驗收標準**

- 答案下方有「分享」按鈕(16 語言)
- 點擊 Share 出現 Modal,需勾選同意才能產生 link
- 含敏感資訊的 query 觸發 Share disabled + 提示
- 產生的 URL `vela.an-tho.com/q/{share_id}` 任何人不需登入可訪問
- 公開頁面 SSR 渲染,view source 可見完整 OG meta tags
- LinkedIn Post Inspector 跑公開頁 URL,顯示正確 title / description / image
- Twitter Card Validator 通過 `summary_large_image`
- Google Rich Results Test 通過 QAPage schema
- 撤回後公開頁顯示「已撤回」(per 2026-05-05 修訂需求 3,`/q/*` 不在 sitemap.xml,故無「sitemap 自動移除」步驟,僅後端 `is_public=False` + 公開頁渲染撤回畫面即可)
- Per-user rate limit 觸發 429
- 6 個 PostHog 事件全部正確發送
- Settings 「我的分享」頁籤可列表 + 撤回

---

**4.6 SEO Explore Pages(v1.3 新增)** 🟡 PHASE A SHIPPED (2026-05-11) — PHASE B-E PENDING

> **(2026-05-11 PHASE A 修訂)** PHASE A 已 ship — ExplorePage schema (`migrations/005_add_explore_page.sql`) + /explore/{slug} routing + Jinja2 templates 重用 §4.5 PHASE A 的 share_renderer 助手 (parse_research_sections / _augment_citations / _markdown_to_html)。Slug pattern (lowercase + hyphens + ASCII alphanumeric, ≤ 80 chars) 在 route handler 強制驗證,違反 → 400。Draft / archived → 404 (避免揭露未公開頁面存在)。OG image 寫入 `static/og/explore/{slug}-{locale}.png` 與 §4.5 share OG 分離。PHASE B-E 仍 pending — sitemap-explore.xml、content import CLI、breadcrumb + related queries UI、3 PostHog events、Google Rich Results Test integration。

主動建立一組公開、SEO 優化的查詢頁面,佔據長尾搜尋,把 Google 流量導入 Vela。對齊 GTM_V1 § 5.4 L3「SEO 自然流量」機制,並利用 4.5 同一基礎設施。

**v1.3 新增背景:**GTM_V1 § 5.4 L3 SEO 流量原本只依賴 Landing Page + Blog 長文(每月 1-2 篇),頁面數量級不足以對抗 UpToDate / Drugs.com 等成熟競品。但醫療長尾詞(多語言、在地法規、特定族群用藥調整)是這些競品的盲區,亦是 Vela TA 的真實搜尋情境。本功能利用 4.5 已建立的 Public Query Page renderer,以極低增量工程成本擴增公開頁面數至 50-100。

**功能需求**

**需求 1:URL 結構**

- URL 格式:`vela.an-tho.com/explore/{slug}`(語意 URL,人類可讀,SEO 友善)
- slug 規範:小寫、連字號分隔、英數+中文 hyphenated 拼音、長度 ≤ 80 字元
- 範例:
  - `/explore/metformin-renal-dose-adjustment`
  - `/explore/ssri-elderly-bleeding-risk-tw`
  - `/explore/benzodiazepine-indonesia-bpom-equivalents`
  - `/explore/metformin-腎功能調整-台灣健保`(中文 slug 走 punycode)
- 支援 hreflang(對應已建立的 i18n 16 語言基礎設施),同一主題多語言版本互相 alternate

**需求 2:資料模型(ExplorePage 表)**

新增 Postgres 表(獨立於 SharedQuery,因內容生產與授權模型不同):

```
table: ExplorePage
  slug              text PK             -- URL-safe slug
  locale            text NOT NULL       -- e.g. 'zh-TW', 'en', 'ja'
  query_text        text NOT NULL       -- 預先設計的查詢文字
  answer_text       text NOT NULL       -- Vela 生成 + 編輯校對的答案
  citations         jsonb NOT NULL      -- citation 陣列
  meta_title        text NOT NULL       -- SEO title(可手動覆寫,預設 query_text)
  meta_description  text NOT NULL       -- SEO description(可手動覆寫)
  category          text                -- 分類,e.g. 'drug-interaction', 'dose-adjustment', 'regulation'
  hreflang_group    text                -- 同主題不同語言版本的 group key
  status            text NOT NULL       -- 'draft' | 'published' | 'archived'
  published_at      timestamptz
  last_updated_at   timestamptz NOT NULL DEFAULT now()
  view_count        int NOT NULL DEFAULT 0
```

索引:`slug + locale`(複合 PK)、`status`、`hreflang_group`、`category`。

**需求 3:內容生產工作流**

- 內容由產品 / 內容團隊預先撰寫,**不由 LLM 自動生成上線**(品質控管)
- 工作流(初版,可後續優化):
  - 內容團隊維護一份 Notion 或 Markdown repo
  - 每筆 ExplorePage 包含:locale、query、answer、citations、meta、category、hreflang_group
  - 透過後台或 CLI 工具批次匯入至 ExplorePage 表(`status: draft`)
  - 內部 review 後改 `status: published`,自動納入 sitemap
- 初版不做後台 CMS UI,直接 SQL / CLI / Notion sync(降低工程成本)
- 內容更新節奏:每週 2-3 筆,持續 6-12 個月,目標累計 50-100 筆

**需求 4:頁面渲染**

- 重用 4.5 共用基礎設施(Public Query Page renderer)
- 頁面結構與 4.5 公開頁一致,但加入:
  - 頁面頂部 breadcrumb:Vela > Explore > {category} > {query_text}
  - 頁面底部 related queries(同 hreflang_group 其他語言 + 同 category 5-8 筆)
  - 答案下方 CTA banner 改為:「想問你自己的版本?」按鈕導向 `/?from_explore={slug}`(UTM 區分)
- SSR + OG meta + JSON-LD `QAPage` 全部沿用 4.5 規格
- 不顯示「Generated by user」相關文字(因內容是團隊產出,非使用者分享)

**需求 5:Sitemap 與索引**

- 所有 `status: published` 的 ExplorePage 自動加入 `vela.an-tho.com/sitemap-explore.xml`
- 主 sitemap.xml index 引用 sitemap-explore.xml
- robots.txt 確認 `/explore/*` 未被 disallow
- 提交至 Google Search Console + Bing Webmaster Tools(維運計畫 v3 § 9.1 已寫每週 GSC 檢查,加入 explore page indexing 監控)
- hreflang 標籤對應 hreflang_group 內所有 published 兄弟頁面

**需求 6:多語言 SEO 策略**

- Phase 1B 內容生產初期,每筆主題只做主要 TA 語言版本(繁中、英文、日文),不全 16 語言
- 完整翻譯延遲到 Phase 1C 或 Phase 2,先驗證主題選對(看 GSC impressions / clicks)再翻
- hreflang 缺失語言版本的處理:hreflang group 內缺哪個就不寫 hreflang 標籤(避免指向不存在的 URL)

**需求 7:PostHog 事件**

- `explore_page_visited`: { slug, locale, referrer_domain, is_first_view }
- `explore_to_query_clicked`: { slug, time_on_page_sec, scroll_depth }(訪問者按 CTA 進首頁)
- `explore_related_clicked`: { from_slug, to_slug, link_type: 'hreflang' | 'category' }

**需求 8:內容初版主題清單(Week 5 前由內容團隊提供)**

工程上線時資料表為空。初版內容由內容團隊獨立準備,範例方向(僅參考,實際清單由內容 / SEO 分析決定):

- 藥物 + 腎功能調整類(metformin、digoxin、NSAIDs 等高搜尋量)
- 藥物 + 老年人風險類(SSRI bleeding、benzodiazepine fall risk 等)
- 在地法規 + 等同藥物類(印尼 BPOM、越南 DAV、菲律賓 FDA 對應藥)
- 跨語言診斷術語橋接類(部分對應 Phase 1C 跨語言橋接面板,可互相導流)

**驗收標準**

- ExplorePage 表建立,可透過 CLI / SQL 寫入內容
- `/explore/{slug}` 頁面 SSR 渲染,使用 4.5 同一 renderer
- sitemap-explore.xml 自動產生,僅含 published 頁面
- robots.txt 允許 /explore/*
- hreflang 標籤對應 group 內 published 兄弟頁面
- Google Rich Results Test 通過 QAPage schema
- 內容團隊可在不動工程的情況下新增 / 更新 / 下架頁面
- 3 個 PostHog 事件正確發送
- 上線後 4 週內 GSC 開始出現 impressions(視內容主題而定)

---

**4.5 + 4.6 共用設計檢核**

- 兩功能共用 Public Query Page renderer:同一 React 元件、同一 SSR pipeline、同一 OG 生成邏輯
- 兩功能共用 SSR layer:Next.js dynamic route 共用 server component
- 兩功能共用 PostHog event prefix:`share_*` vs `explore_*` 並列,避免命名衝突
- 兩功能 URL prefix 區分:`/q/*`(隨機 ID,使用者觸發)vs `/explore/*`(語意 slug,團隊產出),避免 SEO 混淆
- ~~兩功能 robots.txt / sitemap 處理:`/q/*` 加入 sitemap 但 noindex(僅供分享用,不主動推 Google 索引,避免 query duplicate);`/explore/*` 加入 sitemap 並 index(主動推索引)~~ **(2026-05-05 修訂)**:`/q/*` **不**進 sitemap(理由見 §4.5 需求 3 修訂),只放 `<meta name="robots" content="noindex, follow">`;`/explore/*` 進 sitemap 並 index 不變。

**4.5 + 4.6 對既有 PRD 章節的影響**

- 0.4 開發原則:本兩功能引入「公開資料路徑」,但仍遵守 user_context 隔離(共用頁面絕不讀 user_context)。Stateless 原則維持。
- 3.1 User Context 資料模型:不影響(SharedQuery / ExplorePage 與 user_context 解耦)
- 3.4 隱私聲明 UI:Privacy Policy 增段落,描述公開分享機制
- 4.1 FeedbackBar:公開頁面不顯示 FeedbackBar(訪客非原 query 提交者,給回饋無語意)
- 4.2 Citation ⓘ:公開頁面 citation 沿用 ⓘ 機制(訪客也應能看 source 說明)
- 4.3 Settings:新增「我的分享」頁籤
- 4.4 處方解析 MVP:處方解析答案的 share / explore 機制 v1.3 不啟用(處方涉及高度個資風險,需獨立評估後再開放)。Share 按鈕在處方解析 answer block 不顯示。
- 6.2 PostHog 事件命名:加入 `share_*` 與 `explore_*` 兩組命名空間
- 6.4 儲存策略:SharedQuery 與 ExplorePage 為新增 Postgres 表,不影響 user_context localStorage 策略

**v1.2 → v1.3 預定變更摘要**

| **變更類型** | **內容** |
| --- | --- |
| 新增 4.5 Share Answer 公開連結(Phase 1B 編號,Phase 0 末段執行,P1) | 使用者觸發的公開分享機制 |
| 新增 4.6 SEO Explore Pages(Phase 1B 編號,Phase 0 末段執行,P1) | 團隊預先建立的長尾 SEO 頁面 |
| 共用基礎設施:Public Query Page renderer | 4.5 / 4.6 共用 SSR + OG + JSON-LD pipeline |
| 調整 4.3 Settings | 新增「我的分享」頁籤 |
| 調整 3.4 隱私聲明 | Privacy Policy 增公開分享段落 |
| 調整 6.2 PostHog 命名 | 新增 share_* 與 explore_* prefix |
| 調整二章 Phase 0 順序 | § 4.5 + § 4.6 插入 § 2.7 Step 8 後、Retrospective 前 |

**五、Phase 1C — 護城河啟動**

Phase 1C 把「別人複製不了」的東西埋進產品。兩個核心功能——在地差異提示和跨語言橋接——都是 OpenEvidence 和 UpToDate 結構上做不到的差異化。

**5.1 在地差異提示 — 分層式全球化** ❌ PENDING (Phase 1B advanced per ADR 004 + advisor discussion 護城河 rebalance — Tier 1 6國 originally Phase 1C, now Phase 1B; see BACKLOG.md)

**戰略定位:**Vela 對抗 OpenEvidence 全球擴張最重要的結構性護城河。OE 因為 NPI 驗證綁定美國,無法做真正的全球在地化。Vela 的「無身份驗證」架構讓我們可以自然服務全球,透過分層式在地提示實現低成本在地化。

**核心概念:機制 vs 資料**

**機制層(對所有使用者通用):**

- LLM 識別回答是否涉及在地敏感議題
- 自動加上「地區差異提示」段落
- 提醒使用者去核對官方來源
**資料層(按國家建立):**

- 每個國家的官方權威連結 map
- 分層支援,不是全有或全無
**關鍵設計原則**

- 不承諾在地答案,只提示去核對:Vela 永遠不給具體在地答案,只提供官方連結
- 零人工標註:全部靠 LLM 判斷 + hardcoded 連結 map
- 從第一天就是全球產品:Tier 1 + Tier 2 確保每個國家使用者都有意義的提示
**Tier 1 初版 6 國(Phase 1B 預告)**

| **地區** | **藥物監管** | **健保/給付** | **備註** |
| --- | --- | --- | --- |
| 台灣 | TFDA | 健保署 (NHI) | 核心市場 |
| 日本 | PMDA | MHLW | 東亞第二大 |
| 韓國 | MFDS | HIRA | 東亞第三 |
| 新加坡 | HSA | MOH | 英語 + 中文 |
| 馬來西亞 | NPRA | MOH | 多語言社會 |
| 泰國 | Thai FDA | NHSO | 泰文使用者 |

**Tier 1 擴展 6 國(Phase 1C)**

| **地區** | **藥物監管** | **健保/給付** | **備註** |
| --- | --- | --- | --- |
| 越南 | DAV | VSS | 越南文使用者 |
| 菲律賓 | FDA Philippines | PhilHealth | 英語 + 塔加洛語 |
| 印尼 | BPOM | BPJS | 東南亞最大人口 |
| 香港 | 衛生署藥物辦公室 | 醫管局 | 中文使用者 |
| 沙烏地 | SFDA | CCHI | 阿拉伯語核心 |
| 阿聯酋 | MOHAP / DHA | DHA / HAAD | 中東樞紐 |

**Tier 2:通用 fallback**

對 Tier 1 以外的國家,使用國際通用權威:

- WHO(世界衛生組織)
- NICE(英國)
- EMA(歐盟)
- Cochrane Library
**Tier 3:使用者貢獻(Phase 2 後評估)**

- 使用者可以點「我所在地區有不同規範」貢獻資訊
- 累積後成為 community database
- Phase 1C 不做
**地區偵測邏輯**

根據多個 signals 推測,優先順序由高到低:

- user_context.locale(Settings 明確選)
- onboarding work_language 推論(zh-TW → TW、ja → JP 等)
- 瀏覽器 timezone
- IP 地理位置(粗略,僅輔助)
**系統 Prompt 設計**

在 Generator 的 system prompt 加入指令(語意摘要):生成主回答後,評估是否涉及藥物劑量、給付條件、ICD 編碼、國家監管、prescribing rules。若 YES:附加「⚠️ 地區差異提示 / Regional Differences Notice」段落。不提供具體在地答案,只指向官方來源。使用者 detected locale 和 authorities 從 config 注入。

**資料層:Authorities Database**

後端儲存 YAML config(v1.2:從 JSON 改為 YAML,詳見 5.1.1 節):每國包含 drug_regulator、insurance、medical_society 等類型,各有 name_native、name_en、url_native、url_search_pattern。DEFAULT_TIER2 用於非 Tier 1 國家的 fallback。

**UI 呈現**

- 位置:回答最下方,主要引用清單之後
- 背景微黃,左側 ⚠️ 圖示
- 標題:Tier 1「⚠️ 地區差異提示(台灣)」、Tier 2「⚠️ Regional Differences Notice」
- 連結點擊新分頁開啟,發 locale_hint_clicked 事件
- 右上角 X 可收起(localStorage 記住)
**PostHog 事件**

- locale_hint_displayed: { query_id, locale, tier, authorities_count }
- locale_hint_clicked: { query_id, locale, tier, authority_type, authority_name }
- locale_hint_dismissed: { query_id, locale }
**驗收標準**

- Tier 1 的 12 國都有完整 authorities 資料
- Tier 2 fallback 對其他地區正常顯示
- LLM 正確識別「涉及在地議題」並加上提示
- 不涉及在地議題的回答不會無謂加上
- 連結點擊新分頁、PostHog 事件正確
- 可收起,記住偏好
**維護成本**

- 初版建 12 國 authorities:1 個週末
- 每季檢查連結失效:30 分鐘
- 新國家加入:30 分鐘-1 小時
**5.1.1 在地知識 YAML 實作規範(v1.2 新增)** ❌ PENDING (Phase 1B advanced per ADR 004 + advisor discussion — Tier 1 schema + 6國 data go to Phase 1B; expansion 6國 stays Phase 1C)

**目標**

把 5.1 提到的「資料層」從 JSON/hardcoded 升級為 YAML 驅動的知識庫,讓在地權威資料的新增、更新、審核流程可工程化。這一節是 5.1 的執行細節,不改變 5.1 的戰略。

**為什麼用 YAML 而不是 JSON**

- YAML 對人類更友善,允許註解(# 開頭),在地 curator 可以在資料旁寫下「這個連結每年 4 月重組,需重驗」
- 多國並列閱讀時 YAML 的縮排結構更易快速掃過
- Pydantic 可直接 load YAML 並驗證 schema,與 FastAPI 後端 stack 相容
- Git diff 對 YAML 比對 JSON 更清晰,未來 PR-based 審核流程更順
**Tier 1 六國範圍(v1.2 對齊)**

Phase 1C 交付的 Tier 1 YAML 涵蓋:台灣 (TW)、日本 (JP)、韓國 (KR)、新加坡 (SG)、馬來西亞 (MY)、泰國 (TH)。5.1 的「Tier 1 擴展 6 國(越南、菲律賓、印尼、香港、沙烏地、阿聯酋)」順延至 Phase 1C 末或 Phase 2 初,視 L3 locale 分布訊號調整。

**為什麼歐美加(US、EU、CA)不在 Tier 1**

這是 v1.2 明確寫下的戰略紀錄,避免未來因為「歐美市場看起來大」而動搖核心 TA 對焦:

- **TA 位錯:**Vela 核心 TA 是「不在大醫院工作 × 工作語言非英語 × Allied Health」。歐美加的英語系醫療人員不屬於這個切片,為他們做在地 YAML 是服務不主打的客群,違反 GTM v7.1 第一條紀律「銳利勝過廣泛」
- **OpenEvidence 結構性占據:**OE 已在美國深耕多年,NPI 驗證綁定美國執業醫師。Vela 在美國市場跟 OE 正面比功能或內容深度,結構上打不贏
- **歐盟監管碎片化:**歐盟不是單一 YAML 就能覆蓋,EMA + 各國 FDA + 各國 health service 的組合極複雜,投入不成比例於我們目標 TA
- **加拿大與歐洲類似問題:**兩語(英法)+ 省級衛生署,維護成本高,TA 回報低
- **Tier 2 已覆蓋基本需求:**若有歐美使用者誤入 Vela,Tier 2 fallback(WHO、NICE、EMA、Cochrane)已提供合理的官方來源提示。不需要為他們建完整 Tier 1 YAML
結論:歐美加永遠停留在 Tier 2 是**策略選擇**,不是能力限制。未來就算歐美使用者暴增,也應該先評估「是否重新定義核心 TA」再考慮建 Tier 1,不是反射性補 YAML。

**YAML Schema 範例**

`# config/locale_authorities/tw.yaml`

`locale: TW`

`language: zh-TW`

`name_native: 台灣`

`name_en: Taiwan`

`tier: 1`

`last_reviewed: 2026-04-17`

`reviewer: andrew`

` `

`authorities:`

`  drug_regulator:`

`    name_native: 衛生福利部食品藥物管理署`

`    name_en: Taiwan Food and Drug Administration`

`    short_name: TFDA`

`    url_native: https://www.fda.gov.tw/`

`    url_search_pattern: https://www.fda.gov.tw/TC/siteListContent.aspx?sid=1619&q={query}`

`    notes: 藥物查詢需搭配中文學名或商品名,英文搜尋效果有限`

` `

`  insurance:`

`    name_native: 衛生福利部中央健康保險署`

`    name_en: National Health Insurance Administration`

`    short_name: NHI`

`    url_native: https://www.nhi.gov.tw/`

`    url_search_pattern: https://www.nhi.gov.tw/Content_List.aspx?n=A1AA0E4C9F8F52E4`

`    notes: 給付條件常修訂,每季需復查 URL 結構是否變動`

` `

`  medical_society:`

`    - name_native: 台灣藥學會`

`      url_native: https://www.tps.org.tw/`

`    - name_native: 台灣家庭醫學醫學會`

`      url_native: https://www.tafm.org.tw/`

Pydantic model 位置建議:api/models/locale_authorities.py。Loader 在 app 啟動時把 config/locale_authorities/ 下所有 YAML 載入記憶體,提供 get_authorities(locale) 函式。

**AI-Assisted Curation 流程**

Tier 1 六國的初版 YAML 用以下流程產出,避免 solo 手工建造的瓶頸:

- **Step 1 AI 草稿:**用 Claude 或 GPT 把目標國家的主要監管機關、健保、醫學會整理成 YAML 初版。Prompt 要求輸出官網 URL、英文官方名稱、原文名稱,附每條的信心分數
- **Step 2 來源核對:**AI 草稿不可直接採用。對每個 URL 做以下三件事:(a) curl / web_fetch 檢查 HTTP 200;(b) 人工點擊看頁面內容是否為該機關官網(防 AI 幻覺假連結);(c) 確認 search pattern 真的能回傳結果
- **Step 3 語言校對:**name_native 必須是該國原文(不是翻譯),若 curator 不通該語言,請當地藥師/醫師朋友掃一遍(30 分鐘內可做完)
- **Step 4 Commit:**每國 YAML 成為一個 git commit,PR title 格式 feat(locale): add {XX} authorities with AI-assisted curation。未來更新也以 PR 為單位,便於追蹤哪一次改動
整體 Tier 1 六國初版預估工期:AI 草稿 1 個下午、人工核對每國 30-60 分鐘、語言校對每國 30 分鐘。總計 1-1.5 個週末。

**可信度三層防護**

YAML 驅動的在地知識有 hallucination 與陳舊風險,用三層防護降低風險:

- **第一層 — Build-time schema 驗證:**app 啟動時 Pydantic 驗證每個 YAML 的欄位完整性。last_reviewed 超過 180 天的 YAML 啟動時 warning(不 block,但寫進 Sentry),提醒下一次復查
- **第二層 — Runtime 連結健康檢查:**每月一次 cron job(可用 GitHub Actions)對所有 url_native 做 HEAD request。失敗的寫入 Slack / email alert,curator 手動修正後提交新 commit。對齊維運計畫 v3 的 SEO Health Check 流程
- **第三層 — 使用者報錯閉環:**若使用者點 locale_hint 連結後導向 404,前端自動發 PostHog event locale_hint_link_broken { locale, authority_type, url }。PostHog Dashboard 有獨立面板監控此事件,出現即排查
**Tier 3 Fallback 機制**

Phase 1C 本版不做 Tier 3 使用者貢獻功能,但保留擴充點:

- Pydantic schema 預留 contributed_by 欄位
- 未來 Tier 3 UI 送出後,不直接進入 main YAML,而是進 pending/ 子目錄
- curator 審核後才 merge 到 main
- 避免 Wikipedia 式亂編(醫療資訊亂編後果比 Wikipedia 嚴重)
**驗收標準**

- config/locale_authorities/ 下有 6 個 YAML(tw.yaml、jp.yaml、kr.yaml、sg.yaml、my.yaml、th.yaml)
- Pydantic schema 完整驗證通過
- 每個 YAML 的 url_native 都能 HTTP 200 存取
- 每個 YAML 有 last_reviewed 欄位(日期)
- Tier 2 fallback(WHO/NICE/EMA/Cochrane)獨立 YAML(global_fallback.yaml)存在
- LLM 可透過 get_authorities(locale) 函式取得對應資料注入 prompt
- 一個測試 case:使用者 locale=US(非 Tier 1),回傳 Tier 2 fallback 且 locale_hint 顯示正確
**不做什麼(對齊 5.1)**

- 不做使用者投稿 Tier 3(Phase 2 後評估)
- 不為歐美加建 Tier 1 YAML(策略選擇,見上面理由)
- 不做 admin 介面管理 YAML(curator 直接改檔 + PR 已足夠)
- 不做自動翻譯 name_native(機器翻譯權威機構名是幻覺溫床,必須人工)
**5.2 跨語言術語橋接面板** ❌ PENDING (Phase 1C)

**戰略定位:**對非英語使用者的核心價值證明。表面是翻譯工具,實際做三件事:教育使用者如何更好提問、證明 Vela 真的在搜英文文獻、累積的點擊數據是獨特資產。

**MVP 範圍**

**MVP 做什麼:**

- 回答頁面加側邊面板(預設收合)
- 展開後顯示「你的問題 → 英文檢索詞」對應
- 顯示「本次回答使用的英文關鍵術語」
- 每個英文術語帶中/原文對照
**MVP 不做:**

- 「切換語言視角」互動(V2)
- 「對比英文 vs 在地」視圖(V2)
- 術語點擊看例句(V2)
**UI**

- 入口:回答頁面右側(桌面)或下方(mobile)
- 預設收合,只顯示小圖示「🌐 語言橋接」
- 僅當 work_language ≠ en 時顯示
**面板內容**

**區塊 1:問題翻譯對照**

- 左欄:使用者原始問題
- 右欄:AI 推論出的英文檢索關鍵詞(2-5 個)
- caveat:「實際搜尋可能使用更多變化形式」
**區塊 2:本次回答使用的關鍵術語**

- 從回答自動萃取 3-6 個關鍵醫學英文術語
- 英文術語為主顯示,括號內為 work_language 對應
- 中文語境下有繁簡差異時同時列出
**技術實作**

*術語萃取:方法 A(簡單,推薦)*

- Generator 生成主回答時,同時輸出 JSON 含 key_english_terms[]
- 一次呼叫完成,延遲較低,成本較低
*問題翻譯*

- 主查詢前先做一次輕量 LLM 呼叫(Haiku 或 4o-mini)
- 回傳 JSON { query_translation, search_terms[] }
- 輸出同時餵 RAG retrieval 和語言橋接面板
**PostHog 事件**

- language_bridge_expanded: { query_id, work_language }
- language_bridge_term_clicked: { query_id, term }
**驗收標準**

- 繁中使用者的面板中英對照正確
- 日文、韓文、泰文等使用者的面板正常
- 英文使用者看不到這個面板
- 查詢處理時間增加 < 10%
- 面板收合/展開狀態記住(localStorage)
**六、共通規範**

本章列所有 Phase 共用的技術與實作規範。新增功能時必須對齊這些規範,避免 tech debt 累積。

**6.1 i18n**

**原則:**

- 所有使用者可見字串必須透過 i18n key 處理,不可 hardcode
- 新增功能時必須同時加 16 語言 key,不可只加英文
- 專有名詞(Vela、PubMed、FDA)保留原文,不翻譯
**i18n key 命名規範:**

- 功能群組作 key 前綴:onboarding.*、settings.*、feedback.*、bug_report.*、prescription.*、locale_hint.*、language_bridge.*、explain.*(v1.2 新增 explain.risk.*、explain.disclaimer)
- 共用字串放 common.*:common.save、common.cancel、common.close 等
- 錯誤訊息放 errors.*:errors.network、errors.rate_limit 等
**v1.1 注意:**FEATURE_AUDIT 發現既有 Onboarding i18n key 格式為 onboardingStep、onboardingTitle 等 camelCase 平鋪格式。新增 key 用點號分層結構。現有 camelCase key 可保留不重構,避免大量 regression。

**翻譯品質要求:**

- 機器翻譯後必須人工校對
- 繁中、簡中、日文、韓文優先級最高
- 醫療術語遵循當地專業慣用詞
**6.2 PostHog 事件命名**

**命名規範:**

- snake_case,動詞過去式或完成式:query_submitted、citation_clicked、feedback_thumbs_up
- 不用 query_submit、citation_click(現在式)
- 不用 submit_query、click_citation(動詞開頭)
**共用 properties(所有事件必備):**

- query_id(見 2.2)
- session_id
- user_context_hash
- locale
- plan_type: free | pro
- work_language
**禁止事項:**

- 不在 event 中包含 PII(email、姓名、真實地址)
- 不在 event 中包含 query 原始文字(僅 metadata)
- 不在 event 中包含處方原始文字
**6.3 錯誤處理**

**後端 API 錯誤格式統一:**

所有 API 錯誤回傳統一 VelaError 結構:

- code: 錯誤代碼(snake_case 常數)
- message: 使用者可讀訊息(已 i18n)
- retryable: boolean,前端是否應該自動重試
- severity: 'info' | 'warning' | 'error' | 'critical'
**錯誤碼清單(v1.1):**

| **code** | **severity** | **說明** |
| --- | --- | --- |
| LLM_RATE_LIMITED | warning | LLM Provider rate limit,前端自動重試 |
| LLM_TIMEOUT | warning | LLM 呼叫超時,前端自動重試一次 |
| LLM_INVALID_REQUEST | error | 呼叫參數錯誤,通常 code bug |
| LLM_AUTH_FAILED | critical | API key 失效,後端立即警示 |
| LLM_PROVIDER_UNAVAILABLE | critical | 供應商服務中斷,觸發 provider 降級 |
| RATE_LIMITED_USER | info | 使用者今日 credits 用完 |
| INVALID_INPUT | error | 使用者輸入格式錯誤 |
| NOT_MEDICAL_QUERY | info | Guard 判定非醫療查詢 |
| INTERNAL_ERROR | error | 後端未預期錯誤,送 Sentry |

**前端錯誤處理原則:**

- retryable=true 自動重試一次,顯示 loading
- retryable=false 立即顯示錯誤訊息
- critical 額外送 Sentry
- 錯誤訊息用使用者語言,不顯示技術細節
**6.4 儲存策略**

**localStorage(優先):**

- user_context(偏好)
- UI 狀態(language_bridge 收合、locale_hint 收起)
- dismissed_prompts(使用者關閉過的提示)
- session_id(每瀏覽器 session 一個 UUID)
**Server Database(僅必要):**

- user_usage(credits 計算)
- user_profile(訂閱者的 context_hash 和 locale,跨裝置恢復)
- user_feedback(FeedbackBar 送來的 thumbs + reason)
- chat_history(僅 Pro 使用者明確開啟時)
**絕不儲存:**

- 處方原始文字
- 查詢原始文字(Free 使用者)
- 病人識別資訊(姓名、ID、病歷號)
**6.5 Prompt 管理**

**System prompts 儲存:**

- 所有 system prompts 在 api/prompts/ 目錄下獨立檔案
- 不 hardcode 在 generator.py、retriever.py、guards.py 等邏輯檔
- 每個 prompt 有版本號註解,修改時 bump version
- (v1.2 補充)explain_system.md 是 2.7 的主要改動目標,改動後 bump 到 v2
**Prompt 變數注入:**

- locale、authorities、work_language 等動態變數透過格式化注入
- 不可在 prompt 中嵌入使用者原始輸入(避免 prompt injection)
**實驗與 A/B 測試:**

- 新 prompt 版本先用 LLM judge 評估(api/utils/llm_judge.py)
- 通過後 10% 流量 A/B,PostHog 追蹤 thumbs_up 率
- 勝出版本才 rollout 到 100%
**6.6 Phase 0 Model Provider 命名對齊**

為避免 refactor 後命名混亂,所有 Model Provider 相關程式遵循:

- Provider interface:api/providers/base.py,class Provider(ABC)
- 實作類別:api/providers/openai_provider.py、anthropic_provider.py
- Factory:api/providers/factory.py,export get_generator()、get_guard()、get_reranker() 等
- 錯誤類別:api/providers/errors.py,export VelaError 與各 LLM_* 錯誤碼
**七、Out of Scope(此版本不做)**

以下功能明確不在 v1.2 範圍(Phase 0-1C)內。記錄於此避免範圍蔓延 + 作為 Phase 2 規劃參考。

**7.1 產品功能層**

| **功能** | **為何不做** | **可能的 Phase** |
| --- | --- | --- |
| 處方 OCR | MVP 文字輸入已夠驗證 PMF;OCR 準確度和隱私問題複雜 | Phase 2 V2 |
| 處方腎肝功能調整 | 需要輸入病人 eGFR 等生理參數,接觸病人資料邊界 | Phase 2 V2 |
| 健保給付條件檢查 | 需維護各國健保 rule base,維護成本極高 | Phase 3 |
| 病人衛教單生成 | 拓展到「產品用於病人」衝擊專業定位 | Phase 2 評估 |
| 實體掃碼 / 條碼識別 | 硬體整合成本高,ROI 不明 | 未來不規劃 |
| 本地模型支援(Llama) | Solo founder 無力維護本地 inference 架構 | Phase 4+ |
| 影像識別(皮膚、影像) | 監管風險極高,profile 不符合 Vela 定位 | 未來不規劃 |
| ICD-10 / CPT 編碼輔助 | 過於 US-centric,與全球定位衝突 | Phase 3 評估 |
| 電子病歷整合 | 需要各國 HIS 對接,solo 不可能 | 未來不規劃 |
| Explain 病歷 PDF OCR | Phase 0 2.7 以文字輸入為主,OCR 先不做 | Phase 2 評估 |
| Tier 3 使用者貢獻在地知識 | 醫療資訊亂編風險高,需 curation 機制成熟後才啟動 | Phase 2 後評估 |
| 歐美加 Tier 1 在地 YAML | 對齊 5.1.1,TA 錯位 + OpenEvidence 結構性占據,策略不做 | 不規劃 |

**7.2 商業功能層**

| **功能** | **為何不做** | **可能的 Phase** |
| --- | --- | --- |
| Team / Enterprise 方案 | 聚焦個人 Pro,Team 需加多座位管理、billing | MRR ≥ $5K 後評估 |
| 白牌 / API 授權 | TAM 小,分心成本高 | Phase 3+ |
| Affiliate / 推薦計畫 | Solo 難維護,早期不是成長瓶頸 | Phase 2 後 |
| 多付款方式(Apple Pay、LINE Pay) | Dodo 已涵蓋主要信用卡 | MRR ≥ $3K 後評估 |
| 地區化定價 | GTM v7.1 明確全球統一,不做 | 不規劃 |
| 實體活動 / conference | ROI 難估計,Solo 時間極度稀缺 | 融資後評估 |

**7.3 技術建設層**

| **功能** | **為何不做** | **可能的 Phase** |
| --- | --- | --- |
| Mobile App(iOS/Android) | PWA 已涵蓋 90% 需求;App Store 審核成本高 | MAU 5K+ 後評估 |
| 離線模式 | 醫療 AI 需即時檢索,離線無意義 | 不規劃 |
| 桌面 App(Electron) | Web 已足夠,多一個平台 = 多一份維護 | 不規劃 |
| WebSocket 即時協作 | 個人工具,協作不是核心 | Phase 4+ |
| 進階分析 dashboard(for users) | 使用者要的是答案,不是分析 | 不規劃 |
| Open Source 部分程式碼 | 保護護城河,除非策略需要 | Phase 3 評估 |

**7.4 內容層**

| **功能** | **為何不做** | **可能的 Phase** |
| --- | --- | --- |
| 自產 CME 學習內容 | 與產品定位(工具而非教育平台)衝突 | 不規劃 |
| 付費醫學資料庫整合(UpToDate) | 授權成本過高,且競爭關係 | 不規劃 |
| 使用者社群 / 討論區 | 管理成本高,易衍生醫療誤解 | 不規劃 |
| AI 生成病例分享 | 隱私與倫理風險極高 | 不規劃 |

**八、成功指標**

以下為 v1.2 的 Phase 驗收指標。未達標不代表立即調整,但需在 Checkpoint 討論是否策略需修正。

**8.1 Phase 0 驗收標準(v1.2 校準)**

**SEO 修復(2.5 + 2.6):**

- npm run build 後 out/index.html > 10KB(原 2.9KB)
- title、og:title、canonical 在初始 HTML 裡
- LinkedIn Post Inspector 顯示正確 preview
- 至少 5 個 hreflang 在 Landing Page 的 <Head>
- sitemap.xml 包含 /pricing、/faq
- /research 等 auth-gated 頁面有 noindex
**PostHog 基礎建設(2.0):**

- utils/analytics.ts 完成,exports track()、identify()、reset()
- PostHog Dashboard 可以看到 event 帶 6 個共通欄位
- Repo 全域 grep posthog.capture 只找到 utils/analytics.ts 內部
**Explain 臨床推理強化(2.7,v1.2 新增):**

- Explain 輸出每個項目有 risk_tier 欄位(green/yellow/red)
- 至少產生一條 clinical_correlations 的測試 case 通過
- Hedging 檢查:20 個真實 case 無斷言式「您有 X 病」
- 所有涉及臨床判斷的引用不只含 LOINC
- LLM judge 針對 Explain 的專用評估 prompt 可用
**Model Provider(2.1):**

- 8 個 backend 檔案都透過 Provider interface,不直接 import openai
- 環境變數切換 openai ↔ anthropic,RAG/Verify/Explain/Guard 都正常運作
- Regression 測試 7 項全通過
**追蹤系統(2.2、2.3):**

- 使用者查詢 → 點擊 citation → 按讚 三個事件可用 query_id join
- PostHog 可 breakdown citation clicks by source_type
**Bug 回報(2.4):**

- 浮動按鈕所有頁面顯示,Onboarding 期間隱藏
- 送出後 support@an-tho.com 收到郵件
**8.2 Phase 1A 驗收標準**

- Onboarding 三步完成率(未略過所有步驟)> 60%
- 首頁範例點擊率(Landing → 首次查詢)> 30%
- Privacy Policy 16 語言完整
- Settings user_context 可修改,localStorage 正確儲存
- 選擇「醫學中心」的使用者看到誠實提示後仍完成 onboarding 比例 > 40%(測試定位訊號效果)
**8.3 Phase 1B 驗收標準(PMF 試金石)**

| **指標** | **目標** | **實際** | **判讀** |
| --- | --- | --- | --- |
| pharmacist 試用處方分析比例 | > 60% | 填入 | 低於此代表入口太隱蔽 |
| 試用後 7 天內再次使用比例 | > 40% | 填入 | 低於此代表實用度不夠 |
| pharmacist Free → Pro 轉換率 | ≥ 其他 2x | 填入 | 達成即 PMF 訊號 ✅ |
| 處方分析 thumbs_up 率 | > 70% | 填入 | 低於此代表輸出品質需提升 |
| FeedbackBar 原因 chip 選擇率 | > 50% | 填入 | 👎 者中選擇具體原因的比例 |

pharmacist Free → Pro 轉換率 ≥ 其他角色 2 倍是 PMF 達成的主要訊號。若此指標未達標,Phase 1C 前必須重新檢視:處方解析 MVP 方向是否正確,或藥師不是真正的核心 TA。

**8.4 Phase 1C 驗收標準**

- locale_hint 觸發率(適用議題的查詢中)> 80%
- locale_hint_clicked / locale_hint_displayed > 15%(非 mainland 使用者)
- language_bridge_expanded / query_submitted > 20%(非英文使用者)
- feedback_reason=not_applicable_region 比例下降 > 50%(對照 Phase 1B baseline)
- locale 分布:非台灣使用者比例 > 10%(L3 被動擴散訊號)
- (v1.2 新增)YAML schema 驗證通過、6 國 YAML 完整、url_native 全部 HTTP 200
**8.5 整體商業指標(MRR 基準)**

| **Phase** | **時程** | **MRR 目標** | **判讀** |
| --- | --- | --- | --- |
| Phase 0 end | Week 3 | $0-50 | 建設期,MRR 不是重點 |
| Phase 1A end | Week 4.5 | $50-200 | Onboarding 改版後轉換改善訊號 |
| Phase 1B end | Week 8 | $200-1,000 | 處方解析驅動 pharmacist 付費 |
| Phase 1C end | Week 12 | $1,000-3,000 | 護城河功能啟動 + L3 擴散 |
| Phase 2 啟動條件 | Week 13+ | MRR ≥ $3K | pre-seed 融資準備訊號 |

**九、時程總覽(v1.2 校準)**

| **週次** | **Phase** | **主要任務** | **驗收點** |
| --- | --- | --- | --- |
| W0-0.5 | Phase 0 P0 | SEO 修復(2.5)+ hreflang(2.6) | Landing Page SEO 通過驗證 |
| W0.5-1 | Phase 0 P1 | PostHog wrapper(2.0)+ query_id(2.2)+ Citation 追蹤(2.3)+ Bug 回報(2.4)+ user_context schema(3.1 前移) | 追蹤體系可用 + 基礎表建好 |
| W1-1.5 | Phase 0 P1(v1.2 新增) | Explain 臨床推理強化(2.7)— prompt、risk tier、hedging、LLM judge | Explain 輸出滿足 2.7 驗收 |
| W1.5-3 | Phase 0 P1 | Model Provider 全面 refactor(2.1)8 檔案 + Regression 測試 | Provider 可切換,無 regression |
| W3-4.5 | Phase 1A | Onboarding 三問(3.2)+ 首頁動態範例(3.3)+ Privacy 四接觸點(3.4)+ Privacy Policy 16 語言 | Phase 1A 驗收標準達成 |
| W5-6 | Phase 1B | FeedbackBar 原因 chip(4.1)+ Citation ⓘ(4.2)+ Settings user_context(4.3) | 反饋體系完整 |
| W6-8 | Phase 1B | 處方解析 MVP(4.4) | PMF 試金石驗證 |
| W9-11 | Phase 1C | 在地差異提示 Tier 1 6 國(YAML 實作,5.1 + 5.1.1)+ Tier 2 fallback | YAML 驗證通過 |
| W11-12 | Phase 1C | 跨語言橋接面板 MVP(5.2) | Phase 1C 驗收達成 |
| W13+ | Phase 2 | 根據 L3 擴散訊號決定 L2 擴展 / pre-seed 融資準備 | MRR ≥ $3K 觸發融資 |

**Phase 0 工時重要注記:**

- v1.2 從 v1.1 的 2-2.5 週延長為 2.5-3 週(13-15 工作天)
- 原因:v1.2 新增 2.7 Explain 臨床推理強化(1-2 天),排在 2.1 Model Provider 之前
- **post-v1.2 再調整(2026-04-20):**Phase 0 工時從 2.5-3 週調整為 3-3.7 週(加 2.8 + 2.9 兩個 post-v1.2 discovered gaps 合計 2.5-3 天)
- Provider 抽象層 refactor 本身就是 5-7 天工作量,是 Phase 0 最大項目
- 若發現時程緊,可將 Bug 回報(2.4)推到 Phase 1A 初期(獨立性高),2.7 不可推遲(Model Provider 依賴其 prompt 定型)
**附錄 A:PRD 使用說明**

**A.1 如何使用這份 PRD**

**給 Claude Code 的工作流程:**

- 每個任務取該章節完整描述作為 context
- 包含需求、驗收標準、不做什麼三個區塊
- 完成後用驗收標準逐項勾選
**單一任務 prompt 範例:**

「請實作 Master PRD v1.2 第 2.7 節 Explain 臨床推理強化。工期目標 1-2 天,主要改動 api/services/explain_service.py 與 api/prompts/explain_system.md。完成後用 2.7 驗收標準逐項確認,並在 api/utils/llm_judge.py 加入 Explain 專用評估 prompt。」

**A.2 章節對照 FEATURE_AUDIT.md** (歷史快照,2026-04 撰寫時的 audit 對照表)

> **2026-05-05 update**: FEATURE_AUDIT.md 已 deprecated(commit 後續移除)。本表保留為 PRD 撰寫時的 audit 對照歷史紀錄,不再代表現況。當前狀態請查 codebase grep + STATE.md / ARCHIVE.md 中的 PRD § status markers。

| **PRD 章節** | **FEATURE_AUDIT 對照** | **關係** |
| --- | --- | --- |
| 2.0 PostHog | 第 4 項 | PostHog event 體系空的,需建 |
| 2.1 Model Provider | 第 5 項 | OpenAI hardcode 散在 8 檔案 |
| 2.2 query_id | backend api/server.py:449 | backend 已有 audit_id,沿用即可 |
| 2.3 Citation | 第 3 項 | source_type enum 需前後端對齊 |
| 2.4 Bug 回報 | 第 8 項 | 僅 mailto,需浮動按鈕 |
| 2.5 Landing SEO | 新發現 | isLoaded gate 導致 SSG 出 spinner shell |
| 2.6 hreflang | 新發現 | repo 無 hreflang,16 語言 SEO 為零 |
| 2.7 Explain 強化(v1.2) | 第 6 項 | explain_service.py 只翻譯數值,無組合推理 |
| 3.1 user_context schema | 第 1 項 | user_usage 無 specialty/role/workplace 欄位 |
| 3.2 Onboarding 三問 | 第 2 項 | 既有 OnboardingOverlay 僅 4 步導覽 |
| 3.4 Privacy Policy i18n | 第 10 項 | 僅英文 |
| 4.1 FeedbackBar reason | 第 11 項 | UserFeedback 表有 feedback_text 永遠 null |
| 4.4 處方解析 | 第 12 項 | Verify 已有交互作用但無處方解析 |
| 5.1 在地差異提示 | 第 13 項 | 完全未實作 |
| 5.1.1 YAML 實作(v1.2) | 第 13 項延伸 | 資料層從 JSON 升級為 YAML + AI curation |

**A.3 文件間關係**

- GTM v7.1:市場定位、渠道、融資、風險。對應「為何要做這些功能」
- Master PRD v1.3(本文件):產品功能規格。對應「要做什麼」
- 維運計畫 v3:上線後監控與運維。對應「如何維護」
- STATE.md:當前焦點 + Next Up 隊列。對應「現在做哪個」
- ARCHIVE.md:已 ship 的工作紀錄(chronological)。對應「做過哪些」
- Codebase grep / git log:現狀 ground truth。對應「目前在哪」

開發新功能建議順序:查 STATE.md「Next Up」→ 讀對應 PRD 章節需求 → grep codebase 確認尚未實作 → 交付 Claude Code。

**十、更新記錄**

**10.1 v1.2 → v1.3 變更(2026-04-28)**

| **變更類型** | **內容** |
| --- | --- |
| 新增:4.5 Share Answer 公開連結 | 使用者觸發,生成匿名公開 URL(`vela.an-tho.com/q/{share_id}`)分享單一查詢結果。功能需求 1-9(Share trigger、URL 結構、SEO/社群 preview、SharedQuery schema、隱私 gate、防 abuse、6 個 PostHog 事件、16 語言 i18n、ToS/Privacy 對應)+ 驗收標準。Phase 1B 編號(維持 4.x cohere),執行順序覆寫至 Phase 0 末段。對齊 GTM_V1 § 5.4 L3 word-of-mouth 機制。 |
| 新增:4.6 SEO Explore Pages | 團隊預先建立的長尾 SEO 頁面(`vela.an-tho.com/explore/{slug}`),共用 4.5 Public Query Page renderer。功能需求 1-8(URL 結構、ExplorePage schema、內容生產工作流、頁面渲染、Sitemap 與索引、多語言 SEO 策略、3 個 PostHog 事件、內容初版主題清單)+ 驗收標準。Phase 1B 編號,Phase 0 末段執行。對齊 GTM_V1 § 5.4 L3 organic discovery 機制。 |
| 新增:4.5 + 4.6 共用設計檢核 | 兩功能共用 Public Query Page renderer / SSR layer / PostHog prefix(`share_*` vs `explore_*`),URL prefix 區分(`/q/*` 隨機 ID + noindex vs `/explore/*` 語意 slug + index)。 |
| 新增:4.5 + 4.6 對既有章節影響清單 | 列出對 0.4 / 3.1 / 3.4 / 4.1 / 4.2 / 4.3 / 4.4 / 6.2 / 6.4 的具體變動或非影響(處方解析 share v1.3 不啟用,因高度個資風險)。 |
| 調整:二章 Phase 0 執行順序 | 新增 v1.3 變更 NOTE 說明 § 4.5 + § 4.6 雖編號 4.x 但執行順序插入 Phase 0 末段(§ 2.7 Step 8 acceptance 後、Phase 0 Retrospective 前)。執行順序:§ 2.7 Step 7 → § 2.7 Step 8 → § 4.5 → § 4.6 → Retrospective。Phase 0 Retrospective 順延對應(時程估算不在本 PRD)。 |
| 調整:四章 Phase 1B header note | 加 1 行 italic 註明 § 4.5 + § 4.6 為 v1.3 新增 spec、執行順序覆寫至 Phase 0 末段、詳見二章 NOTE。 |
| 調整:leading block | v1.3 重點變更段、v1.2 → v1.3 增補 lead 描述、決策依據指向 § 10.1。 |
| 調整:footer 版本與日期 | v1.2 → v1.3,2026-04-17 → 2026-04-28。 |
| 調整:十章編號 | 既有 10.1(v1.1→v1.2)→ 10.2、10.1.1 → 10.2.1、10.2(v1.0→v1.1)→ 10.3、10.3(v1.0)→ 10.4。新 10.1 為 v1.2 → v1.3 變更。 |

**v1.3 決策依據(solo founder PM call,2026-04-28)**

soft launch(= Phase 0 ship gate)需要 word-of-mouth 工具(§ 4.5)與 SEO 內容基礎設施(§ 4.6)day-1 在位。GTM_V1 § 5.4 L3 mechanics 已假設兩者存在;若缺,soft launch L3 traction(paid acquisition cost / organic discovery)診斷訊號失真。

接受的取捨:Phase 0 ship gate 與 Phase 1A 起始點順延(時程不在本 PRD 估算)。

否決的替代方案:

- Phase 1B(原 v1.2 章節編號順序)— 否決,理由:soft launch 期間 L3 機制缺失將汙染「什麼有效 / 什麼沒效」的判讀
- Phase 1A 末段(post soft launch)— 否決,理由同上
- 只做 4.5 延後 4.6 — 否決,理由:4.6 重用 4.5 共用基礎設施,邊際工程成本低;延後 4.6 等於放棄內容團隊 6-12 個月累積期的起跑點

**10.2 v1.1 → v1.2 變更(2026-04-17)**

| **變更類型** | **內容** |
| --- | --- |
| 新增:2.7 Explain 臨床推理強化 | Phase 0 P1 新增任務,排在 2.1 Model Provider 之前執行。核心:改 explain_service.py system prompt 做臨床組合推理(不只翻譯數值),hedging language 強制,citation 禁用 LOINC 作為臨床判斷來源,加風險分層 🟢🟡🔴 標籤。工期 1-2 天。 |
| 新增:5.1.1 在地知識 YAML 實作規範 | Phase 1C 在地差異提示(5.1)的執行細節。Tier 1 六國(TW/JP/KR/SG/MY/TH)、YAML schema、AI-assisted curation 流程、可信度三層防護、Tier 3 預留擴充點。明確寫下「歐美加不在 Tier 1」的策略選擇理由(TA 錯位 + OpenEvidence 結構性占據)。 |
| 調整:Phase 0 時程 | 從 v1.1 的 2-2.5 週延長為 2.5-3 週(13-15 工作天),原因為新增 2.7。Phase 1A 起始點順延至 Week 3。第九章時程總覽對應調整,新增 W1-1.5 的 2.7 列。 |
| 調整:6.1 i18n key 命名 | 新增 explain.* 前綴,包含 explain.risk.* 與 explain.disclaimer。 |
| 調整:6.5 Prompt 管理 | 補充 explain_system.md 是 2.7 主要改動目標,bump 到 v2。 |
| 調整:7.1 Out of Scope | 新增三項:Explain 病歷 PDF OCR、Tier 3 使用者貢獻在地知識、歐美加 Tier 1 在地 YAML(策略不做)。 |
| 調整:8.1 Phase 0 驗收標準 | 新增 Explain 臨床推理強化驗收段落(risk tier、hedging、citation、LLM judge)。 |
| 調整:8.4 Phase 1C 驗收標準 | 新增 YAML 驗證、6 國 YAML 完整、url_native HTTP 200 三項。 |
| 調整:附錄 A.2 章節對照 | 新增 2.7 與 5.1.1 的 FEATURE_AUDIT 對照行。 |
| 調整:附錄 A.1 範例 prompt | 改以 2.7 為範例任務。 |

**10.2.1 v1.2 post-release 變更記錄(非正式 bump 版號)**

- 2026-04-18:新增 § 2.8 Anonymous Trial Flow(discovered gap,見 ADR 001)
- 2026-04-20:新增 § 2.9 Verify 輸出語言對齊 user locale(discovered gap,solo review Accepted,post-2.4 smoke test)

**10.3 v1.0 → v1.1 變更(2026-04-17)**

| **變更類型** | **內容** |
| --- | --- |
| 新增:2.0 PostHog 事件基礎建設 | FEATURE_AUDIT 發現整個 repo 只有 1 處 posthog.capture()。必須先建 utils/analytics.ts wrapper,後續所有追蹤任務依賴此。 |
| 新增:2.5 Landing Page SEO 修復(P0) | Landing Page 的 isLoaded gate 導致 SSG 只產出 2.9KB spinner shell,LinkedIn preview / Google SERP 全斷。Phase 0 Day 1 最優先。 |
| 新增:2.6 i18n SEO hreflang(P0 次高) | 16 語言但只 index 英文。策略 A(hreflang,1-2h)Phase 0 完成,策略 B(獨立 URL)Phase 2 評估。 |
| 擴充:2.1 Model Provider | 範圍從 2 檔案(generator.py、guards.py)擴大到 8 檔案:retriever.py、reranker.py、explain_service.py、entity_extractor.py、llm_judge.py、vector_store.py、server.py 都要 refactor。工期從 2-3 天擴大到 5-7 天。 |
| 修正:2.2 query_id | 從「前端生成 UUID」改為「沿用 backend 現有 audit_id」。避免兩套 ID 混用。 |
| 補充:2.3 Citation | 標註 frontend CitationPanel 已有 source_type,backend schemas enum 更完整,需對齊。 |
| 補充:3.4 Privacy Policy i18n | Phase 1A 實作時同步完成 16 語言翻譯,追加 0.5 天。 |
| 補充:4.1 FeedbackBar | 重用既有 UserFeedback 表 feedback_text 欄位,不做新 migration。 |
| 新增:6.3 錯誤碼清單 | 共通規範章列 9 個錯誤碼(LLM_RATE_LIMITED、LLM_TIMEOUT 等)+ 前端處理原則。 |
| 新增:6.6 Model Provider 命名規範 | api/providers/base.py、factory.py、errors.py 等檔案架構規定。 |
| 校準:Phase 0 時程 | 從 2 週延長為 2-2.5 週(10-13 工作天)。九章時程總覽對應調整。 |
| 新增:附錄 A PRD 使用說明 | 提供 Claude Code 工作流程範例 + PRD vs FEATURE_AUDIT vs GTM vs 維運計畫的文件關係說明。 |

**10.4 v1.0 版本(保留)**

v1.0 涵蓋 Phase 0 / 1A / 1B / 1C 初版規格,包括:Model Provider 抽象(初版 2 檔案)、query_id 關聯、Citation 追蹤、Onboarding 三問、首頁動態範例、Privacy 四接觸點、FeedbackBar 原因 chip、Citation ⓘ、Settings user_context、處方解析 MVP、在地差異提示分層、跨語言橋接面板。

*Vela · vela.an-tho.com · Master PRD v1.3 · Updated 2026-04-28*
