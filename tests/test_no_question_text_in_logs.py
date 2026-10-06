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


def test_generator_and_guard_failures_log_no_exception_text(monkeypatch, caplog, capsys):
    """OpenAI / provider errors on the question path: the generator (main + no-literature fallback stream)
    and both LLM guards used to log the exception text (with a traceback); a provider message is not the
    code's to guarantee, so only the exception TYPE is logged. Fail-closed behaviour is unchanged."""
    from types import SimpleNamespace
    import api.middleware.guards as guards
    from api.models.schemas import StreamEventType
    from api.rag.generator import AnswerGenerator

    class _Boom:
        async def complete(self, req):
            raise RuntimeError(f"provider rejected prompt containing {SENTINEL}")

        async def stream(self, req):
            raise RuntimeError(f"provider rejected prompt containing {SENTINEL}")
            yield  # pragma: no cover — makes this an async generator

    caplog.set_level(logging.DEBUG)
    gen = AnswerGenerator()
    monkeypatch.setattr(gen, "_provider", _Boom())

    async def _drain(status, docs):
        return [e async for e in gen.generate_stream(question=SENTINEL, documents=docs,
                                                     retrieval_status=status, lang="en")]

    for status, docs in (("ok", _docs()), ("no_results", [])):
        events = asyncio.run(_drain(status, docs))
        assert any(e.type == StreamEventType.ERROR for e in events), f"harness: {status} path must error"

    monkeypatch.setattr(guards, "_get_guard_binding",
                        lambda: SimpleNamespace(provider=_Boom(), model="test-model"))
    # A NON-medical sentinel: the intent guard short-circuits on medical keywords (guards.py
    # _has_medical_keywords) before any LLM call, which would leave the failure path unexercised.
    guard_text = f"{SENTINEL_KEY} weekend travel plans 7731"
    assert not guards._has_medical_keywords(guard_text), "harness: must reach the LLM call"
    intent_ok, _ = asyncio.run(guards.check_medical_intent(guard_text))
    long_text = guard_text + " and a long walk by the river on a quiet sunny afternoon" * 2  # >= 100 chars:
    assert len(long_text) >= 100     # the injection guard skips the LLM below 100 (guards.py check_indirect_injection)
    injected, _ = asyncio.run(guards.check_indirect_injection(long_text))
    assert intent_ok is False and injected is True, "fail-CLOSED behaviour must be preserved (Rule 1)"
    assert sum("failed (blocking request)" in r.getMessage() for r in caplog.records) == 2
    assert _leaks(caplog, capsys) == []


def test_retrieval_refusal_shadow_logs_no_question_derived_factor(monkeypatch, caplog, capsys):
    """RETRIEVAL_REFUSAL_SHADOW (a Fly secret — its value is not visible in the repo): the decision's
    `factor` is extracted FROM the question and used to be logged verbatim. Missed by the first P1 scan
    (the variable name was not in its set); caught by the shadow-flag report."""
    from types import SimpleNamespace
    import api.server as server
    import api.services.retrieval_refusal as rr

    async def _assess(llm, *, question, pool_sources, factor_outcome=None):
        return SimpleNamespace(refuse=False, one_sided=False, counter_plausible=False,
                               factor=question, to_sink_dict=lambda: {})

    monkeypatch.setattr(rr, "pool_sources_from_documents", lambda docs: [("1", "a"), ("2", "b")])
    monkeypatch.setattr(rr, "make_strong_llm", lambda: None)
    monkeypatch.setattr(rr, "assess", _assess)
    caplog.set_level(logging.DEBUG)
    asyncio.run(server._run_retrieval_refusal_background("res_sentinel", SENTINEL, []))
    assert any("[RetrievalRefusal]" in r.getMessage() for r in caplog.records), "harness: the decision line must log"
    assert _leaks(caplog, capsys) == []


