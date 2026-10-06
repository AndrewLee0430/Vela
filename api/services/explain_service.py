"""
Explain Feature — 3-Stage Pipeline
Stage 1: Extract entities (entity_extractor.py)
Stage 2: Parallel API lookups (LOINC, RxNorm, MedlinePlus)
Stage 3: Generate plain-language explanation (streaming)

§2.1 PHASE B (PRD v1.4 + ADR 005): Stage 3 generation wired through
api.providers via get_generator_provider(). Model + provider configurable
via GENERATOR_PROVIDER / GENERATOR_MODEL env vars. Stage 1 (entity
extraction) uses LIGHTWEIGHT_PROVIDER via entity_extractor.py.
"""

import asyncio
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Optional
from pydantic import ValidationError

from api.models.explain_schemas import (
    ExtractedEntities, ExplainSource, SourceType,
    ExplainItem, ClinicalCorrelation, RiskTier,
)
from api.services.entity_extractor import extract_entities
from api.data_sources.loinc_client import loinc_client
from api.data_sources.rxnorm_client import rxnorm_client
from api.data_sources.medlineplus_client import medlineplus_client
from api.utils.language_detector import detect_language, get_language_instruction
from api.i18n.explain_strings import (
    get_disclaimer,
    get_downgrade_item_note,
    get_downgrade_corr_note,
)
from api.providers import get_generator_provider, VelaError
from api.providers.base import CompletionRequest

logger = logging.getLogger(__name__)


class ExplainErrorCode(str, Enum):
    """Generic error UX (2026-04-29): codes emitted as SSE error events.
    Frontend ERROR_KEY_MAP in pages/explain.tsx maps these to i18n strings."""
    EMPTY_INPUT = "empty_input"
    NO_VALUES_IN_INPUT = "no_values_in_input"
    INPUT_TOO_LONG = "input_too_long"
    OPENAI_API_ERROR = "openai_api_error"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    OUTPUT_TRUNCATED = "output_truncated"
    GENERIC = "generic"


# Matches pydantic max_length on ExplainRequest.report_text.
# Pydantic blocks >5000 with a 422 before this check fires; this is
# defense-in-depth for any path that bypasses pydantic.
MAX_INPUT_CHARS = 5000

# Startup self-test for language detection
logger.info(f"Lang detector test: {detect_language('W.B.C. Count 白血球計數 6.5 血液檢查')}")

# ─── Stage 3 system prompt (PRD § 2.7, v1 extraction) ───────────────────────
# Loaded from api/prompts/explain_system.md at import time.
# Pattern mirrors Verify (api/server.py _VERIFY_PROMPT_PATH).
_EXPLAIN_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "explain_system.md"
_EXPLAIN_PROMPT_FALLBACK = (
    "You are a medical communication specialist. Translate medical reports "
    "into clear, plain language. ONLY explain what is in the user's input. "
    "Cite inline: [Source: LOINC], [Source: MedlinePlus], [Source: FDA]. "
    "Respond in the SAME language as the user's input. End with a short "
    "disclaimer in the same language."
)

try:
    EXPLAIN_GENERATION_PROMPT = _EXPLAIN_PROMPT_PATH.read_text(encoding="utf-8")
    logger.info("[Explain] system prompt loaded from %s", _EXPLAIN_PROMPT_PATH)
except FileNotFoundError:
    logger.warning("[Explain] prompt file missing, using inline fallback: %s", _EXPLAIN_PROMPT_PATH)
    EXPLAIN_GENERATION_PROMPT = _EXPLAIN_PROMPT_FALLBACK


# ─── Stage 2: Parallel API lookups ──────────────────────────────────────────

