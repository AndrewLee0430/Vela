> **Note**: This document is preserved as historical reference for ADR 003 and ADR 004.
> The decisions encoded here have been propagated to repo files:
> - ADR 003 — Drug Name Resolution Strategy (docs/decisions/003-*.md)
> - ADR 004 — Prescription Parser Deferral (docs/decisions/004-*.md)
> - BACKLOG.md Phase 1B/1C work items
> - PRD.md status markers (§4.4 → 🧊, §5.1 advanced)
> - STATE.md Next Up section
>
> Original status: 草稿 · 待團隊決策 (2026-05-04)
> Decision crystallized: 2026-05-04 by solo founder
>
> **DO NOT modify this file**. It is a snapshot reference. Subsequent decisions should be ADRs that supersede sections here, not edits to this document.

---

# Vela 路線圖討論文件 v0.4

> **用途**：團隊討論用，整理市場顧問分析 + LLM 藥名識別實測 + 護城河重新定位後的最終建議
> **基於**：GTM v7.1 / PRD v1.2 / Decision 001 v0.4 / FEATURE_AUDIT / 維運計畫 v3
> **時間範圍**：Phase 0-1C（Week 0-12）+ Phase 2 候選清單
> **產出日期**：2026-05-04
> **版本**：v0.4（處方解析 MVP 從 Phase 1B 移除，護城河重新定位）
> **狀態**：草稿 · 待團隊決策

---

## 0. 版本演進與核心決策

### 0.1 v0.1 → v0.2 → v0.3 → v0.4 的決策軌跡

| 議題 | v0.1 | v0.2 | v0.3 | **v0.4** |
|---|---|---|---|---|
| TFDA API 範圍 | 全功能 P0 必補 | Phase 2 候選 | 僅處方解析 MVP P0 | **Phase 2 候選**（處方解析移除）|
| Verify input 策略 | 未明確 | 強制英文 | 強制英文 | **強制英文 + 友善引導**（保留）|
| 處方解析 MVP | Phase 1B 殺手功能 | Phase 1B 殺手功能 | Phase 1B 殺手功能（含 TFDA）| **移至 Phase 2 候選** |
| LLM-based 藥名 resolution | 未討論 | 明確不做 | 明確不做 | **明確不做**（保留）|
| Vela 護城河定位 | 未明確 | 處方解析 + 多語 | 處方解析 + 多語 | **多語 + 在地差異 + 跨語言橋接 + 匿名**（重新定位）|

### 0.2 v0.4 的核心決策：移除處方解析 MVP

**決策權重：護城河重新定位**

Vela 的真正護城河不在處方解析，而在：

1. **16 語介面 + 28M+ 英文文獻檢索**
2. **在地藥典差異提示**（TW/JP/KR/SG/MY/TH + 擴展 6 國）
3. **跨語言橋接**（疾病/藥物/概念在不同語言間的對齊）
4. **Anonymous by Default + Privacy-first**

處方解析在 Phase 1B 是「錦上添花的高風險功能」，不是核心差異化。把 10-13 天工程量釋放回**真正的護城河功能**，更紮實、更安全、更符合 Solo founder 紀律。

### 0.3 移除處方解析的次要理由

雖然主要決策權重是護城河重新定位，這些理由也支持移除：

- **工程量風險**：原排程 Week 5-8 緊繃，TFDA + 處方解析共需 10-13 天，buffer 被吃滿
- **法規灰色地帶**：處方解析接近 CDS（臨床決策支援），可能踩到 SaMD 監管紅線；Solo founder 無法務支撐
- **責任歸屬風險**：系統「主動給處方建議」與 Verify「資訊查詢」的法律風險等級不同
- **未驗證需求**：沒有真實藥師用戶訊號顯示處方解析是高頻需求

### 0.4 移除帶來的調整

- Phase 1B 排程重排：原本緊繃的 Week 5-8 釋放出來
- Phase 1C 部分內容提前啟動：在地差異提示、WHO ICD-11
- GTM 行銷訊息重新設計：從「處方解析殺手功能」改為「多語 × 在地 × 匿名」三重楔子
- 處方解析 MVP 規格保留為 Phase 2 候選，含明確重新啟動條件

---

## 1. TL;DR — 一頁摘要

**整體判斷：90% 戰且走 + 10% 補關鍵設計（依功能分流）**

現有 Phase 0-1C 規劃在移除處方解析 MVP 後足以驗證 PMF，且 Phase 1B-1C 排程更從容。Solo founder 12 週紀律保留。

### Vela 功能架構（v0.4 重新定位）

```
核心三大功能（PRD 主架構，維持）:
  ├─ Research（醫學文獻搜尋）
  ├─ Verify（藥物交互作用檢查）
  └─ Explain（檢驗報告解讀）

Phase 1B 升級重點（從處方解析改為）:
  ├─ Verify 強制英文 + 友善引導
  ├─ DailyMed API 整合（補強 Citation）
  └─ Anonymous Trial Flow polish

Phase 1C 護城河功能（提前啟動）:
  ├─ 在地藥典差異提示（Tier 1 6 國 + 擴展 6 國）
  ├─ WHO ICD-11 跨語言對齊
  └─ 跨語言橋接面板 MVP

從 Phase 1B 移除 → Phase 2 候選:
  └─ 處方解析 MVP（含 TFDA、剪貼簿 paste、Stage 1.5 mapping）
```

### 各功能 Input 策略矩陣

| 功能 | Input 性質 | Input 策略 | 需要 TFDA？ |
|---|---|---|---|
| Research | 自然語言問題 | 接受任何語言 | ❌ 否 |
| **Verify** | 藥師主動輸入藥名清單 | **選項 A 強制英文 + 友善引導** | ❌ 否 |
| Explain | 檢驗報告貼上 | 接受任何格式（LOINC mapping）| ❌ 否 |
| ~~處方解析 MVP~~ | ~~藥師被動 paste 整段中文處方~~ | **移至 Phase 2 候選** | Phase 2 評估 |

