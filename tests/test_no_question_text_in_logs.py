# -*- coding: utf-8 -*-
"""Question text never reaches server logs or Sentry (founder ruling P1, archive UI car, 2026-10-05).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails): `pages/privacy.tsx` promises that
query content "is not stored or logged on our servers", and the archive FAQ (Q5) says the logs record a
question's LENGTH, not its text. Both were false: `api/rag/retriever.py` logged `Query rewritten:
'<question>'` at INFO on every Research request (TECH_DEBT E5, 2026-10-02 bullet). These tests push a
SENTINEL question through the real code that used to leak it and assert the sentinel appears in ZERO
captured log records AND zero bytes of stdout / stderr (some sites used print()).

Channels covered, each by driving real code — only the network edge is fake:
  * the retrieval path (`HybridRetriever.retrieve`) with the REAL PubMed + openFDA clients behind an
    httpx MockTransport whose errors carry the request URL — exactly what a real ConnectError /
    HTTPStatusError does — so exception-text echoes are exercised, not just direct interpolation;
  * the "all documents filtered out" branch;
  * a DB write that fails: SQLAlchemy error text includes bound parameters unless the engine hides them;
  * the Sentry init options (no frame locals, no request bodies, no httpx query-string spans).

Run: SENTRY_DSN= python -m pytest tests/test_no_question_text_in_logs.py -q
"""
import asyncio
import logging
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SENTRY_DSN"] = ""
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Import the app module so the test runs under PROD logging config (server.py pins the `httpx`
# logger to WARNING — tests/test_httpx_log_level.py); without it httpx's own INFO request line
# would be captured, which prod never emits.
import api.server  # noqa: E402,F401

SENTINEL = "zqxsentinel side effects of metformin 7731"
SENTINEL_KEY = "zqxsentinel"          # the substring every assertion searches for
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _leaks(caplog, capsys):
    """Every captured record (message + exception text) and stdout/stderr chunk that holds the sentinel."""
    hits = []
    for r in caplog.records:
        text = r.getMessage()
        if r.exc_info:
            text += "\n" + logging.Formatter().formatException(r.exc_info)
        if SENTINEL_KEY in text:
            hits.append(f"{r.name}:{r.lineno} {r.levelname} {r.getMessage()[:160]}")
    out = capsys.readouterr()
    for stream, val in (("stdout", out.out), ("stderr", out.err)):
        if SENTINEL_KEY in val:
            hits.append(f"{stream}: {val[:160]}")
    return hits


class _ModHttpx:
    """Stand-in for the `httpx` module inside ONE data-source module: AsyncClient goes through a
    MockTransport; every other attribute (exceptions, Response, …) is the real httpx's."""

    def __init__(self, handler):
        self._handler = handler

    def __getattr__(self, name):
        if name == "AsyncClient":
            handler = self._handler

            def factory(*args, **kwargs):
                kwargs["transport"] = httpx.MockTransport(handler)
                return _REAL_ASYNC_CLIENT(*args, **kwargs)
            return factory
        return getattr(httpx, name)


def _retriever(monkeypatch, *, fda=True):
    from api.rag.retriever import HybridRetriever
    r = HybridRetriever(enable_local=False, enable_pubmed=True, enable_fda=fda,
                        enable_tfda=False, enable_dailymed=False)

    async def _rewrite(q):
        return [q, q + " clinical"]

    async def _no_dailymed(q, k=3):
        return []

    monkeypatch.setattr(r, "_rewrite_query", _rewrite)
    monkeypatch.setattr(r, "_dailymed_union_queries", _no_dailymed)
    return r


def test_retrieval_path_with_failing_sources_logs_no_question_text(monkeypatch, caplog, capsys):
    """PubMed: the transport raises a ConnectError whose text carries the request URL (term=<question>);
    openFDA: a 500 → HTTPStatusError, whose text carries the URL too. Both used to echo the query."""
    import api.data_sources.fda as fda_mod
    import api.data_sources.pubmed as pubmed_mod

    def pubmed_handler(request):
        raise httpx.ConnectError(f"connection refused for {request.url}", request=request)

    def fda_handler(request):
        return httpx.Response(500, request=request, text="upstream error")

    monkeypatch.setattr(pubmed_mod, "httpx", _ModHttpx(pubmed_handler))
    monkeypatch.setattr(fda_mod, "httpx", _ModHttpx(fda_handler))
    caplog.set_level(logging.DEBUG)
    r = _retriever(monkeypatch)
    docs, status = asyncio.run(r.retrieve(query=SENTINEL, max_results=3))
    assert docs == [] and status in ("no_results", "error"), "harness: the sources were meant to fail"
    assert any("PubMed" in rec.getMessage() for rec in caplog.records), \
        "harness: the PubMed failure path must actually have logged (else this test proves nothing)"
    assert _leaks(caplog, capsys) == []


def test_relevance_filter_empty_branch_logs_no_question_text(monkeypatch, caplog, capsys):
    from api.models.schemas import CredibilityLevel, RetrievedDocument, SourceType

    async def _one_doc(q, n):
        return [RetrievedDocument(content="Metformin label text.", source_type=SourceType.PUBMED,
                                  source_id="PMID:1", title="t", url="https://example.org/1",
                                  credibility=CredibilityLevel.PEER_REVIEWED, relevance_score=0.8)]

    async def _drop_all(q, docs):
        return []

    caplog.set_level(logging.DEBUG)
    r = _retriever(monkeypatch, fda=False)
    monkeypatch.setattr(r, "_search_pubmed", _one_doc)
    monkeypatch.setattr(r, "_filter_by_relevance", _drop_all)
    docs, status = asyncio.run(r.retrieve(query=SENTINEL, max_results=3))
    assert (docs, status) == ([], "irrelevant"), "harness: the filtered-out branch must be the one taken"
    assert _leaks(caplog, capsys) == []


def test_failed_db_write_logs_no_row_values(caplog, capsys):
    """_safe_db_write logs the DB exception; SQLAlchemy's text carries bound parameters (the row's
    values — e.g. an AuditLog's query_content) unless the engine sets hide_parameters."""
    import api.server as server
    from api.database.sql_db import Base, SessionLocal, engine
    from api.models.sql_models import AuditLog

    Base.metadata.create_all(engine)
    caplog.set_level(logging.DEBUG)
    row = dict(id="dup_sentinel_1", user_id="u", action="research", query_content=SENTINEL,
               resource_ids=[], ip_address="0.0.0.0")
    with SessionLocal() as db:
        server._safe_db_write(db, AuditLog(**row))
    with SessionLocal() as db:
        ok = server._safe_db_write(db, AuditLog(**row), label="Audit Log")
    assert ok is False, "harness: the duplicate primary key must make the write fail and log"
    assert any("Audit Log Error" in rec.getMessage() for rec in caplog.records)
    assert _leaks(caplog, capsys) == []


def test_sentry_options_send_no_question_text():
    """What the Sentry SDK may ship: no frame locals (a local holds the question), no request bodies
    (the /api/research body IS the question), and no httpx spans / breadcrumbs (their query strings
    carry the PubMed / openFDA search terms)."""
    import api.server as server
    opts = server._sentry_init_kwargs("https://public@example.invalid/1")
    assert opts["send_default_pii"] is False
    assert opts["include_local_variables"] is False
    assert opts["max_request_body_size"] == "never"
    disabled = {type(i).__name__ for i in opts.get("disabled_integrations", [])}
    assert "HttpxIntegration" in disabled


def _docs():
    from api.models.schemas import CredibilityLevel, RetrievedDocument, SourceType
    return [RetrievedDocument(content=f"doc {i}", source_type=SourceType.PUBMED, source_id=f"PMID:{i}",
                              title="t", url="https://example.org", credibility=CredibilityLevel.PEER_REVIEWED,
                              relevance_score=0.5) for i in range(4)]   # > 2: past the small-pool guard


def test_reranker_skip_paths_log_no_model_or_exception_text(monkeypatch, caplog, capsys):
    """The reranker model is SHOWN the question; on an unparseable reply the raw reply used to be logged
    (it can echo the question), and on a provider error the exception text was logged."""
    from types import SimpleNamespace
    from api.rag.reranker import Reranker

    rr = Reranker(top_k=8)
    caplog.set_level(logging.DEBUG)

    async def _echo(req):
        return SimpleNamespace(content=f"I cannot score this: {SENTINEL}", input_tokens=0, output_tokens=0)

    monkeypatch.setattr(rr._provider, "complete", _echo)
    asyncio.run(rr.rerank(SENTINEL, _docs()))
    assert any("RERANK_SKIP" in r.getMessage() for r in caplog.records), "harness: the parse-skip path must log"

    async def _boom(req):
        raise RuntimeError(f"provider rejected prompt containing {SENTINEL}")

    monkeypatch.setattr(rr._provider, "complete", _boom)
    asyncio.run(rr.rerank(SENTINEL, _docs()))
    assert any("reason=exception" in r.getMessage() for r in caplog.records), "harness: the exception path must log"
    assert _leaks(caplog, capsys) == []
