# c2 — DailyMed reference-label selection: Phase-1 READ-ONLY probe (2026-08-04)

**READ-ONLY. Nothing was built, rebuilt, re-embedded, or configured.** No product code, corpus, flag or
secret was modified. The only artifacts written are this report and a probe script + its JSON output
under `tests/results/` (gitignored measurement scope).

**Every claim below is tagged `CONFIRMED` (live DailyMed query or direct file read, shown) or
`INFERRED` (openFDA mirror / corpus artifact).** The two are never blended — that separation is the
reason this baton exists.

Live API: `https://dailymed.nlm.nih.gov/dailymed/services/v2`, `db_published_date: Jul 31, 2026`.
Probe: `tests/results/_c2_dailymed_probe.py` → `tests/results/c2_dailymed_probe.json`
(6 moieties × 4 tiers, **70 label fetches, 48 distinct setids, 0 fetch failures, 0 parse failures**).

---

## Task A — the current selection rule **`CONFIRMED` against code**

**Builder: `scripts/build_dailymed_label_corpus.py`** (found via `marketing_category_code`; not assumed).

### The rule, transcribed

| # | element | file:line | exact behaviour |
|---|---|---|---|
| 1 | tier list | **`:73`** | `TIERS = [("C73594","NDA"), ("C73607","NDA_authorized_generic"), ("C73584","ANDA"), (None,"other")]` |
| 2 | tier loop | **`:313-322`** (`_resolve_once`) | `for code, tier in TIERS:` → `cands = await _resolve_candidates(...)` → `if not cands: continue` → pick → fetch → **`return`** |
| 3 | within-tier winner | **`:192-200`** (`_pick_reference`) | `score = (1 if head-word in title else 0, -title.count(" and "), spl_version)` → `max(...)` |
| 4 | mono-first variant | **`:208-214`** (`_rank_mono_first`) | same, with a richer combo signal; used only on the `prefer_mono` / rescue paths |
| 5 | moiety key origin | **`:99-105`** (`mono_moieties`) | the corpus key is the **TFDA backbone `drug_name`, verbatim** — distinct mono-ingredient TFDA drug names |
| 6 | key normalization | **`:166-190`** (`_normalize_moiety`) | ⚠️ **used for RESOLUTION only (querying DailyMed), never as the corpus key** — strips trailing salt/hydrate tokens, leading dev-codes, `(as X salt)`, with guards `_ELEMENT_CATIONS` and `_NAME_PART_STEMS` |

### Verdict on the documented rule: **CONFIRMED, no doc drift — but the documentation UNDERSTATES it**

`_meta.reference_selection` records *"marketing_category_code NDA>NDA_AG>ANDA>other, mono title, max
spl_version"*. That matches the code. **No drift to report.**

**But "no Rx-vs-OTC tiebreak" is a weaker statement than what the code does.** `_resolve_once`
**returns on the FIRST tier that yields any candidate at all** (`:315-322`). So it is not that an Rx ANDA
loses a tiebreak to an OTC NDA — **the ANDA tier is never queried.** Once NDA returns anything, the
search stops.

**`CONFIRMED` live:** for `NAPROXEN` the NDA tier returns ALEVE (OTC) as candidate #1, so resolution
terminates at NDA and **never sees `49a00870` — the Rx naproxen label carrying 10,268 chars of Drug
Interactions in the ANDA tier.**

### Rx/OTC awareness anywhere in the path: **NONE `CONFIRMED`**

A grep of the builder and `api/data_sources/dailymed.py` for `otc|prescription|rx_only|monograph`
returns exactly **one comment** (`dailymed.py:14`, noting 34073-7 is absent on OTC Drug-Facts labels).
**No code reads or acts on Rx/OTC status.**

---

## Task B — c2-i prerequisite: **does an Rx label with a real safety section exist? `CONFIRMED` YES, 6 / 6**

All rows below are **`CONFIRMED`** — live `spls.json` + `spls/{setid}.xml` fetches this session. Char
counts are from the live SPL parse. `Rx/OTC` is the SPL document-type code (see Task C).

