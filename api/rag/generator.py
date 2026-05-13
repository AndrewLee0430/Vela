"""
Answer Generator - v2.5
v2.5 改進：
1. 加入統一語言偵測（language_detector.py）
2. 所有路徑（RAG / Fallback / non-stream）明確注入語言指令
3. FALLBACK_PROMPTS 支援所有 10 種語言
4. 偵測不到語言時，不強制注入，讓 system prompt 自然處理

§2.1 PHASE D (PRD v1.4 + ADR 005): wired through api.providers via
get_generator_provider(). Primary model + fallback model both come
from the binding (GENERATOR_PROVIDER / GENERATOR_MODEL /
GENERATOR_FALLBACK_MODEL env vars). Module-level RAG_MODEL +
FALLBACK_MODEL constants removed.
"""

import logging
from typing import List, AsyncGenerator, Optional

from api.models.schemas import (
    RetrievedDocument,
    Citation,
    StreamEvent,
    StreamEventType
)
from api.utils.language_detector import detect_language, get_language_instruction
from api.providers import get_generator_provider
from api.providers.base import CompletionRequest

logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    "error": (
        "Unable to retrieve information at this time due to a service issue. "
        "Please try again in a moment."
    ),
}

FALLBACK_PROMPTS = {
    # Updated 2026-04-20: added Chinese variant handling per 2.9 learnings (see PRD § 2.9 post-release).
    # Applied to "research" key only; "verify" and "document" keys below are dead code (tracked as tech debt).
    "research": """You are a clinical AI assistant supporting healthcare professionals.

No retrieved documents are available for this query.
Answer based on standard medical knowledge and current clinical guidelines.

Requirements:
- Be specific: include drug names, dose ranges, mechanisms, and clinical details
- Structure your answer clearly with relevant subheadings
- Include monitoring parameters and clinical warnings where relevant
- Do NOT add any disclaimer at the end — the system will handle that separately

Supported languages: English, 繁體中文 (zh-TW), 简体中文 (zh-CN), 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the user's question. Never switch to English unless the input is English.
(An explicit language instruction will also be appended at the end of the user message.)

Chinese variant handling (when output language is zh-CN or zh-TW):

**For zh-CN (Simplified Chinese, Mainland China / Singapore medical context):**
- Use Simplified Chinese characters (简体字) EXCLUSIVELY
- Do NOT use Traditional Chinese characters like 嚴/導/聯/時/監/評/狀/覆/與/證
- Use simplified equivalents: 严/导/联/时/监/评/状/覆/与/证
- Medical terminology should follow PRC / NMPA conventions (药物相互作用, 不良反应, 随访)

**For zh-TW (Traditional Chinese, Taiwan medical context):**
- Use Traditional Chinese characters (繁體字) as used in Taiwan
- Medical terminology should follow Taiwan TFDA conventions (藥物交互作用, 不良反應, 追蹤)

If output language is zh-CN but you produce Traditional Chinese characters, the output is INCORRECT. Always verify character form matches the specified variant before returning.
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

Supported languages: English, 繁體中文 (zh-TW), 简体中文 (zh-CN), 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
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

Supported languages: English, 繁體中文 (zh-TW), 简体中文 (zh-CN), 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the visit notes. Never switch to English unless the notes are in English.
(An explicit language instruction will also be appended at the end of the user message.)
"""
}


