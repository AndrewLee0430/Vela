<!-- ─────────────────────────────────────────────────────────────────────────
ADDENDUM — ADDED 2026-08-24, AFTER THE FACT. NOT PART OF THE ORIGINAL REPORT.
The original text begins below the horizontal rule and is PRESERVED UNALTERED.
───────────────────────────────────────────────────────────────────────── -->

> ## ⚠️ LATER ADDENDUM — read before the body
>
> **This report's Part D "Tier 3" finding is SUPERSEDED.** It states that the two
> production sites — `api/services/direction_checker.py:86` and
> `api/services/retrieval_refusal.py:76` — run the `(\d{5,})` regex **without** a
> `source_type` guard, and sizes them as a possible product defect. **That is false.**
> Both sites are guarded, at `direction_checker.py:83-84` and
> `retrieval_refusal.py:73-74` — a `!= SourceType.PUBMED → continue` on the line pair
> immediately preceding the regex.
>
> **Superseded by:** [`recon_20260824_tier3_reachability.md`](recon_20260824_tier3_reachability.md),
> written the same day, which traces the path in full and returns **(b) NOT REACHABLE**.
>
> **🔑 WHY THIS FILE IS KEPT UNCHANGED.** The error is the artifact. It is a worked
> example of a **confident false negative produced by a grep that hard-coded the
> guard's shape**: the search matched the regex line and looked for `SourceType.PUBMED`
> on the SAME line — the spelling used at `scripts/question_neutralization_eval.py:59-60`
> — so the preceding-line `continue` form was invisible to it. The report then stated
> the absence as a finding rather than as a limit of the search. It also contradicted
> the repo's own ledger, which had already recorded the guard twice
> (`TECH_DEBT.md:809`, `TECH_DEBT.md:1079`, both citing `retrieval_refusal.py:73-74`).
>
> **Correcting the body would destroy the record.** Nothing below has been edited,
> condensed, or re-worded. Read Part D as the error it was, not as guidance.
>
> *(Everything outside Part D Tier 3 — the baton-file absence, B1-B6, and the entire
> §2.7 Step 8 archaeology in Part C — is untouched by the supersession and stands.)*

---

All recon complete. No edits, commits, or pushes were made. One blocker: the baton file does not exist.

---

# A. Baton checker — COULD NOT RUN

```
$ PYTHONIOENCODING=utf-8 python tests/probes/baton_check/check_baton.py docs/batons/baton_20260824_gate.md
no such file: docs\batons\baton_20260824_gate.md    (exit 2)
```

**`docs/batons/` does not exist**, and neither does the file — not in the working tree, not untracked, and not in git history:

- `find . -iname "*baton*"` → only `docs/baton_a2_indications_loinc_fix.md`, `docs/baton_a_verify_undergrounding_fix.md`, and the checker's own `tests/probes/baton_check/` (script, README, `suppressions.json`, and fixture `baton_20260821_ratification.md`).
- `find . -iname "*20260824*"` → **nothing**.
- `git log --all -- 'docs/batons/*'` → **empty**. The path has never existed.
- `git status --short` → only `?? .superpowers/`.

The checker itself is present and works — it exited 2 on a missing path, which is correct behaviour, not a tool failure. **Every claim I could not cross-check below is one I could not read from the baton.** Where a section asks me to compare against a baton assertion, I report the repo's value and say the comparison is unverifiable.

---

# B. Load-bearing facts

### B1–B3 ✅ all three confirmed exactly as stated

| Check | Result |
|---|---|
| `git rev-parse HEAD` | `7a24c70233d51d14692f957ad45b2c8a099398fb` ✅ |
| `git ls-remote origin HEAD` | `7a24c70233d51d14692f957ad45b2c8a099398fb` ✅ **local == remote** |
| `git diff --stat 838d0e6^..HEAD -- api/ components/ pages/ scripts/` | **EMPTY** ✅ zero product-code lines across the whole car |

`git log --oneline -6` — order confirmed, oldest→newest `838d0e6 → 1033f74 → e8296f0 → c75ace8 → 7a24c70`, with `03e178f` as the parent:

