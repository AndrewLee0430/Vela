# TECH_DEBT.md — Vela Pre-Existing Gaps & Polish Items

Active tech debt entries identified during shipping. Format preserved verbose because each entry is dense diagnosis context — compressing to a table loses why/how-to-apply specificity.

**Priority levels**:
- **[P0]** — blocks shipping or user-facing
- **[P1]** — affects code quality or upcoming task
- **[P2]** — best practice / future maintenance
- **[P3]** — quality-of-life / cosmetic / opportunistic (added 2026-05-06 during §4.5 UX polish 3/3 — supersedes the earlier "no P3 tier" claim in the [P2] No backend PostHog client entry)

**Resolution targets**:
- "→ Phase 0 Retrospective" — work in retro phase
- "→ Phase 1A polish" — work after Phase 0 ends
- "→ next opportunity" — when convenient

When entries are resolved, mark with the resolving commit SHA (git log is the record), then remove.

---

- **[P1 · FIXED v192 (2026-06-30, commit `0a26250`) — data-cleanup / unbounded growth, privacy-retention] `_cleanup_old_records` filtered a non-existent `AuditLog.created_at` (2026-06-25, pre-existing → FIXED)**
  - **What (probe-confirmed 2026-06-30):** the daily retention job (`api/server.py:190`) filtered `AuditLog.created_at`, which does NOT exist on the model — the column is **`timestamp`** (`sql_models.py:9`). Every daily run raised `AttributeError` (caught + logged "Data cleanup error", loop never crashed). The job IS invoked (`lifespan` → `asyncio.create_task`, `server.py:205`), so it ran daily and accomplished nothing.
  - **Probe verdict = P1, NOT P3 (resolves the old PRIORITY-DECIDING question (ii)):** records were NOT being cleaned → **unbounded growth**, breaking the 180-day retention the privacy policy PROMISES (`privacy.tsx:47` "automatically deleted after 6 months"; `PRD.md:2146` "180 天保留，到期自動刪除").
  - **⚠️ COLLATERAL the old entry MISSED:** because the `AuditLog` delete on line 190 threw FIRST, the `ChatHistory` delete on line 191 (whose `created_at` IS valid) **never executed either** → **`chat_history` was ALSO accumulating unbounded**, not just `audit_logs`. The bug skipped BOTH tables.
  - **Boundary (probe):** the job touches ONLY `audit_logs` + `chat_history`; it NEVER references `user_usage`/billing/the design-E 5yr statutory hold. Both tables are non-statutory (hard-deletable on request per the deletion SOP; the policy promises 6-month auto-purge). 180 days = exactly the promised window.
  - **Fix:** one column reference `AuditLog.created_at → AuditLog.timestamp` (line 190); line 191 already correct and now actually runs. Dev throwaway-DB delete-path test: deletes ONLY >180-day rows in both tables, keeps recent rows, never touches `user_usage`, no AttributeError. **Blast radius = 0** (prod oldest row 2026-03-19; cutoff 2026-01-01 → 0 rows >180 days; first run deletes 0). Deployed v192; prod READ-ONLY count confirmed `audit_logs` 998 / `chat_history` 1276 both `>180d=0` before AND after deploy (data undisturbed). The daily loop (`sleep 86400`) first fires ~24h post-deploy.
  - **Discovered:** 2026-06-25 (v189 log review). **Probed + fixed:** 2026-06-30.

