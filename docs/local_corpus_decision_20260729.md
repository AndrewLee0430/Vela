# Local drug corpus — DEPRECATE vs REPAIR: measurement + recommendation (2026-07-29)

**Basis:** [`citation_gate_findings_20260729.md`](citation_gate_findings_20260729.md) Finding 1 (`1c26c8e`)
— all 690 documents in `data/drug_vectordb/index.json` are field-label stubs (max 5 chars of content),
because `collect_drug_data.py`'s `_extract_*` read a data shape that never existed, leaving ≈3.58 M chars
of real FDA label text unread in `full_label`.

**Nothing was shipped by this baton.** Phase 1 was read-only. Phase 2 made ONE temporary edit
(`api/server.py` `enable_local=True → False`) which was reverted and verified (`git diff api/server.py`
empty). No corpus, prompt, flag, or product behaviour changed.

**RECOMMENDATION: (c) — DEPRECATE `local`, and recover the genuinely-missing coverage in the DailyMed
build where it belongs. Do NOT repair `_extract_*`.** Reasoning in §4.

---

## 1. Phase 1a — the deciding measurement: complementary or redundant?

Method: for each of the 190 local drug records, resolve `drug_name` → DailyMed moiety (salt/family-aware
matching; `exact-base` 153, `family-first-token` 14, `absent` 23) and ask whether DailyMed already
carries a **whitelisted safety section** (34073-7 · 34070-3 · 43685-7 · 34066-1). Independently measure how
much drug-interaction / contraindication / warning / adverse-reaction text `full_label` actually holds —
i.e. exactly what a REPAIR would recover.

> **Method cross-check:** the same script independently reproduces the recorded Step-F figure —
> **128 / 1038 moieties (12.3%) lack any whitelisted safety section.** The matching is not inventing a
> different universe.

### THE SPLIT

| class | drugs | share |
|---|---|---|
| **REDUNDANT** — DailyMed already has it **with** a safety section | **155** | **81.6%** |
| **COMPLEMENTARY** — DailyMed lacks safety for it, `full_label` has safety text | **35** | **18.4%** |
| **NEITHER** — no DailyMed safety AND no `full_label` safety text | **0** | 0.0% |

DailyMed coverage of the 190: `safety` 155 (81.6%) · `no_safety` 12 (6.3%) · `absent` 23 (12.1%).

**So four fifths of a repair would rebuild, worse, what already exists** — as whole-drug blobs with no
URL, against a live per-section corpus with real setid deep-links.

### The complementary 18.4%, decomposed — it is smaller than it looks

| sub-class | drugs | what the text actually is |
|---|---|---|
| structured **Rx** label (real Drug Interactions / Contraindications) | 19 | the clinically valuable part |
| **OTC Drug-Facts "Warnings" only** (no interactions, no contraindications) | 14 | real safety text, but not an interactions section |
| thin / other | 2 | Prednisone, Triamcinolone |
| *of the 19 structured, these are **combination-product** labels* | *2* | *Hydrocodone (w/ acetaminophen), Salmeterol (w/ fluticasone)* |

**Clean, structured, complementary core = 17 drugs / 190 = 8.9%**: Adalimumab, Albuterol, Amphetamine,
Bevacizumab, Canagliflozin, Desvenlafaxine, Dulaglutide, Etanercept, Famotidine, Infliximab,
Insulin Glargine, Insulin Lispro, Liraglutide, Lisdexamfetamine, **Naproxen**, Semaglutide, Terbinafine.
Total complementary safety text: **339,272 chars** (9.5% of the 3.58 M).

### ⚠️ The named clinically-significant cases — and WHY DailyMed lacks them

