"""
Explain Feature — Stage 1: Entity Extraction
Uses GPT-4.1-mini to extract medical entities with bilingual output
"""

import json
import logging
from openai import AsyncOpenAI
from api.models.explain_schemas import (
    ExtractedEntities, LabTestEntity, MedicationEntity,
    DiagnosisEntity, VitalSignEntity
)

logger = logging.getLogger(__name__)

ENTITY_EXTRACTION_PROMPT = """Extract medical entities from the user input. Return JSON only — no preamble, no markdown fences.

Output format:
{
  "input_language": "<language code, e.g. en, zh-TW, zh-CN, ja, ko, es, de>",
  "lab_tests": [
    {"original": "<name as in input>", "english": "<English name>", "value": "<number or null>", "unit": "<unit or null>", "reference_range": "<range or null>"}
  ],
  "medications": [
    {"original": "<name as in input>", "english": "<generic English name>", "dosage": "<dosage or null>"}
  ],
  "diagnoses": [
    {"original": "<name as in input>", "english": "<English name>", "icd_code": "<ICD-10 if identifiable, else null>"}
  ],
  "vital_signs": [
    {"original": "<name as in input>", "english": "<English name>", "value": "<value or null>", "unit": "<unit or null>"}
  ]
}

Rules:
- Only extract entities that are ACTUALLY PRESENT in the input. Never add entities not mentioned.
- For "english" field: translate to standard medical English (e.g. 腎絲球過濾率 → eGFR, 糖化血色素 → HbA1c, 冠脂妥 → Rosuvastatin)
- For medications: use generic name in English (e.g. Crestor → Rosuvastatin)
- If input is already in English, "original" and "english" will be the same
- Return empty arrays [] if no entities of that type are found
- detect input_language from the primary language of the input text"""


async def extract_entities(report_text: str, openai_client: AsyncOpenAI) -> ExtractedEntities:
    """
    Stage 1: Extract structured medical entities from free-text report.
    Returns bilingual entity list for API lookups.
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=2000,
            temperature=0,
            messages=[
                {"role": "system", "content": ENTITY_EXTRACTION_PROMPT},
                {"role": "user", "content": report_text}
            ]
        )

        # Cost tracking
        try:
            from api.services.cost_tracker import log_api_cost_standalone
            if response.usage:
                await log_api_cost_standalone(
                    "system", "explain/entity_extraction", "gpt-4.1-mini",
                    response.usage.prompt_tokens, response.usage.completion_tokens
                )
        except Exception:
            pass

        raw = response.choices[0].message.content.strip()
        logger.info("[EntityExtractor] Raw GPT response length: %d chars", len(raw))

        # Strip markdown fences if LLM adds them despite instruction
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        logger.info(f"[EntityExtractor] Parsed — labs: {len(data.get('lab_tests', []))}, meds: {len(data.get('medications', []))}, vitals: {len(data.get('vital_signs', []))}")

        return ExtractedEntities(
            input_language=data.get("input_language", "en"),
            lab_tests=[LabTestEntity(**item) for item in data.get("lab_tests", [])],
            medications=[MedicationEntity(**item) for item in data.get("medications", [])],
            diagnoses=[DiagnosisEntity(**item) for item in data.get("diagnoses", [])],
            vital_signs=[VitalSignEntity(**item) for item in data.get("vital_signs", [])],
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Parse / shape errors: LLM returned unparseable output.
        # Treat as "no entities detected" so caller can route to empty_input
        # error_code via the Stage 1 entity-count check.
        logger.warning(f"Entity extraction parse error: {e}. Falling back to empty entities.")
        return ExtractedEntities()
    # Note: OpenAI errors (APIError/APITimeoutError/RateLimitError) are NOT
    # caught here — they propagate to run_explain_pipeline which converts
    # them to the openai_api_error SSE event (Generic error UX, 2026-04-29).
    # Other unexpected exceptions also propagate to the server.py catchall
    # which emits the `generic` error_code.