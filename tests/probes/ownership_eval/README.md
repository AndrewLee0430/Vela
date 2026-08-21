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

## Seat SURVIVAL to the answer (`seat_v2.json`, 2026-08-21)

seat_v1 measured **pool membership only**. v2 asks whether a seated doc reaches
the answer, stage by stage across `retriever.py:208-292`.

### ⚠️ v2 could NOT be built from seat_v1.json alone

seat_v1 is **DailyMed-only, raw-arm**. The post-pool stages operate on the
**multi-source merged** pool (PubMed + FDA + TFDA + DailyMed). Replaying stages
over a DailyMed-only pool of ≤5 docs would mean the `[:max_results*4]` = `[:20]`
cut **never binds**, reporting a falsely optimistic "the seat always survives".
v2 therefore performs **real multi-source retrieval** per query and reuses
seat_v1 only for the query set and the seat definition.

**Method — option (a), declared:** stages 3 and 4 are **REAL model calls**, on a
rule-based subset (**every 5th qid** of the sorted 100 → N=20; zero-seat queries
**retained as controls**). Retrieval runs once per query and is reused across all
8 variants. **Cost: 527.9s, 400 LLM calls** (80 rewrite incl. the k=3 union
fan-out, 160 filter, 160 rerank).

**Mirror caveat:** the stages are a mirror of `retrieve()`, not `retrieve()`
itself. Every stage with a real function calls it — `_apply_year_boost`,
`_cut_exemption`, `_filter_by_relevance`, `rerank`, `rank_by_composite_v1`,
`_collapse_subchunks`; only dedup/sort/slice arithmetic is mirrored line-for-line.
This is the TECH_DEBT #8 instrument-blindness class, unavoidable without
instrumenting `api/`, and declared rather than hidden.

### Stage survival (P0 — the honest S1, no protection)

| stage | owned | wrong_obj | salt | mean size | seats surviving |
|---|---|---|---|---|---|
| 0 seeded pool | 0.95 | 0.55 | 0.05 | 18.9 | 24/24 |
| 1 dedup+boost+sort+cut `[:20]` | 0.95 | 0.55 | 0.05 | 11.1 | 24/24 |
| 2 `_cut_exemption` | 0.95 | 0.55 | 0.05 | **11.3** | 24/24 |
| 3 LLM relevance filter | 0.95 | 0.55 | 0.05 | 4.7 | **24/24** |
| 4 rerank + composite + collapse | 0.95 | 0.55 | 0.05 | 4.7 | 24/24 |
| 5 final `[:max_results]` | 0.90 | 0.55 | 0.05 | 3.85 | **22/24** |

### 🔑 THE ANSWER TO THE ":292 QUESTION" — the hypothesis is REFUTED

The premise was: a seated doc carries a below-floor score, sorts last, and the
cuts take from the tail, so it "almost always dies at :292".

**The sort prediction is right; the survival conclusion is wrong.** On raw cosine
ordering **20 of 27 seat-positions (74%) fall outside the top-5** — exactly as
predicted. But only **4 of 27 fall outside `[:20]`**, and **22/24 seats still
reach stage 5 with NO protection at all.**

Two reasons, both structural:

1. **`Reranker.rerank` OVERWRITES `relevance_score`** with its own 0–100/100 score
   (`api/rag/reranker.py:248`) and re-sorts. The seated doc's below-floor cosine is
   **erased at stage 4**, so `:292` slices the *reranked* order, not the cosine
   order. "Sorts last by cosine" and "cut at :292" are simply not the same claim.
2. **The protection already exists in production.** `_cut_exemption` (`:237`) and
   the filter exemption (`:518-529`) both re-add whitelisted-safety docs that the
   `[:20]` cut and the LLM filter dropped. A seated doc **is** a whitelisted safety
   doc by construction, so both levers protect it for free — visible above as
   stage 2 *growing* the pool (11.1 → 11.3) and stage 3 keeping 24/24 seats while
   shrinking the pool from 11.3 to 4.7. **S1 is not unshippable; the exemption the
   baton hypothesized would be needed is already there.**

### Protections at stage 5, and what they displace

