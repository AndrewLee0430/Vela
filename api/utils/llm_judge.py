"""
LLM as Judge - Answer quality evaluation system

Evaluates LLM-generated medical answers on 5 dimensions:
  Accuracy (35%), Completeness (25%), Relevance (20%),
  Source Support (15%), Safety (5%)
"""

import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI

logger = logging.getLogger("vela")


@dataclass
class Source:
    source_id: str
    content: str


class LLMJudge:
    WEIGHTS = {
        "accuracy":       0.35,
        "completeness":   0.25,
        "relevance":      0.20,
        "source_support": 0.15,
        "safety":         0.05,
    }

    THRESHOLDS = {"high": 80, "medium": 60, "low": 0}

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self._client = client or AsyncOpenAI()

    def _build_prompt(self, query: str, answer: str, sources: List[Source]) -> str:
        sources_text = "\n\n".join(
            f"[Source {i+1}] {s.source_id}:\n{s.content[:250]}..."
            for i, s in enumerate(sources[:5])
        )
        return f"""You are a medical fact-checking expert. Evaluate the quality of the generated answer.

# User Question
{query}

# Generated Answer
{answer}

# Reference Sources
{sources_text}

---

Evaluate each dimension (0-100):

1. **Accuracy** — Are facts consistent with sources? Any contradictions?
2. **Completeness** — Does the answer fully address the question?
3. **Relevance** — Is the answer on-topic?
4. **Source Support** — Is every claim supported by sources? Any hallucinations?
5. **Safety** — Does the answer include appropriate medical disclaimers?

Return ONLY valid JSON (no markdown):
{{
  "scores": {{
    "accuracy": <0-100>,
    "completeness": <0-100>,
    "relevance": <0-100>,
    "source_support": <0-100>,
    "safety": <0-100>
  }},
  "has_hallucination": <true/false>,
  "issues": ["..."],
  "recommendations": ["..."]
}}"""

    async def evaluate(self, query: str, answer: str, sources: List[Source]) -> Dict:
        prompt = self._build_prompt(query, answer, sources)
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a medical fact-checking expert. Respond ONLY with valid JSON."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            # Cost tracking
            try:
                from api.services.cost_tracker import log_api_cost_standalone
                if response.usage:
                    await log_api_cost_standalone(
                        "system", "research/llm_judge", "gpt-4.1-mini",
                        response.usage.prompt_tokens, response.usage.completion_tokens
                    )
            except Exception:
                pass

            content = response.choices[0].message.content.strip()
            # Strip optional markdown fences
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()

            result = json.loads(content)
            scores = result["scores"]
            weighted = round(sum(scores[d] * w for d, w in self.WEIGHTS.items()), 2)
            result["weighted_score"] = weighted
            result["overall_score"]  = round(sum(scores.values()) / len(scores), 2)
            result["quality_level"]  = (
                "high"   if weighted >= self.THRESHOLDS["high"]   else
                "medium" if weighted >= self.THRESHOLDS["medium"] else
                "low"
            )
            logger.info("[LLMJudge] weighted=%.1f quality=%s", weighted, result["quality_level"])
            return result

        except Exception as e:
            logger.error("[LLMJudge] evaluation failed: %s", e)
            return {
                "scores": {d: 50 for d in self.WEIGHTS},
                "weighted_score": 50.0,
                "overall_score":  50.0,
                "quality_level":  "medium",
                "has_hallucination": False,
                "issues": ["Evaluation failed"],
                "recommendations": [],
                "error": str(type(e).__name__),
            }
