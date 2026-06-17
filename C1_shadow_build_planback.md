# C1 (③ Direction-Checker) — SHADOW Build Plan-Back

> **Where this was produced vs where it runs.** This plan-back and the reference
> `direction_checker.py` were produced in the Claude **chat** environment, which has
> **only the project docs** mounted read-only — **not** the Vela repo, prod, or OpenAI
> access. So the *execution* steps (push `96806b5`, capture the reference baseline against
> prod, run the 1-call probe, shadow-validate against real runs) **must run inside the repo**
> (Claude Code / your dev box). This document is the A1 §0 "plan-back before code" gate plus
> the validated-design lock — the artifact that must exist *before* any code is written.
>
> **No fabricated results.** No reference-run numbers, baseline, or shadow-validation results
> appear here or anywhere from me — those exist only once it runs in-repo. Inventing them on a
> launch-gating medical-safety check would be the one unrecoverable error.

---

## 0. Carry-forward (A1 §0)
First prod-code touch. Prior cheap / scratch / zero-deploy discipline does **NOT** apply.
Non-negotiables: **plan-back before code** (this doc) · **shadow-first** (C1 surfaces nothing) ·
**golden re-baseline gates the merge**.

---

## 1. In-repo gate runbook — do these in the repo, in order

**Gate 1 — auto-recharge probe (founder says ON; verify, don't trust).**
- Make **one real** OpenAI call through the normal provider path (a trivial Research/Verify call,
  or a direct `provider.complete("ping")`).
- If it returns `[ERROR]` / credit-zero / a billing 4xx → **STOP, report, do not proceed.**
  A dead-balance baseline is silently void.
- If healthy → proceed.

**Gate 2 — `96806b5` fold-in = decision (i).**
- `git push` `96806b5` (generator fidelity fix) + `fdd624c` (holdout) **first**; deploy so prod
  reflects it.
- THEN take the §2 reference baseline **with `96806b5` live**, so C1's later delta is attributed
  to C1, not to the fix.

---

## 2. §1 harness — golden re-baseline (build FIRST; gates everything)

- **Freeze corpus:** the 127-case golden set + the adversarial-contradiction set (the sets behind
  `golden_results_*` and `adversarial_contradiction_*`). Pin exact case IDs + inputs as an
  **immutable** baseline corpus.
- **Reference run:** current prod behavior — gpt-4.1, post-§2.7, **WITH `96806b5`** (gate 2).
  Capture **full-prose** answers + cited sources per case, **not counts-only** (counts-only burned
  us before — the o4-mini "3/3" that didn't reproduce on a persisted re-run).
- **Targeted vs non-targeted split:** tag the known-reversal cases (C01 polypharmacy, C03 glucose,
  C15 DBP, B01 loaded, …) as *targeted*; everything else *non-targeted*.
- **Gate rule:** every A1 PR re-runs the harness. **Non-targeted answers must not move.** For C1
  specifically (shadow), *nothing* moves — C1 touches no answer; the harness here scores C1's
  *flagging* against the frozen answers, not a behavior change.
- **Judge:** reuse the existing direction-of-effect judge (`citation_truth_check.py --adversarial`
  direction judge) so flag-correctness is scored consistently with prior runs.
- **Prereq:** gate 1 green.

> ⚠️ **Coupling I could not pre-write:** the runner is tied to your golden-set schema + the
> existing `--adversarial` harness, neither of which is in this env. The spec above is complete;
> implement the runner against the real `citation_truth_check.py` in-repo.

---

## 3. C1 — ③ direction-checker (SHADOW, flag-only)

Reference core logic provided separately: **`direction_checker.py`**.

**Contract.** Input: the generated answer (full text), the question, and the answer's cited sources,
each with its **FULL abstract** + the source's own reported effect. Output:
`DirectionFlag(flagged, reason, selected_anchor, verdict)`. **SHADOW:** log it to a sink; surface
**NOTHING** to the user.

**Validated design — build exactly this; the MUST-NOTs are documented failures:**

1. **Anchor = counterintuitiveness-vs-prior**, judged from each source's OWN finding + model prior,
   **independent of the answer's claim**. Pick the most counterintuitive cited source.
   - ❌ MUST NOT use naive "the source the answer's main claim is based on" → circular + whitewashing
     (0/3; auto-finds the source that makes a reversed answer look fine).
2. **FULL abstracts.** ❌ MUST NOT truncate (~700-char → 0/3; the protective stat is buried deep in
   stat-dense abstracts that lead with the higher finding).
3. **Whole-answer vs anchor** direction comparison. ❌ MUST NOT per-claim decompose → the
   decomposition-anchoring false-negative (a real reversal slipped through on empty `cited_pmids`).
4. **Structural trigger (the dep-(b) constraint).** Independently detect the *situation* "answer
   cites ≥2 opposite-direction counterintuitive sources on the same factor→outcome" → flag
   **unconditionally**.
   - ❌ MUST NOT gate the flag on the selector's self-reported confidence — the fail-safe leg is
     unvalidated and the selector is overconfident on contested topics (uniform 0.9, wrong-but-0.8
     on HRT). Safety rests on **situation-detection**, not on the selector grading itself.
5. **Flag-only output.** No withhold / block this round (that is A2, route-dependent).

**Integration seams — confirm in-repo, do NOT hardcode:**
- **Hook point:** **downstream of the generator** in the Research path (`server.py` SSE, *after* the
  answer + citations are assembled). **Confirm exact stream/citation line refs at build time**
  (TECH_DEBT note — don't hardcode from memory).
- **Cited sources + full abstracts:** from the retrieval result the generator used; the full abstract
  may need a fetch by PMID — wire `fetch_full_abstract`.
- **Shadow sink:** a shadow log / telemetry sink (a `direction_flag` event/table?), **NOT** the SSE
  stream. Flag-only, invisible to users.
- **LLM call:** route through the §2.1 Provider abstraction (cheap model — gpt-4.1-mini per the
  feasibility runs).
- **Do NOT** re-attempt the failed `(i)` retrieval-prompt rewrite — closed lever.

---

## 4. Shadow validation (in-repo, after C1 lands behind its flag)

Run C1 over the frozen golden/adversarial corpus (the §2 reference answers):
- **Detection:** does it flag the known reversals? (feasibility target was 4/4 on real answers under
  coarse + counterintuitiveness-selection + full abstracts.)
- **FP:** acceptable false-positive on clean faithful answers? (the C01-115632 mixed-answer FP is
  defensible; watch the rate.)
- **Non-targeted unmoved:** trivially true (shadow touches no answers) — but confirm no accidental
  coupling changed any answer.
- Report the **real** numbers from this run. (They don't exist until it runs in-repo; I will not
  invent them.)

---

## 5. Commit sequence (A1 §0: plan-back → code → re-baseline)
1. this plan-back (docs) — the pre-code gate.
2. §2 harness (+ frozen corpus, reference run **with** `96806b5`).
3. C1 module behind a flag, shadow-only (`direction_checker.py` adapted to real seams + the hook +
   the shadow sink).
4. shadow-validation run → numbers into the commit / STATE update.
- **C2/C3 do NOT start until C1 lands. A2 stays out of scope.**

---

## What to report back (from the in-repo run — real numbers only)
- gate-1 probe result (healthy / dead).
- harness built + reference run captured (case count; with-`96806b5` confirmed).
- C1 shadow: detection on known reversals · FP on clean · non-targeted unmoved.
