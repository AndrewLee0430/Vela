# `canary/` — the canary set as an ENFORCING gate

Non-safety Research queries must not cite DailyMed **safety** sections. If a
retrieval change starts pulling Contraindications/Interactions/Warnings/Boxed
into "how does metformin work?", this gate fails.

## What was broken, and what changed (founder ruling 2026-08-21)

The canary has been cited as a gate obligation for months — `BACKLOG.md:847`,
`docs/c2_line_closeout_20260804.md:68`, `docs/nonhuman_label_scope_20260804.md:194`
and others all list "canary" alongside §2.7 and the danger-path re-gate. But:

1. **It had no committed runner.** The five query IDs appeared in exactly two
   tracked lines in the whole repo (`docs/pair_aware_retrieval_probe.md:206-207`),
   and only as *results* — never with the query text. Every script that could run
   it lived under `tests/results/`, which `.gitignore:113` hides, so the queries
   existed on one machine. That is the Rule 20 failure mode by name.
2. **It asserted nothing.** The predecessor (`tests/results/_pairaware_m1.py:245-254`)
   computed `hits` and printed `(want 0)`. There was no `assert`, no exit code, no
   failure path. It was a *measurement script that read as a gate* — **that is the
   defect this file fixes.** Every criterion here is asserted and a violation exits
   non-zero.
3. **Its baseline had silently expired.** See "Production parity" below.

## The canonical set — SIX queries

| id | query | source |
|---|---|---|
| `metformin_moa` | `metformin mechanism of action` | `_pairaware_m1.py:77` |
| `statin_moa` | `statin mechanism of action pharmacology` | `_pairaware_m1.py:78` |
| `glp1_weight` | `GLP-1 減重機轉` | `_pairaware_m1.py:79` |
| `statin_efficacy` | `statin primary prevention efficacy` | `_pairaware_m1.py:80` |
| `sglt2_cv` | `SGLT2 inhibitor cardiovascular outcomes` | `_pairaware_m1.py:81` |
| `statin_moa_tracked` | `What is the mechanism of action of statins?` | `_c1_freedslot_probe.py:51` |

`check_string_provenance()` verifies each string is **byte-identical** to its
source script at run time and records the result in the JSON. The sources are
untracked, so on a machine without them the check records
`SOURCE ABSENT` — never a silent pass.

### ⚠️ The two statin variants — do NOT "clean this up"

`statin_moa` and `statin_moa_tracked` look like a duplicate. They are not, and
deleting either re-creates a divergence that took a full recon to find:

- **`statin_moa`** (`statin mechanism of action pharmacology`) is the M1/K-union
  string. It is the one behind every `0/8` number ever recorded for the canary
  (`docs/pair_aware_retrieval_probe.md:206-207`,
  `docs/kunion_cut_exemption_build.md:28`).
- **`statin_moa_tracked`** (`What is the mechanism of action of statins?`) is the
  c1 string, and it is **the only canary query that ever reached a tracked file**:
  `docs/human_eye_gate_checklist.md:104` (row 8, the human-eye canary row) and
  `STATE.md`'s **`FIRST OWNERSHIP-FORM GATE`** entry (2026-08-10), where its row
  reads `What is the mechanism of action of statins? *(canary)*` … **PASS**.
  ⚠️ **Both are CONTENT ANCHORS — `git grep -F` them, do not trust a line number**;
  this cited `STATE.md:612` until 2026-08-21, and by then the number had drifted off
  the entry entirely. Its id in
  its source is `canary_statin_moa`; the founder renamed it `statin_moa_tracked`
  here to make the relationship legible. **The string is unchanged.**

Two files called the statin canary two different things. Keeping both is the
founder ruling (2026-08-21): the machine gate and the human-eye form now assert
the *same* query, and the historical M1 number keeps its own query.

## ⚠️ CRITERION AMENDED 2026-08-21 — A DELIBERATE LOOSENING

**This is a loosening of an existing gate, not a refinement.** Recorded as such
so nobody later reads it as a tightening or a cleanup.

| | criterion |
|---|---|
| **OLD** | zero whitelisted DailyMed safety LOINC in the final top-5 |
| **NEW** | zero **WRONG-OBJECT** safety LOINC in the final top-5 — a whitelisted safety section whose **moiety is outside the query's key set**. An **owned** safety section no longer fails. |

**Why (founder ruling 2026-08-21, verbatim):**

> The canary was born on the wrong-drug line; what it exists to catch is
> wrong-DRUG intrusion. The reserved-seat mechanism (主線 A) injects a queried
> drug's OWN safety sections by key, so under the old criterion the seat fails
> `metformin mechanism of action` — measured in seat_v2.json: METFORMIN owns four
> whitelisted safety sections (Warnings 0.5263, Boxed Warning 0.5139,
> Contraindications 0.4945, Drug Interactions 0.4711), all below the 0.6 floor and
> therefore all seatable. Blocking the seat on that basis would use a proxy metric
> to veto the fix the metric exists to enable. The other five canaries are
> unaffected: statin / SGLT2 / GLP-1 are class terms with no corpus key.

