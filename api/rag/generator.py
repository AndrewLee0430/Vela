"""
Answer Generator - v2.5
v2.5 改進：
1. 加入統一語言偵測（language_detector.py）
2. 所有路徑（RAG / Fallback / non-stream）明確注入語言指令
3. FALLBACK_PROMPTS 支援所有 10 種語言
4. 偵測不到語言時，不強制注入，讓 system prompt 自然處理
"""

from typing import List, AsyncGenerator
from openai import OpenAI
from api.models.schemas import (
    RetrievedDocument,
    Citation,
    StreamEvent,
    StreamEventType
)
from api.utils.language_detector import detect_language, get_language_instruction

# 模型設定
RAG_MODEL      = "gpt-4.1"
FALLBACK_MODEL = "gpt-4.1-mini"

ERROR_MESSAGES = {
    "error": (
        "Unable to retrieve information at this time due to a service issue. "
        "Please try again in a moment."
    ),
}

FALLBACK_PROMPTS = {
    "research": """You are a clinical AI assistant supporting healthcare professionals.

No retrieved documents are available for this query.
Answer based on standard medical knowledge and current clinical guidelines.

Requirements:
- Be specific: include drug names, dose ranges, mechanisms, and clinical details
- Structure your answer clearly with relevant subheadings
- Include monitoring parameters and clinical warnings where relevant
- Do NOT add any disclaimer at the end — the system will handle that separately

Supported languages: English, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the user's question. Never switch to English unless the input is English.
(An explicit language instruction will also be appended at the end of the user message.)
""",

    "verify": """You are a clinical pharmacology expert supporting healthcare professionals.

No retrieved documents are available for these drugs.
Analyze the drug interaction based on known pharmacology and standard clinical references.

You MUST cover ALL of the following:
1. Interaction severity: Major / Moderate / Minor — with brief rationale
2. Mechanism: pharmacokinetic or pharmacodynamic
3. Clinical consequences: what will actually happen to the patient
4. Specific warning signs: observable symptoms the clinician should watch for
5. Monitoring parameters: exact labs or clinical checks
6. Clinical recommendation: avoid / reduce dose / monitor / time separation

Do NOT give vague answers like "use with caution" without specifying what to monitor and why.
Do NOT add any disclaimer at the end — the system will handle that separately

Supported languages: English, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the user's question. Never switch to English unless the input is English.
(An explicit language instruction will also be appended at the end of the user message.)
""",

    "document": """You are a clinical assistant helping write patient-friendly visit summaries.

Generate a clear, friendly letter to the patient based on the visit notes provided.

Requirements:
- Use simple, non-technical language the patient can understand
- Include: diagnosis or condition, medications prescribed, how and when to take them
- Include: key lifestyle advice, foods or activities to avoid if relevant
- Include: follow-up plan and what to watch out for
- Do NOT add any disclaimer at the end — the system will handle that separately

Supported languages: English, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the visit notes. Never switch to English unless the notes are in English.
(An explicit language instruction will also be appended at the end of the user message.)
"""
}