```
7a24c70 docs(techdebt): split the half-closed §2.7 entry in two…
c75ace8 docs(state): §2.7 gate car closeout…
e8296f0 test(golden): cover rank B's two defensive sub-legs…
1033f74 test(golden): subset-score § 2.7 so the 70% gate stays reachable…
838d0e6 test(golden): make the ratified 18/2/0 floor executable…
03e178f docs(debt): WRONG-SUPPORT — a new failure axis no gate measures…
```

### B4 ✅ BARE pytest is clean — the `--ignore=tests/results` claim is FALSE

```
$ python -m pytest -q
........................................................................ [ 19%]
............................ssssssssssssss..ssssssssssssss.............. [ 38%]
........................................................................ [ 58%]
........................................................................ [ 77%]
........................................................................ [ 97%]
..........                                                               [100%]
342 passed, 28 skipped in 120.86s (0:02:00)
[exited with code 0]
```

- **342 passed, 28 skipped, exit 0.**
- **Collection is clean** — no `ERROR` section, no collection errors, no `errors during collection` line. 370 items collected, all accounted for.
- There is **no pytest config at all**: no `pytest.ini`, `setup.cfg`, `pyproject.toml`, `tox.ini`, or root `conftest.py`. So the clean run is *not* the result of a hidden `norecursedirs`/`collect_ignore` — the bare invocation genuinely walks the tree and `tests/results/` causes no problem.

**This settles the open TECH_DEBT claim: the baseline does NOT need `--ignore=tests/results`.** It also corroborates `STATE.md:261`'s "pytest … → 342 (`e8296f0`), 28 skipped throughout" — 342/28 is exactly what HEAD produces.

### B5 ⚠️ TECH_DEBT total is **147**, and the per-class breakdown sums to **147** — so a 146 is wrong

```
$ grep -c "^- \[" TECH_DEBT.md
147
$ grep -o "^- \[[A-Z-]*\]" TECH_DEBT.md | sort | uniq -c | sort -rn
     79 - [OTHER]
     43 - [DONE]
     17 - [HONESTY]
      8 - [COMPLIANCE]
```

Classes actually present as entry tags: **[OTHER], [DONE], [HONESTY], [COMPLIANCE]** — four, not the list in your prompt. **79 + 43 + 17 + 8 = 147**, exactly equal to the total. No entry carries an unlisted class and none is double-counted.

There is a fifth declared class, **[LAUNCH] = 0**, which exists in the nav legend but tags no entry — that is why the file's own comment blocks write "the five class counts". The nav table at `TECH_DEBT.md:12-17` is self-consistent with the grep: `COMPLIANCE 8 · HONESTY 17 · DONE 43 · OTHER 79 · LAUNCH 0`.

**Which is wrong: the baton's 146.** The repo is 147 and internally consistent two independent ways. I can name the likely stale digit but not confirm it: `TECH_DEBT.md:50` carries a pre-split comment reading *"Counts RE-DERIVED … 0 + 8 + 17 + **42** + 79 = **146**"*, and lines 25–29 record `[DONE] 42 → 43 — CORRECTED, +1 from the split`. A per-class set summing to 146 is almost certainly carrying **[DONE] = 42** (pre-split) instead of 43. **Unverifiable without the baton file.**

### B6 ✅ Confirmed — the header says FOUR, the bracket says 5

`STATE.md:250`, both halves quoted verbatim from the single line:

> **Bracket:** `✅ **PUSHED 2026-08-24 (founder-authorized, 5 commits); NO DEPLOY — prod stays at fly 239 and is unaffected, because ZERO of the five commits contains product code**`
>
> **Header:** `**🔴 THE §2.7 18/2/0 FLOOR IS EXECUTABLE — 15/2/3 EXITED 0 AND NOW EXITS 2. FOUR COMMITS, AND THE SECOND ONE FIXES A DEFECT THE FIRST ONE SHIPPED.**`

