"""
Explain Feature — 3-Stage Pipeline
Stage 1: Extract entities (entity_extractor.py)
Stage 2: Parallel API lookups (LOINC, RxNorm, MedlinePlus, FDA)
Stage 3: Generate plain-language explanation (streaming)
"""

import asyncio
import logging
import time
from typing import AsyncGenerator
from openai import AsyncOpenAI

from api.models.explain_schemas import (
    ExtractedEntities, ExplainSource, SourceType
)
from api.services.entity_extractor import extract_entities
from api.data_sources.loinc_client import loinc_client
from api.data_sources.rxnorm_client import rxnorm_client
from api.data_sources.medlineplus_client import medlineplus_client
from api.utils.language_detector import detect_language, get_language_instruction

logger = logging.getLogger(__name__)

# Startup self-test for language detection
logger.info(f"Lang detector test: {detect_language('W.B.C. Count 白血球計數 6.5 血液檢查')}")

# ─── Stage 3 system prompt ──────────────────────────────────────────────────

EXPLAIN_GENERATION_PROMPT = """You are a medical communication specialist. Your job is to translate medical reports into clear, plain language that any patient can understand.

STRICT RULES:
1. ONLY explain what is in the user's input. NEVER add diagnoses, recommendations, or clinical advice not present in the report.
2. When reference data is provided in the context, cite it inline: [Source: LOINC], [Source: MedlinePlus], [Source: FDA]
3. If the report includes reference ranges, use them to explain whether values are normal, low, or high.
4. If reference ranges are NOT provided, note: "Reference ranges may vary by laboratory and region."
5. LANGUAGE RULE: Always respond in the SAME language as the user's input. If input is Traditional Chinese (繁體中文), respond in Traditional Chinese. If input is Simplified Chinese (简体中文), respond in Simplified Chinese. If English, respond in English. If mixed, use the dominant language.
6. Use a warm, reassuring tone. Explain what the numbers mean, not what the patient should do.
7. Structure your response with clear sections for: Lab Results, Medications (if any), Diagnoses (if any).
8. Do NOT reproduce full article text from MedlinePlus. Use only brief summaries.
9. End with a short disclaimer in the SAME language as the input.

DISCLAIMER TRANSLATIONS:
- English: "⚠️ This explanation is for reference purposes only. It does not replace professional medical advice. Please consult your healthcare provider."
"""


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

async def generate_explanation(
    report_text: str,
    entities: ExtractedEntities,
    context: str,
    openai_client: AsyncOpenAI
) -> AsyncGenerator[str, None]:
    """
    Stage 3: Stream plain-language explanation using retrieved context.
    """
    user_content = f"""Medical report to explain:
---
{report_text}
---

Verified reference data from official sources:
{context if context else "(No external reference data retrieved — explain from medical knowledge only)"}

Detected language: {entities.input_language}

Please explain this report in the same language as the input ({entities.input_language})."""

    stream = await openai_client.chat.completions.create(
        model="gpt-4.1",
        max_tokens=1500,
        temperature=0.3,
        stream=True,
        messages=[
            {"role": "system", "content": EXPLAIN_GENERATION_PROMPT},
            {"role": "user", "content": user_content}
        ]
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ─── Main pipeline entry point ──────────────────────────────────────────────

async def run_explain_pipeline(
    report_text: str,
    openai_client: AsyncOpenAI
) -> AsyncGenerator[dict, None]:
    """
    Full 3-stage Explain pipeline. Yields SSE-compatible dicts:
      {"type": "status", "content": "..."}
      {"type": "sources", "content": [...]}
      {"type": "answer", "content": "token..."}
      {"type": "done"}
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

    # Stage 3: Stream explanation
    yield {"type": "status", "content": "Generating explanation..."}
    async for token in generate_explanation(report_text, entities, context, openai_client):
        yield {"type": "answer", "content": token}

    elapsed = int((time.time() - start) * 1000)
    yield {"type": "done", "query_time_ms": elapsed}