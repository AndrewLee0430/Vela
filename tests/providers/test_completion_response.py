"""Unit tests for CompletionResponse.finish_reason observability contract.

Rule 18 (fail loud): callers must be able to detect provider truncation
(finish_reason == "length") and other terminal states without poking at
the raw provider-specific response. The contract: every Provider.complete()
implementation populates finish_reason on the returned CompletionResponse,
defaulting to None when the underlying SDK doesn't expose it.

Intent under test: the field EXISTS, defaults safely, and round-trips a
value. Integration tests covering actual OpenAI/Groq responses would
require SDK mocking and are deferred.
"""

from __future__ import annotations

from api.providers.base import CompletionResponse


def test_finish_reason_defaults_to_none():
    """Backward-compat: existing call sites that don't set finish_reason
    still construct a valid CompletionResponse."""
    r = CompletionResponse(content="ok", model="gpt-4.1", input_tokens=5, output_tokens=2)
    assert r.finish_reason is None


def test_finish_reason_roundtrips_length():
    """Truncation is observable. A caller can branch on this value to
    emit a distinct error code (see ExplainErrorCode.OUTPUT_TRUNCATED)."""
    r = CompletionResponse(
        content='{"items": [',  # truncated mid-output
        model="gpt-4.1",
        input_tokens=100,
        output_tokens=1500,
        finish_reason="length",
    )
    assert r.finish_reason == "length"


def test_finish_reason_roundtrips_stop():
    """Natural completion remains the common case; the field must accept
    "stop" without special-casing."""
    r = CompletionResponse(
        content='{"items": []}',
        model="gpt-4.1",
        input_tokens=100,
        output_tokens=20,
        finish_reason="stop",
    )
    assert r.finish_reason == "stop"
