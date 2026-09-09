# `baton_check/` — verify a handoff document against the repo before acting on it

**Run it first thing, before you act on a baton:**

```bash
python tests/probes/baton_check/check_baton.py <baton.md>
python tests/probes/baton_check/check_baton.py --self-test    # negative control, no args
python tests/probes/baton_check/check_baton.py STATE.md       # or any ledger file
```

No network, no LLM, no cost. Seconds. **It never blocks** — exit code is always 0.

**Windows, cp950 console (the zh-TW default code page):** the report contains `⚠️` / `✅`, and the script crashes at its final `print(report)` with `UnicodeEncodeError: 'cp950' codec can't encode character '⚠'` (`check_baton.py:438`) — every check has already run; only the print fails. Run it as

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"; python tests/probes/baton_check/check_baton.py <baton.md>
```

(or `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python …` in Git Bash). Docs-only note (2026-09-09) — the checker itself is unchanged; the cp950 class is tracked in TECH_DEBT (the TFDACorpusStore `print()`/cp950 entry names `check_baton.py:438`).

---

## Why it exists

Over ~10 batons in a single session (2026-08-19 → 08-24), **every baton contained at least
one error**, and some were load-bearing:

- a ratification claim citing `TECH_DEBT.md:784` — a **blank line**; the rule was at `:827`
  and read *"proposed 2026-07-27, founder to ratify"*. The claim was false on both halves.
- a pytest workaround citing `tests/test_webhook_cancel.py` — **renamed four days earlier**.
- two artifact filenames off by one and two seconds.
- ten STATE labels reading "committed, NOT pushed" for commits already on `origin/main`.

## 🔴 The design constraint is a measurement, not a preference

The **first** citation scanner written for this raised **193 flags on the ledger, 174 of them
false** — bare basenames like `server.py:450` read as missing files. **10% precision.**
Resolving basenames through `git ls-files` dropped it to **40 flags at ~85% precision**.

Two further false-positive classes were found by running it on the live ledger and fixed:
a **range** citation (`retriever.py:395-413`) that legitimately starts on a blank line, and a
**relative link** (`retrieval_attrition/README.md`) that resolves fine. C2 also had to
exclude the input file from its own count — scanning `STATE.md` reported *113* matches for
the phrase `` ` rather than ` `` because every phrase trivially matches itself.

> **A checker that cries wolf trains the reader to ignore it, which is worse than no checker.**
> Every **blocking** check is zero- or near-zero-false-positive. Everything noisy is
> **advisory** and says so in the output.

Current flag rate on the whole ledger: **~6%** (85 flags against 1,353 verified claims).

## The checks

| id | level | drift category (instances behind it) | what it does |
|---|---|---|---|
| **C1** | blocking | line-number pointers that moved (**12 repaired**; 40/410 ledger citations stale) | resolve `FILE:LINE` and bare `dir/file.ext` — exists? in range? line non-blank? A range is stale only if **every** line in it is blank |
| **C2** | blocking | same | quoted phrases: `grep -c` must be exactly 1 across the other ledger files |
| **C3** | blocking | true-when-written, false-later (**10 STATE labels**) | every SHA: `git branch -r --contains` → on origin, or local-only |
| **C5** | blocking | recorded as ratified when it was not (**2**) | a *ratified/approved/signed-off* claim whose cited target says *"proposed"* or *"to ratify"* |
| **A6** | advisory | population conflation (**4**; 3 failed, 1 held) | a figure on a line that names no query set |
| **A7** | advisory | mirror-not-the-thing (**3**, TECH_DEBT #8) | a cited artifact whose own text declares `mirror_caveat` |
| **C1b** | suggest | prevention | **new** `FILE:LINE` citations in your uncommitted ledger edits, with no anchor phrase beside them |

**C1b scope:** the working-tree diff (staged + unstaged) of the four ledger files against
`HEAD`. That is "about to be written" in the only sense a script can see — no hooks, no
session state — and it catches the citation before the commit that freezes it.
**It suggests, it never blocks.** A line number is sometimes the right thing to write:
`retriever.py:518-529` for an exemption's *extent* is genuinely useful. The suggestion is
*"carry an anchor phrase alongside"*, not *"remove the number"*.

**C2 archive scope (2026-08-27, ledger slimming):** ledger text relocated **verbatim** to
`docs/archive/*.md` (rules C1-30d / C3) is consulted as a **fallback only** — a phrase that
matches zero ledger lines but exactly one archive line verifies as unique. Ledger-hit
semantics are unchanged, so the tombstone + archive duplication of a relocated heading
cannot produce a new multi-match flag.

## 🔴 What this does NOT catch

**It checks whether a number matches a file. It does NOT check whether a conclusion still
holds — and this session's most expensive errors were all the second kind.**

- **A number that is right but means something else.** `13/20 queries end below 5` was
  arithmetically correct; it was measured on the wrong population. No file disagrees with it.
- **A conclusion overturned by later evidence.** Nothing in the repo contradicted *"the seat
  targets the bottleneck"* — it took three live runs to refute.
- **Whether a cited line still says what the prose claims.** `TECH_DEBT.md:242` resolved to a
  non-blank line; it was simply the **wrong entry**. Semantic, not mechanical.
- **Judgement inherited as fact** — a prior session's estimate re-quoted as a measurement.
- **The mirror/thing distinction itself.** A7 only greps for a marker this repo happens to
  write down; it would not transfer to a repo that doesn't.

**Expected yield: roughly two-thirds of baton errors, and none of the expensive ones.**
Of 9 verified baton errors in the source session, **6 were mechanical, 3 were semantic**.

## Negative control

`--self-test` runs against `fixtures/baton_20260821_ratification.md` — a **real** baton whose
errors are documented and independently verified in the TECH_DEBT entry headed
*"[P1 · gate integrity — the section-aware DANGER-PATH criterion had NO ratification record…]"*.
It asserts both known errors fire and that ≥2 blocking findings are produced.

**A gate that has never failed has not been shown to work** — the canary gate's lesson,
applied here. **Do not "fix" the fixture's errors; they are the point.**

**2026-08-27 repair (the tool's own drift class ate its own negative control):** the
fixture's second must-fire, `TECH_DEBT.md:784`, was pinned while that line was blank; the
ledger grew past the pin and the line is now a non-blank entry heading, so the check
correctly stopped firing and `--self-test` reported itself broken (found by the ledger-
slimming recon, `docs/batons/recon_20260827_ledger_slimming.md` §B.5). The fixture is
untouched. The self-test now asserts the fixture's **path-based** error only (time-stable),
plus **dynamic pins located at run time** against the live ledger: an out-of-range citation
(line count + 1000) and the first blank line found that run. No expectation line-pins a
live file anymore, so the self-test survives ledger growth and relocation by construction.

## `suppressions.json`

Known-external paths C1 would otherwise flag. **Every entry carries a `reason`, and the
loader raises if one is missing** — a silent suppression list becomes a place drift hides.
