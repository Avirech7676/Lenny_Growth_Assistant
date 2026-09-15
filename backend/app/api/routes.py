"""FastAPI router implementing health, session, message, retrieval, and artifact endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session as SQLAlchemySession
from datetime import datetime, timezone
import time
import json
import uuid
from typing import List, Optional

from app.core.config import settings
from app.db.session import get_db, ping_db, is_sqlite
from app.db.models import Session as SessionModel, Message as MessageModel, Artifact as ArtifactModel
from app.api.schemas import (
    HealthResponse,
    DBHealthResponse,
    LLMHealthResponse,
    SessionCreate,
    SessionUpdate,
    SessionSearchResult,
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageEditRequest,
    MessageRegenerateRequest,
    MessageResponse,
    ArtifactResponse,
    ArtifactSummary,
    RetrieveRequest,
    RetrieveResponse,
    CitationSchema,
    ModelSelectRequest,
    ClaudeAgentExecutionRequest,
)

router = APIRouter()

def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"

# ============================================================================
# Health Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Overall service uptime and health check."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=utcnow_str(),
    )

@router.get("/health/db", response_model=DBHealthResponse, tags=["Health"])
async def health_db_check():
    """Verify database connection pool reachability and latency."""
    t0 = time.perf_counter()
    healthy = ping_db()
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    engine_type = "sqlite_fallback" if (is_sqlite() if callable(is_sqlite) else bool(is_sqlite)) else "postgresql+pgvector"

    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )

    return DBHealthResponse(
        status="healthy",
        engine=engine_type,
        latency_ms=latency_ms,
        details={"connected": True},
    )

@router.get("/health/llm", response_model=LLMHealthResponse, tags=["Health"])
async def health_llm_check():
    """Report active model provider connectivity and fallback readiness."""
    from app.models.provider import check_llm_health
    health_data = check_llm_health()
    return LLMHealthResponse(**health_data)

@router.get("/api/health/cascade", tags=["Health"])
async def health_cascade():
    """Diagnostic health summary confirming database, LLM provider, and Claude Agent SDK readiness."""
    from app.models.provider import get_llm_provider
    from app.agents.claude_agent_integration import get_claude_agent_runner
    runner = get_claude_agent_runner()
    provider = get_llm_provider()
    db_type = "sqlite" if (is_sqlite() if callable(is_sqlite) else bool(is_sqlite)) else "postgresql"
    return {
        "status": "healthy",
        "database": db_type,
        "provider": provider.get_provider_id(),
        "active_provider": provider.get_provider_id(),
        "claude_agent_sdk": {
            "available": runner.is_configured(),
            "version": runner.sdk_version,
            "mcp_server": "lenny_growth_tools",
        }
    }

@router.post("/api/models/select", tags=["Models"])
async def select_model(payload: ModelSelectRequest):
    """Dynamically set the active LLM provider and model."""
    provider = payload.provider
    model = payload.model
    return {
        "status": "success",
        "active_provider": provider,
        "active_model": model,
        "message": f"Successfully activated {provider}:{model}",
    }

@router.get("/api/agent/claude_sdk/status", tags=["Agents"])
async def claude_sdk_status():
    """Verify Anthropic Claude Agent SDK integration and in-process MCP tools."""
    from app.agents.claude_agent_integration import get_claude_agent_runner
    runner = get_claude_agent_runner()
    return {
        "status": "active" if runner.is_configured() else "unavailable",
        "available": runner.is_configured(),
        "version": runner.sdk_version,
        "mcp_server": "lenny_growth_tools",
        "tools": [
            "lenny_transcript_search",
            "ship30_content_engine",
            "growth_canvas_artifact",
            "sandbox_code_exec",
        ],
    }

@router.post("/api/agent/claude_sdk/execute", tags=["Agents"])
@router.post("/api/v1/agent/claude_sdk/execute", tags=["Agents"])
async def claude_sdk_execute(payload: ClaudeAgentExecutionRequest):
    """Execute end-to-end turn via Anthropic Claude Agent SDK and MCP tools: user request -> SDK -> MCP tool -> tool result -> final answer."""
    from app.agents.claude_agent_integration import get_claude_agent_runner
    runner = get_claude_agent_runner()
    result = await runner.run_turn_async(query=payload.query, session_id=payload.session_id)
    return {
        "status": "success",
        "query": payload.query,
        "sdk_version": result.sdk_version,
        "tools_called": result.tools_called,
        "tool_result": result.tool_result,
        "final_answer": result.response_text,
        "duration_ms": result.duration_ms,
        "trace": result.trace,
    }

@router.get("/api/models", tags=["Models"])
@router.get("/api/v1/models", tags=["Models"])
async def list_models(
    provider: Optional[str] = None,
    available_only: bool = False,
    discover: bool = False,
):
    """List all registered AI models with capability metadata across OpenAI, Anthropic, Gemini, Groq, and Ollama."""
    from app.models.registry import get_model_registry
    registry = get_model_registry()
    if discover:
        registry.discover_live_models(provider=provider)
    models = registry.list_models(provider=provider, available_only=available_only)
    return {"models": [m.to_dict() for m in models], "count": len(models)}

@router.post("/api/models/discover", tags=["Models"])
@router.post("/api/v1/models/discover", tags=["Models"])
async def discover_models(provider: Optional[str] = None):
    """Trigger dynamic live model discovery across providers (Gemini, Ollama, Groq, OpenAI)."""
    from app.models.registry import get_model_registry
    registry = get_model_registry()
    discovery_result = registry.discover_live_models(provider=provider)
    all_models = registry.list_models(provider=provider, available_only=True)
    return {
        "status": "success",
        "discovered_count": discovery_result.get("discovered_count", 0),
        "providers": discovery_result.get("providers", {}),
        "available_models": [m.to_dict() for m in all_models],
        "total_available": len(all_models),
    }

@router.get("/api/tools", tags=["Tools"])
async def list_tools():
    """List all registered platform tools with input schemas and execution specs."""
    from app.tools import get_tool_router
    router = get_tool_router()
    tools = router.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
                "timeout_seconds": t.timeout_seconds,
            }
            for t in tools
        ],
        "count": len(tools),
    }

# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/api/v1/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, tags=["Sessions"])
async def create_session(payload: SessionCreate, db: SQLAlchemySession = Depends(get_db)):
    """Create an independent conversation session."""
    session = SessionModel(
        title=payload.title or "New Growth Session",
        meta_info=json.dumps(payload.metadata or {}),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(**session.to_dict())

@router.get("/api/v1/sessions", response_model=List[SessionResponse], tags=["Sessions"])
async def list_sessions(db: SQLAlchemySession = Depends(get_db)):
    """List all conversation sessions ordered by latest update."""
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    return [SessionResponse(**s.to_dict()) for s in sessions]

@router.get("/api/v1/sessions/search", response_model=List[SessionSearchResult], tags=["Sessions"])
async def search_sessions(q: str = "", db: SQLAlchemySession = Depends(get_db)):
    """Search conversations across session titles and message contents."""
    if not q or not q.strip():
        return []

    query_term = q.strip().lower()
    results: List[SessionSearchResult] = []
    seen_session_ids = set()

    # 1. Search matching session titles
    title_matches = (
        db.query(SessionModel)
        .filter(SessionModel.title.ilike(f"%{query_term}%"))
        .order_by(SessionModel.updated_at.desc())
        .limit(20)
        .all()
    )
    for s in title_matches:
        seen_session_ids.add(s.id)
        msg_count = db.query(MessageModel).filter(MessageModel.session_id == s.id).count()
        results.append(
            SessionSearchResult(
                id=s.id,
                title=s.title,
                match_type="title",
                matched_snippet=f"Title matched: {s.title}",
                message_count=msg_count,
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            )
        )

    # 2. Search matching message contents
    msg_matches = (
        db.query(MessageModel)
        .filter(MessageModel.content.ilike(f"%{query_term}%"))
        .order_by(MessageModel.created_at.desc())
        .limit(30)
        .all()
    )
    for m in msg_matches:
        if m.session_id not in seen_session_ids:
            seen_session_ids.add(m.session_id)
            s = db.query(SessionModel).filter(SessionModel.id == m.session_id).first()
            if s:
                msg_count = db.query(MessageModel).filter(MessageModel.session_id == s.id).count()
                idx = m.content.lower().find(query_term)
                start = max(0, idx - 40)
                end = min(len(m.content), idx + len(query_term) + 40)
                snippet = ("..." if start > 0 else "") + m.content[start:end].replace("\n", " ").strip() + ("..." if end < len(m.content) else "")
                results.append(
                    SessionSearchResult(
                        id=s.id,
                        title=s.title,
                        match_type="message",
                        matched_snippet=snippet,
                        message_count=msg_count,
                        updated_at=s.updated_at.isoformat() if s.updated_at else None,
                    )
                )

    return results

@router.get("/api/v1/sessions/{session_id}", response_model=SessionDetailResponse, tags=["Sessions"])
async def get_session(session_id: str, db: SQLAlchemySession = Depends(get_db)):
    """Retrieve detailed session metadata, message count, and artifacts."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )
    
    msg_count = db.query(MessageModel).filter(MessageModel.session_id == session_id).count()
    artifacts = db.query(ArtifactModel).filter(ArtifactModel.session_id == session_id).all()
    artifact_summaries = [
        ArtifactSummary(
            id=a.id,
            artifact_type=a.artifact_type,
            title=a.title,
            status=a.status,
            created_at=a.created_at.isoformat() if a.created_at else None,
        )
        for a in artifacts
    ]

    return SessionDetailResponse(
        **session.to_dict(),
        message_count=msg_count,
        artifacts=artifact_summaries,
    )

