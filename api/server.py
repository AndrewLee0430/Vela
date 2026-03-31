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
from typing import Optional

from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI, AsyncOpenAI
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
from api.data_sources.fda_cached import fda_client_cached
from api.middleware.phi_handler import PHIDetector
from api.middleware.guards import run_guards
from api.database.sql_db import get_db, engine, Base, SessionLocal
from api.models.sql_models import AuditLog, UserFeedback, ChatHistory
from api.services.usage_service import check_credits, deduct_credits
from api.utils.llm_judge import LLMJudge, Source as JudgeSource

from api.models.explain_schemas import ExplainRequest
from api.services.explain_service import run_explain_pipeline
from api.utils.language_detector import detect_language, get_language_instruction  # ← v2.5

# ============================================================
# 生命週期管理
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


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
    "/api/consultation":          (20, 60),
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
}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    global _rate_store_last_cleanup
    # TEST_MODE only skips auth, never rate limiting
    path = request.url.path
    if path not in RATE_LIMITS:
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
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
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
# Auth
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
logger.info("TEST_MODE = %s", TEST_MODE)

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


async def optional_auth(request: Request) -> Optional[HTTPAuthorizationCredentials]:
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
generator = AnswerGenerator(model="gpt-4.1")
fda_client = FDAClient()
openai_async_client = AsyncOpenAI()
_judge = LLMJudge(client=openai_async_client)


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
# Middleware: PHI 防護
# ============================================================
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    path = request.url.path

    if path in ["/api/research", "/api/consultation", "/api/explain", "/api/verify"]:
        return await call_next(request)

    if path in ["/api/feedback"] and request.method == "POST":
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8")

            phi_type = PHIDetector.detect(body_str)
            if phi_type:
                return StreamingResponse(
                    iter([json.dumps({
                        "type": "error",
                        "content": f"⚠️ 安全攔截：偵測到潛在的個人資訊 ({phi_type})。為符合隱私規範，請移除後再試。"
                    })]),
                    media_type="application/json",
                    status_code=400
                )

            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

        except Exception as e:
            logger.error("Middleware Error: %s", e)

    response = await call_next(request)
    return response


# ============================================================
# 功能 2：Research / RAG
# ============================================================
@app.post("/api/research")
async def research_query(
    body: ResearchRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    start_time = time.time()

    # Credit 檢查（在 streaming 開始前）
    if not TEST_MODE:
        allowed, reason = await check_credits(db, user_id, "research")
        if not allowed:
            if reason == "limit_reached":
                return JSONResponse(status_code=403, content={"error": "limit_reached", "upgrade_url": "/pricing"})
            elif reason == "daily_cap_reached":
                return JSONResponse(status_code=429, content={"error": "daily_cap_reached", "message": "You've reached today's usage limit. Resets at midnight UTC."})

    async def event_stream():
        full_answer = ""
        audit_id = None
        try:
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
            usage_out = []
            async for event in generator.generate_stream(
                question=body.question,
                documents=documents,
                retrieval_status=retrieval_status,
                query_type="research",
                lang=lang,
                usage_out=usage_out
            ):
                if event.type == StreamEventType.ANSWER:
                    content = event.content or ""
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'answer', 'content': content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.FALLBACK:
                    yield f"data: {json.dumps({'type': 'fallback', 'content': event.content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.CITATIONS:
                    citations_data = [c.model_dump() for c in event.content]
                    audit_id = f"res_{uuid.uuid4().hex[:16]}"
                    try:
                        db.add(AuditLog(
                            id=audit_id,
                            user_id=user_id,
                            action="research",
                            query_content=PHIDetector.sanitize_for_log(body.question),
                            resource_ids=[c.get('source_id') for c in citations_data],
                            ip_address="0.0.0.0"
                        ))
                        db.commit()
                    except Exception as e:
                        logger.error("Audit Log Error: %s", e)
                    yield f"data: {json.dumps({'type': 'citations', 'content': citations_data}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.ERROR:
                    yield f"data: {json.dumps({'type': 'error', 'content': event.content}, ensure_ascii=False)}\n\n"
                elif event.type == StreamEventType.DONE:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    try:
                        db.add(ChatHistory(
                            user_id=user_id,
                            session_type="research",
                            question=PHIDetector.sanitize_for_log(body.question),
                            answer=full_answer
                        ))
                        db.commit()
                    except Exception as e:
                        logger.error("History Save Error: %s", e)
                    # 成功後扣減 credits
                    await deduct_credits(db, user_id, "research")
                    # Cost logging
                    if usage_out:
                        from api.services.cost_tracker import log_api_cost
                        u = usage_out[0]
                        await log_api_cost(db, user_id, "research", u["model"], u["prompt_tokens"], u["completion_tokens"])
                    # Fire LLM Judge in background — does not block SSE stream
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
async def get_suggestions(creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth)):
    return SuggestionsResponse.default_suggestions()