### LLM 藥名識別測試結論（40 題 × 三模型）

| 模型 | 識別率 | 誠實 fallback | Confident wrong |
|---|---|---|---|
| GPT-4.1-mini | 13.3% | 33.3% | **53.3%** ❌ |
| GPT-4.1 full | 16.7% | 23.3% | **60.0%** ❌ |
| GPT-5.4 nano | 12.5% | 82.5% | **0%** ✅ |

**結論：LLM-based 藥名 resolution 不可行**。即使 GPT-5.4 nano 0% confident wrong，識別率仍不足，且不解決處方安全核心問題。

### 其他資料源建議

- DailyMed API（補強 FDA labels，整合進現有 Research/Verify）
- WHO ICD-11 API（整合進 Phase 1C 跨語言橋接面板）

### 明確不做

- 處方解析 MVP（**從 Phase 1B 移除**，降為 Phase 2 候選）
- TFDA API（隨處方解析移至 Phase 2 候選）
- 處方截圖剪貼簿 paste（隨處方解析移至 Phase 2 候選）
- LLM-based 藥名 resolution（任何模型，任何功能）
- 16 國藥典 API
- SOC 2 Type II（6 個月內）
- Team 方案（呼應 PRD § 7.2）
- 主動進入歐美市場（守住 GTM v7.1）

---

## 2. 市場顧問分析背景摘要

### 2.1 對歐美擴張的結論

**不應全面挑戰 GTM v7.1「不進歐美」立場，但應戰術性修正**：

1. **OpenEvidence 已於 2026 年初以 EU AI Act 法規不確定性為由撤出歐盟與英國**——形成歐洲 AI 醫療搜尋真空，但 EU AI Act 合規成本對 solo founder 是吞噬性的
2. **美國醫師端 OpenEvidence 已 40%+ 滲透**，但**多語裔 allied health（菲律賓裔護理師、西語裔藥師、東南亞華語裔社區藥師）是結構性盲點**
3. **守住亞洲（台日 SEA）才是 Vela 真正可贏的主戰場**，6 個月內 70% 資源集中在此

### 2.2 戰術性開放（無工程成本）

- 維持「Vela for Work」匿名英文版全球可訪問，不主動行銷美國/歐洲
- 註冊 vela.health / vela.med 等域名（含 .ca / .de / .com.br / .eu）防搶註
- 加拿大魁北克 Francophone 作為 Month 6 後西方市場小規模試金石（合規成本最低）

### 2.3 真正需要警惕的競爭威脅

不是 OpenEvidence 也不是 UpToDate，而是 **ChatGPT for Clinicians 進入亞洲**——在未來 12 個月幾乎必然發生。Vela 必須在那之前以「**多語 + 在地差異 + 跨語言橋接 + 匿名**」四重楔子建立護城河。

注意：v0.4 將「處方安全」從楔子中移除，因為它對應的處方解析 MVP 已從 Phase 1B 移除。

---

## 3. Vela 護城河重新定位（v0.4 核心）

### 3.1 為什麼處方解析不是真護城河

當我們認真盤點 Vela 對抗各競品的真實優勢，會發現處方解析不是關鍵：

| 對抗對象 | Vela 真正能贏的維度 | 是否依賴處方解析？ |
|---|---|---|
| OpenEvidence | 非美國 HCP / 非醫師 / 非英語 / 匿名 / 在地法規 | ❌ 否 |
| UpToDate Expert AI | 個人可用價格 / 多語 / 匿名 / Allied Health | ❌ 否 |
| Perplexity | 醫療專業度（純醫療來源 + 法規對齊）/ 無 Reddit | ❌ 否 |
| ChatGPT | 醫療專屬 RAG / 在地藥典 / 不需企業合約 | ❌ 否 |
| Claude | 醫療專屬 + 在地 + Allied Health | ❌ 否 |

**所有對競品的勝出維度，都不依賴處方解析**。

### 3.2 v0.4 的四重護城河楔子

```
楔子 1: Your Language（多語）
   → 16 語介面 + 28M+ 英文文獻檢索
   → 用工作母語查詢英文最新文獻

楔子 2: Local Awareness（在地差異）
   → TW/JP/KR/SG/MY/TH（Tier 1 初版）
   → VN/PH/ID/HK/SA/AE（Tier 1 擴展）
   → WHO/NICE/EMA/Cochrane（Tier 2 fallback）
   → 每個藥/疾病的在地法規、給付、指引差異

楔子 3: Cross-Language Bridging（跨語言橋接）
   → 疾病、藥物、概念在不同語言間的精確對齊
   → WHO ICD-11 多語 anchor
   → 對 multilingual allied health 工作者是天然命中

楔子 4: Privacy-First & Anonymous
   → No identity verification required
   → No account required to try
   → No conversation history saved (default)
   → 5-Layer Guard Chain (PHI detection)
```

### 3.3 為什麼這四個比處方解析更值得投入

| 維度 | 處方解析 MVP | 四重楔子 |
|---|---|---|
| 工程量 | 10-13 天 | 已部分完成（Phase 0 完成 Anonymous + Privacy；Phase 1C 完成在地差異 + 跨語言）|
| 法規風險 | 高（CDS 灰色地帶）| 低（資訊查詢工具，user 自行判斷）|
| 競品複製難度 | 中（OpenEvidence Tandem 6-12 月可進台灣）| 高（多語在地化是長期累積，不是單一功能）|
| PMF 驗證訊號 | 單一功能使用率 | 四個維度交叉訊號 |
| 與 Vela 既有定位 | 偏離（從查詢工具變 CDS）| 強化（深化既有定位）|
| 失敗代價 | 處方安全責任 | 低 |

---