async def _lookup_loinc(entities: ExtractedEntities) -> tuple[list[ExplainSource], str]:
    """Look up lab tests and vital signs in LOINC."""
    sources: list[ExplainSource] = []
    context_parts: list[str] = []

    all_tests = (
        [(t.english, t.value, t.unit, t.reference_range) for t in entities.lab_tests] +
        [(v.english, v.value, v.unit, None) for v in entities.vital_signs]
    )

    for name, value, unit, ref_range in all_tests:
        try:
            result = await loinc_client.search(name)
            if result:
                long_name = result.get("long_common_name", name)
                # LOINC badges are non-clickable (public search requires login)
                sources.append(ExplainSource(
                    source_type=SourceType.LOINC,
                    label=f"LOINC {name}",
                    url=None,
                    description=long_name
                ))

                ctx = f"[LOINC] {name}: {long_name}"
                if value:
                    ctx += f" — value: {value}"
                    if unit:
                        ctx += f" {unit}"
                if ref_range:
                    ctx += f" (reference: {ref_range})"
                context_parts.append(ctx)
        except Exception as e:
            logger.warning("LOINC lookup failed (term len=%d): %s", len(name or ""), type(e).__name__)

    return sources, "\n".join(context_parts)


async def _lookup_rxnorm_and_medlineplus(entities: ExtractedEntities) -> tuple[list[ExplainSource], str]:
    """Look up medications via RxNorm, then fetch MedlinePlus info."""
    sources: list[ExplainSource] = []
    context_parts: list[str] = []

    for med in entities.medications:
        try:
            # Step 1: RxNorm normalization
            rxcui = await rxnorm_client.get_rxcui(med.english)
            if rxcui:
                sources.append(ExplainSource(
                    source_type=SourceType.RXNORM,
                    label=f"RxNorm {med.original}",
                    url=f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={med.english.replace(' ', '+')}",
                    description=f"RXCUI: {rxcui}"
                ))

            # Step 2: MedlinePlus consumer info
            ml_result = await medlineplus_client.get_drug_info(med.english)
            if ml_result:
                title = ml_result.get("title", med.english)
                url = ml_result.get("url", "")
                summary = ml_result.get("summary", "")

                sources.append(ExplainSource(
                    source_type=SourceType.MEDLINEPLUS,
                    label=f"MedlinePlus: {title}",
                    url=url,
                    description=summary[:200] if summary else None
                ))

                ctx = f"[MedlinePlus] {med.english}: {summary[:300]}" if summary else f"[MedlinePlus] {med.english}: {title}"
                if med.dosage:
                    ctx += f" (dosage mentioned: {med.dosage})"
                context_parts.append(ctx)

        except Exception as e:
            logger.warning("RxNorm/MedlinePlus lookup failed (term len=%d): %s", len(med.english or ""), type(e).__name__)

    return sources, "\n".join(context_parts)


async def _lookup_diagnoses(entities: ExtractedEntities) -> tuple[list[ExplainSource], str]:
    """Look up diagnoses in MedlinePlus."""
    sources: list[ExplainSource] = []
    context_parts: list[str] = []

    for dx in entities.diagnoses:
        try:
            ml_result = await medlineplus_client.get_condition_info(dx.english)
            if ml_result:
                title = ml_result.get("title", dx.english)
                url = ml_result.get("url", "")
                summary = ml_result.get("summary", "")

                sources.append(ExplainSource(
                    source_type=SourceType.MEDLINEPLUS,
                    label=f"MedlinePlus: {title}",
                    url=url,
                    description=summary[:200] if summary else None
                ))

                ctx = f"[MedlinePlus] {dx.english}: {summary[:300]}" if summary else f"[MedlinePlus] {dx.english}: {title}"
                context_parts.append(ctx)
        except Exception as e:
            logger.warning("MedlinePlus lookup failed (term len=%d): %s", len(dx.english or ""), type(e).__name__)

    return sources, "\n".join(context_parts)


async def retrieve_context(entities: ExtractedEntities) -> tuple[list[ExplainSource], str]:
    """
    Stage 2: Parallel API lookups.
    Returns (all_sources, combined_context_string)
    """
    results = await asyncio.gather(
        _lookup_loinc(entities),
        _lookup_rxnorm_and_medlineplus(entities),
        _lookup_diagnoses(entities),
        return_exceptions=True
    )

    all_sources: list[ExplainSource] = []
    all_context: list[str] = []

    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Retrieve stage partial failure: {result}")
            continue
        sources, context = result
        all_sources.extend(sources)
        if context:
            all_context.append(context)

    return all_sources, "\n\n".join(all_context)