| moiety | tier | setid | label | mktg (in SPL) | Rx/OTC | safety sections present (chars) |
|---|---|---|---|---|---|---|
| **NAPROXEN** | NDA | `3ca84972` | ALEVE CAPLETS | NDA | **OTC** | *(34071-1 warnings 2700 — not whitelisted)* |
| | ANDA | **`49a00870`** | **NAPROXEN TABLET** [Preferred Pharms] | ANDA | **Rx** | **boxed 1946 · contra 820 · warn 17314 · interact 10268** |
| | ANDA | `9f026fd5` | NAPROXEN TABLET | ANDA | **Rx** | boxed 1873 · contra 722 · warn 16754 · interact 10201 |
| **OMEPRAZOLE** | NDA | `5b88717a` | CAREONE OMEPRAZOLE | NDA | **OTC** | *(34071-1 1303)* |
| | ANDA | `37291cab` | **PRILOSEC OTC** | ANDA | **OTC** | *(34071-1 249)* |
| | ANDA | **`a19ce586`** | **OMEPRAZOLE DR CAPSULE** | ANDA | **Rx** | **contra 1100 · warn 10483 · interact 8600** |
| | ANDA | `0344268f` | OMEPRAZOLE DR CAPSULE | ANDA | **Rx** | contra 1110 · warn 10517 · interact 8590 |
| **IBUPROFEN** | NDA | `1f01c10a` | ADVIL | NDA | **OTC** | *(34071-1 2614)* |
| | ANDA | **`17577b3b`** | **IBUPROFEN TABLET** [Amneal] | ANDA | **Rx** | **boxed 820 · contra 519 · interact 3762** ⚠️ *+ 11 689 chars of warnings under **34071-1**, see Task C* |
| **CIMETIDINE** | NDA | `e6401e0a` | **TAGAMET** | NDA | **OTC** | *(34071-1 1206)* |
| | ANDA | **`0ab5ea2b`** | **CIMETIDINE TABLET** | ANDA | **Rx** | **contra 107 · interact 1902** ⚠️ thin — no warnings section |
| | ANDA | `db482bd8` | CIMETIDINE TABLET | ANDA | **Rx** | contra 116 · interact 1936 |
| **TERBINAFINE** | NDA | `9dea4789` | **LAMISIL AT CREAM** | NDA | **OTC** | *(34071-1 399)* |
| | ANDA | **`2886b2ff`** | **TERBINAFINE HCl TABLET** | ANDA | **Rx** | **contra 386 · warn 6118 · interact 3571** |
| | other | `3b2c1d7f` | ATHLETE FOOT CREAM | **OTC Monograph Drug** | **OTC** | *(34071-1 317)* |
| **FAMOTIDINE** | NDA | `a2ef8424` | **PEPCID COMPLETE** | NDA | **OTC** | *(34071-1 1180)* — also 3 active moieties |
| | **NDA** | **`9710995d`** | **FAMOTIDINE INJECTION** | **NDA** | **Rx** | **contra 310 · warn 2656 · interact 1178** ← *an **Rx NDA**; see Task C* |
| | ANDA | `b2228be0` | FAMOTIDINE POWDER FOR SUSP | ANDA | **Rx** | contra 334 · warn 1247 · interact 1464 |

### Plain answers

| moiety | Rx label with ≥1 real safety section in DailyMed? | status |
|---|---|---|
| naproxen | **YES** | `CONFIRMED` |
| omeprazole | **YES** | `CONFIRMED` |
| ibuprofen | **YES** | `CONFIRMED` |
| cimetidine | **YES** — but **thin** (contra ~110 chars, interactions ~1.9k, **no warnings section**) | `CONFIRMED` |
| terbinafine | **YES** | `CONFIRMED` |
| famotidine | **YES** | `CONFIRMED` |

**➡️ The c2-i prerequisite is MET, 6/6, against live DailyMed — no longer an openFDA-mirror inference.**

⚠️ **Two caveats that survive:** **(1) cimetidine's Rx label is genuinely thin** — c2-i would fix its
*wrong-drug citation* (COBIMETINIB) but give it much less content than the others. **(2)** the top Rx
famotidine hit is an **injection**, and the ANDA one a **powder for suspension** — for an oral-tablet
question the route differs. **Route/form suitability is NOT addressed by an Rx preference and is not in
this probe's scope.** Flagged, not solved.

---

## Task C — what actually discriminates Rx from OTC?

### `marketing_category_code` does **NOT**. `CONFIRMED`, and this is decisive.

Across the 48 distinct labels:

