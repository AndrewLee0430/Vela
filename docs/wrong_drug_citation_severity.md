# Wrong-drug citation — SEVERITY SIZING + fix-discriminator validation (2026-07-28)

**Last measurement baton. Ends in a build plan-back (§6).** READ-ONLY on product code throughout.

## Decisions applied (not re-litigated)

- **openFDA fallback [P2] = CLOSED, a DECLINE not a gap.** Measured reason: Research already fans out
  to openFDA on every query (`api/rag/retriever.py:185`), and openFDA was **cited 0/18** on exactly the
  queries a fallback would serve. **The binding constraint is RANKING, not availability.** A path that
  cannot change an outcome is not worth building.
- **Wrong-drug citation is the active line**, and it is the **same defect** as pair-aware surface 3.
  Prevalence has moved from *4/8 runs on one query* to **5/6 queries** — re-filed as a **general
  defect, not an edge case**.

---

## 1. ⛔ TASK 1 — SEVERITY: it is BOTH classes, and the worse one is CONFIRMED

Six single-drug queries, full answer text captured alongside the pool and the off-target section text.
Adjudicated per query with both sides quoted. **Verdict: 3 of 6 are live medical misinformation
(class a); 1 is citation-integrity only (class b); 2 are clean.**

### 🔴 (a) aspirin — CONFIRMED MISINFORMATION

Pool: `[1] fda-aspirin-safety` (local) · `[2] ACECLOFENAC #34070-3` (**off-target**).

> **Answer:** "Aspirin is contraindicated in patients with a known allergy to aspirin or related drugs,
> those with asthma …, and patients with active peptic ulcer disease**[2]**"
> … "Allergy to aspirin or other related drugs (such as **diclofenac** or other NSAIDs)**[2]**"

> **ACECLOFENAC label [2]:** "Patients with allergy to these drugs or other analogues **(diclofenac)**.
> Patients with asthma. … Patients with active peptic ulcer."

The answer **restates aceclofenac's contraindication list as aspirin's**, citing it to `[2]`. The
tell is *"diclofenac"* — it appears in the answer only because it is in the **aceclofenac** label.
The claims are roughly true of aspirin as NSAID class effects, which is exactly what makes this
dangerous: it reads as correct and is sourced from the wrong drug.

### 🔴 (a) omeprazole — CONFIRMED MISINFORMATION (cleanest instance)

Pool: `[1] fda-omeprazole-safety` · `[2] PANTOPRAZOLE #34070-3` · `[3] PANTOPRAZOLE #43685-7` (both off-target).

> **Answer:** "Omeprazole is contraindicated in patients with known hypersensitivity … or any
> substituted benzimidazole. It should also not be used in patients receiving rilpivirine-containing
> products**[2]**." … "The provided context **does not specify additional contraindications unique to
> omeprazole** beyond those listed above**[1][2]**."

> **PANTOPRAZOLE label [2]:** "**PROTONIX I.V.** is contraindicated in patients with known
> hypersensitivity … to the formulation or any substituted benzimidazole. … PPIs, **including PROTONIX
> I.V.**, are contraindicated in patients receiving rilpivirine-containing…"

Pantoprazole's contraindications are asserted as omeprazole's **and** the answer explicitly claims
that list is complete for omeprazole. (Both facts are genuine PPI class effects — again, plausible and
wrongly sourced.)

### 🟠 (a, partially mitigated) ibuprofen

Pool: `[1] fda-ibuprofen-safety` · `[2] PIROXICAM #34066-1` · `[3] MEFENAMIC ACID #34070-3` (off-target).
The answer asserts the CABG contraindication and CV/GI boxed-warning content citing `[2][3]`, i.e.
piroxicam's and mefenamic acid's labels. **But it hedges twice** — *"(based on class warnings for
NSAIDs)"* and a closing *"some details are inferred from class effects of NSAIDs."* Honest about the
inference, still misattributed at the citation level.

### 🟡 (b) cimetidine — CITATION-INTEGRITY ONLY

Pool: `[1]–[4]` PubMed · `[5] COBIMETINIB HEMIFUMARATE #34073-7` (off-target — a melanoma kinase
inhibitor, matched on name similarity). **Every claim in the answer cites `[1]`–`[4]`. Nothing traces
to `[5]`.** The generator correctly ignored the off-target document; the defect is the misattributed
chip sitting in the citation list. This is the *good* failure mode — and proof the generator can
ignore off-target docs.

