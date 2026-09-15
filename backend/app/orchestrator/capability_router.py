"""Capability Router for AI Orchestrator.

Determines which of the 14 capabilities are required for a request:
- GENERAL_QA
- RESEARCH
- DEEP_RESEARCH
- CODING
- DEBUGGING
- CODE_REVIEW
- ARCHITECTURE
- DATA_ANALYSIS
- DOCUMENT_ANALYSIS
- WRITING
- PLANNING
- ARTIFACT_GENERATION
- LENNY_RESEARCH
- HYBRID_TASK

Supports compound multi-capability selection based on semantic intent rather
than simplistic keyword matching.
"""

from typing import List, Optional
import re
from app.orchestrator.types import Capability, IntentProfile


class CapabilityRouter:
    """Intelligently routes requests to single or multiple coordinated capabilities."""

    def route(self, query: str, intent_profile: IntentProfile, user_mode: str = "auto") -> List[Capability]:
        """Map intent profile and query structure to an ordered list of required capabilities."""
        q_clean = query.strip()
        q_lower = q_clean.lower()
        mode = user_mode.lower()

        selected: List[Capability] = []

        # ------------------------------------------------------------------
        # 1. COMPOUND & MULTI-CAPABILITY EVALUATION
        # ------------------------------------------------------------------
        # Case A: Research + Coding (e.g. "Research current FastAPI authentication and implement it")
        is_research_and_code = (
            intent_profile.primary_goal == "research_and_implement"
            or (
                any(w in q_lower for w in ["research", "investigate", "look up", "find current", "latest specs"])
                and any(w in q_lower for w in ["implement", "write code", "build an api", "create a script", "code it"])
            )
        )
        if is_research_and_code:
            return [Capability.RESEARCH, Capability.CODING]

        # Case B: Code Review + Debugging + Coding (e.g. "Review this code, find the security bug, and write the fix")
        is_review_and_fix = (
            ("review" in q_lower or "audit" in q_lower)
            and ("bug" in q_lower or "flaw" in q_lower or "issue" in q_lower or "vulnerability" in q_lower)
            and ("fix" in q_lower or "implement" in q_lower or "correct" in q_lower)
        )
        if is_review_and_fix:
            return [Capability.CODE_REVIEW, Capability.DEBUGGING, Capability.CODING]

        # Case C: Data Analysis + Planning + Artifact Generation (e.g. "Analyze our churn metrics, create an experiment plan, and generate a dashboard")
        is_data_plan_artifact = (
            any(w in q_lower for w in ["metrics", "retention", "churn", "data", "numbers"])
            and any(w in q_lower for w in ["plan", "experiment", "roadmap", "playbook"])
            and any(w in q_lower for w in ["dashboard", "canvas", "artifact", "visualize", "chart"])
        )
        if is_data_plan_artifact:
            return [Capability.DATA_ANALYSIS, Capability.PLANNING, Capability.ARTIFACT_GENERATION]

        # Case D: Lenny Research + Planning (e.g. "What did Brian Chesky say about founder mode, and create an experiment plan for our team?")
        if intent_profile.requires_lenny_knowledge and any(w in q_lower for w in ["plan", "experiment", "roadmap", "playbook", "ice score", "actionable steps"]):
            caps = [Capability.LENNY_RESEARCH, Capability.PLANNING]
            if any(w in q_lower for w in ["canvas", "dashboard", "matrix", "artifact"]):
                caps.append(Capability.ARTIFACT_GENERATION)
            return caps

        # Case E: Lenny Research + Writing (e.g. "Synthesize Shreyas Doshi's LNO framework into an essay/memo")
        if intent_profile.requires_lenny_knowledge and (
            mode == "ship30" or any(w in q_lower for w in ["essay", "memo", "article", "newsletter", "write up", "manifesto"])
        ):
            return [Capability.LENNY_RESEARCH, Capability.WRITING]

        # Case F: Hybrid Task (Combining Lenny turnaround principles with current 2026 market benchmarks)
        if intent_profile.requires_lenny_knowledge and (
            intent_profile.is_time_sensitive or any(w in q_lower for w in ["combine", "compare with current", "2026 market", "today's startups"])
        ):
            return [Capability.HYBRID_TASK, Capability.RESEARCH, Capability.LENNY_RESEARCH]

        # Case G: Document Analysis + Web Research (e.g. "Analyze this PDF and compare it with current market information")
        is_doc_and_research = (
            any(w in q_lower for w in ["document", "pdf", "file", "report", "csv", "spreadsheet", "docx", "xlsx"])
            and any(w in q_lower for w in ["current market", "web research", "current information", "latest market", "latest pricing", "compare with current", "online research", "current benchmarks"])
        )
        if is_doc_and_research:
            return [Capability.DOCUMENT_ANALYSIS, Capability.RESEARCH]

        # ------------------------------------------------------------------
        # 2. CODE REVIEW
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "code_review" or any(w in q_lower for w in ["code review", "review this pr", "audit this code"]):
            selected.append(Capability.CODE_REVIEW)
            if "fix" in q_lower or "suggest code" in q_lower:
                selected.append(Capability.CODING)
            return selected

        # ------------------------------------------------------------------
        # 3. DEBUGGING
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "code_debugging" or any(w in q_lower for w in ["debug", "error:", "exception:", "traceback", "fix this error"]):
            selected.append(Capability.DEBUGGING)
            selected.append(Capability.CODING)
            return selected

        # ------------------------------------------------------------------
        # 4. SYSTEM ARCHITECTURE
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "system_architecture" or any(w in q_lower for w in ["system architecture", "design a database", "schema design", "microservices architecture"]):
            selected.append(Capability.ARCHITECTURE)
            if "compare" in q_lower or intent_profile.is_time_sensitive:
                selected.insert(0, Capability.RESEARCH)
            return selected

        # ------------------------------------------------------------------
        # 5. DATA ANALYSIS
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "data_analysis" or any(w in q_lower for w in ["cohort retention", "calculate ltv", "churn rate calculation", "analyze the metrics"]):
            selected.append(Capability.DATA_ANALYSIS)
            if any(w in q_lower for w in ["dashboard", "canvas", "visualize"]):
                selected.append(Capability.ARTIFACT_GENERATION)
            return selected

        # ------------------------------------------------------------------
        # 6. DOCUMENT ANALYSIS
        # ------------------------------------------------------------------
        if any(w in q_lower for w in ["document", "pdf", "transcript analysis", "extract insights from the file", "summarize the report"]):
            selected.append(Capability.DOCUMENT_ANALYSIS)
            return selected

        # ------------------------------------------------------------------
        # 7. WRITING & CONTENT CREATION
        # ------------------------------------------------------------------
        if mode == "ship30" or intent_profile.primary_goal == "content_creation" or any(w in q_lower for w in ["viral essay", "ship 30", "draft an essay", "product announcement"]):
            selected.append(Capability.WRITING)
            if any(w in q_lower for w in ["canvas", "artifact", "matrix"]):
                selected.append(Capability.ARTIFACT_GENERATION)
            return selected

        # ------------------------------------------------------------------
        # 8. STRATEGIC PLANNING & EXPERIMENTS
        # ------------------------------------------------------------------
        if mode in ("experiment", "playbook") or intent_profile.primary_goal == "strategic_planning" or any(w in q_lower for w in ["ice score", "growth experiment", "experimentation roadmap", "sprint plan"]):
            selected.append(Capability.PLANNING)
            selected.append(Capability.ARTIFACT_GENERATION)
            return selected

        # ------------------------------------------------------------------
        # 9. STANDALONE ARTIFACT GENERATION
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "artifact_generation" or any(w in q_lower for w in ["growth canvas", "create a dashboard", "render a widget", "mermaid flowchart"]):
            selected.append(Capability.ARTIFACT_GENERATION)
            return selected

        # ------------------------------------------------------------------
        # 10. CODING
        # ------------------------------------------------------------------
        if intent_profile.primary_goal == "code_generation" or any(w in q_lower for w in [
            "write a python", "write a function", "write code", "implement a", "c++ program", "reverse a string", "fibonacci", "build a fastapi"
        ]):
            selected.append(Capability.CODING)
            if intent_profile.requires_external_web:
                selected.insert(0, Capability.RESEARCH)
            return selected

        # ------------------------------------------------------------------
        # 11. DEEP RESEARCH
        # ------------------------------------------------------------------
        if mode == "deep" or intent_profile.primary_goal == "deep_research_comparison" or any(w in q_lower for w in ["deep research", "versus", " vs ", "difference between", "comprehensive analysis"]):
            selected.append(Capability.DEEP_RESEARCH)
            return selected

        # ------------------------------------------------------------------
        # 12. LENNY RESEARCH
        # ------------------------------------------------------------------
        if intent_profile.requires_lenny_knowledge:
            selected.append(Capability.LENNY_RESEARCH)
            return selected

        # ------------------------------------------------------------------
        # 13. REAL-WORLD WEB RESEARCH
        # ------------------------------------------------------------------
        if intent_profile.requires_external_web or intent_profile.is_time_sensitive or any(w in q_lower for w in ["who is", "who won", "what is the capital", "cm of", "latest", "current", "2026"]):
            selected.append(Capability.RESEARCH)
            return selected

        # ------------------------------------------------------------------
        # 14. GENERAL QA (Conceptual explanations, math, static definitions)
        # ------------------------------------------------------------------
        return [Capability.GENERAL_QA]
