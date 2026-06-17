"""
C1 — Coarse (3) post-hoc direction-checker (SHADOW, flag-only).

REFERENCE CORE for the validated "Path b-coarse" design (see C1_shadow_build_planback.md, sec 3).
Produced in the Claude chat env (docs-only, no repo/prod/OpenAI access). The integration points
marked `# SEAM:` MUST be wired to the real Vela pipeline in-repo. This module holds the
algorithmically load-bearing logic (anchor selection + direction comparison + structural trigger)
so the validated design does not drift back into the documented footguns.

WHAT THIS IS NOT: it does not fetch sources, call prod, or surface anything to the user. It takes an
already-generated answer + its cited sources (with FULL abstracts) and returns a flag + reason.
SHADOW means the caller logs the flag to a sink and shows the user NOTHING. A2 (flag-only vs
withhold vs block, thresholds) is OUT of scope -- route-gated.

Validated-design invariants (each maps to a documented failure if violated):
  1. anchor = MOST COUNTERINTUITIVE cited source vs clinical prior, judged from the SOURCE's own
     finding + model prior, INDEPENDENT of the answer's claim. NOT naive "the source the answer's
     claim is based on" (circular / whitewash, 0/3).
  2. FULL abstracts. Truncation (~700 char) buries the protective stat -> 0/3.
  3. WHOLE-ANSWER vs anchor direction. NOT per-claim decompose (decomposition-anchoring FN).
  4. STRUCTURAL trigger: >=2 opposite-direction counterintuitive sources on the SAME factor->outcome
     => flag UNCONDITIONALLY. The flag is NEVER gated on the selector's self-reported confidence
     (fail-safe leg unvalidated; selector overconfident on contested topics).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Optional

# SEAM: route this to the (2.1) Provider abstraction (cheap model -- gpt-4.1-mini per the feasibility
# runs). It must return the raw completion string.
LLMComplete = Callable[[str], str]

# Defensive heuristic for the truncation footgun (invariant 2). Real abstracts in this domain run
# well past this; a "full" abstract that is short AND ends mid-sentence is almost certainly truncated.
_SUSPECT_TRUNCATION_LEN = 750


@dataclass
class CitedSource:
    pmid: str
    abstract: str                 # MUST be the FULL abstract (invariant 2)
    reported_effect: str = ""     # the source's own stated finding/effect, if already extracted
    # NOTE: intentionally NO "is the answer's main source" field -- selection must not use it.


@dataclass
class DirectionFlag:
    flagged: bool
    reason: str
    selected_anchor_pmid: Optional[str] = None
    verdict: str = ""             # "contradicts" | "consistent" | "structural" | "no_anchor"
    debug: dict = field(default_factory=dict)
    # Selector self-reported confidence is deliberately NOT a field used for gating (invariant 4).


def _require_full_abstracts(sources: list[CitedSource]) -> None:
    """Invariant 2 guard. Fail loud rather than silently degrade into the 0/3 regime."""
    for s in sources:
        a = (s.abstract or "").strip()
        if not a:
            raise ValueError(f"PMID {s.pmid}: empty abstract -- FULL abstract REQUIRED (invariant 2).")
        if len(a) <= _SUSPECT_TRUNCATION_LEN and not a.endswith((".", "?", "!", '"', ")")):
            # Heuristic only. Better: assert against the source-of-truth length at fetch time.
            raise ValueError(
                f"PMID {s.pmid}: abstract looks truncated ({len(a)} chars, no terminal punctuation). "
                "Truncated abstracts collapse selection to 0/3 -- wire fetch_full_abstract() upstream."
            )


def _score_counterintuitiveness(llm: LLMComplete, source: CitedSource) -> dict:
    """
    Invariant 1: grade how surprising THIS source's OWN finding is vs the common clinical prior --
    from the abstract + standard priors, NOT from any downstream answer/claim.
    Returns {"factor","outcome","effect_direction","counterintuitiveness","why_surprising"}.
    Any 'confidence' the model emits is for inspection only; it MUST NOT gate the flag.
    """
    prompt = f"""You are grading a single biomedical source IN ISOLATION. Do NOT consider any
downstream answer or claim -- only this abstract and standard clinical priors.

ABSTRACT (PMID {source.pmid}):
{source.abstract}

Return STRICT JSON, no prose:
{{
  "factor": "<exposure/factor studied, e.g. 'polypharmacy'>",
  "outcome": "<outcome, e.g. 'all-cause mortality'>",
  "effect_direction": "<'increases'|'decreases'|'no_effect'|'mixed'> for factor->outcome, WITH the effect statistic if present (e.g. 'decreases (OR 0.78)')",
  "counterintuitiveness": <0.0-1.0: how surprising this finding is vs the common clinical assumption>,
  "why_surprising": "<one short clause>"
}}"""
    return _safe_json(llm(prompt))


def select_anchor(llm: LLMComplete,
                  sources: list[CitedSource]) -> Optional[tuple[CitedSource, dict]]:
    """Invariant 1 + 2: pick the MOST counterintuitive cited source (full abstracts required).
    The selection key is counterintuitiveness ONLY -- never the source's agreement with the answer."""
    _require_full_abstracts(sources)
    scored: list[tuple[CitedSource, dict]] = [(s, _score_counterintuitiveness(llm, s)) for s in sources]
    if not scored:
        return None
    return max(scored, key=lambda sm: float(sm[1].get("counterintuitiveness", 0.0)))