### ✅ naproxen, loperamide — clean this run

`naproxen`: no DailyMed doc in the pool at all (local FDA + 4 PubMed); answer well-grounded.
*(An earlier run cited NABUMETONE — pool churn, so this is run-dependent, not a fix.)*
`loperamide`: `fda-loperamide-safety` + `fda-loperamide-basic` (local) + PubMed — **no DailyMed safety
section, and that is the honest outcome.** ⚠️ **Worth preserving, not fixing:** the corpus has no
loperamide safety section, so returning none is correct. Note the Phase-1 "nothing retrieved" framing
was imprecise — local FDA safety docs *were* retrieved; it was DailyMed that returned nothing.

### Severity conclusion

**This is not merely a citation-chip defect.** In 3 of 6 cases the generator asserted another drug's
label content as the queried drug's. It is mitigated by the fact that the asserted content is
NSAID/PPI **class** truth in every observed instance — no case produced a claim that is *false* for the
queried drug. **So: serious citation-integrity + attribution defect with demonstrated misinformation
mechanics, but no measured instance of a clinically false statement.** I am **not** calling it a
prod hotfix on this evidence; I am calling it the top build candidate. *(Adjudication limit: n=6,
one run each. A false claim may well exist outside this sample — the mechanism plainly permits it.)*

---

## 2. TASK 2 — the discriminator VALIDATES, with one hard constraint

**Discriminator:** *does the cited section's TEXT mention a drug named in the query?*
Tested offline against **238 cited DailyMed safety sections** pooled from the pair-aware M1 runs, the
pool-size harvest, the Phase-1 single-drug runs, the severity probe, and today's §2.7 gate.

| query kind | ON-TARGET | MENTIONS-QUERY | INTRUSION |
|---|---|---|---|
| PAIR | 74 | 41 | 81 |
| SINGLE | 2 | 0 | 25 |
| GATE | 6 | 0 | 9 |

**On PAIR queries (must keep counterpart sections — the bilateral finding depends on it):**

- Naively: 115/196 kept, **81 dropped** — which would look disqualifying.
- **But 75 of those 81 drops (93%) are QUERY-SIDE IDENTIFICATION failures, not discriminator errors.**
  They come from exactly two cases — `r07_betablocker` (39) and `ace_potassium` (36) — whose queries
  name a **drug CLASS** ("beta-blockers", "ACE inhibitor") with no specific drug, so the query-drug set
  is **empty** and everything is dropped by default.
- **Restricted to PAIR rows where query drugs were actually identified: 115/121 = 95% kept.**
- Of the **6 genuine drops**, **4 are `spironolactone → POTASSIUM ACETATE`** — the *known-correct*
  rejection (the 194-char potassium-supplement contraindication that never mentions spironolactone).
  The remaining 2 (`AMILORIDE HCL` on digoxin_diuretic, `TIROFIBAN` on warfarin_nsaid) are the only
  candidate false positives in 121 rows.

**On SINGLE-drug queries (must reject off-target): 25/27 rejected.** The 2 kept are both genuinely
on-target — `IBUPROFEN LYSINE` and `ESOMEPRAZOLE SODIUM`. **Zero false negatives.**

### ⚠️ The constraint this imposes on the fix

**The discriminator is sound; its failure mode is entirely upstream — query-side drug identification.**
M5 already measured that this is the hard part (class terms exist in **no** repo asset; Tier A/B
reached 0/3 on real pair queries). Therefore:

> **The filter MUST FAIL OPEN.** When query drugs cannot be identified, it must **keep everything**.
> A fail-closed filter would strip all safety sections from every class-term query
> ("contraindications for beta-blockers", "ACE inhibitor + potassium") — 75 sections in this sample
> alone, on danger-path queries.

**CJK/mixed degradation: NOT MEASURABLE from this data (n=3).** All three CJK rows
(`metformin 腎臟…`, `warfarin 和 aspirin…`) contain **Latin** drug names, so identification succeeded.
M5's finding stands unrefuted: a CJK-only brand query (`太田胃散`) resolves *ambiguous* and would yield
an empty drug set → fail-open → unchanged behaviour. **Stated as untested, not as safe.**

