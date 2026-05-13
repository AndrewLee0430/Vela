"""
Unit tests for api.providers factory + provider swap.

These tests do NOT make real LLM API calls. They verify:
- Default factory behavior returns OpenAIProvider for all 9 task layers
- Env var override switches GroqProvider for supported capabilities
- Groq raises LLM_CAPABILITY_UNSUPPORTED for embedder + vision
- Unknown provider name raises VelaError
- Defaults match PRD §2.1 v1.4 表格

Per PHASE A acceptance: env var swap mechanism proves out before
touching any existing backend file.
"""

from __future__ import annotations
import pytest

from api.providers import (
    OpenAIProvider,
    GroqProvider,
    VelaError,
    VelaErrorCode,
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
from api.providers.factory import DEFAULTS, GENERATOR_FALLBACK_DEFAULT


ALL_FACTORIES = [
    ("generator",      get_generator_provider,      "gpt-4.1"),
    ("guard",          get_guard_provider,          "gpt-4.1-mini"),
    ("reranker",       get_reranker_provider,       "gpt-4o-mini"),
    ("lightweight",    get_lightweight_provider,    "gpt-4.1-mini"),
    ("research_judge", get_research_judge_provider, "gpt-4.1-mini"),
    ("explain_judge",  get_explain_judge_provider,  "gpt-4.1"),
    ("vision",         get_vision_provider,         "gpt-4o"),
    ("verify",         get_verify_provider,         "gpt-4.1-mini"),
    ("embedder",       get_embedder_provider,       "text-embedding-3-small"),
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove all provider env vars so tests see DEFAULTS."""
    keys = [
        "GENERATOR_PROVIDER", "GENERATOR_MODEL", "GENERATOR_FALLBACK_MODEL",
        "GUARD_PROVIDER", "GUARD_MODEL",
        "RERANKER_PROVIDER", "RERANKER_MODEL",
        "LIGHTWEIGHT_PROVIDER", "LIGHTWEIGHT_MODEL",
        "RESEARCH_JUDGE_PROVIDER", "RESEARCH_JUDGE_MODEL",
        "EXPLAIN_JUDGE_PROVIDER", "EXPLAIN_JUDGE_MODEL",
        "VISION_PROVIDER", "VISION_MODEL",
        "VERIFY_PROVIDER", "VERIFY_MODEL",
        "EMBEDDER_PROVIDER", "EMBEDDER_MODEL",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)


# ---- Defaults ----

@pytest.mark.parametrize("task,factory,expected_model", ALL_FACTORIES)
def test_default_provider_is_openai(task, factory, expected_model):
    binding = factory()
    assert isinstance(binding.provider, OpenAIProvider), f"task={task} default not OpenAI"
    assert binding.provider.name == "openai"
    assert binding.model == expected_model
    assert binding.task_layer == task


def test_generator_default_fallback_model():
    binding = get_generator_provider()
    assert binding.fallback_model == GENERATOR_FALLBACK_DEFAULT
    assert binding.fallback_model == "gpt-4.1-mini"


def test_non_generator_has_no_fallback():
    for task, factory, _ in ALL_FACTORIES:
        if task == "generator":
            continue
        binding = factory()
        assert binding.fallback_model is None, f"task={task} unexpectedly has fallback_model"


def test_defaults_match_prd_v14_table():
    """DEFAULTS dict in factory.py matches PRD §2.1 v1.4 表格."""
    expected = {
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
    assert DEFAULTS == expected


# ---- Env var swap ----

def test_swap_lightweight_to_groq(monkeypatch):
    monkeypatch.setenv("LIGHTWEIGHT_PROVIDER", "groq")
    monkeypatch.setenv("LIGHTWEIGHT_MODEL", "llama-3.1-8b-instant")
    binding = get_lightweight_provider()
    assert isinstance(binding.provider, GroqProvider)
    assert binding.provider.name == "groq"
    assert binding.model == "llama-3.1-8b-instant"


def test_swap_guard_to_groq(monkeypatch):
    monkeypatch.setenv("GUARD_PROVIDER", "groq")
    monkeypatch.setenv("GUARD_MODEL", "llama-3.1-8b-instant")
    binding = get_guard_provider()
    assert isinstance(binding.provider, GroqProvider)


def test_swap_generator_to_groq_with_custom_fallback(monkeypatch):
    monkeypatch.setenv("GENERATOR_PROVIDER", "groq")
    monkeypatch.setenv("GENERATOR_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("GENERATOR_FALLBACK_MODEL", "llama-3.3-70b-versatile")
    binding = get_generator_provider()
    assert isinstance(binding.provider, GroqProvider)
    assert binding.model == "openai/gpt-oss-120b"
    assert binding.fallback_model == "llama-3.3-70b-versatile"


def test_mixed_providers_per_task(monkeypatch):
    """Different task layers can use different providers simultaneously."""
    monkeypatch.setenv("GENERATOR_PROVIDER", "openai")
    monkeypatch.setenv("GUARD_PROVIDER", "groq")
    monkeypatch.setenv("LIGHTWEIGHT_PROVIDER", "groq")
    monkeypatch.setenv("EMBEDDER_PROVIDER", "openai")

    assert isinstance(get_generator_provider().provider, OpenAIProvider)
    assert isinstance(get_guard_provider().provider, GroqProvider)
    assert isinstance(get_lightweight_provider().provider, GroqProvider)
    assert isinstance(get_embedder_provider().provider, OpenAIProvider)


# ---- Capability checks ----

def test_groq_embedder_unsupported(monkeypatch):
    monkeypatch.setenv("EMBEDDER_PROVIDER", "groq")
    with pytest.raises(VelaError) as exc:
        get_embedder_provider()
    assert exc.value.code == VelaErrorCode.LLM_CAPABILITY_UNSUPPORTED


def test_groq_vision_unsupported(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "groq")
    with pytest.raises(VelaError) as exc:
        get_vision_provider()
    assert exc.value.code == VelaErrorCode.LLM_CAPABILITY_UNSUPPORTED


def test_unknown_provider_name(monkeypatch):
    monkeypatch.setenv("GENERATOR_PROVIDER", "anthropic")
    with pytest.raises(VelaError) as exc:
        get_generator_provider()
    assert exc.value.code == VelaErrorCode.LLM_PROVIDER_UNAVAILABLE


# ---- Capability sets ----

def test_openai_supports_all_capabilities():
    provider = OpenAIProvider()
    from api.providers.base import ProviderCapability
    for cap in ProviderCapability:
        assert provider.supports(cap), f"OpenAI should support {cap.value}"


def test_groq_does_not_support_embedder_or_vision():
    provider = GroqProvider()
    from api.providers.base import ProviderCapability
    assert not provider.supports(ProviderCapability.EMBEDDER)
    assert not provider.supports(ProviderCapability.VISION)
    assert provider.supports(ProviderCapability.GENERATOR)
    assert provider.supports(ProviderCapability.GUARD)
    assert provider.supports(ProviderCapability.LIGHTWEIGHT)
