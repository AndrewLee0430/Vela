from sqlalchemy import Column, String, DateTime, JSON, Integer, Text, Boolean, Float, Date
from datetime import datetime
from api.database.sql_db import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, index=True)
    action = Column(String)
    query_content = Column(Text)
    resource_ids = Column(JSON)
    ip_address = Column(String)
    extra_data = Column(JSON, nullable=True)  # LLM Judge scores + other metadata

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    session_type = Column(String) 
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 🆕 新增：使用者回饋資料表 (數據飛輪的核心)
class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    query = Column(Text)           # 原始問題
    response = Column(Text)        # AI 的回答
    rating = Column(Integer)       # 1=Like, -1=Dislike, 2=Edited
    feedback_text = Column(Text, nullable=True) # 修改後的內容或評論
    category = Column(String)      # "research", "verify"
    
    is_reviewed = Column(Boolean, default=False)   # 是否已人工審核
    is_vectorized = Column(Boolean, default=False) # 是否已轉入向量庫


class UserUsage(Base):
    __tablename__ = "user_usage"

    clerk_user_id = Column(String, primary_key=True)
    plan_type = Column(String, default="free")
    credits_used = Column(Integer, default=0)
    credits_used_today = Column(Integer, default=0)
    last_daily_reset = Column(DateTime, default=datetime.utcnow)
    last_free_reset = Column(Date, nullable=True)
    lemon_customer_id = Column(String, nullable=True)
    lemon_subscription_id = Column(String, nullable=True)
    lemon_variant_id = Column(String, nullable=True)
    dodo_customer_id = Column(String, nullable=True)
    dodo_subscription_id = Column(String, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiCostLog(Base):
    __tablename__ = "api_cost_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    feature = Column(String)
    model = Column(String)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id = Column(String, primary_key=True)
    event_type = Column(String)
    processed_at = Column(DateTime, default=datetime.utcnow)


class AnonymousUsage(Base):
    __tablename__ = "anonymous_usage"

    anon_id = Column(String(64), primary_key=True)
    credits_used_today = Column(Integer, default=0, nullable=False)
    last_reset_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(String, primary_key=True)
    issue_type = Column(String, nullable=False)          # inaccurate | ui_error | feature_request | other
    description = Column(Text, nullable=False)
    email = Column(String, nullable=True)
    user_id = Column(String, nullable=True, index=True)  # Clerk user id, null for anonymous
    query_id = Column(String, nullable=True, index=True) # last query_id when submitted on a feature page
    page_url = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    locale = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SharedQuery(Base):
    """PRD § 4.5 — Public share of a single Research/Verify/Explain answer.

    Snapshot semantics: query_text / answer_text / citations are copied
    in at /api/share/create time (PHASE B). Does NOT FK to chat_history,
    so 180-day ChatHistory cleanup leaves shares intact.
    """
    __tablename__ = "shared_query"

    share_id = Column(String, primary_key=True)
    query_id = Column(String, nullable=True, index=True)       # PHASE B idempotency key
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False)                   # list of citation dicts; jsonb in Postgres
    created_by = Column(String, nullable=True, index=True)     # sha256(salt + user_id)[:16]; PHASE B
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, nullable=False, default=True)
    view_count = Column(Integer, nullable=False, default=0)
    last_viewed_at = Column(DateTime, nullable=True)
    flagged = Column(Boolean, nullable=False, default=False, index=True)
    locale = Column(String, nullable=True)                     # renderer i18n hint