# Citation deep-link prod gate (fly 214) — PASS + six findings (2026-07-29)

**Gate: PASS.** The branch-(3) fix shipped in fly 214 behaves as designed on prod. This document records
the gate result and the six findings the gate surfaced. **Nothing here was fixed** — measurement and
recording only, per the baton.

Related records: [`citation_deeplink_fix.md`](citation_deeplink_fix.md) (the build) ·
[`citation_deeplink_diagnosis.md`](citation_deeplink_diagnosis.md) (the root cause) ·
[`research_openfda_fallback_phase1.md`](research_openfda_fallback_phase1.md) (the corrected Phase-1 entry).

---

## 0. Gate result (founder, prod, signed-in)

| row | query | observed | verdict |
|---|---|---|---|
| 1 | *What are the common side effects of Metformin?* | FDA(local) chip renders **no** "View source"; DailyMed + PubMed links open in a new tab; the answer and references survive behind them | **PASS** — the designed branch-(3) behaviour |
| 2 | `warfarin aspirin bleeding risk interaction` | PubMed + DailyMed both resolve to the document | **PASS** |
| 3–4 | TFDA rows | **produced no TFDA citation as written** → re-run with strong-signal phrasing resolved it | **PASS on retry** — see Finding 2 |
| 5 | openFDA chip | **no linked "FDA" chip appeared in any query** | **consistent with Task 1b** — openFDA is structurally inert; the conclusion now has observational support, not just code inspection |

**Task-1c is now fully closed**: the last unbrowsed source type (TFDA) was clicked by hand.

---

## Finding 1 — the local corpus is **100% empty stubs**. Not "some", not "mostly". All 690.

> The founder's screenshots showed FDA(local) citation cards whose body read like field labels with no
> values. **The screenshots were not taken as proof.** This is the measurement across all 690 documents in
> `data/drug_vectordb/index.json`.

### Method

"PAYLOAD" = document content minus the builder's **literal** template scaffolding
(`scripts/build_drug_vectordb.py:63-157` — `Drug: {name}`, `Generic Name:`, `Brand Names:`,
`Indications and Usage:`, `Dosage and Administration:`, `Contraindications:`,
`Warnings and Precautions:`, `Adverse Reactions:`, `Drug Interactions:`, `Clinical Pharmacology:`).
Those strings are emitted for every document whether or not the underlying field had a value, so
subtracting them leaves exactly what the document actually carries.

### Result — worse than the screenshots suggested

| payload chars | docs | share |
|---|---|---|
| **0 (nothing but labels)** | **190** | **27.5%** |
| 1–19 | 500 | 72.5% |
| 20+ | **0** | **0.0%** |

**Max payload across the entire corpus = 5 characters. Median = 1. Mean = 1.**
**690/690 documents (100%) have ≤ 20 characters of real content.**
**190/190 drugs (100%) have no document above 50 characters.**

| doc_type | docs | payload == 0 | payload ≤ 50 | median |
|---|---|---|---|---|
| basic_info | 190 | **190 (100%)** | 190 (100%) | 0 |
| safety | 188 | 0 | 188 (100%) | 1 |
| adverse_reactions | 167 | 0 | 167 (100%) | 1 |
| interactions | 145 | 0 | 145 (100%) | 1 |
| *pharmacology* | **0** | — | — | — |

`pharmacology` produced **zero documents** — the builder's `if data.get('pharmacology')` guard is never
satisfied, so a whole section type silently does not exist.

### The founder's two cards, reproduced exactly from the data

Porting `CitationPanel.extractAbstract()` (`:50-72`) to the stored content reproduces both screenshots
character-for-character:

| source_id | stored content | what the card renders |
|---|---|---|
| `fda-metformin-adverse` | `Drug: Metformin\n\nAdverse Reactions:\n6` | `Drug: Metformin Adverse Reactions: 6` |
| `fda-rosuvastatin-basic` | `Drug: Rosuvastatin\nGeneric Name: \nBrand Names: \n\nIndications and Usage:\n\n\nDosage and Administration:` | `Drug: Rosuvastatin Generic Name: Brand Names: Indications and Usage: Dosage and Administration:` |

