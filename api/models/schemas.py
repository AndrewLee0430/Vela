"""
Pydantic 模型定義
用於 API Request/Response 驗證
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional

MAX_DRUG_NAME_CHARS = 100  # 最長藥名 (品牌名 + 學名) 不超過此值
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    """資料來源類型"""
    PUBMED = "pubmed"
    FDA = "fda"
    LOCAL = "local"
    TFDA = "tfda"   # ADR 007 grounding-lite: TFDA 官方核准適應症 (indication-only) citable corpus


class CredibilityLevel(str, Enum):
    """可信度等級"""
    PEER_REVIEWED = "peer-reviewed"    # PubMed 同行評審
    OFFICIAL = "official"               # FDA 官方
    CLINICAL_TRIAL = "clinical-trial"   # 臨床試驗
    REVIEW = "review"                   # 綜述文章
    INTERNAL = "internal"               # 內部資料


# ============ Request Models ============

class ResearchRequest(BaseModel):
    """醫學研究查詢請求"""
    question: str = Field(
        ...,
        description="用戶的問題",
        min_length=2,
        max_length=1000,
        examples=["Metformin 和 Warfarin 可以一起使用嗎？"]
    )
    sources: Optional[list[SourceType]] = Field(
        default=None,
        description="限制資料來源（預設全部）"
    )
    max_results: Optional[int] = Field(
        default=5,
        description="最多返回的 Citation 數量",
        ge=1,
        le=10
    )
    response_language: Optional[str] = Field(
        default=None,
        description="期望的回答語言（UI locale，BCP-47，如 zh-TW）；由 _resolve_response_language 解析，回退 Accept-Language → en"
    )


class FeedbackRequest(BaseModel):
    """用戶回饋請求"""
    question: str
    helpful: bool
    citations_clicked: Optional[list[int]] = None
    comment: Optional[str] = None


# ============ Response Models ============

class Citation(BaseModel):
    """引用來源"""
    id: int = Field(..., description="引用編號（對應答案中的 [1][2]）")
    source_type: SourceType = Field(..., description="來源類型")
    source_id: str = Field(..., description="來源 ID（如 PMID:12345678）")
    title: str = Field(..., description="標題")
    snippet: str = Field(..., description="相關片段摘要")
    url: str = Field(..., description="原文連結")
    credibility: CredibilityLevel = Field(..., description="可信度等級")
    year: Optional[str] = Field(None, description="發表年份")
    authors: Optional[str] = Field(None, description="作者")
    journal: Optional[str] = Field(None, description="期刊名稱")


class ResearchResponse(BaseModel):
    """醫學研究查詢回應（非串流版本）"""
    answer: str = Field(..., description="AI 生成的答案")
    citations: list[Citation] = Field(..., description="引用來源列表")
    query_time_ms: int = Field(..., description="查詢耗時（毫秒）")


class StreamEventType(str, Enum):
    """串流事件類型"""
    ANSWER = "answer"           # 答案片段
    CITATIONS = "citations"     # 引用資訊
    ERROR = "error"             # 錯誤
    DONE = "done"               # 完成
    FALLBACK  = "fallback"


class StreamEvent(BaseModel):
    """SSE 串流事件"""
    type: StreamEventType
    content: Optional[str | list[Citation]] = None
    
    def to_sse(self) -> str:
        """轉換為 SSE 格式"""
        import json
        data = self.model_dump()
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============ Internal Models ============

class RetrievedDocument(BaseModel):
    """檢索到的文件"""
    content: str
    source_type: SourceType
    source_id: str
    title: str
    url: str
    credibility: CredibilityLevel
    year: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    relevance_score: float = 0.0
    # PRD §2.10.6 evidence-tier signal (additive metadata; NOT surfaced in Citation —
    # to_citation() below omits it, so user-visible citations are unchanged). Populated
    # for PubMed docs from efetch PublicationType; used only by the source-weighting
    # SHADOW classifier. Empty/None for non-PubMed sources (they get source-default tiers).
    publication_types: Optional[list[str]] = None

    def to_citation(self, citation_id: int) -> Citation:
        """轉換為 Citation"""
        # 截斷 snippet
        snippet = self.content[:500] + "..." if len(self.content) > 500 else self.content
        
        return Citation(
            id=citation_id,
            source_type=self.source_type,
            source_id=self.source_id,
            title=self.title,
            snippet=snippet,
            url=self.url,
            credibility=self.credibility,
            year=self.year,
            authors=self.authors,
            journal=self.journal
        )


# ============ Suggestions ============

class SuggestionsResponse(BaseModel):
    """常見問題建議"""
    suggestions: list[str] = Field(
        ...,
        description="建議的問題列表"
    )
    
    @classmethod
    def default_suggestions(cls) -> "SuggestionsResponse":
        """預設的建議問題"""
        return cls(suggestions=[
            "Metformin 的常見副作用有哪些？",
            "Warfarin 和哪些藥物有交互作用？",
            "老年患者使用 NSAIDs 需要注意什麼？",
            "糖尿病患者的用藥注意事項？",
            "ACE inhibitors 的禁忌症是什麼？",
            "Statins 類藥物的肝功能監測建議？",
            "懷孕期間可以使用哪些止痛藥？",
            "腎功能不全患者的劑量調整原則？"
        ])


# ============ Verify Feature Models ============

class VerifyRequest(BaseModel):
    """藥物交互作用驗證請求"""
    drugs: list[str] = Field(
        ...,
        description="藥物清單 (支援中英文)，最多 10 個，每個藥名不超過 100 字元",
        min_length=1,
        max_length=10,
        examples=[["Metformin", "Warfarin"]]
    )
    patient_context: Optional[str] = Field(
        None,
        description="患者背景 (年齡範圍、性別、共病)，請勿輸入個資",
        max_length=200
    )
    response_language: Optional[str] = Field(
        None,
        description="使用者期待的輸出語言代碼 (e.g. 'zh-TW', 'ja', 'en')。未提供時後端會回退到 Accept-Language → 'en'。",
        max_length=16,
        examples=["zh-TW", "ja", "en"],
    )

    @field_validator("drugs")
    @classmethod
    def validate_drug_name_length(cls, drug_list: list[str]) -> list[str]:
        """
        確保每個藥名不超過 MAX_DRUG_NAME_CHARS 字元。
        Pydantic 的 list max_length 只限制「幾個元素」，
        不限制「每個元素多長」，這裡補上這個檢查。
        """
        for drug in drug_list:
            if len(drug) > MAX_DRUG_NAME_CHARS:
                raise ValueError(
                    f"Drug name too long ({len(drug)} chars). "
                    f"Please keep each drug name under {MAX_DRUG_NAME_CHARS} characters."
                )
        return drug_list


class DrugInteraction(BaseModel):
    """單一交互作用結果"""
    drug_pair: tuple[str, str]
    severity: str  # Canonical enum: Critical, Major, Moderate, Minor, Unknown (for CSS / summary math)
    severity_label: Optional[str] = None  # Localized display (e.g. '嚴重' for zh-TW). Frontend: label || severity
    description: str
    mechanism: Optional[str] = None
    clinical_recommendation: str
    # HONEST attribution default (P1). The interaction is the model's inference; when an
    # FDA label was consulted the main path sets "AI analysis of FDA label", the no-label
    # path sets "Clinical Knowledge (No FDA label available)". This default must never
    # read as an FDA-stated interaction.
    source: str = "AI analysis of FDA label"
    source_url: Optional[str] = None  # ✅ 新增：FDA 原文链接


class TfdaGrounding(BaseModel):
    """ADR 007 T2a: one deterministic TFDA brand→ingredient resolution, passed through
    as structured data so the frontend can render a localized transparency note
    (enum-authority pattern — backend emits data, frontend localizes strings)."""
    query: str                                            # user-entered token, verbatim
    ingredients: list[str]                                # resolved 主成分 (INN); >1 for combos
    is_combo: bool = False
    licenses: list[str] = Field(default_factory=list)     # TFDA 許可證字號 (citation anchors)


class VerifyResponse(BaseModel):
    """驗證結果回應"""
    drugs_analyzed: list[str]
    interactions: list[DrugInteraction]
    summary: str
    risk_level: str  # Canonical enum: Critical, Major, Moderate, Minor, Low, Unknown
    risk_level_label: Optional[str] = None  # Localized display for risk_level
    response_language: Optional[str] = None  # Language used for LLM response (echoed back for frontend debug / analytics)
    disclaimer: str = "For reference only. Does not constitute medical advice. Please consult a qualified healthcare professional."
    query_time_ms: int
    query_id: Optional[str] = None
    # ── ADR 007 T2a structured transparency (ADDITIVE — old clients unaffected).
    #    The same facts stay in `summary` prose (Share answerText / FeedbackBar depend on it);
    #    these fields exist so the UI renders them localized instead of parsing prose.
    tfda_groundings: Optional[list[TfdaGrounding]] = None  # deterministic brand→INN resolutions applied
    verification_status: Optional[str] = None              # "ok" | "deferred_ambiguous_brand" | "failed_no_data"
    deferred_brands: Optional[list[str]] = None            # inputs that caused an ambiguous-brand defer