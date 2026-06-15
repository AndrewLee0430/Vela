"""
OpenAIProvider — default provider for all 9 task layers in Phase 0.

Wraps openai.AsyncOpenAI. All existing Vela behavior is preserved.
"""

from __future__ import annotations
import os
from typing import AsyncIterator

from openai import AsyncOpenAI
from openai import APIError, RateLimitError, AuthenticationError, NotFoundError, APITimeoutError

from api.providers.base import (
    Provider,
    ProviderCapability,
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
    EmbeddingRequest,
    EmbeddingResponse,
)
from api.providers.errors import VelaError, VelaErrorCode


_REASONING_PREFIXES = ("o1", "o3", "o4", "gpt-5")


def _is_reasoning_model(model: str) -> bool:
    return model.startswith(_REASONING_PREFIXES)


def _reasoning_min_completion_tokens() -> int:
    try:
        return int(os.getenv("REASONING_MIN_COMPLETION_TOKENS", "10000"))
    except ValueError:
        return 10000  # malformed env must not block boot


def _apply_param_contract(kwargs: dict, req, model: str) -> dict:
    """Map temperature/max_tokens onto the API kwargs per the model's contract.

    Default (gpt-4.1 etc.): byte-identical to the legacy inline mapping.
    Reasoning models (GPT-5 / o-series): use max_completion_tokens (max_tokens
    is rejected), apply reasoning_effort, and omit temperature (only default(1)
    accepted).
    """
    if not _is_reasoning_model(model):
        # default branch — gpt-4.1 path BYTE-IDENTICAL, do NOT touch
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        return kwargs
    # reasoning branch (GPT-5 / o-series)
    kwargs["max_completion_tokens"] = max(req.max_tokens or 0, _reasoning_min_completion_tokens())
    effort = os.getenv("REASONING_EFFORT", "medium")
    if effort:  # empty string → omit reasoning_effort (no-code escape hatch)
        kwargs["reasoning_effort"] = effort
    # temperature intentionally dropped — reasoning models accept only default(1)
    # NOTE: o1 maps params correctly here but does NOT support system messages —
    #       not an eval target this round.
    return kwargs


class OpenAIProvider(Provider):
    name = "openai"
    capabilities = {
        ProviderCapability.GENERATOR,
        ProviderCapability.GUARD,
        ProviderCapability.RERANKER,
        ProviderCapability.LIGHTWEIGHT,
        ProviderCapability.RESEARCH_JUDGE,
        ProviderCapability.EXPLAIN_JUDGE,
        ProviderCapability.VISION,
        ProviderCapability.VERIFY,
        ProviderCapability.EMBEDDER,
    }

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            # Allow construction without key for capability checks / unit tests;
            # actual call will raise AuthenticationError → VelaError later.
            key = "missing-openai-api-key"
        self._client = AsyncOpenAI(api_key=key)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        try:
            kwargs = {
                "model": req.model,
                "messages": req.messages,
            }
            _apply_param_contract(kwargs, req, req.model)
            if req.response_format is not None:
                kwargs["response_format"] = req.response_format
            kwargs.update(req.extra)

            resp = await self._client.chat.completions.create(**kwargs)
            return CompletionResponse(
                content=resp.choices[0].message.content or "",
                model=resp.model,
                input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                raw=resp,
                finish_reason=getattr(resp.choices[0], "finish_reason", None) if resp.choices else None,
            )
        except RateLimitError as e:
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "openai", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "openai", req.model, e)
        except NotFoundError as e:
            raise VelaError(VelaErrorCode.LLM_MODEL_NOT_FOUND, str(e), "openai", req.model, e)
        except APITimeoutError as e:
            raise VelaError(VelaErrorCode.LLM_TIMEOUT, str(e), "openai", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "openai", req.model, e)

    async def stream(self, req: CompletionRequest) -> AsyncIterator[StreamChunk]:
        try:
            kwargs = {
                "model": req.model,
                "messages": req.messages,
                "stream": True,
                # Surface final usage chunk so callers can log cost-tracking
                # metrics. The final SSE chunk has choices=[] and usage set.
                "stream_options": {"include_usage": True},
            }
            _apply_param_contract(kwargs, req, req.model)
            # Caller-provided extra wins (allows opting out / overriding stream_options).
            kwargs.update(req.extra)

            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                usage = None
                if getattr(chunk, "usage", None):
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                    }
                if delta is not None or usage is not None:
                    yield StreamChunk(delta=delta, usage=usage)
        except RateLimitError as e:
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "openai", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "openai", req.model, e)
        except NotFoundError as e:
            raise VelaError(VelaErrorCode.LLM_MODEL_NOT_FOUND, str(e), "openai", req.model, e)
        except APITimeoutError as e:
            raise VelaError(VelaErrorCode.LLM_TIMEOUT, str(e), "openai", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "openai", req.model, e)

    async def embed(self, req: EmbeddingRequest) -> EmbeddingResponse:
        try:
            resp = await self._client.embeddings.create(model=req.model, input=req.input)
            return EmbeddingResponse(
                embeddings=[d.embedding for d in resp.data],
                model=resp.model,
                input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            )
        except RateLimitError as e:
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "openai", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "openai", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "openai", req.model, e)

    @property
    def raw_client(self) -> AsyncOpenAI:
        return self._client
