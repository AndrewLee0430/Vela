# DailyMed refresh — cost model for a single re-resolve (2026-08-04)

**DRY-RUN ONLY. Nothing written to `data/`, nothing embedded, no selection rule applied, nothing built,
nothing sequenced.** Shipped index verified byte-intact. Branch only; not pushed.
**c2 remains parked** — measuring E-B's blast radius is *not* authorization to build it.

Tags: **`CONFIRMED`** · **`INFERRED`** · **`REFUTED`**.

**Network cost of this baton:** Part 1 issued **420 `spls.json` + 793 SPL XML = 1 213 requests over
1 236 s (~21 min)** for 128 moieties. Part 2 reused the 1 036-setid fetch from Phase 1b (877 s) plus
**13 version checks**. Part 5 was 6 read-only Postgres queries.

---

# 💰 THE HEADLINE THE COST MODEL TURNS ON

> ### Embedding is NOT the constraint. A **full** re-embed of the entire corpus is **$0.063**.
> 4 608 docs · 12 654 249 chars · ≈3.16 M tokens · `text-embedding-3-small` @ $0.02/1M.
> **Earlier docs (including mine) treated "full re-embed" as the expensive part of a refresh. It is
> six cents.** The real costs are **network time**, **🔴 gate cycles**, and **blast radius**.

---

## Part 1 — E-B's blast radius: **45 of 1038 moieties (4.3%)** `CONFIRMED`

**Rule B as measured:** tier order and `_pick_reference` unchanged, but only candidates whose SPL
doctype is `34391-3` (Rx) are eligible; if no tier has an Rx candidate, fall back to rule A.

**⚠️ Search-space bound, stated because it is load-bearing:** under this definition, if rule A's winner
is already Rx it is also the top-scored *Rx* candidate in that tier — so rule B picks the same label.
**Only the 128 moieties whose current pick is non-Rx can change.** A rule B that ignored tier order
would give a different number. *(Self-check: the 908 Rx picks were not re-resolved; the invariant is
argued from the scorer, not measured. If the founder wants rule B defined differently, this number
must be re-measured.)*

| outcome | n |
|---|---|
| examined (non-Rx current pick) | 128 |
| **would CHANGE reference setid** | **45** (**4.3 %** of the full 1038) |
| no Rx label exists at all → unchanged | 83 |

### Coverage effect — unambiguously positive

| | n |
|---|---|
| **GAIN their first whitelisted safety section** | **42** |
| **LOSE a safety section** | **0** |
| had one, still have one | 0 |
| had none, still none | 3 |

**No coverage regression anywhere.** This is E-B's genuine benefit, now quantified for the first time.

### 🔴 Route / form — the never-counted risk, now counted

**6 of 45 changed moieties (13 %) swap ORAL → PARENTERAL:**

| moiety | current form | rule-B form |
|---|---|---|
| **FAMOTIDINE** | TABLET, FILM COATED | **INJECTION, SOLUTION** |
| POTASSIUM GLUCONATE | TABLET | INJECTION, SOLUTION |
| CHOLECALCIFEROL | SOLUTION | INJECTION, SOLUTION |
| DEXPANTHENOL | LIQUID | INJECTION, SOLUTION |
| METHIONINE | LIQUID | INJECTION |
| TAURINE | LIQUID | INJECTION, SOLUTION |

**FAMOTIDINE confirms the Phase-1 observation** — an oral-tablet question would ground on an injection
label, whose dosing and administration warnings are not transferable.

> ⚠️ **SELF-REFUTED FIRST PASS.** My initial classifier reported **10 of 45 (22 %)**. It was wrong twice:
> it counted **container** tokens (BOTTLE, CARTON, KIT, VIAL) as dosage forms, and it classified
> **NAPROXEN `TABLET` → `TABLET, FILM COATED, EXTENDED RELEASE` as oral→non-oral** — an extended-release
> tablet is oral. Corrected classifier excludes container tokens and treats all TABLET*/CAPSULE* as oral.
> **The real number is 6 (13 %), not 10 (22 %).** Known remaining failure mode: `SOLUTION`/`LIQUID`
> without a route qualifier is classified `oral(liquid?)` and may be topical or ophthalmic — 4 of the 6
> above are that shape, so **the oral→parenteral count could be as low as 2** (FAMOTIDINE, POTASSIUM
> GLUCONATE, which are unambiguously oral solid forms today).

