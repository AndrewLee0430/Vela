# Pair-aware retrieval — READ-ONLY SCOPE PROBE — FINAL REPORT

**Date:** 2026-07-27 · **HEAD:** `e0a5a92` (prod = fly 213) · **Classification:** READ-ONLY probe —
**zero** `api/` / `utils/` / `components/` / prompt / flag / config changes. Deliverable is this report.

**Recommendation: (c) RE-SCOPE.** Pair-aware retrieval as specified is **refuted by its own premise**;
a real residual exists but sits on **three different, named surfaces**. Details in §9.

| Measurement | Status |
|---|---|
| M1 re-baseline on HEAD | ✅ **COMPLETE** — 120/120 runs, **0 excluded**, single contiguous window |
| M2 detector feasibility | ✅ complete (prior session, offline) |
| M3 displacement | ✅ complete |
| M4 canaries + R15 baseline | ✅ complete |
| M5 trigger staircase | ✅ complete |
| Step F corpus findings | ✅ complete |

---

## 1. Verified current pipeline (Step 0.5)

`api/rag/retriever.py` unless noted. Prod call site `api/server.py:816`, **`max_results=5`** (`:818`) → **top_k = 5**.

| Stage | Ref |
|---|---|
| `retrieve()` entry | `:130` |
| Step 1 rewrite → 3 queries | `:167` (def `:288`) |
| Step 1b **K-union (lever 1)** — DailyMed-only, `k=3` | `:174` (def `:386`); k× `_rewrite_query` in parallel `:394`; dedup-union `:397-401`; raw-query augment `:402-403`; source_filter guard `:175` |
| Step 2 fan-out — non-DailyMed keep the K=1 set | `:178-190` (local `:181`, pubmed `:183`, fda `:185`, tfda `:187`, dailymed×union `:188-190`) |
| Step 3 dedup by `source_id`, keep max relevance | `:207-213` |
| Step 4 year boost | `:218` (def `:532`) |
| Step 5 sort + candidate cut `[:max_results*4]` = `[:20]` | `:221-222` |
| **Lever 2 cut-exemption** (append-only) | `:227` (def `:65`); `_is_whitelisted_safety_section` `:51`; 4-LOINC whitelist `:44-48` |
| Step 6 relevance filter | `:234` (def `:442`) |
| Step 7 rerank (`Reranker(top_k=8)` `:124`) | `:248` |
| Composite reorder over FULL pool (`SOURCE_WEIGHT_ACTIVE`) | `:269-271`; fail-loud inert warning `:261-268` |
| `_collapse_subchunks` | `:279` (def `:550`) |
| Final cut `documents[:max_results]` | `:282` |
| DailyMed store — **local NumPy index**, query-embedding + cosine, `min_score=0.6` | `_search_dailymed` `:610`; `get_dailymed_store()` `api/database/vector_store.py:244`; threshold `:95`/`:102` |
| `detect_brands_in_text` — **double CJK-gated** | `api/services/tfda_lookup.py:257`; input gate `:268`; index keys filtered `has_cjk(k)` `:248`; `_CJK_RE` `:44` |
| Verify input **structured** vs Research **free text** | `VerifyRequest.drugs: list[str]` `api/models/schemas.py:178` · `ResearchRequest.question: str` `:36` |

---

## 2. M1 — re-baseline on HEAD (N=8, 120/120 runs)

**Run integrity.** Window **16:18:13 → 16:56:09**, single contiguous session, `complete: true`.
**Network-noise filter: 0 runs excluded** (0 zero-doc runs, 0 errored). Every run reached the
filter/rerank stages, so no result below is a disguised network failure.

*Note: the process began ~18 min after launch (first log line 16:18:02) for reasons I could not
determine — it is outside the harness. The delay was **before** the run started; the sample window
itself is contiguous and unaffected.*

### 2.1 Per-drug vs ANY-drug (fly-211 comparable) + content audit

`per-drug BOTH` = both queried drugs' own safety sections cited. `ANY-drug` = the fly-211 metric.
`on-target` / `intrusion` from the §2.2 content audit.