## 4. 建議方向總覽（按優先級）

| 優先級 | 項目 | 類別 | 工期 | 適用功能 | Phase |
|---|---|---|---|---|---|
| **P0** | Verify input 強制英文 + 友善引導 | UI 設計 | 1.5 天 | Verify only | 1B |
| **P0** | DailyMed API | 資料源 | 2-3 天 | Research / Verify | 1B |
| **P0** | 在地差異提示 Tier 1（6 國）| 在地化 | 4-5 天 | 全功能 | **1B 提前啟動** |
| **P1** | WHO ICD-11 API | 資料源 | 2-3 天 | 跨語言橋接 | 1C |
| **P1** | 在地差異提示 Tier 1 擴展（6 國）| 在地化 | 3-4 天 | 全功能 | 1C |
| **P1** | 跨語言橋接面板 MVP | 護城河功能 | 3-4 天 | 全功能 | 1C |
| **P2** | Open Targets API | 資料源 | 3-4 天 | Explain | Phase 2 |
| **P2** | **處方解析 MVP**（含 TFDA + 剪貼簿 paste）| 殺手功能 | 10-13 天 | 新獨立功能 | **Phase 2 候選** |
| **P2** | PMDA / KIKI API（日本）| 資料源 | 5-7 天 | 處方解析（日本擴張時）| Phase 2 |
| **P2** | SFDA / NPHIES（沙烏地）| 資料源 | — | YAML 連結即可 | Phase 2 |
| **❌** | LLM-based 藥名 resolution | UI/技術 | — | 任何功能 | 不做 |
| **❌** | 16 國藥典 API（一次到位）| 資料源 | — | — | 不做（依國家觸發再評估）|
| **❌** | SOC 2 Type II | 合規 | — | — | 不做（6 個月內）|
| **❌** | Team 方案 | 商模 | — | — | 不做（MRR ≥ $5K 後再評估）|

---

## 5. P0 — Phase 1B 核心工作

### 5.1 Verify input 強制英文 + 友善引導

#### 問題陳述

Verify pipeline 依賴 FDA OpenFDA（英文索引）。Vela 生產環境實測（輸入「冠脂妥 + 保栓通」）：

- 識別為 Atorvastatin + Aspirin（兩個都錯）
- Source 標示「Clinical Knowledge (No FDA label available)」
- LLM confident hallucinate，無 fallback 機制

#### 採用選項 A 的核心理由

1. **TA 真實能力**：核心 TA（社區藥師、醫學生、住院醫師）有英文學名識別能力
2. **真實 workflow 整合**：藥師主動輸入藥名清單時，打字成本極低
3. **強化專業形象**：「Vela 不會自動翻譯藥名以避免處方安全風險」是信任訊號
4. **與 Vela 定位一致**：「Retrieves from 28M+ English articles」本來就暗示 query 是英文
5. **0 維運成本**：沒有 LLM call、沒有模型 deprecate 風險、沒有 calibration 漂移
6. **Solo founder 紀律**：1.5 天工期，資源投入正確

#### UI 設計規格

**主 input field**

```
┌─────────────────────────────────────────────┐
│  💊 藥物清單（每行一種）                    │
│  Drug list (one per line)                   │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ rosuvastatin                          │ │
│  │ clopidogrel                           │ │
│  │                                        │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  💡 請輸入英文學名（generic name / INN）   │
│     例：rosuvastatin、clopidogrel           │
│                                             │
│  🔗 不確定學名？                            │
│     [TFDA] [Drugs.com] [PMDA] [MFDS]        │
└─────────────────────────────────────────────┘
            ↓
        [分析交互作用]
```

**偵測非英文輸入時的 inline 警告**

```
┌─────────────────────────────────────────────┐
│  💊 藥物清單                                │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ 冠脂妥                                │ │
│  │ 保栓通                                │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ ⚠️ 偵測到非英文藥名                 │   │
│  │                                      │   │
│  │ Vela 引用英文資料源（FDA / PubMed） │   │
│  │ 為避免翻譯錯誤造成處方安全風險，    │   │
│  │ 請改用英文學名查詢。                │   │
│  │                                      │   │
│  │ 🔗 [查詢 TFDA] [Drugs.com 對照]     │   │
│  │                                      │   │
│  │ [我來修改] [仍要送出（不建議）]     │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**注意**：v0.4 移除 v0.3 警告中「想用中文處方查詢完整藥單?請使用處方解析功能」的引導，因為處方解析功能已移除。

#### 按鈕行為

**「我來修改」（預設高亮）**
- 點下去 → 警告消失 → focus 回原本 input field
- 不清空內容（user 還能看到「冠脂妥」作為提醒）

**「仍要送出（不建議）」**
- 灰色、次要按鈕
- 點下去 → 警告消失 → 送 pipeline → 拿到 fallback 答案
- PostHog 紀錄 `non_english_input_proceeded_anyway`

#### i18n 文案（16 語）

```yaml
verify_input_hint: "請輸入英文學名（generic name / INN）"
verify_input_example: "例：rosuvastatin、clopidogrel"
verify_input_help_links_label: "不確定學名？"
non_english_warning_title: "偵測到非英文藥名"
non_english_warning_body: "Vela 引用英文資料源（FDA / PubMed），為避免翻譯錯誤造成處方安全風險，請改用英文學名查詢。"
non_english_action_modify: "我來修改"
non_english_action_proceed: "仍要送出（不建議）"
```

i18n 工作量：7 個 key × 16 語，半天可完成。

#### 工程量

| 項目 | 工期 |
|---|---|
| Frontend：input field + i18n hint | 0.5 天 |
| Frontend：偵測非英文輸入 | 0.25 天 |
| Frontend：inline 警告 UI + 兩個按鈕 | 0.5 天 |
| i18n：7 個 key × 16 語 | 0.5 天 |
| PostHog：4 個事件埋點 | 0.25 天 |
| 測試：UI flow + 不同語系 | 0.5 天 |
| **總計** | **~1.5-2 天** |

### 5.2 DailyMed API 整合

#### 為什麼補

- Vela Explain pipeline 已 link RxNorm → DailyMed
- 但 Research / Verify pipeline 仍用 FDA OpenFDA
- OpenFDA drug label endpoint 內容稀疏；DailyMed 是同一份資料的「主檔」

#### 規格

- **資料源**：[DailyMed by NIH NLM](https://dailymed.nlm.nih.gov/dailymed/services/v2/)
- **API**：RESTful
- **內容**：SPL（Structured Product Labeling）、適應症、禁忌、交互作用、劑量
- **成本**：免費、無 rate limit、無金鑰
- **工期**：2-3 天
- **整合點**：
  - Research pipeline 加為第 4 個 retrieval source
  - Verify pipeline 取代或補強 FDA OpenFDA
  - Citation ⓘ tooltip（PRD § 4.2）需新增 DailyMed 一句話說明

### 5.3 在地差異提示 Tier 1（6 國）

#### 為什麼從 Phase 1C 提前到 Phase 1B

v0.3 將此功能放在 Phase 1C，但移除處方解析後 Phase 1B 釋放出 5-7 天時間。**在地差異提示是 Vela 真正的護城河之一**，提前啟動加速 PMF 訊號收集。

#### 規格

**Tier 1 初版（6 國）**：TW/JP/KR/SG/MY/TH

每個國家 YAML 結構：

```yaml
country: TW
authorities:
  drug: TFDA
  insurance: NHI（健保署）
  guidelines: 衛福部
  
