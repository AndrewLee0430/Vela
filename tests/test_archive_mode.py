# -*- coding: utf-8 -*-
"""ARCHIVE MODE (founder decision 2026-10-05) — Vela becomes an archived open
work: a capped live demo that serves ANONYMOUS RESEARCH ONLY.

THE BUSINESS RULES (CLAUDE.md Rule 17 — what breaks if each test fails):
  * With ARCHIVE_MODE=true every retired route answers 410 with ONE generic
    body (Rule 5 — no exception text) and does NO work: no DB row written or
    changed, no credit deducted, no guard / LLM call, no outbound network call
    (Dodo, Clerk, Lemon Squeezy, OpenAI). A gate that answered 410 AFTER doing
    the work would still charge, still write, and still call the vendor —
    hence every blocked call reads the seeded rows back and counts outbound
    socket attempts, instead of trusting the status code alone.
  * /api/research is NOT blocked, and in archive mode it writes NO ChatHistory
    row for ANY tier (archive mode stops collecting). Each "no row" assertion
    is paired with the credit deduction the same request DID make, so it
    cannot pass because the stream never reached its DONE branch.
  * The routes archive mode must keep (Dodo webhook — cancellations still have
    to land; Clerk webhook; /health; history read) are not gated.
  * With the flag OFF a blocked route behaves exactly as before — the suite
    runs unchanged and the gate is inert by default.
  * ANON_DAILY_BUDGET_USD makes the anonymous aggregate cap configurable;
    unset keeps the Decision 001 v0.3 A7 value ($2.00), and a malformed value
    fails LOUD (Rule 18) instead of silently becoming some other cap.
  * fly.toml switches archive mode ON for prod, and the frontend flag is a
    Next.js BUILD arg, which only reaches `npm run build` if the Dockerfile
    declares it — a build arg set in fly.toml but not declared there is
    silently dropped (Rule 19: carry the plumbing, not only the value).

HARNESS SAFETY: api.server runs load_dotenv(), so the local .env's LIVE
vendor keys are in the process. A missing gate (the RED run, the mutation run)
would send a real Dodo PATCH / Clerk lookup / OpenAI call. The autouse
`_outbound` fixture blocks every non-loopback DNS lookup and connect, and
dummies the per-request vendor keys, so no request in this file can leave the
machine whatever the handler does.

Run: SENTRY_DSN= python -m pytest tests/test_archive_mode.py -q
"""
import os
import socket
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Env BEFORE importing api.server (same convention as the sibling suites).
# SENTRY_DSN blanked first: load_dotenv() does not override a set key, so the
# local .env DSN never ships this file's logged errors to the real project.
os.environ["SENTRY_DSN"] = ""
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

ARCHIVED_BODY = {"detail": "Vela is archived. This feature is no longer available."}

# TEST_MODE resolves a request with no Authorization header to this user
# (api/server.py require_auth / require_auth_or_anonymous).
USER_ID = os.getenv("TEST_USER_ID", "test_user")
ANON_FP = "archive-anon-fingerprint-0001"
SEED_USER_CREDITS = 5
SEED_ANON_CREDITS = 2
SEED_SUB_ID = "sub_archive_test_0001"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

# The retired surface, one row per route (founder spec 2026-10-05, Segment B).
BLOCKED = [
    ("verify", "/api/verify", {"json": {"drugs": ["Metformin", "Warfarin"]}}),
    ("explain", "/api/explain", {"json": {"report_text": "HbA1c 7.8%, eGFR 45"}}),
    ("explain_extract_image", "/api/explain/extract-image",
     {"files": {"file": ("lab.png", PNG_BYTES, "image/png")}}),
    ("share_create", "/api/share/create",
     {"json": {"query_id": "res_archive", "query_text": "metformin renal dosing",
               "answer_text": "## Summary — English\n\nReduce the dose."}}),
    ("user_context_hash", "/api/user/context/hash", {"json": {"user_context_hash": "abcd1234"}}),
    ("dodo_checkout", "/api/checkout/dodo", {"json": {"product_id": "prod_archive_test"}}),
    ("dodo_cancel", "/api/subscription/cancel", {}),
    ("lemonsqueezy_checkout", "/api/checkout", {"json": {"variant_id": "1"}}),
    ("lemonsqueezy_webhook", "/api/webhooks/lemonsqueezy",
     {"content": b'{"meta": {}}', "headers": {"X-Signature": "00"}}),
]


