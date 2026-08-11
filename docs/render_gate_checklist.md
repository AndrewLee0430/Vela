# Render gate checklist — PRE-GATE FORM

> **This is a BLANK FORM, not a record.** Copy the row table into the gate session, **fill the empty
> cells as you go**, and paste the completed copy into the STATE ship entry. The blank cells are the
> point: an unfilled cell is visibly unfilled.

> ## ✅ GATE 1 RUN AND PASSED — 4/4, founder-run, human-eye, against **fly 216** (2026-08-07)
> **This is the first gate ever run with a form in this repo.** The completed rows are recorded
> below. To run a NEW gate, copy the tables and blank the observation columns again — do not
> overwrite this record.

**Created 2026-08-07.** For gates that check **what a rendered public page CLAIMS** — as opposed to
`docs/human_eye_gate_checklist.md`, which checks **whose label was cited on a Research query**.

---

## Why this is a separate file and not extra columns on the ownership form

The ownership form's per-row fields are `query · EXPECTED OWNER · observed owner(s) · verdict`. On a
render gate there is **no query** (the input is a fixed URL), and **`EXPECTED OWNER` is `n/a` on every
single row** — the entries under test have no owner at all. A column that is `n/a` on every row is the
signal that the instrument does not match the measurement.

Widening the ownership form was considered and **rejected** (founder decision 2026-08-07): a form's
value is that opening it tells you what to fill in, and a form covering two unrelated question types
degrades into a grab-bag. **Two narrow forms beat one wide one.**

### 🔴 This form does NOT close `TECH_DEBT.md` → the `[P2 · gate-design / Rule 17 — 6th instance]` entry (was `TECH_DEBT.md:110`)

That entry closes on a gate that **used the OWNERSHIP form on a Research gate**. Using a *different*
form for a *different* kind of gate is not that, and must not be recorded as if it were. `:110`
**stays open.** The ownership form still has never been used.

---

## What a render gate is for

Unit tests assert on the **data** a renderer produces. They cannot see the **page**. Everything in the
"cannot be unit-tested" rows below is there because it was explicitly flagged as unverified when the
code shipped — legibility and locale fallback are properties of the rendered page, not of a dict.

**Fill in every cell.** `—` means "checked, nothing to report"; an empty cell means **not checked**.

**VERDICT vocabulary:** `PASS` · `FAIL` · `n/a` · `BLOCKED` (could not be evaluated — say why in
NOTES; this is **not** a PASS).

---

## Gate 1 — open-item #7: pre-c1 empty `local` stubs are tombstoned

**Change under test:** `a7e47c2` — a `source_type == 'local'` citation keeps its slot and its `[N]`
but renders with **no credibility pill** and **no source label**, reading *"Source withdrawn"* /
*"來源已撤回"*, and is excluded from the source-chip summary.

❌ ~~⚠️ **Requires a deployed build.** Nothing was deployed when this form was written.~~ → ✅ **RUN 2026-08-07 against fly 216** (deployed the same day, health 200). **Result: 4/4 PASS, plus both of the rows a unit test could never check.**

### Row expectations — derived read-only from prod on 2026-08-06, and from `_augment_citations` output, NOT from a rendered page

| # | URL (copy-pasteable) | locale | expected slots | expected tombstones at `[N]` | observed slots | observed tombstones | credibility pill ABSENT on every tombstone? | every prose `[N]` resolves to a slot? | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/q/6-Si0boVrZo` | en | **2** | **[2]** | 2 ✅ | [2] ✅ | ✅ none | ✅ yes | **PASS** | chips `PubMed: 1`; "Source withdrawn" |
| 2 | `https://vela.an-tho.com/q/7xI-q0dxnVg` | **zh-TW** | **5** | **[1] [4] [5]** | 5 ✅ | [1] [4] [5] ✅ | ✅ none | ✅ yes | **PASS** | chips `PubMed: 2`; **「來源已撤回」** |
| 3 | `https://vela.an-tho.com/q/Eclwok8n_Kw` | en | **5** | **[1] [4] [5]** | 5 ✅ | [1] [4] [5] ✅ | ✅ none | ✅ yes | **PASS** | chips `PubMed: 2`; "Source withdrawn" |
| 4 | `https://vela.an-tho.com/explore/metformin-contraindications-renal` | en | **3** | **[2]** | 3 ✅ | [2] ✅ | ✅ none | ✅ yes | **PASS** | `explore_page` path confirmed independently of rows 1–3 |

