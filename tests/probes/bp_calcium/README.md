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

## Segment 1 build — rewrite disambiguation, ONE variable (2026-09-29 → 30, base `0b210da`) — BUILT, GATED, **REVERTED**

**The edit:** one additive block in the `_rewrite_query` system prompt (`api/rag/retriever.py`) — "STEP 1b —
Confusable terms and class-level interactions" (supplement ≠ the drug class sharing the word; a class-level
interaction question must carry one CLASS + MECHANISM + OUTCOME query) — and the clause `(official drug names,
MeSH terms)` re-worded to `(INN names for the drugs the user NAMED, MeSH terms; never collapse a drug class into
one drug pair)`. Nothing else in the prompt changed. **Verbatim diff: `docs/batons/bp_calcium_car_20260929.md` §2.**
**Status: REVERTED** (`git checkout -- api/rag/retriever.py`, byte-identical to `0b210da`) on gate (e) below, per the
founder's rule "any regression in (c)(d)(e) → REVERT, record, STOP. Do not tune the prompt in a loop."

**Killed partial runs are NOT evidence.** On 2026-09-29 the first treatment golden (18/20 done) and canary (3.4/6
queries) runs were stopped by Claude Code for host memory pressure; their logs stay in scratch. Every treatment number
below is from the 2026-09-30 SERIAL re-runs (one harness resident at a time). Spend: `step6_spend_final.json`.

| gate | control (at `0b210da`, 2026-09-29) | treatment (edit applied, 2026-09-30) | verdict |
|---|---|---|---|
| (a) bp query — rewrites (5 runs × 3 strings) | thiazide **0/5** runs (0/15 strings) · supplement 5/5 runs (5/15 strings) · hypercalcemia 0/5 | thiazide **5/5** runs (5/15 strings) · supplement 5/5 (15/15 strings) · hypercalcemia 2/5 · a "calcium channel blockers + calcium supplement interaction" string in 2/5 (CCB as a BP-drug CLASS with the supplement — the on-target reading, hand-read) | changed as intended |
| (a) bp query — pool / FINAL (N=2 treatment; control = probe-1 run 1) | control: 0 DailyMed in pool, FINAL = 2 PubMed (one CCB review) | run 1: pool 12, **Calcium Chloride 34073-7 enters at 0.6272** (was 0.5919), FINAL = that section + PMID:38345765 (oral calcium citrate in elderly) · run 2: pool 14, Calcium Chloride 0.6272 + **HCTZ 34073-7 0.6226**, FINAL = both. On-target PubMed titles entered 3 / 5 but the filter kept 1 / 0 (CATS PMID:33178509 dropped) | the mechanism section now reaches the generator |
| (a) bp query — generation run 1 (gpt-4.1, authenticated path) | veto (i) CCB reading **TRUE** · veto (ii) thiazide/hypercalcemia **FALSE** | veto (ii) **TRUE** ("Hypercalcemia Risk: … thiazide diuretics, vitamin D, lithium … increase the frequency of serum calcium monitoring" [1]) · veto (i) **regex TRUE / hand-read FALSE, regex too coarse** — the answer opens "with calcium **supplements**"; its CCB mentions are CCBs as a BP class whose effect IV calcium chloride may blunt (from the cited label) | PASS bar met on the hand-read; the regex is the wrong instrument |
| (b) golden R01–R20, floor 18/2/0 | **18 / 2 / 0** — floor MET (R03, R20 WARN; `golden_results_20260929_195639`, 19:56 +08:00) | **20 / 0 / 0** — floor MET (`golden_results_20260930_095410`, 09:54 +08:00). Pools identical 1/20 (R13); **0 verdicts moved on an identical pool**; R03 and R20 WARN→PASS on DIFFERENT pools (R20 gained three DailyMed 34066-1 Boxed Warnings); DailyMed 17→18, PubMed 63→73 docs across the 20 FINAL pools | no breach; the two moves are attributable-by-pool, not separable from PubMed drift |
| (c) canary, 6 × N=8 | PASS · wrong-object 0/8 ×6 · old criterion (any safety) 0/8 ×6 · 48/48 usable | PASS · wrong-object 0/8 ×6 · old criterion 0/8 ×6 · 48/48 usable (the owned metformin citation seen once in the killed partial did not recur) | unchanged |
| (d) danger-path, 3 queries | 0 hard violations · 0 rechecks · exit 0 | 0 · 0 · exit 0 | unchanged |
| (e) straddle, 5 × N=2 — runs with a whitelisted DailyMed safety section in FINAL | **8/10** — warfarin+aspirin **1/2** · spironolactone 2/2 · warfarin+NSAID 2/2 · lithium+ibuprofen 1/2 · R07 2/2 | **7/10** — warfarin+aspirin **0/2** · 2/2 · 2/2 · 1/2 · 2/2 | **REGRESSION on the stated metric → REVERTED** |