**5 is the correct number** (`838d0e6, 1033f74, e8296f0, c75ace8, 7a24c70`); the header's "FOUR" predates `7a24c70`, the docs commit that files the entry. **Not fixed**, as instructed.

---

# C. The §2.7 Step 8 authority question

## C1. PRD §2.7 has **NO enumerated steps at all**

I read `docs/PRD.md:585-763` in full. §2.7 is titled **「2.7 Explain 臨床推理強化(v1.2 新增,P1)」** and its structure is:

**目標 → v1.2 決策 → 背景 → 功能需求 (需求 1–7) → 驗收標準 (7 bullets) → 不做什麼 → 工期**

There is **no "Step 1", no "Step 8", no step enumeration anywhere in the section body.** The word "Step" appears in §2.7 exactly once — inside the status marker on the header line, which was written by a *later* doc commit:

> `**2.7 Explain 臨床推理強化(v1.2 新增,P1)** ✅ SHIPPED 2026-04-30 (Steps 1-8 + Path 1 + M06; commits cd697d1..dffd015)`

**Two further facts about the section that matter:**

1. **§2.7 is 100% about Explain.** Every one of the seven 需求 is an Explain concern: Explain system prompt, hedging, LOINC citation policy, risk tiers 🟢🟡🔴, the Explain JSON schema, i18n keys `explain.risk.*`, and the `explain_completed` PostHog payload. **There is not one Research requirement in it.**
2. **The 驗收標準 contain no numeric pass-rate threshold of any kind.** They are: ≥1 clinical correlation on a diabetes+renal case; no false-positive correlations on a normal panel; citations not LOINC-only for clinical judgment; `risk_tier` on every item; disclaimer present; a hedging check over **20 real cases**; and "add an Explain-specific evaluation prompt to `api/utils/llm_judge.py`". **"95%" appears nowhere in §2.7.** The number 20 in the code traces to the hedging bullet's 「抽 20 個真實 case」, not to a threshold.

## C2. Every "Step 8" reference in the repo — and they agree with each other

`git grep -n "Step 8"` returns 32 hits (2 are `data/dailymed/label_docs.json` false positives — SPL section numbering inside drug label text, unrelated). The substantive ones:

| File | What it says Step 8 is |
|---|---|
| `BACKLOG.md:673` | `§ 2.7 Step 7 (LLM judge) → § 2.7 Step 8 (20-case acceptance) →` |
| `BACKLOG.md:624` | "Discovered during § 2.7 Step 8 acceptance protocol (2026-04-30)" |
| `BACKLOG.md:66, 469, 665, 685` | Step 8 as the acceptance checkpoint gating §4.5/§4.6 |
| `CLAUDE.md:50` | "acceptance protocol checkpoint (e.g., § 2.7 Step 8)" |
| `STATE.md:238` | "§ 2.7 Step 8 acceptance protocol completed 2026-04-30 (commits c5b3a09, 64c72f2, fa80ff9, a52bf9f, dffd015)" |
| `docs/PRD.md:17, 134, 1757, 2500` | **execution-order only** — §4.5/§4.6 run after Step 8 passes. Never defines it. |
| `docs/decisions/002:39-40, 52-54, 160, 194, 227, 244` | "§ 2.7 Step 8 protocol, 60 lines"; Step 4 follow-ups "deferred until Step 8 data" |
| `docs/decisions/005:13, 44` | "§2.7 Step 8 acceptance baseline 是 OpenAI 跑出來的" |
| `docs/retrospectives/phase-0-2026-05.md:232, 278` | "case in production matched §2.7 Step 8 acceptance protocol output 1:1 (3 items + …)" |
| `tests/run_golden_tests.py:31, 1061, 1239, 1344, 1370, 1383` | the `EXPLAIN_THRESHOLD` block and the ExplainJudge wiring |

**They agree unanimously.** Every reference that says what Step 8 *is* says it is the **20-case Explain acceptance run using the ExplainJudge**. Not one associates Step 8 with Research. `scripts/smoke_share_phase_b.py:1` ("PRD § 4.5 PHASE B Step 8") is a different section's step numbering and is not a counterexample.

