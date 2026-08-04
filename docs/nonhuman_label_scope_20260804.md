# Non-human reference labels in the DailyMed retrieval corpus — scope, risk, costed options (2026-08-04)

**READ-ONLY measurement + costed options. NOTHING BUILT, NOTHING SHIPPED, NO EXCLUSION APPLIED.**
No rebuild, no re-embed, no `--resolve`. Shipped index byte-intact. Branch only; not pushed.
**Independent of the c2 sequencing decision** — every option here stands whichever c2 option is chosen,
or none.

Tags: **`CONFIRMED`** · **`INFERRED`** · **`REFUTED`**.

---

## 1.1 Scope — **the 15 is the TOTAL, not a floor** `CONFIRMED`

The original 15 were found by SPL **document type** (neither `34391-3` nor `34390-5`). That cannot catch
a veterinary or non-drug product carrying a *human* doctype. So all **1036** pinned references were
swept by **title + indications/dosage text** for species, animal dosage forms, and supplement markers.

> ### ➡️ **0 additional non-human products were found outside the original 15.**
> **Stated plainly because it is a real and reassuring result:** the doctype signal appears to be
> *sufficient* on this corpus, not merely a partial catch. The exposure is bounded at 15.

### ⚠️ How that number was reached — a first pass was wrong and is recorded

The first sweep flagged **69** labels and "2 outside the 15 with strong veterinary evidence". **Both
were false positives**, and the markers that produced them are recorded so they are not re-added:

| rejected marker | why it is wrong |
|---|---|
| `bolus` | **standard HUMAN IV dosing** — matched 40+ oncology/anaesthesia labels (Doxorubicin, Enoxaparin, Busulfan…) |
| `drinking water` | ordinary human "take with water" prose (Xofluza, Epidiolex, Tivicay PD) |
| `premix` | **LEVAQUIN / moxifloxacin "premix" = a premixed IV bag**, not medicated feed |

With only unambiguous markers (`for animal use only`, `not for human use`, `licensed veterinarian`,
`drench`, `medicated feed`, `withdrawal period`, species-in-use-context), the flag count drops to **3 —
all inside the original 15**.

### The three buckets, kept separate

#### (a) VETERINARY / ANIMAL — the safety risk · **7 labels**

| moiety key | reference label | indexed sections | **whitelisted safety?** |
|---|---|---|---|
| **CHLORTETRACYCLINE HCL** | **CLTC 100 MR** (medicated feed) | 34067-9, 34068-7, **43685-7** | **🔴 YES — citable** |
| **DISODIUM CLODRONATE** | **OSPHOS** (equine) | 34068-7, **34070-3** | **🔴 YES — citable** |
| LEVAMISOLE | LevaMed Soluble **Drench** Powder | 34067-9, 34068-7 | no |
| TRIPTORELIN ACETATE | OvuGel (swine oestrus) | 34067-9, 34068-7 | no |
| ESTRIOL | Incurin (canine) | 34068-7 | no |
| OXYTETRACYCLINE | Tetroxy HCA | 34068-7 | no |
| POTASSIUM GLUCONATE | RenaKare (feline/canine) | 34067-9, 34068-7 | no |

#### (b) DIETARY SUPPLEMENT / NON-DRUG — lower risk · **5 labels** (all doctype `58476-3`)

CHOLECALCIFEROL (D-Vite Pediatric) · FERROUS GLUCONATE · ISPAGHULA HUSK (Super Fiber) ·
LACTOBACILLUS RHAMNOSUS (Florasync) · POLYSACCHARIDE IRON COMPLEX (IFEREX 150).
**All carry only `34068-7` dosage — none is citable as a safety source.**
The finding here is not patient risk; it is that **reference selection is landing on supplements**.

#### (c) LEGITIMATE HUMAN PRODUCT with an unusual doctype · **1 label**

**`GLOBULIN` → Gamunex-C (Immune Globulin (Human))**, doctype `60683-0`. Its content is **entirely
legitimate human prescribing information** — verified: boxed warning on thrombosis/renal failure,
contraindications on IgA deficiency, standard IVIG interactions. **This is NOT part of the veterinary
concern and must not be counted with (a).**

> ⚠️ **A separate defect, recorded not merged:** the moiety key **`GLOBULIN`** is far broader than the
> specific IVIG product it resolved to. Any question about *any* globulin grounds on Gamunex-C. **That is
> the D4 asymmetric-coverage / over-broad-key family** (`docs/c2_dailymed_probe_20260804.md` D4), **not
> this one.**

*(The remaining 2 of 15 — HYDROGEN PEROXIDE SOLUTION, LACTIC ACID — are topical/antiseptic products with
`50577-6`; neither is citable as safety. Counted in the 15, not in (a)/(b)/(c) above.)*

