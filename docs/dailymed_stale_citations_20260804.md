# DailyMed corpus staleness — what a user actually gets today (2026-08-04)

**READ-ONLY. Report only; nothing proposed, nothing built.** No rebuild, no re-embed, no `--resolve`.
Shipped index byte-intact. Branch only; not pushed. **Independent of the c2 decision.**

Tags: **`CONFIRMED`** · **`REFUTED`**.

---

## ❌ FIRST — a REFUTED claim of my own

**Phase 1b Part 2 reported "11 `source_id`s vanished upstream" and framed it as DailyMed having removed
those sections. That is WRONG.**

`CONFIRMED`: all **11 belong to exactly 2 setids** — `TOLTERODINE TARTRATE` (5 sections) and
`ZOLPIDEM TARTRATE` (6 sections) — **the two setids my own fetch failed on**. They are absent from the
re-parse because **I never successfully fetched them**, not because DailyMed removed anything.

> ### **Genuinely vanished upstream: 0.**

**And the two labels are not withdrawn at all.** Live check:

| setid | `drugInfo.cfm` (the citation deep-link) | v2 API `spls/{setid}.xml` |
|---|---|---|
| `d7274947…` TOLTERODINE | **HTTP 200** → *"HIGHLIGHTS OF PRESCRIBING INFORMATION … **Detrol® LA**"* | **404** |
| `404c858c…` ZOLPIDEM | **HTTP 200** → *"HIGHLIGHTS … **AMBIEN CR**"* | **404** |

**The user-facing page serves the correct, current label. Only the API XML 404s.** No redirect, no
"not found" page, no superseded notice.

**➡️ So this is a DailyMed API-vs-web inconsistency that blocks our REFRESH path, not our CITATION
path.** It affects our ability to re-parse those labels; it does **not** affect what a user sees. It is
also why any future refresh must **fail loud on a 404** rather than silently treat the sections as
deleted — which is precisely the misreading this correction is fixing.

*(Corrected in place in `docs/c2_phase1b_measurement_20260804.md` and in the TECH_DEBT staleness entry.)*

---

## ✅ The real finding: **30 sections have drifted**, 18 of them SAFETY sections `CONFIRMED`

Same `source_id`, same setid, **different text** between our index and a fresh parse of the same label.

| LOINC | section | drifted |
|---|---|---|
| **43685-7** | Warnings and Precautions | **10** |
| 34068-7 | Dosage and Administration | 8 |
| 34067-9 | Indications and Usage | 4 |
| **34073-7** | Drug Interactions | **4** |
| **34070-3** | Contraindications | **2** |
| **34066-1** | Boxed Warning | **2** |
| | **safety subtotal** | **18 of 30** |

### The largest safety drifts

| moiety | section | ours | live | delta |
|---|---|---|---|---|
| RILUZOLE | Warnings | 2 172 | 2 913 | **+741** |
| UPADACITINIB HEMIHYDRATE | Warnings | 13 137 | 13 809 | **+672** |
| BUPRENORPHINE HYDROCHLORIDE | Warnings | 21 774 | 21 113 | **−661** |
| BARICITINIB | Warnings | 12 735 | 13 389 | **+654** |
| DEUCRAVACITINIB | Warnings | 8 091 | 8 579 | **+488** |
| **PROGESTERONE** | **Contraindications** | **830** | **1 135** | **+305** |
| PROGESTERONE | Warnings | 1 224 | 1 047 | −177 |
| BUPRENORPHINE HYDROCHLORIDE | Drug Interactions | 10 705 | 10 533 | −172 |

---

## What the user sees — the mismatch, stated concretely

The setid still resolves, so **the deep-link opens the CURRENT label** while **our index holds the OLD
text**. The citation card's snippet and the page it opens can therefore disagree.

**Both directions occur, and they fail differently:**

- **Our text is SHORTER than live (`+` deltas — RILUZOLE +741, PROGESTERONE contraindications +305):**
  we are **missing safety content the current label contains**. The user reads a contraindications
  snippet that omits 305 characters the real label now has. **This is the worse direction** — an
  omission is invisible to the reader.
- **Our text is LONGER than live (`−` deltas — BUPRENORPHINE warnings −661):** we are **serving text
  that is no longer in the label**. Clicking through, the user cannot find the sentence we showed them.

### 🔴 Can stale safety text be presented under a live-looking citation? **YES — `CONFIRMED`.**

That is exactly the state for **18 safety sections** right now: the chip renders, the deep-link works
and opens the real DailyMed page, the label is current — **and the text we quoted is a superseded
revision.** Nothing in the UI signals a version. The citation looks maximally healthy.

**Same honesty family as the pre-c1 empty stubs on `/explore`** — content we serve that no longer
matches what it claims to be — but with an important difference: **the empty stubs were visibly empty,
whereas drifted text is plausible, well-formed, and was true when it was captured.** It cannot be
spotted by reading the card.

### Scale, stated honestly

**30 of 4608 documents (0.65%)** are known-drifted **as of this one comparison**. That is a **floor, not
a rate**: it counts only labels whose text changed between the snapshot and today, and the corpus has
**no refresh mechanism at all** (`monthly_re_pull` is prose, `db_published_date` is null, no CI —
`docs/c2_phase1c_20260804.md` Part 5.3), so **the number can only grow** and nothing measures it.

---

## Rule 18 — limits

- The comparison covers **1036 of 1038** pinned setids. The 2 excluded are the Detrol LA / AMBIEN CR
  API-404 pair above; their drift status is **unknown**, not zero.
- "Drift" is **exact string inequality** on section text. It counts whitespace/markup churn the same as
  a clinical revision. **The 8 large safety deltas listed above are substantive by size; the long tail
  is not individually adjudicated** — I did not read all 30 diffs.
- **No clinical assessment of any drift was made.** Whether a +305-char contraindications change is
  clinically material is a medical judgement, deliberately not attempted here.
- One snapshot comparison on one day. No trend, no rate.