**Where the enumeration actually lived — and why the PRD lacks it.** The Steps 1–8 decomposition was in `FEATURE_AUDIT.md`, which `d79f88b` (2026-05-05) **deleted** ("replaced by codebase grep"). At `dffd015` that file read:

```
Steps 1-6 shipped 2026-04-27 (19 commits). Steps 7-8 acceptance protocol completed 2026-04-30
  cd697d1 Step 1: api/models/explain_schemas.py … RiskTier enum, ExplainItem, ClinicalCorrelation
  bfd390a Step 2A: 抽 system prompt 至 api/prompts/explain_system.md
  bcabb29 Step 2B: rewrite prompt to v2 — 臨床組合推理 / hedging / LOINC scope-limit / risk tier
  148904e Step 2C: explain_service.py → OpenAI JSON mode + explain_result SSE event
  c38b656 Step 3: LOINC scope post-processing guard
  0dba4fa Step 4B: RiskBadge.tsx + ExplainItemCard.tsx + ClinicalCorrelationCard.tsx
  1fa21f2 Step 4C: pages/explain.tsx 整合卡片
  e05102e Step 5: api/i18n/explain_strings.py — 16 語言 risk_label / disclaimer
  e63c231 Step 6: PostHog explain_completed + explain_failed
  c5b3a09 Step 7: ExplainJudge class + explain_judge.md prompt
  fa80ff9 Step 7-8 acceptance protocol: ExplainJudge integration into golden_dataset
```

**All eight steps are Explain.** No tracked file in the working tree today reproduces this list — it survives only in git history.

## C3. `EXPLAIN_THRESHOLD = 95.0` — introduced `fa80ff9`, **no ratification cited**

```
$ git log -S "EXPLAIN_THRESHOLD" --oneline --all
c75ace8 · 6ed0737 · 7e2217e · 09b8e56   (all docs commits discussing it, 2026-08)
fa80ff9 feat(explain): § 2.7 Step 7-8 — ExplainJudge integration + acceptance protocol
```

**Introducing commit: `fa80ff9`, AndrewLee0430, 2026-04-30 14:34:24 +0800.** The constant arrives as one bullet in a 24-bullet changelist:

> `- Per-category threshold check: Explain ≥ 95%`

**No ratification is cited for the number.** The commit's only decision citation — *"Plan B-Modified per user decision 2026-04-30: extend existing golden_dataset (don't duplicate as separate acceptance script)"* — governs **where the cases live**, not the threshold value. Compare `c5b3a09` the day before, which itemises four founder decisions by letter ("Judge scope: B … Scoring: X … Model: Q … Timing: ii"); `fa80ff9` has no equivalent for 95.

**And the repo's own contemporaneous verdict downgraded it.** `FEATURE_AUDIT.md:174` at `dffd015`:

> **"Acceptance verdict: § 2.7 Step 8 spec satisfied. Hard floor + per-dimension correctness is the actual PRD § 2.7 spec compliance signal; 95% numerical threshold is a useful guardrail but secondary."**

So on the day it shipped, 95.0 was recorded as **a secondary guardrail, explicitly not the spec-compliance signal** — and the doc saying so was deleted five days later.

## C4. `git log -S "95.0" -- tests/run_golden_tests.py`

```
fa80ff9 feat(explain): § 2.7 Step 7-8 — ExplainJudge integration + acceptance protocol
```

**Exactly one commit.** The value has never been changed, re-derived, or re-ratified since 2026-04-30.

## C5. What the five-commit protocol actually consisted of — **Explain only**

