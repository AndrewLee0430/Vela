# Pool-size distribution harvest — MEASUREMENT ONLY (2026-07-28)

**Purpose:** R15 showed `pool_size` 1 vs 5 on identical input four minutes apart. This measures how
general that is, **before** any build decision. **No fixes were made and no recommendation is given** —
the distribution is the deliverable.

**Scope:** 25 `research` golden cases (R01–R20 + TB01–TB05) × **N=3**, single session
**11:02:06 → 11:20:17**, `max_results=5`, `SOURCE_WEIGHT_ACTIVE=true`.
**Exclusions: 0 network-zero-doc runs, 0 errored runs** — all 75 runs usable.

> ### ⚠️ TRANSPORT DEVIATION — stated, not hidden
> The baton asked for this through `tests/run_golden_tests.py` (the new `pool_identity` capture).
> **That was not viable on this machine.** The box has **8.1 GB RAM with ~1.0 GB free**, and the uvicorn
> server — which holds three embedding corpora (local 690 + TFDA 10941 + DailyMed 4608) — is killed by
> the OS after roughly 10 requests. Observed **twice**: the server log ends cleanly mid-request with
> **no traceback** (the signature of an external kill, not a crash) and every subsequent case returns
> ERROR. Only 5 cases of pass 1 survived.
>
> This harvest therefore calls `retriever.retrieve()` **in-process** — the same document list the golden
> runner's `pool_identity` is derived from (`server.py:903` citations ← `generator.py:179` ← these docs).
> One process instead of two, no generation, no judge. Proven on this machine: the pair-aware M1 harness
> completed 120 consecutive retrievals in one process on 2026-07-27.
>
> **What the deviation costs:** PASS/WARN/FAIL verdicts. See §4 — the verdict-correlation question is
> reported as **NOT MEASURED**, not estimated.

---

## 1. Per-case table

`turnover` = 1 − |∩ across the 3 runs| / |∪ across the 3 runs|. **0.0 = identical pools every run;
1.0 = no document common to all three.** `jacc` = mean pairwise Jaccard. `mode` is shown only when a
value actually repeats (— when all three runs differ, where a "mode" would be an artefact).

| case | sizes | min | max | mode | turnover | jacc | flags |
|---|---|---|---|---|---|---|---|
| R01 | [5, 5, 5] | 5 | 5 | 5 | 0.0 | 1.0 | |
| **R02** | **[3, 1, 2]** | 1 | 3 | — | **1.0** | 0.167 | **≤2 ×2 · DISJOINT** |
| R03 | [4, 4, 5] | 4 | 5 | 4 | 0.2 | 0.867 | |
| R04 | [4, 4, 5] | 4 | 5 | 4 | 0.2 | 0.867 | |
| R05 | [4, 4, 4] | 4 | 4 | 4 | 0.0 | 1.0 | |
| R06 | [5, 5, 5] | 5 | 5 | 5 | 0.0 | 1.0 | |
| R07 | [5, 4, 5] | 4 | 5 | 5 | 0.5 | 0.656 | |
| R08 | [5, 5, 5] | 5 | 5 | 5 | 0.0 | 1.0 | |
| R09 | [3, 5, 5] | 3 | 5 | 5 | 0.75 | 0.394 | |
| R10 | [4, 5, 5] | 4 | 5 | 5 | 0.333 | 0.756 | |
| R11 | [5, 5, 5] | 5 | 5 | 5 | 0.625 | 0.508 | |
| R12 | [5, 4, 5] | 4 | 5 | 5 | 0.714 | 0.476 | |
| R13 | [5, 5, 4] | 4 | 5 | 5 | 0.778 | 0.333 | |
| R14 | [5, 5, 5] | 5 | 5 | 5 | 0.333 | 0.778 | |
| **R15** | **[1, 1, 1]** | 1 | 1 | 1 | **0.0** | 1.0 | **≤2 ×3** |
| R16 | [5, 5, 5] | 5 | 5 | 5 | 0.0 | 1.0 | |
| **R17** | [4, 5, 4] | 4 | 5 | 4 | **1.0** | 0.333 | **DISJOINT** |
| R18 | [5, 5, 5] | 5 | 5 | 5 | 0.75 | 0.429 | |
| R19 | [4, 3, 4] | 3 | 4 | 4 | 0.667 | 0.494 | |
| R20 | [5, 5, 5] | 5 | 5 | 5 | 0.889 | 0.407 | |
| TB01 | [5, 5, 5] | 5 | 5 | 5 | 0.75 | 0.5 | |
| TB02 | [4, 5, 4] | 4 | 5 | 4 | 0.5 | 0.667 | |
| TB03 | [3, 3, 4] | 3 | 4 | 3 | 0.25 | 0.833 | |
| **TB04** | **[0, 1, 1]** | 0 | 1 | 1 | 0.0 | 1.0 | **≤2 ×3 · ZERO-DOC** |
| TB05 | [5, 5, 5] | 5 | 5 | 5 | 0.333 | 0.778 | |