| Query | Classification | per-drug BOTH | **ANY-drug** | on-target | **intrusion** |
|---|---|---|---|---|---|
| warfarin_aspirin | PARTIAL | 0/8 | 4/8 | 7 | 0 |
| amiodarone_digoxin | PARTIAL | 0/8 | **8/8** | 16 | 0 |
| spironolactone | STILL-MISSING | 0/8 | 5/8 | 1 | **4** |
| warfarin_nsaid | PARTIAL | 4/8 | **8/8** | 13 | 0 |
| ace_potassium | PARTIAL | 0/8 | **8/8** | 32 | 0 |
| digoxin_diuretic | PARTIAL | 0/8 | **8/8** | 12 | 0 |
| **ssri_nsaid** | **STILL-MISSING** | 0/8 | **0/8** | 0 | 0 |
| warfarin_fluconazole | PARTIAL | 5/8 | **8/8** | 29 | 0 |
| lithium_ibuprofen | PARTIAL | 0/8 | **8/8** | 24 | 0 |
| r07_betablocker | RESOLVED-by-K-union | 8/8 | **8/8** | 32 | 2 |

**Tally on the strict per-drug bar: 1 RESOLVED · 7 PARTIAL · 2 STILL-MISSING.**
**Tally on the ANY-drug bar: 7 of 10 at 8/8; one at 5/8; one at 4/8; one total miss.**

### 2.2 ⚠️ The per-drug bar is the WRONG BAR — the pair-aware premise is refuted

I inspected the **actual section text** of every cited safety section (not the moiety name).
**Interaction text is inherently bilateral: a drug's own Drug Interactions section names its
counterparts.** Evidence:

| Query | Section cited | Text names |
|---|---|---|
| amiodarone_digoxin | `DIGOXIN #34073-7` (8/8 runs) | **amiodarone**, digoxin, digitalis |
| warfarin_aspirin | `WARFARIN SODIUM #34073-7` | warfarin, **aspirin**, anticoagulant |
| warfarin_nsaid | `WARFARIN SODIUM #34073-7` · `KETOPROFEN #34073-7` | warfarin + **nonsteroidal/NSAID** |
| ace_potassium | `POTASSIUM CHLORIDE #34073-7` · `LOSARTAN` · `VALSARTAN` | **ACE inhibitor**, renin-angiotensin, potassium |
| digoxin_diuretic | `DIGOXIN #43685-7` | digoxin, **diuretic**, **hypokalemia** |
| spironolactone | `POTASSIUM CHLORIDE #34073-7` | **spironolactone**, **potassium-sparing**, aldosterone |

**The decisive case is `amiodarone_digoxin`.** AMIODARONE is **absent from the entire corpus**
(§7), so "search BOTH drugs' safety sections" is *structurally impossible* — yet the query is
answered **8/8 runs** by DIGOXIN's own interactions section, which names amiodarone explicitly.

> **The premise behind the pair-aware candidate — "a drug-PAIR query has no single section covering
> both drugs" (`BACKLOG.md:778`) — is false as an operational claim.** It is true that no section is
> *authored for* the pair; it is **not** true that no single section *documents* the pair. The correct
> retrieval target is *"the section documenting the interaction,"* which may sit under **either** drug.
> Current retrieval already reaches such a section on **8/8 runs for 7 of 10** canonical queries.

### 2.3 Composite rank — the fly-211 "rank-6 > top_k-5" residual is now **directly confirmed**

fly-211 could only infer this indirectly (per-run rank was not captured). This probe captured it.

Across 80 safety-query runs: **172 safety sections cited, 42 not cited.** Not-cited rank
distribution (0-indexed composite rank): **`{5: 11, 6: 17, 7: 10, 8: 3, 10: 1}`**

**11 sections landed at rank 5 — the 6th slot, one position outside `top_k=5`.** This is a
measured, cheap lever candidate (§9.2), not an inference.

### 2.4 Genuine total miss: `ssri_nsaid`