def _answer_direction(llm: LLMComplete, answer: str, factor: str, outcome: str) -> dict:
    """Invariant 3: the WHOLE answer's overall directional stance on factor->outcome.
    No per-claim decomposition."""
    prompt = f"""Read this WHOLE answer and state its OVERALL directional stance on the relationship
between "{factor}" and "{outcome}". Treat the answer as a whole -- do NOT decompose into atomic claims.

ANSWER:
{answer}

STRICT JSON:
{{
  "answer_direction": "<'increases'|'decreases'|'no_effect'|'mixed'|'not_addressed'>",
  "quote": "<short grounding span, <=15 words>"
}}"""
    return _safe_json(llm(prompt))


def _detect_structural_situation(llm: LLMComplete, sources: list[CitedSource],
                                 factor: str, outcome: str) -> dict:
    """
    Invariant 4 (the dep-(b) safety net): do >=2 cited sources report OPPOSITE directions for
    factor->outcome, with at least one counterintuitive vs common assumption? If yes -> flag
    UNCONDITIONALLY, regardless of which anchor was selected and regardless of any confidence.
    """
    catalog = "\n".join(
        f"- PMID {s.pmid}: {s.reported_effect or '(direction to be read from abstract)'}"
        for s in sources
    )
    prompt = f"""Factor: "{factor}". Outcome: "{outcome}".
Cited sources and their reported directions:
{catalog}

Do at least TWO of these sources report OPPOSITE directions for factor->outcome, where at least one
direction is counterintuitive vs the common clinical assumption?

STRICT JSON: {{"two_opposite_counterintuitive": <true|false>, "which": ["PMID", ...]}}"""
    return _safe_json(llm(prompt))


def check(llm: LLMComplete, *, answer: str, question: str,
          cited_sources: list[CitedSource]) -> DirectionFlag:
    """
    Orchestrator. SHADOW + flag-only -> the CALLER logs the result to a shadow sink and surfaces
    NOTHING. `question` is accepted for logging/context only; selection must not be steered by it.
    """
    if not cited_sources:
        # A confident directional answer with zero citations is itself flagworthy (cf. B07).
        return DirectionFlag(True, "directional answer with no cited sources", verdict="no_anchor")

    picked = select_anchor(llm, cited_sources)
    if picked is None:
        return DirectionFlag(True, "no anchor selectable", verdict="no_anchor")
    anchor, ameta = picked
    factor, outcome = ameta.get("factor", ""), ameta.get("outcome", "")

    # Invariant 4 FIRST -- the structural situation flags unconditionally, never confidence-gated.
    struct = _detect_structural_situation(llm, cited_sources, factor, outcome)
    if bool(struct.get("two_opposite_counterintuitive")):
        return DirectionFlag(
            True,
            f"structural: >=2 opposite-direction counterintuitive sources on {factor}->{outcome}",
            selected_anchor_pmid=anchor.pmid, verdict="structural",
            debug={"anchor_meta": ameta, "structural": struct},
        )

    # Primary: whole-answer stance vs the counterintuitiveness-selected anchor.
    adir = _answer_direction(llm, answer, factor, outcome)
    contradicts = _opposite(adir.get("answer_direction"), ameta.get("effect_direction"))
    return DirectionFlag(
        flagged=bool(contradicts),
        reason=(
            f"answer says '{adir.get('answer_direction')}' on {factor}->{outcome}; "
            f"counterintuitive anchor PMID {anchor.pmid} reports '{ameta.get('effect_direction')}'"
            if contradicts else "answer direction consistent with counterintuitive anchor"
        ),
        selected_anchor_pmid=anchor.pmid,
        verdict="contradicts" if contradicts else "consistent",
        debug={"anchor_meta": ameta, "answer_dir": adir},
    )


def _opposite(answer_dir: Optional[str], source_dir: Optional[str]) -> bool:
    """Direction conflict, tolerant of the effect-statistic suffix in source_dir.
    NOTE: deterministic label compare is the cheap path; for 'mixed'/edge cases an explicit LLM
    comparator ("does the answer contradict this source's finding?") is more robust -- harden in-repo."""
    if not answer_dir or not source_dir:
        return False
    a, s = answer_dir.strip().lower(), source_dir.strip().lower()
    inc = any(t in s for t in ("increase", "higher", "raises"))
    dec = any(t in s for t in ("decrease", "lower", "reduces"))
    if a.startswith("increase") and dec and not inc:
        return True
    if a.startswith("decrease") and inc and not dec:
        return True
    return False


def _safe_json(raw: str) -> dict:
    """Models occasionally wrap JSON in fences/prose despite instructions. Strip and parse; fail loud
    (A1 sec0 'fail loud', cf. CLAUDE.md Rule 18) rather than silently mis-judge."""
    txt = (raw or "").strip()
    if txt.count("```") >= 2:
        txt = txt.split("```")[1]
        if txt.lower().startswith("json"):
            txt = txt[4:]
        txt = txt.strip()
    start, end = txt.find("{"), txt.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"direction-checker: no JSON in model output: {raw[:200]!r}")
    return json.loads(txt[start:end + 1])


# SEAM (shadow caller, pseudocode -- wire in server.py SSE path, DOWNSTREAM of the generator):
#
#   sources = [CitedSource(pmid=c.pmid, abstract=fetch_full_abstract(c.pmid),
#                          reported_effect=c.effect) for c in answer_citations]
#   flag = check(provider.complete, answer=answer_text, question=user_question, cited_sources=sources)
#   shadow_sink.emit("direction_flag", flag)   # log only -- DO NOT touch the SSE stream / answer
#
# A2 (route-gated) later decides whether `flag.flagged` downgrades confidence / withholds / blocks.
