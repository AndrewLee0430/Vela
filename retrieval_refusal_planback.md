# Retrieval-Recall Refusal / Downgrade — SHADOW Build Plan-Back (§0 pre-code gate)

First build of the **retrieval-recall refusal** lever (the advisor's "if the pool is highly
one-directional, Vela refuses to advise without counter-evidence" circuit-breaker). Covers the
failure ③/C1 is **structurally blind** to: a confident wrong answer where the protective/counter
source was **never retrieved**, so there is no counter-source present to compare against.

Non-negotiables (carried from the C1 build): **plan-back before code · shadow-first (detect + LOG,
surface nothing, change no answer) · golden re-baseline gates the merge (in shadow, nothing moves —
it only logs).** No fabricated numbers.

---

## Gate status
- **GATE 1 — credit probe: HEALTHY** (one real completion through the §2.1 provider path).
- **Push: nothing new this round. Fly deploy: deferred.** Shadow detection ships behind
  `RETRIEVAL_REFUSAL_SHADOW` (default OFF), mirroring `DIRECTION_CHECK_SHADOW`.

---

## Seam confirmations (in-repo, real interfaces)

1. **What is "the pool the generator saw"?** The generator is called with `documents` =
   `await retrieve_task` in the Research SSE path (`server.py`), i.e. the **FINAL reranked set**
   (relevance-filter → rerank → `max_results`, default 5). It is **NOT** the broad `pubmed_pool`
   candidate list (that is filtered/reranked away before the generator). **Confirmed against the real
   recall data:** OB-L0's anchor 37290898 is in `pubmed_pool` 7/10 but in `final` **0/10** (reranked
   out) — so reading the broad pool would MISS the danger; reading `final`/`documents` correctly sees
   a one-sided pool. → **The lever reads `documents` (the final set), the same seam the C1 hook reads.
   NOT the answer's chosen citations (a subset the model elected to cite).**
2. **LLM calls** → §2.1 provider abstraction. Use **gpt-4.1 (strong), not gpt-4.1-mini** — the C1
   diagnostic proved mini conflates multi-stat abstracts; a false "this protective source actually
   says harm" read would corrupt the pool-spread (e.g. wrongly mark P-L1's 35268461 as harm → false
   one-sided → false refuse). Accuracy matters more than per-call cost here (background, cents/answer).
3. **Shadow hook** → a non-blocking background task `_run_retrieval_refusal_background(audit_id,
   query, documents)` fired at the Research `DONE` event behind the flag, mirroring
   `_run_direction_check_background`. Touches **no** SSE stream / no answer.
4. **Shadow sink** → `logger` + `AuditLog.extra_data["retrieval_refusal"]` (same pattern as the judge
   + the C1 flag). NOT the SSE stream.

---

## THE HARD PART — detection design (resolved here, after looking at the real cases)

**Decision: H1 (PRIOR-EXPECTATION × POOL-DIRECTIONAL-SPREAD) is the primary trigger.** H2
(counter-query probe) is specified as an OPTIONAL confirmation step to add **only if** H1's
over-refusal is too high (not built this round — it costs an extra retrieval and carries the
obesity↔BMI terminology-mismatch risk the failed (i) rewrite exposed; and H2 is DETECTION, never a
retrieval fix). H3 (curated registry) is noted as a high-precision floor for known pairs, **not built**
(the point of this round is to test the generalizable mechanism, not hardcode known cases).

**Why H1, from the real cases:** the discrimination the lever must make is *obesity-paradox
(genuinely contested + pool one-sided harm → REFUSE)* vs *settled directions (peanut-LEAP,
beta-blockers-in-HFrEF, CAST, smoking-PD → one-sided but DO NOT refuse)*. A naive "one-sided pool →
refuse" over-refuses on every settled one-directional truth (the C1 86%-flag failure, re-skinned).
The only signal that separates them is **whether a counter-direction is genuinely plausible/contested
in the CURRENT literature** — H1's prior leg. The pool-spread leg alone is necessary but not
sufficient; the prior leg is what buys precision.

**Mechanism (H1):**
1. Derive `factor → outcome` from the question (LLM).
2. **Pool spread:** for each FINAL-pool source, read its direction on `factor→outcome` (gpt-4.1:
   increases / decreases / no_effect / not_relevant, full abstract). `one_sided` = there is ≥1
   directional source AND **no opposing-direction source** (`min(#increases, #decreases) == 0`).
