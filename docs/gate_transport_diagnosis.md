# §2.7 gate transport — memory diagnosis (2026-07-28)

## ⛔ HEADLINE: THE PREMISE IS REFUTED. The §2.7 Research gate COMPLETES on this machine.

This baton was opened on my own claim, made in the previous baton, that *"the API server with three
embedding corpora resident is OS-killed after ~10 requests, so the §2.7 gate cannot complete on this
machine, which blocks every 🔴 build baton."*

**That diagnosis was wrong.** Measured today:

| Check | Result |
|---|---|
| §2.7 Research gate, 20 cases, one session | ✅ **COMPLETED 20/20** — 19 PASS / 1 WARN / 0 FAIL / 0 ERROR |
| Server alive at end | ✅ `health 200` |
| Windows Resource-Exhaustion (low-memory) event today | ❌ **none** — most recent is **2026-07-09** |
| All three corpora resident | **195 MB** (not GB) |

**There is no transport blocker to fix.** Tasks 3's options are recorded for completeness, but the
recommendation is **(none of them) — see §5.**

---

## 1. Memory attribution (Task 1)

Measured in-process by loading each store one at a time and sampling RSS between loads
(`tests/results/_mem_attribution.py` — see the housekeeping proposal in §6), rather than inferring
from disk size.

| Stage | RSS MB | Δ MB | embeddings nbytes | shape / dtype |
|---|---|---|---|---|
| baseline (interpreter + deps) | 20.2 | — | — | |
| `import api.database.vector_store` | 65.9 | **+45.7** | — | numpy/openai/etc. |
| `VectorStore` — local drug store | 76.1 | **+10.2** | 4.0 | (690, 1536) float32 · 690 docs |
| `TFDACorpusStore` — indication corpus | 159.3 | **+83.2** | 64.1 | (10941, 1536) float32 · 10941 docs |
| `DailyMedCorpusStore` — label corpus | 215.6 | **+56.3** | 27.0 | (4608, 1536) float32 · 4608 docs |
| **TOTAL with all three resident** | **215.6** | **+195.4** | | |

**Sources on disk:** `data/drug_vectordb/index.json` 21.2 MB · `data/tfda/indication_corpus.json`
11.7 MB + `indication_emb.npy` 32.1 MB · `data/dailymed/label_docs.json` 14.8 MB +
`label_emb.npy` 13.5 MB.

