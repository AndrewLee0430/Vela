# api/database/sql_db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 讀取環境變數，預設為本地 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/medinotes.db")

# 設定 connect_args（僅 SQLite 需要）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# 建立 Engine
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,    # 使用前檢查連線是否存活
        pool_recycle=300,      # 每 5 分鐘回收，避免 Neon idle timeout
        echo=False,
        # Founder ruling P1 (2026-10-05): DB error text must not carry row values (an AuditLog's
        # query_content is the question) — they reach the log via _safe_db_write and Sentry.
        hide_parameters=True,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,
        hide_parameters=True,  # P1 — see the postgresql branch
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