| Commit | Date | Content |
|---|---|---|
| `c5b3a09` | 04-29 22:15 | **Step 7 — ExplainJudge** class + `explain_judge.md`. 7 dimensions, gpt-4.1, acceptance-only. Records that Path 1 permanently invalidated PRD §2.7 acceptance criterion 3 ("citation 不只有 LOINC"), replaced by `citation_source_types_valid` + `no_fabricated_citations`. |
| `64c72f2` | 04-30 10:34 | **Test infra** — TEST_MODE rate-limit bypass. Surfaced because "golden test runner makes 22+ **explain** requests + 22 ExplainJudge calls". `CLAUDE.md`, `api/server.py`. |
| `fa80ff9` | 04-30 14:34 | **Steps 7-8 integration.** `run_golden_tests.py` +275, `golden_dataset.json` +266: 15 existing **E13–E28** enriched with `use_explain_judge` + `expected_explain_judge`, 5 new **E29–E33**. Introduces `EXPLAIN_THRESHOLD` and `HARD_FLOOR_DIMENSIONS`. |
| `a52bf9f` | 04-30 14:37 | **Bug M06** — `ExplainItem.value=null` coercion, found on a Japanese clinical note during the acceptance run. |
| `dffd015` | 04-30 14:43 | **Closeout docs** — `FEATURE_AUDIT.md` §2.7 🔧 → ✅, `CLAUDE.md`, `TODO.md`. |

**Answer: Explain cases only. Zero Research cases.** Every case ID touched is `E*`. `git grep` finds no `R*` case in any of the five diffs, and the only non-test product file touched in the whole protocol is `api/server.py` for the TEST_MODE bypass.

Corroborating measurement at HEAD — `tests/golden_dataset.json`:

```
explain cases: 20     (E13–E24, E26–E33; E25 absent)
use_explain_judge: 18
```

**The Explain category is exactly 20 cases**, matching `BACKLOG.md:673`'s "**20-case** acceptance" precisely. That is not a coincidence — it is the same set.

## C6. ADRs — none govern it

`docs/decisions/` holds 001–007 + README. `git grep -n "95%\|95\.0\|EXPLAIN_THRESHOLD" -- docs/decisions/` → **zero hits.** ADR 005 mentions Step 8 twice but only as a *constraint on provider swaps* ("§2.7 Step 8 acceptance baseline 是 OpenAI 跑出來的" / "主力切換需重做 §2.7 Step 8 acceptance") — it treats the baseline as a given, never sets or approves it. **No ADR covers the threshold.**

---

## Conclusion: **(a)** — Step 8 genuinely covers Explain acceptance; only the AUTHORITY label is false

The TECH_DEBT entry at `TECH_DEBT.md:439` left this deliberately open:

> ⚠️ **NOT ESTABLISHED, and deliberately not guessed: whether PRD §2.7 Step 8 itself genuinely covers Explain acceptance.** If it does, the label's SUBJECT MATTER is right and only its AUTHORITY is false…

**It is now established, and the answer is: it does.** PRD §2.7 is the **Explain** section end to end; every historical definition of Step 8 in this repo calls it the 20-case Explain acceptance run; the Explain category is exactly those 20 cases; all five protocol commits are Explain. The block's `# § 2.7 Step 8 — Acceptance Gate` comment is **scoping the right subject**. What is false is the word **`Gate`** and the printed `✅ § 2.7 Step 8 acceptance gate cleared` — `acceptance_pass` never reaches an exit code or the result JSON, exactly as the entry documents. That defect stands untouched; only its *diagnosis* changes.

**Two qualifications, neither of which changes the (a) verdict — both are founder calls, flagged not decided:**

**1. "PRD §2.7 **Step 8**" is a citation to a construct the PRD never contained.** §2.7 has no enumerated steps. The step decomposition lived in `FEATURE_AUDIT.md`, deleted `d79f88b` 2026-05-05. So the label is accurate about *subject* and *substance*, but its **"PRD" provenance is unsupported** — the PRD only ever referenced "Step 8" in execution-order notes that presuppose a decomposition defined elsewhere. Anyone told to "read PRD §2.7 Step 8 before renaming" (as the debt entry instructs) will find nothing, which is why I am stating it explicitly rather than leaving it as a dead end.

**2. 🔴 The mislabelling runs the *opposite* direction from what the debt entry assumes — this is the finding I'd most want your eyes on.** The entry's premise is that the Explain block sits under a §2.7 heading while "the §2.7 set is the 20 `R*` cases". But **PRD §2.7 contains no Research content whatsoever**. The `SECTION_27_CASE_IDS = {R01…R20}` Research floor rests not on the PRD but on a founder ruling recorded in the code itself (`tests/run_golden_tests.py:82-83`):

