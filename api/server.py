"""
Vela API Server
FastAPI 後端，整合 Research、Verify、Explain、合規防護與數據飛輪回饋
"""

from dotenv import load_dotenv
import os
load_dotenv()

import json
import time
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
from api.database.sql_db import get_db, engine, Base
from api.models.sql_models import AuditLog, UserFeedback, ChatHistory
from api.services.usage_service import check_credits, deduct_credits

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

RATE_LIMITS = {
    "/api/research":     (30, 60),
    "/api/verify":       (30, 60),
    "/api/consultation": (20, 60),
    "/api/explain":      (20, 60),
    "/api/feedback":     (10, 60),
}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path not in RATE_LIMITS:
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    limit, window = RATE_LIMITS[path]
    now = _time.time()

    _rate_store[f"{ip}:{path}"] = [
        t for t in _rate_store[f"{ip}:{path}"] if now - t < window
    ]

    if len(_rate_store[f"{ip}:{path}"]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded. Max {limit} requests per {window}s."}
        )

    _rate_store[f"{ip}:{path}"].append(now)
    return await call_next(request)


# ============================================================
# CORS
# ============================================================
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

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
print(f"🔑 TEST_MODE = {TEST_MODE}")

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            r = await client.get(os.getenv("CLERK_JWKS_URL"))
            _jwks_cache = r.json()
    return _jwks_cache

if not TEST_MODE:
    clerk_guard = None  # 不再用 fastapi-clerk-auth
else:
    clerk_guard = None
    print("⚠️  TEST_MODE: Clerk authentication disabled")


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
        print(f"❌ JWT decode error: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")


def get_user_id(creds: Optional[HTTPAuthorizationCredentials]) -> str:
    if creds is None:
        return "test_user"
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


# ============================================================
# Middleware: PHI 防護
# ============================================================
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    path = request.url.path

    if path in ["/api/research", "/api/consultation", "/api/explain"]:
        return await call_next(request)

    if path in ["/api/verify", "/api/feedback"] and request.method == "POST":
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
            print(f"Middleware Error: {e}")

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
    allowed, reason = await check_credits(db, user_id, "research")
    if not allowed:
        if reason == "limit_reached":
            return JSONResponse(status_code=403, content={"error": "limit_reached", "upgrade_url": "/pricing"})
        elif reason == "daily_cap_reached":
            return JSONResponse(status_code=429, content={"error": "daily_cap_reached", "message": "You've reached today's usage limit. Resets at midnight UTC."})

    async def event_stream():
        full_answer = ""
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
                    try:
                        db.add(AuditLog(
                            id=f"res_{int(time.time()*1000)}",
                            user_id=user_id,
                            action="research",
                            query_content=PHIDetector.sanitize_for_log(body.question),
                            resource_ids=[c.get('source_id') for c in citations_data],
                            ip_address="0.0.0.0"
                        ))
                        db.commit()
                    except Exception as e:
                        print(f"Audit Log Error: {e}")
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
                        print(f"History Save Error: {e}")
                    # 成功後扣減 credits
                    await deduct_credits(db, user_id, "research")
                    # Cost logging
                    if usage_out:
                        from api.services.cost_tracker import log_api_cost
                        u = usage_out[0]
                        await log_api_cost(db, user_id, "research", u["model"], u["prompt_tokens"], u["completion_tokens"])
                    yield f"data: {json.dumps({'type': 'done', 'query_time_ms': elapsed_ms}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
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
        print(f"⚠️ No FDA labels found for {body.drugs}, falling back to LLM")
        try:
            db.add(AuditLog(id=f"ver_{int(time.time()*1000)}", user_id=user_id,
                action="verify_fallback", query_content=f"LLM fallback: {body.drugs}", ip_address="0.0.0.0"))
            db.commit()
        except: pass

        fallback_system = """You are a clinical pharmacologist. Analyze drug interactions based on pharmacological knowledge.
Return valid JSON only:
{"interactions":[{"drugs":["Drug1","Drug2"],"severity":"Major","description":"...","recommendation":"..."}],"summary":"...","risk_level":"Major"}"""

        try:
            client_fb = OpenAI()
            fb_user_content = f"Analyze interaction between: {', '.join(body.drugs)}\nContext: {body.patient_context or 'None'}"
            if lang_instruction:
                fb_user_content += f"\n\n{lang_instruction}"
            fb = client_fb.chat.completions.create(
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
                    source_url=""
                )
                for item in fb_data.get("interactions",[]) if len(item.get("drugs",[])) >= 2
            ]
            return VerifyResponse(
                drugs_analyzed=body.drugs,
                interactions=fb_interactions,
                summary="⚠️ No FDA label data found. " + fb_data.get("summary",""),
                risk_level=fb_data.get("risk_level","Unknown"),
                query_time_ms=int((time.time()-start_time)*1000)
            )
        except Exception as e:
            print(f"❌ Verify fallback failed: {e}")
            return VerifyResponse(
                drugs_analyzed=body.drugs, interactions=[],
                summary="No FDA label data found. Please use specific drug names.",
                risk_level="Unknown", query_time_ms=int((time.time()-start_time)*1000)
            )

    fda_context = "\n".join([label.to_text() for label in drug_labels])

    # ── 移除 "LANGUAGE RULE: Always respond in English"，改由語言偵測控制 ──
    system_prompt = """You are a clinical pharmacist. Analyze FDA drug labels for interactions.
Classify severity as: Critical, Major, Moderate, Minor.
For each interaction include: mechanism, dose context, warning signs, monitoring parameters, safer alternative.

Supported languages: English, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, ภาษาไทย.
IMPORTANT: Respond in the SAME language as the patient_context or question. An explicit language instruction will be appended — follow it exactly.

Return valid JSON only:
{"interactions":[{"drugs":["Drug1","Drug2"],"severity":"Major","description":"...","recommendation":"..."}],"summary":"...","risk_level":"Major"}"""

    client = OpenAI()
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
            completion = client.chat.completions.create(
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
            print(f"❌ LLM attempt {attempt+1} failed: {e}")

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
        db.add(AuditLog(id=f"ver_{int(time.time()*1000)}", user_id=user_id,
            action="verify", query_content=f"Checked: {body.drugs}", ip_address="0.0.0.0"))
        db.add(ChatHistory(user_id=user_id, session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}", answer=summary))
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}"); db.rollback()

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
        print(f"Cost log error: {e}")

    return VerifyResponse(
        drugs_analyzed=body.drugs, interactions=interactions,
        summary=summary, risk_level=risk_level, query_time_ms=elapsed_ms
    )


# ============================================================
# 功能 4：Explain — 醫療報告解讀 (新功能)
# ============================================================
@app.post("/api/explain")
async def explain_report(
    request: ExplainRequest,
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
                report_text=request.report_text,
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
                            question=request.report_text[:500],
                            answer=full_answer
                        ))
                        db.commit()
                    except Exception as e:
                        print(f"History Save Error: {e}")
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
                        print(f"Cost log error: {e}")
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
            id=f"fb_{int(time.time()*1000)}",
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
        print(f"Feedback Error: {e}")
        return {"status": "error", "message": str(e)}


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
# 管理員：Cost Dashboard
# ============================================================
@app.get("/api/admin/costs")
async def admin_costs(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)

    # 僅限管理員
    ADMIN_USER_ID = "user_3B939OrkarbJWpfTT8nCi9kDJ1B"
    if user_id != ADMIN_USER_ID:
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
        vector_store_status = {"error": str(e)}

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
    app.mount("/", StaticFiles(directory="static", html=True), name="static")