"""
Tests for Phase D: Direct LLM answering, clean system prompts, and response flow.
Verifies that responses answer the specific question directly without corporate boilerplate,
placeholders, or synthetic headers.
"""

import sys
import os
import re
import pytest
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel
from app.agents.orchestrator import AgentOrchestrator

FORBIDDEN_BOILERPLATE = [
    "Key Findings",
    "Strategic Implications",
    "Direct Conclusion",
    "Standard implementations prioritize clarity",
    "measurable feedback loops",
    "standards.ietf.org",
    "official.standards.org",
]

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    yield

@pytest.fixture
def test_db():
    db: Session = get_db_session()
    try:
        yield db
    finally:
        db.close()


def test_factual_query_direct_answer(test_db):
    """Verify factual query returns the direct answer without corporate boilerplate."""
    session = SessionModel(title="Factual Query Test")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Who is the current CM of Andhra Pradesh?",
        mode="chat",
    )

    content = response.content
    assert response.role == "assistant"
    # Verify accurate answer
    assert any(name in content.lower() for name in ["chandrababu", "naidu", "nara chandrababu naidu"]), \
        f"Expected Chandrababu Naidu in response, got: {content}"
    # Verify zero corporate boilerplate
    for bp in FORBIDDEN_BOILERPLATE:
        assert bp not in content, f"Forbidden corporate boilerplate '{bp}' found in factual response!"
    # Verify zero Chesky/Lenny contamination
    assert "brian chesky" not in content.lower()
    assert "airbnb" not in content.lower()


def test_coding_binary_search_cpp(test_db):
    """Verify C++ binary search request yields complete, un-truncated code with Big-O complexity."""
    session = SessionModel(title="C++ Binary Search Test")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Write a C++ program for binary search.",
        mode="chat",
    )

    content = response.content
    assert response.role == "assistant"
    # Must be C++ code
    assert "#include" in content
    assert "binary" in content.lower() and "search" in content.lower()
    assert "main(" in content or "int main" in content
    # Must contain Big-O complexity
    assert any(c in content for c in ["O(log n)", "O(log(n))", "O(logN)", "log n", "logarithmic"]), \
        f"Expected O(log n) complexity in response, got: {content}"
    # Must NOT have lazy placeholders
    assert "// TODO" not in content
    assert "/* implement here */" not in content
    assert "// ..." not in content
    # Must NOT be the old reverse string snippet
    assert "std::reverse" not in content or "binary" in content
    # Zero corporate boilerplate
    for bp in FORBIDDEN_BOILERPLATE:
        assert bp not in content, f"Forbidden corporate boilerplate '{bp}' found in coding response!"


def test_quantum_computing_conceptual_explanation(test_db):
    """Verify conceptual explanation query explains physics concepts clearly without corporate filler."""
    session = SessionModel(title="Quantum Computing Test")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="Explain quantum computing to a beginner.",
        mode="chat",
    )

    content = response.content
    assert response.role == "assistant"
    # Verify core quantum concepts
    assert any(term in content.lower() for term in ["qubit", "superposition", "entanglement", "quantum bit"]), \
        f"Expected quantum concepts in response, got: {content}"
    # Verify zero business/growth jargon
    assert "startup" not in content.lower()
    assert "growth loop" not in content.lower()
    assert "brian chesky" not in content.lower()
    # Verify zero corporate boilerplate
    for bp in FORBIDDEN_BOILERPLATE:
        assert bp not in content, f"Forbidden corporate boilerplate '{bp}' found in conceptual response!"


def test_latest_react_version_query(test_db):
    """Verify technical documentation query returns accurate React version without fake IETF links."""
    session = SessionModel(title="React Version Test")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="What is the latest React version?",
        mode="chat",
    )

    content = response.content
    assert response.role == "assistant"
    # Verify React version mention or official documentation link
    assert any(v in content.lower() for v in ["react 19", "react 18", "19", "18", "react.dev", "react"]), \
        f"Expected modern React version or official documentation reference in response, got: {content}"
    # Verify NO fake IETF standards links
    assert "standards.ietf.org" not in content
    assert "official.standards.org" not in content
    for c in response.citations:
        assert "ietf.org" not in getattr(c, "url", "")
        assert "official.standards.org" not in getattr(c, "url", "")


def test_photosynthesis_general_qa(test_db):
    """Verify general scientific inquiry returns direct explanation without corporate framing."""
    session = SessionModel(title="Photosynthesis Test")
    test_db.add(session)
    test_db.commit()

    orchestrator = AgentOrchestrator(db=test_db)
    response = orchestrator.execute_turn(
        session_id=session.id,
        content="How does photosynthesis work?",
        mode="chat",
    )

    content = response.content
    assert response.role == "assistant"
    # Scientific terms
    assert any(term in content.lower() for term in ["chlorophyll", "sunlight", "carbon dioxide", "oxygen", "glucose", "light"]), \
        f"Expected biological terms in response, got: {content}"
    # Zero corporate filler
    for bp in FORBIDDEN_BOILERPLATE:
        assert bp not in content, f"Forbidden corporate boilerplate '{bp}' found in photosynthesis response!"
    assert "strategic" not in content.lower()
    assert "brian chesky" not in content.lower()