| variant | owned | wrong_obj | salt | size | seats | displaced (stage4→5) |
|---|---|---|---|---|---|---|
| P0 none | 0.90 | 0.55 | 0.05 | 3.85 | 22/24 | 17: 7 wrong · **6 relevant** · 4 other |
| P1 cut-exempt | 0.95 | 0.55 | 0.05 | 3.7 | 23/24 | 16: 9 wrong · 2 relevant · 5 other |
| P2 cut + slot (cap 1) | 0.95 | **0.50** | 0.05 | 3.7 | **24/24** | 18: 10 wrong · 2 relevant · 6 other |
| P3 floor-normalized | 0.95 | 0.55 | 0.05 | 3.7 | 23/24 | 18: 10 wrong · 2 relevant · 6 other |

**P3's normalization** rewrites the score of **seated docs only** to
`min(above-floor pool score) − 1e-6·rank`, preserving order among seats. No
non-seated doc is touched and `min_score`/`local_threshold` are unchanged, so it
is a sort-position change, not a threshold change. ⚠️ **P3 can only affect stages
1–2** — the reranker erases its effect at stage 4, which is why P3 and P1 land
identically.

⚠️ **seat_v1's "zero relevant displaced" does NOT hold after the full pipeline.**
At pool level, S2 cap=2 displaced 4 wrong_object + 1 salt_sibling and **zero**
relevant. Through the full pipeline every variant displaces relevant docs — **6
under P0**, 2 under P1/P2/P3. Protections *reduce* relevant displacement rather
than causing it.

### Combined with I1, stage 5 only

| variant | owned | wrong_obj | salt | empty | size | seats |
|---|---|---|---|---|---|---|
| P0+I1 | 0.95 | 0.00\* | 0.05 | 0.00 | 3.05 | 24/24 |
| P1+I1 | 0.95 | 0.00\* | 0.05 | 0.00 | 2.95 | 24/24 |
| P2+I1 | 0.95 | 0.00\* | 0.05 | 0.00 | 2.90 | 24/24 |
| P3+I1 | 0.95 | 0.00\* | 0.05 | 0.00 | 2.90 | 24/24 |

\* **wrong_object → 0 under I1 is TAUTOLOGICAL at every stage, because I1's rule
IS the labeler's rule.** Non-tautological: I1 raises seat survival to 24/24 under
*every* protection (it removes the competitors that were evicting seats) and costs
~0.8 docs of pool size.

### 🔴 CANARY TENSION — the seat breaks one canary

| canary | resolves? | hits | would seat | breaks? |
|---|---|---|---|---|
| `metformin_moa` | **YES** | `METFORMIN` | **4 safety docs** | **🔴 YES** |
| `statin_moa` | no | — | 0 | no |
| `glp1_weight` | no | — | 0 | no |
| `statin_efficacy` | no | — | 0 | no |
| `sglt2_cv` | no | — | 0 | no |
| `statin_moa_tracked` | no | — | 0 | no |

`metformin mechanism of action` whole-token-matches the corpus key `METFORMIN`,
which owns four whitelisted safety sections — Warnings 43685-7 (0.5263), Boxed
Warning 34066-1 (0.5139), Contraindications 34070-3 (0.4945), Drug Interactions
34073-7 (0.4711), all below the 0.6 floor and therefore all seatable. **A
key-based seat fires on OWNERSHIP, not on question intent**, so it would inject
safety sections into a mechanism-of-action question whose committed gate
(`tests/probes/canary/`) requires exactly zero. The other five don't resolve —
`statin`, `SGLT2`, `GLP-1` are class terms with no corpus key, and `statins`
plural whole-token-matches nothing.

### Self-refutation (Rule 21)

**Seat count ≠ seat position count.** 24 seats produced **27** sort-positions,
because seats are scored on the **raw** query while the pool comes from
**rewritten** queries — a doc below the floor on the raw query can be above it on
a rewrite, appearing in both. So the ":292" rate is **20 of 27 positions**, not
20 of 24 seats. Consequence worth noting: **the K-union rewrite already lifts some
would-be-seated docs above the floor**, so the seat's marginal value is smaller
than the raw-arm measurement suggested.

## Files

| file | role |
|---|---|
| `seat_v2.py` / `seat_v2.json` | the survival measurement — real multi-source retrieval, real stage-3/4 model calls |
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
