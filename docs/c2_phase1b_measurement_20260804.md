# c2 Phase-1b — E-A blast radius + the deciding measurement (2026-08-04)

**Branch `c2-phase1b-EA-measurement`. NOT merged, NOT pushed, NOT deployed.**
**No product code was modified — and none needed to be** (see §3.0). The shipped index
`data/dailymed/label_docs.json` + `label_emb.npy` is **byte-untouched**; `git status data/` is clean.

Corrections to the Phase-1 report are in [`c2_dailymed_probe_20260804.md`](c2_dailymed_probe_20260804.md),
marked in place and dated. Tagging discipline (`CONFIRMED` / `INFERRED`) carried over from Phase 1.

---

## 🔴 THE ANSWER, FIRST

> **Does E-A remove the wrong-drug citation? NO — on 5 of 5 queries. `CONFIRMED`, N=3 per arm.**
>
> The wrong-drug citation **persisted in every case**, and on one (`cimetidine`) E-A made it **worse**
> (0/3 → 3/3). E-A **is not a substitute for E-B**, and the load-bearing claim in the Phase-1 E table —
> *"neither is a superset of the other"* — survives, but for a **different and stronger reason than
> stated**: it is not that they fix different halves. It is that **E-A does not reliably fix its own
> half.**
>
> **E-B's cost is therefore NOT avoidable by doing E-A instead.**

The baton's predicted defeat mechanism is **exactly what happened**: *"E-A hands `aspirin` a WARNINGS
document while the gate query is `aspirin contraindications`. Vocabulary may not match. Coverage ≠
retrieval."* **Confirmed.**

---

## Part 2 — E-A's true blast radius `CONFIRMED` (offline, 1036 pinned setids)

**Method:** one network pass over the **pinned** reference setids from the shipped corpus, re-parsed with
the builder's own `_section_docs_from_spl` and its `SECTIONS` constant patched to add `34071-1`.
**No `--resolve`. No re-selection.**

⚠️ **Rule 18 — coverage was NOT 100%.** `1036 / 1038` setids parsed (99.8%). **11 initially failed**
(clustered at the alphabetical tail — connection exhaustion, not per-label faults); a bounded retry
recovered 9. **2 remain unrecoverable**: `TOLTERODINE TARTRATE` (`d7274947…`) and `ZOLPIDEM TARTRATE`
(`404c858c…`). All figures below are over 1036, not 1038.

### How many labels carry `34071-1`, and how much text

| metric | value |
|---|---|
| labels carrying `34071-1` | **381 / 1036 (36.8 %)** |
| chars — min / median / p90 / max | 8 / **1 318** / 7 087 / 20 186 |
| **total chars** | **985 163** |

```
        0-249   66  ███████
      250-499   41  ████
      500-999   60  ██████
    1000-1999   70  ███████
    2000-3999   59  ██████
    4000-9999   68  ███████
       10000+   17  ██
```

**➡️ The Phase-1 E table's "~120 docs" was wrong by ~3×. The real number is 381 documents / 985 163
chars** — `+8.3 %` on the 4 608-doc corpus (→ 4 989). Corrected in place in the Phase-1 report.

### 🔴 THE INDEPENDENT FINDING — this is overwhelmingly an **Rx** problem, not an OTC one

| doctype | labels | carrying `34071-1` | chars recovered |
|---|---|---|---|
| **Rx `34391-3`** | 908 | **264 (29.1 %)** | **914 222** |
| OTC `34390-5` | 113 | 107 (94.7 %) | 66 480 |
| *other doctypes* | 15 | 10 | ~4 461 |

> **264 PRESCRIPTION labels are silently dropping their warnings section TODAY — 914 222 characters,
> 93 % of everything E-A would recover.** Median 2 105 chars, max 20 186.
>
> **E-A is not "index the consumer Drug-Facts warnings". It is 93 % a fix for legacy-format PRESCRIPTION
> labels whose warnings sit under the pre-PLR code.** This is a defect **independent of c2** and it
> stands whether or not c2 ever ships. Draft TECH_DEBT entry in §7.

### Moieties gaining their first safety section

