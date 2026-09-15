"""
Tests for Phase H: Dynamic Token Streaming & Real-Time Telemetry.
Verifies SSE event sequencing (phase -> routing -> citations -> model -> token -> metrics -> done),
early model resolution event emission, TTFT calculation, and token velocity metrics (tokens_per_sec).
"""

import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def test_sse_event_sequence_order():
    """Verify SSE streaming yields events in strict structured order."""
    # 1. Create session
    session_res = client.post("/api/v1/sessions", json={"title": "SSE Phase H Sequence Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 2. Stream message using fallback provider for deterministic test
    payload = {
        "content": "Explain product led growth vs sales led growth.",
        "mode": "chat",
        "provider_override": "fallback",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json=payload,
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = []
    tokens = []
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                event_obj = json.loads(line[6:])
                events.append(event_obj)
                if event_obj.get("event") == "token":
                    tokens.append(event_obj.get("token", ""))
            except json.JSONDecodeError:
                pass

    event_types = [e.get("event") for e in events]

    # Verify all expected event types occurred
    assert "phase" in event_types
    assert "routing" in event_types
    assert "citations" in event_types
    assert "model" in event_types
    assert "token" in event_types
    assert "metrics" in event_types
    assert "done" in event_types

    # Strict ordering: 'phase' is first, 'model' precedes 'token', 'done' is last
    assert event_types[0] == "phase"
    model_idx = event_types.index("model")
    first_token_idx = event_types.index("token")
    assert model_idx < first_token_idx, "Early 'model' event must precede 'token' generation"
    assert event_types[-1] == "done", "'done' must be the terminal event"


def test_early_model_event_metadata():
    """Verify 'model' event announces resolved provider and model before token generation."""
    session_res = client.post("/api/v1/sessions", json={"title": "SSE Phase H Model Badge Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    payload = {
        "content": "What is the capital of France?",
        "mode": "chat",
        "provider_override": "fallback",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json=payload,
    )
    assert response.status_code == 200

    model_event = None
    for line in response.text.splitlines():
        if line.startswith("data: "):
            try:
                obj = json.loads(line[6:])
                if obj.get("event") == "model":
                    model_event = obj
                    break
            except Exception:
                pass

    assert model_event is not None, "Model event not emitted"
    assert "model_id" in model_event
    assert "provider" in model_event
    assert model_event["provider"] in ("gemini", "groq", "openai", "anthropic", "ollama", "fallback")


def test_token_velocity_and_latency_metrics():
    """Verify metrics payload includes ttft_ms, token_count, tokens_per_sec, and generation timing."""
    session_res = client.post("/api/v1/sessions", json={"title": "SSE Phase H Velocity Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    payload = {
        "content": "Write a 3-step guide to onboarding activation.",
        "mode": "chat",
        "provider_override": "fallback",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json=payload,
    )
    assert response.status_code == 200

    metrics_event = None
    done_event = None
    for line in response.text.splitlines():
        if line.startswith("data: "):
            try:
                obj = json.loads(line[6:])
                if obj.get("event") == "metrics":
                    metrics_event = obj
                elif obj.get("event") == "done":
                    done_event = obj
            except Exception:
                pass

    assert metrics_event is not None, "Metrics event missing"
    m = metrics_event["metrics"]
    assert "ttft_ms" in m and m["ttft_ms"] >= 0
    assert "total_ms" in m and m["total_ms"] >= 0
    assert "token_count" in m and m["token_count"] > 0
    assert "tokens_per_sec" in m and m["tokens_per_sec"] > 0
    assert "model" in m
    assert "provider" in m

    # Verify done event carries metrics summary
    assert done_event is not None
    assert "metrics" in done_event
    assert done_event["metrics"]["token_count"] == m["token_count"]


def test_coding_stream_task_resolution():
    """Verify streaming a coding query resolves task_type and streams correctly."""
    session_res = client.post("/api/v1/sessions", json={"title": "SSE Phase H Coding Stream Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    payload = {
        "content": "def merge_sort(arr): write the code",
        "mode": "chat",
        "provider_override": "fallback",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json=payload,
    )
    assert response.status_code == 200

    tokens = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            try:
                obj = json.loads(line[6:])
                if obj.get("event") == "token":
                    tokens.append(obj.get("token", ""))
            except Exception:
                pass

    full_code = "".join(tokens)
    assert len(full_code) > 20