common_diff_patterns:
  - drug_approval_delay: "新藥相對 FDA 平均延遲 18-24 月"
  - insurance_restriction: "健保給付限制（如年齡、共病）"
  - dose_adjustment: "亞洲族群劑量考量（CYP2D6、CYP2C19）"

source_links:
  drug_search: "https://info.fda.gov.tw/MLMS/"
  insurance: "https://www.nhi.gov.tw/"
```

#### 整合方式

不是新功能 tab，是**所有現有功能的增強**：

- Research：搜尋結果側邊顯示「在地差異提示」
- Verify：交互作用結果含「TW 健保限制 vs FDA 標籤」對比
- Explain：檢驗解讀含「在地參考值差異」（如 LDL 治療目標）

#### 工程量

| 項目 | 工期 |
|---|---|
| YAML 資料結構設計 | 0.5 天 |
| 6 國資料整理（每國 0.5-0.75 天）| 3-4 天 |
| Backend：在地差異 retrieval 整合 | 1 天 |
| Frontend：UI 元件（側邊提示 + tooltip）| 1 天 |
| i18n：在地差異標籤 16 語 | 0.5 天 |
| 測試 + Polish | 0.5 天 |
| **總計** | **~6-7 天** |

### 5.4 Anonymous Trial Flow Polish（既有功能優化）

Decision 001 v0.4 已 production verified（FEATURE_AUDIT § 2.8）。Phase 1B 持續優化：

- L0 → L1 升級提示時機優化（PostHog 訊號驅動）
- L1 → L2 轉換 paywall UI 微調
- 16 語 onboarding 流程 polish

#### 工程量

| 項目 | 工期 |
|---|---|
| L0 / L1 / L2 升級提示優化 | 1 天 |
| Paywall UI polish | 0.5 天 |
| Onboarding 16 語 polish | 0.5 天 |
| **總計** | **~2 天** |

---

## 6. P1 — Phase 1C 護城河功能

### 6.1 WHO ICD-11 API

#### 為什麼補

- Phase 1C 跨語言橋接面板的疾病名稱對齊 anchor
- 多語官方 API 是天然的橋接：「糖尿病」/「diabetes」/「糖尿病」/「당뇨병」對齊到 5A11
- 含 traditional medicine 章節（中醫、印度醫學）

#### 規格

- **資料源**：[WHO ICD-11 API](https://icd.who.int/icdapi)
- **認證**：OAuth 2.0，需註冊申請 client_id（免費，3-5 工作天審核）
- **語言**：14 種官方語言（含繁中、簡中、日、韓、阿、俄、西、葡、法、英、德、阿拉伯、義、土）
- **成本**：免費
- **工期**：2-3 天

### 6.2 在地差異提示 Tier 1 擴展（6 國）

延續 § 5.3，擴展到：VN/PH/ID/HK/SA/AE

#### 工程量

| 項目 | 工期 |
|---|---|
| 6 國資料整理 | 3-4 天 |
| Backend / Frontend 已就緒 | 0 天 |
| i18n 補充 | 0.25 天 |
| 測試 | 0.5 天 |
| **總計** | **~4-5 天** |

### 6.3 跨語言橋接面板 MVP

#### 為什麼是護城河

multilingual allied health 工作者（菲律賓裔 RN、東歐護理師、台灣藥師）的核心痛點：

- 在英文教科書/文獻學專業詞彙
- 在工作語言（菲、波、台語）與病人/同事溝通
- 中間缺乏「精確對齊」工具

跨語言橋接面板解這個痛點：用 ICD-11 為 anchor，呈現疾病/藥物/概念在多語言間的精確對應。

#### 規格

- 整合 WHO ICD-11 多語 anchor
- 顯示同一概念在 4-5 種語言（user 工作語 + 英文 + 病人語）的對應
- 含臨床語境提示（學名 vs 俗稱、正式 vs 口語）

#### 工程量

| 項目 | 工期 |
|---|---|
| ICD-11 anchor 資料結構設計 | 0.5 天 |
| Backend：跨語言查詢邏輯 | 1 天 |
| Frontend：橋接面板 UI | 1.5 天 |
| i18n：4-5 語對齊邏輯 | 0.5 天 |
| 測試 | 0.5 天 |
| **總計** | **~3-4 天** |

---

## 7. P2 — Phase 2 候選

### 7.1 處方解析 MVP（從 Phase 1B 移除，降為 Phase 2 候選）

#### 重新啟動的觸發條件

明確寫入文件，未來決策有依據：

| 觸發條件 | 是否啟動處方解析 |
|---|---|
| Verify 月活 ≥ 1,000 + Pro 轉換率 ≥ 3% | ✅ 啟動，PMF 已驗證 |
| 藥師 user 主動詢問處方解析 ≥ 50 次 | ✅ 啟動，需求已驗證 |
| OpenEvidence 進入台灣推出處方功能 | ⚠️ 重新評估（防禦性啟動）|
| 6 個月後 Phase 1B/1C 仍未達 PMF | ❌ 不啟動，回到核心三功能優化 |

#### 啟動後的規格（保留供未來參考）

```
Phase 2 處方解析 MVP 完整規格:

  Stage 1: LLM 解析處方結構
     提取「藥名」、「劑量」、「頻次」、「療程」
  
  Stage 1.5: TFDA 主檔藥名 mapping
     冠脂妥 → rosuvastatin
     保栓通 → clopidogrel
     未對齊藥 → 標記 + 引導 user 手動補完
  
  Stage 2: 用英文學名查 FDA / DailyMed / RxNorm
  
  Stage 3: 結構化呈現 + 安全警示

  UI 增強:
     剪貼簿 paste 按鈕（搭配 iOS Live Text / Android Lens）
     未對齊藥的手動補完介面
