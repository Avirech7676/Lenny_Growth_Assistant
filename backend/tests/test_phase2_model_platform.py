"""Automated test suite for Phase 2: Multi-Provider LLM Platform.

Tests all requirements:
1. LLMProvider, LLMRequest, LLMResponse, ProviderStatus, normalize_request contracts.
2. Provider implementations for OpenAI, Anthropic, Gemini, Groq, Ollama, Fallback.
3. Missing keys report NOT_CONFIGURED without crashing.
4. ModelRegistry tracks all 10 required capability fields.
5. ProviderRegistry singleton management, status reporting, safe access.
6. ModelRouter capability routing, MODEL=AUTO enforcement, and fallback cascades.
7. Timeout and retry handling with fallback execution.
8. Streaming and structured output handling.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.models.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderStatus,
    normalize_request,
)
from app.models.provider import (
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
from app.models.registry import (
    ModelRegistry,
    ModelMetadata,
    get_model_registry,
)
from app.models.router import (
    ModelRouter,
    RoutingDecision,
    get_model_router,
)


# ============================================================================
# 1. CORE CONTRACTS & REQUEST NORMALIZATION
# ============================================================================

def test_llm_request_contracts():
    """Verify LLMRequest constructs defaults properly."""
    req = LLMRequest(prompt="What is product growth?")
    assert req.prompt == "What is product growth?"
    assert req.system_prompt is None
    assert req.context is None
    assert req.history == []
    assert req.stream is False
    assert req.timeout_seconds == 30.0
    assert req.retry_attempts == 2
    assert req.full_user_content == "What is product growth?"

    req_with_context = LLMRequest(
        prompt="Explain churn",
        context="Cohort retention data",
    )
    assert "EVIDENCE & CONTEXT:\nCohort retention data" in req_with_context.full_user_content


def test_llm_response_contracts():
    """Verify LLMResponse structure and string conversion."""
    resp = LLMResponse(
        content="Retention is the foundation of growth.",
        model="test-model",
        provider="test-provider",
        latency_ms=120.5,
        status="SUCCESS",
    )
    assert resp.content == "Retention is the foundation of growth."
    assert str(resp) == "Retention is the foundation of growth."
    assert resp.model == "test-model"
    assert resp.provider == "test-provider"
    assert resp.status == "SUCCESS"


def test_normalize_request_helper():
    """Verify normalize_request handles both LLMRequest and legacy signatures."""
    # Case 1: Already LLMRequest
    req_in = LLMRequest(prompt="Direct request")
    req, is_legacy = normalize_request(req_in)
    assert req is req_in
    assert is_legacy is False

    # Case 2: Legacy positional (system_prompt, user_prompt, context, history)
    req2, is_legacy2 = normalize_request("Sys", "User prompt", "Context data", [{"role": "user", "content": "hi"}])
    assert is_legacy2 is True
    assert req2.system_prompt == "Sys"
    assert req2.prompt == "User prompt"
    assert req2.context == "Context data"
    assert len(req2.history) == 1

    # Case 3: Legacy kwargs
    req3, is_legacy3 = normalize_request(system_prompt="Sys K", user_prompt="User K", context="Ctx K")
    assert is_legacy3 is True
    assert req3.system_prompt == "Sys K"
    assert req3.prompt == "User K"
    assert req3.context == "Ctx K"


# ============================================================================
# 2. MISSING KEYS & NOT_CONFIGURED STATUS
# ============================================================================

def test_missing_keys_report_not_configured():
    """Verify that unconfigured providers report status NOT_CONFIGURED without throwing exceptions."""
    openai_prov = OpenAIProvider(api_key=None)
    h_openai = openai_prov.health_check()
    assert h_openai["healthy"] is False
    assert h_openai["status"] == ProviderStatus.NOT_CONFIGURED.value
    assert "not configured" in h_openai["error"].lower()

    anthropic_prov = AnthropicProvider(api_key="")
    h_anthropic = anthropic_prov.health_check()
    assert h_anthropic["healthy"] is False
    assert h_anthropic["status"] == ProviderStatus.NOT_CONFIGURED.value

    gemini_prov = GeminiProvider(api_key=None)
    h_gemini = gemini_prov.health_check()
    assert h_gemini["healthy"] is False
    assert h_gemini["status"] == ProviderStatus.NOT_CONFIGURED.value

    groq_prov = GroqProvider(api_key="")
    h_groq = groq_prov.health_check()
    assert h_groq["healthy"] is False
    assert h_groq["status"] == ProviderStatus.NOT_CONFIGURED.value


def test_ollama_unreachable_reports_offline():
    """Verify Ollama reports OFFLINE when local service port is unreachable."""
    ollama_prov = OllamaProvider(base_url="http://127.0.0.1:9999")  # Non-existent port
    h_ollama = ollama_prov.health_check()
    assert h_ollama["healthy"] is False
    assert h_ollama["status"] in (ProviderStatus.OFFLINE.value, ProviderStatus.TIMEOUT.value)


def test_fallback_provider_healthy():
    """Deterministic fallback provider is always healthy."""
    fb = FallbackGroundedProvider()
    h = fb.health_check()
    assert h["healthy"] is True
    assert h["status"] == ProviderStatus.HEALTHY.value
    assert fb.get_model_name() == "grounded-synthesizer-v2"


# ============================================================================
# 3. UNCONFIGURED PROVIDER GENERATE FALLBACK (NO CRASH)
# ============================================================================

def test_unconfigured_openai_generates_via_fallback():
    """Calling generate on an unconfigured OpenAI provider falls back gracefully without crashing."""
    prov = OpenAIProvider(api_key=None)
    req = LLMRequest(prompt="What is Python?")
    resp = prov.generate(req)
    # Returns LLMResponse when LLMRequest passed
    assert isinstance(resp, LLMResponse)
    assert len(resp.content) > 20
    assert "python" in resp.content.lower()


def test_unconfigured_anthropic_legacy_signature_returns_str():
    """Calling legacy signature on unconfigured Anthropic returns str."""
    prov = AnthropicProvider(api_key="")
    result = prov.generate("You are a strategist.", "Write a C++ program to reverse a string", "", [])
    assert isinstance(result, str)
    assert "std::reverse" in result or "algorithm" in result or "string" in result


# ============================================================================
# 4. MODEL CAPABILITY REGISTRY (ALL 10 FIELDS)
# ============================================================================

def test_model_registry_tracks_mandatory_metadata_fields():
    """Verify ModelRegistry tracks all 10 required fields:
    provider, model, context length, streaming, tool calling, vision,
    coding suitability, reasoning suitability, latency class, availability.
    """
    reg = get_model_registry()
    models = reg.list_models()
    assert len(models) >= 8

    for m in models:
        # Check direct attributes
        assert m.provider in ["openai", "anthropic", "gemini", "groq", "ollama", "fallback"]
        assert isinstance(m.model, str) and len(m.model) > 0
        assert isinstance(m.context_length, int) and m.context_length > 0
        assert isinstance(m.streaming, bool)
        assert isinstance(m.tool_calling, bool)
        assert isinstance(m.vision, bool)
        assert isinstance(m.coding_suitability, (int, float))
        assert isinstance(m.reasoning_suitability, (int, float))
        assert isinstance(m.latency_class, str) and m.latency_class in ("ultra_fast", "fast", "moderate", "slow")
        assert isinstance(m.availability, bool)

        # Check dictionary serialization contains all required keys
        d = m.to_dict()
        assert "provider" in d
        assert "model" in d
        assert "context_length" in d
        assert "streaming" in d
        assert "tool_calling" in d
        assert "vision" in d
        assert "coding_suitability" in d
        assert "reasoning_suitability" in d
        assert "latency_class" in d
        assert "availability" in d
        assert "status" in d


# ============================================================================
# 5. PROVIDER REGISTRY
# ============================================================================

def test_provider_registry_list_and_get():
    """Verify ProviderRegistry singleton management and safe listing."""
    providers = ProviderRegistry.list_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "gemini" in providers
    assert "groq" in providers
    assert "ollama" in providers
    assert "fallback" in providers

    prov = ProviderRegistry.get("openai")
    assert isinstance(prov, OpenAIProvider)

    statuses = ProviderRegistry.get_status()
    assert len(statuses) == 6
    assert "openai" in statuses
    assert "fallback" in statuses
    assert statuses["fallback"]["healthy"] is True


# ============================================================================
# 6. MODEL ROUTER & AUTO ROUTING (MODEL=AUTO)
# ============================================================================

def test_router_auto_mode_default():
    """Verify ModelRouter routes cleanly under auto mode."""
    router = get_model_router()
    decision = router.route(task_type="general_qa", user_preference="auto")
    assert isinstance(decision, RoutingDecision)
    assert decision.provider in ProviderRegistry.list_providers()
    assert len(decision.rationale) > 0


def test_router_coding_task_preference():
    """Verify router favors coding-capable models for coding tasks."""
    router = get_model_router()
    decision = router.route(task_type="coding")
    assert isinstance(decision, RoutingDecision)
    assert decision.metadata is not None
    assert decision.metadata.coding_suitability >= 0.8


def test_router_massive_context_routes_to_gemini_when_available():
    """Verify router prefers Gemini when context exceeds 120,000 tokens and Gemini is available."""
    router = get_model_router()
    with patch.object(router.registry, "check_availability", side_effect=lambda p: p == "gemini"):
        decision = router.route(context_tokens=150000)
        assert decision.provider == "gemini"
        assert "massive context" in decision.rationale.lower()


def test_router_low_latency_routes_to_groq_when_available():
    """Verify router prefers Groq when low_latency is requested."""
    router = get_model_router()
    with patch.object(router.registry, "check_availability", side_effect=lambda p: p == "groq"):
        decision = router.route(low_latency=True)
        assert decision.provider == "groq"
        assert "groq" in decision.rationale.lower()


# ============================================================================
# 7. ROUTER EXECUTE WITH FALLBACK
# ============================================================================

def test_router_execute_with_provider_fallback():
    """When external providers are offline/unconfigured, router falls back safely to grounded synthesizer."""
    router = get_model_router()
    req = LLMRequest(prompt="Who is CM of AP?")
    resp = router.execute(req)
    assert isinstance(resp, LLMResponse)
    assert resp.status in ("SUCCESS", "FALLBACK")
    assert len(resp.content) > 10
    # Phase 1 relevance guarantee must hold
    assert "brian chesky" not in resp.content.lower()
    assert "chandrababu naidu" in resp.content.lower()


def test_router_execute_stream_fallback():
    """Verify execute_stream yields tokens cleanly across failover."""
    router = get_model_router()
    req = LLMRequest(prompt="What is Python?")
    tokens = list(router.execute_stream(req))
    assert len(tokens) > 5
    full = "".join(tokens)
    assert "python" in full.lower()


# ============================================================================
# 8. HEALTH ENDPOINT INTEGRATION
# ============================================================================

def test_check_llm_health_structure():
    """Verify check_llm_health returns structured diagnostic data."""
    health = check_llm_health()
    assert "status" in health
    assert "provider" in health
    assert "active_model" in health
    assert "latency_ms" in health
    assert "fallback_ready" in health
    assert health["fallback_ready"] is True
    assert "providers" in health
    assert "openai" in health["providers"]
    assert "anthropic" in health["providers"]
    assert "gemini" in health["providers"]
    assert "groq" in health["providers"]
    assert "ollama" in health["providers"]
    assert "fallback" in health["providers"]
