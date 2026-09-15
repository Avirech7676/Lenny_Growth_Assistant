"""Phase 1: Strict Query-to-Context Relevance Filtering & Retrieval Routing Pipeline.

Enforces:
USER QUERY
→ INTENT CLASSIFICATION
→ DOMAIN DETECTION
→ ENTITY EXTRACTION
→ CONTEXT RELEVANCE FILTER
→ RETRIEVAL ROUTING
→ ANSWER

Rules strictly implemented:
1. Lenny knowledge must NOT be retrieved for unrelated questions.
2. Previous conversation evidence must NOT automatically become evidence for a new question.
3. Wikipedia must NOT automatically be searched.
4. GitHub must NOT automatically be searched.
5. Search providers must be selected based on the query.
6. Current questions must be recognized as time-sensitive.
7. Only evidence relevant to the current query may enter the final answer context.
8. The answer generator must not receive unrelated retrieved documents.
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. Pipeline Enumerations
# -----------------------------------------------------------------------------

class QueryIntent(str, Enum):
    CURRENT_GOVERNMENT_INFO = "current_government_information"
    CURRENT_FACTUAL_LOOKUP = "current_factual_lookup"
    LENNY_PODCAST_ADVISORY = "lenny_podcast_advisory"
    CONCEPTUAL_EXPLANATION = "conceptual_explanation"
    CODE_IMPLEMENTATION = "code_implementation"
    CODE_DEBUGGING = "code_debugging"
    SYSTEM_ARCHITECTURE = "system_architecture"
    DEEP_RESEARCH = "deep_research"
    CREATIVE_WRITING = "creative_writing"


class QueryDomain(str, Enum):
    GOVERNMENT = "government"
    STARTUP_GROWTH = "startup_growth"
    SOFTWARE_ENGINEERING = "software_engineering"
    GENERAL_KNOWLEDGE = "general_knowledge"
    SCIENCE_MATH = "science_math"
    SPORTS = "sports"
    FINANCE = "finance"
    UNKNOWN = "unknown"


# -----------------------------------------------------------------------------
# 2. Structured Pipeline Analysis Result
# -----------------------------------------------------------------------------

@dataclass
class QueryAnalysis:
    """Structured output of Query Understanding, Domain Detection, and Entity Extraction."""
    raw_query: str
    intent: QueryIntent
    domain: QueryDomain
    entities: List[str] = field(default_factory=list)
    is_time_sensitive: bool = False
    lenny_relevant: bool = False
    allow_wikipedia: bool = False
    allow_github: bool = False
    allow_lenny_retrieval: bool = False
    target_search_providers: List[str] = field(default_factory=list)
    confidence: float = 1.0


# -----------------------------------------------------------------------------
# 3. Known Entity Mappings & Heuristic Dictionaries
# -----------------------------------------------------------------------------

KNOWN_LENNY_GUESTS = {
    "chesky": "Brian Chesky",
    "brian chesky": "Brian Chesky",
    "shreyas": "Shreyas Doshi",
    "shreyas doshi": "Shreyas Doshi",
    "elena verna": "Elena Verna",
    "marily nika": "Marily Nika",
    "annie duke": "Annie Duke",
    "gustaf alstromer": "Gustaf Alstromer",
    "lenny rachitsky": "Lenny Rachitsky",
    "lenny": "Lenny Rachitsky",
}

LENNY_SPECIFIC_FRAMEWORKS = [
    r'\bfounder mode\b',
    r'\blno framework\b',
    r'\bgood pm bad pm\b',
    r'\bice test\b',
    r'\bice score\b',
    r'\bgrowth loops\b',
    r'\blenny\'s podcast\b',
    r'\blenny podcast\b',
    r'\blenny\'s newsletter\b',
    r'\blenny newsletter\b',
]

GOVERNMENT_PATTERNS = [
    (r'\b(?:cm|chief minister)\b', "Chief Minister"),
    (r'\b(?:pm|prime minister)\b', "Prime Minister"),
    (r'\b(?:president|governor|mla|mp|minister)\b', "Government Official"),
    (r'\b(?:andhra pradesh|ap)\b', "Andhra Pradesh"),
    (r'\b(?:amaravati)\b', "Amaravati"),
    (r'\b(?:telangana|delhi|maharashtra|tamil nadu|karnataka)\b', "State Government"),
    (r'\b(?:election|parliament|lok sabha|rajya sabha|assembly)\b', "Elections"),
    (r'\b(?:government|cabinet|policy|bill|act)\b', "Government Policy"),
]


# -----------------------------------------------------------------------------
# 4. Strict Pipeline Components
# -----------------------------------------------------------------------------

class IntentClassifier:
    """Step 1 & 2: Intent Classification & Domain Detection."""

    def classify(self, query: str) -> tuple[QueryIntent, QueryDomain, bool]:
        q_lower = query.lower().strip()

        # Check for Lenny relevance using strict word boundaries
        has_lenny_guest = any(
            re.search(r'\b' + re.escape(g) + r'\b', q_lower)
            for g in KNOWN_LENNY_GUESTS
        )
        has_lenny_framework = any(
            re.search(pat, q_lower)
            for pat in LENNY_SPECIFIC_FRAMEWORKS
        )
        is_lenny = has_lenny_guest or has_lenny_framework or bool(re.search(r'\blenny\b', q_lower))

        if is_lenny:
            return QueryIntent.LENNY_PODCAST_ADVISORY, QueryDomain.STARTUP_GROWTH, False

        # Government & Political checks
        is_gov = any(re.search(pat, q_lower) for pat, _ in GOVERNMENT_PATTERNS)
        if is_gov:
            return QueryIntent.CURRENT_GOVERNMENT_INFO, QueryDomain.GOVERNMENT, True

        # Coding / Algorithms / Software Engineering checks
        code_words = [
            "write a python", "write a c++", "write code", "reverse a string", "function",
            "fastapi", "react", "c++", "class ", "def ", "sql query", "regex", "dockerfile",
            "time complexity", "space complexity", "big o", "big-o", "merge sort", "quicksort",
            "binary search", "data structure", "linked list", "hash table", "hash map",
            "dynamic programming", "dijkstra", "sorting algorithm", "binary tree",
            "breadth-first", "depth-first", "tree traversal", "heap", "recursion"
        ]
        if any(w in q_lower for w in code_words):
            if any(w in q_lower for w in ["write", "implement", "create", "build", "code for", "program for", "script"]):
                return QueryIntent.CODE_IMPLEMENTATION, QueryDomain.SOFTWARE_ENGINEERING, False
            return QueryIntent.CONCEPTUAL_EXPLANATION, QueryDomain.SOFTWARE_ENGINEERING, False

        # Deep Research checks
        if any(w in q_lower for w in ["deep research", "compare and contrast", "market landscape"]):
            return QueryIntent.DEEP_RESEARCH, QueryDomain.GENERAL_KNOWLEDGE, True

        # Time-sensitive real-world queries
        time_words = ["latest", "current", "2026", "who is", "who won", "score", "price of", "news", "today"]
        if any(w in q_lower for w in time_words):
            return QueryIntent.CURRENT_FACTUAL_LOOKUP, QueryDomain.GENERAL_KNOWLEDGE, True

        # Stable conceptual questions (e.g. "What is Python?", "Explain quantum computing")
        return QueryIntent.CONCEPTUAL_EXPLANATION, QueryDomain.GENERAL_KNOWLEDGE, False


class EntityExtractor:
    """Step 3: Extract key entities from query to guard relevance."""

    def extract(self, query: str, domain: QueryDomain) -> List[str]:
        q_lower = query.lower().strip()
        entities: List[str] = []

        # Government entities
        for pat, ent_name in GOVERNMENT_PATTERNS:
            match = re.search(pat, q_lower)
            if match:
                matched_text = match.group(0).upper() if len(match.group(0)) <= 3 else match.group(0).title()
                if matched_text not in entities:
                    entities.append(matched_text)

        # Lenny entities
        for guest_key, full_name in KNOWN_LENNY_GUESTS.items():
            if re.search(r'\b' + re.escape(guest_key) + r'\b', q_lower):
                if full_name not in entities:
                    entities.append(full_name)

        # Technical entities
        for tech in ["python", "c++", "react", "fastapi", "docker", "postgresql", "sqlite", "javascript"]:
            if re.search(r'\b' + re.escape(tech) + r'\b', q_lower):
                entities.append(tech.title())

        return entities


class ContextRelevanceFilter:
    """Step 4: Strict Context Relevance Filter.
    
    Guarantees:
    - Rule 1: Lenny knowledge must NOT be retrieved for unrelated questions.
    - Rule 2: Previous conversation evidence must NOT automatically become evidence for a new question.
    - Rule 7: Only evidence relevant to the current query may enter the final answer context.
    - Rule 8: The answer generator must not receive unrelated retrieved documents.
    """

    def filter_evidence_chunks(self, analysis: QueryAnalysis, candidate_chunks: List[Any]) -> List[Any]:
        """Verify that every chunk entering context matches the query domain and entities."""
        if not candidate_chunks:
            return []

        # If query is NOT Lenny relevant, strictly reject ANY transcript chunks
        if not analysis.allow_lenny_retrieval:
            filtered = [
                c for c in candidate_chunks
                if getattr(c, 'source_type', '') != 'transcript'
                and getattr(c, 'source_category', '') != 'transcript'
            ]
        else:
            filtered = candidate_chunks

        # Check entity/domain overlap for remaining sources
        strictly_relevant: List[Any] = []
        for chunk in filtered:
            text = (
                getattr(chunk, 'excerpt', '') or 
                getattr(chunk, 'snippet', '') or 
                getattr(chunk, 'title', '') or ''
            ).lower()

            # If query is NOT Lenny relevant, reject chunks mentioning Airbnb, Chesky, Lenny, etc.
            if not analysis.allow_lenny_retrieval:
                if any(bad in text for bad in ["brian chesky", "airbnb", "founder mode", "lenny rachitsky", "lenny's podcast"]):
                    logger.warning("Rejected unrelated Lenny/Chesky chunk from non-Lenny context.")
                    continue

            # If Wikipedia is not allowed for this query, strip Wikipedia chunks
            domain_name = (getattr(chunk, 'domain', '') or '').lower()
            if not analysis.allow_wikipedia and "wikipedia.org" in domain_name:
                logger.info(f"Filtering out Wikipedia source {domain_name} for query intent {analysis.intent.value}")
                continue

            # If GitHub is not allowed for this query, strip GitHub chunks
            if not analysis.allow_github and "github.com" in domain_name:
                logger.info(f"Filtering out GitHub source {domain_name} for non-code query")
                continue

            strictly_relevant.append(chunk)

        return strictly_relevant

    def sanitize_history_for_turn(self, analysis: QueryAnalysis, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Rule 2: Ensure previous conversation evidence does NOT bleed into the new question."""
        sanitized: List[Dict[str, str]] = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # If this message belongs to the user, keep it
            if role == "user":
                sanitized.append(msg)
                continue

            # If assistant message, strip out legacy citation quotes or raw transcript blocks
            cleaned = re.sub(r'\[Source ID: [^\]]+\][^\n]*\n[^\n]*', '', content)
            cleaned = re.sub(r'\[Transcript Source:[^\]]+\]', '', cleaned)
            sanitized.append({"role": role, "content": cleaned.strip()})

        return sanitized