```

#### TFDA API 規格（保留）

- **資料源**：[衛生福利部食品藥物管理署 西藥許可證資料集](https://data.gov.tw/dataset/14062)
- **格式**：CSV / XML download，月度更新
- **成本**：免費，需自建 ingestion pipeline
- **工期**：5-6 天（含 ingestion、mapping service、月度 cron）

#### 法規風險評估（Phase 2 啟動前必做）

啟動處方解析前，必須完成：

- TFDA SaMD 監管框架評估（是否屬醫療器材軟體）
- 「處方建議」vs「資訊查詢」的法律界線釐清
- 責任險評估
- Disclaimer 與 ToS 法律審閱

如果評估後法規風險不可控，**永久不啟動**，將處方解析需求引導至「Verify 強制英文」+「外部 TFDA 連結」。

### 7.2 Open Targets API

**用途**：Explain 場景中疾病-藥物-基因關聯的結構化資料

**觸發條件**：CP3 後若 Explain 使用率 ≥ 預期，且有 user feedback 指向「risk tier 不夠精準」

### 7.3 PMDA / KIKI API（日本）

**觸發條件**：CP3 後若 L3 訊號顯示日本使用者 ≥ 10%，且決策啟動日本 L2 + 處方解析 Phase 2 已啟動

### 7.4 SFDA / NPHIES（沙烏地）— 降級為「YAML 連結即可」

中東阿拉伯語藥師人口相對小。用 in-地差異 YAML 連結即可，不接 API。

---

## 8. ❌ 明確不做（誠實說 NO）

### 8.1 不做的 UI / 技術設計

| 項目 | 理由 |
|---|---|
| **LLM-based 藥名 resolution（任何模型）** | 40 題 × 三模型實測：GPT-4.1 系列 53-60% confident wrong；GPT-5.4 nano 雖 0% confident wrong 但識別率不足；任何 LLM 都有 hallucinate 風險 |
| **校正輸入框 / 第二個 input field** | 違反 single source of truth；mobile 體驗差 |
| **Modal-based 警告** | inline 警告即可；modal 在 mobile 上與鍵盤衝突 |
| **Verify 接受中文輸入後自動翻譯** | 同上，安全風險不可接受 |

### 8.2 不做的功能（v0.4 新增）

| 項目 | 理由 | 何時重新評估 |
|---|---|---|
| **處方解析 MVP（Phase 1B）** | 護城河重新定位為「多語 + 在地 + 跨語言 + 匿名」；工程量與法規風險不對齊 Solo founder 紀律 | Phase 2，依 § 7.1 觸發條件 |
| **TFDA API（Phase 1B）** | 隨處方解析移至 Phase 2 | 隨處方解析 |
| **處方截圖剪貼簿 paste** | 隨處方解析移至 Phase 2 | 隨處方解析 |

### 8.3 不做的資料源

| 項目 | 理由 |
|---|---|
| **16 國藥典 API（一次到位）** | 不可規模化；改為「依國家擴張時觸發」 |
| **OpenFDA FAERS** | 訊號雜訊比極低 |
| **ClinicalTrials.gov API** | 對核心 TA（社區藥師）幾乎無用 |
| **EMA 歐盟藥品資料庫** | 與「不主動進歐盟」紀律衝突 |
| **NICE Guidelines API** | UK NHS 用，與定位錯位 |
| **Lexicomp / Micromedex** | 商業授權年費 USD 5K+，買不起 |
| **自建 RxNorm 反查印度 / 越南藥品名** | 無公開資料源 |

### 8.4 不做的合規 / 商模動作

| 項目 | 理由 | 何時重新評估 |
|---|---|---|
| **SOC 2 Type II** | 6 個月內 solo founder 不可能取得 | MRR ≥ USD 30K + 第二位團隊成員後 |
| **Team 方案** | PRD § 7.2 已明確 Out of Scope | MRR ≥ USD 5K + 5-10 個獨立藥局來信後 |
| **HIPAA BAA / 簽訂醫院合約** | 進入 covered entity 後合規負擔暴增 | 不主動規劃 |
| **EU AI Act 高風險 SaMD 註冊** | OpenEvidence USD 12B 公司都選擇撤出 | 等 2027/2 + ARR ≥ USD 50K |

### 8.5 不做的市場動作

- 不做美國 / 歐洲付費行銷或 BD
- 不做歐盟主動行銷（被動可受）
- 不做美國醫學中心醫師（OE 已 40%+ 滲透）
- 不做英美純英語醫學生（UTD Pro Plus + ChatGPT for Clinicians 已飽和）
- 不做北歐 / 荷蘭（語言楔子失效）

---

## 9. 風險登記表（v0.4 整合版）

| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| Verify 強制英文導致台灣 user 流失 | 中 | 中 | PostHog 追蹤；外部連結引導；流失率 > 30% 時啟動 Phase 2 處方解析 |
| ChatGPT for Clinicians 在 6 個月內進入亞洲 | 高 | 高 | 維持「多語 + 在地 + 跨語言 + 匿名」四重楔子；強化「Vela 不為 UX 妥協安全」訊息 |
| User 在 Verify 選「仍要送出」拿到 fallback 答案誤以為正確 | 低 | 高 | 答案頁明確標示「無 FDA label」+ disclaimer |
| 移除處方解析後 Phase 1B 行銷亮點變弱 | 中 | 中 | 「在地藥典差異提示」作為新行銷亮點：「全球第一個提供 TW/JP/KR 藥品差異對比的 AI」 |
| OpenEvidence 進入台灣搶處方解析 | 中 | 中 | Vela 護城河不在處方解析；維持四重楔子；必要時 Phase 2 防禦性啟動處方解析 |
| 在地差異提示資料維護成本 | 中 | 中 | YAML 結構化；月度更新可由社群貢獻（FEATURE_AUDIT 已記錄人類審查機制）|
| 模型 deprecate 影響其他 LLM 用途 | 中 | 中 | Provider 抽象（PRD § 2.1）已為 Phase 0 完成 |

---

## 10. 決策建議與下一步

### 10.1 馬上行動（本週）

1. **WHO ICD-11 OAuth client_id 申請**（30 分鐘填表 + 等審核）
   - 不卡時程，提早申請

2. **域名註冊**（30 分鐘）
   - vela.health / vela.med 含 .ca / .de / .com.br / .eu

3. **在地差異提示 Tier 1 資料蒐集啟動**（背景進行）
   - 為 Week 5 工程啟動做準備
   - 6 國（TW/JP/KR/SG/MY/TH）藥典與健保網站盤點

### 10.2 Phase 1B 排程（v0.4 重排）

| Week | 工作項目 | 工時 |
|---|---|---|
| Week 4 | Verify 強制英文設計 + UI | 1.5 天 |
| Week 4-5 | DailyMed API 整合 + Citation ⓘ | 2-3 天 |
| Week 5-6 | 在地差異提示 Tier 1（6 國）| 6-7 天 |
| Week 7 | Anonymous Trial Flow polish | 2 天 |
| Week 7-8 | Phase 1B 整合測試 + Polish | 2-3 天 |
| **總計** | **~14-16 天**（Phase 1B 5 週合理範圍）|

**對比 v0.3 排程**：v0.3 因處方解析 + TFDA 排得緊繃，Week 5 buffer 被吃掉。v0.4 移除後，**Week 7-8 留出真實 buffer**，可吸收突發需求或加速 Phase 1C。

### 10.3 Phase 1C 排程（v0.4 微調）

| Week | 工作項目 | 工時 |
|---|---|---|
| Week 9 | WHO ICD-11 API 整合 | 2-3 天 |
| Week 9-10 | 在地差異提示 Tier 1 擴展（6 國）| 4-5 天 |
| Week 11 | 跨語言橋接面板 MVP | 3-4 天 |
| Week 11-12 | Phase 1C 整合測試 + Polish | 2-3 天 |
| **總計** | **~11-15 天**（Phase 1C 4 週合理範圍）|

### 10.4 文件變更建議

| 文件 | 變更類型 | 內容 |
|---|---|---|
| PRD v1.2 → v2.0 | **重大改版** | § 4.4 處方解析 MVP **整章移到 Phase 2 候選附錄**；新增 § 4.5 在地差異提示提前說明；§ 7.1 Out of Scope 大幅修訂 |
| GTM v7.1 → v8.0 | **重大改版** | Phase 1B 行銷訊息從「處方解析殺手功能」改為「多語 + 在地 + 跨語言 + 匿名」四重楔子；護城河論述重新撰寫 |
| 新增 Decision Record 002 | 新增 | Drug Name Resolution Strategy（含完整測試報告 + Verify 選項 A 決策）|
| 新增 Decision Record 003 | 新增 | **Phase 1B 處方解析移除決策**（含護城河重新定位論述）|
| FEATURE_AUDIT | 更新 | 將處方解析從 Phase 1B 規劃移至 Phase 2 候選 |

### 10.5 團隊討論清單

**P0 設計確認**
- [ ] 是否同意從 Phase 1B 移除處方解析 MVP？
- [ ] 是否同意「護城河重新定位為多語+在地+跨語言+匿名」？
- [ ] 是否同意 Verify 採用選項 A（強制英文 + inline 警告）？
- [ ] 是否同意在地差異提示 Tier 1 提前到 Phase 1B？

**Phase 排程確認**
- [ ] Phase 1B 重排（5 週含 buffer）是否合理？
- [ ] Phase 1C 排程（4 週）是否合理？
- [ ] Anonymous Trial Flow polish 工時是否充足？

**Out of Scope 確認**
- [ ] 是否同意 6 個月內不做 SOC 2 Type II？
- [ ] 是否同意維持 PRD § 7.2 Team 方案 Out of Scope 紀律？
- [ ] 是否同意不做 LLM-based 藥名 resolution（任何功能）？
- [ ] 是否同意不做 16 國藥典 API（一次到位）？

**處方解析 Phase 2 觸發條件**
- [ ] 觸發條件門檻（Verify 月活 ≥ 1,000、Pro 轉換 ≥ 3%、user 詢問 ≥ 50 次）是否合理？
- [ ] OpenEvidence 進台灣的「防禦性啟動」是否同意？
- [ ] Phase 2 啟動前的法規風險評估流程是否同意？

**市場方向**
- [ ] 是否同意維持「不主動進歐美」+「Vela for Work 全球可訪問」的不對稱開放策略？
- [ ] 加拿大 Francophone 試點是否進入 Month 6 後選項清單？
- [ ] GTM 行銷訊息調整（從「處方解析」改為「四重楔子」）是否同意？

**競爭風險回應**
- [ ] ChatGPT for Clinicians 進亞洲的時間預估與防禦策略
- [ ] OpenEvidence 進入日韓的時間預估與防禦策略
- [ ] OpenEvidence 進入台灣推出處方功能的觸發監測機制

---

## 11. 附錄 A：LLM 藥名識別測試報告

### 11.1 測試背景

PRD § 4.4 處方解析 MVP 與 Verify pipeline 依賴英文藥名。Vela 生產環境 Verify 實測（輸入「冠脂妥 + 保栓通」）顯示識別錯誤 + confident hallucinate。為了評估替代方案（強制英文 / TFDA API / LLM resolution），進行 40 題 × 三模型實測。

### 11.2 測試方法

**Prompt（一致）**：
```
請辨識以下台灣常見藥品的英文學名（International Nonproprietary Name, INN）。

