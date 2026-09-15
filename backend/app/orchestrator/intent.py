"""Semantic Intent Understanding Engine for AI Orchestrator.

Performs multi-dimensional intent parsing:
- Semantic primary goal detection (beyond naive keyword spotting)
- Multi-domain detection
- Entity extraction
- Temporal & freshness requirements
- Complexity estimation
- Explicit operational constraints
"""

import re
from typing import List, Dict, Any, Optional
from app.orchestrator.types import IntentProfile
from app.services.capability.intent_router import is_lenny_relevant, KNOWN_LENNY_GUESTS, LENNY_FRAMEWORKS


class IntentUnderstanding:
    """Extracts true semantic intent, domain, entity, and constraints from natural language queries."""

    # Common operational action verbs and intent patterns
    CODING_VERB_PATTERNS = [
        r'\b(write|create|implement|build|code|develop|generate|scaffold)\b.*\b(function|script|program|class|component|endpoint|api|algorithm|service|hook|handler)\b',
        r'\b(reverse a string|fibonacci|binary search|quicksort|depth first|linked list)\b',
        r'\b(write|create)\b.*\b(python|c\+\+|javascript|typescript|golang|rust|java|html|css|sql)\b',
    ]

    DEBUGGING_PATTERNS = [
        r'\b(debug|fix|solve|resolve|diagnose)\b.*\b(error|bug|issue|exception|failure|crash|traceback|typo|segfault|leak)\b',
        r'(error:|exception:|traceback|syntaxerror|typeerror|indexerror|referenceerror|valueerror)',
        r'\bwhy (is this|does this|is my)\b.*\b(failing|broken|crashing|returning 500|throwing)\b',
    ]

    REVIEW_PATTERNS = [
        r'\b(review|audit|critique|inspect|analyze|check)\b.*\b(code|pr|pull request|security|vulnerability|flaws|efficiency|cleanliness)\b',
        r'\bcode review\b',
    ]

    ARCHITECTURE_PATTERNS = [
        r'\b(architect|design|structure|model)\b.*\b(system|architecture|database|schema|infrastructure|pipeline|microservice|distributed)\b',
        r'\b(monolith vs microservices|event-driven|event sourcing|cqrs|multi-tenant schema)\b',
    ]

    DATA_ANALYSIS_PATTERNS = [
        r'\b(calculate|analyze|compute|derive|evaluate)\b.*\b(retention|churn|ltv|cac|cohort|conversion|metrics|numbers|data|stats|benchmarks)\b',
        r'\b(statistical analysis|trend analysis|growth rate|mrr|arr)\b',
    ]

    WRITING_PATTERNS = [
        r'\b(draft|write|compose|author)\b.*\b(essay|viral essay|article|blog post|announcement|newsletter|memo|prd|manifesto|copy)\b',
        r'\b(ship 30 for 30|ship30)\b',
    ]

    PLANNING_PATTERNS = [
        r'\b(plan|create a plan|roadmap|strategy|playbook|schedule|milestones|timeline)\b',
        r'\b(ice score|ice framework|growth experiment|experiment plan|sprint plan|action plan)\b',
    ]

    ARTIFACT_PATTERNS = [
        r'\b(generate|create|render|visualize|build)\b.*\b(dashboard|canvas|diagram|flowchart|mermaid|chart|interactive|widget|table)\b',
        r'\b(growth canvas|ui mockup|interactive widget)\b',
    ]

    TEMPORAL_PATTERNS = [
        r'\b(current|currently|latest|recent|recently|today|now|2026|newest|released|who is the current|present)\b',
        r'\b(chief minister|prime minister|president|governor|who won|who is)\b',
    ]

    def understand(self, query: str, history: Optional[List[Dict[str, str]]] = None) -> IntentProfile:
        """Analyze query and extract a rich semantic IntentProfile."""
        q_raw = query.strip()
        q_lower = q_raw.lower()

        domains: List[str] = []
        entities: List[str] = []
        constraints: Dict[str, Any] = {}

        # 1. Detect Temporal Scope & Currentness
        is_temporal = any(re.search(p, q_lower) for p in self.TEMPORAL_PATTERNS)

        # 2. Extract Entities
        # Known political / state entities
        if re.search(r'\b(ap|andhra pradesh)\b', q_lower):
            entities.append("Andhra Pradesh")
            domains.append("government")
        if re.search(r'\b(india|bharat)\b', q_lower):
            entities.append("India")
            domains.append("government")
        if re.search(r'\b(us|united states|uk|britain)\b', q_lower):
            entities.append("International Politics")
            domains.append("government")

        # Known Tech Entities & Frameworks
        tech_entities = [
            ("fastapi", "FastAPI"),
            ("react", "React"),
            ("next.js", "Next.js"),
            ("python", "Python"),
            ("c++", "C++"),
            ("postgresql", "PostgreSQL"),
            ("mongodb", "MongoDB"),
            ("docker", "Docker"),
            ("kubernetes", "Kubernetes"),
            ("jwt", "JWT"),
            ("oauth", "OAuth"),
            ("redis", "Redis"),
            ("tailwind", "Tailwind CSS"),
        ]
        for token, formal in tech_entities:
            if token in q_lower:
                entities.append(formal)
                if "software_engineering" not in domains:
                    domains.append("software_engineering")

        # Known Lenny guests and frameworks
        for guest_key, formal in KNOWN_LENNY_GUESTS.items():
            if re.search(r'\b' + re.escape(guest_key) + r'\b', q_lower):
                entities.append(formal)
                if "startup_growth" not in domains:
                    domains.append("startup_growth")

        # 3. Assess Primary Goal & Complexity
        primary_goal = self._determine_primary_goal(q_raw, q_lower)

        # 4. Check Lenny Knowledge Need (Strict relevance gating)
        requires_lenny = is_lenny_relevant(q_raw)

        # 5. Check External Web Need
        # Web is required for current events, temporal queries, latest specs, external research
        requires_web = (
            is_temporal
            or "compare" in q_lower
            or "market" in q_lower
            or any(w in q_lower for w in ["research", "current", "latest", "benchmark", "pricing", "trends"])
            or ("government" in domains)
        ) and not (primary_goal == "general_explanation" and not is_temporal)

        # 6. Workspace Code Need
        requires_workspace = any(w in q_lower for w in ["repo", "codebase", "workspace", "our files", "in this project"])

        # 7. Complexity Estimation
        word_count = len(q_raw.split())
        has_multiple_conjunctions = len(re.findall(r'\b(and then|and also|and implement|and generate|and verify|and write)\b', q_lower)) > 0
        if has_multiple_conjunctions or word_count > 25:
            complexity = "complex"
        elif word_count > 10 or len(domains) > 1:
            complexity = "moderate"
        else:
            complexity = "simple"

        if not domains:
            domains.append("general")

        return IntentProfile(
            primary_goal=primary_goal,
            domains=domains,
            entities=list(dict.fromkeys(entities)),  # unique
            is_time_sensitive=is_temporal,
            requires_external_web=requires_web,
            requires_lenny_knowledge=requires_lenny,
            requires_workspace_code=requires_workspace,
            complexity=complexity,
            constraints=constraints,
            confidence=0.95,
        )

    def _determine_primary_goal(self, q_raw: str, q_lower: str) -> str:
        """Extract user's operational goal from grammatical composition."""
        # Compound research + code: e.g. "Research ... and implement it"
        if ("research" in q_lower or "investigate" in q_lower or "find" in q_lower) and any(
            re.search(p, q_lower) or "implement" in q_lower for p in self.CODING_VERB_PATTERNS
        ):
            return "research_and_implement"

        # Code review
        if any(re.search(p, q_lower) for p in self.REVIEW_PATTERNS):
            return "code_review"

        # Debugging
        if any(re.search(p, q_lower) for p in self.DEBUGGING_PATTERNS):
            return "code_debugging"

        # System Architecture
        if any(re.search(p, q_lower) for p in self.ARCHITECTURE_PATTERNS):
            return "system_architecture"

        # Data Analysis
        if any(re.search(p, q_lower) for p in self.DATA_ANALYSIS_PATTERNS):
            return "data_analysis"

        # Writing / Viral Essay / Content
        if any(re.search(p, q_lower) for p in self.WRITING_PATTERNS):
            return "content_creation"

        # Planning / Roadmap / Experimentation
        if any(re.search(p, q_lower) for p in self.PLANNING_PATTERNS):
            return "strategic_planning"

        # Interactive Artifact Generation
        if any(re.search(p, q_lower) for p in self.ARTIFACT_PATTERNS):
            return "artifact_generation"

        # Coding
        if any(re.search(p, q_lower) for p in self.CODING_VERB_PATTERNS) or "write code" in q_lower:
            return "code_generation"

        # Deep Research / Comparison
        if any(w in q_lower for w in ["deep research", "compare", "versus", " vs ", "difference between", "pros and cons", "evaluate"]):
            return "deep_research_comparison"

        # Factual Research / Current Events
        if any(re.search(p, q_lower) for p in self.TEMPORAL_PATTERNS) or any(w in q_lower for w in ["who is", "who won", "what is the capital"]):
            return "factual_lookup"

        # Conceptual Explanation
        return "general_explanation"
