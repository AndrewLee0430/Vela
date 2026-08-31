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
*(⚠️ Correction 2026-08-20: this line briefly read `a8b8e1e` — a misplaced edit; `a8b8e1e` is the
ADR-007 (d) commit and belongs to Gate 7 below. Gate 1 ran 2026-08-07 against fly 216 on the
tombstone commit `a7e47c2`; restored, not silently.)*

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

## Gate 2 — B1: landing below-fold sections

> ## ✅ GATE 2 CLOSED (2026-08-11, against fly 227) — FUNCTIONAL PASS · visual finding → B2
> Founder-run. Functional rows passed; the founder's visual finding — sections read as bare
> text — spawned the B2 card system. Row 9 (founderNote copy) was PASS — PRE-APPROVED. The
> observation cells below were not filled row-by-row; the verdict is recorded here and in the
> STATE B0+D3+B1 entry. **No pending rows remain.**

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

## Gate 3 — B2: landing card-based visual upgrade

> ## ⚠️ GATE 3 CLOSED (2026-08-12, against fly 228) — PARTIALLY RUN, honestly recorded
> **Rows 7 (mobile) and 8 (ar RTL) were run by founder eyes: both PASS** — the ar screenshot
> (reviewed 2026-08-12) showed the RTL grid flipping, the inline-start accent placement, and no
> breakage. Rows 7/8 are filled below. **The remaining rows were SUPERSEDED by the founder's
> aesthetic verdict — too plain → B3** — and were never run. This is a partial run recorded as
> such, not a pass. **No pending rows remain.**

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
| 7 | `https://vela.an-tho.com/` | en · either · **mobile ≤ 390px** | stacking | features 3→1 col, privacy 2×2→1 col, equal-height cards don't stretch oddly, no horizontal scroll | stacked correctly, no horizontal scroll (founder eyes) | **PASS** | run 2026-08-12 against fly 228 |
| 8 | `https://vela.an-tho.com/` | **ar** (RTL) · either | RTL grid + accent bar | grids flip; the WHO coral bar sits on the RIGHT (inline-start); icon chips lead each card correctly | RTL grid flipped, inline-start bar correct, no breakage (founder screenshot, reviewed 2026-08-12) | **PASS** | the only two rows run; the rest superseded → B3 |
| 9 | `https://vela.an-tho.com/` | en · either | **WHO accent treatment** | the manifesto block reads as deliberate (bar + coral final line), not like a styling accident; "This tool is for you." is the emphasis point of the section | | | |
| 10 | `https://vela.an-tho.com/` | en · either | chevron still behaves | visible at hero bottom, fades on first scroll, click scrolls to §who | | | |

**No explore row** — this baton touches no shared renderer.

**Known and expected — do NOT record as failures:** privacy chips appear in the hero line AND as
§privacy cards (deliberate verbatim reuse); the limits sub-block is INTENTIONALLY quiet (R5 —
honest-limits register, not a fourth band); the 105 new MT cells are not native-reviewed (reviewer
subset re-enumerated in STATE) — odd phrasing in a locale is reviewer-queue material unless it
STRENGTHENS a claim (that is a FAIL — the fly-225 class).

---

## Gate 4 — B3: paper redesign of the landing below-fold

> ## ❌ GATE 4 CLOSED (2026-08-12) — NEVER RUN, superseded
> The founder's design review of fly 229 ratified B4 (final form) before any row was run.
> Recorded as never-run, not as passed. **No pending rows remain.** The rows below stand as
> the historical form only.

**Change under test:** the B3 commit of 2026-08-12 (`feat(landing): [B3] …` — SHA in the baton
report; fill in at gate time and **confirm `/health` `revision` contains it before row 1**).

**What changed vs Gate 3:** editorial/print register — paper palette (three new R=255-pinned
tokens in the hero's 20–25° hue band), serif body type (Source Serif 4, Latin subset,
system-fallback elsewhere), no icons / no shadows / no band tints below the fold, coral
below-fold = zero (sole survivor REMOVED with the Pro tag per the R4 honesty fix), feature-card
metadata rows (LANGUAGES / ACCESS) + ink pills, privacy as editorial two-column, `max-w-7xl` /
`py-32 md:py-40` rhythm. **Hero claim (AMENDED, R2 Option B): unchanged except the LIGHT outer
gradient stop warmed from #ffffff to paper — the fold seam is structurally gone.** Dark palette
unchanged; dark gets the new layout + type only.

| # | URL | locale / scheme | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/` | en · **light** | **hero: amended claim, both halves** | (a) everything except the outer stop identical to fly 228; (b) scrolling past the fold shows NO seam — hero blends into the paper page | | | |
| 2 | `https://vela.an-tho.com/` | en · **dark** | hero unchanged | dark hero identical to fly 228 (gradient untouched) | | | |
| 3 | `https://vela.an-tho.com/` | en · light | **paper page + cards legibility** | one continuous paper field; paper-2 cards read as surfaces WITHOUT borders or shadows; **hairlines visible but quiet** (the metadata separators must not vanish into paper-2) | | | |
| 4 | `https://vela.an-tho.com/` | en · **dark** | dark = today's palette, new layout | navy family unchanged; cards elevated; hairlines visible; nothing muddy | | | |
| 5 | `https://vela.an-tho.com/` | en · either | **serif register** | WHO + card descriptions + limits block render in Source Serif; the sans/serif contrast reads deliberate, not accidental | | | |
| 6 | `https://vela.an-tho.com/` | **zh-TW** · either | serif fallback typography | CJK falls back to the system stack — must look intentional, not broken (no mixed-weight mush, no faux-italic) | | | |
| 7 | `https://vela.an-tho.com/` | **ar** (RTL) · either | RTL: fallback type + pill arrow | serif fallback acceptable; WHO ink bar sits inline-start (right); **pill arrow points LEFT and its hover shift moves LEFT** | | | |
| 8 | `https://vela.an-tho.com/` | en · either | **pill hover** | arrow translates ~4px on hover, 200ms, smooth; pill inverts correctly in dark | | | |
| 9 | `https://vela.an-tho.com/` | en · **md+ then mobile** | privacy editorial layout | md+: declaration left (~1/3), promise rows right with hairline separators; mobile: declaration stacks ABOVE the rows | | | |
| 10 | `https://vela.an-tho.com/` | en · **mobile ≤ 390px** | full-scroll | hero → who → features (stacked cards) → privacy → footer, no horizontal scroll, pills tappable | | | |
| 11 | *(no URL — truth row)* | — | **metadata truth sign-off** | founder confirms the ACCESS values match deployed reality: Research/Verify = "No account needed" (anonymous-usable), Explain = "Free account required" (sign-in wall; text free; upload Pro) | | | |