**Per-row PASS criterion — identity of the claim, not a count:**
✅ every tombstoned slot shows **no credibility pill**, **no source name**, and **no "View source"
link**, while every non-tombstoned slot keeps its original number and its own source label and pill.
❌ any tombstone showing **"Official"**, **"Local"**, or **"FDA"**; any non-local citation whose
number changed; any prose `[N]` with no corresponding slot.

⚠️ **Row 4 is `explore_page`, a different table and code path** (`server.py:2676`) that reuses the
same renderer. It is in this gate deliberately — passing rows 1–3 does not establish row 4.

### Rows that unit tests CANNOT check — the reason this gate exists

| # | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|
| 5 | **Legibility — does the tombstone read as withdrawn at a glance?** The source label renders in `#a0aec0` (grey), inherited from the pre-existing `local` config; no CSS was added for the tombstone | A reader scanning the references can tell the slot is withdrawn **without reading closely**. Contrast against the page background is sufficient | `#a0aec0` reads clearly against the page background. A tombstone card beside a PubMed card is **unmistakable at a glance** — no coloured source name, no pill, no "View source" link, visibly dimmer | **PASS** | 🔴 **The row that justified the whole form.** No unit test could have checked this — the correction is only worth shipping if it is *visible*, and grey-on-grey was the named risk |
| 6 | **Both locales render their own string, not a fallback** | Row 2 (zh-TW) shows **「來源已撤回」**; rows 1/3/4 (en) show **"Source withdrawn"**. Neither shows the other language, an empty label, or a raw key | Row 2 correct. **And the locale resolves END TO END, not just the one string** — `參考來源`, `同儕審查`, `檢視來源 ↗` all render in zh-TW | **PASS** | Stronger than the criterion asked for: a single-string hit could have masked a broken locale path; the whole page is localised |

**Why 5 is here:** the correction is only worth shipping if it is *visible*. A tombstone the eye
slides past leaves the page reading as though the slot were an ordinary source — the defect would be
fixed in the data and not in practice. **Grey-on-grey is the specific risk**, and it was never
checked; `#a0aec0` was inherited, not chosen for this purpose.

**Why 6 is here:** the code asserts `_STRINGS[locale]["sourceWithdrawn"]` resolves, but only a
rendered page proves the right locale reached the template — row 2 is the only zh-TW row in the set,
so it is the only row that can catch a locale-resolution fault.

### Known and expected — do NOT record these as failures

- **Prose markers point at tombstoned slots.** Rows 2 and 3 cite `[1]`, `[4]`, `[5]` in the answer
  text, all tombstoned. This is **intended**: the alternative — deleting or hiding the entries —
  renumbers the list and re-points the prose at the **wrong** source. The slot is kept precisely so
  the reference still resolves.
- **The scaffolding snippet is still visible** (e.g. `"Drug: Warfarin\n\nContraindications:\n4"`).
  **Intended** (founder decision 2026-08-07): it shows the reader *why* the slot was withdrawn.
  A withdrawn slot with no visible reason would be worse.
  - ✅ **The gate VINDICATED this decision.** Row 3's `[5] Warfarin - Safety` rendered as
    *"Drug: Warfarin Contraindications: 4 Warnings and Precautions:"* — **truncated mid-field, because
    that field had no value at all.** The emptiness is visible to the reader directly, which is
    precisely the argument for keeping it. Hidden, the slot would read as withdrawn for no evident reason.
