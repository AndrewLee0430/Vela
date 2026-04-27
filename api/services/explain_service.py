"""
Explain Feature — 3-Stage Pipeline
Stage 1: Extract entities (entity_extractor.py)
Stage 2: Parallel API lookups (LOINC, RxNorm, MedlinePlus, FDA)
Stage 3: Generate plain-language explanation (streaming)
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
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

logger = logging.getLogger(__name__)

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
            logger.warning(f"LOINC lookup failed for {name}: {e}")

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
            logger.warning(f"RxNorm/MedlinePlus lookup failed for {med.english}: {e}")

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
            logger.warning(f"MedlinePlus lookup failed for {dx.english}: {e}")

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


async def generate_explanation(
    report_text: str,
    entities: ExtractedEntities,
    context: str,
    openai_client: AsyncOpenAI,
    response_language: Optional[str] = None,
) -> dict:
    """
    Stage 3: Generate structured JSON explanation (non-streaming, JSON mode).
    Returns dict {items, clinical_correlations, disclaimer}.
    Raises ValueError on JSON parse or schema validation failure.

    `response_language` (BCP-47, e.g. "zh-TW") drives server-side disclaimer
    and downgrade-note locale lookups (PRD § 2.7 Step 5). Falls back to
    English if missing.
    """
    locale = response_language or "en"
    user_content = f"""Medical report to explain:
---
{report_text}
---

Verified reference data from official sources:
{context if context else "(No external reference data retrieved — explain from medical knowledge only)"}

Detected language: {entities.input_language}

Please explain this report in the same language as the input ({entities.input_language})."""

    response = await openai_client.chat.completions.create(
        model="gpt-4.1",
        max_tokens=1500,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXPLAIN_GENERATION_PROMPT},
            {"role": "user", "content": user_content}
        ]
    )

    raw_content = response.choices[0].message.content or ""

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("[Explain] LLM returned invalid JSON: %s", e)
        raise ValueError("invalid_json") from e

    try:
        items = [ExplainItem.model_validate(i) for i in parsed.get("items", [])]
        correlations = [
            ClinicalCorrelation.model_validate(c)
            for c in parsed.get("clinical_correlations", [])
        ]
    except ValidationError as e:
        logger.error("[Explain] LLM JSON failed schema validation: %s", e)
        raise ValueError("schema_validation_failed") from e

    # Step 3: LOINC scope post-processing guard.
    # Per PRD § 2.7 req 3: clinical-judgment content (yellow/red risk_tier)
    # must include at least one non-LOINC, non-RxNorm citation. When the LLM
    # violates this, downgrade to green rather than re-call (zero added cost).
    # MedlinePlus is acceptable non-code-lookup evidence for this guard.
    for item in items:
        if item.risk_tier in (RiskTier.YELLOW, RiskTier.RED):
            if _is_code_lookup_only(item.citations):
                original_tier = item.risk_tier.value
                logger.warning(
                    "[Explain] Step 3 downgrade triggered: kind=item "
                    "term=%s original_tier=%s citations_source_types=%s",
                    item.term,
                    original_tier,
                    [c.source_type.value if hasattr(c.source_type, "value") else c.source_type for c in item.citations],
                )
                item.risk_tier = RiskTier.GREEN
                item.explanation += "\n\n" + get_downgrade_item_note(locale)

    for corr in correlations:
        if corr.risk_tier in (RiskTier.YELLOW, RiskTier.RED):
            if _is_code_lookup_only(corr.citations):
                original_tier = corr.risk_tier.value
                logger.warning(
                    "[Explain] Step 3 downgrade triggered: kind=correlation "
                    "items_referenced=%s original_tier=%s citations_source_types=%s",
                    corr.items_referenced,
                    original_tier,
                    [c.source_type.value if hasattr(c.source_type, "value") else c.source_type for c in corr.citations],
                )
                corr.risk_tier = RiskTier.GREEN
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
    openai_client: AsyncOpenAI,
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

    # Stage 1: Extract entities
    detected_lang_early = detect_language(report_text)
    lang_instruction = get_language_instruction(detected_lang_early)
    logger.info("[Explain] Processing report, length=%d, language=%s", len(report_text), detected_lang_early)
    logger.info(f"[Explain] Language instruction for GPT: {lang_instruction or '(none - English default)'}")
    yield {"type": "status", "content": "Analyzing your report..."}
    entities = await extract_entities(report_text, openai_client)
    logger.info(f"[Explain] entities.input_language = {entities.input_language}")

    # Override GPT's language detection with ours when they disagree
    if entities.input_language == "en" and detected_lang_early != "en":
        logger.info(f"[Explain] Overriding GPT language '{entities.input_language}' → '{detected_lang_early}'")
        entities.input_language = detected_lang_early

    # Stage 2: Parallel API lookups
    logger.info(f"[Explain] Entities extracted — meds: {[m.english for m in entities.medications]}, labs: {[l.english for l in entities.lab_tests]}, vitals: {[v.english for v in entities.vital_signs]}")
    yield {"type": "status", "content": "Looking up verified sources..."}
    sources, context = await retrieve_context(entities)
    logger.info(f"[Explain] Sources found: {len(sources)} — {[s.label for s in sources]}")

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
            report_text, entities, context, openai_client,
            response_language=response_language,
        )
    except ValueError as e:
        error_code = str(e)  # "invalid_json" or "schema_validation_failed"
        logger.error("[Explain] Stage 3 failed: %s", error_code)
        yield {
            "type": "error",
            "code": f"explain_llm_{error_code}",
            "content": "Failed to generate structured explanation. Please try again.",
        }
        return

    yield {"type": "explain_result", "content": result}

    elapsed = int((time.time() - start) * 1000)
    yield {"type": "done", "query_time_ms": elapsed}