| | |
|---|---|
| moieties with **zero** whitelisted safety sections today | **128** |
| …would gain their first via `34071-1` | **118 (92.2 %)** |
| …still zero after E-A | **10** |

### ⚠️ Bonus: the discriminator is **98.6 % corpus-wide, not 100 %**

Phase 1 measured 48/48 resolving to `34391-3`/`34390-5` on a 6-moiety sample and flagged that a build
must re-validate corpus-wide. **Now measured: 1021 / 1036 (98.6 %).** The residual **15 pinned reference
labels are neither human Rx nor human OTC labels** — doctypes `58476-3` (5), `50578-4` (4), `50577-6`
(4), `50575-0` (1), `60683-0` (1), on moieties like CHOLECALCIFEROL, FERROUS GLUCONATE, LACTOBACILLUS
RHAMNOSUS, ISPAGHULA HUSK, LEVAMISOLE, OXYTETRACYCLINE.
⚠️ **I am not naming those LOINC document types** — that is regulatory classification and I will not
best-guess it (CLAUDE.md). **The recordable fact is that 15 pinned references are not human drug labels
at all**, which is a corpus-quality observation independent of c2.

### ⚠️ Snapshot staleness, surfaced incidentally

Re-parsing the **same pinned setids** and diffing against the shipped corpus:

| | |
|---|---|
| shipped-only `source_id`s (section vanished upstream) | **11** |
| new-only `source_id`s | 0 |
| same `source_id`, **content differs** | **30** |

**DailyMed has changed ≥30 sections since the pinned snapshot.** Independent of c2; same family as the
recorded TFDA snapshot-staleness item. **Deliberately EXCLUDED from the Part-3 arms** (see §3.0) so it
cannot contaminate the comparison.

---

## Part 3 — the deciding measurement

### 3.0 Protocol — and why no product-code change was needed

- **Branch** `c2-phase1b-EA-measurement`. No merge, no push, no deploy.
- **Scratch index** at `tests/results/c2_ea_index/`. The shipped index is never opened for writing.
  `DailyMedCorpusStore.__init__` **already accepts `corpus_path` / `emb_path`** (`vector_store.py:209`),
  so the treatment store is injected by constructing it with scratch paths and assigning the module
  singleton. **No product code modified — the baton's STOP condition was not triggered.**
- **The arms differ by exactly one thing.** TREATMENT = **shipped docs verbatim + their shipped
  embeddings** ⧺ **the 381 new `34071-1` docs only**. Existing rows are neither re-parsed nor
  re-embedded, so the 30 drifted sections above are **held constant across both arms by construction**.
- **Embedding cost actually incurred: 381 rows, ~246 290 tokens, `text-embedding-3-small` ≈ $0.005.**
  Embedded with the builder's own `embed_documents()` for parity.
- **Revert:** nothing to revert. `git diff -- api/ components/ utils/ pages/ scripts/` → **empty**;
  `git status data/` → **clean**. Verified after the run.

### 3.1 ⚠️ A measurement bug I caught and corrected — do not read the in-run log

My harness's live `own_drug` flag matched **text**, and the **Aceclofenac** contraindications section
literally contains the words *"acetylsalicylic acid"*. So the aceclofenac document **false-positived as
an aspirin document**, and the in-run console output reported `own-CITED 3/3` for control aspirin —
which is **wrong**.

**All numbers below are re-derived offline by `setid → moiety` (exact identity), not text.** The raw
`source_id`s were captured, so no re-run was needed. *(This is the same trap the baton names in Part 3:
on-drug is necessary, not sufficient — it caught my own instrument first.)*

### 3.2 Results, N=3 per arm, re-classified by exact moiety