**Known and expected — do NOT record as failures:** the hero composer keeps its `shadow-sm`
(above the fold, out of scope); 10 of 16 locales render serif via system fallback by design
(rows 6–7 judge acceptability, not identity); the four new metadata strings are MT baseline,
not native-reviewed (reviewer subset now 9 keys — odd phrasing is reviewer-queue material
unless it STRENGTHENS a claim, which is a FAIL).

---

## Gate 5 — B4: final-form landing

> ## ⚠️ GATE 5 CLOSED (2026-08-12, against fly 230) — INFORMALLY RUN, superseded by LOCAL ITERATION MODE
> The founder's scroll review judged the direction right (**「好很多了」**) AND surfaced the
> panel pin-overlap defect → hotfixed as **fly 231** (`4be2f55`). The formal 10-row run is
> **SUPERSEDED**: the landing entered **LOCAL ITERATION MODE** (D-B4.1-1) — UI iterates on
> localhost, no per-iteration deploys, no per-iteration gates. **The definitive gate runs ONCE,
> at the stabilization deploy — it will be Gate 6, form to be written then.** No pending rows
> remain here; the rows below stand as the historical form only.

**Change under test:** the B4 build commit of 2026-08-12 (SHA in the baton report; **confirm
`/health` `revision` contains it before row 1**). Gate 4 was superseded before running — this is
the operative form for the fly-229→230 landing change.

**What changed:** warm-white paper page (#FFF9F5 family), hero spotlight replacing the full-page
radial, black GSAP scroll panel replacing WHO, simplified bordered cards (no icons, no metadata
rows), privacy section REMOVED (PRD §0.3 amended; disclaimer keeps its footer render), landing is
LIGHT-ONLY. **The old "hero pixel-identical" claim is retired — this gate judges the new design.**

| # | URL | context | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/` | desktop | **hero spotlight + clean paper bg** | warm glow sits behind the composer only, soft edges, no banding; the rest of the viewport is clean paper; headline/chips/privacy line unchanged in layout | | | |
| 2 | `https://vela.an-tho.com/` | desktop, normal motion | **panel full cycle** | scroll: panel widens 70→95vw, pins; intro → seg1 → seg2 → seg3 cross-fade in order; 3 dots appear during segs with the current one highlighted; unpins after seg3; **reverse scroll plays it backwards cleanly** | | | |
| 3 | `https://vela.an-tho.com/` | desktop | **scroll performance** | no jank/stutter through the pinned range on a normal machine; page scroll elsewhere unaffected | | | |
| 4 | `https://vela.an-tho.com/` | desktop, **OS reduced-motion ON** | reduced-motion static | NO pin, NO width animation: intro + three segments statically stacked, each with its pill; dots hidden; cards don't fade in | | | |
| 5 | `https://vela.an-tho.com/` | **mobile ≤ 390px** | mobile static stack | same static panel stack, full-width; pills tappable; no horizontal scroll anywhere | | | |
| 6 | `https://vela.an-tho.com/` | **ar** (RTL) | RTL | panel text centered correctly; ALL pill arrows point LEFT and hover-shift LEFT; cards read correctly | | | |
| 7 | `https://vela.an-tho.com/` | **zh-TW** | serif fallback | panel serif lines + card descriptions fall back to system faces and look intentional | | | |
| 8 | `https://vela.an-tho.com/` | desktop | **cards + borders legibility** | near-white sheets with visible-but-quiet hairline borders + faint shadow on the warm page; serif descs readable | | | |
| 9 | `https://vela.an-tho.com/` | any | disclaimer visible | the research-tool disclaimer renders in the footer (its surviving render point) | | | |
| 10 | *(no URL — content row)* | en | **copy sign-off** | founder's final word on the panel copy (intro + 3 tags/descs) and the 3 card descriptions AS RENDERED | | | |

**Known and expected — do NOT record as failures:** the landing no longer follows the theme
(D-B4-1 — html.dark users get the light landing by design; product surfaces still follow theme);
the 165 MT cells are not native-reviewed and the pipeline is frozen (odd non-en phrasing is
future-round material unless it STRENGTHENS a claim — that is a FAIL); the hero composer keeps
its small shadow.

---

## Gate 6 — B4.1b→B4.6: the stabilization gate for LOCAL ITERATION MODE

> ## ✅ GATE 6 RUN AND PASSED — 12/12, founder-run, against the LOCAL build (2026-08-14)
> **Founder verdict, verbatim:** *"GATE 6: RUN AND PASSED (founder, 2026-08-14, local build on
> :4321) — 12/12 PASS."*
>
> ✅ **ROW 8 IS NOW COMPLETE — PASSED BY REAL DEVICE (founder, 2026-08-17).** On a real iPhone the
> demo **PLAYS** and **SEEK WORKS**. That closes the touch-play half that the original run had to
> defer.
>
> ⚠️ **The original caveat is PRESERVED AS HISTORY, not deleted** — it is the record of how the
> row was first run: *"Row 8 (mobile) was verified via DevTools 390px emulation because LAN access
> to the local server could not be established (Chrome fell back to search; firewall/IP not
> diagnosed) — controls visible, static panel, no horizontal scroll; the TOUCH-PLAY half is
> deferred to the prod re-check."* Rows the founder explicitly confirmed at the original run:
> **word reveal forward · panel height constant while widening · video pauses on scroll-away ·
> mobile controls present.**
>
> **Deployed as fly 233** (2026-08-15), `/health` `revision` = `78b96ab6b052ba501451eec33c4153a73f282bcb`.
>
> ❌ ~~**THE DEFERRED TOUCH-PLAY CHECK HAS A KNOWN LIKELY FAILURE WAITING FOR IT.**~~ **THAT
> PREDICTION IS REFUTED — recorded, not quietly deleted.** Both of the following are true, and
> neither cancels the other:
> - **The mechanism is real and still measured.** The shipped mp4 serves **no HTTP byte ranges**:
>   `Range: bytes=0-1023` → **200** with the full 2,325,186 bytes, no `Accept-Ranges`, no
>   `Content-Range`. Cause: `fastapi==0.111.0` pins Starlette ≈0.37, and **Range support landed in
>   Starlette 0.39.0 — NOT 0.45** (0.38.6 has none; 0.39.0 has `accept-ranges`, `206` and
>   `_parse_range_header`). The minimum bump is therefore **`fastapi 0.115.2`, not 0.115.7**.
> - **No user-visible harm was observed.** The video plays and seeks on a real iPhone. A browser
>   that simply fetches the whole file is entirely **consistent** with seek working.
>
> ⚠️ **Evidence boundary: ONE 2.3 MB file, ONE device, ONE network.** This does **not** clear the
> gap for larger files or poor mobile networks — which is exactly where whole-file fetching is the
> failure ranges exist to prevent. Filed as `[OTHER][P2]` TECH_DEBT (correctness gap, no observed
> harm), **not** as a defect.
>
> ~~**The prod re-check is now rows 1, 2 and 5+6 — row 8 is done.**~~ ✅ **PROD RE-CHECK DONE —
> founder-run 2026-08-18 against `https://vela.an-tho.com/` on fly 236 (revision `35ce47e`):
> rows 1, 2 and 5+6 = 4/4 PASS.** Hero clean with no horizontal scroll at any width · panel
> near-black / solid-paper as specified · video plays/pauses/resumes correctly · quality and
> poster correct. Combined with row 8 (real iPhone, 2026-08-17):
> 🎉 **GATE 6 IS FULLY CLOSED — 12/12 local + full prod subset. No pending rows remain.**