# ============================================================
# 功能 3：Verify
# ============================================================
@app.post("/api/verify")
async def verify_drug_interaction(
    body: VerifyRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    user_id = get_user_id(creds)

    # Credit 檢查
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

    # ── 語言偵測：優先用 patient_context（含用戶語言），否則從藥名猜 ──
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

    for drug in body.drugs:
        labels = await fda_client.search_drug_labels(drug, limit=1)
        if labels:
            drug_labels.append(labels[0])
            official_name = (labels[0].generic_name or labels[0].brand_name or '').strip()
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
                corrected_labels = await fda_client.search_drug_labels(best_match, limit=1)
                if corrected_labels:
                    drug_labels.append(corrected_labels[0])

    if not drug_labels:
        logger.warning("No FDA labels found for %s, falling back to LLM", body.drugs)
        try:
            db.add(AuditLog(id=f"ver_{uuid.uuid4().hex[:16]}", user_id=user_id,
                action="verify_fallback", query_content=f"LLM fallback: {body.drugs}", ip_address="0.0.0.0"))
            db.commit()
        except Exception:
            pass

        fallback_system = """You are a clinical pharmacologist. Analyze drug interactions based on pharmacological knowledge.
Return valid JSON only:
{"interactions":[{"drugs":["Drug1","Drug2"],"severity":"Major","description":"...","recommendation":"..."}],"summary":"...","risk_level":"Major"}"""

        try:
            fb_user_content = f"Analyze interaction between: {', '.join(body.drugs)}\nContext: {body.patient_context or 'None'}"
            if lang_instruction:
                fb_user_content += f"\n\n{lang_instruction}"
            fb = await openai_async_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": fallback_system},
                    {"role": "user", "content": fb_user_content}
                ],
                response_format={"type": "json_object"}
            )
            fb_data = json.loads(fb.choices[0].message.content)
            fb_interactions = [
                DrugInteraction(
                    drug_pair=tuple(item["drugs"][:2]),
                    severity=item.get("severity","Unknown"),
                    description=item.get("description",""),
                    clinical_recommendation=item.get("recommendation",""),
                    source="Clinical Knowledge (No FDA label available)",
                    source_url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process&query={body.drugs[0].replace(' ', '+')}"
                )
                for item in fb_data.get("interactions",[]) if len(item.get("drugs",[])) >= 2
            ]
            fb_summary = "⚠️ No FDA label data found. " + fb_data.get("summary","")
            try:
                db.add(ChatHistory(user_id=user_id, session_type="verify",
                    question=f"Drugs: {', '.join(body.drugs)}", answer=fb_summary))
                db.commit()
            except Exception as e:
                logger.error("DB Error: %s", e); db.rollback()
            return VerifyResponse(
                drugs_analyzed=body.drugs,
                interactions=fb_interactions,
                summary=fb_summary,
                risk_level=fb_data.get("risk_level","Unknown"),
                query_time_ms=int((time.time()-start_time)*1000)
            )
        except Exception as e:
            logger.error("Verify fallback failed: %s", e)
            fallback_summary = "No FDA label data found. Please use specific drug names."
            try:
                db.add(ChatHistory(user_id=user_id, session_type="verify",
                    question=f"Drugs: {', '.join(body.drugs)}", answer=fallback_summary))
                db.commit()
            except Exception as e2:
                logger.error("DB Error: %s", e2); db.rollback()
            return VerifyResponse(
                drugs_analyzed=body.drugs, interactions=[],
                summary=fallback_summary,
                risk_level="Unknown", query_time_ms=int((time.time()-start_time)*1000)
            )

    fda_context = "\n".join([label.to_text() for label in drug_labels])

    # ── 移除 "LANGUAGE RULE: Always respond in English"，改由語言偵測控制 ──
    system_prompt = """You are a clinical pharmacist. Analyze FDA drug labels for interactions.
Classify severity as: Critical, Major, Moderate, Minor.
For each interaction include: mechanism, dose context, warning signs, monitoring parameters, safer alternative.

Supported languages: English, 繁體中文 (zh-TW), 简体中文 (zh-CN), 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the patient_context or question. An explicit language instruction will be appended — follow it exactly.

Return valid JSON only:
{"interactions":[{"drugs":["Drug1","Drug2"],"severity":"Major","description":"...","recommendation":"..."}],"summary":"...","risk_level":"Major"}"""

    interactions = []
    summary = ""
    risk_level = "Unknown"
    analysis_success = False

    # ── user content 加入語言指令 ──────────────────────────────────
    main_user_content = f"Patient Context: {body.patient_context or 'None'}\nDrugs: {', '.join(body.drugs)}\n\nFDA Data:\n{fda_context}"
    if lang_instruction:
        main_user_content += f"\n\n{lang_instruction}"

    for attempt in range(2):
        try:
            completion = await openai_async_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": main_user_content}
                ],
                response_format={"type": "json_object"}
            )
            analysis = json.loads(completion.choices[0].message.content)
            temp = []
            for item in analysis.get("interactions", []):
                drugs = item.get("drugs", [])
                if len(drugs) < 2 or not all(isinstance(d, str) and d.strip() for d in drugs):
                    continue
                temp.append(DrugInteraction(
                    drug_pair=tuple(drugs[:2]),
                    severity=item.get("severity","Unknown"),
                    description=item.get("description","No description provided"),
                    clinical_recommendation=item.get("recommendation",""),
                    source="FDA Label Analysis",
                    source_url=f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drugs[0].replace(' ','+')}"
                ))
            interactions = temp
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

    try:
        db.add(AuditLog(id=f"ver_{uuid.uuid4().hex[:16]}", user_id=user_id,
            action="verify", query_content=f"Checked: {body.drugs}", ip_address="0.0.0.0"))
        db.add(ChatHistory(user_id=user_id, session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}", answer=summary))
        db.commit()
    except Exception as e:
        logger.error("DB Error: %s", e); db.rollback()

    if spelling_corrections:
        summary = "Note: " + "; ".join(spelling_corrections) + ". Please verify. " + summary

    # 成功後扣減 credits
    await deduct_credits(db, user_id, "verify")

    # Cost logging（Verify 用 gpt-4.1-mini，從 completion 取得 usage）
    try:
        from api.services.cost_tracker import log_api_cost
        if analysis_success and 'completion' in locals():
            await log_api_cost(
                db, user_id, "verify", "gpt-4.1-mini",
                completion.usage.prompt_tokens,
                completion.usage.completion_tokens
            )
    except Exception as e:
        logger.error("Cost log error: %s", e)

    return VerifyResponse(
        drugs_analyzed=body.drugs, interactions=interactions,
        summary=summary, risk_level=risk_level, query_time_ms=elapsed_ms
    )


# ============================================================
# 功能 4：Explain — 醫療報告解讀 (新功能)
# ============================================================
@app.post("/api/explain")
async def explain_report(
    body: ExplainRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db),
):
    """
    3-stage pipeline:
    Stage 1: Entity extraction (GPT-4.1-mini)
    Stage 2: Parallel API lookups (LOINC, RxNorm, MedlinePlus)
    Stage 3: Plain-language explanation (GPT-4.1, streaming)
    """

    user_id = get_user_id(creds)

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
        try:
            async for event in run_explain_pipeline(
                report_text=body.report_text,
                openai_client=openai_async_client,
            ):
                # Accumulate answer for history
                if isinstance(event, dict) and event.get("type") == "answer":
                    full_answer += event.get("content", "")
                # Save to history when done
                if isinstance(event, dict) and event.get("type") == "done":
                    try:
                        db.add(ChatHistory(
                            user_id=user_id,
                            session_type="explain",
                            question=body.report_text[:500],
                            answer=full_answer
                        ))
                        db.commit()
                    except Exception as e:
                        logger.error("History Save Error: %s", e)
                    # 成功後扣減 credits
                    await deduct_credits(db, user_id, "explain")
                    # Cost logging
                    try:
                        from api.services.cost_tracker import log_api_cost
                        usage = event.get("usage")
                        if usage:
                            await log_api_cost(
                                db, user_id, "explain",
                                usage.get("model", "gpt-4.1"),
                                usage.get("prompt_tokens", 0),
                                usage.get("completion_tokens", 0)
                            )
                    except Exception as e:
                        logger.error("Cost log error: %s", e)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("Explain stream error: %s", type(e).__name__)
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred. Please try again.'})}\n\n"

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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
):
    get_user_id(creds)  # Auth check

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
        response = await openai_async_client.chat.completions.create(
            model="gpt-4o",
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
        extracted = response.choices[0].message.content or ""
        return {"text": extracted.strip()}
    except Exception as e:
        logger.error("Image extraction error: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"detail": "Could not extract text from image."})


# ============================================================
# 功能 5：Feedback
# ============================================================
class FeedbackCreate(BaseModel):
    query: str
    response: str
    rating: int
    feedback_text: Optional[str] = None
    category: str

@app.post("/api/feedback")
async def create_feedback(
    feedback: FeedbackCreate,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
# 功能 6：History
# ============================================================
@app.get("/api/history")
async def get_user_history(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    return db.query(ChatHistory)\
        .filter(ChatHistory.user_id == user_id)\
        .order_by(desc(ChatHistory.created_at))\
        .limit(50).all()


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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
        ip_address=request.client.host if request.client else "unknown",
    ))

    db.add(WebhookEvent(event_id=f"dodo_{event_id}", event_type=event_type))
    db.commit()
    return {"status": "ok", "event": event_type}


@app.get("/api/user/status")
async def user_status(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
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
async def api_status(creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth)):
    try:
        from api.database.vector_store import get_vector_store
        vector_store_status = get_vector_store().get_stats()
    except Exception as e:
        vector_store_status = {"error": "unavailable"}

    return {
        "status": "healthy",
        "version": "2.2.0",
        "features": {
            "consultation": True, "research": True, "pubmed": True,
            "fda": True, "verify": True, "explain": True,
            "feedback": True, "history": True
        },
        "vector_store": vector_store_status
    }


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