**The "Show more" observation is also confirmed and is a corpus-wide invariant:** `isLong` requires
`abstract.length > 200`. **0 / 690** local documents can ever reach it. Every DailyMed card can. The
founder's "these had no Show more, DailyMed did" was reading a real structural difference.

### Root cause — proven in code, and it is NOT "the data doesn't exist"

`scripts/collect_drug_data.py` calls `FDAClient.get_drug_label()`, which returns
`FDADrugLabel.to_dict()` (`api/data_sources/fda.py:77-91`) — **a flat dict of plain strings**. But every
`_extract_*` method was written for the **raw openFDA JSON** shape, where each section is a *list*:

```python
def _extract_adverse_reactions(self, label_data: dict) -> str:
    return label_data.get("adverse_reactions", [""])[0]     # :132
```

- Keys that **do** exist in `to_dict()` are **strings**, so `[0]` returns **the first character** —
  `'6'` from `"6 ADVERSE REACTIONS…"`, `'4'` from `"4 CONTRAINDICATIONS…"`, `'7'`, `'A'`, `'C'`, `'D'`, `'W'`.
  **Verified 190/190 exact match** on `adverse_reactions`, `contraindications`, `drug_interactions`,
  `warnings`: `flat == full_label[field][0]`, zero mismatches.
- Keys that exist only in the **raw** shape — `indications_and_usage`, `dosage_and_administration`,
  `clinical_pharmacology`, `openfda`, `pregnancy` — are absent, so the `[""]` default yields `""`.
  **That is why `indications`, `dosage`, `generic_name`, `brand_names`, `pharmacology` are empty
  190/190.**

**⚠️ The real text is present and unused.** Every record keeps `full_label` (`collect_drug_data.py:72`),
which the builder never reads:

| full_label field | empty | median len | max len | total chars |
|---|---|---|---|---|
| adverse_reactions | 23 | 5,354 | 36,743 | **1,363,991** |
| dosage | 2 | 3,260 | 29,142 | 831,449 |
| drug_interactions | 45 | 2,486 | 23,937 | 633,312 |
| warnings | 114 | 0 | 27,141 | 350,044 |
| indications | 4 | 986 | 10,149 | 286,432 |
| contraindications | 25 | 456 | 2,747 | 110,215 |

**≈3.58 million characters of real FDA label text sit in the builder's own input, unread.** So the
honest framing is **not** "the local corpus has no data" — it is **"the builder reads a shape that never
existed, and discards the data it was given."**

### What these documents actually are, in retrieval terms

Embedding check (690 × 1536, L2-normalised): mean pairwise cosine **0.467**; within-doc_type **0.588–0.664**;
**0** near-duplicates above 0.95; **690/690 distinct** content strings. So they are *not* degenerate —
they are cleanly separated **by drug name and section label**, and by nothing else.

**That is precisely the failure mode**: each document is a high-quality embedding of
`"<drug name> + <section heading>"` with **no content behind it**. A query naming a drug and a section
matches them *well* — which is why they reach `top_k` — and then contributes nothing to the answer.

### Recorded consequences

**(a) They occupy `top_k` slots, and displacement is not free.** Cross-ref the **[P2] Research pool
budget** surface (BACKLOG): **11 whitelisted DailyMed safety sections measured at composite rank 5 — one
slot outside `top_k=5`**, and M3 showed the documents a promotion evicts are on-point studies
(`PMID:8247921` *"Possible interaction between warfarin and fluconazole"*), not filler. Every stub in the
top-5 is a slot a real document did not get. **⚠️ And they are weighted UP:** the ratified §2.10.6 tier
assignment gives `local` **Tier 2 ×1.5 → composite multiplier 2.25**, above Tier-4 PubMed studies at ×1.0.

**(b) A citation with no readable content AND no link is the worst combination** for the
citation-mandatory positioning. Post-fix, an FDA(local) card offers the user *no* text they can read and
*no* document they can open — while its tooltip asserts *"From official FDA drug labeling data."*
See Finding 5.

