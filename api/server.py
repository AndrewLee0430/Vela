"""
Vela API Server
FastAPI 後端，整合 Research、Verify、Explain、合規防護與數據飛輪回饋
"""

from dotenv import load_dotenv
import logging
import os
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

_SENTRY_DSN = os.getenv("SENTRY_DSN")
if _SENTRY_DSN:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.2,
        environment=os.getenv("FLY_APP_NAME", "development"),
        send_default_pii=False,
    )
    logging.getLogger("vela").info("Sentry initialized")
else:
    logging.getLogger("vela").warning("SENTRY_DSN not set, Sentry disabled")

import asyncio
import json
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Tuple

from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger("vela")

from api.models.schemas import (
    ResearchRequest,
    SuggestionsResponse,
    StreamEvent,
    StreamEventType,
    VerifyRequest,
    VerifyResponse,
    DrugInteraction
)
from api.rag.retriever import HybridRetriever
from api.rag.generator import AnswerGenerator
from api.data_sources.fda import FDAClient
from api.middleware.phi_handler import PHIDetector
from api.middleware.guards import run_guards
from api.database.sql_db import get_db, engine, Base, SessionLocal
from api.models.sql_models import AuditLog, UserFeedback, ChatHistory, BugReport
from api.services.usage_service import (
    check_credits,
    deduct_credits,
    check_anonymous_credits,
    deduct_anonymous_credits,
    ANONYMOUS_DAILY_LIMIT,
)
from api.services.anonymous_identity import derive_anon_id, validate_fingerprint
from api.services.cost_guard import check_anonymous_budget
from api.errors import (
    FeatureNotAvailable,
    AnonymousQuotaExceeded,
    AnonymousBudgetExceeded,
    InvalidFingerprint,
)
from api.utils.llm_judge import LLMJudge, Source as JudgeSource

from api.models.explain_schemas import ExplainRequest
from api.services.explain_service import run_explain_pipeline
from api.utils.language_detector import detect_language, get_language_instruction, LANGUAGE_NAMES, get_language_name  # ← v2.5
from api.i18n.verify_strings import get_verify_disclaimer

# ============================================================
# Verify system prompt (PRD § 2.9, v2)
# ============================================================
_VERIFY_PROMPT_PATH = Path(__file__).parent / "prompts" / "verify_system.md"
_VERIFY_PROMPT_FALLBACK = (
    "You are a clinical pharmacist. Analyze FDA drug labels for interactions.\n\n"
    "Respond in {response_language}. Drug names stay in English canonical form "
    "(e.g., 'Warfarin'). `severity` and `risk_level` stay as English enum "
    "(Critical/Major/Moderate/Minor). `severity_label` and `risk_level_label` "
    "are the localized display in {response_language}. `description`, "
    "`recommendation`, and `summary` must be in {response_language}.\n\n"
    "Return valid JSON only:\n"
    '{{"interactions":[{{"drugs":["Drug1","Drug2"],"severity":"Major",'
    '"severity_label":"嚴重","description":"...","recommendation":"..."}}],'
    '"summary":"...","risk_level":"Major","risk_level_label":"嚴重"}}'
)

try:
    _VERIFY_SYSTEM_TEMPLATE = _VERIFY_PROMPT_PATH.read_text(encoding="utf-8")
    logger.info("[Verify] system prompt loaded from %s", _VERIFY_PROMPT_PATH)
except FileNotFoundError:
    logger.warning("[Verify] prompt file missing, using inline fallback: %s", _VERIFY_PROMPT_PATH)
    _VERIFY_SYSTEM_TEMPLATE = _VERIFY_PROMPT_FALLBACK


def _resolve_response_language(body_value: Optional[str], request: Request) -> str:
    """
    Resolve user's desired response language for Verify per PRD § 2.9.

    Fallback chain:
      1. body.response_language (if valid LANGUAGE_NAMES key)
      2. first tag from Accept-Language header (if valid)
      3. "en"
    """
    # Normalize common aliases
    def _normalize(code: str) -> Optional[str]:
        if not code:
            return None
        code = code.strip()
        if code in LANGUAGE_NAMES:
            return code
        # BCP-47 normalization: "zh-tw" → "zh-TW", "ZH-CN" → "zh-CN"
        if "-" in code:
            primary, region = code.split("-", 1)
            canonical = f"{primary.lower()}-{region.upper()}"
            if canonical in LANGUAGE_NAMES:
                return canonical
        # Bare primary subtag: "zh" → "zh-TW" (matches existing detect_language behavior)
        if code.lower() == "zh":
            return "zh-TW"
        low = code.lower()
        if low in LANGUAGE_NAMES:
            return low
        return None

    resolved = _normalize(body_value) if body_value else None
    if resolved:
        return resolved

    accept = request.headers.get("accept-language", "")
    if accept:
        # "zh-TW,zh;q=0.9,en;q=0.8" → first tag = "zh-TW"
        first_tag = accept.split(",", 1)[0].split(";", 1)[0].strip()
        resolved = _normalize(first_tag)
        if resolved:
            return resolved

    return "en"

# ============================================================
# DB write helper
# ============================================================

def _safe_db_write(db: Session, *records, label: str = "DB") -> bool:
    """Add one or more records and commit. Returns True on success."""
    try:
        for rec in records:
            db.add(rec)
        db.commit()
        return True
    except Exception as e:
        logger.error("%s Error: %s", label, e)
        db.rollback()
        return False


# ============================================================
# 生命週期管理
# ============================================================
async def _cleanup_old_records():
    """Delete AuditLog and ChatHistory records older than 6 months. Runs daily."""
    from datetime import datetime, timedelta
    while True:
        await asyncio.sleep(86400)  # Run once per day
        try:
            cutoff = datetime.utcnow() - timedelta(days=180)
            db = SessionLocal()
            try:
                deleted_audit = db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
                deleted_chat = db.query(ChatHistory).filter(ChatHistory.created_at < cutoff).delete()
                db.commit()
                if deleted_audit or deleted_chat:
                    logger.info("Data cleanup: deleted %d audit logs, %d chat history records older than 6 months",
                                deleted_audit, deleted_chat)
            finally:
                db.close()
        except Exception as e:
            logger.error("Data cleanup error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    cleanup_task = asyncio.create_task(_cleanup_old_records())
    yield
    cleanup_task.cancel()


app = FastAPI(
    title="Vela API",
    description="AI-powered medical assistant",
    version="2.2.0",
    lifespan=lifespan
)



# ============================================================
# Rate Limiter
# ============================================================
import time as _time
from collections import defaultdict

_rate_store: dict = defaultdict(list)
_rate_store_last_cleanup = 0.0

RATE_LIMITS = {
    "/api/research":              (30, 60),
    "/api/verify":                (30, 60),
    "/api/explain":               (20, 60),
    "/api/feedback":              (10, 60),
    "/api/explain/feedback":      (10, 60),
    "/api/checkout":              (5,  60),
    "/api/checkout/dodo":         (5,  60),
    "/api/webhook/dodo":          (30, 60),
    "/api/webhooks/lemonsqueezy": (30, 60),
    "/api/admin/costs":           (10, 60),
    "/api/user/portal":           (5,  60),
    "/api/subscription/cancel":   (3,  60),
    "/api/explain/extract-image": (10, 60),
    "/api/bug-report":            (5,  3600),
}

def _get_client_ip(request: Request) -> str:
    # Fly edge proxy sets X-Forwarded-For; first entry is the originating client.
    # Fall back to request.client.host for local/non-proxied requests.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    global _rate_store_last_cleanup

    # TEST_MODE bypasses rate limiting. Test runner makes 22+ explain
    # requests + 22 ExplainJudge calls = 44+ requests in ~5 min, exceeding
    # all per-IP limits. Production guard at module init (server.py:305-308)
    # raises RuntimeError if TEST_MODE=true with FLY_APP_NAME set — process
    # won't start, so this branch can't leak to prod.
    if TEST_MODE:
        return await call_next(request)

    path = request.url.path
    if path not in RATE_LIMITS:
        return await call_next(request)

    ip = _get_client_ip(request)
    limit, window = RATE_LIMITS[path]
    now = _time.time()

    # Purge stale keys every 5 minutes to prevent unbounded growth
    if now - _rate_store_last_cleanup > 300:
        max_window = max(w for _, w in RATE_LIMITS.values())
        stale_keys = [k for k, v in _rate_store.items() if not v or now - v[-1] > max_window]
        for k in stale_keys:
            del _rate_store[k]
        _rate_store_last_cleanup = now

    key = f"{ip}:{path}"
    _rate_store[key] = [t for t in _rate_store[key] if now - t < window]

    if len(_rate_store[key]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded. Max {limit} requests per {window}s."}
        )

    _rate_store[key].append(now)
    return await call_next(request)


# ============================================================
# CORS
# ============================================================
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Anon-Fingerprint"],
)


# ============================================================
# Auth
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
if TEST_MODE and os.getenv("FLY_APP_NAME"):
    raise RuntimeError("TEST_MODE cannot be enabled in production (FLY_APP_NAME detected)")
logger.info("TEST_MODE = %s", TEST_MODE)

# PRD § 4.5 PHASE B — created_by hash salt. Fail loudly at startup if
# missing in production so we never silently degrade to an empty salt.
# TEST_MODE accepts a built-in fallback so local smoke tests work
# without forcing every developer to copy a value into .env.
SHARE_CREATED_BY_SALT = os.getenv("SHARE_CREATED_BY_SALT")
if not SHARE_CREATED_BY_SALT:
    if TEST_MODE:
        SHARE_CREATED_BY_SALT = "vela_share_test_salt_v1"
        logger.warning("[share] SHARE_CREATED_BY_SALT not set; using TEST_MODE default")
    else:
        raise RuntimeError(
            "SHARE_CREATED_BY_SALT must be set (PRD § 4.5 PHASE B). "
            "Generate via `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`."
        )

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

_jwks_cache = None
_jwks_cache_ts: float = 0
_JWKS_TTL = 6 * 3600  # 6 hours