# ── harness ────────────────────────────────────────────────────────────────

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "testserver", "testclient"}


def _host(address):
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address)


@pytest.fixture(autouse=True)
def _outbound(monkeypatch):
    """Block every non-loopback DNS lookup and connect; record each attempt.
    Loopback stays open because Windows builds asyncio's self-pipe from a
    loopback socketpair. Also dummies the vendor keys handlers read per
    request, so even a resolved call could not authenticate."""
    attempts = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _getaddrinfo(host, *args, **kwargs):
        if host is not None and str(host) not in _LOOPBACK:
            attempts.append(("dns", str(host)))
            raise OSError(f"outbound network blocked by test_archive_mode: {host}")
        return real_getaddrinfo(host, *args, **kwargs)

    def _connect(self, address):
        if _host(address) not in _LOOPBACK:
            attempts.append(("connect", _host(address)))
            raise OSError(f"outbound network blocked by test_archive_mode: {address}")
        return real_connect(self, address)

    def _connect_ex(self, address):
        if _host(address) not in _LOOPBACK:
            attempts.append(("connect_ex", _host(address)))
            raise OSError(f"outbound network blocked by test_archive_mode: {address}")
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    for key in ("DODO_API_KEY", "CLERK_SECRET_KEY", "LEMON_SQUEEZY_API_KEY"):
        monkeypatch.setenv(key, "test-dummy-not-a-key")
    return attempts


@pytest.fixture
def guard_calls(monkeypatch):
    """Replace the two LLM guards with recorders (they would call OpenAI)."""
    import api.middleware.guards as guards
    calls = []

    async def _intent(text):
        calls.append(("check_medical_intent", text))
        return True, ""

    async def _injection(text):
        calls.append(("check_indirect_injection", text))
        return False, ""

    monkeypatch.setattr(guards, "check_medical_intent", _intent)
    monkeypatch.setattr(guards, "check_indirect_injection", _injection)
    return calls


@pytest.fixture
def app_db():
    """Per-test in-memory DB (StaticPool) with the real schema, wired into the
    app via dependency_overrides, seeded with a PRO user that holds credits
    AND a live-looking Dodo subscription id, plus one anonymous usage row —
    so "unchanged" is a real reading, not a default."""
    import api.server as server
    from api.database.sql_db import Base, get_db
    from api.models.sql_models import AnonymousUsage, UserUsage
    from api.services.anonymous_identity import today_utc

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    server.app.dependency_overrides[get_db] = _override_get_db
    with TestSession() as db:
        db.add(UserUsage(clerk_user_id=USER_ID, plan_type="pro",
                         credits_used_today=SEED_USER_CREDITS,
                         dodo_customer_id="cus_archive_test",
                         dodo_subscription_id=SEED_SUB_ID))
        db.add(AnonymousUsage(anon_id=_anon_id(), credits_used_today=SEED_ANON_CREDITS,
                              last_reset_date=today_utc()))
        db.commit()
    try:
        yield TestSession
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _anon_id():
    from api.services.anonymous_identity import derive_anon_id
    return derive_anon_id("testclient", ANON_FP)


def _client():
    import api.server as server
    from fastapi.testclient import TestClient
    return TestClient(server.app)  # no context manager → no lifespan side effects


