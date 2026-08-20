# `ownership_eval/` — ownership-anchored retrieval eval harness, v1

The 前置 instrument for 主線 A #1 (reserved-seat measurement). BACKLOG entry:
"Ownership-anchored retrieval eval harness (offline, key-derived qrels)".

## Scope (founder ruling 2026-08-20 — hard)

- **DailyMed store ONLY** (TFDA = v1.5 — needs its own key via `drug_name` /
  `brand_ingredient.json`, post the TFDA snapshot re-pull).
- **Raw arm ONLY** — the query goes straight to the store; **no LLM rewrite**.
  The rewrite arm has no freeze facility (temperature=0, no seed, no cache), so
  rewrite-arm measurement is N≥3-with-a-band territory — out of v1.
- **Pool-level metrics ONLY** (citation/rerank level = v2).
- **Zero LLM calls.** The only paid call is the query embedding inside the
  store's own `search()` (memo-wrapped: exactly one per distinct query,
  shared between the pool search and the full-corpus scan).
- **Never constructs `HybridRetriever`** — calls
  `get_dailymed_store().search(q, n_results, min_score)` directly
  (`api/database/vector_store.py:60-123`), the real production pool code path.
- `min_score` / `n_results` are **parsed from the production source at
  runtime** (`api/server.py` + `api/rag/retriever.py`, cross-checked); the
  harness contains no hardcoded 0.6/5 and stops loudly on mismatch.

## Ground truth — key-derived, never hand-labeled (Rules 21/23)

- `relevant` = `doc.moiety ∈ the query's key set`.
- `wrong_object` = `doc.loinc ∈ _SAFETY_SECTION_WHITELIST` (IMPORTED from
  `api/rag/retriever.py`, never copied) AND moiety outside the key set.
- `other` = everything else; never counted against.
- Key sets merge ONLY by keys: the explicit alias table (seeded
  `{ASPIRIN, ACETYLSALICYLIC ACID}`), shared `setid`, shared non-empty
  `rxcui`. **No salt-suffix normalization** (Rule 23: STATIN→NYSTATIN).
  Measured on the shipped corpus: `setid` and `rxcui` merge NOTHING —
  `rxcui` is empty in **all 4,608 docs** — so the alias table is the only
  live multi-key source today. Salt/ester/hydrate keys surfaced by the
  self-refutation block (`moiety_contains_key_but_wrong_object`) are
  **candidate alias entries pending founder rulings** (the IBUPROFEN LYSINE
  precedent); they are listed, never auto-merged.
- The labeler never reads `content`/`title` — mention is not ownership
  (`tests/probes/wrongdrug/owner_assertion.py`, Constraint 1). Guarded by
  `tests/test_ownership_eval_labels.py` (DB-free; mutation-tested: a
  substring labeler fails all four tests).

## nDCG note

`ndcg5` uses a TWO-level gain (relevant=1, else 0); IDCG over
`min(5, R_corpus)` where `R_corpus` = owned docs in the whole corpus.
A three-level gain (owned > same-class > wrong-object) **awaits a class
key** — there is none in the corpus, and inventing one from strings is the
exact Rule-23 hazard this harness exists to avoid.

## Smoke gate — raw-arm encoding (corrected 2026-08-20)

The baton phrased the WD01 gate as "ACECLOFENAC in pool" — that is the
FULL-PIPELINE observation (rewrite arm; the recorded 12/12). On the raw arm
the record itself says the opposite, and the harness reproduces the record
to four decimals: **0/4608 docs ≥ 0.6** for the WD01 query (recorded
`docs/c2_phase1b_measurement_20260804.md:214`, re-confirmed 2026-08-06) →
the raw pool is EMPTY; **ACECLOFENAC — Contraindications is the corpus
top-1 overall, below the floor** (0.5787 — the doc the rewrite arm lifts
into the pool); **DURLAZA — Contraindications ≈ 0.4031 / rank 500**
(TECH_DEBT "#13 probe" note). The gate asserts those three recorded facts.

## Seat + interception offline measurement (`seat_v1.json`, 2026-08-20)

Founder ruling 2026-08-20: **salt/ester aliases are NOT merged** — a FOURTH label
`salt_sibling` shows how much of the 35% they are. Suffix list used (FIXED, 17 —
feeds only the label, never a merge): SULFATE, SULPHATE, HYDROCHLORIDE, HCL,
SODIUM, POTASSIUM, CALCIUM, MONOHYDRATE, DIHYDRATE, ACETATE, PROPIONATE,
UNDECANOATE, TARTRATE, MALEATE, CITRATE, MESYLATE, DEXTRAN. Whole-token match
after stripping the DOC moiety's trailing suffix tokens — METHYLTESTOSTERONE is
NOT a sibling of testosterone (negative-tested, `tests/test_seat_measurement.py`).

Rates over the same 100 sampled queries (`seat_measurement.py` → `seat_v1.json`):

