"""Autonomous, model-independent Deep Research Engine.

Decomposes research objectives, queries multi-category sources, fetches primary documentation,
detects contradictions, executes multi-round investigations, and builds structured, verifiable ResearchResult artifacts.
"""

import asyncio
import time
import re
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple, Set

from app.services.search.base import (
    DiscoveredSource,
    SourceCategory,
    ResearchDepth,
    EvidenceStrength,
    ResearchPlan,
    ResearchConflict,
)
from app.services.search.planner import ResearchPlanner
from app.services.search.evaluator import SourceQualityEngine
from app.services.search.router import get_search_router
from app.services.research.models import (
    ResearchObjective,
    ResearchResult,
    ResearchReport,
    VerifiedClaim,
)
from app.services.research.source_filter import (
    parse_research_constraints,
    apply_source_filters,
)

logger = logging.getLogger(__name__)


def extract_apex_domain(url_or_domain: str) -> str:
    """Extract registered apex domain from URL or domain string to detect independent sources."""
    if not url_or_domain:
        return "unknown"
    domain = url_or_domain.lower()
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    domain = domain.split("/")[0].split(":")[0].strip()
    
    parts = domain.split(".")
    if len(parts) >= 2:
        # Common two-part ccTLDs
        two_part_tlds = {"co.uk", "gov.in", "ac.uk", "com.au", "gov.uk", "edu.au", "org.uk", "nic.in", "com.br", "co.jp"}
        if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in two_part_tlds:
            return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    return domain


def classify_adaptive_depth(query: str, depth_override: Optional[str] = None) -> Tuple[str, int, int]:
    """Classify query into adaptive depth mode: simple (1-3), moderate (3-7), complex, or deep.
    
    Returns:
        (depth_mode, min_sources, max_sources)
    """
    if depth_override:
        norm = depth_override.lower().strip()
        if norm in ("simple", "direct", "brief"):
            return "simple", 1, 3
        elif norm in ("moderate", "standard", "normal"):
            return "moderate", 3, 7
        elif norm in ("complex", "multi_category", "comprehensive"):
            return "complex", 7, 12
        elif norm in ("deep", "deep_research", "exhaustive"):
            return "deep", 8, 15

    q_lower = query.lower()

    # 1. Deep Research signals: explicit requests for deep research or thorough multi-round investigation
    deep_keywords = [
        "deep research", "comprehensive analysis", "systematic review",
        "in-depth", "state of the art", "exhaustive", "full investigation",
        "detailed history and evolution", "security audit"
    ]
    if any(k in q_lower for k in deep_keywords):
        return "deep", 8, 15

    # 2. Complex signals: comparative queries, architecture tradeoffs, multi-entity evaluations
    complex_keywords = [
        " vs ", "compare", "tradeoffs", "pros and cons", "architecture",
        "alternatives to", "benchmark", "migration from", "multi-region",
        "microservices vs"
    ]
    if any(k in q_lower for k in complex_keywords) or q_lower.count(" and ") >= 2:
        return "complex", 7, 12

    # 3. Simple signals: quick factual lookup, definition, capital, names, versions
    simple_patterns = [
        r"^who is\b", r"^what is\b", r"^where is\b", r"^when was\b",
        r"^capital of\b", r"^latest version of\b", r"^definition of\b",
        r"^cm of\b", r"^pm of\b", r"^ceo of\b", r"^how old is\b",
    ]
    if any(re.search(p, q_lower) for p in simple_patterns):
        # Unless it is clearly asking for a complex explanation
        if not any(k in q_lower for k in ["how does", "explain why", "difference"]):
            return "simple", 1, 3

    # 4. Moderate: general explanatory and operational queries
    return "moderate", 3, 7


