# -*- coding: utf-8 -*-
"""Slice-1 observability gate for the reranker "unexpected scores format" skip
(TECH_DEBT [P1]).

These tests pin the FAIL-LOUD behavior added in slice 1 and PROVE it is behavior-neutral:
  (i)   a simulated n-1 response emits a WARNING carrying the RERANK_SKIP marker + the
        expected/received counts + the model + the raw payload;
  (ii)  the returned document order on the skip path is the input order, unmutated
        (no reorder, no relevance_score write) — same as before slice 1;
  (iii) the process counter increments per reason (success / format_reject / exception);
  (iv)  when source-weighting is active but the rerank skipped (empty pool), retrieve()
        emits ONE SOURCE_WEIGHT_INERT warning AND returns the identical order it would
        with activation OFF (the composite is bypassed either way — the log adds nothing
        to behavior).

The reranker's provider is stubbed for determinism (no network, no LLM).

Run: python tests/test_reranker_observability.py    (or: venv/Scripts/pytest tests/test_reranker_observability.py)
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402
from api.rag import reranker as reranker_mod  # noqa: E402
from api.rag import retriever as retriever_mod  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────────
class _StubResp:
    def __init__(self, content):
        self.content = content
        self.input_tokens = 0
        self.output_tokens = 0
        self.finish_reason = "stop"


class _FakeProvider:
    """Returns a fixed payload, or raises, from complete() — no network."""
    def __init__(self, content=None, raise_exc=None):
        self._content = content
        self._raise = raise_exc

    async def complete(self, req):
        if self._raise is not None:
            raise self._raise
        return _StubResp(self._content)


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def warnings(self):
        return [r.getMessage() for r in self.records if r.levelno == logging.WARNING]

    def messages(self):
        return [r.getMessage() for r in self.records]


def _attach(logger):
    cap = _LogCapture()
    logger.addHandler(cap)
    logger.setLevel(logging.DEBUG)
    return cap


def _make_docs(n):
    """Fresh doc set each call (rerank mutates relevance_score in place on success)."""
    return [
        RetrievedDocument(
            content=f"Doc {i} about warfarin bleeding risk. " * 3,
            source_type=(SourceType.FDA if i % 3 == 0 else SourceType.PUBMED),
            source_id=f"SRC:{i}", title=f"Title {i}", url=f"https://x/{i}",
            credibility=CredibilityLevel.OFFICIAL if i % 3 == 0 else CredibilityLevel.PEER_REVIEWED,
            year="2023", relevance_score=0.5 + i * 0.01,
            publication_types=(["Observational Study"] if i % 3 else []),
        )
        for i in range(n)
    ]


def _reranker_with(provider, top_k=8):
    r = reranker_mod.Reranker(top_k=top_k)
    r._provider = provider
    return r


def _reset_stats():
    for k in list(reranker_mod._RERANK_STATS.keys()):
        reranker_mod._RERANK_STATS[k] = 0


# ── (i) fail-loud WARNING with counts + payload + model + marker ───────────────────
def test_count_mismatch_logs_rerank_skip_with_counts():
    _reset_stats()
    docs = _make_docs(6)
    r = _reranker_with(_FakeProvider(content="[85, 90, 70, 50, 40]"))  # 5 scores for 6 docs
    cap = _attach(reranker_mod.logger)
    try:
        asyncio.run(r.rerank("q", docs, score_sink=[]))
    finally:
        reranker_mod.logger.removeHandler(cap)
    warns = cap.warnings()
    skip = [m for m in warns if "RERANK_SKIP" in m]
    assert skip, f"expected a RERANK_SKIP WARNING, got: {warns}"
    msg = skip[0]
    assert "format_reject" in msg, msg
    assert "expected=6" in msg, msg
    assert "received=5" in msg, msg
    assert "gpt-4o-mini" in msg, msg
    assert "[85, 90, 70, 50, 40]" in msg, msg  # raw payload included


# ── (ii) skip path returns input order, unmutated ─────────────────────────────────
def test_skip_path_returns_input_order_unmutated():
    _reset_stats()
    docs = _make_docs(6)
    before_ids = [d.source_id for d in docs]
    before_scores = [d.relevance_score for d in docs]
    r = _reranker_with(_FakeProvider(content="[85, 90, 70, 50, 40]"))  # n-1 → skip
    result = asyncio.run(r.rerank("q", docs, score_sink=[]))
    assert [d.source_id for d in result] == before_ids[: r.top_k], "skip must return input order"
    assert [d.relevance_score for d in docs] == before_scores, "skip must NOT mutate relevance_score"


# ── (iii) counter increments per reason ───────────────────────────────────────────
def test_counter_increments_per_reason():
    _reset_stats()
    asyncio.run(_reranker_with(_FakeProvider(content="[10,20,30,40,50,60]")).rerank("q", _make_docs(6), score_sink=[]))   # success
    asyncio.run(_reranker_with(_FakeProvider(content="[10,20,30,40,50]")).rerank("q", _make_docs(6), score_sink=[]))      # format_reject
    asyncio.run(_reranker_with(_FakeProvider(raise_exc=RuntimeError("boom"))).rerank("q", _make_docs(6), score_sink=[]))  # exception
    s = reranker_mod._RERANK_STATS
    assert s["attempts"] == 3, s
    assert s["success"] == 1, s
    assert s["skip_format_reject"] == 1, s
    assert s["skip_exception"] == 1, s


def test_small_pool_not_counted_as_attempt():
    """<=2 docs never issues the LLM call → must NOT inflate the attempt denominator."""
    _reset_stats()
    asyncio.run(_reranker_with(_FakeProvider(content="[10,20]")).rerank("q", _make_docs(2), score_sink=[]))
    s = reranker_mod._RERANK_STATS
    assert s["attempts"] == 0, s
    assert s["success"] == 0 and s["skip_format_reject"] == 0 and s["skip_exception"] == 0, s


# ── (iv) retriever SOURCE_WEIGHT_INERT warning + neutral ordering ──────────────────
def _build_stub_retriever_that_skips_rerank():
    """HybridRetriever whose rerank ALWAYS skips (provider returns n-1 scores)."""
    r = retriever_mod.HybridRetriever(enable_local=True, enable_pubmed=False,
                                      enable_fda=False, enable_tfda=False, enable_dailymed=False)

    async def _fake_rewrite(query):
        return ["warfarin bleeding risk"]
    r._rewrite_query = _fake_rewrite

    async def _fake_local(query, max_results):
        return _make_docs(8)
    r._search_local = _fake_local

    async def _fake_filter(original_query, documents):
        return documents  # keep all 8 → LLM path
    r._filter_by_relevance = _fake_filter

    r.reranker._provider = _FakeProvider(content="[10,20,30,40,50,60,70]")  # 7 scores for 8 → skip
    return r


def test_source_weight_inert_warns_when_active_and_rerank_skips():
    _reset_stats()
    r = _build_stub_retriever_that_skips_rerank()
    cap = _attach(retriever_mod.logger)
    try:
        docs, status = asyncio.run(r.retrieve("warfarin safety", max_results=5, source_weight_active=True))
    finally:
        retriever_mod.logger.removeHandler(cap)
    assert status == "ok"
    warns = cap.warnings()
    assert any("SOURCE_WEIGHT_INERT" in m for m in warns), f"expected SOURCE_WEIGHT_INERT, got: {warns}"


def test_active_and_off_return_identical_order_when_rerank_skips():
    """Behavior-neutrality: when rerank skips, activation ON vs OFF return the SAME order
    (composite is bypassed either way); the INERT log changes nothing."""
    _reset_stats()
    r1 = _build_stub_retriever_that_skips_rerank()
    off, _ = asyncio.run(r1.retrieve("warfarin safety", max_results=5, source_weight_active=False))
    r2 = _build_stub_retriever_that_skips_rerank()
    on, _ = asyncio.run(r2.retrieve("warfarin safety", max_results=5, source_weight_active=True))
    assert [d.source_id for d in off] == [d.source_id for d in on], "active vs off must match on skip"


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
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
