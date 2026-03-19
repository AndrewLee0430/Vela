# api/services/usage_service.py

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.models.sql_models import UserUsage

# Credit 設定（僅後端，不暴露給前端）
FREE_CREDIT_LIMIT = 15
PRO_DAILY_SAFETY_CAP = 50

CREDIT_COSTS = {
    "research": 3,
    "explain": 2,
    "verify": 1,
}


async def get_or_create_usage(db: Session, user_id: str) -> UserUsage:
    """取得或建立用戶的 usage record"""
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == user_id
    ).first()

    if not usage:
        usage = UserUsage(clerk_user_id=user_id)
        db.add(usage)
        db.commit()
        db.refresh(usage)

    return usage


async def reset_daily_if_needed(db: Session, usage: UserUsage) -> UserUsage:
    """如果已經是新的一天，重置每日計數"""
    now = datetime.now(timezone.utc)
    last_reset = usage.last_daily_reset

    # 確保 last_reset 有 timezone info
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    if now.date() > last_reset.date():
        usage.credits_used_today = 0
        usage.last_daily_reset = now
        db.commit()
        db.refresh(usage)

    return usage


async def check_and_deduct_credits(
    db: Session, user_id: str, feature: str
) -> tuple[bool, str]:
    """
    檢查並扣減 credits。返回 (allowed, reason)
    - Free 用戶：credits_used >= FREE_CREDIT_LIMIT → 拒絕
    - Pro 用戶：credits_used_today >= PRO_DAILY_SAFETY_CAP → 拒絕
    """
    usage = await get_or_create_usage(db, user_id)
    usage = await reset_daily_if_needed(db, usage)
    cost = CREDIT_COSTS.get(feature, 1)

    if usage.plan_type == "free":
        if usage.credits_used >= FREE_CREDIT_LIMIT:
            return False, "limit_reached"

    elif usage.plan_type == "pro":
        if usage.credits_used_today >= PRO_DAILY_SAFETY_CAP:
            return False, "daily_cap_reached"

    # 扣減 credits（atomic update）
    if usage.plan_type == "free":
        usage.credits_used += cost
    usage.credits_used_today += cost
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()

    return True, "ok"


async def check_credits(
    db: Session, user_id: str, feature: str
) -> tuple[bool, str]:
    """只檢查，不扣減"""
    usage = await get_or_create_usage(db, user_id)
    usage = await reset_daily_if_needed(db, usage)

    if usage.plan_type == "free":
        if usage.credits_used >= FREE_CREDIT_LIMIT:
            return False, "limit_reached"
    elif usage.plan_type == "pro":
        if usage.credits_used_today >= PRO_DAILY_SAFETY_CAP:
            return False, "daily_cap_reached"

    return True, "ok"


async def deduct_credits(
    db: Session, user_id: str, feature: str
) -> None:
    """只扣減，不檢查（在成功後呼叫）"""
    usage = await get_or_create_usage(db, user_id)
    cost = CREDIT_COSTS.get(feature, 1)

    if usage.plan_type == "free":
        usage.credits_used += cost
    usage.credits_used_today += cost
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()