3. **Counter prior:** ask gpt-4.1 — "for `factor→outcome`, is a counter-direction / paradox / reversal
   **genuinely plausible or still contested in the CURRENT literature** (a recognized active paradox),
   as opposed to a settled one-directional consensus — even if the consensus itself was historically
   counterintuitive?" → `counter_plausible`. (The "CURRENT / settled-even-if-historically-
   counterintuitive" framing is the explicit guard against over-refusing CAST / LEAP / smoking-PD.)
4. **Trigger:** `refuse = one_sided AND counter_plausible`. (Shadow: log the decision; enforce nothing.)

**The gating risk = OVER-REFUSAL** (the C1 lesson). The prior-leg's calibration on
"currently-contested (obesity paradox)" vs "counterintuitive-but-settled (CAST/LEAP/smoking-PD)" is
the whole precision story, and it is **UNPROVEN** — this round measures it explicitly against a frozen
control set; if H1 over-refuses on the settled-counterintuitive controls, H1 alone is insufficient and
H2 confirmation is required (a finding, not a failure).

---

## Corpus (frozen BEFORE running — `tests/retrieval_refusal_corpus.json`)

- **Detection set (SHOULD refuse) — the real retrieval-miss cases** (`retrieval_recall_20260616_133331.json`,
  final pools, anchor 37290898 absent → one-sided harm pool): **OB-L0, OB-L1, OB-L2** (obesity paradox
  in HF — genuinely contested + protective source not retrieved). Tested over the first 3 captured runs
  each (pool composition varies per run → report fire-rate per case).
- **Complete-pool controls (should NOT refuse — tests the pool-spread leg):** **P-L1, P-L2**
  (polypharmacy; protective 35268461 present in `final` 10/10 → two-sided → must not fire; these are
  ③/C1's source-in-hand domain, not retrieval-miss).
- **Over-refusal control set (should NOT refuse — tests the prior leg), frozen criterion + n:**
  topics with an **established direction and no genuinely-active counter-paradox** — drawn from the
  captured `direction_shadow_20260617_143022.json` final pools (`doc_pmids`). Deliberately includes the
  HARD stress cases: **counterintuitive-but-SETTLED** topics (where a naive prior would over-refuse).
  n = the set below; selection criterion frozen pre-run:
  - settled / intuitive one-directional: **R10** digoxin→toxicity, **R05** serotonin-antagonists→
    serotonin-toxicity, **H5** bisphosphonate→atypical-femoral-fracture.
  - counterintuitive-but-SETTLED (the stress cases): **H4** early-peanut→allergy (LEAP), **HD-BB**
    beta-blockers→mortality-HFrEF, **H2** smoking→Parkinson's, **H1** class-I-antiarrhythmics→
    mortality-post-MI (CAST), **C08** beta-carotene→lung-cancer-in-smokers (ATBC/CARET), **C06**
    beta-blockers→COPD-safety.
  - Selection criterion (frozen): "factor→outcome whose direction is an ESTABLISHED consensus with NO
    genuinely-active/contested counter-paradox in the CURRENT literature (a historically-counterintuitive
    but now-settled finding still qualifies as one-directional). Drawn from the captured one-directional
    `direction_shadow` cases; excludes genuinely-contested topics (metformin-CKD, HRT, alcohol, DBP-
    J-curve, glucose-ACCORD)." Report per-case whether the pool was actually one-sided (only one-sided
    controls stress the prior leg) + whether H1 refused.

> Reuses captured pools — **no re-retrieval, no re-generation** (cheap). Full prose is not regenerated;
> the captured answers/pools are the immutable inputs.

---

## Files touched · flag · rollback
- **NEW** `api/services/retrieval_refusal.py` — H1 detector (async; factor/outcome extraction +
  pool-spread + counter-prior + trigger). Flag-only decision object; no enforcement.
- **EDIT** `api/server.py` — `_run_retrieval_refusal_background` fired at the Research `DONE` event
  behind `RETRIEVAL_REFUSAL_SHADOW` (default OFF → zero prod behavior change; no SSE/answer change).
- **NEW** `scripts/retrieval_refusal_eval.py` — offline harness over the frozen corpus (reuses captured
  pools), scores detection + over-refusal, persists `tests/results/retrieval_refusal_*.json`.
- **NEW** `tests/retrieval_refusal_corpus.json` — the frozen corpus record.
- **Rollback:** flag OFF = no-op; revert the commit. No migration, no schema change.

## Out of scope
Front-end neutralization lever (next task); ③/C1 rework; the route; A2 / actual enforcement (refuse vs
downgrade-to-literature-display vs flag, and thresholds). This round = DETECTION + shadow log only,
strictest-reasonable default.

