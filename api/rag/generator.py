"""
Answer Generator - v2.1
使用 LLM 基於檢索到的文件生成答案，並支援串流輸出

v2.1 改進：
1. 錯誤分層 - 區分「無結果」/「不相關」/「API 錯誤」給出不同提示
2. 強化 system prompt - 要求劑量區分、出血徵兆、時效性聲明
3. Verify 專用 prompt - 藥物交互作用回覆更完整
4. 時效性標記 - 自動標注文獻年份，提示用戶確認最新指引
"""

from typing import List, AsyncGenerator
from openai import OpenAI
from api.models.schemas import (
    RetrievedDocument,
    Citation,
    StreamEvent,
    StreamEventType
)

# 不同狀態的友善錯誤訊息
ERROR_MESSAGES = {
    "no_results": (
        "No relevant literature found for this query. "
        "Try rephrasing with more specific drug names or clinical terms. "
        "You may also consult UpToDate or clinical guidelines directly."
    ),
    "irrelevant": (
        "The retrieved documents do not appear to directly address this question. "
        "The available literature may not cover this specific topic, "
        "or the query may need to be more specific. "
        "Consider consulting primary clinical references."
    ),
    "error": (
        "Unable to retrieve information at this time due to a service issue. "
        "Please try again in a moment, or consult clinical guidelines directly."
    ),
}