class AnswerGenerator:

    def __init__(self, model: Optional[str] = None):
        binding = get_generator_provider()
        self._provider = binding.provider
        # Explicit constructor model wins over factory default (test-friendly).
        self.model = model or binding.model
        self._fallback_model = binding.fallback_model or binding.model

    # ─── Public: streaming ──────────────────────────────────────────────────

    async def generate_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research",
        lang: str = "",
        usage_out: list = None,  # 用來回傳 token 使用量給 server.py
        model_override: Optional[str] = None  # Decision 001 v0.3 A8 — L0 uses gpt-4.1-mini
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

        effective_model = model_override or self.model
        context       = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt   = self._build_user_prompt(question, context, query_type, resolved_lang)
        citations     = [doc.to_citation(citation_id=i + 1) for i, doc in enumerate(documents)]

        try:
            req = CompletionRequest(
                model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500,
            )
            async for chunk in self._provider.stream(req):
                if chunk.delta:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.delta
                    )
                if chunk.usage and usage_out is not None:
                    usage_out.append({
                        "model": effective_model,
                        "prompt_tokens": chunk.usage["prompt_tokens"],
                        "completion_tokens": chunk.usage["completion_tokens"]
                    })
            yield StreamEvent(type=StreamEventType.CITATIONS, content=citations)
            yield StreamEvent(type=StreamEventType.DONE)

        except Exception as e:
            # Broad Exception catches VelaError (provider errors) + anything
            # else. Preserves fail-CLOSED behavior: stream emits error event.
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            logger.error("Generation error: %s", e, exc_info=True)
            yield StreamEvent(type=StreamEventType.DONE)

    # ─── Public: non-streaming ───────────────────────────────────────────────

    async def generate_non_stream(
        self,
        question: str,
        documents: List[RetrievedDocument],
        retrieval_status: str = "ok",
        query_type: str = "research",
        lang: str = "",
        model_override: Optional[str] = None  # Decision 001 v0.3 A8 — L0 uses gpt-4.1-mini
    ) -> tuple[str, List[Citation]]:

        if retrieval_status == "error":
            return ERROR_MESSAGES["error"], []

        resolved_lang = lang or detect_language(question)

        if not documents:
            try:
                system_prompt    = FALLBACK_PROMPTS.get(query_type, FALLBACK_PROMPTS["research"])
                lang_instruction = get_language_instruction(resolved_lang)
                user_content     = f"{question}\n\n{lang_instruction}" if lang_instruction else question

                req = CompletionRequest(
                    model=self._fallback_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_content}
                    ],
                    temperature=0.2,
                    max_tokens=2500,
                )
                completion = await self._provider.complete(req)
                return completion.content, []
            except Exception as e:
                logger.error("Fallback generation error (non-stream): %s", e, exc_info=True)
                return ERROR_MESSAGES["error"], []

        effective_model = model_override or self.model
        context       = self._build_context(documents)
        system_prompt = self._get_system_prompt(query_type)
        user_prompt   = self._build_user_prompt(question, context, query_type, resolved_lang)
        citations     = [doc.to_citation(citation_id=i + 1) for i, doc in enumerate(documents)]

        try:
            req = CompletionRequest(
                model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500,
            )
            completion = await self._provider.complete(req)
            return completion.content, citations
        except Exception as e:
            logger.error("Generation error (non-stream): %s", e, exc_info=True)
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

            req = CompletionRequest(
                model=self._fallback_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content}
                ],
                temperature=0.2,
                max_tokens=2500,
            )
            async for chunk in self._provider.stream(req):
                if chunk.delta:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.delta
                    )
                if chunk.usage and usage_out is not None:
                    usage_out.append({
                        "model": self._fallback_model,
                        "prompt_tokens": chunk.usage["prompt_tokens"],
                        "completion_tokens": chunk.usage["completion_tokens"]
                    })
            yield StreamEvent(type=StreamEventType.CITATIONS, content=[])
            yield StreamEvent(type=StreamEventType.DONE)

        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=ERROR_MESSAGES["error"])
            logger.error("Fallback generation error: %s", e, exc_info=True)
            yield StreamEvent(type=StreamEventType.DONE)

    # Updated 2026-04-20: added Chinese variant handling per 2.9 learnings (see PRD § 2.9 post-release)
    def _get_system_prompt(self, query_type: str = "research") -> str:
        base = """You are a clinical AI assistant supporting healthcare professionals.
Your answers must be evidence-based, precise, and clinically actionable.

Core rules:
- Cite EVERY factual claim using [1], [2] format
- Never make claims beyond what the provided context supports
- Always note if evidence is low-certainty or outdated
- Do NOT add any disclaimer at the end — the system will handle that separately

Supported languages: English, 繁體中文 (zh-TW), 简体中文 (zh-CN), 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: An explicit language instruction will be appended in the user message — follow it exactly.

Chinese variant handling (when output language is zh-CN or zh-TW):

**For zh-CN (Simplified Chinese, Mainland China / Singapore medical context):**
- Use Simplified Chinese characters (简体字) EXCLUSIVELY
- Do NOT use Traditional Chinese characters like 嚴/導/聯/時/監/評/狀/覆/與/證
- Use simplified equivalents: 严/导/联/时/监/评/状/覆/与/证
- Medical terminology should follow PRC / NMPA conventions (药物相互作用, 不良反应, 随访)

**For zh-TW (Traditional Chinese, Taiwan medical context):**
- Use Traditional Chinese characters (繁體字) as used in Taiwan
- Medical terminology should follow Taiwan TFDA conventions (藥物交互作用, 不良反應, 追蹤)

If output language is zh-CN but you produce Traditional Chinese characters, the output is INCORRECT. Always verify character form matches the specified variant before returning.
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
Place an evidence strength emoji (🟢, 🟡, or 🔴) directly in EACH section header after the section name.
Judge each section independently:
- 🟢 Strong — supported by RCT, meta-analysis, or major guideline
- 🟡 Moderate — supported by observational study or conditional recommendation
- 🔴 Limited — based on case report, expert opinion, or insufficient retrieved evidence

## [Summary 🟢 — translated to user's language]
2-3 sentences: direct answer first, then key mechanism.
Put the conclusion FIRST. Do not bury it after background.

---

## [Clinical Notes 🟡 — translated to user's language]
Cover ALL of the following in natural prose or structured bullets:
- Safety warnings and when NOT to use the drug/treatment
- Key contraindications (cardiac, respiratory, metabolic, drug interactions)
- Specific monitoring parameters with concrete thresholds and frequency
  (e.g. "Check eGFR at baseline; reduce dose if eGFR 30-60; stop if eGFR < 30")

(The emoji shown above is an example — choose the correct level for the actual content.)

Do NOT include a separate Evidence section. Do NOT add any disclaimer at the end — the system will handle that separately.
If evidence predates 2020, note it inline. If sources conflict, present both sides.
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
                "\n\nIMPORTANT: Follow the mandatory 2-section structure: "
                "Summary → Clinical Notes. "
                "Place evidence strength emoji (🟢/🟡/🔴) in each section header. "
                "Do NOT include a separate Evidence section."
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