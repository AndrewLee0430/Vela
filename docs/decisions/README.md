# Vela Decision Records

本資料夾存放 Vela 的戰略決策紀錄(Architecture / Product Decision Records, ADR-style)。

## 用途

**Spec vs State vs Decision 的分工**:

- `docs/PRD.md` — **Spec**,描述「要做什麼」(穩定,慢改;§ status markers 反映 ship 狀態)
- `STATE.md` / `ARCHIVE.md` / codebase grep — **State**,描述「現在做到哪」(STATE.md = current focus,ARCHIVE.md = shipped log,codebase = ground truth)
- `docs/decisions/` — **Decision**,描述「為什麼這樣做」(決策當下 + 後續調整紀錄)

決策紀錄不汙染 PRD(PRD 保持簡潔),也不汙染 STATE/ARCHIVE(那是現況不是理由)。

## 格式規則

1. **一個決策 = 一個檔案**,編號遞增不重用(即使 superseded 也保留舊檔)
2. 檔名格式:`NNN-short-kebab-case-title.md`(例:`001-anonymous-trial-flow.md`)
3. 每個決策必須包含:**Context / Decision / Consequences / Alternatives Considered**
4. Status:`Proposed` → `Accepted` / `Rejected` / `Superseded by ###`
5. 決策若被後續修改,不改舊檔,而是新增 `NNN` 並標記 `Supersedes: ###`

## 決策索引

| # | 標題 | Status | 日期 | 簡述 |
|---|---|---|---|---|
| 001 | Anonymous Trial Flow | Accepted (solo founder review, 2026-04-19) | 2026-04-18 | 兩層 UX / 三層資料設計,兌現 Privacy-first 承諾 |
| 002 | Documentation Reorganization | Accepted (2026-04-30) | 2026-04-30 | 拆 CLAUDE.md (574→111),新增 STATE/BACKLOG/ARCHIVE/TECH_DEBT,docs/architecture.md;PRD 加 status markers |
| 003 | Drug Name Resolution Strategy | Accepted (2026-05-04) | 2026-05-04 | Verify 採 Option A:強制英文 INN 輸入 + 非英文 inline warning + 外部查詢連結;基於 40-題×3 模型實測拒絕 LLM resolution / TFDA dict |
| 004 | Prescription Parser Deferral | Accepted (2026-05-04) | 2026-05-04 | 處方解析 MVP 永久移除(Phase 1B + 任何未來階段);TFDA API 不整合;護城河重新定位:5-wedge→4-wedge(multilingual + 在地差異 + 跨語言橋接 + privacy) |
| 007 | TFDA Open-Data Grounding | Accepted (2026-06-26) | 2026-06-26 | TFDA 仿單 open data 採為可引用 RAG grounding 來源(deep local grounding);scope ADR 003/004「No TFDA API」拒絕為「live-runtime 藥名解析依賴」,periodic BATCH ingestion 開放;ingest-and-cite constitution(無 LLM 生成在地規則 / 無 DDI verdict);醫學會指引 copyright-blocked → pointer + 主動爭取授權。 |

> 註:ADR 005/006 尚未補入本索引表,待回填(兩個 ADR 本身已存在於 `docs/decisions/`)。

## 如何加新決策

1. 在此資料夾新增 `NNN-title.md`(編號遞增)
2. 使用 `001-anonymous-trial-flow.md` 的結構為模板
3. 更新本檔案的「決策索引」表格
4. 在 PRD 對應章節加 `> See decision: docs/decisions/NNN-title.md` pointer
5. 若 ADR 影響進行中工作,同步更新 STATE.md / BACKLOG.md / TECH_DEBT.md
6. Commit message 格式:`docs(decisions): add ADR NNN — <short title>`

## 何時該記 ADR

**記**:
- 影響使用者體驗的產品決策
- 影響技術架構的重大選擇(例如 model provider、auth 模式)
- 影響商業模型的設計(pricing、quota、tier 劃分)
- 反向改動(例如「決定不做 feature X」)

**不記**:
- 純 bug fix
- 純 refactor 不改行為
- 小 UI 文案調整
- 內部 tooling 改動
