# DailyMed US-label corpus — PER-SECTION (offline artifact)

**Status: BUILT + VALIDATED, NOT WIRED.** This corpus is imported nowhere in the live
retrieval path. It becomes a Research 5th source only in **Stage B / B-2** (adds
`SourceType.DAILYMED`, `retriever._search_dailymed`, the §2.7 Research re-baseline +
danger-path + human-eye gate, and the `share_renderer.py` debt-(2) reconcile). Do not
treat this as shipped — the founder owns the B-2 baton + the STATE bump.

**Supersedes the Stage-A whole-label artifact (`3928aa3`).** B-1 changed ONLY doc
construction (whole-label → per-section) + the dedup key (`setid` → `(setid, loinc)`);
the reference-label selection is held fixed (same pinned setids — see Determinism).

## What it is
US drug labels (DailyMed SPL) for the same active moieties Vela already grounds in TW via
the v193 TFDA indication corpus — the "market-overlap" scope (DailyMed = the US-comparison
arm, ADR 004/007 ingest-and-cite: store the label's own text, **no DDI-verdict logic**).

- `label_docs.json` — **one doc per NON-EMPTY clinically-relevant LOINC section** (was: one
  `DailyMedLabel.to_text()` doc per label). `content` = the section's FULL text (prose +
  full flattened table), taken via `dm._collect_prose(sec)` + `dm._flatten_tables(sec)`
  **directly** — never `_section_text` / `to_text`, so nothing the Verify surface reads is
  touched and the label's own interaction TABLE is kept in full. Per-doc metadata:
  `source_id=DailyMed:{setid}#{loinc}` (unique per section; `~{i}` suffix if a giant section
  sub-chunked), setid deep-link `url`, `title="{brand} ({generic}) — {section}"`, `moiety`,
  `marketing_category`, `setid`, `spl_version`, and the NEW `loinc` + `section_type` (so B-2
  retrieval/citation can name which section a hit came from).
- `label_emb.npy` — float16, shape **(4297, 1536)**, `text-embedding-3-small` (identical to
  TFDA/local → comparable in the shared reranked pool). 13.2 MB (TFDA ballpark, NOT the
  ~500 MB full-raw trap).

## Two fixes folded in vs Stage-A
1. **Full section text** — Stage-A embedded `to_text()`, whose `_section_text` capped each
   section at `_MAX_SECTION_CHARS=2000` and (pre-Baton-A) dropped the interaction TABLE.
   Per-section docs now carry the full prose + full table (warfarin interactions =
   6,529 chars incl. fluconazole / rifampin / the CYP2C9-2C19 table, vs 2,000 truncated).
2. **Indications now present** — Stage-A had 0 indications docs (the `_LOINC_INDICATIONS`
   `"34067-0"` typo never matched); the A2-typo fix (`"34067-9"`, fly 205) is a hard
   dependency of this build. Indications = **971 docs** here.

## Rebuild (monthly re-pull discipline, mirrors TFDA's dated snapshot)
```
python scripts/build_dailymed_label_corpus.py            # STEP 1: reuse pinned setids, re-fetch + per-section -> label_docs.json
python scripts/build_dailymed_label_corpus.py --resolve  # STEP 1 (full re-pull): re-resolve moieties from scratch (~13 min network)
python scripts/build_dailymed_label_corpus.py --embed    # STEP 2: embed -> label_emb.npy
```
**Determinism:** the default build reuses the PINNED reference selection from the prior
`label_docs.json` (the `(moiety, setid, marketing_category, spl_version)` tuples produced by
`_resolve_moiety`/`_pick_reference`) and re-fetches each SPL — so **same setids → same
per-section docs**, and the corpus scope stays fixed to the pinned selection even as
DailyMed publishes newer `db_published_date` snapshots. `--resolve` runs the full network
re-resolve (unchanged selection logic: `marketing_category_code` NDA C73594 >
NDA-authorized-generic C73607 > ANDA C73584 > other) for a monthly refresh. Snapshot pins
recorded in `label_docs.json._meta.stats` (`snapshot_db_published_date` = current fetch;
`prior_stage_a_snapshot` = the pinned selection's origin).

## Validation (B-1 gate — no §2.7, nothing live)
- Backbone: **1,040 pinned reference setids** (the Stage-A selection). **988 labels** carry
  ≥1 clinical section; **52 dropped** (0 clinical LOINC sections or SPL re-fetch miss — the
  expected ~52, mostly `other`-tier OTC/monograph/chemical labels).
- Corpus: **4,297 section-docs**, avg **4.35 sections/label**, **0 `source_id` collisions**.
- Per-section-type: **dosage 986 · indications 971 · contraindications 829 · interactions
  658 · warnings 584 · boxed 269** — indications **> 0** confirms the A2-typo fix took.
- Reference-label tiers (labels-with-sections): **NDA 691 / ANDA 159 / other 138** (the 52
  drops are 5 NDA + 47 other — the `other` tier loses the most, as expected).
- Chunk guard: single embedding per section unless > 24,000 chars, then ~10% overlap
  sub-chunk. **35 docs sub-chunked** (a handful of very long dosage/warnings sections);
  longest section capped at 24,000/chunk.
- Index: **dim 1536** (HARD TFDA/local parity), npy **13.2 MB** / docs 14.5 MB.
- Load: `DailyMedCorpusStore` loads all 4,297 docs unchanged (doc-count-agnostic; `loinc` +
  `section_type` surface in the loaded doc dict — no store code change needed).
- Dormancy: `get_dailymed_store`/`DailyMedCorpusStore` imported nowhere in the live path;
  `SourceType` has NO `DAILYMED`; `retriever.py` untouched; no user-facing output changes.

## OPEN items for founder review BEFORE Stage B / B-2
1. ~~**Per-section truncation**~~ — **RESOLVED by this rebuild** (full uncapped section text).
2. ~~**Whole-label embedding**~~ — **RESOLVED by this rebuild** (per-section docs; each hit
   names its `section_type`).
3. **138 "other"-tier moieties** — no NDA/ANDA/NDA-AG reference found → fell to the
   unfiltered top SPL. Often legitimate (no US approval), but a few may be repackager-only
   for a real drug. Review `marketing_category == "other"` in `label_docs.json` before wiring.
4. **High-freq union** — no query-log source in the repo, so this ships the TFDA-moiety
   backbone only. High-freq expansion is a later same-pipeline add once a frequency source exists.
5. **`rxcui` not recorded** — `/v2/spls.json?drug_name=` rows expose only
   `setid/title/spl_version`; the corpus keys on moiety. Per-setid `rxcui` needs an extra
   lookup — deferred (not needed for the vector corpus).
6. **B-2 scope reminders (from the B-1 probe):** add `SourceType.DAILYMED` + `_search_dailymed`;
   reconcile the `share_renderer.py:235` host-map (`dailymed.nlm.nih.gov` → currently `rxnorm`)
   with `sourceLabels.ts` (debt-(2)); §2.7 Research re-baseline + danger-path (a DailyMed
   interactions/contraindications doc must never present as safety clearance the way the v193
   TFDA-indication constitution guards) + human-eye gate. NONE of these are done in B-1.

## Known cosmetic (pre-existing, NOT B-1)
`vector_store.py` uses `print("✅/⚠️ …")` (Rule #4 `print()` + emoji), which raises
`UnicodeEncodeError` on a cp950 Windows console when the store loads outside uvicorn. It does
NOT affect the actual load (verified under `PYTHONIOENCODING=utf-8`) or the app runtime.
Tracked in TECH_DEBT.
