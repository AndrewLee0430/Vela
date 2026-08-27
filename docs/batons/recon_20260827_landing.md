# RECON 2026-08-27 — Landing car Phase 0 + inventory (read-only; evidence-only commits)

**READ-ONLY RECON. No product code, no i18n edits, no copy written. Writes: this baton + `tests/probes/landing_hero_overflow/` (probe script + result JSON). NO push, NO deploy.**

**Authority for this car: `docs/batons/positioning_audit_20260823.md` §3 RULING C** — *"landing copy proceeds under EXISTING rulings (route = B2B-interim, ruled 2026-06; current TA per ADR 004). The A1 Taiwan-localization pivot is NOT ruled here and is NOT a landing blocker."* Rule 16 applies to any future copy change (×16 locales); this recon inventories so the founder can rule scope first.

- **Repo assertion (Rule 24):** toplevel `C:/Users/andre/projects/Vela`; HEAD at start `123cf487207328d4500d70beed205b300fd830fa`.
- **Readbacks (verified fresh, not inherited):** `git ls-remote origin main` = `123cf487207328d4500d70beed205b300fd830fa` — **MATCH**, and == local HEAD (no divergence; tree clean except untracked `.superpowers/`). Prod `GET /health` → `revision` = `ac5b2a2d9c503ddcfb635792be60d28c80be2329` — **MATCH** (fly 240). Prod currency for the landing surface: `git diff --stat ac5b2a2..123cf487 -- api/ components/ pages/` = **EMPTY** — the 6 commits past prod are docs/tooling; prod measurements below measure HEAD-equivalent landing code.
- Line numbers in this doc are **as-of `123cf48`** footnotes; the anchors are the quoted phrases.
- **CORRECTION 2026-08-27 (same car, pre-ruling; Rule 25 derived-vs-previously-written):** the first version of this baton (commit `9b70813`, incl. its commit message) attributed the fly 232 fix to **`61d49f1`** and framed the conflict as "the flag predates the fix by one day". Derived: the fix is **`2c1e5db`** (09:19:22 +0800, `pages/index.tsx` +19/−1, `git log --all -S "overflow-x-clip"`); `61d49f1` (09:25:39) is a **docs-only** STATE header bump (1 line) recording the readback — exactly as `docs/render_gate_checklist.md` Gate 6 records. And the correct shape is **parallel lines**: the flag was authored on the unpushed B4.1 line (`b0582d1`, A:08-13 15:51) and that line was rebased onto the hotfix at 08-14 09:26–09:28 — "the flag measured a local build that did not contain the fix", not merely an earlier date. Phase 0a #2, the 0a closing paragraph, 0b WHY (i), and the 0c draft annotation are corrected in place below; the probe numbers and the STALE verdict are unchanged by this correction.

---

## PHASE 0 — `.hero-spotlight` overflow: ledger conflict adjudicated

### 0a. Ledger census (every statement found; verbatim; timeline order)

Derivation: keyword sweep (`hero-spotlight`, `491`, `scrollWidth`, `hOverflow`, `overflow-x`, `overflow-clip`, `horizontal scroll/overflow`) over `STATE.md`, `TECH_DEBT.md`, `docs/archive/*.md`, `docs/batons/*.md`, printing ±windows inside the monster single lines `git grep` truncates.