**What (e) does and does not support.** N=2 per query. The control's own warfarin+aspirin pair was {2 sections, 0
sections} — the same swing the treatment shows as {0, 0}. The straddle harness does not capture rewrite strings, so
whether the 0/2 is the edit or PubMed/LLM nondeterminism is **not separable** here. The query names two INNs and no
supplement or class, so neither new clause applies to it on its face — that is a reading, not a measurement. The rule
was applied as written; **whether to re-measure that one query at N=8 on both arms (~16 retrievals, ≈ $0.05) is the
founder's call**, not a tuning loop.

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step6_treatment_rewrite.json` (`step2_rewrite.py step6_treatment`) | 5 rewrites + 1 union under the edit | a rate beyond N=5 |
| `step6_treatment_trace.json` / `step6_treatment_answer_run1.md` (`step3_trace.py --n 2 --prefix step6_treatment`, singleton re-wrap fixed) | 2 retrievals + 1 generation under the edit | the anonymous L0 path; N=2 |
| `step6_golden_{control,treatment}.json` + `step6_golden_compare.json` (`step6_compare_golden.py`) | the two `--filter R` runs and their per-case pool_identity diff; floor via the runner's own `research_golden_floor` | separating PubMed drift from the edit (rewrites not captured by the runner); the pre-top_k pool |
| `step6_canary_{control,treatment}.json` (`canary_gate.py`, output moved out of `canary/`) | the two 48-call gates, both criteria per query | — |
| `step6_danger_{control,treatment}.json` | the two 3-query danger-path runs | — |
| `step6_straddle_{control,treatment}.json` (`step6_straddle.py`) | N=2 per straddle query, production retriever | attribution (no rewrite capture); statistical power at N=2 |
| `step6_spend_final.json` (`step6_spend.py`) | `api_cost_log` SELECT since t0 = 2026-09-29T11:45:35Z, grouped by feature/model | the runner's own judge (40 gpt-4.1-mini calls, ≈ $0.03), the danger-path judge (6 calls), embeddings — all unlogged; the killed partial runs ARE included (real spend) |
| `step6_treatment.json` (`step6_collect.py`) | the machine-readable summary of everything above, derived not typed | — |

**Spend:** logged **$0.937** (gpt-4.1 generations 58 calls $0.54 · rewrites 852 calls $0.20 · filter 209 $0.12 ·
server-side judge 58 $0.05 · rerank 193 $0.03) + ≈ $0.04 unlogged ≈ **$0.98 of the US$5 cap**.

## Segment 1b — gate (e) re-measured at N=8; edit RE-APPLIED (2026-09-30, base `f38307f`)

**Founder ruling 2026-09-30:** the N=2 straddle gate had no discriminating power (the strategy side's own design error,
recorded). **Pre-registered rule, written in baton §3b before any run:** PASS iff treatment_total(40) ≥ control_total(40) − 2
AND no single query drops by more than 2 runs vs control.

| query | control8 (prompt == `0b210da`, 03:16–03:25Z) | treatment8 (baton §2 edit + `:305` docstring, 03:26–03:34Z) | drop |
|---|---|---|---|
| warfarin+aspirin | 4/8 | 4/8 | 0 |
| spironolactone | 8/8 | 8/8 | 0 |
| warfarin+NSAID | 8/8 | 8/8 | 0 |
| lithium+ibuprofen | 8/8 | 8/8 | 0 |
| R07 beta-blocker | 8/8 | 8/8 | 0 |
| **total** | **36/40** | **36/40** | **PASS** (36 ≥ 34; worst drop 0; 0 unusable runs either arm) |

`step6_straddle.py --n 8` also captured every rewrite string per run: warfarin+aspirin rewrites are INN-pair strings in
BOTH arms (neither new clause engages on a two-INN query), so the Segment-1 0/2 was drift, not the edit.

**bp query at N=8 on the re-applied prompt** (`step3_trace.py --n 8 --prefix step7b --gen-all`; retrieval + generation
each; veto (i) HAND-READ on all 8 answers per the founder's ship bar — *"does the answer answer a CCB question instead of the
supplement question?"*):

| run | DailyMed in pool | 34073-7 in FINAL | path | veto (i) hand-read | veto (ii) regex | FINAL |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | grounded | FALSE (IV-chloride framing) | TRUE | Calcium Chloride 34073-7 (FilterExempt re-add) |
| 2 | 0 | 0 | grounded | FALSE | FALSE | PMID:16199918 (CCB drug-food interactions review) |
| 3 | 1 | 1 | grounded | FALSE | TRUE | Calcium Chloride 34073-7 + PMID:38345765 (oral calcium citrate, elderly) |
| 4 | 1 | 1 | grounded | FALSE | TRUE | HCTZ 34073-7 (FilterExempt re-add) |
| 5 | 1 | 1 | grounded | FALSE (IV-chloride framing) | TRUE | Calcium Chloride 34073-7 + PMID:16199918 |
| 6 | 2 | 2 | grounded | FALSE | TRUE | HCTZ + Calcium Chloride 34073-7 + PMID:16199918 (FilterExempt re-add) |
| 7 | 2 | 2 | grounded | FALSE | TRUE | Calcium Chloride + HCTZ 34073-7 |
| 8 | 2 | 2 | grounded | FALSE | TRUE | Calcium Chloride + HCTZ 34073-7 |
| **rate** | | **7/8** | **8/8 grounded, 0 fallbacks** | **0/8 → SHIP BAR MET** | **7/8** | |

Veto (i) hand-read: every answer treats the user's "calcium" as a calcium substance (supplement / citrate / chloride) and
mentions CCBs only as a BP-drug CLASS the label says calcium blunts; none answers a CCB question in place of the
supplement question. **Caveat recorded, not filed:** 6/8 answers frame calcium primarily around **IV calcium chloride**
(the corpus's only calcium-side interaction sections are IV products — H8); runs 3 and 4 frame it as an oral supplement.
Run 2 (no DailyMed in pool) is grounded on a CCB drug-food-interaction review and names no thiazide.

**The floor-edge mechanism (why 7/8, not 8/8):** the label section enters only through specific phrasings the K=3 union
happens to draw — `calcium channel blockers calcium supplement drug interaction` → Calcium Chloride 34073-7 at **0.6272**
(runs 1, 3, 5, 7, 8); `thiazide diuretics calcium supplements drug interaction` → HCTZ 34073-7 at **0.6226** (runs 4, 6, 7, 8);
a `…supplements…` variant at 0.6212 (run 6). `…supplement interaction elderly` scores **0.5993** and the flagship
mechanism string `calcium supplement thiazide diuretic hypercalcemia risk` only **0.5646** — neither clears 0.6. This is
the recorded K-union straddle mechanism (BACKLOG DailyMed-integration entry, "cosine flips across the 0.6 line") on a
class-level query — cited, not re-filed. `[FilterExempt]` (surface iii) rescued the dropped section in runs 1, 4, 6.

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step6_straddle_control8.json` / `step6_straddle_treatment8.json` (`step6_straddle.py --n 8`, rewrites captured) | the two N=8 arms with timestamps | a rate beyond N=8; PubMed drift between arms (10 min apart) |
| `step6_straddle_compare8.json` (`step6_compare_straddle.py`) | the pre-registered rule applied; per-query rewrite-set diffs | — |
| `step7_rewrite.json` / `step7_trace.json` / `step7_answer_run1.md` | the first single-run confirm on the re-applied edit (0 DailyMed in pool → fallback) — superseded by step7b, kept as the run that surfaced the floor edge | anything rate-like (N=1) |
| `step7b_trace.json` / `step7b_answer_run1..8.md` (`step3_trace.py --n 8 --gen-all`) | 8 retrievals + 8 generations, per-run cosines and prompts | the anonymous L0 path (fallback model); a rate beyond N=8 |
| `step6_spend_seg1b.json` | `api_cost_log` since t1 = 2026-09-30T03:15:42Z | the unlogged pieces (embeddings; no judge ran in 1b) |