**Change under test:** the **11 unpushed commits `4d0c8fe`…`8b173e1`** (B4.1b → B4.6), i.e.
everything the founder has been reviewing on localhost. ⚠️ The deploy will also carry
`61d49f1` (a docs-only STATE header bump already on `origin/main`), so **12 commits separate
prod from HEAD** — 11 of them product. Prod is **fly 232 = `2c1e5db`**; confirm `/health`
`revision` matches `8b173e1` before running the prod subset.

**ALL ROWS ARE LIGHT.** D-B4-1 makes the logged-out landing light-only, so there are no dark
rows in this gate by design — that is not an omission.

**What changed vs fly 232:** panel slideshow removed and GSAP retired (rAF width expand
instead); panel copy replaced by one headline + one sub with a scroll-linked per-word reveal;
panel recoloured to near-black `#121212` and the headline gradient **deleted** in favour of
solid bold paper; panel pinned to a single viewport (`md:h-[92vh]`); a Research CTA pill added;
the demo **video** (poster-first, viewport-gated) added below the CTA; cards narrowed to 64rem;
and — the only non-landing change — the `/research` answer pane now scrolls back to the Summary
when a stream completes.

| # | URL | context | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `http://127.0.0.1:4321/` | desktop · light | **hero** | warm spotlight sits **behind the composer only**, soft edges, no banding; the rest of the first viewport is clean paper; **no horizontal scrollbar at any desktop width** — the fly-232 fix is on prod already and this build must not regress it | | | |
| 2 | `http://127.0.0.1:4321/` | desktop | **panel appearance** | panel is **near-black** (not the warm brown of B4.3, not pure black); headline is **solid paper-white, BOLD serif, with NO gradient or colour ramp**; the sub is **visibly lighter/not bold**; the **Try Research** pill reads clearly as an inverted paper pill | | | |
| 3 | `http://127.0.0.1:4321/` | desktop, normal motion | **word reveal, BOTH directions** | scrolling down: headline words then sub words fade+rise in a staggered wave, finishing before the panel leaves; **scrolling back up plays it in reverse and the words return to the same partial states** — no words stuck opaque, no flicker, nothing left half-faded at rest | | | |
| 4 | `http://127.0.0.1:4321/` | desktop | **panel geometry** | the whole panel — headline, sub, CTA, video — **fits in one viewport without internal scrolling**; as you scroll, the panel **widens** but its **height does not change** (watch the top and bottom edges: they should stay put while the sides move out) | | | |
| 5 | `http://127.0.0.1:4321/` | desktop | **video behaviour** | the demo **starts playing when the panel comes into view** and **pauses when you scroll away** (scroll back: it resumes, it does not restart from a black frame); it **never plays while off-screen** | | | |
| 6 | `http://127.0.0.1:4321/` | desktop | **video image quality** | text inside the demo is **sharp, not squashed or stretched** — circles round, the UI's own type not condensed; the frame fills its box with no letterbox bars; **before it plays, the poster shows the finished answer with the Summary card at the TOP of the pane** (not mid-answer) | | | |
| 7 | `http://127.0.0.1:4321/` | desktop | **cards** | three **white sheets on the warm paper**, each with a **visible but quiet hairline border**; the three **Try Research / Try Verify / Try Explain** pills all present and legible | | | |
| 8 | `http://127.0.0.1:4321/` | **mobile ≤ 390px** | **mobile full scroll** | hero → panel → cards → footer scrolls cleanly with **no sideways scroll at any point**; the panel is **static** (no width animation, no reveal); the video shows the **poster with visible, tappable controls** and playing it works on tap | | | |
| 9 | `http://127.0.0.1:4321/` | **ar** (RTL) · desktop | **RTL** | panel headline and sub stay **centred**; the card **pill arrows point LEFT** and their hover-shift moves LEFT; nothing overlaps, no clipped text, no horizontal scroll | | | |
| 10 | `http://127.0.0.1:4321/` | **zh-TW** · desktop | **CJK typography + reveal unit** | the serif falls back to a system CJK face and **looks intentional** — no faux-bold mush, no mixed weights; the panel headline **reveals as ONE unit rather than word-by-word** (expected: no spaces to split on) and still reads as deliberate rather than broken | | | |
| 11 | `http://127.0.0.1:4321/` | desktop · **OS reduced-motion ON** | **reduced motion** | **no word reveal** (all text fully visible immediately), **no width animation** (panel sits at its resting width), and the **video does NOT autoplay** — it shows the **poster with controls**. Nothing is hidden or mid-transition at rest | | | |
| 12 | *(no URL — content row)* | en | **copy sign-off** | the founder's **final word on the words as rendered**: `panelHeadline`, `panelSub`, and the three card descriptions (`cardDescResearch` / `cardDescVerify` / `cardDescExplain`). This row records approval or names the edit | | | |

