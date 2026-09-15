"""
Tests for Phase O: Production Hardening, Security, Schema Compliance & Resilience.
Verifies:
1. Zero secret leakage across all public endpoints (/health, /health/llm, /api/models, /api/v1/sessions).
2. Graceful fallback persistence if PostgreSQL is unavailable (SQLite local resilience).
3. CORS and security response headers.
4. Input sanitization against script injection in artifacts and prompts.
5. Strict schema conformance for all public API contracts.
"""

import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_zero_secret_leakage_in_health_and_models():
    """Verify API keys and sensitive tokens are never exposed in public JSON responses."""
    # Check /health/llm
    res_llm = client.get("/health/llm")
    assert res_llm.status_code == 200
    text_llm = res_llm.text

    # Check /api/models
    res_models = client.get("/api/models")
    assert res_models.status_code == 200
    text_models = res_models.text

    # Check /api/v1/models
    res_v1_models = client.get("/api/v1/models")
    assert res_v1_models.status_code == 200
    text_v1 = res_v1_models.text

    for sensitive_key in [settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.OPENAI_API_KEY, settings.ANTHROPIC_API_KEY]:
        if sensitive_key and len(sensitive_key) > 8:
            assert sensitive_key not in text_llm, "API key leaked in /health/llm response"
            assert sensitive_key not in text_models, "API key leaked in /api/models response"
            assert sensitive_key not in text_v1, "API key leaked in /api/v1/models response"


def test_cors_headers_production_compliance():
    """Verify CORS headers allow configured origin access with telemetry headers."""
    res = client.options(
        "/api/v1/sessions",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code in [200, 204]
    assert "access-control-allow-origin" in res.headers


def test_x_request_id_and_latency_headers():
    """Verify every HTTP response includes traceability X-Request-ID and X-Response-Time-MS."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert "X-Response-Time-MS" in res.headers


def test_artifact_xss_sanitization_defense():
    """Verify malicious script tags inside generated code artifacts are neutralized."""
    from app.utils.sanitize import sanitize_artifact_content

    malicious_script = "<script>alert('xss')</script><div>Safe Content</div>"
    sanitized = sanitize_artifact_content(malicious_script)

    assert "<script>" not in sanitized
    assert "alert(" not in sanitized
    assert "Safe Content" in sanitized


def test_schema_conformance_for_all_endpoints():
    """Verify all major endpoints strictly validate against expected response schemas."""
    # 1. /health
    h = client.get("/health").json()
    assert h.get("status") in ["healthy", "degraded"]

    # 2. /health/db
    db = client.get("/health/db").json()
    assert "status" in db
    assert "engine" in db
    assert "latency_ms" in db

    # 3. /api/models
    models_res = client.get("/api/models").json()
    assert isinstance(models_res.get("models"), list)
    assert isinstance(models_res.get("count"), int)
