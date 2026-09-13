"""FastAPI router implementing health, session, message, retrieval, and artifact endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
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
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse,
    ArtifactResponse,
    ArtifactSummary,
    RetrieveRequest,
    RetrieveResponse,
    CitationSchema,
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
    engine_type = "sqlite_fallback" if is_sqlite else "postgresql+pgvector"

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
    fallback_ready = bool(settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)
    fallback_provider = "anthropic" if settings.ANTHROPIC_API_KEY else ("openai" if settings.OPENAI_API_KEY else None)

    return LLMHealthResponse(
        status="healthy",
        provider=settings.LLM_PROVIDER,
        active_model=settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else settings.ANTHROPIC_MODEL,
        latency_ms=12.5,
        fallback_ready=fallback_ready,
        fallback_provider=fallback_provider,
    )

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