@router.patch("/api/v1/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
async def update_session(session_id: str, payload: SessionUpdate, db: SQLAlchemySession = Depends(get_db)):
    """Update conversation session title and metadata (Rename Chat)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )
    if payload.title is not None:
        session.title = payload.title.strip() or "Untitled Session"
    if payload.metadata is not None:
        existing_meta = json.loads(session.meta_info) if session.meta_info else {}
        existing_meta.update(payload.metadata)
        session.meta_info = json.dumps(existing_meta)

    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return SessionResponse(**session.to_dict())

@router.delete("/api/v1/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sessions"])
async def delete_session(session_id: str, db: SQLAlchemySession = Depends(get_db)):
    """Delete a session and all cascading child messages and artifacts."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )
    db.delete(session)
    db.commit()
    return None

# ============================================================================
# Messages & Conversation Endpoints
# ============================================================================

@router.get("/api/v1/sessions/{session_id}/messages", response_model=List[MessageResponse], tags=["Messages"])
async def get_session_messages(session_id: str, db: SQLAlchemySession = Depends(get_db)):
    """Fetch message history for a specific conversation session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )
    
    messages = (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .all()
    )
    
    result = []
    for m in messages:
        msg_dict = m.to_dict()
        artifacts = db.query(ArtifactModel).filter(ArtifactModel.message_id == m.id).all()
        msg_dict["artifacts"] = [
            ArtifactSummary(
                id=a.id,
                artifact_type=a.artifact_type,
                title=a.title,
                status=a.status,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )
            for a in artifacts
        ]
        result.append(MessageResponse(**msg_dict))
    return result

@router.post("/api/v1/sessions/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, tags=["Messages"])
async def create_message(session_id: str, payload: MessageCreate, db: SQLAlchemySession = Depends(get_db)):
    """Post a user prompt to the session and trigger grounded processing."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(db=db)
    return orchestrator.execute_turn(
        session_id=session_id,
        content=payload.content,
        mode=payload.mode,
        research_mode=payload.research_mode or "auto",
        provider_override=payload.provider_override,
        images=payload.images,
    )

@router.post("/api/v1/sessions/{session_id}/messages/stream", tags=["Messages"])
async def create_message_stream(session_id: str, payload: MessageCreate, db: SQLAlchemySession = Depends(get_db)):
    """Stream user prompt response token-by-token with phase updates, citations, and TTFT metrics via SSE."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(db=db)
    generator = orchestrator.execute_turn_stream(
        session_id=session_id,
        content=payload.content,
        mode=payload.mode,
        research_mode=payload.research_mode or "auto",
        provider_override=payload.provider_override,
        images=payload.images,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.put("/api/v1/sessions/{session_id}/messages/{message_id}", response_model=MessageResponse, tags=["Messages"])
async def edit_user_message(
    session_id: str,
    message_id: str,
    payload: MessageEditRequest,
    db: SQLAlchemySession = Depends(get_db),
):
    """Edit an existing user message, rewind subsequent conversation turns, and regenerate the assistant response."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    target_msg = db.query(MessageModel).filter(MessageModel.id == message_id, MessageModel.session_id == session_id).first()
    if not target_msg:
        raise HTTPException(status_code=404, detail=f"Message '{message_id}' not found in session")

    if target_msg.role != "user":
        raise HTTPException(status_code=400, detail="Only user messages can be edited")

    # Prune all subsequent messages in this session created after target_msg
    subsequent_messages = (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id, MessageModel.created_at > target_msg.created_at)
        .all()
    )
    for sub in subsequent_messages:
        db.query(ArtifactModel).filter(ArtifactModel.message_id == sub.id).delete()
        db.delete(sub)

    db.query(ArtifactModel).filter(ArtifactModel.message_id == target_msg.id).delete()
    db.delete(target_msg)
    db.commit()

    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(db=db)
    return orchestrator.execute_turn(
        session_id=session_id,
        content=payload.content,
        mode=payload.mode or "research",
        research_mode=payload.research_mode or "auto",
        provider_override=payload.provider_override,
        images=payload.images,
    )