規則：
1. 只回答你確定的答案
2. 不確定時請明確寫「不確定」，不要猜測
3. 格式：藥名 → 學名 (信心度: 高/中/低)
```

**測試題目（40 題）**：

常見藥（30 題）：冠脂妥、保栓通、普拿疼、安伯諾、立普妥、脈優、得安穩、康肯、信法明、諾胰保、伏冒熱飲、適泰樂、舒腹達、雅樂特、樂活喜、利福全、賜得安、怡諾思、樂耐平、喜美定、安胃靜、服寧、心律平、解尿通、善胃得、樂瑪可、拜瑞妥、福適佳、順爾寧、維康速

長尾藥（10 題）：速悅、拓凡瑞、易博定、安立復、思維佳、妥復克、立復健、益穩盈、邁可癒、復邁

**測試模型**：GPT-4.1-mini、GPT-4.1 full、GPT-5.4 nano（OpenAI Playground）

### 11.3 測試結果摘要

| 維度 | GPT-4.1-mini | GPT-4.1 full | GPT-5.4 nano |
|---|---|---|---|
| 樣本數 | 30 題 | 30 題 | 40 題 |
| 識別正確 | 4 題（13.3%）| 5 題（16.7%）| 5 題（12.5%）|
| 誠實 fallback（不確定）| 10 題（33.3%）| 7 題（23.3%）| 33 題（82.5%）|
| **High-confidence wrong** | **16 題（53.3%）**| **18 題（60.0%）**| **0 題（0%）**|
| Medium/low-confidence wrong | n/a | n/a | 2 題（5%）|
| 紅線題（拜瑞妥 NOAC）| ❌ Ticagrelor | ✅ Rivaroxaban | ✅ Rivaroxaban |
| 紅線題（妥復克 imatinib）| 未測 | 未測 | ✅ 安全 fallback |
| 紅線題（邁可癒 MMF）| 未測 | 未測 | ✅ 安全 fallback |

### 11.4 失敗模式分析

#### GPT-4.1-mini 與 GPT-4.1 full 的共同失敗模式

**Pattern 1：字面音似誤識**
- 安伯諾（glimepiride）→ Ambroxol
- 信法明（metformin）→ Sildenafil 或 Cephalexin
- 樂耐平（lorazepam）→ Lisinopril

**Pattern 2：同類藥猜最常見的**
- 冠脂妥（rosuvastatin）→ Atorvastatin
- 心律平（propafenone）→ Amiodarone

**Pattern 3：跨類別大跳躍**
- 得安穩（valsartan ARB）→ Diazepam（BZD）
- 順爾寧（montelukast）→ Sertraline（SSRI）

**特別觀察：GPT-4.1 full 比 mini 更愛猜**

#### GPT-5.4 nano 的 calibration 改善

**關鍵發現：0% confident wrong**
- 唯一錯誤的題（拓凡瑞 → Tafamidis）給「中」信心度
- 心律平 → Flecainide（誠實的近似錯誤）給「中」信心度

### 11.5 為什麼仍不採用 GPT-5.4 nano

雖然 nano 在純識別任務上 0% confident wrong：

1. **識別率僅 12.5%**：87.5% 的藥名需要 fallback
2. **處方安全不容 5% 誤差**：即使「中信心度錯誤」在處方場景仍是風險
3. **工程量不對稱**：選項 A 1.5 天 vs LLM resolution + UI 7-8 天

**v0.4 進一步論點**：移除處方解析後，LLM resolution 的應用場景大幅縮小（僅可能用於 Verify 中文輸入），而 Verify 採用選項 A 強制英文已足夠安全簡潔。

### 11.6 結論

1. **GPT-4.1 系列 confident wrong rate 不可接受**（53-60%）
2. **GPT-5.4 nano calibration 安全但識別率不足**
3. **依功能分流（v0.3）+ 移除處方解析（v0.4）= 最簡潔安全方案**：
   - Verify / Research → 選項 A 強制英文
   - Explain → 接受任何格式（LOINC 結構化）
   - 處方解析 → 移至 Phase 2 候選

---

## 12. 附錄 B：競品近期動態（決策背景）

- **OpenEvidence**：2026/1 Series D USD 250M @ USD 12B；2026/3 Mount Sinai Epic 部署；2026/4 Tandem 處方/PA 整合；**2026 撤出 EU/UK**
- **UpToDate**：2025/9 Expert AI 推出（限 Enterprise）；2025/10 Pro Plus 含學生版；2025/11 Lexidrug 整合
- **Perplexity**：2026/3 Personal Health Data search 推出
- **OpenAI**：2026/1/8 ChatGPT for Healthcare（GPT-5.2 + HIPAA BAA）；2026 ChatGPT for Clinicians 個人 HCP 免費；**ChatGPT Health 排除 EEA/瑞士/英國**
- **Anthropic**：2026/1/11 Claude for Healthcare（CMS / ICD-10 / NPI Registry connectors + HealthEx EHR partnership）

---

## 13. 附錄 C：資料源整體地圖（v0.4 完成後狀態）

```
Research pipeline:
  ✅ NumPy vector store（191 drugs）
  ✅ PubMed API
  ✅ FDA drug labels API
  🆕 DailyMed API（補強）
  🆕 強制英文輸入 + inline 警告
  🆕 在地差異提示整合（Tier 1 6 國）

