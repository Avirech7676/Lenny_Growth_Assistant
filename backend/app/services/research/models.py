"""Data models and immutable contracts for the Model-Independent Research Engine."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.services.search.base import (
    DiscoveredSource,
    ResearchPlan,
    ResearchConflict,
    SourceCategory,
    ResearchDepth,
    EvidenceStrength,
    FreshnessRequirement,
)


@dataclass
class ResearchConstraint:
    """User-specified or inferred constraints on sources and depth."""
    allowed_categories: Optional[List[SourceCategory]] = None
    excluded_domains: List[str] = field(default_factory=list)
    prioritized_domains: List[str] = field(default_factory=list)
    only_official: bool = False
    only_academic: bool = False
    only_government: bool = False
    time_window_days: Optional[int] = None


@dataclass
class ResearchObjective:
    """Explicitly formulated research objective."""
    query: str
    target_depth: ResearchDepth
    domain: str
    constraints: ResearchConstraint = field(default_factory=ResearchConstraint)


@dataclass
class VerifiedClaim:
    """Individual factual claim evaluated against source evidence."""
    statement: str
    supporting_urls: List[str] = field(default_factory=list)
    evidence_snippets: List[str] = field(default_factory=list)
    independent_sources: List[str] = field(default_factory=list)
    status: str = "verified"     # "verified", "disputed", "unconfirmed"
    confidence: str = "high"     # "high", "moderate", "low"
    verification_method: str = "multi_source_cross_reference"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "supporting_urls": self.supporting_urls,
            "evidence_snippets": self.evidence_snippets,
            "independent_sources": self.independent_sources,
            "status": self.status,
            "confidence": self.confidence,
            "verification_method": self.verification_method,
        }


@dataclass
class ResearchReport:
    """Structured, professional deep research report output."""
    title: str
    executive_summary: str
    key_findings: List[str] = field(default_factory=list)
    verified_claims: List[VerifiedClaim] = field(default_factory=list)
    evidence_synthesis: str = ""
    comparisons: Optional[Dict[str, Any]] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    implications: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    independent_sources_count: int = 0
    research_rounds: int = 1
    evidence_strength: str = "Strong"
    depth: str = "standard"
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "evidence_synthesis": self.evidence_synthesis,
            "comparisons": self.comparisons or {},
            "conflicts": self.conflicts,
            "implications": self.implications,
            "recommendations": self.recommendations,
            "sources": self.sources,
            "citations": self.citations,
            "independent_sources_count": self.independent_sources_count,
            "research_rounds": self.research_rounds,
            "evidence_strength": self.evidence_strength,
            "depth": self.depth,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ResearchResult:
    """Immutable, model-independent research outcome that any LLM can synthesize."""
    query: str
    objective: ResearchObjective
    plan: ResearchPlan
    discovered_sources: List[DiscoveredSource] = field(default_factory=list)
    used_sources: List[DiscoveredSource] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=dict)
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    conflicts: List[ResearchConflict] = field(default_factory=list)
    report: Optional[ResearchReport] = None
    synthesis_context: str = ""
    independent_sources_count: int = 0
    research_rounds: int = 1
    latency_ms: float = 0.0

    @property
    def context_str(self) -> str:
        """Backward-compatible alias for synthesis_context."""
        return self.synthesis_context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "depth": self.plan.depth.value if hasattr(self.plan.depth, "value") else str(self.plan.depth),
            "domain": self.plan.domain,
            "sources_count": len(self.used_sources),
            "independent_sources_count": self.independent_sources_count,
            "research_rounds": self.research_rounds,
            "evidence_strength": self.evidence_strength.value if hasattr(self.evidence_strength, "value") else str(self.evidence_strength),
            "category_breakdown": self.category_counts,
            "conflicts_count": len(self.conflicts),
            "report": self.report.to_dict() if self.report else None,
            "latency_ms": round(self.latency_ms, 2),
        }