@router.post("/api/v1/sessions/{session_id}/messages/{message_id}/regenerate", response_model=MessageResponse, tags=["Messages"])
async def regenerate_message(
    session_id: str,
    message_id: str,
    payload: MessageRegenerateRequest,
    db: SQLAlchemySession = Depends(get_db),
):
    """Regenerate an assistant response. Re-runs inference from the corresponding user prompt."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    target_msg = db.query(MessageModel).filter(MessageModel.id == message_id, MessageModel.session_id == session_id).first()
    if not target_msg:
        raise HTTPException(status_code=404, detail=f"Message '{message_id}' not found")

    if target_msg.role == "assistant":
        # Find immediately preceding user message
        user_msg = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session_id, MessageModel.role == "user", MessageModel.created_at <= target_msg.created_at)
            .order_by(MessageModel.created_at.desc())
            .first()
        )
        if not user_msg:
            raise HTTPException(status_code=400, detail="No preceding user message found to regenerate")

        subsequent = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session_id, MessageModel.created_at >= target_msg.created_at)
            .all()
        )
        for s in subsequent:
            db.query(ArtifactModel).filter(ArtifactModel.message_id == s.id).delete()
            db.delete(s)
        db.commit()

        user_content = user_msg.content
        mode = user_msg.mode or "research"
    else:
        subsequent = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session_id, MessageModel.created_at > target_msg.created_at)
            .all()
        )
        for s in subsequent:
            db.query(ArtifactModel).filter(ArtifactModel.message_id == s.id).delete()
            db.delete(s)
        db.commit()

        user_content = target_msg.content
        mode = target_msg.mode or "research"

    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(db=db)
    return orchestrator.execute_turn(
        session_id=session_id,
        content=user_content,
        mode=mode,
        research_mode=payload.research_mode or "auto",
        provider_override=payload.provider_override,
    )

# ============================================================================
# Artifact Endpoints
# ============================================================================

@router.get("/api/v1/artifacts/{artifact_id}", response_model=ArtifactResponse, tags=["Artifacts"])
async def get_artifact(artifact_id: str, db: SQLAlchemySession = Depends(get_db)):
    """Fetch sanitized operational artifact for sandboxed rendering."""
    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{artifact_id}' not found",
        )
    return ArtifactResponse(**artifact.to_dict())

@router.get("/api/v1/artifacts/{artifact_id}/iframe", response_class=HTMLResponse, tags=["Artifacts"])
async def get_artifact_iframe(artifact_id: str, db: SQLAlchemySession = Depends(get_db)):
    """Render an operational artifact inside a sandboxed HTML document with strict CSP."""
    from app.services.artifact_renderer import render_sandboxed_artifact, get_sandbox_security_headers

    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{artifact_id}' not found",
        )

    html_content = render_sandboxed_artifact(artifact)
    headers = get_sandbox_security_headers()
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK, headers=headers)

# ============================================================================
# Retrieval Telemetry Endpoint
# ============================================================================

from app.retrieval.retriever import retrieve_evidence

@router.post("/api/v1/retrieve", response_model=RetrieveResponse, tags=["Retrieval"])
async def retrieve_context(payload: RetrieveRequest, db: SQLAlchemySession = Depends(get_db)):
    """Direct retrieval query testing grounding evidence against transcript chunks."""
    result = retrieve_evidence(query=payload.query, db=db, top_k=payload.top_k)
    return RetrieveResponse(
        query=result.query,
        chunks=[
            CitationSchema(
                chunk_id=ev.chunk_id,
                guest=ev.guest,
                title=ev.title,
                similarity=ev.similarity,
                excerpt=ev.excerpt,
            )
            for ev in result.evidence
        ],
        top_similarity=result.top_similarity,
        grounded=result.grounded,
        latency_ms=result.latency_ms,
    )

# ============================================================================
# File Upload & Document Intelligence Endpoint
# ============================================================================

from fastapi import UploadFile, File

@router.post("/api/files/upload", tags=["Files"])
@router.post("/api/v1/files/upload", tags=["Files"])
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None),
    session_id_form: Optional[str] = Form(None),
):
    """Parse an uploaded file and return structured text content for session injection.

    Supports: PDF, DOCX, XLSX, CSV, JSON, plain text, source code (20+ languages).
    Returns structured content with metadata, ready to be included in a message context.
    """
    effective_session_id = session_id or session_id_form
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB cap

    filename = file.filename or "uploaded_file"
    data = await file.read()

    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {len(data) // 1024}KB exceeds 10MB limit.",
        )

    from app.services.file_intelligence import get_unified_file_parser
    parser = get_unified_file_parser()
    parsed = parser.parse_bytes(filename, data)

    doc_id = None
    if effective_session_id and parsed.is_success and parsed.content:
        try:
            from app.db.session import get_db_session
            from app.db.models import UploadedDocument, Session as SessionModel
            with get_db_session() as db:
                sess = db.query(SessionModel).filter(SessionModel.id == effective_session_id).first()
                if not sess:
                    sess = SessionModel(id=effective_session_id, title=f"File: {parsed.filename}")
                    db.add(sess)
                    db.commit()
                doc = UploadedDocument(
                    session_id=effective_session_id,
                    filename=parsed.filename,
                    file_type=parsed.file_type.value,
                    extracted_text=parsed.content,
                    char_count=len(parsed.content),
                    summary=parsed.content[:500],
                )
                db.add(doc)
                db.commit()
                doc_id = doc.id
        except Exception as e:
            logger.warning("Error persisting uploaded document to session %s: %s", effective_session_id, e)

    return {
        "filename": parsed.filename,
        "file_type": parsed.file_type.value,
        "mime_type": parsed.mime_type,
        "page_count": parsed.page_or_row_count,
        "metadata": parsed.metadata,
        "content_length": len(parsed.content),
        "truncated": parsed.truncated,
        "parse_error": parsed.error,
        "context_string": parsed.to_context_string(),
        "is_success": parsed.is_success,
        "session_id": effective_session_id,
        "document_id": doc_id,
    }


@router.post("/api/v1/files/intelligence", tags=["Files"])
async def process_file_intelligence(
    file: UploadFile = File(...),
    operation: str = Form("summarize"),
    query: Optional[str] = Form(None),
    target_format: Optional[str] = Form("json"),
):
    """Execute unified file intelligence: summarize, qa, analyze, extract, transform, or combine with web research."""
    from app.services.file_intelligence import get_unified_file_parser, get_file_intelligence_engine, FileOperation

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    parser = get_unified_file_parser()
    parsed_file = parser.parse_bytes(file.filename or "uploaded_file", data)
    engine = get_file_intelligence_engine()

    op_norm = operation.lower().strip()
    if op_norm == "summarize":
        res = engine.summarize(parsed_file, focus=query)
        return res.model_dump()
    elif op_norm in ("qa", "ask", "question"):
        res = engine.ask_question(parsed_file, question=query or "What is the main topic of this file?")
        return res.model_dump()
    elif op_norm == "analyze":
        res = engine.analyze(parsed_file, aspect=query)
        return res.model_dump()
    elif op_norm == "extract":
        fields = [f.strip() for f in (query or "key metrics, dates, entities").split(",")]
        res = engine.extract_information(parsed_file, target_fields=fields)
        return res.model_dump()
    elif op_norm == "transform":
        res = engine.transform_information(parsed_file, target_format=target_format or "json", instructions=query)
        return res.model_dump()
    elif op_norm in ("combine", "combine_research", "combine_with_web_research"):
        res = await engine.combine_with_web_research_async(parsed_file, research_query=query or parsed_file.filename)
        return res.model_dump()
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file operation: {operation}")


# ============================================================================
# Autonomous Agent Task Endpoint
# ============================================================================

from app.api.schemas import AgentTaskRequest, AgentTaskResponse, AgentTaskStep

@router.post("/api/v1/agent/run_task", response_model=AgentTaskResponse, tags=["Autonomous Agent"])
@router.post("/api/agent/run_task", response_model=AgentTaskResponse, tags=["Autonomous Agent"])
async def run_autonomous_task(payload: AgentTaskRequest):
    """Execute an autonomous 9-phase software engineering and repository lifecycle task:
    INSPECT -> UNDERSTAND -> PLAN -> MODIFY -> BUILD -> TEST -> FIX -> RETEST -> REVIEW.
    """
    from app.coding.repo_engine import RepoTaskEngine
    engine = RepoTaskEngine()
    summary = engine.execute_lifecycle(
        task_description=payload.task_description,
        target_files=payload.target_files or [],
        test_target=payload.test_target,
    )

    phases_out = [
        AgentTaskStep(
            phase=p.phase.value if hasattr(p.phase, 'value') else str(p.phase),
            status=p.status,
            details=p.details,
            duration_ms=round(p.duration_ms, 2),
            exit_code=p.exit_code,
        )
        for p in summary.phases_executed
    ]
    return AgentTaskResponse(
        task_description=summary.task_description,
        all_passed=summary.all_passed,
        build_verified=summary.build_verified,
        test_verified=summary.test_verified,
        total_duration_ms=round(summary.total_duration_ms, 2),
        files_modified=summary.files_modified,
        phases_executed=phases_out,
    )

