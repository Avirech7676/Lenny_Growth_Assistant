"""Query understanding, domain classification, depth determination, and sub-query research planner."""

import re
from typing import List, Tuple
from app.services.search.base import (
    ResearchPlan,
    ResearchDepth,
    SourceCategory,
    FreshnessRequirement,
)

# Domain detection keywords
DOMAIN_PATTERNS = {
    "technology": [
        "react", "vue", "angular", "python", "fastapi", "django", "docker", "kubernetes",
        "graphql", "api", "framework", "frontend", "backend", "database", "postgres",
        "npm", "pypi", "github", "rust", "golang", "typescript", "javascript", "llm architecture"
    ],
    "science": [
        "quantum", "physics", "biology", "sleep", "hallucination", "neural", "dna",
        "astronomy", "climate", "peer-reviewed", "academic", "paper", "research study"
    ],
    "sports": [
        "formula 1", "f1", "fifa", "world cup", "cricket", "match", "race", "champion",
        "olympics", "grand prix", "tournament", "premier league", "nba", "score"
    ],
    "finance": [
        "stock", "earnings", "sec filing", "valuation", "investor", "revenue", "ebitda",
        "cac", "ltv", "venture capital", "pre-seed", "series a", "series b", "ipo", "rbi"
    ],
    "business": [
        "startup", "pricing", "monetization", "growth loop", "retention", "activation",
        "plg", "onboarding", "market analysis", "competitor", "tam", "business model"
    ],
    "government": [
        "capital", "chief minister", "prime minister", "president", "policy", "election",
        "andhra pradesh", "amaravati", "legislation", "parliament", "treaty", "court"
    ],
    "product": [
        "laptop", "smartphone", "iphone", "macbook", "gpu", "processor", "under ₹",
        "best buy", "specifications", "benchmark test", "review"
    ]
}