| drug | DailyMed | class | interactions | contra | warnings | adverse |
|---|---|---|---|---|---|---|
| **Naproxen** | no_safety | COMPLEMENTARY | **10,898** | 868 | 0 | 6,967 |
| **Aspirin** | no_safety | COMPLEMENTARY | 0 | 0 | **2,292** | 0 |
| **Ibuprofen** | no_safety | COMPLEMENTARY | 0 | 0 | **2,615** | 0 |
| Famotidine | no_safety | COMPLEMENTARY | 1,428 | 328 | 0 | 2,593 |
| Omeprazole | no_safety | COMPLEMENTARY | 0 | 0 | 1,387 | 0 |
| Terbinafine | no_safety | COMPLEMENTARY | 3,570 | 341 | 0 | 4,779 |
| Ranitidine · Esomeprazole · Pantoprazole · Lansoprazole · Rabeprazole | safety | **REDUNDANT** | — | — | — | — |
| **Cimetidine** | — | **NOT IN the 190-drug local set at all** | — | — | — | — |

Sample of what a repair would recover (verbatim, truncated):

- **Naproxen** — `7 DRUG INTERACTIONS  See Table 1 for clinically significant drug interactions with
  naproxen. Table 1: … Drugs That Interfere with Hemostasis  Clinical Impact: • Naproxen…` (10,898 chars)
  **This is exactly the content whose absence produces wrong-drug citations on NSAID safety queries.**
- **Aspirin** — `Warnings  Reye's syndrome: Children and teenagers who have or are recovering from
  chicken pox or flu-like symptoms should not use this product…` (2,292 chars — **OTC Drug Facts**)
- **Ibuprofen** — `Warnings  Allergy alert: Ibuprofen may cause a severe allergic reaction, especially
  in people allergic to aspirin…` (2,615 chars — **OTC Drug Facts**)

#### 🔎 ROOT CAUSE of the DailyMed gap — it is a reference-label SELECTION artifact, not missing data

**120 of the 128 no-safety moieties (93.8%) carry exactly `{34067-9 indications, 34068-7 dosage}` — the
OTC Drug-Facts section shape.** And the reference label the build selected for the clinically significant
ones is an **NDA-approved OTC brand**:

| moiety | reference label selected | sections it has |
|---|---|---|
| NAPROXEN | **Aleve** (NAPROXEN SODIUM) | indications + dosage only |
| ASPIRIN | **VAZALORE** (aspirin) | indications + dosage only |
| IBUPROFEN | **ADVIL** (ibuprofen) | indications + dosage only |
| OMEPRAZOLE | **Prilosec OTC** | indications + dosage only |
| FAMOTIDINE | **PEPCID AC** | indications + dosage only |
| CIMETIDINE | **Tagamet** | indications + dosage only |
| TERBINAFINE | **Lamisil AT Cream** | indications + dosage only |
| TRIAMCINOLONE | **Nasacort Allergy 24HR** | indications + dosage only |

The build's preference is `marketing_category_code NDA > NDA_AG > ANDA > other` (`_meta.reference_selection`)
with **no Rx-vs-OTC tiebreak** — and these OTC brands are NDA-approved, so the rule *actively prefers them*
over Rx generic ANDAs. **OTC Drug Facts labels have no safety LOINC sections at all**, so the moiety lands
in the 128.

**Evidence that an Rx label exists and was simply not selected:** for the SAME moieties, openFDA's first
hit is an **Rx generic label carrying real interactions text** — Naproxen 10,898 · Terbinafine 3,570 ·
Famotidine 1,428 chars. (For Aspirin / Ibuprofen / Omeprazole both sources land on OTC, so their
complementary content is Drug-Facts *Warnings* only — stated so the claim is not over-read.)
⚠️ **This is inference from the openFDA mirror, not a live DailyMed query** — before acting on it, confirm
an Rx SPL with 34073-7 exists in DailyMed for at least Naproxen.

**The remaining 23 `absent` drugs are a SCOPE boundary, not a defect:** the DailyMed corpus's declared
scope is *"mono-ingredient **TFDA** moieties → NDA-preferred US reference label"*. Biologics (Adalimumab,
Infliximab, Bevacizumab, Etanercept), insulins, GLP-1s (Semaglutide, Dulaglutide, Liraglutide) and
controlled substances (Amphetamine, Lisdexamfetamine) are out of that scope by construction — consistent
with the previously recorded "INSULIN = biologics scope boundary".