Verify pipeline:
  ✅ FDA API
  🆕 DailyMed API（補強）
  🆕 強制英文輸入 + inline 警告
  🆕 在地差異提示整合

Explain pipeline:
  ✅ LOINC
  ✅ RxNorm
  ✅ MedlinePlus
  🆕 在地差異提示整合（檢驗參考值差異）
  📅 Open Targets API（Phase 2 候選）

In-Local YAML（Phase 1B-1C）:
  🆕 TW/JP/KR/SG/MY/TH（Tier 1 初版 6 國）
  🆕 VN/PH/ID/HK/SA/AE（Tier 1 擴展 6 國）
  ✅ WHO/NICE/EMA/Cochrane（Tier 2 fallback）
  🆕 WHO ICD-11 API anchor（跨語言對齊）

Phase 2 候選（觸發後啟動）:
  📅 處方解析 MVP（含 TFDA + Stage 1.5 mapping + 剪貼簿 paste）
  📅 PMDA / KIKI（日本擴張時，給處方解析）
  📅 MFDS（韓國擴張時，給處方解析）
  📅 SFDA YAML 連結（不接 API）

明確不做:
  ❌ LLM-based 藥名 resolution（任何模型，任何功能）
  ❌ 16 國藥典 API（一次到位）
  ❌ EMA / NICE / Lexicomp / Micromedex
