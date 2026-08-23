# -*- coding: utf-8 -*-
"""Render the answer-layer review pack as ONE markdown file the founder fills in.

NO JUDGEMENT IS MADE HERE. Sorting is MECHANICAL and is labelled as such in the pack.
Column set follows docs/human_eye_gate_checklist.md — the form that already exists and
has been used twice. It is not reinvented.
"""
import io, json, glob, os, sys, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).parent
src = sorted(glob.glob(str(HERE / "answer_layer_pack_*.json")), key=os.path.getmtime)[-1]
d = json.loads(Path(src).read_text(encoding="utf-8"))
OUT = Path(src).with_suffix(".md")

units = d["units"]
# ── MECHANICAL sort: most NO-MATCH DailyMed citations first, then most DailyMed cites ──
def suspicion(u):
    return (-(u.get("n_no_match") or 0), -(u.get("n_dailymed") or 0), u["id"])
units = sorted(units, key=suspicion)

L = []
A = L.append
A("# Answer-layer wrong-drug review pack — FOUNDER FILLS THIS IN")
A("")
A(f"**Generated** {d['generated']} · **{d['n_cases']} units** · N=1 per case · "
  f"in-process, **no server, NO LLM JUDGE**.")
A(f"**Config:** `max_results={d['config']['max_results']}` · "
  f"`source_weight_active={d['config']['source_weight_active']}` · "
  f"`_annotate_research_question` applied · {d['config']['retriever']}.")
A("")
A("Column set follows [`docs/human_eye_gate_checklist.md`](../../../docs/human_eye_gate_checklist.md) — "
  "the form already used for the fly-215 and fly-206 gates. **VERDICT vocabulary is that file's:** "
  "`PASS` · `FAIL` · `n/a` · `UNSCORED` (pair queries) · `BLOCKED`. Leave nothing blank at the end — "
  "`—` means *checked, nothing to report*; an **empty cell means not checked**.")
A("")
A("---")
A("")
A("## 🔴 READ THIS BEFORE SCORING — what the MECHANICAL flag is and is not")
A("")
A("Each DailyMed citation carries a flag comparing its **moiety** against the **question text** "
  "(exact whole-token, plus the salt-base form). It exists **only to order your reading**.")
A("")
A("| flag | means | does NOT mean |")
A("|---|---|---|")
A("| `MATCH` | the cited drug's name appears in the question | **NOT evidence the citation is correct.** "
  "A question can name drug X and still be answered from the wrong section, or from X's label where "
  "another drug's was needed |")
A("| `NO-MATCH` | the cited drug's name does not appear in the question | **NOT evidence of an error.** "
  "A class question (*\"NSAIDs\"*, *\"statins\"*) legitimately cites specific member drugs; a pair "
  "question is legitimately answered from a counterpart's label |")
A("| `NO-DRUG-IN-QUESTION` | no corpus drug name resolves from the question at all | the wrong-object "
  "axis does not apply — per the gate form, write `n/a — class query` |")
A("")
A("**Ownership itself is resolved ONLY by the corpus join** `source_id → setid → moiety` "
  "(`owner_assertion.py`, Constraint 1). The flag above is question-side text matching used for "
  "sort order and nothing else. **It never decides ownership, and it is not a verdict.**")
A("")
A("**From the gate form, carried over verbatim:**")
A("- **EXPECTED OWNER is PLURAL BY CONSTRUCTION** — one substance can occupy two corpus keys with "
  "different labels and different safety coverage (`ASPIRIN` → VAZALORE, **no** safety sections; "
  "`ACETYLSALICYLIC ACID` → DURLAZA, three). A single-key expectation reproduces the bug the field exists to catch.")
A("- **Class queries:** write `n/a — class query`, never a guess. A class member cited on a class query "
  "is **legitimately owned**; if unhelpful, that is *answer-relevance*, a different axis.")
A("- **Pair / interaction queries:** mark `pair query — not scored for wrong-object (v1)`. Record what "
  "was cited; do not score it.")
A("- **Check the citation TITLE, not the chip** — the chip reads \"DailyMed\", which is always true.")
A("- ⚠️ **Do not derive keys by substring** — a `STATIN` search returns **NYSTATIN**, an antifungal.")
A("")
A("**Sort order is MECHANICAL:** units with the most `NO-MATCH` DailyMed citations first, then most "
  "DailyMed citations. That is a reading-order heuristic, **not a suspicion ranking you should trust**.")