| # | When | Statement (verbatim excerpt) | Anchor (file · phrase) |
|---|---|---|---|
| 1 | **B4.1c, 2026-08-13 — THE FLAG** | "⚠️ **FLAGGED, NOT FIXED (pre-existing, outside B4.1c): `.hero-spotlight` is a ~1277px fixed-width blob — at 375px it creates REAL horizontal scroll** (scrollWidth 491 vs clientWidth 360; html/body overflow-x visible); no overflow at desktop width; founder decides whether to clip." | STATE.md, the `**B4.1c (local, 2026-08-13…)**` header paragraph, phrase "FLAGGED, NOT FIXED" *(as-of :34)* |
| 2 | **fly 232, 2026-08-14 — THE FIX = `2c1e5db` (09:19:22 +0800), the deployed revision itself** — `fix(landing): [fly 232 hotfix] contain the hero spotlight`, `pages/index.tsx` +19/−1, and `git log --all -S "overflow-x-clip"` shows the string entering code in exactly this commit. (`61d49f1`, 09:25:39, is the **docs-only** STATE header bump recording the readback — 1 line of STATE.md; the first version of this baton mis-attributed the fix to it, corrected 2026-08-27, see header note.) | "**fly 232 = hero-spotlight horizontal-overflow hotfix**, readback-verified `revision` = `2c1e5db…`. Defect: the page scrolled sideways… **founder-confirmed on a real phone**, live since B4. Cause: `.hero-spotlight` is 190% of the composer form… ~1277px centred… overran the right edge on **every viewport under ~1277px**. Fix: `overflow-x-clip` on the first-viewport wrapper — **clip, never `hidden`**" — STATE.md header strikethrough block, phrase "hero-spotlight horizontal-overflow hotfix" *(as-of :3)* |
| 3 | B4.2, 2026-08-14 | "**hOverflow 0 — the fly-232 class is not reintroduced** (the spotlight still extends to x=492 but is clipped, which is the fix working, not a regression)" | STATE.md, `**B4.2 (local, 2026-08-14)**` paragraph *(as-of :30)* |
| 4 | B4.3, 2026-08-14 | "Mobile 375px: content-driven 622px, media full width, **hOverflow 0**" | STATE.md, `**B4.3 (local, 2026-08-14)**` paragraph *(as-of :28)* |
| 5 | B4.5, 2026-08-14 | "**375px hOverflow 0** (the fly-232 class is not reintroduced)" | STATE.md, `**B4.5 (local, 2026-08-14)**` VERIFIED line *(as-of :24, :26)* |
| 6 | B4.6, 2026-08-14 | "**hOverflow 0** at desktop and at 375px" | STATE.md, `**B4.6 (local, 2026-08-14)**` paragraph *(as-of :17)* |
| 7 | fly 233, 2026-08-15 — prod spot-check | "controls visible, static panel, **no horizontal scroll**" (and fly 232 recorded as a sanctioned worktree-isolated hotfix) | STATE.md, `**fly 233 (2026-08-15)**` paragraph *(as-of :13)* |