| marketing category (from the SPL) | OTC | Rx |
|---|---|---|
| **NDA** | **21** | **1** |
| **ANDA** | **11** | **13** |
| OTC Monograph Drug | 2 | 0 |

**Both NDA and ANDA contain both kinds.** The ANDA tier is almost evenly split (11 OTC / 13 Rx), and
`FAMOTIDINE INJECTION` (`9710995d`) is an **Rx label with marketing category NDA** — so "NDA ⇒ OTC brand"
is false in both directions. **A tiebreak built on marketing category alone would be unreliable.**

### The SPL **document-type code** does. `CONFIRMED`, 100% on this sample.

The root `<code>` element of every SPL carries a LOINC document type:

| code | meaning | n |
|---|---|---|
| **`34391-3`** | HUMAN PRESCRIPTION DRUG LABEL | **14** |
| **`34390-5`** | HUMAN OTC DRUG LABEL | **34** |
| *anything else / missing* | — | **0** |

**48 / 48 labels resolved to exactly one of the two. Zero unknowns, zero missing.**

**And it predicts safety-section presence perfectly on this sample:**

| doctype | n | with ≥1 **corpus-whitelisted** safety section |
|---|---|---|
| **Rx `34391-3`** | 14 | **14 (100 %)** |
| **OTC `34390-5`** | 34 | **0 (0 %)** |

**➡️ Recommendation for the discriminator question (mechanism only, not a build decision): the SPL
document-type code is the reliable field; `marketing_category_code` is not.** It is available on the
same SPL fetch the builder already performs (`_resolve_once :319`), so reading it costs no extra request.

⚠️ **Reliability caveat, stated honestly:** 48 labels across 6 deliberately-chosen dual-status moieties
is **not** a corpus-wide validation. It is a strong signal on exactly the population c2-i targets. **A
build should re-validate across the full 1038-moiety backbone before relying on it** — this probe does
not license the general claim.

### 🔎 Task-C side finding — **LOINC `34071-1` is not in the corpus's section list at all**

The builder's `SECTIONS` (`:77-84`) covers `34073-7 · 34066-1 · 34070-3 · 43685-7 · 34067-9 · 34068-7`.
**`34071-1` ("WARNINGS", the Drug-Facts-style section) is absent.** `CONFIRMED` by file read.

- **35 / 48** probed labels carry a `34071-1` section.
- **34 / 34 OTC labels contribute ZERO whitelisted safety sections** — because their only safety content
  lives in `34071-1`. **This is the mechanical explanation of the recorded 120/128 (93.8%) OTC-shaped
  no-safety class**, now confirmed at label level rather than inferred from section-shape counts.
- ⚠️ **It also costs an Rx label:** `17577b3b` (IBUPROFEN, Rx) puts **11 689 chars of warnings** under
  `34071-1`. Even after an Rx-preference fix, **that section would still be dropped.**

---

## Task D — c2-iii scope and blast radius

### D1. The aspirin split — **`CONFIRMED` still true in the current corpus**

| corpus moiety key | setid | reference label | doctype | indexed sections |
|---|---|---|---|---|
| **`ASPIRIN`** | `c623d479` | **VAZALORE (aspirin)** | **OTC** `34390-5` | indications, dosage — **no safety section** |
| **`ACETYLSALICYLIC ACID`** | `4c2a1403` | **DURLAZA (Acetylsalicylic Acid)** | **Rx** `34391-3` | **contra 375 · interactions 2198 · warnings 1111** + indications, dosage |

### D2. Where the duplicate originates — **NOT in DailyMed, and NOT in the builder**

**`CONFIRMED`:** the TFDA backbone contains **both `ASPIRIN` and `ACETYLSALICYLIC ACID` as distinct
mono-ingredient `drug_name` values**. `mono_moieties()` (`:99-105`) takes them verbatim, so the builder
issues two independent DailyMed queries and legitimately gets two different labels.
**The duplication is upstream, in the TFDA source data.** Any alias map is therefore a *correction
applied to TFDA's naming*, not a repair of a DailyMed or builder bug — which is where its risk comes from.

### D3. Insertion point for an alias (identified, **not implemented**)

The only sound place is **between the backbone read and resolution**: `mono_moieties()` (`:99-105`)
produces the key list, and `_resolve_moiety` (`:348`) consumes it. An alias would have to either
(a) collapse two backbone keys to one before resolution, or (b) leave both keys and share one resolved
reference. **(a) changes the corpus key set; (b) creates two moieties pointing at one setid — a state
that does not exist today (see D4).**

