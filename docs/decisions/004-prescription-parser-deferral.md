# ADR 004: Prescription Parser Deferral

**Status**: Accepted
**Date**: 2026-05-04
**Decision-makers**: Solo founder (user) + advisor discussion 2026-05-04 (顧問)

## Context

Prior plan (PRD v1.3 § 4.4) listed Prescription Parser MVP as Phase 1B 殺手功能, integrated with TFDA API for Stage 1.5 mapping (冠脂妥 → rosuvastatin). Estimated 10-13 engineering days.

Advisor discussion 2026-05-04 challenged this position by re-examining Vela's真實護城河 against actual competitor advantage dimensions. Investigation preserved in git commit 394545e § 0, § 3 (file removed 2026-05-05 per cleanup decision).

Key finding: across all major competitors (OpenEvidence / UpToDate Expert AI / Perplexity / ChatGPT / Claude), Vela's winning dimensions are **multilingual + 在地差異 + 跨語言橋接 + Privacy-first** — none depend on prescription parsing. Prescription parser is "錦上添花的高風險功能" not core differentiation.

## Decision

**Permanently remove Prescription Parser from Phase 1B**. No Phase 2 candidate spec. No TFDA API integration (any phase, any future spec).

If future market/competitive conditions warrant revisit, the feature will be re-designed from scratch — 2026-05-04 spec (preserved in git commit 394545e) is not preserved as "ready-to-ship".

## Vela 護城河重新定位

5-wedge → 4-wedge:
- Wedge 1: Your Language (16 lang UI + 28M+ English literature)
- Wedge 2: Local Awareness (TW/JP/KR/SG/MY/TH + 6 expansion + WHO fallback)
- Wedge 3: Cross-Language Bridging (WHO ICD-11 anchor)
- Wedge 4: Privacy-First & Anonymous

Removed wedge: 處方安全 (was conflated with prescription parser).

## Consequences

**Positive**: Eliminates SaMD/CDS regulatory exposure. Releases 10-13 days of Phase 1B engineering for higher-leverage work (在地差異提示 Tier 1 advanced from Phase 1C to 1B). Cleaner narrative: "Vela is a multilingual literature search + verification tool, not a prescription tool."

**Negative**: Phase 1B 行銷 narrative loses "killer feature" framing. Mitigated by 4-wedge positioning: "全球第一個提供 TW/JP/KR 藥品差異對比的 AI" replaces "處方解析" as marketing anchor.

**Risk acknowledged**: If OpenEvidence enters Taiwan with prescription functionality, defensive position shifts to multilingual + local-difference depth — not feature parity in prescription parsing.

## What Phase 1B becomes instead

Per advisor discussion (git commit 394545e § 5):
- Verify 強制英文 + 友善引導 (per ADR 003)
- DailyMed API integration
- 在地差異提示 Tier 1 (TW/JP/KR/SG/MY/TH) — advanced from Phase 1C
- Anonymous Trial Flow polish

Detail: see BACKLOG.md Phase 1B section (added in Commit 4 of this batch).

## References

- Advisor discussion notes 2026-05-04 — full護城河 analysis + competitor matrix + risk assessment (preserved in git commit 394545e, file removed 2026-05-05)
- [ADR 003](003-drug-name-resolution-strategy.md) — sister decision (drug name resolution)
- [BACKLOG.md](../../BACKLOG.md) — Phase 1B work items
- [PRD.md § 4.4](../PRD.md) — original spec, marker updated to 🧊 OUT OF SCOPE in Commit 4
