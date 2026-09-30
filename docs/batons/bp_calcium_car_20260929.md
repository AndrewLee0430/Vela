# BP+CALCIUM car — Segment 1: rewrite disambiguation, ONE variable (built 2026-09-29 → REVERTED 2026-09-30)

**Car tag:** `bp_calcium`. **Mode:** BUILD LOCAL → **GATED → REVERTED.** The commit that adds this file carries
**NO product code**: `api/rag/retriever.py` was edited, gated and restored byte-identical to `0b210da` inside the car.
**NOT pushed, NOT deployed.** Prod = fly 260 at `bfb4a8fd5c9e96708bc73ab1b13f5a8244440d34`, unchanged.
**Base:** `0b210da04fa168a74efde0585a3d256f888fe3a1` (Rule 24 asserted: toplevel `C:/Users/andre/projects/Vela`).
**Authority:** `tests/probes/bp_calcium/` verdicts A / B / C at `0b210da` (probe 1 `71936e8`, probe 2 `0b210da`).
**Ledger pins at base (extraction §3 at `0b210da`, all MATCH):** STATE `1e4b845038df2619` · BACKLOG `be5c292f43454a57` ·
TECH_DEBT `0fe197fcdbd640ef`.
**Line numbers** are "at 0b210da" unless marked.

## §0 Founder rulings (2026-09-29 build prompt · 2026-09-29 23:58 restart prompt; verbatim where quoted)

- **R1 Fix layer = `_rewrite_query` ONLY.** "Do NOT touch: the generator prompts, `_filter_by_relevance`,
  min_score/local_threshold, K, top_k, FilterExempt/CutExempt whitelists, the DailyMed corpus/builder, the golden set,
  the hero chip."
- **R2 Budget: founder cap US$5.** "If projected spend passes US$5, STOP and report before running more."
- **R3 Segment 2 (generator branch) is RULED OUT of this car** — "record it as a candidate only."
- **R4 ONE edit, no tuning loop:** "Any regression in (c)(d)(e) or a floor breach in (b) → REVERT the edit, record the
  numbers, STOP. Do not tune the prompt in a loop." Restart prompt: "(e) … compare to control 8/10; ≥ control required."
- **R5 NEXT CAR = TECH_DEBT entries (2)+(3)** (Verify grounded-tag honesty), founder-ruled 2026-09-29; the generator
  "context does not answer the question" branch is **CANDIDATE ONLY, founder to sequence**.
- **R6 Control arm same day (SOP line 5), at `0b210da` BEFORE any edit.**
- **R7 (restart, 2026-09-29 23:58):** "The killed partial runs are NOT results: discard their logs from the evidence set
  (keep them in scratch only)." Treatment gates re-run **SERIAL, one harness resident at a time.**

## §1 Step 0 — read, not assumed

### (a) The rewrite site (`api/rag/retriever.py` at `0b210da`)

- `_rewrite_query` `:298-394`; the system prompt is one string literal `:324-350`; `temperature=0`, `max_tokens=150`,
  `response_format={"type": "json_object"}`; JSON-array parse `:365-375`; fallback `_translate_to_medical_english`.
- **The clause this car re-worded, verbatim at `:342`:**
  `"3. Precise medical terminology angle (official drug names, MeSH terms)\n\n"`
- `_dailymed_union_queries` `:396-413`: k=3 PARALLEL `_rewrite_query` calls, first-seen union, then **the raw query is
  appended** as a deterministic augment. DailyMed-only.
- The 0.6 floor is `local_threshold` in the production construction `api/server.py:523`, passed to
  `dailymed_store.search(min_score=…)` `:696-704` — **untouched**.

### (b) Rule 19 inventory — what sits AROUND the rewrite output; each UNCHANGED by the (now reverted) edit

