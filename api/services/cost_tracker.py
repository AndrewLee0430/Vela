# api/services/cost_tracker.py

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.models.sql_models import ApiCostLog

# GPT-4.1 pricing (per 1M tokens)
MODEL_COSTS = {
    "gpt-4.1":      {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


async def log_api_cost(
    db: Session,
    user_id: str,
    feature: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> None:
    """記錄單次 API call 的 token 成本"""
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
