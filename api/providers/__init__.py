"""
Vela Model Provider abstraction layer.

Per PRD §2.1 v1.4 + ADR 005:
- OpenAI is the default provider for all 9 task layers (Phase 0 ship state)
- Groq is framework-ready, Phase 1B activation for Lightweight/Guard/Reranker
- 19 env vars: 9 task layers × 2 (provider + model) + 1 generator fallback model

Usage:
    from api.providers import get_generator_provider
    provider = get_generator_provider()
    response = await provider.generate(...)
"""

from api.providers.base import Provider, ProviderCapability
from api.providers.errors import VelaError, VelaErrorCode
from api.providers.factory import (
    get_generator_provider,
    get_guard_provider,
    get_reranker_provider,
    get_lightweight_provider,
    get_research_judge_provider,
    get_explain_judge_provider,
    get_vision_provider,
    get_verify_provider,
    get_embedder_provider,
)
from api.providers.openai_provider import OpenAIProvider
from api.providers.groq_provider import GroqProvider

__all__ = [
    "Provider",
    "ProviderCapability",
    "VelaError",
    "VelaErrorCode",
    "OpenAIProvider",
    "GroqProvider",
    "get_generator_provider",
    "get_guard_provider",
    "get_reranker_provider",
    "get_lightweight_provider",
    "get_research_judge_provider",
    "get_explain_judge_provider",
    "get_vision_provider",
    "get_verify_provider",
    "get_embedder_provider",
]
