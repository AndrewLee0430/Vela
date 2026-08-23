# `retrieval_attrition/` — where documents die between the corpus and the answer

Evidence for the TECH_DEBT entry headed
**`[P1 · retrieval measurement / premise integrity — five read-only recons + TWO founder-authorized
live runs, 2026-08-22/23; FINDINGS ONLY, nothing re-scoped]`**.

**Why this directory and not `ownership_eval/`.** Five of the six diagnostics measure *where documents
die across the whole pipeline* on the **real golden Research set**. That is a different question, on a
different population, from `ownership_eval/`'s synthetic single-drug line — and co-locating them is
exactly how the population confusion this work kept tripping over would be re-created. The one
resolver diagnostic lives here because it was produced by the same sweep and is cited by the same
entry; the modules it evaluates (`resolver.py`, `build_query_set.py`) live in `ownership_eval/`.

---

## 🔴 POPULATION IS THE POINT — read this before citing any number below

Three findings in this line were measured on `ownership_eval/`'s **synthetic `{drug}+{template}`**
queries. **Two failed to generalise to real Research queries; one held.** The method was identical
every time. **Only the population decided.**

| finding | synthetic | real golden Research set | generalised? |
|---|---|---|---|
| pool size below 5 | 65% (13/20) | **41% pre-c1 · 47% post-c1** | ❌ **NO** |
| resolver reach | resolves by construction | **20/30 name a class or no drug** | ❌ **NO** |
| relevance-filter attrition | 58.4% | **60.7%** | ✅ yes, within 2.3 pts |

⚠️ **A synthetic-set result is a hypothesis about Research traffic, never a measurement of it.** The
confirming case is the dangerous one — read alone it teaches the wrong lesson.

⚠️ **And the "real" set is itself a curated golden test set**, built to exercise known behaviours
(the R10/R15/R16/R20 oscillators, CJK `TB` cases, edge cases). It over-represents hard queries by
construction. It is the best real-query witness in this repo and it is still **25 cases × N=3**. It
supports claims about those 25 cases; it does **not** support claims about traffic distribution.

---

## The artifacts

| file | what it measures | population | date | 🔴 what it does NOT support |
|---|---|---|---|---|
| `resolver_builder_diag_20260822.json` | both key-set builders side by side: aspirin gap, merge-mechanism counts, CALCIUM, branch exclusivity, all 232 non-moiety bases **unfiltered** | 30 queries: R01–R20 + 6 canaries + 4 known misfires. **Offline, no network** | 2026-08-22 | not a production resolver — neither builder is wired into `api/`. The "clean hit" split is **my judgement**, not a measurement. The 232-base list is **unfiltered on purpose**; which bases are "ordinary English" is a judgement the founder has not made |
| `attrition_ladder_20260823.json` | offline attrition ladder, the `min_score` floor distribution, and the **hand-mapped** 30-query reach ceiling | seat_v2's 20 synthetic queries (ladder) + the 30-query set (ceiling). **Offline** | 2026-08-23 | the ladder is from a **MIRROR** of `retrieve()`, not `retrieve()` — TECH_DEBT #8. The ceiling is **hand-mapped by reading each query**, a judgement stated as one, and it is **reach not benefit** |
| `poolsize_harvest_20260823_115117.json` | raw post-c1 pool sizes, per run, with `source_ids` **and** `source_types` | **25 real golden Research cases × N=3 = 75 live `retrieve()` calls** | 2026-08-23 | one session. The original harvest measured mean run-to-run turnover **0.423**, so single-run pools are not stable |
| `poolsize_postc1_comparison_20260823.json` | pre/post-c1 deltas, TB02 diagnosis, ex-TB02 sensitivity | same 25 cases, vs the 2026-07-28 raw below | 2026-08-23 | ⚠️ **the c1 effect is CONFOUNDED with ~4 weeks of live PubMed/FDA drift and cannot be separated** without a same-day A/B, which is not retrospectively possible |
| `filter_attrition_20260823_122149.json` | raw per-run stage counts read from **production's own logger** | same 25 cases × N=3 = 75 live calls | 2026-08-23 | **counts only.** `retriever.py:531` logs `N -> M`; it does **not** log *which* documents were dropped. Nothing here says whether the filter dropped the *right* 60% |
| `filter_attrition_analysis_20260823.json` | removal-rate distribution, the full ladder, per-case table with stability spread | same | 2026-08-23 | same counts-only limit. Per-case stability is over **3 runs**, which shows spread but not a distribution |

### Also here

| file | why |
|---|---|
| `_filter_attrition_harvest.py` | the runner. **Zero `api/` change by construction** — it attaches a `logging.Handler` to the existing `api.rag.retriever` logger and reads records production already emits (`:225` dedup, `:75` CutExempt, `:531` filter, `:527` FilterExempt, `:291` pre-slice). Per Rule 20, probe scripts belong here — the six force-added scripts under `tests/results/` are the **historical mistake** this directory exists to correct, not a precedent to follow |
| `poolsize_harvest_20260728_110204.json` | 🔴 **IRREPLACEABLE — the strongest reason anything here is committed.** The **pre-c1** raw harvest. It cannot be regenerated: c1 removed the `local` corpus from retrieval (fly 215, 2026-07-29), so re-running does not produce a comparable snapshot — the source it measured is **gone from production**. `docs/poolsize_distribution_harvest.md` §5 lists it as gitignored; **its survival on one machine was luck, not policy.** Verified against that report's committed markdown table: **zero disagreements** |

---

## Reproducing

- **Offline** (no network, no LLM): `resolver_builder_diag`, `attrition_ladder` — recomputable from
  the shipped corpus and the committed `ownership_eval/` artifacts.
- **Live** (network + LLM, ~17 min, 75 `retrieve()` calls each): the two harvests.
  `tests/results/_poolsize_harvest.py` produced the pool-size runs; `_filter_attrition_harvest.py`
  here produced the filter run.
- ⚠️ **Re-running does not reproduce these snapshots.** Live PubMed/FDA content changes, and
  `_rewrite_query` is nondeterministic (temperature=0, no seed). The JSON is the evidence; the script
  is the method. Both are needed — that is why both are committed.