# ─── Stage 3: Generate explanation (streaming) ──────────────────────────────

# Path 1 citation-hallucination defense (2026-04-29): the LLM may emit
# fabricated PubMed/NICE/Cochrane citations because the prompt's older
# "≥1 non-LOINC source required" rule pushed it that way. The retrieval
# pipeline does NOT fetch PubMed/NICE/Cochrane evidence — only LOINC,
# RxNorm, MedlinePlus, FDA. Any citation outside that whitelist, or any
# URL not actually present in the retrieved sources, is fabricated and
# must be stripped before pydantic validation (PUBMED was removed from
# the SourceType enum, so unfiltered output would fail schema_validation).
ALLOWED_CITATION_SOURCE_TYPES = {"LOINC", "RxNorm", "MedlinePlus", "FDA"}


def _is_valid_citation_dict(citation: dict, retrieved_urls: set[str]) -> bool:
    """
    Returns False if the citation appears fabricated. Operates on the raw
    JSON dict (pre-pydantic) so banned source_types like PubMed are
    stripped before SourceType enum validation rejects the whole response.
    """
    source_type = citation.get("source_type", "")
    if source_type not in ALLOWED_CITATION_SOURCE_TYPES:
        return False
    url = citation.get("url") or ""
    if url:
        url_lower = url.lower()
        if "pubmed" in url_lower or "ncbi.nlm.nih.gov" in url_lower:
            return False
        # URL must match one we actually retrieved. LOINC citations
        # legitimately have url=null (handled by the `if url:` guard),
        # so this only fires when the LLM invents a URL.
        if url not in retrieved_urls:
            return False
    return True


def _normalize_explain_items(parsed: dict) -> int:
    """Coerce ExplainItem.value=null to "" before pydantic validation.

    The LLM legitimately emits `null` for items with no numeric value
    (dietary recommendations, lifestyle advice, qualitative findings).
    The schema declares `value: str` (required). Without this coercion
    the entire response fails schema_validation_failed (Bug M06,
    2026-04-30). Frontend gates rendering on falsy `item.value`, so an
    empty string renders cleanly with no value line.

    Returns count of items normalized (for logging).
    """
    normalized = 0
    for item in parsed.get("items", []):
        if item.get("value") is None:
            item["value"] = ""
            normalized += 1
    return normalized


def _filter_citations_in_dict(parsed: dict, sources: list[ExplainSource]) -> int:
    """
    Strip fabricated citations from the raw LLM JSON dict in place.
    Returns total count of citations dropped (for logging).
    """
    retrieved_urls = {s.url for s in sources if s.url}
    dropped = 0
    for item in parsed.get("items", []):
        before = len(item.get("citations", []))
        item["citations"] = [
            c for c in item.get("citations", [])
            if _is_valid_citation_dict(c, retrieved_urls)
        ]
        dropped += before - len(item["citations"])
    for corr in parsed.get("clinical_correlations", []):
        before = len(corr.get("citations", []))
        corr["citations"] = [
            c for c in corr.get("citations", [])
            if _is_valid_citation_dict(c, retrieved_urls)
        ]
        dropped += before - len(corr["citations"])
    return dropped


def _is_code_lookup_only(citations: list[ExplainSource]) -> bool:
    """
    Returns True if all citations are LOINC/RxNorm only, OR citations is empty.
    Used by Step 3 LOINC scope guard: clinical-judgment claims (yellow/red)
    cited only by code-lookup sources are treated as insufficient evidence.
    """
    if not citations:
        return True
    code_lookup_types = (SourceType.LOINC, SourceType.RXNORM)
    return all(c.source_type in code_lookup_types for c in citations)


def _has_any_value(entities: ExtractedEntities) -> bool:
    """Generic error UX (2026-04-29): True if at least one entity carries a
    numeric value, unit, or dosage. Diagnoses are name-only and don't count
    toward "has values" (a bare "I have diabetes" without labs/meds is the
    no_values_in_input case)."""
    for lab in entities.lab_tests:
        if lab.value or lab.unit:
            return True
    for vital in entities.vital_signs:
        if vital.value:
            return True
    for med in entities.medications:
        if med.dosage:
            return True
    return False


