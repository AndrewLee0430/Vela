# RECON 2026-08-27 — Ledger slimming: weight map, anchor census, relocation options

**READ-ONLY RECON. Nothing was moved, edited, or deleted in any ledger. This file is the only write.**
**No recommendation is made — §E is an options table; the founder rules the relocation rules.**

- **Repo assertion (Rule 24):** toplevel `C:/Users/andre/projects/Vela`; HEAD = `e0b545f7f5f7887271b3e0b1eccdf3f94ae2a999` = `origin/main` (verified `git ls-remote origin main`); tree clean except untracked `.superpowers/`.
- **Baseline claims verified, not assumed:** prod = **fly 240** ✅ (`fly status` — both machines VERSION 240, one `stopped`/one `started`); TECH_DEBT nav = **152** ✅ (`grep -c "^- \["` = 152; per-class `grep -oE "^- \[[A-Z_ -]+\]" | sort | uniq -c` = OTHER 80 + DONE 47 + HONESTY 17 + COMPLIANCE 8, LAUNCH 0); BACKLOG = **44** ✅ (`grep -cE "^### "` = 44).
- **Governing constraints honored throughout:** git history is the backup; every candidate is **relocation, never deletion**; **mark-never-delete stands** — a tombstone is a pointer, never a summary-as-replacement (summaries may point, only full text may carry); anchors are load-bearing — §B measures exactly what each candidate would do to every citation class found.
- **Rule 20 note:** every figure below names its derivation command inline and re-derives in seconds from tracked files at the stated HEAD; no separate probe JSON is retained because the repo at `e0b545f` **is** the snapshot the figures are about.
- **check_baton note:** running `check_baton.py` on THIS file flags 3 WRONG — all three are intentional: `docs/archive/state_shipped_2026.md` and `docs/archive/tech_debt_done.md` are **proposed** destinations that do not exist yet (this recon proposes, it does not create), and `tests/test_webhook_cancel.py` is quoted from the self-test's must-fire list, where it is a **deliberately nonexistent** path. Everything else verified (24 claims).

---

## §A — Weight map

**Token estimator: tokens ≈ bytes / 4** (stated per instruction). Caveat: zh-TW text runs ≈3 bytes/char and ≈1 token/char, so bytes/4 **under**-estimates CJK-heavy passages; these files are majority-English, so /4 is used uniformly and read as a floor.

Derivation: `wc -l` / `wc -c` per file at HEAD; section splits via `awk` on the line ranges printed below.

### A.0 File table

| File | Lines | Bytes | ~Tokens | Session-read? (source of that status) |
|---|---:|---:|---:|---|
| STATE.md | 962 | 645,235 | 161.3k | **YES — every session** (doc map; Step 0.1) |
| TECH_DEBT.md | 1,972 | 544,391 | 136.1k | **YES** (doc map: "active gaps") |
| BACKLOG.md | 1,949 | 290,080 | 72.5k | **YES — per task** (Step 0.2) · **NOT A SLIMMING TARGET** (§A.3) |
| CLAUDE.md | 161 | 19,273 | 4.8k | **YES — auto-loaded** |
| docs/INDEX.md | 51 | 2,291 | 0.6k | **YES** (navigation) |
| **Session-read core total** | **5,095** | **1,501,270** | **≈375.3k** | |
| docs/PRD.md | 2,559 | 162,967 | 40.7k | on demand, § only (Step 0.3) |
| docs/decisions/ (10 files) | — | 86,800 | 21.7k | on demand, per ADR ref (Step 0.4) |
| docs/render_gate_checklist.md | 515 | 47,428 | 11.9k | per gate only (blank FORM) |
| docs/architecture.md | 267 | 14,321 | 3.6k | on demand |
| docs/human_eye_gate_checklist.md | 152 | 11,080 | 2.8k | per gate only (blank FORM) |
| docs/batons/recon_20260824_step8_and_pmid.md | 333 | 27,224 | 6.8k | **NO** — see §C4 |
| docs/batons/recon_20260825_payment_coverage.md | 323 | 20,784 | 5.2k | **NO** |
| docs/batons/positioning_audit_20260823.md | 144 | 17,603 | 4.4k | **NO** |
| docs/batons/recon_20260824_tier3_reachability.md | 175 | 15,802 | 4.0k | **NO** |
| docs/retrospectives/phase-0-2026-05.md | 346 | 16,277 | 4.1k | **NO** — read for archeology only |

