# -*- coding: utf-8 -*-
"""Executable coverage for BOTH payment webhooks — dodo_webhook + lemonsqueezy_webhook.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
A paying user must receive pro, and a cancelled/expired/refunded user must lose
it. Both directions fail SILENTLY: the handler returns 200 to the provider
either way, so the provider dashboard shows delivery success while the account
state is wrong (TECH_DEBT 2026-08-21 payment-coverage filing). Every test here
asserts the user_usage ROW, not the response body — the response is what lies.

The Dodo idempotency tests additionally pin the 2026-08-25 fix: the key is now
the Standard Webhooks `webhook-id` header. Real Dodo payloads carry NEITHER
`data.id` NOR a top-level `id` (prod evidence: top-level keys are
business_id/data/timestamp/type; data carries subscription_id, not id), so the
old payload-derived key always fell through to a locally-generated value
(epoch-ms in 32a82a4, uuid4 after 4443855) — every replay got a fresh key and
`already_processed` could never fire. The stored double-prefix rows on prod
(`dodo_dodo_<epoch-ms>`) are the residue of that fallback.

FIXTURE SHAPE — real payloads, not invented ones
------------------------------------------------
Dodo fixtures mirror the prod-observed delivery shape: top-level
business_id/data/timestamp/type; data.subscription_id, data.status,
data.metadata.clerk_user_id, data.customer.{email,customer_id}. Deliberately NO
data.id, NO top-level id, NO data.clerk_user_id — which means the handler
exercises the production identity join (customer email → Clerk lookup) even
under TEST_MODE, because the TEST_MODE bypass reads data.clerk_user_id, a key
real payloads do not have. The Clerk HTTP call is faked by monkeypatching
httpx.AsyncClient (no mock-HTTP dependency is installed; car brief prefers
patching over adding one — the handler's lookup is inline, so the class attr
on the httpx module is the narrowest seam).

IMPORT-ORDER CONSTRAINT (documented per car brief)
--------------------------------------------------
api/server.py binds TEST_MODE at import (server.py:318) and
api/database/sql_db.py binds DATABASE_URL into the engine at import. Both env
vars are therefore set BEFORE the first `import api.server` in this process —
same convention as test_share_local_tombstone / test_verify_tfda_payload, and
this file sorts alphabetically ahead of both, so under full-suite collection it
IS the first importer. TEST_MODE stays true throughout: it bypasses the
rate-limit middleware, whose /api/webhook* buckets (30 req/60 s, process-global
_rate_store) would otherwise leak state across tests; the identity join under
test is not TEST_MODE-gated (see above). The app's own engine is never used —
every test overrides get_db with a per-test in-memory engine (StaticPool +
check_same_thread=False so the handler thread and the assertion session share
one connection; in-repo precedent: tests/models/test_user_profile.py fixture,
chosen over the global-engine pattern per the recon baton's pooling caveat).

Run: python -m pytest tests/test_payment_webhooks.py -q
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import api.server as server  # noqa: E402
from api.database.sql_db import Base, get_db  # noqa: E402
from api.models.sql_models import UserUsage, WebhookEvent  # noqa: E402

CLERK_USER = "user_test_payment_webhooks"
CUSTOMER_EMAIL = "payer@example.com"
# Standard Webhooks secret: whsec_ + base64(raw key), as Dodo issues them.
DODO_SECRET = "whsec_" + base64.b64encode(b"vela-test-dodo-webhook-key-32byte").decode()
LS_SECRET = "vela-test-ls-signing-secret"


# ---------------------------------------------------------------------------
# Fixtures: per-test DB via dependency override; secrets; faked Clerk lookup
# ---------------------------------------------------------------------------

@pytest.fixture()
def sessions():
    """Per-test in-memory engine, dependency-overridden into the app.

    StaticPool = one shared connection, so rows committed by the handler's
    session are visible to assertion sessions opened afterwards.
    """
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestingSession = sessionmaker(bind=eng, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    server.app.dependency_overrides[get_db] = override_get_db
    yield TestingSession
    server.app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(sessions, monkeypatch):
    """TestClient without context manager — no lifespan side effects
    (precedent: test_verify_tfda_payload). Secrets injected per-test; both
    handlers read them per-request via os.getenv, so no re-import is needed.
    """
    monkeypatch.setenv("DODO_WEBHOOK_SECRET", DODO_SECRET)
    monkeypatch.setenv("LEMON_SQUEEZY_SIGNING_SECRET", LS_SECRET)
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClerkClient)
    return TestClient(server.app)


class _FakeClerkResponse:
    status_code = 200

    def json(self):
        return [{"id": CLERK_USER}]


class _FakeClerkClient:
    """Stands in for httpx.AsyncClient inside dodo_webhook's Clerk email
    lookup. Any GET answers with one matching Clerk user."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None, timeout=None):
        return _FakeClerkResponse()