### 🔴 What the amendment COSTS — a KNOWN UNCOVERED CASE

The old criterion **also** caught a second thing: an **owned** safety section
appearing in a mechanism-of-action question — **topical mismatch**. **That is now
unguarded.** Accepted on the founder ruling that an owned section is at worst
noise, whereas a wrong-drug section is a safety claim about the wrong substance.

**What would re-open it:** user-visible evidence that owned-but-off-topic sections
degrade answers.

### Two counters, kept independent

Every query records **both** numbers, so the eras stay comparable and a future
reader can see exactly what the loosening covered:

- `safety_cited` — the **OLD** criterion. Still measured; no longer gated on.
- `wrong_object_cited` — the **NEW** criterion. What the gate keys on.

The aggregate also carries `old_criterion_would_have_failed`, naming any query
that the pre-amendment gate would have failed.

### Class queries stay exactly as strict — asserted, not assumed

A query resolving to **no** key set (`statin`, `SGLT2`, `GLP-1` — class terms with
no corpus key) has an **EMPTY** key set, so **every** whitelisted safety section is
wrong-object for it. For those five queries the amended criterion is **identical**
to the old one. The gate **asserts** `safety_cited == wrong_object_cited` whenever
the key set is empty and **LOUD STOPs** if it ever diverges; the check is recorded
per query as `class_query_equivalence`.

Ownership is decided by key only (Rule 21): `source_id` → `DailyMed:{setid}#{loinc}`,
then `setid` → `moiety` joined from `label_docs.json` (a total, conflict-free join —
1,038 setids, 0 conflicts). An unresolvable setid is treated as **wrong-object**, so
the failure mode leans strict rather than toward a silent pass.

The key set comes from **`tests/probes/ownership_eval/resolver.py`** — a shared
module placed beside the other key logic (`build_key_sets`, `strip_salt_suffixes`)
and loaded here **by file path**. It **imports** `strip_salt_suffixes` from
`seat_measurement.py`; no logic is copied. It expands plurally per Rule 23, so
`metformin` resolves to `{METFORMIN, METFORMIN HCL}`, never one key. ⚠️ Its known
false-positive mode (base→salt expansion firing on a common word, e.g. dietary
"sodium" → `SODIUM ACETATE`) makes a key set **larger**, which makes this gate
**less** strict — recorded in the resolver's docstring rather than patched with an
invented deny-list.

## Criterion — the enforcement mechanics

Per query, **N=8** real `retrieve()` calls, **full pipeline / rewrite arm** (the
same arm the predecessor used — deliberately not the raw arm).

**PASS iff zero usable runs cite a WRONG-OBJECT whitelisted DailyMed safety LOINC in
the final top-`max_results`** — i.e. a whitelisted safety section whose moiety falls
outside the query's resolved key set. An **owned** safety section does not fail the
gate. *(Wording taken from the code, not from the amendment note: `evaluate()` fails a
query on `q["wrong_object_cited"] > 0` — `canary_gate.py:338` — and `wrong_object_cited`
counts usable runs whose `wrong_object_cited_ids` is non-empty, `:371`. The OLD
criterion — ANY whitelisted safety LOINC — is still computed as `safety_cited` (`:370`,
`:382`) and reported, but nothing gates on it.)*

- **Whitelist is IMPORTED** from `api/rag/retriever.py` (`_SAFETY_SECTION_WHITELIST`),
  never copied. If the founder-locked list changes, this gate follows automatically.
- **Detection is key-only (Rule 21):** `source_id` must parse as
  `DailyMed:{setid}#{loinc}`. No title or content text is ever inspected.
- **Usable runs:** `status in ("no_results","error")` is excluded as network noise —
  `retrieve()` short-circuits before any filter/rerank stage, so those runs cannot
  distinguish a miss from an outage. `status == "irrelevant"` **is** usable: documents
  were retrieved and the filter dropped them, which is a real retrieval outcome.
- **`usable_runs < 6` of 8 FAILS the query** (`canary_gate.py:343`), independently of
  either counter. A canary that mostly errored is not a pass — this is the half the
  predecessor could not express at all. The two failure kinds are reported separately in
  the aggregate as `failed_on_wrong_object_citation` and `failed_on_insufficient_runs`;
  either one makes `evaluate()` return exit 1 (`:361`).

Exit codes: **0** all clean · **1** gate FAILED · **2** configuration could not be
established (parse miss / cross-check mismatch).

## Production parity — why every flag is named

The predecessor constructed `HybridRetriever()` **bare**. When `enable_local`
flipped to `False` on 2026-07-29 (`c9d36cf`, the c1 local-corpus deprecation), its
2026-07-27 baseline silently expired: it had measured **five** sources, production
now runs **four**. Nothing announced this. That is TECH_DEBT open item #8
(`build_production_retriever()`) biting a real baseline.

