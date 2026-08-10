# Human-eye gate checklist — PRE-GATE FORM

> **This is a BLANK FORM, not a record.** Copy this file's row table into the gate session, **fill the
> empty cells as you go**, and paste the completed copy into the STATE.md ship entry. The blank cells
> are the point: an unfilled cell is visibly unfilled. A past-tense prose paragraph is not — it can be
> read and nodded at.

**Created 2026-08-05.** Companion to the process rules in `BACKLOG.md` → `[ops] Pre-gate stale-server
SOP` (SOP lines 1–5), which cover *how* to run a gate. This file covers *what each row asserts*.

> **Where these gates run — PROD, and confirm the build first.** Gates using this form run against
> **production**: the deterministic probe's 12/12 was measured on the **prod** index, and
> harness-vs-production divergence is a recorded failure class in this repo (instrument-blind
> **#5**, **#13**, **#14**). **Confirm which build you are gating before row 1** — `/health` returns a
> `revision` field carrying the deployed git SHA, available since **fly 217**; match it against the
> commit under test. A gate against an unconfirmed build is the stale-server hazard one level up.

---

## Why this file exists — read once

**SOP line 4 was added 2026-08-03 and reads:** *"ANY GATE ROW THAT CHECKS CITATIONS MUST NAME THE
EXPECTED DRUG, NOT JUST A SOURCE TYPE OR A COUNT"* — and it already gave the aspirin /
`ACETYLSALICYLIC ACID` example verbatim.

**The fly-215 gate, the same day, recorded 8/8** while row 3 was answered **entirely** from
`Clanza (Aceclofenac) — Contraindications` (its sole source) and row 4 cited `[1] Piroxicam — Boxed
Warning`. Under an ownership check that gate reads **6/8**.

The rule was already written, already correct, already specific — **and it was not executed.** The
same pattern holds for `TECH_DEBT.md:264`, which documented the dual-moiety-key defect on 2026-07-27
and went unapplied across five c2 batons.

**➡️ Prose does not prevent recurrence. A form a reviewer fills in row by row might.** That is the
entire intervention here, and it is deliberately not another SOP line.

**Instrument-blind instance #6** — *"instrument blind to its own target"* — and the **first in the
class to be addressed in a hand-written checklist rather than in code.** CLAUDE.md **Rule 17**
(*tests must verify intent, not just behaviour*) extended from automated tests to human-eye rows.

---

## 🔴 How to fill EXPECTED OWNER — the rule that cost five batons

**EXPECTED OWNER is PLURAL BY CONSTRUCTION. List every corpus key for the substance, never one.**

The DailyMed corpus key is the TFDA backbone `drug_name` **verbatim**
(`scripts/build_dailymed_label_corpus.py:99-105`) — `_normalize_moiety()` is used for resolution
only, never as the key. **So one substance can occupy two keys with different reference labels and
different safety coverage:**

| key | reference label | whitelisted safety sections |
|---|---|---|
| `ASPIRIN` | VAZALORE (OTC) | **NONE** |
| `ACETYLSALICYLIC ACID` | **DURLAZA (Rx)** | **34070-3 · 34073-7 · 43685-7** |

An adjudication that checked only `ASPIRIN` concluded *"aspirin's own label has no safety section"*
and recorded it in BACKLOG as **"6 of 6"**. It is false: *DURLAZA — Contraindications* is **row 57 of
the shipped index**, 375 chars, embedding norm 0.9995, row-aligned. **A single-key EXPECTED OWNER
cell reproduces the exact bug this field exists to catch.**

**Check the citation card's TITLE, not the chip's source label.** The defect is invisible at chip
level — the chip reads "DailyMed", which is true. Only the card title/snippet names the drug.

**Class queries:** write **`n/a — class query`**, never a guess. A class member cited on a class
query is **legitimately owned**; if it is unhelpful the defect is **answer-relevance**, a different
axis, and it must not share a bucket with wrong-object citation. Do not hand-write class rosters.

**Pair / interaction queries:** mark **`pair query — not scored for wrong-object (v1)`**. A
counterpart drug's label can be the correct answer (on `spironolactone + potassium`, the POTASSIUM
CHLORIDE label genuinely answers it), and judging that needs mention-based reasoning, which the
ownership assertion forbids. Record what was cited; do not score it as pass or fail.

**Deriving the key list:** `tests/probes/wrongdrug/owner_assertion.py` holds the ownership join, and
`fixtures.json` records worked examples. ⚠️ **Do not derive keys by substring** — a `STATIN`
substring search returns **NYSTATIN**, an antifungal. Hand-check every candidate.

---

## The form

Fill **OBSERVED OWNER(S)**, **VERDICT** and **NOTES** during the gate. Leave nothing blank at the end
— `—` means "checked, nothing to report"; an empty cell means **not checked**.

**VERDICT vocabulary:** `PASS` · `FAIL` · `n/a` · `UNSCORED` (pair queries) · `BLOCKED` (row could not
be evaluated — say why in NOTES; this is **not** a PASS).

### Seeded rows — the 8 fly-215 gate queries

> Seeded as a **template**, with EXPECTED OWNER pre-filled from the shipped corpus and the
> observation columns **deliberately empty**. The fly-215 verdicts are **not** copied in: that gate's
> recorded **8/8 stands as what was recorded**, and this file is a form for the *next* gate, not a
> re-adjudication of a past one.

