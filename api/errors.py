"""Custom API exceptions for tier-aware error responses."""

from fastapi import HTTPException


class FeatureNotAvailable(HTTPException):
    """L0 tier attempting L1+ feature. Frontend shows signup CTA."""

    def __init__(self, feature: str) -> None:
        super().__init__(
            status_code=403,
            detail={"type": "signup_required", "feature": feature},
        )


class AnonymousQuotaExceeded(HTTPException):
    """Per-anon_id daily quota hit (ANONYMOUS_DAILY_LIMIT credits)."""

    def __init__(self, used: int, limit: int) -> None:
        super().__init__(
            status_code=429,
            detail={
                "type": "anonymous_quota_exceeded",
                "used": used,
                "limit": limit,
            },
        )


class AnonymousBudgetExceeded(HTTPException):
    """Global $2/day anonymous aggregate cap (Decision 001 v0.3 A7)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail={"type": "budget_exceeded"},
        )


class AccountDeleted(HTTPException):
    """user_usage row is FROZEN (deleted_at set) — account under/after deletion
    (design E). The row is retained for statutory billing/audit but denied to
    all product logic; a frozen account must never be silently re-activated."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            detail={"type": "account_deleted"},
        )


class InvalidFingerprint(HTTPException):
    """X-Anon-Fingerprint header failed validation (Decision 001 v0.3 A2)."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            status_code=400,
            detail={"type": "invalid_fingerprint", "reason": reason},
        )
