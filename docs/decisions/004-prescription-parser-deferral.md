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

> **Scoped by [ADR 007](007-tfda-open-data-grounding.md) (2026-06-26):** this rejection targets a LIVE-runtime TFDA-API drug-name-resolution dependency; periodic BATCH ingestion of TFDA open-data into Vela's own corpus is out of this rejection's scope and is adopted in ADR 007.

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

### Founder decision (2026-06-26) — US-market deprioritization + DailyMed/TFDA ingest-and-cite constitution

(Recorded after the 2026-06-26 localization-grounding repo scan. Positioning/GTM + grounding-strategy consequences.)

- **US is DEPRIORITIZED as a GTM MARKET, NOT as a data source.** No US marketing; do NOT chase NPI-gated US physicians. Vela's GTM stays the non-English / local markets (Wedge 2 Local Awareness). The US matters only as a *comparison* reference, never a target market.
- **DailyMed integration STAYS ACTIVE** (reverses any "deprioritize DailyMed" reading). Role: (1) the **US-comparison arm** for Taiwan-vs-US differentiation (report Rec 3) — a fuller source than the sparse openFDA mirror; (2) better global drug-label data. It is **NOT a US-market feature**.
- **Ingest-and-cite constitution — applies equally to DailyMed AND TFDA:** retrieve + cite the label text (including its interaction section). Vela must **NOT** build a DDI engine that actively judges "these two drugs cannot be combined" — that crosses the medical-device line (report Rec 7). Consistent with "Eliminates SaMD/CDS regulatory exposure" in **Positive** above: present/cite what the label *says*, never generate an authoritative local rule or interaction verdict.
- **Couple DailyMed integration WITH the open Verify "FDA Label Analysis" [P1] honesty item:** real DailyMed label text replaces the LLM-generated interaction analysis currently mislabeled `source="FDA Label Analysis"`. Build as ONE coordinated piece. Both are 🔴 medical-output changes → require a **§2.7 re-baseline + human-eye gate** before ship.

**✅ Reconciliation — RESOLVED by [ADR 007](007-tfda-open-data-grounding.md) (2026-06-26):** the **Decision** section above states "No TFDA API integration (any phase, any future spec)" — that was scoped to the *prescription-parser drug-name-resolution* use (ADR 003 sister decision). This 2026-06-26 constitution treats **TFDA 仿單 *evidence* ingestion** as a going concern, which was in tension with that blanket wording. **ADR 007 resolves it:** the rejection is scoped to a LIVE-runtime TFDA-API drug-name-resolution dependency (still rejected); **periodic BATCH ingestion of TFDA open-data into Vela's own corpus is out of that rejection's scope and is ADOPTED in ADR 007.** ADR 007 is governed by the ingest-and-cite constitution in this addendum.

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
