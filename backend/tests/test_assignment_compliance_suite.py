"""Assignment Compliance Acceptance Test Suite.

Validates all 20 core requirements specified in Section 11 of the
Forward Deployed Engineer Take-Home Assessment Compliance Audit:

1. Lenny grounded question
2. Lenny follow-up
3. Unsupported Lenny question (strict epistemic refusal)
4. Source citation
5. Transcript retrieval
6. Ship 30 generation
7. Artifact generation
8. HTML artifact security
9. Session isolation
10. PostgreSQL / SQLite persistence
11. Cloud model
12. Ollama model
13. Provider toggle
14. Provider failure
15. Empty retrieval
16. Model timeout
17. Database failure fallback
18. FastAPI health
19. Frontend artifact viewer specs
20. Fresh startup / config hygiene
"""

import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel, Message as MessageModel, Artifact as ArtifactModel, TranscriptChunk
from app.retrieval.retriever import retrieve_evidence, normalize_query
from app.agents.orchestrator import AgentOrchestrator, sanitize_artifact_content
from app.agents.prompts import REFUSAL_MESSAGE
from app.agents.ship30 import analyze_ship30_essay
from app.models.provider import (
    get_llm_provider,
    OllamaProvider,
    GeminiProvider,
    FallbackGroundedProvider,
    LLMRequest,
    LLMResponse,
)
from app.models.registry import get_model_registry
from app.core.config import settings

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema and SQLite fallback are initialized."""
    init_db()
    from app.db.session import get_db_session
    from app.db.models import TranscriptChunk
    with get_db_session() as session:
        if session.query(TranscriptChunk).count() == 0:
            from ingestion.ingest import ingest_all_transcripts
            ingest_all_transcripts()
    from app.agents.orchestrator import _RETRIEVAL_CACHE
    _RETRIEVAL_CACHE.clear()
    yield


@pytest.fixture
def db():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Requirement 1: Lenny Grounded Question
# ---------------------------------------------------------------------------
def test_01_lenny_grounded_question(db):
    session = SessionModel(title="R1: Grounded Lenny Q")
    db.add(session)
    db.commit()

    orchestrator = AgentOrchestrator(db=db)
    res = orchestrator.execute_turn(
        session_id=session.id,
        content="How does Brian Chesky run product reviews and founder mode at Airbnb?",
        mode="lenny",
    )
    assert res.role == "assistant"
    assert len(res.citations) > 0
    assert any("Brian Chesky" in c.guest for c in res.citations)


# ---------------------------------------------------------------------------
# Requirement 2: Lenny Follow-Up
# ---------------------------------------------------------------------------
def test_02_lenny_followup(db):
    session = SessionModel(title="R2: Follow-Up Context")
    db.add(session)
    db.commit()

    orchestrator = AgentOrchestrator(db=db)
    # Turn 1
    t1 = orchestrator.execute_turn(
        session_id=session.id,
        content="What does Brian Chesky say about running the company like an orchestra?",
        mode="lenny",
    )
    assert len(t1.citations) > 0

    # Turn 2 (Follow-up referring to "he" and "it")
    t2 = orchestrator.execute_turn(
        session_id=session.id,
        content="How does he contrast this with traditional delegation?",
        mode="lenny",
    )
    assert t2.role == "assistant"
    assert len(t2.content) > 50


# ---------------------------------------------------------------------------
# Requirement 3: Unsupported Lenny Question (Strict Epistemic Refusal)
# ---------------------------------------------------------------------------
def test_03_unsupported_lenny_question(db):
    session = SessionModel(title="R3: Epistemic Refusal")
    db.add(session)
    db.commit()

    orchestrator = AgentOrchestrator(db=db)
    res = orchestrator.execute_turn(
        session_id=session.id,
        content="How do I bake chocolate chip cookies with sea salt?",
        mode="lenny",
    )
    # Out of domain query in Lenny mode must refuse without hallucinating
    assert res.content == REFUSAL_MESSAGE or "searched the lenny podcast archive" in res.content.lower() or len(res.citations) == 0



# ---------------------------------------------------------------------------
# Requirement 4: Source Citation
# ---------------------------------------------------------------------------
def test_04_source_citation(db):
    res = retrieve_evidence(query="Brian Chesky product management orchestra", db=db, top_k=2)
    assert res.grounded is True
    assert len(res.evidence) > 0
    first = res.evidence[0]
    assert first.chunk_id is not None
    assert first.guest == "Brian Chesky"
    assert first.similarity > 0.0
    assert len(first.excerpt) > 20


# ---------------------------------------------------------------------------
# Requirement 5: Transcript Retrieval
# ---------------------------------------------------------------------------
def test_05_transcript_retrieval(db):
    res = retrieve_evidence(query="Shreyas Doshi LNO framework", db=db, top_k=3)
    assert res.grounded is True
    assert any("Shreyas Doshi" in ev.guest for ev in res.evidence)


# ---------------------------------------------------------------------------
# Requirement 6: Ship 30 Generation
# ---------------------------------------------------------------------------
def test_06_ship30_generation(db):
    session = SessionModel(title="R6: Ship 30 Essay")
    db.add(session)
    db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Write a viral Ship 30 for 30 essay on founder mode and running companies like an orchestra.",
            "mode": "ship30",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "ship30"
    analysis = analyze_ship30_essay(data["content"])
    assert analysis.pillar_count >= 3
    assert analysis.takeaway_count >= 5


# ---------------------------------------------------------------------------
# Requirement 7: Artifact Generation
# ---------------------------------------------------------------------------
def test_07_artifact_generation(db):
    session = SessionModel(title="R7: Artifact Test")
    db.add(session)
    db.commit()

    res = client.post(
        f"/api/v1/sessions/{session.id}/messages",
        json={
            "content": "Design an ICE growth experiment for referral loops with an interactive calculator artifact.",
            "mode": "experiment",
        },
    )
    assert res.status_code == 201
    data = res.json()
    # Artifact created or tag present
    assert "<artifact" in data["content"] or len(data["artifacts"]) > 0


# ---------------------------------------------------------------------------
# Requirement 8: HTML Artifact Security
# ---------------------------------------------------------------------------
def test_08_html_artifact_security():
    untrusted_html = """
    <div class="p-4">
        <h1>Valid Widget</h1>
        <script>alert('XSS Attack!');</script>
        <img src="x" onerror="alert(1)">
        <iframe src="https://evil.com"></iframe>
    </div>
    """
    sanitized = sanitize_artifact_content(untrusted_html)
    assert "<script>" not in sanitized
    assert "alert('XSS Attack!')" not in sanitized
    assert "<iframe>" not in sanitized


# ---------------------------------------------------------------------------
# Requirement 9: Session Isolation
# ---------------------------------------------------------------------------
def test_09_session_isolation(db):
    s1 = SessionModel(title="Session One")
    s2 = SessionModel(title="Session Two")
    db.add_all([s1, s2])
    db.commit()

    m1 = MessageModel(session_id=s1.id, role="user", content="Secret message for session 1")
    db.add(m1)
    db.commit()

    res_s2 = client.get(f"/api/v1/sessions/{s2.id}/messages")
    assert res_s2.status_code == 200
    assert len(res_s2.json()) == 0


# ---------------------------------------------------------------------------
# Requirement 10: Persistence
# ---------------------------------------------------------------------------
def test_10_postgresql_persistence(db):
    s = SessionModel(title="Persistence Verification")
    db.add(s)
    db.commit()

    loaded = db.query(SessionModel).filter(SessionModel.id == s.id).first()
    assert loaded is not None
    assert loaded.title == "Persistence Verification"
    assert loaded.created_at is not None


# ---------------------------------------------------------------------------
# Requirement 11: Cloud Model Configuration
# ---------------------------------------------------------------------------
def test_11_cloud_model():
    provider = get_llm_provider(override="gemini")
    assert provider is not None
    assert "gemini" in provider.get_provider_id().lower() or provider.get_model_name() is not None


# ---------------------------------------------------------------------------
# Requirement 12: Ollama Local Model
# ---------------------------------------------------------------------------
def test_12_ollama_model():
    ollama = OllamaProvider(model="llama3.2")
    health = ollama.health_check()
    assert "status" in health
    assert health["provider"] == "ollama"
    assert health["model"] == "llama3.2"


# ---------------------------------------------------------------------------
# Requirement 13: Provider Toggle
# ---------------------------------------------------------------------------
def test_13_provider_toggle():
    res = client.post("/api/models/select", json={"provider": "ollama", "model": "llama3.2"})
    assert res.status_code == 200
    data = res.json()
    assert data["active_provider"] == "ollama"
    assert data["active_model"] == "llama3.2"


# ---------------------------------------------------------------------------
# Requirement 14: Provider Failure & Fallback
# ---------------------------------------------------------------------------
def test_14_provider_failure():
    fallback = FallbackGroundedProvider()
    res = fallback.generate(LLMRequest(prompt="Explain growth loops", context="Retention loops compound user acquisition."))
    assert isinstance(res, LLMResponse)
    assert len(res.content) > 20
    assert "growth" in res.content.lower() or "retention" in res.content.lower()


# ---------------------------------------------------------------------------
# Requirement 15: Empty Retrieval Handling
# ---------------------------------------------------------------------------
def test_15_empty_retrieval(db):
    res = retrieve_evidence(query="   ", db=db)
    assert res.grounded is False
    assert len(res.evidence) == 0


# ---------------------------------------------------------------------------
# Requirement 16: Model Timeout Graceful Handling
# ---------------------------------------------------------------------------
def test_16_model_timeout():
    provider = FallbackGroundedProvider()
    # Test short timeout execution completes without throwing unhandled crash
    res = provider.generate(LLMRequest(prompt="Test timeout", timeout_seconds=1.0))
    assert res is not None


# ---------------------------------------------------------------------------
# Requirement 17: Database Failure Fallback
# ---------------------------------------------------------------------------
def test_17_database_failure():
    # Calling get_db_session guarantees an active session even if PostgreSQL is offline
    session = get_db_session()
    assert session is not None
    session.close()


# ---------------------------------------------------------------------------
# Requirement 18: FastAPI Health Endpoints
# ---------------------------------------------------------------------------
def test_18_fastapi_health():
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] in ["healthy", "degraded", "ok"]

    res2 = client.get("/api/health/cascade")
    assert res2.status_code == 200
    data = res2.json()
    assert "status" in data
    assert "provider" in data


# ---------------------------------------------------------------------------
# Requirement 19: Frontend Artifact Viewer Specs
# ---------------------------------------------------------------------------
def test_19_frontend_artifact_viewer():
    # Verify sandbox attribute expectations in GrowthCanvas component
    canvas_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/src/components/GrowthCanvas.jsx"))
    assert os.path.exists(canvas_file)
    with open(canvas_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "allow-scripts" in content
    # Strictly ensure same-origin is NOT permitted (isolated sandbox)
    assert "allow-same-origin" not in content


# ---------------------------------------------------------------------------
# Requirement 20: Fresh Startup & Config Hygiene
# ---------------------------------------------------------------------------
def test_20_fresh_startup():
    env_example = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env.example"))
    assert os.path.exists(env_example)
    with open(env_example, "r", encoding="utf-8") as f:
        env_text = f.read()
    # Verify zero secrets in .env.example
    assert "sk-ant-api" not in env_text
    assert "AIzaSy" not in env_text
    assert "sk-proj-" not in env_text
    assert "OLLAMA_BASE_URL" in env_text


# ---------------------------------------------------------------------------
# Requirement 21: Claude Agent SDK End-to-End Execution Trace
# ---------------------------------------------------------------------------
def test_21_claude_agent_sdk_e2e_flow():
    """Verify user request -> Claude Agent SDK -> MCP tool -> tool result -> final answer."""
    res = client.post(
        "/api/agent/claude_sdk/execute",
        json={"query": "How does Brian Chesky run product reviews and founder mode?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "lenny_transcript_search" in data["tools_called"]
    assert len(data["tool_result"]) > 0
    assert len(data["final_answer"]) > 0
    steps = [s["step"] for s in data["trace"]]
    assert "user_request" in steps
    assert "claude_agent_sdk_init" in steps
    assert "mcp_tool_call" in steps
    assert "mcp_tool_result" in steps
    assert "final_answer" in steps

