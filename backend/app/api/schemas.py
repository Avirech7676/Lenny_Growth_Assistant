"""Pydantic request and response schemas with strict validation."""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

# ============================================================================
# Health & Diagnostics Schemas
# ============================================================================

class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall health state")
    version: str = Field(default="2.0.0", description="API version")
    environment: str = Field(default="development", description="Environment profile")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")

class DBHealthResponse(BaseModel):
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    engine: str = Field(..., description="'postgresql+pgvector' or 'sqlite_fallback'")
    latency_ms: float = Field(..., description="Round-trip ping latency in milliseconds")
    details: Optional[Dict[str, Any]] = None

class LLMHealthResponse(BaseModel):
    status: str = Field(..., description="'healthy' or 'degraded'")
    provider: str = Field(..., description="Active provider: 'ollama', 'anthropic', 'openai'")
    active_model: str = Field(..., description="Active model identifier")
    latency_ms: float = Field(..., description="Ping latency to inference engine")
    fallback_ready: bool = Field(default=False, description="Whether cloud fallback is configured")
    fallback_provider: Optional[str] = None

# ============================================================================
# Citation & Artifact Schemas
# ============================================================================

class CitationSchema(BaseModel):
    chunk_id: str = Field(..., description="Transcript chunk UUID")
    guest: str = Field(..., description="Podcast guest name")
    title: str = Field(..., description="Episode or article title")
    similarity: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    excerpt: str = Field(..., description="Grounded transcript excerpt text")

class ArtifactSummary(BaseModel):
    id: str
    artifact_type: str
    title: str
    status: str
    created_at: Optional[str] = None

class ArtifactResponse(BaseModel):
    id: str
    session_id: str
    message_id: Optional[str] = None
    artifact_type: str
    title: str
    sanitized_content: str
    status: str
    created_at: Optional[str] = None

# ============================================================================
# Session Schemas
# ============================================================================

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default="New Growth Session", max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionDetailResponse(SessionResponse):
    message_count: int = 0
    artifacts: List[ArtifactSummary] = Field(default_factory=list)

# ============================================================================
# Message & Conversation Schemas
# ============================================================================

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="User prompt text")
    mode: Literal["research", "ship30", "experiment", "playbook"] = Field(
        default="research",
        description="Target skill execution mode",
    )
    provider_override: Optional[Literal["ollama", "anthropic", "openai"]] = Field(
        default=None,
        description="Optional model provider override",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be blank or whitespace-only")
        return v

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    mode: str
    model: str
    latency_ms: float = 0.0
    citations: List[CitationSchema] = Field(default_factory=list)
    artifacts: List[ArtifactSummary] = Field(default_factory=list)
    created_at: Optional[str] = None

# ============================================================================
# Retrieval Schemas
# ============================================================================

class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    top_k: int = Field(default=4, ge=1, le=10, description="Max candidate chunks")

class RetrieveResponse(BaseModel):
    query: str
    chunks: List[CitationSchema]
    top_similarity: float
    grounded: bool
    latency_ms: float

# ============================================================================
# Structured Error Schema
# ============================================================================

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    request_id: Optional[str] = Field(None, description="Correlated request ID")
    error_code: str = Field(default="BAD_REQUEST", description="Machine-readable error code")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