**0/8 on ANY-drug** — the only query where no whitelisted safety section was cited at all, and none
appeared in the pool at any composite rank. Consistent with the 2026-07-22 threshold probe, which
recorded SSRI+NSAID as the single STABLE-MISS. This is a real recall gap and it is **not**
addressable by pair fan-out (see §9.3).

---

## 3. M2 — detector feasibility (complete; unchanged from the checkpoint)

Best detector today's assets allow = DailyMed `moiety` index (**1038 moieties**, 910 with ≥1 safety
section, 1479 tokens) + class-term list + intent gate.

| Corpus | Recall | FP rate |
|---|---|---|
| 8 probe-authored canonical queries, **no** intent gate | 6/10 | **71%** |
| 8 probe-authored canonical queries, **with** intent gate | 6/10 | 0% |
| **35 curated golden `research` cases (independent)** | **0/3** | **0/32** |

The intent gate is **mandatory** (71% FP without it). The 6/10 figure is inflated by the canonical
queries' English keyword-dense phrasing; on an independent corpus the detector fires on **nothing**.

**Asset inventory**

| Asset | Coverage | English-generic capable | Location |
|---|---|---|---|
| DailyMed `moiety` index | 1038 moieties / 910 with safety | **YES** — the only viable backing | `data/dailymed/label_docs.json` |
| `brand_ingredient.json` | 17,824 by_name / 15,877 by_stem | **NO** — `english` values are *product* names (`SODIUM BICARBONATE TABLETS "F.Y."`) | `data/tfda/` |
| RxNorm | n/a | Yes but **network** (`rxnav.nlm.nih.gov`, `api/data_sources/rxnorm_client.py:15`) | Explain path |
| Drug class terms | **0** | — | **no asset**; 5 of 10 canonical queries name a class |

---

## 4. M5 — trigger reachability staircase ⭐ (carries the verdict)

Base rate: **3/35 = 8.6%** of the curated corpus is a genuine pair-interaction query
(R12, R13, TB03). `R17` (DAPT duration) is pair-*adjacent*, reported separately, never scored.

| Tier | Reach | FP | New asset required |
|---|---|---|---|
| **A** English moiety match + English intent | **0/3** | 0/31 | none |
| **B** A + TFDA brand table (shipped `detect_brands_in_text`) | **0/3** | 0/31 | none |
| **C** B + CJK co-administration lexicon (13 terms) | **1/3** | 0/31 | small: the lexicon |
| **D** intent-only, zero drug names | R12, TB03 unreachable | — | **not built, not prototyped** |

### 4.1 ⚠️ Tier B adds **ZERO** reach — refuting `BACKLOG.md:780`

`BACKLOG.md:780` suggests *"a zh-TW-brand router could close a slice of [P3] + zh-TW DailyMed."*
**On this evidence it closes no slice of the pair surface**, for **two independent reasons**:

1. **TB03** (`太田胃散和warfarin一起吃安全嗎`): the shipped detector *does* fire on 太田胃散, but resolves
   it **`ambiguous` with `ingredients=[]`**. An ambiguous brand names no moiety, so there is no
   safety section to target — it cannot anchor a fan-out.
2. **R13** (`warfarin 和 aspirin 一起用 safe 嗎`): both drug names are **Latin-script**, and the TFDA
   index is CJK-keyed (`tfda_lookup.py:248`), so the brand router never sees them.

Only Tier C reaches anything, and the one query it reaches (**R13**) unlocks via **Chinese** intent —
not the English-generic case `BACKLOG.md:780` describes.

### 4.2 Tier D — mechanism class (named only, not built)

**R12** (`is it ok to give both blood thinners at the same time`) contains **zero drug names**.
Reaching it requires resolving an *implicit class reference* ("blood thinners" → anticoagulant
class) — a semantic/ontology or LLM-classification mechanism, categorically **not** name matching.

---

## 5. M3 — displacement / cost envelope

