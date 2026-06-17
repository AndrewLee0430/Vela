"""
C1 — Coarse (③) post-hoc direction-checker (SHADOW, flag-only). IN-REPO build.

Async port of the validated reference core `direction_checker.py` (repo root), adapted to the real
Vela seams confirmed in `C1_inrepo_planback.md`:
  - LLM call → §2.1 Provider abstraction (async `provider.complete`), wrapped by an async
    `AsyncLLM = Callable[[str], Awaitable[str]]` adapter (see `make_lightweight_llm`).
  - FULL abstracts → the caller passes `RetrievedDocument.content` (the full abstract the generator
    actually saw) or `PubMedClient.fetch_details(pmid).abstract`. NEVER the 500-char citation snippet.

SHADOW: the caller logs the returned DirectionFlag to a sink and surfaces NOTHING to the user. This
module touches no SSE stream and changes no answer. A2 (flag-only vs withhold vs block, thresholds)
is OUT of scope — route-gated.

Validated-design invariants (each maps to a documented failure if violated):
  1. anchor = MOST COUNTERINTUITIVE cited source vs clinical prior, judged from the SOURCE's own
     finding + model prior, INDEPENDENT of the answer's claim. NOT naive "the source the answer's
     claim is based on" (circular / whitewash, 0/3).
  2. FULL abstracts. Truncation (~700 char) buries the protective stat -> 0/3.
  3. WHOLE-ANSWER vs anchor direction. NOT per-claim decompose (decomposition-anchoring FN).
  4. STRUCTURAL trigger: >=2 opposite-direction counterintuitive sources on the SAME factor->outcome
     => flag UNCONDITIONALLY, never gated on the selector's self-reported confidence.
  5. Flag-only output.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

from api.providers.factory import get_lightweight_provider
from api.providers.base import CompletionRequest
from api.models.schemas import SourceType

# Async adapter: prompt string -> raw completion string, through the §2.1 provider path.
AsyncLLM = Callable[[str], Awaitable[str]]

# Invariant 2 footgun = the 500-char CITATION SNIPPET (`RetrievedDocument.to_citation` does
# `content[:500] + "..."`). That is the only truncated form reachable in this wiring, and it has a
# distinctive signature (ends "..." and ~<=503 chars). We guard against THAT precisely, rather than a
# blunt length heuristic that false-positives on genuinely short real abstracts (e.g. brief reports).
_SNIPPET_MAX_LEN = 520            # snippet is content[:500] + "..."; real short abstracts can be shorter
_VERY_SHORT_ABSTRACT = 200        # logged (not raised) — informational


def make_lightweight_llm() -> AsyncLLM:
    """Build the AsyncLLM adapter bound to the cheap model (gpt-4.1-mini per the feasibility runs)."""
    binding = get_lightweight_provider()

    async def _llm(prompt: str) -> str:
        resp = await binding.provider.complete(CompletionRequest(
            model=binding.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
            response_format={"type": "json_object"},
        ))
        return resp.content or ""

    return _llm


@dataclass
class CitedSource:
    pmid: str
    abstract: str                 # MUST be the FULL abstract (invariant 2)
    reported_effect: str = ""     # the source's own stated finding/effect, if already extracted
    # NOTE: intentionally NO "is the answer's main source" field -- selection must not use it.


def cited_sources_from_documents(documents) -> list[CitedSource]:
    """Build CitedSource list from the RetrievedDocument objects the generator used (PubMed only).
    `RetrievedDocument.content` is the FULL abstract (`article.to_text()`) the generator actually saw
    -> satisfies invariant 2 with no re-fetch. FDA labels / non-PubMed sources are skipped (the
    direction check is for PubMed findings)."""
    out: list[CitedSource] = []
    for d in documents or []:
        if getattr(d, "source_type", None) != SourceType.PUBMED:
            continue
        content = (getattr(d, "content", "") or "").strip()
        m = re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")
        if not m or not content:
            continue
        out.append(CitedSource(pmid=m.group(1), abstract=content))
    return out


@dataclass
class DirectionFlag:
    flagged: bool
    reason: str
    selected_anchor_pmid: Optional[str] = None
    verdict: str = ""             # "contradicts" | "consistent" | "structural" | "no_anchor"
    debug: dict = field(default_factory=dict)
    # Selector self-reported confidence is deliberately NOT used for gating (invariant 4).

    def to_sink_dict(self) -> dict:
        return {
            "flagged": self.flagged,
            "verdict": self.verdict,
            "reason": self.reason,
            "selected_anchor_pmid": self.selected_anchor_pmid,
            "debug": self.debug,
        }


def _require_full_abstracts(sources: list[CitedSource]) -> None:
    """Invariant 2 guard. Fail loud on the REAL footguns (empty abstract, or the 500-char citation
    snippet) rather than on legitimately short full abstracts."""
    for s in sources:
        a = (s.abstract or "").strip()
        if not a:
            raise ValueError(f"PMID {s.pmid}: empty abstract -- FULL abstract REQUIRED (invariant 2).")
        if a.endswith("...") and len(a) <= _SNIPPET_MAX_LEN:
            raise ValueError(
                f"PMID {s.pmid}: abstract looks like the 500-char CITATION SNIPPET ({len(a)} chars, "
                "trailing '...'). Selection collapses to 0/3 on snippets -- pass the full "
                "RetrievedDocument.content (invariant 2), never citation.snippet."
            )
        if len(a) < _VERY_SHORT_ABSTRACT:
            logger.warning("PMID %s: short abstract (%d chars) -- using as-is (this is the full text "
                           "the generator saw; not a truncation).", s.pmid, len(a))


async def _score_counterintuitiveness(llm: AsyncLLM, source: CitedSource) -> dict:
    """Invariant 1: grade how surprising THIS source's OWN finding is vs the common clinical prior --
    from the abstract + standard priors, NOT from any downstream answer/claim. Any 'confidence' the
    model emits is for inspection only; it MUST NOT gate the flag."""
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
    return _safe_json(await llm(prompt))


async def select_anchor(llm: AsyncLLM,
                        sources: list[CitedSource]) -> Optional[tuple[CitedSource, dict]]:
    """Invariant 1 + 2: pick the MOST counterintuitive cited source (full abstracts required).
    Selection key is counterintuitiveness ONLY -- never the source's agreement with the answer."""
    _require_full_abstracts(sources)
    scored: list[tuple[CitedSource, dict]] = []
    for s in sources:
        scored.append((s, await _score_counterintuitiveness(llm, s)))
    if not scored:
        return None
    return max(scored, key=lambda sm: float(sm[1].get("counterintuitiveness", 0.0)))


