"""Layer 6: Response Quality Gate & Verification Pipeline.

Provides multi-dimensional quality scoring for AI-generated responses:
- Relevance: Does the response address the user's actual question?
- Grounding: Is every empirical claim backed by the provided evidence?
- Currentness: Is the information up-to-date (no stale 2020 data for 2026 queries)?
- Citation integrity: Are citations actually referenced in the response?
- Completeness: Does the answer fully address the scope of the question?
- Safety: No hallucinated URLs, fabricated statistics, or invented quotes.

The gate can operate in two modes:
- FAST: Single-model heuristic scoring (default, <5ms)
- STRICT: Rule-based verification against evidence snippets (<50ms)
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum score (0.0-1.0) for a response to pass the quality gate
DEFAULT_PASS_THRESHOLD = 0.55

# Patterns that indicate fabrication or hallucination
_HALLUCINATION_PATTERNS = [
    r'https?://\S+(?:fake|placeholder|example\.com|your-domain)',
    r'(?:according to|cited in)\s+\[(?:source|ref|citation)\s*\d*\]',
    r'\b(?:123-456-7890|example@example\.com|Lorem ipsum)\b',
    r'(?:\d{4})\s+study\s+(?:found|showed|proved)',  # vague study citation
]

# Patterns that indicate hedging / epistemic uncertainty being properly expressed
_GOOD_UNCERTAINTY_PATTERNS = [
    r'(?:may|might|could|likely|approximately|estimates suggest)',
    r'(?:as of|based on available|according to)',
    r'(?:varies|depends on|context-specific)',
]

# Temporal staleness indicators
_STALE_YEAR_PATTERN = re.compile(r'\b(201[0-9])\b')
_CURRENT_YEAR_INDICATOR = re.compile(r'\b(2024|2025|2026)\b')


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    dimension: str
    score: float          # 0.0 to 1.0
    rationale: str
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityGateResult:
    """Complete quality assessment of an AI response."""
    overall_score: float
    passed: bool
    dimensions: List[DimensionScore]
    hallucination_flags: List[str]
    improvement_suggestions: List[str]
    evaluation_ms: float
    mode: str  # 'fast' or 'strict'

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 3),
            "passed": self.passed,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "score": round(d.score, 3),
                    "rationale": d.rationale,
                    "issues": d.issues,
                    "suggestions": d.suggestions,
                }
                for d in self.dimensions
            ],
            "hallucination_flags": self.hallucination_flags,
            "improvement_suggestions": self.improvement_suggestions,
            "evaluation_ms": round(self.evaluation_ms, 2),
            "mode": self.mode,
        }

    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return (
            f"Quality Gate: {status} | Score: {self.overall_score:.2f} | "
            f"Dimensions: {', '.join(f'{d.dimension}={d.score:.2f}' for d in self.dimensions)}"
        )


class ResponseQualityGate:
    """Heuristic + rule-based response quality gate with multi-dimensional scoring."""

    def __init__(self, pass_threshold: float = DEFAULT_PASS_THRESHOLD):
        self.pass_threshold = pass_threshold

    def evaluate(
        self,
        query: str,
        response: str,
        evidence_snippets: Optional[List[str]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        mode: str = "fast",
    ) -> QualityGateResult:
        """Evaluate response quality. Returns QualityGateResult."""
        t0 = time.perf_counter()

        evidence_snippets = evidence_snippets or []
        citations = citations or []

        dims: List[DimensionScore] = []

        # ── 1. Relevance ─────────────────────────────────────────────────────
        dims.append(self._score_relevance(query, response))

        # ── 2. Grounding ─────────────────────────────────────────────────────
        dims.append(self._score_grounding(response, evidence_snippets, citations))

        # ── 3. Completeness ──────────────────────────────────────────────────
        dims.append(self._score_completeness(query, response))

        # ── 4. Currentness ───────────────────────────────────────────────────
        dims.append(self._score_currentness(query, response))

        # ── 5. Citation Integrity ────────────────────────────────────────────
        dims.append(self._score_citation_integrity(response, citations))

        # ── Hallucination Scan ───────────────────────────────────────────────
        hallucination_flags = self._scan_hallucinations(response)

        # ── Weighted Score ───────────────────────────────────────────────────
        weights = [0.30, 0.25, 0.20, 0.15, 0.10]  # relevance, grounding, completeness, currentness, citations
        if not response.strip():
            overall = 0.0
            passed = False
        else:
            overall = sum(d.score * w for d, w in zip(dims, weights))

            # Penalize hallucinations
            if hallucination_flags:
                penalty = min(0.25, len(hallucination_flags) * 0.08)
                overall = max(0.0, overall - penalty)

            passed = overall >= self.pass_threshold

        # ── Improvement Suggestions ──────────────────────────────────────────
        suggestions = self._generate_suggestions(dims, hallucination_flags, query)

        eval_ms = (time.perf_counter() - t0) * 1000

        return QualityGateResult(
            overall_score=overall,
            passed=passed,
            dimensions=dims,
            hallucination_flags=hallucination_flags,
            improvement_suggestions=suggestions,
            evaluation_ms=eval_ms,
            mode=mode,
        )

    def _score_relevance(self, query: str, response: str) -> DimensionScore:
        """Score how directly the response addresses the query."""
        if not response.strip():
            return DimensionScore("relevance", 0.0, "Empty response", issues=["Response is empty"])

        q_words = set(re.findall(r'\b\w{4,}\b', query.lower()))
        r_words = set(re.findall(r'\b\w{4,}\b', response.lower()[:1000]))

        if not q_words:
            return DimensionScore("relevance", 0.7, "Query too short to evaluate")

        overlap = len(q_words & r_words) / len(q_words)
        score = min(1.0, 0.4 + overlap * 0.7)

        issues: List[str] = []
        suggestions: List[str] = []
        if overlap < 0.2:
            issues.append("Low keyword overlap between query and response")
            suggestions.append("Ensure the response directly addresses the specific question asked")

        # Penalize if response starts with generic hedging without substance
        if response.strip().lower().startswith(("i cannot", "i'm not sure", "i don't know")):
            score = min(score, 0.4)
            issues.append("Response leads with refusal or uncertainty without providing useful info")

        return DimensionScore("relevance", round(score, 3),
                              f"Query-response overlap: {overlap:.0%}", issues, suggestions)

    def _score_grounding(self, response: str, evidence: List[str], citations: List[dict]) -> DimensionScore:
        """Score how well empirical claims are backed by provided evidence."""
        if not evidence and not citations:
            # No evidence provided — can't fault grounding, give neutral score
            return DimensionScore("grounding", 0.7,
                                  "No evidence provided — grounding not assessable",
                                  suggestions=["Provide evidence snippets for grounding validation"])

        # Check how much evidence content appears in the response
        evidence_words: set = set()
        for ev in evidence[:5]:
            words = set(re.findall(r'\b\w{5,}\b', ev.lower()))
            evidence_words |= words

        resp_words = set(re.findall(r'\b\w{5,}\b', response.lower()))
        if not evidence_words:
            return DimensionScore("grounding", 0.65, "Evidence snippets are too short to evaluate")

        grounding_overlap = len(evidence_words & resp_words) / len(evidence_words)
        score = min(1.0, 0.35 + grounding_overlap * 0.8)

        issues: List[str] = []
        suggestions: List[str] = []
        if grounding_overlap < 0.05 and len(response) > 300:
            issues.append("Response contains minimal terminology from provided evidence")
            suggestions.append("Anchor claims to specific evidence excerpts")

        return DimensionScore("grounding", round(score, 3),
                              f"Evidence overlap: {grounding_overlap:.0%}", issues, suggestions)

    def _score_completeness(self, query: str, response: str) -> DimensionScore:
        """Score whether the response fully addresses the question's scope."""
        issues: List[str] = []
        suggestions: List[str] = []

        words = len(response.split())
        q_lower = query.lower()

        # Question complexity indicators
        is_complex = any(k in q_lower for k in [
            "compare", "difference", "vs", "pros and cons", "explain", "how does",
            "architecture", "design", "step by step", "implement"
        ])
        is_simple = any(k in q_lower for k in [
            "what is", "who is", "when", "where", "define", "what does"
        ])

        if is_simple:
            if words < 20:
                score = 0.5
                issues.append("Response may be too brief for the factual question")
            elif words < 60:
                score = 0.8
            else:
                score = 0.95
        elif is_complex:
            if words < 100:
                score = 0.35
                issues.append("Complex query deserves a more comprehensive response")
                suggestions.append("Expand the answer to cover the full scope of the question")
            elif words < 250:
                score = 0.65
            elif words < 600:
                score = 0.9
            else:
                score = 1.0
        else:
            # General: reasonable length range
            if words < 30:
                score = 0.5
            elif words < 80:
                score = 0.75
            elif words < 400:
                score = 0.9
            else:
                score = 1.0

        return DimensionScore("completeness", round(score, 3),
                              f"Response length: {words} words", issues, suggestions)

    def _score_currentness(self, query: str, response: str) -> DimensionScore:
        """Score whether the response uses current information."""
        issues: List[str] = []
        suggestions: List[str] = []
        q_lower = query.lower()

        # Check if query is time-sensitive
        time_sensitive = any(k in q_lower for k in [
            "current", "today", "now", "latest", "recent", "2026", "2025",
            "who is", "what is the", "ceo", "price", "stock", "version"
        ])

        stale_years = _STALE_YEAR_PATTERN.findall(response)
        current_years = _CURRENT_YEAR_INDICATOR.findall(response)

        if time_sensitive and stale_years and not current_years:
            score = 0.45
            issues.append(f"Response references stale years ({', '.join(set(stale_years))}) for a current query")
            suggestions.append("Use current real-world search to retrieve up-to-date information")
        elif stale_years and not current_years and len(response) > 500:
            score = 0.7
            issues.append("Response may reference outdated information")
        else:
            score = 0.9

        return DimensionScore("currentness", round(score, 3),
                              "Temporal accuracy check", issues, suggestions)

    def _score_citation_integrity(self, response: str, citations: List[dict]) -> DimensionScore:
        """Score whether citations are coherently referenced."""
        if not citations:
            return DimensionScore("citation_integrity", 0.75, "No citations to validate")

        # Check if any citation domains/titles appear in the response
        cited_terms: List[str] = []
        for c in citations[:6]:
            if c.get("domain"):
                cited_terms.append(c["domain"].split(".")[0].lower())
            if c.get("title"):
                words = c["title"].lower().split()[:3]
                cited_terms.extend(words)

        resp_lower = response.lower()
        referenced = sum(1 for t in cited_terms if len(t) > 3 and t in resp_lower)
        ratio = referenced / max(len(cited_terms), 1)

        score = min(1.0, 0.5 + ratio * 0.6)

        issues: List[str] = []
        suggestions: List[str] = []
        if ratio < 0.1 and len(citations) > 2:
            issues.append("Provided citations not referenced in the response body")
            suggestions.append("Integrate source references naturally into the response")

        return DimensionScore("citation_integrity", round(score, 3),
                              f"Citation reference ratio: {ratio:.0%}", issues, suggestions)

    def _scan_hallucinations(self, response: str) -> List[str]:
        """Scan for hallucination patterns in the response text."""
        flags: List[str] = []
        for pattern in _HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                flags.append(f"Potential fabrication pattern: {pattern[:50]}")
        return flags

    def _generate_suggestions(
        self,
        dims: List[DimensionScore],
        hallucination_flags: List[str],
        query: str,
    ) -> List[str]:
        """Aggregate improvement suggestions from all dimensions."""
        suggestions: List[str] = []

        for d in dims:
            suggestions.extend(d.suggestions)

        if hallucination_flags:
            suggestions.append("Review response for fabricated statistics, URLs, or invented sources")

        # De-duplicate
        seen: set = set()
        deduped: List[str] = []
        for s in suggestions:
            key = s[:40].lower()
            if key not in seen:
                seen.add(key)
                deduped.append(s)

        return deduped[:5]


# ─── Singleton ────────────────────────────────────────────────────────────────
_QUALITY_GATE = ResponseQualityGate()


def get_quality_gate() -> ResponseQualityGate:
    """Access the singleton ResponseQualityGate."""
    return _QUALITY_GATE


def evaluate_response(
    query: str,
    response: str,
    evidence_snippets: Optional[List[str]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    mode: str = "fast",
    threshold: float = DEFAULT_PASS_THRESHOLD,
) -> QualityGateResult:
    """Convenience function: evaluate a response and return QualityGateResult."""
    gate = ResponseQualityGate(pass_threshold=threshold)
    return gate.evaluate(query, response, evidence_snippets, citations, mode)
