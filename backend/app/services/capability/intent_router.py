"""Intelligent Query Understanding, Strict Relevance Gating, and Full-Spectrum Capability Router."""

import re
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

class AgentCapability(str, Enum):
    """Full-spectrum capabilities for a production-grade AI assistant."""
    GENERAL_QA = "general_qa"
    WEB_RESEARCH = "web_research"
    DEEP_RESEARCH = "deep_research"
    CODING = "coding"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    WRITING = "writing"
    PLANNING = "planning"
    LENNY_RESEARCH = "lenny_research"
    HYBRID_RESEARCH = "hybrid_research"

@dataclass
class IntentClassification:
    """Comprehensive structured classification of incoming user intent."""
    capability: AgentCapability
    intent: str
    domain: str
    entity: Optional[str] = None
    time_sensitive: bool = False
    requires_web: bool = False
    lenny_relevant: bool = False
    research_depth: str = "direct"  # "direct", "targeted", "standard", "deep"
    source_types: List[str] = field(default_factory=list)
    confidence: float = 1.0
    suggested_skill: Optional[str] = None

# Curated Lenny entities, guests, and frameworks
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

LENNY_FRAMEWORKS = {
    "founder mode",
    "lno framework",
    "lno",
    "good pm bad pm",
    "ice score",
    "ice test",
    "growth loops",
    "plg loops",
    "lenny's podcast",
    "lenny podcast",
    "lenny's newsletter",
    "lenny newsletter",
}

def is_lenny_relevant(query: str) -> bool:
    """Strict relevance gate for Lenny's transcript knowledge base.
    
    Returns True ONLY if the query explicitly references Lenny, a known guest,
    or a podcast-specific framework. Otherwise returns False to prevent any
    unrelated real-world queries from retrieving transcript evidence.
    """
    q_lower = query.lower()
    
    # 1. Explicit reference to Lenny
    if re.search(r'\blenny\b', q_lower) or re.search(r'\blenny\'s\b', q_lower):
        return True
        
    # 2. Explicit citation or attribution phrase
    if any(phrase in q_lower for phrase in ["according to lenny", "from the podcast", "from the transcript", "lenny recommends", "lenny said"]):
        return True

    # 3. Known podcast guests (word boundaries)
    for guest_key in KNOWN_LENNY_GUESTS:
        if re.search(r'\b' + re.escape(guest_key) + r'\b', q_lower):
            return True

    # 4. Known Lenny podcast frameworks (word boundaries)
    for framework in LENNY_FRAMEWORKS:
        if re.search(r'\b' + re.escape(framework) + r'\b', q_lower):
            return True

    return False