So this gate names every flag and **sources each from `api/server.py` at run time**:

| value | where it comes from |
|---|---|
| `enable_local`, `enable_pubmed`, `enable_fda`, `enable_tfda` | parsed from the `retriever = HybridRetriever(...)` construction in `api/server.py` |
| `enable_dailymed` | **not passed** by server.py → the constructor default, asserted against the `api/rag/retriever.py` signature |
| `local_threshold` | parsed from server.py, cross-checked against the constructor default |
| `max_results` | parsed from `max_results=body.max_results or N`, cross-checked against the `retrieve()` default |
| `source_weight_active` | runtime env flag; the **shape of the read** is asserted in server.py, deployed value ON per `docs/kunion_cut_exemption_build.md:72` |
| `_annotate_research_question` | asserted still applied to `body.question` in server.py before `retrieve()` |

Any parse miss or cross-check mismatch is a **LOUD STOP (exit 2)** — never a
default. The fully resolved configuration and its per-field provenance are written
into the result JSON, so a future reader can see exactly what was measured.

## Negative control (Rule 17) — TWO injections since the amendment

Both drive the **same** `evaluate()` the real gate uses; a control exercising a
different path would prove nothing. Recorded in the JSON under `self_test`, and a
broken control fails the whole run.

| control | injection | must |
|---|---|---|
| **(a)** | a **wrong-object** safety doc | exit **non-zero** |
| **(b)** | an **owned** safety doc into `metformin_moa` | exit **zero**, with `safety_cited=1` and `wrong_object_cited=0` |
| clean | neither counter set | exit zero |

**(b) is the one that proves the amendment landed** — an owned safety section is
cited (so the OLD criterion would have failed, and the JSON says so by name in
`old_criterion_would_have_failed`) yet the gate passes, demonstrating that the two
counters are genuinely independent rather than one being derived from the other.

`python tests/probes/canary/canary_gate.py --self-test` runs **all three** with **zero
API calls** — `run_self_test()` (`canary_gate.py:415-485`) evaluates injection (a),
injection (b) and the clean control, and returns `BROKEN` unless
`code_a != 0 and code_b == 0 and code_clean == 0` (`:460`).

## Reproducibility — a dated snapshot, not a reproducible number

Every run queries live PubMed/FDA and calls a non-deterministic LLM rewrite
(temperature=0, but no seed and no cache). Pool composition varies between runs and
between days. **Re-running this gate re-measures; it does not reproduce.** The PASS
criterion is stable under that drift by design: it asserts an *absence* (zero safety
citations), not a pool identity.

## Three eras of baseline — keep all three legible

| era | criterion | config | result | artifact |
|---|---|---|---|---|
| **five-source** 2026-07-27 | any safety LOINC | `enable_local=True`, **5 sources** | 0/8 × 5 queries | `tests/results/pairaware_m1_20260727_161811.json` (**untracked**) |
| **HEAD / old criterion** 2026-08-21 | any safety LOINC | 4 sources | 0/8 × 6, 48/48 usable | `canary_baseline_20260821_pre_amendment.json` |
| **HEAD / new criterion** 2026-08-21 | wrong-object only | 4 sources | **0/8 × 6 on BOTH counters**, 48/48 usable | `canary_baseline_20260821.json` |

The **five-source** figure is **not a HEAD baseline and must not be compared as
one** — it measured a configuration with a source that is now off.

⚠️ **Filename collision, handled explicitly:** both HEAD runs happened on
2026-08-21, so the amended run overwrote the date-named file. The pre-amendment
artifact was recovered from commit `6d4d099` and committed under
`…_pre_amendment.json` so the two HEAD eras coexist rather than one silently
replacing the other. It has **no `wrong_object_cited` field** — that counter did
not exist yet, which is itself the record of what changed.

**The amendment was a NO-OP on current behaviour, as predicted:** every query
reports `safety_cited == wrong_object_cited == 0/8`. No seat exists yet, so
nothing owned is being injected; the loosening changes what the gate *would*
tolerate, not what it currently observes.

## Files

| file | role |
|---|---|
| `canary_gate.py` | the gate — asserts, exits non-zero, no measurement-only path |
| `canary_baseline_YYYYMMDD.json` | the evidence: per-run citations, resolved config, self-test |

## Re-run

```bash
python tests/probes/canary/canary_gate.py             # full gate (48 real retrieve() calls)
python tests/probes/canary/canary_gate.py --self-test # negative control only, no API calls
```

Requires `.env` with provider keys (same convention as
`tests/probes/ownership_eval/`). Not wired into pytest: it makes live API calls and
costs real money and minutes, so it is a gate you run, not a unit test.

## Not fixed here

`golden_results_*.json` and `direction_shadow_*.json` remain gitignored under
`.gitignore:113` — R06's and B01's most recent verdicts still exist on one machine
only. Filed as debt this baton, deliberately not migrated. See `TECH_DEBT.md`.
