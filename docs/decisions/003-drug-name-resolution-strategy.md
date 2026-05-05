# ADR 003: Drug Name Resolution Strategy

**Status**: Accepted
**Date**: 2026-05-04
**Decision-makers**: Solo founder (user) + advisor discussion 2026-05-04 (顧問 + 三模型實測)

## Context

Verify pipeline depends on FDA OpenFDA (English-indexed). Production verification (input "冠脂妥 + 保栓通") showed confident hallucinate — drugs misidentified, no fallback mechanism. Three options were considered: (A) Force English input + friendly guidance, (B) LLM-based name resolution, (C) Internal dictionary via TFDA API.

40-題 × 3-model empirical test (GPT-4.1-mini / GPT-4.1 full / GPT-5.4 nano) revealed:
- GPT-4.1 series: 53-60% confident-wrong rate (unacceptable for prescription safety)
- GPT-5.4 nano: 0% confident wrong but 12.5% recognition rate (UX broken)

Full test report + UI spec + i18n keys + engineering breakdown documented in advisor discussion notes (preserved in git commit 394545e § 5.1, § 11; file removed 2026-05-05 per cleanup decision).

## Decision

**Adopt Option A**: Verify accepts only English INN (generic name) input. Non-English input triggers inline warning + friendly external links (TFDA / Drugs.com / PMDA / MFDS) without auto-translation.

Option B (LLM resolution) and Option C (TFDA API) both rejected — see ADR 004 for prescription parser deferral context (sister decision).

## Consequences

**Positive**: Zero confident-hallucinate risk. No LLM dependency / model lifecycle exposure. Strengthens "safety-first" positioning. 1.5-day implementation enables Phase 1B on schedule.

**Negative**: Some TW pharmacist friction (need to look up English INN). Mitigated by inline external lookup links + PostHog tracking (`non_english_input_proceeded_anyway`) for revisit if friction proves prohibitive (>30% over 30 days).

## Implementation

Deferred to Phase 1B Week 4 per BACKLOG.md. UI spec, i18n keys (7 keys × 16 languages), and PostHog event schema documented in advisor discussion notes (git commit 394545e § 5.1).

Estimated engineering: 1.5-2 days.

## References

- Advisor discussion notes 2026-05-04 (preserved in git commit 394545e — file removed 2026-05-05)
- [ADR 004](004-prescription-parser-deferral.md) — sister decision (護城河 rebalance)
- [BACKLOG.md](../../BACKLOG.md) — Phase 1B work item entry
