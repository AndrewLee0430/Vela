"""
Retrieval-recall REFUSAL / DOWNGRADE detector (SHADOW, decision-only). IN-REPO build.

Covers the failure the ③ direction-checker is STRUCTURALLY BLIND to: a confident answer where the
protective / counter-direction source was NEVER retrieved, so the answer is built only from one-sided
(e.g. harm-side) papers and there is no counter-source present to compare against.

Design = H1 (PRIOR-EXPECTATION × POOL-DIRECTIONAL-SPREAD), per retrieval_refusal_planback.md:
  refuse = (pool is one-sided on factor->outcome) AND (a counter-direction is genuinely plausible /
           contested in CURRENT literature).
The prior leg is what separates obesity-paradox (contested + one-sided -> REFUSE) from settled
one-directional truths incl. counterintuitive-but-settled ones (CAST/LEAP/smoking-PD -> DO NOT refuse).

SHADOW: the caller logs the RetrievalRefusalDecision to a sink and surfaces NOTHING / changes NO
answer. Enforcement (refuse vs downgrade-to-literature-display vs flag, thresholds) = A2, route-gated.

Reads the FINAL pool the generator saw (RetrievedDocument.content, full abstracts), NOT the answer's
cited subset. Uses gpt-4.1 (strong) — the C1 diagnostic proved gpt-4.1-mini conflates multi-stat
abstracts, which would corrupt the pool-spread (mislabel a present protective source as harm).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from api.providers.openai_provider import OpenAIProvider
from api.providers.base import CompletionRequest
from api.models.schemas import SourceType

AsyncLLM = Callable[[str], Awaitable[str]]

# Strong model — accuracy of the per-source direction read matters more than per-call cost (background,
# cents/answer). A mis-read protective source -> false one-sided -> false refuse.
STRONG_MODEL = "gpt-4.1"


def make_strong_llm(model: str = STRONG_MODEL) -> AsyncLLM:
    prov = OpenAIProvider()

    async def _llm(prompt: str) -> str:
        resp = await prov.complete(CompletionRequest(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=500, response_format={"type": "json_object"}))
        return resp.content or ""

    return _llm


@dataclass
class RetrievalRefusalDecision:
    refuse: bool
    reason: str
    factor: str = ""
    outcome: str = ""
    one_sided: bool = False
    counter_plausible: bool = False
    pool_directions: dict = field(default_factory=dict)   # pmid -> direction
    debug: dict = field(default_factory=dict)

    def to_sink_dict(self) -> dict:
        return {"refuse": self.refuse, "reason": self.reason, "factor": self.factor,
                "outcome": self.outcome, "one_sided": self.one_sided,
                "counter_plausible": self.counter_plausible, "pool_directions": self.pool_directions}


def pool_sources_from_documents(documents) -> list[tuple[str, str]]:
    """[(pmid, full_abstract)] from the FINAL RetrievedDocument list (PubMed only; .content = full)."""
    out: list[tuple[str, str]] = []
    for d in documents or []:
        if getattr(d, "source_type", None) != SourceType.PUBMED:
            continue
        content = (getattr(d, "content", "") or "").strip()
        m = re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")
        if m and content:
            out.append((m.group(1), content))
    return out


async def _factor_outcome(llm: AsyncLLM, question: str) -> dict:
    prompt = f"""Identify the SINGLE primary factor->outcome relationship a clinical answer to this
question would be ABOUT (the exposure/intervention and the clinical outcome).

QUESTION: {question}

