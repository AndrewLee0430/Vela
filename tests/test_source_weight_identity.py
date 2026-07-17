# -*- coding: utf-8 -*-
"""HARD identity gate for the source-weighting SHADOW (v198).

THE gate for enabling SOURCE_WEIGHT_SHADOW anywhere: retrieval output — the returned
documents, their order, their relevance_scores, and their Citations — MUST be
byte-identical whether the shadow sink is present (flag ON) or absent (flag OFF). The
sink only ever READS docs; this proves it empirically end-to-end through the real
retrieve() + reranker, with the LLM/search stubbed for determinism (no network).

If this fails, the shadow can perturb a user-visible result and must NOT ship enabled.

Run: python tests/test_source_weight_identity.py   (or via pytest)
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402


def _make_docs():
    """Fresh doc set each call (rerank mutates relevance_score in place)."""
    return [
        RetrievedDocument(content=f"Doc about warfarin bleeding risk number {i}. " * 3,
                          source_type=(SourceType.FDA if i % 3 == 0 else SourceType.PUBMED),
                          source_id=f"SRC:{i}", title=f"Title {i}", url=f"https://x/{i}",
                          credibility=CredibilityLevel.OFFICIAL if i % 3 == 0 else CredibilityLevel.PEER_REVIEWED,
                          year="2023", relevance_score=0.5 + i * 0.01,
                          publication_types=(["Observational Study"] if i % 3 else []))
        for i in range(8)
    ]


def _build_stub_retriever():
    """A HybridRetriever whose rewrite/search/relevance-filter/rerank-LLM are stubbed
    deterministic — so the ONLY variable across runs is the shadow_sink argument."""
    from api.rag.retriever import HybridRetriever

    r = HybridRetriever(enable_local=True, enable_pubmed=False, enable_fda=False, enable_tfda=False)

    async def _fake_rewrite(query):
        return ["warfarin bleeding risk"]
    r._rewrite_query = _fake_rewrite

    async def _fake_local(query, max_results):
        return _make_docs()
    r._search_local = _fake_local

    async def _fake_filter(original_query, documents):
        return documents  # keep all — deterministic
    r._filter_by_relevance = _fake_filter

    # Deterministic reranker: stub the provider to return fixed descending scores.
    class _StubResp:
        def __init__(self, content):
            self.content = content
            self.input_tokens = 0
            self.output_tokens = 0

    async def _fake_complete(req):
        # 8 docs → keyed-by-index scores (reverse of input so rerank actually reorders)
        scores = [30, 40, 50, 60, 70, 80, 90, 95]
        return _StubResp(json.dumps({"scores": [{"index": i, "score": s} for i, s in enumerate(scores)]}))
    r.reranker._provider.complete = _fake_complete
    return r


def _snapshot(docs):
    """Comparable, order-sensitive fingerprint of retrieval output incl. citations."""
    out = []
    for i, d in enumerate(docs):
        c = d.to_citation(i + 1)
        out.append((d.source_id, str(d.source_type), round(d.relevance_score, 6),
                    d.title, d.url, c.snippet, c.id))
    return out


def test_retrieve_output_identical_shadow_on_vs_off():
    async def run():
        r = _build_stub_retriever()
        docs_off, status_off = await r.retrieve("warfarin safety", max_results=5, shadow_sink=None)
        sink = []
        docs_on, status_on = await r.retrieve("warfarin safety", max_results=5, shadow_sink=sink)
        return (status_off, _snapshot(docs_off)), (status_on, _snapshot(docs_on)), sink

    off, on, sink = asyncio.run(run())
    assert off == on, f"IDENTITY VIOLATION:\n OFF={off}\n ON ={on}"
    assert len(off[1]) == 5, "expected top-5 citations returned"
    # And the sink actually captured the FULL pool (8) — proving it's populated without
    # perturbing the returned 5.
    assert len(sink) == 8, f"shadow sink should hold the full reranked pool, got {len(sink)}"


def test_sink_holds_doc_score_pairs_in_reranked_order():
    async def run():
        r = _build_stub_retriever()
        sink = []
        await r.retrieve("warfarin safety", max_results=5, shadow_sink=sink)
        return sink

    sink = asyncio.run(run())
    scores = [s for _, s in sink]
    assert scores == sorted(scores, reverse=True), "sink must be in reranked (desc) order"
    assert all(hasattr(d, "source_id") for d, _ in sink)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