### 🔴 What the two citable veterinary sections actually say

**`CHLORTETRACYCLINE HCL` → CLTC 100 MR — "Warnings and Precautions" (`43685-7`), CITABLE:**

> *"**CAUTION:** Federal law restricts medicated feed containing this **veterinary feed directive (VFD)**
> drug to use by or on the order of a licensed veterinarian. **For use in manufacturing medicated animal
> feeds only.** … **Human exposure should therefore be minimized** by observing the general industry
> standards for occupational health and safety."*

**This is not merely the wrong species — it is an OCCUPATIONAL-HYGIENE notice for feed-mill workers,
about minimising human exposure to the product.** Served under a "Warnings and Precautions" chip on a
clinical chlortetracycline question, it reads as drug safety information and is nothing of the kind.

**`DISODIUM CLODRONATE` → OSPHOS — "Contraindications" (`34070-3`), CITABLE:**

> *"**Horses** with hypersensitivity to clodronate disodium should not receive OSPHOS. **Do not use in
> horses** with impaired renal function or with a history of renal disease."*

Self-evidently wrong to an attentive reader — but it is a **Contraindications** section for the queried
moiety, exactly the shape a safety query retrieves.

### Why this outranks the recorded wrong-object family

| defect | what the cited document is |
|---|---|
| combination-product label (22/190) | a **human** drug **containing** the queried moiety |
| wrong-drug citation (aspirin → Aceclofenac) | a **human** drug, **neighbouring** class, clinically related content |
| **non-human label (this)** | **not a human drug at all** — dosing and contraindications written for horses, swine, or feed manufacture |

---

## 1.2 Has any of them ever been retrieved? **No observation exists — and here is exactly what was checked** `CONFIRMED`

**203 persisted artifacts scanned** (`tests/results/*.json`, `tests/probes/**/*.json`): golden runs with
`pool_identity`, the pool-size harvest, pair-aware M1/M3, K-union gates, severity / OTC-single-drug /
discriminator probes, the c2 A/B and variance runs, and the citation-URL audit.

> **0 occurrences of any of the 15 setids.**

⚠️ **This is "no observation", NOT "never retrieved".** Absence of evidence is not evidence of absence,
and the search space is a set of probes aimed at other questions — none targeted these moieties.

⚠️ **Rule 18 — what could NOT be checked:** the **production database's stored `/q/` share rows and
`ExplorePage` citations** live in Postgres, not in any file in this repo. **No offline artifact covers
them.** If a real user has ever been served one of these, it would be recorded there and this sweep
cannot see it.

---

## 1.3 Costed exclusion options — **the re-embed question is the whole cost question**

### The mechanism that decides it `CONFIRMED` from code

`DailyMedCorpusStore.search()` (`api/database/vector_store.py:79-99`) computes
`scores = self.embeddings @ query_emb` and then reads `meta = self.documents[idx]` — **documents and
embedding rows are aligned purely by ROW INDEX.** `_load_compact` (`:222-235`) simply loads both and
asserts equal length.

> ### ➡️ **YES — two of the three options avoid a re-embed entirely.** Deleting a document is a
> **parallel row deletion** on `label_docs.json` and `label_emb.npy`. The surviving vectors are
> unchanged, so **no embedding call is needed.** **27 of 4608 documents (0.59%) are affected.**

| option | where | re-embed? | cost | blast radius / notes |
|---|---|---|---|---|
| **(a) BUILD-TIME** — skip non-human doctypes during resolution, **and re-select a human label** | `_resolve_moiety` / `_resolve_once` | **YES — full** | `--resolve` ≈25 min network **+ full re-embed of 4608+ docs** | **The only option that can FILL the hole** rather than leave it. Also the only one that would pick up the 30 drifted sections. Highest cost. |
| **(b) INDEX-TIME** — filter the shipped artifact: drop the 27 rows from docs **and** the matching rows from the `.npy` | a small script over the two files | **NO** | minutes, **$0** | ⚠️ Must be atomic — a docs/emb length mismatch makes `_load_compact` **disable the entire DailyMed source** (`:231-234`). Verify row counts after. Leaves the moieties empty. |
| **(c) RETRIEVAL-TIME** — exclude by setid/moiety at query time | `_search_dailymed` in `api/rag/retriever.py` | **NO** | one code change + an exclusion set | **Corpus unchanged**, instantly reversible, **flag-gateable**. But the corpus still *contains* them, so any other consumer (a future surface, a share re-render) still sees them. |

### ⚠️ Every option leaves a coverage hole — measured, not assumed

> **All 15 moieties have exactly ONE reference setid. Excluding it leaves them with ZERO documents.**
> `CONFIRMED`: 15 moieties touched, **15 drop to zero**, 0 retain another setid.