### 🔴 Combination products — **E-B makes this WORSE, by a lot**

| | among the 45 changed |
|---|---|
| multi-active BEFORE | **2** |
| multi-active AFTER | **23** |
| **newly introduced by rule B** | **21 (47 % of changed)** |

Examples — the queried moiety is one ingredient among many:

| moiety | rule-B label | active moieties |
|---|---|---|
| CHOLECALCIFEROL | PEDIATRIC INFUVITE MULTIPLE VITAMINS | **13** |
| DEXPANTHENOL | PEDIATRIC INFUVITE MULTIPLE VITAMINS | **13** |
| BROMELAIN | BRUSELIX BRUISING | 7 |
| BISACODYL | GAVILYTE-H AND BISACODYL | 5 |
| LACTIC ACID | PHEXXI | 3 |
| MAGNESIUM OXIDE | CLENPIQ | 3 |

**This is the recorded combination-product wrong-object family (22/190, 11.6 % on the local corpus),
and rule B would multiply it ~10× on the moieties it touches.** The builder has mono-preference
machinery on the resolve path (`_find_mono_reference`, `dropped_combo`) — **whether an E-B
implementation would inherit it is unmeasured**; this dry-run replicated `_pick_reference` only.

### Non-human 15 — E-B barely helps, and the help is itself contaminated

**4 of 15 replaced** (CHOLECALCIFEROL, LACTIC ACID, POLYSACCHARIDE IRON COMPLEX, POTASSIUM GLUCONATE) —
**and all 4 replacements are multi-ingredient products** (INFUVITE 13-active, PHEXXI, PUREVIT DUALFE
PLUS, NORMOSOL-R). **11 of 15 remain non-human**, including **both citable veterinary safety labels**
(`CHLORTETRACYCLINE HCL` → CLTC 100 MR, `DISODIUM CLODRONATE` → OSPHOS).

**➡️ E-B does NOT fix the non-human problem. Item 1 needs its own exclusion regardless.**

### Net read (evidence, not a recommendation)

E-B buys **42 first-time safety sections** and **0 coverage losses** — real. It costs **21 new
combination-product groundings** and **2–6 oral→parenteral swaps**. **Both costs are members of the
wrong-object family this whole line of work exists to reduce.** Whether that trade is worth taking is a
founder call; the numbers are now on the table for the first time.

---

## Part 2 — refresh scope: what a re-pull would actually change `CONFIRMED`

**This is a CENSUS, not a sample** — all pinned setids re-parsed, **4 597 comparable sections**.

| | n |
|---|---|
| sections with **changed content** | **30 (0.65 %)** |
| …of which **SAFETY** sections | **18** |
| distinct labels involved | **13** |
| pinned setids **superseded** (`spl_version` bumped) | **13 — all of them** |
| resolve to a **different label** now | see Part 1 (a selection question, not a fetch question) |
| **fetch failures — NOT deletions** | **2** (TOLTERODINE, ZOLPIDEM) |

### Direction split — both failure modes are present

| direction | sections | safety |
|---|---|---|
| we **LACK** text upstream has (ours shorter) | **20** | **13** |
| 🔴 we **SERVE** text upstream **REMOVED** (ours longer) | **9** | **4** |
| same length, text edited | 1 | 1 |

### 🔎 The finding that makes cheap detection possible

**All 13 drifted labels bumped `spl_version`** (AZITHROMYCIN 48→49, PROGESTERONE 24→**26**,
UPADACITINIB 100→101, BUPRENORPHINE 42→43, …). **Zero silent revisions.**

