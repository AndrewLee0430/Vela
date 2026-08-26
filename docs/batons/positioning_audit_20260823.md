# RECOVERED RECORD — the 2026-08-23 BACKLOG positioning audit + the three founder rulings of 2026-08-26

**What this file is.** The BACKLOG positioning audit was performed **2026-08-23, read-only, in a founder conversation, and was never committed** — the positioning-ruling car's Phase 0 (2026-08-26, earlier session) searched the repo, the working tree, all branches, the stash, and past session scratchpads, found no artifact, and stopped per its stop condition. The audit content was then **recovered from the founder's 2026-08-23 conversation record and supplied 2026-08-26**; this file carries it into the repo and records the three founder rulings that resolve it. Filed at HEAD `a356fb5a1c83c0df78f3b573aa4252fabffefb71`.

**Provenance marks used throughout** (Rule 25 — derived vs cited stated in every case, including matches):

- ✅ **RE-DERIVED AT HEAD** — the figure was re-measured against the repo at `a356fb5` on 2026-08-26; the command or anchor is named.
- 🗣️ **per 2026-08-23 audit, not re-derivable** — a conversation-only observation (the auditor's classification or a window that no longer exists); recorded as the audit's claim, not as a repo measurement.

---

## §1 Audit findings

### 1.1 Three batches of consultant/advisor input exist in-system, all prioritized

Audit-cited priority census: **P0×3 / P1×8 / P2×16 / P3×5** (sum 32). ✅ **RE-DERIVED AT HEAD — EXACT MATCH: P0=3 / P1=8 / P2=16 / P3=5.** Unit: P-tags carried in `### ` headings of BACKLOG.md (`grep "^### " BACKLOG.md`, per-heading tag inspection). Two prose mentions inside headings are excluded from the count, correctly: the pool-budget heading's cross-reference *"from the recall-miss [P1] probe"* (the entry itself is [P2]) and the ruled-out LAYER 2 heading's historical *"was: P3 — GATED"*. A naive `grep -c` that counts those reads 9/6 for P1/P3 and is wrong.

**① 2026-05-04 advisor discussion** → the BACKLOG `## Phase 1B` / `## Phase 1C` sections. ✅ **RE-DERIVED AT HEAD: six entries cite commit `394545e` to §-precision** — derived detail: **7 §-precision citations across exactly 6 entries** (the WHO ICD-11 entry cites twice), plus one section-level citation in the Phase 1B preamble:

| entry (heading anchor) | citation |
|---|---|
| `### [OTHER] [P2 — HOST B of 2, …] §2.7 post-pass over the pool_identity capture` | `394545e § 5.2` |
| `### [OTHER] [P0] 在地差異提示 Tier 1 (TW/JP/KR/SG/MY/TH)` | `394545e § 5.3` (via ADR 004) |
| `### [OTHER] [P1] Anonymous Trial Flow polish` | `394545e § 5.4` |
| `### [OTHER] [P1] 在地差異提示 Tier 1 expansion (VN/PH/ID/HK/SA/AE)` | `394545e § 6.2` |
| `### [OTHER] [P1] 跨語言橋接面板 MVP` | `394545e § 6.3` |
| `### [P1] WHO ICD-11 API integration` | `394545e § 6.1` **and** `§ 10.1` |
| *(section preamble, not an entry)* `## Phase 1B (post Phase 0 Retrospective) — per advisor discussion + ADR 003+004` | "advisor discussion 2026-05-04 (preserved in git commit 394545e)" |

**② 2026-08-18/19 consultant evaluation session** → ✅ **RE-DERIVED AT HEAD — every named artifact exists:**

- The **<1% wrong-attribution criterion**, verbatim in both 主線-A candidate entries: *"Consultant pass bar for the line: wrong-attribution <1% over ~100 high-risk drug-name queries."*
- **CONSULTANT-MVP ADDENDUM 2026-08-19** — present inside the `### [P2 — NEW 2026-08-03, GATED] LAYER 3: Calibration UI` entry (*"filed here, not as a new stub — dedup: this entry already owns the direction"*).
- **STUBS** — ⚠️ derived differs from the recovered phrasing "4 Korea MFDS stubs": the `### STUBS — scope on pickup` section holds **4 STUB entries of which exactly ONE is Korea MFDS** (Korea MFDS DUR + 허가정보 · cross-country approval-status TW/KR/HK/SG · Spain CIMA · pricing A/B flag). Count right, attribution over-narrow.
- **EU-vs-US label probe** — `### [P3 · measurement, half-day, offline, founder-ratified 2026-08-19] EU SmPC probe`, with its pre-registered decision rule.
- **REJECTED DIRECTIONS entry** — `### [REJECTED DIRECTIONS · recorded 2026-08-19] Generative UI (Layers 1+2) and Japan data ingest — ruled OUT`.
- STATE carries **"FOUNDER'S INTEGRATED SEQUENCING (2026-08-19, from the consultant-evaluation session — a dated note, not a re-write of the table below)"** verbatim.

**③ Medical advisor review** → rejected direct B2C, drove the B2B pivot. ✅ **RE-DERIVED AT HEAD: recorded in STATE, NOT in BACKLOG.** STATE holds it at two sites: *"**Medical-advisor review:** REJECTED direct B2C public launch in the current state — the 'reverses a counterintuitive finding *and* cites a real source' failure is clinically + legally unacceptable (TW 醫師法 §28 密醫罪, FDA device exposure)"* and *"🟠 B2C public launch gated (2026-06-15 …) … UPDATE 2026-06-19 — … route DECIDED = B2B-interim; B2C is a SaMD-gated terminal."* BACKLOG: `grep -ci "direct B2C\|B2B pivot" BACKLOG.md` = **0** (BACKLOG's only B2B-interim mentions are the [LAUNCH] class-definition wording in its nav table).

### 1.2 The scrubbed source document

✅ **ALL RE-DERIVED AT HEAD, every figure matching the audit:**

- `394545e` — 2026-05-05 **13:38:27** +0800, `docs: archive Roadmap Discussion v0.4 as reference for ADR 003+004` — **adds** `docs/roadmap-discussion-v0.4.md`.
- `52848ef` — 2026-05-05 **18:14:03** +0800, `docs(cleanup): remove v0.4 archive + scrub references` — **deletes it the SAME DAY**, 4h36m later.
- `git show 394545e:docs/roadmap-discussion-v0.4.md | wc -l` = **894** — exactly the audit's figure.
- The six entries' references survive the scrub **because they cite the COMMIT, not the path** — the document is reachable only via `git show`, and every §-number in §1.1's table points into a file that exists in no checkout.

### 1.3 Execution reality (deploy-car provenance)

🗣️ **per 2026-08-23 audit, not re-derived:** of the last 4 deploy cars at audit time, **only fly 238 was BACKLOG-sourced**; shipped commits with a SHA recorded in BACKLOG = **1**.

⚠️ **DENOMINATOR DISAGREEMENT, recorded per Rule 25 — the discrepancy is the fact:** the 2026-08-23 audit says **8 commits**; the 2026-08-24 baton says **9**. Both figures are conversation-sourced; neither is re-derived here, because re-derivation requires re-constituting the audit-time window ("the last 4 deploy cars" as of 2026-08-23) and re-classifying each car's work source — not cheap, and doing it at HEAD would produce a third figure for a different window, not adjudicate these two. **Recorded unresolved.**

### 1.4 The auditor's verdict (characterization, quoted as the audit's verdict)

> BACKLOG is an archive of external strategy, not a task list; a recording surface that has largely stopped recording; priority labels are decorative in practice.

- *"14 of 43 entries were not open work"* — 🗣️ the **14** is the auditor's classification, not re-derivable. The **43** denominator ✅ **CONFIRMED independently at HEAD:** BACKLOG's committed 2026-08-24 nav-recount comment records *"(43 in the file before this car's entry, 44 after)"*.
- The `top_k` sweep entry — audit cited it as ":838"; ⚠️ **that line reference has already rotted** (the heading now sits elsewhere; cite it by heading: `### [OTHER] [P2] Research pool budget — top_k=5 cuts safety sections sitting at composite rank 6 …`). ✅ **RE-DERIVED AT HEAD, the audit's characterization is exact:**
  - **Rewritten 4× in four weeks** — dated in-entry revisions: 2026-07-27 (evidence) → 2026-07-29 (note, later ⛔ OBSOLETE) → 2026-08-04 (supersede + "WHAT THE SWEEP WOULD ACTUALLY MEASURE TODAY (rewritten 2026-08-04)") → 2026-08-06 ("THERE ARE TWO `5`s") → 2026-08-23 (🚩 founder flag).
  - **Its own evidence marked stale by its own text:** *"The 11-at-rank-5 figure is a **pre-c1 measurement and should not be quoted as current**."*
  - **The measurement never run, per its own 2026-08-23 flag:** *"the 5-vs-6-vs-7 sweep it scopes has still never run."*

### 1.5 HISTORICAL, since repaired: the nav-table drift

At audit time (2026-08-23) the BACKLOG nav total was **handwritten and wrong by 7 — said 36, actual 43**. ✅ **CONFIRMED against committed evidence:** the 2026-08-24 recount comment in BACKLOG's nav block records *"BEFORE … = 36. AFTER … = 44 … Pre-existing drift of SEVEN"*. **Repaired 2026-08-24** (recounted from the file, commands recorded in the comment). At HEAD: `grep -c "^### " BACKLOG.md` = **44**, equal to the nav table's cited 44 — re-derived by this car on 2026-08-26. Recorded with both dates: **broken 2026-08-23, repaired 2026-08-24, holding at HEAD 2026-08-26.**

### 1.6 The audit's own framing, preserved

CLAUDE.md already names STATE as the execution order (*"`STATE.md` is the authoritative 'what to do now' — not PRD, not BACKLOG"*), so the gap the audit measured is **not per-se a defect — it is a positioning question**: is BACKLOG a task list that has failed, or an archive that has never been labeled as one? That question is what **Ruling A** answers.

---

## §2 主線 A #1 — pointers only (this evidence is ALREADY committed; nothing is copied here)

Unlike §1, the 主線 A #1 evidence base needs no recovery. It lives at:

- **TECH_DEBT** — the entry headed `[P1 · retrieval measurement / premise integrity — five read-only recons + TWO founder-authorized live runs, 2026-08-22/23; FINDINGS ONLY, nothing re-scoped] 🔴 主線 A #1 … was scoped on a premise the measurements now contradict: THE SEAT TARGETS A STAGE WHERE DOCUMENTS DO NOT DIE`.
- **STATE** — the Recently Shipped entry dated **2026-08-23**, `主線 A #1 RECON FINDINGS FILED — the measurements contradict premises the line was scoped on. EVIDENCE RECORDED; NO RULING RE-SCOPED.`
- **BACKLOG** — the reserved-seat entry's appended 2026-08-23 blockquote: *"THE OFFLINE MEASUREMENT THIS ENTRY REQUIRED HAS NOW RUN, AND IT CONTRADICTS THE PREMISE. RULING UNCHANGED; EVIDENCE APPENDED … the founder re-sequences."*

**The conversation-context line, anchored to its committed measurement:** the measured loss lives in the **LLM relevance filter — 60.7% removal on the real golden set** (13.85 → 5.32 docs, median 62.5%; synthetic 58.4%, agreeing within 2.3 points) — **not the `min_score` floor** (17 of 20 queries enter with ≥5 docs; the sub-5 final size is created downstream of retrieval) **and not the final slice** (production-log ladder: filter **−8.28** vs final slice **−1.18**, ~7×; rerank/composite/collapse **0.00**). Committed in the TECH_DEBT entry above (findings **①** and **⑧**) and STATE's 2026-08-23 entry; raw artifacts at [`tests/probes/retrieval_attrition/`](../../tests/probes/retrieval_attrition/) (committed 2026-08-24).

**The successor question's committed home:** the same probe directory's README states the limitation that defines it — *"`retriever.py:531` logs `N -> M`; it does **not** log *which* documents were dropped. **Nothing here says whether the filter dropped the *right* 60%**"* — and the standing repair candidate is the TECH_DEBT entry headed `[P2 · relevance-filter quality — surfaced by the filter-exemption probe 2026-07-20 …] _filter_by_relevance (gpt-4.1-mini) keeps OFF-TOPIC docs while dropping the query drug's own safety section — MASKED (not fixed) …`.

---

## §3 THE THREE RULINGS (founder, 2026-08-26) — verbatim

Recorded verbatim from the founder's 2026-08-26 ruling text. The bracketed `[VERIFY …]` clauses were instructions to the recording car, not ruling content; each is resolved immediately below the ruling that carries it.

> **RULING A — BACKLOG positioning: RATIFIED AS A DECISION ARCHIVE, not an execution
> queue. STATE.md remains the sole execution order (consistent with CLAUDE.md's
> existing text). Consequences authorized by this ruling:**
>   **(a) the doc-map label for BACKLOG changes from "Open future tasks"-style wording
>       to archive wording [VERIFY the current label text in INDEX.md / CLAUDE.md
>       doc map and quote before/after];**
>   **(b) the discharge convention is written down where the doc map describes
>       BACKLOG: entries are discharged at car closeout by write-back from STATE;**
>   **(c) any per-entry estimated-time promise is downgraded to optional
>       [VERIFY where that promise lives — the audit says a Step 0 text; quote it].**

*Resolution of A(a)'s [VERIFY] — the before-texts at HEAD, verbatim:*
- CLAUDE.md Project Doc Map row: `| Open future tasks | BACKLOG.md |`
- docs/INDEX.md pointer: `- **What's the open backlog?** → ../BACKLOG.md`

*Resolution of A(c)'s [VERIFY] — the promise lives in CLAUDE.md "Workflow for a new task", Step 0, item 2, verbatim:*

> 2. Find that task in `BACKLOG.md` → read short description + phase + estimated time

*(The after-texts are what the Phase-2 commit of this car applies; see that commit's diff. CLAUDE.md's Source-of-truth priority lines — "STATE.md is the authoritative 'what to do now'" / "BACKLOG.md organizes work by phase" — were checked and already agree with Ruling A; untouched. ⚠️ Flagged, not changed, founder's call: BACKLOG.md's own H1 reads "# BACKLOG.md — Vela Open Future Work" — same-style wording, but it is BACKLOG's self-label, not the doc map, so Ruling A(a) as written does not reach it.)*

> **RULING B — 主線 A #1 (reserved-seat mechanism): PARKED, premise-refuted, per the
> entry's own "founder re-sequences" clause. The successor line is the existing
> open question "which 60% does the LLM relevance filter drop" — promote that item
> from blocked-on-this-ruling to schedulable. Park is mark-never-delete: annotate
> the BACKLOG entry and the TECH_DEBT entry with the dated ruling; nothing is
> rewritten or removed.**

*Location note for the successor item (derived; no entry is literally titled "which 60%"): the question is committed as the limitation row of `tests/probes/retrieval_attrition/README.md` ("whether the filter dropped the *right* 60%") and its standing schedulable carrier is the TECH_DEBT `_filter_by_relevance` [P2] entry — that entry received the promotion annotation.*

> **RULING C — landing-copy dependency: landing copy proceeds under EXISTING rulings
> (route = B2B-interim, ruled 2026-06; current TA per ADR 004). The A1
> Taiwan-localization pivot is NOT ruled here and is NOT a landing blocker; if A1
> is later ruled, the copy rework is A1's cost. Record this so the landing car's
> prompt can cite it as its authority.**

*Authority anchors, verified at HEAD: the B2B-interim route decision is STATE's "UPDATE 2026-06-19 — … route DECIDED = B2B-interim; B2C is a SaMD-gated terminal"; ADR 004 (`docs/decisions/004-prescription-parser-deferral.md`, 2026-05-04) carries the "Vela 護城河重新定位" 4-wedge positioning (Your Language · Local Awareness · Cross-Language Bridging · Privacy-First & Anonymous). **The landing-copy car cites this file, §3 Ruling C, as its authority to proceed.***

---

## §4 Decision rationale (recorded with the rulings, one paragraph each)

**Ruling A.** Evidence strength: the strongest of the three — every load-bearing figure was either re-derived at HEAD with an exact match (P-census, the six §-precision citations, the same-day add/delete pair, 894 lines) or confirmed against committed recount comments (the 36→43 drift, the 43→44 total); only the auditor's classifications (the "14 of 43", the deploy-car provenance) rest on the conversation record. The ruling ratifies what the repo already practices — CLAUDE.md has named STATE the sole execution order since before the audit — so its cost is a label change and its benefit is that the doc map stops promising a queue that six months of execution reality says BACKLOG is not. Deliberately not decided: which entries to discharge, any re-prioritization, and BACKLOG's own H1 wording (flagged above).

**Ruling B.** Evidence strength: strong on "premise refuted" — the refuting measurements are committed, ran on the real golden set (75 live `retrieve()` calls), and the one finding that survived synthetic-to-real contact (filter attrition, 58.4% vs 60.7%) is precisely the one the successor line is built on. Weaker, and known to be weaker, on the successor's payoff: the attrition evidence is counts-only, and whether the filter drops the *right* 60% is exactly the open question being promoted, not a result in hand. The park honors the entry's own sequencing clause rather than overriding it. Deliberately not decided: the top_k entry's re-rate (its 🚩 flag stands), the P1-vs-P2 seat question (moot while parked, recorded not answered), and any resolver work.

**Ruling C.** Evidence strength: rests entirely on rulings already committed and dated — the B2B-interim route (STATE, 2026-06-19) and the ADR 004 positioning — so it creates no new decision, it scopes an existing one: landing copy binds to the rulings that exist today, and a hypothetical future A1 pivot pays for its own copy rework. This is what unblocks the landing-copy car under Rule 16 (every landing string ×16 locales — the reason copy could not be written before positioning was ruled). Deliberately not decided: A1 itself, in either direction.

---

*Filed 2026-08-26 by the positioning-ruling car (Phase 1). Phase 2 of the same car applied Rulings A and B to the live docs (CLAUDE.md doc map · docs/INDEX.md · the BACKLOG 主線 A #1 entry · the TECH_DEBT premise-integrity and `_filter_by_relevance` entries) — see that commit's diff; nav counts re-derived there per house convention.*
