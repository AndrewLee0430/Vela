"""
GroqProvider — Phase 1B activation target per ADR 005.

Phase 0 ship state: framework ready, default NOT enabled.
Groq is OpenAI-compatible — reuses openai.AsyncOpenAI SDK with custom base_url.

Capabilities supported: generator/guard/reranker/lightweight/research_judge/
explain_judge/verify (text-only).
NOT supported: embedder (Groq has no embedding model), vision (deferred Phase 2+).

Per ADR 005 expected use: Lightweight tasks → Llama 3.1 8B at $0.05/$0.08.
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
    EmbeddingRequest,
    EmbeddingResponse,
)
from api.providers.errors import VelaError, VelaErrorCode


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(Provider):
    name = "groq"
    capabilities = {
        ProviderCapability.GENERATOR,
        ProviderCapability.GUARD,
        ProviderCapability.RERANKER,
        ProviderCapability.LIGHTWEIGHT,
        ProviderCapability.RESEARCH_JUDGE,
        ProviderCapability.EXPLAIN_JUDGE,
        ProviderCapability.VERIFY,
        # NOT VISION, NOT EMBEDDER
    }

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            # Allow construction without key for capability checks;
            # actual call will raise AuthenticationError → VelaError later.
            key = "missing-groq-api-key"
        self._client = AsyncOpenAI(api_key=key, base_url=GROQ_BASE_URL)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        try:
            kwargs = {
                "model": req.model,
                "messages": req.messages,
            }
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.max_tokens is not None:
                kwargs["max_tokens"] = req.max_tokens
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
            )
        except RateLimitError as e:
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "groq", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "groq", req.model, e)
        except NotFoundError as e:
            raise VelaError(VelaErrorCode.LLM_MODEL_NOT_FOUND, str(e), "groq", req.model, e)
        except APITimeoutError as e:
            raise VelaError(VelaErrorCode.LLM_TIMEOUT, str(e), "groq", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "groq", req.model, e)

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        try:
            kwargs = {
                "model": req.model,
                "messages": req.messages,
                "stream": True,
            }
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.max_tokens is not None:
                kwargs["max_tokens"] = req.max_tokens
            kwargs.update(req.extra)

            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except RateLimitError as e:
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "groq", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "groq", req.model, e)
        except NotFoundError as e:
            raise VelaError(VelaErrorCode.LLM_MODEL_NOT_FOUND, str(e), "groq", req.model, e)
        except APITimeoutError as e:
            raise VelaError(VelaErrorCode.LLM_TIMEOUT, str(e), "groq", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "groq", req.model, e)

    async def embed(self, req: EmbeddingRequest) -> EmbeddingResponse:
        raise VelaError(
            VelaErrorCode.LLM_CAPABILITY_UNSUPPORTED,
            "Groq does not provide embedding models. Use OpenAI for EMBEDDER_PROVIDER.",
            provider="groq",
            model=req.model,
        )