- **The 8 stub citations remain in the prod database.** Deliberate residue — deleting them hits the
  same renumbering hazard. See the `[P2 · honesty / persisted artifacts]` TECH_DEBT entry.

---

## Gate 2 — B1: landing below-fold sections (BLANK — founder runs post-deploy)

**Change under test:** the B1 landing-sections commit of 2026-08-11 (`fix(landing): [B1] …` —
SHA recorded in the baton report and the STATE draft entry; fill in here at gate time, and
**confirm `/health` `revision` matches it before row 1**).

**What shipped:** three sections (`#who` / `#how` / `#privacy`) + expanded footer below the hero
on `/`; the `.landing-bg` gradient re-scoped from the hero+footer wrapper to the first-viewport
div; a scroll-hint chevron at the hero's bottom center. **The hero is claimed UNCHANGED** — that
claim is row 1, and it is the row most worth failing honestly: the gradient element changed from
~100vh+footer to exactly 100vh, a ~4vh center shift argued imperceptible. If it is visible, say so.

| # | URL (copy-pasteable) | locale / scheme | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/` | en · **light** | **hero unchanged vs fly 226** | headline, input, chips, privacy line, warm gradient all read as before; no layout shift, gradient center not visibly moved | | | |
| 2 | `https://vela.an-tho.com/` | en · **dark** | hero unchanged vs fly 226 | same, on the dark gradient | | | |
| 3 | `https://vela.an-tho.com/` | en · light | **section legibility** | scroll through §who/§how/§privacy: all text readable, step numbers visible, §how's tinted band distinct from the page | | | |
| 4 | `https://vela.an-tho.com/` | en · **dark** | section legibility | same in dark — this is the fly-219 regression class; any washed-out text ⇒ FAIL | | | |
| 5 | `https://vela.an-tho.com/` | en · either | **chevron subtlety** | visible-but-quiet at hero bottom; fades on first scroll; clicking it scrolls to §who; does NOT overlap the privacy line | | | |
| 6 | `https://vela.an-tho.com/` | en · either · **mobile width** (≤ 390px) | mobile | sections stack single-column, no horizontal scroll, footer wraps cleanly | | | |
| 7 | `https://vela.an-tho.com/` | **ar** (RTL) · either | RTL | sections right-align correctly, step numbers/text order sane, chevron still centered | | | |
| 8 | `https://vela.an-tho.com/` | **zh-TW** · either | locale strings | §who/§how/§privacy render zh-TW text (not en fallback); footer anchors labelled in zh-TW | | | |
| 9 | *(no URL — content row)* | en | **founder copy approval** | the founderNote small-type line ("built and maintained by one independent developer…") — founder APPROVES the wording or names the edit | wording as shipped in `9c8aed3` | **PASS — PRE-APPROVED** | ✅ founder approved the shipped wording 2026-08-11, PRE-DEPLOY (recorded at the fly-227 deploy baton); this row RECORDS the approval rather than asking for it |

**Explore-CTA row deliberately ABSENT:** P0.1 verdict was NOT safe-to-link (one published explore
page, no index route — bare `/explore` serves the landing itself). §how ships without the CTA;
there is nothing to gate.

**Known and expected — do NOT record as failures:** the three privacy chips and the research-tool
disclaimer appear BOTH in the hero zone and in §privacy — deliberate verbatim reuse (D2), not a
duplication bug. The new-key MT (15 locales) is NOT native-reviewed — recorded in STATE; a wording
that reads oddly in a non-en locale is reviewer-queue material, not a gate FAIL, unless it makes a
CLAIM the English does not (that IS a FAIL — the fly-225 class).

---

## Gate 3 — B2: landing card-based visual upgrade (BLANK — founder runs post-deploy)

**Change under test:** the B2 commit of 2026-08-11 (`feat(landing): [B2] …` — SHA in the baton
report; fill in at gate time and **confirm `/health` `revision` contains it before row 1**).

