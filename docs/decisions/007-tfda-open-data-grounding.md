# ADR 007: TFDA Open-Data Grounding (Deep Local Grounding)

**Status**: Accepted
**Date**: 2026-06-26
**Decision-makers**: Solo founder (founder decision 2026-06-26)
**Scopes**: ADR 003 + ADR 004 — specifically their "No TFDA API (any phase)" rejection lines

## Context

This ADR follows the **2026-06-26 localization-grounding repo scan** + a **TFDA open-data web probe**. It IS the **dedicated localization-grounding ADR** that the [ADR 004](004-prescription-parser-deferral.md) **2026-06-26 addendum** ("⚠️ Open reconciliation") explicitly deferred to — that addendum recorded the DailyMed + ingest-and-cite constitution but flagged that ADR 003/004's blanket "No TFDA API (any phase, any future spec)" line was in tension with treating TFDA 仿單 evidence ingestion as a going concern, and deferred the resolution to "a dedicated localization-grounding ADR." This is that ADR.

The strategy thesis (from the localization-grounding report): Vela's only defensible moat is **deep local grounding** — ingesting Taiwan TFDA Chinese drug labels (仿單) as a citable RAG source and answering with Taiwan standards + citations — versus the current frontend "pointer" panel that only points users to TFDA/NHI to self-verify.

**Source-of-truth note:** the **ingest-and-cite constitution is GOVERNED BY the [ADR 004](004-prescription-parser-deferral.md) 2026-06-26 addendum**. The restatement in **Decision point 3** below is a convenience copy for readers, **NOT** a competing source of truth — if the two ever diverge, the ADR 004 addendum prevails.

## Decision

1. Adopt TFDA 仿單 OPEN DATA as a citable RAG evidence source (deep local grounding),
   first step serving the pharmacist core TA. TWO assets:
   (a1) 全部藥品許可證資料集 (infoId=37 未註銷, CSV/JSON/XML/API, weekly, 政府資料開放
        授權條款 v1.0) — gives 中文品名↔主成分 (brand→ingredient) + 適應症/用法用量
        (grounding-lite). Trivially ingestible; high confidence.
   (a2) 藥品電子結構化仿單資料庫 (full structured label text, mcp.fda.gov.tw) — deep
        grounding content; bulk full-text access path is a build-time confirmation.

   **📌 2026-06-29 data-probe correction (the real dataset was pulled + characterized):** two factual errors in the a1 description above — (1) **name↔id mapping:** in the current TFDA OpenAPI, **id=37 = 「未註銷藥品許可證資料集」 (active-only — the correct set to use)**; the name **「全部藥品許可證資料集」 is actually id=36** (includes cancelled). Keep using **id=37**, but its correct name is *未註銷藥品許可證資料集*. (2) **access:** it is **bulk-ZIP-only** — `GET /data/opendata/export/37/json` returns `application/zip` (inner `37_5.json`, **26,020 records**, 29.5 MB); the per-dataset query API `/dataset/openapi/{id}` returns **404** → there is **NO queryable/paged API**, so the design is **pin-a-dated-snapshot + periodic (monthly) re-pull**, not live query (the CSV/XML export variants are the same bulk ZIP). For later: **id=39 = 藥品仿單或外盒資料集 is the a2 full-仿單 source.** The Decision is otherwise unchanged.

2. SCOPING of ADR 003/004 "No TFDA API (any phase, any future spec)": that rejection
   targeted a LIVE-RUNTIME TFDA-API dependency for drug-name RESOLUTION (ADR 003
   Option C). It is NOT reversed for that use — Vela still does NOT resolve drug names
   via a live TFDA API call in the query path. This ADR carves out a DIFFERENT use:
   PERIODIC BATCH INGESTION of TFDA open-data dumps into Vela's OWN vector store /
   lookup table, served from Vela's own infra (same pattern as PubMed + the existing
   drug corpus). Coupling is soft (a stale-but-present local corpus survives a TFDA
   sync failure, unlike a live per-query resolution dependency). CLARIFICATION for
   future readers: fetching TFDA OPEN-DATA EXPORT endpoints in order to PERFORM that
   periodic batch ingestion is WITHIN this carve-out — it is NOT the rejected mechanism.
   The rejection concerns a live, per-query, runtime drug-name-resolution dependency;
   retrieving an open-data dump to index locally is a different thing.

3. Ingest-and-cite constitution (per ADR 004 2026-06-26 addendum) governs ALL grounding:
   retrieve+cite label text; NO LLM-generated local rules; NO individualized advice;
   NO DDI "cannot-combine" verdict engine. FDA/DailyMed retained as US-comparison arm.

4. Scope discipline: deep grounding ONLY for open-commercial-downloadable data
   (currently TW TFDA 仿單). TW MEDICAL-SOCIETY GUIDELINES (高血壓/糖尿病/感染症) are
   #2 TA-priority (clinical-decision core; nurses + med students also use them) but
   copyright-blocked → POINTER now + ACTIVELY PURSUE per-society licensing (they
   GRADUATE to grounding IF a license is secured; do NOT RAG-ingest them without a
   license — the diabetes society explicitly prohibits reproduction). JP/KR/SG/MY/TH =
   PASSIVE POINTER (no open data, no licensing track). International fallback =
   WHO/NICE/EMA.

## Consequences

Unblocks TFDA sequencing (T2/T3/T4). brand→ingredient data layer
CONFIRMED via (a1) — removes the existing item's "no open dataset" uncertainty. Deep
grounding (a2) gated on the mcp.fda.gov.tw bulk-access confirmation. License covers
copyright not patents/trademarks/logos (no TFDA-logo endorsement).

## References

- [ADR 004](004-prescription-parser-deferral.md) — 2026-06-26 addendum (the ingest-and-cite constitution this ADR is governed by; its "⚠️ Open reconciliation" flag is RESOLVED by this ADR) + the "No TFDA API (any phase)" Decision line this ADR scopes.
- [ADR 003](003-drug-name-resolution-strategy.md) — sister rejection (Option C "Internal dictionary via TFDA API") this ADR scopes.
- `BACKLOG.md` — TFDA-grounding CANDIDATE tasks (a1/a2/c/d/e/f/g) + the brand-name→ingredient + Q2-a items this ADR annotates.
- `docs/PRD.md` §5.1 / §5.1.1 (deep-grounding tier above the pointer model) + §2.3 / §2.10 (`tfda` SourceType strategy + source-authority label).
- 2026-06-26 localization-grounding strategy report + repo scan + TFDA open-data web probe (external).
