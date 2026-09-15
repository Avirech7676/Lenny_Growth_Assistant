import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db_session
from app.db.models import Session as SessionModel, Artifact as ArtifactModel
from app.services.artifact_renderer import (
    wrap_artifact_html,
    render_sandboxed_artifact,
    get_sandbox_security_headers,
    CSP_POLICY,
)
from app.agents.orchestrator import sanitize_artifact_content

client = TestClient(app)

def test_wrap_artifact_html():
    """Verify wrap_artifact_html wraps content with valid HTML5, theme tokens, and typography."""
    html_out = wrap_artifact_html(
        title="ICE Scoring Matrix",
        artifact_type="ice_calculator",
        sanitized_content="<div class='ice-card'>ICE Score: 8.5</div>"
    )

    assert "<!DOCTYPE html>" in html_out
    assert "<title>ICE Scoring Matrix</title>" in html_out
    assert "ICE Score: 8.5" in html_out
    assert "Plus Jakarta Sans" in html_out
    assert "#0A0E17" in html_out
    assert "#10B981" in html_out
    assert "Lenny Assistant Epistemic Sandbox" in html_out
    assert "allow-scripts (origin-isolated)" in html_out


def test_sandbox_security_headers():
    """Verify get_sandbox_security_headers produces strict CSP and isolation directives."""
    headers = get_sandbox_security_headers()
    assert "Content-Security-Policy" in headers
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "SAMEORIGIN"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "no-store" in headers["Cache-Control"]


def test_artifact_iframe_endpoint():
    """Verify GET /api/v1/artifacts/{id}/iframe returns 200 with HTML and security headers."""
    # Create test session and artifact
    with get_db_session() as db:
        session = SessionModel(title="Sandbox Test Session")
        db.add(session)
        db.flush()

        artifact = ArtifactModel(
            session_id=session.id,
            artifact_type="ice_calculator",
            title="Activation Funnel Experiment",
            raw_content="<div><p>Raw Content</p></div>",
            sanitized_content="<div class='p-4 bg-slate-800 rounded'><p>Sanitized Funnel</p></div>",
            status="sanitized"
        )
        db.add(artifact)
        db.commit()
        artifact_id = artifact.id

    res = client.get(f"/api/v1/artifacts/{artifact_id}/iframe")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "SAMEORIGIN"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in res.headers["content-security-policy"]

    body = res.text
    assert "<!DOCTYPE html>" in body
    assert "Activation Funnel Experiment" in body
    assert "Sanitized Funnel" in body


def test_artifact_iframe_not_found():
    """Verify non-existent artifact returns 404 error."""
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/artifacts/{random_id}/iframe")
    assert res.status_code == 404
    assert "not found" in res.json()["error"].lower()


def test_artifact_xss_protection():
    """Verify malicious payloads (script tags, inline event handlers, javascript URIs) are neutralized."""
    malicious_input = (
        "<div class='card'>"
        "<h3>Legitimate Title</h3>"
        "<script>alert('XSS Attack!')</script>"
        "<img src='invalid.jpg' onerror='alert(\"img-xss\")' />"
        "<a href='javascript:alert(\"link-xss\")'>Click me</a>"
        "</div>"
    )

    clean_content = sanitize_artifact_content(malicious_input)
    assert "<script>" not in clean_content
    assert "alert('XSS Attack!')" not in clean_content
    assert "onerror=" not in clean_content
    assert "javascript:" not in clean_content
    assert "Legitimate Title" in clean_content

    # Now wrap into iframe document
    rendered_page = wrap_artifact_html(
        title="Sanitized Artifact",
        artifact_type="security_test",
        sanitized_content=clean_content
    )
    assert "<script>alert" not in rendered_page
    assert "onerror=" not in rendered_page
    assert "javascript:alert" not in rendered_page


def test_render_sandboxed_artifact_fallback():
    """Verify fallback handling when artifact has empty content."""
    with get_db_session() as db:
        session = SessionModel(title="Empty Test Session")
        db.add(session)
        db.flush()

        artifact = ArtifactModel(
            session_id=session.id,
            artifact_type="generic",
            title="Empty Artifact",
            raw_content="",
            sanitized_content="",
            status="pending"
        )
        db.add(artifact)
        db.commit()
        artifact_id = artifact.id

    res = client.get(f"/api/v1/artifacts/{artifact_id}/iframe")
    assert res.status_code == 200
    assert "No artifact content available" in res.text
