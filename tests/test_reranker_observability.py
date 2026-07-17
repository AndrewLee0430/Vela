# -*- coding: utf-8 -*-
"""Reranker observability + keyed-schema gate (TECH_DEBT [P1] slice 1 + slice 2).

SLICE 1 (fly 207) shipped fail-loud observability. SLICE 2 replaces the fragile positional
score array with a KEYED-BY-INDEX object schema (`{"scores":[{"index":i,"score":n},...]}`,
`response_format=json_object`) so a dropped element is STRUCTURALLY detectable instead of
tripping an off-by-one length check. These tests pin:

  parser (`_parse_keyed_scores`, pure):
    - all n indices present (any order) → aligned scores by index;
    - missing index → keyed_missing; duplicate / out-of-range / non-dict / positional-array
      / non-numeric → keyed_invalid; unparseable JSON → json_parse.
  rerank():
    - success reorders by keyed score assigned BY INDEX (not position);
    - every skip reason emits `[RERANK_SKIP reason=<reason>]` + the WARNING summary, returns
      input order with relevance_score UNMUTATED, and leaves score_sink EMPTY (→ composite
      bypass), including the exception path (slice-2: no more stale-score activation);
    - `[RERANK_STATS]` summary is WARNING (slice-2 piggyback, ships through Fly log loss);
    - counter increments per reason; <=2-doc pools are not counted.
  retriever: SOURCE_WEIGHT_INERT still fires on an empty-sink skip and ordering is neutral.

Provider stubbed for determinism (no network).

Run: python tests/test_reranker_observability.py   (or: venv/Scripts/pytest tests/test_reranker_observability.py)
"""
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402
from api.rag import reranker as reranker_mod  # noqa: E402
from api.rag import retriever as retriever_mod  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────────
def keyed(scores, *, entries=None):
    """Build a new keyed-schema response body. `scores` = positional list → entries in
    order; or pass explicit `entries` (list of dicts) for missing/dup/out-of-range cases."""
    if entries is None:
        entries = [{"index": i, "score": s} for i, s in enumerate(scores)]
    return json.dumps({"scores": entries})


class _StubResp:
    def __init__(self, content):
        self.content = content
        self.input_tokens = 0
        self.output_tokens = 0
        self.finish_reason = "stop"


class _FakeProvider:
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


# ── parser unit tests (_parse_keyed_scores) ───────────────────────────────────────
def test_parse_valid_aligns_by_index_not_position():
    # entries deliberately SCRAMBLED: index 2 first. Result must map by INDEX.
    body = keyed(None, entries=[{"index": 2, "score": 90}, {"index": 0, "score": 10},
                                {"index": 1, "score": 50}])
    aligned, reason = reranker_mod._parse_keyed_scores(body, 3)
    assert reason == "ok", reason
    assert aligned == [0.10, 0.50, 0.90], aligned  # doc0=10/100, doc1=50, doc2=90


def test_parse_missing_index_returns_keyed_missing():
    body = keyed([80, 70])  # 2 entries for 3 docs
    aligned, reason = reranker_mod._parse_keyed_scores(body, 3)
    assert aligned is None and reason == "keyed_missing", (aligned, reason)


def test_parse_duplicate_index_returns_keyed_invalid():
    body = keyed(None, entries=[{"index": 0, "score": 1}, {"index": 0, "score": 2},
                                {"index": 1, "score": 3}])
    aligned, reason = reranker_mod._parse_keyed_scores(body, 3)  # n=3, dup 0, missing 2
    assert aligned is None and reason == "keyed_invalid", (aligned, reason)


def test_parse_out_of_range_index_returns_keyed_invalid():
    body = keyed(None, entries=[{"index": 0, "score": 1}, {"index": 3, "score": 2}])
    aligned, reason = reranker_mod._parse_keyed_scores(body, 3)  # idx 3 out of range
    assert aligned is None and reason == "keyed_invalid", (aligned, reason)


def test_parse_positional_array_returns_keyed_invalid():
    aligned, reason = reranker_mod._parse_keyed_scores("[85, 40, 92]", 3)  # old shape
    assert aligned is None and reason == "keyed_invalid", (aligned, reason)


