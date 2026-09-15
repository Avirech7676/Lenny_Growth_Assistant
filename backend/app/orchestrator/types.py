"""Type definitions and contracts for Unified AI Orchestrator.

Defines:
- Capability Enum (14 full-spectrum capabilities)
- IntentProfile
- TaskStep & ExecutionPlan
- VerificationResult
- OrchestratorRequest & OrchestratorResponse
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Capability(str, Enum):
    """Full-spectrum operational capabilities supported by the unified AI Orchestrator."""
    GENERAL_QA = "GENERAL_QA"
    RESEARCH = "RESEARCH"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    CODING = "CODING"
    DEBUGGING = "DEBUGGING"
    CODE_REVIEW = "CODE_REVIEW"
    ARCHITECTURE = "ARCHITECTURE"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    WRITING = "WRITING"
    PLANNING = "PLANNING"
    ARTIFACT_GENERATION = "ARTIFACT_GENERATION"
    LENNY_RESEARCH = "LENNY_RESEARCH"
    HYBRID_TASK = "HYBRID_TASK"


@dataclass
class IntentProfile:
    """Detailed semantic intent representation of a user query."""
    primary_goal: str
    domains: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    is_time_sensitive: bool = False
    requires_external_web: bool = False
    requires_lenny_knowledge: bool = False
    requires_workspace_code: bool = False
    complexity: str = "moderate"  # "simple", "moderate", "complex"
    constraints: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class TaskStep:
    """Individual execution step within a compound multi-capability plan."""
    step_id: int
    capability: Capability
    name: str
    description: str
    tool_required: Optional[str] = None
    target_model_profile: str = "auto"  # "coding", "research", "fast", "general"
    status: str = "pending"  # "pending", "running", "completed", "failed"
    output: Optional[Any] = None


@dataclass
class ExecutionPlan:
    """Coordinated multi-step pipeline generated for a request."""
    plan_id: str
    capabilities: List[Capability]
    steps: List[TaskStep]
    is_compound: bool = False
    estimated_latency_tier: str = "fast"  # "instant", "fast", "standard", "deep"
    rationale: str = ""


@dataclass
class VerificationResult:
    """Quality and epistemic validation outcome."""
    is_verified: bool
    grounding_score: float  # 0.0 to 1.0
    code_syntax_valid: Optional[bool] = None
    live_execution_verified: Optional[bool] = None
    citation_integrity_valid: bool = True
    adheres_to_constraints: bool = True
    issues: List[str] = field(default_factory=list)
    corrections_applied: List[str] = field(default_factory=list)


@dataclass
class OrchestratorRequest:
    """Unified request passed to the AI Orchestrator."""
    query: str
    session_id: str = "default_session"
    user_mode: str = "auto"
    provider_override: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    context_override: Optional[str] = None
    stream: bool = False
    client_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResponse:
    """Unified response produced by the AI Orchestrator."""
    content: str
    session_id: str
    selected_capabilities: List[Capability]
    plan: ExecutionPlan
    model_used: str
    provider_used: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    verification: Optional[VerificationResult] = None
    latency_breakdown: Dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    status: str = "SUCCESS"
