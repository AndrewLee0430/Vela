from sqlalchemy import Column, String, DateTime, JSON, Integer, Text, Boolean, Float
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
    lemon_customer_id = Column(String, nullable=True)
    lemon_subscription_id = Column(String, nullable=True)
    lemon_variant_id = Column(String, nullable=True)
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