async def generate_explanation(
    report_text: str,
    entities: ExtractedEntities,
    context: str,
    response_language: Optional[str] = None,
    sources: Optional[list[ExplainSource]] = None,
) -> dict:
    """
    Stage 3: Generate structured JSON explanation (non-streaming, JSON mode).
    Returns dict {items, clinical_correlations, disclaimer}.
    Raises ValueError on JSON parse or schema validation failure.

    `response_language` (BCP-47, e.g. "zh-TW") drives server-side disclaimer
    and downgrade-note locale lookups (PRD § 2.7 Step 5). Falls back to
    English if missing.

    Uses GENERATOR_PROVIDER / GENERATOR_MODEL per PRD §2.1 v1.4 needs 6.
    """
    locale = response_language or "en"
    user_content = f"""Response language: {locale}

Medical report to explain:
---
{report_text}
---

Verified reference data from official sources:
{context if context else "(No external reference data retrieved — explain from medical knowledge only)"}

Input language (for entity-to-source matching only, NOT for output): {entities.input_language}"""

    binding = get_generator_provider()
    req = CompletionRequest(
        model=binding.model,
        messages=[
            {"role": "system", "content": EXPLAIN_GENERATION_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3,
        max_tokens=8000,
        response_format={"type": "json_object"},
    )
    response = await binding.provider.complete(req)

    # Rule 18: detect max_tokens truncation BEFORE parsing. A truncated
    # response is invalid JSON by construction; surfacing finish_reason
    # here gives the user an actionable error instead of a generic
    # "invalid_json" that obscures the cause (output budget exceeded).
    if response.finish_reason == "length":
        logger.error(
            "[Explain] Stage 3 output truncated by max_tokens (finish_reason=length, "
            "output_tokens=%d)", response.output_tokens
        )
        raise ValueError("output_truncated")

    raw_content = response.content or ""

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("[Explain] LLM returned invalid JSON: %s", e)
        raise ValueError("invalid_json") from e

    # Path 1 defense: drop fabricated citations before pydantic validation.
    # Without this, a LLM-emitted source_type="PubMed" would fail SourceType
    # enum validation and reject the entire response.
    dropped_count = _filter_citations_in_dict(parsed, sources or [])
    if dropped_count > 0:
        logger.warning(
            "[Explain] Filtered %d fabricated citation(s) from LLM response",
            dropped_count,
        )

    # Bug M06 (2026-04-30): coerce ExplainItem.value=null to "" before pydantic.
    # LLM legitimately emits null for items without numeric values (dietary
    # advice, lifestyle recommendations); schema requires str.
    normalized_count = _normalize_explain_items(parsed)
    if normalized_count > 0:
        logger.info(
            "[Explain] Normalized %d item(s) with null value → empty string",
            normalized_count,
        )

    try:
        items = [ExplainItem.model_validate(i) for i in parsed.get("items", [])]
        correlations = [
            ClinicalCorrelation.model_validate(c)
            for c in parsed.get("clinical_correlations", [])
        ]
    except ValidationError as e:
        logger.error("[Explain] LLM JSON failed schema validation: %s", e)
        raise ValueError("schema_validation_failed") from e

    # Step 3: limited-citation transparency note.
    # When a yellow/red item has only code-lookup citations (LOINC/RxNorm,
    # or empty after Path 1 filtering), append a note disclosing the
    # citation limitation. The LLM's risk_tier reflects medical judgment
    # and is preserved — citation completeness is not a proxy for medical
    # severity (Bug X1, 2026-04-29: prior version forced green here, which
    # produced medically incorrect UX after Path 1 stripped fabricated
    # PubMed cites).
    for item in items:
        if item.risk_tier in (RiskTier.YELLOW, RiskTier.RED):
            if _is_code_lookup_only(item.citations):
                logger.info(
                    "[Explain] Step 3 limited-citation note appended: kind=item "
                    "term_len=%d tier=%s citations_source_types=%s",
                    len(item.term or ""),
                    item.risk_tier.value,
                    [c.source_type.value if hasattr(c.source_type, "value") else c.source_type for c in item.citations],
                )
                item.explanation += "\n\n" + get_downgrade_item_note(locale)

    for corr in correlations:
        if corr.risk_tier in (RiskTier.YELLOW, RiskTier.RED):
            if _is_code_lookup_only(corr.citations):
                logger.info(
                    "[Explain] Step 3 limited-citation note appended: kind=correlation "
                    "items_referenced=%s tier=%s citations_source_types=%s",
                    corr.items_referenced,
                    corr.risk_tier.value,
                    [c.source_type.value if hasattr(c.source_type, "value") else c.source_type for c in corr.citations],
                )
                corr.insight += "\n\n" + get_downgrade_corr_note(locale)

    disclaimer = get_disclaimer(locale)

    return {
        "items": [i.model_dump(mode="json") for i in items],
        "clinical_correlations": [c.model_dump(mode="json") for c in correlations],
        "disclaimer": disclaimer,
    }


# ─── Main pipeline entry point ──────────────────────────────────────────────

async def run_explain_pipeline(
    report_text: str,
    response_language: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    Full 3-stage Explain pipeline. Yields SSE-compatible dicts:
      {"type": "status", "content": "..."}
      {"type": "sources", "content": [...]}
      {"type": "identified", "language": "...", "items": [...]}
      {"type": "checking", "items": [...]}
      {"type": "explain_result", "content": {items, clinical_correlations, disclaimer}}
      {"type": "error", "content": "..."}   # on Stage 3 JSON/schema failure
      {"type": "done", "query_time_ms": N}

    `response_language` (BCP-47) is threaded into Stage 3 for server-side
    disclaimer + downgrade-note locale lookups (PRD § 2.7 Step 5).
    """
    start = time.time()

    # Pre-stream validation (Generic error UX, 2026-04-29).
    # Empty / whitespace-only input → emit empty_input SSE event and bail.
    if len(report_text.strip()) == 0:
        logger.info("[Explain] empty_input — whitespace-only or empty report_text")
        yield {
            "type": "error",
            "code": ExplainErrorCode.EMPTY_INPUT.value,
            "message": "Empty input",
        }
        return

    # Length cap (defense-in-depth; pydantic max_length=5000 normally blocks first).
    if len(report_text) > MAX_INPUT_CHARS:
        logger.info("[Explain] input_too_long — len=%d > %d", len(report_text), MAX_INPUT_CHARS)
        yield {
            "type": "error",
            "code": ExplainErrorCode.INPUT_TOO_LONG.value,
            "message": f"Input exceeds {MAX_INPUT_CHARS} characters",
        }
        return

    # Stage 1: Extract entities
    detected_lang_early = detect_language(report_text)
    lang_instruction = get_language_instruction(detected_lang_early)
    logger.info("[Explain] Processing report, length=%d, language=%s", len(report_text), detected_lang_early)
    logger.info(f"[Explain] Language instruction for GPT: {lang_instruction or '(none - English default)'}")
    yield {"type": "status", "content": "Analyzing your report..."}
    try:
        entities = await extract_entities(report_text)
    except VelaError as e:
        # §2.1 PHASE B: provider layer wraps openai.APIError / RateLimitError /
        # timeout into VelaError before reaching here.
        logger.warning("[Explain] Provider error in Stage 1: %s", e)
        yield {
            "type": "error",
            "code": ExplainErrorCode.OPENAI_API_ERROR.value,
            "message": "LLM service unavailable",
        }
        return
    logger.info(f"[Explain] entities.input_language = {entities.input_language}")

    # Override GPT's language detection with ours when they disagree
    if entities.input_language == "en" and detected_lang_early != "en":
        logger.info(f"[Explain] Overriding GPT language '{entities.input_language}' → '{detected_lang_early}'")
        entities.input_language = detected_lang_early

    # Generic error UX (2026-04-29): distinguish "no entities" from "entities without values".
    # Real entity field names: lab_tests / medications / diagnoses / vital_signs.
    # MedicationEntity has a single `dosage` field (no separate dose/frequency).
    total_entities = (
        len(entities.lab_tests)
        + len(entities.medications)
        + len(entities.diagnoses)
        + len(entities.vital_signs)
    )
    if total_entities == 0:
        logger.info("[Explain] empty_input — Stage 1 detected zero medical entities")
        yield {
            "type": "error",
            "code": ExplainErrorCode.EMPTY_INPUT.value,
            "message": "No medical entities detected",
        }
        return
    if not _has_any_value(entities):
        logger.info(
            "[Explain] no_values_in_input — %d entities, none with numeric values",
            total_entities,
        )
        yield {
            "type": "error",
            "code": ExplainErrorCode.NO_VALUES_IN_INPUT.value,
            "message": "Entities detected but no values",
        }
        return

    # Stage 2: Parallel API lookups
    logger.info("[Explain] Entities extracted — meds: %d, labs: %d, vitals: %d", len(entities.medications), len(entities.lab_tests), len(entities.vital_signs))
    yield {"type": "status", "content": "Looking up verified sources..."}
    sources, context = await retrieve_context(entities)
    logger.info("[Explain] Sources found: %d", len(sources))

    # Emit sources for frontend badge rendering
    yield {
        "type": "sources",
        "content": [s.model_dump() for s in sources]
    }

    # ── Identification confirmation events ────────────────────────────
    detected_lang = detect_language(report_text)

    # Build "identified" items from entities (medications + lab tests)
    identified_items = []
    for med in entities.medications:
        identified_items.append({
            "input": med.original,
            "standard": med.english,
            "source": "RxNorm",
        })
    for lab in entities.lab_tests:
        identified_items.append({
            "input": lab.original,
            "standard": lab.english,
            "source": "LOINC",
        })
    for vs in entities.vital_signs:
        identified_items.append({
            "input": vs.original,
            "standard": vs.english,
            "source": "LOINC",
        })

    yield {
        "type": "identified",
        "language": detected_lang,
        "items": identified_items,
    }

    # Build "checking" items from actual Stage 2 source lookups
    checking_items = []
    for s in sources:
        # Extract a clean name from the label (strip prefix like "RxNorm ", "LOINC ", "MedlinePlus: ")
        name = s.label
        for prefix in ("RxNorm ", "LOINC ", "MedlinePlus: "):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        checking_items.append({
            "name": name,
            "source": s.source_type.value,
        })

    yield {
        "type": "checking",
        "items": checking_items,
    }

    # Stage 3: Generate structured JSON explanation (blocking)
    yield {"type": "status", "content": "Generating explanation..."}
    try:
        result = await generate_explanation(
            report_text, entities, context,
            response_language=response_language,
            sources=sources,
        )
    except VelaError as e:
        # §2.1 PHASE B: provider layer wraps openai.APIError into VelaError.
        logger.warning("[Explain] Provider error in Stage 3: %s", e)
        yield {
            "type": "error",
            "code": ExplainErrorCode.OPENAI_API_ERROR.value,
            "message": "LLM service unavailable",
        }
        return
    except ValueError as e:
        # generate_explanation raises ValueError("invalid_json"),
        # ValueError("schema_validation_failed"), or
        # ValueError("output_truncated"). Truncation gets a distinct code
        # so the frontend can show actionable copy ("split into smaller
        # sections") instead of the generic schema-validation message.
        inner = str(e)
        logger.error("[Explain] Stage 3 LLM output invalid: %s", inner)
        if inner == "output_truncated":
            yield {
                "type": "error",
                "code": ExplainErrorCode.OUTPUT_TRUNCATED.value,
                "message": "LLM output exceeded token budget — report too long for single pass",
            }
        else:
            yield {
                "type": "error",
                "code": ExplainErrorCode.SCHEMA_VALIDATION_FAILED.value,
                "message": f"LLM output failed validation ({inner})",
            }
        return

    yield {"type": "explain_result", "content": result}

    elapsed = int((time.time() - start) * 1000)
    yield {"type": "done", "query_time_ms": elapsed}