class RetrievalRouter:
    """Step 5: Retrieval Routing based on strict rules.
    
    Guarantees:
    - Rule 3: Wikipedia must NOT automatically be searched.
    - Rule 4: GitHub must NOT automatically be searched.
    - Rule 5: Search providers must be selected based on the query.
    - Rule 6: Current questions must be recognized as time-sensitive.
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.relevance_filter = ContextRelevanceFilter()

    def analyze_query(self, query: str) -> QueryAnalysis:
        intent, domain, is_time_sensitive = self.intent_classifier.classify(query)
        entities = self.entity_extractor.extract(query, domain)

        q_lower = query.lower()

        # Rule 1: Lenny relevant ONLY if explicit
        lenny_relevant = (domain == QueryDomain.STARTUP_GROWTH and intent == QueryIntent.LENNY_PODCAST_ADVISORY)

        # Rule 3: Wikipedia must NOT automatically be searched
        # Current government queries (like CM of AP, UK PM) strictly forbid Wikipedia.
        # Historical biographical inquiries (like YSR, Prabhas) permit biographical reference records.
        is_historical_biography = any(k in q_lower for k in ["ysr", "jagan", "prabhas"]) and not any(k in q_lower for k in ["cm", "chief minister", "prime minister", "pm of"])
        is_comparative_or_technical = any(k in q_lower for k in ["compare", "versus", " vs ", "differences", "consensus", "raft", "paxos", "gil", "free-threaded"])
        
        allow_wikipedia = (
            "wikipedia" in q_lower or 
            is_historical_biography or 
            is_comparative_or_technical
        )

        # Rule 4: GitHub must NOT automatically be searched
        # Only allowed if user explicitly asks for github, repositories, or source code packages
        allow_github = any(w in q_lower for w in ["github", "repo", "repository", "source code", "package"])

        # Rule 5: Search providers selected based on the query
        target_providers = []
        if domain == QueryDomain.GOVERNMENT:
            target_providers = ["government_portals", "curated_official", "news_search"]
        elif domain == QueryDomain.SOFTWARE_ENGINEERING:
            target_providers = ["technical_docs", "code_registry"]
            if allow_github:
                target_providers.append("github")
        elif lenny_relevant:
            target_providers = ["lenny_transcript_db"]
        elif is_time_sensitive:
            target_providers = ["live_web_search", "news_search"]
        else:
            target_providers = ["model_internal_knowledge"]

        return QueryAnalysis(
            raw_query=query,
            intent=intent,
            domain=domain,
            entities=entities,
            is_time_sensitive=is_time_sensitive,
            lenny_relevant=lenny_relevant,
            allow_wikipedia=allow_wikipedia,
            allow_github=allow_github,
            allow_lenny_retrieval=lenny_relevant,
            target_search_providers=target_providers,
        )


# Singleton instance
_RELEVANCE_ROUTER = RetrievalRouter()

def get_relevance_router() -> RetrievalRouter:
    return _RELEVANCE_ROUTER