async def get_jwks():
    global _jwks_cache, _jwks_cache_ts
    if _jwks_cache is None or (time.time() - _jwks_cache_ts) > _JWKS_TTL:
        async with httpx.AsyncClient() as client:
            r = await client.get(os.getenv("CLERK_JWKS_URL"))
            _jwks_cache = r.json()
            _jwks_cache_ts = time.time()
    return _jwks_cache

if not TEST_MODE:
    clerk_guard = None  # 不再用 fastapi-clerk-auth
else:
    clerk_guard = None
    logger.warning("TEST_MODE: Clerk authentication disabled")


async def require_auth(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Require a valid Clerk JWT. Raises 403 if missing or invalid.

    Used by L1/L2-only endpoints (history, feedback, billing, admin, bug-report's
    adjacent handlers, etc.). Decision 001 v0.4 A9 — renamed from optional_auth()
    because the original name was misleading (it was never truly optional).
    For endpoints that also accept L0 anonymous traffic, use
    require_auth_or_anonymous() instead.
    """
    if TEST_MODE:
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Missing token")

    token = auth_header.split(" ", 1)[1]

    try:
        jwks = await get_jwks()
        payload = jose_jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        # 模擬 HTTPAuthorizationCredentials
        class FakeCreds:
            decoded = payload
        return FakeCreds()
    except JWTError as e:
        logger.error("JWT decode error: %s", e)
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")


async def require_auth_or_anonymous(
    request: Request,
) -> Tuple[Optional[str], Optional[str]]:
    """Accept either a Clerk JWT (L1/L2) or an X-Anon-Fingerprint header (L0).

    Returns (user_id, anon_id). Exactly one is non-None.

    Decision 001 v0.3 § A, D / v0.4 A9 — used by Research / Verify / Explain.
    Explain raises FeatureNotAvailable("explain") if anon_id is set (L0 cannot
    access Explain per Decision 001 v0.3).

    TEST_MODE behavior:
      - Bearer token present → treat as L1/L2 (use TEST_USER_ID)
      - X-Anon-Fingerprint present → treat as L0 (derive anon_id normally)
      - Neither → fall back to TEST_USER_ID as L1 (preserves legacy test flow)
    """
    auth_header = request.headers.get("Authorization", "")
    fp_header = request.headers.get("X-Anon-Fingerprint", "")

    if auth_header.startswith("Bearer "):
        creds = await require_auth(request)
        user_id = get_user_id(creds)
        return user_id, None

    if fp_header:
        try:
            fingerprint = validate_fingerprint(fp_header)
        except ValueError as e:
            raise InvalidFingerprint(str(e))
        client_ip = _get_client_ip(request)
        anon_id = derive_anon_id(client_ip, fingerprint)
        return None, anon_id

    if TEST_MODE:
        return os.getenv("TEST_USER_ID", "test_user"), None

    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Missing token")


def get_user_id(creds: Optional[HTTPAuthorizationCredentials]) -> str:
    if creds is None:
        # TEST_MODE: use TEST_USER_ID env var if set, otherwise fallback
        return os.getenv("TEST_USER_ID", "test_user")
    return creds.decoded["sub"]


# ============================================================
# 初始化元件
# ============================================================
retriever = HybridRetriever(
    local_threshold=0.6,
    enable_local=True,
    enable_pubmed=True,
    enable_fda=True
)
generator = AnswerGenerator()
fda_client = FDAClient()
_judge = LLMJudge()

# §2.1 PHASE D (PRD v1.4 + ADR 005): module-level lazy bindings for the
# Verify and Vision task layers. Replaces former openai_async_client
# singleton. Each binding is created on first use (cached for the process).
from api.providers import get_verify_provider, get_vision_provider
from api.providers.base import CompletionRequest

_verify_binding = None
_vision_binding = None


def _get_verify():
    global _verify_binding
    if _verify_binding is None:
        _verify_binding = get_verify_provider()
    return _verify_binding


def _get_vision():
    global _vision_binding
    if _vision_binding is None:
        _vision_binding = get_vision_provider()
    return _vision_binding


async def _run_judge_background(audit_id: str, query: str, answer: str, documents: list):
    """Background task: evaluate answer quality and write scores to AuditLog.extra_data."""
    try:
        sources = [
            JudgeSource(source_id=getattr(d, "source_id", str(i)), content=getattr(d, "content", ""))
            for i, d in enumerate(documents)
        ]
        evaluation = await _judge.evaluate(query, answer, sources)
        db = SessionLocal()
        try:
            log = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
            if log:
                log.extra_data = {
                    "llm_judge": {
                        "scores":          evaluation["scores"],
                        "weighted_score":  evaluation["weighted_score"],
                        "quality_level":   evaluation["quality_level"],
                        "has_hallucination": evaluation.get("has_hallucination", False),
                    }
                }
                db.commit()
                logger.info("[LLMJudge] completed: audit_id=%s score=%.1f quality=%s",
                            audit_id, evaluation["weighted_score"], evaluation["quality_level"])
        finally:
            db.close()
    except Exception as e:
        logger.error("[LLMJudge] background task failed: %s", e)


# ============================================================
# Middleware: PHI 防護 (feedback only — SSE endpoints use inline checks)
# ============================================================
def _phi_blocked_response(phi_type: str) -> JSONResponse:
    """Return a standardized PHI-blocked error response."""
    return JSONResponse(
        status_code=400,
        content={
            "type": "phi_blocked",
            "content": "Personal information detected",
            "detail": f"We detected what appears to be a {phi_type} in your input. To protect your privacy, Vela does not process queries containing personal identifiable information.",
            "suggestion": "Please remove any personal information (ID numbers, phone numbers, SSN, etc.) and try again."
        }
    )


def _check_phi(text: str, endpoint: str, request: Request) -> JSONResponse | None:
    """Check text for PHI. Returns a 400 JSONResponse if detected, else None."""
    try:
        phi_type = PHIDetector.detect(text)
        if phi_type:
            client_ip = _get_client_ip(request)
            logger.warning("[PHI] Blocked: type=%s, endpoint=%s, ip=%s", phi_type, endpoint, client_ip)
            return _phi_blocked_response(phi_type)
    except Exception as e:
        logger.error("PHI check error: %s", e)
    return None


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    path = request.url.path

    # SSE endpoints skip middleware body read (causes chunked read errors).
    # PHI detection for those is done inline in each route handler.
    if path in ["/api/research", "/api/explain", "/api/verify"]:
        return await call_next(request)

    if path == "/api/feedback" and request.method == "POST":
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8")
            body_dict = json.loads(body_str) if body_str.strip() else {}

            feedback_text = body_dict.get("feedback_text", "")
            if feedback_text:
                phi_resp = _check_phi(feedback_text, "/api/feedback", request)
                if phi_resp:
                    return phi_resp

            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error("PHI middleware error: %s", e)

    response = await call_next(request)
    return response


# ============================================================
# 功能 2：Research / RAG
# ============================================================
@app.post("/api/research")
async def research_query(
    body: ResearchRequest,
    request: Request,
    auth: Tuple[Optional[str], Optional[str]] = Depends(require_auth_or_anonymous),
    db: Session = Depends(get_db)
):
    user_id, anon_id = auth
    is_anonymous = anon_id is not None

    # PHI 偵測（在 streaming 開始前）
    phi_resp = _check_phi(body.question, "/api/research", request)
    if phi_resp:
        return phi_resp

    start_time = time.time()

    # Credit / quota / budget 檢查（在 streaming 開始前）
    # Decision 001 v0.3 A7 / A8: L0 走 $2/day aggregate cap + per-anon ANONYMOUS_DAILY_LIMIT + gpt-4.1-mini
    if is_anonymous:
        logger.info("[Research] tier=L0 anon_id=%s query_length=%d", anon_id[:8], len(body.question))
        budget_ok, _spent = await check_anonymous_budget(db)
        if not budget_ok:
            raise AnonymousBudgetExceeded()
        allowed, remaining = await check_anonymous_credits(db, anon_id, "research")
        if not allowed:
            raise AnonymousQuotaExceeded(
                used=ANONYMOUS_DAILY_LIMIT - remaining,
                limit=ANONYMOUS_DAILY_LIMIT,
            )
        # §2.1 PHASE D: anon path uses GENERATOR_FALLBACK_MODEL (default gpt-4.1-mini)
        # so the literal stays env-var-driven. Preserves Decision 001 v0.3 A8 intent.
        model_override: Optional[str] = generator._fallback_model
    else:
        logger.info("[Research] user=%s query_length=%d", user_id, len(body.question))
        if not TEST_MODE:
            allowed, reason = await check_credits(db, user_id, "research")
            if not allowed:
                if reason == "limit_reached":
                    return JSONResponse(status_code=403, content={"error": "limit_reached", "upgrade_url": "/pricing"})
                elif reason == "daily_cap_reached":
                    return JSONResponse(status_code=429, content={"error": "daily_cap_reached", "message": "You've reached today's usage limit. Resets at midnight UTC."})
        model_override = None

    async def event_stream():
        full_answer = ""
        audit_id = f"res_{uuid.uuid4().hex[:16]}"
        try:
            # Emit query_id first so the client can tag subsequent analytics events
            yield f"data: {json.dumps({'type': 'query_id', 'query_id': audit_id})}\n\n"

            passed, guard_error = await run_guards(body.question)
            if not passed:
                yield f"data: {json.dumps({'type': 'error', 'content': guard_error}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'content': 'Searching medical literature...'}, ensure_ascii=False)}\n\n"

            documents, retrieval_status = await retriever.retrieve(
                query=body.question,
                max_results=body.max_results or 5,
                source_filter=body.sources
            )

            yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing documents...'}, ensure_ascii=False)}\n\n"

            lang = detect_language(body.question)
            yield f"data: {json.dumps({'type': 'language', 'lang': lang}, ensure_ascii=False)}\n\n"
            usage_out = []
            async for event in generator.generate_stream(
                question=body.question,
                documents=documents,
                retrieval_status=retrieval_status,
                query_type="research",
                lang=lang,
                usage_out=usage_out,
                model_override=model_override
            ):
                if event.type == StreamEventType.ANSWER:
                    content = event.content or ""
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'answer', 'content': content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.FALLBACK:
                    yield f"data: {json.dumps({'type': 'fallback', 'content': event.content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.CITATIONS:
                    citations_data = [c.model_dump() for c in event.content]
                    # L0 anonymous: skip AuditLog (no history persistence for anon)
                    if not is_anonymous:
                        _safe_db_write(db, AuditLog(
                                id=audit_id,
                                user_id=user_id,
                                action="research",
                                query_content=PHIDetector.sanitize_for_log(body.question),
                                resource_ids=[c.get('source_id') for c in citations_data],
                                ip_address="0.0.0.0"
                            ), label="Audit Log")
                    yield f"data: {json.dumps({'type': 'citations', 'content': citations_data}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.ERROR:
                    yield f"data: {json.dumps({'type': 'error', 'content': event.content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.DONE:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    if is_anonymous:
                        # L0: deduct anon quota + log cost with user_id=None marker (v0.4 A10)
                        await deduct_anonymous_credits(db, anon_id, "research")
                        if usage_out:
                            from api.services.cost_tracker import log_api_cost
                            u = usage_out[0]
                            await log_api_cost(db, None, "research", u["model"], u["prompt_tokens"], u["completion_tokens"])
                    else:
                        _safe_db_write(db, ChatHistory(
                                user_id=user_id,
                                session_type="research",
                                question=PHIDetector.sanitize_for_log(body.question),
                                answer=full_answer
                            ), label="History Save")
                        # 成功後扣減 credits
                        await deduct_credits(db, user_id, "research")
                        # Cost logging
                        if usage_out:
                            from api.services.cost_tracker import log_api_cost
                            u = usage_out[0]
                            await log_api_cost(db, user_id, "research", u["model"], u["prompt_tokens"], u["completion_tokens"])
                        # Fire LLM Judge in background — does not block SSE stream (L1/L2 only)
                        if audit_id and full_answer:
                            asyncio.create_task(
                                _run_judge_background(audit_id, body.question, full_answer, documents)
                            )
                    yield f"data: {json.dumps({'type': 'done', 'query_time_ms': elapsed_ms}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("Research stream error: %s", type(e).__name__)
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred. Please try again.'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/api/research/suggestions")
async def get_suggestions(creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth)):
    return SuggestionsResponse.default_suggestions()


# ============================================================
# 功能 3：Verify
# ============================================================
@app.post("/api/verify")
async def verify_drug_interaction(
    body: VerifyRequest,
    request: Request,
    auth: Tuple[Optional[str], Optional[str]] = Depends(require_auth_or_anonymous),
    db: Session = Depends(get_db)
):
    user_id, anon_id = auth
    is_anonymous = anon_id is not None

    # PHI 偵測
    drugs_text = " ".join(body.drugs)
    phi_resp = _check_phi(drugs_text, "/api/verify", request)
    if phi_resp:
        return phi_resp

    start_time = time.time()
    audit_id = f"ver_{uuid.uuid4().hex[:16]}"

    # Credit / quota / budget 檢查
    # Decision 001 v0.3 A7 / A8: L0 走 $2/day aggregate cap + per-anon ANONYMOUS_DAILY_LIMIT (Verify 已是 gpt-4.1-mini)
    if is_anonymous:
        logger.info("[Verify] tier=L0 anon_id=%s drugs=%s", anon_id[:8], body.drugs)
        budget_ok, _spent = await check_anonymous_budget(db)
        if not budget_ok:
            raise AnonymousBudgetExceeded()
        allowed, remaining = await check_anonymous_credits(db, anon_id, "verify")
        if not allowed:
            raise AnonymousQuotaExceeded(
                used=ANONYMOUS_DAILY_LIMIT - remaining,
                limit=ANONYMOUS_DAILY_LIMIT,
            )
    else:
        logger.info("[Verify] user=%s drugs=%s", user_id, body.drugs)
        if not TEST_MODE:
            allowed, reason = await check_credits(db, user_id, "verify")
            if not allowed:
                if reason == "limit_reached":
                    return JSONResponse(status_code=403, content={"error": "limit_reached", "upgrade_url": "/pricing"})
                elif reason == "daily_cap_reached":
                    return JSONResponse(status_code=429, content={"error": "daily_cap_reached", "message": "You've reached today's usage limit. Resets at midnight UTC."})

    # ── Guard：藥物名稱不需要間接 injection 掃描 ──────────────────
    verify_input = " ".join(body.drugs) + (f" {body.patient_context}" if body.patient_context else "")
    passed, guard_error = await run_guards(verify_input, skip_indirect=True)
    if not passed:
        return JSONResponse(status_code=400, content={"detail": guard_error})

    # ── PRD § 2.9: 語言決策優先 body.response_language，不再從藥名猜 ──
    response_language = _resolve_response_language(body.response_language, request)
    response_language_name = get_language_name(response_language)
    logger.info("[Verify] response_language=%s (body=%s)", response_language, body.response_language)

    # Legacy lang detection retained for fallback path's lang_instruction only
    verify_query = body.patient_context or " ".join(body.drugs)
    lang = detect_language(verify_query)
    lang_instruction = get_language_instruction(lang)

    drug_labels = []
    spelling_corrections: list[str] = []

    def levenshtein(a, b):
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]; dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                dp[j] = prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
                prev = temp
        return dp[n]

    KNOWN_DRUGS = [
        "warfarin","aspirin","metformin","lisinopril","atorvastatin","amlodipine",
        "simvastatin","ibuprofen","acetaminophen","paracetamol","fluoxetine","tramadol",
        "spironolactone","clarithromycin","iohexol","insulin","metoprolol","omeprazole",
        "amoxicillin","ciprofloxacin","prednisone","levothyroxine","gabapentin",
        "sertraline","losartan",
    ]

    # Parallel FDA lookups for all drugs
    fda_results = await asyncio.gather(
        *[fda_client.search_drug_labels(drug, limit=1) for drug in body.drugs],
        return_exceptions=True
    )

    # Process results and apply spell correction for misses
    correction_tasks = []  # (index, drug_name, best_match)
    for i, (drug, result) in enumerate(zip(body.drugs, fda_results)):
        if isinstance(result, Exception):
            result = []
        if result:
            drug_labels.append(result[0])
            official_name = (result[0].generic_name or result[0].brand_name or '').strip()
            if official_name:
                drug_lower, official_lower = drug.lower().strip(), official_name.lower().strip()
                if drug_lower not in official_lower and official_lower not in drug_lower:
                    dist = levenshtein(drug_lower, official_lower)
                    if 1 <= dist <= 3 and abs(len(drug_lower) - len(official_lower)) <= 2:
                        spelling_corrections.append(f"'{drug}' was interpreted as '{official_name.title()}'")
        else:
            drug_lower = drug.lower().strip()
            best_match, best_dist = None, 999
            for known in KNOWN_DRUGS:
                dist = levenshtein(drug_lower, known)
                if dist < best_dist and dist <= 3 and abs(len(drug_lower) - len(known)) <= 2:
                    best_dist = dist; best_match = known
            if best_match:
                spelling_corrections.append(f"'{drug}' was interpreted as '{best_match.title()}'")
                correction_tasks.append((i, drug, best_match))

    # Parallel FDA lookups for spell-corrected drugs
    if correction_tasks:
        corrected_results = await asyncio.gather(
            *[fda_client.search_drug_labels(match, limit=1) for _, _, match in correction_tasks],
            return_exceptions=True
        )
        for (_, _, _), corrected in zip(correction_tasks, corrected_results):
            if not isinstance(corrected, Exception) and corrected:
                drug_labels.append(corrected[0])

    if not drug_labels:
        logger.warning("No FDA labels found for %s, falling back to LLM", body.drugs)
        if not is_anonymous:
            _safe_db_write(db, AuditLog(id=audit_id, user_id=user_id,
                    action="verify_fallback", query_content=f"LLM fallback: {body.drugs}", ip_address="0.0.0.0"),
                    label="Verify Audit")

        # PRD § 2.9: fallback prompt also follows response_language contract
        fallback_system = _VERIFY_SYSTEM_TEMPLATE.format(response_language=response_language_name)

        try:
            fb_user_content = (
                f"Analyze interaction between: {', '.join(body.drugs)}\n"
                f"Context: {body.patient_context or 'None'}\n"
                "(No FDA label data available — rely on general clinical pharmacology knowledge.)"
            )
            verify_binding = _get_verify()
            fb_req = CompletionRequest(
                model=verify_binding.model,
                messages=[
                    {"role": "system", "content": fallback_system},
                    {"role": "user", "content": fb_user_content}
                ],
                response_format={"type": "json_object"},
            )
            fb = await verify_binding.provider.complete(fb_req)
            fb_data = json.loads(fb.content)
            fb_interactions = [
                DrugInteraction(
                    drug_pair=tuple(item["drugs"][:2]),
                    severity=item.get("severity","Unknown"),
                    severity_label=item.get("severity_label") or None,
                    description=item.get("description",""),
                    clinical_recommendation=item.get("recommendation",""),
                    source="Clinical Knowledge (No FDA label available)",
                    source_url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process&query={body.drugs[0].replace(' ', '+')}"
                )
                for item in fb_data.get("interactions",[]) if len(item.get("drugs",[])) >= 2
            ]
            fb_summary = "⚠️ No FDA label data found. " + fb_data.get("summary","")
            if not is_anonymous:
                _safe_db_write(db, ChatHistory(user_id=user_id, session_type="verify",
                        question=f"Drugs: {', '.join(body.drugs)}", answer=fb_summary), label="Verify History")
            # Credit / cost accounting for fallback path
            if is_anonymous:
                await deduct_anonymous_credits(db, anon_id, "verify")
                try:
                    from api.services.cost_tracker import log_api_cost
                    await log_api_cost(
                        db, None, "verify", verify_binding.model,
                        fb.input_tokens,
                        fb.output_tokens,
                    )
                except Exception as e:
                    logger.error("Cost log error (verify fallback anon): %s", e)
            else:
                await deduct_credits(db, user_id, "verify")
                try:
                    from api.services.cost_tracker import log_api_cost
                    await log_api_cost(
                        db, user_id, "verify", verify_binding.model,
                        fb.input_tokens,
                        fb.output_tokens,
                    )
                except Exception as e:
                    logger.error("Cost log error (verify fallback): %s", e)
            return VerifyResponse(
                drugs_analyzed=body.drugs,
                interactions=fb_interactions,
                summary=fb_summary,
                risk_level=fb_data.get("risk_level","Unknown"),
                risk_level_label=fb_data.get("risk_level_label") or None,
                response_language=response_language,
                disclaimer=get_verify_disclaimer(response_language),
                query_time_ms=int((time.time()-start_time)*1000),
                query_id=audit_id,
            )
        except Exception as e:
            logger.error("Verify fallback failed: %s", e)
            fallback_summary = "No FDA label data found. Please use specific drug names."
            if not is_anonymous:
                _safe_db_write(db, ChatHistory(user_id=user_id, session_type="verify",
                        question=f"Drugs: {', '.join(body.drugs)}", answer=fallback_summary), label="Verify History")
            return VerifyResponse(
                drugs_analyzed=body.drugs, interactions=[],
                summary=fallback_summary,
                risk_level="Unknown",
                response_language=response_language,
                disclaimer=get_verify_disclaimer(response_language),
                query_time_ms=int((time.time()-start_time)*1000),
                query_id=audit_id,
            )

    fda_context = "\n".join([label.to_text() for label in drug_labels])

    # ── PRD § 2.9: system prompt v2 從 api/prompts/verify_system.md 載入 ──
    system_prompt = _VERIFY_SYSTEM_TEMPLATE.format(response_language=response_language_name)

    interactions = []
    summary = ""
    risk_level = "Unknown"
    risk_level_label = None
    analysis_success = False

    main_user_content = (
        f"Patient Context: {body.patient_context or 'None'}\n"
        f"Drugs: {', '.join(body.drugs)}\n\n"
        f"FDA Data:\n{fda_context}"
    )

    verify_binding = _get_verify()
    for attempt in range(2):
        try:
            main_req = CompletionRequest(
                model=verify_binding.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": main_user_content}
                ],
                response_format={"type": "json_object"},
            )
            completion = await verify_binding.provider.complete(main_req)
            analysis = json.loads(completion.content)
            temp = []
            for item in analysis.get("interactions", []):
                drugs = item.get("drugs", [])
                if len(drugs) < 2 or not all(isinstance(d, str) and d.strip() for d in drugs):
                    continue
                temp.append(DrugInteraction(
                    drug_pair=tuple(drugs[:2]),
                    severity=item.get("severity","Unknown"),
                    severity_label=item.get("severity_label") or None,
                    description=item.get("description","No description provided"),
                    clinical_recommendation=item.get("recommendation",""),
                    source="FDA Label Analysis",
                    source_url=f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drugs[0].replace(' ','+')}"
                ))
            interactions = temp
            risk_level_label = analysis.get("risk_level_label") or None
            analysis_success = True
            break
        except Exception as e:
            logger.error("LLM attempt %d failed: %s", attempt+1, e)

    if analysis_success:
        if interactions:
            severity_order = {"Critical":4,"Major":3,"Moderate":2,"Minor":1}
            counts: dict = {}
            for i in interactions:
                counts[i.severity] = counts.get(i.severity, 0) + 1
            summary = f"Found {len(interactions)} interaction(s): " + ", ".join(
                f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: severity_order.get(x[0],0), reverse=True)
            )
            if any(i.severity=="Critical" for i in interactions): risk_level = "Critical"
            elif any(i.severity=="Major" for i in interactions):   risk_level = "Major"
            elif any(i.severity=="Moderate" for i in interactions): risk_level = "Moderate"
            else: risk_level = "Minor"
        else:
            summary = "No significant drug interactions found in the FDA data."
            risk_level = "Low"

    elapsed_ms = int((time.time()-start_time)*1000)

    if not is_anonymous:
        _safe_db_write(db,
            AuditLog(id=audit_id, user_id=user_id,
                action="verify", query_content=f"Checked: {body.drugs}", ip_address="0.0.0.0"),
            ChatHistory(user_id=user_id, session_type="verify",
                question=f"Drugs: {', '.join(body.drugs)}", answer=summary),
            label="Verify")

    if spelling_corrections:
        summary = "Note: " + "; ".join(spelling_corrections) + ". Please verify. " + summary

    # 成功後扣減 credits + log cost
    if is_anonymous:
        await deduct_anonymous_credits(db, anon_id, "verify")
    else:
        await deduct_credits(db, user_id, "verify")

    # Cost logging (§2.1 PHASE D: model from verify_binding; v0.4 A10: anon → user_id=None)
    try:
        from api.services.cost_tracker import log_api_cost
        if analysis_success and 'completion' in locals():
            await log_api_cost(
                db,
                None if is_anonymous else user_id,
                "verify",
                verify_binding.model,
                completion.input_tokens,
                completion.output_tokens,
            )
    except Exception as e:
        logger.error("Cost log error: %s", e)

    return VerifyResponse(
        drugs_analyzed=body.drugs, interactions=interactions,
        summary=summary, risk_level=risk_level,
        risk_level_label=risk_level_label,
        response_language=response_language,
        disclaimer=get_verify_disclaimer(response_language),
        query_time_ms=elapsed_ms,
        query_id=audit_id,
    )


# ============================================================
# 功能 4：Explain — 醫療報告解讀 (新功能)
# ============================================================
@app.post("/api/explain")
async def explain_report(
    body: ExplainRequest,
    request: Request,
    auth: Tuple[Optional[str], Optional[str]] = Depends(require_auth_or_anonymous),
    db: Session = Depends(get_db),
):
    """
    3-stage pipeline:
    Stage 1: Entity extraction (GPT-4.1-mini)
    Stage 2: Parallel API lookups (LOINC, RxNorm, MedlinePlus)
    Stage 3: Plain-language explanation (GPT-4.1, streaming)
    """
    user_id, anon_id = auth

    # Decision 001 v0.3: L0 anonymous cannot access Explain (Pro-only feature path)
    if anon_id is not None:
        raise FeatureNotAvailable("explain")

    # PHI 偵測
    phi_resp = _check_phi(body.report_text, "/api/explain", request)
    if phi_resp:
        return phi_resp

    # Resolve user-preferred response language (mirrors Verify § 2.9 pattern)
    response_language = _resolve_response_language(body.response_language, request)

    logger.info("[Explain] user=%s report_length=%d response_language=%s",
                user_id, len(body.report_text), response_language)

    # Credit 檢查
    if not TEST_MODE:
        allowed, reason = await check_credits(db, user_id, "explain")
        if not allowed:
            if reason == "limit_reached":
                return JSONResponse(status_code=403, content={"error": "limit_reached", "upgrade_url": "/pricing"})
            elif reason == "daily_cap_reached":
                return JSONResponse(status_code=429, content={"error": "daily_cap_reached", "message": "You've reached today's usage limit. Resets at midnight UTC."})

    async def event_stream():
        full_answer = ""
        audit_id = f"exp_{uuid.uuid4().hex[:16]}"
        try:
            # Emit query_id first so the client can tag subsequent analytics events
            yield f"data: {json.dumps({'type': 'query_id', 'query_id': audit_id})}\n\n"

            async for event in run_explain_pipeline(
                report_text=body.report_text,
                response_language=response_language,
            ):
                # Serialize structured result for ChatHistory.answer text column
                if isinstance(event, dict) and event.get("type") == "explain_result":
                    full_answer = json.dumps(event.get("content", {}), ensure_ascii=False)
                # Save to history when done
                if isinstance(event, dict) and event.get("type") == "done":
                    _safe_db_write(db, AuditLog(
                            id=audit_id,
                            user_id=user_id,
                            action="explain",
                            query_content=PHIDetector.sanitize_for_log(body.report_text[:500]),
                            ip_address="0.0.0.0"
                        ), label="Explain Audit")
                    _safe_db_write(db, ChatHistory(
                            user_id=user_id,
                            session_type="explain",
                            question=body.report_text[:500],
                            answer=full_answer
                        ), label="Explain History")
                    # 成功後扣減 credits
                    await deduct_credits(db, user_id, "explain")
                    # Cost logging
                    try:
                        from api.services.cost_tracker import log_api_cost
                        usage = event.get("usage")
                        if usage:
                            await log_api_cost(
                                db, user_id, "explain",
                                # Default to generator model (Explain Stage 3 uses GENERATOR_* per PHASE B).
                                usage.get("model", generator.model),
                                usage.get("prompt_tokens", 0),
                                usage.get("completion_tokens", 0)
                            )
                    except Exception as e:
                        logger.error("Cost log error: %s", e)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            # Generic error UX (2026-04-29): unexpected exceptions become
            # the `generic` error_code. Pipeline-internal errors emit their
            # own SSE error events with specific codes before reaching here.
            logger.exception("Explain stream error: %s", type(e).__name__)
            yield f"data: {json.dumps({'type': 'error', 'code': 'generic', 'message': 'Unexpected error'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Explain: identification correction feedback ───────────────
class IdentifyCorrectionRequest(BaseModel):
    original_input: str
    identified_as: str
    correct_name: str

@app.post("/api/explain/feedback")
async def explain_identify_feedback(
    body: IdentifyCorrectionRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(creds)
    try:
        db.add(UserFeedback(
            id=f"fb_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            query=body.original_input,
            response=body.identified_as,
            rating=2,
            feedback_text=body.correct_name,
            category="identify_correction",
        ))
        db.commit()
        return {"status": "success", "message": "Correction recorded"}
    except Exception as e:
        logger.error("Explain identify feedback error: %s", type(e).__name__)
        return {"status": "error", "message": "Failed to save correction. Please try again."}


# ============================================================
# 功能 4b：Explain — Image text extraction
# ============================================================
from fastapi import File, UploadFile

@app.post("/api/explain/extract-image")
async def explain_extract_image(
    file: UploadFile = File(...),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(creds)

    # Pro-only gate: file upload requires Pro plan
    if not TEST_MODE:
        from api.models.sql_models import UserUsage
        usage = db.query(UserUsage).filter(UserUsage.clerk_user_id == user_id).first()
        if not usage or usage.plan_type != "pro":
            return JSONResponse(status_code=403, content={
                "type": "pro_required",
                "detail": "PDF and image upload requires Pro plan",
                "suggestion": "Upgrade to Pro to upload and analyze medical reports, lab results, and images."
            })

    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        return JSONResponse(status_code=400, content={"detail": "Unsupported file type. Use JPG, PNG, or WebP."})

    # Read and validate size (10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"detail": "File too large. Maximum size is 10MB."})

    import base64 as _b64
    b64_image = _b64.b64encode(contents).decode("utf-8")
    media_type = file.content_type or "image/jpeg"

    try:
        vision_binding = _get_vision()
        vision_req = CompletionRequest(
            model=vision_binding.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical document reader. Extract all text from this medical report image exactly as written in the original language. Do not translate. Preserve all original characters, numbers, units, symbols and formatting. Output only the extracted text, nothing else.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64_image}"},
                        }
                    ],
                },
            ],
            max_tokens=4000,
            temperature=0,
        )
        response = await vision_binding.provider.complete(vision_req)
        extracted = response.content or ""
        return {"text": extracted.strip()}
    except Exception as e:
        logger.error("Image extraction error: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"detail": "Could not extract text from image."})


# ============================================================
# 功能 5：Feedback
# ============================================================
class FeedbackCreate(BaseModel):
    query: str = Field(..., max_length=5000)
    response: str = Field(..., max_length=20000)
    rating: int
    feedback_text: Optional[str] = Field(None, max_length=2000)
    category: str = Field(..., max_length=100)

@app.post("/api/feedback")
async def create_feedback(
    feedback: FeedbackCreate,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    try:
        db.add(UserFeedback(
            id=f"fb_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            query=feedback.query,
            response=feedback.response,
            rating=feedback.rating,
            feedback_text=PHIDetector.sanitize_for_log(feedback.feedback_text) if feedback.feedback_text else None,
            category=feedback.category
        ))
        db.commit()
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.error("Feedback error: %s", type(e).__name__)
        return {"status": "error", "message": "Failed to save feedback. Please try again."}


# ============================================================
# 功能 5a：Bug Report (PRD 2.4)
# ============================================================
_BUG_REPORT_ISSUE_TYPES = {"inaccurate", "ui_error", "feature_request", "other"}


class BugReportCreate(BaseModel):
    issue_type: str = Field(..., max_length=32)
    description: str = Field(..., min_length=1, max_length=2000)
    email: Optional[str] = Field(None, max_length=200)
    query_id: Optional[str] = Field(None, max_length=64)
    page_url: Optional[str] = Field(None, max_length=500)
    locale: Optional[str] = Field(None, max_length=16)


async def _optional_user_id(request: Request) -> Optional[str]:
    """Extract Clerk user_id from Authorization header if present and valid.

    Unlike require_auth(), this returns None on missing/invalid tokens rather
    than raising — required for endpoints that accept anonymous submissions.
    """
    if TEST_MODE:
        return os.getenv("TEST_USER_ID") or None
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        jwks = await get_jwks()
        payload = jose_jwt.decode(
            token, jwks, algorithms=["RS256"], options={"verify_aud": False}
        )
        return payload.get("sub")
    except JWTError as e:
        logger.warning("[bug-report] JWT verification failed: %s", e)
        return None
    except Exception as e:
        logger.error("[bug-report] Unexpected error in _optional_user_id: %s: %s", type(e).__name__, e)
        return None


@app.post("/api/bug-report")
async def create_bug_report(
    payload: BugReportCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    if payload.issue_type not in _BUG_REPORT_ISSUE_TYPES:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid issue_type"})

    user_id = await _optional_user_id(request)
    user_agent = request.headers.get("user-agent", "")[:500] or None
    bug_id = f"bug_{uuid.uuid4().hex[:16]}"

    record = BugReport(
        id=bug_id,
        issue_type=payload.issue_type,
        description=PHIDetector.sanitize_for_log(payload.description) or payload.description,
        email=payload.email or None,
        user_id=user_id,
        query_id=payload.query_id or None,
        page_url=payload.page_url or None,
        user_agent=user_agent,
        locale=payload.locale or None,
    )
    if _safe_db_write(db, record, label="BugReport"):
        return {"status": "success", "id": bug_id}
    return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to save bug report."})


# ============================================================
# 功能 6：History
# ============================================================
@app.get("/api/history")
async def get_user_history(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)

    # Determine plan type
    from api.models.sql_models import UserUsage
    usage = db.query(UserUsage).filter(UserUsage.clerk_user_id == user_id).first()
    is_pro = usage and usage.plan_type == "pro"

    query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)

    if is_pro:
        # Pro: full history (last 365 days)
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        query = query.filter(ChatHistory.created_at >= cutoff)
    else:
        # Free: last 7 days only
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        query = query.filter(ChatHistory.created_at >= cutoff)

    return query.order_by(desc(ChatHistory.created_at)).limit(200).all()


# ============================================================
# Phase 4：Lemon Squeezy 金流
# ============================================================
import hmac
import hashlib

class CheckoutRequest(BaseModel):
    variant_id: str

@app.post("/api/checkout")
async def create_checkout(
    body: CheckoutRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    try:
        from api.services.lemonsqueezy_service import create_checkout as ls_checkout
        url = await ls_checkout(
            variant_id=body.variant_id,
            clerk_user_id=user_id
        )
        return {"url": url}
    except Exception as e:
        logger.error("Checkout error: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"detail": "Checkout failed"})


class DodoCheckoutRequest(BaseModel):
    product_id: str

@app.post("/api/checkout/dodo")
async def create_dodo_checkout(
    body: DodoCheckoutRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    dodo_api_key = os.getenv("DODO_API_KEY", "")
    clerk_secret = os.getenv("CLERK_SECRET_KEY", "")

    # Fetch user email + name from Clerk
    user_email = ""
    user_name = ""
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient() as hc:
            resp = await hc.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {clerk_secret}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                clerk_user = resp.json()
                primary_email_id = clerk_user.get("primary_email_address_id", "")
                for ea in clerk_user.get("email_addresses", []):
                    if ea.get("id") == primary_email_id:
                        user_email = ea.get("email_address", "")
                        break
                first = clerk_user.get("first_name") or ""
                last = clerk_user.get("last_name") or ""
                user_name = f"{first} {last}".strip() or user_email.split("@")[0]
    except Exception as e:
        logger.warning("Clerk user lookup error: %s", type(e).__name__)

    if not user_email:
        return JSONResponse(status_code=422, content={"detail": "Could not retrieve user email"})

    # Call Dodo Payments API
    payload = {
        "product_id": body.product_id,
        "quantity": 1,
        "customer": {"email": user_email, "name": user_name},
        "billing": {"country": "TW"},
        "payment_link": True,
        "return_url": "https://vela.an-tho.com/dashboard",
        "metadata": {"clerk_user_id": user_id},
    }
    logger.info("[Dodo] POST /subscriptions for product=%s", body.product_id)
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient() as hc:
            resp = await hc.post(
                "https://live.dodopayments.com/subscriptions",
                headers={
                    "Authorization": f"Bearer {dodo_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15.0,
            )
            logger.info("[Dodo] Response status: %d", resp.status_code)
            if resp.status_code not in (200, 201):
                return JSONResponse(status_code=502, content={"detail": "Payment provider error"})
            data = resp.json()
            payment_link = data.get("payment_link") or data.get("url") or ""
            if not payment_link:
                logger.error("[Dodo] Missing payment_link in response")
                return JSONResponse(status_code=502, content={"detail": "No payment link returned"})
            logger.info("[Dodo] payment_link generated")
            return {"payment_link": payment_link}
    except Exception as e:
        logger.error("[Dodo] Exception: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"detail": "Checkout failed"})


@app.post("/api/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, db: Session = Depends(get_db)):
    # 驗證 webhook signature
    signing_secret = os.getenv("LEMON_SQUEEZY_SIGNING_SECRET", "")
    if not signing_secret:
        return JSONResponse(status_code=500, content={"detail": "Webhook signing secret not configured"})

    body_bytes = await request.body()
    signature = request.headers.get("X-Signature", "")

    expected = hmac.new(
        signing_secret.encode(),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return JSONResponse(status_code=401, content={"detail": "Invalid signature"})

    payload = json.loads(body_bytes)
    event_name = payload.get("meta", {}).get("event_name", "")
    event_id = payload.get("meta", {}).get("uuid", "")
    custom_data = payload.get("meta", {}).get("custom_data", {})
    clerk_user_id = custom_data.get("clerk_user_id", "")
    attrs = payload.get("data", {}).get("attributes", {})

    if not clerk_user_id:
        return {"status": "ignored", "reason": "no clerk_user_id"}

    # Idempotency 檢查
    from api.models.sql_models import WebhookEvent, UserUsage
    existing = db.query(WebhookEvent).filter(
        WebhookEvent.event_id == event_id
    ).first()
    if existing:
        return {"status": "already_processed"}

    # 處理事件
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == clerk_user_id
    ).first()
    if not usage:
        usage = UserUsage(clerk_user_id=clerk_user_id)
        db.add(usage)

    from datetime import datetime, timezone

    if event_name == "subscription_created":
        usage.plan_type = "pro"
        usage.lemon_subscription_id = str(payload.get("data", {}).get("id", ""))
        usage.lemon_variant_id = attrs.get("variant_id", "")
        ends_at = attrs.get("renews_at") or attrs.get("ends_at")
        if ends_at:
            usage.current_period_end = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))

    elif event_name == "subscription_updated":
        ends_at = attrs.get("renews_at") or attrs.get("ends_at")
        if ends_at:
            usage.current_period_end = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))

    elif event_name in ["subscription_cancelled", "subscription_expired"]:
        usage.plan_type = "free"

    elif event_name == "subscription_payment_refunded":
        usage.plan_type = "free"

    elif event_name == "subscription_payment_failed":
        # 給寬限期，不立即降級
        pass

    # 記錄已處理的 event
    db.add(WebhookEvent(event_id=event_id, event_type=event_name))
    db.commit()

    return {"status": "ok", "event": event_name}


# ============================================================
# Dodo Payments webhook
# ============================================================
@app.post("/api/webhook/dodo")
async def dodo_webhook(request: Request, db: Session = Depends(get_db)):
    body_bytes = await request.body()

    # Signature verification — Standard Webhooks spec (MANDATORY)
    # https://www.standardwebhooks.com/
    dodo_secret = os.getenv("DODO_WEBHOOK_SECRET", "")
    if not dodo_secret:
        logger.error("[Dodo Webhook] DODO_WEBHOOK_SECRET not configured, rejecting")
        return JSONResponse(status_code=500, content={"detail": "Webhook not configured"})

    webhook_id        = request.headers.get("webhook-id", "")
    webhook_timestamp = request.headers.get("webhook-timestamp", "")
    webhook_signature = request.headers.get("webhook-signature", "")

    if not webhook_id or not webhook_timestamp or not webhook_signature:
        return JSONResponse(status_code=401, content={"detail": "Missing signature headers"})

    # Replay protection: reject timestamps older than 5 minutes
    try:
        ts = int(webhook_timestamp)
        if abs(time.time() - ts) > 300:
            return JSONResponse(status_code=401, content={"detail": "Timestamp too old"})
    except ValueError:
        return JSONResponse(status_code=401, content={"detail": "Invalid timestamp"})

    import base64
    # Strip "whsec_" prefix and base64-decode the secret
    raw_secret = dodo_secret[len("whsec_"):] if dodo_secret.startswith("whsec_") else dodo_secret
    secret_bytes = base64.b64decode(raw_secret)

    # Signed payload: {webhook-id}.{webhook-timestamp}.{raw_body}
    signed_payload = f"{webhook_id}.{webhook_timestamp}.".encode() + body_bytes

    # HMAC-SHA256, base64-encoded
    expected_sig = base64.b64encode(
        hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()
    ).decode()

    # webhook-signature may be space-separated "v1,<sig>" entries
    received_sigs = [
        part.split(",", 1)[1]
        for part in webhook_signature.split(" ")
        if part.startswith("v1,")
    ]
    if not received_sigs or not any(hmac.compare_digest(expected_sig, s) for s in received_sigs):
        return JSONResponse(status_code=401, content={"detail": "Invalid signature"})

    import json as _json
    payload = _json.loads(body_bytes)
    event_type = payload.get("type", "")
    event_id = payload.get("data", {}).get("id") or payload.get("id", "")
    if not event_id:
        event_id = f"dodo_{uuid.uuid4().hex[:16]}"

    # Idempotency check
    from api.models.sql_models import WebhookEvent, UserUsage
    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == f"dodo_{event_id}").first()
    if existing:
        return {"status": "already_processed"}

    # Only handle subscription events we care about
    handled_events = ("subscription.active", "subscription.cancelled", "subscription.expired", "subscription.failed")
    if event_type not in handled_events:
        db.add(WebhookEvent(event_id=f"dodo_{event_id}", event_type=event_type))
        db.commit()
        return {"status": "ignored", "event": event_type}

    # Locate customer from payload
    customer = payload.get("data", {}).get("customer") or payload.get("customer", {})
    customer_email = customer.get("email", "") if isinstance(customer, dict) else ""

    # TEST_MODE: accept clerk_user_id directly from payload to bypass Clerk lookup
    clerk_user_id = None
    if TEST_MODE:
        clerk_user_id = (
            payload.get("data", {}).get("clerk_user_id")
            or payload.get("clerk_user_id")
            or (customer.get("clerk_user_id") if isinstance(customer, dict) else None)
        )
        if clerk_user_id:
            logger.info("TEST_MODE: using clerk_user_id=%s from payload", clerk_user_id)
        else:
            logger.warning("TEST_MODE: no clerk_user_id in payload, falling back to Clerk lookup")
    else:
        logger.debug("Webhook: TEST_MODE=false, using Clerk lookup for %s", customer_email)

    if not clerk_user_id:
        if not customer_email:
            logger.warning("Dodo webhook %s: no customer email in payload", event_type)
            return JSONResponse(status_code=422, content={"detail": "No customer email"})

        # Look up Clerk user by email
        clerk_secret = os.getenv("CLERK_SECRET_KEY", "")
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient() as hc:
                resp = await hc.get(
                    "https://api.clerk.com/v1/users",
                    params={"email_address": customer_email, "limit": 1},
                    headers={"Authorization": f"Bearer {clerk_secret}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    users = resp.json()
                    if users:
                        clerk_user_id = users[0].get("id")
        except Exception as e:
            logger.warning("Clerk lookup error: %s", type(e).__name__)

    if not clerk_user_id:
        logger.warning("Dodo webhook %s: Clerk user not found", event_type)
        return JSONResponse(status_code=422, content={"detail": "Clerk user not found"})

    # Update UserUsage
    usage = db.query(UserUsage).filter(UserUsage.clerk_user_id == clerk_user_id).first()
    if not usage:
        usage = UserUsage(clerk_user_id=clerk_user_id)
        db.add(usage)

    # Store Dodo customer/subscription IDs
    dodo_customer_id = customer.get("customer_id", "") if isinstance(customer, dict) else ""
    dodo_subscription_id = payload.get("data", {}).get("subscription_id") or payload.get("data", {}).get("id", "")
    if dodo_customer_id:
        usage.dodo_customer_id = dodo_customer_id
    if dodo_subscription_id:
        usage.dodo_subscription_id = dodo_subscription_id

    if event_type == "subscription.active":
        usage.plan_type = "pro"
        logger.info("Dodo: upgraded to pro (customer=%s, sub=%s)", dodo_customer_id, dodo_subscription_id)
    elif event_type in ("subscription.cancelled", "subscription.expired", "subscription.failed"):
        usage.plan_type = "free"
        usage.dodo_subscription_id = None  # Clear subscription, keep customer_id for re-subscribe
        logger.info("Dodo: downgraded to free (%s) — plan_type=%s, user=%s", event_type, usage.plan_type, clerk_user_id)

    # Audit log
    from api.models.sql_models import AuditLog
    audit_id = f"wh_{uuid.uuid4().hex[:16]}"
    db.add(AuditLog(
        id=audit_id,
        user_id=clerk_user_id,
        action=f"dodo_webhook:{event_type}",
        query_content=f"customer={dodo_customer_id}, sub={dodo_subscription_id}",
        ip_address=_get_client_ip(request),
    ))

    db.add(WebhookEvent(event_id=f"dodo_{event_id}", event_type=event_type))
    db.commit()
    return {"status": "ok", "event": event_type}


@app.get("/api/user/status")
async def user_status(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    from api.models.sql_models import UserUsage
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == user_id
    ).first()

    if not usage:
        return {"plan_type": "free", "credits_used_today": 0, "daily_limit": 10}

    from api.services.usage_service import reset_daily_if_needed, FREE_DAILY_LIMIT, PRO_DAILY_SAFETY_CAP
    usage = await reset_daily_if_needed(db, usage)
    daily_limit = PRO_DAILY_SAFETY_CAP if usage.plan_type == "pro" else FREE_DAILY_LIMIT
    return {
        "plan_type": usage.plan_type,
        "credits_used_today": usage.credits_used_today,
        "daily_limit": daily_limit,
    }


@app.get("/api/user/portal")
async def user_portal(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    from api.models.sql_models import UserUsage
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == user_id
    ).first()

    if not usage or usage.plan_type != "pro":
        return JSONResponse(status_code=404, content={"detail": "No active subscription"})

    # Dodo Payments uses a universal customer portal
    return {"url": "https://customer.dodopayments.com"}


@app.post("/api/subscription/cancel")
async def cancel_subscription(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    from api.models.sql_models import UserUsage
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == user_id
    ).first()

    if not usage or not usage.dodo_subscription_id:
        return JSONResponse(status_code=404, content={"error": "No active subscription found"})

    dodo_api_key = os.getenv("DODO_API_KEY", "")
    if not dodo_api_key:
        logger.error("DODO_API_KEY not configured")
        return JSONResponse(status_code=500, content={"error": "Service configuration error"})

    try:
        import httpx as _httpx
        async with _httpx.AsyncClient() as hc:
            resp = await hc.patch(
                f"https://live.dodopayments.com/subscriptions/{usage.dodo_subscription_id}",
                json={"status": "cancelled"},
                headers={"Authorization": f"Bearer {dodo_api_key}", "Content-Type": "application/json"},
                timeout=15.0,
            )
            if resp.status_code not in (200, 204):
                logger.error("Dodo cancel failed: %s %s", resp.status_code, resp.text)
                return JSONResponse(status_code=500, content={"error": "Unable to cancel subscription"})
    except Exception as e:
        logger.error("Dodo cancel error: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"error": "Unable to cancel subscription"})

    logger.info("Subscription cancel requested: user=%s, sub=%s", user_id, usage.dodo_subscription_id)
    return {"status": "success", "message": "Subscription cancelled"}


# ============================================================
# 管理員：Cost Dashboard
# ============================================================
@app.get("/api/admin/costs")
async def admin_costs(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)

    # 僅限管理員
    admin_id = os.getenv("ADMIN_USER_ID", "")
    if not admin_id or user_id != admin_id:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    from sqlalchemy import func, cast, Date
    from datetime import datetime, timezone
    from api.models.sql_models import ApiCostLog

    today = datetime.now(timezone.utc).date()

    # 今日總成本
    daily = db.query(
        func.sum(ApiCostLog.estimated_cost_usd)
    ).filter(
        cast(ApiCostLog.created_at, Date) == today
    ).scalar() or 0.0

    # 按功能分類
    by_feature = db.query(
        ApiCostLog.feature,
        func.sum(ApiCostLog.estimated_cost_usd)
    ).filter(
        cast(ApiCostLog.created_at, Date) == today
    ).group_by(ApiCostLog.feature).all()

    # 平均成本
    avg_costs = db.query(
        ApiCostLog.feature,
        func.avg(ApiCostLog.estimated_cost_usd)
    ).group_by(ApiCostLog.feature).all()

    # 總用戶數
    from api.models.sql_models import UserUsage
    total_users = db.query(func.count(UserUsage.clerk_user_id)).scalar() or 0

    # 今日總 API calls
    total_calls_today = db.query(
        func.count(ApiCostLog.id)
    ).filter(
        cast(ApiCostLog.created_at, Date) == today
    ).scalar() or 0

    return {
        "daily_total_usd": round(float(daily), 6),
        "by_feature": {row[0]: round(float(row[1]), 6) for row in by_feature},
        "avg_cost_per_feature": {row[0]: round(float(row[1]), 6) for row in avg_costs},
        "total_users": total_users,
        "total_api_calls_today": total_calls_today
    }


# ============================================================
# 健康檢查
# ============================================================
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.2.0"}

@app.get("/api/status")
async def api_status(creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth)):
    try:
        from api.database.vector_store import get_vector_store
        vector_store_status = get_vector_store().get_stats()
    except Exception as e:
        vector_store_status = {"error": "unavailable"}

    return {
        "status": "healthy",
        "version": "2.2.0",
        "features": {
            "research": True, "pubmed": True,
            "fda": True, "verify": True, "explain": True,
            "feedback": True, "history": True
        },
        "vector_store": vector_store_status
    }


# ============================================================
# Public Query Page — PRD § 4.5 Share Answer (PHASE A)
# Must register BEFORE serve_nextjs_pages catch-all below; the
# catch-all `@app.get("/{path:path}")` would otherwise absorb /q/*
# and try to serve a static HTML file that doesn't exist.
# ============================================================
from api.models.sql_models import SharedQuery as _SharedQueryModel
from api.services import share_renderer as _share_renderer
from api.services.og_image import generate_og_png as _generate_og_png

# Per-IP view rate limit for /q/{share_id}. PHASE A uses Option B
# (in-handler check) instead of extending the middleware path-matcher
# to support prefixes — keeps the change isolated and avoids touching
# every other dynamic route's matching semantics.
_Q_VIEW_LIMIT = 60
_Q_VIEW_WINDOW = 60  # seconds


def _resolve_share_locale(request: Request, share_locale: str | None) -> str:
    """Prefer the locale recorded at share-creation time. Fall back to
    Accept-Language. PHASE A only ships en + zh-TW renderer copy so
    anything else degrades to en (utils/i18n-share.ts has the same
    fallback policy)."""
    if share_locale:
        return _share_renderer.resolve_locale(share_locale)
    accept = (request.headers.get("accept-language") or "").lower()
    if "zh-tw" in accept or "zh-hant" in accept:
        return "zh-TW"
    return "en"


@app.get("/q/{share_id}")
async def serve_share_page(share_id: str, request: Request, db: Session = Depends(get_db)):
    # Defense-in-depth: reject path traversal even though FastAPI route
    # parsing should already prevent it.
    if not share_id or "/" in share_id or "\\" in share_id or len(share_id) > 64:
        return JSONResponse(status_code=404, content={"detail": "Not found."})

    # Per-IP rate limit (Option B: in-handler, see comment above)
    if not TEST_MODE:
        ip = _get_client_ip(request)
        key = f"{ip}:/q/"
        now = _time.time()
        _rate_store[key] = [t for t in _rate_store[key] if now - t < _Q_VIEW_WINDOW]
        if len(_rate_store[key]) >= _Q_VIEW_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {_Q_VIEW_LIMIT} requests per {_Q_VIEW_WINDOW}s."},
            )
        _rate_store[key].append(now)

    share = db.query(_SharedQueryModel).filter(_SharedQueryModel.share_id == share_id).first()
    if share is None:
        return JSONResponse(status_code=404, content={"detail": "Not found."})

    locale = _resolve_share_locale(request, getattr(share, "locale", None))

    # Flagged + revoked must return 200 so social scrapers see the
    # takedown notice instead of a blank 404 (preview cards already
    # cached by Slack/Twitter remain valid links).
    if getattr(share, "flagged", False):
        html = _share_renderer.render_flagged_page(locale, share=share)
        return Response(content=html, media_type="text/html; charset=utf-8")

    if not getattr(share, "is_public", True):
        html = _share_renderer.render_revoked_page(locale, share=share)
        return Response(content=html, media_type="text/html; charset=utf-8")

    html = _share_renderer.render_public_page(share, locale)

    # Non-blocking side effects: view_count + last_viewed_at, PostHog event.
    # All wrapped in try/except per CLAUDE.md Rule 13 (non-essential
    # tracking must never fail the request).
    try:
        from datetime import datetime as _dt
        is_first_view = share.last_viewed_at is None
        share.view_count = (share.view_count or 0) + 1
        share.last_viewed_at = _dt.utcnow()
        db.commit()
    except Exception as e:
        logger.warning("[share] view_count update failed for %s: %s", share_id, e)
        try:
            db.rollback()
        except Exception:
            pass
        is_first_view = False

    # TODO(PHASE B+): server-side `share_link_visited` PostHog event.
    # Backend currently has no posthog client wired (utils/analytics.ts
    # is frontend-only). Skipping rather than blocking PHASE A on it.
    # Payload would be: {share_id, referrer_domain, is_first_view}.
    _ = is_first_view

    return Response(content=html, media_type="text/html; charset=utf-8")


# ============================================================
# Explore Pages — PRD § 4.6 PHASE A
# Team-curated public SEO pages at /explore/{slug}. Reuses share_renderer
# helpers and follows the same registration ordering rule as /q/{share_id}
# above (before the Next.js catch-all). Uses Option B (in-handler) rate
# limit matching /q/. PHASE B-E add sitemap, content import CLI,
# breadcrumb UI, and PostHog wiring.
# ============================================================
from api.services import explore_renderer as _explore_renderer
from fastapi import HTTPException as _HTTPException

_EXPLORE_VIEW_LIMIT = 60
_EXPLORE_VIEW_WINDOW = 60  # seconds


def _resolve_explore_locale_from_request(request: Request, query_locale: str | None) -> str:
    """Prefer ?locale= querystring (explicit), fall back to Accept-Language,
    default 'en'. PHASE A first-class locales: en + zh-TW; others ship
    machine-baseline copy and degrade to en at the renderer."""
    if query_locale:
        return query_locale
    accept = (request.headers.get("accept-language") or "").lower()
    if "zh-tw" in accept or "zh-hant" in accept:
        return "zh-TW"
    return "en"


@app.get("/explore/category/{category}")
async def serve_explore_category(category: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)):
    """PRD § 4.6 PHASE D — category listing page.

    Registered BEFORE /explore/{slug} so FastAPI's path-matching
    priority resolves /explore/category/foo to this handler (not to
    /explore/{slug=category} which would 400 on validate_slug if
    `category` contained dots/etc).
    """
    if not TEST_MODE:
        ip = _get_client_ip(request)
        key = f"{ip}:/explore/category/"
        now = _time.time()
        _rate_store[key] = [t for t in _rate_store[key] if now - t < _EXPLORE_VIEW_WINDOW]
        if len(_rate_store[key]) >= _EXPLORE_VIEW_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {_EXPLORE_VIEW_LIMIT} requests per {_EXPLORE_VIEW_WINDOW}s."},
            )
        _rate_store[key].append(now)

    resolved_locale = _resolve_explore_locale_from_request(request, locale)

    try:
        html = _explore_renderer.render_category_listing(db, category, resolved_locale)
    except _HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return Response(content=html, media_type="text/html; charset=utf-8")


@app.get("/explore/{slug}")
async def serve_explore_page(slug: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)):
    # Per-IP rate limit (Option B, in-handler — same pattern as /q/{share_id})
    if not TEST_MODE:
        ip = _get_client_ip(request)
        key = f"{ip}:/explore/"
        now = _time.time()
        _rate_store[key] = [t for t in _rate_store[key] if now - t < _EXPLORE_VIEW_WINDOW]
        if len(_rate_store[key]) >= _EXPLORE_VIEW_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {_EXPLORE_VIEW_LIMIT} requests per {_EXPLORE_VIEW_WINDOW}s."},
            )
        _rate_store[key].append(now)

    resolved_locale = _resolve_explore_locale_from_request(request, locale)

    try:
        html, page = _explore_renderer.render_explore_page(db, slug, resolved_locale)
    except _HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    # Non-blocking view_count + last_updated_at NOT touched (last_updated_at
    # is content-update timestamp, not view timestamp).
    try:
        page.view_count = (page.view_count or 0) + 1
        db.commit()
    except Exception as e:
        logger.warning("[explore] view_count update failed for %s/%s: %s", slug, resolved_locale, e)
        try:
            db.rollback()
        except Exception:
            pass

    return Response(content=html, media_type="text/html; charset=utf-8")


# ============================================================
# Sitemap — PRD § 4.6 PHASE B
# /sitemap-explore.xml is a dynamic FastAPI route that queries the
# ExplorePage table. No rate limit (crawler-friendly). public/sitemap.xml
# (Next.js static) is the sitemap INDEX referencing this + the main
# static sitemap.
# ============================================================
from api.services import sitemap_explore as _sitemap_explore


@app.get("/sitemap-explore.xml")
async def sitemap_explore_xml(db: Session = Depends(get_db)):
    xml = _sitemap_explore.generate_explore_sitemap(db)
    return Response(content=xml, media_type="application/xml; charset=utf-8")


# ============================================================
# Share API — PRD § 4.5 PHASE B
# Endpoints: POST /api/share/create, POST /api/share/{id}/revoke,
#            GET  /api/share/list,    POST /api/share/track-visit
# Auth: signed-in only on create/revoke/list (per PRD 修訂 1).
#       track-visit is unauthenticated (called from the public Jinja2
#       template) but rate-limited per IP via the global rate limiter.
# ============================================================
import hashlib as _hashlib
import secrets as _secrets
from datetime import timedelta as _timedelta

from api.middleware.phi_handler import ShareDetectResult as _ShareDetectResult

_SHARE_DAILY_LIMIT = 50
_SHARE_ID_RETRIES = 3


def _hash_created_by(user_id: str) -> str:
    """sha256(salt + user_id)[:16]. Same hex-truncation convention
    as anon_id derivation (api/services/anonymous_identity.py)."""
    raw = f"{SHARE_CREATED_BY_SALT}:{user_id}".encode("utf-8")
    return _hashlib.sha256(raw).hexdigest()[:16]


def _share_url(share_id: str) -> str:
    base = os.getenv("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com").rstrip("/")
    return f"{base}/q/{share_id}"


def _og_image_public_url(share_id: str) -> str:
    base = os.getenv("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com").rstrip("/")
    return f"{base}/static/og/{share_id}.png"


class ShareCreateRequest(BaseModel):
    query_id: str = Field(..., min_length=1, max_length=128)
    query_text: str = Field(..., min_length=1, max_length=8000)
    answer_text: str = Field(..., min_length=1, max_length=40000)
    citations: list = Field(default_factory=list)
    locale: Optional[str] = Field(default=None, max_length=16)


@app.post("/api/share/create")
async def share_create(
    body: ShareCreateRequest,
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(creds)
    if not user_id:
        # Defense-in-depth — require_auth would have raised already.
        return JSONResponse(
            status_code=403,
            content={"type": "share_anon_blocked", "message": "Sign in to share answers."},
        )

    # ── 1. Sensitive detection (PRD § 4.5 PHASE B Step 2.2) ───
    share_check = PHIDetector.detect(
        body.query_text,
        mode="share",
        locale=body.locale,
    )
    if isinstance(share_check, _ShareDetectResult) and not share_check.is_safe:
        return JSONResponse(
            status_code=422,
            content={
                "type": "share_sensitive_blocked",
                "reasons": share_check.reasons,
                "unknown_locale_fallback": share_check.unknown_locale_fallback,
            },
        )

    created_by = _hash_created_by(user_id)

    # ── 2. Per-user daily quota ───────────────────────────────
    from datetime import datetime as _dt
    one_day_ago = _dt.utcnow() - _timedelta(days=1)
    try:
        used_today = (
            db.query(_SharedQueryModel)
            .filter(
                _SharedQueryModel.created_by == created_by,
                _SharedQueryModel.created_at > one_day_ago,
            )
            .count()
        )
    except Exception as e:
        logger.error("[share] quota count failed: %s", e)
        return JSONResponse(status_code=500, content={"type": "share_error", "message": "Service unavailable."})

    if used_today >= _SHARE_DAILY_LIMIT:
        # retry_after_seconds = time until oldest record in the
        # last-24h window falls off. Simpler than tracking a sliding
        # window — gives the client a usable ETA.
        oldest = (
            db.query(_SharedQueryModel)
            .filter(
                _SharedQueryModel.created_by == created_by,
                _SharedQueryModel.created_at > one_day_ago,
            )
            .order_by(_SharedQueryModel.created_at.asc())
            .first()
        )
        if oldest:
            retry_after = max(1, int((oldest.created_at + _timedelta(days=1) - _dt.utcnow()).total_seconds()))
        else:
            retry_after = 3600
        return JSONResponse(
            status_code=429,
            content={
                "type": "share_daily_limit",
                "limit": _SHARE_DAILY_LIMIT,
                "retry_after_seconds": retry_after,
            },
        )

    # ── 3. Idempotency: same (query_id, created_by) → return existing
    existing = (
        db.query(_SharedQueryModel)
        .filter(
            _SharedQueryModel.query_id == body.query_id,
            _SharedQueryModel.created_by == created_by,
        )
        .first()
    )
    if existing is not None:
        return JSONResponse(
            status_code=200,
            content={
                "share_id": existing.share_id,
                "url": _share_url(existing.share_id),
                "og_image_url": _og_image_public_url(existing.share_id),
                "created": False,
            },
        )

    # ── 4. Generate unique share_id (max 3 retries) ───────────
    share_id: Optional[str] = None
    for _attempt in range(_SHARE_ID_RETRIES):
        candidate = _secrets.token_urlsafe(8)
        if not db.query(_SharedQueryModel).filter(_SharedQueryModel.share_id == candidate).first():
            share_id = candidate
            break
    if share_id is None:
        logger.error("[share] share_id collision after %d retries", _SHARE_ID_RETRIES)
        return JSONResponse(status_code=500, content={"type": "share_error", "message": "Service unavailable."})

    # ── 5. INSERT (use _safe_db_write per CLAUDE.md Rule 7) ──
    record = _SharedQueryModel(
        share_id=share_id,
        query_id=body.query_id,
        query_text=body.query_text,
        answer_text=body.answer_text,
        citations=body.citations or [],
        created_by=created_by,
        is_public=True,
        view_count=0,
        flagged=False,
        locale=body.locale,
    )
    if not _safe_db_write(db, record, label="ShareCreate"):
        return JSONResponse(status_code=500, content={"type": "share_error", "message": "Service unavailable."})

    # ── 6. OG image — synchronous but failure non-fatal ───────
    try:
        _generate_og_png(share_id, body.query_text)
    except Exception as e:
        logger.error("[share] OG image generation failed for %s: %s", share_id, e)

    return JSONResponse(
        status_code=201,
        content={
            "share_id": share_id,
            "url": _share_url(share_id),
            "og_image_url": _og_image_public_url(share_id),
            "created": True,
        },
    )


@app.post("/api/share/{share_id}/revoke")
async def share_revoke(
    share_id: str,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if not share_id or "/" in share_id or "\\" in share_id or len(share_id) > 64:
        return JSONResponse(status_code=404, content={"detail": "Not found."})

    user_id = get_user_id(creds)
    if not user_id:
        return JSONResponse(status_code=403, content={"type": "share_anon_blocked"})

    record = db.query(_SharedQueryModel).filter(_SharedQueryModel.share_id == share_id).first()
    if record is None:
        return JSONResponse(status_code=404, content={"detail": "Not found."})

    caller_hash = _hash_created_by(user_id)
    if record.created_by != caller_hash:
        return JSONResponse(status_code=403, content={"type": "share_not_owner"})

    record.is_public = False
    try:
        db.commit()
    except Exception as e:
        logger.error("[share] revoke commit failed: %s", e)
        db.rollback()
        return JSONResponse(status_code=500, content={"type": "share_error", "message": "Service unavailable."})

    return JSONResponse(
        status_code=200,
        content={"share_id": share_id, "is_public": False},
    )


@app.get("/api/share/list")
async def share_list(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(creds)
    if not user_id:
        return JSONResponse(status_code=403, content={"type": "share_anon_blocked"})

    caller_hash = _hash_created_by(user_id)
    rows = (
        db.query(_SharedQueryModel)
        .filter(_SharedQueryModel.created_by == caller_hash)
        .order_by(desc(_SharedQueryModel.created_at))
        .limit(100)
        .all()
    )
    shares = [
        {
            "share_id": r.share_id,
            "query_preview": (r.query_text or "")[:60],
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "is_public": bool(r.is_public),
            "view_count": int(r.view_count or 0),
        }
        for r in rows
    ]
    return JSONResponse(status_code=200, content={"shares": shares})


class TrackVisitRequest(BaseModel):
    share_id: str = Field(..., min_length=1, max_length=64)
    referrer_domain: Optional[str] = Field(default=None, max_length=253)
    is_first_view: bool = False


@app.post("/api/share/track-visit")
async def share_track_visit(body: TrackVisitRequest, request: Request):
    """Forwarded by the public Jinja2 template's inline script.

    PHASE B: backend has no PostHog client wired (utils/analytics.ts is
    frontend-only), so we just log the visit and return 204. PHASE C+
    will swap in a backend PostHog client. This endpoint exists now so
    the template's contract doesn't change later."""
    if "/" in body.share_id or "\\" in body.share_id:
        return Response(status_code=400)
    logger.info(
        "[share_visit] share_id=%s referrer_domain=%s is_first_view=%s",
        body.share_id,
        body.referrer_domain,
        body.is_first_view,
    )
    return Response(status_code=204)


class TrackCitationClickRequest(BaseModel):
    share_id: str = Field(..., min_length=1, max_length=64)
    source_type: Optional[str] = Field(default=None, max_length=32)
    citation_id: Optional[str] = Field(default=None, max_length=16)
    url: Optional[str] = Field(default=None, max_length=2048)


@app.post("/api/share/track-citation-click")
async def share_track_citation_click(body: TrackCitationClickRequest, request: Request):
    """PRD § 4.5 UX polish 1 — fired by the public page when a visitor
    clicks a citation "View source" link. No-op handler: server-side
    log only, returns 204. Swapping to a backend PostHog client later
    is a one-line change. No DB write (per existing P3 TECH_DEBT)."""
    if "/" in body.share_id or "\\" in body.share_id:
        return Response(status_code=400)
    logger.info(
        "[share_citation] share_id=%s source_type=%s citation_id=%s",
        body.share_id,
        body.source_type,
        body.citation_id,
    )
    return Response(status_code=204)


# 靜態檔案服務
static_path = Path("static")
if static_path.exists():
    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")

    # Catch-all: serve Next.js static export pages (e.g. /explain → static/explain.html)
    @app.get("/{path:path}")
    async def serve_nextjs_pages(path: str):
        resolved_root = static_path.resolve()

        def _safe(p: Path) -> bool:
            """Reject any path that escapes the static directory."""
            try:
                return str(p.resolve()).startswith(str(resolved_root))
            except (OSError, ValueError):
                return False

        # Try exact file (CSS/JS/images/etc.)
        file = static_path / path
        if _safe(file) and file.is_file():
            return FileResponse(file)
        # Try .html (Next.js static export: pages/explain.tsx → out/explain.html)
        html_file = static_path / f"{path}.html"
        if _safe(html_file) and html_file.is_file():
            return FileResponse(html_file)
        # Try directory index
        index_file = static_path / path / "index.html"
        if _safe(index_file) and index_file.is_file():
            return FileResponse(index_file)
        # Fallback to index.html for client-side routing
        return FileResponse(static_path / "index.html")

    app.mount("/", StaticFiles(directory="static", html=True), name="static")