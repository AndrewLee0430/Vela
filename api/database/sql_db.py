# api/database/sql_db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 讀取環境變數，預設為本地 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/medinotes.db")

# 設定 connect_args（僅 SQLite 需要）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# 建立 Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
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