async def _answer_direction(llm: AsyncLLM, answer: str, factor: str, outcome: str) -> dict:
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
    return _safe_json(await llm(prompt))


async def _detect_structural_situation(llm: AsyncLLM, sources: list[CitedSource],
                                       factor: str, outcome: str) -> dict:
    """Invariant 4 (the dep-(b) safety net): do >=2 cited sources report OPPOSITE directions for
    factor->outcome, with at least one counterintuitive vs common assumption? If yes -> flag
    UNCONDITIONALLY, regardless of which anchor was selected and regardless of any confidence."""
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
    return _safe_json(await llm(prompt))


async def check(llm: AsyncLLM, *, answer: str, question: str,
                cited_sources: list[CitedSource],
                enable_structural: bool = True) -> DirectionFlag:
    """Orchestrator. SHADOW + flag-only -> the CALLER logs the result to a shadow sink and surfaces
    NOTHING. `question` is accepted for logging/context only; selection must not be steered by it.

    `enable_structural`: invariant-4 structural trigger. Default True (production hook). The shadow
    validation also re-scores with this OFF to isolate the primary whole-answer-vs-anchor path, after
    the structural detector was found to over-fire on real multi-source retrievals (see STATE/TECH_DEBT)."""
    if not cited_sources:
        # A confident directional answer with zero citations is itself flagworthy (cf. B07).
        return DirectionFlag(True, "directional answer with no cited sources", verdict="no_anchor")

    picked = await select_anchor(llm, cited_sources)
    if picked is None:
        return DirectionFlag(True, "no anchor selectable", verdict="no_anchor")
    anchor, ameta = picked
    factor, outcome = ameta.get("factor", ""), ameta.get("outcome", "")

    # Invariant 4 -- the structural situation flags unconditionally, never confidence-gated.
    if enable_structural:
        struct = await _detect_structural_situation(llm, cited_sources, factor, outcome)
        if bool(struct.get("two_opposite_counterintuitive")):
            return DirectionFlag(
                True,
                f"structural: >=2 opposite-direction counterintuitive sources on {factor}->{outcome}",
                selected_anchor_pmid=anchor.pmid, verdict="structural",
                debug={"anchor_meta": ameta, "structural": struct},
            )

    # Primary: whole-answer stance vs the counterintuitiveness-selected anchor.
    adir = await _answer_direction(llm, answer, factor, outcome)
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
    """Direction conflict, tolerant of the effect-statistic suffix in source_dir."""
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
    (CLAUDE.md Rule 18 'fail loud') rather than silently mis-judge."""
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