### D4. ⚠️ BLAST RADIUS — **56 collision groups, and several are NOT synonyms**

Applying the builder's **own** `_normalize_moiety` to all 1038 corpus moieties yields **56 groups where
two or more distinct moieties collapse to the same normalized form.** `CONFIRMED` by running the
builder's function over the shipped corpus.

**`CONFIRMED`: 0 setids are currently shared between moieties** — every one of the 1038 has its own
reference label. **So any alias map is a genuine merge, not a de-duplication of something already merged.**

**These groups are pharmacologically DISTINCT — merging them would be the same wrong-object family as the
defect c2 exists to fix:**

| group | members | why merging is wrong |
|---|---|---|
| FLUTICASONE | `FLUTICASONE FUROATE` (safety=3) · `FLUTICASONE PROPIONATE` (safety=**0**) | **different drugs** (Arnuity vs Flovent), different products |
| BETAMETHASONE | `BETAMETHASONE` · `…SODIUM PHOSPHATE` · `…VALERATE` | injectable vs topical — different routes |
| ESTRADIOL | `ESTRADIOL` · `…BENZOATE` · `…VALERATE` | different esters, different PK |
| DICLOFENAC | `…POTASSIUM` (safety=4) · `…SODIUM` (safety=**0**) | IR oral vs DR/topical |
| TESTOSTERONE | `TESTOSTERONE` · `…PROPIONATE` | different esters |
| CAFFEINE | `…CITRATE` · `…SODIUM BENZOATE` | citrate is neonatal-apnoea specific |

**⚠️ The dangerous pattern: asymmetric coverage.** In several groups one member has safety sections and
the other has **zero** — `DICLOFENAC POTASSIUM 4 / SODIUM 0`, `FLUTICASONE FUROATE 3 / PROPIONATE 0`,
`TETRACYCLINE 2 / HCL 0`, `TRIPTORELIN 3 / ACETATE 0`, `ESOMEPRAZOLE 0/0/3`. **A merge would "fix"
coverage for the empty member by giving it a different drug's label.** That is exactly the failure mode
being repaired. **An alias map must be curated and justified per pair, never derived from string
similarity.**

### D5. ⚠️ **`ASPIRIN` / `ACETYLSALICYLIC ACID` is NOT among those 56 groups** — and that matters

`_normalize_moiety("ACETYLSALICYLIC ACID")` → `ACETYLSALICYLIC ACID` (no trailing salt token);
`_normalize_moiety("ASPIRIN")` → `ASPIRIN`. They never collide. `CONFIRMED`.

**So c2-iii is NOT "extend the existing normalizer" — it is "introduce a curated TRUE-SYNONYM map",
a different and riskier mechanism than the salt-stripping already in place.** The existing normalizer is
conservative and guarded (it already learned this lesson once: stripping `BENZYL BENZOATE` → `BENZYL`
wrongly matched PRE-PEN, hence `_NAME_PART_STEMS` at `:154-158`). A synonym map has **no such structural
guard** — correctness rests entirely on curation.

**Scope correction to the BACKLOG entry:** c2-iii is described there as *"no new data at all — just a key
alias … the cheapest of the three sub-fixes."* **The DATA claim is confirmed** (DURLAZA is already
indexed). **The "cheapest / lowest-risk" framing needs qualifying** — the mechanism is a curated synonym
list, which is a new class of correctness dependency, not a reuse of the existing normalizer.

---

## Task E — the residual: dual OTC/Rx drugs where ONE reference label is structurally insufficient

### ⚠️ First, a CORRECTION to a previously recorded finding

I earlier recorded *"DURLAZA carries no Reye's warning (verified, 0 hits)."* **That was scoped to the
five INDEXED corpus sections and remains true there. It is NOT true of the full label.** `CONFIRMED` by
live fetch: **the DURLAZA SPL full text DOES contain "reye"** — it simply is not inside any section the
corpus indexes. Both statements are true at different scopes; the earlier wording implied the label
lacked it. **Corrected here.**

### And the finding that reshapes the options

**`CONFIRMED` by live fetch of the corpus's own pinned ASPIRIN reference (`c623d479`, VAZALORE, OTC):**

