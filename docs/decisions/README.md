# Vela Decision Records

本資料夾存放 Vela 的戰略決策紀錄(Architecture / Product Decision Records, ADR-style)。

## 用途

**Spec vs State vs Decision 的分工**:

- `docs/PRD.md` — **Spec**,描述「要做什麼」(穩定,慢改)
- `FEATURE_AUDIT.md` — **State**,描述「現在做到哪」(高頻,由 Claude Code 維護)
- `docs/decisions/` — **Decision**,描述「為什麼這樣做」(決策當下 + 後續調整紀錄)

決策紀錄不汙染 PRD(PRD 保持簡潔),也不汙染 FEATURE_AUDIT(那是現況不是理由)。

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

## 如何加新決策

1. 在此資料夾新增 `NNN-title.md`(編號遞增)
2. 使用 `001-anonymous-trial-flow.md` 的結構為模板
3. 更新本檔案的「決策索引」表格
4. 在 PRD 對應章節加 `> See decision: docs/decisions/NNN-title.md` pointer
5. 在 FEATURE_AUDIT 相關條目也加反向連結
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
