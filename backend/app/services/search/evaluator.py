"""Source quality engine, deduplication, conflict detection, and qualitative evidence strength evaluator."""

import re
import urllib.parse
from typing import List, Dict, Tuple, Set
from collections import defaultdict

from app.services.search.base import (
    DiscoveredSource,
    SourceCategory,
    EvidenceStrength,
    ResearchConflict,
)

def normalize_url(raw_url: str) -> str:
    """Normalize URL by stripping tracking parameters, fragments, and trailing slashes."""
    try:
        parsed = urllib.parse.urlparse(raw_url)
        # Filter out common tracking query params
        query_params = urllib.parse.parse_qsl(parsed.query)
        clean_params = [
            (k, v) for k, v in query_params
            if not k.startswith("utm_") and k not in {"ref", "source", "fbclid", "gclid"}
        ]
        clean_query = urllib.parse.urlencode(clean_params)
        netloc = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.rstrip("/")
        return urllib.parse.urlunparse((parsed.scheme, netloc, path, "", clean_query, ""))
    except Exception:
        return raw_url.strip().lower()

class SourceQualityEngine:
    """Evaluates credibility, deduplicates entries, detects conflicts, and rates evidence strength."""

    def deduplicate_sources(self, sources: List[DiscoveredSource]) -> List[DiscoveredSource]:
        """Remove exact URL duplicates and duplicate titles across discovered sources."""
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_sources: List[DiscoveredSource] = []

        for src in sources:
            norm_url = normalize_url(src.url)
            norm_title = re.sub(r'[^a-zA-Z0-9]', '', src.title.lower())[:40]

            if norm_url in seen_urls:
                continue
            if norm_title and norm_title in seen_titles:
                continue

            seen_urls.add(norm_url)
            if norm_title:
                seen_titles.add(norm_title)
            unique_sources.append(src)

        return unique_sources

    def score_source_relevance(self, query: str, source: DiscoveredSource) -> float:
        """Score keyword alignment between query and source title/snippet."""
        q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower()))
        if not q_tokens:
            return 0.80

        text_to_check = f"{source.title} {source.snippet}".lower()
        matched = sum(1 for tok in q_tokens if tok in text_to_check)
        ratio = matched / len(q_tokens)
        return round(0.5 + (0.5 * min(ratio, 1.0)), 3)

    def evaluate_and_rank(self, query: str, sources: List[DiscoveredSource]) -> List[DiscoveredSource]:
        """Calculate composite quality score and sort sources with primary authority preference."""
        deduped = self.deduplicate_sources(sources)

        for src in deduped:
            relevance = self.score_source_relevance(query, src)
            # Authority calculation: official & primary sources get prioritized
            authority_weight = 0.50 if src.is_primary else 0.35
            relevance_weight = 0.35
            freshness_weight = 0.15

            composite_score = (
                (authority_weight * src.authority_score) +
                (relevance_weight * relevance) +
                (freshness_weight * 0.90)
            )
            src.authority_score = round(composite_score, 3)

        # Sort by composite authority and primary source flag
        deduped.sort(key=lambda s: (s.is_primary, s.authority_score), reverse=True)
        return deduped

    def detect_conflicts(self, sources: List[DiscoveredSource]) -> List[ResearchConflict]:
        """Detect factual contradictions (e.g. mismatched version numbers or conflicting dates)."""
        conflicts: List[ResearchConflict] = []
        if len(sources) < 2:
            return conflicts

        # Group discovered version numbers by domain
        version_pattern = re.compile(r'\bv?(\d+\.\d+(?:\.\d+)?)\b')
        domain_versions: Dict[str, Set[str]] = defaultdict(set)

        for src in sources:
            text = f"{src.title} {src.snippet}"
            for v in version_pattern.findall(text):
                if v not in {"1.0", "2.0"}:
                    domain_versions[src.domain].add(v)

        distinct_domains = [d for d, vs in domain_versions.items() if vs]
        if len(distinct_domains) >= 2:
            d1, d2 = distinct_domains[0], distinct_domains[1]
            max_v1 = max(domain_versions[d1], key=lambda x: [int(p) for p in x.split('.') if p.isdigit()])
            max_v2 = max(domain_versions[d2], key=lambda x: [int(p) for p in x.split('.') if p.isdigit()])

            # If major/minor versions differ between domains
            v1_major = max_v1.split('.')[0]
            v2_major = max_v2.split('.')[0]
            if v1_major != v2_major or max_v1 != max_v2:
                conflicts.append(
                    ResearchConflict(
                        topic="Version Discrepancy",
                        source_a=d1,
                        claim_a=f"Mentions version {max_v1}",
                        source_b=d2,
                        claim_b=f"Mentions version {max_v2}",
                        explanation=(
                            f"Sources reference differing releases ({max_v1} on {d1} vs {max_v2} on {d2}). "
                            f"Prioritizing the primary release documentation."
                        )
                    )
                )

        return conflicts


    def calculate_evidence_strength(
        self,
        sources: List[DiscoveredSource],
        conflicts: List[ResearchConflict]
    ) -> EvidenceStrength:
        """Determine qualitative evidence strength without fake percentage values."""
        if not sources:
            return EvidenceStrength.LIMITED

        has_primary = any(s.is_primary for s in sources)
        categories = {s.category for s in sources}
        avg_authority = sum(s.authority_score for s in sources) / len(sources)

        # If conflicts exist and no dominant primary source resolves it -> Limited
        if conflicts and not has_primary:
            return EvidenceStrength.LIMITED

        # Strong evidence: primary source verified or multiple distinct categories agree
        if (has_primary and len(sources) >= 2) or (len(categories) >= 3 and avg_authority >= 0.85):
            return EvidenceStrength.STRONG

        # Moderate evidence: at least 2 sources with reasonable authority
        if len(sources) >= 2 and avg_authority >= 0.75:
            return EvidenceStrength.MODERATE

        return EvidenceStrength.LIMITED