| # | query (verbatim, copy-pasteable) | EXPECTED OWNER (all corpus keys) | expected sources | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|---|---|---|
| 1 | `What are the side effects of Metformin in patients with renal impairment?` | **`METFORMIN`** (Glumetza) · **`METFORMIN HCL`** (Metformin HCl) | DailyMed + PubMed | | | |
| 2 | `warfarin 和 aspirin 一起用 safe 嗎` | **pair query — not scored for wrong-object (v1)**. Record what was cited. Keys if needed: `WARFARIN SODIUM` (COUMADIN) · `ASPIRIN` · `ACETYLSALICYLIC ACID` | PubMed (± DailyMed) | | | |
| 3 | `aspirin contraindications and who should not take it` | 🔴 **`ASPIRIN`** (VAZALORE — **no safety sections**) · **`ACETYLSALICYLIC ACID`** (DURLAZA — 34070-3/34073-7/43685-7) | DailyMed | | | |
| 4 | `ibuprofen warnings and precautions` | 🔴 **`IBUPROFEN`** (ADVIL — **no safety sections**) · **`IBUPROFEN LYSINE`** (NEOPROFEN — 34070-3/34073-7/43685-7) ⚠️ see route/form note below | DailyMed safety section(s) | | | |
| 5 | *Cross-row check, not a query:* **confirm NO "FDA" chip appears anywhere in rows 1–4** | n/a — not a citation-identity row | — | | | |
| 6 | `冠脂妥台灣核准的適應症是什麼` | **TFDA row** — expect the citation chip 「TFDA 核准適應症」, not DailyMed. If a DailyMed citation appears, expected owner is **`ROSUVASTATIN CALCIUM`** (CRESTOR) | TFDA | | | |
| 7 | `metformin 腎臟不好的病人可以用嗎` | **`METFORMIN`** · **`METFORMIN HCL`** *(locale-panel row; citation identity still applies)* | DailyMed + PubMed + 在地差異 panel | | | |
| 8 | `What is the mechanism of action of statins?` *(canary)* | **`n/a — class query`** | PubMed-dominated | | | |

### Per-row PASS criteria carried over from the fly-215 gate table

Kept verbatim except where the criterion is what failed. Source:
`docs/local_corpus_deprecation_c1_build.md:622-631`.

| # | PASS | FAIL |
|---|---|---|
| 1 | DailyMed (Contraindications / Warnings) + PubMed chips; answer covers renal dosing + lactic-acidosis risk | an **FDA** chip appears; or safety content thinner than before |
| 2 | Answer warns about bleeding risk; **no "FDA" chip**; every chip's "View source" opens the real document | an FDA chip appears, or a citation opens nothing |
| 3 | ❌ ~~*"A single DailyMed Contraindications citation is a PASS"*~~ — **THIS CRITERION IS WITHDRAWN. It asserted COUNT and passed a wrong-drug citation.** ✅ **A DailyMed Contraindications section whose card title names ASPIRIN or ACETYLSALICYLIC ACID.** Answer must still address who should not take aspirin | zero citations; an answer asserting contraindications with **no** source; **or a safety citation owned by any other moiety** |
| 4 | ✅ **≥1 DailyMed safety citation owned by `IBUPROFEN` or `IBUPROFEN LYSINE`**; answer warns (GI/CV) | no safety citation at all; **or the only safety citations are owned by other moieties** |
| 5 | References panel shows only **PubMed · DailyMed · TFDA** chips; layout normal, no empty slot | any chip reading **"FDA"** ⇒ **STOP and report** (openFDA became live ⇒ re-opens the homepage-URL provenance issue) |
| 6 | Chip 「TFDA 核准適應症」 renders; 查看來源 opens `mcp.fda.gov.tw/im_detail_pdf/<字號>` (a **licence detail page**, not a PDF) | no TFDA citation ⚠️ then check phrasing — weak phrasings legitimately miss (`冠脂妥適應症` cosine 0.5632 < 0.6) |
| 7 | 在地差異 panel appears with TFDA/NHI authorities; `?localeDebug=1` shows `country=TW · level=… · tier=1` | panel missing or empty |
| 8 | Normal answer, no safety-section intrusion, no FDA chip | shape visibly changed |

### ⚠️ Row 4 — non-blocking route/form divergence

`IBUPROFEN LYSINE` counts as a **legitimate owner** (same active moiety; a lysine salt is not a class
sibling — consistent with the aspirin / acetylsalicylic acid treatment). **But NEOPROFEN is an
intravenous neonatal product** for patent ductus arteriosus closure. If row 4's only owned citation
is NEOPROFEN, that is **`correct_owner` + `owner_route_form_divergent`** — record the flag in NOTES;
**do not fail the row for it.** "An owner exists" and "that owner is clinically applicable" are
separate claims on separate axes and must not be merged. Same boundary as the class-query exclusion.

---

## Adding a row

1. Write the query **verbatim and copy-pasteable** — weak phrasings make rows fail for unrelated
   reasons (see SOP line 5's TFDA note).
2. Fill EXPECTED OWNER with **every** corpus key for the substance, hand-checked. Never one key,
   never a substring result.
3. If it is a class or pair query, mark it as such — do **not** invent an owner.
4. State the PASS criterion in terms of **identity**, not count. *"≥1 safety citation"* and
   *"3 citations"* are the shape that failed.

## Related

- Process rules (stale server · deep-links · expected drug · same-day control · TFDA phrasing):
  `BACKLOG.md` → `[ops] Pre-gate stale-server SOP`
- The ownership join and its six outcomes: `tests/probes/wrongdrug/owner_assertion.py` ·
  [`docs/t1_ownership_assertion_20260805.md`](t1_ownership_assertion_20260805.md)
- Why this file is a form and not more prose:
  [`docs/t1_followon_20260805.md`](t1_followon_20260805.md) §1
- The dual-key defect: `TECH_DEBT.md:264` (data) and `[P2 · adjudication method / corpus dual-key]`
  (method — it recurred *after* being documented)
