"""
Tests for Phase E: Dynamic Provider Abstraction (LLMProvider, ProviderRegistry).
Verifies custom provider registration, dynamic model binding, model-to-provider resolution,
capability inspection, and isolation reset.
"""

import sys
import os
import pytest
from typing import Dict, Any, Generator, Union

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.base import LLMProvider, LLMRequest, LLMResponse, ProviderStatus
from app.models.provider import (
    ProviderRegistry,
    GeminiProvider,
    OpenAIProvider,
    AnthropicProvider,
    GroqProvider,
    OllamaProvider,
    FallbackGroundedProvider,
)


class MockCustomProvider(LLMProvider):
    """Custom mock provider implementation for registry testing."""

    def __init__(self, model: str = "mock-model-v1"):
        self.model = model

    def get_model_name(self) -> str:
        return self.model

    def get_provider_id(self) -> str:
        return "mock"

    def health_check(self) -> Dict[str, Any]:
        return {"status": ProviderStatus.HEALTHY.value, "healthy": True, "provider": "mock"}

    def generate(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> LLMResponse:
        return LLMResponse(content="Mock dynamic response", model=self.model, provider="mock")

    def generate_stream(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> Generator[str, None, None]:
        yield "Mock "
        yield "stream"


def test_custom_provider_registration():
    """Verify custom providers can be dynamically registered with aliases."""
    mock_inst = MockCustomProvider(model="custom-gpt-test")
    ProviderRegistry.register("mock_ai", mock_inst, aliases=["mock-v1", "mock-legacy"])

    # Fetch by primary name
    p1 = ProviderRegistry.get("mock_ai")
    assert p1 is mock_inst
    assert p1.get_model_name() == "custom-gpt-test"

    # Fetch by alias
    p2 = ProviderRegistry.get("mock-v1")
    assert p2 is mock_inst

    # Verify presence in list_providers
    providers = ProviderRegistry.list_providers()
    assert "mock_ai" in providers


def test_get_for_model_dynamic_binding():
    """Verify get_for_model instantiates or reconfigures providers for specific target models."""
    p_flash = ProviderRegistry.get_for_model("gemini", "gemini-3.5-flash-lite")
    assert isinstance(p_flash, GeminiProvider)
    assert p_flash.get_model_name() == "gemini-3.5-flash-lite"

    p_lite = ProviderRegistry.get_for_model("gemini", "gemini-3.1-flash-lite")
    assert isinstance(p_lite, GeminiProvider)
    assert p_lite.get_model_name() == "gemini-3.1-flash-lite"

    # Verify instances with different models are distinct
    assert p_flash is not p_lite


def test_get_provider_for_model_resolution():
    """Verify automatic model identifier resolution to correct parent provider."""
    # Registered models
    p_gemini = ProviderRegistry.get_provider_for_model("gemini-3.5-flash")
    assert isinstance(p_gemini, GeminiProvider)
    assert p_gemini.get_model_name() == "gemini-3.5-flash"

    p_openai = ProviderRegistry.get_provider_for_model("gpt-4o")
    assert isinstance(p_openai, OpenAIProvider)
    assert p_openai.get_model_name() == "gpt-4o"

    p_claude = ProviderRegistry.get_provider_for_model("claude-3-5-sonnet-latest")
    assert isinstance(p_claude, AnthropicProvider)

    # Heuristic resolution for unregistered models
    p_gpt_custom = ProviderRegistry.get_provider_for_model("gpt-4.5-preview")
    assert isinstance(p_gpt_custom, OpenAIProvider)
    assert p_gpt_custom.get_model_name() == "gpt-4.5-preview"


def test_provider_capability_inspection():
    """Verify LLMProvider feature inspection and is_configured status."""
    gemini = ProviderRegistry.get("gemini")
    assert gemini.is_configured() is True
    assert gemini.supports_feature("streaming") is True
    assert gemini.supports_feature("tools") is True
    assert gemini.supports_feature("structured_output") is True

    fallback = ProviderRegistry.get("fallback")
    assert fallback.is_configured() is True
    assert fallback.get_provider_id() == "fallback"


def test_provider_registry_reset():
    """Verify registry reset clears dynamic registrations cleanly."""
    temp_mock = MockCustomProvider("temp-model")
    ProviderRegistry.register("temp_vendor", temp_mock)
    assert "temp_vendor" in ProviderRegistry.list_providers()

    ProviderRegistry.reset()
    assert "temp_vendor" not in ProviderRegistry.list_providers()
    # Standard providers must still be accessible via auto-instantiation
    assert isinstance(ProviderRegistry.get("gemini"), GeminiProvider)
