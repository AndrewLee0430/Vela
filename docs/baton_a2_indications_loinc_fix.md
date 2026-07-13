# Baton A2-typo — indications LOINC one-char fix

**Status: BUILT + §2.7-passed, NOT DEPLOYED, NOT PUSHED. Prod human-eye gate = FOUNDER-PENDING (🔴).**
CC does not self-certify prod. The founder owns deploy + push timing; this is a build record.

## The defect
`dailymed.py:41` `_LOINC_INDICATIONS = "34067-0"` was a typo for the real SPL
"INDICATIONS & USAGE SECTION" code **34067-9**. So `.indications` NEVER populated
(0/1040 in the Stage-A DailyMed corpus; live-verified: warfarin + atorvastatin both carry
34067-9, not 34067-0). Verify's `to_text()` has silently omitted the entire indications
section from the LLM context since the DailyMed integration shipped (v201).

## The fix (one char)
`dailymed.py:41` `"34067-0"` → `"34067-9"`. Nothing Baton A changed is touched
(`_section_text`, `to_text()`, the prose-cap, the honesty layer). Verify-visible
(to_text now includes indications) → 🔴, kept as its OWN small baton with §2.7 +
human-eye gate, separate from the dormant B-1 corpus rebuild.

- **Ripple (live):** warfarin `.indications` now populates (1406 chars); `to_text()`
  11399 → 12832 (+1433, pure addition); `.drug_interactions` unchanged (3933, truthy).
- **Honesty layer untouched:** the interaction-grounding section is 34073-7 (not
  indications); the tiering (`server.py:1214`) keys on `.drug_interactions` truthiness,
  the resolver on setid/tier — neither reads `.indications`.

## §2.7 Verify re-baseline (fresh code, :8000 cleared before the run)
**13 PASS / 3 WARN / 0 FAIL** (V01–V16). **No interaction VERDICT changed**; V16
warfarin+fluconazole still PASS. All 3 WARNs are judge-phrasing oscillators:
- **V03** (simvastatin+amiodarone, "CK monitoring") — documented oscillator; reverted to
  PASS on re-run.
- **V12** (lithium+ibuprofen, "renal prostaglandin inhibition") — documented persistent
  oscillator (answer states the renal-clearance mechanism correctly).
- **V07** (methotrexate+NSAID, "renal clearance reduction") — first-ever WARN, so a
  **causal test** was run: on **pre-fix code (indications absent)** V07 also flips
  PASS/WARN → the WARN is a judge oscillator, **NOT indications-caused**. V07's interaction
  verdict is Major + correctly grounded (states methotrexate toxicity + nephrotoxicity +
  increased plasma concentrations + monitoring); the judge nitpicks the exact phrase.
- **No indications-dilution regression** — the added indications is descriptive and changed
  no interaction judgment.

## Human-eye evidence (BEFORE/AFTER, for the founder's prod gate)
- **warfarin+fluconazole** (Baton-A canonical): interaction still grounds with indications
  now in context — Major, `dailymed_grounded`, CYP2C9 mechanism intact.
- **warfarin+amoxicillin**: interaction analysis unchanged (Major, `dailymed_grounded`).
- indications now appears in the label context; the interaction verdict is uncompromised.

## Levers — UNCHANGED this baton (by name)
`RETRIEVAL_REFUSAL_SHADOW` · `SOURCE_WEIGHT_SHADOW` · `SOURCE_WEIGHT_ACTIVE` ·
`DIRECTION_CHECK_SHADOW` · `QUESTION_NEUTRALIZATION_SHADOW` · locale-hint — no flag change.

## Founder next steps
1. Kill any stale local `:8000` server before the prod human-eye gate.
2. Prod human-eye: a drug's Verify card now includes indications in grounding, interaction
   verdict unchanged; warfarin+fluconazole still surfaces the CYP2C9 interaction.
3. Deploy via `deploy.ps1` after the prod gate; push at your discretion.
Commit: code+tests `18e7ee3`.
