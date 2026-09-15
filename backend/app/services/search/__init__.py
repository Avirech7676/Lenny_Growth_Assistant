"""Multi-Source Research Engine package exposing core planner, router, and models."""

from app.services.search.base import (
    SourceCategory,
    ResearchDepth,
    EvidenceStrength,
    FreshnessRequirement,
    DiscoveredSource,
    ResearchPlan,
    ResearchConflict,
    ResearchSynthesis,
    SearchProvider,
)
from app.services.search.planner import ResearchPlanner
from app.services.search.evaluator import SourceQualityEngine
from app.services.search.curated_provider import CuratedKnowledgeProvider
from app.services.search.web_provider import DuckDuckGoProvider
from app.services.search.router import SearchRouter, get_search_router

__all__ = [
    "SourceCategory",
    "ResearchDepth",
    "EvidenceStrength",
    "FreshnessRequirement",
    "DiscoveredSource",
    "ResearchPlan",
    "ResearchConflict",
    "ResearchSynthesis",
    "SearchProvider",
    "ResearchPlanner",
    "SourceQualityEngine",
    "CuratedKnowledgeProvider",
    "DuckDuckGoProvider",
    "SearchRouter",
    "get_search_router",
]
