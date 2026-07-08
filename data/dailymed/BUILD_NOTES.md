# DailyMed US-label corpus — Stage A (offline artifact)

**Status: BUILT + VALIDATED, NOT WIRED.** This corpus is imported nowhere in the live
retrieval path. It becomes a Research 5th source only in **Stage B** (adds
`SourceType.DAILYMED`, `retriever._search_dailymed`, the §2.7 Research re-baseline +
danger-path + human-eye gate, and the `share_renderer.py` debt-(2) reconcile). Do not
treat this as shipped — the founder owns the Stage-B baton + the STATE bump.

## What it is
US drug labels (DailyMed SPL) for the same active moieties Vela already grounds in TW via
the v193 TFDA indication corpus — the "market-overlap" scope (DailyMed = the US-comparison
arm, ADR 004/007 ingest-and-cite: store the label's own text, **no DDI-verdict logic**).

- `label_docs.json` — one doc per representative SPL (content = `DailyMedLabel.to_text()`,
  all 6 LOINC sections; metadata: `source_id=DailyMed:{setid}`, setid deep-link `url`,
  `moiety`, `marketing_category`, `setid`, `spl_version`).
- `label_emb.npy` — float16, shape (1040, 1536), `text-embedding-3-small` (identical to
  TFDA/local → comparable in the shared reranked pool).

## Rebuild (monthly re-pull discipline, mirrors TFDA's dated snapshot)
```
python scripts/build_dailymed_label_corpus.py           # STEP 1: resolve+fetch+parse -> label_docs.json
python scripts/build_dailymed_label_corpus.py --embed   # STEP 2: embed -> label_emb.npy
```
Snapshot pinned by DailyMed `db_published_date` (recorded in `label_docs.json._meta.stats`).
DailyMed is a live DB → a re-run is deterministic given the same setids but **not**
byte-identical across days (new `spl_version`s publish). Reference selection is server-side
via `marketing_category_code` (NDA C73594 > NDA-authorized-generic C73607 > ANDA C73584 >
other), so it prefers the originator/reference label over repackagers at build time — this
resolves the live [P2] repackager-selection debt offline.

## Validation (Stage-A gate — no §2.7, nothing live)
- Backbone: 1,908 mono-ingredient TFDA moieties (of 2,995 total distinct).
- Corpus: **1,040 docs**, 1,040 distinct moieties, **0 duplicate setids**.
- Coverage: 54.5% of the mono backbone matched a US label; 868 misses are expected
  (TW-only drugs, radiopharmaceuticals, chemicals, OTC-monograph items — e.g. 177Lu/18F
  tracers, chlorhexidine solution, 95% alcohol).
- Reference-label tiers: **NDA 696 / ANDA 159 / other 185**. Spot-checks resolve to
  originators (ABACAVIR→ZIAGEN, IVOSIDENIB→TIBSOVO, ZONISAMIDE→Zonegran).
- Index: dim 1536 (TFDA parity), npy 3.2MB / docs 5.3MB (TFDA ballpark, NOT the ~500MB
  157k full-raw trap).

## OPEN items for founder review BEFORE Stage B
1. **Per-section truncation** — `_MAX_SECTION_CHARS=2000` (`dailymed.py:44`) clipped
   **warnings 49% / drug_interactions 28% / boxed_warning 8% / contraindications 2%** of
   docs. Material on warnings + interactions. Per-section re-chunk (or a higher cap) is a
   founder call — NOT changed here (it would also affect the shipped Verify surface).
2. **185 "other"-tier moieties** — no NDA/ANDA/NDA-AG reference found → fell to the
   unfiltered top SPL. Often legitimate (drug has no US approval: aceclofenac, aluminum
   antacids/OTC, alcohol), but a few may be repackager-only for a real drug. Review the
   list (`marketing_category == "other"` in `label_docs.json`) before wiring.
3. **High-freq union** — no query-log/analytics source in the repo, so v1 ships the
   TFDA-moiety backbone only. High-freq expansion is a later same-pipeline RxCUI-add (no
   re-architecture) once a query-frequency source exists.
4. **`rxcui` not recorded** — the `/v2/spls.json?drug_name=` rows expose only
   `setid/title/spl_version` (no inline `rxcui`/`marketing_category`); the corpus keys on
   moiety instead. Adding per-setid `rxcui` needs an extra lookup — deferred (not needed
   for the vector corpus).
5. **Whole-label embedding** — one doc embeds all 6 sections (up to ~12k chars), which is
   fuzzier than TFDA's single-indication docs. Retrieval-tuning consideration for Stage B
   (e.g. per-section docs vs whole-label) — flagged, not decided here.
