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
    severity: str  # Critical, Major, Moderate, Minor, Unknown
    description: str
    mechanism: Optional[str] = None
    clinical_recommendation: str
    source: str = "FDA Label / AI Analysis"
    source_url: Optional[str] = None  # ✅ 新增：FDA 原文链接


class VerifyResponse(BaseModel):
    """驗證結果回應"""
    drugs_analyzed: list[str]
    interactions: list[DrugInteraction]
    summary: str
    risk_level: str  # High, Moderate, Low
    disclaimer: str = "此資訊僅供參考，不構成醫療建議。請諮詢專業醫療人員。"
    query_time_ms: int