# `tests/probes/` — committed measurement evidence

**Why this directory exists.** `tests/results/` is gitignored (`.gitignore:113`). Probe *scripts* have
historically been force-added into it one at a time (`_citation_url_audit.py`, `_poolsize_harvest.py`,
`_severity_probe.py`, `_otc_singledrug_probe.py`, `_discriminator_validation.py`, `_mem_attribution.py`)
while their *outputs* were never committed. That made several recorded findings **unverifiable by
anyone but the session that produced them** — e.g. the 48-label table in
`docs/c2_dailymed_probe_20260804.md` cited a JSON that existed only on one laptop.

**Convention.** Per baton (2026-08-04), measurement evidence that a doc *cites as a finding* belongs
here, in a directory that is **not** gitignored:

| what | where | committed? |
|---|---|---|
| probe **scripts** | `tests/probes/<topic>/` | ✅ always |
| **small result JSON** that a `docs/` report cites (≲ a few hundred KB) | `tests/probes/<topic>/` | ✅ yes |
| **bulk intermediates** (multi-MB corpora dumps, scratch vector indexes) | `tests/results/` | ❌ never — regenerate from the script |
| scratch **indexes** / embeddings | `tests/results/` | ❌ never |

**Why point-in-time JSON is committed at all**, when a script could regenerate it: these probes query
**live external APIs** (DailyMed, PubMed) whose content changes. Re-running does **not** reproduce the
snapshot a finding was based on — it produces a *new* one. The JSON is the evidence; the script is the
method. Both are needed.

**Rule:** if a `docs/` report states a number, the artifact behind that number should be committed here,
or the report must say the artifact is not retained and why.

---

## `c2/` — DailyMed reference-label selection (Phase 1 + Phase 1b, 2026-08-04)

Reports: [`docs/c2_dailymed_probe_20260804.md`](../../docs/c2_dailymed_probe_20260804.md) ·
[`docs/c2_phase1b_measurement_20260804.md`](../../docs/c2_phase1b_measurement_20260804.md)

| file | what it is |
|---|---|
| `_c2_dailymed_probe.py` → `c2_dailymed_probe.json` | Phase 1 Tasks B/C — live DailyMed, 6 moieties × 4 tiers, 70 fetches / 48 distinct setids |
| `_c2_ea_fetch.py` | Phase 1b — one pass over the **1036 pinned** setids with `SECTIONS` patched to add `34071-1` |
| `_c2_part2_analysis.py` → `c2_part2_summary.json` | Part 2 — E-A blast radius, Rx/OTC split, staleness diff |
| `_c2_build_ea_index.py` | Part 3a — builds the E-A **scratch** index (shipped docs verbatim ⧺ 381 new rows) |
| `_c2_ab_retrieval.py` → `c2_ab_retrieval.json` | Part 3b — CONTROL vs TREATMENT, N=3, full post-rerank pools + store probe |

**NOT committed, by the rule above** — regenerate with the scripts:

- `tests/results/c2_ea_fetch.json` — **15.8 MB**, all sections of 1036 labels (input to Parts 2/3a/4)
- `tests/results/c2_ea_index/` — **31 MB**, the scratch E-A vector index (docs + float16 embeddings)

⚠️ **`_c2_ab_retrieval.py`'s in-run `own_drug` flag is lexical and FALSE-POSITIVES** (the Aceclofenac
label contains the words *"acetylsalicylic acid"*). The report's numbers are re-derived offline by
`setid → moiety`. **Do not read the script's console output as the result** — see Part 3.1.

---

## `baton_check/` — verify a handoff document before acting on it (2026-08-24)

Every baton in the 2026-08-19→24 session contained at least one error; two were load-bearing.
`check_baton.py` resolves citations, anchors, SHAs and ratification claims against the repo.
**No network, no LLM, seconds, never blocks.** Its precision is a measurement, not a
preference: the first scanner ran at **10% precision** and was rebuilt to ~85%. See its
[`README.md`](baton_check/README.md) — especially **§What this does NOT catch**, which is the
honest two-thirds/none-of-the-expensive-ones limit.

| file | what it is |
|---|---|
| `check_baton.py` | the checker — C1/C2/C3/C5 blocking, A6/A7 advisory, C1b suggests anchors for new citations |
| `suppressions.json` | known-external paths; **every entry carries a reason and the loader enforces it** |
| `fixtures/baton_20260821_ratification.md` | the negative control — a REAL baton with documented errors. Do not "fix" them |

