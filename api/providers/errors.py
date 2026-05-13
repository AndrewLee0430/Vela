"""
VelaError schema per PRD §2.1 v1.4 需求 8.

All provider-layer errors should be wrapped into VelaError with one of the
LLM_* error codes for consistent downstream handling.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any


class VelaErrorCode(Enum):
    LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"
    LLM_MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
    LLM_CAPABILITY_UNSUPPORTED = "LLM_CAPABILITY_UNSUPPORTED"


@dataclass
class VelaError(Exception):
    """Unified error type for provider layer."""
    code: VelaErrorCode
    message: str
    provider: str | None = None
    model: str | None = None
    original: Exception | None = None
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        bits = [f"[{self.code.value}]"]
        if self.provider:
            bits.append(f"provider={self.provider}")
        if self.model:
            bits.append(f"model={self.model}")
        bits.append(self.message)
        return " ".join(bits)