### Known and expected — do NOT record these as failures

- **The video's share of the panel height varies with window height.** It is the flex remainder
  after the headline/sub/CTA block, which costs a fixed number of pixels — so a shorter window
  gives the video proportionally less. Measured 52.6% at one window height and 49.1% at another;
  both are correct. Only a video that has become a thin strip (below ~40%) is a finding.
- **The poster carries a small mouse cursor** near the source chips. It is a screen recording and
  the same cursor is in the video; the frame was kept for continuity with the video's last frame.
- **Non-Latin locales fall back to a system serif.** 10 of 16 locales have no Source Serif
  coverage. Rows 9–10 judge whether the fallback looks *intentional*, not whether it matches Latin.
- **The machine-translated cells are NOT native-reviewed.** ⚠️ **90 cells, not 45** — see the
  ledger note below; the count was corrected while writing this form. Odd phrasing in a non-en
  locale is **reviewer-queue material, not a gate FAIL** — *unless* it makes or strengthens a
  CLAIM the English does not make. That **is** a FAIL (the fly-225 class, where the Bengali
  `/explore` copy asserted government endorsement the English never claimed).
- **The demo video shows a query that took ~34s in real life.** The cut opens after the wait.
  Founder-ruled 2026-08-14: a cut selects a segment, it does not distort time, and no timer is
  on screen. Not a gate row.

### How to run it — LOCAL

The render gate must run against **the built static export**, because that is the artifact that
deploys. `npm run dev` renders the same components but is *not* the shipped output; use it for
quick re-checks only, never for the gate verdict.

```bash
npm run build                 # writes out/
cd out && python -m http.server 4321 --bind 127.0.0.1
# then open http://127.0.0.1:4321/
```

- **Locale rows (9, 10):** switch language with the in-page settings dropdown (top right).
- **Mobile row (8):** DevTools device toolbar at ≤390px, **or** a real phone pointed at the
  machine's LAN IP on port 4321. A real phone is worth it for row 8's tap test.
- **Reduced motion (row 11):** Windows → Settings → Accessibility → Visual effects → Animation
  effects OFF. Reload the page after changing it.
- **Row 3 needs a slow, deliberate scroll in both directions** — a fast flick will not show the
  stagger, and reverse is the half that has regressed before.

### Prod re-check after deploy — SHORT SUBSET

The full 12 rows run **once, locally, before the deploy**. After deploying, confirm `/health`
`revision` = the deployed SHA, then repeat **only** these against `https://vela.an-tho.com/`:

| repeat | why this row and not the others |
|---|---|
| **1 — hero** | the fly-232 horizontal-overflow defect was **prod-only-visible** and founder-caught on a real phone; the local build cannot fully retire that risk |
| **2 — panel appearance** | the single highest-visibility change; a CDN/CSS-ordering fault would show here first |
| **5 + 6 — video** | the only row whose asset is fetched over the network at runtime; `preload="none"` + range requests behave differently on a real host than on `http.server` |
| **8 — mobile** | phones are the primary traffic and the one surface where local emulation has already proved insufficient |

Rows 3, 4, 7, 9, 10, 11, 12 are **not repeated**: they are properties of the built bundle and the
copy, which the deploy does not alter. If any of them failed locally the deploy should not have
happened at all.

---

## Gate 7 — "Gate (d)": ADR-007 (d) locale-panel authority-row suppression on grounded answers

> ## 🎉 GATE 7 CLOSED (2026-08-20) — LOCAL 4/4 (+1 bonus) · PROD P1–P3 3/3 · sweep spot-check 4/4. No pending rows remain.
> Founder-run end to end: the local run 2026-08-19/20 (rows above), the prod re-verification
> 2026-08-20 against **fly 238** (the `5e9aaa3` deploy — `/health` revision carries `a8b8e1e`), and
> the provenance-sweep render spot-check in the same session (recorded below the P-table). The same
> founder session block also passed the **5-page light-scheme theme eye row** (post deploy-car-3,
> fly 239) — that row's record lives in the STATE closeout entry and the TECH_DEBT theme entries.
>
> **Local-run deviation, preserved as history:** the local run used the **`:3000` dev server** —
> CORS blocked the static-export serve on `:4321`. These are behavior-logic rows (does the filter
> fire?), and the shipped bundle is covered by the probes; **the prod re-verification ran against
> the built artifact**, which is what retires the deviation. Row 4 was **PASS-BY-EVIDENCE** with a
> prod residual — discharged by P2.

