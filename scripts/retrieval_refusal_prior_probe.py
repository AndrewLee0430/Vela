#!/usr/bin/env python
"""Supplementary: characterize the H1 PRIOR leg's generalization beyond the single contested topic
(obesity) the main run validated. The prior leg ("is a counter-direction genuinely contested in
CURRENT literature?") is the crux of whether retrieval-refusal generalizes — the main run tested
contested=True on obesity only (+ settled=False on 9 controls). This runs the prior alone on a frozen
list of genuinely-contested vs settled factor->outcomes. Cheap (prior call only, no pools)."""
import sys, json, asyncio
from pathlib import Path
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv; load_dotenv()
from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest
from api.services.cost_tracker import MODEL_COSTS
import api.services.retrieval_refusal as rr
from datetime import datetime

MODEL = rr.STRONG_MODEL
_TOK = {"in": 0, "out": 0}

# frozen: (factor, outcome, expected_counter_plausible, label)
CASES = [
    ("intensive glucose control", "all-cause mortality in type 2 diabetes", True, "contested (ACCORD vs UKPDS)"),
    ("low diastolic blood pressure", "cardiovascular harm in elderly hypertensives", True, "contested (J-curve)"),
    ("moderate alcohol consumption", "cardiovascular disease", True, "contested (MR debate)"),
    ("very low dietary sodium", "cardiovascular risk", True, "contested (J-curve)"),
    ("hormone replacement therapy started near menopause", "cardiovascular outcomes", True, "contested (timing hypothesis)"),
    ("higher body mass index (overweight/obesity)", "mortality in heart failure", True, "contested (obesity paradox) [positive control]"),
    ("early dietary peanut introduction", "peanut allergy", False, "settled (LEAP) [neg control]"),
    ("beta-blockers", "mortality in HFrEF", False, "settled [neg control]"),
    ("cigarette smoking", "lung cancer", False, "settled/obvious [neg control]"),
    ("statins", "cardiovascular events", False, "settled [neg control]"),
]


async def main():
    prov = OpenAIProvider()
    async def llm(prompt):
        r = await prov.complete(CompletionRequest(model=MODEL, messages=[{"role": "user", "content": prompt}],
                                                  temperature=0, max_tokens=300, response_format={"type": "json_object"}))
        _TOK["in"] += r.input_tokens or 0; _TOK["out"] += r.output_tokens or 0
        return r.content or ""
    rows, correct = [], 0
    for factor, outcome, exp, label in CASES:
        pr = await rr._counter_prior(llm, factor, outcome)
        got = bool(pr.get("counter_plausible"))
        ok = (got == exp)
        correct += ok
        rows.append({"factor": factor, "outcome": outcome, "expected": exp, "got": got,
                     "ok": ok, "label": label, "paradox": pr.get("paradox_name"), "reason": pr.get("reason")})
        print(f"  [{'OK ' if ok else 'XX '}] counter={got!s:5} exp={exp!s:5} | {label} :: {factor} -> {outcome}")
    pc = MODEL_COSTS[MODEL]; cost = _TOK["in"]/1e6*pc["input"] + _TOK["out"]/1e6*pc["output"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _REPO/"tests"/"results"/f"retrieval_refusal_prior_probe_{ts}.json"
    json.dump({"timestamp": ts, "model": MODEL, "correct": correct, "n": len(CASES),
               "tokens": _TOK, "cost_usd": round(cost, 4), "rows": rows}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nPRIOR discrimination: {correct}/{len(CASES)} correct "
          f"(contested->True / settled->False).  cost ${cost:.4f}\nSaved -> {out}")

asyncio.run(main())
