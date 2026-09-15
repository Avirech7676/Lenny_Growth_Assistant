"""Data models and contracts for the Unified File Intelligence System."""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file categories."""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    TXT = "txt"
    MARKDOWN = "markdown"
    CODE = "code"
    IMAGE = "image"
    UNKNOWN = "unknown"


class FileOperation(str, Enum):
    """User operations supported on files."""
    SUMMARIZE = "summarize"
    QA = "qa"
    ANALYZE = "analyze"
    COMPARE = "compare"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    COMBINE_WITH_WEB_RESEARCH = "combine_with_web_research"


@dataclass
class ParsedFile:
    """Standardized parsed file representation."""
    filename: str
    file_type: FileType
    mime_type: str
    content: str
    page_or_row_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    truncated: bool = False
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None

    def to_context_string(self) -> str:
        """Render standard grounded context block."""
        header = f"[FILE: {self.filename} | TYPE: {self.file_type.value.upper()} | METRIC: {self.page_or_row_count}]"
        meta_str = ", ".join(f"{k}={v}" for k, v in list(self.metadata.items())[:5]) if self.metadata else ""
        meta_line = f"[METADATA: {meta_str}]\n" if meta_str else ""
        warning = f"[WARNING: {self.error}]\n" if self.error else ""
        return f"{header}\n{meta_line}{warning}\n{self.content}"


class EvidenceBlock(BaseModel):
    """Explicitly distinguished evidence source block."""
    source_type: str  # "USER_FILE", "CURRENT_WEB_RESEARCH", "ANALYSIS"
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileAnalysisResult(BaseModel):
    """Structured outcome for single file operations."""
    operation: FileOperation
    filename: str
    file_type: FileType
    summary_or_answer: str
    extracted_data: Optional[Dict[str, Any]] = None
    transformed_content: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceBlock] = Field(default_factory=list)
    latency_ms: float = 0.0


class MultiFileComparisonResult(BaseModel):
    """Structured outcome for multi-file comparisons."""
    operation: FileOperation = FileOperation.COMPARE
    filenames: List[str]
    comparison_summary: str
    contrast_matrix: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    shared_themes: List[str] = Field(default_factory=list)
    key_differences: List[str] = Field(default_factory=list)
    evidence: List[EvidenceBlock] = Field(default_factory=list)
    latency_ms: float = 0.0


class CombinedResearchAnalysisResult(BaseModel):
    """Structured outcome combining User File + Current Web Research + Analysis."""
    operation: FileOperation = FileOperation.COMBINE_WITH_WEB_RESEARCH
    filename: str
    research_query: str
    user_file_evidence: str
    web_research_evidence: str
    comparative_analysis: str
    key_takeaways: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_blocks: List[EvidenceBlock] = Field(default_factory=list)
    latency_ms: float = 0.0

    def to_formatted_report(self) -> str:
        """Render distinct three-part evidence report."""
        divider = "═" * 68
        return (
            f"{divider}\n"
            f"1. [EVIDENCE SOURCE: USER FILE]\n"
            f"Document: {self.filename}\n"
            f"{self.user_file_evidence.strip()}\n\n"
            f"{divider}\n"
            f"2. [EVIDENCE SOURCE: CURRENT WEB RESEARCH]\n"
            f"Query: {self.research_query}\n"
            f"{self.web_research_evidence.strip()}\n\n"
            f"{divider}\n"
            f"3. [ANALYSIS & SYNTHESIS]\n"
            f"{self.comparative_analysis.strip()}\n"
            f"{divider}"
        )