**Cost.** DailyMed search is a **local NumPy index** (query embedding + CPU cosine,
`retriever.py:610`), so a DailyMed-scoped fan-out adds embedding calls and CPU, and **zero
PubMed/FDA external rate-limit exposure**. Current per-query LLM calls: 1 rewrite + 3 K-union
rewrites (parallel, `:394`) + relevance filter + rerank ≈ **6**. M1 mean latency **15.5–20.2 s/query**.

**Displacement** (deterministic composite top-5 with-vs-without the whitelisted safety docs,
mirroring `_kunion_gate.py:99-113`; 3 queries × 4 runs). **Displaced doc types, named:**

| Query | Displaced | Type / tier |
|---|---|---|
| warfarin_aspirin | `PMID:37037980` *Contemporary Antiplatelet and Anticoagulant Therapies for Secondary Stroke Prevention* | pubmed, tier 4 |
| warfarin_aspirin | `PMID:22867637` *Pharmacokinetic and pharmacodynamic interaction of Danshen-Gegen extract with warfarin* | pubmed, tier 4 |
| warfarin_fluconazole | `PMID:25451849` *Comparison of the effects of azole antifungal agents on the anticoagulant activity of warfarin* | pubmed, tier 4 |
| warfarin_fluconazole | `PMID:8247921` *Possible interaction between warfarin and fluconazole* | pubmed, tier 5 |
| lithium_ibuprofen | none | — |

**0 safety/danger docs displaced** — consistent with the fly-211 bar. But note the displaced docs
are **directly on-topic studies**, not filler: `PMID:8247921` is literally titled *"Possible
interaction between warfarin and fluconazole."* Pool-budget pressure at `top_k=5` is a **real
trade**, not free headroom. Any lever that admits more docs pays this cost.

---

## 6. M4 — canaries + R15 baseline

**Canaries — all clean, 0/8 each (N=8):** `metformin_moa` 0/8 · `statin_moa` 0/8 · `glp1_weight` 0/8 ·
`statin_efficacy` 0/8 · `sglt2_cv` 0/8. The metformin-MoA canary sitting 0.017 below 0.6 did **not**
intrude in any run.

### 6.1 ⚠️ R15 baseline: **PASS / PASS / PASS (3/3)** — it is NOT a stable fail

Captured on HEAD via `tests/run_golden_tests.py --filter R15`, N=3, against a local `TEST_MODE`
server. **Capture-only — no fix attempted, per baton.**

`TECH_DEBT.md` records R15 as a **"STABLE FAIL"** and amended the §2.7 Research floor to
*17/2/1-with-R15-known-fail* (founder-accepted 2026-07-24), stating it was *"Confirmed STABLE on
re-run (not judge oscillation)."*

**It now passes 3/3, with no `api/` code changed since fly 211** (b1 and b1-fix were frontend-only —
verified zero `api/` in both merges). Per the TECH_DEBT **escalation condition**, movement must be
investigated rather than pattern-matched — so, stating it plainly:

