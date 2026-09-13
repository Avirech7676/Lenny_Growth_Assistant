"""Tests for LLM provider abstraction, model switching, offline fallback, and health checks."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel
from app.models.provider import (
    BaseLLMProvider,
    OllamaProvider,
    AnthropicProvider,
    OpenAIProvider,
    FallbackGroundedProvider,
    get_llm_provider,
    check_llm_health,
)

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database tables are initialized."""
    init_db()
    yield

@pytest.fixture
def test_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def test_provider_instantiation_and_model_names():
    """Verify each provider initializes cleanly and reports its active model identifier."""
    ollama = OllamaProvider()
    assert ollama.get_model_name() == settings.OLLAMA_MODEL

    anthropic = AnthropicProvider(api_key="test_key", model="claude-3-5-sonnet-20241022")
    assert anthropic.get_model_name() == "claude-3-5-sonnet-20241022"

    openai = OpenAIProvider(api_key="test_key", model="gpt-4o")
    assert openai.get_model_name() == "gpt-4o"

    fallback = FallbackGroundedProvider()
    assert fallback.get_model_name() == "grounded-synthesizer-v2"
    assert fallback.health_check()["healthy"] is True


def test_runtime_provider_overrides():
    """Verify get_llm_provider factory handles runtime overrides and missing keys gracefully."""
    # When keys are absent, cloud requests must gracefully fallback
    p_anthropic = get_llm_provider("anthropic")
    assert isinstance(p_anthropic, (AnthropicProvider, FallbackGroundedProvider))

    p_openai = get_llm_provider("openai")
    assert isinstance(p_openai, (OpenAIProvider, FallbackGroundedProvider))

    p_fallback = get_llm_provider("fallback")
    assert isinstance(p_fallback, FallbackGroundedProvider)


def test_offline_fallback_resilience():
    """Verify fallback synthesizer generates grounded responses for all modes without network."""
    fb = FallbackGroundedProvider()
    context = "Brian Chesky spoke about running Airbnb like an orchestra."
    history = []

    res_research = fb.generate("Research prompt", "How did Chesky organize?", context, history)
    assert "orchestra" in res_research.lower()

    res_ship30 = fb.generate("Ship 30 for 30 essay", "Write an essay", context, history)
    assert "Pillar 1" in res_ship30

    res_experiment = fb.generate("Growth Experiment with ICE Score", "Design test", context, history)
    assert "Hypothesis" in res_experiment

    res_playbook = fb.generate("Growth Playbook with Acquisition", "Build playbook", context, history)
    assert "Acquisition Loops" in res_playbook


def test_health_llm_endpoint_response():
    """Verify /health/llm returns live provider health and fallback diagnostics."""
    res = client.get("/health/llm")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "degraded")
    assert "provider" in data
    assert "active_model" in data
    assert data["latency_ms"] >= 0.0
    assert data["fallback_ready"] is True
    assert "fallback_provider" in data


def test_per_request_override_via_api(test_db):
    """Verify API accepts provider_override in MessageCreate and generates valid response."""
    session = SessionModel(title="Override Test Session")
    test_db.add(session)
    test_db.commit()

    # Override: anthropic
    r1 = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "What was Brian Chesky's orchestra metaphor for Airbnb's product roadmap?",
            "mode": "research",
            "provider_override": "anthropic",
        },
    )
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["role"] == "assistant"
    assert len(d1["citations"]) > 0

    # Override: openai
    r2 = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Explain Shreyas Doshi's LNO framework for ruthless product prioritization.",
            "mode": "research",
            "provider_override": "openai",
        },
    )
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2["role"] == "assistant"
    assert len(d2["citations"]) > 0
