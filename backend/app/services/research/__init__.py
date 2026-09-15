"""Model-Independent Deep Research Engine Package."""

from app.services.research.models import (
    ResearchConstraint,
    ResearchObjective,
    VerifiedClaim,
    ResearchReport,
    ResearchResult,
)
from app.services.research.source_filter import (
    parse_research_constraints,
    apply_source_filters,
)
from app.services.research.engine import (
    DeepResearchEngine,
    get_deep_research_engine,
)
from app.services.research.pipeline import (
    EvidenceResearchPipeline,
    get_research_pipeline,
    EvidencePipelineResult,
    StageTelemetry,
)

__all__ = [
    "ResearchConstraint",
    "ResearchObjective",
    "VerifiedClaim",
    "ResearchReport",
    "ResearchResult",
    "parse_research_constraints",
    "apply_source_filters",
    "DeepResearchEngine",
    "get_deep_research_engine",
    "EvidenceResearchPipeline",
    "get_research_pipeline",
    "EvidencePipelineResult",
    "StageTelemetry",
]