| case | arm | own-drug DailyMed doc **in pool** | own-drug **CITED** | **WRONG drug CITED** | own `34071-1` cited |
|---|---|---|---|---|---|
| **aspirin** | control | 0/3 | 0/3 | **3/3** | 0/3 |
| | **E-A** | **0/3** | **0/3** | **3/3** | 0/3 |
| **ibuprofen** | control | 0/3 | 0/3 | **3/3** | 0/3 |
| | **E-A** | **3/3** ✅ | **3/3** ✅ | **3/3** ❌ | **3/3** |
| **naproxen** | control | 0/3 | 0/3 | **3/3** | 0/3 |
| | **E-A** | **0/3** | **0/3** | **3/3** | 0/3 |
| **omeprazole** | control | 0/3 | 0/3 | **3/3** | 0/3 |
| | **E-A** | **3/3** ✅ | **3/3** ✅ | **3/3** ❌ | **3/3** |
| **cimetidine** | control | 0/3 | 0/3 | **0/3** | 0/3 |
| | **E-A** | 0/3 | 0/3 | **3/3** 🔴 **WORSE** | 0/3 |

**Wrong-drug identities cited** (`CONFIRMED`, by moiety):

| case | control | E-A |
|---|---|---|
| aspirin | ACECLOFENAC ×3 | ACECLOFENAC ×3, MEFENAMIC ACID ×1 |
| ibuprofen | PIROXICAM ×2, IBUPROFEN LYSINE ×1, MEFENAMIC ACID ×1 | PIROXICAM ×1, IBUPROFEN LYSINE ×3, MEFENAMIC ACID ×1, **METHOXSALEN ×3** |
| naproxen | NABUMETONE ×3 | NABUMETONE ×3 |
| omeprazole | PANTOPRAZOLE ×5, ESOMEPRAZOLE ×2 | ESOMEPRAZOLE ×3, PANTOPRAZOLE ×3 |
| cimetidine | *(none)* | **COBIMETINIB ×3, MEXILETINE ×1, METFORMIN ×1** |

### 3.3 Per-query verdict and mechanism

| case | E-A removes the wrong-drug citation? | mechanism `CONFIRMED` |
|---|---|---|
| **aspirin** | **NO** | **Vocabulary mismatch** — exactly the predicted failure. VAZALORE's `34071-1` **is in the index** (954 chars, contains "reye"), but the pool contains only *Mefenamic acid — **Contraindications***, a PubMed doc, and *Aceclofenac — **Contraindications***. The query says **contraindications**; aspirin's only safety doc is a **Warnings** section. **Store probe: 0 hits above `min_score=0.6` for the whole DailyMed store — aspirin's own doc never clears threshold.** |
| **ibuprofen** | **NO** (but real coverage gain) | Own doc retrieved and **cited at rank [1]** (*ADVIL — Warnings*). **Store probe: own `34071-1` at rank 0.** But it **took a slot rather than displacing** the wrong ones — Piroxicam, Ibuprofen lysine, Mefenamic acid **and a NEW intrusion, METHOXSALEN** (a psoralen, unrelated) all still cited. |
| **naproxen** | **NO** | Own doc never enters. **Store probe: 0 hits.** Same vocabulary miss. |
| **omeprazole** | **NO** (but real coverage gain) | Own doc retrieved and cited (**store probe: rank 0**), yet PANTOPRAZOLE + ESOMEPRAZOLE persist. |
| **cimetidine** | **NO — REGRESSION** 🔴 | Control cited **no** wrong drug; E-A cites **three** (COBIMETINIB, MEXILETINE, METFORMIN). Own doc never enters (**store probe: 0 hits**). **Adding 381 documents perturbed the pool and pulled in wrong-drug documents on a query that was previously clean.** |

**Does the retrieved `34071-1` document ANSWER the question asked?** On the 2 successes it is **on-drug
but only partly on-question**: both queries asked about *warnings/contraindications* and received a
**Warnings** section — appropriate for `ibuprofen warnings`, **not** an answer to a contraindications
question. **On-drug is necessary, not sufficient — and on aspirin the distinction is decisive**, because
"contraindications" is precisely the vocabulary that pulls the *sibling* NSAIDs' 34070-3 sections in.

### 3.4 ⚠️ Limits of this measurement

- **N=3 per arm on 5 queries.** Rewrite nondeterminism is established in this repo; **cimetidine's 0→3
  regression on N=3 is a signal, not a quantity.** It must not be reported as an effect size.