---

## `retrieval_attrition/` — where documents die between corpus and answer (2026-08-22/23)

Evidence for the TECH_DEBT entry headed *"[P1 · retrieval measurement / premise integrity …]"*.
Six diagnostics + the runner + the **irreplaceable pre-c1 raw harvest**. See its own
[`README.md`](retrieval_attrition/README.md) — it leads with a **population table**, because two of
three findings measured on synthetic queries failed to generalise to real Research queries and one
held, and only the population decided which.

| file | what it is |
|---|---|
| `resolver_builder_diag_20260822.json` | both key-set builders side by side; CALCIUM; branch exclusivity; all 232 non-moiety bases unfiltered. Offline |
| `attrition_ladder_20260823.json` | offline ladder + floor distribution + the hand-mapped 30-query reach ceiling |
| `poolsize_harvest_20260823_115117.json` | raw post-c1, **75 live `retrieve()` calls** on the golden Research set |
| `poolsize_postc1_comparison_20260823.json` | pre/post deltas, TB02 diagnosis, ex-TB02 sensitivity |
| `_filter_attrition_harvest.py` → `filter_attrition_20260823_122149.json` | filter attrition read from **production's own logger** — **zero `api/` change** |
| `filter_attrition_analysis_20260823.json` | removal-rate distribution, ladder, per-case stability |
| `poolsize_harvest_20260728_110204.json` | 🔴 **PRE-c1 raw — IRREPLACEABLE.** c1 removed the `local` corpus, so no re-run can reproduce it |

---

## `wrongdrug/` — the ownership assertion (T1, 2026-08-05)

Report: [`docs/t1_ownership_assertion_20260805.md`](../../docs/t1_ownership_assertion_20260805.md)

An **instrument**, not a fix. It answers "whose label is this citation?" — the predicate the
fly-215 gate never asserted when it passed `aspirin contraindications` answered entirely from
`Clanza (Aceclofenac)`.

| file | what it is |
|---|---|
| `owner_assertion.py` | the pure module — `source_id → setid → moiety` join, six non-collapsing outcomes. No network, no `api/` import |
| `fixtures.json` | 3 fixtures. `WD03` (spironolactone) is a **pair** query, retained but reported `unclassified` — never as passing |
| `replay_probe.py` → `wrongdrug_replay.json` | self-test + replay over committed c2 evidence + the c1-ship §2.7 calibration |

**No live retrieval.** Every input is a committed artifact, so unlike the `c2/` probes this one is
fully reproducible: `python tests/probes/wrongdrug/replay_probe.py`.

⚠️ It **supersedes** `_c2_ab_retrieval.py`'s lexical `own_drug` flag, and its self-test asserts the
contradiction: on the ACECLOFENAC document the recorded flag says `own_drug: true` and the ownership
join says `wrong_owner_cited`. If that check ever flips, the module has regressed to mention-based
logic. It also deliberately does **not** reuse `tests/results/_pairaware_m1_content_audit.py`, whose
`ON-TARGET-COUNTERPART` bucket is mention-based.

---

## `history_timezone/` — created_at rendered in the wrong timezone (2026-09-03)

Entry: `TECH_DEBT.md` → `[HONESTY][P2] timestamps shown in the wrong timezone` · car baton:
[`docs/batons/history_honesty_car_20260903.md`](../../docs/batons/history_honesty_car_20260903.md)

The evidence behind the entry's **"03:21 AM vs 11:21 AM"** derivation. The same instant, serialized
naive (fly-244 wire) and with `+00:00` (segment-1 wire), pushed through the formatter copied verbatim
from `pages/history.tsx:285-288` under `TZ=Asia/Taipei`.

| file | what it is |
|---|---|
| `repro.mjs` → `result.json` | 4 wire strings (± microseconds) → rendered strings + parsed epoch; the `Date.parse` skew for `MySharesTab.tsx` (-8 h). Exits 1 if `TZ` is not honoured |

**No network, no `api/` import** — fully reproducible: `TZ=Asia/Taipei node tests/probes/history_timezone/repro.mjs`.
The `result.json` is committed anyway because the finding was derived on a specific Node (`v22.19.0`)
and ICU; a different ICU can change the `toLocaleString` output shape.