| mitigation | where | status under the edit |
|---|---|---|
| K=3 DailyMed union of rewrites | `_dailymed_union_queries` `:396-413` | unchanged — output contract (JSON array of ≤3 strings) unchanged |
| raw-query augment (deterministic) | `:411-412` | unchanged |
| TFDA brand→ingredient identity annotation, **CJK-gated** | `api/server.py:790-830` → `tfda_lookup.detect_brands_in_text` (`[]` for non-CJK) | unchanged — runs BEFORE the rewriter; the English hero chip passes through byte-identical (asserted in `step3_trace.py`) |
| FilterExempt (whitelisted safety-section re-add after the LLM filter) | `retriever.py:517-529` | unchanged |
| CutExempt (same, at the `[:max_results*4]` cut) | `:61-76`, `:237` | unchanged |
| relevance filter prompt, reranker, composite reorder, sub-chunk collapse | `:452-536`, `:250-290` | unchanged |
| rewrite fallback on parse failure → `_translate_to_medical_english` | `:389-394` | unchanged |

### (c) Gate tooling and their CURRENT floors (read at `0b210da`, not inherited)

| gate | tool | floor / criterion | command |
|---|---|---|---|
| (b) Research golden | `tests/run_golden_tests.py` | `RESEARCH_GOLDEN_MIN_PASS=18 / MAX_WARN=2 / MAX_FAIL=0` over the frozen 20-case set `R01–R20` (`:90-101`, founder ruling 2026-08-21); `pool_identity` per case (`:462-478`, FINAL top_k only); ERROR>0 → NOT SCORED | `python tests/run_golden_tests.py --filter R` against a TEST_MODE server on `:8000` |
| (c) canary | `tests/probes/canary/canary_gate.py` | 6 canaries × N=8; PASS iff 0 usable runs cite a WRONG-OBJECT whitelisted DailyMed safety LOINC in FINAL; `usable ≥ 6/8`; old any-safety criterion recorded per query | `python tests/probes/canary/canary_gate.py` — ⚠️ writes `tests/probes/canary/canary_baseline_<YYYYMMDD>.json`; each output was MOVED into `tests/probes/bp_calcium/` right after its run (`canary/` left clean) |
| (d) danger-path | `scripts/dailymed_danger_path_verify.py` | 3 danger queries; exit 0 = 0 hard violations AND 0 mandatory rechecks; `source_weight_active=True` `:171-173` | `python scripts/dailymed_danger_path_verify.py` → `tests/results/…json` (gitignored; copied into the probe dir) |
| (e) straddle set | **NO committed harness** — only `tests/results/_kunion_gate.py` (untracked, N=8) | re-implemented in `tests/probes/bp_calcium/step6_straddle.py` (N=2, production retriever via `_harness.py`, 5 strings verbatim from `_kunion_gate.py` STRADDLES): runs whose FINAL contains ≥1 whitelisted DailyMed safety section | `python tests/probes/bp_calcium/step6_straddle.py --arm control\|treatment` |
| pytest | `python -m pytest -q` | last recorded full figure **458 passed / 28 skipped** (`docs/batons/phi_boundary_car_20260923.md:26`) | `SENTRY_DSN= python -m pytest -q` |

### (d) Rule 27 greps (at `0b210da`)