- **[P1 · medical-safety / display — FIXED v194 (2026-07-03, commit `aac164f`) — 2026-07-01 recon finding, previously UNRECORDED] Ambiguous-brand defer rendered as "No interactions found" — a refused verification displayed like a clean result**
  - **What:** Verify's ambiguous-brand DEFER path (`api/server.py`: returns `interactions=[]`, `risk_level="Unknown"`, the defer explanation ONLY in `summary` prose) met the frontend's enum-authority design (`pages/verify.tsx` recomputes the summary line from `interactions` and NEVER renders `result.summary`) → the zero-length-interactions branch showed the clean-result copy (`noInteractions`, 「未發現交互作用」) + a neutral "Unknown" badge. **A refusal displayed as reassurance** — the user asked to verify 太田胃散-type ambiguous brands and saw what reads as a clean pass.
  - **Root cause:** the same seam as the grounding-note entry below — defer information lived ONLY as prose inside `summary`, which the UI by design never renders (the enum-authority / wrong-language fix); the zero-length branch then defaults to clean-result copy. Discovered as GAP B during the 2026-07-01 read-only seam recon (the recon that answered the entry below's probe question).
  - **Fix (v194, `aac164f`):** structured emission — additive `verification_status` ("ok" | "deferred_ambiguous_brand") + `deferred_brands` on `VerifyResponse` (`summary` prose UNCHANGED — Share/FeedbackBar contract); `pages/verify.tsx` renders a warning-styled deferred block (names the brands, pharmacist/INN advice) + a "Not Verified" badge override instead of the clean presentation; 16-locale i18n. Payload shape pinned by `tests/test_verify_tfda_payload.py` (real-endpoint defer test — deterministic T2a path, zero LLM/FDA calls). **Human-eye gate: PENDING founder** (Verify = medical-output surface; API-level prod probes cannot see UI render).
  - **Discovered:** 2026-07-01 (recon). **Fixed:** 2026-07-03.

- **[P2 · transparency / UI-completion — FIXED v194 (2026-07-03, commit `aac164f`)] v191 T2a brand→ingredient grounding note not rendered in the Verify UI**
  - **RESOLVED (2026-07-03, v194 `aac164f`) — the ⚠️ seam probe below is ANSWERED:** the transparency text WAS in the `/api/verify` payload, but ONLY as prose merged into `summary` (`server.py` "TFDA grounding — …" prefix) — and the frontend **by design never renders `result.summary`** (enum-authority: the Summary line is recomputed frontend-side from `interactions`; `summary` only feeds FeedbackBar + Share answerText). So the verdict = **BACKEND-EMIT + FRONTEND-RENDER**, not the hoped-for pure frontend render fix. Fixed by additive structured emission — `tfda_groundings` ({query, ingredients, is_combo, licenses} per resolved brand) on `VerifyResponse`, populated at all 4 return sites from the already-computed deterministic resolutions (pass-through; zero prompt/generation contact) — rendered as a localized, visually-subordinate provenance note (5 new i18n keys × 16 locales in `i18n-ui.ts`). `summary` prose unchanged. **Human-eye gate: PENDING founder.**
  - **What:** on the Verify 「仍要送出（不建議）」 proceed-anyway path a Chinese brand now resolves correctly (冠脂妥 → ROSUVASTATIN CALCIUM, v191) and the analysis is right, BUT the grounding-transparency line explaining *why* — 「冠脂妥 = ROSUVASTATIN CALCIUM（per TFDA 許可證）」 — is present in the backend Verify summary yet **does NOT render in the frontend**. User sees a correct analysis with no visible disclosure that a deterministic TFDA brand→ingredient substitution happened. This is the T2a UI finish v191 missed (v191 shipped the resolver + prod-verified the analysis; the transparency-render was not closed).
  - **⚠️ Probe-to-confirm the seam (CC, BEFORE building):** confirm whether the transparency string is actually in the `/api/verify` response payload. **IF yes** → pure frontend render fix (display-only, low-risk, no §2.7). **IF the backend does NOT emit it** → slightly more (backend surfaces resolved-INN + source into the payload, then frontend renders) — still small, touches the Verify result shape. Founder prod observation = "backend summary has it, frontend doesn't render" → most likely the former, but the payload check decides.
  - **Risk note:** rendering an already-computed deterministic mapping is a transparency DISCLOSURE, not a change to the medical analysis → not a generation/prompt change. Likely display-only pending the seam probe; still human-eye verify (Verify = medical-output surface).
  - **Cross-ref:** STATE v191 (T2a `7c50fd6`). The grounding-lite follow-ups (a1-i..a1-iv, BACKLOG) are the **v193 Research** family — this is the DISTINCT **v191 Verify** family, tracked separately here. Same citation/chip display layer as the DailyMed chip-label [P2] below.
  - **Discovered:** 2026-07-01 (founder prod manual test; CC API probes can't see UI render → human-eye only).

- **[P2 · latent seam — flagged during the v195 ship] Lever-2 shadow override would strip the v195 TFDA identity annotation if ever enabled**
  - **What:** the Lever-2 question-neutralization shadow override (`api/server.py:815`, flag `QUESTION_NEUTRALIZATION_SHADOW` — OFF in prod) neutralizes from `body.question`, not from the v195-annotated `research_question` — if that flag is ever enabled, the TFDA identity annotation is stripped from the GENERATION path (retrieval keeps it; the fallback would lose it → the a1-i mis-ID could reappear on neutralized loaded queries).
  - **Action required:** any future Lever-2 activation must re-verify annotation survival — add it to that flag's activation checklist (cross-ref the Lever-2/A2 enforce items in BACKLOG §706a).
  - **Flagged:** 2026-07-03 (v195 ship), deliberately not changed — the flag is OFF and changing shadow-path code was out of a1-i scope.

- **[P2 · honesty / display — FIXED v196 (2026-07-03, commit `2a4fd71`)] Verify fallback-fail path returned `verification_status="ok"` — a total failure read as ok**
  - **What:** the Verify LLM-fallback-fail path (no FDA labels found AND the fallback LLM call throws) returned `interactions=[]` + `verification_status="ok"` → the UI rendered the clean "no interactions" presentation for a total failure. Pre-existing display behavior; the v194 enum made it nameable.
  - **Fix (v196, `2a4fd71`):** the path now emits `verification_status="failed_no_data"`; `pages/verify.tsx` renders the v194 warning presentation (badge "Not Verified", localized could-not-complete message + retry/consult advice via `verifyFailedMsg`/`verifyFailedAdvice` ×16). ok/deferred paths unchanged. All 3 enum values endpoint-pinned in `tests/test_verify_tfda_payload.py` (the fail-path test stubs the LLM to RAISE — no medical output mocked). Prod note: the path is not API-triggerable on demand (needs a live LLM failure) — human-eye/monitoring covers the rendered state.
  - **Discovered:** flagged during the v194 ship (2026-07-03). **Fixed:** 2026-07-03 (v196).

- **[P2 · honesty / consistency] DailyMed outbound-link chip label + host-mapping inconsistency (deferred from the 2026-06-25 DailyMed sweep)**
  - **(i) chip label reads like an integrated source:** `utils/sourceLabels.ts:52` maps source_type `dailymed` → chip label **'DailyMed'** (with `officialTip`). It's "reserved (Phase 1B)" and effectively **dormant today** (Explain's RxNorm badge keeps `source_type:'rxnorm'`, so the host-detection branch rarely/never fires), BUT if any citation is ever tagged `dailymed` the chip would read "DailyMed" — which blurs "we link OUT to DailyMed" vs "our data comes FROM DailyMed". Consider relabeling to **"FDA drug label"**.
  - **(ii) BUG — host→type mapping drift:** `utils/sourceLabels.ts:79` maps host `dailymed.nlm.nih.gov` → `'dailymed'`, while `api/services/share_renderer.py:233` maps the SAME host → `'rxnorm'`. So a DailyMed-linked citation would label **differently in the share OG render vs the live panel**. Reconcile to ONE mapping, aligned with the (i) chip-label decision.
  - **Why deferred:** the 2026-06-25 DailyMed over-claim sweep (PART I) was kept FRONTEND-only + zero-backend, so this (touches `sourceLabels.ts` + `share_renderer.py`) was deferred. Low priority — the chip is dormant today.
  - **Discovered:** 2026-06-25 during the DailyMed reference inventory.

- **[P2 · honesty — PROMPT-GATED, out of frontend-sweep scope] `explain_system.md` lists "FDA DailyMed" as a source category to the LLM (deferred 2026-06-25)**
  - `api/prompts/explain_system.md` (~L120 "**D. FDA DailyMed** — for prescription drug labels (when available)"; ~L228 example `"url": "https://dailymed.nlm.nih.gov/..."`) tells the **LLM** that "FDA DailyMed" is a source category, which can cause the model to NAME DailyMed in Explain output — the same over-claim family as the frontend copy, but at the prompt layer.
  - **Why deferred:** editing this edits a **system prompt** → requires a **§2.7 ExplainJudge re-baseline** (CLAUDE.md Rule 17), so it was OUT of scope for the frontend copy sweep (PART I). **Batch with the next Explain prompt edit / re-baseline.**
  - **Discovered:** 2026-06-25 during the DailyMed reference inventory.

- **[P2 · tooling / lint] ESLint flat-config breakage — `npm run lint` failed repo-wide — ✅ RESOLVED 2026-06-25 (`eslint.config.mjs` added)**
  - **Correct cause (the earlier 2026-06-24 note MISDIAGNOSED this as "repo still carries the old `.eslintrc`" — verified WRONG: there was NO `.eslintrc*` AND NO `eslint.config.*` of any kind):** ESLint 9 + a bare `"lint": "eslint"` script + **no config file at all** → ESLint 9 errors before linting, so `npm run lint` exited non-zero repo-wide (NOT a code lint error — identical on a clean checkout). The repo already shipped the flat-config deps (`@eslint/eslintrc` FlatCompat shim + `eslint-config-next` 15.5.5); only the config file was missing.
  - **Fix (this commit):** added the standard Next.js 15 flat config `eslint.config.mjs` (FlatCompat → `next/core-web-vitals` + `next/typescript`, plus a build-artifact `ignores` block) + set `eslint.ignoreDuringBuilds: true` in `next.config.ts` so `next build` keeps its pre-existing behavior (it did NOT run ESLint while the config was missing → build stays the deploy gate, lint is a standalone net). `npm run lint` now RUNS.
  - **NEW follow-up (separate task — deliberately NOT fixed here):** with lint working again it surfaces **7 errors + 14 warnings of PRE-EXISTING lint debt** (e.g. `@typescript-eslint/no-explicit-any` in `explain.tsx`/`research.tsx`/`verify.tsx`; `react/no-unescaped-entities` + `@next/next/no-html-link-for-pages` in `terms.tsx`; assorted unused-vars / `react-hooks/exhaustive-deps` warnings). Real findings in existing code, left for a dedicated lint-cleanup pass. Do NOT mass-autofix.
  - **Was DUPLICATED** in BACKLOG "ESLint flat-config migration" (Stage-4 S4.4) — that entry described the cause correctly; consolidated here, removed there.

- **[P2 · honesty / public-copy accuracy] DailyMed over-claim — ✅ COPY portion SHIPPED v189 (2026-06-25, `ead65fb`; human-verified on prod); deferred backend/prompt pieces still OPEN**
  - **✅ DONE (the copy half):** the 6 user-facing Bucket-A strings (`researchAttr2`/`explainAttr3`/`verifyAttr1` footers + 2 FAQ answers + `composerModeDescVerify`) ×16 locales no longer claim data "via DailyMed" → now "FDA drug labels (OpenFDA)"; `explainAttr3` dropped the drug-label clause entirely. Bundle-verified on prod v189 (old "official drug labels via" claim = 0; Bucket-B functional `dailymed.nlm.nih.gov` lookup links + FDA tooltip KEPT). One ⚠️ note: the FAQ data-sources answer now reads "FDA drug labels (OpenFDA) (official drug label and interaction data)" (double parenthetical — minimal token swap, cosmetic follow-up if desired).
  - **🟡 STILL OPEN (deferred in `ead65fb`, NOT closed by the copy sweep):** (1) Verify "FDA Label Analysis" label implies official FDA source for LLM-generated analysis → BACKLOG [P1]; (2) DailyMed chip-label + `sourceLabels.ts`↔`share_renderer.py` host-mapping drift → TECH_DEBT [P2] (above); (3) `explain_system.md` lists "FDA DailyMed" to the LLM (prompt-gated, needs §2.7 re-baseline) → TECH_DEBT [P2] (above). **The "sweep" is NOT fully closed — only the copy half shipped.**
  - **[ORIGINAL diagnosis preserved below for history.]** — **[ONE task tracked in two docs: this ↔ BACKLOG [P2] "Full-site DailyMed over-claim sweep".]**
  - **What:** the `/llms.txt` honesty fix earlier today (`6d4ff86`, "FDA DailyMed" → "FDA drug labels", because the real source is OpenFDA not DailyMed) was **incomplete**. During the v184 post-deploy (C) check, a signed-in Explain footer "Data Sources & Attribution" still claims **"Drug label data from DailyMed (FDA/NLM)."** The footer is likely a SHARED component, so other surfaces (Verify page, landing) probably carry the same overclaim.
  - **Framing:** same honesty principle as `6d4ff86` — do not claim a data source we don't have (misleads users / crawlers / B2B). Doubly irrelevant on Explain, which uses LOINC/MedlinePlus/RxNorm and no drug labels at all.
  - **⚠️ Two-sweeps timing (do NOT conflate):** **remove-NOW** (a current false claim → near-term honesty fix, independent of integration; do NOT defer to "whenever DailyMed is integrated" — that's Phase 1C+ and may never happen, which would leave the false claim live indefinitely) vs **add-real-AT-integration** (when DailyMed actually lands, the reverse step — add correct attribution + enum + labels — is inherent to that task and supersedes this removal).
  - **Fix-direction:** a FULL-SITE grep sweep for "DailyMed" overclaims → remove/soften to OpenFDA / FDA drug labels (not page-by-page). See BACKLOG [P2] "Full-site DailyMed over-claim sweep".
  - **Discovered:** 2026-06-23 during the v184 piece-(C) post-deploy signed-in Explain check.

- **[P1 · medical-safety / residual-risk — already warned by piece (A)] Chinese brand-name → ingredient confident-wrong on the Verify "proceed-anyway" path (2026-06-22)**
  - **Concrete instance:** during the post-deploy manual click-test of Phase 1B piece (A) (Verify force-English guard, shipped v183), the founder hit **"仍要送出（不建議）"** (proceed-anyway) with the Chinese brand name **「冠脂妥」** (+ 「普拿疼」). The system returned a confident, professional-looking interaction analysis but **mis-identified 「冠脂妥」 as Simvastatin**. 「冠脂妥」 is actually **rosuvastatin** (AstraZeneca Crestor's Taiwan brand name); Simvastatin (Zocor / 素果) is a *different* statin. A concrete instance of the GPT-4.1 53–60% confident-wrong rate on Chinese drug names that ADR 003 cites.
  - **Framing (important — this is NOT a piece-(A) bug):** piece (A) did its job — it detected the non-Latin input, warned (「偵測到非英文藥名」), guided to the English INN, and labeled the proceed button 「不建議」. The mis-identification happened ONLY because the user *deliberately bypassed* the warning via 「仍要送出」. This is the **EXPECTED residual risk that (A) explicitly warns about** — not a regression, not a UX failure of (A). The residual is: the proceed-anyway path still lets the LLM confident-wrong map a Chinese brand→ingredient and present the wrong-drug analysis as authoritative.
  - **Correct fix-direction (factual-lookup, NOT reasoning):** brand-name → ingredient is a **FACTUAL-LOOKUP problem (a mapping table), not a reasoning problem.** Ground it in a REAL lookup table: **best** = TFDA drug-license data (商品名↔成分) if a downloadable dataset/API exists (deterministic); RxNorm brand→generic exists but is mostly US brands → likely won't cover Taiwan brands like 冠脂妥; **pragmatic** = a hand-curated Taiwan-common brand→ingredient YAML (same pattern as the 在地差異提示 hand-curated YAML). Natural home = **fold into the 在地差異 / local-augmentation effort** (Phase 1C, or whenever 在地差異 grows a drug-name component) — NOT a separate near-term Phase 1B insertion (would break the current 1B ordering).
  - **⚠️ GUARDRAIL (prevents a future wrong turn):** do **NOT** try to fix this by swapping the model or tuning the prompt — it's a factual-lookup problem, not a reasoning one. The same lesson as this week's reversal/self-correction work (LLM self-correction can't fix precise factual problems). A stronger model only changes the error RATE (e.g. 55%→20%), still catastrophic for a single drug-interaction miss, and you never know *which* names it gets wrong because it's equally confident on both. Only a deterministic table is reliable.
  - **Cross-ref:** BACKLOG Phase 1C "Taiwan brand-name → ingredient grounding" pointer; ADR 003 (force-English decision); the 2026-06-21 dogfooding/reversal lesson family (factual problems need grounding, not bigger models).
  - **✅ DATA LAYER CONFIRMED (2026-06-26, [ADR 007](docs/decisions/007-tfda-open-data-grounding.md)):** the "if a downloadable dataset/API exists" condition in the fix-direction above is **MET** — TFDA **全部藥品許可證資料集** (infoId=37, 中文品名↔主成分略述) is open data (政府資料開放授權條款 OGDL v1.0). Its data layer is **SHARED with TFDA-grounding candidate (a1)** — one 商品名↔成分 layer serves BOTH this brand→ingredient fix AND grounding-lite. (Priority marker unchanged.)
  - **Discovered:** 2026-06-22 during the v183 piece-(A) post-deploy manual click-test.

- **[P0 · medical-safety / generation-reversal defense] C1 (③ coarse direction-checker) FAILED real-data shadow validation — feasibility micro-tests did not generalize (2026-06-17)**
  - **What:** the coarse ③ post-hoc direction-checker (BACKLOG §706a (b)) was built to the validated reference design (`api/services/direction_checker.py`, async port; `server.py` shadow hook behind `DIRECTION_CHECK_SHADOW`, default OFF; harness `scripts/direction_shadow_eval.py`; plan-back `C1_inrepo_planback.md`) and shadow-validated over a frozen 43-case live subset (`tests/direction_shadow_corpus.json`) with `96806b5` live in HEAD.
  - **Result (real, `direction_shadow_20260617_143022.json` + `_rescore_nostruct`):** **NOT deployable.** Structural-trigger ON (invariant 4): detection 11/11 but **FP 12/16 (75%)**, flags **37/43 (86%) of ALL answers** — the gpt-4.1-mini structural detector rubber-stamps `two_opposite_counterintuitive=True` on real 4–5-source retrievals (35/43 verdict=structural), incl. unambiguous single-direction topics (peanut-LEAP, beta-blockers-HFrEF, digoxin, serotonin-syndrome) → **no precision.** Structural OFF (primary whole-answer-vs-anchor only): **detection 0/11** → **no recall.**
  - **Root causes (mechanistically confirmed):** (1) **the conflation trap is INSIDE C1's own anchor-scorer** — on P-L1 the protective anchor 35268461 was retrieved, but `_score_counterintuitiveness` read `increases (OR 2.04)` (the multimorbidity composite) instead of polypharmacy `OR 0.78`. C1 fell into the SAME B01 multi-stat-conflation failure it exists to catch — so a cheap (gpt-4.1-mini) scorer cannot do the job; this is the same hard problem as the generator. (2) **deterministic `_opposite` can't handle "mixed"** anchors (OB-L1: anchor "mixed/U-shaped" vs answer "decreases" → no flag). (3) genuine retrieval-miss (C01) is ③'s designed blind spot, not a bug.
  - **Why feasibility lied:** dep(a) 5/5, dep(b) 4/4, coarse 4/4 used **hand-curated synthetic source bundles + curated answers**; they never exercised the structural detector against messy real retrievals or measured FP at scale. **Lesson (generalize):** curated micro-validations are necessary but NOT sufficient — a real-pipeline shadow run over a representative corpus must gate any "feasibility VALIDATED" claim before production. (Same family as the o4-mini "3/3" counts-only non-reproduction.)
  - **Status / how to apply:** `DIRECTION_CHECK_SHADOW` MUST stay OFF (hook is inert by default; code committed locally, NOT pushed; Fly deploy deferred). C1 needs **fundamental rework, not tuning** (stronger scorer that doesn't conflate multi-stat abstracts — undercuts the "cheap backstop" premise; precise-or-removed structural detector; LLM direction-comparator robust to "mixed") OR reroute to the front-end vague-loaded-neutralization pre-filter (§706a (b2), unbuilt) / the B2B-interim route. Founder decision pending — see STATE TOP NEXT.
  - **Discovered:** 2026-06-17, the C1 shadow build (first prod-code touch in the §706a chain).
  - **2026-06-17 follow-up DIAGNOSTIC — the conflation is a CHEAP-MODEL artifact, NOT task-intrinsic (`scripts/direction_extract_probe.py`, `direction_extract_probe_20260617_153856.json`; route is now B2B-interim so this is advisory, not launch-gating).** Isolated test (no regeneration; reused captured answers; 5 cases): re-ran ONLY the two ③ sub-tasks with a STRONGER model (gpt-4.1, NOT gpt-4.1-mini). **(a) effect-extraction: gpt-4.1 cleanly disentangled the multi-stat conflation trap — P-L1 + P-L2 both extracted polypharmacy `OR 0.78 (decreases)` AND named the trap `multimorbidity OR 1.82/2.04 (increases)`, 2/2 — the exact case the mini scorer failed; clean controls (H4 peanut, HD-BB beta-blocker) 2/2.** (b) LLM direction-comparator (replacing the deterministic `_opposite` that broke on "mixed"): detection 2/2 on the conflation reversals, FP 0/2 on clean controls. **VERDICT: the primary-path failure that killed C1 = (cheap gpt-4.1-mini scorer) + (brittle deterministic comparator), NOT the task being impossible.** A ③ thin backstop therefore HAS a path — IF built with a **strong scorer** (gpt-4.1, ~$0.004/call here; undercuts "cheap" but is cents/answer, affordable for a B2B backstop) + an **LLM comparator**. **STILL UNRESOLVED (do not over-read 2/2):** (i) the **structural over-fire (75% FP) is model-independent** and must be DROPPED/replaced — this probe only tested the primary path; (ii) **anchor-SELECTION over real 4–5-source retrievals was NOT tested** (the probe fed the known anchor PMID; dep(a)/(b) selection validations didn't generalize); (iii) **single-source "mixed"/U-shaped abstracts remain a soft spot** — OB-L1: even gpt-4.1 extracted a real protective HR 0.93 but DROPPED the U-shaped/nadir caveat (oversimplified). Caveats: 5 cases, gpt-4.1 (the strongest non-reasoning tested), single run, $0.022 total. **So: ③ is NOT dead, but "viable B2B backstop" is CONDITIONAL on drop-structural + prove-selection-at-scale + handle-mixed — this proves the extraction sub-task is tractable, not that ③ works end-to-end.**

- **[P2 · eval harness] Eval paths must PERSIST answer prose, not just verdict counts (2026-06-15)**
  - **Incident:** the first B01 loaded-framing recheck (o4-mini, 2026-06-15) was an inline snippet that printed only verdict *counts* to stdout and saved no JSON. Its "3/3 no-contradict" result was therefore **non-auditable** — when we later needed the actual direction language to judge fidelity-vs-evasion, the prose was gone (stdout-only, process exited), and re-generation gives *different* non-deterministic answers (it can't recover the originals). A fresh persisted re-run then showed **2/3 CONTRADICTS**, i.e. the original counts-only "3/3" was not robust and not inspectable.
  - **Fix (shipped, `f072a7f`):** added `--recheck` mode to `scripts/citation_truth_check.py` that saves full answer prose + every claim-pair (claim, PMID, verdict, evidence, reasoning) to `tests/results/recheck_{ts}.json`. The `--adversarial` / `--run` paths already persist answers.
  - **Resolution / rule:** any eval or recheck that informs a medical-safety / launch judgment MUST persist the generated prose (a verdict count alone is not evidence). Do not use counts-only inline snippets for conclusions. Audit other ad-hoc eval scripts for the same gap when next touched.
  - **Discovered**: 2026-06-15 during the BACKLOG §706a o4-mini B01 fidelity audit.

- **[P2 · calibration] The cheap selector's clinical prior is overconfident on contested topics → confidence is NOT a safe gate (2026-06-17)**
  - During the §706a (b) coarse-③ anchor-selection dep-(a) validation (`anchor_prior_crosstab_20260617.json`, gpt-4.1-mini), the selector's COLD clinical prior was **wrong-but-high-confidence on HRT** (said "HRT reduces CV," confidence **0.8**, on a genuinely **contested** topic) — while correctly drawing its **lowest** confidence (0.7) on the other contested topic (alcohol). So the model's confidence does **not** reliably track prior-shakiness.
  - **Implication (the actionable part):** a future production coarse-③ must **NOT use the selector's self-reported confidence as a safety gate** to catch prior-misses — it would have missed the HRT case. (It didn't matter this round: selection still picked the right anchor 5/5 because the rule reads each source's *explicit* effect size, not just the prior. But if a prior-miss ever propagates to a selection error, confidence can't catch it.)
  - **Caveat:** the HRT "wrong" is **debatable** — the factor was framed "HRT *started near menopause*," for which "reduces CV" is a defensible conventional answer; and it did not cause a selection error. Logged as a **calibration watch-item**, not a hard failure. Resolution direction if pursued: mitigate prior-miss risk via topic breadth / a second-source cross-check, NOT a confidence threshold.
  - **2026-06-17 update (dep (b) reinforces this):** the §706a (b) dep-(b) competing-sources test set its MEDIUM-threshold bar as "pick right **OR fail SAFE** (abstain/low-confidence)" — but the selector picked **confidently (0.9) in all 4 bundles** (incl. contested HRT) and **never abstained**, so the **fail-safe leg is unexercised/unproven** and a confidence-based fail-safe would be unreliable given this overconfidence. The MEDIUM-threshold safety net therefore rests on unvalidated calibration — IF a future competing case stumps the selector, it would likely mis-pick *confidently* (no abstain), which is the dangerous whitewash mode.
  - **Discovered:** 2026-06-17 during the §706a (b) dep-(a) cross-topic prior-reliability test.

- **[P2 · dependency] openai SDK 1.30.1 predates `max_completion_tokens` / `reasoning_effort` kwargs (2026-06-15)**
  - `requirements.txt` pins `openai==1.30.1`. Its `chat.completions.create()` signature has `max_tokens` but **not** `max_completion_tokens` / `reasoning_effort`, and **no `**kwargs` passthrough** — so reasoning models (o-series / GPT-5) can't be called with the new param names (raises `TypeError` before the network call; confirmed via an o4-mini probe 2026-06-15).
  - **Current workaround (shipped, `455bcb5`):** `api/providers/openai_provider.py` `_apply_param_contract()` routes `max_completion_tokens` + `reasoning_effort` through `kwargs["extra_body"]` (the SDK forwards extra_body into the request payload regardless of version). This unblocks the BACKLOG §706a o4-mini eval without an app-wide bump. The gpt-4.1 / default path is unaffected (it never enters the reasoning branch).
  - **Resolution (future, separate round):** a planned `openai` SDK bump to a version with first-class `max_completion_tokens` / `reasoning_effort`, then drop the `extra_body` indirection. **Blast radius is app-wide** (all providers + embeddings + vision share the SDK), so it needs its own **plan-back + full smoke** — deliberately NOT done this round (no-push/no-deploy exploratory state).
  - **Discovered**: 2026-06-15 during the BACKLOG §706a stronger-model eval (o4-mini STEP 0 probe).

- **[P0 · medical-safety → gates B2C public launch] Direction-of-effect reversal on counterintuitive findings (CONTRADICTS) — measured 2026-06-13/14**
  - **What**: the answer states the OPPOSITE direction of effect from the cited source on a counterintuitive finding, while citing a real (existing) PMID. The dangerous shape is "reverses a counterintuitive finding *and* cites a real source" — it reads as well-grounded but inverts the evidence.
  - **Measured prevalence** (honest bounds): **~0.6% random lower-bound** (Stage-2 citation-truth: 1/180 claim-citation pairs CONTRADICTS; abstract-only judging over-counts unsupported, so this is a lower bound) … **~18.8% adversarial upper-bound** (Stage-3 adversarial famous-set: 3/16 reversed; the set is loaded toward failure, so this is an upper bound). The true rate sits between. **Reproduced 3×**: C01 polypharmacy/mortality (PMID 35268461 — answer "increased death risk" vs abstract OR 0.78 LOWER), C03 intensive-glucose, C15 DBP J-curve. Cohort-specific adversarial 0/3 is UNDERPOWERED, NOT evidence of safety.
  - **Advisor verdict**: rejected direct B2C public launch in this state (clinically + legally unacceptable — TW 醫師法 §28 密醫罪, FDA device exposure).
  - **Resolution DIRECTION**: (1) prompt instruction to report the source's direction-of-effect faithfully — **DONE / PARTIAL (2026-06-15, commit `96806b5`; see sub-section below)**: resolves neutral-framed reversers but NOT loaded-framing → insufficient on its own; (2) a stronger generation model via the §2.1 Provider abstraction — **DONE / INSUFFICIENT (2026-06-15, o4-mini; see sub-section below)**: 0/3 fidelity on B01-loaded → a model-swap does NOT fix framing-sensitivity; (3) **[ACTIVE — now the path]** the advisor's Phase-2 **contradiction circuit-breaker** = a **structural-citation fallback** (bind each direction claim to the retrieved effect statistic so prose can't contradict it) **+ a full-text NLI post-hoc direction checker** (flag-only / post-hoc per the NLI-gate feasibility entry below — no clean pre-return chokepoint; streaming streams tokens before citations resolve) — see BACKLOG §706a (b)+(c); (4) retrieval stabilization (addresses the C15-type unstable-retrieval variance). **Both #1 (prompt) and #2 (model) are now tried-and-insufficient → #3 is elevated from "later" to a B2C-launch precondition.**
  - **Related**: the 2026-05-06 dogfooding entry "Verify 答案品質 nuance issues" issue #4 ("Counterintuitive finding 缺乏 mechanism explanation") — same family, now *measured as a direction reversal*, not merely missing mechanism.
  - **Discovered**: 2026-06-13/14 during Task-A answer-quality QA (Stage 2 + Stage 3).
  - **── Prompt-fix attempt (2026-06-15, commit `96806b5` — generator.py "DIRECTION-OF-EFFECT FIDELITY" 3-bullet block; holdout cases `fdd624c`; both committed, NOT pushed, NOT deployed) ──**
    - **Verdict: PARTIAL mitigation.** Do NOT read this as "the reversal rate dropped." Post-fix adversarial famous-set reversal was **19% / 25% / 19%** across 3 runs — **INSIDE** the baseline band of **19% / 25% / 38%** (overlapping; variance-dominated at temp 0.2). The aggregate rate did **not** clearly move; the fix removed the two targeted reliable failures but variance-fringe cases (C08/C10/C11) filled the gap.
    - **What genuinely improved (the real signal):** the two **stable, reproducible, NEUTRAL-FRAMED** reversers **C01** (polypharmacy/AF clinical outcomes) and **C13** (smoker's-paradox STEMI) resolved to `same` across **all 3** post-fix runs (baseline: reversed every run). C01 stayed faithful **even in run2/run3 when retrieval cited a different PMID (35155632) instead of 35268461** — so the effect-statistic anchor is a **general mechanism, not memorization of one PMID**. The live probe showed faithful phrasing ("lower odds, OR 0.78"), i.e. real fidelity, **not** evasion-by-vagueness.
    - **KEY NEW FINDING — FRAMING-SENSITIVITY (the mode that matters for B2C):** on the **Stage-2 B01** query "*Why is polypharmacy a serious problem in elderly Asian patients?*" — a **premise-loaded** question — PMID **35268461 STILL CONTRADICTS** under the fixed prompt (answer still asserts "increased … higher rates of all-cause death" and cites the OR-0.78-*lower* source). **Same topic, same PMID as C01, but the loaded premise overrides the fidelity instruction.** Neutral framing (C01) fixed; loaded framing (B01) NOT. **Real B2C users ask loaded questions**, so this is the failure mode that gates a consumer launch.
    - **Did NOT move:** **C15** (DBP J-curve) reversed in all 3 post-fix runs — confounded by conflicting-evidence framing + unstable retrieval (different PMID set per run), so it is **not** clean evidence for/against the fix. **C03** moved only partially (reversed 2/3 post-fix).
    - **Mild signal to watch:** non-targeted famous-set `not_directional` pairs trended **up** (mean ~5.3 → ~8.7) while `same` stayed flat — a small evasion drift on the cases the fix did NOT target. The *targeted* cases (C01/C13) went to `same`, not `not_directional`, so their resolution is real; the drift is on the periphery.
    - **Over-correction check:** the 5-case on-topic **holdout stayed 0/5 reversed in all 3 runs** (no new reversals introduced, `same` stable). **Caveat: this only proves "no new harm" — it is NOT evidence of generalization** to unseen reversal modes (the holdout had 0 baseline reversals, a floor; it cannot show improvement, only regression-absence).
    - **Measurement provenance:** 6 adversarial run JSONs (`adversarial_contradiction_2026061[45]_*.json`) + the B01 Stage-2 recheck, all in `tests/results/` (gitignored). EVIDENCE for human judgment — NOT an endorsement; adversarial = upper bound (loaded set), Stage-2 = lower bound (abstract-only).
    - **Net:** consistent with the advisor's "partial, not reliable catching." A prompt-only fix is **proven insufficient** to open B2C; next evaluation is the stronger-model path (Resolution DIRECTION #2) on a precise small set.
  - **── Model-swap attempt (o4-mini, 2026-06-15 — provider param-contract `455bcb5`/`22ab342`, `--recheck` persist-prose harness `f072a7f`; committed, NOT pushed, NOT deployed) ──**
    - **Verdict: INSUFFICIENT.** Swapping the Research generator gpt-4.1 → o4-mini (reasoning model) did NOT fix loaded-framing reversal. Gate checks held: ① gpt-4.1 no-op smoke = **no regression**; ② o4-mini `complete()` `finish_reason=stop` + reasoning-token usage OK; **no `[ERROR]`** in any run.
    - **0/3 FIDELITY on the loaded query B01** (`recheck_20260615_225242.json`, judge gpt-4.1, **full prose persisted** — auditable, unlike the lost counts-only originals): run2 + run3 **CONTRADICTS** PMID 35268461 (assert "higher all-cause death **OR 1.82**" while citing the **OR-0.78-*lower*** source — **conflated the multimorbidity ORs onto polypharmacy**); run1's "no-contradict" was an **evasion** (routed risk through multimorbidity, judge PARTIAL), not a faithful OR-0.78 statement. **No run stated the OR-0.78 lower-death finding.**
    - **Neutral-vs-loaded split = the key evidence:** the SAME o4-mini, SAME PMID 35268461 — on the **NEUTRAL** query C01 stated *"counterintuitively linked to lower odds of all-cause death (OR 0.78)"* faithfully (flagging the paradox) and attributed other cohorts' higher-mortality HRs to their sources; on the **LOADED** query B01 it reversed 2/3. **Only framing differs → framing-sensitivity is systemic, not a model-capability gap.**
    - **Prior optimistic read OVERTURNED:** an earlier *counts-only* B01 recheck reported "3/3 no-contradict." It **did NOT reproduce** on a persisted re-run and was never auditable (root-cause logged in the "[P2 · eval harness] persist answer prose" entry). The **0/3-fidelity persisted result is the record.**
    - **Scope caveat:** ONE loaded query (B01), 2/3 — same small-sample limit as the prior optimistic read; not generalized. A **GPT-5.4** comparison is an optional last check with **LOW expected value** (the failure looks systemic, not compute-limited).
    - **Net:** with both #1 prompt-fix (PARTIAL) and #2 model-swap (INSUFFICIENT) exhausted, the active path is the Phase-2 defensive **circuit-breaker** (#3: structural-citation fallback + post-hoc NLI checker) — now a **B2C-launch precondition** (BACKLOG §706a (b)+(c)).
  - **── Two-failure-mode split (2026-06-16 — Phase-3 eval `evalrun_{o4-mini,gpt-4.1}_20260616` + N=10 retrieval-recall diagnostic `retrieval_recall_20260616_133331.json`, script `4248dfd`; docs-only) ──**
    - **Overturns the implicit "bad answers all come from generation" assumption.** The reversal problem is **two distinct failure modes needing different fixes:**
    - **(1) GENERATION-reversal (polypharmacy 35268461 — source IN HAND):** the protective OR-0.78 source is **reliably retrieved at loaded framing** — 10/10 in pool AND final at L1/L2, rank 2, never reranked out. Yet the model still reverses the direction (the B01 failures). → a pure generation failure; **the post-hoc NLI direction checker (§706a (b)) is the matching defense** (it can compare the claim to the cited source).
    - **(2) RETRIEVAL-recall failure (obesity 37290898 — source NEVER SEEN):** the protective paradox source is often not retrieved at all — loaded **OB-L2 = 0/10 in pool** (recall-miss: the loaded rewrite → "obesity heart failure pathophysiology/impact" → PubMed returns harm-mechanism/HFpEF papers, paradox doc never enters); neutral **OB-L0 = in pool 7/10 but reranked OUT 7/10** (enters low-scored ~rank 14, reranker keeps 5 newer higher-scored papers). The model answers from harm-side papers and **never sees** the protective source → **the NLI checker is BLIND to this** (no cited source to compare against). → needs **retrieval-side fixes** (BACKLOG §706a (d): query-rewrite loaded-premise bias + rerank recency/score bias). ① structural fallback partially covers it (no protective coverage → low-confidence/withhold).
    - **Sub-findings:** neither anchor is in the **local 690-doc store** (100% FDA labels) — both are **live-PubMed + LLM query-rewrite**, NOT local indexing/chunking. Framing biases retrieval itself, **oppositely by topic**: polypharmacy loaded recalls the anchor **MORE** (L2 10/10 vs L0 5/10), obesity loaded **SUPPRESSES** it (L2 0/10 vs L0 7/10) — for obesity, **framing and retrieval are the SAME root cause**. **Hypothesis (unverified):** anchor title wording — polypharmacy paper "*Multimorbidity and Polypharmacy… Clinical Outcomes*" carries loaded harm terms (loaded rewrite hits it); obesity paper "*Body mass index and survival*" is neutral (loaded rewrite drifts off it).
    - **Model comparison (clean anchor-retrieved cases):** o4-mini vs gpt-4.1 tied **3/6 genuine passes each (same 3 cases)** — reconfirms model-swap doesn't fix generation-reversal.
    - **Caveat:** single retrieval query-wording per topic, N=10, two topics — strong directional signal, **not generalized**; the title-wording driver is a **hypothesis**.
    - **── (i) retrieval prompt-fix — FAILED + reverted (2026-06-16; `retrieval_recall_20260616_141620.json` vs `_133331.json`; retriever.py back at HEAD, NO commit) ──** the first retrieval-stabilization lever — a prompt-level **valence-neutral query-rewrite** instruction in `_rewrite_query` — failed both gates. **(target) OB-L2 0/10 → 0/10, no movement:** root cause is NOT valence but a **TERMINOLOGY mismatch** — the rewrite emits lay "obesity" while anchor 37290898's title is "*Body mass index and survival*", so PubMed never matches it (premise-neutralization can't fix obesity↔BMI). **(regression) P-L1 collapsed 10/10 → 0/10** (deterministic, prompt-caused) + OB-L0 pool 7/10 → 0/10, while **P-L0 improved 5→10 under the SAME edit**. **Blunt-lever lesson:** anchor recall is hyper-sensitive to the exact search-term string, so **a single global rewrite instruction cannot optimize recall across topics** (one edit fixed P-L0 and broke P-L1). → the **prompt-rewrite sub-approach is closed**; deeper levers (lay→MeSH term-expansion / two-sided retrieval = "Path B") are **deferred**; the **retrieval-miss case is absorbed by ① structural-citation fallback** (missing protective coverage → low-confidence/withhold). Active build focus moves to the **generation-side** (b)/(c). See BACKLOG §706a (d).

- **[P1 · evidence contract] Confident zero-citation answer (B07) — retrieval miss / ungrounded assertion**
  - Stage-2 citation-truth surfaced B07: a confident, definitive-reading AF stroke-prevention answer returned with **0 citations**. For an "evidence-based" product this violates the evidence-cited contract — the failure is *absence* of grounding on a confident clinical claim (distinct from fabrication; no fake PMID was emitted).
  - **Resolution (record-only)**: retrieval-side investigation (why no docs retrieved for this query) + a "no citations → degrade/withhold confidence (or withhold the answer)" guard so a confident tone never ships ungrounded.
  - **Discovered**: 2026-06-14 during Task-A QA Stage 2 (`citation_truth_20260614_113716.json`).

- **[P2 → Phase 1B Week 4] R10 digoxin toxicity answer completeness**
  - Stage-1 golden eval: the digoxin-toxicity answer omits canonical toxicity features — nausea/vomiting + visual disturbances. Same family as the canonical-term under-coverage entry below; batch into the Week-4 Research system-prompt polish.
  - **Discovered**: 2026-06-13 during Task-A QA Stage 1 (`golden_results_20260613_144748.json`).

- **[P2 · test infra] Golden-runner `response_language` staleness after the v179 UI-language change** — **[ONE item with BACKLOG "Test infra — multilingual response_language assertion completeness" (same root: thread `response_language` for all multilingual cases + an audit net); track as one.]**
  - v179 made Research's answer language UI-driven (`response_language`), so the golden runner must **send `response_language`** before any multilingual-number / language-assertion case is valid. Not doing so produced **6 false FAILs** in Stage-1 (harness artifact, NOT a product regression — part of the 22/24 contaminated FAILs).
  - **Resolution (record-only)**: thread `response_language` for all multilingual cases + an audit that flags any multilingual golden case missing it. Cross-ref BACKLOG "Test infra — multilingual response_language assertion completeness" (same root, now with a concrete failure count).
  - **Discovered**: 2026-06-13 during Task-A QA Stage 1.

- **[P2 · access/UX — decision needed] Guard over-block of colloquial symptom queries**
  - The input guard blocked **11** colloquial symptom-phrased queries in Stage-1 (counted as FAILs but actually guard behavior, not content failure — part of the 22/24 contaminated FAILs). **Open call**: is blocking colloquial symptom phrasing the correct safety behavior, or an access regression that frustrates real users (esp. B2C lay phrasing)? Needs a product/safety decision, NOT a silent fix. Decide before launch.
  - **Discovered**: 2026-06-13 during Task-A QA Stage 1.

- **[P1 · mitigation feasibility — assessed, NOT built] Contradiction / NLI gate** — **[= the same mitigation as BACKLOG §706a (b) post-hoc direction checker, which is the AUTHORITATIVE tracker (built + shadow-validated → FAILED real-data 2026-06-17, needs rework/reroute). This entry is the original feasibility note; defer to §706a + the P0 "Direction-of-effect reversal" entry.]**
  - **Verdict: PARTIAL mitigation, not reliable catching.** The streaming architecture streams answer tokens to the client while citations are only resolved at the end of the stream — so there is no clean pre-return choke point. A gate must either **buffer** the whole answer before returning (kills the streaming UX) or run **post-hoc** (flag-only — can surface a warning but cannot block the already-streamed answer). Abstract-only judging also can't reliably separate *contradicts* from *terse-abstract* → a false-positive killer if used as a hard gate. Build size **M–L**. (Confirm exact `server.py` stream/citation line refs at build time.)
  - Maps to advisor **Phase-2 "contradiction circuit-breaker."** Recorded as feasibility context for the OPEN route decision — not a committed build.
  - **Discovered**: 2026-06-14 during Task-A QA (gate feasibility assessment).

- **[P0 · ops/stability — pre-launch] OpenAI auto-recharge OFF + prepaid credit EXPIRES**
  - Auto-recharge is OFF and prepaid credit expires (Andrew already lost ~$28 to expired grants). Credit-zero = the WHOLE service returns `[ERROR]` to ALL users — every Research/Verify/Explain call hits OpenAI. A public-traffic stability risk for **either** B2C or B2B.
  - **Resolution (record-only)**: enable auto-recharge before any launch; add a low-balance alert.
  - **Discovered**: 2026-06-15 during Task-A QA session (ops review).
  - **2026-06-18 update — auto-recharge ON (founder-confirmed) + a NEW burn-rate watch-item.** Founder confirmed auto-recharge is now ON; verified inferred-live all session (every Gate-1 probe HEALTHY, ~$5+ of real eval calls + a prod deploy with zero credit-zero `[ERROR]`). Caveat: a completion probe only confirms credit is LIVE — it does NOT read the auto-recharge toggle (the API doesn't expose it). **NEW BURN-RATE RISK (v181, 2026-06-18):** `RETRIEVAL_REFUSAL_SHADOW=true` is now LIVE in prod — Lever 1 shadow runs **gpt-4.1 on the retrieved pool for every SIGNED-IN Research query** (≈ $0.005–0.015/query). This is added, non-user-facing OpenAI spend that scales with signed-in traffic. **Watch the auto-recharge threshold against this new burn rate** as signed-in usage grows; if shadow spend is material before the A2/enforce decision, consider down-sampling the shadow (run on a fraction of queries) or moving it to gpt-4.1-mini (accepting the conflation risk on the pool-stance read).

- **[P2 → future recon] Explain language resolution may be fragile on mixed CJK+Latin input (2026-06-11)**
  - Explain resolves the report's language differently from Research: `entities.input_language` from the entity extractor, with a `detect_language` override when they disagree (`api/services/explain_service.py:520-525`). `detect_language`'s script heuristic flips to Chinese on **any** CJK char, so a report that is ~half Latin lab abbreviations (GOT/GPT/HbA1c) + ~half Chinese terms can be mis-resolved → inconsistent EN-vs-ZH answers (the same class of bug fixed for Research in v175).
  - Real-world relevance: Taiwanese lab reports **routinely** mix Latin abbreviations + Chinese, so this is genuine user input, not just a contrived example. The v177-follow-up only replaced a mixed *example chip* (`pages/explain.tsx`) with a language-clean one — it does **not** address mixed *user* input.
  - Resolution: a future recon of Explain's language-resolution path (is the `input_language` + override logic robust to balanced CJK+Latin? should it prefer the extractor's judgment, a dominant-script threshold, or an explicit response-language control like Research/Verify?). **Flagged, not fixed** — example-text change only this turn.
  - **Scope sharpened (v179, `12e7f4a`):** the v179 work made **answer** language UI-driven across all three features, so the earlier "→ inconsistent EN-vs-ZH **answers**" framing above is imprecise: Explain's `entities.input_language` is used **only** for entity-to-source matching (`explain_service.py:355` — explicitly "NOT for output"); the answer + disclaimer language come from `response_language` (UI-resolved), not `input_language`. So this entry's real remaining scope is **source-matching robustness** on balanced CJK+Latin input (could mis-match LOINC/RxNorm/FDA sources), **not** answer-language selection. Still OPEN at that narrowed scope.
  - Discovered: 2026-06-11 during the Explain example-chip cleanup (Item C).

- **[P3 → next opportunity] Dead `evidence*` i18n keys after the evidence-indicator redesign (2026-06-10)**
  - The evidence-indicator redesign (design X) removed `EvidenceLegend` from `pages/research.tsx`; its only consumers — `evidenceStrong` / `evidenceModerate` / `evidenceLimited` + the three `…Tip` variants (6 keys × 16 locales = 96 cells) in `utils/i18n-ui.ts` — are now **dead** (still declared in the `UITranslations` interface + present in every locale, so the build is satisfied; just unused).
  - Left in place deliberately: mass-removing 6 keys across the strict interface + 16 inline locale objects is a large mechanical diff with breakage risk, disproportionate to a cosmetic cleanup.
  - Resolution: drop the 6 interface fields + all 16×6 locale values in one scripted pass at the next i18n-touch opportunity (e.g. the §3.4 i18n-refactor). Verify `npm run build` after (strict interface will catch any miss).
  - Discovered: 2026-06-10 during the evidence-indicator redesign (Sub-task B).

- **[P3 → next opportunity] Dead credibility-label i18n keys after the reference badge removal (2026-06-10)**
  - The Research reference source-label cleanup (A1) removed the credibility badge from `components/CitationPanel.tsx` (and `useCredibilityConfig`). Its label keys — `peerReviewed` / `official` / `internal` + `internalTip` (4 keys × 16 = 64 cells) in `utils/i18n-ui.ts` — are now **dead** (no consumer; Verify/Explain never used them). The tooltip keys `peerReviewedTip` / `officialTip` are **still live** — reused as the source-name tooltips via the shared `utils/sourceLabels.ts` map.
  - Left in place deliberately (same rationale as the `evidence*` / `status*` keys): mass-removal across the strict interface + 16 locales is disproportionate churn.
  - Resolution: drop the 4 dead interface fields + their 16×4 locale values in the same scripted i18n cleanup pass as `evidence*` / `status*`. Verify `npm run build` after.
  - Discovered: 2026-06-10 during the Research reference source-label cleanup.

- **[P3 → next opportunity] Dead `statusSearching` / `statusAnalyzingDocs` i18n keys after the multi-step status change (2026-06-10)**
  - The Research multi-step status change replaced the two single status strings with a 3-step scheme (`statusStepSearch` / `statusStepRank` / `statusStepGenerate`). The old keys `statusSearching` ("Searching medical literature…") and `statusAnalyzingDocs` ("Analyzing documents…") are now **dead** (still declared in the `UITranslations` interface + present in every locale, still referenced as legacy graceful-map fallbacks in `research.tsx` `statusMap`, but the backend no longer emits those strings).
  - Left in place deliberately (same rationale as the dead `evidence*` keys above): mass-removing across the strict interface + 16 locales is disproportionate churn.
  - Resolution: drop both interface fields + all 16×2 locale values (and the two legacy `statusMap` fallback lines in `research.tsx`) in the same scripted i18n cleanup pass as the `evidence*` keys. Verify `npm run build` after.
  - Discovered: 2026-06-10 during the Research multi-step status change.

- **[P2 → mostly SHIPPED] Verify 答案品質 nuance issues — dogfooding 發現 (2026-05-06) — 4/5 DONE, only #3 survives**
  - The 2026-05-06 dogfooding 5-issue set (query「為什麼亞洲老年人 polypharmacy 問題嚴重」, all citations real / 0 hallucination) is mostly shipped: **#1 citation-scope-mismatch + #2 geographic-coverage → Research v185 (`20a84c9`)**; **#5 no-self-rating → Verify v184 (`bf1c5ec`)**; **#4 counterintuitive-mechanism → absorbed by the reversal-defense direction-of-effect chain** (see the TECH_DEBT P0 "Direction-of-effect reversal" entry + BACKLOG §706a). **Only #3 survives** = citation-ranking bias toward recency over scope-match (the best-match PMID 37574369, Malaysia primary-care 393pt, ranked 4th behind narrower China inpatient studies) → tracked as **BACKLOG [P2] "Citation retrieval ranking evaluation"** (pre-req: 5-10 dogfooding samples) + the related "Research canonical-term under-coverage" entry below. (Original 5-issue diagnosis preserved in git history pre-trim.)

- **[P1 → Round 2B + 3 完成後一起 E2E 測試]** Clerk email sign-up/sign-in end-to-end 驗證
  - **背景**: 2026-04-22 localhost /sign-in 已確認 Clerk Development instance 有 email input(切 Dev instance + 啟用 email code verification 後解決)。Production instance email 設定也已確認 ON。
  - **尚未驗證**:
    - Email code 能否真的發到使用者信箱(依賴 Clerk email 發送能力)
    - 新使用者透過 email 註冊 → Clerk user 建立 → backend JWT 驗證成功 → /research 能載入
    - Email 與 SSO Google 同一 email 時,Clerk 如何處理(期待:同一 Clerk user)
  - **測試順序**(Round 2B + 3 完成後一起做):
    1. 無痕視窗 /sign-up → 輸入全新 email → 收 code → 輸入 → 完成註冊 → redirect /research
    2. 無痕視窗 /sign-in → 輸入 #1 註冊的 email → 收 code → 登入成功
    3. 新 email 註冊 → logout → 改用同 email Google SSO → 看 Clerk 是否合併 user
  - **Priority**: P1(2.8 完整驗收一部分),軟啟動前必須通過
  - **Discovered**: 2026-04-22 during Clerk Dev/Prod instance diagnostic

- **[P1] print() violations in api/** (54 處, audited 2026-04-19)
  - 生產路徑 9 處(影響 Sentry + log aggregation):
    - `fda.py:149/152/177` — FDA 請求失敗用 print 而非 logger
    - `simple_cache.py:90/111/179/183` — cache 事件(179/183 每次 cached call 都吵)
    - `vector_store.py:38/46` — 啟動 log;L46 含 ✅ emoji 在 Windows CP950 會爆
  - Test harness (`if __name__ == "__main__":`) 45 處,低優先
  - `fda_cached.py` 整檔為 dead code (CLAUDE.md 已標),可順手刪除
  - Resolution: 排入 Phase 0 Retrospective 一次清理
  - **2026-05-05 update**: Re-confirmed during §4.5 PHASE A smoke test on Windows local uvicorn — the `print()` at `vector_store.py:46` containing U+2705 (✅) crashes uvicorn boot under cp950 console. Workaround for local dev: `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 uvicorn ...`. Production unaffected (Linux/UTF-8). Fix is still pending — replace with `logging.getLogger(__name__).info(...)` per CLAUDE.md Rule 4.
  - **2026-05-21 update**: Re-discovered during §3.1 PHASE B test work — the crash is now at `vector_store.py:52` (line shifted; same `print(f"✅ Vector store loaded...")` from commit 3e4471ed). Concrete test impact: blocks `import api.server` from any pytest module on Windows, which prevents constructing a `TestClient(app)` with dependency overrides → blocks endpoint-level integration tests (POST 403 free-user gate, POST 422 missing-field, GET 404, GET 200 round-trip, rate-limit). Workaround used in §3.1 PHASE B: idempotency verified at the SQL layer via `sqlite_insert.on_conflict_do_update` instead of through the endpoint (see `tests/models/test_user_profile.py`). One-line fix still pending; not P0 because production is Linux/UTF-8.

- **[P2] PowerShell 運行 `.env` parse warning**
  - `python-dotenv` 啟動時 warn `could not parse statement starting at line 1/2`
  - 不影響功能但 log 很吵
  - 可能原因:`.env` 檔 UTF-8 BOM,或前兩行有 shell export 語法
  - Resolution: Phase 0 Retrospective 清 .env 編碼

- **[P2] Chinese variant handling 已 spread(2026-04-20 完成),但 {response_language} pattern 仍不一致**
  - Verify 2.9 用 `{response_language}` 變數注入 system prompt
  - Research / Explain 用 `get_language_instruction()` append 到 user message
  - 兩套都 work,但 pattern 不一致,未來擴充語言 feature 要同步改兩處
  - Resolution: Phase 1A i18n mop-up 時統一 pattern(建議走 Verify 2.9 的 `{response_language}` 路線,同步 extract Research/Explain prompt to api/prompts/)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread

- **[P2] zh-TW / zh-CN severity Critical/Major 邊界 drift**
  - zh-TW dict: Critical=危急, Major=嚴重
  - zh-CN dict: Critical=严重, Major=重度
  - 兩套設計:zh-TW 是 Taiwan 醫療 triage 4 級視覺語彙,zh-CN 是結構對稱
  - Bilingual user 可能困惑(同字不同 severity)
  - Resolution: Phase 1A 找台灣 + 大陸母語醫療人員 review,決定統一或保留 drift

- **[P1] Research/Explain prompt 仍 inline 在 Python files(PRD § 6.5 違規)**
  - `generator.py` 有 4 個 inline prompt string(`_get_system_prompt` + `FALLBACK_PROMPTS` × 3)
  - `explain_service.py` 有 1 個 inline prompt(`EXPLAIN_GENERATION_PROMPT`)
  - 違反 PRD § 6.5 "All system prompts 在 api/prompts/ 目錄下獨立檔案"
  - 2.9 當下為了 scope 保護選擇 inline 編輯,未抽檔
  - Resolution: 2.7 Explain 臨床推理強化時順便 extract `explain_service.py`(已完成 — Step 5 e05102e);Research 的 prompt extract 排 Phase 1A
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread diagnostic

- **[P2] Dead code in `api/rag/generator.py`**
  - `FALLBACK_PROMPTS["verify"]` (dict entry at line ~34): Verify 走 `api/prompts/verify_system.md` 不經 `generator.generate_stream`,此 key 從未被呼叫
  - `FALLBACK_PROMPTS["document"]` (dict entry at line ~34): 舊 patient-letter / consultation feature,全 codebase grep 無 caller
  - `_get_system_prompt()` `query_type == "verify"` branch (line ~263): 同上
  - Verification method: grep `query_type` + `FALLBACK_PROMPTS\[` 確認無活 caller,或 trace 從 /api endpoints 哪些 route 到 `generator.generate_stream`
  - Resolution: Phase 1A i18n mop-up 或 2.7 Explain 抽檔時順手 sweep dead code
  - Risk if kept: wasted maintenance attention, false impression for future readers, ~150-300 prompt tokens wasted per call (dead FALLBACK entries not triggered but pollute code)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread (diagnostic flagged)

- **[P0 → 已部分解決, status unclear]** Landing Page 收尾
  - 發現 2026-04-20(2.9 ship 後)
  - **兩個問題:**
    1. **Hero placeholder 硬寫英文** — 已解 (commit a22ce9f "Landing Page i18n 16-language expansion" 2026-04-21)
    2. **Privacy section 過長** — 5 條「我們承諾」+ 3 條「它不代表什麼」共 8 個 bullet。Privacy section 簡化狀態 unclear — verify at Phase 0 Retrospective.
       - 決策(solo founder 2026-04-20 review):
         - **刪除**:3 條「它不代表什麼」全部(移至 Privacy Policy 處理,該頁為 Phase 1A i18n mop-up)
         - **壓縮**:5 條承諾 → 3 條:
           - ✓ 不需驗證身分或執照
           - ✓ 預設匿名,不要求真實姓名
           - ✓ 資料不外流、不訓練 AI 模型
  - **Resolution at Phase 0 Retrospective**: verify Privacy section state in production. If still 8-bullet, apply the simplification per spec. Logged 1101dcc.

- **[P1 → Phase 0 Retrospective] CLAUDE.md 結構性精簡 — ✅ DOING NOW (2026-04-30 doc reorg)**
  - 問題:
    - 當前 ~574 行 (post § 2.7 結案),違反 LLM instruction budget 最佳實踐(社群共識 < 300 行)
    - 多處內容為 reference material 而非 instruction(architecture 詳細、env vars、file paths),違反 Progressive Disclosure pattern
    - Current Development Status / Discovered Gaps 與 FEATURE_AUDIT.md / decision docs 有 drift 風險
  - **Resolution in progress (2026-04-30 commits 3fdeddc, 59002d1, [this commit])**:
    1. ✅ Drift sync (3fdeddc)
    2. ✅ Architecture extract → docs/architecture.md (59002d1)
    3. ✅ STATE.md / BACKLOG.md / ARCHIVE.md / TECH_DEBT.md split (this commit)
    4. PRD.md status markers (next commit)
    5. ADR 002 doc reorg rationale (final commit)
  - 驗收:CLAUDE.md ~150 lines after this commit; new doc structure documented in ADR.
  - Discovered: 2026-04-21(Landing Page ship 後 solo founder 討論 instruction budget best practice 時識別)

- **[P2]** Clerk JWT authorized_parties (azp) claim 未驗證
  - **現況**: `api/server.py` 使用 hand-rolled `jose_jwt.decode` with `options={"verify_aud": False}`,依賴 JWKS RS256 簽名驗證 + issuer 隱式信任。未檢查 `azp` claim。
  - **風險**: 理論上若攻擊者能取得 Clerk 公開 JWKS 並知道 issuer,可能能 forge token 通過 signature verify。實務上極難(需拿到使用者 session token 或攻破 Clerk infra),但 defense-in-depth 標準作業應驗證 authorized_parties。
  - **Resolution**:
    - 新建 `CLERK_AUTHORIZED_PARTIES` env var(allowlist of origin URLs)
    - `api/server.py` JWT decode 後手動檢查 `azp` claim 在 allowlist 中
    - 或:改用 `fastapi_clerk_auth` 套件的完整驗證鏈(當前 import 未使用)
  - **Priority**: P2(未有明確攻擊 vector 但屬 best practice);排入 Phase 0 Retrospective 或 Phase 1A 安全 review
  - **Discovered**: 2026-04-22 during 2.8 Round 2A Clerk config diagnose

- **[P2 → Round 3 或 Phase 1A]** 阻止 signed-in user 訪問 `/sign-in` 和 `/sign-up`
  - **現況**: logged-in user 打 `/sign-in` 會看到 Clerk SignIn card,可能困惑
  - **解法**: `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx` 頂部加 `<SignedIn><RedirectToResearch /></SignedIn>` wrapper(或 useEffect + router.push('/research'))
  - **Priority**: P2 UX polish
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P2 → Phase 1A]** Backend error response shape 不統一
  - **現況**: pre-Round 1B endpoints 回 `{error: "code"}`,Round 1B 新 `api/errors.py` 回 `{type: "code", ...}`
  - **Round 2B frontend 處理**: dual-read pattern 兼容 `const code = data.type ?? data.error`
  - **解法**: Phase 1A 統一 endpoint error shape(建議走 `{type, message}` 新 shape),frontend 簡化掉 dual-read
  - **Priority**: P2 consistency
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P1 → Round 3 已部分解決, verification needed]** Anonymous quota message 不 surface 正確 type
  - **現況**: E2E Test 4 發現 anon daily quota 耗盡時,前端顯示通用 "Too many requests. Please wait a moment and try again.",而非 Round 2B 預期的 "Daily free limit reached. Sign up to continue."
  - **Root cause 假設**: FastAPI `HTTPException(status_code=429, detail={type: "anonymous_quota_exceeded", ...})` 序列化後 response body 是 `{detail: {type: ...}}` 而非 `{type: ...}` → `utils/sse.ts` 的 dual-read `data.type ?? data.error` 抓不到(真實路徑應為 `data.detail?.type ?? data.type ?? data.error`)
  - **Round 3 commit 24b1d79 shipped AnonymousUpgradeCTA infrastructure**. Quota message specific fix verification still needed.
  - **Verification needed at Phase 0 Retrospective**: trigger anon daily quota in prod, confirm correct message + CTA path appears.
  - **Priority**: P1(軟啟動前必須 fix,影響 anon-to-signup 轉換訊息)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 4 E2E

- **[P2]** No backend PostHog client (`api/` has no `import posthog`)
  - **現況**: All PostHog events flow through `utils/analytics.ts` `track()` from the frontend. Server-side events (e.g. PRD §4.5 需求 7 `share_link_visited`, which fires when LinkedIn/X/Facebook bots scrape OG cards) cannot be captured.
  - **Risk for §4.5**: `share_link_visited` was specced as backend-fired with `referrer_domain` + `is_first_view`. Per 2026-05-05 PRD §4.5 修訂, this event is being moved to frontend (accepts that bot views are not counted — arguably correct behavior, view_count remains accurate via server increment).
  - **Resolution if needed later**: Add `posthog` to requirements.txt + module-level `Posthog(api_key, host=...)` in `api/server.py` + helper for server-side `track()`. ~10 lines. Required only if a future feature needs server-side analytics that frontend cannot emit.
  - **Priority**: P2 — current §4.5 design absorbs this gap; no other open need. (TECH_DEBT.md has no P3 tier; lowest is P2.)
  - **Discovered**: 2026-05-05 during §4.5 PHASE A smoke test (PostHog server-side fire was specced but no client existed).

- **[P2]** ShareButton anonymous gating uses redirect, not in-context AnonymousUpgradeCTA modal
  - **現況**: `components/ShareButton.tsx` for anonymous users routes to `/sign-up` via `router.push` instead of opening `components/AnonymousUpgradeCTA.tsx` modal in-place. PRD §4.5 修訂 1 specced "AnonymousUpgradeCTA 風格" prompt; PHASE B chose redirect to keep scope narrow.
  - **Conversion impact**: redirect breaks the user's high-intent moment ("I just got an answer, I want to share") by yanking them off the current page. Modal pattern (per ADR 001 / commit 24b1d79) preserves context. Anonymous → registered conversion rate from share-locked trigger is likely lower than from other triggers (`third_query`, etc.) for this reason. Magnitude unknown until data comes in.
  - **PostHog attribution preserved**: `share_modal_opened` fires with `gated:true, gate_reason:'anonymous'` so the funnel is measurable.
  - **Resolution**: extend AnonymousUpgradeCTA with a new `trigger='share_locked'` value (~5-10 LOC). Update ShareButton to render `<AnonymousUpgradeCTA trigger='share_locked' onClose={...} />` instead of `router.push('/sign-up')`. Re-test 8k flow.
  - **Priority**: P2 — measurable conversion cost, but not blocking §4.5 ship. Pick up when GTM data shows share-locked → signup conversion underperforming other triggers, OR opportunistically during Phase 1B Anonymous Trial Flow polish (per STATE.md Phase 1B Week 7 work item).
  - **Discovered**: 2026-05-06 during §4.5 PHASE B implementation; deviation accepted by reviewer to avoid widening PHASE B scope.
  - **2026-05-06 update**: Resolution scope unchanged but now applies to BOTH `variant='inline'` (history.tsx) and `variant='navbar'` (research/verify/explain pages, commit ca571ce). When implemented, fix in one place propagates to both call sites since both share the same anon-gating code path inside `components/ShareButton.tsx`.

- **[P2 → Dodo 付費啟用前]** `CLERK_SECRET_KEY` 仍是 `sk_live_` 對 Dev instance user checkout 會 500
  - **現況**: Round 2B JWT Dev/Prod mismatch fix 只改 `CLERK_JWKS_URL` 指向 Dev instance (`joint-guppy-23.clerk.accounts.dev`);`CLERK_SECRET_KEY` 仍為 Prod `sk_live_NhG...`
  - **影響範圍**: Dodo checkout path 會用 `CLERK_SECRET_KEY` call Clerk Backend API 取 user email/name;Dev instance user ID 對 Prod secret key 查不到 → 500 error
  - **現行不爆的原因**: Round 2B 測試只跑 Research + Verify,沒動到 Dodo checkout;Dodo 付費要到 Phase 1A 才啟用
  - **解法** (Dodo 付費啟用前):
    - 改用 Dev instance secret key(`sk_test_...`)for localhost + Dev user 測試
    - 或將 Prod env 與 Dev env 的 Clerk 設定徹底分離(`fly secrets` vs `.env`)
    - 驗證 `/api/checkout/dodo` + `/api/webhook/dodo` 路徑對 Dev user 能順利 create subscription
  - **Priority**: P2(不 block 當前軟啟動;Dodo 付費啟用是 Phase 1A scope)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 5 Clerk JWT Dev/Prod mismatch fix

- **[P2]** Native-speaker review pending for §4.5 share i18n legal-weighted strings
  - **現況**: `utils/i18n-share.ts` ships 16-locale ShareTranslations (commit b378659). en + zh-TW user-reviewed for legal precision; ja user-reviewed PASS during PHASE B live test. Other 12 locales (zh-CN, ko, es, fr, de, it, pt, th, ar, hi, bn, he, vi) are machine-translation baseline.
  - **Risk**: legal-weighted strings — `modalConsentCheckbox` (consent attestation list of identifiers + irrevocability clause), `publicDisclaimer` (visitor-facing AI medical disclaimer), `publicShortDisclaimer`, `settingsRevokeConfirm` — translation accuracy in those 12 locales unverified. Specific identifier list (病患姓名/身分證字號/病歷號/健保號) and "無法完全收回" clause must survive translation in any language Share is opened to.
  - **Resolution**: native-speaker review of the 4 legal-weighted keys × 12 unreviewed locales (= 48 strings). Trigger: before opening Share to non-en/zh-TW/ja traffic in production. Reviewer can pre-launch focus on Vela target locales (likely ja already done; ko + es + th worth prioritizing for SE Asia GTM).
  - **Priority**: P2 — gates non-en/zh-TW/ja Share traffic; not blocking en/zh-TW soft launch.
  - **Discovered**: 2026-05-06 during §4.5 UX polish 2.5 i18n rollout.

- **[P2]** /terms + /privacy pages are en-only — i18n retrofit pending
  - **現況**: pages/terms.tsx + pages/privacy.tsx are hardcoded English JSX with no i18n infrastructure (no useLang(), no per-locale dict, no markdown content). Both predate the §4.5 share i18n 16-locale rollout (commit b378659). 17 sections total (9 Terms + 8 Privacy) are en-only despite the rest of the product being 16-locale.
  - **Risk**: legal compliance — non-en/zh-TW users see the entire ToS + Privacy Policy in English regardless of their UI locale, which weakens consent validity in jurisdictions requiring local-language disclosure (notably zh-TW, ja, ko per Vela's Tier 1 GTM target). Discovered 2026-05-08 during §4.5 PHASE D when Share clauses were added en-only to match existing pattern.
  - **Resolution**: dedicated commit to refactor /terms + /privacy to 16-locale i18n. Approximately 238 legal-weighted strings (17 sections × 14 added locales). Translation should be reviewed by qualified legal translator per locale, NOT machine-translation baseline (this is a hard commitment to users, unlike share i18n strings which are UI labels). Native-speaker review process should align with existing P2 entry "Native-speaker review pending for share i18n legal-weighted strings".
  - **Priority**: P2 — gates non-en production traffic at scale (Tier 1 GTM expansion to JP/KR/ID/VN/PH would require this). Not blocking soft launch in en + zh-TW markets if both legal pages have at least zh-TW translation by then. Consider doing zh-TW first as a Phase 1A gate (since zh-TW is Vela's home market), then ja + ko before Phase 1B Tier 1 expansion.
  - **Discovered**: 2026-05-08 during §4.5 PHASE D recon (commit 6f7a154 follow-up).

- **[P3]** Backend dotenv loader doesn't read .env.local
  - **現況**: FastAPI backend reads `.env` but NOT `.env.local`. During §4.5 PHASE B local dev, user set `VELA_PUBLIC_BASE_URL=http://localhost:3000` in `.env.local` (Next.js convention) but backend continued falling back to production URL hardcoded default. User had to set `$env:VELA_PUBLIC_BASE_URL` via PowerShell process env to override.
  - **Risk**: dev quality-of-life paper cut. Easy to accidentally generate share URLs pointing to production from localhost. (Did happen once during this work — user spent 30min debugging "share URL goes to production landing page" before identifying the env-loading mismatch.)
  - **Resolution**: pick one — (a) extend backend dotenv loader to chain `.env.local` before `.env` (matches Next.js convention; least surprise); (b) document in `.env.example` that backend-side vars (`VELA_PUBLIC_BASE_URL`, `SHARE_CREATED_BY_SALT`) belong in `.env`, not `.env.local`. (a) is preferred for symmetry.
  - **Related backend latent bug**: `VELA_PUBLIC_BASE_URL` fallback when unset defaults to production URL. Should fall back to `http://localhost:3000` if `TEST_MODE=true` and not set. Bundle the fix with (a).
  - **Priority**: P3 — dev-only.
  - **Discovered**: 2026-05-06 during §4.5 PHASE B smoke test 8l.

- **[P3]** components/Untitled stale backup file
  - **現況**: `components/Untitled` is a tracked file containing an old copy of CitationPanel.tsx with the StarRating component still defined and referenced. Discovered 2026-05-08 during Commit 211d9f7 (5-star UI removal) — the active CitationPanel.tsx was cleaned but the Untitled backup still has the dead code.
  - **Risk**: minor — stale backup files clutter codebase grep results and risk being mistaken for the active component. No runtime impact (file is not imported by any active code).
  - **Resolution**: at Phase 0 Retrospective, delete `components/Untitled` (or rename to `.bak` and gitignore). Verify it's truly orphaned via `git grep "Untitled" -- '*.tsx' '*.ts'` first.
  - **Priority**: P3 — codebase hygiene.
  - **Discovered**: 2026-05-08 during dogfooding star-removal commit.

- **[P2 → Phase 0 production deploy checklist]** `/explore/category/:category` dev rewrites gap
  - **現況**: §4.6 PHASE D shipped category listing pages at `/explore/category/:category` (commit a8361f5). The Next.js static export rewrites work in production via Fly.io / CDN, but `npm run dev` does not rewrite `/explore/category/foo` → the category listing page. During PHASE D live test, navigation from breadcrumb category link 404'd on localhost.
  - **影響範圍**: dev-only — production unaffected (static export + edge rewrites resolve correctly). Affects local dogfooding + future development of Explore category UI.
  - **Resolution**: ~15 min followup commit — add `rewrites()` config in `next.config.js` (or equivalent middleware) so `/explore/category/:category` resolves to the static page in dev. Gate on Phase 0 production deploy checklist so dev + prod parity is verified before soft launch.
  - **Priority**: P2 — not blocking production ship; blocks local dogfooding of category listing UI.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test (PHASE D dogfooding).

- **[P2 → Phase 0 production deploy checklist]** CLI sync overwrites DB status with markdown status, silently un-publishing pages
  - **現況**: `scripts/explore_cli.py` (PHASE C, commit 0f139d2) sync command reads the `status:` frontmatter from each markdown file and writes it to the `explore_page.status` DB column. If a markdown file was created with `status: draft` and the DB row was later flipped to `published` (via direct SQL or admin UI), the next CLI sync silently overwrites `published` → `draft`, un-publishing the page without warning.
  - **影響範圍**: caused live test case (a) FAIL during PHASE D dogfooding — `/explore/metformin-contraindications-renal` returned 404 until the markdown `status:` was bumped to `published` and re-synced. Could silently break published pages in production if CLI is run after a manual DB status change.
  - **3 candidate fixes** (decide at Phase 0 deploy checkpoint):
    1. **Markdown-as-source-of-truth (current behavior, make explicit)**: keep current logic but log a WARNING when CLI flips a DB `published` → `draft`. Force a `--force-unpublish` flag to actually demote. Safest if content workflow is "markdown is authoritative".
    2. **DB-as-source-of-truth for status**: CLI never writes `status` column; only writes content fields. Status is managed via separate admin UI / SQL. Requires admin tooling.
    3. **Two-way merge**: CLI writes markdown `status` only if DB row is missing OR DB `status='draft'`. Never demote `published` → `draft` via CLI. Compromise — keeps markdown as primary source for new content while preventing silent unpublish.
  - **Resolution**: pick one of the 3 fixes at Phase 0 production deploy checkpoint, before any production content is published via CLI. Recommendation: fix #3 (two-way merge, no demote) is least surprising and requires no new tooling.
  - **Priority**: P2 — silent data corruption potential; not blocking ship but must resolve before production content sync.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test case (a) FAIL diagnosis.

- **[P2 → Phase 0 production deploy checklist]** Locale fallback — Accept-Language non-en/zh-TW returns 404 on /explore pages
  - **現況**: §4.6 PHASE B sitemap-explore.xml hreflang logic skips missing locales (commit 8fb10ca). Explore pages exist in en + zh-TW only at PHASE D ship. When a user (or SEO crawler) hits `/explore/<slug>` with `Accept-Language: ja` / `ko` / `es` / etc., the server returns 404 instead of falling back to en (or zh-TW for zh-* variants).
  - **影響範圍**: production blocker for SEO crawler discovery in non-Tier-1 locales. Google / Bing crawlers identifying as non-en locales (e.g. Googlebot-Mobile crawling from JP region) would see 404 and drop the page from index. Also blocks human users from non-Tier-1 locales reading existing en content while translations are pending.
  - **Resolution**: at Phase 0 production deploy checklist — implement locale fallback chain. Recommended order: requested locale → en (universal fallback). For zh-* variants: zh-CN → zh-TW → en. Implement in the Next.js `/explore/[slug]` page resolver or middleware. Verify with Google Rich Results Test (PHASE E acceptance) hitting from multiple Accept-Language headers.
  - **Priority**: P2 — production SEO blocker for non-Tier-1 locales; must resolve before soft launch if non-en/zh-TW indexing is desired.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test (Accept-Language testing).

- **[P3]** `api/providers/factory.py` creates a new Provider instance on every `get_xxx_provider()` call
  - **現況**: Each call to `get_generator_provider()` / `get_lightweight_provider()` / `get_embedder_provider()` etc. instantiates a fresh `OpenAIProvider` / `GroqProvider` (which constructs a new `AsyncOpenAI` httpx client). Acceptable for current call frequency — most call sites cache the binding at module load or class `__init__` (e.g. `VectorStore.__init__`).
  - **Risk**: minor — if any hot path repeatedly calls a factory (e.g. inside a per-request loop), HTTP client churn could hurt latency. No such hot path exists today.
  - **Resolution**: at Phase 0 Retrospective or next opportunity, consider `functools.lru_cache` on factory functions, or module-level singletons keyed by `(provider_name, model)`. Validate via profiling before optimizing.
  - **Priority**: P3 — quality-of-life / future maintenance.
  - **Discovered**: 2026-05-13 during §2.1 PHASE B (wiring 3 Low files to Provider abstraction).

- **[P2 → Phase 1A §3.1] Clerk publicMetadata.plan dormant dual-source vs user_usage.plan_type — discovered 2026-05-19 pre-deploy audit** — **[CONSOLIDATED: 1 of 3 user-lifecycle-governance items (this + the `user.deleted` webhook entry below + BACKLOG "Deletion-feature C", the superset); resolve together under one user-lifecycle ADR per §3.1.]**
  - **背景**: Frontend `_app.tsx` PostHog identify() reads `publicMetadata.plan` and forwards as person property. Backend gating uses `user_usage.plan_type` exclusively. Manual Clerk Dashboard inspection of the only real Pro user (user_3BN1HkLU7kw7458c351oqMVwmv9, Andrew personal) confirmed `publicMetadata.plan` has never been written. TypeScript signature suggests alternative source-of-truth that doesn't exist in practice.
  - **影響範圍**: No active drift today (publicMetadata.plan reads `undefined` → fallback path). Risk surfaces if any external system (Clerk Dashboard rule, future webhook, manual admin action) writes `publicMetadata.plan` without coordinating with user_usage. Then frontend identify() and backend gate disagree on plan_type, silently. PostHog person properties become unreliable for plan-segmented analytics.
  - **Resolution**: Phase 1A §3.1 audit decision G4 already taken: user_usage.plan_type is authoritative; drop publicMetadata.plan read path from `_app.tsx::identify()`. Concrete change: remove `plan` property from `publicMetadata` TypeScript signature in `types/clerk.ts` (or equivalent); update `_app.tsx::identify()` to source plan_type from backend `/api/user/usage` instead.
  - **驗證方法**: After fix, verify `_app.tsx` no longer references `publicMetadata.plan`; PostHog identify event includes `plan_type` from backend response.
  - **Discovered**: 2026-05-19 pre-deploy DB state audit (3 Pro users in user_usage: 1 real + 1 orphan-now-cleaned + 1 TEST_MODE marker; orphan row had `dodo_customer_id = test_cust_*` Dodo sandbox leftover, cleaned same session)

- **[P2 → Phase 1A §3.1] Clerk user.deleted webhook → user_usage cleanup not wired — discovered 2026-05-19** — **[CONSOLIDATED: the Clerk `user.deleted` webhook is also one of the 3 Triggers in BACKLOG "Deletion-feature C" (the superset record); this entry = the `user_usage`-cleanup slice. Verified 2026-06-25: still no `/api/webhooks/clerk` handler. Pair with the publicMetadata.plan entry above under one user-lifecycle ADR.]**
  - **背景**: user_3B939OrkarbJWpfTT8nCi9kDJ1B was deleted from Clerk Dashboard at unknown earlier date but user_usage row persisted with plan_type='pro'. No automatic sync between Clerk user.deleted webhook and user_usage table. Manually cleaned 2026-05-19 via psycopg2 transaction; full backup preserved in docs/retrospectives/phase-0-2026-05.md § 1.2.
  - **影響範圍**: Low for current production scale (1 known orphan row in 2 months). Risk compounds over time + after soft launch: deleted users leave dangling user_usage rows skewing plan_type distribution analytics, holding stale Dodo customer references, no path for Right-to-Erasure GDPR compliance.
  - **Resolution**: Phase 1A §3.1 scope. Wire Clerk webhook `user.deleted` event to a new handler in `api/server.py` that performs (soft-delete vs hard-delete decision TBD during §3.1 work) on the user_usage row. Decision tradeoff: hard-delete simpler but loses analytics history; soft-delete (e.g. `deleted_at` timestamp column) preserves history but adds complexity to all queries.
  - **驗證方法**: After implementation, test in dev by deleting a test Clerk user, verify user_usage row updated/removed per chosen strategy. Add idempotency: webhook may fire multiple times; handler must be safe under repeated invocation.
  - **Discovered**: 2026-05-19 pre-deploy DB state audit; related to G4 publicMetadata.plan entry above (both are user lifecycle governance issues; consider folding into a single user lifecycle ADR during §3.1 design)

- **[P3 → opportunistic] deploy.ps1 hardcoded 10-second settle insufficient for vector store cold start — discovered 2026-05-19**
  - **背景**: `deploy.ps1` Step 2 sleeps 10 seconds after `fly deploy` exit before running Step 3 machine status check. But vector store load (FAISS + 690 documents) takes 30-60 seconds on cold machine boot. Manual workaround during 2026-05-19 deploy: insert additional 60-second sleep before running PART B.3 smoke curls.
  - **影響範圍**: Low operational. Affects deploy day operator experience only — if operator runs PART B smoke immediately after deploy.ps1 exit, vector store may still be loading and queries silently return 0 results until ready. Confusing but not user-facing.
  - **Resolution**: Two options. (A) Parameterize settle time via env var (e.g. `DEPLOY_SETTLE_SEC=60`). (B) Replace fixed sleep with poll loop hitting `/health` or `/api/status` until 200, timeout after N seconds. Option B is correct long-term but adds complexity; Option A is 3 LoC.
  - **Discovered**: 2026-05-19 production deploy day, observed during PART B verification

- **[P3 → opportunistic] Raw SQL migration introspection missing — no schema_versions table — discovered 2026-05-19**
  - **背景**: Production Neon migrations are applied manually via `psql -f migrations/00X.sql`. Pre-deploy audit verified migrations 002-005 applied via table-presence inference (e.g. `shared_query` table exists → 004 applied), NOT via a versioning table. No `alembic_version` table exists (project doesn't use alembic); no equivalent introspection mechanism.
  - **影響範圍**: Currently fine while migration count is low (5 migrations total). Fragile as migration count grows: "what's applied" inferred from side-effects, easy to lose track during a multi-day deploy or rollback scenario. Phase 1A §3.1 introduces migration 006 (user_profile) — natural point to add lightweight introspection.
  - **Resolution**: Add a minimal `schema_versions(filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW())` table in a new migration (could bundle with 006). Update existing `migrations/00X.sql` files to `INSERT INTO schema_versions (filename) VALUES ('00X_name.sql') ON CONFLICT DO NOTHING;` at end. Backfill 002-005 entries manually in production. Eliminates "is X migration applied" guesswork forever.
  - **Discovered**: 2026-05-19 pre-deploy state audit (Claude Code investigation found no alembic_version table and inferred migration state from public schema table list)

- **[P3 → Phase 1B Week 4] Research response missing canonical clinical terms — 4 WARN pattern (2026-05-19 golden run)**
  - **背景**: 2026-05-19 golden eval 4 個 WARN 中 3 個(R03/R09/R20)為 Research response 漏掉 canonical clinical 元素:
    - R03: AFib anticoagulation indications 沒提 CHA2DS2-VASc(THE stroke risk scoring tool)
    - R09: Lithium therapy monitoring 沒提 thyroid function(standard protocol — 30% 引起 subclinical hypothyroidism per literature)
    - R20: ACE-I in pregnancy 沒提 safer alternatives(methyldopa / labetalol — physician 自然 follow-up question after "contraindicated")
  - **第 4 個 WARN(E26)**: empty_input error 路徑正確(blocked = ✅),wording 觸發 fuzzy must_contain miss,unrelated 議題,low priority
  - **Pattern**: Research generator / RAG retrieval 可能對「canonical scoring tools」「standard monitoring protocols」「alternative drug recommendations」有 systematic under-coverage。3/3 Research WARN 都是 "missing canonical term" 而非 hallucination / fabrication / off-topic — pattern 一致。
  - **Hypothesis**:
    - (a) RAG retrieval 偏向 high-citation general papers,specialty-specific scoring tool papers ranking 較低 — retrieval-side gap
    - (b) Generator prompt 沒明確要求「contraindicated → suggest alternatives」/「monitoring → list all canonical parameters」logical chain — prompt-side gap
    - (c) Token limit 截斷 detail — output-length gap (less likely given other detail present)
  - **影響範圍**: Medium for clinical user trust. Physicians expect canonical terms (CHA2DS2-VASc, MELD, BISAP, INR target ranges, etc.) — their absence reads as "incomplete answer" even if the medical content is correct.
  - **Resolution**: Phase 1B Week 4 Verify 強制英文 + system prompt polish window,順手 evaluate Research prompt 是否需要 reinforcement on canonical terms。Candidate intervention: Research system prompt 加一段「if answer involves treatment decision, always mention canonical scoring tools (e.g. CHA2DS2-VASc for AFib, MELD for liver), standard monitoring protocols (e.g. thyroid for lithium, INR for warfarin), or alternative drugs when stating contraindication」.
  - **驗證方法**: Phase 1B Week 4 fix 後重跑 R03 / R09 / R20,目標全 PASS (min_score ≥ 70). 如果還 WARN 表示 root cause 是 retrieval 不是 prompt,需要 deeper RAG eval (Hypothesis a).
  - **Related**: Synergy with TECH_DEBT entry "Verify 答案品質 nuance issues — dogfooding 發現 (2026-05-06)" Task A which also addresses Verify/Research system prompt polish in Week 4. Both can share the same work session.
  - **Discovered**: 2026-05-19 post-deploy golden eval run (96.7% overall pass rate, 4 WARN, 0 FAIL — no regression)
  - **2026-06-13 re-measurement (Task-A QA Stage 1, `golden_results_20260613_144748.json`)**: pattern persists. **R09 (lithium/thyroid) now PASS** (improved). **R03 still omits CHA₂DS₂-VASc**; **R16/R20 still under-cover safer alternatives** (R20 ACE-I-in-pregnancy alternatives; R16 added to the same family). The "canonical scoring tools / standard monitoring protocols / alternative drugs" under-coverage is now confirmed across two golden runs ~1 month apart → reinforces the Week-4 Research system-prompt reinforcement candidate above. (R10 digoxin completeness is logged as its own entry at the top of this file.)

- **[P2 → Phase 2 candidate] chat-history privacy model — docs were stale + behavior is "honest but not maximal"**
  - **Discovered**: 2026-05-25 during blog llms.txt fact-check (the public-facing privacy claim audit that preceded /llms.txt copy).
  - **Background — actual shipped behavior**: L0 anonymous queries are not tied to any account / not written to ChatHistory. L1 (signed-in free, "Vela for Work") + L2 Pro both write to ChatHistory on every successful Research / Verify / Explain request. Universal 180-day retention via `_cleanup_old_records` at `api/server.py:179–197`. No per-tier distinction. No `history_enabled` opt-in toggle exists anywhere (verified via repo-wide grep `history_enabled|enable_history|store_history` → 0 hits; no DB column on user_usage or user_profile; no Settings UI; no frontend flag).
  - **Public surface (pages/privacy.tsx) is HONEST and matches code**: §1 "Anonymized and sanitized query content"; §2 "We do not store PHI" (PHI gate at request boundary enforces); §4 "up to 6 months ... automatically deleted" (matches 180-day cleanup exactly). No public over-claim.
  - **Stale internal-PRD claims now reconciled in this commit (docs/PRD.md §6.4 + §2.8)**: §6.4 line 2111 previously said "chat_history 僅 Pro 使用者明確開啟時" (false — never implemented). §6.4 line 2115 previously said "絕不儲存:查詢原始文字(Free 使用者)" (false — L1 free queries DO write to ChatHistory; Research sanitizes-for-log first, Verify stores drug-names-only, Explain stores `report_text[:500]` after PHI gate). §2.8 line 716 previously said "7 天 history" for L1 (ambiguous — was display scope, not retention). All three reconciled with this commit's PRD edits.
  - **Why this is P2 not P0/P1**: the public-facing claims are accurate. No user was promised a thing the code doesn't deliver. No regulatory exposure, no privacy fraud. The drift was internal-doc-only.
  - **Two follow-up considerations for Phase 2 (candidates, NOT bugs)**:
    - **(a) "Anonymized" wording precision**: pages/privacy.tsx §1 uses "Anonymized and sanitized query content". ChatHistory rows do carry the Clerk `user_id` string — so strictly this is **pseudonymized** (re-identifiable with the auth provider's records), not **anonymized** (irreversibly de-linked). Defensible under most privacy regimes but worth a legal-wording review before any compliance audit (e.g. GDPR Article 4 distinguishes the two). Cheap fix if needed: change "Anonymized" → "Pseudonymized" or rephrase.
    - **(b) Stronger privacy model fits the brand**: Vela's positioning is Privacy-first (§0.3) and the landing card explicitly says "NO ACCOUNT NEEDED". For a Privacy-first product, a stronger chat-history model (free tier not stored at all, or shorter retention + Pro-only opt-in toggle) would better live up to positioning. This is a candidate feature — only worth building if there's market/regulatory pull. Implementation surface: new `history_enabled` column on user_profile, Settings UI toggle, write-site gates at the 5 ChatHistory locations in api/server.py (697, 898, 938, 1024, 1128), per-tier `_cleanup_old_records` retention logic.
  - **Resolution target**: Phase 2 candidate (neither blocks anything today). If pursued: change scope ~1d for option (a) wording-only, ~3-4d for option (b) opt-in feature + retention-per-tier.
  - **Reference**: investigation chat session 2026-05-25 (preserved verbatim); public privacy.tsx §1-§4; docs/PRD.md §6.4 + §2.8 reconciled lines.

- **[P3 → revisit only on §6.1 migration] i18n-ui.ts is whole-file flat camelCase vs PRD §6.1 dot-namespace**
  - **Discovered**: 2026-06-08 during §3.1 PHASE D (OnboardingWizard i18n). PRD §6.1 prefers dot-namespaced keys (`onboarding.*`), but `utils/i18n-ui.ts` is entirely flat camelCase on a strict `UITranslations` interface (no key-level fallback; `getUI` falls back whole-object only). The 31 new PHASE-D onboarding keys followed the existing file style (decision 4a) for file-internal consistency rather than introducing a lone nested `onboarding.*` island.
  - **Resolution**: no action unless a deliberate §6.1 dot-namespace migration of the whole `i18n-ui.ts` is ever undertaken — at which point the PHASE-D `onboarding*` keys migrate with the rest. Cosmetic/convention only; zero functional impact.

- **[P3 → docs reconciliation] PRD §3.1 Role enum ↔ §3.2 Step-2 display list drift**
  - **Discovered**: 2026-06-08 during §3.1 PHASE E (role_category). §3.2/PHASE D ship role values `pharmacy_student`, `nursing_student`, and the therapist roles `physical_therapist`/`occupational_therapist`/`speech_language_pathologist` that the PRD §3.1 Role enum + the G7 role_category student-bucket *enumeration* (L1013–1024) don't list.
  - **Current handling**: PHASE E `utils/contextOptions.ts` `roleToCategory()` maps them by G7 *intent* — PT/OT/SLP → `clinical` (all community/* + hospital/* are clinical), pharmacy_student/nursing_student → `student`. No functional bug; analytics bucketing is correct.
  - **Resolution**: a docs pass — update PRD §3.1 Role enum to match §3.2's shipped list, and redefine the G7 `student` bucket as pattern-based ("any specific `*_student` / student-track role") rather than a literal 3-value enumeration, so future student roles don't need re-listing. Convention/docs only.

- **[P1 · R5 privacy/compliance] Privacy claims ↔ actual backend drift** — **(a)+(b) RESOLVED 2026-06-09 (legal-reviewed stopgap)**; (c)+(d) follow-ups below
  - **(a)** ~~PRD §0.3 L93 "Stateless / server does not retain query content" vs `ChatHistory` persisting query+answer 6mo for signed-in users~~ → **RESOLVED 2026-06-09 (`effc3ea`):** chose "amend wording to match shipped behavior" — the inaccurate "stateless" claim is replaced in **PRD §0.4** with the accurate retention principle (L0 not stored; signed-in PHI-masked 6mo deletable; Pro pseudonymous hash; billing 5yr de-identified). (The offending text was in §0.4, not §0.3.)
  - **(b)** ~~Privacy Policy doesn't disclose the PHASE-E Pro `user_context_hash` sync~~ → **RESOLVED 2026-06-09 (`bebe20e`):** the /privacy English stopgap now discloses the Pro 16-char pseudonymized hash sync (§1 "Pro Subscription Preferences"), cross-border (Tokyo/Fly.io), 5yr billing retention, 30-day email deletion, and an English-prevails disclaimer; all inaccurate "anonymized" stored-data wording → "de-identified/pseudonymized".
  - **(c) [PENDING follow-up]** The PRD §0.3 Privacy-first list also appears on the **Landing Page + About** (PRD L76 "should appear … all consistent"). Those surfaces must be aligned to the new de-identified/pseudonymous framing — future copy pass, not this batch.
  - **(d) [PENDING follow-up]** The /privacy "backups overwritten within 24 hours" wording is a defensive buffer over the current **Neon Free** ~6h PITR window. **When Neon upgrades to a paid plan** (longer PITR), revise the /privacy backup-residual wording accordingly.
  - (The onboarding privacy-card W1 reword 2026-06-08 already avoids the false "never stored" claim. The Explain raw-report `ChatHistory.question` sanitize gap is tracked in its own task — not duplicated here.)

- **[P2 · R5 privacy] `ChatHistory.answer` stored unsanitized (all features)** (logged 2026-06-08)
  - `ChatHistory.answer` is persisted unsanitized for Research / Verify / Explain — an LLM-generated answer could theoretically echo an identifier from the input. Upstream `_check_phi` (`api/server.py:1088`) blocks identifiable input at the boundary, and "answer unsanitized" is the consistent established behavior across all features, so this is a **broader policy decision** (sanitize ALL stored answers?) — not a one-line fix. Distinct from the Explain `ChatHistory.question` raw-storage gap, which WAS fixed 2026-06-08 (now mirrors AuditLog `sanitize_for_log`). Pending decision; **do NOT auto-fix.**

- **[P2 · R5 privacy] `PHIDetector.sanitize_for_log` misses the Taiwan mobile format** — **RESOLVED 2026-06-09 (`751705b`)**
  - e.g. `0912-345-678` was NOT masked by the shared sanitizer, so it survived into both `AuditLog.query_content` and `ChatHistory.question`. Pre-existing coverage gap (not introduced by the Explain fix `bbc41e9`; the AuditLog copy had the same gap). TW is the core market, so TW phone numbers are real identifiers. **Fix:** extended the SHARED `TAIWAN_PHONE_PATTERN` (was `\b09\d{8}\b`, contiguous-only) to cover dashed/spaced/+886 forms — patches BOTH `detect()`/`_check_phi` (input gate) and `sanitize_for_log` (storage mask) in one edit; separators limited to `-`/space (not `/`) so dates/lab values aren't false-positived. Unit test `tests/test_phi_taiwan_phone.py` (7 formats mask+block + clinical-content negatives). No schema/retention change.