- This movement is **not** change-induced; no PubMed-retrieval code changed.
- It is therefore **live-API drift** — precisely the mechanism the TECH_DEBT entry itself names
  (*"live-API result variance + `_rewrite_query` nondeterminism → R15 flipped PASS→FAIL … with no
  code change"*).
- **The consequence is that the "STABLE" characterisation is not supported.** R15 has now flipped in
  *both* directions with no code change. It is an **oscillator**, like R16/R20.

**Proposed correction (do not apply — founder sequences):** amend the TECH_DEBT R15 entry from
"stable FAIL" to "**oscillator** — observed FAIL 3/3 on 2026-07-24 and PASS 3/3 on 2026-07-27 with
zero intervening `api/` change," and reconsider whether the §2.7 floor should carry it as a
*known-fail* at all. **This does not invalidate the fly-211 ship decision** — the R15 counterfactuals
in that gate showed it never passed *on that day's* API state, which remains true of that sample.

---

## 7. ⭐ STANDALONE FINDING — DailyMed corpus coverage (NOT part of the pair-aware verdict)

**This is its own headline finding and must not be buried inside a closed entry.**

### 7.1 Build drop rate

From the corpus's own `_meta.stats` (`data/dailymed/label_docs.json`):

| Stat | Value |
|---|---|
| `backbone_reference_labels` | 1908 |
| `labels_with_sections` | 1203 |
| `labels_dropped_zero_sections_or_fetch_fail` | **705 → 36.9%** |
| `resolve_provenance.path_counts` | `miss: 627 · original: 952 · normalized_recall: 135 · mono_rescue: 116 · dropped_combo: 78` |

### 7.2 Common-drug reachability — 5/47 (11%), but **four distinct causes**

Checked 47 commonly-prescribed generics. **Reachability fact: 5/47 = 11% unreachable for a
safety-section lever.** Causes are **not** the same and must not be closed together:

| Drug | Cause | Defect? |
|---|---|---|
| **AMIODARONE** | `AMIODARONE HCL` **is** in the TFDA mono set (in scope) but absent from the corpus — lost downstream | ✅ **YES — the only genuine unexplained loss** |
| **PREDNISONE** | Family match: TFDA has it **combo-only**; mono forms are MEPREDNISONE/METHYLPREDNISONE. PREDNISOLONE family = 7 TFDA mono / 3 in corpus **with** safety | ❌ **market difference** — Taiwan prescribes prednisolone |
| **INSULIN** | Family match: **0** in TFDA mono, combo, and corpus — the TFDA 西藥許可證 backbone carries no biologics | ❌ **scope boundary** |
| **ASPIRIN**, **NAPROXEN** | present in corpus, **no safety sections** — OTC Drug-Facts label shape | ⚠️ see §7.4 |

**Method note (important):** PREDNISONE/INSULIN were re-checked with **family/substring** matching,
not literal equality — because this report documents a synonym-fragmentation defect (§7.4) that
applies to my own measurement method too. Family matching did not change their verdict.

**Attribution limit (Rule 18):** the `705` counter **conflates** zero-sections with fetch-failure and
there is **no per-drug log**, so I **cannot** determine which bucket AMIODARONE fell into. Stating
that rather than inferring. Determining it requires re-running the build with per-drug logging —
out of scope for a read-only probe.

### 7.3 ⭐ Research-vs-Verify asymmetry — a mitigation that did not travel

**Measured, with refs.** The gap is **Research-only**:

- **Verify resolves DailyMed LIVE**, never reading the corpus: `DailyMedClient` imported
  `api/server.py:65`, instantiated `:460`, called `api/server.py:1206` → `search_drug_labels`
  (`api/data_sources/dailymed.py:103`) → `_resolve_setids` (`:137`) issues a live
  `GET /v2/spls.json?drug_name=` (`:141-142`) → `_fetch_spl_xml` (`:167`).
- **Research reads the corpus**: `retriever.py:22`, `:120`, `:189`, `:618`.

Sharper: `api/server.py:1202-1204` **already documents this exact hole and mitigates it** —
> *"A label counts here ONLY if its LOINC 34073-7 Drug Interactions section is present (OTC
> Drug-Facts labels — **e.g. aspirin** — lack it → treated as a miss so we fall through to openFDA)."*

**Verify knows about the aspirin gap and falls back to openFDA. Research has no such fallback.**

> **CLASS OF BUG: a mitigation existed on one surface and was not carried across when the same data
> source was extended to a second surface.** Structurally identical to b1's
> *"country-keyed the DATA but not the STRINGS"* — the extension moved the data path and left the
> compensating logic behind.

### 7.4 Moiety-synonym fragmentation (distinct from retrieval)

`ASPIRIN` and `ACETYLSALICYLIC ACID` are **two separate moiety keys for the same drug**; safety
sections exist on **only one**:

| Moiety | Sections |
|---|---|
| `ASPIRIN` | indications (34067-9), dosage (34068-7) — **no safety** |
| `ACETYLSALICYLIC ACID` | contraindications, interactions, warnings |

A detector or lookup keyed on "aspirin" reaches the wrong record. **`NAPROXEN` is a different
defect** — present, no safety sections, **no** synonym alternative: a genuine content gap.

