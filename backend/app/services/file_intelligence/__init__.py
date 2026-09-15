"""Unified File Intelligence System package."""

from app.services.file_intelligence.models import (
    FileType,
    FileOperation,
    ParsedFile,
    EvidenceBlock,
    FileAnalysisResult,
    MultiFileComparisonResult,
    CombinedResearchAnalysisResult,
)
from app.services.file_intelligence.parser import (
    UnifiedFileParser,
    get_unified_file_parser,
)
from app.services.file_intelligence.engine import (
    FileIntelligenceEngine,
    get_file_intelligence_engine,
)

__all__ = [
    "FileType",
    "FileOperation",
    "ParsedFile",
    "EvidenceBlock",
    "FileAnalysisResult",
    "MultiFileComparisonResult",
    "CombinedResearchAnalysisResult",
    "UnifiedFileParser",
    "get_unified_file_parser",
    "FileIntelligenceEngine",
    "get_file_intelligence_engine",
]
