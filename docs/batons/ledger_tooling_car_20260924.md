# LEDGER-TOOLING car — entry walker · extraction retention · STATE 30-day ×5 · C3 ×1 (built 2026-09-24)

**Car tag:** `ledger_tooling`. **Mode:** BUILD LOCAL — two commits, **NOT pushed, NOT deployed**. Docs + tooling only;
no product file (api/ pages/ components/ utils/ styles/) touched. Prod = fly 259 at
`9fc4d47bf6dca6069a9fb7a5981d92b1a17bf7ca`, unchanged.
**Base:** `eb0db2e2c346b53db26a0a345c4f702d2d729212` (Rule 24 asserted: toplevel `C:/Users/andre/projects/Vela`).
**Commits:** A `0fab1d0` fix(tooling) — `scripts/extract_session.ps1` only · B (the commit that adds this file) — docs.
**Line numbers** below are at `eb0db2e` unless marked otherwise, and are written as "TECH_DEBT :N" / "STATE :N".

## §0 Founder rulings 2026-09-24 (verbatim; founder replied 「照建議」 to the strategy proposal)

- **R1** The extract_session.ps1 entry-walker defect gets NO new TECH_DEBT entry; its home is STATE Next Up item 4 open-list (5) + this car's baton.
- **R2** Walker selection: (1) first hit on a ^- \[ heading line; else (2) first hit NOT inside an <!-- --> block whose upward walk reaches a ^- \[ line; else (3) print "NO ENTRY HIT" plus every hit classified — never print a range starting at line 1 by fallback.
- **R3** Extraction retention: new parameter -Keep (int, default 2, must be >= 1). After the new file is fully written, keep the newest -Keep files by NAME timestamp among top-level files matching ^extraction_\d{8}_\d{6}\.md$ in the output folder; delete the rest (files only, no recursion, -LiteralPath), print each deleted name and the kept count; a prune failure is a Write-Warning, never a failed extraction. The three committed citations of extraction files (TECH_DEBT :1292 ×2, :1640 ×1 at eb0db2e) are annotated with a dated bullet, never rewritten.
- **R4** Relocate the 5 STATE Recently Shipped candidates (lines 385–453 at eb0db2e, cutoff < 2026-08-25) to docs/archive/state_shipped_2026.md.
- **R5** C3: relocate ONLY the [DONE] body at TECH_DEBT :1282 (Explain LEGACY rows) this car. E2 (:1434), E3 (:1452), E4 (:1466) stay full: E2's body carries open-list item (6) (":1448 recorded, NOT filed"), and all three are the ground-(i) record that open-list item (1) PHI-at-rest must read. Held until item (1) is dispositioned.
- **In-car ruling (2026-09-24, asked mid-build):** STEP 4(d) said each STATE heading "stays verbatim and gains the suffix" AND "in the SAME
  form as the 2026-09-21 archive pass". The two conflict for all 5 candidates (first lines 240–945 chars). Founder chose the
  **precedent 139-char form** (the `885eae3` commit message's rule: first line whole if <= 139 chars, else cut at the last space at
  index <= 139, append U+2026 plus `**` iff the prefix has an odd `**` count, then the pointer suffix). Self-tested 114 / 114 against
  the existing STATE tombstones before use (N=138 → 96, N=140 → 102 under the same cut; so N=139 is pinned, not assumed).

## §1 Probe summary (read-only, same session, at `eb0db2e`)

- Ledger pins (extraction §3 method): STATE `7a1eea7288d978af` · TECH_DEBT `b1043b62cdcd64db` · BACKLOG `be5c292f43454a57` — all MATCH.
- Old walker: first `git grep -n -i "<Task>" -- TECH_DEBT.md` hit, walk up to the nearest `^- \[` line, walk down to the line before the
  next one. The first `^- \[` line in TECH_DEBT is :1251, so ANY first hit above it (85 `<!-- -->` blocks, the title-list rows, the
  single-line `<!-- … → [DONE] -->` tombstones) stopped at line 1 and printed lines 1–1250, silently.
- `authorized_parties` hits: :555 (inside the NAV block :534–:568) · :2529 (the entry heading) · :2531 · :2533 · :2547 · :2695 —
  exactly the extraction's claim.
- Rule 27 (walker): `grep -n -i -E "walker|entry-walker|title-row|extract_session" TECH_DEBT.md BACKLOG.md STATE.md` +
  `grep -rn -i "walker" docs/batons/` — the only ledger text was the STATUS 2026-09-22 bullet TECH_DEBT :1293 inside the `[DONE]` entry at
  :1282 ("founder to rule"); no entry of its own. Rule 27 (retention): none found —
  `grep -n -i -E "extraction.{0,60}(retention|prune|delete|keep)" TECH_DEBT.md BACKLOG.md STATE.md` (the unnarrowed
  `extraction.*(…)` form hit 9 very long lines whose words sat hundreds of chars apart — all false positives).
- Extraction folder before this car: 22 files, all matching the name pattern, 0 other entries; name order == LastWriteTime order.

## §2 Commit A `0fab1d0` — walker (R2) + retention (R3)

Edited through a Python file under the probe scratch folder; the file's UTF-8 BOM and LF endings preserved; 0 control bytes other than
\t \n \r. Comment state is scanned across the whole file (multi-line blocks); a "heading" is a `^- \[` line whose start is not inside a
comment. Rule (3) classes: `comment` (the match column is inside a block) · `title-list` (`^- ` + backtick + `[`) · `body-no-heading`.

**Walker before / after** — every "after" is a real run of the script, `-PriorSha eb0db2e`:

| Run | `-Task` | before (at `eb0db2e`) | after (commit A) |
|---|---|---|---|
| 1 | `authorized_parties` | first hit :555 (NAV comment) → printed :1–1250 | `entry walker: hit :2529 selected by rule heading` → :2529–2549 |
| 2 | `PHI input gate coverage` | first hit :1200 (`<!-- → [DONE] -->` tombstone) → printed :1–1250 | `hit :1452 selected by rule heading` → :1452–1465 |
| 3 | `ChatHistory.answer stored unsanitized` | first hit :556 (NAV comment) → printed :1–1250 | `NO ENTRY HIT …` + `:556 [comment] …`; no range |
| 4 | `CLERK_AUTHORIZED_PARTIES` | first hit :2533 → :2529–2549 (worked by luck of order) | `hit :2533 selected by rule body` → :2529–2549 |

Run 4 phrase derivation: `git grep -n -i "CLERK_AUTHORIZED_PARTIES" -- TECH_DEBT.md` → :2533, :2547 — both body lines, below :1251, outside
every comment, neither a heading → qualifies for rule (2).
Negative check: `-Keep 0` is refused at parameter binding ("less than the minimum allowed range of 1"); no file written.

**Prune readback:** run 1 wrote `extraction_20260924_130508.md` and printed 21 `PRUNED:` names + `KEPT: 2` — 22 existing + 1 new − 2
kept = 21 (the prompt's "20" did not count the new file). Runs 2–4 each pruned 1. Folder after the four runs: exactly 2 files, the
newest two by name. The prune never deletes the file just written, even under clock skew.

## §3 Commit B — ledgers

- **R3 annotations.** Re-derived `git grep -n -i -E "extraction_20[0-9]{6}_[0-9]{6}" -- .` → 3 names on 2 lines (TECH_DEBT :1292 ×2,
  :1640 ×1) = the probe's 3, MATCH. One dated bullet appended at the end of each citing entry: the `[DONE]` "Explain LEGACY rows" entry
  (:1282; appended BEFORE its body moved, so the archive carries it, and it records the :1293 walker item as discharged by commit A under
  R1/R2) and the `[OTHER][P2]` public API surface entry (:1627). Citation text itself unchanged.
- **R5 / C3.** The :1282 body (16 lines at `eb0db2e` + the new bullet = 17 lines) → new section
  `## Archive pass 2026-09-24 — 1 [DONE] body (C3; …)` at the end of `docs/archive/tech_debt_done.md`, same form as the 2026-09-21 pass.
  Heading line unchanged in TECH_DEBT, the standard tombstone line under it. **Byte compare (LF-normalized) pre-change body vs archived
  block: IDENTICAL** (sha256-16 `d05f818b3b7fe961` both sides); first 16 lines == the HEAD blob's :1283–1298: True.
  Script readback after: `[DONE]` 64 — 61 relocated, 3 still full (E2 / E3 / E4, held per R5).
- **R4 / STATE 30-day.** Placement derived first: in `docs/archive/state_shipped_2026.md` the 2026-09-21 pass section follows the
  2026-08-27 pass and sits BEFORE the trailer line `For older work see` + backticked `git log` (the file's last line); the new section
  `## Archive pass 2026-09-24 — 5 entries (2026-08-23 → 2026-08-24), cutoff < 2026-08-25` went in the same place, trailer still last.
  Candidates re-derived = STATE :385–403 · :405–416 · :418–429 · :431–439 · :441–453 (65 lines) — MATCH with R4. **Byte compare
  (LF-normalized) 5 blocks at HEAD vs archived: IDENTICAL** (sha256-16 `ae08f34a6c2f4ada` both sides). Each heading → the 139-char
  tombstone + pointer suffix (in-car ruling, §0). `extract_session.ps1` §6 re-run after the edit: **0 candidates, 119 already archived,
  37 within 30 days** (36 + this car's ship entry). STATE 657 → 598 lines; archive 649 → 721.
- **NAV.** Pre (at `eb0db2e`) and post, same commands: 0 + 9 + 18 + 64 + 101 = 192 · `^- ` 227 = 192 + 35 · [sec] loose 15 / strict 14.
  Delta 0. New dated NAV block at the top of TECH_DEBT; older blocks untouched. RULE 27: NO new entry.
- **STATE.** New header segment on line 3 (prepended; "Previous header follows"); Next Up item 4 open list annotated (R1–R5 verbatim;
  (3) DONE · (4) PARTIAL, E2/E3/E4 held · (5) FIXED · (8) NEW retention DONE); one terse Recently Shipped entry.
- Encoding: all four ledger/archive files are LF, no BOM (`git ls-files --eol` i/lf w/lf), preserved; 0 control bytes asserted on write.

## §4 Recorded, NOT filed

- **(i) Same-second file-name collision.** The output name has one-second resolution; two runs inside the same second share one name and
  `WriteAllText` overwrites the first. Out of scope per the car prompt; noted in a script comment only.
- **(ii) TECH_DEBT :1748 has a non-standard MERGED tombstone** (at `eb0db2e`). The script's substring test counted 60 relocated bodies,
  while `git grep -c -F "(body → docs/archive/tech_debt_done.md" -- TECH_DEBT.md` = 59: the P3 credential-hygiene entry's
  pointer reads "relocated VERBATIM to …" inside a MERGED-duplicate note, followed by two later dated bullets. The substring count is
  right; any tool keyed on the standard tombstone line would read 59. (After this car: 61 by the substring test, 60 standard.)
- **(iii) A backtick in an entry heading makes a plain-text `-Task` phrase miss the heading.** The `ChatHistory.answer` entry heading
  (TECH_DEBT :2794 at `eb0db2e`) wraps the symbol in backticks, so "ChatHistory.answer stored unsanitized" matches only the NAV comment.
  The old walker hid this behind a file-head dump; it now surfaces as NO ENTRY HIT with the hit classified.

## §5 Open after this car

Next Up item 4 open list, still founder to sequence: (1) PHI-at-rest `ChatHistory.answer` policy · (2) azp code fix · (6) the test-harness
seam · (7) the fail-closed UX message on /verify. (4) is PARTIAL — E2 / E3 / E4 bodies held until (1) is dispositioned (R5).
Push of `0fab1d0` + commit B: founder call.