A("")
A("### 🔴 KNOWN BLIND SPOTS IN THE FLAG — disclosed, not silently carried")
A("")
A("The flag uses `resolver.resolve_key_set`, whose limits are measured and recorded. **Two of them "
  "affect units in this pack, so check these by eye rather than trusting the flag:**")
A("")
A("1. **A question can name a drug the resolver cannot see, and the flag will say "
  "`NO-DRUG-IN-QUESTION` anyway.** Concrete case in this pack: **`R09`** asks about *lithium therapy*, "
  "and both its citations are `LITHIUM CARBONATE` — which is almost certainly the right label. But the "
  "corpus key is `LITHIUM CARBONATE` and `CARBONATE` is **not** in the 17-suffix salt list, so "
  "base→salt expansion cannot bridge *lithium* → `LITHIUM CARBONATE`. **The flag is wrong on R09 in "
  "the conservative direction** — it under-claims, it does not over-claim.")
A("2. **`exact` and `base` matching are mutually exclusive** (`resolver.py:102-108` returns before "
  "`:110`), so on a two-drug question where one drug matches exactly, the other is dropped from the "
  "key set entirely. Any pair question in this pack inherits that.")
A("")
A("Neither blind spot can create a **false `NO-MATCH`** — they only produce false "
  "`NO-DRUG-IN-QUESTION`. So the sort can bury a unit; it cannot invent a suspicious one.")
A("")
A("---")
A("")
A("## Summary table — fill VERDICT and NOTES")
A("")
A("| # | id | question | DailyMed cites | NO-MATCH | EXPECTED OWNER (all corpus keys — you fill) | VERDICT | NOTES |")
A("|---|---|---|---|---|---|---|---|")
for i, u in enumerate(units, 1):
    q = (u["question"] or "").replace("|", "\\|")
    A(f"| {i} | `{u['id']}` | `{q}` | {u.get('n_dailymed','—')} | "
      f"**{u.get('n_no_match','—')}** | | | |")
A("")
A("---")
A("")
A("## The units")
A("")
for i, u in enumerate(units, 1):
    A(f"### {i}. `{u['id']}` — {u.get('n_no_match',0)} NO-MATCH of {u.get('n_dailymed',0)} DailyMed citations")
    A("")
    A(f"**Question as asked:**")
    A("")
    A(f"> {u['question']}")
    A("")
    if u.get("error"):
        A(f"🔴 **ERROR — no answer produced:** `{u['error']}`")
        A(""); A("---"); A(""); continue
    A(f"`status={u['status']}` · `{u['latency_s']}s` · resolver keys: "
      f"{('`' + '`, `'.join(u['resolver_keys']) + '`') if u['resolver_keys'] else '**none — no corpus drug resolves from this question**'}")
    A("")
    A("**Citations as returned:**")
    A("")
    A("| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |")
    A("|---|---|---|---|---|---|")
    for c in u["citations"]:
        t = (c["title"] or "").replace("|", "\\|")
        A(f"| {c['n']} | `{c['source_type']}` | `{c['source_id']}` | {t} | "
          f"{('`'+c['moiety']+'`') if c['moiety'] else '—'} | "
          f"{('`'+c['mechanical_flag']+'`') if c['mechanical_flag'] else '—'} |")
    A("")
    A("**Answer as generated:**")
    A("")
    for line in (u["answer"] or "(empty)").split("\n"):
        A("> " + line if line.strip() else ">")
    A("")
    A("| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |")
    A("|---|---|---|---|")
    A("| | | | |")
    A("")
    A("---")
    A("")
A("## What this pack cannot establish, even if every unit is scored")
A("")
A("- **It is N=1 per query.** Retrieval churns run-to-run — the 2026-07-28 harvest measured mean "
  "turnover **0.423** on identical input minutes apart. A single run shows what happened once, not a rate.")
A("- **24 units cannot separate *rare* from *common*.** With zero observed wrong-drug answers, the "
  "95% upper bound on the true rate is roughly **1 − 0.05^(1/24) ≈ 12%** — i.e. a defect affecting up "
  "to ~1 in 8 answers is entirely consistent with a clean sweep of this pack.")
A("- **The population is curated and deliberately loaded.** R01–R20 over-represents hard cases by "
  "construction, and the four `MF` units were *selected because they are already known to misfire*. "
  "This pack is a detector, not an estimator; it cannot support a traffic-rate claim.")
A("- **It measures the answer layer only.** It says nothing about whether a better document existed "
  "and was not retrieved — a correct-looking answer from a thin pool still scores clean here.")
A("")
Path(OUT).write_text("\n".join(L), encoding="utf-8")
print(f"WROTE {OUT}  ({OUT.stat().st_size} bytes, {len(units)} units)")
