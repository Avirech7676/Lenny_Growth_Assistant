"""Base types, enums, dataclasses, and abstract interfaces for the Multi-Source Research Engine."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
import re

class SourceCategory(str, Enum):
    """11 canonical source categories for question-aware evidence routing."""
    OFFICIAL = "official"          # Primary docs, company sites, regulatory bodies, standards
    ACADEMIC = "academic"          # Peer-reviewed papers, arXiv, PubMed, universities
    NEWS = "news"                  # Reputable news organizations, wire services, sports journalism
    INDUSTRY = "industry"          # Analyst reports, professional orgs, tech benchmark publications
    COMMUNITY = "community"        # Reddit, Stack Overflow, developer forums, practitioner discussions
    TECHNICAL = "technical"        # GitHub, GitLab, package registries (npm, PyPI), API references
    REFERENCE = "reference"        # Wikipedia, encyclopedias, general reference databases
    FINANCIAL = "financial"        # SEC filings, investor relations, financial databases, central banks
    GOVERNMENT = "government"      # Government datasets, statistical agencies, official records
    PRODUCT = "product"            # Hardware manufacturers, spec sheets, reputable review publications
    USER_PROVIDED = "user_provided"# User-uploaded PDFs, documents, text files, custom URLs

class ResearchDepth(str, Enum):
    """5-level adaptive research depth controller."""
    DIRECT = "direct"              # Level 0: Fast direct answer, no external search needed
    TARGETED = "targeted"          # Level 1: 1-3 targeted high-authority sources
    STANDARD = "standard"          # Level 2: 3-7 sources across 2+ categories
    DEEP_MULTI_QUERY = "deep"      # Level 3: 3-6 sub-queries, 5-15 sources across categories
    EXHAUSTIVE = "exhaustive"      # Level 4: Multi-round iterative cross-checking and citation audit

class EvidenceStrength(str, Enum):
    """Qualitative evidence strength rating (no fabricated percentage confidences)."""
    STRONG = "Strong"              # Multiple independent authoritative primary sources agree
    MODERATE = "Moderate"          # Secondary sources agree, or single primary source confirmed
    LIMITED = "Limited"            # Sparse independent corroboration or conflicting reports detected

class FreshnessRequirement(str, Enum):
    """Freshness classification for questions."""
    STABLE = "stable"              # Stable conceptual knowledge, timeless explanations
    RECENT = "recent"              # Recent developments (past 6-12 months)
    CURRENT = "current"            # Current state (2026/current year)
    LATEST = "latest"              # Latest/live information (current version, latest race, breaking news)
    HISTORICAL = "historical"      # Specific past period or archive

@dataclass
class DiscoveredSource:
    """Rich source representation with categorization and quality metadata."""
    title: str
    url: str
    domain: str
    snippet: str
    category: SourceCategory = SourceCategory.REFERENCE
    authority_score: float = 0.85
    freshness: FreshnessRequirement = FreshnessRequirement.STABLE
    published_date: Optional[str] = None
    source_type: str = "external"
    is_primary: bool = False
    independence_key: str = ""
    why_useful: str = ""

    def __post_init__(self):
        if not self.independence_key:
            # Normalized domain + key title words for syndication detection
            cleaned_title = re.sub(r'[^a-zA-Z0-9]', '', self.title.lower())[:32]
            self.independence_key = f"{self.domain}:{cleaned_title}"

@dataclass
class ResearchPlan:
    """Internal research plan for query decomposition and category targeting."""
    depth: ResearchDepth
    domain: str
    sub_queries: List[str]
    target_categories: List[SourceCategory]
    freshness: FreshnessRequirement
    status_message: str

@dataclass
class ResearchConflict:
    """Detected disagreement or contradiction between sources."""
    topic: str
    source_a: str
    claim_a: str
    source_b: str
    claim_b: str
    explanation: str

@dataclass
class ResearchSynthesis:
    """Complete research synthesis outcome."""
    query: str
    plan: ResearchPlan
    discovered_sources: List[DiscoveredSource] = field(default_factory=list)
    used_sources: List[DiscoveredSource] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=dict)
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    conflicts: List[ResearchConflict] = field(default_factory=list)
    synthesis_context: str = ""
    latency_ms: float = 0.0

class SearchProvider(ABC):
    """Abstract base class for pluggable search providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Name of the search provider."""
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Synchronous search execution."""
        pass

    @abstractmethod
    async def search_async(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Asynchronous search execution."""
        pass