STRICT JSON: {{"factor": "<exposure/intervention>", "outcome": "<clinical outcome>"}}"""
    return _safe_json(await llm(prompt))


async def _source_direction(llm: AsyncLLM, abstract: str, factor: str, outcome: str, pmid: str) -> dict:
    """Read the source's overall STANCE/valence on factor->outcome (harmful / beneficial / mixed),
    not strictly a mortality HR. A harm-FRAMED mechanism/prognosis review (e.g. "obesity adversely
    impacts cardiac structure") counts as 'harmful' even with no mortality statistic — the threat the
    lever detects is one-sided *coverage/valence* with the counter-paradox absent, not a missing HR.
    Treats closely-related measures of the same construct as the factor (BMI/body-weight ↔ obesity;
    number-of-medications ↔ polypharmacy) to avoid the terminology-mismatch footgun."""
    prompt = f"""Judge this abstract's OVERALL STANCE on whether "{factor}" is HARMFUL or BENEFICIAL
for "{outcome}". Consider the whole picture — effect on risk, prognosis, mortality, OR adverse/
protective mechanism. A paper describing how {factor} worsens or damages relevant physiology counts as
'harmful' even without a mortality statistic; one describing protection/benefit counts as 'beneficial'.
Treat closely-related measures of the same construct as the factor (e.g. BMI / body weight / adiposity
all count for an 'obesity'/'higher body weight' factor). If the abstract genuinely does not address
this factor and outcome at all, say 'not_relevant'.

TARGET: "{factor}" -> "{outcome}"

ABSTRACT (PMID {pmid}):
{abstract}

STRICT JSON: {{"stance": "<'harmful'|'beneficial'|'mixed'|'no_effect'|'not_relevant'>",
"statistic": "<key stat if any, else 'none'>"}}"""
    return _safe_json(await llm(prompt))


async def _counter_prior(llm: AsyncLLM, factor: str, outcome: str) -> dict:
    prompt = f"""Clinical-evidence calibration question. For the relationship "{factor}" -> "{outcome}":

Is a COUNTER-DIRECTION / paradox / reversal genuinely PLAUSIBLE or still actively CONTESTED in the
CURRENT medical literature (a recognized, still-debated paradox)?

CRITICAL: a finding that was historically counterintuitive but is now a SETTLED consensus does NOT
count — answer false for those (e.g. CAST antiarrhythmics-increase-mortality, early-peanut-reduces-
allergy/LEAP, smoking-inversely-associated-with-Parkinson's, beta-blockers-reduce-mortality-in-HFrEF
are all SETTLED -> false). Answer true ONLY for relationships where the opposite direction is a
genuinely active, unresolved debate today (e.g. the obesity paradox in heart failure).

STRICT JSON: {{"counter_plausible": <true|false>, "paradox_name": "<name or 'none'>",
"reason": "<=1 sentence>"}}"""
    return _safe_json(await llm(prompt))


def _spread(stances: list[str]) -> dict:
    """one_sided = >=1 stanced source AND no OPPOSING stance present (and no 'mixed' source, which
    itself carries both sides = a paradox is present)."""
    harm = sum(1 for s in stances if s == "harmful")
    ben = sum(1 for s in stances if s == "beneficial")
    mixed = sum(1 for s in stances if s == "mixed")
    directional = harm + ben + mixed
    one_sided = directional >= 1 and mixed == 0 and (harm == 0 or ben == 0)
    return {"harmful": harm, "beneficial": ben, "mixed": mixed,
            "directional": directional, "one_sided": one_sided}


async def assess(llm: AsyncLLM, *, question: str,
                 pool_sources: list[tuple[str, str]],
                 factor_outcome: Optional[dict] = None) -> RetrievalRefusalDecision:
    """H1 detector. SHADOW + decision-only. `factor_outcome` may be pre-supplied (harness caches it)."""
    if len(pool_sources) < 2:
        return RetrievalRefusalDecision(False, "pool too small to assess one-sidedness",
                                        debug={"n_sources": len(pool_sources)})
    fo = factor_outcome or await _factor_outcome(llm, question)
    factor, outcome = fo.get("factor", ""), fo.get("outcome", "")

    dirs: dict[str, str] = {}
    for pmid, abstract in pool_sources:
        sd = await _source_direction(llm, abstract, factor, outcome, pmid)
        dirs[pmid] = (sd.get("stance") or "not_relevant").strip().lower()
    spread = _spread(list(dirs.values()))

    prior = await _counter_prior(llm, factor, outcome)
    counter = bool(prior.get("counter_plausible"))

    refuse = bool(spread["one_sided"] and counter)
    if refuse:
        reason = (f"one-sided pool on {factor}->{outcome} ({spread['harmful']} harmful / "
                  f"{spread['beneficial']} beneficial) AND counter-direction genuinely plausible "
                  f"({prior.get('paradox_name','')}) -> counter-evidence likely MISSING from the pool")
    elif spread["one_sided"]:
        reason = f"one-sided pool but counter-direction NOT currently contested (settled) -> no refuse"
    else:
        reason = "pool is two-sided (counter-evidence present) -> no refuse"

    return RetrievalRefusalDecision(
        refuse=refuse, reason=reason, factor=factor, outcome=outcome,
        one_sided=spread["one_sided"], counter_plausible=counter, pool_directions=dirs,
        debug={"spread": spread, "prior": prior, "factor_outcome": fo})


def _safe_json(raw: str) -> dict:
    t = (raw or "").strip()
    if t.count("```") >= 2:
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"retrieval_refusal: no JSON in model output: {raw[:200]!r}")
    return json.loads(t[s:e + 1])
