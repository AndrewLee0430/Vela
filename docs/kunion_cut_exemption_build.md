# K-union rewrite + cut-exemption — build notes (recall-miss [P1] rewrite-nondeterminism surface)

**Shipped:** fly 211 (2026-07-24, nrt) · **Commits:** `57e1b5c` → `2b56941` (6) + docs · **Status:** DEPLOYED, prod human-eye gate PASSED (founder).
**Scope:** 🔴 changes WHAT is retrieved on Research (DailyMed fan-out breadth + candidate-cut survival). Full gate suite + founder prod gate required and completed before this doc was promoted.
**Precedent:** mirrors surface-(iii) (filter-exemption, fly 209) one stage earlier; reuses its 4-LOINC safety whitelist unchanged.

---

## Problem (measured)

`_rewrite_query` (gpt-4.1-mini, temp=0) is non-deterministic; a DailyMed safety section clears the 0.6 retrieval gate only when a run happens to emit the section's clinical vocabulary → the section straddles 0.6 run-to-run (recovery 33–58% at K=1, probe `rewrite_nondeterminism_probe_REPORT.md`). **And** even when recovered, the section dies at the pre-rerank `candidates = unique_docs[:max_results*4]` (=[:20]) cut — DailyMed cosine (~0.61) loses to PubMed synthetic scores (~0.85), so it ranks below the cut *before* the surface-(iii) filter-exemption can act. **Recovery ≠ citation.** Two additive levers address the two stages.

## Lever 1 — DailyMed-only K=3 union + raw-query augment (`_dailymed_union_queries`)

Runs `_rewrite_query(query)` **K=3 times in parallel** (`asyncio.gather`), unions the emitted rewrites (first-seen, deduped), and appends the raw `query` as a deterministic augment. Used ONLY for `_search_dailymed`; the 4 non-DailyMed sources keep the single K=1 rewrite set (no PubMed/FDA/local/TFDA pool inflation, no eutils stress). Returns `[]` when DailyMed is disabled. `retrieve()` Step-2 fan-out is split: non-DailyMed loops the 3 rewrites, DailyMed loops the K-union set (guarded on `source_filter`).

## Lever 2 — additive cut-exemption (`_cut_exemption`)

Immediately after `candidates = unique_docs[:max_results*4]`, re-adds any RETRIEVED whitelisted official-label SAFETY section the cut dropped (`source_id not in cut_ids and _is_whitelisted_safety_section`). **APPEND-only** — never drops, reorders, or displaces a survived candidate; mirrors surface-(iii) one stage earlier. Reuses `_SAFETY_SECTION_WHITELIST` (34073-7 Drug Interactions · 34070-3 Contraindications · 43685-7 Warnings · 34066-1 Boxed Warning) and `_is_whitelisted_safety_section` unchanged — NO new whitelist.

**Composition (no double-count):** Step-3 dedup guarantees one doc per `source_id`; lever-2 appends at most once (`not in cut_ids`); surface-(iii) re-adds at most once (`not in kept_ids`); `_collapse_subchunks` dedups by section key at the end. The two exemptions are sequential guards on the same single doc, not additive copies (unit test `test_combined_cut_and_filter_exemption_cited_exactly_once`).

## Gate results (measurement artifact: `tests/results/kunion_gate_report.md`)

| Gate | Bar | Result |
|---|---|---|
| CITED recovery (straddles, retrieval top_k, N=8) | materially > K=1 | **0.625 → 0.90 mean** (+44% rel; 4/5 up, 1 flat, 0 down); spironolactone 0.125→0.875 |
| Canary (0 safety-cited, N=8) | 0/8 each | metformin-MoA 0/8 · statin-MoA 0/8 · GLP-1 0/8 |
| Latency (K=3 parallel) | ≪ ~2–4 s serial | +0.9 s (12.4 → 13.3 s) |
| Displacement | 0 danger-relevant displacement (by section nature / whitelisted LOINC) | **0 danger-LOINC displaced**; 2 descriptive accepted (below) |
| Danger-path (section-aware) | 0 hard / 0 recheck | 0 / 0 — surfaced Drug Interactions + Contraindications, `implies_clearance=False` |
| §2.7 Research golden | 18/2/0 floor | 17/2/1 → **floor amended (below)** |
| R07 concept-2 (bonus) | — | PASS ×3/3 |

### Displacement — accepted-with-characterization (founder gate review 2026-07-24)

The v2 gate harness counted `safety_displaced=2`, but its `_is_safety_source()` predicate (any `DailyMed:`/`fda-`/`tfda` prefix) **over-counts descriptive sections**. Both events are a descriptive section displaced by the **same drug's whitelisted danger section** on a danger query:

- **warfarin_aspirin:** displaced `DailyMed:…#34068-7` (**Dosage & Administration** — descriptive, NOT a whitelist LOINC) by a whitelisted danger section of the same warfarin label → evidence upgrade.
- **spironolactone:** displaced `fda-spironolactone-basic` (**Indications + Dosage**; contraindications live in the separate `-safety` doc) by the DailyMed Contraindications section on a *hyperkalemia-contraindication* query → evidence upgrade.

**0 whitelisted danger-LOINC sections displaced.** The corrected PASS bar is **"0 danger-relevant displacement, judged by section nature / whitelisted LOINC — not source-tier"**; future gate harnesses must classify displacement by section LOINC, not source prefix.