> `# Founder ruling 2026-08-21: the § 2.7 case set IS these 20. The 35-case research CATEGORY … is NOT the § 2.7 set.`

Measured against the PRD, **the Explain block's "§ 2.7" is the one with spec backing, and the new Research floor's "§ 2.7" is the one without it.** The two case sets being disjoint is confirmed and unchanged; what flips is which side inherited the name legitimately. This does not make the new floor wrong — a founder ruling can define a gate — but it does mean the rename decision the debt entry defers to you is not "what should the Explain block be renamed to", it is **"which of these two things is entitled to the name §2.7"**. I have not touched either.

**Who approved `EXPLAIN_THRESHOLD = 95.0`: no one on record.** It is not in PRD §2.7's 驗收標準, not in any ADR, not in STATE's ratification records, and its introducing commit cites a founder decision about *dataset placement* rather than about the number. The one contemporaneous statement about it — now deleted along with `FEATURE_AUDIT.md` — called it "**a useful guardrail but secondary**". It has stood unchanged and un-reratified for 116 days. **The authority label is false; and unlike the subject, this half has no founder ruling behind it either.**

---

# D. Sizing the `extract_pmid` car

### D1. The extraction logic — `scripts/citation_truth_check.py:130-133`

```python
def extract_pmid(citation):
    sid = (citation.get("source_id") or "")
    m = re.search(r"(\d{5,})", sid) or re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", citation.get("url") or "")
    return m.group(1) if m else None
```

**There is no source-type check anywhere in it.** It takes the **first run of ≥5 consecutive digits found anywhere in `source_id`**, regardless of what kind of source that is, and returns it as a PMID. The URL fallback — the only PubMed-aware branch — is `or`-guarded and therefore **unreachable whenever `source_id` contains any 5-digit run**, which every DailyMed and TFDA id does.

DailyMed ids are `DailyMed:{setid}#{loinc}~{i}` (`api/rag/retriever.py:564`) where `setid` is a UUID; a UUID reliably contains ≥5 consecutive digits, and even failing that the LOINC segment (`#34070-3`) matches on `34070`. TFDA ids are numeric permit numbers.

### D2. Every call site — 5, all in one file, plus 1 transitive importer

```
scripts/citation_truth_check.py:130   def extract_pmid
scripts/citation_truth_check.py:151       inside claim_pairs()
scripts/citation_truth_check.py:202       --run path
scripts/citation_truth_check.py:411       (mode path)
scripts/citation_truth_check.py:515       (mode path)
scripts/citation_truth_check.py:590       (mode path)
```

**`extract_pmid` is never imported by name anywhere.** But it leaks transitively: `scripts/direction_shadow_eval.py:37` does `from scripts.citation_truth_check import judge_direction, claim_pairs, ADVERSARIAL`, and **`claim_pairs` calls `extract_pmid` internally at :151**. So `direction_shadow_eval.py` inherits the bug without naming it. `tests/question_neutralization_corpus.json:2` documents that its harness "reuses `citation_truth_check.judge_direction`" — that specific symbol does not touch `extract_pmid`.

### D3. Today's behaviour on a DailyMed / TFDA citation: **silent mis-resolution**, and a worse second-order failure

It does not error. Tracing `:202` → `:209-227`, the flow is: extract → `pubmed.fetch_details(pmids)` → judge each claim against the returned abstract. Two outcomes, both bad:

- **If the bogus digits happen to be a live PMID → silent mis-resolution.** The measured DailyMed value **84432** is a valid legacy PubMed identifier, so efetch resolves it, the script prints `N/N resolve` with **no warning**, and the direction-of-effect judge scores the drug-label claim against a **completely unrelated abstract**. `TECH_DEBT.md:322` and `STATE.md:269` both record the measurement (DailyMed → PMID `84432`; TFDA → `057803`, 2026-08-23). On R12's three DailyMed citations it fetches three unrelated abstracts and judges against those.
- **If the digits resolve to nothing → a loud but *misattributed* failure.** It prints `⚠️ MISSING: [...]`, and the surrounding code counts that toward `halluc_count` / `exist_ok` (`:230-235`). **The script would report a real, correctly-attributed DailyMed citation as a hallucinated one.** That is arguably the more damaging mode, because it is loud enough to be believed and points at the wrong culprit.