class ResearchPlanner:
    """Intelligent planner decomposing questions into domain-aware research strategies."""

    def classify_domain(self, query: str) -> str:
        q_lower = query.lower()
        for domain, keywords in DOMAIN_PATTERNS.items():
            if any(k in q_lower for k in keywords):
                return domain
        return "general"

    def classify_freshness(self, query: str) -> FreshnessRequirement:
        q_lower = query.lower()
        if any(w in q_lower for w in ["latest", "current", "2026", "yesterday", "recent", "today", "now", "who won"]):
            return FreshnessRequirement.LATEST
        if any(w in q_lower for w in ["this year", "trends", "modern", "contemporary"]):
            return FreshnessRequirement.CURRENT
        if any(w in q_lower for w in ["in 2019", "in 2020", "history of", "who was", "past", "founded"]):
            return FreshnessRequirement.HISTORICAL
        # Timeless conceptual explanations
        if any(q_lower.startswith(prefix) for prefix in ["what is ", "what are ", "explain ", "how does ", "define "]) and not any(k in q_lower for k in ["latest", "2026", "current", "version"]):
            return FreshnessRequirement.STABLE
        return FreshnessRequirement.RECENT

    def determine_depth(self, query: str, user_mode: str = "auto") -> ResearchDepth:
        """Adaptive research depth controller (Level 0 through Level 4)."""
        mode_clean = (user_mode or "auto").lower()

        # Explicit user control overrides
        if mode_clean in ["deep", "deep_research"]:
            return ResearchDepth.DEEP_MULTI_QUERY
        if mode_clean == "search":
            return ResearchDepth.STANDARD

        q_lower = query.lower()

        # High complexity / comparison / strategic research -> Level 3 Deep Multi-Query
        is_comparison = any(w in q_lower for w in ["compare", "versus", " vs ", "difference between", "better for"])
        is_deep_research = any(w in q_lower for w in ["deep research", "market analysis", "viability", "thorough", "comprehensive analysis", "evaluate startup"])
        if is_comparison or is_deep_research:
            return ResearchDepth.DEEP_MULTI_QUERY

        # Direct stable conceptual questions -> Level 0 Direct Answer (keep fast)
        is_direct = (
            any(q_lower.startswith(p) for p in ["what is ", "what are ", "explain ", "how to "])
            and not any(w in q_lower for w in ["latest", "2026", "current", "who won", "news", "today", "pricing", "version", "under ₹", "compare"])
        )
        if is_direct:
            return ResearchDepth.DIRECT

        # Factual lookups (e.g. latest version, who won) -> Level 1 Targeted
        is_targeted = (
            ("latest" in q_lower and "version" in q_lower)
            or any(w in q_lower for w in ["latest version", "capital of", "who is", "who won", "official documentation"])
        )
        if is_targeted:
            return ResearchDepth.TARGETED


        # Standard real-world questions -> Level 2 Standard
        return ResearchDepth.STANDARD

    def target_categories_for_domain(self, domain: str) -> List[SourceCategory]:
        """Map domain to preferred mix of primary, independent, and secondary source categories."""
        if domain == "technology":
            return [SourceCategory.OFFICIAL, SourceCategory.TECHNICAL, SourceCategory.COMMUNITY, SourceCategory.INDUSTRY]
        elif domain == "science":
            return [SourceCategory.ACADEMIC, SourceCategory.OFFICIAL, SourceCategory.NEWS]
        elif domain == "sports":
            return [SourceCategory.OFFICIAL, SourceCategory.NEWS]
        elif domain == "finance":
            return [SourceCategory.FINANCIAL, SourceCategory.OFFICIAL, SourceCategory.NEWS, SourceCategory.INDUSTRY]
        elif domain == "business":
            return [SourceCategory.INDUSTRY, SourceCategory.OFFICIAL, SourceCategory.NEWS]
        elif domain == "government":
            return [SourceCategory.GOVERNMENT, SourceCategory.OFFICIAL, SourceCategory.NEWS, SourceCategory.REFERENCE]
        elif domain == "product":
            return [SourceCategory.PRODUCT, SourceCategory.OFFICIAL, SourceCategory.COMMUNITY]
        return [SourceCategory.OFFICIAL, SourceCategory.NEWS, SourceCategory.REFERENCE]

    def generate_subqueries(self, query: str, domain: str, depth: ResearchDepth) -> List[str]:
        """Generate targeted sub-queries for multi-query deep research."""
        if depth in [ResearchDepth.DIRECT, ResearchDepth.TARGETED]:
            return [query]

        clean_q = query.strip().rstrip("?")

        if depth == ResearchDepth.STANDARD:
            # 2 targeted variations
            if domain == "technology":
                return [clean_q, f"{clean_q} official documentation guide"]
            elif domain == "sports":
                return [clean_q, f"{clean_q} official results"]
            return [clean_q, f"{clean_q} current report"]

        # Level 3 & Level 4: Deep Multi-Query Plan (3-5 orthogonal angles)
        sub_queries = [clean_q]

        if "compare" in clean_q.lower() or " vs " in clean_q.lower():
            sub_queries.extend([
                f"{clean_q} benchmarks and technical architecture",
                f"{clean_q} developer adoption and community sentiment",
                f"{clean_q} production suitability and ecosystem maturity",
            ])
        elif domain == "technology":
            sub_queries.extend([
                f"official documentation: {clean_q}",
                f"developer sentiment and adoption: {clean_q}",
                f"benchmarks and production patterns: {clean_q}",
            ])
        elif domain == "science":
            sub_queries.extend([
                f"academic peer-reviewed research: {clean_q}",
                f"recent empirical findings: {clean_q}",
            ])
        elif domain == "business":
            sub_queries.extend([
                f"industry benchmark data: {clean_q}",
                f"market analysis and unit economics: {clean_q}",
                f"case studies and practitioner evidence: {clean_q}",
            ])
        else:
            sub_queries.extend([
                f"official announcement: {clean_q}",
                f"independent reporting: {clean_q}",
            ])

        return sub_queries[:4]

    def plan_research(self, query: str, user_mode: str = "auto") -> ResearchPlan:
        """Create a complete internal research plan."""
        domain = self.classify_domain(query)
        freshness = self.classify_freshness(query)
        depth = self.determine_depth(query, user_mode)
        categories = self.target_categories_for_domain(domain)
        sub_queries = self.generate_subqueries(query, domain, depth)

        status_msg = (
            "Formulating direct answer..." if depth == ResearchDepth.DIRECT else
            f"Searching {categories[0].value} sources..." if depth == ResearchDepth.TARGETED else
            f"Researching {domain} across {len(sub_queries)} queries..." if depth == ResearchDepth.STANDARD else
            f"Executing deep multi-query research ({len(sub_queries)} angles across {len(categories)} categories)..."
        )

        return ResearchPlan(
            depth=depth,
            domain=domain,
            sub_queries=sub_queries,
            target_categories=categories,
            freshness=freshness,
            status_message=status_msg,
        )