> **➡️ Drift can be detected by comparing `spl_version` alone — no XML parse, no diff, no embed.**
> 100 % detection on this sample. This is what makes the Part-4 "detect without rebuilding" option
> genuinely cheap.

⚠️ **`spl_version` was NOT measured in the first pass** — the fetch echoed the *shipped* version back,
so an earlier "0 superseded" reading was comparing a value to itself. **REFUTED and re-measured** on the
13 drifted setids directly.

⚠️ **404 ≠ deletion.** The 2 fetch failures are excluded from every count above. Their `drugInfo.cfm`
pages return **HTTP 200** with the correct live labels (Detrol® LA, AMBIEN CR); only the API XML 404s.
Their drift status is **unknown**, not zero.

---

## Part 3 — the combined-operation cost model

**Common facts for every row:** full re-embed ≈ **$0.063**; a full `--resolve` is ≈**25 min** by
`BUILD_NOTES.md` (this baton's 128-moiety dry-run took 21 min at 6 candidates/tier, so a real resolve at
1 candidate/tier is consistent with that figure); **selective re-embed is available** — v197 precedent:
only rows whose `content` changed need new vectors, and docs↔embeddings align by row index, so unchanged
vectors are preserved by concatenation.

| path | contents | network | embed | 🔴 gate cycles | rollback |
|---|---|---|---|---|---|
| **R1** | **refresh only** (re-pull, same rule) | ~25 min | **~$0.0003** (30 changed sections only) | **1** | trivial — keep the old pair of files |
| **R2** | refresh + non-human exclusion | ~25 min | same | **1** | trivial |
| **R3** | refresh + exclusion + **E-B** | ~25 min + Rx probing | **$0.063** (many labels change ⇒ effectively full) | **1** | trivial |
| **R4** | refresh + exclusion + E-B + **E-A-Rx** | ~25 min + Rx probing | **$0.063** | **1** | trivial |
| **R5** | each as its own baton | ~25 min **× 4** | ~$0.07 total | **4** | trivial each |

**R5's real cost is not compute — it is 4 × (§2.7 + section-aware danger-path re-gate + canary + prod
human-eye gate) and 4 × the risk of a gate cycle surfacing an unrelated oscillation.** R1–R4 pay that
once.

### ⚠️ Two statements the model must make explicitly

**1. Every path — including R1 — is 🔴.** A refresh changes retrieval input on every Research query even
with no selection change, because **the section text itself changes**: 30 sections, 18 of them safety,
in both directions. **R1 is not a maintenance no-op** and needs the full gate set.

**2. What NO path fixes.** Per the c2 Phase-1c §0 strong conclusion, **supplying a correct document does
not displace an incorrect one** — measured on the only two cases able to test it. **None of R1–R4 is
evidenced to fix the wrong-drug citation.** The deterministic probe (`aspirin` → ACECLOFENAC, 12/12)
would be expected to survive all of them. **Do not sequence any of these as a wrong-drug fix.**

---

## Part 4 — cadence MECHANISM options (no cadence chosen)

**Both requirements below appear in every option:**
- **`db_published_date` MUST be populated.** It is currently `None`, so the corpus cannot state which
  day of DailyMed it corresponds to — the `monthly_re_pull` note literally points at a null field.
- **FAIL LOUD on 404** (Rule 18). A refresh that reads a fetch failure as an upstream deletion is
  exactly the misreading that produced the false "11 vanished sections" claim.

| mechanism | cost | 🔴? | failure modes |
|---|---|---|---|
| **M1 — manual SOP line** (add to the deploy/gate checklist) | zero | no | **relies on memory; this is what exists today and it produced a frozen corpus with a null pin date.** The recorded intent already failed once |
| **M2 — CI cron running the full `--resolve` + embed** | ~25 min/run, ~$0.06 | **YES** — it changes retrieval input | ⚠️ **an automated 🔴 change with no gate is the wrong shape.** Would need to open a PR, not deploy. Also no `.github/workflows/` exists at all today |
| **M3 — drift DETECTION only: compare `spl_version` per setid, report, change nothing** | **1 038 cheap JSON queries, no XML, no embed, minutes** | **NO — changes nothing** | can only detect what version-bumps (measured: **13/13**, 100 % on this sample); a silent revision would be missed |