Both modes are **unbounded silence about the type confusion itself** — nothing anywhere prints "this was not a PubMed source".

### D4. The pattern is duplicated **nine times**, including **twice in production `api/`**

```
api/services/direction_checker.py:86      re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")   ← PRODUCT CODE
api/services/retrieval_refusal.py:76      re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")   ← PRODUCT CODE
scripts/citation_truth_check.py:132       (the one under review)
scripts/direction_shadow_eval.py:98
scripts/direction_shadow_eval.py:141      list comprehension
scripts/direction_shadow_eval.py:143      re-evaluates the same regex as its own guard
scripts/pathb_recall_probe.py:58
scripts/question_neutralization_eval.py:59
scripts/question_neutralization_eval.py:60
scripts/retrieval_recall_check.py:46
```

**The literal `r"(\d{5,})"` appears in 10 places across 7 files.** Two are under `api/` and ship to production.

**One important asymmetry, which I checked rather than assumed:** `scripts/question_neutralization_eval.py:59-60` **does** guard the extraction with `getattr(d, "source_type", None) == SourceType.PUBMED`. That is the correct shape and proves the guard is available. **The other nine sites, including both `api/` sites, do not have it.** Whether the two `api/` sites are actually exposed depends on what document set reaches `direction_checker` and `retrieval_refusal` at runtime — **I did not trace that, and it is the single highest-value follow-up**, because a source-type confusion in `retrieval_refusal.py` decides whether the product refuses to answer.

### D5. No test imports or exercises the script

`git grep "citation_truth_check" -- tests/` returns **two hits, neither an import**:
- `tests/probes/wrongdrug/answer_layer_pack.py:8` — a docstring comment describing it.
- `tests/question_neutralization_corpus.json:2` — prose in a `"purpose"` field.

**Zero test coverage.** Nothing in the 342-test suite would fail if `extract_pmid` were deleted outright. Consistent with `TECH_DEBT.md:322`'s classification: "a Task-A QA harness whose output has never been committed", "not a gate".

### Estimated blast radius

**Tier 1 — the named car (small, contained):** `scripts/citation_truth_check.py`, one function, four call sites plus `claim_pairs`. A source-type guard is ~3 lines, and `question_neutralization_eval.py:59` is the in-repo precedent for the exact shape. **No test will break, because no test exists** — which also means the fix ships unverified unless a test is written with it. Per Rule 17 and this repo's `computed → printed → never returned` history, a bare 3-line patch here would be the wrong shape.

**Tier 2 — silent inheritance (small, easy to miss):** `scripts/direction_shadow_eval.py` gets the bug through `claim_pairs` without mentioning `extract_pmid`, and has three more copies of the raw regex of its own. Fixing only `citation_truth_check.py` leaves it half-fixed in a way that greps clean.

**Tier 3 — the real exposure, unsized:** the two `api/` sites. `TECH_DEBT.md:322` and `STATE.md:269` both scope this defect as "not a gate, PubMed-only, flagged not fixed" — a **script-only** framing. That framing is **incomplete**: `api/services/direction_checker.py:86` and `api/services/retrieval_refusal.py:76` run the identical unguarded regex in production. Whether they are actually reachable with a DailyMed or TFDA document is **not established here** and is the question that decides whether this is a QA-harness cleanup or a product defect.

**My recommendation on sequencing** (a call, not an action): **size Tier 3 before touching Tier 1.** If the `api/` sites are reachable with non-PubMed sources, the car is a product fix with a regression guard, not a script cleanup — and the existing debt entries would need their "not a gate" scoping corrected. Nothing has been changed.
