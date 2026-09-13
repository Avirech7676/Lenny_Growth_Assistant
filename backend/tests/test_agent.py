"""Tests for Agent Orchestrator, bounded skill prompts, epistemic refusal, and artifact extraction."""

import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session, get_db
from app.db.models import Session as SessionModel, Message as MessageModel, Artifact as ArtifactModel
from app.agents.orchestrator import AgentOrchestrator, sanitize_artifact_content
from app.agents.prompts import REFUSAL_MESSAGE

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize database and ensure tables are present."""
    init_db()
    yield

@pytest.fixture
def test_db():
    db: Session = get_db_session()
    try:
        yield db
    finally:
        db.close()


def test_html_sanitization():
    """Verify bleach sanitization eliminates malicious tags and attributes while preserving styling."""
    malicious = """
    <div class="card" onclick="alert('xss')">
        <h3 class="text-xl">Safe Title</h3>
        <script>window.location='https://attacker.com';</script>
        <img src="x" onerror="alert(1)">
        <p style="color: green;">Safe paragraph</p>
    </div>
    """
    sanitized = sanitize_artifact_content(malicious)
    assert "<script>" not in sanitized
    assert "onclick" not in sanitized
    assert "onerror" not in sanitized
    assert "Safe Title" in sanitized
    assert "Safe paragraph" in sanitized


def test_agent_grounded_research(test_db):
    """Verify grounded research query yields transcript citations and relevant guest advice."""
    session = SessionModel(title="Research Test Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="How did Brian Chesky handle product management and redesign the app?",
        mode="research",
    )

    assert response.role == "assistant"
    assert response.mode == "research"
    assert len(response.citations) > 0
    assert any("Brian Chesky" in c.guest for c in response.citations)
    assert response.latency_ms > 0
    assert "Brian Chesky" in response.content or "orchestra" in response.content.lower()


def test_agent_epistemic_refusal(test_db):
    """Verify out-of-domain queries trigger epistemic refusal without hallucinations."""
    session = SessionModel(title="Refusal Test Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="What is the optimal sourdough bread hydration ratio for a high-altitude oven?",
        mode="research",
    )

    assert response.role == "assistant"
    assert response.content == REFUSAL_MESSAGE
    assert len(response.citations) == 0
    assert len(response.artifacts) == 0
    assert response.model == "epistemic-gate-v2"


def test_agent_ship30_skill_generation(test_db):
    """Verify Ship 30 for 30 skill transforms transcript wisdom into structured viral essay."""
    session = SessionModel(title="Ship 30 Test Session")
    test_db.add(session)
    test_db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Write a viral essay on how Shreyas Doshi prioritizes high-leverage product tasks.",
            "mode": "ship30",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "ship30"
    assert "Pillar" in data["content"] or "Takeaway" in data["content"]
    assert len(data["citations"]) > 0


def test_agent_experiment_mode_and_artifact(test_db):
    """Verify Growth Experiment generation extracts interactive artifact and registers it in DB."""
    session = SessionModel(title="Experiment Test Session")
    test_db.add(session)
    test_db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Design an experiment to reduce onboarding friction based on Brian Chesky's Airbnb lesson on reducing clicks from 40 to 10.",
            "mode": "experiment",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "experiment"
    assert "Hypothesis" in data["content"] or "ICE" in data["content"]

    # Verify extracted artifact
    assert len(data["artifacts"]) > 0
    artifact_id = data["artifacts"][0]["id"]

    # Fetch artifact via REST endpoint
    art_res = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert art_res.status_code == 200
    art_data = art_res.json()
    assert art_data["status"] == "sanitized"
    assert "<script>" not in art_data["sanitized_content"]
    assert "ICE" in art_data["title"] or "Prioritization" in art_data["title"]


def test_agent_multi_turn_history(test_db):
    """Verify multi-turn messages maintain context within the session."""
    session = SessionModel(title="Multi-Turn Session")
    test_db.add(session)
    test_db.commit()

    # Turn 1
    r1 = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={"content": "What did Brian Chesky say about running teams like an orchestra?", "mode": "research"},
    )
    assert r1.status_code == 201

    # Turn 2
    r2 = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={"content": "Can you summarize his core takeaway in playbook format?", "mode": "playbook"},
    )
    assert r2.status_code == 201
    assert r2.json()["mode"] == "playbook"

    # Verify total messages in session: 2 user + 2 assistant = 4
    hist_res = client.get(f"/api/v1/sessions/{session.id}/messages")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "user"
    assert history[3]["role"] == "assistant"