**Change under test:** **`a8b8e1e`** (`feat(locale-hint): suppress the integrated authority's
pointer row on grounded answers (ADR-007 (d) option ii)`, 2026-08-19). At the prod re-verification,
**confirm `/health` `revision` contains it before row P1**.

**What changed:** when an answer's citations include a source whose authority is in
`INTEGRATED_AUTHORITY_KEYS` (today: TFDA via source_type `tfda`), that authority's pointer row is
dropped from the 在地差異 panel — `localeHintNote` ("Vela 未整合上述機關資料") is then true for every
row that survives. A TFDA-only panel collapses entirely via the existing empty-authorities guard
(**absent-or-panel-absent is expected — both are PASS shapes for "row ABSENT"**). Un-grounded
answers keep the pointer. Zero string changes; the flag `NEXT_PUBLIC_LOCALE_HINT_ENABLED` is
already ON in prod, so this ships inside the existing flag. Panel renders in zh-TW/en only.

**⚠️ AMENDMENT 2026-08-20 — the deploy car now also carries the provenance sweep, which REWORDS
`localeHintNote`** (semantic level corpus→per-answer, founder-ratified with this local run already
passed on the OLD string). At the prod re-verification, any "note PRESENT" assertion reads the
**NEW** text: zh-TW **「本回答未使用上述機關的資料，連結僅供你自行查證。」** / en **"This answer did
not use data from these authorities; the links are pointers for your own verification."**

**Rows follow convention 5 below** (never bare "TFDA"). Queries are suggestions — any query
producing the stated citation state is valid; per the fly-214 Finding 2 lesson, a grounded row
that retrieves no TFDA citation needs **stronger phrasing, not a FAIL** (the canonical grounded
query is `冠脂妥台灣核准的適應症是什麼`).

| # | URL | UI lang / setup | query (suggested) | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `https://vela.an-tho.com/research` | **zh-TW**, country resolves TW | `冠脂妥台灣核准的適應症是什麼` | **the citation chip reading 『TFDA 核准適應症』 is present** → **the locale-panel pointer row "TFDA" is ABSENT** (row absent, or the whole panel absent via the collapse path — both PASS); if the reimbursement category matched, the NHI pointer row is PRESENT; the note renders ONLY if ≥1 pointer row survives | citation chips 『TFDA 核准適應症』 ×4 → **whole panel ABSENT** (collapse path — TFDA was the only matched authority) | **PASS** | local `:3000` run, 2026-08-19/20 |
| 2 | `https://vela.an-tho.com/research` | **en**, country resolves TW | `What is the approved indication of 冠脂妥 in Taiwan?` (must fire an EN keyword, e.g. "approved indication", AND produce the TFDA citation chip) | same assertions as row 1, English panel text | chip 『TFDA 核准適應症』 ×1 → **panel ABSENT** (same collapse path, en) | **PASS** | local `:3000` run |
| 3 | `https://vela.an-tho.com/research` | **zh-TW**, country resolves TW | `metformin 起始劑量與最大劑量` (keyword fires; retrieval expected PubMed/DailyMed, **no** TFDA citation; must NOT be an isFallback answer — that suppresses the panel for a different reason) | **no citation chip reading 『TFDA 核准適應症』** → **the locale-panel pointer row "TFDA" is PRESENT** and the note is PRESENT — the protective behavior survives un-grounded | DailyMed-only citations → **panel PRESENT, pointer row "TFDA" PRESENT, note PRESENT** | **PASS** | local run against the OLD note string; prod re-verification reads the NEW text (amendment above) |
| 4 | `https://vela.an-tho.com/research` | **en** · `/settings` → **My Context** tab (second tab — default is My Shares) → **Country / region** → Singapore → **Save** (writes `vela_user_context.locale = "SG"` — waterfall **L1**, authoritative over L2/L3/L4). Confirm with `?localeDebug=1` → `country=SG · level=settings`. Restore the previous value after the row. | `What is the starting dose of metformin?` | panel byte-identical to pre-change: HSA pointer row present, note present — the suppression must not touch authorities outside `INTEGRATED_AUTHORITY_KEYS` (SG/MY/Tier-2 pass through) | **PASS-BY-EVIDENCE, prod residual:** the run's original cell named a non-existent path ("Settings → Country/region" without the tab — form error, corrected in this cell), and a DevTools timezone override (Asia/Singapore) was overridden by an upstream waterfall layer (see below). Pass-through established by (a) the mutation-tested guard's SG/MY/Tier-2 byte-identical assertions + (b) the observed zero-suppression TW panel on an un-grounded answer. **SG UI eyeball moves to the prod re-verification (row P2).** | **PASS-BY-EVIDENCE** | see waterfall note below |
| 5 *(bonus, recorded)* | `https://vela.an-tho.com/research` | **en**, country resolves TW | un-grounded en query (locale keyword fired, no TFDA citation) | pointer + note present on the **en** path too | **pointer row "TFDA" PRESENT, note PRESENT** | **PASS** | protective behavior confirmed on the en path |

**Why the DevTools timezone override could not work (row 4, investigated 2026-08-20):** the
waterfall (`utils/country.ts` `resolveCountry`) is **L1 `vela_user_context.locale` (Settings → My
Context → Country/region) > L2 `vela_user_context.work_language` > L3 IANA timezone > L4 UI
language**. A signed-in founder profile carries L1 and/or L2 in the `vela_user_context`
localStorage blob, so an L3 timezone override can never win; DevTools sensor overrides also reset
silently between queries (the documented `?localeDebug=1` rationale). **The real SG reproduction
is the L1 path now written into row 4's setup cell.**

