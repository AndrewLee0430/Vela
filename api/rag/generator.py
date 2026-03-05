"""
Answer Generator - v2.4
v2.4 改進：
1. RAG 生成升級到 gpt-4.1（更強的文獻整合能力）
2. Fallback 升級到 gpt-4.1-mini
3. Research prompt 加入禁忌症完整分類要求
"""

from typing import List, AsyncGenerator
from openai import OpenAI
from api.models.schemas import (
    RetrievedDocument,
    Citation,
    StreamEvent,
    StreamEventType
)

# 模型設定
RAG_MODEL      = "gpt-4.1"        # RAG 生成：最強，處理多篇矛盾文獻
FALLBACK_MODEL = "gpt-4.1-mini"   # Fallback：平衡品質與成本

ERROR_MESSAGES = {
    "error": (
        "Unable to retrieve information at this time due to a service issue. "
        "Please try again in a moment."
    ),
}

# 每個 query_type 有獨立的 Fallback prompt
# 確保 RAG 找不到文件時，仍根據正確場景回答
FALLBACK_PROMPTS = {
    "research": """You are a clinical AI assistant supporting healthcare professionals.

No retrieved documents are available for this query.
Answer based on standard medical knowledge and current clinical guidelines.

Requirements:
- Be specific: include drug names, dose ranges, mechanisms, and clinical details
- Structure your answer clearly with relevant subheadings
- Include monitoring parameters and clinical warnings where relevant
- Do NOT add any disclaimer at the end — the system will handle that separately

Language: Respond in the same language as the user's question.
If the question is in Traditional Chinese (繁體中文), answer in Traditional Chinese.
""",

    "verify": """You are a clinical pharmacology expert supporting healthcare professionals.

No retrieved documents are available for these drugs.
Analyze the drug interaction based on known pharmacology and standard clinical references.

You MUST cover ALL of the following:
1. Interaction severity: Major / Moderate / Minor — with brief rationale
2. Mechanism: pharmacokinetic (absorption, distribution, metabolism, excretion) or pharmacodynamic
3. Clinical consequences: what will actually happen to the patient
4. Specific warning signs: observable symptoms the clinician should watch for
5. Monitoring parameters: exact labs or clinical checks (e.g. INR, serum levels, renal function)
6. Clinical recommendation: what action to take (avoid, reduce dose, monitor, time separation)

Do NOT give vague answers like "use with caution" without specifying what to monitor and why.
Do NOT add any disclaimer at the end — the system will handle that separately

Language: Respond in the same language as the user's question.
If the question is in Traditional Chinese (繁體中文), answer in Traditional Chinese.
""",

    "document": """You are a clinical assistant helping write patient-friendly visit summaries.

Generate a clear, friendly letter to the patient based on the visit notes provided.

Requirements:
- Use simple, non-technical language the patient can understand
- Include: diagnosis or condition, medications prescribed, how and when to take them
- Include: key lifestyle advice, foods or activities to avoid if relevant
- Include: follow-up plan and what to watch out for
- Do NOT add any disclaimer at the end — the system will handle that separately

Language: Respond in the same language as the visit notes.
If the notes are in Traditional Chinese (繁體中文), write in Traditional Chinese.
"""
}