---

## 2. Aggregate

**Pool-size distribution across all 75 runs:**

| pool_size | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| runs | 1 | 6 | 1 | 5 | 18 | **44** |
| share | 1% | 8% | 1% | 7% | 24% | **59%** |

- **`pool_size ≤ 2`: 8/75 runs = 11%**, concentrated in **3/25 cases (12%)** — **R02, R15, TB04**.
  It is not spread thinly across the corpus; it clusters on specific queries.
- **`pool_size = 5` (the `max_results` ceiling) on 59% of runs** — the pool is usually full.
- **One zero-doc run (TB04 run0)** with status `irrelevant`: documents *were* retrieved and the
  relevance filter dropped all of them. Correctly **not** network-excluded under the M1 filter rule
  (`no_results`/`error` only) — this is a real retrieval outcome, not a network artefact.

**Churn (union turnover across the 3 runs):**

- **mean 0.423 · median 0.333**
- **fully stable (turnover 0.0): 7/25 cases** — R01, R05, R06, R08, R15, R16, TB04
- **fully disjoint (turnover 1.0): 2/25 cases** — **R02, R17**
- The remaining 16 sit in between, i.e. **churn is the norm, not the exception**: on a typical case
  ~a third to a half of the retrieved union is not common to all three runs, on identical input,
  minutes apart, with zero code change.

**Worked example — R02** (`first-line treatment for hypertension in diabetic patients`):

| run | pool |
|---|---|
| 0 | `PMID:40545747` · `PMID:33793326` · `PMID:10979055` |
| 1 | `PMID:32389335` |
| 2 | `PMID:32389335` · `PMID:21470107` |

Run 0 shares **no document at all** with runs 1–2, and pool size swings 3 → 1 → 2.

---

## 3. ⚠️ R15's churn is itself intermittent — a second baseline

| date | pools | turnover |
|---|---|---|
| **2026-07-27** | `[8975463]` · `[9475822, 27230048, 32337112, 20059332, 37601013]` · `[8975463]` | **1.0 (disjoint)** |
| **2026-07-28** | `[8975463]` · `[8975463]` · `[8975463]` | **0.0 (stable)** |

**On consecutive days the same query went from completely disjoint pools to perfectly stable ones.**
This matters for the escalation rule: **a single day's N=3 can show turnover 0.0 and still be a churning
query.** Any causal test must compare *distributions across versions*, and a stable-looking arm is not
evidence of stability.

---

## 4. Verdict correlation — **NOT MEASURED**

The baton asked whether verdict (PASS/WARN/FAIL) correlates with `pool_size`. **This harvest cannot
answer it**: the in-process transport produces no judge verdict (§ deviation box).

The only surviving golden-runner records with both a verdict and `pool_identity` are **10 runs**
(5 from 2026-07-27, 5 from the truncated pass 1 today) — all PASS, spanning pool sizes 1–5. That is
**too thin to support a correlation claim in either direction**, so none is made. Answering it properly
needs either more RAM (so the server survives a full pass) or a harness that runs the judge in-process.

---

## 5. Artifacts

- `tests/results/_poolsize_harvest.py` — harvest script (throwaway, committed for reproducibility)
- `tests/results/poolsize_harvest_20260728_110206.json` — raw per-run data (gitignored)
- `tests/results/_poolsize_run.log` — run log (gitignored)

**No recommendation on what to build.** That is the founder's call after seeing this distribution.