---

## 3. TASK 3 — prevalence beyond the constructed set

Today's §2.7 gate (20 research cases, real golden queries, `pool_identity` captured):
**6 ON-TARGET · 0 MENTIONS-QUERY · 9 INTRUSION** among cited DailyMed safety sections.

So the defect is **not** an artifact of my six purpose-built queries — it appears on the standard
research golden set too, at a comparable rate. **Caveat:** the gate is N=1 per case and many of its
cases are single-drug or class-level, where "intrusion" is expected to be higher; and the gate cases
still all PASSED the judge, i.e. **the rubric does not currently detect this**.

---

## 4. TASK 4 — mechanism link: partly, not wholly

**Do intrusions concentrate on the 128/1038 (12.3%) no-safety moieties?**
Of 115 INTRUSION rows, **26 (23%)** have a query drug in that no-safety set.

- **On SINGLE-drug queries the link is essentially total** — every rejected case (aspirin, ibuprofen,
  naproxen, cimetidine, omeprazole) is a drug whose moiety lacks a safety section. Retrieval returns a
  semantic neighbour **precisely because there is nothing on-target to return.**
- **On PAIR/class queries it is not the driver** — those intrusions are dominated by the class-term
  identification failure, not by corpus gaps.

**So: for the single-drug half, corpus-coverage [P2] and this defect are two ends of ONE problem.**
**Which end is cheaper?** **This end.** Filling corpus coverage means re-running the DailyMed build
with better resolution (the 705-label drop) and hoping upstream labels exist — unbounded, and it
cannot fix class-query intrusions at all. The citation-integrity guard is **additive, local,
testable offline, and covers both halves.** Fix the citation end; treat coverage as a separate,
slower data-quality track.

---

## 5. Data + limits

- 238 sections analysed; 6 severity queries with full answers; 20 gate cases.
- **Adjudication is n=1 run per severity query.** Pool churn (mean turnover 0.423) means a different
  run can yield a different pool — `naproxen` demonstrated this by being clean here and
  NABUMETONE-cited earlier.
- The "clinically significant" and "class truth" judgements in §1 are mine and quoted so they can be
  disputed.
- **Server note:** `:8000` was held by a stale listener (`Errno 10048`) — the exact scenario the
  `[ops] Pre-gate stale-server SOP` covers. Followed the SOP, then used `:8001` after the socket
  lingered. The SOP earned its keep the same week it was written.
- **My error, recorded:** the first probe run was truncated by piping to `head`, which SIGPIPE-killed
  it after 4 of 6 cases. Re-ran the missing two rather than reporting partial coverage.

---

## 6. BUILD PLAN-BACK — port Verify's non-confident-match discipline to Research

> ## 🔴 HARD DESIGN CONSTRAINT — added 2026-08-04 from the c2 Phase-1b/1c measurement. **Read before designing the filter.**
>
> ### A filter keyed on *"does this document MENTION the queried drug"* WILL PASS the worst real instance.
>
> The best-evidenced wrong-drug case in the repo is `aspirin contraindications` → **`Clanza
> (Aceclofenac) — Contraindications`**, cited **12 / 12 runs across two index configurations, zero
> variance** (c2 Phase-1c Part 1). Its text reads:
>
> > *"Patients with allergy to these drugs or other analogues (diclofenac). … Like NSAIDS,
> > **acetylsalicylic acid** and other drugs which inhibit prostagladin-synthesis may precipitate attacks
> > of asthma…"*
>
> **The aceclofenac label literally contains "acetylsalicylic acid" — and that is CORRECT drafting.**
> NSAID cross-sensitivity genuinely belongs in an aceclofenac contraindications section. The document is
> not defective; it is being *used* for the wrong purpose.
>
> **This was discovered the hard way: the c2 Phase-1b harness used a mention-based `own_drug` flag and
> false-positived on exactly this document, reporting "own drug cited 3/3" for a pool that contained no
> aspirin document at all.** A measurement instrument built on the mention heuristic failed on the first
> real case it met. **A production filter built on it would fail the same way, silently.**
>
> ### ➡️ The filter must determine WHOSE LABEL the document is, not WHOM it mentions.
>
> **This is cheap — the corpus already carries it.** Every DailyMed doc has a **`moiety`** field and a
> `setid` (`scripts/build_dailymed_label_corpus.py:297-299`); ownership is a **lookup, not an inference**.
> The c2 probes re-classified entirely on `setid → moiety` and it was exact.
>
> ⚠️ **A mention-based filter is both easier to build and wrong — which is the combination that gets
> built by default.** Recorded now because it is cheap now and expensive after such a filter exists.
>
> ### And one more constraint from the same measurement
>
> **Supplying the correct document does NOT displace the incorrect one.** On the only two c2 cases where
> the drug's own safety document entered the pool *and was cited*, the wrong drug was **still cited 3/3**
> (c2 Phase-1c §0). The pool holds ~5 slots and both fit. **So a coverage fix upstream will not remove
> the need for this filter** — which also means this item's "blocked by c2" rationale is weaker than
> recorded. Cross-ref TECH_DEBT surface 3/3 and STATE open-item #2.

