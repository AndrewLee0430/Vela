# Pair-aware retrieval probe — CHECKPOINT (session aborted for power loss, 2026-07-27)

> **Promoted from `tests/results/pair_aware_probe_CHECKPOINT.md` (2026-07-27).** `tests/results/`
> is gitignored, so the complete-and-decisive M2 result existed on a single laptop that had
> already lost power once. Same precedent as the b1 build notes. This file is the durable copy;
> it will be **superseded in place** by the finished report once M1 has been re-run in full.

**Status: INCOMPLETE. This is not the deliverable.** The deliverable
(`tests/results/pair_aware_retrieval_probe_REPORT.md`) was never written and must not be
inferred from this file. **No recommendation is recorded here** — M1 decides whether the
residual exists at all, and M1 did not produce a result.

---

## ⚠️ M1 INCOMPLETE — ABORTED FOR POWER LOSS. DO NOT READ AS A BASELINE.

**M1 must be RE-RUN IN FULL, IN A SINGLE SESSION.** The live-API sample has to sit inside one
time window: PubMed/FDA results and `_rewrite_query` (gpt-4.1-mini, non-deterministic even at
the shipped `temperature=0`) both drift across sessions. A split window would reintroduce
exactly the live-API drift confound this probe exists to measure, and would silently
contaminate the RESOLVED / PARTIAL / STILL-MISSING split that is the decision artifact.
Do **not** stitch a resumed run onto the aborted one.

### Abort state

| | |
|---|---|
| Harness | `tests/results/_pairaware_m1.py` (N=8, `SOURCE_WEIGHT_ACTIVE=true`, `max_results=5`) |
| Run started | **2026-07-27 12:18:52** |
| Last completed run | **2026-07-27 12:39:57** |
| Runs completed | **86 / 120** |
| Killed | manually (background shell `b5xud81sl`), battery |

### ⚠️ Correction to the abort figure

The kill instruction cited **31/120**. That number came from my last status message and was
already stale when written — the run continued while I worked on M2. The **actual** count at
kill was **86/120**, verified from the run log (`grep -c 'Final:' tests/results/_pairaware_m1_run.log`).
Recording the measured number, not the quoted one.

### Runs completed per query (from `_pairaware_m1_run.log`)

| Query | Runs completed | Of |
|---|---|---|
| warfarin aspirin bleeding risk interaction | 8 | 8 |
| amiodarone digoxin interaction toxicity | 8 | 8 |
| spironolactone potassium hyperkalemia contraindication | 8 | 8 |
| warfarin NSAID bleeding interaction | 8 | 8 |
| ACE inhibitor potassium hyperkalemia interaction | 8 | 8 |
| digoxin diuretic hypokalemia toxicity interaction | 8 | 8 |
| SSRI NSAID bleeding risk interaction | 8 | 8 |
| warfarin fluconazole interaction bleeding INR | 8 | 8 |
| lithium ibuprofen interaction toxicity | 8 | 8 |
| What are the contraindications for using beta-blockers? | 8 | 8 |
| **M4 canary** metformin mechanism of action | **7** | 8 |
| **M4 canary** statin mechanism of action pharmacology | **0** | 8 |
| **M4 canary** GLP-1 減重機轉 | **0** | 8 |
| **M4 canary** statin primary prevention efficacy | **0** | 8 |
| **M4 canary** SGLT2 inhibitor cardiovascular outcomes | **0** | 8 |

### ⚠️ The 86 completed runs produced NO usable artifact

`_pairaware_m1.py` writes its JSON only **after** all queries *and* all canaries finish
(`OUT.write_text(...)` at the end of `main()`). The abort happened during the canary block, so
**no N=8 JSON was written and the per-run data was in memory and is lost.** All 10 safety
queries finishing 8/8 does **not** mean their results survived — they did not.

**The only `pairaware_m1_*.json` on disk is `pairaware_m1_20260727_121342.json`, which is the
N=1 SMOKE run** (written 12:17, before the N=8 run started). It is a single run per query and
is **not** a baseline either. Do not mistake it for M1.

**Fix before the re-run:** make the harness persist per query (write/append after each query
completes) so an interrupted run keeps the runs it paid for. As written, the N=8 re-run is
all-or-nothing across ~30 min of live API.

---

## ✅ M2 — COMPLETE AND VALID (offline; unaffected by the abort)

Artifacts: `tests/results/pairaware_m2_detector.json` · `tests/results/pairaware_m2_golden_fp.json`
Scripts: `_pairaware_m2_detector.py` · `_pairaware_m2_golden_fp.py`

### Verified code facts

- **`detect_brands_in_text` is double-CJK-gated** — BACKLOG's claim holds, and is stronger than
  stated: the **input** gate is `api/services/tfda_lookup.py:268` (`if not text or not has_cjk(text): return []`),
  and the **index** itself is filtered to CJK keys at `api/services/tfda_lookup.py:248`
  (`if len(k) < MIN_DETECT_KEY_LEN or not has_cjk(k) or k in GENERIC_CLASS_TERMS: continue`),
  built from the TFDA `by_name` + `by_stem` tables (`:246-247`). `_CJK_RE` at `:44`, `has_cjk` at `:75`.
  It cannot reach an English generic under any input.
