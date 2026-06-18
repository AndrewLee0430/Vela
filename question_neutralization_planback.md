# Lever 2 — Front-End Question-Neutralization — A/B SHADOW Build Plan-Back (§0 pre-code gate)

Covers the OTHER failure mode (vs Lever 1 retrieval-refusal): **GENERATION-reversal, source-in-hand** —
the protective/counterintuitive source IS retrieved, but a LOADED question framing induces the generator
to state the direction backwards (polypharmacy B01: "why is polypharmacy dangerous" → asserts increased
mortality while citing OR 0.78 lower). Lever: rewrite the INTERNAL generator question to neutral framing
WITHOUT losing user intent; the user still sees their own question answered. Evidence basis: the
generation-stage neutralization probe (`neutralization_generation_20260617_105516.json`, polypharmacy/
35268461, retrieve-once-freeze) cut reversal 3/10→0/10. Advisor-named PRIMARY lever (upstream — bypasses
the multi-stat extraction bottleneck that killed C1's post-hoc path).

**NOT a pure-observer shadow.** Lever 2 changes the generator input → it changes the answer. The "shadow"
is an **A/B HARNESS** (generate BOTH arms on the SAME frozen context, compare reversal A vs B). Production
user-facing behavior is UNCHANGED this round: `QUESTION_NEUTRALIZATION_SHADOW` default OFF; neutralization
exercised only in the harness.

---

## Gate status
- **GATE 1 — credit probe: HEALTHY.** **Push: nothing new. Fly deploy: deferred. Flag default OFF.**

## Seam confirmations (in-repo)
- **Generator-question seam:** `server.py` Research path calls `retriever.retrieve(query=body.question)`
  then `generator.generate_stream(question=body.question, documents=documents, …)`. The retrieval query
  and the generation question are the **same object but separable**: neutralization rewrites ONLY the
  `question=` passed to `generate_stream`, AFTER retrieval. Both arms share the frozen `documents`
  (retrieve-once-freeze, exactly the probe's design). Retrieval/query-rewrite untouched (the failed (i)
  lever is closed — that was retrieval; this is the GENERATOR question).
- **Flag/shadow:** `QUESTION_NEUTRALIZATION_SHADOW` default OFF. When OFF, `generate_stream` gets
  `body.question` unchanged (zero production change). When ON (future), the neutralized question. The A/B
  VALIDATION is entirely in the offline harness this round.
- **LLM calls** (loaded-detector, rewriter) → §2.1 provider abstraction.
- **Reuse the existing direction judge** (`citation_truth_check.judge_direction`, gpt-4.1) to score
  reversal on BOTH arms — consistent ground truth across levers.

---

## Detection sub-design decision (resolved, to be CONFIRMED by the harness numbers)

**Recommend: DETECT-THEN-NEUTRALIZE** (a lightweight loaded-question classifier gates the rewriter; only
flagged-loaded questions are rewritten), NOT always-neutralize. Rationale: real traffic is mostly neutral
information-seeking; always-rewriting every question maximizes the over-sanitize blast radius (target 2)
on questions that never needed it. Detect-then-neutralize confines the rewrite to the loaded minority.
**Risk:** a false-negative classifier leaves a loaded question unprotected; a false-positive triggers an
unnecessary (but, if the rewriter is intent-preserving, harmless) rewrite.

**The harness evaluates BOTH so the recommendation is data-backed, not assumed:**
- the **detector's accuracy** (loaded set → flag loaded; clean set → flag neutral) — precision + recall;
- the **rewriter on clean/neutral** questions (always-neutralize's exposure) — does it change a faithful
  answer's correctness? (the don't-break-clean + don't-over-sanitize tests).
If the detector is accurate AND the rewriter is NOT idempotent-safe on clean → detect-then-neutralize.
If the rewriter proves idempotent-safe on clean → always-neutralize is acceptable + simpler. Decide from
the numbers.

---

## TWO FIRST-CLASS VALIDATION TARGETS (designed up front)

**(1) CROSS-TOPIC GENERALIZATION.** Multi-topic loaded set, **source-in-hand only** (the anchor must be
in the frozen pool — else it's a Lever-1 retrieval-miss, excluded + noted). Per-topic reporting, never
pooled-only. Candidate topics (author loaded framings; the harness retrieves each + confirms anchor-in-
pool at build): **polypharmacy** (35268461, protective→pushed-harm), **beta-blockers in HFrEF** (29040525,
protective→pushed-harm), **early peanut/LEAP** (25705822, protective→pushed-harm), **smoking→Parkinson's**
(protective/inverse→pushed-harm), **beta-carotene in smokers** (ATBC/CARET, harmful→pushed-benefit). Mix
of both reversal directions. **A result that only holds on polypharmacy is NOT a pass** — report per topic;
topics whose anchor isn't retrieved under the loaded query are reported as retrieval-miss (Lever-1), not
counted in reversal-reduction.

**(2) OVER-NEUTRALIZATION = the FP-analog (gating risk).** Frozen clean/neutral control set + denominator
BEFORE running. Three measures:
- **INTENT-PRESERVATION:** LLM judge (+ spot-checks) — does the neutralized question still ask what the
  user asked (no dropped constraint / changed scope / changed factor→outcome)?
- **DON'T-BREAK-CLEAN:** on already-neutral questions that produce faithful answers, neutralization must
  NOT change the answer's correctness. Generate original-arm vs neutralized-arm on the SAME frozen context;
  the neutral arm must not REGRESS a faithful answer. Report over-trigger (detector firing on clean) +
  clean-answer regression rate against the frozen denominator.
- **DON'T-OVER-SANITIZE:** neutralization must not strip a genuinely important clinical qualifier (e.g.
  "in elderly patients on 5+ drugs" → generic "polypharmacy"). Author qualifier-bearing controls; flag any
  loss. (LLM intent judge + explicit qualifier-retention check.)

---

## Corpus (frozen pre-run — `tests/question_neutralization_corpus.json`)

- **loaded_topics:** per topic — anchor PMID, correct direction, factor→outcome, 2 loaded framings, the
  representative loaded retrieval query. The harness retrieves once per topic, freezes the context, records
  `anchor_in_pool` (source-in-hand gate).
- **clean_control (over-neutralization denominator, n frozen):** already-neutral questions (incl. plain
  golden R-set + qualifier-bearing ones to stress over-sanitize). Criterion: "information-seeking framing
  with no directional presupposition; produces a faithful answer; includes ≥3 with an important clinical
  qualifier to test retention."
- Selection criteria (loaded-vs-neutral; clean) frozen in the record before generating. Full-prose per arm
  persisted (no counts-only — the o4-mini "3/3" lesson).

## Cost projection (state BEFORE the run; this is the most expensive lever)
Live-generates BOTH arms (gpt-4.1) across topics, N=3 samples/framing for a rate. ~5 topics × 2 loaded
framings × N=3 = ~30 loaded gens + 30 neutralized gens; clean ~8 × 2 = 16 gens → ~76 gpt-4.1 generations.
Plus detector/rewriter/judge small calls (~150). **Projected ≈ $2–3.** Retrieve-once-freeze per topic
(only generation re-runs). Report ACTUAL cost.

## Files touched · flag · rollback
- **NEW** `api/services/question_neutralization.py` — `is_loaded(question)` detector + `neutralize(question)`
  rewriter (async; provider abstraction; intent-preserving, qualifier-retaining).
- **EDIT** `api/server.py` — flag-gated rewrite of the generator question behind
  `QUESTION_NEUTRALIZATION_SHADOW` (default OFF → `body.question` unchanged). Seam realization only;
  validation is in the harness.
- **NEW** `scripts/question_neutralization_eval.py` — A/B harness (retrieve-once-freeze per topic, generate
  both arms ×N, reuse `judge_direction`, intent + clean-regression + detector accuracy), persists
  `tests/results/question_neutralization_*.json`.
- **NEW** `tests/question_neutralization_corpus.json` — frozen corpus.
- **Rollback:** flag OFF = no-op; revert. No migration.

## Out of scope
③/C1 (deferred); Lever 1 (done); the route; A2/enforcement (always-vs-detected ON in prod, thresholds).
This round = A/B harness + shadow flag (OFF) + validation numbers. No enforcement.

---

## Build refinements (smoke/run findings)
- **Vague-loaded framings, not explicit.** Explicit loaded framings ("…that increases mortality / worsen
  survival") SELF-CORRECT (the probe's L2 nuance) → 0 reversal. The reversing framing is the VAGUE harm/
  benefit presupposition ("why is X a serious problem"). Corpus framings set to vague-loaded.
- **Source-in-hand gate relaxed** from exact-anchor-PMID to "correct/counterintuitive direction present in
  the pool via ANY source" — the exact-PMID gate wrongly marked beta-blockers/peanut/CAST as retrieval-miss
  when their protective direction is retrievable via other papers.
- **Intent judge fixed** to NOT count presupposition-removal (the intended transformation) as an intent
  violation — only genuine clinical-qualifier loss counts.

## RESULTS — A/B shadow validation (2026-06-18; gpt-4.1; `question_neutralization_20260618_110411.json` [N=5, relaxed gate] + de-risk `…_104531.json`)

**Design CONFIRMED = detect-then-neutralize** (detector accurate on strong-loaded + 0/16 over-trigger on
clean → safe to gate the rewriter; confines rewrites to loaded questions).

**REVERSAL REDUCTION — PER TOPIC (loaded → neutral, N=5×2 framings = /10):**
| Topic | source-in-hand | loaded REVERSED | neutral REVERSED |
|---|---|---|---|
| **polypharmacy** | yes (anchor in pool) | **4/10** | **0/10** ✅ eliminated |
| beta_blockers_hfref | yes (direction present) | 0/10 | 0/10 |
| beta_carotene_smokers | yes (anchor in pool) | 0/10 | 0/10 |
| cast_antiarrhythmics | yes (direction present) | 0/10 | 0/10 |
| peanut_leap | NO (empty pool, FDA-500 + relevance-filtered) | — | retrieval-miss (Lever-1) |

**HONEST VERDICT — NOT a cross-topic pass; the lever is SAFE + EFFECTIVE-where-reversal-occurs, but the
reversal phenomenon itself is NARROW:**
- Where loaded-framing reversal occurs (**polypharmacy**), neutralization **eliminates it: 4/10 → 0/10**
  (reproduces the probe; also 4/6→0/6 in the de-risk realization). Strong.
- **The other 3 source-in-hand topics do NOT reverse under loaded framing at all (0/10 each)** — verified
  REAL (not judge misses): the model answers faithfully even when asked "why are beta-blockers a concern"
  ("cornerstone… lower mortality HR 0.66") / "why do smokers take beta-carotene" ("RCTs showed harm").
- So per the founder's bar ("a result that only holds on polypharmacy is NOT a pass"): **reversal-reduction
  is demonstrated on polypharmacy ONLY.** The limiting factor is NOT the lever — it is that source-in-hand
  loaded-framing reversal is **largely confined to the conflation-trap structure** (multimorbidity OR 1.82/
  2.04 co-located with polypharmacy OR 0.78 in the same abstracts → the vague-loaded framing makes the
  model grab the harm stat). Topics with clean single-direction abstracts stay faithful.

**OVER-NEUTRALIZATION (the gating risk) — PASSES strongly (clean control n=8/run, 16 total):**
- detector over-trigger (flagged a clean question as loaded): **0/16**.
- intent / qualifier-retention failures: **0/16** — every clinical qualifier (elderly/AF/HFrEF/infants/
  renal-impairment/diabetic) preserved; only the directional presupposition removed.
- clean-answer regression: 1/8 each run BUT a DIFFERENT case each time (CLN-7, then CLN-5) and **both are
  generation-stochasticity artifacts** — CLN-5's neutralized question was IDENTICAL to the original, so the
  "regression" was two independent generations differing in completeness, not a neutralization effect.
  **→ 0 real regressions.** (Caveat: the clean-regression metric is inherently confounded by generation
  variance — it compares two independent generations.)
- detector accuracy: flagged ALL strong-loaded framings correctly; missed only BCAR-LA (the weak "why are
  they popular" benefit framing — defensibly ambiguous, not a clear presupposition).

**Cost: $1.11 (run 2) + ~$0.45 (de-risk).** Per-query production cost (detect-then-neutralize) ≈ 1–2
gpt-4.1 calls ≈ cents.

**Net:** the lever is SAFE (over-neutralization passes; intent preserved) and ELIMINATES reversal where it
occurs, but its addressable surface is NARROW (loaded-framing source-in-hand reversal ≈ polypharmacy-type
conflation traps). Two-lever coverage = Lever 1 (retrieval-miss, obesity-type, validated) + Lever 2
(source-in-hand loaded reversal, polypharmacy-type — narrow). `QUESTION_NEUTRALIZATION_SHADOW` stays OFF;
A2/enforcement (and whether the narrow benefit justifies enabling) is route/founder-gated.
**Caveats:** 4 source-in-hand topics, 2 vague framings/topic, N=5, single frozen context/topic (reversal is
pool-dependent); stronger/other framings or contexts might surface reversal on more topics — directional,
not exhaustive.
