# -*- coding: utf-8 -*-
"""Research history fidelity — the single Research write site persists the
answer markdown AND the streamed citation list (HISTORY car segment 3, half B).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
Until segment 3 the Research ChatHistory INSERT stored ONLY the answer
markdown; the citation list streamed as a separate SSE `citations` event and
was never written to chat_history (the AuditLog copy keeps bare source_ids —
lossy, recon_20260901 §7-D2), so /history could style a `[4]` marker but never
resolve it. Founder ruling 2026-09-02: embed the citations in the answer JSON
(recon §4 option (i)), Explain-parity, no schema change, NO backfill — every
pre-segment-3 row stays plain markdown and renders through the half-A path.

These tests drive the REAL POST /api/research handler (SSE) against an
in-memory DB with only the NETWORK edges stubbed (the two LLM guards,
retrieval, the answer generator, the background judge — same isolation
pattern as tests/test_verify_history_payload.py; production guard code is
NOT modified) and assert the STORED answer:
  * parses as JSON carrying the explicit `kind: research_v1` marker
    (the key /history branches on — a plain-markdown write fails here);
  * round-trips the streamed markdown BYTE-IDENTICALLY under `answer`;
  * carries the SAME citation objects the SSE `citations` event streamed —
    count, ids and full dicts (no re-shaping, no lossy subset);
  * survives the empty-citations shapes: the generator's fallback path
    (CITATIONS with content=[]) and its exception path (ERROR → DONE with NO
    CITATIONS event at all) — the second is the checkpoint-9 find: the
    `citations_data` local is bound only inside the CITATIONS branch, so the
    write must not assume it fired.

Run: python -m pytest tests/test_research_history_payload.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server: TEST_MODE bypasses Clerk/credits checks; the
# DATABASE_URL default keeps module init off any real DB (all reads/writes in
# these tests go through a dependency-overridden StaticPool engine below).
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

QUESTION = "Is metformin safe in moderate renal impairment?"

# Rule-12 two-section markdown, streamed as THREE chunks (the handler
# accumulates `full_answer += content`); CJK + em-dash exercise ensure_ascii.
ANSWER_CHUNKS = [
    "## Summary — English\n\nMetformin is generally safe when eGFR ≥ 45 [1].",
    "\n\n---\n\n## Clinical Notes — English\n\n- Reassess below 45 [2]\n",
    "- 腎功能 eGFR < 30 停用 [1]\n",
]


def _citations():
    from api.models.schemas import Citation, CredibilityLevel, SourceType
    return [
        Citation(id=1, source_type=SourceType.PUBMED, source_id="PMID:12345678",
                 title="Metformin in CKD", snippet="Abstract text one.",
                 url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                 credibility=CredibilityLevel.PEER_REVIEWED, year="2021",
                 authors="Doe J", journal="Diabetes Care"),
        Citation(id=2, source_type=SourceType.DAILYMED, source_id="setid:abc",
                 title="GLUCOPHAGE label", snippet="Dosage and administration.",
                 url="https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc",
                 credibility=CredibilityLevel.OFFICIAL),
    ]


def _fresh_db(server_module):
    """Per-test in-memory DB shared across connections (StaticPool), with the
    real schema, wired into the app via dependency_overrides on get_db."""
    from api.database.sql_db import Base, get_db

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    server_module.app.dependency_overrides[get_db] = _override_get_db
    return engine, TestSession, get_db


class _FakeGenerator:
    """Yields a scripted StreamEvent sequence; appends no usage (cost log skipped)."""
    _fallback_model = "test-fallback-model"
    model = "test-model"

    def __init__(self, events):
        self._events = events

    async def generate_stream(self, **kwargs):
        for ev in self._events:
            yield ev


class _FakeRetriever:
    async def retrieve(self, **kwargs):
        return [], "ok"


def _sse_events(body_text):
    out = []
    for line in body_text.splitlines():
        if line.startswith("data: "):
            out.append(json.loads(line[len("data: "):]))
    return out


def _post_research(monkeypatch, events):
    """Drive POST /api/research through the real SSE handler with stubbed
    edges; return (parsed SSE events, stored research ChatHistory rows)."""
    import api.middleware.guards as guards
    import api.server as server
    from api.models.sql_models import ChatHistory
    from fastapi.testclient import TestClient

    async def _always_ok(text):
        return True, ""

    async def _never_injection(text):
        return False, ""

    async def _judge_noop(*args, **kwargs):
        return None

    monkeypatch.setattr(guards, "check_medical_intent", _always_ok)
    monkeypatch.setattr(guards, "check_indirect_injection", _never_injection)
    monkeypatch.setattr(server, "retriever", _FakeRetriever())
    monkeypatch.setattr(server, "generator", _FakeGenerator(events))
    monkeypatch.setattr(server, "_run_judge_background", _judge_noop)

    engine, TestSession, get_db = _fresh_db(server)
    try:
        client = TestClient(server.app)  # no context manager → no lifespan side effects
        resp = client.post("/api/research", json={
            "question": QUESTION,
            "response_language": "en",
        })
        assert resp.status_code == 200, resp.text
        with TestSession() as db:
            rows = db.query(ChatHistory).filter(
                ChatHistory.session_type == "research").all()
            stored = [(r.user_id, r.question, r.answer) for r in rows]
        return _sse_events(resp.text), stored
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _script(chunks, citations_event=True, citations=None):
    from api.models.schemas import StreamEvent, StreamEventType
    events = [StreamEvent(type=StreamEventType.ANSWER, content=c) for c in chunks]
    if citations_event:
        events.append(StreamEvent(type=StreamEventType.CITATIONS,
                                  content=citations if citations is not None else []))
    events.append(StreamEvent(type=StreamEventType.DONE))
    return events


def test_stored_row_carries_marker_markdown_and_streamed_citations(monkeypatch):
    """Happy path: 3 answer chunks + 2 citations → ONE research row whose
    answer is research_v1 JSON with the byte-identical markdown and the
    exact citation dicts the SSE `citations` event carried."""
    sse, stored = _post_research(monkeypatch, _script(ANSWER_CHUNKS, citations=_citations()))

    streamed_answer = "".join(e["content"] for e in sse if e.get("type") == "answer")
    assert streamed_answer == "".join(ANSWER_CHUNKS), "harness: the stub stream drifted"
    streamed_citations = [e for e in sse if e.get("type") == "citations"]
    assert len(streamed_citations) == 1
    streamed_citations = streamed_citations[0]["content"]
    assert [c["id"] for c in streamed_citations] == [1, 2]

    assert len(stored) == 1, f"expected exactly one research history row, got {len(stored)}"
    _, question, answer = stored[0]
    assert question == QUESTION

    parsed = json.loads(answer)  # raises → plain-markdown regression
    assert parsed["kind"] == "research_v1", "explicit schema marker /history branches on"
    assert parsed["answer"] == streamed_answer, "markdown must round-trip byte-identically"
    assert "## Summary — English" in parsed["answer"] and "腎功能" in parsed["answer"]
    assert len(parsed["citations"]) == len(streamed_citations) == 2
    assert [c["id"] for c in parsed["citations"]] == [c["id"] for c in streamed_citations]
    assert parsed["citations"] == streamed_citations, \
        "stored citations must be the SAME objects the SSE event emitted (no re-shaping)"
    # The renderer's keys survive verbatim (CitationPanel reads these).
    assert parsed["citations"][0]["source_type"] == "pubmed"
    assert parsed["citations"][0]["credibility"] == "peer-reviewed"
    assert parsed["citations"][1]["url"].startswith("https://dailymed.nlm.nih.gov/")
    assert set(parsed) == {"kind", "answer", "citations"}, \
        "no audit/request id in the payload — no correlation-key route"


def test_fallback_shape_stores_empty_citations(monkeypatch):
    """Generator fallback path (api/rag/generator.py emits CITATIONS with
    content=[]) → stored JSON still carries the marker + markdown, citations []."""
    sse, stored = _post_research(monkeypatch, _script(ANSWER_CHUNKS, citations=[]))
    assert [e for e in sse if e.get("type") == "citations"][0]["content"] == []
    assert len(stored) == 1
    parsed = json.loads(stored[0][2])
    assert parsed["kind"] == "research_v1"
    assert parsed["answer"] == "".join(ANSWER_CHUNKS)
    assert parsed["citations"] == []


def test_no_citations_event_still_writes_row_with_empty_citations(monkeypatch):
    """Generator exception path emits ERROR → DONE with NO CITATIONS event
    (api/rag/generator.py, the except branch). The DONE write must not
    depend on the CITATIONS branch having bound `citations_data`: the row is
    written with citations [] — never a NameError swallowed into an error
    event and a silently missing row."""
    sse, stored = _post_research(monkeypatch, _script(ANSWER_CHUNKS[:1], citations_event=False))
    assert not [e for e in sse if e.get("type") == "citations"], "harness: no citations event"
    assert not [e for e in sse if e.get("type") == "error"], \
        "an error event here means the write path crashed after DONE"
    assert len(stored) == 1, "the DONE write must still land without a CITATIONS event"
    parsed = json.loads(stored[0][2])
    assert parsed["kind"] == "research_v1"
    assert parsed["answer"] == ANSWER_CHUNKS[0]
    assert parsed["citations"] == []
