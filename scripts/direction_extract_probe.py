#!/usr/bin/env python
"""Isolated diagnostic: is C1's conflation failure a CHEAP-MODEL artifact or TASK-INTRINSIC?

NOT a rebuild of C1. Reuses already-captured answers (no regeneration). Runs ONLY the two ③ sub-tasks
with a STRONGER model (gpt-4.1, via the §2.1 provider abstraction — NOT gpt-4.1-mini):
  (a) effect-extraction: given the FULL abstract + a target factor->outcome, extract the correct
      effect statistic + direction for THAT factor (not a co-reported different factor).
  (b) direction-compare: given the answer's whole-answer stance + the extracted source direction,
      is it a reversal? Uses an LLM comparator (NOT the deterministic _opposite that broke on "mixed").

Diagnostic set isolates the extraction bottleneck (anchor RETRIEVED + reversed) + 2 clean controls.
Real numbers only; prints raw model output for audit; reports actual token/$ cost.
Standalone — does NOT touch direction_checker.py prod behavior or the shadow hook.
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv
load_dotenv()

from api.data_sources.pubmed import PubMedClient
from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest
from api.services.cost_tracker import MODEL_COSTS

CAPTURED = _REPO / "tests" / "results" / "direction_shadow_20260617_143022.json"
STRONG_MODEL = "gpt-4.1"   # stronger than the gpt-4.1-mini C1 scorer; the question = cheap-model vs task

# Diagnostic cases: (id, anchor_pmid, factor, outcome, expected_dir, key_stat, expect_flag)
# expected_dir/key_stat = the CORRECT reading of the anchor for THAT factor (the conflation target).
DIAG = [
    ("P-L1",  "35268461", "polypharmacy", "all-cause mortality",
     "decreases", "0.78", True),   # trap = multimorbidity OR 2.04 (different factor)
    ("P-L2",  "35268461", "polypharmacy", "all-cause mortality",
     "decreases", "0.78", True),
    ("OB-L1", "29951802", "higher body mass index (overweight/obesity)", "all-cause mortality",
     "mixed", "", True),           # U-shaped anchor; tests the comparator on a "mixed" source
    ("H4",    "25705822", "early dietary peanut introduction", "peanut allergy",
     "decreases", "", False),      # clean control (LEAP: reduces)
    ("HD-BB", "29040525", "beta-blockers", "mortality in heart failure with reduced ejection fraction",
     "decreases", "", False),      # clean control (reduces mortality)
]

_TOK = {"in": 0, "out": 0}


def _safe_json(raw: str) -> dict:
    t = (raw or "").strip()
    if t.count("```") >= 2:
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"no JSON: {raw[:200]!r}")
    return json.loads(t[s:e + 1])


async def strong(prov, prompt: str) -> dict:
    resp = await prov.complete(CompletionRequest(
        model=STRONG_MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0, max_tokens=600, response_format={"type": "json_object"}))
    _TOK["in"] += resp.input_tokens or 0
    _TOK["out"] += resp.output_tokens or 0
    return _safe_json(resp.content)


def extract_prompt(abstract, factor, outcome, pmid):
    return f"""You are extracting ONE specific effect from a biomedical abstract. The abstract may report
SEVERAL different factors (e.g. polypharmacy AND multimorbidity) with DIFFERENT effect directions.
Extract the effect ONLY for the target factor below — do NOT report a different factor's statistic.

TARGET factor -> outcome: "{factor}" -> "{outcome}"

ABSTRACT (PMID {pmid}):
{abstract}

STRICT JSON:
{{
  "effect_direction": "<'increases'|'decreases'|'no_effect'|'mixed'> for the TARGET factor->outcome",
  "effect_statistic": "<the exact statistic for the TARGET factor (e.g. 'OR 0.78, 95% CI 0.63-0.96'), or 'none stated'>",
  "evidence_quote": "<short verbatim quote from the abstract for the TARGET factor>",
  "other_factors_note": "<other factors in the abstract with DIFFERENT directions, so we can see the trap, e.g. 'multimorbidity OR 1.82 (increases)'>"
}}"""


def compare_prompt(answer, factor, outcome, src_dir, src_stat):
    return f"""Decide whether an AI ANSWER REVERSES the direction of effect that a cited SOURCE reports,
for one specific relationship. Judge the answer's OVERALL stance (whole answer), not one sentence.
Handle 'mixed'/U-shaped source directions sensibly: if the source is mixed and the answer asserts a
single unqualified direction, that is a (partial) reversal/oversimplification.

