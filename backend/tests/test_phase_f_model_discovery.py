"""
Tests for Phase F: Dynamic Model Discovery.
Verifies dynamic query capability for Gemini API, Ollama /api/tags, Groq, OpenAI,
and FastAPI discovery endpoints (/api/models?discover=true, POST /api/models/discover).
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.registry import ModelRegistry, get_model_registry
from app.core.config import settings
from fastapi.testclient import TestClient
from app.main import app


def test_gemini_discovery_active():
    """Verify live/configured Gemini discovery enumerates models and registers them."""
    registry = ModelRegistry()
    if settings.GEMINI_API_KEY:
        discovered = registry._discover_gemini()
        assert isinstance(discovered, list)
        if len(discovered) > 0:
            model_ids = [m.model_id for m in discovered]
            # Ensure at least one flash or pro model was registered
            assert any("flash" in m.lower() or "pro" in m.lower() for m in model_ids)
            # Verify registered models exist in registry.list_models()
            registered = registry.list_models(provider="gemini")
            assert len(registered) >= len(discovered)
    else:
        pytest.skip("GEMINI_API_KEY not configured for live test")


def test_mock_ollama_discovery():
    """Verify dynamic discovery of local Ollama models via /api/tags."""
    registry = ModelRegistry()
    mock_tags = {
        "models": [
            {"name": "deepseek-coder-v2:16b"},
            {"name": "llama3.2:3b"},
            {"name": "qwen2.5:7b"},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_tags

    with patch("requests.get", return_value=mock_resp):
        discovered = registry._discover_ollama()
        assert len(discovered) == 3

        coder = registry.get_model("deepseek-coder-v2:16b")
        assert coder is not None
        assert coder.provider == "ollama"
        assert coder.supports_code is True
        assert coder.coding_suitability >= 0.90
        assert "coding" in coder.capabilities

        general = registry.get_model("llama3.2:3b")
        assert general is not None
        assert general.provider == "ollama"
        assert general.coding_suitability < 0.90


def test_mock_groq_discovery():
    """Verify dynamic discovery of Groq models via /openai/v1/models."""
    registry = ModelRegistry()
    mock_models = {
        "data": [
            {"id": "llama-3.3-70b-versatile", "context_window": 128000},
            {"id": "mixtral-8x7b-32768", "context_window": 32768},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_models

    with patch.object(settings, "GROQ_API_KEY", "gsk_test_key"):
        with patch("requests.get", return_value=mock_resp):
            discovered = registry._discover_groq()
            assert len(discovered) == 2

            m = registry.get_model("llama-3.3-70b-versatile")
            assert m is not None
            assert m.provider == "groq"
            assert m.context_window == 128000
            assert m.supports_streaming is True


def test_mock_openai_discovery():
    """Verify dynamic discovery of OpenAI models via /v1/models."""
    registry = ModelRegistry()
    mock_models = {
        "data": [
            {"id": "gpt-4o-2024-11-20"},
            {"id": "o3-mini-2025-01-31"},
            {"id": "text-embedding-3-small"},  # Should be excluded
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_models

    with patch.object(settings, "OPENAI_API_KEY", "sk-test-key"):
        with patch("requests.get", return_value=mock_resp):
            discovered = registry._discover_openai()
            assert len(discovered) == 2
            ids = [m.model_id for m in discovered]
            assert "gpt-4o-2024-11-20" in ids
            assert "o3-mini-2025-01-31" in ids
            assert "text-embedding-3-small" not in ids


def test_discover_live_models_orchestrator():
    """Verify discover_live_models orchestrates multi-provider discovery gracefully."""
    registry = ModelRegistry()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "mistral:latest"}]}

    with patch("requests.get", return_value=mock_resp):
        res = registry.discover_live_models(provider="ollama")
        assert "discovered_count" in res
        assert "providers" in res
        assert "ollama" in res["providers"]
        assert "mistral:latest" in res["providers"]["ollama"]


def test_api_endpoints_discovery():
    """Verify GET /api/models?discover=true and POST /api/models/discover API routes."""
    client = TestClient(app)

    # 1. GET /api/models?discover=true
    resp_get = client.get("/api/models?discover=true")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "models" in data_get
    assert "count" in data_get
    assert data_get["count"] > 0

    # 2. POST /api/models/discover
    resp_post = client.post("/api/models/discover")
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["status"] == "success"
    assert "discovered_count" in data_post
    assert "providers" in data_post
    assert "available_models" in data_post
    assert "total_available" in data_post
    assert data_post["total_available"] > 0
