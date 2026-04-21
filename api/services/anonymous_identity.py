"""
Anonymous identity derivation and daily reset helpers for Decision 001 L0 tier.

Identity is derived from (client_ip, fingerprint) SHA-256 hash — no PII stored.
"""

import hashlib
import re
from datetime import date, datetime, timezone

_ANON_SALT = "vela_anon_v1"  # version salt; bump if identity schema changes

_FP_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]+$")


def today_utc() -> date:
    """Return today's date in UTC (for quota reset comparison)."""
    return datetime.now(timezone.utc).date()


def derive_anon_id(client_ip: str, fingerprint: str) -> str:
    """
    Derive 64-char SHA-256 hex from (IP + fingerprint + salt).
    Deterministic: same (IP, fingerprint) always yields same anon_id.
    No PII persisted — only the hash.
    """
    raw = f"{_ANON_SALT}:{client_ip}:{fingerprint}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_fingerprint(fp: str | None) -> str:
    """
    Validate X-Anon-Fingerprint header per Decision 001 v0.3 A2.
    Length 16-128, URL-safe base64 alphabet.
    Raises ValueError if invalid.
    """
    if not fp:
        raise ValueError("fingerprint required")
    if not (16 <= len(fp) <= 128):
        raise ValueError("fingerprint length out of range (16-128)")
    if not _FP_PATTERN.match(fp):
        raise ValueError("fingerprint contains invalid characters")
    return fp