def _seed_user(TestingSession, plan="pro", dodo_sub="sub_seed_1"):
    s = TestingSession()
    s.add(UserUsage(clerk_user_id=CLERK_USER, plan_type=plan,
                    dodo_subscription_id=dodo_sub))
    s.commit()
    s.close()


def _usage_row(TestingSession):
    s = TestingSession()
    row = s.query(UserUsage).filter(UserUsage.clerk_user_id == CLERK_USER).first()
    s.close()
    return row


def _webhook_rows(TestingSession):
    s = TestingSession()
    rows = s.query(WebhookEvent).all()
    s.close()
    return rows


# ---------------------------------------------------------------------------
# Dodo helpers — sign_webhook() salvaged from scripts/smoke_webhook_cancel.py
# (the correct Standard Webhooks signer; the live-backend orchestration around
# it was deliberately NOT converted — see the recon baton §2.3).
# ---------------------------------------------------------------------------

def dodo_payload(event_type, sub_id="sub_test_1"):
    """Prod-observed Dodo delivery shape. No data.id, no top-level id,
    no data.clerk_user_id — see module docstring."""
    return {
        "business_id": "bus_test_1",
        "timestamp": "2026-08-25T00:00:00Z",
        "type": event_type,
        "data": {
            "payload_type": "Subscription",
            "subscription_id": sub_id,
            "status": event_type.split(".")[-1],
            "metadata": {"clerk_user_id": CLERK_USER},
            "customer": {"email": CUSTOMER_EMAIL, "customer_id": "cus_test_1"},
        },
    }


