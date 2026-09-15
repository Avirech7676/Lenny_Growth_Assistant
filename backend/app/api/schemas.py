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
    provider: str = Field(..., description="Active provider: 'openai', 'anthropic', 'gemini', 'groq', 'ollama'")
    active_model: str = Field(..., description="Active model identifier")
    latency_ms: float = Field(..., description="Ping latency to inference engine")
    fallback_ready: bool = Field(default=False, description="Whether cloud fallback is configured")
    fallback_provider: Optional[str] = None
    routing_rationale: Optional[str] = None
    providers: Optional[Dict[str, Any]] = None

# ============================================================================
# Citation & Artifact Schemas
# ============================================================================

class CitationSchema(BaseModel):
    chunk_id: str = Field(..., description="Transcript chunk UUID or external source identifier")
    guest: str = Field(..., description="Podcast guest name or external source author/authority")
    title: str = Field(..., description="Episode, article, or document title")
    similarity: float = Field(..., description="Cosine similarity score or relevance confidence (0.0 to 1.0)")
    excerpt: str = Field(..., description="Grounded excerpt or factual summary")
    source_type: Literal["transcript", "external", "synthesis"] = Field(
        default="transcript",
        description="Origin of knowledge: 'transcript' (Lenny), 'external' (real-world web), 'synthesis' (strategic model inference)",
    )
    url: Optional[str] = Field(default=None, description="External reference URL if available")
    domain: Optional[str] = Field(default=None, description="Source domain identifier (e.g., openview.com, react.dev)")
    source_category: Optional[str] = Field(default="reference", description="11-category classification (official, academic, news, etc.)")
    evidence_strength: Optional[str] = Field(default="Moderate", description="Qualitative rating: Strong, Moderate, or Limited")
    why_useful: Optional[str] = Field(default=None, description="Explanation of why this source was useful")


class LatencyMetrics(BaseModel):
    ttft_ms: float = Field(default=0.0, description="Time to first token in milliseconds")
    retrieval_ms: float = Field(default=0.0, description="Knowledge retrieval and routing latency in milliseconds")
    llm_ms: float = Field(default=0.0, description="Inference and token generation latency in milliseconds")
    total_ms: float = Field(default=0.0, description="End-to-end turn latency in milliseconds")

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

class SessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255, description="Updated session title")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Updated metadata dict")

class SessionSearchResult(BaseModel):
    id: str
    title: str
    match_type: Literal["title", "message"]
    matched_snippet: str
    message_count: int = 0
    updated_at: Optional[str] = None

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
    mode: Optional[str] = Field(
        default="research",
        description="Target skill execution mode (chat, search, deep_research, coding, lenny, ship30, etc.)",
    )
    research_mode: Optional[Literal["auto", "search", "deep_research", "deep"]] = Field(
        default="auto",
        description="Dynamic research depth: 'auto' (adaptive), 'search' (targeted/web), 'deep_research' (multi-query)",
    )
    provider_override: Optional[Literal["auto", "ollama", "anthropic", "openai", "gemini", "groq", "fallback"]] = Field(
        default=None,
        description="Optional model provider override ('auto', 'openai', 'anthropic', 'gemini', 'groq', 'ollama')",
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="Optional list of image URLs or base64 data URIs for multimodal queries",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be blank or whitespace-only")
        return v

class MessageEditRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Revised user prompt text")
    mode: Optional[str] = Field(default="research", description="Optional mode override")
    research_mode: Optional[str] = Field(default="auto", description="Optional research depth")
    provider_override: Optional[str] = Field(default=None, description="Optional provider override")
    images: Optional[List[str]] = Field(default=None, description="Optional image URLs or base64 data URIs")

class MessageRegenerateRequest(BaseModel):
    provider_override: Optional[str] = Field(default=None, description="Optional provider override for re-execution")
    research_mode: Optional[str] = Field(default=None, description="Optional research mode override")

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    mode: str
    model: str
    latency_ms: float = 0.0
    intelligence_mode: Optional[Literal["lenny", "real_world", "hybrid", "direct"]] = Field(
        default=None,
        description="Multi-source intelligence mode: 'lenny' (Mode A), 'real_world' (Mode B), 'hybrid' (Mode C), 'direct'",
    )
    capability: Optional[str] = Field(
        default=None,
        description="Resolved agent capability (e.g., coding, debugging, architecture, web_research, general_qa, lenny_research)",
    )
    research_depth: Optional[str] = Field(
        default=None,
        description="Resolved research depth: 'direct', 'targeted', 'standard', 'deep'",
    )
    evidence_strength: Optional[str] = Field(
        default=None,
        description="Qualitative evidence strength: 'Strong', 'Moderate', 'Limited'",
    )
    category_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Count of discovered sources by category",
    )
    latency_metrics: Optional[LatencyMetrics] = Field(
        default=None,
        description="Component-level latency observability breakdown (TTFT, retrieval, LLM)",
    )
    citations: List[CitationSchema] = Field(default_factory=list)
    artifacts: List[ArtifactSummary] = Field(default_factory=list)
    quality_score: Optional[float] = Field(default=None, description="Quality gate score (0.0 - 1.0)")
    quality_passed: Optional[bool] = Field(default=None, description="Whether response passed quality gate verification")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Contextual next-step follow-up prompt chips")
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


# ============================================================================
# Autonomous Agent Task Schemas
# ============================================================================

class AgentTaskRequest(BaseModel):
    task_description: str = Field(..., min_length=1, max_length=5000, description="Autonomous goal or task instructions")
    target_files: Optional[List[str]] = Field(default_factory=list, description="Target file paths to inspect or modify")
    test_target: Optional[str] = Field(default=None, description="Optional pytest target to run during verification")
    auto_confirm: bool = Field(default=False, description="Whether to execute without human-in-the-loop pause")


class AgentTaskStep(BaseModel):
    phase: str
    status: str
    details: str
    duration_ms: float = 0.0
    exit_code: Optional[int] = None


class AgentTaskResponse(BaseModel):
    task_description: str
    all_passed: bool
    build_verified: bool
    test_verified: bool
    total_duration_ms: float
    files_modified: List[str] = Field(default_factory=list)
    phases_executed: List[AgentTaskStep] = Field(default_factory=list)


class ModelSelectRequest(BaseModel):
    provider: str = Field(default="ollama", description="Provider ID (e.g. ollama, gemini, anthropic, openai)")
    model: str = Field(default="llama3.2", description="Model name (e.g. llama3.2, claude-3-5-sonnet, gpt-4o)")


class ClaudeAgentExecutionRequest(BaseModel):
    query: str = Field(..., description="User query to process via Claude Agent SDK and MCP tools")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")