**(c) It materially strengthens the local-corpus DEPRECATION question** recorded in
`citation_deeplink_fix.md` Task 5 §2 — **and it changes its shape.** The choice is no longer
"keep vs delete". It is now three-way:

1. **DEPRECATE** — remove the 690 docs. Cheapest; also removes the Finding-5 UX problem entirely.
2. **REPAIR** — point the builder at `full_label` (a ~10-line change) and re-embed. This turns 690 empty
   stubs into 690 substantive FDA-label documents at ~3.58M chars. **⚠️ This is NOT a small change**: it is
   a 🔴 retrieval-input change to every Research query, needs its own §2.7 + danger-path re-gate, and it
   would put a **second** whole-drug FDA-label corpus alongside the live **per-section** DailyMed corpus
   (4,608 docs) — with the pool budget already tight (consequence (a)). It also does not fix the URL:
   `full_label.url` is `https://labels.fda.gov/` on 190/190, so repaired documents would still be
   unlinkable, or worse, falsely linkable (same hazard as the openFDA ordering constraint).
3. **KEEP AS-IS** — accept name-and-section-only documents in the cited pool.

**⚠️ It also undermines a ratified founder decision.** The 2026-07-06 ratification of `local = Tier 2 ×1.5`
rests on the stated reason *"local IS cached FDA labeling that relabels to 'FDA'; openFDA is T2; local
must match its own source"* (TECH_DEBT [P2 · founder-decision]). **That premise is false as built** —
local is not cached FDA labeling, it is field-label boilerplate. The decision may still be right for
other reasons, but **it was ratified on a factual claim this measurement refutes**, and the founder
should get the chance to revisit it. Consistent with the sweep's own finding that local-tier changed
*ordering* but **never** citation membership (`local→top-5` = 0 under every tier) — unsurprising once you
know the documents are near-contentless.

**Measurement scripts** (scratchpad, not committed): payload/abstract distribution, the
`flat == full_label[0]` verification, and the embedding-separation check.

---

## Finding 2 — TFDA row RESOLVED; the recorded [P3] phrasing sensitivity is now **demonstrated on prod**

The checklist's TFDA rows as written produced **no TFDA citation**:

| query | actual citations |
|---|---|
| `metformin 腎臟不好的病人可以用嗎` | DailyMed 4 + PubMed 1 |
| `冠脂妥適應症查詢` | FDA 1 + PubMed 3 |

The founder's retry with strong-signal phrasing **`冠脂妥台灣核准的適應症是什麼`** retrieved it: 1 citation,
**「TFDA 核准適應症 — 冠脂妥膜衣錠5毫克」**, 許可證字號 **衛署藥輸字第024597號**.

This is a **live prod confirmation** of TECH_DEBT **[P3] "Indication-corpus recall depends on query
phrasing"** (flagged 2026-07-06 at the v200 activation gate; `冠脂妥適應症` measured at cosine 0.5632,
below the 0.6 threshold). The defect moves from *measured offline* to *demonstrated in production*, with a
matched working/failing phrasing pair. The TECH_DEBT entry has been updated with that evidence.

### Recorded

**(i) The ops gate checklist must use a phrasing known to retrieve the indication corpus.**
Canonical gate query: **`冠脂妥台灣核准的適應症是什麼`**. Added to the `[ops]` SOP third line. Using a
weak-signal phrasing makes the gate's TFDA row **fail for a reason that has nothing to do with the change
under test** — exactly what happened here.

**(ii) NAMING COLLISION — "TFDA" labels two different things, and both can appear on one screen.**

| | what it is | where the label comes from | what clicking does |
|---|---|---|---|
| **citation chip** | a retrieved, cited document from the v193 10,941-doc indication corpus | `sourceLabels.ts:65` `labelKey: 'tfdaSourceLabel'` → **"TFDA 核准適應症"** / "TFDA Approved Indication" | opens `mcp.fda.gov.tw/im_detail_pdf/<字號>` — **the specific licence Vela cited** |
| **locale-panel pointer** | an authority Vela suggests you check yourself; **no data behind it** | `localeHint.ts:41-45` `TW_TFDA.short_name` = **"TFDA"** | opens `https://www.fda.gov.tw/` — **the agency homepage** |