- `git grep -n -i "rewrite" -- TECH_DEBT.md BACKLOG.md STATE.md | grep -i -E "disambigu|confusab|ambigu"` → 2 hits:
  `BACKLOG.md:1125` (a1-i: the English-only rewriter as CJK-brand mis-ID point #1; *ambiguous brands* — a different
  ambiguity) · the TECH_DEBT bullet reading *"at the ambiguity band edge"* (DURLAZA — a cosine margin, not a word
  sense; `:2170` at `0b210da`, shifted by this car's own insertion above it).
  **Neither names the confusable-term / class-level-interaction defect → entry (1) is NEW.**
- `git grep -n -i "official drug names" -- TECH_DEBT.md BACKLOG.md STATE.md docs/` → **0 hits** (the phrase exists only in
  `api/rag/retriever.py:305,342`).
- `git grep -n -i -E "dailymed_grounded|fake-authority|label-stated" -- TECH_DEBT.md BACKLOG.md STATE.md` → `BACKLOG.md:824`
  (v201 Verify ingest-and-cite), `:1031`/`:1033` (legacy `attribution_kind` caption; optional unlink hardening),
  `STATE.md:172` (ⓘ "Vela AI-assessed (not label-stated)" tooltip, ruled 2026-09-03), `STATE.md:539` (v199 fake-authority
  relabel, shipped). **None records that the grounded tag attaches to the setid rather than the claim → entry (2) is NEW.**
- `git grep -n -i -E "combination label|wrong-object|repackager" -- TECH_DEBT.md BACKLOG.md STATE.md` → `BACKLOG.md:1023`
  **"[OTHER] [P2] DailyMed setid selection prefers repackager over reference label"** (max-`spl_version` pick — entry (3)
  cross-references it), `BACKLOG.md:968` wrong-object intrusion [P2], `TECH_DEBT.md:1947` veterinary labels [P2],
  `TECH_DEBT.md:1882` combination products in the local corpus. **No Verify grounding on a COMBINATION label → entry (3) NEW.**
- `git grep -n -i "dormant" -- TECH_DEBT.md BACKLOG.md STATE.md api/` → `TECH_DEBT.md:2347`/`:2350` (two `[DONE]` P3s
  calling the corpus "dormant" as of 2026-07-14 — a superseded state), `api/database/vector_store.py:204` (the docstring).
  **No entry says the docstring is stale → entry (4) NEW.**

## §2 The edit (Step 2) — applied 2026-09-29 20:02 +08:00, REVERTED 2026-09-30 10:1x +08:00 — verbatim diff

Additive block + one clause re-worded; every other prompt line byte-identical. `python -c "import ast; ast.parse(...)"`
OK at the time. Restored with `git checkout -- api/rag/retriever.py`; `git diff --quiet -- api/rag/retriever.py` → clean;
`grep -c "STEP 1b"` → 0.

```diff
@@ -338,0 +339,13 @@ class HybridRetriever:
+                            # bp_calcium car (2026-09-29, tests/probes/bp_calcium/ verdicts A/C): a
+                            # class-level question ("BP meds with calcium") never produced a rewrite naming
+                            # the thiazide/hypercalcemia mechanism, so no source was ever asked for it.
+                            "STEP 1b — Confusable terms and class-level interactions:\n"
+                            "- CONFUSABLE TERMS: calcium, potassium, magnesium, iron or vitamin D taken as a "
+                            "co-administered SUPPLEMENT is NOT the drug class that shares the word "
+                            "(calcium channel blocker, potassium-sparing diuretic ...). Read it from context: "
+                            "when a supplement, food or OTC product is taken WITH a drug or drug class, "
+                            "treat it as a supplement.\n"
+                            "- CLASS-LEVEL INTERACTION QUESTIONS (one side is a drug CLASS or a lay term such as "
+                            "\"BP meds\", or a supplement/food): at least ONE query must name the specific known "
+                            "interaction as CLASS + MECHANISM + OUTCOME "
+                            "(e.g. \"thiazide diuretic calcium supplement hypercalcemia\"), not a single drug pair.\n\n"
@@ -342 +355,2 @@ class HybridRetriever:
-                            "3. Precise medical terminology angle (official drug names, MeSH terms)\n\n"
+                            "3. Precise medical terminology angle (INN names for the drugs the user NAMED, MeSH terms; "
+                            "never collapse a drug class into one drug pair)\n\n"
```

Not changed, flagged: the `_rewrite_query` docstring at `:305` still reads "藥名/術語精確版（official drug names + MeSH
terms）" — it is a docstring, not the prompt; it would need the same re-wording if the edit is ever re-applied.

## §3 Gate numbers — control (at `0b210da`, 2026-09-29, BEFORE the edit) vs treatment (edit applied, 2026-09-30 SERIAL)

**Killed partial runs are NOT evidence (R7).** On 2026-09-29 the first treatment golden (18/20 done: 16 PASS / 2 WARN)
and canary (metformin_moa · statin_moa · glp1_weight complete, statin_efficacy 3/8) runs, and the `:8000` server, were
stopped by Claude Code for host memory pressure. Their logs are in scratch (`*_KILLED_20260929.log`); nothing from them
is cited below. Cause, as read: three Python processes each holding the DailyMed + TFDA float32 matrices (~100 MB) plus
the server. The re-run was SERIAL, one harness resident at a time.

| gate | control | treatment | verdict |
|---|---|---|---|
| (a) bp rewrites, 5 runs × 3 | thiazide **0/5** runs (0/15 strings) · supplement 5/5 runs (5/15 strings) · hypercalcemia 0/5 · CCB 0/5 | thiazide **5/5** (5/15) · supplement 5/5 (**15/15**) · hypercalcemia 2/5 · a "calcium channel blockers + calcium supplement interaction" string in 2/5 (CCB as BP-drug CLASS with the supplement — the on-target reading, hand-read) | changed as intended |
| (a) bp pool / FINAL | probe-1 run 1: 0 DailyMed in pool; FINAL 2 PubMed (one CCB review) | run 1: pool 12, **Calcium Chloride 34073-7 enters at 0.6272** (was 0.5919), FINAL = it + PMID:38345765 · run 2: pool 14, + **HCTZ 34073-7 at 0.6226**, FINAL = both DailyMed. On-target PubMed titles entered 3 / 5, filter kept 1 / 0 (CATS PMID:33178509 dropped) | the mechanism section reaches the generator |
| (a) bp generation run 1 (gpt-4.1, authenticated path) | veto (i) **TRUE** · veto (ii) **FALSE** | veto (ii) **TRUE** ("Hypercalcemia Risk: … thiazide diuretics, vitamin D, lithium … increase the frequency of serum calcium monitoring" [1]) · **veto (i) regex TRUE / hand-read FALSE, regex too coarse** — the answer opens "with calcium **supplements**"; its CCB mentions are CCBs as a BP class whose effect IV calcium chloride may blunt (from the cited label) | PASS bar met on the hand-read |
| (b) golden R01–R20, floor 18/2/0 | **18 / 2 / 0** MET (R03, R20 WARN; `golden_results_20260929_195639`, 19:56 +08:00) | **20 / 0 / 0** MET (`golden_results_20260930_095410`, 09:54 +08:00). Pools identical 1/20 (R13); **0 verdicts moved on an identical pool**; R03 + R20 WARN→PASS on DIFFERENT pools (R20 gained three DailyMed 34066-1 Boxed Warnings); DailyMed 17→18, PubMed 63→73 across the 20 FINAL pools | no breach; moves attributable-by-pool, not separable from PubMed drift |
| (c) canary 6 × N=8 | PASS · wrong-object 0/8 ×6 · old criterion 0/8 ×6 · 48/48 usable | PASS · 0/8 ×6 · 0/8 ×6 · 48/48 usable (the owned metformin citation seen once in the killed partial did NOT recur) | unchanged |
| (d) danger-path | 0 / 0 · exit 0 (`20260929_195853`) | 0 / 0 · exit 0 (`20260930_100706`) | unchanged |
| (e) straddle 5 × N=2 | **8/10** — warfarin+aspirin **1/2** · spironolactone 2/2 · warfarin+NSAID 2/2 · lithium+ibuprofen 1/2 · R07 2/2 | **7/10** — warfarin+aspirin **0/2** · 2/2 · 2/2 · 1/2 · 2/2 | **REGRESSION on the stated metric → REVERTED (R4)** |
| pytest | last recorded 458 / 28 | **480 passed / 28 skipped** (103 s; no product code in this commit — the +22 predate this car) | — |
| spend | — | logged **$0.937** (`step6_spend_final.json`; includes the killed partials — real spend) + ≈ $0.04 unlogged (runner judge 40 calls, danger judge 6, embeddings) ≈ **$0.98 of US$5** | under cap |

**(e) — what it does and does not support.** N=2 per query; the control's own warfarin+aspirin pair swung {2 sections,
0 sections}, the same swing the treatment shows as {0, 0}. `step6_straddle.py` does not capture rewrite strings, so
edit-vs-drift is **not separable**. The query names two INNs and no class / supplement, so neither new clause applies to
it on its face — a reading, not a measurement. The rule was applied as written. **Whether to re-measure that query at
N=8 on both arms (~16 retrievals, ≈ $0.05) before any re-apply is the founder's call** — not a tuning loop.