### 7.5 Proposed BACKLOG entry (wording only — not applied)

> **[P2] DailyMed Research corpus has an unmeasured common-drug safety-coverage hole (honesty)**
> — 36.9% of reference labels (705/1908) dropped at build; **11% of 47 commonly-prescribed generics
> unreachable** for a safety-section lever, incl. AMIODARONE (in scope, unexplained loss), ASPIRIN
> and NAPROXEN (no safety sections). **Research-only** — Verify resolves live and already falls back
> to openFDA for OTC Drug-Facts labels (`server.py:1202-1204`); Research has no fallback.
> Sub-items: (a) per-drug build logging to attribute the 705; (b) moiety-synonym normalization
> (ASPIRIN↔ACETYLSALICYLIC ACID); (c) decide whether Research needs Verify's openFDA fallback;
> (d) publish the coverage number.
> **Cross-ref the existing `[P2]` full-site DailyMed over-claim sweep — same honesty family:** we
> present DailyMed as the 5th Research retrieval source while its common-drug safety coverage has a
> hole we have never measured or disclosed.

**Suggested priority: [P2].** Reasoning: it is **not [P1]** because it is not a live incorrect
*assertion* — Research degrades to other sources rather than fabricating, and the highest-risk
surface (Verify, structured drug input, interaction claims) is **structurally immune**. It is **not
[P3]** because it is an honesty/credibility exposure on a shipped, user-visible source claim, which
is exactly the family the existing over-claim sweep already treats as [P2]. Placing it beside that
entry keeps one consistent bar.

---

## 8. ⭐ STANDALONE FINDING — the fly-211 gate metric under-attributes

**The shipped gate's headline "CITED recovery 0.625 → 0.90 mean" was computed with an "any DailyMed
whitelisted safety section cited" metric that does not attribute the section to the queried drug**
(`_kunion_gate.py:49-50`, `_dm_safety` → LOINC membership only).

Measured consequence on `spironolactone potassium hyperkalemia contraindication`:

| Metric | Result |
|---|---|
| ANY-drug (fly-211 metric) | **5/8** |
| …of which the section **answers the question** | **1/8** (`POTASSIUM CHLORIDE #34073-7`) |
| …of which is a **wrong-object intrusion** | **4/8** (`POTASSIUM ACETATE #34070-3`) |
| SPIRONOLACTONE's own safety section | **0/8** — never entered the pool at any rank |

The 4 intrusion runs cited this section **in full** (194 chars):

> "CONTRAINDICATIONS Potassium administration is contraindicated in patients with severe renal
> insufficiency or adrenal insufficiency and in diseases where high potassium levels may be
> encountered."

No mention of spironolactone, potassium-sparing diuretics, or the interaction. It is about
*administering potassium supplements* — a different clinical object.

**Framing (accurate):** fly 211 is **additive** and its **ship decision is NOT invalidated** — the
lever demonstrably increased safety-section reach, canaries stayed clean, and danger-path was 0/0.
**What needs qualifying is the recorded NUMBER**, which counts semantically-adjacent wrong-drug
sections as recovery.

**Cross-ref CLAUDE.md Rule 17** — *tests must verify intent, not just behavior*. The gate metric
verified "a whitelisted LOINC appeared," not "the query's interaction was answered." The business
rule it should protect is the latter.

**Proposed correction note (wording only — do not apply; founder sequences):**

> **⚠️ METRIC QUALIFICATION (added 2026-07-27, pair-aware probe).** The CITED-recovery figures in
> this entry (0.625→0.90; spironolactone 0.125→0.875) use an **any-DailyMed-whitelisted-safety-section**
> metric that does **not** attribute the section to the queried drug. Re-measured on HEAD with
> per-drug attribution + content inspection, `spironolactone` scores **5/8 any-drug but 1/8
> question-answering**, with **4/8 wrong-object intrusions** (`POTASSIUM ACETATE` contraindications,
> which never mentions spironolactone) and **0/8** for spironolactone's own section. The **ship
> decision stands** (additive lever, clean canaries, 0/0 danger-path); the **recovery number is
> overstated for at least this query**. Future recall gates should assert the cited section
> *documents the queried interaction* (Rule 17), not merely that a whitelisted LOINC appeared.