**Known and expected — do NOT record as failures:** on row 1/2, the panel disappearing entirely
(rather than rendering with fewer rows) is the DESIGNED collapse path when TFDA was the only
matched authority; the un-grounded-TW residual of the naming collision (row 3 shows the pointer
row "TFDA" while non-TFDA citation chips are visible) is **deferred by option (C)**, not a defect
of this change.

### Prod re-verification — ✅ RUN AND PASSED 3/3, founder-run 2026-08-20 against fly 238 (`5e9aaa3` deploy)

Any "note PRESENT" assertion reads the **NEW** `localeHintNote` text quoted in the amendment above.

| # | URL | setup | query | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| P1 | `https://vela.an-tho.com/research` | **zh-TW**, country resolves TW | `冠脂妥台灣核准的適應症是什麼` | row 1's assertion on the built artifact: chip 『TFDA 核准適應症』 present → pointer row "TFDA" ABSENT (or whole panel absent) | citation chips 『TFDA 核准適應症』 ×4 → **whole panel ABSENT** (collapse path — same shape as the local run, now on the built artifact) | **PASS** | founder, 2026-08-20, fly 238 |
| P2 | `https://vela.an-tho.com/research` | **en** · `/settings` → **My Context** tab → **Country / region** → Singapore → Save → confirm `?localeDebug=1` shows `country=SG · level=settings`; restore afterwards | `What is the starting dose of metformin?` | HSA pointer row present + the NEW note text present — SG pass-through eyeballed on prod (the half row 4 deferred) | `level=settings` verified via `?localeDebug=1` · panel renders (Singapore) · **HSA pointer row PRESENT** · the NEW note text PRESENT · **zero suppression** | **PASS** | discharges row 4's deferred SG eyeball — the corrected My-Context steps worked first try |
| P3 | `https://vela.an-tho.com/research` | **zh-TW**, country resolves TW | `metformin 起始劑量與最大劑量` | pointer row "TFDA" PRESENT + the **NEW zh-TW note** 「本回答未使用上述機關的資料，連結僅供你自行查證。」 rendered verbatim | un-grounded answer → **pointer row "TFDA" PRESENT** + the NEW zh-TW note rendered **verbatim** | **PASS** | the protective behavior survives on prod |

### Provenance-sweep render spot-check — ✅ 4/4 PASS, same founder session (2026-08-20)

| # | surface | what PASS looks like | VERDICT |
|---|---|---|---|
| S1 | `/research` footer | `researchAttr2` names DailyMed (FDA/NLM) · **new `researchAttr4` OGDL line renders** | **PASS** |
| S2 | `/verify` footer | `verifyAttr1` reads "(DailyMed, with OpenFDA fallback)" | **PASS** |
| S3 | `/faq` | both answers carry the new parentheticals ("DailyMed, FDA/NLM" · "DailyMed, with OpenFDA fallback") | **PASS** |
| S4 | TFDA chip tooltip | the zh-TW `tfdaSourceTip` cell verified **verbatim** on the chip (no longer the wrong-agency `officialTip`) | **PASS** |

---

## Gate 8 — Landing build car: nav + Verify band + ruled copy (2026-08-28)

**Change under test:** the 2026-08-28 landing build car — product commits `537e3ab` (NUL byte
fix) · `6bcc1bb` (ruled copy ×16 + meta/OG) · `caaa4be` (desktop nav links + Try Vela CTA) ·
`05ef6cf` (Verify band + 6 keys retired + `paper-band` token + WebP asset) · `9d563a4` (poster
deletion + `VIDEO_PRELOAD` toggle), plus test/docs commits `d1bfc10` · `24eb7eb` · `45d65fe`.
The car's **final SHA is its STATE closeout commit** — before running, confirm `git rev-parse
HEAD` matches the SHA in STATE's landing-build-car ship entry. Local serve per the Gate 6
method: `npm run build`, then `python -m http.server 4321 --directory out`, open
`http://127.0.0.1:4321/`.

**ALL ROWS ARE LIGHT** (D-B4-1: the logged-out landing is light-only — no dark rows by design).

**What changed vs fly 240:** hero H1 reads the NEW tagline (only hero change); nav gains five
desktop-only links + the Try Vela CTA (the hardcoded "Upgrade" is gone from the landing); the
three-card "What Vela does" section and the footer `#features` link are REMOVED; a warm-gray
Verify showcase band (`paper-band`, NEW token — founder eyeballs the value at this gate) sits
directly after the panel with new copy + the WebP demo screenshot; panel headline/sub rewritten
(rulings #5/#6); the demo video lost its poster and runs one of two pre-play treatments behind
the one-line `VIDEO_PRELOAD` toggle (ruling E — the pick is row 5 of this gate); meta/OG follow
the new tagline (ruling H).

> **AMENDED 2026-08-28 (iteration 2, pre-run):** the **Explain band** (`paper-band-2` token,
> staggered input→result captures, `tryExplain` restored byte-identical from `caaa4be`, 4 new
> `explain*` keys) added after the Verify band — **row 6b added; rows 7 / 8 / 9 extended** to
> cover it. Iterations 1–2 also moved the nav links left beside the logo and matched both bands
> to the panel's widened width — rows 2 and 6 read on the current build either way.
>
> **AMENDED AGAIN 2026-08-28 (iteration 4, pre-run):** the Explain composition changed from
> the overlapping stagger to a **side-by-side row** (tops aligned, no overlap) — **rows 6b and
> 8 rewritten** to state the new identity. ✅ **The sub-2× sharpness caveat that iteration 3
> added to row 6b is WITHDRAWN, not silently dropped:** it was true of the stagger's 70%-wide
> result capture (1.870× available at DPR 2), and the side-by-side cut the rendered width to
> 453.5 px, which **re-derives to 2.587× — it now clears 2×**, as does the input capture
> (3.092×). A 2× re-capture is no longer indicated for the desktop band; **mobile was never
> affected** (3.78× / 4.17×). Nothing about this row is a known-soft exception any more.
>
> **AMENDED AGAIN 2026-08-31 (iteration 5, pre-run):** media sizing and one sub. **Rows 4, 6 and
> 6b rewritten.** The founder **dropped the equal-fraction goal** (the two media never share a
> screen), so each is now sized to its own 2× ceiling: the Research video is **capped at 0.625**
> of the panel's inner width while staying height-adaptive, and the Verify screenshot is **raised
> to 0.85** of the band's. Measured after the change — video **0.586 / 2.134×** at 1280×800,
> **0.447 / 2.797×** at 1280×700 (adaptive shrink, no overflow), **0.625 / 2.001×** in ar where
> the cap binds; Verify **0.85 / 2.063×**; both media clear 2× at DPR 2 in every locale and
> viewport measured, and **Gate 6 row 4's property still holds** (panel content height == box
> height, no internal scrolling, at both window heights). The panel was tightened to `py-10` +
> `gap-4` to make the cap reachable, and `verifySub` was replaced.
>
> **COPY RULED 2026-08-31 (same iteration, rows 4 and 6 now carry the FINAL strings):** `panelSub`
> = the **W2-preserving variant**, because the measurement showed it costs nothing where it counts
> — both candidates reach the 0.625 cap at 1280×800 (budget 416px vs the 413.7px the cap needs),
> so there was no reason to undo ruling #6 and return Local Awareness to zero landing carriers.
> `verifySub` **regains the authorship clause**: the previous rewrite was not an overclaim (not
> fly-225 class) but an **under-specification** — it said a flag exists without saying whose
> assessment it marks, while the band's own screenshot shows the product's flag reading *"Vela
> AI-assessed (not label-stated)"*. **Copy must not be vaguer than the picture beside it.**
> Re-measured with the longer sub in place: Gate 6 row 4 still holds (see the row-4 assertion).

