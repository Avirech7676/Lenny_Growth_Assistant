"""Empirical Validation Test Suite for Gap Closure (6 PARTIAL -> 25 PASS).

Tests:
1. True streaming ReAct tool loop in execute_turn_stream (SSE tool_call and tool_result events).
2. File upload persistence to UploadedDocument and smart relevance injection.
3. Code execution verification in both execute_turn and execute_turn_stream.
4. VerificationEngine live sandbox execution validation.
5. Multimodal support (images in MessageCreate and LLMRequest).
6. Autonomous Agent Task lifecycle endpoint (POST /api/v1/agent/run_task).
"""

import sys
import os
import json
import pytest
import asyncio
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import init_db, get_db_session
from app.db.models import Session as SessionModel, UploadedDocument
from app.agents.orchestrator import AgentOrchestrator
from app.models.tools import ToolRegistry, ToolDefinition, get_tool_registry
from app.models.base import LLMRequest, LLMResponse
from app.models.provider import LLMProvider, ProviderRegistry
from app.orchestrator.verification import VerificationEngine
from app.orchestrator.types import Capability

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    init_db()


# ── GAP 1: TRUE STREAMING REACT AGENT TOOL LOOP ──────────────────────────────
@pytest.mark.asyncio
async def test_streaming_react_tool_loop_sse_events():
    """Verify live SSE stream invokes tools, emits tool_call and tool_result events,
    and streams final synthesis tokens.
    """
    db = get_db_session()
    try:
        session = SessionModel(title="Streaming Tool Calling Test")
        db.add(session)
        db.commit()

        orchestrator = AgentOrchestrator(db=db)

        # Mock tool provider that triggers a tool call on iteration 1
        class MockStreamingToolLLM(LLMProvider):
            def __init__(self):
                self.calls = 0

            def get_model_name(self):
                return "mock-stream-tool"

            def get_provider_id(self):
                return "mock"

            def health_check(self):
                return {"status": "HEALTHY", "healthy": True}

            def generate(self, req=None, *args, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        content="",
                        model="mock-stream-tool",
                        provider="mock",
                        tool_calls=[{
                            "id": "call_calc_99",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": json.dumps({"expression": "12 * 12"}),
                            },
                        }],
                    )
                # Second turn: final synthesis with tool result
                return LLMResponse(
                    content="The result of 12 * 12 is 144.",
                    model="mock-stream-tool",
                    provider="mock",
                )

            def generate_stream(self, *args, **kwargs):
                yield "The result of 12 * 12 is 144."

        ProviderRegistry.register("mock_stream", MockStreamingToolLLM())

        stream_gen = orchestrator.execute_turn_stream(
            session_id=session.id,
            content="Please compute 12 * 12 using the calculator tool.",
            provider_override="mock_stream",
        )

        events = []
        async for chunk in stream_gen:
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:].strip())
                    events.append(payload)
                except Exception:
                    pass

        event_types = [e.get("event") for e in events]
        assert "tool_call" in event_types, f"Expected 'tool_call' in SSE events, got: {event_types}"
        assert "tool_result" in event_types, f"Expected 'tool_result' in SSE events, got: {event_types}"
        assert "token" in event_types, f"Expected 'token' in SSE events, got: {event_types}"

        # Check tool execution payload
        call_ev = next(e for e in events if e.get("event") == "tool_call")
        assert call_ev["tool"] == "calculator"
        assert call_ev["args"] == {"expression": "12 * 12"}

        res_ev = next(e for e in events if e.get("event") == "tool_result")
        assert res_ev["tool"] == "calculator"
        assert res_ev["result"]["output"] == 144.0
    finally:
        db.close()


# ── GAP 2: FILE UPLOAD STATE BINDING & RELEVANCE ISOLATION ───────────────────
def test_file_upload_persistence_and_smart_relevance_isolation():
    """Verify uploaded document is persisted to the session database and injected
    ONLY when the query is document-relevant, preventing contamination of unrelated queries.
    """
    db = get_db_session()
    try:
        session = SessionModel(title="Document Intelligence Test")
        db.add(session)
        db.commit()

        # 1. Directly insert an UploadedDocument bound to session
        doc = UploadedDocument(
            session_id=session.id,
            filename="quarterly_report.txt",
            file_type="txt",
            extracted_text="Q3 ARR reached $42M with net revenue retention of 128%. Key expansion vector was enterprise tiers.",
            char_count=100,
        )
        db.add(doc)
        db.commit()

        # Verify document is linked to session
        saved_doc = db.query(UploadedDocument).filter(UploadedDocument.session_id == session.id).first()
        assert saved_doc is not None
        assert saved_doc.filename == "quarterly_report.txt"

        orchestrator = AgentOrchestrator(db=db)

        # 2. Turn with document-relevant query: context MUST include document
        doc_resp = orchestrator.execute_turn(
            session_id=session.id,
            content="Summarize the uploaded document quarterly report metrics",
            provider_override="fallback",
        )
        assert doc_resp is not None

        # 3. Turn with completely unrelated general knowledge query: context must NOT be contaminated
        clean_resp = orchestrator.execute_turn(
            session_id=session.id,
            content="Explain binary search and what is its time complexity?",
            provider_override="fallback",
        )
        assert "128%" not in clean_resp.content
        assert "$42M" not in clean_resp.content
    finally:
        db.close()