def _snapshot(TestSession):
    """Row count of EVERY table + the seeded rows' mutable fields."""
    from api.database.sql_db import Base
    from api.models.sql_models import AnonymousUsage, UserUsage
    with TestSession() as db:
        counts = {t.name: db.execute(select(func.count()).select_from(t)).scalar()
                  for t in Base.metadata.sorted_tables}
        u = db.query(UserUsage).filter(UserUsage.clerk_user_id == USER_ID).one()
        a = db.query(AnonymousUsage).filter(AnonymousUsage.anon_id == _anon_id()).one()
        seeded = {
            "user_credits": u.credits_used_today, "plan_type": u.plan_type,
            "dodo_subscription_id": u.dodo_subscription_id,
            "dodo_customer_id": u.dodo_customer_id, "anon_credits": a.credits_used_today,
        }
    return counts, seeded


# ── 1. every retired route: 410, generic body, zero work ──────────────────

@pytest.mark.parametrize("name,path,kwargs", BLOCKED, ids=[b[0] for b in BLOCKED])
def test_archived_route_returns_410_and_does_no_work(
        name, path, kwargs, monkeypatch, app_db, guard_calls, _outbound):
    monkeypatch.setenv("ARCHIVE_MODE", "true")
    before = _snapshot(app_db)

    resp = _client().post(path, **kwargs)

    assert resp.status_code == 410, f"{name}: expected 410, got {resp.status_code} {resp.text[:200]}"
    assert resp.json() == ARCHIVED_BODY, "one generic body on every retired route (Rule 5)"
    after = _snapshot(app_db)
    assert after[0] == before[0], f"{name}: a table's row count changed — the gate let a write through"
    assert after[1] == before[1], f"{name}: a seeded row changed (credits / plan / subscription id)"
    assert guard_calls == [], f"{name}: the LLM guards ran — the gate fired after guard work"
    assert _outbound == [], f"{name}: an outbound call was attempted ({_outbound}) — vendor/LLM work happened"


def test_archived_route_410_also_for_anonymous_caller(monkeypatch, app_db, guard_calls, _outbound):
    """Verify is reachable by L0 too; the anonymous path must be gated the same
    way (no anon credit consumed, no guard run)."""
    monkeypatch.setenv("ARCHIVE_MODE", "true")
    before = _snapshot(app_db)
    resp = _client().post("/api/verify", json={"drugs": ["Metformin", "Warfarin"]},
                          headers={"X-Anon-Fingerprint": ANON_FP})
    assert resp.status_code == 410
    assert resp.json() == ARCHIVED_BODY
    assert _snapshot(app_db) == before
    assert guard_calls == [] and _outbound == []


# ── 2. Research stays up and stops collecting ─────────────────────────────

class _FakeGenerator:
    _fallback_model = "test-fallback-model"
    model = "test-model"

    async def generate_stream(self, **kwargs):
        from api.models.schemas import StreamEvent, StreamEventType
        yield StreamEvent(type=StreamEventType.ANSWER,
                          content="## Summary — English\n\nReduce the dose below eGFR 45 [1].")
        yield StreamEvent(type=StreamEventType.CITATIONS, content=[])
        yield StreamEvent(type=StreamEventType.DONE)


class _FakeRetriever:
    async def retrieve(self, **kwargs):
        return [], "ok"


def _post_research(monkeypatch, TestSession, *, anonymous):
    import api.server as server
    from api.models.sql_models import AnonymousUsage, ChatHistory, UserUsage

    async def _judge_noop(*args, **kwargs):
        return None

    monkeypatch.setattr(server, "retriever", _FakeRetriever())
    monkeypatch.setattr(server, "generator", _FakeGenerator())
    monkeypatch.setattr(server, "_run_judge_background", _judge_noop)
    headers = {"X-Anon-Fingerprint": ANON_FP} if anonymous else {}
    resp = _client().post("/api/research", json={
        "question": "Is metformin safe in moderate renal impairment?",
        "response_language": "en",
    }, headers=headers)
    with TestSession() as db:
        rows = db.query(ChatHistory).count()
        user = db.query(UserUsage).filter(UserUsage.clerk_user_id == USER_ID).one()
        anon = db.query(AnonymousUsage).filter(AnonymousUsage.anon_id == _anon_id()).one()
        return resp, rows, user.credits_used_today, anon.credits_used_today


