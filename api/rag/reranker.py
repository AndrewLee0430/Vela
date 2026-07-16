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

# ── Observability counters (TECH_DEBT [P1] slice 1 — MEASUREMENT ONLY) ──────────────
# Process-cumulative rerank outcome tallies. Surfaced in logs so the rerank-skip
# inert-rate (the v200 source-weighting composite is silently bypassed on a skip) is
# greppable from Fly logs alone — no DB, no metrics backend, no PostHog. These counters
# NEVER affect which docs are returned or their order; they are read-only observability.
#   attempts           = rerank() calls that actually issued the LLM scoring request
#                        (<=2-doc pools skip the LLM by design and are NOT counted, so
#                        the denominator matches the probe's 31.9% = skips/attempts).
#   success            = parsed a valid same-length score array and reranked.
#   skip_format_reject = LLM returned a non-list or a wrong-length array (the deterministic
#                        off-by-one at pool >=6) → rerank skipped, composite bypassed.
#   skip_exception     = the LLM call / JSON parse raised → rerank skipped.
_RERANK_STATS = {
    "attempts": 0,
    "success": 0,
    "skip_format_reject": 0,
    "skip_exception": 0,
}


def _rerank_summary() -> str:
    """One-line cumulative summary of rerank observability counters (inert-rate =
    skips / attempts). Read-only — computes a string, mutates nothing."""
    a = _RERANK_STATS["attempts"]
    skips = _RERANK_STATS["skip_format_reject"] + _RERANK_STATS["skip_exception"]
    rate = (skips / a * 100.0) if a else 0.0
    return ("[RERANK_STATS] attempts=%d success=%d skip_format_reject=%d "
            "skip_exception=%d inert_rate=%.1f%%") % (
        a, _RERANK_STATS["success"], _RERANK_STATS["skip_format_reject"],
        _RERANK_STATS["skip_exception"], rate,
    )


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
        score_sink: list | None = None,
    ) -> list[RetrievedDocument]:
        """
        對文件重新評分並排序

        Args:
            query: 原始使用者問題
            documents: 已經過相關性過濾的候選文件
            score_sink: OPTIONAL measurement-only out-param. When a list is passed, it
                is populated with the FULL scored candidate pool as [(doc, score_0_1)]
                in reranked order — for the source-weighting SHADOW. Purely additive:
                the returned top_k and every doc.relevance_score are byte-identical
                whether or not a sink is provided.

        Returns:
            重新排序後的 top_k 份文件
        """
        if not documents:
            return []

        # 文件太少不需要 rerank
        if len(documents) <= 2:
            if score_sink is not None:
                score_sink.extend((d, d.relevance_score) for d in documents)
            return documents

        # Observability: this call will issue the LLM scoring request (past the small-pool
        # guard). Count it as an attempt — the denominator of the inert-rate.
        _RERANK_STATS["attempts"] += 1

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
                _RERANK_STATS["skip_format_reject"] += 1
                received = len(scores) if isinstance(scores, list) else f"non-list({type(scores).__name__})"
                # FAIL LOUD (CLAUDE.md Rule 18): the composite is now silently bypassed for
                # this query. Marker RERANK_SKIP + reason so Fly log search / future alerting
                # can grep it; raw payload truncated to 500 chars to keep logs sane.
                logger.warning(
                    "[RERANK_SKIP reason=format_reject] expected=%d received=%s model=%s raw=%.500s",
                    len(documents), received, self.model, response.content,
                )
                logger.info(_rerank_summary())
                return documents[:self.top_k]

            # 把分數寫回文件的 relevance_score，然後排序
            for doc, score in zip(documents, scores):
                doc.relevance_score = score / 100.0  # 統一到 0-1

            reranked = sorted(documents, key=lambda d: d.relevance_score, reverse=True)
            result = reranked[:self.top_k]

            # SHADOW capture (measurement-only): full scored pool in reranked order.
            # doc.relevance_score already holds the reranker score/100 at this point.
            if score_sink is not None:
                score_sink.extend((d, d.relevance_score) for d in reranked)

            _RERANK_STATS["success"] += 1
            logger.info("Reranker: %d -> top %d docs (scores: %s)",
                        len(documents), len(result), [round(s) for s in scores])
            logger.info(_rerank_summary())

            return result

        except Exception as e:
            _RERANK_STATS["skip_exception"] += 1
            # FAIL LOUD: labeled RERANK_SKIP marker (distinct reason from format_reject —
            # do not merge distinct causes). Note the composite is NOT bypassed here: the
            # sink is populated below with the pre-rerank score, so activation still runs
            # (on stale scores — a slice-2 concern, not this observability slice).
            logger.warning("[RERANK_SKIP reason=exception] %s: %s model=%s",
                           type(e).__name__, e, self.model)
            logger.info(_rerank_summary())
            if score_sink is not None:
                score_sink.extend((d, d.relevance_score) for d in documents[:self.top_k])
            return documents[:self.top_k]