So **(b)** and **(c)** are *deletions*, not *corrections*: chlortetracycline, clodronate, levamisole,
estriol, oxytetracycline, potassium gluconate, triptorelin acetate and the 5 supplements would have **no
DailyMed grounding at all**. Only **(a)** can attempt to re-select a human label — **and it may find
none**: several of these moieties are predominantly veterinary in the US market, which is plausibly *why*
the resolver landed on a veterinary label in the first place. **That is a hypothesis, not measured.**

**Is zero better than wrong?** For the 2 citable-safety entries, plausibly yes. For the other 13 —
which contribute only indications/dosage — it is a genuine trade. **Founder's call; not made here.**

### 🔴 Gate requirement, unchanged

**All three options change what is retrieved ⇒ 🔴.** Any of them needs its own **§2.7 + section-aware
danger-path re-gate + canary + prod human-eye gate** before shipping, with human-eye rows naming the
**expected drug** per the 4th ops SOP line. **Nothing here is built or ready to ship.**

---

## 1.4 DRAFT TECH_DEBT entry — **[P1] PROPOSED, priority not assumed. The founder files it.**

> - **[P1 · PROPOSED — medical-safety / wrong-object — measured 2026-08-04] Two VETERINARY label safety
>   sections are in the production retrieval corpus and are CITABLE on clinical questions**
>   - **What:** of 1036 pinned DailyMed reference labels, **15 are not human drug labels**; **7 are
>     veterinary** and **2 of those carry whitelisted SAFETY sections**, i.e. can be cited as a safety
>     source in a Research answer:
>     - **`CHLORTETRACYCLINE HCL` → CLTC 100 MR** (`43685-7` Warnings) — the text is a **veterinary feed
>       directive occupational-hygiene notice**: *"For use in manufacturing medicated animal feeds only …
>       Human exposure should therefore be minimized."*
>     - **`DISODIUM CLODRONATE` → OSPHOS** (`34070-3` Contraindications) — *"**Horses** with
>       hypersensitivity … Do not use in **horses** with impaired renal function."*
>   - **Why [P1] is PROPOSED (severity argument, explicitly relative to the recorded family):** the
>     wrong-object family already contains combination-product labels (22/190) and wrong-drug citations
>     (aspirin → Aceclofenac, 12/12). **This outranks both.** A combination label is a *human* drug
>     containing the queried moiety; a wrong-drug citation is a *human* drug in a neighbouring class
>     whose content is often class-true. **A veterinary label is not a human drug at all** — its dosing,
>     contraindications and warnings are written for horses, swine, or feed manufacture. It is the first
>     member of the family where the cited document has **no valid reading** for a human patient.
>   - **Scope is BOUNDED and verified:** a title/dosage-form/species sweep of all 1036 references found
>     **0 additional non-human products outside these 15** — the doctype signal is sufficient here.
>     ⚠️ A first sweep pass produced false positives on `bolus` / `premix` / `drinking water`; those
>     markers are recorded as rejected.
>   - **Exposure is UNQUANTIFIED, not zero:** **0 occurrences across 203 persisted measurement
>     artifacts**, but **the prod `/q/` and `/explore` stored citations were NOT checked** (Postgres, no
>     offline artifact). No claim is made that a user has never been served one.
>   - **✅ Cheap to fix, and cheaper than expected:** documents and embeddings align by **row index**, so
>     an index-time or retrieval-time exclusion needs **NO re-embed** — 27 of 4608 documents (0.59%).
>     ⚠️ **But all 15 moieties have exactly one reference setid, so exclusion leaves them with ZERO
>     documents**; only a build-time re-resolve could attempt to re-select a human label, and may find
>     none. **Three costed options in `docs/nonhuman_label_scope_20260804.md` §1.3.**
>   - **🔴 Any fix changes what is retrieved ⇒ own §2.7 + danger-path re-gate + canary + prod human-eye
>     gate.** **Independent of the c2 sequencing decision** — it stands whichever c2 option is chosen, or
>     none.
>   - **Surfaced:** 2026-08-04. **Evidence:** `docs/nonhuman_label_scope_20260804.md`;
>     `docs/c2_phase1c_20260804.md` Part 2.

---

## Rule 18 — what this did NOT establish

- **Whether any of the 15 has ever been served to a real user.** The prod DB was not queried.
- **Whether a human reference label even exists** for the 7 veterinary moieties — the re-selection
  question under option (a) is **unmeasured**, and the "predominantly veterinary in the US" explanation
  is a hypothesis.
- The sweep is **title + indications/dosage text**. A veterinary product whose title, indications and
  dosage are all species-neutral would not be caught. **0-outside-the-15 is a strong result on this
  method, not a proof.**
- No retrieval measurement was run for these moieties — no query was issued to see whether they *can* be
  surfaced in practice.