### ⚠️ Quality of what a repair would import — three defects it would inherit

1. **11.6% combination-product labels (22/190).** `Metformin`'s label is **SITAGLIPTIN AND METFORMIN**;
   `Lisinopril`'s is **LISINOPRIL AND HYDROCHLOROTHIAZIDE**; `Codeine`'s is **ACETAMINOPHEN AND CODEINE**.
   Repair would import combination-product safety text under a mono-drug name — **the same wrong-object
   family as the recorded [P2] wrong-drug intrusion and the [P2] setid repackager-vs-reference item.**
   (Within the complementary 35: 6 are combination products.)
2. **Repackager labels.** Manufacturers on the complementary set include **A-S Medication Solutions (4),
   Bryant Ranch Prepack (3), CVS Pharmacy (2)**, Preferred Pharmaceuticals, PD-Rx. The collector takes
   `search_drug_labels_sync(drug, limit=1)` — **the first hit, with no reference-label preference at all**,
   which is precisely the problem the DailyMed build already solved.
3. **Still no URL.** `full_label.url` is `https://labels.fda.gov/` on **190/190**, so repaired documents
   remain unlinkable — or worse, falsely linkable (identical hazard to the openFDA hard ordering constraint).

*(Good news, stated for balance: **0/190** records have a `full_label` that fails to mention their own drug
name — the collector never fetched a completely unrelated drug.)*

---

## 2. Phase 1b — deprecation blast radius

### Consumers of the local store (complete)

| site | what it does | affected by deprecation? |
|---|---|---|
| `api/server.py:449-455` `HybridRetriever(enable_local=True)` | **the only retrieval wiring point** | ✅ the switch |
| `api/rag/retriever.py:109` / `:180` | `get_vector_store() if enable_local` + the fan-out guard | ✅ already guarded — `enable_local=False` is a supported, tested path |
| `api/server.py:2418-2419` `/api/status` | calls `get_vector_store().get_stats()` **directly**, bypassing `enable_local` | ⚠️ **would still load the 690 docs into memory**; needs handling |
| `api/services/source_weight_shadow.py:31,93,141` | `local` = Tier 2 ×1.5 in the composite | ⚠️ becomes dead config (harmless, should be cleaned) |
| `utils/sourceLabels.ts:61` | `local → "FDA"` display merge | ⚠️ becomes dead (and removes the FDA/openFDA chip ambiguity) |
| `api/services/share_renderer.py:195` | `local → "Local"` on the shared public page | ⚠️ dead — **and note it disagrees with the frontend's "FDA"**, an instance of the recorded [P2] sourceLabels↔share_renderer drift |
| `tests/citation_url_guard.mjs` | the **documented `local` exemption** | ⚠️ **MUST be updated** — the guard asserts the local corpus exists and is URL-less; deleting the corpus without touching the guard would make it assert about nothing |
| `scripts/build_drug_vectordb.py`, `scripts/collect_drug_data.py` | the builders | become unused |
| `scripts/init_knowledge_base.py` | 🔎 **already dead and broken** — calls `VectorStore(persist_directory=…, collection_name=…)` and `add_documents(...)`; the real signature is `VectorStore(index_path=…)` with no such method. Chroma-era leftover, referenced nowhere (not in CLAUDE.md setup, not in the Dockerfile). **Flagged, not touched.** | — |

**Verify and Explain do not touch it.** Verify is DailyMed-primary with an openFDA fallback
(`server.py:1202-1204`); Explain uses the LOINC/RxNorm/MedlinePlus cache. **`HybridRetriever` is
instantiated exactly once in `api/` (`server.py:449`)** — Research only.

### Does the "official FDA drug data" claim survive? **YES — plainly, and it never depended on `local`.**

