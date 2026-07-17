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

# ── Observability counters (TECH_DEBT [P1] slice 1/2 — MEASUREMENT ONLY) ────────────
# Process-cumulative rerank outcome tallies. Surfaced in logs (WARNING, slice-2: ships
# reliably through Fly log-shipping loss) so the rerank-skip inert-rate (the v200
# source-weighting composite is silently bypassed on a skip) is greppable from Fly logs
# alone — no DB, no metrics backend, no PostHog. These counters NEVER affect which docs
# are returned or their order; they are read-only observability.
#   attempts           = rerank() calls that issued the LLM scoring request (<=2-doc pools
#                        skip the LLM by design and are NOT counted).
#   success            = parsed a valid keyed score set (all n indices present) and reranked.
#   skip_keyed_missing = keyed object valid but NOT every index 0..n-1 present (the slice-1
#                        off-by-one, now STRUCTURALLY detected instead of a length check).
#   skip_keyed_invalid = wrong root / non-array / positional array / duplicate index /
#                        out-of-range index / non-numeric score.
#   skip_json_parse    = model output was not parseable JSON.
#   skip_exception     = the LLM call raised (network/provider) → rerank skipped.
_SKIP_REASONS = ("keyed_missing", "keyed_invalid", "json_parse", "exception")
_RERANK_STATS = {
    "attempts": 0,
    "success": 0,
    **{f"skip_{r}": 0 for r in _SKIP_REASONS},
}


def _rerank_summary() -> str:
    """One-line cumulative summary of rerank observability counters (inert-rate =
    skips / attempts). Read-only — computes a string, mutates nothing."""
    a = _RERANK_STATS["attempts"]
    skips = sum(_RERANK_STATS[f"skip_{r}"] for r in _SKIP_REASONS)
    rate = (skips / a * 100.0) if a else 0.0
    return ("[RERANK_STATS] attempts=%d success=%d skip_keyed_missing=%d skip_keyed_invalid=%d "
            "skip_json_parse=%d skip_exception=%d inert_rate=%.1f%%") % (
        a, _RERANK_STATS["success"], _RERANK_STATS["skip_keyed_missing"],
        _RERANK_STATS["skip_keyed_invalid"], _RERANK_STATS["skip_json_parse"],
        _RERANK_STATS["skip_exception"], rate,
    )


def _rerank_max_tokens(n: int) -> int:
    """Output-token ceiling for the keyed schema, sized to the pool.

    Each entry `{"index": 12, "score": 85}` is ~14 tokens; the `{"scores":[...]}` wrapper is
    ~4. We budget 40 tokens/doc + 200 fixed (≈3x the real cost) so a full pool never truncates
    — the pool is bounded by retriever candidates[:max_results*4] (<=40) and in practice <=~20
    (the probe saw expected=13). Capped at 4096 for safety."""
    return min(4096, 40 * n + 200)


def _parse_keyed_scores(raw: str, n: int):
    """Parse the keyed reranker response into scores aligned BY INDEX.

    Returns (aligned, reason) where:
      - aligned = list[float] of length n (position i = doc i's score, normalized to 0-1) and
        reason == "ok" when EVERY index 0..n-1 is present exactly once with a numeric score;
      - (None, "keyed_missing")  — valid entries but some index absent (the slice-1 off-by-one);
      - (None, "keyed_invalid")  — wrong root / non-array `scores` / non-dict entry / duplicate
                                   index / out-of-range index / bool or non-int index /
                                   non-numeric score (incl. a bare positional array);
      - (None, "json_parse")     — not parseable JSON.

    Pure — no I/O, never raises. NO fabrication/interpolation of a missing score (a partial
    accept would change scoring semantics — a founder-level decision, out of scope for slice 2).
    """
    text = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None, "json_parse"
    if not isinstance(obj, dict):
        return None, "keyed_invalid"
    entries = obj.get("scores")
    if not isinstance(entries, list):
        return None, "keyed_invalid"
    by_index: dict[int, float] = {}
    for e in entries:
        if not isinstance(e, dict):
            return None, "keyed_invalid"
        idx = e.get("index")
        sc = e.get("score")
        # bool is an int subclass in Python — reject it explicitly for both fields.
        if isinstance(idx, bool) or not isinstance(idx, int) or not (0 <= idx < n):
            return None, "keyed_invalid"
        if idx in by_index:
            return None, "keyed_invalid"          # duplicate index
        if isinstance(sc, bool) or not isinstance(sc, (int, float)):
            return None, "keyed_invalid"
        by_index[idx] = float(sc)
    if len(by_index) != n:
        return None, "keyed_missing"              # some index 0..n-1 absent
    return [by_index[i] / 100.0 for i in range(n)], "ok"


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

        n = len(documents)
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

Output ONLY a JSON object of exactly this shape:
{{"scores": [{{"index": 0, "score": 85}}, {{"index": 1, "score": 40}}, ...]}}
Include EXACTLY one entry for EVERY document index from 0 to {n - 1} (there are {n} documents),
each with its 0-100 score. Do not omit, duplicate, or invent an index."""

        try:
            req = CompletionRequest(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical evidence evaluator. Output ONLY a valid JSON object."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=_rerank_max_tokens(n),
                response_format={"type": "json_object"},
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

        except Exception as e:
            # LLM call raised (network/provider). FAIL LOUD + BYPASS: leave score_sink empty
            # so the v200 composite is bypassed (relevance order), NOT run on stale pre-rerank
            # scores (slice-2 fix — consistent with the parse-skip path below).
            _RERANK_STATS["skip_exception"] += 1
            logger.warning("[RERANK_SKIP reason=exception] %s: %s model=%s",
                           type(e).__name__, e, self.model)
            logger.warning(_rerank_summary())
            return documents[:self.top_k]

        # Parse the keyed schema — score attaches to its INDEX (structural alignment). A
        # dropped element is now a detectable missing index, not a silent off-by-one.
        aligned, reason = _parse_keyed_scores(response.content, n)
        if aligned is None:
            _RERANK_STATS[f"skip_{reason}"] += 1
            # FAIL LOUD (CLAUDE.md Rule 18): composite silently bypassed for this query.
            # Marker RERANK_SKIP + reason; raw payload truncated to 500 chars to keep logs sane.
            logger.warning("[RERANK_SKIP reason=%s] expected=%d model=%s raw=%.500s",
                           reason, n, self.model, response.content)
            logger.warning(_rerank_summary())
            return documents[:self.top_k]

        # 把分數寫回文件的 relevance_score（by index），然後排序
        for i, doc in enumerate(documents):
            doc.relevance_score = aligned[i]  # already normalized to 0-1

        reranked = sorted(documents, key=lambda d: d.relevance_score, reverse=True)
        result = reranked[:self.top_k]

        # SHADOW capture (measurement-only): full scored pool in reranked order.
        # doc.relevance_score already holds the reranker score/100 at this point.
        if score_sink is not None:
            score_sink.extend((d, d.relevance_score) for d in reranked)

        _RERANK_STATS["success"] += 1
        logger.info("Reranker: %d -> top %d docs (scores: %s)",
                    n, len(result), [round(s * 100) for s in aligned])
        logger.warning(_rerank_summary())

        return result