class QueryUnderstandingEngine:
    """Production-grade query understanding engine performing domain classification,
    time-sensitivity detection, strict relevance gating, and capability routing.
    """

    def analyze(self, query: str, user_mode_override: Optional[str] = None, session_history: Optional[List[Dict[str, str]]] = None) -> IntentClassification:
        q_clean = query.strip()
        q_lower = q_clean.lower()
        mode_override = (user_mode_override or "auto").lower()

        lenny_rel = is_lenny_relevant(q_clean)

        # -------------------------------------------------------------
        # 1. Explicit User Mode Overrides
        # -------------------------------------------------------------
        if mode_override in ("deep", "deep_research"):
            return IntentClassification(
                capability=AgentCapability.DEEP_RESEARCH,
                intent="deep_research",
                domain="research",
                time_sensitive=True,
                requires_web=True,
                lenny_relevant=lenny_rel,
                research_depth="deep",
                source_types=["official", "academic", "news", "technical", "industry"],
            )

        # -------------------------------------------------------------
        # 2. Coding, Debugging, and Technical Implementation
        # -------------------------------------------------------------
        is_coding = any(k in q_lower for k in [
            "write a python", "write a function", "write code", "implement", "create a react",
            "build a fastapi", "def ", "class ", "sql query", "write a script", "regex for",
            "reverse a string", "fibonacci", "dockerfile", "c++", "golang", "rust function",
            "typescript", "javascript function"
        ])
        algo_keywords = [
            "time complexity", "space complexity", "big o", "big-o", "merge sort", "quicksort",
            "binary search", "data structure", "linked list", "hash table", "hash map",
            "dynamic programming", "dijkstra", "sorting algorithm", "binary tree",
            "breadth-first", "depth-first", "tree traversal", "heap", "recursion"
        ]
        is_algo = any(k in q_lower for k in algo_keywords)
        is_debugging = any(k in q_lower for k in [
            "fix this", "debug", "error:", "exception:", "traceback", "syntaxerror",
            "why does this fail", "why is my api returning 500", "fix the error", "bug in"
        ])
        is_architecture = any(k in q_lower for k in [
            "system architecture", "design a database", "software architecture",
            "microservices vs monolith", "multi-tenant architecture", "database schema design"
        ])

        if is_debugging:
            return IntentClassification(
                capability=AgentCapability.DEBUGGING,
                intent="code_debugging",
                domain="software_engineering",
                time_sensitive=False,
                requires_web=False,
                lenny_relevant=False,
                research_depth="direct",
                source_types=["technical"],
            )

        if is_architecture:
            return IntentClassification(
                capability=AgentCapability.ARCHITECTURE,
                intent="software_architecture",
                domain="software_engineering",
                time_sensitive=False,
                requires_web=False,
                lenny_relevant=False,
                research_depth="direct",
                source_types=["technical"],
            )

        is_complexity = any(w in q_lower for w in ["time complexity", "space complexity", "big o", "big-o", "complexity of", "worst-case", "best-case"])
        is_conceptual = (
            bool(re.match(r'^(what is|what are|explain|describe)\b', q_lower))
            and not is_coding
            and not is_complexity
            and not any(w in q_lower for w in ["code", "program", "function", "write", "implement", "script", "c++", "cpp", "python script", "algorithm code"])
        )
        if is_algo and is_conceptual:
            return IntentClassification(
                capability=AgentCapability.GENERAL_QA,
                intent="conceptual_explanation",
                domain="computer_science",
                time_sensitive=False,
                requires_web=False,
                lenny_relevant=False,
                research_depth="direct",
                source_types=[],
            )

        if is_coding or is_algo:
            # Check if user specifically requested current API or docs
            needs_web = any(w in q_lower for w in ["latest", "current", "react 19", "next.js 15", "openai api v1"])
            return IntentClassification(
                capability=AgentCapability.CODING,
                intent="code_generation" if is_coding else "algorithm_complexity",
                domain="software_engineering",
                time_sensitive=needs_web,
                requires_web=needs_web,
                lenny_relevant=False,
                research_depth="targeted" if needs_web else "direct",
                source_types=["technical", "official"] if needs_web else [],
            )

        # -------------------------------------------------------------
        # 3. Lenny Knowledge & Specialized Podcast Growth Advisory
        # -------------------------------------------------------------
        if lenny_rel:
            # Check if query asks to combine Lenny with current 2026 real-world data
            is_hybrid = any(k in q_lower for k in [
                "combine", "compare with current", "market trends", "2026", "real-world data",
                "current startup", "latest benchmarks"
            ])
            if is_hybrid:
                return IntentClassification(
                    capability=AgentCapability.HYBRID_RESEARCH,
                    intent="hybrid_synthesis",
                    domain="startup_strategy",
                    time_sensitive=True,
                    requires_web=True,
                    lenny_relevant=True,
                    research_depth="standard",
                    source_types=["transcript", "industry", "news"],
                )
            return IntentClassification(
                capability=AgentCapability.LENNY_RESEARCH,
                intent="lenny_advisory",
                domain="growth_strategy",
                time_sensitive=False,
                requires_web=False,
                lenny_relevant=True,
                research_depth="targeted",
                source_types=["transcript"],
            )

        # -------------------------------------------------------------
        # 4. Deep Research & Multi-Source Comparison
        # -------------------------------------------------------------
        is_comparison = any(w in q_lower for w in [
            "compare", "versus", " vs ", "difference between", "better for", "should i use",
            "evaluate", "pros and cons"
        ])
        is_deep = is_comparison or any(w in q_lower for w in [
            "deep research", "market analysis", "comprehensive review", "state of", "trends in 2026"
        ])
        if is_deep or mode_override == "deep":
            return IntentClassification(
                capability=AgentCapability.DEEP_RESEARCH,
                intent="multi_source_comparison",
                domain="technical" if any(w in q_lower for w in ["postgres", "mongodb", "claude", "gemini", "gpt"]) else "general",
                time_sensitive=True,
                requires_web=True,
                lenny_relevant=False,
                research_depth="deep",
                source_types=["official", "technical", "industry", "academic"],
            )

        # -------------------------------------------------------------
        # 5. Real-World Web Research (Current facts, politicians, sports, news, prices)
        # -------------------------------------------------------------
        gov_keywords = [
            "cm of", "chief minister", "prime minister", "president of", "capital of",
            "andhra pradesh", "amaravati", "governor", "election", "parliament"
        ]
        is_gov_political = any(k in q_lower for k in gov_keywords) or bool(re.search(r'\b(mp|mla)\b', q_lower))
        is_temporal_current = any(k in q_lower for k in [
            "latest", "current", "2026", "today", "yesterday", "recent", "now", "who won",
            "price of", "stock", "news", "score", "match", "weather", "released"
        ])
        is_specific_factual = any(k in q_lower for k in [
            "who is", "who won", "what is the capital", "what is the version", "when did"
        ])

        if is_gov_political or is_temporal_current or is_specific_factual or mode_override == "search":
            domain = "government" if is_gov_political else ("sports" if "won" in q_lower or "score" in q_lower else "general")
            return IntentClassification(
                capability=AgentCapability.WEB_RESEARCH,
                intent="current_factual_lookup",
                domain=domain,
                entity="Andhra Pradesh" if "ap" in q_lower or "andhra pradesh" in q_lower else None,
                time_sensitive=True,
                requires_web=True,
                lenny_relevant=False,
                research_depth="targeted",
                source_types=["official", "government", "news"],
            )

        # -------------------------------------------------------------
        # 6. General Knowledge (Stable concepts, science explanations, definitions)
        # -------------------------------------------------------------
        # Stable questions like "What is recursion?", "What is a binary tree?", "Explain quantum computing"
        return IntentClassification(
            capability=AgentCapability.GENERAL_QA,
            intent="conceptual_explanation",
            domain="general",
            time_sensitive=False,
            requires_web=False,
            lenny_relevant=False,
            research_depth="direct",
            source_types=[],
        )

# Global singleton engine
_INTENT_ENGINE = QueryUnderstandingEngine()

def get_query_understanding_engine() -> QueryUnderstandingEngine:
    return _INTENT_ENGINE