| claim | where | what actually serves it |
|---|---|---|
| *"checks drug interactions against official FDA data"* | `i18n-faq.ts` (16 langs) | **Verify** → DailyMed-primary + openFDA fallback |
| *"Verify checks drug interactions using official FDA drug labels (OpenFDA) data"* | `i18n-faq.ts` | **Verify's openFDA path, which works** (it passes a single drug name, so `fda.py:127` matches) |
| *"FDA drug labels (OpenFDA) — official drug label and interaction data"* (1 of 3 databases) | `i18n-faq.ts` | Verify's openFDA + the **4,608-doc DailyMed corpus**, which **is the FDA/NLM SPL archive** (`_meta.source`: *"DailyMed v2 SPL (US labels)"*) |
| *"verified by PubMed, FDA, and local authorities"* · *"FDA reference integration"* | `pages/index.tsx:156,226` | same |
| `dashVerifyDesc` *"Check drug interactions against official FDA label data"* | `i18n-extra.ts` | Verify |

**Every FDA claim is attached to Verify or to the FDA-label family generally — none to the `local`
Research store.** Deprecating it removes no true claim.

Two naming notes, recorded not acted on: **(i)** "local authorities" in the landing copy means *regulatory
authorities* (the TFDA/NHI locale panel), **not** the `local` vector store — do not conflate them.
**(ii)** the copy says "FDA drug labels **(OpenFDA)**", a wording chosen by the v189 over-claim sweep when
DailyMed was *not* integrated. DailyMed has been the 5th Research source since fly 206 and openFDA is
structurally inert in Research, so the parenthetical is now stale **in the opposite direction**. Belongs in
the consolidated provenance-string sweep, not here.

---

## 3. Phase 2 — live §2.7 Research gate with `local` EXCLUDED

**Ops (per the SOP):** stale-`:8000` check first (nothing listening), server backgrounded, fresh bind
confirmed (**no `Errno 10048`**). ⚠️ **Deviation, stated:** the SOP asks for the runner in the
*foreground*; each arm takes ~9.5 min against a 10-min foreground tool cap, so both runners were
backgrounded. The fail-loud guard is the safety net, and it is reported explicitly below.

⚠️ **I ran a same-day CONTROL arm rather than comparing to the 2026-07-28 baseline — and that decision
mattered.** See R17 below.

**Treatment condition verified at the server, not assumed:** the local-OFF server log shows
`TFDA indication corpus loaded: 10941` and `DailyMed label corpus loaded: 4608` and **no
`Vector store loaded: 690 documents` line at all.**

### Verdicts

| run | condition | PASS | WARN | FAIL | ERROR | `run_complete` | `gate_valid` | `cases_expected/attempted` | `never_ran` | exit |
|---|---|---|---|---|---|---|---|---|---|---|
| `golden_results_20260728_114818` | baseline (local ON) | 19 | 1 | **0** | 0 | true | true | 20 / 20 | [] | — |
| `golden_results_20260729_141234` | **CONTROL** (local ON) | 18 | 2 | **0** | 0 | **true** | **true** | **20 / 20** | **[]** | **0** |
| `golden_results_20260729_172107` | **TREATMENT** (local OFF) | **19** | **1** | **0** | 0 | **true** | **true** | **20 / 20** | **[]** | **0** |

**Both runs cleared the §2.7 floor (18/2/0, every FAIL adjudicated individually). Zero FAILs in either
arm, so no adjudication was required. Removing `local` cost nothing and, on this run, gained one verdict.**

⚠️ **The fail-loud completeness guard STILL has not been exercised on a real interrupted gate** — both runs
completed, so it reported `run_complete=true` / `gate_valid=true` / exit 0. Its negative-control-only status
is unchanged.

### Per-case deltas — and the reason a same-day control was necessary

**R17 (DAPT duration) moved WARN → PASS with a byte-IDENTICAL retrieved pool.** Identical pool ⇒ identical
generator input ⇒ the movement is **judge oscillation**, not retrieval. Against the 07-28 baseline (19/1/0)
I would have counted R17 as a *regression caused by removing local*. It is not. Pool-identity capture is
what discriminated it — the mechanism built for the R15 escalation rule doing exactly its job.