| section | chars | contains "reye" | contains "chicken pox" |
|---|---|---|---|
| **`34071-1` WARNINGS** | **954** | ✅ **yes** | ✅ **yes** |
| indications | 260 | | |
| dosage | 268 | | |

**➡️ Aspirin's own already-pinned OTC reference label carries a 954-char warnings section containing
Reye's syndrome and chicken pox. It is not indexed solely because `34071-1` is missing from the
builder's `SECTIONS` list.** No selection change, no new label, no new query is required to reach it.

### The options (cost + blast radius; **no recommendation — founder scope call**)

| # | option | what it fixes | cost | blast radius |
|---|---|---|---|---|
| **E-A** | **Add `34071-1` to `SECTIONS`** — index Drug-Facts warnings; change **nothing** about selection | Gives **all ~120 OTC-shaped moieties** their first safety section. **Closes the aspirin Reye's gap.** Recovers the 11 689-char warnings on the Rx ibuprofen label too | **Smallest**: one constant + re-parse of pinned setids (the non-`--resolve` path) + **re-embed of the new docs** | 🔴 **Changes what is retrieved on every Research query** — adds ~120+ new docs competing for a `top_k=5` budget already measured tight (11 safety sections parked at composite rank 5) |
| **E-B** | **Rx-preference selection (c2-i as scoped)** | The **wrong-drug citation** for naproxen / omeprazole / ibuprofen / cimetidine / terbinafine | Build change + **full `--resolve` re-pull (~25 min network) + full re-embed** | 🔴 Changes the reference label for an unknown number of the 1038 moieties — **must be measured before it is chosen** |
| **E-C** | **E-A + E-B together** | Both the citation and the OTC-only content | Highest single-shot cost; one re-resolve + one re-embed | 🔴 Largest, but **one** gate cycle instead of two. ⚠️ Two safety sections per dual-status moiety ⇒ more near-duplicate crowding (cross-ref the Finding-C 4×-TFDA observation) |
| **E-D** | **Dual-label indexing for a bounded, curated list of dual-status moieties only** | Both, for the drugs that matter, without corpus-wide growth | Curation effort + selection change; needs a defensible "which drugs are dual-status" rule | 🔴 Smaller than E-C but introduces a **second reference label per moiety**, a shape the corpus has never had (D4: 0 shared setids today) |
| **E-E** | **Do nothing; document the gap** | Nothing | Zero | Zero — but leaves a live wrong-drug citation on prod, which the fly-215 gate captured |

**⚠️ Every option except E-E changes what is retrieved on every Research query ⇒ 🔴.** Flagged as
instructed.

**Observation, not a recommendation:** E-A is the only option that closes the **Reye's** gap, and E-B is
the only one that fixes the **wrong-drug citation**. **They fix different halves of the same case and
neither is a superset of the other.**

---

## Rule 18 — what this probe did NOT establish

- **The Task-C discriminator is validated on 48 labels across 6 moieties, not corpus-wide.** A build must
  re-validate over the full 1038-moiety backbone. This probe does not license the general claim.
- **The blast radius of E-B is UNMEASURED.** I did not determine how many of the 1038 moieties would
  change reference label under an Rx preference — that needs a full dry-run re-resolve, which is a
  network operation this read-only phase deliberately did not perform.
- **Route/form suitability is out of scope and unaddressed** (famotidine's Rx hits are an injection and a
  powder; terbinafine's OTC is a topical cream while its Rx is an oral tablet). An Rx preference does not
  reason about route.
- **`ASPIRIN` and the other 5 c2-i moieties were probed; the remaining ~114 OTC-shaped moieties were
  not.** The 120/128 figure remains `INFERRED` from section-shape counts; only its *mechanism* is now
  `CONFIRMED`.
- **Cimetidine's Rx label is thin** (no warnings section) — c2-i helps it least of the six.
- No §2.7, danger-path, canary or human-eye gate was run. **None applies to a read-only probe.**

## For the build phase (recorded, not started)

c2 changes **what is retrieved** ⇒ 🔴: own **§2.7 Research gate + section-aware danger-path re-gate +
canary + prod human-eye gate**. Per the 4th ops SOP line, the human-eye rows **must name the expected
drug** — `aspirin contraindications` and `ibuprofen warnings and precautions` become named rows, with the
expected citation being **that drug's own label**, not merely "a DailyMed safety section". That is
precisely how the fly-215 gate passed `aspirin → Aceclofenac`.