def _route_db(server_module):
    """Per-test in-memory DB wired into the app (same pattern as tests/test_archive_mode.py)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from api.database.sql_db import Base, get_db

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    TS = sessionmaker(bind=eng)

    def _override():
        db = TS()
        try:
            yield db
        finally:
            db.close()
    server_module.app.dependency_overrides[get_db] = _override
    return eng, get_db


def test_research_route_end_to_end_logs_no_question_text(monkeypatch, caplog, capsys):
    """CATCH-ALL for the Research path (added after the first P1 scan missed a site): the sentinel goes
    through the REAL /api/research route — guards, PHI check, TFDA annotation, retriever, reranker,
    generator, source-weight shadow — signed-in AND anonymous, with ARCHIVE_MODE and all three shadow
    flags ON; then the three background tasks run with their captured arguments. Only LLM / network
    edges are stubbed, and the fake model ECHOES the question in its answer and in the shadow factor
    (worst case). Not one log record or stdout byte may contain the sentinel."""
    import json
    from types import SimpleNamespace
    import api.server as server
    import api.services.retrieval_refusal as rr
    import api.services.direction_checker as dc
    from fastapi.testclient import TestClient

    for flag in ("ARCHIVE_MODE", "SOURCE_WEIGHT_SHADOW", "RETRIEVAL_REFUSAL_SHADOW", "DIRECTION_CHECK_SHADOW"):
        monkeypatch.setenv(flag, "true")
    R = server.retriever

    async def _rewrite(q):
        return [q, q + " clinical"]

    async def _none(*a, **k):
        return []

    async def _docs_for(q, n):
        return _docs()[:3]

    async def _keep(q, docs):
        return docs

    async def _rerank_ok(req):
        return SimpleNamespace(content=json.dumps({"scores": [{"index": i, "score": 90 - i} for i in range(3)]}),
                               input_tokens=0, output_tokens=0)

    class _EchoGen:
        async def stream(self, req):
            yield SimpleNamespace(delta=f"Answer about {SENTINEL} [1].", usage=None)
            yield SimpleNamespace(delta="", usage={"prompt_tokens": 1, "completion_tokens": 1})

    monkeypatch.setattr(R, "_rewrite_query", _rewrite)
    monkeypatch.setattr(R, "_dailymed_union_queries", lambda q, k=3: _none())
    monkeypatch.setattr(R, "_search_pubmed", _docs_for)
    for m in ("_search_fda", "_search_tfda", "_search_dailymed", "_search_local"):
        monkeypatch.setattr(R, m, _none)
    monkeypatch.setattr(R, "_filter_by_relevance", _keep)
    monkeypatch.setattr(R.reranker._provider, "complete", _rerank_ok)
    monkeypatch.setattr(server.generator, "_provider", _EchoGen())

    captured = []

    for name in ("_run_judge_background", "_run_direction_check_background", "_run_retrieval_refusal_background"):
        real = getattr(server, name)

        def _mk(n, fn):
            async def _f(*args):
                captured.append((n, fn, args))
            return _f
        monkeypatch.setattr(server, name, _mk(name, real))

    eng, get_db = _route_db(server)
    caplog.set_level(logging.DEBUG)
    try:
        client = TestClient(server.app)
        for headers in ({}, {"X-Anon-Fingerprint": "e2e-sentinel-fingerprint-0001"}):
            resp = client.post("/api/research", json={"question": SENTINEL, "response_language": "en"},
                               headers=headers)
            assert resp.status_code == 200 and '"type": "answer"' in resp.text, resp.text[:200]
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        eng.dispose()
    assert any("[Research]" in r.getMessage() for r in caplog.records), "harness: the route must have logged"
    assert any("[SourceWeightShadow]" in r.getMessage() for r in caplog.records), "harness: shadow must have run"

    async def _llm_echo(prompt):
        return json.dumps({"factor": SENTINEL, "outcome": SENTINEL, "stance": "harmful",
                           "counter_plausible": False, "verdict": "consistent"})

    async def _judge_eval(q, a, s):
        return {"scores": {}, "weighted_score": 9.0, "quality_level": "high"}

    monkeypatch.setattr(rr, "make_strong_llm", lambda *a, **k: _llm_echo)
    monkeypatch.setattr(dc, "make_lightweight_llm", lambda *a, **k: _llm_echo)
    monkeypatch.setattr(server._judge, "evaluate", _judge_eval)
    ran = set()
    for name, fn, args in captured:
        asyncio.run(fn(*args))
        ran.add(name)
    assert ran == {"_run_judge_background", "_run_direction_check_background", "_run_retrieval_refusal_background"}, ran
    assert _leaks(caplog, capsys) == []