**R15 adjudicated on its own merits, not pre-accepted:** **PASS in both arms**, pool size 1, pool
**IDENTICAL** across arms. No escalation condition met.

**R20** WARN in both arms (`missing: mentions safer alternative such as methyldopa or labetalol`) — the
documented safer-alternative oscillator, unchanged.

### ⚠️ What filled the freed slots — the honest answer is "only two slots were actually freed"

`local` contributed **2 documents out of 87** (2.3%) in the control arm — and **the same two** as the
07-28 baseline, so its footprint is reproducible, not a fluke:

| | docs in pools | local docs | which |
|---|---|---|---|
| baseline 07-28 (local ON) | 90 | **2** | R01 `fda-metformin-adverse` · R13 `fda-warfarin-interactions` |
| control 07-29 (local ON) | 87 | **2** | R01 `fda-metformin-adverse` · R13 `fda-warfarin-interactions` |
| treatment 07-29 (local OFF) | 84 | **0** | — |

Both are 1-character stubs: `Drug: Metformin\n\nAdverse Reactions:\n6` and
`Drug: Warfarin\n\nDrug Interactions:\n7`. **On R13 — `warfarin 和 aspirin 一起用 safe 嗎`, a danger-path
interaction query — the pool carried a citation titled "Warfarin - Interactions" whose entire content is
one character.**

What happened to those two slots:

