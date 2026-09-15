"""
Tests for Phase G: Dynamic Model Routing & Task-to-Model Affinity.
Verifies quantitative scoring, task-specific routing (coding, deep research, fast response),
user preference precedence, graceful unavailable model fallback, and get_llm_provider integration.
"""

import sys
import os
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.base import LLMProvider, ProviderStatus
from app.models.registry import ModelRegistry, ModelMetadata
from app.models.router import ModelRouter, RoutingDecision
from app.models.provider import ProviderRegistry, get_llm_provider


@pytest.fixture
def custom_router():
    """Create a ModelRouter with a controlled test ModelRegistry."""
    registry = ModelRegistry()
    # Clear default models for isolated scoring tests
    registry._models.clear()

    # 1. High-caliber Coder (Moderate Latency, Low Cost)
    registry.register(ModelMetadata(
        provider="ollama",
        model_id="deepseek-coder-test",
        display_name="DeepSeek Coder Test",
        capabilities=["coding", "debugging"],
        context_window=32768,
        supports_tools=False,
        supports_web=False,
        supports_vision=False,
        supports_code=True,
        supports_streaming=True,
        supports_reasoning=True,
        coding_suitability=0.96,
        reasoning_suitability=0.88,
        relative_cost="free",
        relative_latency="moderate",
        availability=True,
        status=ProviderStatus.HEALTHY.value,
    ))

    # 2. Ultra-Fast Generalist (Ultra-Fast, Low Context)
    registry.register(ModelMetadata(
        provider="groq",
        model_id="fast-llama-test",
        display_name="Fast Llama Test",
        capabilities=["chat", "fast_response", "general_qa"],
        context_window=8192,
        supports_tools=True,
        supports_web=True,
        supports_vision=False,
        supports_code=True,
        supports_streaming=True,
        supports_reasoning=False,
        coding_suitability=0.78,
        reasoning_suitability=0.75,
        relative_cost="low",
        relative_latency="ultra_fast",
        availability=True,
        status=ProviderStatus.HEALTHY.value,
    ))

    # 3. Deep Research & Massive Context Engine
    registry.register(ModelMetadata(
        provider="gemini",
        model_id="deep-gemini-test",
        display_name="Deep Gemini Test",
        capabilities=["deep_research", "research", "multimodal"],
        context_window=2000000,
        supports_tools=True,
        supports_web=True,
        supports_vision=True,
        supports_code=True,
        supports_streaming=True,
        supports_reasoning=True,
        coding_suitability=0.85,
        reasoning_suitability=0.98,
        relative_cost="medium",
        relative_latency="fast",
        availability=True,
        status=ProviderStatus.HEALTHY.value,
    ))

    # 4. Offline / Unavailable Model
    registry.register(ModelMetadata(
        provider="openai",
        model_id="offline-o3-test",
        display_name="Offline O3 Test",
        capabilities=["reasoning"],
        context_window=128000,
        supports_tools=True,
        supports_web=False,
        supports_vision=False,
        supports_code=True,
        supports_streaming=True,
        supports_reasoning=True,
        coding_suitability=0.95,
        reasoning_suitability=0.98,
        relative_cost="high",
        relative_latency="slow",
        availability=False,  # Offline!
        status=ProviderStatus.NOT_CONFIGURED.value,
    ))

    # 5. Deterministic Fallback Anchor
    registry.register(ModelMetadata(
        provider="fallback",
        model_id="grounded-synthesizer-v2",
        display_name="Grounded Synthesizer",
        capabilities=["offline_fallback"],
        context_window=16384,
        supports_tools=True,
        supports_web=True,
        supports_vision=False,
        supports_code=True,
        supports_streaming=True,
        supports_reasoning=False,
        coding_suitability=0.80,
        reasoning_suitability=0.80,
        relative_cost="free",
        relative_latency="ultra_fast",
        availability=True,
        status=ProviderStatus.HEALTHY.value,
    ))

    router = ModelRouter()
    router.registry = registry
    return router


def test_coding_query_affinity_routing(custom_router):
    """Verify coding tasks route to the model with highest coding suitability."""
    decision = custom_router.route(task_type="coding", user_preference="auto")
    assert decision.model_id == "deepseek-coder-test"
    assert decision.provider == "ollama"
    assert "coding" in decision.rationale.lower()


def test_deep_research_affinity_routing(custom_router):
    """Verify deep research tasks route to the model with highest reasoning suitability and context window."""
    decision = custom_router.route(task_type="deep_research", user_preference="auto")
    assert decision.model_id == "deep-gemini-test"
    assert decision.provider == "gemini"
    assert "deep_research" in decision.rationale.lower()


def test_low_latency_affinity_routing(custom_router):
    """Verify fast_response / low_latency tasks route to the ultra-fast low-latency model."""
    decision = custom_router.route(task_type="general_qa", low_latency=True, user_preference="auto")
    assert decision.model_id == "fast-llama-test"
    assert decision.provider == "groq"
    assert "ultra_fast" in decision.rationale.lower()


def test_massive_context_affinity_routing(custom_router):
    """Verify very large token requests (>120k tokens) route to million-token context models."""
    decision = custom_router.route(task_type="general_qa", context_tokens=250000, user_preference="auto")
    assert decision.model_id == "deep-gemini-test"
    assert decision.metadata.context_window >= 1000000


def test_explicit_user_preference_precedence(custom_router):
    """Verify explicit user selection overrides task affinity auto-routing."""
    # User selects the fast model even though task is coding
    decision = custom_router.route(task_type="coding", user_preference="fast-llama-test")
    assert decision.model_id == "fast-llama-test"
    assert "Explicit user model selection" in decision.rationale


def test_unavailable_model_graceful_fallback(custom_router):
    """Verify that when a user selects an unavailable model, router falls back to best available substitute."""
    decision = custom_router.route(task_type="coding", user_preference="offline-o3-test")
    # offline-o3-test has availability=False, so router should gracefully auto-route to deepseek-coder-test
    assert decision.model_id == "deepseek-coder-test"
    assert decision.provider == "ollama"


def test_score_model_constraints(custom_router):
    """Verify hard constraints: vision requirement and context window limits."""
    gemini_m = custom_router.registry.get("deep-gemini-test")
    llama_m = custom_router.registry.get("fast-llama-test")

    # Vision requirement: Gemini supports vision, Llama does not
    score_gemini_vis = custom_router.score_model(gemini_m, requires_vision=True)
    assert score_gemini_vis > 0.0
    score_llama_vis = custom_router.score_model(llama_m, requires_vision=True)
    assert score_llama_vis == -1.0  # Rejected

    # Context window: request 50k tokens -> Llama (8k) rejected, Gemini (2M) accepted
    score_gemini_ctx = custom_router.score_model(gemini_m, context_tokens=50000)
    assert score_gemini_ctx > 0.0
    score_llama_ctx = custom_router.score_model(llama_m, context_tokens=50000)
    assert score_llama_ctx == -1.0  # Rejected


def test_get_llm_provider_integration():
    """Verify get_llm_provider factory routes through ModelRouter and returns correct Provider instance."""
    # Test default/auto routing
    p_auto = get_llm_provider(override="auto", task_type="general_qa")
    assert isinstance(p_auto, LLMProvider)
    assert p_auto.get_model_name() != ""

    # Test explicit model override
    p_gemini_lite = get_llm_provider(override="gemini-3.5-flash-lite")
    assert isinstance(p_gemini_lite, LLMProvider)
    assert p_gemini_lite.get_model_name() == "gemini-3.5-flash-lite"
