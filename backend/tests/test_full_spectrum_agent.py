"""Production test suite verifying full-spectrum agent capabilities,
strict Lenny relevance gating, and zero false-positive vector collisions.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session, get_db
from app.db.models import Session as SessionModel, Message as MessageModel, TranscriptChunk
from app.agents.orchestrator import AgentOrchestrator
from app.services.capability import (
    AgentCapability,
    QueryUnderstandingEngine,
    is_lenny_relevant,
)

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


# ==============================================================================
# 1. MANDATORY VERIFICATION: "Who is CM of AP"
# ==============================================================================

def test_who_is_cm_of_ap_no_chesky_collision(test_db):
    """MANDATORY REGRESSION TEST:
    Verify 'Who is CM of AP' answers with N. Chandrababu Naidu,
    cites official government sources (ap.gov.in), and NEVER mentions
    Brian Chesky, Lenny's Podcast, or injects transcript citations.
    """
    session = SessionModel(title="AP CM Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Who is CM of AP",
        mode="research",
        research_mode="auto",
    )

    # 1. Intelligence mode and capability verification
    assert response.intelligence_mode == "real_world", f"Expected real_world, got {response.intelligence_mode}"
    assert response.capability == "web_research", f"Expected web_research, got {response.capability}"

    # 2. Answer correctness: N. Chandrababu Naidu
    content_lower = response.content.lower()
    assert "chandrababu naidu" in content_lower or "naidu" in content_lower, (
        f"Answer did not identify N. Chandrababu Naidu: {response.content}"
    )

    # 3. ABSOLUTE BAN: Brian Chesky and Lenny Podcast must NOT be mentioned
    assert "brian chesky" not in content_lower, f"CRITICAL LEAK: Brian Chesky found in answer: {response.content}"
    assert "chesky" not in content_lower, f"CRITICAL LEAK: Chesky found in answer: {response.content}"
    assert "lenny's podcast" not in content_lower, f"CRITICAL LEAK: Lenny's Podcast found in answer: {response.content}"

    # 4. Citations verification: Must cite government sources, zero transcript citations
    assert len(response.citations) > 0, "Expected external citations for AP CM query"
    for citation in response.citations:
        assert citation.source_type == "external", f"Expected external citation, got {citation.source_type}"
        assert "ap.gov.in" in (citation.domain or "") or "wikipedia.org" in (citation.domain or ""), (
            f"Unexpected citation domain: {citation.domain}"
        )
        assert "Chesky" not in citation.guest, f"Transcript author leaked into citations: {citation.guest}"


def test_is_lenny_relevant_gate():
    """Verify strict relevance gate prevents false positives on real-world queries."""
    # Real-world queries must return False
    assert is_lenny_relevant("Who is CM of AP") is False
    assert is_lenny_relevant("Who is the Prime Minister of India?") is False
    assert is_lenny_relevant("Write a Python function to reverse a string") is False
    assert is_lenny_relevant("How to fix TypeError in JavaScript?") is False
    assert is_lenny_relevant("Compare PostgreSQL vs MongoDB for high throughput") is False

    # Lenny queries must return True
    assert is_lenny_relevant("What did Brian Chesky say about founder mode?") is True
    assert is_lenny_relevant("According to Shreyas Doshi, what is the LNO framework?") is True
    assert is_lenny_relevant("What did Lenny say in his podcast about retention?") is True
    assert is_lenny_relevant("How does Elena Verna define PLG growth loops?") is True


# ==============================================================================
# 2. FULL-SPECTRUM CAPABILITY TESTS
# ==============================================================================

def test_general_qa_conceptual(test_db):
    """Verify conceptual questions route to general_qa with zero citations."""
    session = SessionModel(title="General QA Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="What is recursion in computer science?",
        mode="research",
    )

    assert response.capability == "general_qa"
    assert response.intelligence_mode == "real_world"
    assert len(response.citations) == 0  # No unnecessary citations for basic concepts
    assert "base case" in response.content.lower() or "function" in response.content.lower()


def test_coding_generation(test_db):
    """Verify coding requests route to coding capability with production-grade code."""
    session = SessionModel(title="Coding Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Write a Python function to reverse a string",
        mode="research",
    )

    assert response.capability == "coding"
    assert response.intelligence_mode == "real_world"
    assert len(response.citations) == 0
    assert "def " in response.content or "return" in response.content


def test_debugging_support(test_db):
    """Verify bug/error debugging requests route to debugging capability."""
    session = SessionModel(title="Debugging Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Fix this error: TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        mode="research",
    )

    assert response.capability == "debugging"
    assert response.intelligence_mode == "real_world"
    assert "str(" in response.content or "int(" in response.content or "type" in response.content.lower()


def test_architecture_guidance(test_db):
    """Verify system architecture requests route to architecture capability."""
    session = SessionModel(title="Architecture Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="What is the recommended system architecture for a multi-tenant SaaS application?",
        mode="research",
    )

    assert response.capability == "architecture"
    assert response.intelligence_mode == "real_world"
    assert len(response.content) > 50


def test_lenny_knowledge_mode_grounded(test_db):
    """Verify Lenny podcast questions route to lenny capability and return transcript excerpts."""
    session = SessionModel(title="Lenny Knowledge Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="What did Brian Chesky say about founder mode?",
        mode="research",
    )

    assert response.intelligence_mode == "lenny"
    assert response.capability == "lenny_research"
    assert len(response.citations) > 0
    assert response.citations[0].source_type == "transcript"
    assert "Brian Chesky" in response.citations[0].guest


def test_multi_turn_context_isolation(test_db):
    """Verify Turn 2 does NOT inherit Turn 1's transcript chunks when Turn 2 is a general query."""
    session = SessionModel(title="Multi-Turn Isolation Session")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)

    # Turn 1: Lenny question
    turn1_res = orchestrator.execute_turn(
        session_id=session.id,
        content="What did Brian Chesky say about founder mode?",
        mode="research",
    )
    assert turn1_res.intelligence_mode == "lenny"
    assert "Chesky" in turn1_res.citations[0].guest

    # Turn 2: Real-world political query
    turn2_res = orchestrator.execute_turn(
        session_id=session.id,
        content="Who is CM of AP",
        mode="research",
    )
    assert turn2_res.intelligence_mode == "real_world"
    assert turn2_res.capability == "web_research"
    assert "chandrababu naidu" in turn2_res.content.lower() or "naidu" in turn2_res.content.lower()
    assert "brian chesky" not in turn2_res.content.lower()
    for cit in turn2_res.citations:
        assert cit.source_type == "external"
        assert "Chesky" not in cit.guest
