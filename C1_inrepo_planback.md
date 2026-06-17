# C1 (③ Direction-Checker) — IN-REPO Seam Confirmation + Plan-Back (A1 §0 pre-code gate)

Produced **in-repo** (Claude Code) by reading the real Vela source, to satisfy the
`C1_shadow_build_planback.md` §0 requirement: *confirm the real seam interfaces before writing
code; if a real interface contradicts a seam assumption, surface it and STOP rather than guess.*

This is the companion to the chat-produced authoritative spec (`C1_shadow_build_planback.md`) and the
validated reference core (`direction_checker.py`). Where reality differs from the reference core's
`# SEAM:` assumptions, the reconciliation is recorded below. **No invented results.**

---

## Gate status (in-repo)

- **GATE 1 — credit probe: HEALTHY.** One real completion through the §2.1 provider path
  (`get_lightweight_provider()` → openai/gpt-4.1-mini, `provider.complete`) returned a real token
  string. Not credit-zero, no billing 4xx. → proceed.
- **GATE 2 — push: NO-OP at git level.** `96806b5` (generator fidelity fix) + `fdd624c` (holdout)
  are **already on `origin/main`** (pushed in an earlier batch; the STATE "NOT pushed/deployed" note
  is stale re: *push*). The only unpushed commits are the **8 docs commits** — which stay unpushed
  per the push constraints. So "push 96806b5+fdd624c" requires no new push.
- **GATE 2 — deploy: DEFERRED (founder decision 2026-06-17).** No Fly prod release this round. The
  baseline is captured with `96806b5` live in HEAD via the in-process prod code path (see
  §Methodology). The founder fires `.\deploy.ps1` separately when they want the fix in front of users.