### §2.7 — R15 known-fail, non-attributable (founder-accepted baseline amendment)

The golden run was 17 PASS / 2 WARN / 1 FAIL. R16/R20 are the known WARN oscillators. **R15** (HIT Type-1/Type-2 distinction) is a NEW, **stable** FAIL — but **provably orthogonal to the levers**:

- **Pool counterfactual (in-process):** lever-ON and lever-OFF return the identical top-3 PubMed docs (PMID 11235727 / 16798180 / 17174213), no DailyMed in the pool either way.
- **Verdict counterfactual (real pre-lever code `0b05de5`, golden judge, ×3):**

| OFF-arm run | Verdict | Missing |
|---|---|---|
| 1 | WARN | Type-1 non-immune |
| 2 | FAIL | Type-1 + Type-2 |
| 3 | FAIL | Type-1 + Type-2 |

**0 PASS / 1 WARN / 2 FAIL — R15 never passes on pre-lever code.** It is a pre-existing PubMed recall gap / live-API drift on a non-DailyMed query the levers do not touch. Filed to TECH_DEBT with an escalation condition. **The §2.7 Research floor is recorded as 17/2/1-with-R15-known-fail** (same treatment as the R16/R20 oscillator acceptances) until the R15 finding is resolved.

## ⚠️ Layer distinction (gate metric vs prod citation) — do NOT read as a regression

The gate's CITED-recovery metric measures **retrieval top_k** (does the DailyMed safety section reach the returned pool) → 7/8 on spironolactone. Post-deploy prod probes measure **citations** (what the generator actually cites) on the **anonymous** path, which uses `gpt-4.1-mini`. On anon, the DailyMed-named section is cited **~1/5** of runs — the generator frequently grounds on the equivalent `fda-spironolactone-safety` (FDA Contraindications+Warnings) instead. **Safety grounding is present every run**; only the *source chosen* varies. This is expected generator-choice behavior, **NOT a lever failure and NOT a regression** — the retrieval layer surfaces the section reliably; citation frequency is model- and layer-dependent (higher on the authenticated stronger-model path, per the founder's STEP 2 gate). A future session must not read the ~1/5 prod citation rate as a lever regression against the gate's 7/8 retrieval rate — they measure different layers.

## Deploy + prod verification (2026-07-24)

- **fly 211 complete**, image `deployment-01KY8W1H14B2TZT0RNYFTRH5RS`; both machines report v211 (`683d447c2e5428` started; `2879720c66d478` stopped = autostop baseline, wakes on traffic). `/health` 200. (Transient rollout "not listening on 0.0.0.0:8000" was a false-negative; smoke/health checks passed.)
- **DailyMed corpus is live in prod** (git-tracked ~3MB float16 `data/dailymed/`, not dockerignored; `COPY data/` fresh in build). Straddle prod probe cited `DailyMed:8123cce8…#34070-3` (Contraindications) — levers confirmed working in prod.
- **Canary** (metformin-MoA) prod: 3/3 ZERO DailyMed safety sections. **Log-grep:** no new `retriever.py` ERROR/WARNING (only benign `[RERANK_STATS] inert_rate=0.0%`).
- **PROD HUMAN-EYE GATE PASSED (founder, authenticated UI):** danger queries cite safety grounding (DailyMed-named or FDA-equivalent), zero false clearance; canary clean (PubMed-only); latency fine.

## Lever state (BY NAME, UNCHANGED this ship — code-only, no fly.toml/secrets change)

`RETRIEVAL_REFUSAL_SHADOW`=ON · `SOURCE_WEIGHT_SHADOW`=ON · `SOURCE_WEIGHT_ACTIVE`=ON (3 secrets share digest `d8c5ac2e11c8e492`) · `DIRECTION_CHECK_SHADOW`=OFF · `QUESTION_NEUTRALIZATION_SHADOW`=OFF (unset) · `locale-hint`=ON (`fly.toml [build.args] NEXT_PUBLIC_LOCALE_HINT_ENABLED="true"`, build-arg — verify in fly.toml, NOT `fly secrets list`). The `0b05de5..2b56941` diff touched only `api/rag/retriever.py` + 2 test files; a code-only image deploy cannot alter secrets.

## Residuals (measure-only; composite/top_k/flags deliberately untouched)

- **warfarin K2>K3 inversion:** NOT measured — the gate harness ran only TRUE-K=1 vs K=3+raw columns (no K=2 column), so it could neither be confirmed nor refuted. Flagged for a future dedicated sweep if wanted.
- **composite-rank-6 > top_k-5 residual:** manifested indirectly as the non-citing K=3+raw runs (warfarin_aspirin 2/8, spironolactone 1/8, lithium 1/8) — consistent with the recovered section landing at composite rank 6, just outside top-5. Per-run rank not captured in v2. Unchanged; not addressed this baton.

## Files touched

- `api/rag/retriever.py` — `_dailymed_union_queries` (lever 1) + split Step-2 fan-out + `_cut_exemption` (lever 2) wired after the candidate cut. Reuses surface-(iii)'s whitelist/helper. No prompt/generator/composite/flag change.
- `tests/test_cut_exemption.py` (9) · `tests/test_dailymed_union.py` (5) — additive-property + composition + canary-no-op unit tests.