**Spend (Segment 1b):** $0.15 logged of the US$1 cap. pytest: see baton §3b.

## Ship readback — fly 261 (2026-10-01)

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step8_prod_smoke.py` / `step8_prod_smoke.json` / `step8_prod_smoke_answer.md` | ONE anonymous prod `/api/research` call with the hero-chip question after fly 261 (readback, not a gate): HTTP 200, citations = Calcium Chloride 34073-7, answer names no thiazide (frames calcium as IV calcium chloride vs CCBs) | the L1 path (L0 uses the generator's fallback model); a rate (N=1); the prod eye gate, which is the founder's |

## E6 mini — 12 variant queries × N=2 on the L0 path (2026-10-01, HEAD `a6d59b9` = prod fly 261 code)

**What:** generalisation + over-trigger test of the shipped `_rewrite_query` edit. Each run = the production retriever + generation on the ANONYMOUS path (`model_override = generator._fallback_model` = gpt-4.1-mini, as `api/server.py` binds L0); lang = zh-TW for CJK queries, en otherwise. `step9_e6_mini.py` (runs + regex pre-marks) · `step9_e6_mini_grades.json` (HAND grades, all 24 answers read) · `step9_e6_table.py` → `step9_e6_mini_table.md` · answers `step9_answer_Q*_r*.md`. Failure rule (founder): a query fails when either run answers a different question OR over-triggers (thiazide content on Q3/Q9/Q11); mechanism-named is reported, not gated.

| Q | query | rewrite strings (run 1 / run 2, first K=1 call) | DailyMed safety in FINAL | different question (hand) | mechanism named (hand) | over-trigger (hand) | verdict |
|---|---|---|---|---|---|---|---|
| Q1 | 鈣片和降血壓藥可以一起吃嗎 | calcium supplement antihypertensive drug interaction mechanism; management calcium supplement with blood pressure medication; calcium supplement antihypertensive agents coadministration safety / calcium supplement antihypertensive drug interaction mechanism; management calcium supplement with blood pressure medication; calcium supplement antihypertensive agents coadministration safety | 0 / 0 | n / n | n / Y | n / n | pass — the hero chip in zh-TW. r1 grounded on ONE PubMed doc (dietary calcium + calcium antagonists in SHR rats) → reads 降血壓藥 as CCBs and claims synergy; no thiazide. r2 = no-docs FALLBACK, names 噻嗪類 affecting 鈣 metabolism from model knowledge. ⚠️ 0/8 rewrite calls across both runs named a thiazide — the shipped clause's example did not transfer to the zh-TW phrasing; 0 DailyMed in either pool |
| Q2 | Can I take potassium with my BP pills? | potassium supplement antihypertensive drug interaction; management potassium supplementation blood pressure medication; potassium antihypertensive agents drug interaction / potassium supplement antihypertensive drug interaction; management potassium supplementation blood pressure medication; potassium antihypertensive agents drug interaction | 4 / 4 | n / n | Y / Y | n / n | pass — hyperkalemia with ACEI/ARB/K-sparing, 4 DailyMed safety sections in FINAL both runs — the generalisation the clause was built for |
| Q3 | Calcium with amlodipine? | calcium supplement amlodipine interaction mechanism; amlodipine calcium supplement coadministration management; calcium channel blockers amlodipine drug interactions / calcium supplement amlodipine interaction mechanism; amlodipine calcium supplement coadministration effects; calcium channel blockers amlodipine drug interactions | 1 / 1 | n / n | n / n | n / n | pass — over-trigger probe: NO thiazide content (pass). Both runs say the refs hold no calcium–amlodipine data (honest; the amlodipine 34073-7 section is in FINAL but names no calcium) — the calcium-may-blunt-CCB mechanism is not stated |
| Q4 | iron supplements with blood pressure medication | iron supplement antihypertensive drug interaction mechanism; management iron supplementation hypertension treatment; iron supplement blood pressure medication pharmacology / iron supplement antihypertensive drug interaction mechanism; management iron supplementation hypertension treatment; iron supplement blood pressure medication pharmacology | 0 / 0 | n / n | Y / Y | n / n | pass — both runs = no-docs FALLBACK (pool filtered to 0); absorption-interference / 2-h separation from model knowledge; thiazide appears only in a class list |
| Q5 | magnesium and diuretics elderly | magnesium diuretic interaction elderly mechanism; magnesium supplementation diuretic induced hypomagnesemia elderly; magnesium diuretics elderly pharmacology clinical management / magnesium depletion diuretics elderly mechanism; magnesium supplementation diuretic induced hypomagnesemia elderly; diuretics magnesium imbalance elderly pharmacology | 0 / 0 | n / n | Y / Y | n / n | pass — diuretic-induced hypomagnesemia in the elderly, grounded (PubMed) |
| Q6 | Can elderly take vitamin D with water pills? | thiazide diuretics vitamin D hypercalcemia risk; vitamin D supplementation elderly diuretic use; thiazide diuretics vitamin D interaction elderly / thiazide diuretic vitamin D hypercalcemia risk; vitamin D supplementation elderly diuretic use; thiazide diuretics vitamin D interaction elderly | 1 / 1 | n / n | Y / Y | n / n | pass — thiazide + vitamin D → hypercalcemia, 1 DailyMed safety section each; rewrite 'thiazide diuretics vitamin D hypercalcemia risk' — 'water pills' resolved to thiazides |
| Q7 | 降血壓藥和鉀離子補充劑 | antihypertensive drugs potassium supplements / antihypertensive drugs potassium supplements | 1 / 1 | n / n | Y / Y | n / n | pass — zh-TW potassium: 高血鉀 with 保鉀利尿劑 / RAAS inhibitors, 1 DailyMed safety section each; the rewriter emitted ONE string ('antihypertensive drugs potassium supplements') in all 8 calls |
| Q8 | sugar pills with BP meds | placebo effect blood pressure medication mechanism; management blood pressure with placebo control; antihypertensive drugs placebo controlled trials / placebo effect blood pressure medication mechanism; management blood pressure with placebo control; antihypertensive drugs placebo controlled trials | 0 / 0 | Y / Y | Y / Y | n / n | **FAIL** — JUDGMENT CALL: both runs commit to 'sugar pills' = PLACEBO (rewrite 'placebo effect blood pressure medication mechanism' → irrelevant → fallback) and never consider the lay sense 'sugar pills' = diabetes medication; the trailing 'if you meant something else, please clarify' is generic. Graded as answering a different question because the ambiguity is resolved silently to one reading; founder may overrule |
| Q9 | aspirin with BP medication elderly | aspirin antihypertensive drug interaction mechanism; aspirin blood pressure medication elderly management; acetylsalicylic acid antihypertensive agents elderly / aspirin antihypertensive drug interaction mechanism; aspirin blood pressure medication elderly management; acetylsalicylic acid antihypertensive agents elderly | 0 / 0 | n / n | Y / n | n / n | pass — CONTROL: ASPREE-grounded 'low-dose aspirin does not change BP with antihypertensives'; r1 adds the high-dose COX-2/renal caveat, r2 does not. No thiazide content (over-trigger pass) |
| Q10 | BP meds with grapefruit | calcium channel blockers grapefruit juice interaction; grapefruit induced blood pressure medication effects; calcium channel blocker grapefruit juice pharmacokinetics / calcium channel blockers grapefruit juice interaction; management of hypertension grapefruit juice effects; antihypertensive drugs grapefruit juice pharmacology | 0 / 0 | n / n | Y / Y | n / n | pass — CYP3A4 inhibition → dihydropyridine CCB exposure (felodipine most; amlodipine spared) — correct, grounded |
| Q11 | calcium and lisinopril | calcium and lisinopril / calcium and lisinopril | 0 / 0 | Y / Y | n / n | n / n | **FAIL** — FAIL — THE ORIGINAL HARM: both runs read 'calcium' as CALCIUM CHANNEL BLOCKERS and answer 'lisinopril vs CCBs in diabetic nephropathy' + nitrosamine contamination; the calcium SUPPLEMENT is never considered. The rewriter returned the raw string 'calcium and lisinopril' unchanged in 7 of 8 calls (one call produced proper supplement rewrites) — the confusable-terms clause did not engage on a bare 'X and Y' INN pair. No thiazide content (over-trigger pass) |
| Q12 | potassium with spironolactone | potassium with spironolactone / potassium with spironolactone | 2 / 2 | n / n | Y / Y | n / n | pass — hyperkalemia, 2 DailyMed safety sections each (the straddle family query); r2 wanders into acne / transgender monitoring cohorts but answers |

**Failure rate: 4/24 runs; 2/12 queries fail** (a query fails when either run answers a different question OR over-triggers): Q8, Q11. L0 model gpt-4.1-mini; 2026-10-01T03:03:05Z → 2026-10-01T03:09:22Z.

**Readings (hand):** (1) **Q11 is the original harm on a bare INN pair** — "calcium and lisinopril" is read as calcium-channel blockers in both runs; the rewriter returned the raw string unchanged in 7/8 calls, so the confusable-terms clause never engaged (it engages when the query has a verb/context: "take … with …", "Calcium with amlodipine?" → `calcium supplement amlodipine …`). (2) **Q1, the hero chip in zh-TW, never produced a thiazide-naming rewrite** (0/8 calls) — the clause's English example did not transfer to 鈣片/降血壓藥; run 1 was grounded on one rat-model paper (reads 降血壓藥 as CCBs), run 2 named 噻嗪類 only via the no-docs fallback. (3) Q8 "sugar pills" is resolved silently to placebo (judgment call, founder may overrule). (4) No over-trigger anywhere; potassium (Q2/Q7/Q12), vitamin D (Q6), magnesium (Q5), grapefruit (Q10) generalise correctly with the expected mechanism named.

**Does NOT support:** a rate beyond N=2 per query; the L1 (gpt-4.1) path — this is the L0 path by design; zh-TW results beyond the two CJK queries. **Spend:** $0.04 logged (rewrite/filter/rerank; in-process gpt-4.1-mini generations are not logged by the generator — ≈ $0.07 unlogged) ≈ $0.11 of the US$0.8 cap.

**E6 mini — founder re-grade (2026-10-01):** Q8 "sugar pills" re-graded **PASS-with-note** (ruling: placebo is the dominant
English sense; the diabetes reading is a zh calque). The original hand grade stays visible in `step9_e6_mini_grades.json`
(`different_question: true` + `ruled_different_question: false`) and `step9_e6_mini_table.md` now prints both rates:
**strict 4/24 runs · 2/12 queries (Q8, Q11)** · **ruled 2/24 runs · 1/12 queries (Q11)**. ⚠️ **Q1 is still a hero-chip miss
regardless of the rate** — the zh-TW phrasing produced 0/8 thiazide-naming rewrite calls and the grounded run named no
mechanism; it is NOT the shipped chip string (`utils/i18n.ts:499` = `老人血壓藥可以跟鈣片一起吃嗎？`), which Segment 1c
measures directly (`step8_zh_*`).

## Segment 1c — L0 binding + the shipped zh-TW chip (2026-10-01, read-only)

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step8_l0_trace.json` / `step8_l0_answer_run1..8.md` (`step3_trace.py --n 8 --prefix step8_l0 --gen-all --l0`) | EN hero chip on the anonymous binding (gpt-4.1-mini), retrieval + generation ×8 | the L1 path (measured in Segment 1b); a rate beyond N=8 |
| `step8_zh_l0_*` / `step8_zh_l1_*` (`--query "老人血壓藥可以跟鈣片一起吃嗎？" --lang zh-TW`, N=4 each) | the SHIPPED zh-TW chip string (`utils/i18n.ts:499`) on L0 and on gpt-4.1 | other locales; a rate beyond N=4 |
| `step8_grades.json` | HAND grades for all 16 answers + the three verdict lines | — |
| `step6_spend_seg1c.json` | `api_cost_log` since t3 = 2026-10-01T03:15:12Z | the unlogged in-process generations |

**Verdicts:** `EN chip L0: veto (i) 6/8 FALSE · veto (ii) 5/8 · grounded 8/8` (original harm 2/8 on the anonymous path) ·
`zh-TW chip: L0 veto (i) 4/4 FALSE, veto (ii) 3/4 · L1 veto (i) 4/4 FALSE, veto (ii) 4/4` (thiazide-naming rewrites 0/22 and
0/28 — the clause does not transfer to zh). STEP 2d (rewriter passthrough) and the full tables: baton §9.