### 💡 M3 costed separately, as instructed

**M3 would have surfaced the buprenorphine drift months ago for near-zero cost, and it is not 🔴 because
it changes nothing.** It converts "we have no idea how stale we are" into a number, without touching
retrieval. It is also **the only option that makes the cadence question answerable with data** — you
cannot choose a refresh interval without knowing the drift rate, and today the rate is a single
measurement (30 sections / 13 labels over one unknown interval, because the pin date is null).

**Not chosen. The cadence and the mechanism are the founder's call**, and they interact: with embedding
at six cents, the argument for a slow cadence rests on **gate burden**, not compute.

---

## Part 5 — Postgres: **ran successfully, read-only, against the CONFIRMED prod database**

**Prod identity verified**, not assumed: `explore_page` contains `metformin-contraindications-renal`
(status `published`) — the exact slug served live on prod today.
**Access: strictly `SELECT` only. No writes, no schema changes, no DDL.**

### Q1 — do the veterinary / supplement setids appear in stored citations?

> ## ✅ **NO — 0 occurrences.**

Scanned **all 15 shared_query rows + all 3 explore_page rows** for the 15 non-human setids and their
product names (OSPHOS, CLTC, RenaKare, Incurin, LevaMed, OvuGel, Tetroxy, Florasync, IFEREX, D-Vite…).
**No user has ever been served a veterinary or supplement label via a share or explore page.**
⚠️ This covers **persisted** artifacts only — a transient answer that was never shared leaves no record
anywhere, so this is not a statement about all traffic.

### Q2 — the `/q/` population that open-item #7 was blocked on

| | n |
|---|---|
| `shared_query` rows total | **15** |
| …public | 12 |
| …flagged | 0 |
| `explore_page` rows | 3 (1 published, 2 archived) |
| **rows whose stored citations contain a pre-c1 LOCAL stub** | **4 of 18** |

**The 4 affected rows, named:**

| surface | id | public? | views |
|---|---|---|---|
| shared_query | `6-Si0boVrZo` | **yes** | 0 |
| shared_query | `7xI-q0dxnVg` | **yes** | 1 |
| shared_query | `Eclwok8n_Kw` | **yes** | 1 |
| explore_page | `metformin-contraindications-renal` | **published** | — |

**➡️ Open-item #7's scope is 4 rows, all public, 2 with recorded views.** That item has been blocked on
this number; it is now available. **The options (leave / suppress at render / backfill) are unchanged
and remain the founder's call** — but the scale is tiny, which materially changes the calculus.

*(Incidental: the 2 archived `explore_page` rows are `metformin-renal-dose-adjustment` en + zh-TW. This
also explains the earlier `?locale=zh-TW` 404 — the published slug genuinely has no zh-TW row.)*

---

## Rule 18 — what this baton did NOT establish

- **The 908 Rx-pick moieties were NOT re-resolved.** The "only 128 can change" bound is argued from the
  scorer's behaviour, not measured. Under a different rule-B definition it does not hold.
- **The dry-run replicated `_pick_reference` only** — not `_find_mono_reference` / `dropped_combo`. A
  real E-B implementation inheriting the mono-preference machinery **might reduce the 21 new combination
  groundings**; that is unmeasured and is the single most important follow-up if E-B is considered.
- **Route/form classification is heuristic.** Container tokens excluded, ER tablets counted oral, but
  bare `SOLUTION`/`LIQUID` remains ambiguous — the oral→parenteral count is **2 confirmed, up to 6**.
- **Drift is one snapshot** against a corpus with a **null pin date**, so the interval is unknown and no
  *rate* can be derived. 30 sections is a floor.
- **The 2 fetch-failed setids' drift status is unknown.**
- **Q1 covers persisted artifacts only** — transient answers leave no record.
- No gate of any kind was run. Nothing was built, embedded, written to `data/`, or sequenced.
