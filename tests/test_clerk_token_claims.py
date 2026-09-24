# -*- coding: utf-8 -*-
"""Clerk JWT claim verification — iss pin + azp allowlist + exp required
(azp car, founder rulings Q1–Q4 2026-09-24).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
A Clerk session token is only accepted when it was minted by VELA's Clerk
instance (iss) FOR Vela's own frontend origin (azp) and it carries an expiry
(exp). A token signed by a trusted key but minted for another origin, by
another issuer, with no azp, or with no exp must be REJECTED — a signature
alone proves only "some Clerk key signed this", not "this is a Vela session".
Both decode sites are covered: require_auth (403 on any failure, Rule 1
fail-closed) and _optional_user_id (None = anonymous on any failure, Q4).

Harness: a locally generated RSA key stands in for Clerk's signing key; its
public half is served as the JWKS by monkeypatching get_jwks (no network).
TEST_MODE is read at import, so it is patched to False on the module for these
tests. require_auth is driven through a REAL protected endpoint (GET
/api/history) with the in-memory DB pattern of tests/test_history_delete.py;
the authorized case reads its own seeded row back, proving `sub` was used.

Run: python -m pytest tests/test_clerk_token_claims.py -q
"""
import asyncio
import base64
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server (same as the sibling suites): the DATABASE_URL
# default keeps module init off any real DB. TEST_MODE is switched OFF per test
# on the module attribute, which is what require_auth reads at call time.
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# The rejection cases log at warning/error; with a DSN inherited from a local
# .env those would be shipped to the real Sentry project. Empty = disabled
# (api/server.py:25); load_dotenv does not override an already-set key.
os.environ["SENTRY_DSN"] = ""

import pytest  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from jose import jwk, jwt as jose_jwt  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Literals, not the server constants: the claim values a real Vela token
# carries (founder fact 2026-09-24, own prod token, payload only).
GOOD_ISS = "https://clerk.vela.an-tho.com"
GOOD_AZP = "https://vela.an-tho.com"
SUB = "user_claims_test"
KID = "test-kid-1"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
_PUBLIC_PEM = _PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()
_JWK = jwk.construct(_PUBLIC_PEM, "RS256").to_dict()
_JWK.update({"kid": KID, "use": "sig"})
JWKS = {"keys": [_JWK]}

_DEFAULT = object()


def _mint(iss=GOOD_ISS, azp=GOOD_AZP, exp=_DEFAULT, sub=SUB):
    now = int(time.time())
    claims = {"sub": sub, "iat": now, "nbf": now - 5, "sid": "sess_test"}
    if iss is not None:
        claims["iss"] = iss
    if azp is not None:
        claims["azp"] = azp
    if exp is _DEFAULT:
        claims["exp"] = now + 300
    elif exp is not None:
        claims["exp"] = exp
    return jose_jwt.encode(claims, _PRIVATE_PEM, algorithm="RS256", headers={"kid": KID})


@pytest.fixture
def server(monkeypatch):
    import api.server as server_module

    async def _fake_jwks():
        return JWKS

    monkeypatch.setattr(server_module, "get_jwks", _fake_jwks)
    monkeypatch.setattr(server_module, "TEST_MODE", False)
    return server_module


@pytest.fixture
def client(server):
    from api.database.sql_db import Base, get_db
    from api.models.sql_models import ChatHistory
    from fastapi.testclient import TestClient

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with TestSession() as db:
        db.add(ChatHistory(user_id=SUB, session_type="research",
                           question="claims-test question", answer="claims-test answer"))
        db.commit()

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    server.app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(server.app)  # no context manager → no lifespan tasks
    finally:
        server.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _history(client, token):
    return client.get("/api/history", headers={"Authorization": f"Bearer {token}"})


# ── require_auth (via GET /api/history) ─────────────────────────────────────

def test_1_valid_token_is_authorized_as_its_sub(client):
    resp = _history(client, _mint())
    assert resp.status_code == 200, resp.text
    questions = [row["question"] for row in resp.json()]
    assert "claims-test question" in questions, "the token's sub must own the result"


def test_2_foreign_azp_is_rejected(client):
    resp = _history(client, _mint(azp="https://evil.example"))
    assert resp.status_code == 403, resp.text


def test_3_missing_azp_is_rejected(client):
    resp = _history(client, _mint(azp=None))
    assert resp.status_code == 403, resp.text


def test_4_foreign_issuer_is_rejected(client):
    resp = _history(client, _mint(iss="https://clerk.other.example"))
    assert resp.status_code == 403, resp.text


def test_5_missing_exp_is_rejected(client):
    resp = _history(client, _mint(exp=None))
    assert resp.status_code == 403, resp.text


def test_6_expired_token_is_rejected(client):
    resp = _history(client, _mint(exp=int(time.time()) - 60))
    assert resp.status_code == 403, resp.text


# ── _optional_user_id (direct) ──────────────────────────────────────────────

def _request_with(token):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/bug-report",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    return Request(scope)


def test_optional_user_id_valid_token_returns_sub(server):
    assert asyncio.run(server._optional_user_id(_request_with(_mint()))) == SUB


def test_optional_user_id_foreign_azp_is_anonymous(server):
    token = _mint(azp="https://evil.example")
    assert asyncio.run(server._optional_user_id(_request_with(token))) is None


# ── constants consistency ───────────────────────────────────────────────────

def test_issuer_constant_matches_committed_publishable_key():
    """CLERK_ISSUER must name the same Clerk frontend API host as the
    publishable key the frontend is BUILT with (fly.toml [build.args]); if the
    key is rotated to another instance without the constant following, every
    login would 403 — this fails first."""
    import api.server as server_module

    with open(os.path.join(REPO, "fly.toml"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY\s*=\s*"pk_(?:live|test)_([A-Za-z0-9+/=_-]+)"', text)
    assert m, "publishable key not found in fly.toml"
    b64 = m.group(1)
    host = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode().rstrip("$")

    assert server_module.CLERK_ISSUER == f"https://{host}"
    assert server_module.CLERK_ISSUER == GOOD_ISS
    assert GOOD_AZP in server_module.CLERK_AUTHORIZED_PARTIES
