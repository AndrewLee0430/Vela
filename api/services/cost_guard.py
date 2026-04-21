"""Anonymous aggregate cost guard per Decision 001 v0.3 A7 / v0.4 A10."""

from typing import Tuple
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from api.models.sql_models import ApiCostLog
from api.services.anonymous_identity import today_utc

ANONYMOUS_DAILY_BUDGET_USD = 2.00


async def check_anonymous_budget(db: Session) -> Tuple[bool, float]:
    """
    Check whether anonymous aggregate spend today is under the daily cap.
    Returns (allowed, spent_today_usd).

    Anonymous rows are identified by ApiCostLog.user_id IS NULL
    (Decision 001 v0.4 A10 — no separate anon_id column).
    """
    result = db.query(
        func.coalesce(func.sum(ApiCostLog.estimated_cost_usd), 0.0)
    ).filter(
        ApiCostLog.user_id.is_(None)
    ).filter(
        cast(ApiCostLog.created_at, Date) == today_utc()
    ).scalar()

    spent = float(result or 0.0)
    return spent < ANONYMOUS_DAILY_BUDGET_USD, spent
