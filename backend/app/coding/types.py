"""Type definitions and contracts for the first-class Coding Agent and execution sandbox."""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CodingCapability(str, Enum):
    """12 first-class coding capabilities supported by the Coding Agent."""
    CODE_GENERATION = "code_generation"
    CODE_EXPLANATION = "code_explanation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    OPTIMIZATION = "optimization"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    ARCHITECTURE = "architecture"
    REPOSITORY_ANALYSIS = "repository_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    API_IMPLEMENTATION = "api_implementation"
    DATABASE_IMPLEMENTATION = "database_implementation"


class RepoTaskPhase(str, Enum):
    """9-stage lifecycle pipeline for repository tasks."""
    INSPECT = "INSPECT"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    MODIFY = "MODIFY"
    BUILD = "BUILD"
    TEST = "TEST"
    FIX = "FIX"
    RETEST = "RETEST"
    REVIEW = "REVIEW"


class ExecutionLanguage(str, Enum):
    """Supported sandbox execution and validation languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    SQL = "sql"
    FASTAPI = "fastapi"
    REACT = "react"


class SandboxSecurityPolicy(BaseModel):
    """Security rules governing isolated sandbox execution."""
    banned_modules: List[str] = Field(
        default_factory=lambda: [
            "ctypes", "pty", "posix", "nt", "_thread", "socket", 
            "subprocess", "asyncio.subprocess", "shutil"
        ]
    )
    banned_calls: List[str] = Field(
        default_factory=lambda: ["fork", "kill", "system", "popen", "spawn", "execv", "execve"]
    )
    max_timeout_seconds: float = 15.0
    max_memory_mb: int = 512
    allow_network: bool = False


class SandboxExecutionRequest(BaseModel):
    """Request payload for sandboxed execution."""
    language: ExecutionLanguage
    code: str
    entrypoint: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    timeout_seconds: float = 10.0
    context_schema: Optional[str] = None  # DDL for SQL, Pydantic schemas for FastAPI, etc.


class SandboxExecutionResult(BaseModel):
    """Structured result returned from the execution sandbox."""
    success: bool
    language: ExecutionLanguage
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    verified: bool = False
    sandbox_used: str = "epistemic-sandbox"
    security_violation: Optional[str] = None
    parsed_output: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RepoInspectionResult(BaseModel):
    """Inspection output from scanning a real repository."""
    root_path: str
    total_files: int
    detected_frameworks: List[str]
    package_manifests: List[str]
    languages_detected: List[str]
    git_branch: Optional[str] = None
    git_clean: bool = True
    key_directories: List[str] = Field(default_factory=list)


class DependencyGraph(BaseModel):
    """Analysis of project dependencies and vulnerabilities/updates."""
    manifest_file: str
    dependencies: Dict[str, str] = Field(default_factory=dict)
    dev_dependencies: Dict[str, str] = Field(default_factory=dict)
    vulnerabilities_detected: int = 0
    deprecated_packages: List[str] = Field(default_factory=list)


class RepoStepResult(BaseModel):
    """Result of a single phase in the repository task pipeline."""
    phase: RepoTaskPhase
    status: str  # "completed", "failed", "skipped"
    details: str
    artifacts_generated: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    exit_code: Optional[int] = None


class RepoExecutionSummary(BaseModel):
    """Complete summary of a repository task run through all 9 phases."""
    task_description: str
    phases_executed: List[RepoStepResult] = Field(default_factory=list)
    all_passed: bool = False
    total_duration_ms: float = 0.0
    files_modified: List[str] = Field(default_factory=list)
    build_verified: bool = False
    test_verified: bool = False


class CodingAgentRequest(BaseModel):
    """Input to the first-class Coding Agent."""
    capability: CodingCapability
    prompt: str
    language: Optional[ExecutionLanguage] = ExecutionLanguage.PYTHON
    code_snippet: Optional[str] = None
    repo_path: Optional[str] = None
    execute_in_sandbox: bool = True
    target_files: Optional[List[str]] = None


class CodingAgentResponse(BaseModel):
    """Final output from the first-class Coding Agent."""
    capability: CodingCapability
    explanation: str
    generated_code: Optional[str] = None
    execution_result: Optional[SandboxExecutionResult] = None
    repo_summary: Optional[RepoExecutionSummary] = None
    test_cases: Optional[List[str]] = None
    review_findings: Optional[List[Dict[str, Any]]] = None
    verified: bool = False
    model_used: str = "coding-agent"
    duration_ms: float = 0.0