class AnswerGenerator:

    def __init__(self, model: str = RAG_MODEL):
        self.model = model
        self.client = OpenAI()

    async def generate_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research"
    ) -> AsyncGenerator[StreamEvent, None]:
        if retrieval_status == "error":
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            yield StreamEvent(type=StreamEventType.DONE)
            return

        if not documents:
            async for event in self._generate_fallback_stream(question, query_type):
                yield event
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
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            print(f"❌ Generation error: {e}")
            yield StreamEvent(type=StreamEventType.DONE)

    async def _generate_fallback_stream(
        self,
        question: str,
        query_type: str = "research"
    ) -> AsyncGenerator[StreamEvent, None]:
        system_prompt = FALLBACK_PROMPTS.get(query_type, FALLBACK_PROMPTS["research"])
        try:
            yield StreamEvent(type=StreamEventType.FALLBACK, content="no_literature")

            stream = self.client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
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

            yield StreamEvent(type=StreamEventType.CITATIONS, content=[])
            yield StreamEvent(type=StreamEventType.DONE)

        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            print(f"❌ Fallback generation error: {e}")
            yield StreamEvent(type=StreamEventType.DONE)

    def _get_system_prompt(self, query_type: str = "research") -> str:
        base = """You are a clinical AI assistant supporting healthcare professionals.
Your answers must be evidence-based, precise, and clinically actionable.

Core rules:
- Cite EVERY factual claim using [1], [2] format
- Never make claims beyond what the provided context supports
- Always note if evidence is low-certainty or outdated
- End with a disclaimer in the SAME language as the user's question:
  * English: "⚠️ Clinical decisions require individual patient assessment."
  * Traditional Chinese: "⚠️ 臨床決策需根據個別病患狀況評估。"
  * Japanese: "⚠️ 臨床判断は個々の患者状況に基づいて行う必要があります。"
  * Korean: "⚠️ 임상적 결정은 개별 환자 상황에 따라 이루어져야 합니다。"
  * Thai: "⚠️ การตัดสินใจทางคลินิกต้องอาศัยการประเมินผู้ป่วยเป็นรายบุคคล"
  * Spanish: "⚠️ Las decisiones clínicas requieren una evaluación individual del paciente."
  * For other languages, translate the disclaimer appropriately.

Language: Respond in the same language as the user's question.
If the question is in Traditional Chinese (繁體中文), answer in Traditional Chinese.
"""

        if query_type == "verify":
            return base + """
Drug Interaction specific requirements — you MUST include ALL of the following:

1. **Severity classification**: Major / Moderate / Minor with brief rationale
2. **Mechanism**: Why this interaction occurs (pharmacokinetic or pharmacodynamic)
3. **Dose context**: Distinguish effects by dose where relevant
4. **Clinical warning signs**: List concrete observable symptoms
5. **Monitoring parameters**: Specific labs or clinical checks
6. **Clinical recommendation**: What action to take

Do NOT say "increases bleeding risk" without specifying HOW to detect it clinically.
"""

        if query_type == "research":
            return base + """
MANDATORY STRUCTURE — Every response MUST follow exactly 3 sections.
The entire response — including ALL section headers — must be written in the SAME language as the user's question.

SECTION HEADER TRANSLATION RULE:
Translate these 3 headers into the user's language naturally and professionally.
Do NOT use English headers if the question is not in English.
Examples (use as reference, not hard-coded):
- English:    ## Summary / ## Clinical Notes / ## Evidence
- 繁體中文:   ## 摘要 / ## 臨床備註 / ## 證據強度
- 日本語:     ## まとめ / ## 臨床メモ / ## エビデンス
- 한국어:     ## 요약 / ## 임상 참고사항 / ## 근거 수준
- Español:   ## Resumen / ## Notas Clínicas / ## Evidencia
- Deutsch:   ## Zusammenfassung / ## Klinische Hinweise / ## Evidenz
- For ANY other language: translate the 3 headers appropriately into that language.

---

## [Summary — translated to user's language]
2-3 sentences: direct answer first, then key mechanism.
Put the conclusion FIRST. Do not bury it after background.

---

## [Clinical Notes — translated to user's language]
Cover ALL of the following in natural prose or structured bullets — do NOT use English sub-labels:
- Safety warnings and when NOT to use the drug/treatment
- Key contraindications (cardiac, respiratory, metabolic, drug interactions)
- Specific monitoring parameters with concrete thresholds and frequency
  (e.g. "Check eGFR at baseline; reduce dose if eGFR 30-60; stop if eGFR < 30")
- Do NOT write vague statements like "monitor renal function" — always specify what, when, and threshold.

---

## [Evidence — translated to user's language]
Rate with one of:
- 🟢 Strong — RCT or meta-analysis; major guideline recommends
- 🟡 Moderate — observational study; conditional recommendation
- 🔴 Limited — case report or expert opinion

If evidence predates 2020, note it.
If sources conflict, present both sides.
End with the disclaimer translated into the user's language.
"""

        return base

    def _build_context(self, documents: List[RetrievedDocument]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.content[:2000] + "..." if len(doc.content) > 2000 else doc.content
            year_info = ""
            if hasattr(doc, 'year') and doc.year and doc.year != "Unknown":
                year_info = f" [{doc.year}]"
            context_parts.append(f"[{i}] {doc.title}{year_info}\n{content}")
        return "\n\n".join(context_parts)

    def _build_user_prompt(self, question: str, context: str, query_type: str) -> str:
        extra_instruction = ""
        if query_type == "verify":
            extra_instruction = (
                "\n\nIMPORTANT: You must explicitly cover dose-dependent effects "
                "and list specific clinical warning signs for this interaction."
            )
        elif query_type == "research":
            extra_instruction = (
                "\n\nIMPORTANT: Follow the mandatory 5-section structure: "
                "Direct Answer → Mechanism → Clinical Warnings & Contraindications → Monitoring → Evidence Strength. "
                "Every section is required. Do not skip any section even if the question seems narrow."
            )

        return f"""Reference documents (with publication year):
{context}

Question: {question}{extra_instruction}

Instructions:
1. Answer ONLY based on the provided context
2. Cite every claim with [1], [2], etc.
3. If context is insufficient, state what's missing
4. Be clinically precise

Answer:"""

    async def generate_non_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research"
    ) -> tuple[str, List[Citation]]:
        if retrieval_status == "error":
            return ERROR_MESSAGES["error"], []

        if not documents:
            try:
                system_prompt = FALLBACK_PROMPTS.get(query_type, FALLBACK_PROMPTS["research"])
                completion = self.client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    temperature=0.2,
                    max_tokens=2500
                )
                return completion.choices[0].message.content, []
            except Exception as e:
                print(f"❌ Fallback error: {e}")
                return ERROR_MESSAGES["error"], []

        context = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt = self._build_user_prompt(question, context, query_type)
        citations = [doc.to_citation(citation_id=i + 1) for i, doc in enumerate(documents)]

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