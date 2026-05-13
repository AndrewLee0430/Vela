"""
Factory functions — one per task layer per PRD §2.1 v1.4 需求 6.

Each factory reads its task-layer env vars and returns a configured Provider
instance bound to the task-specific model. The Provider singleton pattern is
NOT enforced here; PHASE B+ will refactor callers to cache instances
appropriately.

Defaults baked in: if env var missing, fall back to PRD v1.4 default.
"""

from __future__ import annotations
import os
from dataclasses import dataclass

from api.providers.base import Provider, ProviderCapability
from api.providers.openai_provider import OpenAIProvider
from api.providers.groq_provider import GroqProvider
from api.providers.errors import VelaError, VelaErrorCode


# Defaults per PRD §2.1 v1.4 需求 6 表格
DEFAULTS = {
    "generator":      ("openai", "gpt-4.1"),
    "guard":          ("openai", "gpt-4.1-mini"),
    "reranker":       ("openai", "gpt-4o-mini"),
    "lightweight":    ("openai", "gpt-4.1-mini"),
    "research_judge": ("openai", "gpt-4.1-mini"),
    "explain_judge":  ("openai", "gpt-4.1"),
    "vision":         ("openai", "gpt-4o"),
    "verify":         ("openai", "gpt-4.1-mini"),
    "embedder":       ("openai", "text-embedding-3-small"),
}

# Fallback model for generator (no provider env var — same provider as generator)
GENERATOR_FALLBACK_DEFAULT = "gpt-4.1-mini"


@dataclass
class ProviderBinding:
    """A bound provider + model + (optional) fallback model for a task layer."""
    provider: Provider
    model: str
    fallback_model: str | None = None  # only for generator
    task_layer: str = ""


def _build_provider(name: str) -> Provider:
    """Map provider name string to instance."""
    if name == "openai":
        return OpenAIProvider()
    if name == "groq":
        return GroqProvider()
    raise VelaError(
        VelaErrorCode.LLM_PROVIDER_UNAVAILABLE,
        f"Unknown provider name: {name!r}. Supported: openai, groq.",
    )


def _get_binding(
    task: str,
    provider_env: str,
    model_env: str,
    required_capability: ProviderCapability,
    fallback_env: str | None = None,
) -> ProviderBinding:
    default_provider, default_model = DEFAULTS[task]
    provider_name = os.getenv(provider_env, default_provider)
    model_name = os.getenv(model_env, default_model)
    provider = _build_provider(provider_name)

    if not provider.supports(required_capability):
        raise VelaError(
            VelaErrorCode.LLM_CAPABILITY_UNSUPPORTED,
            f"Provider {provider_name!r} does not support {required_capability.value!r} (task={task}).",
            provider=provider_name,
            model=model_name,
        )

    fallback_model = None
    if fallback_env:
        fallback_model = os.getenv(fallback_env, GENERATOR_FALLBACK_DEFAULT)

    return ProviderBinding(
        provider=provider,
        model=model_name,
        fallback_model=fallback_model,
        task_layer=task,
    )


def get_generator_provider() -> ProviderBinding:
    return _get_binding(
        "generator",
        "GENERATOR_PROVIDER",
        "GENERATOR_MODEL",
        ProviderCapability.GENERATOR,
        fallback_env="GENERATOR_FALLBACK_MODEL",
    )


def get_guard_provider() -> ProviderBinding:
    return _get_binding("guard", "GUARD_PROVIDER", "GUARD_MODEL", ProviderCapability.GUARD)


def get_reranker_provider() -> ProviderBinding:
    return _get_binding("reranker", "RERANKER_PROVIDER", "RERANKER_MODEL", ProviderCapability.RERANKER)


def get_lightweight_provider() -> ProviderBinding:
    return _get_binding("lightweight", "LIGHTWEIGHT_PROVIDER", "LIGHTWEIGHT_MODEL", ProviderCapability.LIGHTWEIGHT)


def get_research_judge_provider() -> ProviderBinding:
    return _get_binding("research_judge", "RESEARCH_JUDGE_PROVIDER", "RESEARCH_JUDGE_MODEL", ProviderCapability.RESEARCH_JUDGE)


def get_explain_judge_provider() -> ProviderBinding:
    return _get_binding("explain_judge", "EXPLAIN_JUDGE_PROVIDER", "EXPLAIN_JUDGE_MODEL", ProviderCapability.EXPLAIN_JUDGE)


def get_vision_provider() -> ProviderBinding:
    return _get_binding("vision", "VISION_PROVIDER", "VISION_MODEL", ProviderCapability.VISION)


def get_verify_provider() -> ProviderBinding:
    return _get_binding("verify", "VERIFY_PROVIDER", "VERIFY_MODEL", ProviderCapability.VERIFY)


def get_embedder_provider() -> ProviderBinding:
    return _get_binding("embedder", "EMBEDDER_PROVIDER", "EMBEDDER_MODEL", ProviderCapability.EMBEDDER)