**What changed vs Gate 2:** how-steps section REPLACED by a three-card FEATURES section (reused
mode-selector keys + the selector's Pro tag on Explain); privacy became FOUR cards (the three
shipped promises + "No account required to try.") with an honest-limits sub-block under them; the
WHO block gained a coral inline-start accent bar and a stepped-up final line; cards are bg-bg-1,
rounded-2xl, no borders, shadow in light only; accent = coral icon chips (the B1 badge DNA).
**Hero untouched — pixel-identical to fly 227 is the claim; row 1 exists to falsify it.**

| # | URL | locale / scheme | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/` | en · **light** | **hero pixel-unchanged vs fly 227** | headline, input, chips, gradient identical; the only new pixel in the first viewport is nothing — the chevron was already there | | | |
| 2 | `https://vela.an-tho.com/` | en · **dark** | hero pixel-unchanged vs fly 227 | same | | | |
| 3 | `https://vela.an-tho.com/` | en · light | **feature cards legibility** | three white cards read one step off the tinted band; coral icon chips visible; Explain's Pro tag matches the mode selector's; text ≥ comfortably readable | | | |
| 4 | `https://vela.an-tho.com/` | en · **dark** | feature cards legibility | cards read as ELEVATED navy on the deep gradient — no muddy shadow (shadow is light-only), no washed-out text | | | |
| 5 | `https://vela.an-tho.com/` | en · light | **privacy cards + limits block** | 2×2 cards, full sentences (no invented titles); the limits sub-block reads QUIETER than the cards but still legible — it must not disappear | | | |
| 6 | `https://vela.an-tho.com/` | en · **dark** | privacy cards + limits block | same, dark | | | |
| 7 | `https://vela.an-tho.com/` | en · either · **mobile ≤ 390px** | stacking | features 3→1 col, privacy 2×2→1 col, equal-height cards don't stretch oddly, no horizontal scroll | | | |
| 8 | `https://vela.an-tho.com/` | **ar** (RTL) · either | RTL grid + accent bar | grids flip; the WHO coral bar sits on the RIGHT (inline-start); icon chips lead each card correctly | | | |
| 9 | `https://vela.an-tho.com/` | en · either | **WHO accent treatment** | the manifesto block reads as deliberate (bar + coral final line), not like a styling accident; "This tool is for you." is the emphasis point of the section | | | |
| 10 | `https://vela.an-tho.com/` | en · either | chevron still behaves | visible at hero bottom, fades on first scroll, click scrolls to §who | | | |

**No explore row** — this baton touches no shared renderer.

**Known and expected — do NOT record as failures:** privacy chips appear in the hero line AND as
§privacy cards (deliberate verbatim reuse); the limits sub-block is INTENTIONALLY quiet (R5 —
honest-limits register, not a fourth band); the 105 new MT cells are not native-reviewed (reviewer
subset re-enumerated in STATE) — odd phrasing in a locale is reviewer-queue material unless it
STRENGTHENS a claim (that is a FAIL — the fly-225 class).

---

## Adding a gate to this file

1. Name the **change under test** by commit SHA.
2. Give each row a **copy-pasteable URL and its locale** — locale is a row property here, not a
   global.
3. State expectations as an **identity or a claim** (*"no credibility pill"*), never as a count
   (*"3 citations"*). Counting is the failure mode that let the fly-215 gate pass a wrong-drug
   citation.
4. Add a row for **anything a unit test cannot see** — legibility, locale resolution, layout,
   link behaviour. That is the whole reason a human is running this.

## Related

- **Ownership** gates (whose label was cited on a Research query):
  [`docs/human_eye_gate_checklist.md`](human_eye_gate_checklist.md)
- Process rules (stale server · deep-links · expected drug · same-day control · TFDA phrasing):
  `BACKLOG.md` → `[ops] Pre-gate stale-server SOP`