**One fix shape, and it is Rule 19's own finding** (Rule 19 row #5, `docs/research_openfda_fallback_phase1.md` §2):
Verify **never attaches a specific setid on a low-confidence drug match** (`api/server.py:1013-1020`)
and fails honest instead. **Research has no drug-identity check at all.** Port the *discipline*, not
the mechanism.

### What changes — additive only

1. **New pure helper** (new module, e.g. `api/rag/citation_guard.py` — no edits to existing logic):
   `query_drug_tokens(query) -> set[str]` over the DailyMed moiety index, and
   `section_supports_query(doc, tokens) -> bool` implementing the validated discriminator
   (own-moiety match **OR** section text mentions a query drug).
2. **One call site**, after `_collapse_subchunks` and **before** the final `documents[:max_results]`
   cut (`api/rag/retriever.py:279-282`): demote — **do not delete** — whitelisted DailyMed *safety*
   sections that fail the check.
3. **FAIL OPEN, mandatory:** if `query_drug_tokens()` returns empty → **no filtering at all**. This is
   the §2 constraint and is the single most important line in the change.
4. **Demote, not drop:** move failing sections to the end of the ordering rather than removing them,
   so a query whose entire pool fails still returns documents. Nothing is silently deleted.

### What happens when nothing on-target exists

**Do not invent a new pattern — reuse v190.** Research already has the no-retrieval honesty path
(`isFallback`, the 「未找到相關文獻／基於一般醫學知識」 banner) which the locale-hint panel also keys off.
If, after demotion, no label-level source supports the queried drug, the answer should degrade to the
**existing** honest state rather than a new "no label-level source" string. Consistency with v190 is
the requirement; a new message is a new thing to translate, gate and maintain.

### Gate list

- **§2.7 Research 20/20** — and per the carried-forward note, report **`run_complete`, `gate_valid`
  and the exit code explicitly**, not just the pass count. *(The fail-loud guard has still never been
  exercised on a real gate; this build is its first.)*
- **Section-aware danger-path re-gate** — 0 hard / 0 recheck.
- **Canary set** — metformin-MoA, statin-MoA, GLP-1, statin-efficacy, SGLT2-CV must stay 0/8.
- **Guard test with a NEGATIVE CONTROL** — inject an off-target safety section into a single-drug
  query's pool; the guard **must FAIL** without the fix and pass with it. A guard that has never
  failed on a real instance is not evidence (the standard applied to the b1 anti-leak guard).
- **Bilateral regression gate (the real risk, see below).**

### ⚠️ The risk: over-filtering breaks the bilateral pair case — and how the gate proves it did not

The bilateral finding is **load-bearing**: it is why pair-aware retrieval was refuted, and it depends
on counterpart-drug sections being **kept**. An over-eager filter would silently undo it.

**Proof obligation, stated as a pass/fail bar:** re-run the 10 pair-aware M1 queries at **N=8** with
the guard ON, and require **ON-TARGET + MENTIONS-QUERY retention ≥ the measured 95% baseline** on rows
where query drugs are identified, with the **class-term cases (`r07_betablocker`, `ace_potassium`)
showing ZERO sections removed** — they are the fail-open canary. Any drop there means fail-open is
broken, and the build does not ship.

**Not scoped here (deliberately):** the class-term identification gap. Fail-open makes it harmless;
closing it would need the drug-class asset M5 showed does not exist, and that is its own baton.
