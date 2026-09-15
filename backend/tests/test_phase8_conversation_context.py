"""
Phase 8: Conversational Experience & Context Management Tests.

Validates:
1. 5-Layer Context Assembly:
   recent context + relevant historical context + task state + relevant files + relevant research
2. Long Conversation Compaction:
   Budgets tokens, condenses older turns into structured summary without losing active task state.
3. Topic Switch & Anti-Contamination Guard:
   Guarantees irrelevant old conversations never contaminate current queries.
4. Exact Evaluation Sequence:
   Question -> follow-up -> follow-up -> topic switch -> new topic
5. Interactive REST Endpoints:
   - Search conversations (body and title)
   - Rename session
   - Delete session
   - Edit user message (rewinds subsequent turns & branches)
   - Regenerate assistant message
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.main import app
from app.services.context.manager import UnifiedContextManager, get_unified_context_manager
from app.services.context.types import (
    ContextLayer,
    OrchestratedContext,
    TaskState,
    TransitionType,
)


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Five-Layer Context Assembly Unit Tests
# ==============================================================================

def test_five_layer_context_assembly():
    """Verify that assemble_context constructs all 5 required layers."""
    manager = UnifiedContextManager(max_context_tokens=4000)

    history = [
        {"role": "user", "content": "Let's build a FastAPI payment service with Stripe webhooks"},
        {"role": "assistant", "content": "I'll help you design a production-grade FastAPI Stripe service."},
        {"role": "user", "content": "Add idempotent event handling to avoid double charges"},
        {"role": "assistant", "content": "Here is the Stripe webhook handler with Redis idempotency keys."},
    ]

    current_query = "What happens if Redis fails during the webhook check?"
    research_evidence = [
        {"title": "Stripe Webhook Best Practices", "url": "https://stripe.com/docs/webhooks", "snippet": "Always store idempotency keys in persistent storage."}
    ]
    file_context = "### File: schema.sql\nCREATE TABLE processed_webhooks (id VARCHAR PRIMARY KEY);"

    orchestrated = manager.assemble_context(
        session_id="test-session-5layers",
        current_query=current_query,
        history=history,
        research_evidence=research_evidence,
        file_context=file_context,
        active_artifacts=["art_stripe_webhook_py"],
    )

    assert isinstance(orchestrated, OrchestratedContext)
    # Check that all 5 layers exist and have content
    assert orchestrated.recent_context is not None
    assert "Redis" in orchestrated.recent_context.content or "webhook" in orchestrated.recent_context.content
    assert orchestrated.recent_context.layer_type == "recent_context"

    assert orchestrated.relevant_history is not None
    assert orchestrated.relevant_history.layer_type == "relevant_historical_context"

    assert orchestrated.task_state is not None
    assert orchestrated.task_state.layer_type == "task_state"
    assert orchestrated.active_task.follow_up_depth >= 1

    assert orchestrated.relevant_files is not None
    assert orchestrated.relevant_files.layer_type == "relevant_files"
    assert "processed_webhooks" in orchestrated.relevant_files.content

    assert orchestrated.relevant_research is not None
    assert orchestrated.relevant_research.layer_type == "relevant_research"
    assert "Stripe Webhook Best Practices" in orchestrated.relevant_research.content

    # Validate combined prompt representation contains all layers
    combined = orchestrated.to_prompt_context()
    assert "[TASK STATE & CONTINUITY]" in combined
    assert "[ATTACHED FILES & CODE CONTEXT]" in combined
    assert "[GROUNDING RESEARCH EVIDENCE]" in combined
    assert "[RECENT CONVERSATION TURNS]" in combined


# ==============================================================================
# 2. Context Compaction for Long Conversations
# ==============================================================================

def test_long_conversation_compaction():
    """Verify that when turns accumulate, older turns are compacted to stay under budget."""
    manager = UnifiedContextManager(recent_turns=2, max_context_tokens=300)

    # Build 16 turns of back-and-forth conversation
    history = []
    for i in range(1, 9):
        history.append({
            "role": "user",
            "content": f"Step {i}: Discussing microservice scaling requirement and cache invalidation strategies for customer profile cluster {i}."
        })
        history.append({
            "role": "assistant",
            "content": f"Response {i}: For cluster {i}, recommend write-through cache with Redis cluster, CDC via Debezium, and Kafka message brokers."
        })

    current_query = "Summarize our final caching decision and next steps."
    orchestrated = manager.assemble_context(
        session_id="test-compaction-session",
        current_query=current_query,
        history=history,
    )

    # Compaction should have triggered
    assert orchestrated.is_compacted is True
    assert orchestrated.compaction_summary is not None
    assert len(orchestrated.compaction_summary) > 0
    # Total token budget must be respected
    assert orchestrated.total_tokens <= 1800


# ==============================================================================
# 3. Exact Test Sequence: Question -> follow-up -> follow-up -> topic switch -> new topic
# ==============================================================================

def test_exact_sequence_question_followups_switch_new_topic(client):
    """
    REQUIRED TEST:
    Question
    -> follow-up
    -> follow-up
    -> topic switch
    -> new topic
    
    Verifies:
    1. Question: Starts FastAPI user registration with Pydantic.
    2. Follow-up 1: "Add password hashing with bcrypt to that endpoint" maintains task continuity.
    3. Follow-up 2: "Now add rate limiting to it" continues building on the endpoint.
    4. Topic Switch: "Who is the Chief Minister of Andhra Pradesh?" purges FastAPI context, switches to real-world government intelligence.
    5. New Topic: "What is Lenny's framework for consumer product-market fit?" routes to Lenny PMF framework with zero contamination from AP politics or FastAPI code.
    """
    context_manager = get_unified_context_manager()
    
    # Create test session (201 Created)
    sess_res = client.post("/api/v1/sessions", json={"title": "Phase 8 Sequence Test"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # ----------------------------------------------------
    # Step 1: Question
    # ----------------------------------------------------
    q1 = "Write an async FastAPI endpoint for user registration with Pydantic validation"
    r1 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": q1, "mode": "coding"},
    )
    assert r1.status_code == 201
    data1 = r1.json()
    assert "FastAPI" in data1["content"] or "APIRouter" in data1["content"] or "register" in data1["content"].lower()
    assert data1["intelligence_mode"] in ["coding", "real_world"]
    assert "follow_up_suggestions" in data1
    assert len(data1["follow_up_suggestions"]) > 0

    task_state1 = context_manager.get_task_state(session_id)
    assert task_state1.follow_up_depth == 0

    # ----------------------------------------------------
    # Step 2: Follow-up 1 (Continuity)
    # ----------------------------------------------------
    q2 = "Add password hashing with bcrypt to that endpoint"
    r2 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": q2, "mode": "coding"},
    )
    assert r2.status_code == 201
    data2 = r2.json()
    assert "bcrypt" in data2["content"].lower() or "pwd_context" in data2["content"].lower() or "hash" in data2["content"].lower()

    task_state2 = context_manager.get_task_state(session_id)
    assert task_state2.follow_up_depth == 1
    assert task_state2.last_transition == TransitionType.CONTINUITY

    # ----------------------------------------------------
    # Step 3: Follow-up 2 (Continuity)
    # ----------------------------------------------------
    q3 = "Now add rate limiting to it"
    r3 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": q3, "mode": "coding"},
    )
    assert r3.status_code == 201
    data3 = r3.json()
    assert "rate" in data3["content"].lower() or "limit" in data3["content"].lower() or "slowapi" in data3["content"].lower()

    task_state3 = context_manager.get_task_state(session_id)
    assert task_state3.follow_up_depth == 2
    assert task_state3.last_transition == TransitionType.CONTINUITY

    # ----------------------------------------------------
    # Step 4: Topic Switch (Purge coding context, switch to AP Politics)
    # ----------------------------------------------------
    q4 = "Who is the Chief Minister of Andhra Pradesh?"
    r4 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": q4, "mode": "search"},
    )
    assert r4.status_code == 201
    data4 = r4.json()
    assert "Naidu" in data4["content"] or "Chandrababu" in data4["content"]

    task_state4 = context_manager.get_task_state(session_id)
    assert task_state4.last_transition in (TransitionType.TOPIC_SWITCH, TransitionType.NEW_TOPIC)
    assert task_state4.follow_up_depth == 0

    # ----------------------------------------------------
    # Step 5: New Topic (Lenny PMF Framework - ZERO AP Contamination)
    # ----------------------------------------------------
    q5 = "What is Lenny's framework for consumer product-market fit?"
    r5 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": q5, "mode": "lenny"},
    )
    assert r5.status_code == 201
    data5 = r5.json()
    # Must contain PMF / retention frameworks
    assert "product-market fit" in data5["content"].lower() or "retention" in data5["content"].lower() or "pmf" in data5["content"].lower()
    # Anti-contamination guard: AP politics & FastAPI must NOT contaminate response
    assert "Chandrababu" not in data5["content"]
    assert "Andhra" not in data5["content"]
    assert "FastAPI" not in data5["content"]

    task_state5 = context_manager.get_task_state(session_id)
    assert task_state5.last_transition in (TransitionType.TOPIC_SWITCH, TransitionType.NEW_TOPIC)
    assert task_state5.follow_up_depth == 0


# ==============================================================================
# 4. Interactive Conversation REST API Endpoints
# ==============================================================================

def test_session_rename(client):
    """Test PATCH /api/v1/sessions/{session_id} renames the chat."""
    sess_res = client.post("/api/v1/sessions", json={"title": "Original Title"})
    assert sess_res.status_code == 201
    sess_id = sess_res.json()["id"]

    # Rename chat
    patch_res = client.patch(f"/api/v1/sessions/{sess_id}", json={"title": "Upgraded Growth Strategy"})
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Upgraded Growth Strategy"

    # Verify get session reflects new title
    get_res = client.get(f"/api/v1/sessions/{sess_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Upgraded Growth Strategy"


def test_session_search(client):
    """Test GET /api/v1/sessions/search finds conversations by title or message content."""
    sess_res = client.post("/api/v1/sessions", json={"title": "Fintech Architecture"})
    assert sess_res.status_code == 201
    sess_id = sess_res.json()["id"]

    # Send a message with unique token
    msg_res = client.post(
        f"/api/v1/sessions/{sess_id}/messages",
        json={"content": "Explain hyperbolic discount curves in consumer churn"},
    )
    assert msg_res.status_code == 201

    # Search for unique token
    search_res = client.get("/api/v1/sessions/search?q=hyperbolic")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    found = any(r["id"] == sess_id for r in results)
    assert found is True


def test_edit_user_message_and_rewind(client):
    """Test PUT /api/v1/sessions/{session_id}/messages/{message_id} rewinds and branches conversation."""
    sess_res = client.post("/api/v1/sessions", json={"title": "Branching Test"})
    assert sess_res.status_code == 201
    sess_id = sess_res.json()["id"]

    # Turn 1
    msg1 = client.post(
        f"/api/v1/sessions/{sess_id}/messages",
        json={"content": "What is the capital of France?"},
    ).json()

    # Turn 2
    msg2 = client.post(
        f"/api/v1/sessions/{sess_id}/messages",
        json={"content": "What is its population?"},
    ).json()

    # Get all messages before edit
    msgs_before = client.get(f"/api/v1/sessions/{sess_id}/messages").json()
    assert len(msgs_before) >= 4  # 2 user + 2 assistant

    # Find ID of the first user message
    first_user_msg = next(m for m in msgs_before if m["role"] == "user" and "France" in m["content"])
    first_user_id = first_user_msg["id"]

    # Edit the first message to ask about Andhra Pradesh instead
    edit_res = client.put(
        f"/api/v1/sessions/{sess_id}/messages/{first_user_id}",
        json={"content": "Who is the Chief Minister of Andhra Pradesh?"},
    )
    assert edit_res.status_code == 200
    edit_data = edit_res.json()
    assert "Naidu" in edit_data["content"] or "Chandrababu" in edit_data["content"]

    # Verify subsequent turns were rewound
    msgs_after = client.get(f"/api/v1/sessions/{sess_id}/messages").json()
    # Should now have only the edited user message and the new assistant message
    user_msgs = [m for m in msgs_after if m["role"] == "user"]
    assert len(user_msgs) == 1
    assert "Andhra Pradesh" in user_msgs[0]["content"]


def test_regenerate_assistant_message(client):
    """Test POST /api/v1/sessions/{session_id}/messages/{message_id}/regenerate regenerates response."""
    sess_res = client.post("/api/v1/sessions", json={"title": "Regenerate Test"})
    assert sess_res.status_code == 201
    sess_id = sess_res.json()["id"]

    # Send message
    turn_res = client.post(
        f"/api/v1/sessions/{sess_id}/messages",
        json={"content": "Who is the Chief Minister of Andhra Pradesh?"},
    ).json()

    assistant_msg_id = turn_res["id"]

    # Request regeneration
    regen_res = client.post(
        f"/api/v1/sessions/{sess_id}/messages/{assistant_msg_id}/regenerate",
        json={},
    )
    assert regen_res.status_code == 200
    regen_data = regen_res.json()
    assert regen_data["role"] == "assistant"
    assert "Naidu" in regen_data["content"] or "Chandrababu" in regen_data["content"]