## Decisions (founder, 2026-06-17)
- **Fly deploy: DEFERRED** — decoupled from C1; not a prerequisite.
- **Reference-run scope: direction-relevant + FP sample** (NOT the full 127 live). For a shadow
  checker that touches no answer, "non-targeted unmoved" is structural, so live-running the ~100
  non-direction golden cases buys no signal. C1's only launch-gating signals: **detection** (reversals
  flagged) + **false-positive** (clean-faithful answers wrongly flagged) — both from direction-relevant
  cases. **FP-denominator discipline (mandatory):** concrete target n, representative (no cherry-pick),
  **selection criterion frozen into the corpus record BEFORE generation**, every selected case run
  FULL-PROSE. **Freeze** the full 127-golden + adversarial IDs as the immutable corpus record
  (separate from what runs live). **Report** detection X/Y (which flagged/missed) + FP a/b WITH the
  denominator n and the frozen clean-faithful definition + a **scope caveat** (this FP is on a
  direction-adjacent sample = C1's mis-fire rate on the answers it acts on, NOT a site-wide FP rate).

## Methodology — in-process generation (recorded rationale)
The reference answers are generated **in-process** via the exact prod code path
(`retriever.retrieve(...)` → `generator.generate_stream(...)`, `96806b5` in HEAD, gpt-4.1, no
model_override), matching the validated feasibility runs (neutralization probe / dep (a) / dep (b)).
Rationale: (1) it is byte-faithful to prod answer behavior (server.py calls these same two functions;
guards/PHI/credit are pre-generation gates that do not alter answer content); (2) it yields the
**full** `RetrievedDocument.content` abstracts the generator actually saw → satisfies invariant 2
directly with **no re-fetch** (the cleanest full-abstract source — C1 checks exactly what the
generator read). `judge_direction` (gpt-4.1, abstract-only) is still reused for ground-truth
corroboration so scoring stays consistent with prior runs. The `server.py` shadow hook (the "wired to
real seams" deliverable) is built + flag-gated separately; the validation NUMBERS come from this
offline harness calling C1's `check()` on the captured (answer, documents).

---

## Seam reconciliations (reference-core assumption → real repo)

1. **Provider LLM call.** Core assumes `LLMComplete = Callable[[str], str]` (sync, prompt→string).
   Real interface: `Provider.complete(req: CompletionRequest) -> CompletionResponse` is **async**
   (`api/providers/base.py`). → Wire an **async adapter**: `await binding.provider.complete(
   CompletionRequest(model=binding.model, messages=[{"role":"user","content":prompt}],
   temperature=0, response_format={"type":"json_object"}))` returning `.content`. Cheap model via
   `get_lightweight_provider()` (gpt-4.1-mini), matching the feasibility runs. The in-repo C1 module
   is therefore **async**; it ports the core's *logic* verbatim (anchor selection / whole-answer vs
   anchor / structural trigger), only the I/O becomes async.

2. **`fetch_full_abstract` does NOT exist in the repo.** It is named only in the spec + core.
   Two real sources of the FULL abstract:
   - **In-process pipeline:** `RetrievedDocument.content` = `article.to_text()` (the *full* abstract
     the generator actually saw; `api/rag/retriever.py:427`). The same `documents` list is already
     handed to the existing `_run_judge_background` hook.
   - **From a captured SSE answer:** SSE `citations` carry only `snippet` = `content[:500]` (the
     **truncation footgun**, `schemas.py:127`). So re-fetch the full abstract by PMID via
     **`PubMedClient.fetch_details([pmid])[0].abstract`** — the exact call the existing
     `--adversarial` harness uses. **This is the real `fetch_full_abstract` seam.**
   → C1 must read full abstracts from `document.content` (in-process) or `fetch_details` (from a
     captured answer). It must **never** use the 500-char citation `snippet` (invariant 2).

3. **Hook point — confirmed, with an existing precedent to mirror.** `api/server.py` Research SSE
   path fires, at the `DONE` event, a **non-blocking background task**:
   `asyncio.create_task(_run_judge_background(audit_id, body.question, full_answer, documents))`
   (`server.py:752-755`; the fn at `:494`). This is exactly the shadow contract: downstream of the
   generator, after `full_answer` + `documents` are assembled, **does not touch the SSE stream**,
   surfaces nothing to the user. → C1's shadow caller mirrors `_run_judge_background`: a sibling
   `_run_direction_check_background(audit_id, question, full_answer, documents)` fired the same way,
   **behind an env flag** (default OFF). (Note: the existing judge runs L1/L2 only — fine; shadow
   coverage of signed-in traffic is sufficient and anon path is out of scope.)

4. **Shadow sink.** Two non-SSE sinks already exist as precedent: `logger` + `AuditLog.extra_data`
   (the judge writes `log.extra_data["llm_judge"]`). → C1 logs the flag via `logger` and (when an
   `audit_id` row exists) writes `AuditLog.extra_data["direction_flag"]` = the `DirectionFlag` dict.
   For the **offline shadow-validation run** the sink is a JSON results file under `tests/results/`.

5. **Judge reuse for flag-correctness scoring.** Reuse `judge_direction` (gpt-4.1, abstract-only,
   `citation_truth_check.py:365`) so scoring is consistent with prior runs. Caveat to record: that
   judge is **per-claim-pair** (`same|reversed|...` for one sentence↔one PMID), whereas **C1 emits a
   WHOLE-answer flag** (invariant 3). They are not the same unit. Scoring approach: C1's flag is
   scored against the **ground-truth reversal label** of each case (known reversals from the eval
   sets / prior persisted runs), with the per-pair `reversed` signal used as corroboration — not as
   C1's own mechanism (C1 must stay whole-answer, never per-claim, to avoid the decomposition FN).

6. **Baseline capture path — DEV backend, not Fly prod.** The harness POSTs to `TEST_BASE_URL`
   (`/api/research` SSE) and `_guard_env()` **aborts unless `DATABASE_URL` is the dev branch**
   ("refusing — answer-gen would hit the wrong DB"). So the reference baseline is **structurally
   captured against a dev/local backend**, never Fly prod. Running that backend on current HEAD code
   (which contains `96806b5`) satisfies "baseline with the fix live" independent of any Fly deploy.

---

7. **Truncation guard retargeted (smoke-test finding, invariant 2).** The reference core's
   `_require_full_abstracts` raised on `len<=750 AND no terminal punctuation` — a blunt heuristic that
   **false-positives on genuinely short real abstracts** (smoke: C01's PMID 32448024 is a 746-char
   *complete* abstract; `to_text()` embeds `self.abstract` verbatim, confirmed no upstream truncation
   — so it hard-errored the flagship polypharmacy case). Invariant 2 is **not** weakened: the wiring
   structurally guarantees the full abstract (`cited_sources_from_documents` reads
   `RetrievedDocument.content`, never the snippet). The runtime guard was retargeted to the **actual**
   footgun signature — the 500-char citation snippet (`content[:500] + "..."`): raise on empty, or on
   `endswith("...") and len<=520`; short full abstracts log a warning and proceed. Recorded so the
   change to a validated-core guard is traceable.

## Deploy reconciliation (surfaced for founder — §0 "surface, don't guess")

GATE 2 says "deploy so prod reflects `96806b5`, THEN capture the baseline with the fix live." Three
in-repo facts the instruction predates:

- **Push is already done** (96806b5 + fdd624c on origin/main).
- **Deploy can't cherry-pick:** `.\deploy.ps1` ships current **HEAD = main**, which over the deployed
  v180 (`0e03659`) carries **3** prod-code files: `generator.py` (+5 = 96806b5, intended),
  `openai_provider.py` (+56/-8 = reasoning-param contract — verified **gpt-4.1 byte-identical**: the
  default branch is unchanged; the reasoning branch only triggers on `o1/o3/o4/gpt-5` prefixes), and
  `cost_tracker.py` (+6 = additive o4-mini/gpt-5.4 pricing rows). All already on origin/main; none
  change gpt-4.1 generation behavior. So a HEAD deploy is **behavior-safe** but is *more than the two
  named commits*.
- **The baseline does not need the Fly deploy** (it hits a dev backend, per reconciliation #6). The
  attribution goal ("delta is C1, not the fix") is met by running the dev backend on HEAD.

→ The Fly prod deploy is therefore a **separate production release** (founder decision (i): put the
fidelity fix in front of real users now), not a technical prerequisite for the C1 build/baseline.
Confirm before firing (outward-facing, hard-to-reverse, scoped differently than described).

---

## Files touched · flag/branch · rollback

- **NEW** `api/services/direction_checker.py` — the in-repo C1 module (async port of the reference
  core; same invariants). Self-contained logic; provider-adapter + full-abstract inputs injected by
  the caller.
- **EDIT** `api/server.py` — add `_run_direction_check_background(...)` and fire it at the Research
  `DONE` event **behind an env flag** `DIRECTION_CHECK_SHADOW` (default **OFF** → zero prod behavior
  change; no SSE change; no answer change). Mirrors `_run_judge_background` exactly.
- **NEW** `scripts/direction_shadow_eval.py` — offline harness: load a frozen corpus of captured
  answers + cited PMIDs, fetch full abstracts via `fetch_details`, run C1's `check()`, score flags vs
  ground-truth, persist `tests/results/direction_shadow_*.json`.
- **Corpus freeze** — pin the case IDs + inputs of the 127-golden (`tests/golden_dataset.json`) + the
  adversarial-contradiction set (`ADVERSARIAL`, 24 cases) + `loaded_framing_set.json` as an immutable
  list recorded in the results artifact.
- **Flag/branch strategy:** all C1 code is inert unless `DIRECTION_CHECK_SHADOW=true`. Committed
  **locally, not pushed** this round. Shadow validation runs offline against the captured baseline.
- **Rollback:** flag OFF = no-op; revert the two commits if needed. No migration, no schema change
  (AuditLog.extra_data is an existing JSON column).

## Out of scope (unchanged)
C2, C3 — queued after C1. A2 (flag-only vs withhold vs block, thresholds, neutralization mandate) —
route-gated; C1 ships at the strictest-reasonable shadow / flag-only default so A2 can tighten
without rebuild.

---

## RESULTS — shadow validation run (2026-06-17, `direction_shadow_20260617_143022.json`, gpt-4.1 generator, 96806b5 in HEAD)

Live subset = 43 (25 targeted + 18 clean-faithful). Ground truth = reused gpt-4.1 direction judge.
**REAL numbers — C1 as-built FAILS shadow validation. Do NOT enable `DIRECTION_CHECK_SHADOW` in prod
until redesigned.**

| Config | Detection (actual reversals) | False-positive (clean-faithful) | Overall flag rate |
|---|---|---|---|
| **Structural ON (as-built, invariant 4)** | **11/11** | **12/16 (75%)** | **37/43 (86%)** |
| **Structural OFF (primary whole-answer-vs-anchor only)** | **0/11** | **1/16 (R04)** | 1/43 |

- **Detection 11/11 is an artifact**, not a win: the structural trigger flags 86% of ALL answers
  (35/43 verdict=`structural`), so it "catches" every reversal only by flagging almost everything.
  It rubber-stamped `two_opposite_counterintuitive=True` on unambiguous single-direction topics
  (H4 peanut-LEAP, HD-BB beta-blockers-HFrEF, R05 serotonin-syndrome, R10 digoxin, C06 BB-in-COPD).
  The cheap gpt-4.1-mini detector has **no precision** on real 4–5-source retrievals.
- **Primary path detects 0/11.** Three root causes, mechanistically confirmed:
  1. **Conflation inside C1's own scorer** — P-L1: the protective anchor 35268461 *was* retrieved, but
     `_score_counterintuitiveness` read `increases (OR 2.04)` (the multimorbidity composite) instead of
     polypharmacy `OR 0.78`. **C1 fell into the exact B01 conflation trap it exists to catch.**
  2. **`_opposite` label brittleness** — OB-L1: anchor `mixed (U-shaped)` vs answer `decreases` →
     deterministic compare returns False, missing a real reversal (the reference core flagged this).
  3. **Retrieval-miss** — C01: protective anchor not retrieved → answer faithful to its conventional
     sources → genuinely `consistent` (③'s designed blind spot, not a C1 bug).
- **FP-denominator note:** clean-faithful denom = 16 (R01, R03 excluded — judge called them reversed:
  both cited a genuine dissenting counterintuitive source). Denom is **direction-ADJACENT**, NOT
  site-wide: this is C1's mis-fire rate on the answers it acts on, not a whole-product FP rate.

**Verdict:** the dep(a) 5/5 / dep(b) 4/4 / coarse 4/4 feasibility validations used hand-curated
synthetic source bundles + curated answers and **did NOT generalize** to the real pipeline. On real
retrievals C1 is unusable in BOTH configs (structural = no precision; primary = no recall). C1 needs a
**fundamental rework, not tuning** — see STATE / TECH_DEBT. Shadow-first caught this before any user
exposure (the build's whole purpose). Pushed nothing; Fly deploy still deferred.