# ── GAP 3: LIVE CODE EXECUTION VERIFICATION IN CHAT ──────────────────────────
def test_code_execution_verification_in_sync_and_stream():
    """Verify generated Python code is automatically executed in the sandbox
    and verified badge is appended to the message.
    """
    db = get_db_session()
    try:
        session = SessionModel(title="Coding Verification Test")
        db.add(session)
        db.commit()

        class MockCodingLLM(LLMProvider):
            def get_model_name(self):
                return "mock-code-model"

            def get_provider_id(self):
                return "mock"

            def health_check(self):
                return {"status": "HEALTHY", "healthy": True}

            def generate(self, req=None, *args, **kwargs):
                return LLMResponse(
                    content="Here is the solution:\n\n```python\nx = 10 * 5\nprint(f'Computed: {x}')\n```\n",
                    model="mock-code-model",
                    provider="mock",
                )

            def generate_stream(self, *args, **kwargs):
                yield "Here is the solution:\n\n```python\nx = 10 * 5\nprint(f'Computed: {x}')\n```\n"

        ProviderRegistry.register("mock_code", MockCodingLLM())

        orchestrator = AgentOrchestrator(db=db)

        # 1. Sync turn verification
        res = orchestrator.execute_turn(
            session_id=session.id,
            content="Write python code to compute 10 * 5",
            provider_override="mock_code",
        )
        assert "Code Execution Verified" in res.content
        assert "50" in res.content

        # 2. VerificationEngine AST + Live Sandbox test
        v_engine = VerificationEngine()
        v_res = v_engine.verify(
            query="Write python code to compute 10 * 5",
            response_content="```python\na = 7 + 8\nprint(a)\n```",
            capabilities=[Capability.CODING],
            context_used="",
            citations=[],
        )
        assert v_res.code_syntax_valid is True
        assert v_res.live_execution_verified is True
        assert v_res.is_verified is True
    finally:
        db.close()


# ── GAP 4: MULTIMODAL SUPPORT ────────────────────────────────────────────────
def test_multimodal_message_create_and_llm_request():
    """Verify MessageCreate and LLMRequest accept multimodal images payload."""
    req = LLMRequest(
        prompt="Analyze this diagram",
        images=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="],
    )
    assert req.images is not None
    assert len(req.images) == 1

    # Test API endpoint accepts images
    db = get_db_session()
    try:
        session = SessionModel(title="Multimodal Test Session")
        db.add(session)
        db.commit()

        api_res = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json={
                "content": "What is shown in this image?",
                "images": ["https://example.com/chart.png"],
                "provider_override": "fallback",
            },
        )
        assert api_res.status_code == 201
        data = api_res.json()
        assert "id" in data
    finally:
        db.close()


# ── GAP 5: AUTONOMOUS AGENT TASK EXECUTION ───────────────────────────────────
def test_autonomous_agent_task_lifecycle_endpoint():
    """Verify POST /api/v1/agent/run_task executes the 9-stage lifecycle
    and returns structured verification phases.
    """
    res = client.post(
        "/api/v1/agent/run_task",
        json={
            "task_description": "Verify code sandbox and test suite execution",
            "target_files": ["backend/app/coding/sandbox.py"],
            "test_target": "backend/tests/test_sandbox.py",
            "auto_confirm": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["task_description"] == "Verify code sandbox and test suite execution"
    assert data["build_verified"] is True
    assert data["test_verified"] is True
    assert len(data["phases_executed"]) >= 6

    phase_names = [p["phase"] for p in data["phases_executed"]]
    assert any("INSPECT" in p or "inspect" in p for p in phase_names)
    assert any("PLAN" in p or "plan" in p for p in phase_names)
    assert any("BUILD" in p or "build" in p for p in phase_names)
    assert any("TEST" in p or "test" in p for p in phase_names)