- **Verify is structured, Research is free text** — `VerifyRequest.drugs: list[str]`
  (`api/models/schemas.py:178`) vs `ResearchRequest.question: str` (`api/models/schemas.py:36`).
  The recall-miss lives on Research free text, so a pair-aware lever needs a detector Vela does not have.
- `_annotate_research_question` (`api/server.py:695`) is a **no-op on English** (`has_cjk` gate at
  `:706`) — English pair queries reach retrieval byte-identical.

### Detector asset inventory

| Asset | Coverage | English-generic capable | Where |
|---|---|---|---|
| **DailyMed corpus `moiety` index** | **1038 moieties**, 910 with ≥1 safety section, 1479 indexed tokens | **YES** — the only viable backing asset | `data/dailymed/label_docs.json` (`moiety` field) |
| `data/tfda/brand_ingredient.json` | 17,824 `by_name` / 15,877 `by_stem`; all have an `english` field | **NO** — the `english` values are *product* names (`SODIUM BICARBONATE TABLETS "F.Y."`, `LIHONYU`, `PILU OINTMENT`), not clean generics | `data/tfda/` |
| RxNorm | n/a | Yes, but **network** (`https://rxnav.nlm.nih.gov/REST`, `api/data_sources/rxnorm_client.py:15`) — not deterministic-offline; adds latency + an external dependency | Explain path |
| Drug class terms (NSAID / SSRI / ACE-inhibitor / diuretic / beta-blocker) | **0** | — | **exist in NO asset**; **5 of the 10 canonical queries name a class** |

### Measured detector performance — the two numbers disagree, and that is the finding

Detector = moiety-index entity match + class-term list, `≥2 entities`, with an interaction-intent gate.

**(a) On the 8 probe-authored canonical queries** (`_pairaware_m2_detector.py`):

| Config | Recall | FP rate | Precision |
|---|---|---|---|
| no intent gate | 6/10 | **10/14 = 71%** | 38% |
| **with intent gate** | 6/10 | 0/14 = 0% | 100% |

An intent gate is **mandatory** — without one the detector fans out on 71% of non-pair queries.

**(b) On the 35 curated `research` cases in `tests/golden_dataset.json`** — authored for a
different purpose, so it cannot flatter this probe:

| | |
|---|---|
| true pair-interaction queries | **3** (R12, R13, TB03) |
| detector fired (TP) | **0** → **RECALL = 0%** |
| false fires (FP) | **0 / 32** → **FP RATE = 0%** |
| correctly silent (TN) | 32 |

**The detector is silent on every genuine pair-interaction query in the independent corpus.**

Why each was missed:

| Case | Query | Miss reason |
|---|---|---|
| **R12** | `is it ok to give both blood thinners at the same time` | **0 drug names in the text.** No name-matching detector can ever reach this. |
| **R13** | `warfarin 和 aspirin 一起用 safe 嗎` | Both drugs **found** (`WARFARIN SODIUM`, `ASPIRIN`), but intent is Chinese (一起用) — the English INTENT list misses it. |
| **TB03** | `太田胃散和warfarin一起吃安全嗎` | 1 entity only — zh-TW brand + English generic needs the TFDA table **and** the moiety index together. |

The 6/8 figure comes from probe-authored English keyword-dense strings
(`"...bleeding risk interaction"`) that match the INTENT list by construction. **The canonical 8
are not representative of real user phrasing.** Any recall claim based on them is inflated.

### ⚠️ M2 FRAMING FINDING — RECORD ONLY, DO NOT ACT ON

**2 of the 3 real pair-interaction questions (R13, TB03) are CJK or mixed-script, not English
generic pairs.** This **contradicts the framing in `BACKLOG.md:780`**, which separates the
surfaces as *"TFDA = zh-TW brands the detector DOES fire on; English DailyMed pairs it does
NOT"* and concludes *"one routing mechanism does NOT serve both"*.

On the only independent evidence available, the observed pair questions are **CJK-intent or
mixed-script**, so an English-generic-only detector would not have addressed them either.
Whether this generalises is **unknown** — n=3, from a curated eval set, not production traffic.
**Not acted on. Flagged for founder sequencing.**

### M2 limitations (stated, not papered over)

- The FP corpus in `_pairaware_m2_detector.py` (14 queries) is **self-authored** and therefore
  weak evidence; the golden-corpus measurement above exists precisely because of that.
- **n=3 true pair queries** is a very small denominator. A real precision/recall estimate needs
  **production query data (PostHog)**, which this probe did not access.