Both rendered on the same gate screen and the founder could not tell which the checklist meant.
**Proposed (NOT applied — three options, founder picks):**

- **(A) Rename the pointer, not the citation** — the locale panel already renders `name_native` +
  `name_en`; drop the bare `short_name` chip there, or render it as **"衛福部食藥署 (TFDA) — 官方網站"**.
  Cheapest, and touches the surface that has *less* claim to the name (a pointer is not a source).
- **(B) Distinguish by role, not by name** — keep both "TFDA" but make the panel's chips visually a
  *pointer* affordance (e.g. an outbound-arrow row) distinct from a *citation* chip. No string change,
  but a design change, and it does not help someone reading a written checklist.
- **(C) Do nothing; fix the checklist only** — write gate rows as "the **citation chip** reading
  『TFDA 核准適應症』", never bare "TFDA".
  **Recommended as the immediate step regardless of A/B**, since it is free and it is what actually
  went wrong here.

⚠️ (A) is a user-visible string → **Rule 16, all 16 languages**. It also interacts with Finding 3 — if the
panel graduates to suppression on grounded topics, the TW collision largely disappears on exactly the
screens where it is confusing. **Sequence Finding 3 first.**

**(iii) OBSERVATION (record only, do not act):** that answer was generated from a pool of **ONE** document
(「根據 1 篇來源」). A live prod instance of the `pool_size ≤ 2` shape the pool-size harvest measured at
**11%**. Cross-ref the **[P2] Research pool budget** surface and the **[P2] `RETRIEVAL_REFUSAL_SHADOW` is
structurally blind to the most one-sided pools** entry — a 1-document pool is the exact shape that
instrument cannot see.

**(iv) ⚠️ TFDA deep-link BROWSER-CONFIRMED — and my Task-1c wording was WRONG.**
The founder clicked 查看來源 and landed on `mcp.fda.gov.tw/im_detail_pdf/衛署藥輸字第024597號`, which is the
**per-licence detail page** for 冠脂妥膜衣錠5毫克 / Crestor 5mg Film-Coated Tablets — showing 許可證號, 申請商,
發證/有效日期 and a 仿單清單 listing the label PDF. **Precise per-document provenance — the link is good.**
But Task 1c described it as *"the percent-encoded Chinese PDF path **does** resolve"*, i.e. a direct PDF.
**It is not a PDF; it is a detail page with the PDF one click further.** HTTP 200 was correct; the
characterization was not. Corrected in the `citation_deeplink_fix.md` resolve table.

---

## Finding 3 — **[ESCALATED]** the b1 locale panel contradicts itself on the same screen

Captured by the founder on one page:

- **top:** 「根據 1 篇來源」 → **TFDA 核准適應症 1**, and the entire answer is generated from that TFDA
  document, citing 許可證字號 衛署藥輸字第024597號;
- **bottom, same page:** 「**Vela 未整合上述機關資料**，本提示僅供你自行查證」
  — *"Vela has not integrated data from these authorities."*

So the panel tells the user Vela has **no** TFDA data, on a screen whose **only** source **is** TFDA data.
v193 shipped a 10,941-doc TFDA indication corpus that is retrieved, cited, and deep-linked.

**Verified in code, not inferred:**

- `utils/i18n-ui.ts` `localeHintNote` — one shared string, **16 locales**, EN
  *"Vela has not integrated data from these authorities; this notice is only a pointer for your own
  verification."* / zh-TW 「Vela 未整合上述機關資料，本提示僅供你自行查證。」
- `components/LocaleHintPanel.tsx:165` renders `{ui.localeHintNote}` **unconditionally** — no grounding
  check, no per-authority condition.
- `utils/localeHint.ts:109` — the TW entry's authorities are `[TW_TFDA, TW_NHI]`, so **TFDA is one of
  "上述機關"**. The contradiction is structural for Taiwan, not a rare coincidence.

**This is the concrete, user-visible instance of BACKLOG (d) "Pointer→grounding graduation"** — no longer
a future nicety. Linked, and its priority-raise proposal recorded on that entry.