class AnswerGenerator:
    """
    答案生成器 v2.1

    功能：
    1. 基於已驗證的相關文件生成答案
    2. 支援串流輸出（SSE）
    3. 自動標註引用來源
    4. 區分錯誤類型給出對應提示
    5. 強制要求臨床安全資訊（劑量、徵兆）
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI()

    # ─────────────────────────────────────────────
    # 串流生成（主要介面）
    # ─────────────────────────────────────────────

    async def generate_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research"  # "research" | "verify" | "document"
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        串流生成答案

        Args:
            question: 使用者問題
            documents: 已通過相關性驗證的文件
            retrieval_status: "ok" | "no_results" | "irrelevant" | "error"
            query_type: 查詢類型，影響 prompt 策略
        """
        # 非 ok 狀態：直接回傳對應錯誤訊息
        if retrieval_status != "ok" or not documents:
            error_msg = ERROR_MESSAGES.get(retrieval_status, ERROR_MESSAGES["error"])
            yield StreamEvent(type=StreamEventType.ERROR, content=error_msg)
            yield StreamEvent(type=StreamEventType.DONE)
            return

        context = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt = self._build_user_prompt(question, context, query_type)

        citations = [
            doc.to_citation(citation_id=i + 1)
            for i, doc in enumerate(documents)
        ]

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True,
                temperature=0.2,
                max_tokens=2500
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.choices[0].delta.content
                    )

            yield StreamEvent(type=StreamEventType.CITATIONS, content=citations)
            yield StreamEvent(type=StreamEventType.DONE)

        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=ERROR_MESSAGES["error"]
            )
            print(f"❌ Generation error: {e}")
            yield StreamEvent(type=StreamEventType.DONE)

    # ─────────────────────────────────────────────
    # System Prompts
    # ─────────────────────────────────────────────

    def _get_system_prompt(self, query_type: str = "research") -> str:
        """
        根據查詢類型選擇對應 system prompt
        """
        base = """You are a clinical AI assistant supporting healthcare professionals.
Your answers must be evidence-based, precise, and clinically actionable.

Core rules:
- Cite EVERY factual claim using [1], [2] format
- Never make claims beyond what the provided context supports
- Always note if evidence is low-certainty or outdated
- End with: "⚠️ Clinical decisions require individual patient assessment."

Language: Respond in the same language as the user's question.
If the question is in Traditional Chinese (繁體中文), answer in Traditional Chinese.
"""

        if query_type == "verify":
            return base + """
Drug Interaction specific requirements — you MUST include ALL of the following:

1. **Severity classification**: Major / Moderate / Minor with brief rationale
2. **Mechanism**: Why this interaction occurs (pharmacokinetic or pharmacodynamic)
3. **Dose context**: Distinguish effects by dose where relevant
   - Example: low-dose aspirin (75–100mg) vs. analgesic-dose aspirin (≥325mg) have very different risk profiles when combined with anticoagulants
4. **Clinical warning signs**: List concrete observable symptoms the patient/clinician should watch for
   - Example for bleeding risk: gum bleeding, black/tarry stools, unexplained bruising, prolonged bleeding from cuts, blood in urine
5. **Monitoring parameters**: Specific labs or clinical checks (e.g., INR range, renal function)
6. **Clinical recommendation**: What action to take (avoid / monitor / adjust dose / use alternative)

Do NOT say "increases bleeding risk" without specifying HOW to detect it clinically.
"""

        if query_type == "research":
            return base + """
Research query requirements:

1. **Answer the specific question directly** — do not summarize tangentially related topics
2. **Evidence hierarchy**: Note study type (RCT, meta-analysis, cohort, etc.) when relevant
3. **Recency flag**: If the cited evidence is from before 2020, explicitly state:
   "⚠️ Note: This evidence predates 2020. More recent guidelines may differ."
4. **Conflicting evidence**: If sources disagree, present both sides fairly
5. **Clinical applicability**: Note patient population studied vs. general applicability
"""

        return base

    # ─────────────────────────────────────────────
    # Prompt 建構
    # ─────────────────────────────────────────────

    def _build_context(self, documents: List[RetrievedDocument]) -> str:
        """將文件列表轉換為帶年份標記的 context"""
        context_parts = []

        for i, doc in enumerate(documents, 1):
            content = doc.content[:2000] + "..." if len(doc.content) > 2000 else doc.content

            # 加入年份資訊（讓 LLM 能判斷時效性）
            year_info = ""
            if hasattr(doc, 'year') and doc.year and doc.year != "Unknown":
                year_info = f" [{doc.year}]"

            context_parts.append(
                f"[{i}] {doc.title}{year_info}\n{content}"
            )

        return "\n\n".join(context_parts)

    def _build_user_prompt(self, question: str, context: str, query_type: str) -> str:
        """建構 user prompt"""
        extra_instruction = ""
        if query_type == "verify":
            extra_instruction = (
                "\n\nIMPORTANT: You must explicitly cover dose-dependent effects "
                "and list specific clinical warning signs for this interaction. "
                "If the source material mentions dose distinctions, highlight them."
            )
        elif query_type == "research":
            extra_instruction = (
                "\n\nIMPORTANT: If any cited evidence is from before 2020, "
                "flag it explicitly. Do not state clinical effects are 'unclear' "
                "if the context contains evidence supporting a conclusion."
            )

        return f"""Reference documents (with publication year):
{context}

Question: {question}{extra_instruction}

Instructions:
1. Answer ONLY based on the provided context
2. Cite every claim with [1], [2], etc.
3. If context is insufficient for any part of the answer, state what's missing
4. Be clinically precise

Answer:"""

    # ─────────────────────────────────────────────
    # 非串流版本
    # ─────────────────────────────────────────────

    async def generate_non_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research"
    ) -> tuple[str, List[Citation]]:
        """非串流生成（用於 Judge 評估等需要完整答案的場景）"""
        if retrieval_status != "ok" or not documents:
            error_msg = ERROR_MESSAGES.get(retrieval_status, ERROR_MESSAGES["error"])
            return error_msg, []

        context = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt = self._build_user_prompt(question, context, query_type)

        citations = [
            doc.to_citation(citation_id=i + 1)
            for i, doc in enumerate(documents)
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500
            )
            return completion.choices[0].message.content, citations

        except Exception as e:
            print(f"❌ Generation error: {e}")
            return ERROR_MESSAGES["error"], citations