class AnswerGenerator:

    def __init__(self, model: str = RAG_MODEL):
        self.model  = model
        self.client = OpenAI()

    # ─── Public: streaming ──────────────────────────────────────────────────

    async def generate_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research",
        lang: str = "",
        usage_out: list = None  # 用來回傳 token 使用量給 server.py
    ) -> AsyncGenerator[StreamEvent, None]:

        if retrieval_status == "error":
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            yield StreamEvent(type=StreamEventType.DONE)
            return

        resolved_lang = lang or detect_language(question)

        if not documents:
            async for event in self._generate_fallback_stream(question, query_type, resolved_lang, usage_out):
                yield event
            return

        context       = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt   = self._build_user_prompt(question, context, query_type, resolved_lang)
        citations     = [doc.to_citation(citation_id=i + 1) for i, doc in enumerate(documents)]

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                stream=True,
                stream_options={"include_usage": True},
                temperature=0.2,
                max_tokens=2500
            )
            for chunk in stream:
                # 最後一個 chunk choices 可能是空的（usage chunk）
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.choices[0].delta.content
                    )
                # 最後一個 chunk 包含 usage
                if chunk.usage and usage_out is not None:
                    usage_out.append({
                        "model": self.model,
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens
                    })
            yield StreamEvent(type=StreamEventType.CITATIONS, content=citations)
            yield StreamEvent(type=StreamEventType.DONE)

        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            print(f"❌ Generation error: {e}")
            yield StreamEvent(type=StreamEventType.DONE)

    # ─── Public: non-streaming ───────────────────────────────────────────────

    async def generate_non_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research",
        lang: str = ""
    ) -> tuple[str, List[Citation]]:

        if retrieval_status == "error":
            return ERROR_MESSAGES["error"], []

        resolved_lang = lang or detect_language(question)

        if not documents:
            try:
                system_prompt    = FALLBACK_PROMPTS.get(query_type, FALLBACK_PROMPTS["research"])
                lang_instruction = get_language_instruction(resolved_lang)
                user_content     = f"{question}\n\n{lang_instruction}" if lang_instruction else question

                completion = self.client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_content}
                    ],
                    temperature=0.2,
                    max_tokens=2500
                )
                return completion.choices[0].message.content, []
            except Exception as e:
                print(f"❌ Fallback error: {e}")
                return ERROR_MESSAGES["error"], []

        context       = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt   = self._build_user_prompt(question, context, query_type, resolved_lang)
        citations     = [doc.to_citation(citation_id=i + 1) for i, doc in enumerate(documents)]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500
            )
            return completion.choices[0].message.content, citations
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return ERROR_MESSAGES["error"], citations

    # ─── Private helpers ─────────────────────────────────────────────────────

    async def _generate_fallback_stream(
        self,
        question: str,
        query_type: str = "research",
        lang: str = "en",
        usage_out: list = None
    ) -> AsyncGenerator[StreamEvent, None]:

        system_prompt    = FALLBACK_PROMPTS.get(query_type, FALLBACK_PROMPTS["research"])
        lang_instruction = get_language_instruction(lang)
        user_content     = f"{question}\n\n{lang_instruction}" if lang_instruction else question

        try:
            yield StreamEvent(type=StreamEventType.FALLBACK, content="no_literature")

            stream = self.client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content}
                ],
                stream=True,
                stream_options={"include_usage": True},
                temperature=0.2,
                max_tokens=2500
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.choices[0].delta.content
                    )
                if chunk.usage and usage_out is not None:
                    usage_out.append({
                        "model": FALLBACK_MODEL,
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens
                    })
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
- End with this disclaimer: "⚠️ This information is for reference only and does not constitute medical advice. Please consult a qualified healthcare professional."

Supported languages: English, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: An explicit language instruction will be appended in the user message — follow it exactly.
"""

        if query_type == "verify":
            base += """
Drug Interaction Analysis Rules:
- Always state severity: Major / Moderate / Minor
- Always state mechanism: pharmacokinetic or pharmacodynamic
- List specific clinical consequences (not vague "use with caution")
- Specify exact monitoring parameters with thresholds
- Give clear clinical recommendation (avoid / reduce dose / monitor / time separation)
"""
        elif query_type == "research":
            base += """
## [Summary — translated to user's language]
2-3 sentences: direct answer first, then key mechanism.
Put the conclusion FIRST. Do not bury it after background.

---

## [Clinical Notes — translated to user's language]
Cover ALL of the following in natural prose or structured bullets:
- Safety warnings and when NOT to use the drug/treatment
- Key contraindications (cardiac, respiratory, metabolic, drug interactions)
- Specific monitoring parameters with concrete thresholds and frequency
  (e.g. "Check eGFR at baseline; reduce dose if eGFR 30-60; stop if eGFR < 30")

---

## [Evidence — translated to user's language]
Rate with one of:
- 🟢 Strong — RCT or meta-analysis; major guideline recommends
- 🟡 Moderate — observational study; conditional recommendation
- 🔴 Limited — case report or expert opinion

If evidence predates 2020, note it. If sources conflict, present both sides.
End with the disclaimer translated into the user's language.
"""
        return base

    def _build_context(self, documents: List[RetrievedDocument]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content   = doc.content[:2000] + "..." if len(doc.content) > 2000 else doc.content
            year_info = ""
            if hasattr(doc, 'year') and doc.year and doc.year != "Unknown":
                year_info = f" [{doc.year}]"
            context_parts.append(f"[{i}] {doc.title}{year_info}\n{content}")
        return "\n\n".join(context_parts)

    def _build_user_prompt(
        self,
        question: str,
        context: str,
        query_type: str,
        lang: str = "en"
    ) -> str:
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
                "Every section is required."
            )

        lang_instruction = get_language_instruction(lang)
        lang_line        = f"\n\n{lang_instruction}" if lang_instruction else ""

        return f"""Reference documents (with publication year):
{context}

Question: {question}{extra_instruction}

Instructions:
1. Answer ONLY based on the provided context
2. Cite every claim with [1], [2], etc.
3. If context is insufficient, state what's missing
4. Be clinically precise{lang_line}

Answer:"""