**Class name: a string that was TRUE when written and became FALSE when the data shipped.**
Identical shape to b1's **"NHI reimbursement"** leak: a string authored under a narrower world
(there, Taiwan-only; here, TFDA-not-integrated) that no one revisited when the world widened.
**Cross-ref CLAUDE.md Rule 19** — Rule 19 covers a *mitigation* that failed to travel with the data;
this is its sibling: **a disclaimer that failed to retire when the data arrived**. Both are silent,
both are only visible from a surface the author was not looking at, and neither has an automated guard.
**Proposed as a Rule-19 amendment for founder ratification — CLAUDE.md NOT edited.**

**Recorded, NOT fixed.** The panel copy is user-visible and 16-language (Rule 16), and the right fix may
be **conditional suppression** (the (d) graduation) rather than a reworded string — that is a design
decision for the founder, not a copy edit. **A reworded string is the trap here**: softening it to
"may not be integrated" would make it vague on every screen instead of wrong on one.

---

## Finding 4 — the locale panel fired on 4 of 5 gate queries; category mix varies

| query | lang | fired? | categories |
|---|---|---|---|
| metformin side effects | en | ✅ | Dosing |
| metformin 腎臟不好的病人可以用嗎 | zh | ✅ | Dosing |
| 冠脂妥適應症查詢 | zh | ✅ | Dosing |
| 冠脂妥台灣核准的適應症是什麼 | zh | ✅ | **劑量 + 適應症** |
| warfarin aspirin bleeding | en | ❌ | — |

**4/5 is a fire rate, not a defect** — the gate queries were deliberately drug-and-label-heavy, which is
exactly what the keyword lists target. But two things are worth recording:

**(a) The multi-category zh case narrows the concern.** 「劑量 + 適應症」 shows the classifier is **not**
uniformly collapsing to Dosing. So any over-firing worry is **specific to the English keyword list**, not
to the classifier — which matters, because the English list is the one whose blast radius is global
(b1 shipped 29 EN terms, deliberately tighter than zh-TW's 34, precisely on this reasoning).

**(b) Re-measure, do not guess.** The b1 gate included a **no-fire precision check** (mechanism-of-action
query correctly did not fire), so there is a method already. The right next step is to re-run that
precision check against a set of English queries that should NOT fire, and count.

**Recorded as an open measurement item. Proposed priority: [P3].** Not [P2] because nothing is known to
be wrong — 4/5 on drug-label queries is the designed behaviour and the one no-fire was correct; the item
is "we have not measured English precision since the list shipped", not "the list is wrong."
**The keyword list is NOT changed.**

---

## Finding 5 — UX: FDA(local) citations now look broken (founder-reported)

A source card with no "View source" reads as a bug to a user who does not know the corpus has no URLs.
Founder proposal: explain it in the existing tooltip.

**Recorded as a candidate, with three constraints:**

**(i) Rule 16.** Any new user-visible string needs all 16 languages.

**(ii) ⚠️ The EXISTING tooltip is the bigger problem, and Finding 1 makes it worse.**
`sourceLabels.ts:60-61` maps both `fda` and `local` to `tooltipKey: 'officialTip'` =
**"From official FDA drug labeling data"** (16 locales). After Finding 1, that string is attached to a
card whose entire body is `Drug: Rosuvastatin Generic Name: Brand Names: Indications and Usage:`.
**Calling that "official FDA drug labeling data" claims a great deal for a field-label string.**
`sourceLabels.ts:13` already carries a prior honesty note of exactly this kind (for `localauthority`:
*"unproven as FDA, never produced today — do NOT misattribute FDA trust to it"*). **Adding a reassuring
sentence to a tooltip that is already over-claiming would compound the problem, not fix it.**

**(iii) 🔎 Found while checking (ii) — not part of the founder's report, flagged not fixed:**
`sourceLabels.ts:65` gives the **TFDA** chip `tooltipKey: 'officialTip'` as well — so a Taiwanese licence
citation tells the user it came *"From official FDA drug labeling data."* Wrong agency, wrong country,
wrong data type. Same one-line family as (ii); worth batching with it.

**(iv) ⚠️ SEQUENCING — do the deprecation question FIRST.** If the local corpus is deprecated, this
problem **disappears** and the 16-language work is wasted. If it is repaired (Finding 1, option 2), the
cards gain real content and the tooltip becomes true — also making this item moot. **Only option 3
(keep as-is) requires this work.** So this is downstream of a decision that has not been made.

**What measurement would answer the deprecation question** (with existing tooling, no new harness):

1. **Cost side — does removing the 690 docs lose any answer quality?** Run the **§2.7 20-case Research
   gate** with the local store excluded (`source_filter` already supports it) and diff verdicts against
   the current baseline. Floor is **18/2/0** with every FAIL individually adjudicated (per the 2026-07-27
   amendment) — a run that holds the floor is direct evidence the stubs are not load-bearing.
2. **Displacement side — what enters the pool in their place?** Reuse the **pool-identity capture** now in
   `tests/run_golden_tests.py` (added for the R15 escalation rule) to record the cited pool with and
   without `local`, and classify what fills the freed slots. That answers consequence (a) with identities,
   not counts — the same method the M3 displacement analysis used.
3. **Frequency side — how often does this reach users at all?** Count local-document appearances in cited
   top-5 across the golden set. Phase-1 measurement already established that `local` reaches `top_k`
   regularly (unlike openFDA), so this bounds the blast radius of either direction.

Steps 1 and 2 are the same run. **Cheap, and it decides three open items at once** (this one, Finding 1's
three-way choice, and the ratified local-tier premise).

---

## Finding 6 — **[has a clock on it]** the TFDA corpus cites licences that EXPIRE

The first TFDA citation ever browser-eyeballed carries 有效日期 **116-01-18 = 2027-01-18** — under six
months from today. The corpus is built from a **pinned** id=37 snapshot
(`data/tfda/snapshot_20260630/drug_license_id37.zip`, 26,020 rows, pulled 2026-06-30). id=37 is
未註銷藥品許可證資料集 — *active as of the snapshot*. **Licences expire; a pinned snapshot does not.**

### Measurement

Joined all 10,941 corpus documents back to the snapshot on 許可證字號. **17,881 distinct licences cited;
0 unmatched; 0 missing dates.** Reference date **2026-07-29**.

**By cited licence (n = 17,881):**

| bucket | licences | share | cumulative |
|---|---|---|---|
| **ALREADY EXPIRED** | **71** | 0.4% | 0.4% |
| expires < 3 months | 298 | 1.7% | 2.1% |
| expires 3–6 months | 533 | 3.0% | 5.0% |
| expires 6–12 months | 1,245 | 7.0% | **12.0%** |
| expires 1–2 years | 4,351 | 24.3% | 36.3% |
| expires 2+ years | 11,383 | 63.7% | 100% |

**By document** (a document is only fully stale when **all** its licences are):

- **34 / 10,941 (0.31%)** documents have **every** cited licence expired.
- 34 / 10,941 (0.31%) have *some* expired.
- Forward decay of each document's latest-expiring licence: **1.5%** stale within 3 months, **3.7%** within
  6, **8.9%** within 12.

**Cumulative cited-licence expiry:** 0.4% today → **2.1%** at 3 months → **5.0%** at 6 → **12.0%** at 12 →
**36.3%** at 24.

### ⚠️ Sub-finding — the DEEP-LINK anchor decays faster than the document

The URL and `source_id` are built from **one representative licence**, and that choice is **not
expiry-aware**:

| representative licence (= the deep-link) | docs | share |
|---|---|---|
| already expired | **40** | 0.4% |
| expires < 6 months | **476** | **4.4%** |
| expires 6–12 months | 679 | 6.2% |
| expires 1–2 years | 2,778 | 25.4% |
| expires 2+ years | 6,968 | 63.7% |

- **1,223 documents (11.2%)** have a representative licence that expires **sooner than one of its own
  siblings** — a longer-lived licence was available and not chosen.
- **8,748 documents (80.0%)** are backed by exactly **one** licence, so there is no sibling to fall back to.

**The gate's own citation is an instance.** 冠脂妥膜衣錠5毫克 carries **12** licences spanning
**2027-01-18 → 2031-07-18**, and the deep-link anchors on **衛署藥輸字第024597號 — the earliest-expiring of
the twelve**. The document has four more years of validity behind it; the link the user clicks has under
six months.

### Is 有效日期 carried in the corpus? **No — it was dropped at build time.**

Corpus document fields are `content · source_type · source_id · title · url · credibility · doc_type ·
drug_name · licenses · product_count`. **No date field, and 0/10,941 documents mention 有效日期 in their
content.** **Therefore no runtime staleness check is currently possible** — nothing at request time can
tell whether a cited licence is still valid. The date is only recoverable by re-joining to the snapshot
ZIP, which is exactly what this measurement had to do.

The build did filter once: `_meta.stats` records `dropped_expired_or_no_date: 1069` at
`ref_date: 2026/06/30`. **That filter was correct and is already decaying** — **71 licences that were
valid at build time have expired in the 29 days since** (the earliest batch all lapsed on 2026-06-30
itself, the snapshot date).

### Proposed refresh mechanism (proposed, NOT scoped)

id=37 is a **single anonymous bulk-ZIP GET** (`data.fda.gov.tw/data/opendata/export/37/json`, OGDL v1.0,
~4.4 MB) — re-pulling is genuinely cheap, and the manifest already records the intent
(`"note": "Pin + monthly re-pull"`) with `pulled_at: 2026-06-30`, **so the first monthly re-pull is due
now**. The open questions are cadence and whether a diff should gate anything:

- **Cadence** — monthly matches the manifest's own note and comfortably outruns the decay curve (2.1% per
  quarter). Nothing in the data argues for faster.
