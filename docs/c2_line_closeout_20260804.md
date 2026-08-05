# c2 line — CLOSE-OUT (2026-08-04)

**Docs-only. No measurement, no build, no network, no DB query, no embedding.** Every number here is
cited from a branch report. Branch `c2-phase1b-EA-measurement`; **not pushed, not merged, not deployed.**
**No priority set, no option chosen, no queue reordered.** Every decision below is founder-pending.

**Read this file alone to resume.** The five underlying reports are cited but should not be needed.

---

# 1. WHAT THE LINE ESTABLISHED

## ✅ CONFIRMED

| # | finding | source |
|---|---|---|
| 1 | An Rx label with real safety sections exists for all six c2-i moieties | Phase 1, live, 6/6 |
| 2 | `marketing_category_code` does **not** discriminate Rx/OTC; the SPL **doctype** does — **98.6%** corpus-wide | Phase 1 + 1b |
| 3 | Selection **returns on the first tier with any candidate** — the ANDA tier is never queried once NDA answers | `_resolve_once:313-322` |
| 4 | `34071-1` missing from `SECTIONS` costs **264 prescription labels 914,222 chars** of warnings — **93% an Rx problem, not OTC** | 1b Part 2 |
| 5 | **E-A does not remove the wrong-drug citation — 0 of 5** — 🆕 **and it INTRODUCED one**, see 5b | 1b Part 3 |
| 5b | 🆕 🔴 **E-A INTRODUCED a new wrong-object citation: `UVADEX (Methoxsalen) — Drug Interactions`, a psoralen unrelated to ibuprofen, cited in 3/3 TREATMENT runs and 0/27 control runs.** ⚠️ **E-A did not add that document** — UVADEX `#34073-7` is in the **shipped** corpus already and was never cited in any control run. E-A's +381 rows perturbed ranking enough to surface it. **So E-A is not merely ineffective (0/5); on this query it made the defect worse.** | `c2_ab_retrieval.json`, N=3/arm, 1 query — filed 2026-08-05 |
| 6 | 🔴 **Supplying a correct document does not displace an incorrect one** — 2 cases, wrong drug still cited 3/3 | 1c §0 |
| 7 | `aspirin → ACECLOFENAC` is **deterministic: 12/12, two index configs, zero variance** | 1c Part 1 |
| 8 | The corpus has **no refresh mechanism** — `monthly_re_pull` is prose, `db_published_date` is **null**, no CI | 1c Part 5.3 |
| 9 | **15 non-human references**, scope **bounded** (0 found outside); **2 citable as safety** | non-human scope |
| 10 | **E-B blast radius: 45/1038 (4.3%)** — 42 gain a first safety section, **0 lose one** | refresh cost, Part 1 |
| 11 | **E-B introduces 21 combination groundings (47% of changed)** and 2–6 oral→parenteral swaps | refresh cost, Part 1 |
| 12 | **All 13 drifted labels bumped `spl_version`** — drift detectable by version compare alone | refresh cost, Part 2 |
| 13 | **A full re-embed of the whole corpus is $0.063** | refresh cost |
| 14 | **0 veterinary/supplement setids in any stored prod citation** (observed zero) | refresh cost, Part 5 |

## ❌ REFUTED — previously recorded, now measured against

