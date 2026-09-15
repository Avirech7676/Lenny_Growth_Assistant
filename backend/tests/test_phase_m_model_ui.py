"""
Tests for Phase M: Frontend Model Platform UI & API Integration.
Verifies /api/v1/models contract, dynamic model discovery endpoint,
tools schema catalog, and streaming telemetry payloads for frontend consumption.
"""

import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def test_models_v1_and_root_endpoints():
    """Verify both /api/v1/models and /api/models return full registered catalog."""
    res_v1 = client.get("/api/v1/models")
    res_root = client.get("/api/models")

    assert res_v1.status_code == 200
    assert res_root.status_code == 200

    data_v1 = res_v1.json()
    data_root = res_root.json()

    assert "models" in data_v1
    assert "count" in data_v1
    assert data_v1["count"] >= 5
    assert data_v1["count"] == data_root["count"]

    # Verify model schema fields expected by frontend Header & ChatInput
    sample_model = data_v1["models"][0]
    assert "model_id" in sample_model
    assert "provider" in sample_model
    assert "display_name" in sample_model
    assert "context_window" in sample_model
    assert "is_available" in sample_model


def test_models_filtering_available_only():
    """Verify available_only query param correctly filters to online models."""
    res = client.get("/api/v1/models?available_only=true")
    assert res.status_code == 200
    data = res.json()

    models = data.get("models", [])
    assert len(models) >= 1

    for m in models:
        assert m["is_available"] is True


def test_models_discover_post_endpoint():
    """Verify POST /api/v1/models/discover executes discovery and returns available models."""
    res = client.post("/api/v1/models/discover")
    assert res.status_code == 200
    data = res.json()

    assert data.get("status") == "success"
    assert "discovered_count" in data
    assert "providers" in data
    assert "available_models" in data
    assert len(data["available_models"]) >= 1


def test_tools_list_endpoint():
    """Verify GET /api/tools provides tool specs for the UI and orchestrator."""
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()

    assert "tools" in data
    tools = data["tools"]
    assert len(tools) >= 3

    tool_names = [t.get("name") for t in tools]
    assert "calculator" in tool_names or "python_sandbox" in tool_names or "web_search" in tool_names


def test_streaming_early_model_and_metrics_telemetry():
    """Verify SSE stream emits early model event and rich metrics HUD payload for frontend UI."""
    session_res = client.post("/api/v1/sessions", json={"title": "Phase M Telemetry Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json={
            "content": "What is the LNO framework by Shreyas Doshi?",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res.status_code == 200

    events = []
    for line in res.text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass

    event_map = {e.get("event"): e for e in events if e.get("event")}

    # 1. Early model event verification
    assert "model" in event_map, "Missing 'model' SSE event"
    model_evt = event_map["model"]
    assert "model_id" in model_evt
    assert "provider" in model_evt

    # 2. Rich telemetry metrics verification
    assert "metrics" in event_map, "Missing 'metrics' SSE event"
    metrics = event_map["metrics"].get("metrics", {})
    assert "ttft_ms" in metrics
    assert "tokens_per_sec" in metrics
    assert "token_count" in metrics
    assert "total_ms" in metrics
    assert "model" in metrics
    assert "provider" in metrics
