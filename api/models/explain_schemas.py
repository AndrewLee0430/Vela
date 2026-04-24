"""
Explain Feature — Pydantic Models
ExplainRequest, MedicalEntity, ExplainSource
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    LOINC      = "LOINC"
    MEDLINEPLUS = "MedlinePlus"
    FDA        = "FDA"
    RXNORM     = "RxNorm"
    PUBMED     = "PubMed"
    LLM        = "LLM"  # no external verification


class ExplainRequest(BaseModel):
    report_text: str = Field(
        ...,
        description="Medical report, lab results, or clinical document to explain",
        max_length=5000,
        examples=["eGFR 45 mL/min (ref >60), HbA1c 7.8%, Metformin 1000mg BID"]
    )


class LabTestEntity(BaseModel):
    original: str           # as it appears in input (any language)
    english: str            # English name for API lookups
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class MedicationEntity(BaseModel):
    original: str
    english: str            # generic English name
    dosage: Optional[str] = None


class DiagnosisEntity(BaseModel):
    original: str
    english: str
    icd_code: Optional[str] = None


class VitalSignEntity(BaseModel):
    original: str
    english: str
    value: Optional[str] = None
    unit: Optional[str] = None


class ExtractedEntities(BaseModel):
    lab_tests:   list[LabTestEntity]   = Field(default_factory=list)
    medications: list[MedicationEntity] = Field(default_factory=list)
    diagnoses:   list[DiagnosisEntity]  = Field(default_factory=list)
    vital_signs: list[VitalSignEntity]  = Field(default_factory=list)
    input_language: str = "en"          # detected language code


class ExplainSource(BaseModel):
    source_type: SourceType
    label: str          # e.g. "LOINC 62238-1"
    url: Optional[str] = None
    description: Optional[str] = None


# ─── § 2.7 structured output types ──────────────────────────────────────────

class RiskTier(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ExplainItem(BaseModel):
    """Single interpreted lab/report item."""
    term: str                               # e.g. "eGFR", "LDL"
    value: str                              # e.g. "45 mL/min/1.73m²", "145 mg/dL"
    explanation: str                        # plain-language interpretation (hedging)
    risk_tier: RiskTier
    risk_label_key: str                     # i18n key, e.g. "explain.risk.yellow"
    citations: list[ExplainSource] = Field(default_factory=list)


class ClinicalCorrelation(BaseModel):
    """Cross-item insight, e.g. eGFR + Metformin → dosage risk."""
    items_referenced: list[str]             # terms matching ExplainItem.term
    insight: str                            # reasoning in hedging language
    risk_tier: RiskTier
    risk_label_key: str
    citations: list[ExplainSource] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    explanation: str
    sources: list[ExplainSource] = Field(default_factory=list)
    input_language: str = "en"
    disclaimer: str = "⚠️ This explanation is for reference only. It does not constitute medical advice. Please consult your healthcare provider."
    query_time_ms: int = 0

    # § 2.7 structured output (populated by Stage 3 after this step's prompt rewrite)
    items: list[ExplainItem] = Field(default_factory=list)
    clinical_correlations: list[ClinicalCorrelation] = Field(default_factory=list)


class ExplainCompletedPayload(BaseModel):
    """DTO for the `explain_completed` PostHog event (not persisted)."""
    query_id: str
    items_count: int
    correlations_count: int
    risk_tier_distribution: dict[str, int]  # {"green": N, "yellow": N, "red": N}