| # | URL | context | check | what PASS looks like | observed | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `http://127.0.0.1:4321/` | desktop · light · en | **hero unchanged** | spotlight behind the composer only, typewriter + chips + privacy line exactly as fly 240; the ONLY difference is the H1 now reading *"Ask in any language. Answered in yours — with sources you can check."*; **no horizontal scrollbar at any width** | | | |
| 2 | `http://127.0.0.1:4321/` | desktop · en | **nav links + CTA** | Research / Verify / Explain / Pricing / FAQ each visible and **each routes to its page**; the **Try Vela** pill routes to `/research` (anonymous — no sign-in wall before the page); the gear dropdown still opens **aligned under the single-row bar** (its `top-[72px]` anchor — no overlap, no gap jump) | | | |
| 3 | `http://127.0.0.1:4321/` | **mobile ≤ 390px** · en | **mobile minimal row** | the five links are **ABSENT**; the row is logo · gear · Try Vela · Sign In on **one line, nothing wrapped**, no hamburger | | | |
| 4 | `http://127.0.0.1:4321/` | desktop · en | **panel with new copy** | near-black panel; headline **solid bold paper serif** reading *"Ask in your language. Answers grounded in evidence."* (no "Decisions"); **(iteration 5, FINAL)** sub reads *"Search peer-reviewed literature and official drug labels in any language. Vela cites every source and flags where local guidance may differ."* — **both sentences present**: the second is the **W2 (Local Awareness) carrier** that ruling #6 put on the page, and the page has no other; Try Research pill present; **word reveal still plays forward AND reverse**; **(iteration 5)** the demo video is **noticeably larger than fly 240** and **never wider than ~62.5% of the panel's inner width**, and the panel still **fits one viewport with no internal scrolling at 1280×800 AND at a short 1280×700 window** — the video shrinks on the short window rather than overflowing (Gate 6 row 4's property, re-asserted here because this car enlarged the media) | | | |
| 5 | `http://127.0.0.1:4321/` | desktop + mobile · en | **2f pre-play pick (FOUNDER DECISION ROW)** | flip `VIDEO_PRELOAD` in `components/LandingSections.tsx` between `'metadata'` (first frame paints pre-play; may fetch the whole 2.3 MB — no byte ranges, `[OTHER][P2]`) and `'none'` (blank bordered box until play); **pick one**; the pick ships and the toggle + losing branch are deleted before deploy | | | |
| 6 | `http://127.0.0.1:4321/` | desktop · light · en | **Verify band** | band reads as a **warm gray in the paper family** — visibly distinct from the page, never a cool Apple gray (this row ratifies or adjusts the `paper-band` value, ruling C); headline *"Interactions, checked against the label."*; **(iteration 5, FINAL)** sub reads *"Enter your drug list to search documented FDA interactions. See the source for each finding, flagged when the assessment is Vela’s, not the label’s."* — the closing clause must name **whose** assessment it is, matching the flag visible in this band's own screenshot (*"Vela AI-assessed (not label-stated)"*); **Try Verify** ink pill routes `/verify`; the screenshot is **sharp, not squashed** (its own 2020×1225 proportions — iteration-1 re-capture) and now spans **~85% of the band's inner width** (iteration 5 A2) | | | |
| 6b | `http://127.0.0.1:4321/` | desktop · light · en | **Explain band (iteration 2)** | band reads **one step whiter than the Verify band and still off the page paper** (ratifies/adjusts `paper-band-2`); headline *"Your report, explained item by item."*; sub carries **BOTH access truths as separate facts** — free account required, PDF/image upload with Pro; **Try Explain** pill routes `/explain`; the composition reads "paste this → get this" as a **SIDE-BY-SIDE row (iteration 4)**: input capture inline-start, result capture inline-end, **VERTICALLY CENTRED on one another (iteration 5 C2 — no longer tops-aligned), NO overlap and no layering**, split 48/52 of the space left after the gap; the **result is simply the taller image and extends further down** — neither is cropped, stretched, or forced to match the other's height, each at its own proportions (1294×954 / 1173×1204); both carry the same border treatment as the Verify band image (no drop shadow on either) | | | |
| 7 | `http://127.0.0.1:4321/` | desktop · **zh-TW** | **zh-TW page** | gear → 繁體中文: hero reads 「用任何語言提問。以你的語言回答——附上可查證的來源。」, Verify band headline 「交互作用，對照藥物標示查核。」, **Explain band headline 「你的報告，逐項解讀。」 with the access clause 「需要免費帳號；PDF 與圖片上傳為 Pro 功能。」**; **no raw key names, no leftover English** apart from proper nouns (Vela · FDA · LOINC · RxNorm) | | | |
| 8 | `http://127.0.0.1:4321/` | desktop · **ar** | **ar RTL** | layout mirrors (pill arrows flip, text right-aligned), **both bands** stay sane — the Explain ROW mirrors too (**input starts from the right, result sits to its left**, tops still aligned), no overlapping glyphs, **no horizontal scroll** | | | |
| 9 | `http://127.0.0.1:4321/` | **mobile ≤ 390px** | **mobile full scroll** | hero → panel → Verify band → **Explain band** → footer scrolls with **no sideways scroll at any point**; band images fit the width — the Explain pair collapses to a **vertical stack, input above result, full width, NO overlap**; the footer has **no dead "What Vela does" link** | | | |
| 10 | rendered page | desktop · en | **copy sign-off** | the founder re-reads tagline · panelHeadline · panelSub · verifyHeadline · verifySub **on the rendered page** and signs them as the shipped ratification of the Phase-1 table | | | |
| 11 | rendered page | **zh-TW** | **fly-225-class provenance row (new MT cells)** | in zh-TW the panelSub 「官方」 scopes to 藥物標示 (labels) only — no government-endorsement reading; nothing in the band reads as a safety **verdict**; the other 14 locales carry the same claim structure — their native check is the reviewer round (`deliverables/vela_landing_i18n_review_20260828.csv` — **15 keys × 15 locales = 225 rows**, **NOT sent**; the *150* written here at the form's creation was the build-car set and went stale when iteration 2 added the Explain band, corrected 2026-08-28) | | | |

### ⚠️ Carried by this deploy but NOT a landing row: the /explain colour change (added 2026-08-29)

**Every row above is LIGHT**, because the logged-out landing is light-only (D-B4-1). The same car
also changed a **THEMED PRODUCT SURFACE**: `/explain`'s result view — source chips neutralised to
Research's token pair, risk-tier accent bars removed, the Clinical Correlations panel and its term
chips neutralised (`9014b8d` + the 2026-08-29 follow-up). `/explain` follows the user's theme, so
**it needs a LIGHT *and* DARK eye check that no row in this gate performs.** It is recorded here so
the check cannot be lost between the landing gate and the deploy; **this is a note, not a new gate.**

- **Local evidence already in hand** (does not replace the prod eye): rendered in both themes and
  computed styles read back per theme — chip/card tokens flip `rgba(23,23,23,…)` ↔
  `rgba(255,255,255,…)`, card `border-left` 3px coloured → 1px neutral, correlation surface ==
  item-card surface, and **zero `#b794f4`/`rgba(183,148,244,…)` literals remain in the DOM**.
- **What the prod pass must confirm, in BOTH schemes:** the VERIFIED SOURCES chips are legible
  (they were previously dark-tuned pastels applied inline, so **light is the scheme that was
  actually broken**); the badges are the only colour left on the surface; the correlation panel
  reads as a card, not as a smudge.
- **Precedent for the shape of this check:** the **5-page light-scheme theme eye row** the founder
  ran post-deploy-car-3 (fly 239), recorded in Gate 7's closure block above and in the STATE
  closeout entry. Same idea, different surface.

### Prepared (NOT run): post-deploy prod pass

After the founder authorizes push + deploy, re-run rows **1, 2, 6, 7, 9** against
`https://vela.an-tho.com/` (confirm `/health` `revision` = the pushed HEAD first), **plus the
/explain light+dark eye check noted directly above**, **plus** one
instance of the ownership form — [`docs/human_eye_gate_checklist.md`](human_eye_gate_checklist.md)
seeded 8 rows, EXPECTED OWNER filled **at run time** per that file's Rule-23 procedure (plural by
construction). This car touches no retrieval code, so the ownership instance is the standing
post-deploy spot-check, not a new-risk gate.