| claim | status |
|---|---|
| *"c2 is a coverage defect, not a ranking defect"* | **Both.** The ranking half produces the citation and c2 does not touch it |
| *"the wrong-drug filter is blocked by c2 — c2 may descope or close it"* | **Premise refuted.** 2 of 6 adjudicated: **not fixed**. Dependency removed |
| *"cimetidine 0/3 → 3/3 is a 🔴 REGRESSION"* | **Control alone oscillates 0/3 → 4/6.** Not attributable |
| *"11 `source_id`s vanished upstream"* | **0 vanished.** All 11 were my own 2 failed fetches; both labels serve HTTP 200 |
| *"doctype predicts safety-section presence perfectly"* | **Circular** — measured the whitelist. Once `34071-1` counts: Rx 14/14 **and** OTC 34/34 |
| 🆕 *"in 6 of 6 adjudicated cases the queried drug's own reference label has no safety section"* (BACKLOG:860) | **REFUTED FOR ASPIRIN (2026-08-05, T1).** The corpus keys one substance under **two** moiety strings: `ASPIRIN` → VAZALORE (OTC, none) and **`ACETYLSALICYLIC ACID` → DURLAZA (Rx, 34070-3/34073-7/43685-7)**. *DURLAZA — Contraindications* is **row 57 of the shipped index, 375 chars, norm 0.9995, row-aligned** — an owned aspirin Contraindications doc **was in the index that cited Aceclofenac**. The adjudication checked one key, never the synonym. **Aspirin is a RANKING failure, not a coverage gap.** The other 5 are **not re-adjudicated** — UNMEASURED. [`t1_ownership_assertion_20260805.md`](t1_ownership_assertion_20260805.md) §2 |

> **⚠️ ADDENDUM 2026-08-05 — this close-out is no longer complete on its own.** It remains the resume
> point for the c2 *options*, but two things postdate it: the refutation above, and a **third defect
> mechanism**. The record here says coverage **or** ranking; it is now coverage / **threshold** /
> ranking, because whether DURLAZA's section ever clears the store `min_score` is **UNVERIFIED** and
> decides which of the two non-coverage mechanisms is operating. See TECH_DEBT [P2 · corpus dual-key].
> **c2 remains PARKED — nothing here reopens it.**
| *"E-A recovers the 11,689-char Rx ibuprofen warnings"* | That label is not pinned — an **E-C** benefit |
| *"c2-iii is cheapest, no new data, just a key alias"* | Data claim holds; **mechanism is a curated synonym map**, a new correctness dependency |
| *"a full re-embed is the expensive part of a refresh"* | **$0.063.** Cost is gate cycles and blast radius |
| *"E-A is the only option that closes the Reye's gap"* | The doc is indexed and **never retrieved** (0/6) |

## ❓ UNMEASURED

- **The mono-preference question** (below) — the one that decides E-B.
- Whether **any** of the 264 Rx `34071-1` documents is ever retrieved (E-A-Rx untested).
- **E-C / E-D** — never measured.
- Whether a **human mono label exists** for the 7 veterinary moieties.
- Drift **rate** — one snapshot against a null pin date.

---

# 2. c2 — PARKED STATE

**Every option is costed. No option has a measured upside on the defect c2 exists to fix.**

| option | measured effect | cost |
|---|---|---|
| **E-A** (all `34071-1`) | ❌ ~~**0/5 on the citation.** 2/5 gained own-doc coverage~~ → **0/5 AND it INTRODUCED a new wrong-object citation** (METHOXSALEN, 3/3 treatment vs **0/27** control) — 2/5 gained own-doc coverage. **Not neutral: net negative on the one query where it was observed.** See finding 5b | +381 docs (+8.3%), ~$0.005 |
| **E-A-Rx** (`34071-1`, Rx doctype only) | **UNTESTED** — the 5 measured queries were all OTC-class, so E-A's **Rx half was never exercised** | +264 docs, 914,222 chars, **0% lay language** |
| **E-B** (Rx-preference selection) | **45/1038 (4.3%)** change · **42 gain a first safety section, 0 lose one** · ⚠️ **21 of 45 (47%) newly ground on a COMBINATION product** · **2–6 oral→parenteral** · fixes only **4 of 15** non-human refs, all 4 with multi-ingredient labels, **both citable veterinary labels survive** | `--resolve` ~25 min + re-embed **$0.063** |
| **E-C** (A+B) | never measured | highest, one gate cycle |
| **E-D** (dual-label, curated) | never measured | curation + a corpus shape never used |
| **E-E** (do nothing) | leaves a **deterministic** wrong-drug citation live | zero |

