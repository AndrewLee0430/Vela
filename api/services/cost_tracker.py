# api/services/cost_tracker.py

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.models.sql_models import ApiCostLog

logger = logging.getLogger(__name__)

# GPT-4.1 pricing (per 1M tokens)
MODEL_COSTS = {
    "gpt-4.1":      {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4o-mini":  {"input": 0.15, "output": 0.60},
    "gpt-4o":       {"input": 2.50, "output": 10.00},
}


async def log_api_cost(
    db: Session,
    user_id: str,
    feature: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> None:
    """記錄單次 API call 的 token 成本（使用已有的 db session）"""
    cost_config = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4.1-mini"])
    estimated_cost = (
        (prompt_tokens / 1_000_000) * cost_config["input"] +
        (completion_tokens / 1_000_000) * cost_config["output"]
    )

    log = ApiCostLog(
        user_id=user_id,
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=round(estimated_cost, 6),
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()


async def log_api_cost_standalone(
    user_id: str,
    feature: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> None:
    """記錄 token 成本（自建 db session，供 pipeline 內部元件使用）"""
    try:
        from api.database.sql_db import SessionLocal
        db = SessionLocal()
        try:
            cost_config = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4.1-mini"])
            estimated_cost = (
                (prompt_tokens / 1_000_000) * cost_config["input"] +
                (completion_tokens / 1_000_000) * cost_config["output"]
            )
            log = ApiCostLog(
                user_id=user_id,
                feature=feature,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=round(estimated_cost, 6),
                created_at=datetime.now(timezone.utc)
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.warning("Cost tracking failed (%s/%s): %s", feature, model, e)
