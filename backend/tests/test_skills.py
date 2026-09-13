"""Automated test suite for Decision-Support Skills: Growth Experiments and Growth Playbooks."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel
from app.agents.experiments import validate_growth_experiment, generate_ice_calculator_artifact
from app.agents.playbooks import validate_growth_playbook, generate_playbook_matrix_artifact
from app.agents.orchestrator import sanitize_artifact_content

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure tables are ready for tests."""
    init_db()
    yield

@pytest.fixture
def test_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def test_experiment_validation_complete():
    """Verify complete growth experiment specification passes validation with correct ICE arithmetic."""
    spec = """# Growth Experiment Specification: Streamlined Host Onboarding

### Objective
Reduce host onboarding churn by 20% by cutting unnecessary form steps.

### Hypothesis
If we reduce host setup from 40 clicks to 10 clicks, then activation will increase by 24% because cognitive fatigue is removed.

### Target Metrics
- Primary Metric: Day-7 Host Activation Rate.
- Guardrail Metric: User identity verification completion rate (>= 98%).

### ICE Score
- Impact (1-10): 9.0
- Confidence (1-10): 8.0
- Ease (1-10): 7.0

### Transcript Precedent
As Brian Chesky recounted on Lenny's Podcast, Airbnb rebuilt setup from 40 clicks down to 10 clicks.

### 48-Hour Smoke Test
Deploy a 5-step prototype flow to 10% of new signups.
"""
    result = validate_growth_experiment(spec)
    assert result.is_valid is True
    assert result.has_objective is True
    assert result.has_hypothesis is True
    assert result.has_metrics is True
    assert result.ice_impact == 9.0
    assert result.ice_confidence == 8.0
    assert result.ice_ease == 7.0
    assert result.ice_composite == 8.0
    assert result.has_precedent is True
    assert result.has_smoke_test is True
    assert len(result.feedback) == 0


def test_experiment_validation_incomplete():
    """Verify incomplete experiment returns validation failure and diagnostic feedback."""
    incomplete = "Let's run a test on buttons to see if people click them."
    result = validate_growth_experiment(incomplete)
    assert result.is_valid is False
    assert len(result.feedback) > 0


def test_ice_calculator_artifact_generation():
    """Verify ICE calculator artifact produces valid, sanitizable markup."""
    raw = generate_ice_calculator_artifact(
        title="Onboarding Optimization",
        guest_name="Brian Chesky",
        impact=9.0,
        confidence=8.0,
        ease=7.0,
    )
    assert '<artifact type="html"' in raw
    assert "Onboarding Optimization" in raw
    assert "Brian Chesky" in raw
    assert "8.0" in raw

    sanitized = sanitize_artifact_content(raw)
    assert "<script>" not in sanitized
    assert "ICE Prioritization" in sanitized


def test_playbook_validation_complete():
    """Verify complete operational playbook passes 4-pillar validation and guest attribution."""
    playbook = """# Executive Growth Playbook: High-Agency Operating Model

Grounded in Brian Chesky's leadership turnaround at Airbnb:

### 1. Acquisition Loops
Build defensible organic growth loops driven by PR, brand storytelling, and direct word-of-mouth.

### 2. Frictionless Activation
Measure customer click-depth and remove unnecessary onboarding friction.

### 3. Sustainable Retention
Align the entire organization like an orchestra with a single unified roadmap rather than fragmented sub-teams.

### 4. High-Efficiency Monetization
Cut wasteful performance marketing spend and align pricing with true customer value.
"""
    result = validate_growth_playbook(playbook)
    assert result.is_valid is True
    assert result.has_acquisition is True
    assert result.has_activation is True
    assert result.has_retention is True
    assert result.has_monetization is True
    assert result.pillars_detected == 4
    assert result.guest_referenced is True
    assert len(result.feedback) == 0


def test_playbook_validation_incomplete():
    """Verify incomplete playbook reports missing pillars."""
    incomplete = "### 1. Acquisition\nDo marketing on social media."
    result = validate_growth_playbook(incomplete)
    assert result.is_valid is False
    assert result.pillars_detected < 4
    assert len(result.feedback) > 0


def test_playbook_matrix_artifact_generation():
    """Verify playbook matrix artifact generates valid markup with 4 pillars."""
    raw = generate_playbook_matrix_artifact(
        title="Airbnb Operating Model",
        guest_name="Brian Chesky",
        acquisition_items=["Organic host loops", "Brand PR", "Word-of-mouth"],
        activation_items=["10-click setup", "Instant photo verification", "TTV under 5m"],
        retention_items=["Single company roadmap", "Bi-annual release cadence", "Founder reviews"],
        monetization_items=["Eliminate performance search bidding", "Value-based pricing"],
    )
    assert '<artifact type="html"' in raw
    assert "Airbnb Operating Model" in raw
    assert "Acquisition Loops" in raw

    sanitized = sanitize_artifact_content(raw)
    assert "<script>" not in sanitized
    assert "Growth Playbook Matrix" in sanitized


def test_live_experiment_api_turn(test_db):
    """Verify live API message endpoint generates a valid Growth Experiment and registers artifact."""
    session = SessionModel(title="Live Experiment Session")
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
    assert len(data["citations"]) > 0

    validation = validate_growth_experiment(data["content"])
    assert validation.has_objective is True
    assert validation.has_hypothesis is True
    assert validation.has_smoke_test is True

    # Verify registered artifact
    assert len(data["artifacts"]) > 0
    art_id = data["artifacts"][0]["id"]
    art_res = client.get(f"/api/v1/artifacts/{art_id}")
    assert art_res.status_code == 200
    assert art_res.json()["status"] == "sanitized"


def test_live_playbook_api_turn(test_db):
    """Verify live API message endpoint generates a valid 4-pillar Growth Playbook."""
    session = SessionModel(title="Live Playbook Session")
    test_db.add(session)
    test_db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Summarize Brian Chesky's Airbnb reorganization, orchestra model, and host growth loops into an operational playbook.",
            "mode": "playbook",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "playbook"
    assert len(data["citations"]) > 0

    validation = validate_growth_playbook(data["content"])
    assert validation.is_valid is True
    assert validation.pillars_detected == 4