def test_parse_malformed_json_returns_json_parse():
    aligned, reason = reranker_mod._parse_keyed_scores("{not json", 3)
    assert aligned is None and reason == "json_parse", (aligned, reason)


def test_parse_bool_index_rejected_as_invalid():
    # JSON true is an int-subclass in Python (True == 1); must NOT be accepted as index.
    body = keyed(None, entries=[{"index": True, "score": 1}, {"index": 1, "score": 2},
                                {"index": 2, "score": 3}])
    aligned, reason = reranker_mod._parse_keyed_scores(body, 3)
    assert aligned is None and reason == "keyed_invalid", (aligned, reason)


def test_parse_strips_code_fence():
    aligned, reason = reranker_mod._parse_keyed_scores(
        "```json\n" + keyed([50, 60, 70]) + "\n```", 3)
    assert reason == "ok" and aligned == [0.50, 0.60, 0.70], (aligned, reason)


# ── rerank(): success reorders by keyed score, assigned by INDEX ───────────────────
def test_keyed_success_reranks_by_index():
    _reset_stats()
    docs = _make_docs(4)  # SRC:0..3
    # highest score to index 3, then 0, then 2, then 1
    body = keyed(None, entries=[{"index": 0, "score": 80}, {"index": 1, "score": 10},
                                {"index": 2, "score": 40}, {"index": 3, "score": 95}])
    result = asyncio.run(_reranker_with(_FakeProvider(content=body)).rerank("q", docs, score_sink=[]))
    assert [d.source_id for d in result] == ["SRC:3", "SRC:0", "SRC:2", "SRC:1"], [d.source_id for d in result]
    assert reranker_mod._RERANK_STATS["success"] == 1


# ── rerank(): skip reasons ─────────────────────────────────────────────────────────
def test_keyed_missing_skips_with_marker_and_empty_sink():
    _reset_stats()
    docs = _make_docs(6)
    before_ids = [d.source_id for d in docs]
    before_scores = [d.relevance_score for d in docs]
    sink = []
    cap = _attach(reranker_mod.logger)
    try:
        result = asyncio.run(_reranker_with(_FakeProvider(content=keyed([80, 70, 60, 50, 40]))).rerank("q", docs, score_sink=sink))
    finally:
        reranker_mod.logger.removeHandler(cap)
    warns = cap.warnings()
    assert any("RERANK_SKIP" in m and "keyed_missing" in m for m in warns), warns
    assert reranker_mod._RERANK_STATS["skip_keyed_missing"] == 1
    assert sink == [], "skip must leave score_sink EMPTY (→ composite bypass)"
    assert [d.source_id for d in result] == before_ids[:8], "skip returns input order"
    assert [d.relevance_score for d in docs] == before_scores, "skip must NOT mutate relevance_score"


def test_keyed_invalid_duplicate_skips():
    _reset_stats()
    docs = _make_docs(4)
    body = keyed(None, entries=[{"index": 0, "score": 1}, {"index": 0, "score": 2},
                                {"index": 1, "score": 3}, {"index": 2, "score": 4},
                                {"index": 3, "score": 5}])
    cap = _attach(reranker_mod.logger)
    try:
        asyncio.run(_reranker_with(_FakeProvider(content=body)).rerank("q", docs, score_sink=[]))
    finally:
        reranker_mod.logger.removeHandler(cap)
    assert any("RERANK_SKIP" in m and "keyed_invalid" in m for m in cap.warnings()), cap.warnings()
    assert reranker_mod._RERANK_STATS["skip_keyed_invalid"] == 1


def test_positional_array_now_skips_keyed_invalid():
    _reset_stats()
    asyncio.run(_reranker_with(_FakeProvider(content="[85, 90, 70, 50, 40, 60]")).rerank("q", _make_docs(6), score_sink=[]))
    assert reranker_mod._RERANK_STATS["skip_keyed_invalid"] == 1, reranker_mod._RERANK_STATS


