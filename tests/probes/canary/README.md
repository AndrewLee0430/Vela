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
  `STATE.md:612` (the 2026-08-10 ownership-form gate, recorded PASS). Its id in
  its source is `canary_statin_moa`; the founder renamed it `statin_moa_tracked`
  here to make the relationship legible. **The string is unchanged.**

Two files called the statin canary two different things. Keeping both is the
founder ruling (2026-08-21): the machine gate and the human-eye form now assert
the *same* query, and the historical M1 number keeps its own query.

## Criterion — unchanged in substance, now enforced

Per query, **N=8** real `retrieve()` calls, **full pipeline / rewrite arm** (the
same arm the predecessor used — deliberately not the raw arm).

**PASS iff zero usable runs cite a whitelisted DailyMed safety LOINC in the final
top-`max_results`.**

- **Whitelist is IMPORTED** from `api/rag/retriever.py` (`_SAFETY_SECTION_WHITELIST`),
  never copied. If the founder-locked list changes, this gate follows automatically.
- **Detection is key-only (Rule 21):** `source_id` must parse as
  `DailyMed:{setid}#{loinc}`. No title or content text is ever inspected.
- **Usable runs:** `status in ("no_results","error")` is excluded as network noise —
  `retrieve()` short-circuits before any filter/rerank stage, so those runs cannot
  distinguish a miss from an outage. `status == "irrelevant"` **is** usable: documents
  were retrieved and the filter dropped them, which is a real retrieval outcome.
- **`usable_runs < 6` of 8 FAILS the query.** A canary that mostly errored is not a
  pass — this is the half the predecessor could not express at all.

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

## Negative control (Rule 17)

`run_self_test()` injects a synthetic whitelisted safety citation
(`DailyMed:0000…0000#34073-7`) and requires the gate to exit non-zero, then
confirms the same record without the injection exits zero. It drives the **same**
`evaluate()` the real gate uses — a control exercising a different path would prove
nothing. The outcome is recorded in the JSON under `self_test`, and a broken
control fails the whole run.

`python tests/probes/canary/canary_gate.py --self-test` runs the control alone with
**zero API calls**.

## Reproducibility — a dated snapshot, not a reproducible number

Every run queries live PubMed/FDA and calls a non-deterministic LLM rewrite
(temperature=0, but no seed and no cache). Pool composition varies between runs and
between days. **Re-running this gate re-measures; it does not reproduce.** The PASS
criterion is stable under that drift by design: it asserts an *absence* (zero safety
citations), not a pool identity.

## The historical five-source baseline

`0/8 each, 2026-07-27, enable_local=True` — retained as a **dated historical figure
for the five-source era**, from `tests/results/pairaware_m1_20260727_161811.json`
(untracked; 5 canaries, 0/8 each, 8 usable runs, 0 exclusions, `complete=true`).
**It is not a HEAD baseline and must not be compared as one** — it measured a
configuration with a source that is now off.

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
