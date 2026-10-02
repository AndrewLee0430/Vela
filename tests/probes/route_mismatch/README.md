# tests/probes/route_mismatch — ROUTE-MISMATCH car (opened 2026-10-02)

Read-only, OFFLINE, zero LLM calls, zero network. Inputs: `data/dailymed/label_docs.json`, `data/tfda/brand_ingredient.json`,
and the saved answers / traces under `tests/probes/bp_calcium/`. Baton: `docs/batons/route_mismatch_car_20261002.md`.

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step1_corpus_route_census.py` → `step1_corpus_route_census.json` | per-label route from a TEXT classifier over D&A text; safety sections by route; moieties whose every safety label is injection-like, with TFDA oral/injection mono-product counts (a KEY) | a key-based route (the corpus has none — see the baton §1); precision beyond the hand-sample |
| `step1_hand_verification.json` | Rule 21 hand-sample (sizes, FPs, misses), 8 targeted classifier errors + overrides, Rule 23 key sets per substance with rejected keys, the 67 → 49 reduction | how COMMONLY a substance is taken orally (TFDA licensing is the proxy); INN-synonym keys (first-token cross-check only) |
| `step2_answer_markers.py` | marker-sentence aid for the hand-read (route words + Calcium Chloride label content) | a grade — it only surfaces sentences |
| `step2_grades.py` → `step2_grades.json` | the HAND grades (A/B/C) for all 149 answers, the per query × arm table, family rates, DailyMed sections in FINAL of A answers | answers not saved (traced runs without an answer file); a clinician's A/B line (domain flag, baton §2) |
| `step3_exempt_door.py` → `step3_exempt_door.json` | per FINAL safety section: LLM-kept vs FilterExempt vs CutExempt, from saved traces | E6 stage attribution (E6 jsons record FINAL only); live behaviour at HEAD |

Re-run order: step1 → step2_grades (needs nothing from step1) → step3 (reads step1 JSONs).

## Segment 1 — the route KEY sidecar (2026-10-02, base `48416bb`; network = DailyMed only, zero LLM)

`scripts/build_dailymed_route_sidecar.py` fetched every corpus setid's SPL from the SAME endpoint the corpus builder uses and wrote
`data/dailymed/label_routes.json` (route / product-form KEY per setid; no behaviour change — nothing reads it yet).
`seg1_route_key_validation.py` → `seg1_route_key_validation.json` validates it against the STEP-1 text classifier.

| artifact | what it is | what it does NOT support |
|---|---|---|
| `data/dailymed/label_routes.json` | per setid: `routes` (SPL `routeCode`), `forms` (product `formCode` — packaging NOT read), kit `part_forms`, `spl_version`, `corpus_spl_version_match`, `document_type`, per-product detail; `_meta.failures` / `_meta.no_route` | the 21 setids DailyMed no longer serves (HTTP 404 — listed, never defaulted); content drift on the 115 setids whose CURRENT SPL version ≠ the corpus build's (the key describes the newer revision); SPL route quirks (FLUORESCITE: OPHTHALMIC on an IV dye) |
| `seg1_route_key_validation.py` / `.json` | (a) coverage · (b) key × classifier confusion + agreement + every disagreement · (c) the probe's counts re-derived on the key · (d) version drift + document types | a clinical route judgment — the route-class map (`PARENTERAL` / `ORAL` / `ORAL_MUCOSAL` / `OTHER`) is explicit and every observed route is mapped (0 unmapped), but `PARENTERAL` there means invasive non-oral (it includes intracavitary implants) |

**(a) coverage:** 1017/1038 setids carry ≥ 1 routeCode (**97.98%**); 21 fetch failures, all HTTP 404; 0 fetched SPLs without a route.

**(b) agreement (injection axis: classifier INJ_ONLY ∪ MIXED_INJ_DOMINANT vs key all-parenteral):** **2466/2544 safety-section docs (96.9%)** · **884/910 labels with safety sections (97.1%)**. Confusion (unit: safety-section docs):

| classifier ↓ / key → | INJ_ONLY | INJ_AND_ORAL | INJ_AND_OTHER | ORAL_ONLY | ORAL_AND_OTHER | OTHER_ONLY | NO_KEY | Σ |
|---|---|---|---|---|---|---|---|---|
| INJ_ONLY | 532 | · | 7 | 9 | · | 16 | 9 | 573 |
| MIXED_INJ_DOMINANT | 177 | 7 | · | 9 | · | 4 | · | 197 |
| MIXED | 9 | 47 | · | 87 | · | 13 | 8 | 164 |
| MIXED_ORAL_DOMINANT | · | · | · | 97 | · | · | 3 | 100 |
| ORAL_ONLY | · | · | · | 1122 | 8 | 59 | 28 | 1217 |
| OTHER_ROUTE | 3 | · | · | 4 | · | 118 | 5 | 130 |
| NONE | 5 | · | · | 125 | · | 31 | 2 | 163 |
| **Σ** | 726 | 54 | 7 | 1453 | 8 | 241 | 55 | 2544 |

All 26 disagreeing labels hand-read:

| # | label | classifier | key | hand verdict |
|---|---|---|---|---|
| 1 | Gastrocrom | INJ_ONLY | ORAL | key ✓ (oral concentrate) |
| 2 | LEVAQUIN | MIXED_INJ_DOM | ORAL | key ✓ for this setid's products (tablets); its text also covers IV dosing |
| 3 | INVEGA SUSTENNA | MIXED | IM | key ✓ |
| 4 | Ribavirin (SPAG) | INJ_ONLY | — 404 | no key; inhalation by hand |
| 5 | Gliadel | NONE | INTRACAVITARY | key ✓ (implanted wafer — non-oral; "parenteral" class = invasive non-oral) |
| 6 | SUPRANE | INJ_ONLY | INHALATION | key ✓ |
| 7 | Butorphanol | INJ_ONLY | NASAL | key ✓ |
| 8 | XARACOLL | OTHER_ROUTE | Parenteral (implant) | key ✓ |
| 9 | Nexplanon | MIXED | SUBCUTANEOUS (implant) | key ✓ |
| 10 | TEPADINA | INJ_ONLY | IV + intracavitary + intravesical | key ✓ — class split (INJ_AND_OTHER), non-oral either way |
| 11 | UVADEX | INJ_ONLY | EXTRACORPOREAL | key ✓ |
| 12 | Nascobal | INJ_ONLY | NASAL | key ✓ |
| 13 | ZEMBRACE SYMTOUCH | INJ_ONLY | — 404 | no key; SC injection by hand (classifier right) |
| 14 | Theo-24 | INJ_ONLY | ORAL | key ✓ |
| 15 | SEROQUEL | INJ_ONLY | ORAL | key ✓ |
| 16 | COUMADIN | MIXED_INJ_DOM | ORAL | key ✓ |
| 17 | Mycamine | INJ_ONLY | — 404 | no key; IV by hand (classifier right) |
| 18 | Prepidil | INJ_ONLY | VAGINAL | key ✓ |
| 19 | Chloramphenicol | NONE (no D&A) | IV | key ✓ |
| 20 | Lupron Depot (kit) | INJ_ONLY | IM + TOPICAL (kit part) | key ✓ — class split, non-oral either way |
| 21 | Provocholine | MIXED_INJ_DOM | INHALATION | key ✓ |
| 22 | FLUORESCITE | INJ_ONLY | OPHTHALMIC | **key MISLEADING** — SPL routeCode OPHTHALMIC on an IV dye ("500 mg via intravenous administration"); classifier right |
| 23 | Tc-99m sulfur colloid kit | MIXED_INJ_DOM | IV + ORAL + SC | key ✓ |
| 24 | OMNIPAQUE | MIXED_INJ_DOM | IV … + ORAL + RECTAL | key ✓ |
| 25 | Pyrazinamide | MIXED_INJ_DOM | ORAL | key ✓ |
| 26 | MIOSTAT | INJ_ONLY | OPHTHALMIC | key ✓ (intraocular surgical solution — non-oral either way) |

**Tally: key right 20 · key right but split across classes 2 · key misleading 1 (FLUORESCITE) · no key (404) 3.**

Off the injection axis: 23 labels the classifier called ORAL_ONLY are topical / inhaled / transdermal / rectal by the key (Exelon patch, Retin-A, PULMICORT …) — the topical-for-oral class STEP 1 met with Vectical.

**(c) re-derived on the key (Rule 25):** injection-route safety sections **726** (all routes parenteral) vs the classifier's **770** → **delta −44** (= 770 − 61 classifier-only, 9 of them no-key + 17 key-only); with ANY parenteral route: 787. Moieties whose every safety label is injection-only by key AND TFDA licenses an oral mono product: raw **58** (classifier 67) → after the probe's reductions **50** (probe **49**) → **delta +1** = **+3** CAFFEINE CITRATE, MOXIFLOXACIN HYDROCHLORIDE, RANITIDINE (the STEP-1 text read called these "label covers both routes"; the SPL's products are injection-only) **−2** METHOXSALEN, SUMATRIPTAN SUCCINATE (METHOXSALEN: route EXTRACORPOREAL, not injection — key right; SUMATRIPTAN SUCCINATE: its label ZEMBRACE is a 404, no key).

**(d) version drift:** **115** of 1017 setids' current SPL version ≠ the corpus build's (report only — the indexed text may differ from the current label).

**⚠️ CORRECTION (Rule 21 self-refutation, the key catching my own STEP-1 text read):** the STEP-1 hand override "Potassium Chloride → INJECTION concentrate" was **WRONG** — the key (SPL v11 = corpus v11) is **ORAL / SOLUTION**; the label reads "Dilute the potassium chloride solution with at least 4 ounces of cold water … Take with meals", and its "intravenous" hits are "consider intravenous therapy". So **potassium is NOT injection-only** (the oral solution carries 34070 / 34073 / 43685), and the E6 potassium answers citing it were route-MATCHED. Recorded in `step1_hand_verification.json` `_corrections`; `step2_grades.json` notes and `step3_exempt_door.json` regenerated — grades (149) and STEP-3 totals unchanged. The other 9 hand overrides: 8 confirmed by the key, 1 no key.
