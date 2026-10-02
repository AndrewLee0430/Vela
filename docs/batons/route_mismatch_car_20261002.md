# ROUTE-MISMATCH CAR — baton (opened 2026-10-02, base `69b4992`)

**Status:** STEP 1–5 read-only probe DONE (zero LLM calls, zero network); a new TECH_DEBT entry is filed
(`[HONESTY][P1 proposed · founder ratification pending]`); NOTHING built; this commit is NOT pushed and NOT deployed.
Prod = fly 262 (`/health` revision `919ca0750b8bd1b7623e219927d97c55e213156d`).
Evidence: `tests/probes/route_mismatch/` (README there). Predecessor car: `docs/batons/bp_calcium_car_20260929.md` (§12).

## §0 Founder rulings 2026-10-02 13:52 (condensed from the paste)

1. **Prod eye fly 262 ROW 1 RE-GRADED FAIL** (team review). The answer transfers IV calcium chloride (injection label) advice to an
   oral-supplement question ("avoid concomitant use of calcium chloride and calcium channel blockers"; digoxin / PTH / teriparatide).
   The cited label does not support the oral reading. **The strategy side's veto (i) detected only the CCB misreading; its "IV-chloride
   framing is a corpus caveat, not a FAIL" judgment at the fly-261 AND fly-262 gates was WRONG** — recorded so.
2. **SYSTEMIC, not chip-2:** FIX FIRST; no chip hiding (anonymous Research ≤ 3/day; the fix covers every user).
3. This car goes **AHEAD of the Verify grounded-tag car**.

## §1 STEP 1 — corpus route census (`step1_corpus_route_census.py` → `.json`; hand checks `step1_hand_verification.json`)

**Key vs text (Rule 21).** `data/dailymed/label_docs.json` docs carry NO route / dosage-form field (keys: content, source_id, title,
url, credibility, doc_type, moiety, marketing_category, setid, spl_version, rxcui, loinc, section_type). The SPL XML has the key
(`manufacturedProduct/formCode`, `consumedIn/substanceAdministration/routeCode`), but `scripts/build_dailymed_label_corpus.py`
`_section_docs_from_spl` (`:266`) keeps only names + per-LOINC text, and no SPL cache exists locally — recovering the key is a
NETWORK step (≈ 1038 setids), out of scope for this offline probe. So the LABEL route is a **text classifier**: injection vs oral
marker counts in the label's Dosage & Administration section (34068-7; all sections when absent). The ORAL-availability side uses a
**key**: `data/tfda/brand_ingredient.json` `form` (劑型) of TFDA-licensed MONO products whose ingredient set is exactly the moiety.