| variant | owned | MRR | wrong_obj | salt_sib | empty | nDCG@5 | mean pool |
|---|---|---|---|---|---|---|---|
| S0 (baseline)   | 0.65 | 0.6017 | **0.34** | **0.02** | 0.24 | 0.3729 | 2.05 |
| S1 (floor seat) | 1.00 | 0.8832 | 0.34 | 0.02 | 0.00 | 0.7031 | 3.67 |
| S2 cap=1        | 1.00 | 0.8832 | 0.34 | 0.02 | 0.00 | 0.4867 | 2.44 |
| S2 cap=2        | 1.00 | 0.8842 | 0.34 | 0.02 | 0.00 | 0.6056 | 3.00 |
| I1 (intercept)  | 0.65 | 0.6500 | 0.00\* | 0.02 | **0.33** | 0.3891 | 1.44 |
| S1+I1           | 1.00 | 0.9883 | 0.00\* | 0.02 | 0.00 | 0.7494 | 3.06 |
| S2c1+I1         | 1.00 | 0.9883 | 0.00\* | 0.02 | 0.00 | 0.5197 | 1.83 |
| S2c2+I1         | 1.00 | 0.9900 | 0.00\* | 0.02 | 0.00 | 0.6514 | 2.43 |

\* **Circularity guard (Rule 17): I1's rule IS the labeler's rule, so
wrong_object→0 under I1 is tautological at pool level.** Non-tautological and
reported in the JSON: the full list of the **61 docs I1 removes** (34 queries) for
human judgment; **9 pools become EMPTY under I1 alone** (0.24→0.33 — interception
without a seat destroys coverage); the seat metrics, which are independent of the
labeler. Displacement: S1 and S2c1 displace NOTHING; S2c2 displaces **5 docs — 4
wrong_object + 1 salt_sibling, zero relevant** (seats evict junk, not signal).

**Entity-resolution honesty:** the sim assumes the query drug is KNOWN (true by
construction — we generated the queries). A production seat needs a resolver from
free-text query → key set; **that resolver's miss rate is the residual
wrong-object rate in production.** Deliberately not quantified (out of scope).

**The 35% split:** 34% wrong_object + 2% salt_sibling (per-query flags; one query,
Q086 testosterone, has both — hence 34+2 > 35). Only **3 salt_sibling docs total**
(IRON DEXTRAN; TESTOSTERONE PROPIONATE/UNDECANOATE): the salt/ester family is a
SMALL slice of the 35%, not its bulk. Asymmetry found (letter-of-the-rule): the
strip applies to the DOC moiety only, so 6 pool docs under salt-suffixed QUERY
drugs (e.g. CEFTRIAXONE under "ceftriaxone sodium") are same-substance by
symmetric strip yet stay wrong_object — listed in
`self_refutation.query_side_strip_asymmetry`, not relabeled.

**WD01 gate corrections (deviations from the baton, diagnosed before encoding):**
(a) at cap=1 the seat legitimately goes to DURLAZA — **Drug Interactions**
(34073-7, 0.4118 / rank 388 — the v1 record's own `best_corpus_relevant_safety`),
NOT Contraindications (34070-3, 0.4031; gap 0.0087) — "Contraindications must
appear under S2" is UNSATISFIABLE at cap=1; asserted for S1 and cap=2, measured
and reported at cap=1. The seat lifts the best-SCORING owned safety section, not
the asked-about section. (b) Re-embedding is not bit-deterministic: 5 pool scores
drifted (max 0.0013). The S0 gate asserts membership/order/labels/metrics EXACTLY
and bounds score drift at 0.01, recording both values per drifted doc.

**Coverage half:** 127/1,037 corpus key sets own ZERO whitelisted safety docs —
no seat can help those. Sampled queries with zero: 0 — **by construction** (v1
eligibility required ≥1), not a discovery.

## Files

| file | role |
|---|---|
| `build_query_set.py` | deterministic query-set builder + the key-based labeler |
| `query_set_v1.json`  | seed 20260820 · 100 (drug, template) pairs over 910 eligible drugs |
| `run_eval.py`        | the runner — writes `result_v1.json` (the evidence) |
| `result_v1.json`     | per-query pools + aggregates + smoke + self-refutation |
| `render_report.py`   | `report_v1.html` is a RENDER of the JSON, nothing else |
| `seat_measurement.py` | offline seat/interception sim over `result_v1.json` (zero LLM; ~103 embeddings) |
| `seat_v1.json`       | per-variant pools + aggregates + displaced + removed + smoke + self-refutation |

## Re-run

```bash
python tests/probes/ownership_eval/build_query_set.py   # deterministic (seed in JSON)
python tests/probes/ownership_eval/run_eval.py          # ~103 embedding calls, no LLM
python tests/probes/ownership_eval/render_report.py
```

Requires `.env` with the embedder key (same convention as
`tests/probes/c2/_c2_ab_retrieval.py`). Re-running reproduces the pools
exactly IF the embedder returns identical vectors for identical input;
the committed JSON is the evidence for the recorded numbers either way
(Rule 20 / the probes README).
