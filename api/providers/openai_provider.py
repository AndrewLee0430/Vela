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
    EmbeddingRequest,
    EmbeddingResponse,
)
from api.providers.errors import VelaError, VelaErrorCode


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
            raise VelaError(VelaErrorCode.LLM_RATE_LIMITED, str(e), "openai", req.model, e)
        except AuthenticationError as e:
            raise VelaError(VelaErrorCode.LLM_AUTH_FAILED, str(e), "openai", req.model, e)
        except NotFoundError as e:
            raise VelaError(VelaErrorCode.LLM_MODEL_NOT_FOUND, str(e), "openai", req.model, e)
        except APITimeoutError as e:
            raise VelaError(VelaErrorCode.LLM_TIMEOUT, str(e), "openai", req.model, e)
        except APIError as e:
            raise VelaError(VelaErrorCode.LLM_PROVIDER_UNAVAILABLE, str(e), "openai", req.model, e)

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