- **R01**: local doc OUT → **`PMID:38837240` IN** (*"Metformin for preventing the progression of chronic
  kidney disease"*) — an on-topic study replaced a 1-char stub. Pool 5 → 4.
- **R13**: local doc OUT → **nothing entered.** Pool **5 → 3**. The freed slot went unfilled.

**Whitelisted safety sections in pools rose 12 → 15 (+3)** — R10 gained *Digoxin — Warnings and
Precautions*, R11 gained *Metformin HCl — Contraindications* **and** *Glumetza — Contraindications*.
⚠️ **I am NOT claiming those for the treatment.** `local` was not in R10's or R11's control pool, so no slot
was freed there; those gains are **rewrite-nondeterminism pool churn**, the same class as R15. 11 of 20
cases changed pool identity, including cases with no local document at all (R08's five PubMed docs turned
over completely). **Attributable effect = the two slots above. Everything else is churn.**

### Wrong-drug intrusion count

Content-audit classification over every pooled document (corpus text for local/DailyMed/TFDA; title-only
for PubMed, reported separately as the weaker basis):

| | control | treatment | delta |
|---|---|---|---|
| on-target (content-verified) | 14 | 16 | +2 |
| **INTRUSION** (content mentions no query term) | **0** | **0** | **0** |
| title-only:on (PubMed) | 68 | 64 | −4 |
| title-only:off (PubMed) | 5 | 4 | −1 |
| whitelisted safety sections | 12 | 15 | +3 |

**The intrusion count did not move: 0 → 0.** Reported and left to stand. ⚠️ **This is not evidence that
the wrong-drug defect is fixed or unaffected** — that defect was measured on a *different* query set (the
pair-aware canonical safety queries, where `POTASSIUM ACETATE` was cited 4/8 on a spironolactone query),
and the §2.7 Research set contains none of those queries. **This measurement has no power over it.**

---

## 4. Recommendation — **(c): DEPRECATE `local`, recover the real gap in the DailyMed build**

Not (a) alone and explicitly **not (b)**.

### Why not (b) REPAIR — the numbers argue against it on four independent grounds

1. **81.6% of it is redundant.** A repair rebuilds, in an inferior format, what DailyMed already has.
2. **The valuable remainder is 17 drugs (8.9%)** — and for the OTC-selection half of it, the *better* fix
   produces per-section, deep-linkable, reference-quality documents instead of whole-drug blobs.
3. **It would import three known defects**: 11.6% combination-product labels, repackager-first selection,
   and still-unlinkable URLs. Two of those are the very defect families already open as [P2] items.
4. **It is 🔴 and expensive**: re-embedding 690 substantive documents changes retrieval input on every
   Research query, needs its own §2.7 + danger-path re-gate, and adds a *second* whole-drug FDA corpus
   competing for a `top_k=5` budget already measured as tight (11 safety sections parked at composite
   rank 5).

### Why (c)

- **Phase 2 says the cost of removal is nil**: 2 stub documents out of 87, no verdict cost (18/2/0 →
  19/1/0, 0 FAIL both arms), R15 unaffected.
- **Deprecation also closes three open items for free**: the Finding-5 "FDA cards look broken" UX problem
  disappears; the FDA-chip ambiguity (`local` vs openFDA both labelled "FDA") disappears; and the
  sourceLabels↔share_renderer "FDA" vs "Local" drift loses one of its two sides.
- **The genuinely missing coverage is a DailyMed-build problem, not a local-corpus problem** — and fixing
  it there yields *better* artifacts than repair ever could.

### Proposed sequence

**(c1) DEPRECATE — remove `local` from Research retrieval.** 🔴 retrieval change.
**(c2) Recover the complementary coverage in the DailyMed build** — two separable pieces:
  - **(c2-i) Rx-preference tiebreak in reference-label selection.** Prefer a label that *has* safety
    sections over an OTC Drug-Facts label when both exist for a moiety. Targets the NAPROXEN / FAMOTIDINE /
    TERBINAFINE class and up to ~8 of the 128. **⚠️ Confirm first** that an Rx SPL with 34073-7 exists in
    DailyMed for Naproxen — the current evidence is the openFDA mirror, not a live DailyMed query.
  - **(c2-ii) Scope widening** for the biologics / insulin / GLP-1 class (23 drugs absent because the
    corpus is keyed to TFDA mono moieties). Larger, and a genuine scope decision — **founder call, not a
    build tweak.**

(c1) and (c2) are independent and can ship in either order. (c1) is ready now; (c2-i) needs one
confirmation; (c2-ii) needs a scope decision.

### Gates required before (c1) ships

| # | gate | status |
|---|---|---|
| 1 | **§2.7 Research 20 cases**, floor 18/2/0, every FAIL adjudicated | ✅ **pre-measured today: 19/1/0, exit 0, `gate_valid=true`** — re-run on the actual change |
| 2 | **Section-aware danger-path re-gate** | ❌ not run — required (🔴 changes what is retrieved) |
| 3 | **Canary check** (metformin / statin / GLP-1 no-safety-intrusion) | ❌ not run |
| 4 | **Prod human-eye gate**, incl. the standing citation-deep-link SOP row | ❌ founder |
| 5 | `tests/citation_url_guard.mjs` — **update the documented `local` exemption**, negative-controlled | ❌ the guard currently asserts the local corpus exists |
| 6 | `/api/status` (`server.py:2418`) — stop loading the store outside `enable_local` | ❌ |
| 7 | Dead-config cleanup: `source_weight_shadow` local tier · `sourceLabels.ts` local entry · `share_renderer` local entry | ❌ |
| 8 | Decide the **artifact's** fate — leave `data/drug_vectordb/` in place (unloaded) or delete builders too | ❌ founder |

### Limits

- Phase 2 is **one run per arm on 20 cases**. Pool churn affected 11/20 cases, so per-case attribution is
  weak by construction; the robust claims are the verdict totals and local's 2-document footprint (which
  reproduced exactly across two independent local-ON runs).
- The content audit classifies PubMed by **title only** (no local corpus text) — 68/87 and 64/84 documents
  fall in that weaker class, and they are reported separately rather than merged.
- The §2.7 Research set does not contain the queries on which the wrong-drug defect was measured, so the
  0 → 0 intrusion result has **no power** over that defect in either direction.
- (c2-i) rests on the openFDA mirror as evidence that an Rx SPL exists; **not confirmed against DailyMed
  directly.**
