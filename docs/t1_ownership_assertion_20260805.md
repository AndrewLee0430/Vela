# T1 — the ownership assertion: making wrong-drug citation visible to the gates

**Date:** 2026-08-05 · **Baton:** T1 Phase 1 · **Scope:** test/harness layer only — no `api/`, no
`data/`, no index rebuild, no network · **Status:** instrument built and self-tested; **not wired to
any gate** (see §6)

This adds a **measurement instrument**. It does **not** fix the wrong-drug defect, and it is not the
wrong-drug filter (STATE open-item #2), which remains unbuilt.

---

## 1. What was built

| file | role |
|---|---|
| `tests/probes/wrongdrug/owner_assertion.py` | the pure module — ownership join + six outcomes |
| `tests/probes/wrongdrug/fixtures.json` | 3 fixtures, with the competing owner-set readings recorded |
| `tests/probes/wrongdrug/replay_probe.py` | self-test, fixture replay, §2.7 calibration |
| `tests/probes/wrongdrug/wrongdrug_replay.json` | committed output |

**Ownership is resolved only by the corpus join** — `source_id` → `setid` →
`data/dailymed/label_docs.json` → `moiety`. Verified exact for all 4608 docs. There is no text
matching in the module body; the self-test asserts this structurally.

**The six outcomes never collapse:** `correct_owner` · `wrong_owner_cited` ·
`no_right_owner_in_corpus` · `out_of_scope_class_query` · `unclassified` · `unresolved_source_id`.
All six print in every tally, including zeros.

### Instrument self-test — 5/5

The decisive check: the committed c2 evidence records `own_drug: true` for the ACECLOFENAC document
on an aspirin query — a mention-based false positive, because that label legitimately contains the
words *"acetylsalicylic acid"*. The ownership join returns `wrong_owner_cited` on the same document.
**The instrument is asserted to contradict its predecessor on the project's worst recorded
wrong-drug citation.** If that check ever flips, the module has regressed to mention-based logic.

---

## 2. 🔴 CORRECTION TO THE RECORD — aspirin is a RANKING failure, not a coverage gap

**`BACKLOG.md` → the c2 entry's "Why now" bullet (was `BACKLOG.md:860`) records:** *"In 6 of 6 adjudicated cases the queried drug's own reference label
has no safety section and the wrongly-cited sibling's does."*
**`docs/local_corpus_deprecation_c1_build.md:512`** records aspirin's own safety sections as `NONE`.

**For aspirin this is false at the corpus level.** The corpus keys aspirin under **two** moiety
strings, because the corpus key is the TFDA backbone `drug_name` verbatim
(`scripts/build_dailymed_label_corpus.py:99-105`):

| moiety key | reference label | whitelisted safety sections |
|---|---|---|
| `ASPIRIN` | VAZALORE (OTC) | **NONE** |
| `ACETYLSALICYLIC ACID` | **DURLAZA (Rx)** | **34070-3, 34073-7, 43685-7** |

Verified at the index level, not inferred:

- `DailyMed:4c2a1403-3862-1efd-0a91-444989222b37#34070-3` — *DURLAZA (Acetylsalicylic Acid) —
  Contraindications*, **375 chars of real content**
- **row 57** of `data/dailymed/label_docs.json`; `label_emb.npy` is `(4608, 1536)`, **row-aligned**;
  that row's embedding norm is **0.9995**, not zero

**An owned aspirin Contraindications document was present and embedded in the shipped index that
cited Aceclofenac instead.** So the flagship fixture is `wrong_owner_cited` — a **ranking** failure —
where the record says coverage gap. Opposite bucket, opposite fix.

**Why the c1 adjudication got it wrong:** it resolved aspirin to the `ASPIRIN` key, found VAZALORE
with no safety sections, and stopped. It never looked at the synonym key. Acetylsalicylic acid *is*
aspirin — same substance, not a class sibling — so I treat this reading as settled rather than as a
founder question; the alternate reading is recorded in `fixtures.json` only to show what the
adjudication did.

### What I did NOT verify

**Whether DURLAZA's section clears the store's `min_score` threshold on that query.** That needs a
live embedding call, which this baton's no-network scope forbids. `docs/c2_phase1b_measurement_
20260804.md:214` records *"0 hits above min_score=0.6 for the whole DailyMed store"* on the aspirin
query — but that probe was looking for VAZALORE's `34071-1`, not DURLAZA's `34070-3`, so it does not
settle the question either way. **UNKNOWN, and it is the next thing worth measuring.**

This distinction is exactly why the module decides coverage from the **corpus**, never from the
**pool** — conflating "no owned doc exists" with "no owned doc was retrieved" is the error above.

### Scope of the two-key split — NOT measured

1038 moiety keys; **128 (12.3%) have no whitelisted safety section**. I attempted an automated sweep
for how many of those are shadowed by a synonym key that *does* — it returned mostly false pairs
(`GLYCERIN`→`NITROGLYCERIN`, `LORATADINE`→`DESLORATADINE`, `PSEUDOEPHEDRINE`→`EPHEDRINE`,
`SALICYLIC ACID`→`ACETYLSALICYLIC ACID` are all different substances) because it was substring-based
— i.e. the same mention-style matching this work exists to reject. **That number is withheld as
untrustworthy.** Only the two hand-verified cases below are reported. A real synonym census needs a
normalised vocabulary (RxNorm ingredient IDs) and is a separate task.

---

## 3. 🔴 FOUNDER DECISION PENDING — is NEOPROFEN an owner for "ibuprofen"?

Ibuprofen has the same two-key structure, but unlike aspirin it is **not** medically unambiguous:

| moiety key | reference label | whitelisted safety sections |
|---|---|---|
| `IBUPROFEN` | ADVIL (OTC) | **NONE** |
| `IBUPROFEN LYSINE` | **NEOPROFEN** | 34070-3, 34073-7, 43685-7 |

Ibuprofen lysine is the same active moiety as a lysine salt — but NEOPROFEN is an **intravenous
neonatal** product for patent ductus arteriosus closure. Whether its warnings legitimately answer an
adult oral ibuprofen question is a **clinical** judgment, not a lexical one, so per CLAUDE.md I am
flagging it rather than guessing.

**It changes the outcome:**

| reading | WD02 outcome |
|---|---|
| strict (`IBUPROFEN` only) | `no_right_owner_in_corpus` — coverage gap |
| salt-inclusive (adds `IBUPROFEN LYSINE`) | `wrong_owner_cited` — ranking failure |

Both are computed and printed. Nothing is silently chosen.

---

## 4. Fixture replay — committed c2 evidence, shipped index (control arm)

| fixture | outcome | detail |
|---|---|---|
| **WD01** aspirin | **`wrong_owner_cited`** | `ACECLOFENAC #34070-3` — **1 distinct identity across 9 recorded runs** (deterministic; reported as one identity, not nine samples) |
| **WD02** ibuprofen | `no_right_owner_in_corpus` (strict) / `wrong_owner_cited` (salt-inclusive) | PIROXICAM, IBUPROFEN LYSINE, MEFENAMIC ACID |
| **WD03** spironolactone | **`unclassified`** | pair query, `out_of_scope_v1` — **never reported as passing** |

The **treatment arm is excluded from the authoritative tally**: it was retrieved against the c2 E-A
scratch index, not the shipped one. The module detected this itself — on WD02 treatment it emitted a
`🔴 CONTRADICTION` because an owned document (`#34071-1`) was cited although the shipped corpus
contains no owned whitelisted safety section. That is the index mismatch showing up as a loud
inconsistency rather than as a quiet wrong number.

---

## 5. CALIBRATION — the assertion changes **nothing** on §2.7, and that is the finding

Replayed against `tests/results/golden_results_20260729_230006.json` (the c1 ship, recorded
**20 PASS / 0 WARN / 0 FAIL**, `gate_valid=true`). Citation identity **was** fully reconstructible —
all 20 cases carry `pool_identity` with `source_id` and `cited_in_answer`.

| outcome | per §2.7 case | per citation |
|---|---|---|
| `correct_owner` | 3 | 6 |
| `wrong_owner_cited` | **0** | **0** |
| `no_right_owner_in_corpus` | 0 | 0 |
| `out_of_scope_class_query` | **14** | 14 |
| `unclassified` | 3 | 3 |
| `unresolved_source_id` | 0 | 0 |

**§2.7 cases whose verdict would flip: 0.**

### This is NOT "the assertion has no discriminating power"

The baton's stop condition was *"if the calibration shows the assertion changes nothing **anywhere**"*.
It does not. On the **fly-215 production human-eye gate** it flips **8/8 → 6/8**: rows 3
(`aspirin contraindications` → sole citation Aceclofenac) and 4 (`ibuprofen warnings` →
`[1] Piroxicam`), both recorded at `docs/local_corpus_deprecation_c1_build.md:402,438` and
`BACKLOG.md` → the `[ops] Pre-gate stale-server SOP` FOURTH SOP LINE (was `BACKLOG.md:945`). So the instrument discriminates. **§2.7 is simply the wrong host for it.**

**Why §2.7 scores zero — the golden set does not contain the query shape that exhibits the defect:**

- **14 of 20 are class-level** queries, excluded by design. Inspected, and the exclusion is not
  hiding defects: R07 cited metoprolol, esmolol, nebivolol, atenolol (all genuine beta-blockers),
  R20 cited perindopril (an ACE inhibitor), R16 salsalate (a salicylate NSAID). All legitimately
  owned.
- **1 is a pair** query (R13).
- **Of the 5 single-drug cases, 3 are correctly owned** (metformin ×2, lithium) and **2 retrieve no
  DailyMed document at all** (R08, R10).

R08 is the sharpest evidence. It is *"the recommended **dose** of aspirin for cardiovascular
prevention"* and pulls **zero** DailyMed docs. The fly-215 gate asked *"aspirin **contraindications**"*
and got Aceclofenac. **Same drug, different question shape, opposite outcome** — the corpus holds
only safety sections, so a dosing question never reaches them.

**Consequence for the gate wiring:** wiring this to §2.7 as it stands adds a check that, on today's
golden set, can never fire. That would be a green light with no discriminating power behind it —
instrument-blind #6 in a new costume. **The BACKLOG entry therefore names the fixture gap as part of
the wiring, not as a follow-up.**

---

## 6. Deferred gate wiring — filed, not done

Per the baton's binding condition, filed as its own BACKLOG entry naming the concrete mechanism: a
post-pass over the `pool_identity` `source_id` capture already present at
`tests/run_golden_tests.py:195-201`. **No wiring was performed.**

---

## 7. Incidental — flagged, not fixed

| # | item |
|---|---|
| 1 | **`BACKLOG.md` cites an untracked, gitignored file as the reusable method** — `tests/results/_pairaware_m1_content_audit.py` exists only on this machine (`tests/results/` is gitignored at `.gitignore:113`). Doc drift, and evidence bearing on the still-open `tests/probes/` convention decision |
| 2 | **`BACKLOG.md` → the c2 entry's "Why now" bullet (was `BACKLOG.md:860`) / `local_corpus_deprecation_c1_build.md:512`** state aspirin has no owned safety section. False at the corpus level (§2). Not edited — the correction is recorded here for the founder to place |
| 3 | **STATE open-item #9** — `vector_store.py:52` `print()`, Rule 4. Confirmed still present at the real path `api/database/vector_store.py`. Out of scope, untouched |
| 4 | **`RetrievedDocument` drops `moiety` and `setid`** at `api/database/vector_store.py:99-119` although the corpus carries both on 4608/4608 docs. Ownership is recoverable only by re-joining the corpus offline. Carrying the fields through would make it available in-process — an `api/` change, out of scope |

---

## 8. What was NOT done (Rule 18)

- **No live retrieval, no network.** Every input is a committed artifact.
- **The `min_score` question is UNKNOWN** (§2) — whether DURLAZA's Contraindications section clears
  the store threshold on the aspirin query was not measured.
- **The synonym-shadowing census is UNMEASURED** (§2) — my automated attempt was unreliable and its
  number is withheld rather than reported.
- **No wrong-drug filter** was built or partially built. **c2 remains parked.**
- **No gate wiring.** No `api/`, `data/`, index or flag changes. No gate cycle run.
