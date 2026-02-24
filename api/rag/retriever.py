"""
Hybrid Retriever - v2.1
混合檢索器：結合本地向量資料庫、PubMed、FDA API

v2.1 改進：
1. 查詢翻譯 - 中文查詢自動轉為英文醫學術語
2. 相關性驗證 - 過濾低相關度文件，避免答非所問
3. 年份加權 - 優先返回近 5 年文獻
4. 友善錯誤分層 - 區分「無結果」vs「API 錯誤」
"""

import asyncio
from typing import Optional
from openai import OpenAI
from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel
from api.database.vector_store import get_vector_store
from api.data_sources.pubmed import PubMedClient
from api.data_sources.fda import FDAClient

# 相關性過濾門檻（0~1），低於此值的文件會被丟棄
RELEVANCE_THRESHOLD = 0.45

# 年份加權：近幾年文獻的加分
YEAR_BOOST = {0: 0.10, 1: 0.08, 2: 0.06, 3: 0.04, 4: 0.02}  # key = 距今幾年


class HybridRetriever:
    """
    混合檢索器 v2.1

    檢索流程：
    1. 查詢翻譯（中文 → 英文醫學術語）
    2. 並行檢索（本地 DB / PubMed / FDA）
    3. 相關性驗證（過濾不相關文件）
    4. 年份加權排序
    5. 回傳最相關文件
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
        # Step 1：翻譯查詢
        english_query = await self._translate_to_medical_english(query)
        print(f"🔤 Query translated: '{query}' → '{english_query}'")

        # Step 2：並行檢索
        tasks = []
        if self.enable_local and (not source_filter or SourceType.LOCAL in source_filter):
            tasks.append(self._search_local(english_query, max_results))
        if self.enable_pubmed and (not source_filter or SourceType.PUBMED in source_filter):
            tasks.append(self._search_pubmed(english_query, max_results))
        if self.enable_fda and (not source_filter or SourceType.FDA in source_filter):
            tasks.append(self._search_fda(english_query, max_results))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_documents = []
        has_api_error = False
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                print(f"⚠️ Retrieval error: {result}")
                has_api_error = True

        # 無任何結果
        if not all_documents:
            status = "error" if has_api_error else "no_results"
            return [], status

        # Step 3：去重
        seen = set()
        unique_docs = []
        for doc in all_documents:
            if doc.source_id not in seen:
                seen.add(doc.source_id)
                unique_docs.append(doc)

        # Step 4：年份加權
        unique_docs = self._apply_year_boost(unique_docs)

        # Step 5：排序並限制數量
        unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        candidates = unique_docs[:max_results * 2]  # 多取一些供相關性驗證

        # Step 6：相關性驗證（核心新增）
        relevant_docs = await self._filter_by_relevance(query, candidates)

        if not relevant_docs:
            print(f"⚠️ Relevance check: all documents filtered out for query '{query}'")
            return [], "irrelevant"

        return relevant_docs[:max_results], "ok"

    # ─────────────────────────────────────────────
    # 查詢翻譯
    # ─────────────────────────────────────────────

    async def _translate_to_medical_english(self, query: str) -> str:
        """
        將查詢翻譯為英文醫學術語
        - 如果已是英文，直接清理並回傳
        - 中文查詢轉為 PubMed 適用的英文關鍵字
        """
        # 快速判斷是否需要翻譯（是否包含中文字元）
        has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in query)
        if not has_chinese:
            return query.strip()

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a medical terminology translator. "
                                "Convert the given query into concise English medical search terms "
                                "suitable for PubMed. Output ONLY the English search terms, "
                                "no explanations. Keep it under 10 words. "
                                "Example: '孕婦使用抗生素的安全性' → 'antibiotic safety pregnancy'"
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
    # 相關性驗證（核心改進）
    # ─────────────────────────────────────────────

    async def _filter_by_relevance(
        self,
        original_query: str,
        documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        """
        用 LLM 驗證每份文件是否真正回答了用戶的問題
        過濾掉「被向量相似度誤召回」的不相關文件
        """
        if not documents:
            return []

        # 建立批次驗證 prompt（一次送全部，節省 API 呼叫）
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
                    model="gpt-4o-mini",
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

            import json
            raw = response.choices[0].message.content.strip()
            # 清理可能的 markdown 包裝
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
            # 失敗時 fallback：用分數門檻過濾
            return [doc for doc in documents if doc.relevance_score >= RELEVANCE_THRESHOLD]

    # ─────────────────────────────────────────────
    # 年份加權
    # ─────────────────────────────────────────────

    def _apply_year_boost(self, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """
        對近年文獻給予加分，優先返回最新證據
        """
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
    # 各來源檢索（內部方法）
    # ─────────────────────────────────────────────

    async def _search_local(self, query: str, max_results: int) -> list[RetrievedDocument]:
        """搜尋本地向量資料庫"""
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
        """搜尋 PubMed（使用英文查詢，計算真實相關性分數）"""
        try:
            articles = await self.pubmed.search_and_fetch(query, max_results)

            documents = []
            total = len(articles)
            for rank, article in enumerate(articles):
                # 用排名計算初始相關性分數（第 1 名最高）
                # 範圍：0.65 ~ 0.85
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
        """搜尋 FDA"""
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