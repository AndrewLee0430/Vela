"""
Provider abstract base class.

All providers must implement the methods their declared capabilities support.
NotImplementedError is acceptable for unsupported capabilities (e.g. Groq lacks
embedder + vision); callers are expected to check capabilities before invoking.

Per PRD §2.1 v1.4 需求 2.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


class ProviderCapability(Enum):
    """Capabilities a provider may or may not support."""
    GENERATOR = "generator"           # streaming RAG
    GUARD = "guard"                   # classification (sync OK)
    RERANKER = "reranker"             # structured JSON
    LIGHTWEIGHT = "lightweight"       # short completions
    RESEARCH_JUDGE = "research_judge" # LLM-as-judge
    EXPLAIN_JUDGE = "explain_judge"   # LLM-as-judge (acceptance-critical)
    VISION = "vision"                 # multimodal (image input)
    VERIFY = "verify"                 # user-facing structured output
    EMBEDDER = "embedder"             # text-embedding


@dataclass
class CompletionRequest:
    """Unified completion request."""
    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Unified completion response."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    raw: Any = None  # provider-specific raw response


@dataclass
class StreamChunk:
    """One unit yielded from Provider.stream().

    Most chunks carry a token `delta`. The final chunk carries `usage` only
    (delta is None) when the provider supports usage-in-stream (OpenAI's
    stream_options={"include_usage": True} contract; Groq same on OpenAI-compat).

    Callers should treat delta and usage independently: a chunk may have one,
    the other, or in some providers both.
    """
    delta: str | None = None
    usage: dict[str, int] | None = None  # {"prompt_tokens": N, "completion_tokens": N} on final chunk


@dataclass
class EmbeddingRequest:
    """Embedding request."""
    model: str
    input: str | list[str]


@dataclass
class EmbeddingResponse:
    """Embedding response."""
    embeddings: list[list[float]]
    model: str
    input_tokens: int


class Provider(ABC):
    """
    Abstract Provider interface.

    Each concrete provider declares its capabilities, then implements
    the corresponding methods. Calling an unsupported method raises
    VelaError with code LLM_CAPABILITY_UNSUPPORTED.
    """

    name: str  # "openai" | "groq" | "anthropic" | ...
    capabilities: set[ProviderCapability]

    @abstractmethod
    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion. Used for guard/reranker/lightweight/judge/verify/vision."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, req: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Streaming completion. Used for generator (RAG).

        Yields StreamChunk objects. Token chunks have `delta` set; the final
        chunk (when the provider supports it) has `usage` set so callers can
        log cost-tracking metrics accurately.
        """
        raise NotImplementedError

    @abstractmethod
    async def embed(self, req: EmbeddingRequest) -> EmbeddingResponse:
        """Embedding. Only embedder-capable providers implement; others raise."""
        raise NotImplementedError

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities
