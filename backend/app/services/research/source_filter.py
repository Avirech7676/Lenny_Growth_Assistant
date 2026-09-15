"""Advanced source filtering and constraint extraction for precision research."""

import re
from typing import List, Optional
from app.services.search.base import DiscoveredSource, SourceCategory
from app.services.research.models import ResearchConstraint


def parse_research_constraints(query: str, instruction: Optional[str] = None) -> ResearchConstraint:
    """Detect advanced filtering constraints from query or explicit research instruction."""
    combined = f"{query} {instruction or ''}".lower()
    constraint = ResearchConstraint()

    # 1. Official Sources Only
    if any(k in combined for k in ["only official", "official sources only", "official docs only", "from official documentation"]):
        constraint.only_official = True
        constraint.allowed_categories = [SourceCategory.OFFICIAL, SourceCategory.GOVERNMENT, SourceCategory.TECHNICAL]

    # 2. Academic Papers Only
    if any(k in combined for k in ["academic only", "academic papers", "peer-reviewed", "arxiv only", "scientific papers"]):
        constraint.only_academic = True
        constraint.allowed_categories = [SourceCategory.ACADEMIC]

    # 3. Government Records Only
    if any(k in combined for k in ["government only", "government sources", "official government", "census only", "sec filings"]):
        constraint.only_government = True
        constraint.allowed_categories = [SourceCategory.GOVERNMENT, SourceCategory.FINANCIAL]

    # 4. Domain Exclusions (e.g., exclude reddit, exclude wikipedia)
    if "exclude reddit" in combined or "no reddit" in combined:
        constraint.excluded_domains.append("reddit.com")
    if "exclude wikipedia" in combined or "no wikipedia" in combined:
        constraint.excluded_domains.append("wikipedia.org")

    # 5. Time Window
    if "last 30 days" in combined or "past month" in combined:
        constraint.time_window_days = 30
    elif "last 7 days" in combined or "past week" in combined:
        constraint.time_window_days = 7
    elif "last year" in combined or "past year" in combined:
        constraint.time_window_days = 365

    return constraint


def apply_source_filters(
    sources: List[DiscoveredSource],
    constraints: ResearchConstraint,
) -> List[DiscoveredSource]:
    """Filter and prioritize discovered sources based on constraints."""
    filtered = []

    for s in sources:
        # Check domain exclusion
        if any(excluded in s.domain.lower() for excluded in constraints.excluded_domains):
            continue

        # Check allowed category restriction
        if constraints.allowed_categories:
            if s.category not in constraints.allowed_categories:
                # If only_official, allow high-authority official domains even if labeled reference
                if constraints.only_official and s.authority_score >= 0.95:
                    pass
                else:
                    continue

        # Check only government
        if constraints.only_government and s.category != SourceCategory.GOVERNMENT:
            if not s.domain.endswith(".gov") and not s.domain.endswith(".gov.in"):
                continue

        # Check only academic
        if constraints.only_academic and s.category != SourceCategory.ACADEMIC:
            if not any(a in s.domain.lower() for a in ["arxiv", "acm.org", "ieee.org", "nature.com", "science.org", ".edu"]):
                continue

        filtered.append(s)

    # Boost prioritized domains if specified
    if constraints.prioritized_domains:
        for s in filtered:
            if any(p in s.domain.lower() for p in constraints.prioritized_domains):
                s.authority_score = min(1.0, s.authority_score + 0.1)

    return filtered