Artifacts: `tests/probes/bp_calcium/step6_*` (README "Segment 1 build" carries the per-artifact "does NOT support" table).

## §4 Ledgers (this commit)

- **TECH_DEBT.md — 4 NEW entries** (inserted above the E5 entry; class/P PROPOSED, founder ratification pending; each
  first bullet = its Rule 27 grep): (1) `[HONESTY][P1 proposed]` heroChip2 answers a different question — root cause
  `_rewrite_query`; STATUS fix BUILT/GATED/REVERTED · (2) `[HONESTY][P2 proposed]` Verify `dailymed_grounded` attaches to
  the setid, not the claim · (3) `[HONESTY][P2 proposed]` Verify grounded HCTZ on a valsartan+HCTZ combination label ·
  (4) `[OTHER][P3 proposed]` `DailyMedCorpusStore` docstring DORMANT-but-live.
- **NAV** (dated block + table; the block is the one headed "NAV RECOUNTED 2026-09-30 (BP+CALCIUM CAR SEGMENT 1"):
  pre-change derive at `0b210da` = 0 + 9 + 18 + 65 + 100 = 192 (bullets 227 = 192 + 35; [sec] 15 / 14). ⚠️ **The table read DONE 64 / OTHER 101** — the 2026-09-29 RECOUNT block computed 65 / 100 and did not
  write it into the table (same total, wrong split; Rule 25). Corrected from the derive. Post-change re-derive
  `0 + 9 + 21 + 65 + 101 = 196` (bullets 231 = 196 + 35; [sec] unchanged 15 / 14): MATCH.