---

## Build refinement (smoke-test finding — pool read is STANCE/valence, not strict HR)

The first smoke read each source's strict mortality direction (increases/decreases). OB-L2's pools are
harm-framed **mechanism/prognosis reviews** ("obesity adversely impacts cardiac structure"; no mortality
HR) → all read `not_relevant` → `directional=0` → the lever couldn't see the one-sidedness (false
negative, fired 1/3). Fix (principled, not p-hacking): `_source_direction` reads the source's overall
**STANCE/valence** (harmful / beneficial / mixed) toward `factor→outcome` — a harm-framed mechanism
paper counts as `harmful` even without an HR; closely-related measures (BMI↔obesity) count as the
factor (terminology-mismatch guard). The threat the lever detects is one-sided *coverage/valence with
the counter-paradox absent*, not a missing HR. Over-refusal is still gated by the prior leg.
**Validated:** the broadened read was spot-checked on OB-L2 run2 — its three `beneficial` reads are
REAL (all three reviews explicitly state "obese individuals with established HF have a better
prognosis" = the paradox), so that run's pool genuinely conveys counter-evidence → correctly NOT
refused. So the lever detects "does the pool convey the counter-direction AT ALL," which is more
accurate than the anchor-PMID-presence proxy.

---

## RESULTS — shadow validation (2026-06-18; gpt-4.1; reused captured pools; `retrieval_refusal_20260618_095609.json` + `_prior_probe_095754.json`)

**H1 PASSES on this evidence — the opposite of C1. H2/H3 NOT needed (H1 alone gave 0 over-refusal).**

| Measure | Result |
|---|---|
| **DETECTION** (one-sided pool + contested → refuse) | **3/3** retrieval-miss cases fired (OB-L0/1/2); **by run 7/9** |
| — the 2 non-firing runs | CORRECT — their pools conveyed the paradox (OB-L2 run2 verified: 3 reviews state the paradox) |
| **OVER-REFUSAL control** (should NOT refuse) | **0/9** — and **8/9 had a one-sided pool**, so the prior leg was genuinely stressed |
| **COMPLETE-POOL controls** (P-L1/P-L2, two-sided) | **0/2** over-fired |
| **PRIOR generalization** (supplementary, prior-only) | **10/10** contested→True (glucose-ACCORD, DBP-J-curve, alcohol, sodium, HRT, obesity) / settled→False (peanut, BB-HFrEF, smoking, statins) |
| Cost | **$0.15** main + $0.009 prior probe |

The C1 "flag everything" failure did NOT recur: the prior leg perfectly separated genuinely-contested
(obesity paradox → refuse) from counterintuitive-but-SETTLED (CAST/LEAP/smoking-PD/beta-carotene → do
NOT refuse) — exactly the discrimination the lever needs.

**Caveats (framing discipline — do NOT over-read):**
1. **End-to-end DETECTION is validated on ONE contested TOPIC** (obesity paradox, 3 framings, anchor
   37290898) — the only retrieval-miss topic the recall diagnostic captured. The prior *generalizes*
   10/10, but whether OTHER contested topics' REAL live pools come back one-sided AND fire is untested
   end-to-end (needs live retrieval — next step / BACKLOG).
2. The prior leg rests on **gpt-4.1's world-knowledge of "currently contested"** — a genuinely-
   contested topic it doesn't recognize → false negative (under-refuse); a settled topic it wrongly
   thinks contested → false positive. 10/10 + 0/9 here, but it is a knowledge dependency (H3 curated
   registry could backstop known pairs).
3. The valence read could in principle hallucinate a `beneficial` → false negative; OB-L2 run2 was
   spot-checked (real), not exhaustively.
4. Reused captured pools (not live), single eval run, n=9 over-refusal / n=6 contested-prior — modest,
   directional, not a generalized guarantee. Per-query firing is pool-composition-dependent (correct,
   but probabilistic, not a deterministic guarantee).
5. SHADOW DETECTION only — enforcement (refuse vs downgrade-to-literature-display) is A2/route-gated.

**Verdict:** H1 (pool-stance-spread × contested-prior) is a VIABLE retrieval-recall refusal detector —
it covers the failure ③ is blind to, with no over-refusal on a stressed control set. Ready to graduate
from "evaluate" to "build out" (broaden contested-topic detection on live retrieval, then A2/enforcement
decision). `RETRIEVAL_REFUSAL_SHADOW` stays OFF until that broadening + an enforcement decision.
