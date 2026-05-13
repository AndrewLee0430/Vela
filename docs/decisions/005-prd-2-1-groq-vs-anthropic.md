# ADR 005: PRD §2.1 swap target — Anthropic → Groq

**Date**: 2026-05-13
**Status**: Accepted
**Supersedes**: PRD v1.3 §2.1 需求 2 + 需求 6 部分

## Context

PRD v1.3 §2.1 Model Provider 抽象層設計 secondary provider 為 Anthropic Claude(Haiku / Sonnet / Opus)。此設計於 2026-04-17 寫入 PRD v1.1,目標是「未來 OpenAI 漲價或服務中斷時,改 env var 秒切 Anthropic Claude」。

2026-05-13 進入 §2.1 工程前重新評估,發現 Anthropic 在 Vela Phase 0-1B 範圍內無實際切換動機:
1. 同 tier 同 price(Claude Sonnet 4.6 $3/$15 vs GPT-4.1 $2/$8 — 沒便宜)
2. §2.7 Step 8 acceptance baseline 是 OpenAI 跑出來的,品質訊號穩定
3. 切換需要重做 acceptance + 127 條 golden test regression — 切換成本 ≥ 不切換成本

進一步評估後,發現另一條完全不同的省錢路徑:Groq(LPU 硬體)跑 open-weight model(Llama 3.1 8B、GPT-OSS 120B)在輕量任務(Guard / Reranker / Retriever / Entity Extractor)上有 8-30x 便宜 + 5-8x 速度提升,且不直接 user-facing 答案,品質風險可控。

## Decision

PRD §2.1 secondary provider 從 Anthropic 改為 Groq:

- **Phase 0 §2.1 實作**:OpenAIProvider + GroqProvider
- **Phase 0 預設行為**:100% OpenAI(GroqProvider framework ready 但 default 不啟用)
- **Phase 1B 第一批切換目標**:Guard + Reranker + Retriever lightweight tasks → Llama 3.1 8B on Groq

Anthropic 與 OpenRouter 延後至 Phase 1B+ 真實需求出現後評估:
- **Anthropic**:Claude long-context 處理長 PubMed paper 是潛在 use case,但目前無 evidence 支持
- **OpenRouter**:Production fallback routing 是潛在 use case,目前 Vela scale 小,outage 影響 < 工程投入

## Rationale

### 為什麼 Groq 適合 Vela

| 維度 | OpenAI(default) | Groq(secondary)|
|---|---|---|
| 主力 RAG(Research / Verify / Explain main) | ✅ gpt-4.1 / gpt-4.1-mini,§2.7 verified | 不換(醫療品質風險) |
| Guard / Reranker / Retriever 輔助任務 | gpt-4.1-mini | **Llama 3.1 8B,30x 便宜,8x 快** |
| Anonymous L0 Trial | gpt-4.1-mini | **GPT-OSS 120B,13x 便宜,5x 快** |
| Embedding | text-embedding-3-small | ❌ Groq 無 embedding |
| Vision OCR | gpt-4o | Phase 2+ Llama 4 Scout 候選 |

### 為什麼不選 Anthropic
- 無 lightweight 任務省錢替代(Anthropic 沒有 8B 模型)
- 主力切換需重做 §2.7 Step 8 acceptance,沒實際好處
- 工程實作後實際上不會啟用,等同死碼

### 為什麼不選 OpenRouter(現階段)
- 5.5% credit purchase fee 在 Phase 0 / 1A 期間意義不大(月 spend 小)
- Production fallback routing 在 Phase 1B 撥開關啟用即可,Phase 0 加入是 premature
- OpenRouter 內部本來就接 Groq,Phase 1B 真要加 OpenRouter,GroqProvider 抽象架構不衝突

## Consequences

### Positive
- Phase 0 §2.1 工期從 5-7 天縮短為 4-5 天(Anthropic 砍掉 -1d)
- Phase 1B 有 specific 切換路徑(Guard / Reranker → Llama 3.1 8B)
- 證實 「Provider 抽象架構穩,Provider 自身不穩沒關係」 設計哲學(Groq 半年 deprecate 6 model 不影響 Vela)

### Negative
- Groq model lineup 不穩定(每季 deprecate 1-2 model),需 monitor Groq 公告
- 失去 Claude long-context 即時 option(Phase 1B+ 補)
- Provider abstraction layer 多 1 個 implementation(GroqProvider)

### Neutral
- Phase 0 ship 後行為跟現狀 100% 一致(預設 OpenAI 不變)

## Rejected alternatives

### Alt 1: PRD v1.3 原版 — OpenAI + Anthropic
**否決理由**:Anthropic 形同死碼,且工期 +1 天無 ROI。

### Alt 2: OpenAI + OpenRouter(取代 Anthropic)
**否決理由**:OpenRouter 5.5% fee + Phase 0-1A scale 小,production fallback 訊號弱;Phase 1B 撥開關時邊際工程量極小,延後加更合理。

### Alt 3: OpenAI + Anthropic + Groq 三 provider
**否決理由**:Anthropic 仍然死碼;blast radius 大;工程量 +1.5d。

### Alt 4: 完全不做 Provider abstraction(維持 OpenAI hardcode)
**否決理由**:CLAUDE.md Rule 15 已 mandate abstraction;OpenAI hardcode 散在 9 個檔案,Phase 1B 切換時必須先 refactor;一次性 refactor 比兩次便宜。

## Reference

- PRD §2.1 v1.4(2026-05-13 修訂)
- 對話紀錄:2026-05-13 solo founder PM call(本 ADR 撰寫當日)
- Audit report:HEAD c95117f LLM Model + Provider Configuration Audit
- 否決 OpenRouter 詳細 trade-off 分析:同對話 2026-05-13 「OpenRouter / Groq 評估」 段落
