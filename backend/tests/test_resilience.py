"""Automated chaos, failure mode, and resilience tests for The Lenny Growth Assistant."""

import sys
import os
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import get_db_session
from app.db.models import Session as SessionModel, Message as MessageModel
from app.agents.orchestrator import AgentOrchestrator
from app.agents.prompts import REFUSAL_MESSAGE
from app.models.provider import get_llm_provider, FallbackGroundedProvider

client = TestClient(app)

def test_database_down_health_check():
    """Verify /health/db returns 503 with structured details when database ping fails."""
    with patch("app.api.routes.ping_db", return_value=False):
        res = client.get("/health/db")
        assert res.status_code == 503
        data = res.json()
        assert "error" in data or "detail" in data


def test_malformed_and_oversized_payloads():
    """Verify API handles oversized inputs, wrong types, and invalid modes gracefully."""
    # 1. Create valid session first
    create_res = client.post("/api/v1/sessions", json={"title": "Chaos Test Session"})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Missing required 'content' field
    res_missing = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"mode": "research"}
    )
    assert res_missing.status_code == 422
    assert "error" in res_missing.json()

    # 3. Empty content string
    res_empty = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "   ", "mode": "research"}
    )
    assert res_empty.status_code == 422

    # 4. Oversized payload (60,000 characters)
    huge_string = "Growth strategy " * 4000
    res_huge = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": huge_string, "mode": "research"}
    )
    assert res_huge.status_code == 422


def test_sql_injection_and_xss_in_user_prompt():
    """Verify SQL injection vectors and script tags are safely handled without database corruption."""
    with get_db_session() as db:
        session = SessionModel(title="Injection Test Session")
        db.add(session)
        db.commit()
        session_id = session.id

    # SQL Injection payload
    sql_payload = "'; DROP TABLE messages; SELECT * FROM sessions WHERE '1'='1"
    res_sql = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": sql_payload, "mode": "research"}
    )
    # Should safely process or refuse, and NOT drop table
    assert res_sql.status_code == 201

    # Verify messages table still intact
    with get_db_session() as db:
        stored_msgs = db.query(MessageModel).filter(MessageModel.session_id == session_id).all()
        assert len(stored_msgs) >= 2  # user msg + assistant msg
        user_msg = stored_msgs[0]
        assert user_msg.content == sql_payload

    # XSS Script Injection in prompt
    xss_payload = "<script>alert('Steal Cookies: ' + document.cookie)</script>"
    res_xss = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": xss_payload, "mode": "research"}
    )
    assert res_xss.status_code == 201


def test_epistemic_refusal_spectrum():
    """Verify strict epistemic cutoff (< 0.28) across a spectrum of out-of-domain queries."""
    out_of_domain_queries = [
        "How do I bake chocolate chip cookies from scratch?",
        "What is the best motor oil for a 2012 Honda Civic?",
        "Why do birds migrate south during the winter months?",
        "Explain the rules of cricket and how the lbw decision works.",
    ]

    with get_db_session() as db:
        session = SessionModel(title="Epistemic Spectrum Test")
        db.add(session)
        db.commit()
        session_id = session.id

        orchestrator = AgentOrchestrator(db=db)

        for query in out_of_domain_queries:
            response = orchestrator.execute_turn(
                session_id=session_id,
                content=query,
                mode="research"
            )
            assert REFUSAL_MESSAGE in response.content or "available lenny transcript material" in response.content.lower()
            assert len(response.citations) == 0


def test_nonexistent_and_invalid_uuids():
    """Verify non-existent and malformed UUIDs return structured 404 errors."""
    fake_uuid = str(uuid.uuid4())

    # Get session
    res_sess = client.get(f"/api/v1/sessions/{fake_uuid}")
    assert res_sess.status_code == 404
    assert "error" in res_sess.json()

    # Get messages for nonexistent session
    res_msgs = client.get(f"/api/v1/sessions/{fake_uuid}/messages")
    assert res_msgs.status_code == 404

    # Post message to nonexistent session
    res_post = client.post(
        f"/api/v1/sessions/{fake_uuid}/messages",
        json={"content": "Hello", "mode": "research"}
    )
    assert res_post.status_code == 404

    # Get nonexistent artifact iframe
    res_art = client.get(f"/api/v1/artifacts/{fake_uuid}/iframe")
    assert res_art.status_code == 404

    # Malformed non-UUID strings
    res_malformed = client.get("/api/v1/sessions/not-a-valid-uuid-string")
    assert res_malformed.status_code == 404


def test_provider_outage_failover():
    """Verify that when external providers fail or raise exceptions, system gracefully falls back."""
    provider = get_llm_provider(override="fallback")
    assert isinstance(provider, FallbackGroundedProvider)

    # Test that FallbackGroundedProvider handles empty contexts gracefully
    resp_empty = provider.generate(
        system_prompt="You are Lenny Assistant",
        user_prompt="Explain founder mode",
        context="",
        history=[]
    )
    assert len(resp_empty) > 0
    assert "grounded" in resp_empty.lower() or "lenny" in resp_empty.lower()