# ── rerank(): exception path now BYPASSES (empty sink), no stale-score activation ──
def test_exception_path_leaves_sink_empty():
    _reset_stats()
    docs = _make_docs(6)
    before = [d.source_id for d in docs]
    sink = []
    cap = _attach(reranker_mod.logger)
    try:
        result = asyncio.run(_reranker_with(_FakeProvider(raise_exc=RuntimeError("boom"))).rerank("q", docs, score_sink=sink))
    finally:
        reranker_mod.logger.removeHandler(cap)
    assert any("RERANK_SKIP" in m and "exception" in m for m in cap.warnings()), cap.warnings()
    assert reranker_mod._RERANK_STATS["skip_exception"] == 1
    assert sink == [], "exception path must leave sink EMPTY (no stale-score activation)"
    assert [d.source_id for d in result] == before[:8], "exception returns input order"


# ── rerank(): RERANK_STATS summary is now WARNING (slice-2 piggyback) ──────────────
def test_rerank_stats_summary_is_warning():
    _reset_stats()
    cap = _attach(reranker_mod.logger)
    try:
        asyncio.run(_reranker_with(_FakeProvider(content=keyed([50, 60, 70, 80, 90, 40]))).rerank("q", _make_docs(6), score_sink=[]))
    finally:
        reranker_mod.logger.removeHandler(cap)
    assert any("RERANK_STATS" in m for m in cap.warnings()), f"RERANK_STATS must be WARNING now: {cap.warnings()}"


# ── counters ───────────────────────────────────────────────────────────────────────
def test_counter_increments_per_reason():
    _reset_stats()
    asyncio.run(_reranker_with(_FakeProvider(content=keyed([10, 20, 30, 40, 50, 60]))).rerank("q", _make_docs(6), score_sink=[]))       # success
    asyncio.run(_reranker_with(_FakeProvider(content=keyed([10, 20, 30, 40, 50]))).rerank("q", _make_docs(6), score_sink=[]))           # keyed_missing
    asyncio.run(_reranker_with(_FakeProvider(content="[10,20,30,40,50,60]")).rerank("q", _make_docs(6), score_sink=[]))                 # keyed_invalid (positional)
    asyncio.run(_reranker_with(_FakeProvider(raise_exc=RuntimeError("boom"))).rerank("q", _make_docs(6), score_sink=[]))                # exception
    s = reranker_mod._RERANK_STATS
    assert s["attempts"] == 4, s
    assert s["success"] == 1, s
    assert s["skip_keyed_missing"] == 1, s
    assert s["skip_keyed_invalid"] == 1, s
    assert s["skip_exception"] == 1, s


def test_small_pool_not_counted_as_attempt():
    _reset_stats()
    asyncio.run(_reranker_with(_FakeProvider(content=keyed([10, 20]))).rerank("q", _make_docs(2), score_sink=[]))
    s = reranker_mod._RERANK_STATS
    assert s["attempts"] == 0, s


# ── retriever SOURCE_WEIGHT_INERT + neutral ordering on skip ──────────────────────
def _build_stub_retriever_that_skips_rerank():
    r = retriever_mod.HybridRetriever(enable_local=True, enable_pubmed=False,
                                      enable_fda=False, enable_tfda=False, enable_dailymed=False)

    async def _fake_rewrite(query):
        return ["warfarin bleeding risk"]
    r._rewrite_query = _fake_rewrite

    async def _fake_local(query, max_results):
        return _make_docs(8)
    r._search_local = _fake_local

    async def _fake_filter(original_query, documents):
        return documents
    r._filter_by_relevance = _fake_filter

    r.reranker._provider = _FakeProvider(content=keyed([10, 20, 30, 40, 50, 60, 70]))  # 7 for 8 → keyed_missing
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
    assert any("SOURCE_WEIGHT_INERT" in m for m in cap.warnings()), cap.warnings()


def test_active_and_off_return_identical_order_when_rerank_skips():
    _reset_stats()
    off, _ = asyncio.run(_build_stub_retriever_that_skips_rerank().retrieve("warfarin safety", max_results=5, source_weight_active=False))
    on, _ = asyncio.run(_build_stub_retriever_that_skips_rerank().retrieve("warfarin safety", max_results=5, source_weight_active=True))
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
