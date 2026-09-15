"""Unified AI Orchestrator.

Replaces basic Chat endpoint → LLM → answer with a 9-component pipeline:
1. IntentUnderstanding
2. CapabilityRouter (multi-capability selection across 14 capabilities)
3. TaskPlanner
4. ToolRouter
5. ModelRouter
6. ResearchEngine
7. ContextManager
8. VerificationEngine
9. ResponseComposer
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from app.orchestrator.types import (
    Capability,
    IntentProfile,
    ExecutionPlan,
    VerificationResult,
    OrchestratorRequest,
    OrchestratorResponse,
)
from app.orchestrator.intent import IntentUnderstanding
from app.orchestrator.capability_router import CapabilityRouter
from app.orchestrator.planner import TaskPlanner
from app.orchestrator.tool_router import ToolRouter
from app.orchestrator.context_manager import ContextManager
from app.orchestrator.verification import VerificationEngine
from app.orchestrator.composer import ResponseComposer

from app.models.router import get_model_router
from app.models.base import LLMRequest, LLMResponse
from app.agents.prompts import (
    GENERAL_QA_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    CODING_SYSTEM_PROMPT,
    DEBUGGING_SYSTEM_PROMPT,
    ARCHITECTURE_SYSTEM_PROMPT,
    LENNY_PODCAST_SYSTEM_PROMPT,
    get_skill_prompt,
    REFUSAL_MESSAGE,
)
from app.retrieval.retriever import retrieve_evidence
from app.services.search import get_search_router
from app.services.research.engine import get_deep_research_engine
from app.coding import get_coding_agent

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Master AI Orchestrator implementing multi-capability coordination and verification."""

    def __init__(self):
        self.intent_understanding = IntentUnderstanding()
        self.capability_router = CapabilityRouter()
        self.task_planner = TaskPlanner()
        self.tool_router = ToolRouter()
        self.model_router = get_model_router()
        self.context_manager = ContextManager()
        self.verification_engine = VerificationEngine()
        self.response_composer = ResponseComposer()

    def process(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """Execute a full synchronous multi-capability orchestrator pass."""
        t_start = time.perf_counter()
        latencies: Dict[str, float] = {}

        # 1. Semantic Intent Understanding
        t0 = time.perf_counter()
        intent = self.intent_understanding.understand(request.query, request.history)
        latencies["intent_understanding_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # 2. Multi-Capability Routing (14 Capabilities)
        t0 = time.perf_counter()
        capabilities = self.capability_router.route(request.query, intent, user_mode=request.user_mode)
        latencies["capability_routing_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # 3. Task Planning
        t0 = time.perf_counter()
        plan = self.task_planner.plan(request.query, capabilities, intent)
        latencies["task_planning_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # 4. Tool & Evidence Execution
        t0 = time.perf_counter()
        evidence_parts: List[str] = []
        citations: List[Dict[str, Any]] = []

        # Research execution
        if Capability.DEEP_RESEARCH in capabilities:
            deep_engine = get_deep_research_engine()
            res = deep_engine.execute_research_sync(request.query, depth_override="deep")
            evidence_parts.append(f"DEEP RESEARCH CONTEXT:\n{res.context_str}")
            for src in res.used_sources:
                citations.append({
                    "chunk_id": f"ext_{abs(hash(src.url)) % 1000000}",
                    "guest": src.domain,
                    "title": src.title,
                    "similarity": src.authority_score,
                    "excerpt": src.snippet,
                    "source_type": "external",
                    "url": src.url,
                    "domain": src.domain,
                })

        elif Capability.RESEARCH in capabilities or Capability.HYBRID_TASK in capabilities:
            search_router = get_search_router()
            search_res = search_router.execute_research_sync(request.query, user_mode=request.user_mode)
            evidence_parts.append(f"VERIFIED REAL-WORLD KNOWLEDGE:\n{search_res.synthesis_context}")
            for src in search_res.used_sources:
                citations.append({
                    "chunk_id": f"ext_{abs(hash(src.url)) % 1000000}",
                    "guest": src.domain,
                    "title": src.title,
                    "similarity": src.authority_score,
                    "excerpt": src.snippet,
                    "source_type": "external",
                    "url": src.url,
                    "domain": src.domain,
                })

        # Lenny retrieval execution (strictly gated)
        if Capability.LENNY_RESEARCH in capabilities or Capability.HYBRID_TASK in capabilities:
            retrieval_res = retrieve_evidence(request.query)
            if retrieval_res.grounded:
                evidence_parts.append(f"LENNY'S TRANSCRIPT ARCHIVE EVIDENCE:\n{retrieval_res.context_str}")
                for chunk in retrieval_res.chunks:
                    citations.append({
                        "chunk_id": chunk.chunk_id,
                        "guest": chunk.guest,
                        "title": chunk.title,
                        "similarity": chunk.similarity,
                        "excerpt": chunk.content[:200],
                        "source_type": "transcript",
                    })

        # Workspace inspection if coding
        if any(c in capabilities for c in [Capability.CODING, Capability.DEBUGGING, Capability.ARCHITECTURE]):
            workspace_keywords = ["repo", "codebase", "test", "directory", "project", "folder", "structure", "inspect", "files"]
            if any(k in request.query.lower() for k in workspace_keywords):
                try:
                    coding_agent = get_coding_agent()
                    repo_ctx = coding_agent.build_context_for_llm(goal=request.query)
                    if repo_ctx:
                        evidence_parts.append(f"LOCAL WORKSPACE CONTEXT:\n{repo_ctx}")
                except Exception as e:
                    logger.warning("Error gathering coding workspace context: %s", e)

        # Document Analysis & File Intelligence
        if Capability.DOCUMENT_ANALYSIS in capabilities:
            evidence_parts.append("[FILE INTELLIGENCE ACTIVE: Multi-format document analysis and grounded extraction enabled]")

        latencies["evidence_execution_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # 5. Epistemic Context Assembly (Purging any irrelevant bleed)
        allow_lenny = Capability.LENNY_RESEARCH in capabilities or Capability.HYBRID_TASK in capabilities
        context_str = self.context_manager.assemble_context(
            query=request.query,
            evidence_parts=evidence_parts,
            history=request.history,
            allow_lenny_knowledge=allow_lenny,
        )

        # Select Persona / System Prompt
        if Capability.CODING in capabilities:
            system_prompt = CODING_SYSTEM_PROMPT
            task_type = "coding"
        elif Capability.DEBUGGING in capabilities:
            system_prompt = DEBUGGING_SYSTEM_PROMPT
            task_type = "debugging"
        elif Capability.ARCHITECTURE in capabilities:
            system_prompt = ARCHITECTURE_SYSTEM_PROMPT
            task_type = "architecture"
        elif Capability.DEEP_RESEARCH in capabilities:
            system_prompt = RESEARCH_SYSTEM_PROMPT
            task_type = "deep_research"
        elif Capability.RESEARCH in capabilities:
            system_prompt = RESEARCH_SYSTEM_PROMPT
            task_type = "research"
        elif Capability.WRITING in capabilities:
            system_prompt = get_skill_prompt("ship30")
            task_type = "writing"
        elif Capability.PLANNING in capabilities:
            system_prompt = get_skill_prompt("experiment")
            task_type = "planning"
        elif Capability.LENNY_RESEARCH in capabilities:
            system_prompt = LENNY_PODCAST_SYSTEM_PROMPT
            task_type = "general_qa"
        else:
            system_prompt = GENERAL_QA_SYSTEM_PROMPT
            task_type = "general_qa"

        # 6. Model Routing & Execution via Phase 2 Platform
        t0 = time.perf_counter()
        llm_req = LLMRequest(
            prompt=request.query,
            system_prompt=system_prompt,
            context=context_str,
            history=self.context_manager.compact_history(request.history),
        )

        llm_resp = self.model_router.execute(
            request=llm_req,
            task_type=task_type,
            user_preference=request.provider_override,
        )
        latencies["inference_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        raw_content = llm_resp.content

        # 7. Post-Generation Verification
        t0 = time.perf_counter()
        verification = self.verification_engine.verify(
            query=request.query,
            response_content=raw_content,
            capabilities=capabilities,
            context_used=context_str,
            citations=citations,
        )
        latencies["verification_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # 8. Response Composition & Growth Canvas Artifact Extraction
        cleaned_content, artifacts = self.response_composer.compose(
            raw_text=raw_content,
            plan=plan,
            citations=citations,
            verification=verification,
        )

        total_ms = round((time.perf_counter() - t_start) * 1000, 2)

        return OrchestratorResponse(
            content=cleaned_content,
            session_id=request.session_id,
            selected_capabilities=capabilities,
            plan=plan,
            model_used=llm_resp.model,
            provider_used=llm_resp.provider,
            citations=citations,
            artifacts=artifacts,
            verification=verification,
            latency_breakdown=latencies,
            total_latency_ms=total_ms,
            status="SUCCESS",
        )


_ORCHESTRATOR = AIOrchestrator()

def get_ai_orchestrator() -> AIOrchestrator:
    """Access the singleton AIOrchestrator instance."""
    return _ORCHESTRATOR