The session-read core is ≈375k tokens, and **STATE + TECH_DEBT alone are 79% of it** (1,189,626 B). BACKLOG is 19%; CLAUDE + INDEX are 1.4%.

### A.1 STATE.md breakdown (962 lines / 645,235 B)

| Section (line range) | Bytes | ~Tokens | Notes |
|---|---:|---:|---|
| Header block (1–44) | 98,236 | 24.6k | Stack of superseded status paragraphs + "Archived header" (38–44). **Line 3 alone — the current-state line — is 21,848 B (~5.5k tok).** 5 strikethrough lines carry 47,188 B. |
| Phase (45–48) | 279 | 0.1k | |
| Current Focus (49–124) | 62,133 | 15.5k | Contains the Task-A QA block (81–124) = **51,144 B**, dated 2026-06-15, heading region marked CONCLUDED/deferred → §C5. Line 123 alone is 18,755 B. |
| Next Up block (125–254) | 40,156 | 10.0k | Incl. "Completed §2.1" (221–234, 598 B — negligible). |
| Recently Shipped (255–953) | 431,084 | 107.8k | 124 entries (`grep -cE "^- \*\*2026"` on the section), reverse-chronological, 2026-05-19 → 2026-08-26. |
| Pointer (954–962) | 319 | 0.1k | |

**Recently Shipped by month** (awk attributing each line to the current `- **YYYY-MM-DD**` entry):

| Month | Entries | Bytes | Avg B/entry |
|---|---:|---:|---:|
| 2026-08 | 62 | 273,053 | 4,404 |
| 2026-07 | 25 | 108,713 | 4,349 |
| 2026-06 | 22 | 43,018 | 1,956 |
| 2026-05 | 15 | 5,906 | 394 |

⚠️ Observation, not a proposal: **average entry weight grew 11× from May to July and has stayed there.** Any cutoff-based archive rule buys a one-time win; the steady-state cost is set by the recent window (Aug alone = 273 KB). Whether entry weight itself is a topic is the founder's, not this recon's.

**Strikethrough (`~~`) lines:** 43 lines / 81,732 B total — header 5/47,188 · Next Up 3/8,339 · Recently Shipped 35/26,205.

**Cutoff sizing for §C1** (entries strictly older than cutoff; today = 2026-08-27):

| Cut | Cutoff date | Entries | Bytes | First archived line |
|---|---|---:|---:|---:|
| 30-day | < 2026-07-28 | 59 | 128,408 | **848** (entry dated 2026-07-27) |
| 60-day | < 2026-06-28 | 34 | 42,518 | below 848 |
| 90-day | < 2026-05-29 | 15 | 5,906 | further below |

### A.2 TECH_DEBT.md breakdown (1,972 lines / 544,391 B)