def test_research_is_not_blocked_and_writes_no_history_signed_in(monkeypatch, app_db, guard_calls):
    monkeypatch.setenv("ARCHIVE_MODE", "true")
    resp, rows, user_credits, _ = _post_research(monkeypatch, app_db, anonymous=False)
    assert resp.status_code == 200, resp.text[:200]
    assert '"type": "answer"' in resp.text and '"type": "done"' in resp.text
    assert user_credits == SEED_USER_CREDITS + 3, \
        "control: the stream reached DONE and charged — so 'no row' below is not vacuous"
    assert rows == 0, "archive mode must not write a ChatHistory row for a signed-in user"


def test_research_is_not_blocked_anonymous_and_writes_no_history(monkeypatch, app_db, guard_calls):
    monkeypatch.setenv("ARCHIVE_MODE", "true")
    resp, rows, _, anon_credits = _post_research(monkeypatch, app_db, anonymous=True)
    assert resp.status_code == 200, resp.text[:200]
    assert '"type": "answer"' in resp.text
    assert anon_credits == SEED_ANON_CREDITS + 3, "control: the anon stream charged the anon quota"
    assert rows == 0


def test_research_flag_off_still_writes_history_control(monkeypatch, app_db, guard_calls):
    """CONTROL: the same harness with the flag OFF does write the row, so the
    archive-mode 'rows == 0' is the flag's effect, not the harness's."""
    monkeypatch.delenv("ARCHIVE_MODE", raising=False)
    resp, rows, user_credits, _ = _post_research(monkeypatch, app_db, anonymous=False)
    assert resp.status_code == 200
    assert user_credits == SEED_USER_CREDITS + 3
    assert rows == 1


# ── 3. what archive mode keeps ─────────────────────────────────────────────

KEPT = [
    ("POST", "/api/webhook/dodo", {"content": b"{}"}),
    ("POST", "/api/webhooks/clerk", {"content": b"{}"}),
    ("GET", "/health", {}),
    ("GET", "/api/history", {}),
]


@pytest.mark.parametrize("method,path,kwargs", KEPT, ids=[k[1] for k in KEPT])
def test_kept_routes_are_not_gated(method, path, kwargs, monkeypatch, app_db, _outbound):
    """The Dodo webhook must keep landing cancellation events after archive;
    an unsigned request is rejected by the handler's own signature check
    (401/500), never by the archive gate."""
    monkeypatch.setenv("ARCHIVE_MODE", "true")
    resp = _client().request(method, path, **kwargs)
    assert resp.status_code != 410, f"{path} is on the keep list but answered 410"
    try:
        body = resp.json()
    except ValueError:
        body = None
    assert body != ARCHIVED_BODY


# ── 4. the gate is inert when the flag is off ─────────────────────────────

@pytest.mark.parametrize("flag", [None, "false", ""], ids=["unset", "false", "empty"])
def test_flag_off_blocked_route_behaves_as_before(flag, monkeypatch, app_db, _outbound):
    """Flag off: /api/subscription/cancel runs its real handler. A user with
    NO subscription id gets the handler's own 404 — not 410, and no vendor
    call (the 404 branch precedes the Dodo request)."""
    from api.models.sql_models import UserUsage
    if flag is None:
        monkeypatch.delenv("ARCHIVE_MODE", raising=False)
    else:
        monkeypatch.setenv("ARCHIVE_MODE", flag)
    with app_db() as db:
        db.query(UserUsage).filter(UserUsage.clerk_user_id == USER_ID).update(
            {"dodo_subscription_id": None})
        db.commit()
    resp = _client().post("/api/subscription/cancel")
    assert resp.status_code == 404
    assert resp.json() == {"error": "No active subscription found"}
    assert _outbound == []