## Adding a gate to this file

1. Name the **change under test** by commit SHA.
2. Give each row a **copy-pasteable URL and its locale** — locale is a row property here, not a
   global.
3. State expectations as an **identity or a claim** (*"no credibility pill"*), never as a count
   (*"3 citations"*). Counting is the failure mode that let the fly-215 gate pass a wrong-drug
   citation.
4. Add a row for **anything a unit test cannot see** — legibility, locale resolution, layout,
   link behaviour. That is the whole reason a human is running this.
5. **"TFDA" is never written bare in a gate row** — write **the citation chip reading
   『TFDA 核准適應症』** or **the locale-panel pointer row "TFDA"**. Standing rule per the fly-214
   gate's naming collision (`docs/citation_gate_findings_20260729.md` Finding 2(ii)), resolved as
   **option (C), founder-ratified 2026-08-19**: fix the checklist wording only. Options (A)
   (rename the pointer, a 16-language string change) and (B) (visual pointer-vs-citation
   distinction) are **consciously deferred** — ADR-007 (d) suppression makes the collision's
   confusing instances disappear by construction on grounded screens; the residual (an
   un-grounded TW answer where the pointer row and non-TFDA citation chips are both visible) is
   **recorded here as deferred, not fixed**.

## Related

- **Ownership** gates (whose label was cited on a Research query):
  [`docs/human_eye_gate_checklist.md`](human_eye_gate_checklist.md)
- Process rules (stale server · deep-links · expected drug · same-day control · TFDA phrasing):
  `BACKLOG.md` → `[ops] Pre-gate stale-server SOP`