def sign_dodo(payload_bytes, webhook_id, secret=DODO_SECRET, ts=None):
    ts = str(int(time.time()) if ts is None else ts)
    raw = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    signed = f"{webhook_id}.{ts}.".encode() + payload_bytes
    sig = base64.b64encode(
        hmac.new(base64.b64decode(raw), signed, hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json",
        "webhook-id": webhook_id,
        "webhook-timestamp": ts,
        "webhook-signature": f"v1,{sig}",
    }


def post_dodo(client, event_type, webhook_id, sub_id="sub_test_1", **sign_kw):
    body = json.dumps(dodo_payload(event_type, sub_id=sub_id)).encode()
    return client.post("/api/webhook/dodo", content=body,
                       headers=sign_dodo(body, webhook_id, **sign_kw))


# ---------------------------------------------------------------------------
# Dodo — signature verification
# ---------------------------------------------------------------------------

def test_dodo_valid_signature_accepted(client, sessions):
    resp = post_dodo(client, "subscription.active", "msg_sig_ok")
    assert resp.status_code == 200


def test_dodo_missing_signature_headers_rejected(client, sessions):
    body = json.dumps(dodo_payload("subscription.active")).encode()
    resp = client.post("/api/webhook/dodo", content=body,
                       headers={"Content-Type": "application/json"})
    assert resp.status_code == 401
    assert _webhook_rows(sessions) == [] and _usage_row(sessions) is None


def test_dodo_bad_hmac_rejected(client, sessions):
    wrong = "whsec_" + base64.b64encode(b"some-entirely-different-key-32-b!").decode()
    resp = post_dodo(client, "subscription.active", "msg_bad_sig", secret=wrong)
    assert resp.status_code == 401
    assert _webhook_rows(sessions) == [] and _usage_row(sessions) is None


def test_dodo_stale_timestamp_rejected(client, sessions):
    resp = post_dodo(client, "subscription.active", "msg_stale",
                     ts=int(time.time()) - 301)
    assert resp.status_code == 401
    assert _webhook_rows(sessions) == []


def test_dodo_missing_secret_500(client, sessions, monkeypatch):
    monkeypatch.setenv("DODO_WEBHOOK_SECRET", "")
    resp = post_dodo(client, "subscription.active", "msg_no_secret")
    assert resp.status_code == 500
    assert _webhook_rows(sessions) == []


# ---------------------------------------------------------------------------
# Dodo — idempotency (the fires-proof of the 2026-08-25 key fix)
# ---------------------------------------------------------------------------

def test_dodo_replay_of_same_delivery_is_idempotent(client, sessions):
    """The fix's proof: an identical redelivery (same webhook-id, same body,
    same signature) must hit `already_processed` and write exactly ONE
    webhook_events row. On the pre-fix payload-derived key this FAILS: real
    payloads carry no data.id / id, every delivery minted a fresh local key,
    and the replay was processed as a brand-new event."""
    body = json.dumps(dodo_payload("subscription.active")).encode()
    headers = sign_dodo(body, "msg_replay_1")

    first = client.post("/api/webhook/dodo", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "ok"

    second = client.post("/api/webhook/dodo", content=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"

    rows = _webhook_rows(sessions)
    assert len(rows) == 1, f"replay must not add a second row: {[r.event_id for r in rows]}"
    assert rows[0].event_id == "dodo_msg_replay_1"  # dodo_ prefix retained
    assert _usage_row(sessions).plan_type == "pro"


def test_dodo_distinct_deliveries_same_subscription_both_process(client, sessions):
    """Business rule: cancelling is a DIFFERENT delivery about the SAME
    subscription — it must never be swallowed by the activation's idempotency
    record. Keying on webhook-id guarantees this; a payload-derived key equal
    for both deliveries (the recon baton §5.1 risk) would eat the cancel and
    leave a cancelled user on pro, silently."""
    r1 = post_dodo(client, "subscription.active", "msg_seq_active", sub_id="sub_seq")
    r2 = post_dodo(client, "subscription.cancelled", "msg_seq_cancel", sub_id="sub_seq")
    assert r1.json()["status"] == "ok" and r2.json()["status"] == "ok"

    row = _usage_row(sessions)
    assert row.plan_type == "free", "the cancel was swallowed — user kept pro"
    assert row.dodo_subscription_id is None
    assert sorted(r.event_id for r in _webhook_rows(sessions)) == \
        ["dodo_msg_seq_active", "dodo_msg_seq_cancel"]


# ---------------------------------------------------------------------------
# Dodo — plan flips (assignment sites re-derived at HEAD after the fix:
# server.py:2167 → pro, server.py:2170 → free)
# ---------------------------------------------------------------------------

def test_dodo_active_flips_user_to_pro(client, sessions):
    """A paying user must receive pro — the silent-failure direction that ends
    in a support ticket from someone already charged."""
    resp = post_dodo(client, "subscription.active", "msg_up_1", sub_id="sub_up_1")
    assert resp.status_code == 200

    row = _usage_row(sessions)
    assert row is not None, "handler must create the usage row for a new payer"
    assert row.plan_type == "pro"
    assert row.dodo_subscription_id == "sub_up_1"
    assert row.dodo_customer_id == "cus_test_1"


@pytest.mark.parametrize("event", ["subscription.cancelled",
                                   "subscription.expired",
                                   "subscription.failed"])
def test_dodo_terminal_events_downgrade_to_free(client, sessions, event):
    """A cancelled/expired/failed user must lose pro — the unbilled-service
    direction no ledger would show. customer_id is kept for re-subscribe;
    subscription_id must clear."""
    _seed_user(sessions, plan="pro", dodo_sub="sub_seed_1")
    resp = post_dodo(client, event, f"msg_down_{event}")
    assert resp.status_code == 200

    row = _usage_row(sessions)
    assert row.plan_type == "free"
    assert row.dodo_subscription_id is None


@pytest.mark.parametrize("event", ["subscription.updated",
                                   "subscription.renewed",
                                   "payment.succeeded"])
def test_dodo_unhandled_events_ignored_without_plan_change(client, sessions, event):
    """Events outside handled_events must not touch the plan. A webhook_events
    row IS written — at HEAD the insert precedes the ignored-return
    (server.py, unhandled branch; unchanged since 32a82a4), which CONTRADICTS
    the early-return hypothesis in this car's brief: the absence of monthly
    updated/renewed/payment.succeeded rows on prod is NOT explained by this
    code path."""
    _seed_user(sessions, plan="pro")
    resp = post_dodo(client, event, f"msg_ign_{event}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    assert _usage_row(sessions).plan_type == "pro", "unhandled event changed the plan"
    rows = _webhook_rows(sessions)
    assert [r.event_id for r in rows] == [f"dodo_msg_ign_{event}"]
    assert rows[0].event_type == event


# ---------------------------------------------------------------------------
# LemonSqueezy helpers
# ---------------------------------------------------------------------------

def ls_payload(event_name, event_uuid, renews_at="2026-09-25T00:00:00Z"):
    return {
        "meta": {
            "event_name": event_name,
            "uuid": event_uuid,
            "custom_data": {"clerk_user_id": CLERK_USER},
        },
        "data": {
            "type": "subscriptions",
            "id": "424242",
            "attributes": {"variant_id": "77", "renews_at": renews_at},
        },
    }


def post_ls(client, event_name, event_uuid, secret=LS_SECRET, omit_sig=False,
            payload=None):
    body = json.dumps(payload or ls_payload(event_name, event_uuid)).encode()
    headers = {"Content-Type": "application/json"}
    if not omit_sig:
        headers["X-Signature"] = hmac.new(secret.encode(), body,
                                          hashlib.sha256).hexdigest()
    return client.post("/api/webhooks/lemonsqueezy", content=body, headers=headers)


# ---------------------------------------------------------------------------
# LemonSqueezy — signature verification
# ---------------------------------------------------------------------------

def test_ls_missing_signature_header_rejected(client, sessions):
    resp = post_ls(client, "subscription_created", "evt-ls-nosig", omit_sig=True)
    assert resp.status_code == 401
    assert _webhook_rows(sessions) == [] and _usage_row(sessions) is None


def test_ls_bad_signature_rejected(client, sessions):
    resp = post_ls(client, "subscription_created", "evt-ls-badsig",
                   secret="wrong-secret")
    assert resp.status_code == 401
    assert _webhook_rows(sessions) == [] and _usage_row(sessions) is None


def test_ls_missing_secret_500(client, sessions, monkeypatch):
    monkeypatch.setenv("LEMON_SQUEEZY_SIGNING_SECRET", "")
    resp = post_ls(client, "subscription_created", "evt-ls-nosecret")
    assert resp.status_code == 500
    assert _webhook_rows(sessions) == []


# ---------------------------------------------------------------------------
# LemonSqueezy — idempotency (stable meta.uuid key; pins existing behavior)
# ---------------------------------------------------------------------------

def test_ls_replay_same_uuid_already_processed(client, sessions):
    first = post_ls(client, "subscription_created", "evt-ls-replay")
    assert first.json()["status"] == "ok"

    second = post_ls(client, "subscription_created", "evt-ls-replay")
    assert second.json()["status"] == "already_processed"

    rows = _webhook_rows(sessions)
    assert len(rows) == 1 and rows[0].event_id == "evt-ls-replay"
    assert _usage_row(sessions).plan_type == "pro"


# ---------------------------------------------------------------------------
# LemonSqueezy — plan flips (assignment sites at HEAD: server.py:2000 → pro,
# :2013 cancelled/expired → free, :2016 refunded → free, :2018-2020
# payment_failed grace no-op)
# ---------------------------------------------------------------------------

def test_ls_created_flips_user_to_pro(client, sessions):
    """A paying user must receive pro (site :2000), with the subscription
    identifiers the cancel path later depends on."""
    resp = post_ls(client, "subscription_created", "evt-ls-up")
    assert resp.status_code == 200

    row = _usage_row(sessions)
    assert row.plan_type == "pro"
    assert row.lemon_subscription_id == "424242"
    assert row.lemon_variant_id == "77"
    assert row.current_period_end is not None


@pytest.mark.parametrize("event", ["subscription_cancelled",
                                   "subscription_expired"])
def test_ls_cancelled_expired_downgrade_to_free(client, sessions, event):
    """Site :2013 — a cancelled/expired user must lose pro."""
    _seed_user(sessions, plan="pro", dodo_sub=None)
    resp = post_ls(client, event, f"evt-ls-{event}")
    assert resp.status_code == 200
    assert _usage_row(sessions).plan_type == "free"


def test_ls_refund_downgrades_to_free(client, sessions):
    """Site :2016 — a refunded payment must not leave the user on pro."""
    _seed_user(sessions, plan="pro", dodo_sub=None)
    resp = post_ls(client, "subscription_payment_refunded", "evt-ls-refund")
    assert resp.status_code == 200
    assert _usage_row(sessions).plan_type == "free"


def test_ls_payment_failed_is_grace_period_no_downgrade(client, sessions):
    """Sites :2018-2020 — payment_failed is a deliberate grace-period no-op
    (unlike Dodo, whose subscription.failed downgrades immediately — the
    cross-provider asymmetry recorded in the recon baton §5.2)."""
    _seed_user(sessions, plan="pro", dodo_sub=None)
    resp = post_ls(client, "subscription_payment_failed", "evt-ls-grace")
    assert resp.status_code == 200
    assert _usage_row(sessions).plan_type == "pro"


def test_ls_unknown_event_recorded_and_ok_without_plan_change(client, sessions):
    """LS has no handled_events tuple: an unknown event falls through every
    branch, is still recorded, and answers "ok" (where Dodo answers
    "ignored") — behavior pinned so a change is a decision, not drift."""
    _seed_user(sessions, plan="pro", dodo_sub=None)
    resp = post_ls(client, "order_created", "evt-ls-unknown")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert _usage_row(sessions).plan_type == "pro"
    assert [r.event_id for r in _webhook_rows(sessions)] == ["evt-ls-unknown"]


def test_ls_missing_clerk_user_id_acknowledged_but_unrecorded(client, sessions):
    """A delivery without meta.custom_data.clerk_user_id returns "ignored"
    BEFORE the webhook_events insert — acknowledged to the provider yet
    invisible to any later replay audit (recon baton §5.4). Pinned as-is."""
    payload = ls_payload("subscription_created", "evt-ls-nouser")
    del payload["meta"]["custom_data"]["clerk_user_id"]
    resp = post_ls(client, "subscription_created", "evt-ls-nouser",
                   payload=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert _webhook_rows(sessions) == [] and _usage_row(sessions) is None
