# bp_calcium — root-cause trace of the heroChip2 Research answer (read-only)

**Query:** `Can elderly patients take BP meds with calcium?` — the landing hero chip
`heroChip2` (`utils/i18n.ts:88`, en). **HEAD** `13e56fb1858ffc4528092a7c55be284b6e9d8d4b`,
2026-09-29, local, Dev DB branch `ep-spring-voice-a127ye10`.
**Runs:** 5 full Research retrievals · 5 rewrite samples + 1 k=3 union call · 1 generation
(run 1) · 3 `/api/verify` calls · 9 embedding-only re-scores (see *Harness defect*).
**No product code, prompt, golden-set or ledger file was touched. Findings are recorded
here, NOT filed.**

## What each artifact does NOT support

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step1_corpus.py` / `.json` | corpus-only scan (0 LLM calls) of `data/dailymed/label_docs.json` + `data/tfda/indication_corpus.json` | any claim about the *live* DailyMed API Verify uses — Verify grounds on labels the Research corpus does not contain (chlorthalidone) |
| `step2_rewrite.py` / `.json` | 5 × `_rewrite_query` + 1 × `_dailymed_union_queries(k=3)` | a rate — N=5, temperature 0, and 4 of 5 runs emitted near-identical sets |
| `step3_trace.py` / `.json` | 5 real `retrieve()` calls, production config, per-stage source_ids + run-1 cosines + run-1 prompt/answer | **openFDA parity** — openFDA returned HTTP 500 on every call in every run (external). What openFDA contributes on a healthy day is **unmeasured** |
| `step3b_dm_counterfactual.py` / `.json` | embedding-only re-score of every distinct DailyMed query string from all 5 runs | anything about PubMed / openFDA / the filter |
| `step3_answer_run1.md` | the run-1 answer (gpt-4.1, authenticated path) | the anonymous L0 path, which uses the generator's fallback model |
| `step4_verify.py` / `.json` | 3 Verify calls, local TEST_MODE server | a Verify reliability rate (N=3) |
| `result.json` | the summary below, machine-readable | — |

`_harness.py` resolves production config via `tests/probes/canary/canary_gate.py
load_production_config()` (parses the `retriever = HybridRetriever(...)` block in
`api/server.py`; never a bare constructor), runs `load_dotenv()` first, blanks
`SENTRY_DSN`, and asserts the Dev DB host. The `config` block inside `step3_trace.json`
carries the canary gate's own `n_runs: 8 / min_usable_runs: 6` — those are the canary's
fields, **not** this probe's N (5).

## Findings (recorded, NOT filed)

| # | hypothesis | verdict |
|---|---|---|
| **H1** | the rewriter reads "calcium" as calcium-channel blockers | **REFUTED at rewrite.** 0/5 runs, 0/15 strings name a CCB; 5/5 runs name "calcium supplements" in exactly 1 of 3 strings; **0/5 name a thiazide or hypercalcemia**. The other 2 strings keep a bare "calcium" |
| **H8** | the data is not there | **SPLIT.** *Thiazide side ABSENT:* key set `{HYDROCHLOROTHIAZIDE, INDAPAMIDE, METOLAZONE}` — 0 of their 6 safety sections mention calcium / hypercalc / vitamin D (HCTZ's calcium text lives in PRECAUTIONS, which the corpus does not ingest — its 34073-7 only says "see PRECAUTIONS, General"); CHLORTHALIDONE and CHLOROTHIAZIDE are not corpus moieties. *Calcium side EXISTS in 5 docs:* Calcium Gluconate ×2 + Calcium Chloride (IV, 34073-7: "thiazide diuretics … may cause hypercalcemia"), Vectical calcitriol + Zemplar paricalcitol (43685-7). The **oral** supplement labels (TUMS, D-Vite) have no interaction/warning section. TFDA indication corpus: 41 thiazide docs, 0 calcium hits (expected) |
| **stage** | where the thiazide/calcium section died | **NEVER ENTERED.** 0 DailyMed docs clear the 0.6 floor on any of the 9 distinct DailyMed query strings across 5 runs. Closest: Calcium Chloride 34073-7 at **0.5919 (−0.0081)** — the doc that *does* carry the sentence; HCTZ 34073-7 at 0.5805 |
| **repro** | "2 PubMed docs, CCB, no thiazide, admits no evidence" | **REPRODUCED on run 1** — final = PMID:15927106 (antihypertensive DDIs) + PMID:3154329 (*Calcium channel antagonists Part III*); answer is entirely about CCBs; closes *"The context does not address the use of calcium supplements … no conclusion can be drawn"*. Veto (i) CCB reading **TRUE**, veto (ii) thiazide/hypercalcemia **FALSE** (regex + hand-read; judge not run). The dolomite trace-metal paper (PMID:3415787) is final in runs 3 and 5 |
| **E7** | Verify already has the capability | **YES, UNRELIABLY.** 3/3 → Moderate, `dailymed_grounded`; hypercalcemia named **1/3**, and that description itself says the label "does not explicitly describe the interaction" |

**Mechanism as measured.** The rewrite is ambiguous, not wrong. The CCB reading enters at
**PubMed**: bare "calcium antihypertensive" terms retrieve a CCB review. With DailyMed
contributing nothing (floor), TFDA nothing, and openFDA down, the pool is **100% PubMed in
all 5 runs**, and the **relevance filter is the only lossy stage** (kept 2/10, 1/15,
3/15, 0/11, 3/15; the `[:20]` cut, FilterExempt, rerank and top-k dropped nothing). The
filter judges against the same ambiguous question, so it keeps whichever reading the
pool happened to supply. The generator is instructed *"Answer ONLY based on the
provided context … If context is insufficient, state what's missing"*
(`api/rag/generator.py` `_build_user_prompt`). Hence the CCB answer and its closing
admission. Run 4 had 0 docs kept → `irrelevant` → the **no-docs fallback** prompt
(general knowledge), a different answer path on 1 of 5 runs.

## Harness defect (fail loud, Rule 18)

`step3_trace.py` re-instrumented a fresh retriever per run, but `get_dailymed_store()` is
a **singleton**, so each run wrapped the previous run's `_get_embedding` wrapper. From run
2 the chain reached run 1's already-popped `_dm_emb` key → `KeyError` → production's
fail-soft logged `DailyMed search error: '_dm_emb'` and DailyMed returned `[]` for runs
2–5 **because of the harness**. Repair without spending retrieval budget: DailyMed
search is a pure function of the query string, so `step3b` re-embedded all 9 distinct
DailyMed strings those runs issued. **0 clear the floor** → production would also have
returned `[]` → the defect changed no run's outcome. Run 1 was unaffected (6 DailyMed
queries embedded normally). A second, earlier slip: the first `step2` run executed from
this directory, so the relative-path stores loaded empty. The rewrite arm never searches
a store, so the result stands, and `_harness.py` now `chdir`s to the repo root.

## Rule 21 self-refutation — string heuristics used

- **H8 thiazide side** — moiety key = INN base at word start (`^(BASE)\b`, so
  CHLOROTHIAZIDE cannot match HYDROCHLOROTHIAZIDE) ∪ a title sweep; content marker
  `calcium|hypercalc|vitamin\s*d`. **Negatives hand-read: all 6 of 6** thiazide safety
  sections (3 × 34073-7, 3 × 34070-3) were read in full. None names calcium; HCTZ's
  only pointer is to PRECAUTIONS.
- **H8 calcium side** — key = moiety **starting** with `CALCIUM` or a vitamin-D INN.
  **Rejected** (salt-suffix / non-supplement): ACAMPROSATE CALCIUM, CALCITONIN SALMON,
  CINACALCET HCL, EDETATE CALCIUM DISODIUM, ETELCALCETIDE HCL, LEUCOVORIN CALCIUM,
  PITAVASTATIN CALCIUM, POLYCARBOPHIL CALCIUM, ROSUVASTATIN CALCIUM. **Known false
  inclusion:** CALCIUM SENNOSIDES (a laxative), which contributed 0 hits. Positives
  hand-read: all 5 sentences are printed verbatim in `step1_corpus.json`.
- **H1 rewrite** — markers per class are in `step2_rewrite.json`. **Rejected markers:**
  bare "calcium" (the query's own ambiguous word) and "antihypertensive" (names BP meds,
  not either reading). All 15 strings were hand-read; the classification matches.
- **Veto grading** — the regex `calcium[- ]channel` / `thiazide|…|hypercalc`, confirmed
  by reading the whole run-1 answer.
- **Verify** — `hypercalc` regex over the response JSON, with all 3 descriptions
  hand-read. The "valsartan + HCTZ combination" identity of setid `167f49f0…` comes from
  the model's own call-2 description and was **not independently verified** against
  DailyMed.

## Probe 2 — which layer to fix (2026-09-29, HEAD `71936e8`)

**Budget:** 0 LLM completions · 3 of 4 embedding calls (batched) · 3 of 3 DailyMed fetches
· 3 of 3 PubMed string lookups (each is esearch + **efetch**, the production path; the
brief said esummary). Summary: `step5_layer_choice.json`.

| verdict | text |
|---|---|
| **A** | NO interaction-on-target doc ever entered the pool (retrieval-side), 0/5 runs by title-level hand-read. Supplement-TOPIC docs (regex-marked) entered in 3/5 runs (7 instances, 5 distinct PMIDs); the relevance filter dropped 5/7 and kept 2 (PMID:3415787, the dolomite paper, both times) |
| **B** | if 42232-9 were in the corpus, HCTZ PRECAUTIONS clears 0.6 on **0/9** strings (best 0.5096, would-be rank 10). **Upper bound:** the calcium sentence alone clears 0/9 (best 0.4978). Chlorthalidone **unanswered** (below) |
| **C** | a disambiguated rewrite WOULD retrieve on-target PubMed docs: **YES, CONDITIONALLY**. 5 on-target of 9 returned (15 slots): 4/4 for the mechanism-naming string, 1/5 for the population string, **0 docs** for `hydrochlorothiazide calcium carbonate interaction` |

**Reading (not a ruling):** the loss is at the **query layer**. No rewrite names the thiazide
mechanism, so neither DailyMed (at any section scope) nor PubMed is asked for it. The filter
is a secondary loss that never saw an interaction doc, and adding a section does not reach
this query.

| artifact | what it does NOT support |
|---|---|
| `step5_census.py` / `.json` | abstract-level claims: step3_trace recorded **titles only**. Two title-negatives are **flagged, not cleared**: PMID:3306212 *Diuretics in the management of hypertension* and PMID:28267687 *Pharmacology of the Kidney in Hypertension* (both filter-dropped) |
| `step5_precautions.py` / `.json` | chlorthalidone. The builder's picker chose `5441e163…` *CHLORTHALIDONE TABLET [BRYANT RANCH PREPACK]* (repackager, doctype 34391-3), which has **no 42232-9** (PLR format); its 43685-7 was not scored (XML not persisted; a refetch would exceed the cap) |
| `step5_precautions_ub.py` / `.json` | a candidate doc: a single sentence the builder would never produce, a ceiling only |
| `step5_pubmed.py` / `.json` | that any rewriter would emit these strings (they are hand-written); PubMed ranking is live and will drift |
| all | a rate beyond this one query; openFDA's contribution (HTTP 500 throughout the recorded runs) |

**Rule 25:** the brief said 10 DailyMed query strings ("9 rewrites + raw"). step3b recorded
**9 distinct strings, raw included**, and 9 were used. Earlier in this session I said "6
supplement-topic instances"; the script derives **7**.

**Rule 21:** census markers are in `step5_census.json` with the rejected markers (bare
"calcium", "diuretic", "antihypertensive") and every marked doc hand-graded, plus 3 unmarked
negatives per run (title level). PubMed: all 9 returned abstracts were hand-read; grades
are in `step5_layer_choice.json`. The CCB regex fired on 2 PubMed docs that are incidental
CCB mentions.

**Harness notes:** `scripts/build_dailymed_label_corpus.py` re-wraps `sys.stdout` at import,
and the orphaned wrapper is GC-closed together with the shared buffer. `step5_precautions.py`
keeps both wrappers alive; the first attempt failed before any network call, so no budget
was spent.
