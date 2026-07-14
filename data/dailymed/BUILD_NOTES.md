# DailyMed US-label corpus — PER-SECTION, fresh-snapshot (offline artifact)

**Status: LIVE-WIRED as the Research 5th source (B-2 Phase 2, 2026-07-14) — committed, NOT
yet deployed; PROD human-eye gate FOUNDER-PENDING (🔴).** The corpus now feeds live Research
retrieval: `SourceType.DAILYMED` (`schemas.py:20`), `retriever._search_dailymed` +
`enable_dailymed=True` (mirrors TFDA), a retrieval-time sub-chunk collapse
(`_collapse_subchunks`), the `share_renderer.py` debt-(2) host-map reconcile
(`dailymed`→"DailyMed", no longer "RxNorm"), and a section-aware danger-path harness.
Gates (local, fresh code): **§2.7 Research 20/20 PASS** (≥ 18/2/0 baseline, no regression);
**danger-path 0 violations / 0 mandatory-rechecks** (founder-signed-off section-aware
criterion); dogfooding shows DailyMed safety sections surface + get cited but do NOT robustly
out-rank strong PubMed (×1.5 weight = partial lift — a prominence/tuning flag, not a safety
issue). The founder owns the deploy + the prod human-eye gate + the STATE bump.

Founder decisions baked in: citation granularity = **SECTION-LEVEL** (distinct sections of a
drug cite separately; only `~i` sub-chunks of one section collapse). Elevated per founder:
a danger query citing a DailyMed DESCRIPTIVE section with ZERO safety section → MANDATORY
human-eye recheck regardless of the LLM-judge verdict.

**Supersedes the B-1 per-section artifact (`6c2c3a9`).** B-2 Phase 1 = a single FRESH
`--resolve` on one coherent snapshot + two resolve-quality fixes surfaced by the B-1 eyeball
(moiety-string normalization + mono-preferred selection).