```

---

## 14. 附錄 D：與現有文件的對齊關係

| 本文件章節 | 對應現有文件 | v0.4 變更影響 |
|---|---|---|
| § 5.1 Verify 強制英文設計 | PRD v1.2 § Verify pipeline（補強）| 新增章節 |
| § 5.2 DailyMed API | PRD v1.2 § 4.2 Citation ⓘ + Explain pipeline 既有 RxNorm 整合 | 提前到 Phase 1B |
| § 5.3 在地差異提示 Tier 1 | PRD v1.2 § 5.1（提前啟動）| **從 Phase 1C 提前到 Phase 1B** |
| § 6 Phase 1C | PRD v1.2 § 5.1 / § 5.2 | Phase 1C 範圍縮小但深化 |
| § 7.1 處方解析 Phase 2 候選 | PRD v1.2 § 4.4 整章 | **整章移至 Phase 2 附錄** |
| § 8 Out of Scope | PRD v1.2 § 7.1 / § 7.2 | 大幅擴充 |

---

## 15. 附錄 E：關鍵術語

- **Tier 1 / Tier 2 / Tier 3**：在地差異提示分層（PRD § 5.1）
- **L0 / L1 / L2**：使用者層級（L0 匿名 / L1 Vela for Work / L2 Pro，Decision 001）
- **CP1 / CP2 / CP3**：GTM v7.1 Checkpoint（Week 5 / 9 / 15）
- **PMF**：Product-Market Fit
- **SaMD**：Software as a Medical Device
- **CDS**：Clinical Decision Support（臨床決策支援系統）
- **NPI**：National Provider Identifier（美國醫師執業號）
- **BAA**：Business Associate Agreement（HIPAA 合約）
- **INN**：International Nonproprietary Name（學名）
- **Confident wrong**：LLM 給高信心度但答案錯誤的失敗模式
- **Confidence calibration**：模型信心度與正確率的對應關係
- **四重楔子**：v0.4 重新定位的 Vela 護城河（多語 + 在地 + 跨語言 + 匿名）

---

## 16. 修訂紀錄

| 版本 | 日期 | 作者 | 變更 |
|---|---|---|---|
| 0.1 | 2026-05-04 | andre + 市場顧問分析 | 初版，基於 Phase 0-1C 規劃對齊與競品分析整理 |
| 0.2 Final | 2026-05-04 | andre + 顧問 + 三模型實測 | 基於 40 題 × 三模型測試重寫；TFDA 降為 Phase 2 候選；LLM resolution 明確不做；選項 A 強制英文升為 P0 |
| 0.3 Final | 2026-05-04 | andre + 顧問 | 修正 v0.2 對處方解析 MVP input 策略的盲點：依功能分流（Verify 強制英文 / 處方解析 MVP TFDA mapping）；TFDA 重新升為 P0 但範圍縮小到僅處方解析 MVP |
| **0.4** | **2026-05-04** | **andre + 顧問** | **處方解析 MVP 從 Phase 1B 移除，降為 Phase 2 候選；Vela 護城河重新定位為「多語 + 在地 + 跨語言 + 匿名」四重楔子；在地差異提示 Tier 1 從 Phase 1C 提前到 Phase 1B；TFDA 隨處方解析移至 Phase 2；新增 Phase 2 處方解析觸發條件與法規風險評估流程；Phase 1B/1C 排程重排** |

---

*文件用途：團隊內部討論用。決策後相關內容應遷移至 PRD v2.0 / GTM v8.0 / 新 Decision Record 002 + 003。*
*Vela · vela.an-tho.com · Roadmap Discussion v0.4 · 2026-05-04*