---

## 9. Plan-back — **(c) RE-SCOPE**

### 9.1 Close the pair-aware candidate — its premise is refuted, and its trigger cannot fire

Two independent, sufficient reasons:

1. **The premise is false (§2.2).** `BACKLOG.md:778` claims a pair query "has no single section that
   covers both drugs." Interaction text is **bilateral**: one drug's Drug Interactions section names
   its counterpart. `amiodarone_digoxin` is answered **8/8** by DIGOXIN's section *while AMIODARONE
   is entirely absent from the corpus*. "Search BOTH drugs' sections and merge" solves a problem
   that does not exist; **ANY-drug reach is already 8/8 on 7 of 10** canonical queries.
2. **The trigger cannot fire (§4).** The best staircase over existing assets reaches **1 of 3** real
   pair queries; Tiers A and B reach **0/3**. A lever whose trigger never fires is inert regardless
   of residual size. And the base rate is **8.6%**.

Adding fan-out would also **worsen** the measured pool-budget trade (§5) — displacing on-topic
studies — and would add more wrong-drug candidates of exactly the kind §8 documents.

**Record in BACKLOG:** close the pair-aware structural candidate on `BACKLOG.md:779` / `:791` as
**REFUTED-BY-MEASUREMENT** (not merely "inadequate"), citing §2.2. Correct `BACKLOG.md:778`'s
premise sentence and `:780`'s zh-TW-router hypothesis (§4.1).

### 9.2 Re-scope to surface 1 — **pool budget at `top_k=5`** (cheapest, best-evidenced)

**11 safety sections landed at composite rank 5**, one slot outside `top_k=5` (§2.3) — the fly-211
rank-6 residual, now directly measured. A `top_k` change is a **one-line config-level lever**, orders
of magnitude cheaper than a retrieval-architecture change. **But it is not free** (§5): it admits
displaced-doc competition and changes generation input for **every** Research query → needs its own
§2.7 + danger-path gate. **Recommend a dedicated measure-only sweep first** (`top_k` 5 vs 6 vs 7:
recall gain, canary intrusion, displacement, latency, cost) before any build decision.

### 9.3 Re-scope to surface 2 — **`ssri_nsaid` total miss** (real, and not a pair problem)

**0/8 ANY-drug**, no section in the pool at any rank (§2.4). Reproduces the 2026-07-22 STABLE-MISS.
Pair fan-out would not fix it — nothing for either drug clears `min_score=0.6`. This is a
**relevance/embedding** gap, a different surface from both pair-awareness and `top_k`.

### 9.4 Re-scope to surface 3 — **danger-path wrong-object intrusion** (safety-adjacent)

The `POTASSIUM ACETATE` case (§8) is a **contraindications section about a different clinical
object surfacing on a danger-path query**, 4/8 runs. `r07_betablocker` shows the same shape twice
(`PINDOLOL` contraindications, naming no queried term). This is a **precision** defect on the exact
query class where precision matters most. It is currently **invisible** to the fly-211-style gate,
which counts it as success. **Recommend: treat as its own [P2] investigation** with a content-aware
assertion (does the cited section name the queried drug/class?), reusing this probe's audit method.

### 9.5 Not folded into the verdict

- **§7 corpus coverage** — standalone [P2], proposed wording in §7.5.
- **§8 gate-metric qualification** — standalone, proposed wording in §8.
- **§6.1 R15 is an oscillator, not a stable fail** — proposed TECH_DEBT correction in §6.1.
- **Strategy question (§10)** — for founder, not a defect.

---

## 10. Strategy question for the founder (NOT a defect, no fix proposed)

