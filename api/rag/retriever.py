"""
Hybrid Retriever - v2.2
混合檢索器：結合本地向量資料庫、PubMed、FDA API

v2.2 新增：
1. Query Rewriting - 將口語/非英文查詢改寫為 3 個精確醫學術語查詢，並行檢索
2. 其餘邏輯（去重、年份加權、相關性驗證）完全不變
"""

import asyncio
import json
from typing import Optional
from openai import OpenAI
from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel
from api.database.vector_store import get_vector_store
from api.data_sources.pubmed import PubMedClient
from api.data_sources.fda import FDAClient
from api.rag.reranker import Reranker

# 相關性過濾門檻
RELEVANCE_THRESHOLD = 0.45

# 年份加權
YEAR_BOOST = {0: 0.10, 1: 0.08, 2: 0.06, 3: 0.04, 4: 0.02}


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
        enable_local: bool = True,
        enable_pubmed: bool = True,
        enable_fda: bool = True
    ):
        self.local_threshold = local_threshold
        self.enable_local = enable_local
        self.enable_pubmed = enable_pubmed
        self.enable_fda = enable_fda

        self.vector_store = get_vector_store() if enable_local else None
        self.pubmed = PubMedClient() if enable_pubmed else None
        self.fda = FDAClient() if enable_fda else None
        self.llm = OpenAI()
        self.reranker = Reranker(top_k=8)

    # ─────────────────────────────────────────────
    # 公開介面
    # ─────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        max_results: int = 5,
        source_filter: Optional[list[SourceType]] = None
    ) -> tuple[list[RetrievedDocument], str]:
        """
        混合檢索（回傳文件列表 + 狀態碼）

        Returns:
            (documents, status)
            status: "ok" | "no_results" | "irrelevant" | "error"
        """
        # Step 1：Query Rewriting（生成 3 個標準化查詢）
        rewritten_queries = await self._rewrite_query(query)
        print(f"🔤 Query rewritten: '{query}'")
        for i, q in enumerate(rewritten_queries, 1):
            print(f"   [{i}] {q}")

        # Step 2：對每個 rewritten query 並行檢索所有來源
        all_tasks = []
        for rq in rewritten_queries:
            if self.enable_local and (not source_filter or SourceType.LOCAL in source_filter):
                all_tasks.append(self._search_local(rq, max_results))
            if self.enable_pubmed and (not source_filter or SourceType.PUBMED in source_filter):
                all_tasks.append(self._search_pubmed(rq, max_results))
            if self.enable_fda and (not source_filter or SourceType.FDA in source_filter):
                all_tasks.append(self._search_fda(rq, max_results))

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        all_documents = []
        has_api_error = False
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                print(f"⚠️ Retrieval error: {result}")
                has_api_error = True

        if not all_documents:
            status = "error" if has_api_error else "no_results"
            return [], status

        # Step 3：去重（source_id 唯一）
        seen = set()
        unique_docs = []
        for doc in all_documents:
            if doc.source_id not in seen:
                seen.add(doc.source_id)
                unique_docs.append(doc)

        print(f"📚 Retrieved {len(all_documents)} docs → {len(unique_docs)} unique after dedup")

        # Step 4：年份加權
        unique_docs = self._apply_year_boost(unique_docs)

        # Step 5：排序，取候選
        unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        candidates = unique_docs[:max_results * 4]  # 多取供相關性驗證

        # Step 6：相關性驗證
        relevant_docs = await self._filter_by_relevance(query, candidates)

        if not relevant_docs:
            print(f"⚠️ Relevance check: all documents filtered out for query '{query}'")
            return [], "irrelevant"

        # Step 7：Rerank
        try:
            documents = await self.reranker.rerank(query, relevant_docs)
        except Exception as e:
            print(f"⚠️ Rerank failed: {e}, using relevance order")
            documents = relevant_docs

        print(f"✅ Final: {len(documents)} documents returned")
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
        - Query 3：藥名/術語精確版（official drug names + MeSH terms）

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
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a medical search query optimizer. "
                                "Given a user question in ANY language or writing style, "
                                "generate exactly 3 different English search queries for PubMed/medical databases.\n\n"
                                "Each query should approach the topic from a different angle:\n"
                                "1. Mechanism/pharmacology angle (how/why)\n"
                                "2. Clinical management angle (symptoms/treatment/dosing)\n"
                                "3. Precise medical terminology angle (official drug names, MeSH terms)\n\n"
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
                    response_format={"type": "json_object"}
                )
            )

            raw = response.choices[0].message.content.strip()
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
            print(f"⚠️ Query rewriting failed: {e}, falling back to translation")

        # Fallback：退回原本的翻譯邏輯
        fallback = await self._translate_to_medical_english(query)
        return [fallback]

    async def _translate_to_medical_english(self, query: str) -> str:
        """Fallback：單純翻譯為英文醫學術語"""
        has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in query)
        if not has_chinese:
            return query.strip()

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model="gpt-4.1-mini",
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
                    max_tokens=50
                )
            )
            translated = response.choices[0].message.content.strip()
            return translated if translated else query

        except Exception as e:
            print(f"⚠️ Translation failed: {e}, using original query")
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
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model="gpt-4.1-mini",
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
                    max_tokens=100
                )
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            relevant_indices = json.loads(raw)

            filtered = [
                documents[i] for i in relevant_indices
                if isinstance(i, int) and 0 <= i < len(documents)
            ]
            print(f"✅ Relevance filter: {len(documents)} → {len(filtered)} documents kept")
            return filtered

        except Exception as e:
            print(f"⚠️ Relevance filter failed: {e}, returning all documents")
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

    # ─────────────────────────────────────────────
    # 各來源檢索
    # ─────────────────────────────────────────────

    async def _search_local(self, query: str, max_results: int) -> list[RetrievedDocument]:
        try:
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(
                None,
                lambda: self.vector_store.search(
                    query=query,
                    n_results=max_results,
                    min_score=self.local_threshold
                )
            )
            return documents
        except Exception as e:
            print(f"⚠️ Local search error: {e}")
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
                    relevance_score=rank_score
                )
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"⚠️ PubMed search error: {e}")
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
            print(f"⚠️ FDA search error: {e}")
            return []