- The `is_pair_interaction` labels on the golden corpus are **my hand-labels**, recorded in
  `_pairaware_m2_golden_fp.py` (`PAIR_TRUE = {"R12","R13","TB03"}`) so they can be disputed.

---

## ✅ Structural ceiling — COMPLETE AND VALID (offline)

Artifact: `tests/results/pairaware_ceiling.json` · Script: `_pairaware_ceiling.py`

Before any live run, the corpus bounds what pair-aware retrieval *could* recover:

| Query | Ceiling | Note |
|---|---|---|
| amiodarone_digoxin | **PARTIAL-CEILING** | **`AMIODARONE` is absent from the entire 1038-moiety corpus.** No retrieval change can surface a document that does not exist. |
| warfarin_aspirin | BOTH-REACHABLE | …but **only via `ACETYLSALICYLIC ACID`**. The `ASPIRIN` moiety entry carries only indications (34067-9) + dosage (34068-7) — **no safety sections**. A detector keyed on "aspirin" needs a synonym map to reach it. |
| spironolactone · r07_betablocker | SINGLE-REACHABLE | single-drug queries, not pairs |
| warfarin_nsaid · ace_potassium · digoxin_diuretic · ssri_nsaid · warfarin_fluconazole · lithium_ibuprofen | BOTH-REACHABLE | |

Corpus: 4608 docs · 1038 moieties · 910 with ≥1 safety section · scope =
*"mono-ingredient TFDA moieties → NDA-preferred US reference label"*.

---

## Verified pipeline map (Step 0.5) — carry into the report

`api/rag/retriever.py` unless noted. Prod call site: `api/server.py:816`, **`max_results=5`** (`:818`) → **top_k = 5**.

| Stage | Ref |
|---|---|
| `retrieve()` entry | `:130` |
| Step 1 rewrite → 3 queries | `:167` (def `:288`) |
| Step 1b **K-union (lever 1)**, DailyMed-only, `k=3` | `:174` (def `:386`); k× `_rewrite_query` in **parallel** `:394`; dedup-union `:397-401`; **raw-query augment** `:402-403`; source_filter guard `:175` |
| Step 2 fan-out — non-DailyMed use the K=1 set (no pool inflation) | `:178-190` (local `:181`, pubmed `:183`, fda `:185`, tfda `:187`, dailymed×union `:188-190`) |
| Step 3 dedup by `source_id`, keep max relevance | `:207-213` |
| Step 4 year boost | `:218` (def `:532`) |
| Step 5 sort + candidate cut `[:max_results*4]` = `[:20]` | `:221-222` |
| **Lever 2 cut-exemption** (additive, append-only) | `:227` (def `:65`); `_is_whitelisted_safety_section` `:51`; 4-LOINC whitelist `:44-48` |
| Step 6 relevance filter | `:234` (def `:442`) |
| Step 7 rerank (`Reranker(top_k=8)` at `:124`) | `:248` |
| Composite reorder over the FULL pool when `SOURCE_WEIGHT_ACTIVE` | `:269-271`; fail-loud inert warning `:261-268` |
| `_collapse_subchunks` (sub-chunks only; distinct sections stay separate) | `:279` (def `:550`) |
| Final cut `documents[:max_results]` | `:282` |
| DailyMed store — **local NumPy index**, query-embedding + cosine, `min_score=0.6` | `_search_dailymed` `:610`; `get_dailymed_store()` `api/database/vector_store.py:244`; threshold `:95`/`:102` |

**M3-relevant fact already established:** DailyMed search is a **local** vector search (1 OpenAI
embedding call + CPU cosine). A DailyMed-scoped pair fan-out therefore adds **zero PubMed/FDA
external rate-limit exposure** — but this has **not** been converted into the measured latency /
displacement numbers M3 requires.

---

## Still to run

1. **M1 — full re-run, single session, N≥8.** Nothing from the aborted run is reusable.
   Persist per query first.
2. **M3 — displacement.** Harness is written (`_pairaware_m3_displacement.py`, 3 queries,
   deterministic composite-top-5 with-vs-without method mirroring `_kunion_gate.py:99-113`)
   but **has never been executed**. No displaced doc types have been named.
3. **M4 — R15 baseline, N≥3** on HEAD via `uv run python tests/run_golden_tests.py --filter R15`.
   **Not started.** The M4 canary sweep is also incomplete (see the per-query table).

## No recommendation

BUILD / CLOSE-INADEQUATE / RE-SCOPE is **not** recorded, and must not be inferred from the M2
and ceiling findings alone. **M1 decides whether the residual exists at all.**

---

## Probe scripts written this session (throwaway, `tests/results/`, product code untouched)

`_pairaware_ceiling.py` · `_pairaware_m1.py` · `_pairaware_m2_detector.py` ·
`_pairaware_m2_golden_fp.py` · `_pairaware_m3_displacement.py` (unrun)

**READ-ONLY honoured:** no `api/`, `utils/`, `components/`, prompt, flag, or config file was
modified at any point in this session.