Attribution: each line assigned to the most recent `^- \[CLASS\]` heading above it (the handful of `####` group-header lines mid-file land in the preceding entry's class — noise ≤5 lines).

| Class | Entries | Lines | Bytes | ~Tokens |
|---|---:|---:|---:|---:|
| Preamble + nav (before first entry) | — | 310 | 24,377 | 6.1k |
| [OTHER] | 80 | 755 | 207,931 | 52.0k |
| **[DONE]** | **47** | **578** | **191,812** | **48.0k** |
| [HONESTY] | 17 | 231 | 76,440 | 19.1k |
| [COMPLIANCE] | 8 | 98 | 32,677 | 8.2k |

**Answer to the §A question: yes — [DONE] carries the bulk disproportionately.** 47/152 entries (31%) hold 191,812/520,014 entry-bytes (37%), and of that, **heading lines are only 12,081 B** (`grep "^- \[DONE\]" | awk length-sum`) — **93.7% of [DONE] weight is body text below headings**, which is exactly what a heading-verbatim tombstone (§C3) relocates.

### A.3 BACKLOG.md — measured, NOT a slimming target

1,949 lines / 290,080 B / ≈72.5k tokens. **Ruled a Decision Archive 2026-08-26 (founder Ruling A, `docs/batons/positioning_audit_20260823.md` §3) — it already IS the archive; no relocation class touches it.** Its weight is addressable only via §D tiering (when it gets read), never via moving content out of it.

---

## §B — Anchor dependency census

### B.1 What was searched (pattern classes + commands)

| # | Pattern class | Command (over tracked files) | Hits |
|---|---|---|---:|
| P1 | `file:line` citations into ledgers | `git grep -oE "(STATE\|TECH_DEBT\|BACKLOG\|CLAUDE)(\.md)?:[0-9]+" -- "*.md" "*.py"` | **111** (unique targets: 15 STATE lines, 19 TECH_DEBT lines) |
| P2 | Marked heading-citations | `git grep -cniE "heading ends\|entry headed\|the entry whose\|see the .* entry\|sub-bullet" -- "*.md"` | 80 lines across 10 files |
| P3 | Backticked anchor phrases (check_baton C2 semantics: ≥20 chars, ≥3 words, not a `file:line`) from the 4 batons + 2 gate checklists + CLAUDE.md, resolved against STATE/TECH_DEBT with region classification | scratch Python replicating `ANCHOR`/`CITE` regexes from `check_baton.py` | 21 at-risk matches (below) |
| P3′ | Same, **mutual**: STATE anchors→TECH_DEBT and TECH_DEBT anchors→STATE | same script | 31 + 46 (below) |
| P4 | `batons/` path references | `git grep -c "batons/" -- "*.md" "*.py"` | 22 across 6 files |
| P5 | Programmatic/content use of ledgers by code | `git grep -lnE "STATE\.md\|TECH_DEBT\.md\|BACKLOG\.md" -- "*.py" "*.ps1" "*.ts" "*.tsx" "*.mjs" scripts/ tests/` + manual read of each hit | 9 files, **all comment/docstring pointers except `check_baton.py`** |

**Coverage statement — what this census may have missed:** plain-quoted or *italicized* heading fragments that carry none of the P2 marker phrases and no backticks; 「」-quoted CJK fragments; quotations living in untracked files or session transcripts; BACKLOG-body quotations of STATE/TECH_DEBT phrases (BACKLOG is not a move target, but its quotes of moved body text would resolve only via the archive after a move). The census is stated as **pattern-class-complete for P1/P4/P5, and sample-complete for quoted-phrase classes (P2/P3) at the listed marker patterns and regex** — not exhaustive over free-form prose quotation.

### B.2 Line-number citations (P1) vs candidate regions

Every cited line was classified by containing region/entry (scratch script; entry = most recent `^- \[CLASS\]` heading for TECH_DEBT, section line-ranges from §A.1 for STATE):

- **Safe under every candidate:** TECH_DEBT:12/50/110/242/264/270 (all in preamble/nav, above the first [DONE] at line 318); STATE:67/75/84/161/167/238/249/250/261/269/612/706/730 (all above line 848, and C1 removes only below 848).
- **C1 (30-day) touches exactly ONE cited line:** `STATE.md:848` (cited by TECH_DEBT.md:429) — it is the *first* archived entry's heading, so its one-line tombstone stays at ≈ the same line number and keeps the heading text. Near-zero rot. 60/90-day cuts touch **zero** cited lines.
- **C2 (header) is the dangerous one for line cites:** deleting ~35 lines from the TOP shifts **every** cited STATE line below 44 (14 distinct lines, incl. self-cites and TECH_DEBT→STATE cites). A shifted-but-in-range cite is **silent** — `check_baton.py` C1 flags only out-of-range/blank, and its own docstring calls this the worst rot class.
- **C3 ([DONE] bodies) — cited lines INSIDE moving bodies: 5** (TECH_DEBT:322, 933, 935, 1044, 1079 — cited by batons and by `tests/probes/ownership_eval/run_eval.py:314` docstring), plus **13 more cited TECH_DEBT lines ≥318 shift** as bodies above them leave.

### B.3 Anchor phrases (P3/P3′) vs candidate regions

At-risk matches (phrase currently resolving into a region a candidate would move):

| Citing file → target region | Matches |
|---|---:|
| recon_20260824_step8_and_pmid.md → TECH_DEBT [DONE] bodies | 9 |
| recon_20260825_payment_coverage.md → TECH_DEBT [DONE] bodies | 6 |
| human_eye_gate_checklist.md → TECH_DEBT [DONE] bodies | 2 |
| render_gate_checklist.md → TECH_DEBT [DONE] bodies | 1 |
| CLAUDE.md → TECH_DEBT [DONE] bodies (incidental content overlap, Rule-12 strings) | 2 |
| recon_20260825_payment_coverage.md → STATE header (C2 region) | 1 |
| **Mutual:** STATE anchors → TECH_DEBT [DONE] bodies | **31** |
| **Mutual:** TECH_DEBT anchors → STATE header / STATE RS≥848 | 3 / 4 |
| (For scale, anchors into KEPT regions — unaffected: batons/checklists→STATE RS-kept 22, →TECH_DEBT open classes 10, TECH_DEBT→STATE RS-kept 39.) | |

**What a move does to these:** a grep for a **heading** still hits the tombstone (kept verbatim) *and* the archive copy — truthful, one extra hit. A grep for **body** text hits only the archive — truthful but one hop away; a grep *scoped to the original file* for body text hits nothing, which is why **the tombstone pointer must name the archive file** (the hop is then recoverable in one step). This satisfies "every existing grep hits something truthful" for heading-anchors unconditionally, and for body-anchors only via the repo-wide grep habit.

### B.4 Tooling dependencies

- **`tests/probes/baton_check/check_baton.py` is the only code that reads ledger CONTENT.** `LEDGER = ["STATE.md", "TECH_DEBT.md", "BACKLOG.md", "CLAUDE.md"]` (line 42). Consequences of any move: **(a)** C2 anchor-uniqueness greps exactly those four files — a phrase whose hits drop 1→0 becomes *silent* (treated as prose: no error, but also **no verification**; the 31+18 body-anchors above lose their check); 2→1 becomes "verified unique" (fine). A new `docs/archive/` file is **not** in LEDGER — extending LEDGER is a one-line change, listed as an option in §E, not assumed. **(b)** C1 resolves `file.md:NNN` — §B.2 covers it. **(c)** c1b diff-scope covers only the four ledger files — tombstone edits are in scope (good), archive files are not.
- **No other script parses the ledgers.** All other P5 hits are docstring/comment pointers. Two committed gate scripts (`scripts/dailymed_danger_path_verify.py`, `tests/test_danger_path_exit_codes.py`) cite the DANGER-PATH ratification **by entry heading** and explicitly say "GREP THE HEADING, NOT THE NUMBER" (`dailymed_danger_path_verify.py:9-10`). That entry **is [DONE]** (TECH_DEBT.md:616) — under C3 its heading survives in the tombstone (the grep still resolves) but the **ratification record body moves to the archive file**; the scripts' "the record is the TECH_DEBT.md entry headed…" sentences become one-hop-indirect. Flagged as C3's most load-bearing single anchor.

### B.5 🔴 PRE-EXISTING FINDING (discovered by this census, not caused by it): the baton-checker self-test is broken at HEAD

`python tests/probes/baton_check/check_baton.py --self-test` at `e0b545f` exits 1: **`❌ SELF-TEST BROKEN — these known errors did NOT fire: ['TECH_DEBT.md:784']`.** The fixture's known-error citation `TECH_DEBT.md:784` was pinned when line 784 was blank (TECH_DEBT.md:1218 records ":784 was a blank line"); ordinary ledger growth has since made line 784 a non-blank `[HONESTY]` entry heading, so the C1 check correctly does not fire — **the negative control rotted by the exact mechanism the tool exists to catch.** The other must-fire (`tests/test_webhook_cancel.py`) still fires. Read-only recon: **not fixed here.** Two repair shapes for the founder: repin the fixture to a currently-failing citation, or make `must_fire` content-based instead of line-pinned. ⚠️ Sequencing: **any C3/C2 relocation reshuffles TECH_DEBT/STATE line numbers and re-rolls this dice** — the self-test repair belongs **before or with** the first relocation car, else the gate's pass/fail flips silently with each move.

---

## §C — Candidate relocation classes (sized; ranked in §E; nothing recommended)

Tombstone byte estimates: STATE ≈100 B/line (date + heading + destination), TECH_DEBT ≈ heading line kept verbatim + ≈80 B pointer line.

| Class | What moves | Bytes saved (net of tombstones) | Tombstones | Anchor risk (from §B) | Effort |
|---|---|---:|---:|---|---|
| **C1-30d** | STATE RS entries < 2026-07-28 → `docs/archive/state_shipped_2026.md` | 128,408 − ~5.9k ≈ **122.5k** | 59 | **LOW** — 1 cited line (STATE:848, = first tombstone, ≈same line, heading kept); 4 TECH_DEBT anchors into the region (heading-tombstones keep them resolving) | one careful docs car |
| C1-60d | subset of above | 42,518 − ~3.4k ≈ **39.1k** | 34 | **NEAR-ZERO** — no cited lines, region entirely below 848 | small car |
| C1-90d | subset | 5,906 − ~1.5k ≈ **4.4k** | 15 | none found | trivial, low yield |
| **C2** | STATE header history (lines ~4–44 minus the current-state line) → current-state line + pointer | ≈ **75.7k** (98,236 − line 3's 21,848 − ~0.7k kept) | 1–7 | **HIGHEST PER BYTE** — shifts ALL 14 cited in-range STATE lines below; silent rot invisible to check_baton; 3 TECH_DEBT anchors + 1 baton anchor into the region | small edit, big blast radius — if ever, do LAST + publish a shift note |
| **C3** | TECH_DEBT [DONE] entry **bodies** → `docs/archive/tech_debt_done.md`; tombstone = original `- [DONE]…` heading line **VERBATIM** + pointer | 191,812 − 12,081 − ~3.8k ≈ **176.0k** | 47 | **MEDIUM** — nav consequence: **counts unchanged by construction** (heading survives ⇒ `grep -c "^- \["` still 152; class breakdown after: OTHER 80 · DONE 47 · HONESTY 17 · COMPLIANCE 8 — identical counts; DONE line-weight drops 578→~94 lines). BUT: 5 cited lines inside moving bodies + 13 shifted below line 318; **49 body-anchor phrases (31 from STATE, 18 from batons/checklists) drop out of check_baton's LEDGER grep**; the DANGER-PATH ratification record (§B.4) goes one-hop; **§B.5 self-test must be repinned first** | 1–2 docs cars (47 bodies), the heaviest but highest-yield move |
| **C4** | docs/batons/ (4 files, 81,413 B) | **0 from the repo** — batons are in NEITHER the CLAUDE.md doc map NOR docs/INDEX.md; they are cited *by* the ledgers as evidence (22 path refs) but are already point-in-time, repo-only docs. **No repo move needed; the win is §D PK-tiering only.** | 0 | none | none (habit only) |
| **C5a** | STATE Task-A QA block (lines 81–124, dated 2026-06-15, marked CONCLUDED/deferred in the section headers) | 51,144 − ~0.2k ≈ **50.9k** | ~2 | **LOW** — 1 baton anchor into Current Focus; block sits above line 125 so moving it shifts all cited lines 161–848 → same silent-shift caveat as C2, **unless moved in the same car as C2** (one shift event instead of two) | small car |
| C5b (observations only, no class proposed) | (i) 35 strikethrough RS-kept lines / 26,205 B — future C1 fodder as they age; (ii) monster single lines: STATE line 3 = 21,848 B and line 123 = 18,755 B — both *current*, so slimming them is a founder content call, not a relocation; (iii) the recent-window growth itself (§A.1: Aug = 273 KB stays under every cut) | — | — | — | — |

---

## §D — PK tiering proposal (paper only; **founder-side sync-habit change, not a repo change**)

**Assumption stated up front:** the actual PK sync set is not derivable from the repo; the "before" figure assumes PK mirrors the session-read core + PRD + architecture. If the real set differs, the arithmetic re-derives in one minute from §A.0.

- **Session tier (synced into PK, read every session):** CLAUDE.md · STATE.md · TECH_DEBT.md · docs/INDEX.md · docs/architecture.md (optional).
- **Archive tier (repo-only, fetched on demand):** **BACKLOG.md** (its own ruling already names it an archive; Step 0.2 fetches the one entry the STATE queue names) · docs/PRD.md (§-fetch) · docs/decisions/ · docs/batons/ (C4) · docs/retrospectives/ · both gate-checklist FORMs (per-gate) · the new docs/archive/* files.

| Scenario | PK bytes | ~Tokens |
|---|---:|---:|
| Before (assumed: core 5 + PRD + architecture) | 1,678,558 | 419.6k |
| After — tiering only, no repo moves (drop BACKLOG/PRD/checklists/batons to archive tier) | 1,225,511 | 306.4k |
| After — tiering + C1-30d + C3 | ≈927,000 | ≈231.8k |
| After — tiering + C1-30d + C3 + C2 + C5a | ≈800,400 | ≈200.1k |

Moving BACKLOG to the archive tier changes **when it is read** (per task, per entry), not where it lives or what it says — consistent with Ruling A; still a founder call because Step 0.2 currently assumes it is at hand.

---

## §E — Options table (rule combinations; ranked by effort/risk; **NO recommendation — founder rules**)

Baseline: session-read core = 1,501,270 B ≈ 375.3k tokens.

| Option | Composition | Core after (bytes / ~tokens) | Saved | Tombstones | Risk summary |
|---|---|---:|---:|---:|---|
| **O0** | §D tiering only (incl. C4) — zero repo edits | 1,501,270 in repo; **PK-read drops to ≈306k tok** | PK −113k tok | 0 | none (habit change only) |
| **O1′** | C1-60d | 1,462,157 / 365.5k | 39.1k B | 34 | near-zero |
| **O1** | C1-30d | 1,378,769 / 344.7k | 122.5k B | 59 | low (1 boundary cite) |
| **O2** | C1-30d + C3 | 1,202,769 / 300.7k | 298.5k B | 106 | medium — §B.5 repin is a prerequisite; 49 body-anchors leave check_baton's grep; ratification record one-hop |
| **O3** | O2 + C5a | 1,151,869 / 288.0k | 349.4k B | ~108 | medium — C5a shifts cited lines below 124 (pair it with C2 if C2 ever runs) |
| **O4 (max)** | O3 + C2 | 1,076,169 / **269.0k** | 425.1k B | ~115 | highest — every in-range STATE line cite below the header silently shifts; do C2 last, publish a shift note, run `check_baton` over all four batons after |
| Optional rider for O2+ | add `docs/archive/*` to `check_baton.py` LEDGER (one-line change) so moved body-anchors stay verifiable | — | — | — | turns C3's "silent" anchor class back into a checked one; touches `tests/probes/` (no longer docs-only) |

**Best case including tiering: session-read ≈269k tokens in-repo, ≈200k as actually synced (§D) — vs 375k/420k today.** The floor is set by what no rule here touches: BACKLOG (72.5k tok, ruled archive), the recent RS window (Aug alone ≈68k tok), and open TECH_DEBT classes (≈79k tok).

**Sequencing constraints regardless of option chosen:** (1) repair §B.5 (self-test repin) before or with the first relocation car; (2) all moves within one file happen in ONE car, navs re-derived after (`grep -c "^- \["` = 152 expected unchanged under C3); (3) after any move, run `check_baton.py` on all four batons and inventory new WRONG/DRIFT — remembering it cannot see shifted-in-range cites; (4) tombstone pointer lines name the destination file explicitly, so a scoped body-grep miss recovers in one hop.
