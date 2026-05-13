"""
Reranker - v1.0
用 LLM 對召回文件重新評分排序

原理：
向量相似度只看「語意相近」，不看「是否真的能回答這個問題」
Reranker 讓 LLM 直接判斷每份文件對這個 query 的有用程度 (0-100)
排序後只保留最高分的 top_k 份文件給 Generator

位置：在 _filter_by_relevance 之後、Generator 之前

§2.1 PHASE C (PRD v1.4 + ADR 005): wired through api.providers via
get_reranker_provider(). Model + provider configurable via
RERANKER_PROVIDER / RERANKER_MODEL env vars.
"""

import logging
import json

from api.models.schemas import RetrievedDocument
from api.providers import get_reranker_provider
from api.providers.base import CompletionRequest

logger = logging.getLogger(__name__)


class Reranker:
    """
    LLM-based Reranker

    流程：
    1. 把所有候選文件和 query 一起送給 LLM
    2. LLM 對每份文件打 0-100 的相關性分數
    3. 按分數重新排序，只保留 top_k
    """

    def __init__(self, top_k: int = 5):
        binding = get_reranker_provider()
        self._provider = binding.provider
        self.model = binding.model
        self.top_k = top_k

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        """
        對文件重新評分並排序

        Args:
            query: 原始使用者問題
            documents: 已經過相關性過濾的候選文件

        Returns:
            重新排序後的 top_k 份文件
        """
        if not documents:
            return []

        # 文件太少不需要 rerank
        if len(documents) <= 2:
            return documents

        # 建立送給 GPT 的文件摘要
        doc_summaries = []
        for i, doc in enumerate(documents):
            preview = doc.content[:400].replace('\n', ' ')
            doc_summaries.append(f"[{i}] Title: {doc.title}\nContent: {preview}")

        docs_text = "\n\n".join(doc_summaries)

        prompt = f"""You are a medical evidence evaluator.

Given a clinical question and a list of retrieved documents, score each document's relevance 
to answering the question on a scale of 0-100.

Scoring criteria:
- 90-100: Directly answers the question with specific clinical data
- 70-89:  Highly relevant, contains useful related information  
- 50-69:  Partially relevant, tangentially related
- 0-49:   Not useful for answering this question

Clinical question: {query}

Retrieved documents:
{docs_text}

Output ONLY a JSON array with scores in order, e.g.: [85, 40, 92, 60, 75]
One score per document, same order as input."""

        try:
            req = CompletionRequest(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical evidence evaluator. Output ONLY valid JSON arrays."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200,
            )
            response = await self._provider.complete(req)

            # Cost tracking — use self.model so future Groq swap stays accurate.
            try:
                from api.services.cost_tracker import log_api_cost_standalone
                if response.input_tokens or response.output_tokens:
                    await log_api_cost_standalone(
                        "system", "research/rerank", self.model,
                        response.input_tokens, response.output_tokens
                    )
            except Exception:
                pass

            raw = response.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            scores = json.loads(raw)

            if not isinstance(scores, list) or len(scores) != len(documents):
                logger.warning("Reranker: unexpected scores format, skipping rerank")
                return documents[:self.top_k]

            # 把分數寫回文件的 relevance_score，然後排序
            for doc, score in zip(documents, scores):
                doc.relevance_score = score / 100.0  # 統一到 0-1

            reranked = sorted(documents, key=lambda d: d.relevance_score, reverse=True)
            result = reranked[:self.top_k]

            logger.info("Reranker: %d -> top %d docs (scores: %s)",
                        len(documents), len(result), [round(s) for s in scores])

            return result

        except Exception as e:
            logger.warning("Reranker failed: %s, returning original order", e)
            return documents[:self.top_k]