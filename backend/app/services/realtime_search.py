"""Real-time intelligence and external search engine for Mode B (Real-World) and Mode C (Hybrid)."""

import re
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ExternalSource:
    title: str
    url: str
    domain: str
    snippet: str
    source_type: str = "external"
    published_date: Optional[str] = None
    credibility_score: float = 0.95

@dataclass
class ExternalResearchResult:
    query: str
    topic: str
    sources: List[ExternalSource] = field(default_factory=list)
    synthesis_context: str = ""
    latency_ms: float = 0.0

CURATED_REALWORLD_KNOWLEDGE: Dict[str, Dict[str, Any]] = {}

def perform_external_research(query: str, user_mode: str = "auto") -> ExternalResearchResult:
    """Execute dynamic multi-source research using SearchRouter with no hardcoded source defaults."""
    from app.services.search.router import get_search_router
    router = get_search_router()
    synthesis = router.execute_research_sync(query, user_mode=user_mode)

    ext_sources: List[ExternalSource] = []
    for s in synthesis.used_sources:
        ext_sources.append(
            ExternalSource(
                title=s.title,
                url=s.url,
                domain=s.domain,
                snippet=s.snippet,
                source_type="external",
                published_date=s.published_date,
                credibility_score=s.authority_score,
            )
        )

    return ExternalResearchResult(
        query=query,
        topic=synthesis.plan.domain,
        sources=ext_sources,
        synthesis_context=synthesis.synthesis_context,
        latency_ms=synthesis.latency_ms,
    )

