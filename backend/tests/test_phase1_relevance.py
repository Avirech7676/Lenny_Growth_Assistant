"""Phase 1 Automated Regression Tests: Strict Query-to-Context Relevance Filtering.

Verifies:
USER QUERY
→ INTENT CLASSIFICATION
→ DOMAIN DETECTION
→ ENTITY EXTRACTION
→ CONTEXT RELEVANCE FILTER
→ RETRIEVAL ROUTING
→ ANSWER

Enforces 8 core rules:
1. Lenny knowledge must NOT be retrieved for unrelated questions.
2. Previous conversation evidence must NOT automatically become evidence for a new question.
3. Wikipedia must NOT automatically be searched.
4. GitHub must NOT automatically be searched.
5. Search providers must be selected based on the query.
6. Current questions must be recognized as time-sensitive.
7. Only evidence relevant to the current query may enter the final answer context.
8. The answer generator must not receive unrelated retrieved documents.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Session as SessionModel, Message as MessageModel
from app.services.relevance import (
    get_relevance_router,
    QueryIntent,
    QueryDomain,
    QueryAnalysis,
)
from app.agents.orchestrator import AgentOrchestrator
from app.services.capability import AgentCapability


from app.db.session import init_db, get_db_session


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    yield


@pytest.fixture
def db_session():
    """Database session fixture with access to indexed transcript chunks."""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


class TestPhase1QueryUnderstandingAndRouting:
    """Automated tests for Query Intent, Domain Detection, Entity Extraction & Routing."""

    def test_cm_of_ap_classification(self):
        """Mandatory Test 1: 'Who is CM of AP?' must be classified as current government information."""
        router = get_relevance_router()
        analysis = router.analyze_query("Who is CM of AP?")

        # 1. Intent Classification
        assert analysis.intent == QueryIntent.CURRENT_GOVERNMENT_INFO
        # 2. Domain Detection
        assert analysis.domain == QueryDomain.GOVERNMENT
        # 3. Entity Extraction
        assert any(e in ["CM", "Chief Minister"] for e in analysis.entities)
        assert any(e in ["AP", "Andhra Pradesh"] for e in analysis.entities)
        # 6. Time sensitivity
        assert analysis.is_time_sensitive is True
        # 1. Lenny relevance gating
        assert analysis.lenny_relevant is False
        assert analysis.allow_lenny_retrieval is False
        # 3. Wikipedia must NOT automatically be searched
        assert analysis.allow_wikipedia is False
        # 4. GitHub must NOT automatically be searched
        assert analysis.allow_github is False
        # 5. Search provider selection based on query
        assert "government_portals" in analysis.target_search_providers

    def test_brian_chesky_product_classification(self):
        """Mandatory Test 2: 'What did Brian Chesky say about product?' MUST retrieve Lenny material."""
        router = get_relevance_router()
        analysis = router.analyze_query("What did Brian Chesky say about product?")

        assert analysis.intent == QueryIntent.LENNY_PODCAST_ADVISORY
        assert analysis.domain == QueryDomain.STARTUP_GROWTH
        assert "Brian Chesky" in analysis.entities
        assert analysis.lenny_relevant is True
        assert analysis.allow_lenny_retrieval is True
        assert "lenny_transcript_db" in analysis.target_search_providers

    def test_python_classification(self):
        """Mandatory Test 3: 'What is Python?' should not retrieve Lenny."""
        router = get_relevance_router()
        analysis = router.analyze_query("What is Python?")

        assert analysis.intent == QueryIntent.CONCEPTUAL_EXPLANATION
        assert analysis.domain == QueryDomain.GENERAL_KNOWLEDGE
        assert "Python" in analysis.entities
        assert analysis.lenny_relevant is False
        assert analysis.allow_lenny_retrieval is False
        assert analysis.allow_github is False

    def test_github_wikipedia_not_automatically_searched(self):
        """Rules 3 & 4: Neither Wikipedia nor GitHub are searched by default."""
        router = get_relevance_router()
        analysis = router.analyze_query("Who is the Prime Minister of the UK?")
        assert analysis.allow_github is False
        assert analysis.allow_wikipedia is False

        # Only allowed if user explicitly asks for GitHub repo or code
        code_analysis = router.analyze_query("Find the GitHub repository for FastAPI")
        assert code_analysis.allow_github is True


class TestPhase1ContextRelevanceAndSanitization:
    """Automated tests for Context Relevance Filtering and Multi-Turn Isolation."""

    def test_context_filter_rejects_lenny_chunks_for_government_queries(self):
        """Rules 7 & 8: Unrelated Lenny/Chesky chunks must be rejected from Government context."""
        router = get_relevance_router()
        analysis = router.analyze_query("Who is CM of AP?")

        class MockChunk:
            def __init__(self, title, snippet, source_type, domain=""):
                self.title = title
                self.snippet = snippet
                self.excerpt = snippet
                self.source_type = source_type
                self.domain = domain

        candidates = [
            MockChunk("Andhra Pradesh Official Portal", "Nara Chandrababu Naidu sworn in as CM", "external", "ap.gov.in"),
            MockChunk("Brian Chesky on Founder Mode", "We redesigned Airbnb like an orchestra", "transcript", "lenny.com"),
            MockChunk("Wikipedia AP entry", "State of AP profile", "external", "wikipedia.org"),
        ]

        filtered = router.relevance_filter.filter_evidence_chunks(analysis, candidates)

        # Transcript chunk must be strictly eliminated
        assert len(filtered) == 1
        assert filtered[0].domain == "ap.gov.in"
        assert "ap.gov.in" in filtered[0].domain

    def test_multi_turn_history_isolation(self):
        """Rule 2: Previous conversation evidence must NOT automatically become evidence for a new question."""
        router = get_relevance_router()
        ap_analysis = router.analyze_query("Who is CM of AP?")

        # Simulate prior turn discussing Brian Chesky
        history_with_prior_evidence = [
            {"role": "user", "content": "What did Brian Chesky say about product?"},
            {
                "role": "assistant",
                "content": (
                    "Brian Chesky spoke about founder mode.\n"
                    "[Source ID: ep_123_chunk_4] Guest: Brian Chesky | Episode: Founder Mode\n"
                    "We sat in a room and removed 30 clicks from the flow."
                ),
            },
        ]

        sanitized = router.relevance_filter.sanitize_history_for_turn(ap_analysis, history_with_prior_evidence)

        # Verify raw transcript citation block was stripped
        assistant_turn = sanitized[1]["content"]
        assert "[Source ID:" not in assistant_turn
        assert "We sat in a room and removed 30 clicks" not in assistant_turn


class TestPhase1EndToEndOrchestration:
    """Full End-to-End Orchestrator execution tests."""

    def test_cm_of_ap_end_to_end(self, db_session):
        """Mandatory End-to-End: 'Who is CM of AP?' must answer Chandrababu Naidu with ZERO Lenny pollution."""
        session = SessionModel(title="AP CM Test Session")
        db_session.add(session)
        db_session.commit()

        orchestrator = AgentOrchestrator(db_session)
        response = orchestrator.execute_turn(
            session_id=session.id,
            content="Who is CM of AP?",
            research_mode="auto",
        )

        # 1. Capability & intelligence mode verification
        assert response.intelligence_mode == "real_world"
        assert response.capability == AgentCapability.WEB_RESEARCH.value

        # 2. Response content checks
        content = response.content
        assert "Chandrababu Naidu" in content or "Naidu" in content
        assert "Brian Chesky" not in content
        assert "Chesky" not in content
        assert "Lenny" not in content
        assert "transcript" not in content.lower()

        # 3. Citation checks: NO transcript sources
        for cit in response.citations:
            assert cit.source_type != "transcript"
            assert cit.source_category != "transcript"
            assert "lenny" not in (cit.title or "").lower()

    def test_brian_chesky_end_to_end(self, db_session):
        """Mandatory End-to-End: 'What did Brian Chesky say about product?' MUST retrieve Lenny material."""
        session = SessionModel(title="Chesky Test Session")
        db_session.add(session)
        db_session.commit()

        orchestrator = AgentOrchestrator(db_session)
        response = orchestrator.execute_turn(
            session_id=session.id,
            content="What did Brian Chesky say about product?",
            research_mode="auto",
        )

        assert response.intelligence_mode == "lenny"
        assert response.capability == AgentCapability.LENNY_RESEARCH.value

        content = response.content
        assert "Brian Chesky" in content
        assert any(k in content.lower() for k in ["product", "orchestra", "founder mode", "airbnb"])

    def test_what_is_python_end_to_end(self, db_session):
        """Mandatory End-to-End: 'What is Python?' should not retrieve Lenny."""
        session = SessionModel(title="Python Test Session")
        db_session.add(session)
        db_session.commit()

        orchestrator = AgentOrchestrator(db_session)
        response = orchestrator.execute_turn(
            session_id=session.id,
            content="What is Python?",
            research_mode="auto",
        )

        assert response.intelligence_mode == "real_world"
        assert response.capability == AgentCapability.GENERAL_QA.value

        content = response.content
        assert "Python" in content
        assert any(w in content.lower() for w in ["programming language", "guido van rossum", "interpreted", "syntax"])
        assert "Brian Chesky" not in content
        assert "Lenny" not in content
        assert len(response.citations) == 0 or all(c.source_type != "transcript" for c in response.citations)

    def test_multi_turn_isolation_regression(self, db_session):
        """Turn 1: Chesky -> Turn 2: CM of AP -> Turn 2 has ZERO Chesky leakage."""
        session = SessionModel(title="Multi-Turn Isolation Session")
        db_session.add(session)
        db_session.commit()

        orchestrator = AgentOrchestrator(db_session)

        # Turn 1: Brian Chesky
        t1 = orchestrator.execute_turn(session.id, "What did Brian Chesky say about product?")
        assert "Brian Chesky" in t1.content

        # Turn 2: CM of AP (in the SAME session)
        t2 = orchestrator.execute_turn(session.id, "Who is CM of AP?")
        assert "Chandrababu Naidu" in t2.content or "Naidu" in t2.content
        assert "Brian Chesky" not in t2.content
        assert "Chesky" not in t2.content
        assert "Lenny" not in t2.content
        for c in t2.citations:
            assert c.source_type != "transcript"
            assert "chesky" not in (c.title or "").lower()