### ⚠️ E-B trades one wrong-object class for another

`CHOLECALCIFEROL → PEDIATRIC INFUVITE` (**13 active moieties**), `BROMELAIN → 7`, `BISACODYL → 5`,
`FAMOTIDINE` tablet **→ injection**. **~4× the recorded 22/190 (11.6%) combination defect on the
moieties it touches** — and combination grounding and route mismatch are **the very class of defect this
whole line exists to reduce.**

### 💰 Embedding is NOT the constraint

**A full re-embed of the entire 4,608-doc corpus is $0.063.** Several earlier documents — including
branch reports written in this line — treated it as the expensive part. **That framing is corrected
here, in TECH_DEBT, and in the refresh entry.** The real costs are **network time, 🔴 gate cycles, and
blast radius.**

## 🔓 UNPARK CONDITIONS — conditions, not a plan

1. **E-B — THE DECIDING QUESTION.** The 47% combination figure is an **UPPER BOUND, not an
   expectation**: the dry-run replicated `_pick_reference` **only**, not **`_find_mono_reference` /
   `dropped_combo`**. A real implementation inheriting the mono-preference machinery **might cut most of
   those 21**. **This single question decides whether E-B is dead or viable. It is purely OFFLINE — no
   network, no embedding — and it is UNMEASURED.**
2. **E-A-Rx** — measure whether any of the 264 Rx `34071-1` documents is ever retrieved.
3. **Any option** — a reason to pay a 🔴 gate cycle for a change with **no measured upside**.

## What c2 no longer blocks

