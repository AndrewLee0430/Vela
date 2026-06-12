# api/services/usage_service.py

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.models.sql_models import UserUsage, AnonymousUsage
from api.services.anonymous_identity import today_utc
from api.errors import AccountDeleted

# Credit 設定（僅後端，不暴露給前端）
FREE_DAILY_LIMIT = 10
PRO_DAILY_SAFETY_CAP = 100

# Decision 001 v0.3 A6: "2R + 2V" pattern (2×3 + 2×1 = 8 credits).
# Aggregate limit (not per-feature) simplifies check/deduct logic.
# $2/day global anonymous budget cap provides cost safety net.
ANONYMOUS_DAILY_LIMIT = 8

CREDIT_COSTS = {
    "research": 3,
    "explain": 2,
    "verify": 1,
}


def _resolve_usage(db: Session, user_id: str, *, create: bool) -> Optional[UserUsage]:
    """Single 3-state resolver for user_usage (account-deletion design E).

    - active row (deleted_at IS NULL) → return it
    - FROZEN row (deleted_at set)     → raise AccountDeleted (403). NEVER serve,
      NEVER recreate — a frozen account must not be silently re-activated.
    - no row → create a fresh active row if `create`, else return None.

    The lookup is by clerk_user_id WITHOUT a deleted_at filter on purpose, so a
    frozen row is always detected (filtering it out would let get_or_create
    recreate it as active — the re-creation trap).
    """
    usage = db.query(UserUsage).filter(
        UserUsage.clerk_user_id == user_id
    ).first()

    if usage is not None:
        if usage.deleted_at is not None:
            raise AccountDeleted()
        return usage

    if create:
        usage = UserUsage(clerk_user_id=user_id)
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return usage

    return None


async def get_or_create_usage(db: Session, user_id: str) -> UserUsage:
    """取得或建立用戶的 usage record（frozen → 403 account_deleted）"""
    return _resolve_usage(db, user_id, create=True)


def get_active_usage(db: Session, user_id: str) -> Optional[UserUsage]:
    """Product-gating read: the active user_usage row, or None if no row.
    Frozen rows raise AccountDeleted (403) — route every gating read through
    this so a deleted account is denied everywhere. Sync (callers need no await)."""
    return _resolve_usage(db, user_id, create=False)


async def reset_daily_if_needed(db: Session, usage: UserUsage) -> UserUsage:
    """如果已經是新的一天，重置每日計數（Free + Pro 都重置）"""
    now = datetime.now(timezone.utc)
    last_reset = usage.last_daily_reset

    # 確保 last_reset 有 timezone info
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    if now.date() > last_reset.date():
        usage.credits_used_today = 0
        usage.last_daily_reset = now
        # Also track free reset date separately
        if usage.plan_type == "free":
            usage.last_free_reset = now.date()
        db.commit()
        db.refresh(usage)

    return usage


async def check_and_deduct_credits(
    db: Session, user_id: str, feature: str
) -> tuple[bool, str]:
    """
    檢查並扣減 credits。返回 (allowed, reason)
    - Free 用戶：credits_used_today >= FREE_DAILY_LIMIT → 拒絕
    - Pro 用戶：credits_used_today >= PRO_DAILY_SAFETY_CAP → 拒絕
    """
    usage = await get_or_create_usage(db, user_id)
    usage = await reset_daily_if_needed(db, usage)
    cost = CREDIT_COSTS.get(feature, 1)

    if usage.plan_type == "free":
        if usage.credits_used_today >= FREE_DAILY_LIMIT:
            return False, "limit_reached"

    elif usage.plan_type == "pro":
        if usage.credits_used_today >= PRO_DAILY_SAFETY_CAP:
            return False, "daily_cap_reached"

    # 扣減 credits（atomic update）
    usage.credits_used_today += cost
    if usage.plan_type == "free":
        usage.credits_used += cost  # Keep lifetime counter for analytics
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
        if usage.credits_used_today >= FREE_DAILY_LIMIT:
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

    usage.credits_used_today += cost
    if usage.plan_type == "free":
        usage.credits_used += cost  # Keep lifetime counter for analytics
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()


# --------------------------------------------------------------------------- #
# Decision 001 L0 anonymous tier — quota helpers                              #
# --------------------------------------------------------------------------- #


async def _get_or_create_anonymous_usage(
    db: Session, anon_id: str
) -> AnonymousUsage:
    """取得或建立 anonymous session 的 usage record."""
    usage = db.query(AnonymousUsage).filter(
        AnonymousUsage.anon_id == anon_id
    ).first()

    if not usage:
        usage = AnonymousUsage(
            anon_id=anon_id,
            credits_used_today=0,
            last_reset_date=today_utc(),
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)

    return usage


async def _reset_anonymous_daily_if_needed(
    db: Session, usage: AnonymousUsage
) -> AnonymousUsage:
    """如果已經是新的一天（UTC），重置 anonymous 每日 credits."""
    today = today_utc()
    if usage.last_reset_date < today:
        usage.credits_used_today = 0
        usage.last_reset_date = today
        db.commit()
        db.refresh(usage)
    return usage


async def check_anonymous_credits(
    db: Session, anon_id: str, feature: str
) -> tuple[bool, int]:
    """
    檢查匿名身份是否有足夠 credits 執行此次請求。不扣減。
    返回 (allowed, credits_remaining_after_this_cost).
    若 not allowed, remaining = credits left before this request (>= 0).
    """
    usage = await _get_or_create_anonymous_usage(db, anon_id)
    usage = await _reset_anonymous_daily_if_needed(db, usage)
    cost = CREDIT_COSTS.get(feature, 1)

    if usage.credits_used_today + cost > ANONYMOUS_DAILY_LIMIT:
        remaining = max(0, ANONYMOUS_DAILY_LIMIT - usage.credits_used_today)
        return False, remaining

    return True, ANONYMOUS_DAILY_LIMIT - usage.credits_used_today - cost


async def deduct_anonymous_credits(
    db: Session, anon_id: str, feature: str
) -> None:
    """扣減並更新 last_active_at（在成功後呼叫）."""
    usage = await _get_or_create_anonymous_usage(db, anon_id)
    cost = CREDIT_COSTS.get(feature, 1)

    usage.credits_used_today += cost
    usage.last_active_at = datetime.now(timezone.utc)
    db.commit()