**⚠️ `.npy` embeddings are float16 on disk and expanded to float32 in RAM** at
`api/database/vector_store.py:175` and `:230` (`.astype(np.float32)` — "float16 on disk → float32 for
cosine"). That is the 2× between disk and resident for TFDA (32.1 → 64.1) and DailyMed (13.5 → 27.0).
The local store is built from a JSON list at `:51` (`np.array(data["embeddings"], dtype=np.float32)`).

### When each loads: **import time, eagerly, all three**

`retriever = HybridRetriever(...)` sits at **module level** in `api/server.py:449` — **not** inside the
`lifespan` handler (`:205`). `HybridRetriever.__init__` calls `get_vector_store()` (`retriever.py:109`)
and `get_dailymed_store()` (`:120`); TFDA likewise. Each getter is a lazy singleton
(`vector_store.py:139` / `:189` / `:244`) but they are invoked at import, so laziness never applies.
**Consequence: `import api.server` pays the full 195 MB, for every entry point** — server, tests, scripts.

### Growth per request: **modest growth, not flat, not a leak**

Sampled during the live 20-case gate:

| | RSS |
|---|---|
| after startup (steady state) | **309 MB** |
| after 20 research cases | **400 MB** |
| growth | **+91 MB ≈ 4.6 MB/case** |

Growth is real but **bounded and modest** — at this rate a full 133-case run would add ~600 MB.
Not a leak in the runaway sense; consistent with per-request caches/audit accumulation.
*(309 MB steady state vs the 215.6 MB attribution figure: uvicorn + FastAPI + the SDK clients add
~90 MB on top of the corpora.)*

---

## 2. Is it an OOM-kill? **NO — and the evidence is direct, not inferred (Task 1)**

The baton required OS evidence, and correctly said the premise depends on it.

- **No Windows Resource-Exhaustion event (System log, Event ID 2004) today.** The most recent is
  **2026-07-09**, 19 days ago. Windows *does* log low-virtual-memory conditions on this box — the
  history contains entries naming `vmmem`, `node.exe`, `chrome`, `claude` — so the absence is
  meaningful, not a gap in instrumentation.
- **The `Application Error` (Event 1000) `python.exe` faults recorded today are a DIFFERENT PROJECT.**
  Faulting module: `C:\Users\andre\projects\Ming\backend\.venv\Lib\site-packages\pythonmonkey\mozjs-132a1.dll`,
  exception `0x80000003`. Nothing to do with Vela. I nearly mis-attributed these; they are a red herring.
- **Windows has no Linux-style OOM killer.** Memory exhaustion in CPython on Windows surfaces as a
  `MemoryError` **with a traceback**, or a commit failure — not a clean, traceback-free exit.
  The observed signature was therefore never consistent with OOM.
- **Machine state:** 8,109 MB physical, ~1,310 MB free, **282 processes summing 7,254 MB** — saturated
  by the dev environment (Chrome, VS Code, Claude, Defender), no single hog. Commit limit 19,025 MB
  with 3,620 MB free, i.e. **pagefile headroom existed**.

**Conclusion: the earlier failures were not memory.** The most likely cause is background-task process
lifecycle: both failures occurred when the gate/harvest ran as a **background task** (once alongside a
separately-backgrounded server, once with the server `nohup`-ed inside the same task). Today's success
ran the **server as its own background task and the gate in the foreground**. I have **not** proven that
mechanism — stating it as the leading hypothesis, not a finding.

---

## 3. What this changes

- **The §2.7 gate is not blocked.** It ran end-to-end today: **20/20, 19 PASS / 1 WARN / 0 FAIL**,
  which **meets the 18/2/0 floor** recorded in TECH_DEBT (and R15 passed, consistent with §6.1 there).
- **The pool-size harvest's transport deviation stands as recorded** (it was real at the time) but its
  stated *cause* was wrong. `docs/poolsize_distribution_harvest.md` should be read with this correction.
- **`api/database/vector_store.py:52` remains worth its own baton** — but for the reasons already
  recorded (Rule 4 `print()` on an import-time path; unblocking the four deferred §3.1 endpoint tests),
  **not** for memory.

---

## 4. Task 3 — transport options (recorded for completeness)

| | Effort | Risk | §2.7 semantics preserved? |
|---|---|---|---|
| **(a) chunked execution + server restart between chunks** | low (tests-only) | low | **Partly — see below** |
| **(b) lazy / mmap corpus loading** | medium (product code, import path) | **medium-high** | yes |
| **(c) run the gate on a larger machine** | low-medium (ops) | low | yes, if reproducible |

**(a) Chunking.** Tests-only, no product code. **What §2.7 actually depends on:** *fresh-code identity* —
every case must run against the same build. Restarting the server between chunks **preserves that**.
What it breaks is a **contiguous live-API sample window**: PubMed/FDA results and `_rewrite_query`
churn drift across a longer wall-clock run. Given the measured churn (mean union turnover **0.423**,
`docs/poolsize_distribution_harvest.md`), a split window adds variance to an already-noisy signal —
material for a *recall* measurement, less so for a *verdict* gate. **So: acceptable for §2.7 verdicts,
not acceptable for a recall/pool measurement.**

**(b) Lazy / mmap loading.** `np.load(..., mmap_mode="r")` would avoid resident float32 expansion, and
deferring the three `get_*_store()` calls out of import into the `lifespan` handler would stop every
script paying 195 MB. **Overlaps the already-proposed `vector_store.py:52` baton — same file, same
import chain** — so if ever done, do them together. **But with the premise refuted there is no memory
problem to solve, so this is now a tidiness/startup-time item, not a blocker fix.**

**(c) Larger machine.** No code change. Would need reproducible: `.env` secrets (OpenAI, PubMed, FDA,
Clerk, `DATABASE_URL`), the three corpora (~93 MB, gitignored — must be rebuilt or copied), Python
3.12 + `uv`, and network egress to PubMed/FDA/OpenAI. Cost: a VM plus the setup, and secrets leave this
machine — a real consideration given the gate needs live production-grade keys.

---

## 5. Recommendation

**None of (a), (b) or (c). Do not change transport — there is no blocker.**

The gate completes. What the incident actually exposed is a **reporting** weakness, not a capacity one:
an interrupted run could be misread as a completed gate. That is fixed by the Task 2 completeness guard
(shipped this baton), which is worth having regardless of why a run stops.

**Operational note (the only behavioural change needed):** run the gate with the **server as its own
background task and the runner in the foreground**. Both observed failures had the runner backgrounded
too. This is an invocation convention, not a code change, and the Task 2 guard now makes any recurrence
loud rather than silent.

**If a genuinely larger gate is ever needed** (full 133-case suite, or many repeats), revisit **(c)**
first — it preserves §2.7 semantics exactly, and (b) touches the import path of every entry point for a
problem that has not been shown to exist.

---

## 6. Housekeeping — proposed home for probe scripts (PROPOSAL ONLY, nothing moved)

**The problem, stated plainly.** `tests/results/` is gitignored, but probe scripts are being
**force-added** into it because they are worth keeping. After this baton that directory holds **two
tracked files among many untracked ones** — `_poolsize_harvest.py` (38349e2) and `_mem_attribution.py`
(this commit) — which is a confusing state: `git status` stays quiet about edits to some files in a
directory it otherwise ignores, and a `git clean` would delete the neighbours but not these.

**Proposal: `tests/probes/`** — a normal tracked directory, `_`-prefixed filenames kept so they remain
obviously throwaway/diagnostic rather than part of the test suite.

- **Tracked (scripts):** `tests/probes/*.py` — reproducible diagnosis, reviewable in a diff.
- **Ignored (output):** raw JSON / logs stay in `tests/results/`, unchanged.
- **Rule of thumb:** if a future reader would need to re-run it to trust a number in `docs/`, it belongs
  in `tests/probes/`. If it is a one-shot that produced a number already written down, leave it ignored.

**Should prior probe scripts move too?** There are **~20** `_*.py` probe scripts in `tests/results/`
(`_kunion_gate.py`, `_threshold_probe.py`, `_recallmiss_probe.py`, `_pairaware_*.py`, `_slice2_*.py`, …),
all currently untracked. **Recommendation: move only the ones cited by a committed `docs/` file** — those
are the ones whose absence would make a shipped claim unreproducible. By that test the candidates are the
`_pairaware_*` set (cited by `docs/pair_aware_retrieval_probe.md`), `_kunion_gate.py` (cited by
`docs/kunion_cut_exemption_build.md`), plus the two already force-added. **A bulk move of all ~20 is not
recommended** — most are superseded one-shots, and tracking them adds noise without adding trust.

**Not moved unilaterally** — this touches file locations referenced by several committed docs, so it
should be one deliberate commit with the doc cross-references updated in the same change.