**Corpus:** 4608 docs · **1038 distinct setids** (the build meta's "1203 labels with sections" counts moiety×label pairs, not setids)
· **2544 whitelisted safety-section docs** (34073-7 722 · 34070-3 906 · 43685-7 632 · 34066-1 284).

| label route (classifier) | labels | safety-section docs |
|---|---|---|
| INJ_ONLY | 210 | **573** |
| MIXED_INJ_DOMINANT (inj ≥ 3× oral) | 70 | **197** |
| MIXED | 54 | 164 |
| MIXED_ORAL_DOMINANT | 34 | 100 |
| ORAL_ONLY | 447 | 1217 |
| OTHER_ROUTE (topical / ophthalmic / inhaled …) | 69 | 130 |
| NONE (no marker in D&A) | 154 | 163 |

**Injection-like safety sections: 573 + 197 = 770 of 2544 (30.3%)** — a TEXT-classifier estimate, not a key count.

**Rule 21 hand-sample (seed 20261002):** INJ_ONLY **19/20** correct (FP: Gastrocrom — oral concentrate; its only hit is the
negation "NOT FOR INHALATION OR INJECTION"); MIXED_INJ_DOMINANT **12/12**; negatives **67/68** non-injection (miss: INVEGA SUSTENNA,
IM, bucketed MIXED). **Targeted reads found 8 more classifier errors** (Nascobal = nasal → INJ_ONLY; Potassium Chloride = injection →
MIXED; Vectical = topical ointment → ORAL_ONLY; SEROQUEL / Theo-24 / pyrazinamide / COUMADIN = oral → injection-like; Ribavirin =
inhalation → INJ_ONLY) — every per-substance verdict below is HAND-verified, not classifier output.
**Rejected / weak markers (do not re-add without a negation guard):** bare `injection` (fires on "NOT FOR … INJECTION"); `oral` in a
topical label ("oral calcitriol" comparison text); comparison mentions of another route (Nascobal "IM or SC B12", Invega "oral
paliperidone"). The 2026-08-04 E-B classifier's container-token error (`TECH_DEBT.md` instrument-blind table row 10) was avoided by
not reading package text at all.

**Substances (Rule 23 key sets, hand-filtered; rejected keys listed in the JSON):**

| substance | keys (route, safety LOINCs) | verdict |
|---|---|---|
| calcium | CALCIUM (Calcium Gluconate IV) · CALCIUM CHLORIDE DIHYDRATE (IV) · CALCIUM GLUCONATE (IV) — each 34070/34073/43685 · CALCIUM ACETATE (PhosLo oral, 34070 only) · CALCIUM CARBONATE (TUMS, none) | **Interactions + Warnings text = injection-only**; the only oral safety text is PhosLo's Contraindications |
| magnesium | MAGNESIUM SULFATE HEPTAHYDRATE (inj, 34070) · MAGNESIUM OXIDE / HYDROXIDE (oral, none) | **only safety text = injection** |
| potassium | POTASSIUM CHLORIDE (inj concentrate, 34070/34073/43685) · POTASSIUM ACETATE (inj, 34070) · POTASSIUM GLUCONATE (RenaKare — veterinary, none) | **only safety text = injection**; the only oral key is veterinary (already in `docs/nonhuman_label_scope_20260804.md:49`) |
| sodium bicarbonate | SODIUM BICARBONATE (inj, 34070/34073) | **injection-only**; TFDA licenses 8 oral mono products (蘇打錠) |
| iron | IRON (Venofer IV) · IRON DEXTRAN (INFeD IV) · FERRIC CITRATE (Auryxia oral, full set) · 2 oral keys without safety | NOT injection-only |
| zinc | ZINC (zinc chloride inj, 34070) · ZINC ACETATE DIHYDRATE (GALZIN oral, 34070/34073) | NOT injection-only |
| vitamin D | CALCITRIOL (Vectical — **topical**, 34070/43685) · PARICALCITOL (Zemplar oral) · CHOLECALCIFEROL (oral, none); ERGOCALCIFEROL / CALCIFEDIOL / DOXERCALCIFEROL / ALFACALCIDOL absent | not injection — but calcitriol's only safety text is **topical** (a second route class) |
| phosphate | no phosphate-supplement key | — |

**Others the census surfaced:** of 67 moieties whose every safety-bearing label is injection-like AND that TFDA licenses orally (mono),
hand-reading removed 6 (not injection), 5 (label covers both routes), 5 (oral label under a sibling key: CEFUROXIME AXETIL,
CLINDAMYCIN HCL, ERYTHROMYCIN BASE, MORPHINE HCL, ONDANSETRON) and 2 (entity has oral safety elsewhere: iron, zinc) → **49 moiety keys
/ 47 entities** whose only corpus safety text is injection-route while a TFDA oral mono product exists. BP-relevant among them:
**FUROSEMIDE, LABETALOL HCL, NICARDIPINE HCL**; also ACETAMINOPHEN, METRONIDAZOLE, METHYLPREDNISOLONE, TRANEXAMIC ACID, ASCORBIC ACID,
THIAMINE, PYRIDOXINE. Two are **wrong-object keys** (Rule 23 class): `SODIUM CHLORIDE` → Adrenalin (epinephrine in NaCl) and `FLUORIDE`
→ Sodium Fluoride F-18 (a PET tracer). The cross-key check is first-token only — INN synonyms are not caught.

## §2 STEP 2 — saved answers, hand-read (`step2_answer_markers.py` aid; grades `step2_grades.py` → `.json`)

**Grading rule (written before tabulation):** **A** — injection-only label content (Calcium Chloride Injection's CCB-antagonism /
digoxin "during administration" / ECG items) forms advice to an ORAL question; a caveat ("the context does not address oral
supplements") does NOT lift an answer out of A (precedent: ruling 1 — the fly-262 row-1 answer carried that caveat). **B** — injection
framing stated and FENCED off from the oral answer. **C** — none. Every answer with a marker hit was read; ambiguous ones in full;
negatives read in full: 5 EN-chip zero-hit answers, 2 zh, 1 potassium, 1 iron — all C.

**149 answers: A 42 · B 5 · C 102.**

| query family | n | A | B | C |
|---|---|---|---|---|
| EN hero chip (all arms, incl. both prod smokes) | 53 | **35** | 3 | 15 |
| zh hero chip | 32 | **7** | 2 | 23 |
| bare pair "calcium and lisinopril" (pair arms + E6 Q11) | 12 | 0 | 0 | 12 |
| E6 calcium (Q1 zh, Q3 "Calcium with amlodipine?") | 12 | 0 | 0 | 12 |
| E6 potassium (Q2 / Q7 / Q12) | 14 | 0 | 0 | 14 |
| E6 iron / magnesium / vitamin D | 4 / 4 / 4 | 0 | 0 | all |
| E6 other (Q8 / Q9 / Q10) | 14 | 0 | 0 | 14 |

Per query × arm: `step2_grades.json` `by_query_arm` (e.g. 2b EN L0 7/8 A · Option-A EN L0 7/8 · fly-261 ship-bar `step7b` 5/8 · 0b
4/8 · `step8_zh_l1` 4/4 · prod smokes fly 261 and fly 262 both A).

**The (A) carrier is ONE section: `DailyMed:c4c65e48-85f8-4dcf-6281-06e40959cc79#34073-7` (Calcium Chloride — Drug Interactions),
in FINAL for 42/42 A answers** (8 of them also carried HCTZ 34073-7). **Separation is total:** that section in FINAL → A 42 · B 5 ·
C 0 (n = 47 answers); not in FINAL → C 102/102. The generator never declined it.
**Potassium:** Potassium Chloride Injection 34073-7 reached FINAL on E6 Q2 / Q7 / Q12 (14 runs), but its interaction text (K-sparing
diuretics, RAAS inhibitors, NSAIDs → hyperkalemia) is route-agnostic and no IV-specific text was carried → C, noted
`inj_label_route_agnostic`. **Iron / magnesium / vitamin D:** no injection-route safety section reached FINAL in any E6 run.
**Introduced by the fly-261 rewrite fix — consistent, not proven:** pre-fix EN traced runs carried an injection-route section in
FINAL **0/5** (`step3_trace`, `71936e8`; the miss then was the CCB misreading); on the shipped rewrite **22/31** (`step6` 2/2 · `step7`
0/1 · `step7b` 6/8 · `step8_l0` 4/8 · `step10_ctl_en_l1` 3/4 · `step11_2b_en_l0` 7/8). The rewrite's "calcium supplement …" strings
are what reach the label.
⚠️ **Domain flag:** the A/B line encodes a clinical judgment — that IV calcium's CCB antagonism and digoxin "during administration"
arrhythmia do not transfer to oral supplements, while the label's hypercalcemia drug list (incl. thiazides) is route-agnostic. A
clinician should confirm it before it becomes a gate.

## §3 STEP 3 — the FilterExempt door (`step3_exempt_door.py` → `.json`)

Whitelist condition, quoted (`api/rag/retriever.py:43-62`): `_SAFETY_SECTION_WHITELIST = {"34073-7", "34070-3", "43685-7",
"34066-1"}`; `_is_whitelisted_safety_section` returns True iff `source_type` ∈ (`dailymed`, `fda`) AND `source_id` contains `#` AND the
LOINC after it is in the whitelist. **LOINC only — no route, product, moiety or question check.** Used by `_cut_exemption` (`:65-77`,
`[CutExempt]`) and the filter exemption (`:532-543`, `[FilterExempt]`).

**Measured (18 runs-format traces, 86 runs; 57 safety sections in FINAL):** the Calcium Chloride 34073-7 section reached FINAL **42
times — LLM-kept 41, FilterExempt 1, CutExempt 0.** Injection-route sections overall: 42 in FINAL, 41 LLM-kept. **The exemption is
NOT the door: the gpt-4.1-mini relevance filter keeps the injection label on its own.** (The 7 FilterExempt re-adds in FINAL are 4 ×
HCTZ, 1 × Vasotec, 1 × ARBLI — all oral — and the 1 Calcium Chloride.) The E6 json files record FINAL only (no stage data).

## §4 STEP 4 — generator door (facts, no change)

`api/rag/generator.py:443-447` (`_build_user_prompt`): `1. Answer ONLY based on the provided context` · `2. Cite every claim with
[1], [2], etc.` · `3. If context is insufficient, state what's missing` · `4. Be clinically precise`. Rule 3 tells the model to SAY
what is missing — it does not tell it to withhold a source whose product / route does not match the question, and §2 shows it never
does. **Precedent for a source-scope rule already in this function:** the TFDA indication `SCOPE LIMIT` block (`:418-432`) — "contains
ONLY the Taiwan-approved INDICATION … You MUST NOT treat it as safety clearance". No route-scope analogue exists (Rule 19 shape: a
mitigation written for one source, not carried to another).

## §5 STEP 5 — canary coverage

**Confirmed: the canary does not measure safety queries.** `tests/probes/canary/canary_gate.py:1` — "non-safety Research queries must
NOT cite DailyMed safety sections"; its 6 queries (`:118-123`) are mechanism-of-action / efficacy. Its wrong-object criterion is
**moiety-keyed** (`tests/probes/ownership_eval/resolver.py` `resolve_key_set`), so route is invisible to it by construction:
measured offline — the EN hero chip resolves to {CALCIUM, CALCIUM ACETATE}, so Calcium Chloride would count wrong-object only by a
KEY accident while Calcium Gluconate IV (key CALCIUM) would count OWNED; "iron supplements with blood pressure medication" resolves to
{IRON, IRON DEXTRAN} — both IV-only labels, both OWNED.

## §6 Levers — facts for the founder, nothing built

1. **Retrieval:** the relevance filter (LLM-kept 41/42) — a route / product check on DailyMed sections for oral-intake questions.
2. **Generator:** a route-scope rule beside the TFDA scope limit (`generator.py:418-432`); rule 3 alone does not withhold.
3. **Corpus:** recover `formCode` / `routeCode` from the SPL at build time (network; the key exists, the builder drops it).
4. **Gate:** a safety-query canary with a route criterion — today's canary cannot see this class (§5).

## §7 Eye gate — none this segment (nothing built)