The DailyMed corpus scope is **`mono-ingredient TFDA moieties → NDA-preferred US reference label`**
(`_meta.scope`) — i.e. **the Taiwan market overlap**. That was coherent when DailyMed shipped as the
5th Research source (fly 206, Taiwan-first).

**b1/b1-fix (fly 212/213) have since shipped 6-country locale support with SG and MY live.** A drug
licensed in Singapore or Malaysia but absent from Taiwan's mono set is **structurally unreachable**
in Research's DailyMed corpus — the locale panel will point an SG/MY user at HSA/NPRA while the
underlying retrieval corpus is scoped to Taiwan's formulary.

**Not quantified — and not cheaply quantifiable.** It would require SG (HSA) and MY (NPRA) product
registries, neither of which is in the repo. The only in-repo anchor is the ratio itself: the corpus
covers **1038 moieties** against a TFDA mono backbone of **1910**. Stating the limit rather than
estimating past it.

**Question for sequencing:** should the corpus backbone remain Taiwan-scoped now that the product
addresses six countries, or is the Taiwan-overlap scope still the right bet? No recommendation.

---

## 11. Assumptions, limitations, and what I could not measure

1. **`is_pair_interaction` labels are mine.** `PAIR_TRUE = {R12, R13, TB03}` is my hand-labelling of
   the golden corpus, recorded in `_pairaware_m2_golden_fp.py` so it can be disputed. **n=3** is a
   very small denominator.
2. **No production query data.** All FP/recall figures are from a curated eval set, not PostHog
   traffic. A real base rate and FP rate need production queries; this probe did not access them.
3. **The canonical 8 queries are probe-authored**, English and keyword-dense — demonstrably
   unrepresentative of the real phrasing in the curated corpus (§3). M1's absolute numbers should be
   read as *"what these 8 strings do,"* not *"what users experience."*
4. **AMIODARONE's drop cause is not determinable** from the artifact (§7.2).
5. **SG/MY corpus-scope exposure not quantified** (§10) — registries unavailable.
6. **M3 is N=4 on 3 queries** — sufficient to name displaced doc types, not to estimate a rate.
7. **R15 baseline ran against a local `TEST_MODE` server**, the runner's default target
   (`run_golden_tests.py:36`). I did not verify whether the 2026-07-24 baseline used identical
   conditions; if it did not, the PASS/FAIL comparison carries that caveat.
8. **A pre-existing bug blocked the golden runner** on Windows: `run_golden_tests.py:731` prints a
   `✅` under cp950 → `UnicodeEncodeError`. Worked around with `PYTHONIOENCODING=utf-8` (environment
   only — **the file was not modified**). Worth its own tiny fix; not done here (read-only baton).
9. **The ~18-minute launch queueing delay** before M1's process started is unexplained. It occurred
   **before** the run; the sample window (16:18:13→16:56:09) is contiguous.

---

## 12. Artifacts

**Committed (docs):** `docs/pair_aware_retrieval_probe.md` (`e0a5a92`, pushed) — to be superseded
in place by this report.

**Local only (`tests/results/`, gitignored):**
`pair_aware_retrieval_probe_REPORT.md` (this file) · `pairaware_m1_20260727_161811.json` (M1, N=8,
complete) · `pairaware_m1_content_audit.json` · `pairaware_m3_20260727_165945.json` ·
`pairaware_m5_staircase.json` · `pairaware_ceiling.json` · `pairaware_m2_detector.json` ·
`pairaware_m2_golden_fp.json` · `pair_aware_probe_CHECKPOINT.md`

**Probe scripts (throwaway):** `_pairaware_m1.py` (now persists incrementally + network-noise
filter) · `_pairaware_m1_content_audit.py` · `_pairaware_m3_displacement.py` ·
`_pairaware_m5_staircase.py` · `_pairaware_ceiling.py` · `_pairaware_m2_detector.py` ·
`_pairaware_m2_golden_fp.py`

**READ-ONLY honoured:** no `api/`, `utils/`, `components/`, prompt, flag, or config file was modified
at any point. STATE / BACKLOG / TECH_DEBT deliberately **not** updated — founder sequences that.