**The flag and the fix sat on PARALLEL LINES, not merely in date order — derived from author-vs-committer dates.** The hotfix `2c1e5db` was built in an **isolated worktree cut from `origin/main`** (STATE's own record: "precisely so the 6 unpushed local commits could not ride along") while the B4.1 iteration line lived unpushed on local main. The flag's own commit — `b0582d1` *"docs(state): [B4.1c] reconcile dual-session verification — fold … hero-spotlight overflow flag into the ship entry"* — is **authored 08-13 15:51** on that local line and **rebased onto the hotfix at 08-14 09:27** (the whole B4.1b–B4.1e block carries committer dates 09:26–09:28, immediately after `2c1e5db` 09:19 / `61d49f1` 09:25; `git merge-base --is-ancestor 2c1e5db 78b96ab` confirms the local line now sits on top). So **the flag measured a local build that did not contain the fix** — and the very first post-rebase sweep (B4.2, `045baf7`, 08-14 10:57) is exactly where the ledger flips to "hOverflow 0 — the fly-232 class is not reintroduced". Statements #3–#7 all measure fix-bearing builds and are unanimous. The flag even ends "founder decides whether to clip" — fly 232 IS that decision executed.

### 0b. Fresh measurement — prod fly 240 (2026-08-27T05:45:57Z)

No committed browser-overflow probe existed (`tests/probes/b41d_panel_smoke.mjs` reads the static export, not a live viewport), so one was written: **`tests/probes/landing_hero_overflow/probe.mjs`** (Playwright 1.62.1, system-Chrome channel, headless, mobile UA + touch, dsf 3). Result committed as `result.json` (prod revision recorded INSIDE the run = `ac5b2a2…` fly 240). Numbers, each at its own width:

| viewport | clientWidth | scrollWidth | **hOverflow** | `.hero-spotlight` rect (left / right / width) | rects beyond right edge |
|---:|---:|---:|---:|---|---|
| **360** | 360 | 360 | **0** | −131.6 / **491.6** / 623.2 | 1 — the spotlight itself (clipped) |
| **375** | 375 | 375 | **0** | −138.3 / 513.3 / 651.7 | 1 — same |
| **390** | 390 | 390 | **0** | −145.1 / 535.1 / 680.2 | 1 — same |

Caveat stated in the probe header: `getBoundingClientRect` ignores ancestor clipping, so the spotlight rect exceeding the edge inside the `overflow-x-clip` wrapper is **the fly-232 fix working** (exactly statement #3's "extends to x=492 but is clipped"); the authoritative scroll number is `scrollingElement.scrollWidth − clientWidth`, and it is **0 at all three widths, including 360 — the flag's own unit**.

**WHY the flag and the fresh measurement disagree — both halves, per the house rule:** (i) *provenance* — **the flag measured a local build that did not contain the fix**: the flag was authored 08-13 on the unpushed B4.1 line (`b0582d1`), while the fix `2c1e5db` was built 08-14 09:19 in an isolated worktree from `origin/main`; the local line acquired the fix only at the 09:26–09:28 rebase, and its first subsequent sweep (B4.2) already reads hOverflow 0; (ii) *geometry corroboration* — at the **360** viewport the spotlight's right edge measures **491.6**, i.e. the flag's "scrollWidth 491" was a **360-frame** number (unclipped spotlight edge ⇒ scrollWidth 491, clientWidth 360, overflow 131 = fly 232's "131→0"), even though the flag's prose said "at 375px". The flag's numbers were real and internally consistent; only its width label was off by one frame, and the geometry it measured is still present — now clipped.

### 0c. VERDICT (drafted for the founder — NOT applied)

**The flag is STALE.** Overflow = 0 at 360/375/390 against prod fly 240; the flag measured a local build that did not contain the fly 232 fix (parallel lines, 0a); every fix-bearing measurement since agrees; the underlying geometry is unchanged and clipped, which is the fix's designed behaviour.

**DRAFT mark-never-delete annotation for the flag site** (STATE.md, the B4.1c paragraph, appended after "founder decides whether to clip."), for founder ruling — **not applied by this car**:

> *(✅ 2026-08-27 ADJUDICATED STALE — this flag measured a local B4.1c build that did not contain the fly 232 hotfix: the fix is `2c1e5db` (2026-08-14 09:19, `overflow-x-clip` on the first-viewport wrapper, built in an isolated worktree from origin/main while this line was unpushed; `61d49f1` is the docs header bump recording its readback), and this line acquired it at the 09:27 rebase — the next sweep (B4.2) already read hOverflow 0. Probed live against prod fly 240: hOverflow **0** at 360/375/390; the spotlight still extends to x≈491.6 at 360px but is clipped — the fix working, not a regression. The flag's "scrollWidth 491 vs clientWidth 360" were 360-frame numbers though its text said "at 375px" (hero right edge = 491.6 at 360px). Evidence: `tests/probes/landing_hero_overflow/`. Original text unedited.)*

---

## V1 — dead keys `researchSub` / `verifySub` / `explainSub`

**Rule 25 derivation:** command = `git grep -cnE "\b(researchSub|verifySub|explainSub)\b" -- "*.ts" "*.tsx" "*.js" "*.mjs"` (word boundary excludes the *live, different* `researchSubtitle` family consumed by `pages/{research,verify,explain}.tsx`). Result: **ZERO hits — the keys neither exist nor are consumed at HEAD.**

- Unit: cells = key×locale pairs. Cited figure "48 cells, zero consumers" = 3 keys × 16 locales — the arithmetic matches the ledger's own record, but it describes the **pre-fix state**: the `[DONE]` entry headed *"[P3 · dead i18n keys — surfaced by the 2026-08-18 provenance recon; ✅ FIXED 2026-08-20 by the provenance-sweep commit: the 3 keys deleted from the `LandingContent` interface + all 16 locale blocks (−48 cells + 3 interface lines)…]"* (now in `docs/archive/tech_debt_done.md`, heading tombstoned in TECH_DEBT.md).
- **Derived (0 cells at HEAD) ≠ cited (48)** — the difference is the 2026-08-20 fix, already discharged. Nothing to do.

## V2 — duplicate-copy flags

| Pair | en strings at HEAD (verbatim) | Render sites | Verdict |
|---|---|---|---|
| `panelSub` vs `cardDescResearch` | panelSub: "Access authoritative medical evidence in the language you know best, backed by sources you can verify." · cardDescResearch: "Ask a clinical question the way you'd say it. Research searches the medical literature and returns a synthesized answer with citations you can open and check." | panelSub: `components/LandingSections.tsx` panel H1+sub block *(as-of :396)*; cardDescResearch: features card grid *(as-of :497)* | **DISTINCT at HEAD — the flag is DISCHARGED.** The flag (STATE.md B4.1c paragraph: *"`panelSub` (EN) ends with the same clause as `cardDescResearch` — 'with citations you can open and check' appears twice on the page"*, as-of :34) was resolved the same day by B4.1d: *"`panelSub` REWRITTEN in all 16 locales… **which also de-duplicates the 'citations you can open and check' tail it used to share with `cardDescResearch`**"* (STATE.md B4.1d paragraph, as-of :32). The committed probe still guards the retired tail (`RETIRED_SUB_TAIL` in `tests/probes/b41d_panel_smoke.mjs`). The clause now appears once on the page. |
| `cardDescVerify` vs any panel string | "Enter the drugs you want to check. Verify looks for documented interactions in FDA drug labeling and shows you the source for each finding." | features card grid *(as-of :498)* | Distinct — no panel string shares text. |
| `cardDescExplain` vs any panel string | "Paste lab values and Explain walks through them against standard reference ranges, with sources. A free account is required; PDF and image upload comes with Pro." | features card grid *(as-of :499)* | Distinct. |
| ⚠️ NEW (found by the family sweep): `tagline` vs `panelHeadline` | tagline: "**Ask in your language.** Verified by official sources. Answered in yours." · panelHeadline: "**Ask in your language.** Decisions grounded in evidence." | tagline: hero (`pages/index.tsx` as-of :335); panelHeadline: panel (LandingSections as-of :396) | **Shared first sentence, verbatim** ("Ask in your language."). Both founder-ratified; echo may be intentional — founder call, flagged not fixed. |

## V3 — full landing key census at HEAD

Derivation: consumer sweep over `pages/index.tsx` + `components/LandingSections.tsx` (the landing component chain; `LandingSections.tsx` trips grep's binary heuristic — extracted via Python regex on `lc.` / `t.` / `ui.` / `extra.`). Coverage: every key counted as occurrences in its string file — **17 = 1 interface line + 16 locale consts** (both `LandingContent` and `Translations` interfaces have **no optional keys**, and the maps are `Record<LangCode, …>`, so tsc forces 16/16; command = per-key `\bKEY\s*:` count).

**Core landing-copy layer (`lc.*` = `landingContent[lang]`, `utils/i18n.ts`): 13 keys, and the interface↔consumption is a clean bijection** (13 declared, 13 consumed, zero dead, zero undeclared):

| Key | en (verbatim) | Consumer (as-of) | Coverage | Review status (STATE fly 233 paragraph, as-of :13) |
|---|---|---|---|---|
| tagline | Ask in your language. Verified by official sources. Answered in yours. | index.tsx hero :335 | 16/16 | byte-identical to fly 232, "no new review debt" |
| subtitle | The AI medical search for healthcare professionals who work beyond English. | index.tsx hero :338 | 16/16 | byte-identical to fly 232 |
| scrollHint | Scroll to learn more | index.tsx :405 (ScrollHint) | 16/16 | byte-identical to fly 232 |
| panelHeadline | Ask in your language. Decisions grounded in evidence. | LandingSections :396 | 16/16 | **eligible-not-sent**: EN founder-ratified, 15 MT |
| panelSub | Access authoritative medical evidence in the language you know best, backed by sources you can verify. | LandingSections :396 | 16/16 | **eligible-not-sent**: EN ratified (B4.1d), 15 MT |
| panelDemoAlt | Screenshot of a Research answer with citations. | LandingSections :480 | 16/16 | **eligible-not-sent**: EN ratified, 15 MT |
| tryResearch / tryVerify / tryExplain | Try Research / Try Verify / Try Explain | LandingSections :438 (CTA) · :498 · :499 (cards) | 16/16 ×3 | **eligible-not-sent** ×3 |
| cardDescResearch | (V2 above) | LandingSections :497 | 16/16 | byte-identical to fly 232 **and** on the 2026-08-12 entry's "FUTURE-round candidate list (claim-bearing strings accumulating)" |
| cardDescVerify | (V2 above) | LandingSections :498 | 16/16 | same |
| cardDescExplain | (V2 above) | LandingSections :499 | 16/16 | same |
| featuresHeading | What Vela does | LandingSections :493 + index.tsx footer nav :424 | 16/16 | byte-identical to fly 232 |

**Secondary layers consumed by the signed-out landing** (enumerated; claims-bearing ones enter C2): `t.*` (`translations[lang]`): `heroChip1-3` (role-filtered example chips, index.tsx :117; `egNurse1`…`egStudent3` when a role is set), `privacyPromise1-3` (privacy strip :400), `footerCopy`, `footerDisclaimer` (:418, :420), `signIn` — all 16/16. `ui.pricingTitle` (footer Pricing link reuses it verbatim, per the in-code comment). `extra.*`: `faqLabel/privacyLabel/refundLabel/termsLabel/allRightsReserved` (footer legal links) — all 16/16. `TYPEWRITER_PROMPTS` are hardcoded multilingual by design ("the language mix IS the showcase" — in-code comment), not i18n keys. The `dash*` extra keys render only in the SignedIn dashboard view — out of positioning scope.

**Cross-check vs the prompt's "UNSTABLE/DO-NOT-SEND" list** (`panelHeadline`, `panelSub`, `tryResearch/Verify/Explain`, `cardDescResearch/Verify/Explain`, `panelDemoAlt`): **all 9 exist at HEAD, none dead, none renamed.** But the list conflates two different statuses, and the FROZEN premise is **superseded**: STATE's fly 233 paragraph says *"**REVIEW PIPELINE UNFROZEN** — the design being final is exactly the condition that unfroze it… ELIGIBLE for the next reviewer round, **ready to send, NOT sent — the founder dispatches**: `panelHeadline`, `panelSub`, `panelDemoAlt`, `tryResearch`, `tryVerify`, `tryExplain` — 6 keys × 16 locales = 96 cells, 6 EN founder-ratified, 90 MT not native-reviewed"*, while `cardDesc*` (+ `featuresHeading`/`tagline`/`subtitle`/`scrollHint`) are *"byte-identical to fly 232 and carry no new review debt"*. The deleted generation (`panelIntroTitle/Sub`, `panelTag1-3`, `panelDesc1-3` — added 2026-08-12, retired pre-review in B4.1c) no longer exists at HEAD — verified zero grep hits in code.

**Dead key found live at HEAD: `t.tryIt`** — 17 declarations (interface + 16 locales = **16 cells**, unit: key-locale pairs), **zero consumers** (`git grep "tryIt"` excluding the string files = zero). Already flagged at fly 233 ("`tryIt` is a dead key, pre-existing at fly 232") — still unfixed. Same class as the V1 deletion (pure removal, Rule 16 not triggered).

---

## C1/C2 — copy vs Ruling C route + ADR 004 wedges

Wedges (ADR 004 `docs/decisions/004-prescription-parser-deferral.md`, "Vela 護城河重新定位", verbatim): **W1 Your Language** (16 lang UI + 28M+ English literature) · **W2 Local Awareness** (TW/JP/KR/SG/MY/TH + 6 expansion + WHO fallback) · **W3 Cross-Language Bridging** (WHO ICD-11 anchor) · **W4 Privacy-First & Anonymous**. Route: B2B-interim (STATE: *"UPDATE 2026-06-19 — … route DECIDED = B2B-interim; B2C is a SaMD-gated terminal"*, as-of :253). Also load-bearing from ADR 004: the **ingest-and-cite constitution** (present what the label says, never an interaction verdict) and "Vela is a multilingual literature search + verification tool, **not a prescription tool**".

| Key | en text (abridged; verbatim above) | Wedge(s) | Flag |
|---|---|---|---|
| tagline | "Ask in your language. **Verified by official sources.** Answered in yours." | W1 | ⚠️ **REVIEW — fly-225 class candidate**: "official sources" is a blanket provenance claim; Verify (FDA labeling) and TFDA are official, but Research's primary source is PubMed **literature**, which is authoritative, not "official". Same class as the fly-225 Bengali "government sources" removal — a provenance word stronger than the source warrants. Founder rules whether "official" over-claims here. |
| subtitle | "The AI medical search **for healthcare professionals** who work beyond English." | W1 + route | ✅ carries the B2B-interim TA explicitly. No flag. |
| panelHeadline | "Ask in your language. **Decisions grounded in evidence.**" | W1 | ⚠️ **REVIEW — wording question, not a defect**: "Decisions" brushes the clinical-decision framing ADR 004 walls off ("not a prescription tool"; no CDS). EN is founder-ratified post-ADR — likely a knowing choice; flagged because C2's job is to surface it, not to assume it. |
| panelSub | "…medical evidence in the language you know best, backed by **sources you can verify**." | W1 | none — verification claim is supportable (citations render on every answer). |
| tryResearch / tryVerify / tryExplain / featuresHeading / scrollHint / panelDemoAlt | CTAs / structural | — | none — no claims. |
| cardDescResearch | "…searches the **medical literature**… **citations you can open and check**." | W1 (partial: "the way you'd say it") | none — accurate to the pipeline. |
| cardDescVerify | "…**documented interactions in FDA drug labeling** and shows you **the source for each finding**." | — (feature claim) | ✅ conforms to the ingest-and-cite constitution (documented-in-label, source shown; no verdict language). |
| cardDescExplain | "…**standard reference ranges, with sources**. A free account is required; PDF and image upload comes with Pro." | — | none — no FDA claim (the false `explainSub` FDA claim died with V1's deletion). Pricing claim is product-config, verify at gate time. |
| heroChip1-3 | example queries | W1 (showcase) | none. |
| privacyPromise1-3 | "No identity or license verification required" / "Anonymous by default — no real name required" / "Your data is never shared, sold, or used to train AI" | **W4 — the only wedge-4 carriers on the page** | none on wording (the "never stored"-class false claim was already reworded 2026-06-08 per ledger); W4 presence is healthy. |
| footerDisclaimer | "Vela is a research tool, **not a medical device**. It does not provide medical advice." | — | ✅ the SaMD guard, aligned with ADR 004. |
| **— (absent)** | — | **W2 Local Awareness: NO landing string carries it.** The product HAS the feature (locale-hint Tier-1 live for zh-TW since fly 210; b1 waterfall fly 212/213) — the landing does not claim the differentiator ADR 004 calls the marketing anchor (*"全球第一個提供 TW/JP/KR 藥品差異對比的 AI" replaces "處方解析" as marketing anchor*). | **GAP** |
| **— (absent)** | — | **W3 Cross-Language Bridging: NO landing string carries it** (closest is tagline's "Answered in yours", which is W1 phrasing). | **GAP** |

**C2 summary: 2 of 4 wedges (W2, W3) have zero landing presence; W4 lives only in the hero privacy strip; W1 is carried 5×.** No string contradicts the route; two strings warrant provenance/framing review (tagline "official", panelHeadline "Decisions").

## C3 — Rule 16 cost lines for every flagged key

Premise correction first: the review pipeline is **UNFROZEN** at HEAD (STATE fly 233 paragraph — the FROZEN statement is the 2026-08-12 entry, superseded); what remains founder-gated is **dispatch** (reviewer round not sent) and **how non-en cells get produced** for any new change.

| Flagged item | Cost if changed |
|---|---|
| tagline reword | 16 cells (1 EN founder copy + 15 non-en — production mode is the founder's call: MT-then-review vs hold for reviewer round). tagline sits in the sent 84-row legal CSV lineage ("its 5 share/explore keys + tagline… none deleted") — a reword also touches that review artifact's lineage. |
| panelHeadline reword | 16 cells; EN is ratified + already carries 15 MT cells in the eligible-not-sent 90 — changing it before dispatch avoids double-review; changing after wastes a review round. **Sequencing point for the founder.** |
| W2/W3 wedge copy (if added) | NEW keys × 16 cells each + reviewer round growth; C2 gap is a scope decision, not a defect. |
| `tryIt` deletion | 0 new cells (pure removal, Rule 16 not triggered — precedent: the V1 3-key deletion rode a frontend commit). |
| Duplicate-flag + overflow-flag annotations | docs-only, 0 cells. |

---

## DECISION POINTS FOR FOUNDER

1. **Apply the 0c stale-flag annotation to the B4.1c overflow flag?** Evidence: 0a timeline + `tests/probes/landing_hero_overflow/result.json` (hOverflow 0 at 360/375/390 vs prod fly 240). Options: (a) apply the drafted annotation as-is; (b) re-verify on a real phone first (the original defect was founder-confirmed on-device; the probe is emulation); (c) leave the flag standing.
2. **Mark the V2 duplicate-copy flag discharged?** Evidence: B4.1d rewrite quote + HEAD strings distinct. Options: dated annotation on the B4.1c flag site / leave (it already reads as history inside a superseded header block).
3. **`tryIt` dead key (16 cells):** delete on the next frontend commit / keep. Evidence: zero-consumer grep at HEAD; flagged since fly 233.
4. **tagline "Verified by official sources":** rule whether "official" over-claims Research's PubMed surface (fly-225 class). Options: rule it fine (Verify/TFDA genuinely official) / reword (16 cells, C3 lineage note) / park for the reviewer round.
5. **panelHeadline "Decisions grounded in evidence"** vs the non-CDS constitution: ratify as-is (knowing choice) / reword (16 cells + eligible-list resequencing).
6. **W2/W3 wedge gap:** add wedge copy (new keys × 16 + review) / accept the gap for B2B-interim (the wedges live in-product, not on the landing) / defer until the A1 ruling. Evidence anchor: ADR 004 "行銷 narrative… replaces 處方解析 as marketing anchor" vs the C2 absence rows.
7. **Reviewer dispatch sequencing:** the 90 MT cells (6 keys) have been eligible-not-sent since fly 233; any ruling on #4/#5/#6 changes the send set. Options: dispatch now / rule copy first, then dispatch once.
8. **tagline ↔ panelHeadline shared opening sentence** ("Ask in your language."): intentional echo / vary one (16 cells).

*Filed 2026-08-27 by the landing recon car; Phase 0 commit attribution corrected same day pre-ruling (header note): fix = `2c1e5db` not `61d49f1`, and flag-vs-fix = parallel lines, not date order. Every count above names its command and unit; derived-vs-cited stated including on matches (V1: derived 0 vs cited 48, difference = the 2026-08-20 fix; Phase 0: derived hOverflow 0 vs the flag's 131, difference = the fly 232 fix reaching the flag's line at the 08-14 rebase + a mislabeled width frame; V3: derived 13 keys = consumed 13, match).*