RELATIONSHIP: "{factor}" -> "{outcome}"
SOURCE reports: direction="{src_dir}", statistic="{src_stat}"

ANSWER:
{answer}

STRICT JSON:
{{
  "answer_direction": "<the answer's overall stance on the relationship>",
  "is_reversal": <true|false>,
  "reason": "<=2 sentences>"
}}"""


async def main():
    if not CAPTURED.exists():
        sys.exit(f"ABORT: captured run not found: {CAPTURED}")
    cap = {r["id"]: r for r in json.load(open(CAPTURED, encoding="utf-8"))["results"]}
    pubmed = PubMedClient()
    prov = OpenAIProvider()

    # fetch all anchor abstracts once
    pmids = sorted({c[1] for c in DIAG})
    arts = {a.pmid: a for a in await pubmed.fetch_details(pmids)}
    print(f"strong model = {STRONG_MODEL}; fetched {len(arts)}/{len(pmids)} abstracts\n")

    rows = []
    for cid, pmid, factor, outcome, exp_dir, key_stat, expect_flag in DIAG:
        r = cap.get(cid)
        art = arts.get(pmid)
        if not r or not art or not (art.abstract or "").strip():
            print(f"  [{cid}] SKIP — missing captured answer or abstract"); continue
        answer = r["answer"]
        ex = await strong(prov, extract_prompt(art.abstract, factor, outcome, pmid))
        got_dir = (ex.get("effect_direction") or "").strip().lower()
        got_stat = ex.get("effect_statistic") or ""
        dir_ok = got_dir.startswith(exp_dir) or (exp_dir == "mixed" and got_dir in ("mixed", "no_effect"))
        stat_ok = (key_stat == "") or (key_stat in got_stat)
        a_pass = dir_ok and stat_ok

        cmp = await strong(prov, compare_prompt(answer, factor, outcome, got_dir, got_stat))
        is_rev = bool(cmp.get("is_reversal"))
        b_pass = (is_rev == expect_flag)

        rows.append({"id": cid, "pmid": pmid, "factor": factor, "expected_dir": exp_dir,
                     "key_stat": key_stat, "expect_flag": expect_flag,
                     "extract": ex, "a_pass": a_pass,
                     "compare": cmp, "b_flag": is_rev, "b_pass": b_pass})
        print(f"=== {cid} (anchor {pmid}) — target: {factor} -> {outcome}")
        print(f"  (a) EXTRACT  dir={got_dir!r} stat={got_stat!r}")
        print(f"      other_factors_note: {ex.get('other_factors_note','')[:140]!r}")
        print(f"      -> expected {exp_dir!r}/{key_stat or '(any)'}  => (a) {'PASS' if a_pass else 'FAIL'}")
        print(f"  (b) COMPARE  answer_dir={cmp.get('answer_direction','')!r} is_reversal={is_rev}")
        print(f"      reason: {cmp.get('reason','')[:160]!r}")
        print(f"      -> expected flag={expect_flag}  => (b) {'PASS' if b_pass else 'FAIL'}\n")

    rev = [r for r in rows if r["expect_flag"]]
    clean = [r for r in rows if not r["expect_flag"]]
    a_ok = sum(1 for r in rows if r["a_pass"])
    det = sum(1 for r in rev if r["b_flag"])
    fp = sum(1 for r in clean if r["b_flag"])

    pc = MODEL_COSTS[STRONG_MODEL]
    cost = _TOK["in"] / 1e6 * pc["input"] + _TOK["out"] / 1e6 * pc["output"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _REPO / "tests" / "results" / f"direction_extract_probe_{ts}.json"
    json.dump({"timestamp": ts, "strong_model": STRONG_MODEL, "tokens": _TOK,
               "cost_usd": round(cost, 4), "rows": rows}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("=" * 64)
    print(f"EFFECT-EXTRACTION (a): {a_ok}/{len(rows)} correct factor's direction+statistic")
    print(f"DIRECTION-COMPARE (b, LLM comparator): detection {det}/{len(rev)} reversals flagged; "
          f"FP {fp}/{len(clean)} clean flagged")
    print(f"COST: in={_TOK['in']} out={_TOK['out']} tokens  => ${cost:.4f} (gpt-4.1 @ ${pc['input']}/${pc['output']} per 1M)")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