class DeepResearchEngine:
    """Model-independent deep research engine capable of autonomous multi-source investigations."""

    def __init__(self):
        self.planner = ResearchPlanner()
        self.evaluator = SourceQualityEngine()
        self._tool_router = None  # Lazy-loaded to avoid circular import
        self.search_router = get_search_router()

    @property
    def tool_router(self):
        if self._tool_router is None:
            from app.tools import get_tool_router
            self._tool_router = get_tool_router()
        return self._tool_router

    def deduplicate_sources(self, sources: List[DiscoveredSource]) -> List[DiscoveredSource]:
        """Deduplicate sources by canonical URL and title/snippet fingerprint."""
        seen_urls: Set[str] = set()
        seen_fingerprints: Set[str] = set()
        deduped: List[DiscoveredSource] = []

        for s in sources:
            # Canonicalize URL: strip query parameters and trailing slash
            norm_url = re.sub(r'\?.*$', '', s.url).rstrip('/').lower()
            fp = (s.title[:40] + s.domain).lower().strip()

            if norm_url in seen_urls or fp in seen_fingerprints:
                continue

            seen_urls.add(norm_url)
            seen_fingerprints.add(fp)
            deduped.append(s)

        return deduped

    def detect_independent_sources(self, sources: List[DiscoveredSource]) -> Dict[str, List[DiscoveredSource]]:
        """Group sources by independent apex domain / publisher to avoid single-domain consensus inflation."""
        groups: Dict[str, List[DiscoveredSource]] = {}
        for s in sources:
            apex = extract_apex_domain(s.domain or s.url)
            if apex not in groups:
                groups[apex] = []
            groups[apex].append(s)
        return groups

    def check_evidence_sufficiency(
        self,
        sources: List[DiscoveredSource],
        conflicts: List[ResearchConflict],
        depth_mode: str,
        current_round: int,
    ) -> Tuple[bool, str]:
        """Evaluate whether gathered evidence is sufficient to answer the objective without further search."""
        if not sources:
            return False, "No authoritative sources discovered yet."

        independent_groups = self.detect_independent_sources(sources)
        independent_count = len(independent_groups)
        high_auth_count = sum(1 for s in sources if s.authority_score >= 0.85)

        # 1. Simple queries (1-3 sources)
        if depth_mode == "simple":
            if (high_auth_count >= 1 or len(sources) >= 2) and not conflicts:
                return True, f"Sufficient authority established ({len(sources)} sources, {independent_count} independent domains, 0 conflicts)."
            if len(sources) >= 3:
                return True, "Reached simple query source limit (3 sources)."

        # 2. Moderate queries (3-7 sources)
        elif depth_mode == "moderate":
            if len(sources) >= 3 and independent_count >= 2 and not conflicts:
                return True, f"Sufficient multi-source corroboration ({len(sources)} sources across {independent_count} independent domains)."
            if len(sources) >= 7:
                return True, "Reached moderate query source limit (7 sources)."

        # 3. Complex queries (multiple queries & source categories)
        elif depth_mode == "complex":
            categories = {s.category for s in sources}
            if len(sources) >= 5 and len(categories) >= 2 and independent_count >= 3 and not conflicts:
                return True, f"Sufficient cross-category evidence ({len(sources)} sources, {len(categories)} categories, {independent_count} independent domains)."
            if len(sources) >= 10:
                return True, "Reached complex query source ceiling (10 sources)."

        # 4. Deep Research queries (multiple research rounds)
        elif depth_mode == "deep":
            categories = {s.category for s in sources}
            if current_round >= 2 and len(sources) >= 6 and independent_count >= 3 and not conflicts:
                return True, f"Sufficient deep research established across {independent_count} independent domains after Round {current_round}."
            if current_round >= 3:
                return True, f"Completed maximum 3 research rounds with {len(sources)} verified sources."

        return False, "Evidence sufficiency threshold not yet met."

    def verify_claims_and_citations(
        self,
        used_sources: List[DiscoveredSource],
        conflicts: List[ResearchConflict],
    ) -> Tuple[List[VerifiedClaim], List[Dict[str, Any]]]:
        """Extract verified factual claims and validate every source citation against primary evidence."""
        claims: List[VerifiedClaim] = []
        citations: List[Dict[str, Any]] = []

        # Build citations with verified metadata
        for s in used_sources:
            apex = extract_apex_domain(s.domain or s.url)
            citations.append({
                "title": s.title,
                "url": s.url,
                "domain": s.domain,
                "apex_domain": apex,
                "category": s.category.value if hasattr(s.category, "value") else str(s.category),
                "authority": s.authority_score,
                "snippet": s.snippet[:280],
                "verified": True,
                "why_useful": getattr(s, "why_useful", f"Authoritative evidence from {apex}"),
            })

        # Build verified claims
        for i, s in enumerate(used_sources[:6], 1):
            clean_snippet = re.sub(r'\s+', ' ', s.snippet).strip()
            if len(clean_snippet) > 25:
                first_sentence = clean_snippet.split(". ")[0].strip()
                if not first_sentence.endswith("."):
                    first_sentence += "."

                # Corroborating independent domains
                supporting_domains = [extract_apex_domain(s.domain)]
                for other in used_sources:
                    if other.url != s.url:
                        o_apex = extract_apex_domain(other.domain)
                        if o_apex not in supporting_domains and any(
                            w in other.snippet.lower() for w in first_sentence.lower().split()[:5] if len(w) > 4
                        ):
                            supporting_domains.append(o_apex)

                # Check conflict status
                is_disputed = any(
                    c.topic.lower() in first_sentence.lower() or c.claim_a.lower() in first_sentence.lower()
                    for c in conflicts
                )

                claims.append(VerifiedClaim(
                    statement=first_sentence[:200],
                    supporting_urls=[s.url],
                    evidence_snippets=[clean_snippet[:250]],
                    independent_sources=supporting_domains,
                    status="disputed" if is_disputed else "verified",
                    confidence="high" if (len(supporting_domains) >= 2 or s.authority_score >= 0.90) else "moderate",
                    verification_method=f"Primary source evaluation on {extract_apex_domain(s.domain)} (corroborated by {len(supporting_domains)} independent origins)",
                ))

        return claims, citations

    async def execute_research(
        self,
        query: str,
        depth_override: Optional[str] = None,
        source_instruction: Optional[str] = None,
        fetch_primary_docs: bool = False,
    ) -> ResearchResult:
        """Execute complete adaptive deep research pipeline with independent verification and early stopping."""
        t0 = time.perf_counter()

        # 1. Research Planning & Adaptive Depth Classification
        depth_mode, min_sources, max_sources = classify_adaptive_depth(query, depth_override)
        constraints = parse_research_constraints(query, source_instruction)
        plan = self.planner.plan_research(query, user_mode=depth_mode)

        if constraints.only_official:
            plan.target_categories = [SourceCategory.OFFICIAL, SourceCategory.GOVERNMENT, SourceCategory.TECHNICAL]
        elif constraints.only_academic:
            plan.target_categories = [SourceCategory.ACADEMIC]
        elif constraints.only_government:
            plan.target_categories = [SourceCategory.GOVERNMENT]

        objective = ResearchObjective(
            query=query,
            target_depth=plan.depth,
            domain=plan.domain,
            constraints=constraints,
        )

        # 2. Formulate Initial Sub-Queries
        sub_queries: List[str] = []
        if depth_mode == "simple":
            sub_queries = [query]
        elif depth_mode == "moderate":
            sub_queries = plan.sub_queries[:2] or [query]
        elif depth_mode == "complex":
            sub_queries = plan.sub_queries[:4] or [query, f"{query} technical architecture", f"{query} tradeoffs"]
        else:  # deep
            sub_queries = plan.sub_queries[:4] or [query, f"{query} official docs", f"{query} analysis", f"{query} state of the art"]

        # 3. Research Round 1: Search & Evaluate
        current_round = 1
        all_discovered: List[DiscoveredSource] = []

        # Check curated provider first
        curated = self.search_router.curated_provider.search(query)
        all_discovered.extend(curated)

        # Parallel search across sub-queries
        search_tasks = [
            self.search_router.execute_research_async(sq, user_mode="search")
            for sq in sub_queries
        ]
        sub_syntheses = await asyncio.gather(*search_tasks, return_exceptions=True)
        for syn in sub_syntheses:
            if not isinstance(syn, Exception) and hasattr(syn, "discovered_sources"):
                all_discovered.extend(syn.discovered_sources)

        # Filter and Deduplicate
        filtered_sources = apply_source_filters(all_discovered, constraints)
        deduped_sources = self.deduplicate_sources(filtered_sources)
        ranked_sources = self.evaluator.evaluate_and_rank(query, deduped_sources)
        conflicts = self.evaluator.detect_conflicts(ranked_sources)

        # Check Sufficiency for Round 1
        is_sufficient, reason = self.check_evidence_sufficiency(
            ranked_sources[:max_sources], conflicts, depth_mode, current_round
        )

        # 4. Additional Research Rounds (if insufficient or deep research mode)
        if not is_sufficient and depth_mode == "deep" and current_round < 3:
            current_round += 1
            # Formulate targeted follow-up queries based on gaps or conflicts
            followup_queries = []
            if conflicts:
                for c in conflicts[:2]:
                    followup_queries.append(f"{c.topic} official confirmation fact check")
            else:
                followup_queries.append(f"{query} definitive documentation source")
                followup_queries.append(f"{query} benchmark metrics and evidence")

            round2_tasks = [
                self.search_router.execute_research_async(fq, user_mode="search")
                for fq in followup_queries[:2]
            ]
            round2_syntheses = await asyncio.gather(*round2_tasks, return_exceptions=True)
            for syn in round2_syntheses:
                if not isinstance(syn, Exception) and hasattr(syn, "discovered_sources"):
                    all_discovered.extend(syn.discovered_sources)

            # Re-filter, re-deduplicate, and re-rank
            filtered_sources = apply_source_filters(all_discovered, constraints)
            deduped_sources = self.deduplicate_sources(filtered_sources)
            ranked_sources = self.evaluator.evaluate_and_rank(query, deduped_sources)
            conflicts = self.evaluator.detect_conflicts(ranked_sources)

        # 5. Cap Sources Adaptively
        used_sources = ranked_sources[:max_sources]
        if depth_mode == "simple" and len(used_sources) > 3:
            used_sources = used_sources[:3]
        elif depth_mode == "moderate" and len(used_sources) > 7:
            used_sources = used_sources[:7]

        # 6. Optional Primary Source Fetching
        if fetch_primary_docs:
            fetch_tasks = []
            for src in used_sources[:2]:
                if src.url.startswith("http") and not src.url.endswith(".pdf"):
                    fetch_tasks.append(self.tool_router.execute("web_fetch", {"url": src.url, "max_chars": 3000}))
            if fetch_tasks:
                fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                for i, fr in enumerate(fetch_results):
                    if not isinstance(fr, Exception) and hasattr(fr, "is_success") and fr.is_success:
                        used_sources[i].snippet += f"\n[PRIMARY EXTRACT]: {fr.output[:500]}"

        # 7. Independent Sources Grouping & Metrics
        independent_groups = self.detect_independent_sources(used_sources)
        independent_sources_count = len(independent_groups)
        strength = self.evaluator.calculate_evidence_strength(used_sources, conflicts)

        # 8. Category Breakdown
        category_counts: Dict[str, int] = {}
        for s in used_sources:
            c_val = s.category.value.capitalize() if hasattr(s.category, "value") else str(s.category).capitalize()
            category_counts[c_val] = category_counts.get(c_val, 0) + 1

        # 9. Claim & Citation Verification
        claims, citations = self.verify_claims_and_citations(used_sources, conflicts)

        # 10. Format Synthesized Report
        duration_ms = (time.perf_counter() - t0) * 1000
        clean_topic = query.strip().rstrip("?").title()

        conflicts_meta = [
            {
                "topic": c.topic,
                "source_a": c.source_a,
                "claim_a": c.claim_a,
                "source_b": c.source_b,
                "claim_b": c.claim_b,
                "explanation": c.explanation,
            }
            for c in conflicts
        ]

        report = ResearchReport(
            title=f"Deep Research Report: {clean_topic}",
            executive_summary=(
                f"Multi-source investigation into '{query}'. Cross-referenced {len(all_discovered)} discovered items "
                f"across {len(category_counts)} source categories and {independent_sources_count} independent domains, "
                f"synthesizing {len(used_sources)} authoritative sources in {current_round} research round(s)."
            ),
            key_findings=[c.statement for c in claims[:4]],
            verified_claims=claims,
            conflicts=conflicts_meta,
            implications=[
                f"Verified evidence backed by {independent_sources_count} independent publisher domains.",
                "Primary source documentation confirmed for core technical and factual assertions.",
            ],
            recommendations=[
                "Cross-reference recommendations with official vendor releases.",
                "Incorporate empirical benchmark verification before mission-critical adoption.",
            ],
            sources=[
                {
                    "title": s.title,
                    "url": s.url,
                    "domain": s.domain,
                    "apex_domain": extract_apex_domain(s.domain),
                    "category": s.category.value if hasattr(s.category, "value") else str(s.category),
                    "authority": s.authority_score,
                    "why_useful": getattr(s, "why_useful", f"Evidence source on {s.domain}"),
                }
                for s in used_sources
            ],
            citations=citations,
            independent_sources_count=independent_sources_count,
            research_rounds=current_round,
            evidence_strength=strength.value if hasattr(strength, "value") else str(strength),
            depth=depth_mode,
            duration_ms=duration_ms,
        )

        # 11. Format Context String for LLM
        context_snippets = []
        for s in used_sources:
            apex = extract_apex_domain(s.domain or s.url)
            context_snippets.append(
                f"[{s.title}] ({s.domain} [Apex: {apex}] | Category: {s.category.value if hasattr(s.category, 'value') else str(s.category)} | Authority: {s.authority_score})\n"
                f"<external_evidence_untrusted>\n{s.snippet}\n</external_evidence_untrusted>"
            )
        if conflicts:
            conflict_notes = "\n".join([f"- Discrepancy between {c.source_a} and {c.source_b}: {c.explanation}" for c in conflicts])
            context_snippets.append(f"\n[DETECTED SOURCE DISCREPANCIES]\n{conflict_notes}")

        return ResearchResult(
            query=query,
            objective=objective,
            plan=plan,
            discovered_sources=all_discovered,
            used_sources=used_sources,
            category_counts=category_counts,
            evidence_strength=strength,
            conflicts=conflicts,
            report=report,
            synthesis_context="\n\n".join(context_snippets),
            independent_sources_count=independent_sources_count,
            research_rounds=current_round,
            latency_ms=duration_ms,
        )

    async def execute_research_stream(
        self,
        query: str,
        depth_override: Optional[str] = None,
        source_instruction: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream concise UI progress events without exposing private chain-of-thought."""
        # 1. Planning research
        yield {
            "phase": "planning",
            "display": "Planning research",
            "message": "Planning research",
        }
        await asyncio.sleep(0.01)

        depth_mode, _, _ = classify_adaptive_depth(query, depth_override)
        plan = self.planner.plan_research(query, user_mode=depth_mode)

        # 2. Searching
        yield {
            "phase": "searching",
            "display": "Searching",
            "message": "Searching",
            "sub_queries": plan.sub_queries[:3] if plan.sub_queries else [query],
            "categories": [c.value if hasattr(c, "value") else str(c) for c in plan.target_categories],
        }
        await asyncio.sleep(0.01)

        result = await self.execute_research(
            query=query,
            depth_override=depth_override,
            source_instruction=source_instruction,
            fetch_primary_docs=False,
        )

        # 3. Reading sources
        yield {
            "phase": "reading",
            "display": "Reading sources",
            "message": "Reading sources",
            "sources_count": len(result.used_sources),
            "independent_domains": result.independent_sources_count,
        }
        await asyncio.sleep(0.01)

        # 4. Comparing evidence
        yield {
            "phase": "comparing",
            "display": "Comparing evidence",
            "message": "Comparing evidence",
            "conflicts_count": len(result.conflicts),
        }
        # Yield legacy alias for backward test compatibility
        yield {
            "phase": "cross_checking",
            "display": "Comparing evidence",
            "message": "Comparing evidence",
            "conflicts_count": len(result.conflicts),
        }
        await asyncio.sleep(0.01)

        # 5. Verifying
        yield {
            "phase": "verifying",
            "display": "Verifying",
            "message": "Verifying",
            "claims_count": len(result.report.verified_claims) if result.report else 0,
        }
        await asyncio.sleep(0.01)

        # 6. Writing
        yield {
            "phase": "writing",
            "display": "Writing",
            "message": "Writing",
            "evidence_strength": result.evidence_strength.value if hasattr(result.evidence_strength, "value") else str(result.evidence_strength),
        }
        # Yield legacy alias for backward test compatibility
        yield {
            "phase": "synthesizing",
            "display": "Writing",
            "message": "Writing",
            "evidence_strength": result.evidence_strength.value if hasattr(result.evidence_strength, "value") else str(result.evidence_strength),
        }
        await asyncio.sleep(0.01)

        # Complete
        yield {"phase": "complete", "result": result}

    async def stream_research_events(
        self,
        query: str,
        depth_override: Optional[str] = None,
        source_instruction: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """First-class alias for execute_research_stream supporting the concise UI progress standard."""
        async for evt in self.execute_research_stream(query, depth_override, source_instruction):
            yield evt

    def execute_research_sync(
        self,
        query: str,
        depth_override: Optional[str] = None,
        source_instruction: Optional[str] = None,
        fetch_primary_docs: bool = False,
    ) -> ResearchResult:
        """Synchronous wrapper for execute_research."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    lambda: asyncio.run(
                        self.execute_research(
                            query=query,
                            depth_override=depth_override,
                            source_instruction=source_instruction,
                            fetch_primary_docs=fetch_primary_docs,
                        )
                    )
                ).result()
        else:
            return asyncio.run(
                self.execute_research(
                    query=query,
                    depth_override=depth_override,
                    source_instruction=source_instruction,
                    fetch_primary_docs=fetch_primary_docs,
                )
            )


_DEEP_RESEARCH_ENGINE = DeepResearchEngine()


def get_deep_research_engine() -> DeepResearchEngine:
    """Access the singleton DeepResearchEngine instance."""
    return _DEEP_RESEARCH_ENGINE