# ── 5. ANON_DAILY_BUDGET_USD ───────────────────────────────────────────────

def test_budget_env_parsing():
    from api.services.cost_guard import _budget_from_env
    assert _budget_from_env(None) == 2.00, "unset keeps Decision 001 v0.3 A7 ($2/day)"
    assert _budget_from_env("") == 2.00
    assert _budget_from_env("  ") == 2.00
    assert _budget_from_env("0.5") == 0.5
    assert _budget_from_env("0") == 0.0, "0 is a valid kill switch: every anon request is over budget"
    for bad in ("abc", "-1", "nan", "inf", "$2"):
        with pytest.raises(ValueError):
            _budget_from_env(bad)


@pytest.mark.parametrize("raw,expect_status", [(None, 200), ("0", 503)], ids=["default", "zero"])
def test_budget_value_is_the_one_that_gates_anon_research(
        raw, expect_status, monkeypatch, app_db, guard_calls):
    """The parsed value is what the anonymous Research gate compares against:
    default $2.00 lets the request through; a $0 cap answers 503
    budget_exceeded BEFORE the stream and consumes no anon credit.
    HARNESS BOUNDARY (stated, not hidden): check_anonymous_budget sums today's
    rows via CAST(created_at AS DATE), which SQLite evaluates numerically, so
    "spent" always reads 0 here — a mid-range case ($0.60 vs a $0.50 cap) is
    not measurable on this harness; the 0-vs-default pair is."""
    import api.services.cost_guard as cost_guard
    monkeypatch.delenv("ARCHIVE_MODE", raising=False)
    monkeypatch.setattr(cost_guard, "ANONYMOUS_DAILY_BUDGET_USD", cost_guard._budget_from_env(raw))
    resp, _rows, _, anon_credits = _post_research(monkeypatch, app_db, anonymous=True)
    assert resp.status_code == expect_status, resp.text[:200]
    if expect_status == 503:
        assert resp.json() == {"detail": {"type": "budget_exceeded"}}
        assert anon_credits == SEED_ANON_CREDITS, "a budget-blocked request must not be charged"
    else:
        assert anon_credits == SEED_ANON_CREDITS + 3


# ── 6. deploy plumbing (fly.toml + Dockerfile) ─────────────────────────────

def test_fly_toml_turns_archive_mode_on_and_dockerfile_carries_the_build_arg():
    """If archive mode is ever deliberately lifted, this test is the place to
    change — it pins the archived deployment, by design."""
    from api.services.cost_guard import _budget_from_env
    fly = tomllib.loads((ROOT / "fly.toml").read_text(encoding="utf-8"))
    assert fly["env"]["ARCHIVE_MODE"] == "true"
    assert _budget_from_env(fly["env"]["ANON_DAILY_BUDGET_USD"]) == 0.5
    assert fly["build"]["args"]["NEXT_PUBLIC_ARCHIVE_MODE"] == "true"

    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    build_at = next(i for i, ln in enumerate(lines) if ln.strip() == "RUN npm run build")
    arg_at = [i for i, ln in enumerate(lines) if ln.strip() == "ARG NEXT_PUBLIC_ARCHIVE_MODE"]
    env_at = [i for i, ln in enumerate(lines)
              if ln.strip() == "ENV NEXT_PUBLIC_ARCHIVE_MODE=$NEXT_PUBLIC_ARCHIVE_MODE"]
    assert arg_at and arg_at[0] < build_at, "the build arg must be declared before `npm run build`"
    assert env_at and arg_at[0] < env_at[0] < build_at, \
        "the build arg must be exported as ENV before `npm run build` or Next.js never sees it"