- **STATE.md:** header parenthetical (2026-09-30) · Recently Shipped terse entry · Next Up line extended: NEXT CAR =
  entries (2)+(3) (R5); CANDIDATE ONLY = (i) re-measure (e) at N=8, (ii) Segment 2 generator branch.
- **BACKLOG.md:** untouched.
- All three ledgers: LF, 0 control bytes (asserted by the patch script and re-checked after).

## §5 Local eye gate — MOOT while the edit is reverted (kept BLANK for a re-apply; localhost, Dev DB, Ctrl+Shift+R)

| # | step | expected | PASS/FAIL | note |
|---|---|---|---|---|
| 1 | click hero chip 2 on `/` (EN UI) | first paragraph is about calcium **supplements** and names thiazide / hypercalcemia | | |
| 2 | same question typed in the zh-TW UI | same content, zh-TW prose | | |
| 3 | CONTROL "metformin renal dosing" | unchanged in shape | | |
| 4 | CONTROL 冠脂妥+warfarin | a DailyMed safety section still cited | | |

## §6 Recorded, NOT filed

- The treatment answer leans on an **IV calcium chloride** label for an oral-supplement question ("caution is needed if
  the calcium is administered intravenously as calcium chloride") — hedged, but the corpus's only calcium-side
  interaction sections ARE the IV products (H8); the oral supplement labels (TUMS, D-Vite) have no interaction section.
- The relevance filter dropped every on-target PubMed doc in treatment run 2 (incl. CATS PMID:33178509) while keeping
  the two DailyMed sections — the `_filter_by_relevance` [P2] entry's judgment half, seen again.
- `step3_trace.py`'s veto-(i) regex (`calcium[- ]channel`) is the wrong instrument for "reads calcium as CCB"; it fires
  on any correct CCB-as-class mention. Kept as-is and reported alongside the hand-read.
- `_rewrite_query` docstring `:305` still says "official drug names" (see §2).
- `scripts/build_dailymed_label_corpus.py` re-wraps `sys.stdout` at import (probe 2 harness note) — unchanged.

## §7 Rollback

Already at base: `api/rag/retriever.py` == `0b210da`. Nothing else to roll back; no migration, no env, no secret.

## §8 Candidate ONLY (founder to sequence)

- **Segment 2, the generator branch (R3 — ruled OUT):** `_build_user_prompt` rule 3 "If context is insufficient, state
  what's missing" (`api/rag/generator.py:441-447`) is obeyed LAST — after an adjacent question has been answered
  confidently. A branch that says so FIRST is the candidate.
- **Re-measure (e) warfarin+aspirin at N=8 on both arms** before any re-apply of §2 (≈ $0.05).
