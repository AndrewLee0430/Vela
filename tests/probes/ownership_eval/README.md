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

## Files

| file | role |
|---|---|
| `build_query_set.py` | deterministic query-set builder + the key-based labeler |
| `query_set_v1.json`  | seed 20260820 · 100 (drug, template) pairs over 910 eligible drugs |
| `run_eval.py`        | the runner — writes `result_v1.json` (the evidence) |
| `result_v1.json`     | per-query pools + aggregates + smoke + self-refutation |
| `render_report.py`   | `report_v1.html` is a RENDER of the JSON, nothing else |

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
