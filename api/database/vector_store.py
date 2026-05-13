"""
Vector Store - NumPy 向量搜尋（取代 ChromaDB）
使用 OpenAI embedding + cosine similarity，零外部 C 依賴

§2.1 PHASE B (PRD v1.4 + ADR 005): now wired through api.providers via
get_embedder_provider(). Embedding model + provider configurable via
EMBEDDER_PROVIDER / EMBEDDER_MODEL env vars. search() is now async.
"""

import json
import numpy as np
from typing import Optional
from pathlib import Path

from api.models.schemas import (
    RetrievedDocument,
    SourceType,
    CredibilityLevel
)
from api.providers import get_embedder_provider
from api.providers.base import EmbeddingRequest


class VectorStore:
    """NumPy 向量資料庫（記憶體內搜尋）"""

    def __init__(
        self,
        index_path: str = "data/drug_vectordb/index.json",
    ):
        self.index_path = index_path
        binding = get_embedder_provider()
        self._embedder = binding.provider
        self._embedder_model = binding.model
        self.documents = []
        self.embeddings = None  # np.ndarray, shape (n, dim)

        self._load_index()

    def _load_index(self):
        """載入預建的 embedding index"""
        path = Path(self.index_path)
        if not path.exists():
            print(f"⚠️ Vector index not found: {self.index_path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents = data["documents"]  # list of metadata dicts
        self.embeddings = np.array(data["embeddings"], dtype=np.float32)
        print(f"✅ Vector store loaded: {len(self.documents)} documents, dim={self.embeddings.shape[1]}")

    async def _get_embedding(self, text: str) -> np.ndarray:
        """取得文字的 embedding（透過 EmbedderProvider）"""
        req = EmbeddingRequest(model=self._embedder_model, input=text)
        resp = await self._embedder.embed(req)
        return np.array(resp.embeddings[0], dtype=np.float32)

    async def search(
        self,
        query: str,
        n_results: int = 10,
        source_filter: Optional[list[str]] = None,
        min_score: float = 0.0
    ) -> list[RetrievedDocument]:
        """
        Cosine similarity 搜尋

        Args:
            query: 搜尋查詢
            n_results: 返回數量
            source_filter: 來源類型過濾
            min_score: 最低相關度分數 (0-1)

        Returns:
            RetrievedDocument 列表
        """
        if self.embeddings is None or len(self.documents) == 0:
            return []

        query_emb = await self._get_embedding(query)

        # Cosine similarity: dot(q, d) / (|q| * |d|)
        norms = np.linalg.norm(self.embeddings, axis=1)
        query_norm = np.linalg.norm(query_emb)
        scores = self.embeddings @ query_emb / (norms * query_norm + 1e-10)

        # 排序（降序）
        sorted_idx = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_idx:
            score = float(scores[idx])
            if score < min_score:
                break  # sorted, so no more results above threshold

            meta = self.documents[idx]

            if source_filter and meta.get("source_type") not in source_filter:
                continue

            raw_source_type = meta.get("source_type", "local")
            if raw_source_type == "fda_label":
                raw_source_type = "local"

            results.append(RetrievedDocument(
                content=meta["content"],
                source_type=SourceType(raw_source_type),
                source_id=meta.get("source_id", ""),
                title=meta.get("title", ""),
                url=meta.get("url", ""),
                credibility=CredibilityLevel(meta.get("credibility", "official")),
                year=meta.get("year"),
                authors=meta.get("authors"),
                journal=meta.get("journal"),
                relevance_score=score
            ))

            if len(results) >= n_results:
                break

        return results

    def get_stats(self) -> dict:
        """取得資料庫統計資訊"""
        return {
            "total_documents": len(self.documents),
            "embedding_dim": self.embeddings.shape[1] if self.embeddings is not None else 0,
            "index_path": self.index_path,
            "engine": "numpy"
        }


# Singleton
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """取得 VectorStore 單例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