## What it is
US drug labels (DailyMed SPL) for the same active moieties Vela already grounds in TW via
the v193 TFDA indication corpus — the "market-overlap" scope (ADR 004/007 ingest-and-cite:
store the label's own text, **no DDI-verdict logic**). One doc per NON-EMPTY clinically-
relevant LOINC section (full uncapped text via `dm._collect_prose` + `dm._flatten_tables`
directly — never `_section_text`/`to_text`), indications included (A2-typo fix `34067-9`).

- `label_docs.json` — per-section docs. `source_id=DailyMed:{setid}#{loinc}` (unique; `~{i}`
  if a >24k section sub-chunked), setid deep-link `url`, `title="{brand} ({generic}) —
  {section}"`, `moiety`, `marketing_category`, `setid`, `spl_version`, `loinc`, `section_type`.
- `label_emb.npy` — float16, (4611, 1536), `text-embedding-3-small` (HARD TFDA/local parity).

## B-2 Phase 1 — the two resolve-quality fixes (vs B-1)
The B-1 eyeball flagged: (a) alogliptin grounded on a COMBO label, and (b) real drugs missed
on messy backbone moiety STRINGS. Both are fixed here; selection is otherwise B-1's
`marketing_category_code` NDA C73594 > NDA-AG C73607 > ANDA C73584 > other.

1. **Moiety-string normalization** (`_normalize_moiety`) — before the DailyMed `drug_name`
   resolve, derive the base INN: strip trailing salt/hydrate tokens, a leading dev-code, and
   `(as X salt)`/wrapping parens (`OCTREOTIDE ACETATE`→`OCTREOTIDE`, `IDARUBICIN HCL`→
   `IDARUBICIN`, `TAK-491 (AZILSARTAN MEDOXOMIL (AS POTASSIUM SALT))`→`AZILSARTAN MEDOXOMIL`).
   **Applied ORIGINAL-QUERY-FIRST, normalized-as-fallback** → normalization can ONLY add
   recall, never changes a currently-resolved reference. Guards against over-stripping:
   - **element-cation guard** — never reduce a mineral salt to its bare cation
     (`CALCIUM GLUCONATE`↛`CALCIUM`, `SODIUM CITRATE`↛`SODIUM`); the anion is the drug identity.
   - **name-part guard** (`_NAME_PART_STEMS`, added 2026-07-14) — never reduce a moiety to a
     generic chemical-group prefix that is not a standalone INN. `BENZYL BENZOATE` (a scabicide
     whose name legitimately ends in "benzoate") was stripping to `BENZYL`, which then
     mis-matched **PRE-PEN (benzylpenicilloyl polylysine)** — an unrelated drug. The guard keeps
     `BENZYL BENZOATE` intact; it then misses (no US mono Rx label → absent/safe, NOT PRE-PEN).
     Same shape as the element guard; only `BENZYL BENZOATE` triggers it on the backbone (the
     rest of the set — METHYL/ETHYL/PHENYL/… — is defensive, changes nothing today).
   - excludes ambiguous salt words that are themselves base drugs (e.g. FUMARATE — dimethyl fumarate).
2. **Mono-preferred selection + combo drop** (`_find_mono_reference`, `_active_moieties`) — a
   mono backbone moiety must never ground on a COMBINATION label. If the pick's SPL has >1
   **base active moiety**, re-seek a mono reference for the base INN; if none exists → DROP.
   - combo detection counts **base active moieties** (SPL `<activeMoiety>`), which COLLAPSES a
     salt + its free base (VYNDAQEL lists `tafamidis` + `tafamidis meglumine` but is MONO → 1,
     not 2); a true combo (ampicillin + sulbactam) still counts 2.
   - fires for ANY combo pick incl. bare-INN moieties (`AMPICILLIN`→UNASYN now redirects to the
     ampicillin mono, not just `AMPICILLIN SODIUM`).

## Validation (B-2 Phase 1 gate — no §2.7, nothing live)
- Snapshot: **Jul 13, 2026** for selection + content + deep-link (single coherent snapshot;
  `prior_stage_a_snapshot=None`). ⚠️ DailyMed published a new monthly release mid-work, so
  setids differ from B-1's Jul-10 pinning — that is the intended fresh-snapshot refresh.
- Corpus: **1,908 backbone → 1,203 labels-with-sections → 4,608 section-docs** (avg 3.83/label).
- Per-section-type: dosage 1036 · **indications 1028** · contraindications 906 · interactions
  722 · warnings 632 · boxed 284 (indications > 0 confirms the A2-typo fix).
- Resolve provenance (after the name-part guard): original 952 · normalized_recall 135 ·
  **mono_rescue 116** · dropped_combo 78 · miss 627. (alogliptin → **Nesina** mono with real DPP-4
  interactions + T2DM indications.) The name-part guard's ONLY effect vs the prior corpus:
  `BENZYL BENZOATE` moved mono_rescue(→PRE-PEN, wrong) → miss (absent/safe); mono_rescue 117→116,
  miss 626→627; every other moiety unchanged.
- **Combo-label survivors: 110 (pre-fix) → 8** (title proxy). Of the 8: 3 are proxy
  false-positives that are actually MONO by base-moiety (`Celestone Soluspan` = two betamethasone
  forms; `Premarin` = conjugated estrogens; caffeine-sodium-benzoate); 2 are drug-in-diluent
  premixes (cefuroxime/meropenem in saline/dextrose — clinically the drug); 2 are junk that
  leaked (idebenone/bromelain cosmetics); 1 is a missed rescue (`EPINEPHRINE HCL`→lidocaine+epi,
  but `EPINEPHRINE`→EpiPen mono IS present separately). No coverage lost.
- `dropped_combo` = 78 genuine (vitamins/supplements, US-combo-only drugs — SULBACTAM,
  PIPERACILLIN, SULFAMETHOXAZOLE, COLISTIN, DIENOGEST — and multi-mineral antacid salts).
- Regression vs B-1: 923 common moieties; 79 setid changes = 76 mono_rescue + 3 fresh-snapshot
  churn; 65 "absent" = deduped same-drug variants or dropped combos (none lost to normalization).
- Index: **dim 1536** (HARD parity), emb float16 (4608, 1536), 14.2 MB; row-match docs==emb.
- Content: warfarin interactions full table intact (6,529 chars incl. fluconazole/rifampin/CYP2C9).
- 0 duplicate `source_id` in the final corpus; 0 setids with >1 moiety post-dedup; 0 bare-element
  normalizations; chunk seams lossless (2400-char overlap byte-identical).
- Dormancy: `get_dailymed_store`/`DailyMedCorpusStore` imported nowhere live; `SourceType` has NO
  `DAILYMED`; `retriever.py`/`server.py`/`share_renderer.py` untouched; no user-facing change.

## Rebuild
```
python scripts/build_dailymed_label_corpus.py --resolve   # STEP 1: FRESH full resolve (monthly re-pull) -> label_docs.json
python scripts/build_dailymed_label_corpus.py --embed      # STEP 2: embed -> label_emb.npy (backoff on 429 TPM)
```
`--resolve` re-selects + re-fetches on the current DailyMed snapshot (pinned by
`db_published_date`). Default (no `--resolve`) reuses the prior label_docs.json's setids.

## OPEN items for founder review BEFORE B-2 Phase 2 (the 🔴 wiring)
1. **Residual missed rescues (~1 real):** `EPINEPHRINE HCL`→lidocaine+epi combo and a few
   `dropped_combo` drugs (COLISTIN→colistimethate, PERINDOPRIL ARGININE) have a US mono label
   under a DIFFERENT name that `_find_mono_reference`'s head-word anchor didn't reach. Low volume;
   the base drug is usually covered under another backbone string. A name-synonym map would close it.
2. **Danger-path is the key 🔴 risk at wiring:** the corpus carries full interactions +
   contraindications + boxed-warning text. Phase 2 MUST run the same danger-path gate as v193
   TFDA — a DailyMed safety-section doc must never present as safety *clearance*.
3. **`share_renderer.py:235` host-map** (`dailymed.nlm.nih.gov` → currently `rxnorm`) debt-(2)
   must be reconciled in Phase 2 or DailyMed citations mislabel in share OG renders vs the panel.
4. **`rxcui` still None** (keyed on moiety); per-setid rxcui needs an extra lookup — deferred.
5. **8 combo survivors / 78 drops** — listed in `label_docs.json._meta.stats.resolve_provenance`
   for a founder scan before wiring.

## Known cosmetic (pre-existing, NOT B-2)
`vector_store.py` uses `print("✅/⚠️ …")` (Rule #4 `print()` + emoji) → `UnicodeEncodeError` on a
cp950 Windows console when the store loads outside uvicorn. Does NOT affect the load or runtime
(verified under `PYTHONIOENCODING=utf-8`). Tracked in TECH_DEBT.
