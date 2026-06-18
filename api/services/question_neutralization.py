"""
Lever 2 — Front-end QUESTION-NEUTRALIZATION (detect-then-neutralize). IN-REPO build.

Covers GENERATION-reversal (source-in-hand): the protective/counterintuitive source IS retrieved, but a
LOADED question framing ("why is polypharmacy so dangerous…") induces the generator to state the
direction backwards while citing the OR-0.78-lower source. The lever rewrites the INTERNAL generator
question to a NEUTRAL framing WITHOUT losing user intent; retrieval + the user-facing question are
untouched. Evidence basis: the generation-stage neutralization probe (3/10 -> 0/10 on polypharmacy).

SHADOW this round: production behavior is UNCHANGED — the rewrite is gated by QUESTION_NEUTRALIZATION_
SHADOW (default OFF) and validated only in the A/B harness. A2 (turning it ON; always-vs-detected;
thresholds) is route/founder-gated.

Detect-then-neutralize: `is_loaded` gates `neutralize` so only directionally-presupposing questions are
rewritten (minimizes over-sanitize blast radius on neutral traffic). The rewriter is intent-preserving
and qualifier-retaining (must NOT drop clinical scope like 'elderly / 5+ drugs / HFrEF / infants').
"""

from __future__ import annotations

import json
from typing import Awaitable, Callable, Optional

from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest

AsyncLLM = Callable[[str], Awaitable[str]]

# Strong model — the rewrite must preserve every clinical qualifier (a precision-critical task); the
# detector classification is also quality-critical (a miss leaves a loaded question unprotected).
STRONG_MODEL = "gpt-4.1"


def make_strong_llm(model: str = STRONG_MODEL) -> AsyncLLM:
    prov = OpenAIProvider()

    async def _llm(prompt: str) -> str:
        resp = await prov.complete(CompletionRequest(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=400, response_format={"type": "json_object"}))
        return resp.content or ""

    return _llm


async def is_loaded(llm: AsyncLLM, question: str) -> dict:
    """Detector: does the question presuppose a DIRECTION of effect (loaded/leading) vs neutral
    information-seeking? Returns {loaded, presupposed_direction, reason}."""
    prompt = f"""Classify a clinical question's FRAMING.

LOADED / leading = presupposes a direction of effect before the evidence — e.g. "why is X dangerous/
harmful", "why does X worsen/improve Y", "why is X beneficial/protective", "how does X increase/reduce Y".
NEUTRAL / information-seeking = no directional presupposition — e.g. "what is the effect/association of X
on Y", "what are the clinical outcomes/side effects of X", "what is the relationship between X and Y".

QUESTION: {question}

STRICT JSON: {{"loaded": <true|false>, "presupposed_direction": "<the direction it presupposes, or 'none'>",
"reason": "<=1 sentence"}}"""
    return _safe_json(await llm(prompt))


async def neutralize(llm: AsyncLLM, question: str) -> dict:
    """Rewriter: rewrite to a NEUTRAL, non-leading framing asking the SAME thing. MUST preserve every
    clinical qualifier (population/age/disease/dose/setting, the specific factor + outcome). Returns
    {neutralized, removed_presupposition, qualifiers_kept}."""
    prompt = f"""Rewrite this clinical question into a NEUTRAL, non-leading, information-seeking framing
that asks the SAME thing WITHOUT presupposing any direction of effect (harm or benefit).

HARD CONSTRAINTS:
- Preserve EVERY clinical qualifier EXACTLY: population, age group, disease/subtype, dose/threshold,
  setting, and the SPECIFIC factor and outcome. Do NOT generalize or drop scope (e.g. keep "elderly
  patients on 5 or more medications with atrial fibrillation" — do NOT shorten to "polypharmacy"; keep
  "reduced ejection fraction", "in infants", "renal impairment").
- Remove ONLY the directional presupposition (the "why is it dangerous/beneficial / how does it worsen/
  improve" framing). Change nothing else.
- The result must be answerable by the same evidence and ask the user's actual question.

QUESTION: {question}

STRICT JSON: {{"neutralized": "<the rewritten neutral question>",
"removed_presupposition": "<what directional assumption was removed, or 'none'>",
"qualifiers_kept": ["<each clinical qualifier retained>"]}}"""
    return _safe_json(await llm(prompt))


async def neutralize_if_loaded(llm: AsyncLLM, question: str) -> Optional[str]:
    """Detect-then-neutralize convenience: returns the neutralized question IF the question is loaded,
    else None (caller keeps the original). Used by the flag-gated server seam."""
    det = await is_loaded(llm, question)
    if not det.get("loaded"):
        return None
    out = await neutralize(llm, question)
    nq = (out.get("neutralized") or "").strip()
    return nq or None


def _safe_json(raw: str) -> dict:
    t = (raw or "").strip()
    if t.count("```") >= 2:
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"question_neutralization: no JSON in model output: {raw[:200]!r}")
    return json.loads(t[s:e + 1])
