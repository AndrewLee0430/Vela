# Baton A — Verify under-grounding fix (drug-interaction table truncation)

**Status: BUILT + §2.7-passed, NOT DEPLOYED. Prod human-eye gate = FOUNDER-PENDING (🔴).**
CC does not self-certify prod. The founder owns the deploy (`deploy.ps1`) + the STATE/PK
sync; this note is a build record, not a "shipped" marker.

## The defect (shipped v201)
Verify grounds each interaction's `description` on the DailyMed/openFDA label's interaction
section. Both sources capped that section at **char 2000**, which DROPPED the drug-interaction
**TABLE** (the label's own per-drug CYP450 enumeration) sitting past the cut → major
interactions living only in that table (e.g. **warfarin + fluconazole**) were ABSENT from
the grounding text → Verify under-warned while attribution still claimed "grounded".

## The fix (option b, both sources — ingest-and-cite, no DDI-verdict)
- `dailymed.py` `_section_text`: cap the **prose** portion (bounds runaway narrative), then
  **ALWAYS append the FULL flattened table**. Single returned string (no field-set / `to_text`
  contract change). Invariant preserved + guarded: a section with any content stays non-empty.
- `fda.py` `to_text`: openFDA sections are single prose blobs (no separable table), so the
  drug enumerations live inline. The **safety sections** (Drug Interactions, Warnings,
  Contraindications) are now passed **full**; non-grounding narrative (Indications, Adverse
  Reactions, Dosage) stays bounded via `_truncate`. Parity: the enumeration always reaches the LLM.

## Safety re-verification (Phase 0)
The v201 honesty layer — `attribution_kind` (`server.py:1002-1036`), the setid deep-link, the
frontend markers (`verify.tsx:592-625`) — keys ONLY on setid / tier / `.drug_interactions`
truthiness / the enum, **never on section content/length/"..."/shape**. So this storage
change cannot break attribution. The one dependency (present section → truthy at
`server.py:1214`) is guarded (`return combined or None`) and unit-tested.

## §2.7 Verify re-baseline (fresh code, :8000 cleared before run)
**15 PASS / 1 WARN / 0 FAIL** across V01–V16 (baseline was 14/15 over V01–V15).
- **V16 (warfarin + fluconazole) PASSES** — the new golden case that exercises the dropped
  table. It demonstrably resolves (was under-grounded on v201).
- The sole WARN, **V12 (lithium + ibuprofen)**, is a documented **persistent judge-phrasing
  oscillator** (identical "renal prostaglandin inhibition mechanism" missing-concept signature
  as the 2026-06-22 pre-Baton-A run; WARN 3/3 this session; V10 — the v201-run oscillator —
  PASSED here). Its live answer is correctly grounded (`dailymed_grounded`, Major, states the
  renal-clearance mechanism from the lithium label); the judge wants the exact word
  "prostaglandin" (the label phrases it "renal blood flow"). Causally independent of Baton A —
  un-truncation adds grounding text and cannot make a concept vanish. NOT a fresh regression;
  founder-acceptable per the R01/R20 oscillator protocol.

## Human-eye gate evidence (BEFORE/AFTER — for the founder's prod gate)
- **warfarin + fluconazole (DailyMed main path).** BEFORE (v201): warfarin's 34073-7 grounding
  text truncated 2000 chars; the CYP2C9 table (with fluconazole) dropped — proven: section
  2003 → 3933 chars, `fluconazole` absent → present. AFTER: interaction surfaces — Major,
  `attribution_kind=dailymed_grounded`, warfarin setid deep-link, description grounds on the
  CYP2C9 mechanism ("Fluconazole is a moderate inhibitor of CYP2C9…increase warfarin plasma
  concentrations").
- **openFDA fallback parity (client-level).** warfarin's openFDA `drug_interactions` = 6477
  chars (incl. the Table 2 content dropped on v201) is now **fully retained** in `to_text()`
  (not truncated). A live openFDA-fallback Verify demo needs a drug that both falls to openFDA
  and has a long interaction section (harder to pin live) — covered by the unit test
  `test_openfda_to_text_keeps_full_interaction_section`.

## Levers — UNCHANGED this baton (by name)
`RETRIEVAL_REFUSAL_SHADOW` · `SOURCE_WEIGHT_SHADOW` · `SOURCE_WEIGHT_ACTIVE` ·
`DIRECTION_CHECK_SHADOW` · `QUESTION_NEUTRALIZATION_SHADOW` · locale-hint
(`NEXT_PUBLIC_LOCALE_HINT_ENABLED`) — no flag/lever change.

## Founder next steps
1. Kill any stale local `:8000` server before the prod human-eye gate.
2. Deploy via `deploy.ps1` after the prod human-eye gate passes (🔴 medical surface).
3. Prod human-eye: warfarin+fluconazole surfaces the CYP2C9 interaction with the DailyMed
   setid deep-link; a normal pair unchanged; eyeball V12's lithium+ibuprofen answer (correct
   but judge-strict on "prostaglandin").
