"""
Hybrid Retriever - v2.2
混合檢索器：結合本地向量資料庫、PubMed、FDA API

v2.2 新增：
1. Query Rewriting - 將口語/非英文查詢改寫為 3 個精確醫學術語查詢，並行檢索
2. 其餘邏輯（去重、年份加權、相關性驗證）完全不變

§2.1 PHASE C (PRD v1.4 + ADR 005): all 5 LLM call sites (query rewrite,
translate fallback, relevance filter, 2 cost-logs) wired through
api.providers via get_lightweight_provider(). Model + provider configurable
via LIGHTWEIGHT_PROVIDER / LIGHTWEIGHT_MODEL env vars.
PHASE B fix at _search_local() preserved (VectorStore.search now async).
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel
from api.database.vector_store import get_vector_store, get_tfda_store, get_dailymed_store
from api.data_sources.pubmed import PubMedClient
from api.data_sources.fda import FDAClient
from api.rag.reranker import Reranker
from api.providers import get_lightweight_provider
from api.providers.base import CompletionRequest

logger = logging.getLogger(__name__)

# 相關性過濾門檻
RELEVANCE_THRESHOLD = 0.45

# 年份加權
YEAR_BOOST = {0: 0.10, 1: 0.08, 2: 0.06, 3: 0.04, 4: 0.02}

# ── Official-label SAFETY-section exemption (TECH_DEBT [P1] recall-miss surface iii) ──
# LOINC codes for the 4 official-label (DailyMed) SAFETY sections that are EXEMPT from the
# LLM relevance filter's drop: a section that WAS retrieved (cosine ≥ the store threshold)
# but the filter would drop is RE-ADDED. ADDITIVE ONLY — never drops a kept doc, never
# reorders/rescoves. Descriptive sections (34067-9 indications / 34068-7 dosage) are NOT
# exempt. Founder-locked whitelist (2026-07-20); matches the fly-206 danger-path SAFETY set.
_SAFETY_SECTION_WHITELIST = {
    "34073-7": "Drug Interactions",
    "34070-3": "Contraindications",
    "43685-7": "Warnings",
    "34066-1": "Boxed Warning",
}


def _is_whitelisted_safety_section(doc) -> bool:
    """True iff `doc` is an official-label per-section SAFETY doc whose LOINC is whitelisted.
    Requires an official source_type AND a `…#{loinc}` source_id — FDA whole-labels (no
    LOINC) and non-official sources return False."""
    st = str(getattr(doc.source_type, "value", doc.source_type) or "").lower()
    if st not in ("dailymed", "fda"):
        return False
    sid = doc.source_id or ""
    if "#" not in sid:
        return False
    loinc = sid.split("#", 1)[1].split("~", 1)[0]
    return loinc in _SAFETY_SECTION_WHITELIST


def _cut_exemption(candidates, unique_docs):
    """Lever-2 (recall-miss [P1]): re-add any RETRIEVED whitelisted official-label SAFETY
    section that the candidates[:max_results*4] cut dropped. ADDITIVE — appends only sections
    BELOW the cut (`not in cut_ids`); never drops, reorders, or displaces a survived candidate.
    Mirrors the surface-(iii) filter-exemption one stage earlier (the candidate cut)."""
    cut_ids = {d.source_id for d in candidates}
    exempted = [d for d in unique_docs
                if d.source_id not in cut_ids and _is_whitelisted_safety_section(d)]
    if not exempted:
        return candidates
    logger.info("[CutExempt] re-added %d whitelisted safety section(s) dropped by the "
                "candidate cut: %s", len(exempted), [d.source_id for d in exempted])
    return candidates + exempted


class HybridRetriever:
    """
    混合檢索器 v2.2

    檢索流程：
    1. Query Rewriting（任何語言/口語 → 3 個精確醫學術語查詢）
    2. 並行檢索（每個 query × 每個來源）
    3. 去重 + 年份加權
    4. 相關性驗證
    5. Rerank
    6. 回傳最相關文件
    """

    def __init__(
        self,
        local_threshold: float = 0.6,
        # ⛔ DEFAULT FLIPPED TO False 2026-07-29 (c1) — the local drug corpus is deprecated.
        # WHY THE DEFAULT AND NOT JUST THE SERVER: 9 measurement harnesses construct
        # `HybridRetriever()` with no arguments (dailymed_danger_path_verify, the source-weight
        # evals, the recall probes, …). While the server also passed True those harnesses
        # matched production by accident; the moment production stopped using local they would
        # have kept measuring a DEAD SOURCE and silently reported on a config that no longer
        # ships. Caught exactly that way: the first danger-path re-gate for this ship logged
        # "Vector store loaded: 690 documents" and was therefore invalid.
        # Call sites that genuinely want the corpus (tests/test_cut_exemption.py,
        # tests/test_source_weight_*.py) pass enable_local=True explicitly and are unaffected.
        enable_local: bool = False,
        enable_pubmed: bool = True,
        enable_fda: bool = True,
        enable_tfda: bool = True,
        enable_dailymed: bool = True
    ):
        self.local_threshold = local_threshold
        self.enable_local = enable_local
        self.enable_pubmed = enable_pubmed
        self.enable_fda = enable_fda
        self.enable_tfda = enable_tfda
        self.enable_dailymed = enable_dailymed

        self.vector_store = get_vector_store() if enable_local else None
        self.pubmed = PubMedClient() if enable_pubmed else None
        self.fda = FDAClient() if enable_fda else None
        # ADR 007 grounding-lite: separate bounded TFDA 核准適應症 corpus (its own store, its
        # own retrieval budget — competes in the SAME relevance-filter + LLM reranker, no
        # source-weighting). Fail-soft: missing index → empty store → contributes nothing.
        self.tfda_store = get_tfda_store() if enable_tfda else None
        # B-2: DailyMed US-label PER-SECTION corpus (Research 5th source, ADR 004/007
        # ingest-and-cite). Same pattern as tfda_store — its own bounded vector store,
        # competes in the SAME relevance-filter + reranker; source-weighting gives label
        # sources Tier-2 ×1.5. Fail-soft: missing index → empty store → contributes nothing.
        self.dailymed_store = get_dailymed_store() if enable_dailymed else None
        binding = get_lightweight_provider()
        self._provider = binding.provider
        self._model = binding.model
        self.reranker = Reranker(top_k=8)

    # ─────────────────────────────────────────────
    # 公開介面
    # ─────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        max_results: int = 5,
        source_filter: Optional[list[SourceType]] = None,
        on_stage: Optional[Callable[[str], Awaitable[None]]] = None,
        shadow_sink: Optional[list] = None,
        source_weight_active: bool = False,
    ) -> tuple[list[RetrievedDocument], str]:
        """
        混合檢索（回傳文件列表 + 狀態碼）

        Args:
            shadow_sink: OPTIONAL measurement-only out-param for the source-weighting
                SHADOW. When a list is passed, it is populated with the FULL reranked
                candidate pool as [(doc, rerank_score_0_1)]. Purely additive — the
                returned (documents, status) is byte-identical whether or not it is
                provided (the reranker already scores the full pool; we only capture it).
            source_weight_active: PRD §2.10.3 ACTIVATION. When True, the final top_k is
                REORDERED by composite V1 (rerank × source_weight × tier_weight) over the
                full reranked pool, using the SAME shadow-validated tier/composite code
                (source_weight_shadow.rank_by_composite_v1 — no fork). When False, the
                returned order is today's rerank order (byte-identical). This ONLY reorders
                the already-retrieved+reranked set — no source is dropped or added.

        Returns:
            (documents, status)
            status: "ok" | "no_results" | "irrelevant" | "error"
        """
        async def _emit(label: str) -> None:
            """Surface a real pipeline-stage boundary to the caller (SSE status).
            No-op when on_stage is not provided — observation only, retrieval
            logic is unchanged."""
            if on_stage:
                await on_stage(label)

        # Step 1：Query Rewriting（生成 3 個標準化查詢；non-DailyMed 用這 3 個）
        rewritten_queries = await self._rewrite_query(query)
        logger.info("Query rewritten: len=%d -> %d variants", len(query), len(rewritten_queries))
        for i, q in enumerate(rewritten_queries, 1):
            logger.debug("  [%d] len=%d", i, len(q))

        # Step 1b: DailyMed-ONLY K-union rewrite set (lever 1) — recovers the straddling safety
        # section; isolated to DailyMed so PubMed/FDA/local/TFDA pools are NOT inflated.
        dailymed_queries = (await self._dailymed_union_queries(query, k=3)
                            if (not source_filter or SourceType.DAILYMED in source_filter) else [])

        # Step 2：對每個 rewritten query 並行檢索所有來源（DailyMed 用 union set）
        all_tasks = []
        for rq in rewritten_queries:
            if self.enable_local and (not source_filter or SourceType.LOCAL in source_filter):
                all_tasks.append(self._search_local(rq, max_results))
            if self.enable_pubmed and (not source_filter or SourceType.PUBMED in source_filter):
                all_tasks.append(self._search_pubmed(rq, max_results))
            if self.enable_fda and (not source_filter or SourceType.FDA in source_filter):
                all_tasks.append(self._search_fda(rq, max_results))
            if self.enable_tfda and self.tfda_store and (not source_filter or SourceType.TFDA in source_filter):
                all_tasks.append(self._search_tfda(rq, max_results))
        for dq in dailymed_queries:
            if self.enable_dailymed and self.dailymed_store and (not source_filter or SourceType.DAILYMED in source_filter):
                all_tasks.append(self._search_dailymed(dq, max_results))

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        all_documents = []
        has_api_error = False
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                logger.warning("Retrieval error: %s", type(result).__name__)
                has_api_error = True

        if not all_documents:
            status = "error" if has_api_error else "no_results"
            return [], status

        # Step 3：去重（source_id 唯一，保留 relevance_score 最高的那筆）
        best: dict[str, int] = {}  # source_id -> index in all_documents
        for i, doc in enumerate(all_documents):
            prev = best.get(doc.source_id)
            if prev is None or doc.relevance_score > all_documents[prev].relevance_score:
                best[doc.source_id] = i
        unique_docs = [all_documents[i] for i in sorted(best.values())]

        logger.info("Retrieved %d docs, %d unique after dedup", len(all_documents), len(unique_docs))

        # Step 4：年份加權
        unique_docs = self._apply_year_boost(unique_docs)

        # Step 5：排序，取候選
        unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        candidates = unique_docs[:max_results * 4]  # 多取供相關性驗證

        # Lever-2 (recall-miss [P1]): re-add any whitelisted safety section the [:N] cut dropped,
        # so a retrieved-but-cut label section reaches the filter (+surface-(iii)) + composite.
        # ADDITIVE — never drops/reorders a survived candidate.
        candidates = _cut_exemption(candidates, unique_docs)

        # Step 6：相關性驗證
        # Real stage boundary: fetch produced documents (we're past the
        # no_results short-circuit above) → the relevance-filter + rerank stages
        # are about to run. Emit-on-real-start: short-circuited queries never reach here.
        await _emit("rank")
        relevant_docs = await self._filter_by_relevance(query, candidates)

        if not relevant_docs:
            logger.warning("Relevance check: all documents filtered out for query (len=%d)", len(query))
            return [], "irrelevant"

        # Step 7：Rerank
        # Capture the full reranked pool when EITHER the shadow (measurement) or the
        # activation (reordering) needs it — the SAME capture object, so activation
        # reorders exactly what the shadow measured (parity). Passed to the reranker as
        # score_sink; if rerank throws we leave the sink empty (both degrade gracefully).
        _need_pool = shadow_sink is not None or source_weight_active
        _score_sink = [] if _need_pool else None
        try:
            documents = await self.reranker.rerank(query, relevant_docs, score_sink=_score_sink)
        except Exception as e:
            logger.warning("Rerank failed: %s, using relevance order", type(e).__name__)
            documents = relevant_docs
        if shadow_sink is not None and _score_sink:
            shadow_sink.extend(_score_sink)

        # PRD §2.10.3 ACTIVATION (SOURCE_WEIGHT_ACTIVE, decided by the caller): reorder the
        # final top_k by composite V1 over the FULL reranked pool, reusing the shadow's
        # validated tier/composite code (no fork). POST-rerank (pre-rerank is erased). Only
        # reorders the retrieved+reranked set — never drops/adds a source; the top_k SET
        # changes only when a reorder crosses the max_results cutoff (rare, per the sweep).
        # When _score_sink is empty (rerank degenerate/failed) → falls through to rerank order.
        if source_weight_active and not _score_sink:
            # FAIL LOUD (CLAUDE.md Rule 18): activation is ON but the rerank produced no
            # score pool (skip path leaves the sink empty), so the composite is silently
            # inert for this query. ONE WARNING per retrieve() call (no loop → no double-log)
            # makes the bypass directly observable instead of inferred. Behavior-neutral —
            # the reorder below is already skipped by the same empty-sink condition.
            logger.warning("[SOURCE_WEIGHT_INERT] source_weight_active but rerank produced no "
                           "score pool (rerank skipped) — composite bypassed, relevance order used")
        if source_weight_active and _score_sink:
            from api.services.source_weight_shadow import rank_by_composite_v1
            documents = rank_by_composite_v1(_score_sink)

        # B-2: collapse DailyMed sub-chunks of the SAME section BEFORE the top_k cut, so a
        # section counts as ONE citation slot (a >24k-char section is stored as
        # …#{loinc}~0/~1; both can rank in). Keeps the highest-ranked chunk (documents are
        # already in final order). DISTINCT sections of a drug (…#{loinc_a} vs …#{loinc_b})
        # stay SEPARATE — section-level citation granularity (founder decision). No-op for any
        # source_id without a '~{i}' suffix (all non-DailyMed docs, + un-chunked sections).
        documents = self._collapse_subchunks(documents)

        logger.info("Final: %d documents returned", len(documents))
        return documents[:max_results], "ok"

    # ─────────────────────────────────────────────
    # Query Rewriting（核心新增）
    # ─────────────────────────────────────────────

    async def _rewrite_query(self, query: str) -> list[str]:
        """
        將任何語言、任何風格的查詢改寫為 3 個精確的醫學術語查詢

        策略：
        - Query 1：機制導向（why / how it works）
        - Query 2：臨床導向（symptoms / management / dosing）
        - Query 3：藥名/術語精確版（INN names for the drugs the user NAMED + MeSH terms; never collapse a drug class into one drug pair）

        Examples:
          "warfarin 和阿斯匹靈一起安全嗎？"
          → ["warfarin aspirin drug interaction bleeding risk",
             "anticoagulant antiplatelet combination management INR monitoring",
             "warfarin aspirin hemorrhage CYP2C9 pharmacodynamic interaction"]

          "can I give both blood thinners together"
          → ["anticoagulant antiplatelet concurrent therapy safety",
             "warfarin aspirin dual therapy bleeding cardiovascular risk",
             "antithrombotic combination therapy clinical guidelines"]
        """
        try:
            req = CompletionRequest(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical search query optimizer. "
                            "Given a user question in ANY language or writing style, "
                            "generate exactly 3 different English search queries for PubMed/medical databases.\n\n"
                            "STEP 1 — Clinical interpretation (do this mentally before generating queries):\n"
                            "Patients describe symptoms in everyday language. You must first think: "
                            "\"What clinical diagnosis or condition would a doctor associate with this description?\" "
                            "Then use THAT clinical term in your queries — NEVER translate the patient's words literally.\n"
                            "- \"head pressure/tightness/heaviness\" → tension-type headache, cervicogenic headache "
                            "(NOT intracranial pressure/hypertension)\n"
                            "- \"chest feels stuffy/tight\" → chest tightness, angina, anxiety-related dyspnea "
                            "(NOT nasal congestion)\n"
                            "- \"bones feel sore\" → musculoskeletal pain, arthralgia "
                            "(NOT bone cancer)\n"
                            "Apply this same clinical reasoning to ALL languages and symptom descriptions.\n\n"
                            # bp_calcium car (2026-09-29, tests/probes/bp_calcium/ verdicts A/C): a
                            # class-level question ("BP meds with calcium") never produced a rewrite naming
                            # the thiazide/hypercalcemia mechanism, so no source was ever asked for it.
                            "STEP 1b — Confusable terms and class-level interactions:\n"
                            "- CONFUSABLE TERMS: calcium, potassium, magnesium, iron or vitamin D taken as a "
                            "co-administered SUPPLEMENT is NOT the drug class that shares the word "
                            "(calcium channel blocker, potassium-sparing diuretic ...). Read it from context: "
                            "when a supplement, food or OTC product is taken WITH a drug or drug class, "
                            "treat it as a supplement.\n"
                            "- CLASS-LEVEL INTERACTION QUESTIONS (one side is a drug CLASS or a lay term such as "
                            "\"BP meds\", or a supplement/food): at least ONE query must name the specific known "
                            "interaction as CLASS + MECHANISM + OUTCOME "
                            "(e.g. \"thiazide diuretic calcium supplement hypercalcemia\"), not a single drug pair.\n\n"
                            "STEP 2 — Generate 3 queries from different angles:\n"
                            "1. Mechanism/pharmacology angle (how/why)\n"
                            "2. Clinical management angle (symptoms/treatment/dosing)\n"
                            "3. Precise medical terminology angle (INN names for the drugs the user NAMED, MeSH terms; "
                            "never collapse a drug class into one drug pair)\n\n"
                            "Rules:\n"
                            "- Output ONLY valid JSON array with exactly 3 strings\n"
                            "- Each query: 4-8 words, English only, no punctuation\n"
                            "- Use standard medical terminology and drug names\n"
                            "- NO explanations, NO extra text\n\n"
                            'Example output: ["warfarin aspirin bleeding risk mechanism", '
                            '"anticoagulant antiplatelet combination INR monitoring", '
                            '"warfarin aspirin hemorrhage pharmacodynamic interaction"]'
                        )
                    },
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=150,
                response_format={"type": "json_object"},
            )
            response = await self._provider.complete(req)

            # Cost tracking — use self._model so future Groq swap stays accurate.
            try:
                from api.services.cost_tracker import log_api_cost_standalone
                if response.input_tokens or response.output_tokens:
                    await log_api_cost_standalone(
                        "system", "research/rewrite_query", self._model,
                        response.input_tokens, response.output_tokens
                    )
            except Exception:
                pass

            raw = response.content.strip()
            parsed = json.loads(raw)

            # 支援 {"queries": [...]} 或直接 [...]
            if isinstance(parsed, dict):
                queries = parsed.get("queries", parsed.get("query", []))
            elif isinstance(parsed, list):
                queries = parsed
            else:
                queries = []

            # 確保是 3 個有效字串
            queries = [q for q in queries if isinstance(q, str) and q.strip()][:3]

            if len(queries) >= 1:
                return queries

        except Exception as e:
            logger.warning("Query rewriting failed: %s, falling back to translation", type(e).__name__)

        # Fallback：退回原本的翻譯邏輯
        fallback = await self._translate_to_medical_english(query)
        return [fallback]

    async def _dailymed_union_queries(self, query: str, k: int = 3) -> list[str]:
        """Lever-1 (recall-miss [P1]): DailyMed-ONLY K-union rewrite set. Runs `_rewrite_query`
        k times IN PARALLEL (asyncio.gather — serial would add ~2-4s), unions the emitted
        rewrites (first-seen, deduped), and appends the raw `query` as a deterministic augment.
        Used ONLY for _search_dailymed — the other sources keep the single K=1 rewrite set (no
        PubMed/FDA pool inflation). Returns [] when DailyMed is disabled (no wasted LLM calls)."""
        if not (self.enable_dailymed and self.dailymed_store):
            return []
        batches = await asyncio.gather(*[self._rewrite_query(query) for _ in range(k)])
        seen: set[str] = set()
        out: list[str] = []
        for rws in batches:
            for w in rws:
                if isinstance(w, str) and w.strip() and w not in seen:
                    seen.add(w)
                    out.append(w)
        if query not in seen:
            out.append(query)
        return out

    async def _translate_to_medical_english(self, query: str) -> str:
        """Fallback：單純翻譯為英文醫學術語"""
        has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in query)
        if not has_chinese:
            return query.strip()

        try:
            req = CompletionRequest(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical terminology translator. "
                            "Convert the given query into concise English medical search terms "
                            "suitable for PubMed. Output ONLY the English search terms, "
                            "no explanations. Keep it under 10 words."
                        )
                    },
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=50,
            )
            response = await self._provider.complete(req)
            translated = response.content.strip()
            return translated if translated else query

        except Exception as e:
            logger.warning("Translation failed: %s, using original query", type(e).__name__)
            return query

    # ─────────────────────────────────────────────
    # 相關性驗證
    # ─────────────────────────────────────────────

    async def _filter_by_relevance(
        self,
        original_query: str,
        documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        """用 LLM 驗證每份文件是否真正回答了用戶的問題"""
        if not documents:
            return []

        doc_summaries = []
        for i, doc in enumerate(documents):
            preview = doc.content[:300].replace('\n', ' ')
            doc_summaries.append(f"[{i}] {doc.title}: {preview}")

        docs_text = "\n".join(doc_summaries)

        try:
            req = CompletionRequest(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical relevance judge. "
                            "Given a user question and a list of retrieved documents, "
                            "determine which documents actually contain information "
                            "relevant to answering the question. "
                            "Output ONLY a JSON array of indices (0-based) of relevant documents. "
                            "Example output: [0, 2, 3]  "
                            "If none are relevant, output: []"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User question: {original_query}\n\n"
                            f"Retrieved documents:\n{docs_text}\n\n"
                            f"Which document indices are relevant? Output JSON array only."
                        )
                    }
                ],
                temperature=0,
                max_tokens=100,
            )
            response = await self._provider.complete(req)

            # Cost tracking — use self._model so future Groq swap stays accurate.
            try:
                from api.services.cost_tracker import log_api_cost_standalone
                if response.input_tokens or response.output_tokens:
                    await log_api_cost_standalone(
                        "system", "research/relevance_filter", self._model,
                        response.input_tokens, response.output_tokens
                    )
            except Exception:
                pass

            raw = response.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            relevant_indices = json.loads(raw)

            filtered = [
                documents[i] for i in relevant_indices
                if isinstance(i, int) and 0 <= i < len(documents)
            ]

            # Surface-(iii) exemption: re-add any RETRIEVED whitelisted official-label SAFETY
            # section the filter dropped (the gpt-4.1-mini filter is input-brittle and drops
            # e.g. #34073-7 on some pools — probe filterexempt_probe_REPORT.md 2026-07-20).
            # ADDITIVE: operates ONLY on the drop-set, APPENDS — never removes/reorders a kept
            # doc, never rescoves. Rerank re-sorts afterward, so append order is immaterial.
            kept_ids = {d.source_id for d in filtered}
            exempted = [d for d in documents
                        if d.source_id not in kept_ids and _is_whitelisted_safety_section(d)]
            if exempted:
                logger.info("[FilterExempt] re-added %d whitelisted safety section(s) dropped by "
                            "the filter: %s", len(exempted), [d.source_id for d in exempted])
                filtered = filtered + exempted

            logger.info("Relevance filter: %d -> %d documents kept", len(documents), len(filtered))
            return filtered

        except Exception as e:
            logger.warning("Relevance filter failed: %s, returning all documents", type(e).__name__)
            return [doc for doc in documents if doc.relevance_score >= RELEVANCE_THRESHOLD]

    # ─────────────────────────────────────────────
    # 年份加權
    # ─────────────────────────────────────────────

    def _apply_year_boost(self, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """對近年文獻給予加分"""
        import datetime
        current_year = datetime.datetime.now().year

        for doc in documents:
            try:
                year_str = getattr(doc, 'year', None)
                if year_str and str(year_str).isdigit():
                    doc_year = int(str(year_str)[:4])
                    years_ago = current_year - doc_year
                    boost = YEAR_BOOST.get(years_ago, 0)
                    doc.relevance_score = min(1.0, doc.relevance_score + boost)
            except Exception:
                pass

        return documents

    def _collapse_subchunks(self, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """Collapse sub-chunk docs of ONE section into a single citation.

        A DailyMed section longer than the embed cap is stored as multiple docs sharing the
        section key but suffixed `~0/~1/…` (source_id `DailyMed:{setid}#{loinc}~{i}`). When
        two chunks of the SAME section both survive rerank, they would render as duplicate
        citations (identical setid deep-link, identical section). We keep the FIRST occurrence
        (highest-ranked, since `documents` is already in final order).

        The collapse key strips ONLY a trailing `~{i}` — so DISTINCT sections of the same drug
        (`…#{loinc_a}` vs `…#{loinc_b}`) have DIFFERENT keys and stay SEPARATE citations
        (founder decision: section-level granularity). Any source_id without a `~` (all
        non-DailyMed sources, and un-chunked DailyMed sections) passes through unchanged.
        """
        seen: set[str] = set()
        out: list[RetrievedDocument] = []
        for doc in documents:
            key = doc.source_id.split("~", 1)[0]   # strip the sub-chunk suffix only
            if key in seen:
                continue
            seen.add(key)
            out.append(doc)
        return out

    # ─────────────────────────────────────────────
    # 各來源檢索
    # ─────────────────────────────────────────────

    async def _search_local(self, query: str, max_results: int) -> list[RetrievedDocument]:
        # §2.1 PHASE B (PRD v1.4): VectorStore.search() is now native async
        # (was sync + run_in_executor). EmbedderProvider performs the embedding
        # call asynchronously; the cosine-similarity math is pure CPU work and
        # fast enough to stay on the event loop.
        try:
            documents = await self.vector_store.search(
                query=query,
                n_results=max_results,
                min_score=self.local_threshold
            )
            return documents
        except Exception as e:
            logger.warning("Local search error: %s", type(e).__name__)
            return []

    async def _search_tfda(self, query: str, max_results: int) -> list[RetrievedDocument]:
        # ADR 007 grounding-lite: search ONLY the TFDA 核准適應症 corpus, with the SAME cosine
        # threshold as the local store (so a weakly-similar indication doc on an off-topic —
        # e.g. safety — query is filtered out before it can reach the reranker). Bounded to
        # max_results; the docs carry source_type="tfda" → become numbered citations via the
        # existing to_citation() path when they survive rerank.
        try:
            return await self.tfda_store.search(
                query=query,
                n_results=max_results,
                min_score=self.local_threshold,
            )
        except Exception as e:
            logger.warning("TFDA search error: %s", type(e).__name__)
            return []

    async def _search_dailymed(self, query: str, max_results: int) -> list[RetrievedDocument]:
        # B-2: search ONLY the DailyMed US-label PER-SECTION corpus, SAME cosine threshold as
        # the local/TFDA stores (a weakly-similar section on an off-topic query is filtered out
        # before the reranker). Bounded to max_results; docs carry source_type="dailymed" and a
        # per-section title "{brand} ({generic}) — {section}" → become numbered citations via the
        # existing to_citation() path when they survive rerank. Ingest-and-cite: present the
        # label's own section text; NO DDI verdict (ADR 004/007).
        try:
            return await self.dailymed_store.search(
                query=query,
                n_results=max_results,
                min_score=self.local_threshold,
            )
        except Exception as e:
            logger.warning("DailyMed search error: %s", type(e).__name__)
            return []

    async def _search_pubmed(self, query: str, max_results: int) -> list[RetrievedDocument]:
        try:
            articles = await self.pubmed.search_and_fetch(query, max_results)

            documents = []
            total = len(articles)
            for rank, article in enumerate(articles):
                rank_score = 0.85 - (rank / max(total, 1)) * 0.20

                doc = RetrievedDocument(
                    content=article.to_text(),
                    source_type=SourceType.PUBMED,
                    source_id=article.source_id,
                    title=article.title,
                    url=article.url,
                    credibility=CredibilityLevel.PEER_REVIEWED,
                    year=article.pub_date,
                    authors=", ".join(article.authors[:3]),
                    journal=article.journal,
                    relevance_score=rank_score,
                    publication_types=article.publication_types or [],
                )
                documents.append(doc)

            return documents

        except Exception as e:
            logger.warning("PubMed search error: %s", type(e).__name__)
            return []

    async def _search_fda(self, query: str, max_results: int) -> list[RetrievedDocument]:
        try:
            labels = await self.fda.search_drug_labels(query, limit=max_results)

            documents = []
            for label in labels:
                doc = RetrievedDocument(
                    content=label.to_text(),
                    source_type=SourceType.FDA,
                    source_id=label.source_id,
                    title=f"{label.brand_name} ({label.generic_name})",
                    url=label.url,
                    credibility=CredibilityLevel.OFFICIAL,
                    authors=label.manufacturer,
                    relevance_score=0.75
                )
                documents.append(doc)

            return documents

        except Exception as e:
            logger.warning("FDA search error: %s", type(e).__name__)
            return []