- **Should a diff gate a ship?** The expensive part is **not** the pull, it is the **re-embed** (10,941
  docs). A refresh that only drops expired rows and swaps representative licences may leave content
  byte-identical — the v196 deep-link ship proved that path exists (*"corpus content byte-identical → NO
  re-embed"*). A diff report (licences expired / newly cancelled / representative changed) would let the
  founder decide per-refresh instead of committing to a fixed re-embed cost.
- **Cheapest independent improvement, orthogonal to cadence:** make representative-licence selection
  **prefer the latest-expiring licence**. It would immediately fix the 11.2% that chose a shorter-lived
  anchor than they had available, and it costs one sort key in the build script.
- **Carrying 有效日期 into the corpus record** would enable a runtime check (or at least an offline audit
  without re-joining a ZIP). Recorded as an option; it is a schema change, not free.

**Cross-ref [ADR 007](decisions/007-tfda-open-data-grounding.md)** and the recorded 在地差異 **(e)** item
*"the authority URLs need periodic review"* (BACKLOG) — **same family, different data layer**: (e) is
link-health on a handful of hand-curated authority homepages; this is validity decay across 17,881
machine-ingested licences. They should probably share one "external data goes stale on a schedule"
mechanism rather than each growing its own cron.

### Copyright note — recorded so it is not re-litigated

The `mcp.fda.gov.tw` page carries a **site-content copyright notice**. That is **distinct** from the
corpus's provenance: the corpus comes from the **OGDL v1.0-licensed open data (id=37)**, and
**deep-linking is not reproduction**. This is consistent with, and independently supports, the existing
**a2 DEFER** reasoning (which already records that a user clicking a citation link in-browser is a normal
outbound link, not an automated crawl). **No action needed.**

---

## Limits

- Findings 1 and 6 are **corpus-wide** measurements over the shipped artifacts; Findings 2–5 rest on the
  founder's single prod gate session (5 queries + 1 retry), so their *frequencies* are anecdotal even
  where the underlying mechanism is code-verified.
- Finding 1's root cause is proven by code inspection plus a 190/190 data match; the collector was **not**
  re-run against the live openFDA API to confirm the same shape is returned today.
- Finding 6's dates come from the **pinned 2026-06-30 snapshot**. Licences cancelled or renewed at TFDA
  since then are invisible here **by construction — which is the finding itself.**
- No product code, corpus, prompt, flag, or keyword list was changed by this baton.