**The wrong-drug filter (STATE #2).** Its c2 dependency is removed — see §3.

---

# 3. THE SEQUENCING CONSEQUENCE

**Removing a refuted dependency is not a recommendation.** Priorities and queue positions are
**unchanged**; only false blockers were cleared.

| item | before | now |
|---|---|---|
| **#2 wrong-drug filter** | BLOCKED BY c2 | ✅ **UNBLOCKED** — premise refuted; **2 of 6 adjudicated, not fixed**. Priority/position **unchanged** |
| **#7 published stubs** | blocked on an unknown `/q/` count | ✅ **UNBLOCKED** — **4 of 18 rows**, all public, 2 with views |
| **M3 drift detection** | implicit under the c2/refresh cluster | ✅ **PROMOTED to its own BACKLOG item** — **not 🔴, no gate** |
| **c2** | top build candidate | ⏸️ **PARKED** with the three unpark conditions above |

**Why M3 first, if anything:** R1–R4 all require a **cadence**, and **nothing today can say what cadence
is right — no drift rate exists** (`db_published_date` is null). **M3 produces exactly that number, for
near-zero cost, and changes nothing.** It is a **prerequisite for the refresh question being answerable**,
not a nice-to-have. *(Stated as a dependency, not a recommendation.)*

---

# 4. THE MERGE QUESTION — present only, **decide nothing**

Branch `c2-phase1b-EA-measurement`, 5 commits (`a545a7b` · `11821d1` · `3d38d3e` · `db7d409` · this one)
on top of `c823b10` (already on main). **Never pushed or merged.**

| # | item | size | belongs where | why |
|---|---|---|---|---|
| 1 | **Living-doc edits** — STATE, BACKLOG, TECH_DEBT, `wrong_drug_citation_severity.md` | small | **main** | This is the reconciliation the line exists to deliver. **A stale STATE is the repo's highest-cost drift**, and main currently says c2 is the top build candidate with an unmeasured blast radius — which is now wrong |
| 2 | **`docs/c2_phase1b_measurement_20260804.md`** | ~14 KB | **main** | Holds the deciding measurement (E-A 0/5) that every downstream conclusion rests on |
| 3 | **`docs/c2_phase1c_20260804.md`** | ~13 KB | **main** | Contains §0, the strongest conclusion in the line, and the STATE-OF-c2 resume section |
| 4 | **`docs/dailymed_refresh_cost_20260804.md`** | ~13 KB | **main** | The E-B blast radius, the $0.063 correction, M3 feasibility, and the prod-DB answers |
| 5 | **`docs/nonhuman_label_scope_20260804.md`** · **`docs/dailymed_stale_citations_20260804.md`** | ~9 + 5 KB | **main** | Both are cited by filed TECH_DEBT entries; without them those entries are unverifiable |
| 6 | **This close-out** | ~11 KB | **main** | The single-read resume point |
| 7 | ⚠️ **`tests/probes/` convention + README** | ~4 KB | **main, but decide it on its own merits** | **A new repo-wide convention introduced mid-line** — that committed evidence lives outside the gitignored `tests/results/`. It should be adopted deliberately, **not ride along** with a c2 merge. **If rejected, items 8–9 go with it** |
| 8 | **Probe scripts** `tests/probes/c2/_*.py` (7 files) | ~40 KB | **main, if 7 is adopted** | Make the reports' numbers reproducible; the repo already force-adds probe scripts, so this is a formalisation |
| 9 | **Small evidence JSON** — `c2_dailymed_probe`, `c2_part2_summary`, `c2_ab_retrieval`, `c2_variance`, `nonhuman_scope`, `eb_dryrun` | ~200 KB | **main, if 7 is adopted** | Point-in-time snapshots of a **live external API** — re-running does **not** reproduce them |
| 10 | **`tests/results/c2_ea_fetch.json`** | **15.8 MB** | ❌ **stays off** | Bulk intermediate; regenerable from `_c2_ea_fetch.py` |
| 11 | **`tests/results/c2_ea_index/`** (scratch E-A index) | **31 MB** | ❌ **stays off** | Scratch vector index. ⚠️ **Delete only deliberately** — it is what makes the E-A-Rx unpark condition cheap to test |

**Not represented on the branch and worth noting:** `docs/c2_dailymed_probe_20260804.md` (Phase 1) is
**already on main** at `c823b10`, but its **in-place corrections** are on the branch — so main currently
holds a version containing the **retracted circular doctype claim** and the **withdrawn E-A ibuprofen
claim**. ⚠️ **That is an argument for merging items 1–6 sooner rather than later**, stated as a
consequence, not a recommendation.

**Nothing merged, nothing pushed, nothing deleted.**

---

# 5. DRIFT FOUND WHILE RECONCILING — flagged, not fixed

1. **`docs/c2_dailymed_probe_20260804.md` on main is stale** (see above) — its corrections exist only on
   this branch.
2. **STATE's "Recently Shipped (last 7 days)"** spans 2026-07-22 → 07-29; today is 08-04, so the window
   label is wrong. Flagged in the previous reconciliation and still unaddressed — **the label is the
   founder's convention to set.**
3. **The `[P2] top_k=5` BACKLOG entry** still recommends measuring a `local`-excluded arm. **`local` was
   deprecated in c1 (fly 215)**, so that arm is now the *default*, not a variant. The entry's suggested
   experiment is partly obsolete.
4. **TECH_DEBT's `34071-1` entry and the new M3 BACKLOG item both describe the refresh cost**, from
   different angles. Not contradictory, but a future reader could update one and miss the other.

---

# 6. Rule 18 — the state of the evidence

- **Nothing in this baton was measured.** Every figure is cited from a branch report; where a report
  marks something UNMEASURED, it stays UNMEASURED here.
- **Four false findings were produced and self-caught in this line** (instrument-blind instances 8–11).
  The standing lesson — *string heuristics over drug data are unreliable by default; self-refute before
  reporting* — is filed in TECH_DEBT as a **proposed** practice, **CLAUDE.md not edited.**
- **No priority was set, no option chosen, no queue item reordered.** Two blockers were removed **because
  their premises were refuted by measurement**, which is a correction to the record, not a decision.
