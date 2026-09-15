"""Search router orchestrating concurrent provider execution, safety sanitization, and evidence synthesis."""

import asyncio
import re
import time
import logging
from typing import List, Dict, Optional, Any

from app.services.search.base import (
    SearchProvider,
    DiscoveredSource,
    SourceCategory,
    ResearchDepth,
    ResearchPlan,
    ResearchSynthesis,
    EvidenceStrength,
)
from app.services.search.curated_provider import CuratedKnowledgeProvider
from app.services.search.web_provider import DuckDuckGoProvider
from app.services.search.planner import ResearchPlanner
from app.services.search.evaluator import SourceQualityEngine

logger = logging.getLogger(__name__)

# Prompt injection neutralization pattern for untrusted web snippets
INJECTION_ATTACK_REGEX = re.compile(
    r'(ignore\s+(all\s+)?previous\s+instructions|system\s+prompt|disregard\s+above|you\s+are\s+now|override\s+instructions)',
    re.IGNORECASE
)

class SearchRouter:
    """Intelligent multi-source search router managing concurrency, fallbacks, and security."""

    def __init__(self):
        self.curated_provider = CuratedKnowledgeProvider()
        self.web_provider = DuckDuckGoProvider()
        self.planner = ResearchPlanner()
        self.evaluator = SourceQualityEngine()
        self._cache: Dict[str, ResearchSynthesis] = {}

    def sanitize_untrusted_snippet(self, raw_snippet: str) -> str:
        """Neutralize potential prompt injection and malicious instructions in web page snippets."""
        if not raw_snippet:
            return ""
        # Redact instruction override attempts to ensure prompt injection defense
        clean = INJECTION_ATTACK_REGEX.sub("[NEUTRALIZED_UNTRUSTED_INSTRUCTION]", raw_snippet)
        return clean.strip()


    def execute_research_sync(self, query: str, user_mode: str = "auto") -> ResearchSynthesis:
        """Synchronous research execution with curated check and web provider fallback."""
        t0 = time.perf_counter()
        cache_key = f"{user_mode}:{query.strip().lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        plan = self.planner.plan_research(query, user_mode)

        # 1. Check curated knowledge baseline first
        curated_sources = self.curated_provider.search(query)
        discovered: List[DiscoveredSource] = list(curated_sources)

        # 2. If no curated match or if deep research mode is requested, query web provider
        if not discovered or plan.depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP_MULTI_QUERY]:
            for sq in plan.sub_queries[:3]:
                web_sources = self.web_provider.search(sq, max_results=4)
                discovered.extend(web_sources)

        # Strict Query-to-Context Relevance Filtering (Rules 3, 4, 7, 8)
        from app.services.relevance import get_relevance_router
        analysis = get_relevance_router().analyze_query(query)
        discovered = get_relevance_router().relevance_filter.filter_evidence_chunks(analysis, discovered)

        # 3. Quality evaluation & deduplication
        ranked = self.evaluator.evaluate_and_rank(query, discovered)
        conflicts = self.evaluator.detect_conflicts(ranked)
        strength = self.evaluator.calculate_evidence_strength(ranked, conflicts)

        # 4. Limit to top useful sources based on depth
        max_sources = 3 if plan.depth == ResearchDepth.TARGETED else (6 if plan.depth == ResearchDepth.STANDARD else 10)
        used_sources = ranked[:max_sources]

        # 5. Build category counts
        category_counts: Dict[str, int] = {}
        for s in used_sources:
            cat_name = s.category.value.capitalize()
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        # 6. Build structured synthesis context with untrusted boundary protection
        snippets: List[str] = []
        for s in used_sources:
            safe_snippet = self.sanitize_untrusted_snippet(s.snippet)
            snippets.append(
                f"[{s.title}] ({s.domain} | Category: {s.category.value} | Authority: {s.authority_score})\n"
                f"<external_evidence_untrusted>\n{safe_snippet}\n</external_evidence_untrusted>"
            )

        if conflicts:
            conflict_notes = "\n".join([f"- Discrepancy between {c.source_a} and {c.source_b}: {c.explanation}" for c in conflicts])
            snippets.append(f"\n[DETECTED SOURCE DISCREPANCIES]\n{conflict_notes}")

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        synthesis = ResearchSynthesis(
            query=query,
            plan=plan,
            discovered_sources=ranked,
            used_sources=used_sources,
            category_counts=category_counts,
            evidence_strength=strength,
            conflicts=conflicts,
            synthesis_context="\n\n".join(snippets),
            latency_ms=latency_ms,
        )

        self._cache[cache_key] = synthesis
        return synthesis

    async def execute_research_async(self, query: str, user_mode: str = "auto") -> ResearchSynthesis:
        """Asynchronous concurrent research execution across sub-queries."""
        t0 = time.perf_counter()
        cache_key = f"{user_mode}:{query.strip().lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        plan = self.planner.plan_research(query, user_mode)

        # 1. Immediate curated check
        curated_sources = self.curated_provider.search(query)
        discovered: List[DiscoveredSource] = list(curated_sources)

        # 2. Concurrently execute sub-queries via DuckDuckGo
        if not discovered or plan.depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP_MULTI_QUERY]:
            tasks = [self.web_provider.search_async(sq, max_results=4) for sq in plan.sub_queries[:4]]
            search_batches = await asyncio.gather(*tasks, return_exceptions=True)
            for batch in search_batches:
                if isinstance(batch, list):
                    discovered.extend(batch)

        # Strict Query-to-Context Relevance Filtering (Rules 3, 4, 7, 8)
        from app.services.relevance import get_relevance_router
        analysis = get_relevance_router().analyze_query(query)
        discovered = get_relevance_router().relevance_filter.filter_evidence_chunks(analysis, discovered)

        # 3. Quality ranking, deduplication, conflict audit
        ranked = self.evaluator.evaluate_and_rank(query, discovered)
        conflicts = self.evaluator.detect_conflicts(ranked)
        strength = self.evaluator.calculate_evidence_strength(ranked, conflicts)

        # 4. Limit to top useful sources
        max_sources = 3 if plan.depth == ResearchDepth.TARGETED else (6 if plan.depth == ResearchDepth.STANDARD else 12)
        used_sources = ranked[:max_sources]

        # 5. Build category counts
        category_counts: Dict[str, int] = {}
        for s in used_sources:
            cat_name = s.category.value.capitalize()
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        # 6. Build structured synthesis context
        snippets: List[str] = []
        for s in used_sources:
            safe_snippet = self.sanitize_untrusted_snippet(s.snippet)
            snippets.append(
                f"[{s.title}] ({s.domain} | Category: {s.category.value} | Authority: {s.authority_score})\n"
                f"<external_evidence_untrusted>\n{safe_snippet}\n</external_evidence_untrusted>"
            )

        if conflicts:
            conflict_notes = "\n".join([f"- Discrepancy between {c.source_a} and {c.source_b}: {c.explanation}" for c in conflicts])
            snippets.append(f"\n[DETECTED SOURCE DISCREPANCIES]\n{conflict_notes}")

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        synthesis = ResearchSynthesis(
            query=query,
            plan=plan,
            discovered_sources=ranked,
            used_sources=used_sources,
            category_counts=category_counts,
            evidence_strength=strength,
            conflicts=conflicts,
            synthesis_context="\n\n".join(snippets),
            latency_ms=latency_ms,
        )

        self._cache[cache_key] = synthesis
        return synthesis

_GLOBAL_SEARCH_ROUTER: Optional[SearchRouter] = None

def get_search_router() -> SearchRouter:
    """Singleton getter for the global SearchRouter."""
    global _GLOBAL_SEARCH_ROUTER
    if _GLOBAL_SEARCH_ROUTER is None:
        _GLOBAL_SEARCH_ROUTER = SearchRouter()
    return _GLOBAL_SEARCH_ROUTER
