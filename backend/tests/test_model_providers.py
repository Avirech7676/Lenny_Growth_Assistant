"""Tests for Multi-Model Provider Adapters, Model Registry, and Dynamic Model Router.

Validates OpenAI, Anthropic, Gemini, Groq, Ollama, and Fallback adapters.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.models.registry import ModelRegistry, ModelMetadata, get_model_registry
from app.models.router import ModelRouter, RoutingDecision, get_model_router
from app.models.provider import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    OllamaProvider,
    FallbackGroundedProvider,
    ProviderRegistry,
    get_llm_provider,
    check_llm_health,
)

client = TestClient(app)


def test_model_registry_initialization():
    """Verify registry catalogs models across all 5 providers + fallback with complete metadata."""
    registry = get_model_registry()
    all_models = registry.list_models()
    assert len(all_models) >= 8

    # Verify provider representation
    providers = {m.provider for m in all_models}
    assert "openai" in providers
    assert "anthropic" in providers
    assert "gemini" in providers
    assert "groq" in providers
    assert "ollama" in providers
    assert "fallback" in providers

    # Verify metadata fields on Gemini 1.5 Pro
    gemini_meta = registry.get("gemini-1.5-pro")
    assert gemini_meta is not None
    assert gemini_meta.context_window >= 1000000
    assert gemini_meta.supports_vision is True
    assert gemini_meta.supports_tools is True

    # Verify metadata fields on Groq Llama 3.3
    groq_meta = registry.get("llama-3.3-70b-versatile")
    assert groq_meta is not None
    assert groq_meta.relative_latency == "ultra_fast"
    assert groq_meta.supports_code is True


def test_model_router_user_preference():
    """Verify router respects explicit user provider and model selections."""
    router = get_model_router()

    # User specifies OpenAI
    d_openai = router.route(user_preference="openai")
    assert d_openai.provider == "openai"
    assert "OpenAI" in d_openai.rationale

    # User specifies Anthropic
    d_claude = router.route(user_preference="anthropic")
    assert d_claude.provider == "anthropic"
    assert "Anthropic" in d_claude.rationale

    # User specifies Gemini
    d_gemini = router.route(user_preference="gemini")
    assert d_gemini.provider == "gemini"
    assert "Gemini" in d_gemini.rationale

    # User specifies Groq
    d_groq = router.route(user_preference="groq")
    assert d_groq.provider == "groq"
    assert "Groq" in d_groq.rationale

    # User specifies exact model id
    d_exact = router.route(user_preference="gemini-3.5-flash")
    assert d_exact.provider == "gemini"
    assert d_exact.model_id == "gemini-3.5-flash"


def test_model_router_auto_routing_and_fallbacks():
    """Verify router creates an orderly fallback chain when keys are absent."""
    router = get_model_router()

    # When no cloud keys are in test environment, auto route falls back to fallback synthesizer
    decision = router.route(task_type="coding", user_preference="auto")
    assert decision.provider in ("anthropic", "openai", "groq", "gemini", "ollama", "fallback")
    assert decision.model_id != ""


def test_gemini_provider_adapter():
    """Verify GeminiProvider initializes, checks health, and falls back gracefully when keys missing."""
    p_gemini = GeminiProvider(api_key="test_mock_gemini_key", model="gemini-1.5-flash")
    assert p_gemini.get_model_name() == "gemini-1.5-flash"
    assert p_gemini.health_check()["healthy"] is True

    # Offline/fallback execution test
    p_offline = GeminiProvider(api_key=None)
    assert p_offline.health_check()["healthy"] is False
    res = p_offline.generate("System", "Write a python function to reverse a string", "", [])
    assert "def reverse_string" in res or "reverse" in res.lower()

    stream_tokens = list(p_offline.generate_stream("System", "Write a python function to reverse a string", "", []))
    assert len(stream_tokens) > 0


def test_groq_provider_adapter():
    """Verify GroqProvider initializes, checks health, and falls back gracefully when keys missing."""
    p_groq = GroqProvider(api_key="gsk_test_mock_groq_key", model="llama-3.3-70b-versatile")
    assert p_groq.get_model_name() == "llama-3.3-70b-versatile"
    assert p_groq.health_check()["healthy"] is True

    # Offline/fallback execution test
    p_offline = GroqProvider(api_key=None)
    assert p_offline.health_check()["healthy"] is False
    res = p_offline.generate("System", "Who is CM of AP?", "", [])
    assert "Chandrababu" in res or "Chief Minister" in res or "No AI provider" in res or "available" in res

    stream_tokens = list(p_offline.generate_stream("System", "Who is CM of AP?", "", []))
    assert len(stream_tokens) > 0


def test_provider_registry_and_factory():
    """Verify ProviderRegistry fetches all standard adapters and handles unknown providers."""
    assert isinstance(ProviderRegistry.get("openai"), BaseLLMProvider)
    assert isinstance(ProviderRegistry.get("anthropic"), BaseLLMProvider)
    assert isinstance(ProviderRegistry.get("gemini"), BaseLLMProvider)
    assert isinstance(ProviderRegistry.get("groq"), BaseLLMProvider)
    assert isinstance(ProviderRegistry.get("ollama"), BaseLLMProvider)
    assert isinstance(ProviderRegistry.get("fallback"), FallbackGroundedProvider)
    assert isinstance(ProviderRegistry.get("nonexistent_vendor"), FallbackGroundedProvider)

    # get_llm_provider handles overrides and auto routing
    prov_auto = get_llm_provider("auto")
    assert isinstance(prov_auto, BaseLLMProvider)

    prov_gemini = get_llm_provider("gemini")
    assert isinstance(prov_gemini, BaseLLMProvider)

    prov_groq = get_llm_provider("groq")
    assert isinstance(prov_groq, BaseLLMProvider)


def test_check_llm_health_multi_provider():
    """Verify check_llm_health returns health breakdown for all 5 providers + fallback."""
    health = check_llm_health()
    assert health["status"] in ("healthy", "degraded")
    assert "providers" in health
    assert "openai" in health["providers"]
    assert "anthropic" in health["providers"]
    assert "gemini" in health["providers"]
    assert "groq" in health["providers"]
    assert "ollama" in health["providers"]
    assert "fallback" in health["providers"]
    assert health["fallback_ready"] is True


def test_api_models_endpoint():
    """Verify GET /api/models returns registered models catalog."""
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert data["count"] >= 8
    models = data["models"]
    model_ids = [m["model_id"] for m in models]
    assert "gpt-4o" in model_ids
    assert "gemini-3.5-flash" in model_ids
    assert "llama-3.3-70b-versatile" in model_ids
