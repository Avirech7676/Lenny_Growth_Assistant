"""Dedicated automated test suite for the Ship 30 for 30 viral essay skill."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel
from app.agents.ship30 import analyze_ship30_essay, generate_ship30_cheat_sheet_artifact
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


def test_ship30_essay_structure_analysis():
    """Verify analyzer correctly scores a complete Ship 30 essay."""
    sample_essay = """# The Dangerous Myth of Delegation

Most startup leaders believe the dangerous illusion that hiring senior people and getting out of their way creates autonomy. It doesn't. In high-growth companies, uncoordinated autonomy produces total strategic chaos and fractured customer journeys.

As Brian Chesky explained on Lenny's Podcast, real leadership requires ruthless alignment.

### Pillar 1: Eliminate the Illusion of Empowerment
**When you delegate without shared alignment, you get chaos.** Teams optimize for their individual roadmaps rather than the holistic user experience.

> "If you abdicate your product vision to people five layers down, you don't get empowerment; you get chaos." — Brian Chesky

### Pillar 2: Consolidate Around a Single Cadence
**Run the company like an orchestra, not twenty quartets.** High-agency founders do not manage through twenty fragmented roadmaps; they conduct a single unified release cycle.

### Pillar 3: Obsess Over User Craft
**True leadership is about removing customer friction.** Simplifying an onboarding flow from 40 clicks down to 10 requires dismantling assumptions in the room with the builders.

### 5-Point Actionable Takeaways for Tomorrow:
1. Conduct a sprint audit and identify where fragmented team roadmaps conflict.
2. Cut the bottom 30% of low-leverage vanity metrics.
3. Map your core product onboarding clicks and count every unnecessary friction point.
4. Establish a single company-wide release calendar.
5. Involve leadership in weekly craft and design reviews.

**The Bottom Line:** Great execution is not about doing everything; it is about conducting the few things that matter in perfect harmony.
"""
    analysis = analyze_ship30_essay(sample_essay)
    assert analysis.is_valid is True
    assert analysis.has_hook is True
    assert analysis.has_tension is True
    assert analysis.pillar_count >= 3
    assert analysis.has_bold_anchors is True
    assert analysis.takeaway_count >= 5
    assert analysis.has_outro is True
    assert analysis.structural_score >= 80.0
    assert analysis.quotes_found >= 1


def test_ship30_incomplete_essay_diagnostic():
    """Verify incomplete essays fail structural validation and return feedback."""
    incomplete = "This is a quick summary of a podcast. It has some good advice."
    analysis = analyze_ship30_essay(incomplete)
    assert analysis.is_valid is False
    assert analysis.pillar_count < 3
    assert analysis.takeaway_count < 5
    assert len(analysis.feedback) > 0


def test_ship30_cheat_sheet_artifact_generation():
    """Verify cheat sheet artifact generator produces valid, sanitizable markup."""
    pillars = [
        "Eliminate fragmented roadmaps in favor of a single cadence.",
        "Focus on high-leverage 10x priorities.",
        "Stay in the details of product craft.",
    ]
    takeaways = [
        "Audit sprint tasks by leverage.",
        "Cut low-return meetings.",
        "Measure onboarding clicks.",
        "Establish single release schedule.",
        "Join weekly user testing sessions.",
    ]
    raw_artifact = generate_ship30_cheat_sheet_artifact(
        title="Orchestrated Scaling",
        guest_name="Brian Chesky",
        pillars=pillars,
        takeaways=takeaways,
    )
    assert '<artifact type="html"' in raw_artifact
    assert "Orchestrated Scaling" in raw_artifact
    assert "Brian Chesky" in raw_artifact

    # Verify bleach sanitization preserves classes and elements
    sanitized = sanitize_artifact_content(raw_artifact)
    assert "<script>" not in sanitized
    assert "Executive Cheat Sheet" in sanitized


def test_ship30_live_shreyas_integration(test_db):
    """Verify live API message endpoint produces a high-scoring Ship 30 essay for Shreyas Doshi."""
    session = SessionModel(title="Ship 30 Shreyas Test")
    test_db.add(session)
    test_db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Write a viral Ship 30 for 30 essay on Shreyas Doshi's LNO framework for product management prioritization.",
            "mode": "ship30",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "ship30"
    assert len(data["citations"]) > 0

    analysis = analyze_ship30_essay(data["content"])
    assert analysis.has_hook is True
    assert analysis.pillar_count >= 3
    assert analysis.takeaway_count >= 5
    assert analysis.structural_score >= 70.0

    # Verify registered Growth Canvas artifact
    assert len(data["artifacts"]) > 0
    art_id = data["artifacts"][0]["id"]
    art_res = client.get(f"/api/v1/artifacts/{art_id}")
    assert art_res.status_code == 200
    assert art_res.json()["status"] == "sanitized"


def test_ship30_live_chesky_integration(test_db):
    """Verify live API message endpoint produces a high-scoring Ship 30 essay for Brian Chesky."""
    session = SessionModel(title="Ship 30 Chesky Test")
    test_db.add(session)
    test_db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Write a viral Ship 30 for 30 essay on Brian Chesky's founder mode and running companies like an orchestra.",
            "mode": "ship30",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "ship30"
    assert any("Brian Chesky" in c["guest"] for c in data["citations"])

    analysis = analyze_ship30_essay(data["content"])
    assert analysis.pillar_count >= 3
    assert analysis.takeaway_count >= 5
    assert analysis.is_valid is True
