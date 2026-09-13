"""Automated API endpoint integration tests for The Lenny Growth Assistant."""

import sys
import os
import uuid
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Verify /health returns 200 and valid schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

def test_health_db_endpoint():
    """Verify /health/db returns active database engine status."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "engine" in data
    assert data["latency_ms"] >= 0.0

def test_health_llm_endpoint():
    """Verify /health/llm reports active provider configuration."""
    response = client.get("/health/llm")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "provider" in data
    assert "active_model" in data

def test_request_telemetry_headers():
    """Verify middleware injects X-Request-ID and X-Response-Time-MS."""
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers

def test_session_crud_and_messages():
    """Verify session creation, retrieval, and message post flow."""
    # 1. Create session
    create_res = client.post(
        "/api/v1/sessions",
        json={"title": "Evaluator Benchmark Session", "metadata": {"test": True}},
    )
    assert create_res.status_code == 201
    session = create_res.json()
    session_id = session["id"]
    assert session["title"] == "Evaluator Benchmark Session"
    assert session["metadata"]["test"] is True

    # 2. List sessions
    list_res = client.get("/api/v1/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["id"] == session_id for s in sessions)

    # 3. Get session details
    detail_res = client.get(f"/api/v1/sessions/{session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == session_id
    assert detail["message_count"] == 0

    # 4. Post message to session
    msg_res = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "What is the LNO framework?", "mode": "research"},
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["session_id"] == session_id
    assert msg_data["role"] == "assistant"
    assert "citations" in msg_data

    # 5. Fetch message history
    history_res = client.get(f"/api/v1/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2  # user + assistant turns

    # 6. Delete session
    del_res = client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 204

    # 7. Verify 404 after deletion
    not_found_res = client.get(f"/api/v1/sessions/{session_id}")
    assert not_found_res.status_code == 404
    err_data = not_found_res.json()
    assert "error" in err_data
    assert err_data["error_code"] == "HTTP_404"

def test_validation_error_handling():
    """Verify invalid payloads produce structured 422 errors."""
    # Missing required 'content' field
    res = client.post("/api/v1/sessions/invalid-id/messages", json={})
    assert res.status_code == 422
    err_data = res.json()
    assert "error" in err_data
    assert err_data["error_code"] == "VALIDATION_ERROR"
    assert "request_id" in err_data

def test_retrieve_endpoint():
    """Verify /api/v1/retrieve endpoint schema."""
    res = client.post("/api/v1/retrieve", json={"query": "Brian Chesky crisis", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Brian Chesky crisis"
    assert isinstance(data["chunks"], list)
    assert "latency_ms" in data
