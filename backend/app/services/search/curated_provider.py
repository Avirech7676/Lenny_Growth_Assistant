"""Curated knowledge provider for verified product benchmarks and historical ground truth."""

import time
from typing import List, Dict, Any, Optional
from app.services.search.base import (
    SearchProvider,
    DiscoveredSource,
    SourceCategory,
    FreshnessRequirement,
)

CURATED_ENTITIES: Dict[str, Dict[str, Any]] = {}

class CuratedKnowledgeProvider(SearchProvider):
    """Zero-latency baseline provider for vetted foundational metrics."""

    def get_provider_name(self) -> str:
        return "curated_knowledge"

    def match_curated(self, query: str) -> Optional[DiscoveredSource]:
        # Dynamic lookup only if registered in curated entities
        q_lower = query.lower().strip()
        if q_lower in CURATED_ENTITIES:
            item = CURATED_ENTITIES[q_lower]
            return DiscoveredSource(
                title=item["title"],
                url=item["url"],
                domain=item["domain"],
                snippet=item["snippet"],
                category=item["category"],
                authority_score=item.get("authority", 0.95),
                freshness=item.get("freshness", FreshnessRequirement.CURRENT),
                is_primary=item.get("is_primary", True),
                why_useful=item.get("why_useful", "Verified foundational source."),
            )
        return None

    def search(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        match = self.match_curated(query)
        return [match] if match else []

    async def search_async(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        return self.search(query, max_results)
