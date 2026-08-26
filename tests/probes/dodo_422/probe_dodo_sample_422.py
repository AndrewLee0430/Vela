# -*- coding: utf-8 -*-
"""Probe: classify the prod 422 on POST /api/webhook/dodo (2026-08-25/26 deploy car, Phase 0).

LIVE EVIDENCE BEING CLASSIFIED
------------------------------
Dodo Dashboard -> Webhooks -> Testing tab sent its subscription.active SAMPLE to
https://vela.an-tho.com/api/webhook/dodo -> 422, twice (auto-retry), ~1-3 s each.
Sample's handler-relevant fields (recorded in the car): top-level
business_id/data/timestamp/type; data.metadata == {} (NO clerk_user_id);
data.customer.email "test@acme.com"; payment_method_id null; NO data.id, NO
top-level id.

WHAT CAN 422 ON THIS ROUTE (derived from code, not assumed)
-----------------------------------------------------------
The handler signature is `dodo_webhook(request: Request, db=Depends(get_db))`
(api/server.py:2032-2033) — NO declared Pydantic body model, so FastAPI's
pre-handler RequestValidationError 422 path DOES NOT EXIST for this route, and
no middleware returns 422. The only 422s are two explicit JSONResponse sites,
both AFTER signature verification:
  - server.py:2128  {"detail": "No customer email"}   — customer.email absent
  - server.py:2150  {"detail": "Clerk user not found"} — email present but the
    live GET https://api.clerk.com/v1/users?email_address=<email> returns no
    user (or the lookup raises; exception is swallowed at :2145-2146).
The handler NEVER reads data.metadata — identity comes solely from
customer.email -> Clerk lookup (:2107-2150). The ~1-3 s duration is that live
Clerk round-trip.

FIDELITY OF THIS REPRODUCTION
-----------------------------
- Signer + real-shape fixture reused from tests/test_payment_webhooks.py.
- Clerk is faked PROD-SHAPED: only the known payer email resolves; any other
  email (test@acme.com included) answers an empty user list — which is what
  api.clerk.com answers for an email with no Clerk account.
- TEST_MODE=true is required by the harness (rate-limit bypass) but does NOT
  short-circuit the identity join here: the TEST_MODE bypass reads
  data.clerk_user_id / top-level clerk_user_id / customer.clerk_user_id
  (server.py:2112-2117), none of which exist in the sample or in real payloads
  (real payloads carry data.metadata.clerk_user_id, which the bypass does not
  read either). Every scenario below exercises the production identity join.
- The sample payload is reconstructed from the fields recorded in the car; the
  handler reads only type / data.customer / data.subscription_id / data.id /
  data.clerk_user_id / clerk_user_id, and every one of those is exact here, so
  handler behavior is fully determined.

Run: python tests/probes/dodo_422/probe_dodo_sample_422.py
Writes: tests/probes/dodo_422/probe_dodo_sample_422_result.json
Exit code 0 iff every scenario matched its expectation.
"""
import copy
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _REPO)
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import api.server as server  # noqa: E402
from api.database.sql_db import Base, get_db  # noqa: E402
from tests.test_payment_webhooks import (  # noqa: E402
    CLERK_USER, CUSTOMER_EMAIL, DODO_SECRET, dodo_payload, sign_dodo,
)


class _Resp:
    status_code = 200

    def __init__(self, users):
        self._users = users

    def json(self):
        return self._users


class _ProdShapedClerk:
    """Prod-shaped Clerk fake: resolves ONLY the known payer email; every other
    email answers [] — api.clerk.com's answer for an account-less email such as
    the sample's test@acme.com. `fail=True` simulates a Clerk outage (the
    handler swallows the exception at server.py:2145-2146)."""
    fail = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None, timeout=None):
        if _ProdShapedClerk.fail:
            raise httpx.ConnectError("simulated Clerk outage")
        email = (params or {}).get("email_address", "")
        return _Resp([{"id": CLERK_USER}] if email == CUSTOMER_EMAIL else [])


def dodo_testing_sample():
    """The Testing-tab subscription.active sample, per the delivery evidence:
    metadata {}, email test@acme.com, payment_method_id null, no data.id,
    no top-level id."""
    return {
        "business_id": "bus_sample",
        "timestamp": "2026-08-25T00:00:00Z",
        "type": "subscription.active",
        "data": {
            "payload_type": "Subscription",
            "subscription_id": "sub_sample",
            "status": "active",
            "customer": {"customer_id": "cus_sample",
                         "email": "test@acme.com",
                         "name": "Test Acme"},
            "metadata": {},
            "payment_method_id": None,
        },
    }


