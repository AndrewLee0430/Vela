"""
MediNotes API Server
FastAPI 後端，整合諮詢筆記、RAG 檢索、FDA 驗證、合規防護與數據飛輪回饋
"""

from api.data_sources.fda import FDAClient
from api.data_sources.fda_cached import fda_client_cached

from dotenv import load_dotenv
import os

load_dotenv()  # 載入 .env 檔案

import json
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import desc

# --- 內部模組引用 ---
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
from api.database.sql_db import get_db, engine, Base
from api.models.sql_models import AuditLog, UserFeedback, ChatHistory


# ============================================================
# 生命週期管理 (啟動時建立資料庫 Tables)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MediNotes API",
    description="AI-powered medical assistant for healthcare professionals",
    version="2.1.0",
    lifespan=lifespan
)

# ============================================================
# Rate Limiter（Middleware 實作，避免與 FastAPI Depends 衝突）
# 每個 IP 的請求計數存在記憶體，重啟後清空
# ============================================================
import time as _time
from collections import defaultdict

_rate_store: dict = defaultdict(list)  # {ip: [timestamp, ...]}

RATE_LIMITS = {
    "/api/research":     (30, 60),   # 30次/60秒
    "/api/verify":       (30, 60),
    "/api/consultation": (20, 60),
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

    # 清除過期記錄
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
# 本機開發：allow_origins=["*"]
# 正式環境：從 ALLOWED_ORIGINS 環境變數讀取，限制為實際網域
# .env 範例：ALLOWED_ORIGINS=https://vela.yourdomain.com,https://www.vela.yourdomain.com
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
# TEST_MODE：跳過 JWT 驗證，用於自動化測試
# 使用方式：在 .env 加上 TEST_MODE=true
# 測試完畢後務必移除！
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
print(f"🔑 TEST_MODE = {TEST_MODE}")

# ── 關鍵修正 ──────────────────────────────────────────────
# ClerkHTTPBearer 實例化時會自動註冊全域 middleware。
# TEST_MODE=true 時完全不實例化，避免在 endpoint 執行前就被攔截。
# ─────────────────────────────────────────────────────────
if not TEST_MODE:
    clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
    clerk_guard = ClerkHTTPBearer(clerk_config)
else:
    clerk_guard = None
    print("⚠️  TEST_MODE: Clerk authentication disabled")


async def optional_auth(
    request: Request
) -> Optional[HTTPAuthorizationCredentials]:
    """
    TEST_MODE=true  → 直接回傳 None，完全跳過驗證
    TEST_MODE=false → 正常走 Clerk JWT 驗證
    永遠不使用 Depends(clerk_guard)，避免 ClerkHTTPBearer 全域攔截
    """
    if TEST_MODE or clerk_guard is None:
        return None
    return await clerk_guard(request)


def get_user_id(creds: Optional[HTTPAuthorizationCredentials]) -> str:
    if creds is None:
        return "test_user"
    return creds.decoded["sub"]


# 初始化元件
retriever = HybridRetriever(
    local_threshold=0.6,
    enable_local=True,
    enable_pubmed=True,
    enable_fda=True
)
generator = AnswerGenerator(model="gpt-4.1")
fda_client = FDAClient()


# ============================================================
# Middleware: Audit Log & PHI 防護
# ============================================================
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    path = request.url.path

    if path in ["/api/research", "/api/consultation"]:
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
# 功能 1：諮詢筆記生成 (Consultation)
# ============================================================

class Visit(BaseModel):
    patient_name: str
    date_of_visit: str
    notes: str

consultation_system_prompt = """
You are a medical communication specialist helping doctors write patient education letters.

Your ONLY job is to translate the doctor's existing notes into clear, warm, patient-friendly language.

LANGUAGE RULE: Always respond in the same language as the doctor's input notes. If the notes are in Chinese, respond in Chinese. If in English, respond in English. Match the input language exactly.

STRICT RULES:
1. TRANSLATE ONLY — do not add any clinical information, drug dosages, specific lab thresholds,
   or medical advice that is NOT explicitly stated in the doctor's notes.
2. If the doctor wrote "consider adjusting Metformin", translate exactly that intent —
   do NOT add specific clinical guidance like thresholds or dosage numbers.
3. Replace medical jargon with plain language. Examples:
   - "eGFR 41" becomes "your kidney filtering function has recently decreased"
   - "HbA1c 7.8%" becomes "your average blood sugar over the past 3 months was 7.8%"
   - "HTN" becomes "high blood pressure"
   - "T2DM" becomes "Type 2 diabetes"
4. Use a warm, reassuring tone — not alarming, not overly clinical.
5. Keep it concise — maximum one page, use short paragraphs.
6. If the doctor noted a follow-up plan, include it clearly so the patient knows what to expect next.

Reply with exactly two sections:

### Visit Summary
[Translate the visit findings into plain language. Only what the doctor documented.]

### What Happens Next
[Translate the doctor's plan into patient-friendly language. Only what the doctor documented.
Do NOT add generic advice like "eat healthy" or "exercise" unless the doctor wrote it.]
"""

def user_prompt_for(visit: Visit) -> str:
    return f"""Please translate these doctor's notes into a patient education letter.
Date of Visit: {visit.date_of_visit}

Doctor's Notes:
{visit.notes}

Remember: ONLY translate what is in the notes. Do not add clinical information not present above."""

@app.post("/api/consultation")
def consultation_summary(
    visit: Visit,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    client = OpenAI()

    try:
        audit = AuditLog(
            id=f"doc_{int(time.time()*1000)}",
            user_id=user_id,
            action="consultation_gen",
            query_content="Generated consultation note summary",
            ip_address="0.0.0.0"
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        print(f"Audit Log Error: {e}")

    user_prompt = user_prompt_for(visit)
    prompt = [
        {"role": "system", "content": consultation_system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    stream = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=prompt,
        stream=True,
    )

    def event_stream():
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield f"data: {json.dumps({'text': text})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============================================================
# 功能 2：醫學研究查詢 (Research / RAG)
# ============================================================

@app.post("/api/research")
async def research_query(
    body: ResearchRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)
    start_time = time.time()

    async def event_stream():
        full_answer = ""

        try:
            # ── Guard: Prompt injection + 非醫療意圖 ──────────────
            passed, guard_error = await run_guards(body.question)
            if not passed:
                yield f"data: {json.dumps({'type': 'error', 'content': guard_error}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # ── Status 1: 開始檢索 ────────────────────────────────
            yield f"data: {json.dumps({'type': 'status', 'content': 'Searching medical literature...'}, ensure_ascii=False)}\n\n"

            documents, retrieval_status = await retriever.retrieve(
                query=body.question,
                max_results=body.max_results or 5,
                source_filter=body.sources
            )

            # ── Status 2: 開始生成 ────────────────────────────────
            yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing documents...'}, ensure_ascii=False)}\n\n"

            async for event in generator.generate_stream(
                question=body.question,
                documents=documents,
                retrieval_status=retrieval_status,
                query_type="research"
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
                        audit = AuditLog(
                            id=f"res_{int(time.time()*1000)}",
                            user_id=user_id,
                            action="research",
                            query_content=PHIDetector.sanitize_for_log(body.question),
                            resource_ids=[c.get('source_id') for c in citations_data],
                            ip_address="0.0.0.0"
                        )
                        db.add(audit)
                        db.commit()
                    except Exception as e:
                        print(f"Audit Log Error: {e}")

                    yield f"data: {json.dumps({'type': 'citations', 'content': citations_data}, ensure_ascii=False)}\n\n"

                elif event.type == StreamEventType.ERROR:
                    yield f"data: {json.dumps({'type': 'error', 'content': event.content}, ensure_ascii=False)}\n\n"

                elif event.type == StreamEventType.DONE:
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    try:
                        history = ChatHistory(
                            user_id=user_id,
                            session_type="research",
                            question=PHIDetector.sanitize_for_log(body.question),
                            answer=full_answer
                        )
                        db.add(history)
                        db.commit()
                    except Exception as e:
                        print(f"History Save Error: {e}")

                    yield f"data: {json.dumps({'type': 'done', 'query_time_ms': elapsed_ms}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/research/suggestions")
async def get_suggestions(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth)
):
    return SuggestionsResponse.default_suggestions()


# ============================================================
# 功能 3：藥物交互作用驗證 (Verify)
# ============================================================

@app.post("/api/verify", response_model=VerifyResponse)
async def verify_drug_interaction(
    body: VerifyRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    user_id = get_user_id(creds)

    drug_labels = []
    spelling_corrections: list[str] = []

    def levenshtein(a, b):
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                dp[j] = prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
                prev = temp
        return dp[n]

    KNOWN_DRUGS = [
        "warfarin", "aspirin", "metformin", "lisinopril", "atorvastatin",
        "amlodipine", "simvastatin", "ibuprofen", "acetaminophen", "paracetamol",
        "fluoxetine", "tramadol", "spironolactone", "clarithromycin", "iohexol",
        "insulin", "metoprolol", "omeprazole", "amoxicillin", "ciprofloxacin",
        "prednisone", "levothyroxine", "gabapentin", "sertraline", "losartan",
    ]

    for drug in body.drugs:
        labels = await fda_client.search_drug_labels(drug, limit=1)
        if labels:
            drug_labels.append(labels[0])
            official_name = (labels[0].generic_name or labels[0].brand_name or '').strip()
            if official_name:
                drug_lower = drug.lower().strip()
                official_lower = official_name.lower().strip()
                if drug_lower not in official_lower and official_lower not in drug_lower:
                    dist = levenshtein(drug_lower, official_lower)
                    length_diff = abs(len(drug_lower) - len(official_lower))
                    if 1 <= dist <= 3 and length_diff <= 2:
                        spelling_corrections.append(
                            f"'{drug}' was interpreted as '{official_name.title()}'"
                        )
        else:
            drug_lower = drug.lower().strip()
            best_match = None
            best_dist = 999
            for known in KNOWN_DRUGS:
                dist = levenshtein(drug_lower, known)
                length_diff = abs(len(drug_lower) - len(known))
                if dist < best_dist and dist <= 3 and length_diff <= 2:
                    best_dist = dist
                    best_match = known
            if best_match:
                spelling_corrections.append(
                    f"'{drug}' was interpreted as '{best_match.title()}'"
                )
                corrected_labels = await fda_client.search_drug_labels(best_match, limit=1)
                if corrected_labels:
                    drug_labels.append(corrected_labels[0])

    # ── Verify Fallback ───────────────────────────────────────
    # FDA 找不到資料（藥物類別名稱如 SSRIs/NSAIDs，或罕見藥物）
    # 改用 LLM 根據藥理知識分析，不直接回傳空結果
    # ─────────────────────────────────────────────────────────
    if not drug_labels:
        print(f"⚠️ No FDA labels found for {body.drugs}, falling back to LLM knowledge")
        try:
            db.add(AuditLog(
                id=f"ver_{int(time.time()*1000)}",
                user_id=user_id,
                action="verify_fallback",
                query_content=f"No FDA data, LLM fallback for: {body.drugs}",
                ip_address="0.0.0.0"
            ))
            db.commit()
        except:
            pass

        fallback_system = """You are a clinical pharmacologist. Analyze the drug interaction between the listed drugs based on your pharmacological knowledge and standard clinical references.

You MUST cover ALL of the following:
1. Interaction severity: Major / Moderate / Minor with rationale
2. Mechanism: pharmacokinetic or pharmacodynamic explanation
3. Clinical consequences: what will happen to the patient
4. Specific warning signs: observable symptoms to watch for
5. Monitoring parameters: exact labs or clinical checks
6. Clinical recommendation: action to take (avoid / reduce dose / monitor / timing)

CRITICAL: Return valid JSON only with this exact structure:
{
    "interactions": [
        {
            "drugs": ["Drug1", "Drug2"],
            "severity": "Major",
            "description": "Detailed description including mechanism",
            "recommendation": "Clinical recommendation including monitoring and alternatives"
        }
    ],
    "summary": "Brief summary",
    "risk_level": "Major"
}"""

        fallback_user = f"""Analyze the drug interaction between: {', '.join(body.drugs)}
Patient context: {body.patient_context or 'None'}

Note: These may be drug class names (e.g. SSRIs, NSAIDs, beta-blockers).
If so, analyze the class interaction and note that specific drug choice within the class may affect severity."""

        try:
            client_fb = OpenAI()
            fb_completion = client_fb.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": fallback_system},
                    {"role": "user", "content": fallback_user}
                ],
                response_format={"type": "json_object"}
            )
            fb_analysis = json.loads(fb_completion.choices[0].message.content)
            fb_interactions = []
            for item in fb_analysis.get("interactions", []):
                drugs = item.get("drugs", [])
                if len(drugs) >= 2:
                    fb_interactions.append(DrugInteraction(
                        drug_pair=tuple(drugs[:2]),
                        severity=item.get("severity", "Unknown"),
                        description=item.get("description", ""),
                        clinical_recommendation=item.get("recommendation", ""),
                        source="Clinical Knowledge (No FDA label available)",
                        source_url=""
                    ))
            fb_summary = "⚠️ No FDA label data found for these drugs. " + fb_analysis.get("summary", "")
            fb_risk = fb_analysis.get("risk_level", "Unknown")
            return VerifyResponse(
                drugs_analyzed=body.drugs,
                interactions=fb_interactions,
                summary=fb_summary,
                risk_level=fb_risk,
                query_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            print(f"❌ Verify fallback failed: {e}")
            return VerifyResponse(
                drugs_analyzed=body.drugs,
                interactions=[],
                summary="No FDA label data found. Unable to analyze interaction. Please use specific drug names.",
                risk_level="Unknown",
                query_time_ms=int((time.time() - start_time) * 1000)
            )

    fda_context = "\n".join([label.to_text() for label in drug_labels])

    system_prompt = """You are a clinical pharmacist. Analyze the provided FDA drug labels for interactions.
    Identify interactions between the listed drugs.
    Classify severity as: Critical, Major, Moderate, Minor.

    LANGUAGE RULE: Always respond in English regardless of input language.

    For each interaction you MUST include ALL of the following:
    1. Mechanism: Why this interaction occurs (pharmacokinetic or pharmacodynamic).
    2. Dose context: Distinguish effects by dose where clinically relevant.
       Example: low-dose aspirin (75-100mg) vs analgesic-dose (>=325mg) have very different risk profiles with anticoagulants.
    3. Clinical warning signs: List specific observable symptoms the clinician should watch for.
       Example for bleeding: gum bleeding, black/tarry stools, unexplained bruising, prolonged bleeding from cuts, blood in urine.
    4. Monitoring parameters: Specific labs or clinical checks (e.g. renal function, serum potassium, CK levels).
       IMPORTANT: NEVER state a fixed target range (e.g. "INR 2-3") without noting it varies by indication.
       Instead write: "INR target varies by indication (typically 2-3 for AF/DVT, 2.5-3.5 for mechanical valves)."
    5. Safer alternative: If the recommendation is to avoid or minimize one drug, ALWAYS suggest a clinically appropriate alternative.
       Example: If avoiding NSAIDs with anticoagulants, suggest Acetaminophen/Paracetamol as the preferred analgesic.

    CRITICAL: You MUST return valid JSON with this EXACT structure:
    {
        "interactions": [
            {
                "drugs": ["Drug1", "Drug2"],
                "severity": "Major",
                "description": "Detailed description including mechanism and dose-dependent effects",
                "recommendation": "Clinical recommendation including warning signs, monitoring parameters, and safer alternative if applicable"
            }
        ],
        "summary": "Brief summary of findings",
        "risk_level": "Major"
    }

    DRUG NAME CORRECTION (check this FIRST before analysis):
    - Before analyzing, check each input drug name for misspellings.
    - If a drug name appears misspelled (e.g., "Warrfarin", "Aspirn", "Metfromin"),
      correct it silently for the analysis, BUT you MUST put this exact format in the
      "summary" field at the start:
      "Note: '[original]' was interpreted as '[corrected]'. Please verify this is correct. "
    - The "drugs" field in each interaction should use the CORRECTED name.

    SEVERITY CLASSIFICATION RULES:
    6. Do NOT classify as Major if both drugs are standard first-line combination
       therapy for the same condition (e.g., ACE inhibitor + Metformin for T2DM with HTN,
       Statin + Aspirin for cardiovascular prevention). Only classify as Major if the
       FDA label explicitly states a Major or severe interaction.
    7. Prefer Moderate over Major when the interaction is manageable with routine monitoring
       and does not require avoiding the combination.

    IMPORTANT RULES:
    1. The "drugs" field MUST be an array with exactly 2 drug names (strings)
    2. NEVER use empty arrays [] for the "drugs" field
    3. Drug names must match the input drugs exactly
    4. If no interactions found, return an empty "interactions" array: []
    5. Always include "summary" and "risk_level" fields

    Output JSON only, no additional text."""

    drug_list = ', '.join(body.drugs)
    user_prompt = f"""
    Patient Context: {body.patient_context or 'None'}
    Drugs to Analyze: {drug_list}

    IMPORTANT: Before analyzing, carefully check if any drug name above appears misspelled
    (e.g., extra letters, transposed letters). If so, you MUST start the "summary" field with:
    "Note: '[original]' was interpreted as '[corrected]'. Please verify this is correct."

    Reference FDA Data:
    {fda_context}

    Please analyze interactions between these drugs based on the FDA data provided.
    """

    client = OpenAI()
    summary = ""
    interactions = []
    risk_level = "Unknown"
    max_retries = 2
    analysis_success = False

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            analysis = json.loads(completion.choices[0].message.content)

            temp_interactions = []
            for item in analysis.get("interactions", []):
                try:
                    drugs = item.get("drugs", [])
                    if not drugs or len(drugs) < 2:
                        print(f"⚠️ Warning: Invalid interaction data: {item}")
                        continue
                    if not all(isinstance(d, str) and d.strip() for d in drugs):
                        print(f"⚠️ Warning: Invalid drug names: {drugs}")
                        continue
                    drug1, drug2 = drugs[0], drugs[1]
                    source_url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug1.replace(' ', '+')}"
                    temp_interactions.append(DrugInteraction(
                        drug_pair=tuple(drugs[:2]),
                        severity=item.get("severity", "Unknown"),
                        description=item.get("description", "No description provided"),
                        clinical_recommendation=item.get("recommendation", ""),
                        source="FDA Label Analysis",
                        source_url=source_url
                    ))
                except Exception as e:
                    print(f"⚠️ Error parsing interaction: {e}")
                    continue

            interactions = temp_interactions
            if interactions or analysis.get("interactions") is not None:
                print(f"✅ Analysis successful on attempt {attempt + 1}")
                analysis_success = True
                break
            else:
                if attempt < max_retries - 1:
                    continue

        except Exception as e:
            print(f"❌ LLM call failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                summary = f"Analysis failed after {max_retries} retries. Error: {str(e)}"
                risk_level = "Unknown"

    if analysis_success:
        if interactions:
            severity_counts = {}
            for interaction in interactions:
                severity = interaction.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            summary_parts = []
            for severity, count in sorted(
                severity_counts.items(),
                key=lambda x: {"Critical": 4, "Major": 3, "Moderate": 2, "Minor": 1}.get(x[0], 0),
                reverse=True
            ):
                summary_parts.append(f"{count} 個{severity}")

            summary = f"Found {len(interactions)} drug interaction(s): {', '.join(summary_parts)}. Please review the details below and consult a healthcare professional."

            if any(i.severity == "Critical" for i in interactions):
                risk_level = "Critical"
            elif any(i.severity == "Major" for i in interactions):
                risk_level = "Major"
            elif any(i.severity == "Moderate" for i in interactions):
                risk_level = "Moderate"
            else:
                risk_level = "Minor"
        else:
            summary = "No significant drug interactions found in the FDA data. This does not eliminate all risk — please consult a healthcare professional."
            risk_level = "Low"

    elapsed_ms = int((time.time() - start_time) * 1000)

    try:
        audit_log = AuditLog(
            id=f"ver_{int(time.time()*1000)}",
            user_id=user_id,
            action="verify",
            query_content=f"Checked: {body.drugs}",
            ip_address="0.0.0.0"
        )
        db.add(audit_log)
    except Exception as e:
        print(f"Audit Log Error: {e}")

    try:
        history = ChatHistory(
            user_id=user_id,
            session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}",
            answer=summary
        )
        db.add(history)
        db.commit()
    except Exception as e:
        print(f"History Save Error: {e}")
        db.rollback()

    if spelling_corrections:
        correction_note = "Note: " + "; ".join(spelling_corrections) + ". Please verify this is correct. "
        summary = correction_note + summary

    return VerifyResponse(
        drugs_analyzed=body.drugs,
        interactions=interactions,
        summary=summary,
        risk_level=risk_level,
        query_time_ms=elapsed_ms
    )


# ============================================================
# 功能 4：數據飛輪 - 使用者回饋 (Feedback)
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
        sanitized_text = PHIDetector.sanitize_for_log(feedback.feedback_text) if feedback.feedback_text else None

        db_feedback = UserFeedback(
            id=f"fb_{int(time.time()*1000)}",
            user_id=user_id,
            query=feedback.query,
            response=feedback.response,
            rating=feedback.rating,
            feedback_text=sanitized_text,
            category=feedback.category
        )

        db.add(db_feedback)
        db.commit()
        return {"status": "success", "message": "Feedback recorded"}

    except Exception as e:
        print(f"Feedback Error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================
# 功能 5：查詢歷史紀錄 (History)
# ============================================================

@app.get("/api/history")
async def get_user_history(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(creds)

    history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == user_id)\
        .order_by(desc(ChatHistory.created_at))\
        .limit(50)\
        .all()

    return history


# ============================================================
# 健康檢查與狀態
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.1.0"}

@app.get("/api/status")
async def api_status(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_auth)
):
    try:
        from api.database.vector_store import get_vector_store
        vs = get_vector_store()
        vector_store_status = vs.get_stats()
    except Exception as e:
        vector_store_status = {"error": str(e)}

    return {
        "status": "healthy",
        "version": "2.1.0",
        "features": {
            "consultation": True,
            "research": True,
            "pubmed": True,
            "fda": True,
            "verify": True,
            "feedback": True,
            "history": True
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