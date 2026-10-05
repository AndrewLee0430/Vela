"""Anonymous aggregate cost guard per Decision 001 v0.3 A7 / v0.4 A10."""

import math
import os
from typing import Optional, Tuple
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from api.models.sql_models import ApiCostLog
from api.services.anonymous_identity import today_utc

_DEFAULT_ANONYMOUS_DAILY_BUDGET_USD = 2.00  # Decision 001 v0.3 A7


def _budget_from_env(raw: Optional[str]) -> float:
    """ARCHIVE MODE car (2026-10-05): the cap is configurable via
    ANON_DAILY_BUDGET_USD (fly.toml [env], repo-auditable). Unset or blank →
    the A7 default, byte-for-byte the old behaviour. A malformed, negative or
    non-finite value RAISES at import, so the process does not start rather
    than run under a cap nobody chose (Rule 18). 0 is valid: a kill switch.
    (ADR 001 §3.4 sketched the name ANONYMOUS_DAILY_BUDGET_USD; it was never
    read from env. The car spec names ANON_DAILY_BUDGET_USD.)"""
    if raw is None or not raw.strip():
        return _DEFAULT_ANONYMOUS_DAILY_BUDGET_USD
    value = float(raw.strip())
    if not math.isfinite(value) or value < 0:
        raise ValueError("ANON_DAILY_BUDGET_USD must be a finite number >= 0")
    return value


ANONYMOUS_DAILY_BUDGET_USD = _budget_from_env(os.getenv("ANON_DAILY_BUDGET_USD"))


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