def main():
    eng = create_engine("sqlite://",
                        connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    Base.metadata.create_all(eng)
    TestingSession = sessionmaker(bind=eng, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    server.app.dependency_overrides[get_db] = override_get_db
    os.environ["DODO_WEBHOOK_SECRET"] = DODO_SECRET
    _real_async_client = httpx.AsyncClient
    httpx.AsyncClient = _ProdShapedClerk
    client = TestClient(server.app)

    def post_signed(payload, webhook_id):
        body = json.dumps(payload).encode()
        return client.post("/api/webhook/dodo", content=body,
                           headers=sign_dodo(body, webhook_id))

    def mutated(event, **changes):
        p = copy.deepcopy(dodo_payload(event, sub_id=f"sub_{changes.get('_tag', 'mut')}"))
        if changes.get("metadata_empty"):
            p["data"]["metadata"] = {}
        if changes.get("payment_method_null"):
            p["data"]["payment_method_id"] = None
        if changes.get("email"):
            p["data"]["customer"]["email"] = changes["email"]
        if changes.get("drop_email"):
            del p["data"]["customer"]["email"]
        return p

    scenarios = []

    def run(name, note, resp, expect_status, expect_detail=None):
        got = {"status": resp.status_code, "body": resp.json()}
        ok = got["status"] == expect_status and (
            expect_detail is None or got["body"].get("detail") == expect_detail)
        scenarios.append({"name": name, "note": note,
                          "expected": {"status": expect_status, "detail": expect_detail},
                          "got": got, "matched": ok})
        return ok

    # 1. The exact sample, correctly signed — the prod 422 itself.
    run("sample_signed",
        "Testing-tab sample verbatim, valid signature (prod repro)",
        post_signed(dodo_testing_sample(), "msg_probe_sample"),
        422, "Clerk user not found")

    # 2. Ordering: same sample UNSIGNED — HMAC precedes both 422 sites.
    body = json.dumps(dodo_testing_sample()).encode()
    run("sample_unsigned",
        "Same sample, no signature headers — proves 401 fires before any 422",
        client.post("/api/webhook/dodo", content=body,
                    headers={"Content-Type": "application/json"}),
        401, "Missing signature headers")

    # 3. Real-shape fixtures for every handled event — all must pass.
    for ev in ("subscription.active", "subscription.cancelled",
               "subscription.expired", "subscription.failed"):
        run(f"real_shape_{ev.split('.')[1]}",
            "Prod-observed shape (metadata.clerk_user_id present, payer email known to Clerk)",
            post_signed(dodo_payload(ev, sub_id=f"sub_probe_{ev.split('.')[1]}"),
                        f"msg_probe_{ev}"),
            200)

    # 4. Mutation matrix: real-shape cancelled, ONE field at a time toward the sample.
    run("mut_metadata_emptied",
        "metadata {} like the sample — handler never reads metadata, so no effect",
        post_signed(mutated("subscription.cancelled", metadata_empty=True, _tag="m1"),
                    "msg_probe_m1"),
        200)
    run("mut_payment_method_null",
        "payment_method_id null like the sample — never read, no effect",
        post_signed(mutated("subscription.cancelled", payment_method_null=True, _tag="m2"),
                    "msg_probe_m2"),
        200)
    run("mut_email_unknown_to_clerk",
        "customer.email -> test@acme.com (no Clerk account) — THE flip field",
        post_signed(mutated("subscription.cancelled", email="test@acme.com", _tag="m3"),
                    "msg_probe_m3"),
        422, "Clerk user not found")
    run("mut_email_missing",
        "customer.email removed — the OTHER 422 site (server.py:2128); sample does NOT hit this one",
        post_signed(mutated("subscription.cancelled", drop_email=True, _tag="m4"),
                    "msg_probe_m4"),
        422, "No customer email")

    # 5. Runtime-state risk: real-shape cancelled + Clerk outage -> same 422.
    _ProdShapedClerk.fail = True
    run("real_shape_clerk_outage",
        "Real-shape cancelled, payer email VALID, Clerk API raises — lookup "
        "exception swallowed (server.py:2145-2146) -> 422; recovered only by "
        "Dodo's auto-retry (prod evidence: Dodo does retry 422s)",
        post_signed(dodo_payload("subscription.cancelled", sub_id="sub_outage"),
                    "msg_probe_outage"),
        422, "Clerk user not found")
    _ProdShapedClerk.fail = False

    httpx.AsyncClient = _real_async_client
    server.app.dependency_overrides.pop(get_db, None)

    result = {
        "probe": "dodo_sample_422",
        "run_context": "local TestClient harness, prod-shaped Clerk fake; see module docstring",
        "scenarios": scenarios,
        "all_matched": all(s["matched"] for s in scenarios),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "probe_dodo_sample_422_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    for s in scenarios:
        print(f"[{'OK ' if s['matched'] else 'FAIL'}] {s['name']}: "
              f"expected {s['expected']['status']}, got {s['got']['status']} {s['got']['body']}")
    print(f"\nall_matched={result['all_matched']}  -> {out}")
    return 0 if result["all_matched"] else 1


if __name__ == "__main__":
    sys.exit(main())
