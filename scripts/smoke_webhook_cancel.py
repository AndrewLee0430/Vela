"""
Test: Simulate Dodo subscription.cancelled webhook

Usage:
    TEST_MODE=true \
    TEST_USER_EMAIL=a22817112@gmail.com \
    TEST_USER_ID=user_3B939OrkarbJWpfTT8nCi9kDJ1B \
    DODO_WEBHOOK_SECRET=whsec_xxx \
    uv run python scripts/smoke_webhook_cancel.py

Requires:
    - Backend running locally with TEST_MODE=true
    - DODO_WEBHOOK_SECRET matching the backend's secret
    - TEST_USER_ID: Clerk user ID (used to bypass Clerk email lookup in TEST_MODE)
    - TEST_USER_EMAIL: user email (included in payload for completeness)
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import uuid
import requests

import pytest

API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_EMAIL = os.getenv("TEST_USER_EMAIL", "")
TEST_USER_ID = os.getenv("TEST_USER_ID", "")
DODO_SECRET = os.getenv("DODO_WEBHOOK_SECRET", "")

# Collection-safety (founder ruling 2026-08-19, option (c)): these gates were
# module-scope sys.exit(1), which ABORTS pytest collection for the ENTIRE suite
# with INTERNALERROR when the env vars are unset — the recorded 291/28 baseline
# was only reproducible by --ignore-ing this file. pytest.skip with
# allow_module_level=True degrades to a SKIP under pytest and to a Skipped
# traceback under plain `python` — either way the rest of the world keeps
# running. Any future manual script copied from this one inherits the safe
# pattern. (Run manually per the usage block above; the prints below are a
# filed Rule 4 flag, deliberately left.)
if not TEST_EMAIL or not TEST_USER_ID:
    print("ERROR: Set TEST_USER_EMAIL and TEST_USER_ID environment variables")
    pytest.skip("manual script: TEST_USER_EMAIL/TEST_USER_ID unset", allow_module_level=True)

if not DODO_SECRET:
    print("ERROR: Set DODO_WEBHOOK_SECRET environment variable")
    pytest.skip("manual script: DODO_WEBHOOK_SECRET unset", allow_module_level=True)


def make_webhook_payload(event_type: str) -> dict:
    """Build Dodo webhook payload with clerk_user_id for TEST_MODE bypass.
    Uses uuid4 for event ID to guarantee uniqueness across calls."""
    unique_id = uuid.uuid4().hex[:12]
    return {
        "type": event_type,
        "data": {
            "id": f"test_{event_type}_{unique_id}",
            "subscription_id": f"test_sub_{unique_id}",
            "clerk_user_id": TEST_USER_ID,  # TEST_MODE bypass
            "customer": {
                "email": TEST_EMAIL,
                "customer_id": f"test_cust_{unique_id}",
            },
        },
    }


def sign_webhook(payload_bytes: bytes) -> dict:
    """Generate Standard Webhooks signature headers."""
    webhook_id = f"msg_test_{int(time.time())}"
    webhook_timestamp = str(int(time.time()))

    raw_secret = DODO_SECRET[len("whsec_"):] if DODO_SECRET.startswith("whsec_") else DODO_SECRET
    secret_bytes = base64.b64decode(raw_secret)

    signed_payload = f"{webhook_id}.{webhook_timestamp}.".encode() + payload_bytes
    signature = base64.b64encode(
        hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()
    ).decode()

    return {
        "Content-Type": "application/json",
        "webhook-id": webhook_id,
        "webhook-timestamp": webhook_timestamp,
        "webhook-signature": f"v1,{signature}",
    }


def send_webhook(event_type: str) -> requests.Response:
    payload = make_webhook_payload(event_type)
    payload_bytes = json.dumps(payload).encode()
    headers = sign_webhook(payload_bytes)
    return requests.post(f"{API_URL}/api/webhook/dodo", data=payload_bytes, headers=headers)


def test_cancel_webhook():
    print(f"=== Dodo Webhook Cancel Test ===")
    print(f"API:      {API_URL}")
    print(f"Email:    {TEST_EMAIL}")
    print(f"User ID:  {TEST_USER_ID}")
    print()

    # Step 1: Activate subscription
    print("1. Sending subscription.active...")
    resp = send_webhook("subscription.active")
    print(f"   {resp.status_code}: {resp.json()}")
    if resp.status_code != 200 or resp.json().get("status") == "already_processed":
        print("   FAIL: Could not activate subscription")
        sys.exit(1)

    # Step 2: Verify user is pro via /api/user/status
    # (In TEST_MODE, we need a Bearer token — use a dummy one)
    print("\n2. Checking /api/user/status...")
    status_resp = requests.get(
        f"{API_URL}/api/user/status",
        headers={"Authorization": "Bearer test_token"},
    )
    if status_resp.status_code == 200:
        status = status_resp.json()
        plan = status.get("plan_type", "?")
        print(f"   plan_type = {plan}")
        if plan != "pro":
            print("   WARN: Expected pro after activation")
    else:
        print(f"   SKIP: status check returned {status_resp.status_code} (auth may differ in TEST_MODE)")

    # Step 3: Cancel subscription
    print("\n3. Sending subscription.cancelled...")
    resp2 = send_webhook("subscription.cancelled")
    print(f"   {resp2.status_code}: {resp2.json()}")

    if resp2.status_code == 200:
        data = resp2.json()
        if data.get("event") == "subscription.cancelled":
            print("   PASS: subscription.cancelled processed")
        elif data.get("status") == "already_processed":
            print("   FAIL: Event already_processed — duplicate event_id collision!")
            print("   This means active and cancel had the same data.id")
            sys.exit(1)
        else:
            print(f"   WARN: Unexpected response: {data}")
    else:
        print(f"   FAIL: Expected 200, got {resp2.status_code}")
        sys.exit(1)

    # Step 4: Verify user is back to free
    print("\n4. Checking /api/user/status again...")
    status_resp2 = requests.get(
        f"{API_URL}/api/user/status",
        headers={"Authorization": "Bearer test_token"},
    )
    if status_resp2.status_code == 200:
        status2 = status_resp2.json()
        plan2 = status2.get("plan_type", "?")
        print(f"   plan_type = {plan2}")
        if plan2 == "free":
            print("   PASS: User downgraded to free")
        else:
            print(f"   WARN: Expected free, got {plan2}")
    else:
        print(f"   SKIP: status check returned {status_resp2.status_code}")

    print("\n=== Done ===")
    print("Verify in DB: plan_type='free', dodo_subscription_id=NULL")


if __name__ == "__main__":
    test_cancel_webhook()