- The `shadow_sink` captures the **post-rerank** pool, i.e. **after** the relevance filter. Absence there
  cannot by itself separate "never retrieved" from "filter-dropped" — **the store probe was added
  precisely to break that tie**, and it agrees with the pool result on all five.
- The store probe queries the **raw** question; the retriever uses **rewritten** queries (K-union). The
  two agree here, but they are not the same input.

---

## Part 4 — content stratification `CONFIRMED`

**Method:** deterministic lexical markers — 8 Drug-Facts consumer phrases (*"ask a doctor"*, *"keep out
of reach of children"*, *"when using this product"*…) vs 14 professional-prose terms (*"clinical
trials"*, *"hepatic impairment"*, *"pharmacokinetic"*, *"incidence"*, *"placebo"*…). **Whole population
classified, n = 381 — not a sample.**

| class | n | share | median chars |
|---|---|---|---|
| AMBIGUOUS / thin | 250 | 65.6 % | 1 104 |
| LAY-advisory | 70 | 18.4 % | 785 |
| CLINICAL | 61 | 16.0 % | **7 771** |

**The doctype split is the real finding, and it is cleanly separated at the extremes:**

| doctype | n | LAY-advisory | CLINICAL |
|---|---|---|---|
| **Rx** | 264 | **1 (0 %)** | **60 (23 %)** |
| **OTC** | 107 | **69 (64 %)** | **0 (0 %)** |

**➡️ The lay-consumer-language concern applies almost entirely to the OTC 107, and essentially not at
all to the Rx 264** — which are 93 % of the recovered text.

⚠️ **Method limit, stated:** the 65.6 % AMBIGUOUS bucket is **a property of my classifier, not of the
text**. Sampling shows clearly-clinical prose landing there — e.g. *"WARNINGS Administration of folic
acid alone is improper therapy for pernicious anemia…"* (Rx) and *"WARNINGS Fatal complications,
including pulmonary and cerebral emboli have occurred with inappropriate intravenous administration of
CARAFATE…"* (Rx) — because they miss the 3-marker CLINICAL threshold. **The classifier under-detects
clinical content, so the Rx CLINICAL share is a floor, not an estimate.** What it does reliably: **0 of
264 Rx docs classified LAY; 0 of 107 OTC docs classified CLINICAL.**

**Reported, not judged** — whether consumer-grade text is acceptable under a citation chip is a founder
call. The asymmetry already noted holds: yield ranges **8 chars (LORATADINE) to 20 186**, and
**cimetidine gains more from E-A (Tagamet 1 206) than from E-B (Rx contra 107, no warnings section)** —
still the only one of the six where that is true.

---

## Part 5 — cross-validation against the c1 record `CONFIRMED`

The c1 report recorded **35 COMPLEMENTARY** local records, **14 of them "OTC Drug-Facts Warnings-only"**.
Reproduced exactly (14/14), then checked against the E-A index:

| | count |
|---|---|
| **recoverable from DailyMed via E-A** | **8 / 14** |
| absent from DailyMed entirely | 6 / 14 |
| in DailyMed but no `34071-1` | 0 / 14 |

**It is the same content, not merely similar** — `IBUPROFEN` matches at **exactly 2 615 chars** in both
the local `full_label` and the DailyMed `34071-1` section; `CETIRIZINE` 900 vs 901; `LOPERAMIDE` 990 vs
996. The 6 absent are Temazepam, Polyethylene Glycol, Docusate, Vitamin B12, Omega-3, Vitamin D.

**➡️ Recorded plainly: part of what c1 removed IS retrievable from DailyMed itself.**
**This does NOT reopen c1** — the local documents were empty stubs (≤20 chars indexed) regardless of what
their unread `full_label` held. c1 removed *stubs*; this is about *where the real text lives*.
⚠️ And per Part 3, **being in the index is not the same as being retrieved** — aspirin is in all three
sets (c1 complementary, E-A recoverable, still not retrieved).

---

## Part 6 — `top_k` sweep: **DECLINED, and why**

**Not folded in.** It is not free here. Part 3's harness pins `max_results=5`; a 5-vs-6-vs-7 sweep needs
**additional runs per arm** (≥3 each for nondeterminism → 18+ more retrievals), and interpreting it
against a treatment index that adds 381 competing documents would **confound the `top_k` question with
the E-A question** — two variables, one measurement. **Per the baton: scope discipline beats a bonus
measurement. Declined, not forgotten** — the BACKLOG `[P2] top_k=5` entry is unchanged and still
recommends its own run.

---

## §7 — Proposed TECH_DEBT entry (DRAFT — **not filed**; founder files it)

> - **[P2 · retrieval-corpus coverage — measured 2026-08-04, independent of c2] The DailyMed corpus
>   silently drops the warnings section of 264 PRESCRIPTION labels because LOINC `34071-1` is not in the
>   builder's `SECTIONS` list — 914 222 characters of prescriber-facing safety text**
>   - **What:** `scripts/build_dailymed_label_corpus.py:77-84` whitelists `34073-7 · 34066-1 · 34070-3 ·
>     43685-7 · 34067-9 · 34068-7`. **`34071-1` — the PRE-PLR "WARNINGS" code — is absent.** It is not an
>     OTC-only code: it is what **legacy-format prescription labels** (never converted to the Physician
>     Labeling Rule format) use for warnings, while `43685-7` is the PLR-era "WARNINGS AND PRECAUTIONS".
>   - **Measured** (`CONFIRMED`, 1036/1038 pinned setids re-parsed, no re-selection): **381 labels
>     (36.8 %) carry `34071-1`, totalling 985 163 chars. Of those, 264 are PRESCRIPTION labels carrying
>     914 222 chars — 93 % of the total** (median 2 105, max 20 186). Only 107 are OTC labels (66 480
>     chars).
>   - **Impact:** for those 264 Rx labels the corpus holds interactions/contraindications/boxed but
>     **not warnings**, so a warnings-shaped question can retrieve a *sibling drug's* warnings while the
>     queried drug's own warnings sit unindexed. **118 of the 128 moieties with zero safety sections
>     would gain their first** from this code alone.
>   - **Why it belongs to the instrument-blind class:** the corpus's own coverage metric counts
>     *whitelisted* sections, so a label whose only warnings live in `34071-1` is scored as
>     "no safety section" — **the measurement inherits the omission it should expose.** This is how the
>     "120/128 OTC-shaped" figure came to imply an OTC problem when 93 % of the missing text is Rx.
>     Same shape as the retracted Phase-1 "doctype predicts safety presence" claim, which was circular
>     for the same reason.
>   - **⚠️ Fixing it is NOT free and is NOT a c2 substitute:** adding the code is +381 docs (+8.3 %) into
>     a `top_k=5` budget already measured tight, and **measurement shows it does not remove the
>     wrong-drug citation on any of 5 queries and regressed one** (`docs/c2_phase1b_measurement_20260804.md`
>     Part 3). Record the coverage defect; **sequence the fix with c2, not ahead of it.**
>   - **Surfaced:** 2026-08-04. **Evidence:** `docs/c2_phase1b_measurement_20260804.md` Part 2.

---

## Rule 18 — what this session did NOT establish

- **2 of 1038 pinned setids never parsed** (TOLTERODINE TARTRATE, ZOLPIDEM TARTRATE). All Part-2 figures
  are over **1036**.
- **N=3 × 5 queries.** Enough to answer "does E-A remove the wrong-drug citation" (a clean NO, 5/5, with
  a mechanism confirmed by two independent probes). **Not** enough to quantify the cimetidine regression
  or to rank E-A's coverage benefit.
- **E-B was NOT built or measured.** Its blast radius (how many of 1038 moieties change reference label)
  remains **UNMEASURED** — unchanged from Phase 1, and it needs a dry-run re-resolve.
- **E-C (E-A + E-B together) was not measured.** Part 3 tests E-A alone; it does not license any claim
  about the combination.
- **The 15 non-human-drug doctypes were counted, not identified.** I declined to name the LOINC document
  types rather than guess in regulatory territory.
- **No answer-quality judgement.** Retrieval and citation identity only — no §2.7, danger-path, canary or
  human-eye gate, none of which applies to a branch measurement.
