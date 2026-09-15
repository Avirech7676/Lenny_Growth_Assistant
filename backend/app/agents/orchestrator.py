import sys
import os

# Ensure backend root is in sys.path
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import re
import json
import time
import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import settings
from app.db.models import Session as SessionModel, Message as MessageModel, Artifact as ArtifactModel
from app.api.schemas import MessageResponse, CitationSchema, ArtifactSummary, LatencyMetrics
from app.agents.prompts import (
    get_skill_prompt,
    REFUSAL_MESSAGE,
    GENERAL_QA_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    CODING_SYSTEM_PROMPT,
    DEBUGGING_SYSTEM_PROMPT,
    ARCHITECTURE_SYSTEM_PROMPT,
    LENNY_PODCAST_SYSTEM_PROMPT,
)
from app.models.provider import get_llm_provider
from app.models.base import LLMRequest, LLMResponse
from app.models.tools import get_tool_registry, ToolCall

from app.retrieval.retriever import retrieve_evidence, RetrievalResult
from app.services.realtime_search import perform_external_research, ExternalResearchResult
from app.services.capability import (
    AgentCapability,
    IntentClassification,
    is_lenny_relevant,
    get_query_understanding_engine,
)
from app.services.search import (
    get_search_router,
    ResearchPlanner,
    ResearchDepth,
    SourceCategory,
    EvidenceStrength,
)


from app.services.research.engine import get_deep_research_engine
from app.services.memory.compactor import get_memory_compactor
from app.services.context import get_unified_context_manager, TransitionType
from app.services.coding import get_coding_agent
from app.services.quality import evaluate_response
from app.services.relevance import get_relevance_router, QueryDomain, QueryIntent
from app.utils.sanitize import sanitize_artifact_content, ALLOWED_HTML_TAGS, ALLOWED_HTML_ATTRS

logger = logging.getLogger(__name__)

ARTIFACT_REGEX = re.compile(
    r'<artifact\s+type="(?P<type>[^"]+)"\s+title="(?P<title>[^"]*)">(?P<content>.*?)</artifact>',
    re.DOTALL | re.IGNORECASE
)

# High-Performance In-Memory Query & Retrieval LRU Cache
class LRURetrievalCache:
    def __init__(self, capacity: int = 500):
        self.capacity = capacity
        self._cache: Dict[str, Any] = {}
        self._keys: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            self._keys.remove(key)
            self._keys.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._keys.remove(key)
        elif len(self._keys) >= self.capacity:
            oldest = self._keys.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = value
        self._keys.append(key)

    def clear(self) -> None:
        self._cache.clear()
        self._keys.clear()

_RETRIEVAL_CACHE = LRURetrievalCache(capacity=500)


def classify_query_intent(query: str, retrieval_res: Optional[RetrievalResult] = None) -> str:
    """Classify query intent into routing mode:
    - 'lenny': Explicitly asking about Lenny's podcast, newsletter, guests, transcript frameworks
    - 'hybrid': SaaS/growth/activation/pricing strategy combining Lenny frameworks with real-world data
    - 'real_world': Technical architecture, political/historical figures, current events, general knowledge
    """
    q_lower = query.lower()

    # Strict Lenny relevance check (explicit keyword, guest, or podcast framework)
    lenny_rel = is_lenny_relevant(query)

    # Hybrid indicators: strategic SaaS/growth questions mentioning current context or product metrics
    hybrid_keywords = [
        "activation", "retention", "onboarding", "churn", "saas",
        "2026", "drop", "monetization", "pricing", "market", "startup strategy", "plg"
    ]
    is_growth_query = any(k in q_lower for k in hybrid_keywords)
    if is_growth_query and retrieval_res and retrieval_res.grounded:
        return "hybrid"

    if lenny_rel:
        return "lenny"

    # Route everything else to real_world — no refusals for off-topic lifestyle queries
    return "real_world"


class AgentOrchestrator:
    """Multi-source agent orchestrator coordinating RAG retrieval, real-world intelligence, and token streaming."""

    def __init__(self, db: SQLAlchemySession):
        self.db = db

    def execute_turn(
        self,
        session_id: str,
        content: str,
        mode: str = "research",
        research_mode: str = "auto",
        provider_override: Optional[str] = None,
        images: Optional[List[str]] = None,
    ) -> MessageResponse:
        """Execute a synchronous conversational turn with multi-source intelligence routing."""
        start_time = time.perf_counter()

        # 1. Verify session exists
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session with ID '{session_id}' not found")

        # 2. Fetch & build multi-layer orchestrated context
        all_messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.desc())
            .limit(20)
            .all()
        )
        raw_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(all_messages)
        ]
        context_mgr = get_unified_context_manager()
        orchestrated_context = context_mgr.build_orchestrated_context(
            session_id=session_id,
            user_query=content,
            raw_history=raw_history,
        )
        history = orchestrated_context.llm_history

        # 3. Persist incoming user message
        user_msg = MessageModel(
            session_id=session_id,
            role="user",
            content=content,
            mode=mode,
            model="user",
        )
        self.db.add(user_msg)
        self.db.commit()

        # Strict Phase 1 Relevance Gating Pipeline:
        # USER QUERY → INTENT CLASSIFICATION → DOMAIN DETECTION → ENTITY EXTRACTION → CONTEXT RELEVANCE FILTER → RETRIEVAL ROUTING
        relevance_router = get_relevance_router()
        query_analysis = relevance_router.analyze_query(content)

        # Rule 2: Previous conversation evidence must NOT automatically become evidence for a new question.
        history = relevance_router.relevance_filter.sanitize_history_for_turn(query_analysis, history)

        # 4. Capability & Intent Understanding (Relevance Gated)
        engine = get_query_understanding_engine()
        classification = engine.analyze(
            query=content,
            user_mode_override=research_mode,
            session_history=history,
        )

        # Reconcile classification with strict relevance analysis (Rules 1, 3, 4, 5, 6)
        if not query_analysis.allow_lenny_retrieval:
            classification.lenny_relevant = False
            if classification.capability in [AgentCapability.LENNY_RESEARCH, AgentCapability.HYBRID_RESEARCH]:
                if query_analysis.domain == QueryDomain.GOVERNMENT or query_analysis.is_time_sensitive:
                    classification.capability = AgentCapability.WEB_RESEARCH
                    classification.domain = query_analysis.domain.value
                    classification.requires_web = True
                    classification.time_sensitive = True
                else:
                    classification.capability = AgentCapability.GENERAL_QA
                    classification.domain = query_analysis.domain.value
                    classification.requires_web = False
        elif query_analysis.intent == QueryIntent.LENNY_PODCAST_ADVISORY:
            classification.capability = AgentCapability.LENNY_RESEARCH
            classification.lenny_relevant = True

        logger.info(
            "Turn routed -> capability=%s domain=%s requires_web=%s lenny_rel=%s",
            classification.capability.value,
            classification.domain,
            classification.requires_web,
            classification.lenny_relevant,
        )

        context_parts: List[str] = []
        citations: List[CitationSchema] = []
        research_depth_val = classification.research_depth
        evidence_strength_val = "Strong"
        category_breakdown_val: Dict[str, int] = {}
        retrieval_ms = 0.0

        if classification.capability == AgentCapability.LENNY_RESEARCH and query_analysis.allow_lenny_retrieval:
            intelligence_mode = "lenny"
            t_ret_start = time.perf_counter()
            cache_key = f"ret:{content.strip().lower()}"
            retrieval_res: Optional[RetrievalResult] = _RETRIEVAL_CACHE.get(cache_key)
            if not retrieval_res:
                retrieval_res = retrieve_evidence(query=content, db=self.db, top_k=4)
                if retrieval_res and retrieval_res.grounded and retrieval_res.evidence:
                    _RETRIEVAL_CACHE.set(cache_key, retrieval_res)
            retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            if not retrieval_res.grounded or not retrieval_res.evidence:
                # No transcript evidence found — reroute to general QA instead of refusing
                classification.capability = AgentCapability.GENERAL_QA
                classification.lenny_relevant = False
                intelligence_mode = "real_world"

            for ev in retrieval_res.evidence:
                context_parts.append(
                    f"[Source ID: {ev.chunk_id}] Guest: {ev.guest} | Episode: {ev.title}\n{ev.excerpt}"
                )
                citations.append(
                    CitationSchema(
                        chunk_id=ev.chunk_id,
                        guest=ev.guest,
                        title=ev.title,
                        similarity=round(ev.similarity, 4),
                        excerpt=ev.excerpt,
                        source_type="transcript",
                        source_category="transcript",
                        evidence_strength="Strong",
                        why_useful="Verified transcript excerpt from Lenny's Podcast archive.",
                    )
                )
            system_prompt = get_skill_prompt(mode) if mode in ["ship30", "experiment", "playbook", "strategy"] else LENNY_PODCAST_SYSTEM_PROMPT

        elif classification.capability == AgentCapability.HYBRID_RESEARCH:
            intelligence_mode = "hybrid"
            t_ret_start = time.perf_counter()
            cache_key = f"ret:{content.strip().lower()}"
            retrieval_res = _RETRIEVAL_CACHE.get(cache_key)
            if not retrieval_res:
                retrieval_res = retrieve_evidence(query=content, db=self.db, top_k=4)
                _RETRIEVAL_CACHE.set(cache_key, retrieval_res)

            router = get_search_router()
            synthesis = router.execute_research_sync(content, user_mode=research_mode)
            retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            research_depth_val = synthesis.plan.depth.value
            evidence_strength_val = synthesis.evidence_strength.value
            category_breakdown_val = synthesis.category_counts

            if retrieval_res and retrieval_res.evidence:
                for ev in retrieval_res.evidence:
                    context_parts.append(f"[Transcript Source: {ev.guest} - {ev.title}]\n{ev.excerpt}")
                    citations.append(
                        CitationSchema(
                            chunk_id=ev.chunk_id,
                            guest=ev.guest,
                            title=ev.title,
                            similarity=round(ev.similarity, 4),
                            excerpt=ev.excerpt,
                            source_type="transcript",
                            source_category="transcript",
                            evidence_strength="Strong",
                            why_useful="Verified transcript excerpt from Lenny's Podcast archive.",
                        )
                    )
            context_parts.append(f"CURRENT 2026 BENCHMARKS & OPERATIONAL CONTEXT:\n{synthesis.synthesis_context}")
            for src in synthesis.used_sources:
                citations.append(
                    CitationSchema(
                        chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                        guest=src.domain,
                        title=src.title,
                        similarity=src.authority_score,
                        excerpt=src.snippet,
                        source_type="external",
                        url=src.url,
                        domain=src.domain,
                        source_category=src.category.value,
                        evidence_strength=synthesis.evidence_strength.value,
                        why_useful=src.why_useful,
                    )
                )

            base_prompt = get_skill_prompt(mode)
            system_prompt = (
                f"{base_prompt}\n\n"
                "HYBRID STRUCTURAL REQUIREMENT: You must structure your answer into 3 clearly marked sections:\n"
                "1. '### 🎙️ 1. Lenny's Perspective (Transcript Evidence)'\n"
                "2. '### 🌐 2. Current Market & Operational Context (2026 Benchmarks)'\n"
                "3. '### 💡 3. Strategic Synthesis & Tactical Action Plan'\n"
                "Never misattribute external benchmarks to Lenny's guests."
            )

        elif classification.capability == AgentCapability.DEEP_RESEARCH:
            intelligence_mode = "real_world"
            t_ret_start = time.perf_counter()
            deep_engine = get_deep_research_engine()
            deep_result = deep_engine.execute_research_sync(content, depth_override="deep")
            retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            research_depth_val = deep_result.plan.depth.value if hasattr(deep_result, 'plan') and hasattr(deep_result.plan, 'depth') else getattr(deep_result, 'depth', 'deep')
            evidence_strength_val = deep_result.evidence_strength.value if hasattr(deep_result.evidence_strength, 'value') else str(deep_result.evidence_strength)
            category_breakdown_val = deep_result.category_counts

            context_parts.append(f"DEEP RESEARCH REPORT:\n{deep_result.context_str}")
            for src in deep_result.used_sources:
                citations.append(
                    CitationSchema(
                        chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                        guest=src.domain,
                        title=src.title,
                        similarity=src.authority_score,
                        excerpt=src.snippet,
                        source_type="external",
                        url=src.url,
                        domain=src.domain,
                        source_category=src.category.value if hasattr(src.category, 'value') else str(src.category),
                        evidence_strength=evidence_strength_val,
                        why_useful=getattr(src, 'why_useful', f"Research source: {src.domain}"),
                    )
                )
            system_prompt = RESEARCH_SYSTEM_PROMPT

        elif classification.capability == AgentCapability.WEB_RESEARCH:
            intelligence_mode = "real_world"
            t_ret_start = time.perf_counter()
            router = get_search_router()
            synthesis = router.execute_research_sync(content, user_mode=research_mode)
            retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            research_depth_val = synthesis.plan.depth.value
            evidence_strength_val = synthesis.evidence_strength.value
            category_breakdown_val = synthesis.category_counts

            context_parts.append(f"VERIFIED REAL-WORLD KNOWLEDGE CONTEXT:\n{synthesis.synthesis_context}")
            for src in synthesis.used_sources:
                citations.append(
                    CitationSchema(
                        chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                        guest=src.domain,
                        title=src.title,
                        similarity=src.authority_score,
                        excerpt=src.snippet,
                        source_type="external",
                        url=src.url,
                        domain=src.domain,
                        source_category=src.category.value,
                        evidence_strength=synthesis.evidence_strength.value,
                        why_useful=src.why_useful,
                    )
                )
            system_prompt = RESEARCH_SYSTEM_PROMPT

        elif classification.capability in [AgentCapability.CODING, AgentCapability.DEBUGGING, AgentCapability.ARCHITECTURE]:
            intelligence_mode = "real_world"
            research_depth_val = "direct"
            evidence_strength_val = "Strong"
            workspace_keywords = ["repo", "codebase", "test", "directory", "project", "folder", "structure", "inspect", "files"]
            if any(k in content.lower() for k in workspace_keywords):
                try:
                    coding_agent = get_coding_agent()
                    repo_ctx = coding_agent.build_context_for_llm(goal=content)
                    if repo_ctx:
                        context_parts.append(f"LOCAL WORKSPACE & REPOSITORY CONTEXT:\n{repo_ctx}")
                except Exception as e:
                    logger.warning(f"Error gathering coding agent workspace context: {e}")

            if classification.requires_web:
                t_ret_start = time.perf_counter()
                router = get_search_router()
                synthesis = router.execute_research_sync(content, user_mode=research_mode)
                retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)
                context_parts.append(f"TECHNICAL DOCUMENTATION CONTEXT:\n{synthesis.synthesis_context}")
                for src in synthesis.used_sources:
                    citations.append(
                        CitationSchema(
                            chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                            guest=src.domain,
                            title=src.title,
                            similarity=src.authority_score,
                            excerpt=src.snippet,
                            source_type="external",
                            url=src.url,
                            domain=src.domain,
                            source_category=src.category.value,
                            evidence_strength=synthesis.evidence_strength.value,
                            why_useful=src.why_useful,
                        )
                    )

            if classification.capability == AgentCapability.CODING:
                system_prompt = CODING_SYSTEM_PROMPT
            elif classification.capability == AgentCapability.DEBUGGING:
                system_prompt = DEBUGGING_SYSTEM_PROMPT
            else:
                system_prompt = ARCHITECTURE_SYSTEM_PROMPT

        else:  # GENERAL_QA, WRITING, PLANNING, etc.
            intelligence_mode = "real_world"
            research_depth_val = "direct"
            evidence_strength_val = "Strong"
            if mode in ["ship30", "experiment", "playbook", "strategy"]:
                system_prompt = get_skill_prompt(mode)
            else:
                system_prompt = GENERAL_QA_SYSTEM_PROMPT

        # Strict Context Relevance Filter (Rules 7 & 8)
        citations = relevance_router.relevance_filter.filter_evidence_chunks(query_analysis, citations)
        if not query_analysis.allow_lenny_retrieval:
            context_parts = [
                cp for cp in context_parts
                if not any(bad in cp.lower() for bad in ["[source id:", "[transcript source:", "brian chesky", "lenny rachitsky"])
            ]

        # Inject task continuity context header if follow-up turn is active
        if orchestrated_context.task_state.follow_up_depth > 0:
            context_parts.insert(0, f"[TASK CONTINUITY: {orchestrated_context.task_state.topic} (Follow-up depth {orchestrated_context.task_state.follow_up_depth})]")

        # Smart Document Context Injection — only inject when query is document-relevant
        # This prevents document content contaminating unrelated answers
        _DOC_QUERY_SIGNALS = [
            "document", "file", "upload", "uploaded", "pdf", "docx", "txt", "csv",
            "summarize", "summary", "section", "chapter", "page", "extract",
            "analyze", "analyse", "what does it say", "according to", "in the document",
            "the attachment", "my file", "the report", "the spec",
        ]
        q_lower = content.lower()
        if session_id:
            _is_doc_relevant_query = any(sig in q_lower for sig in _DOC_QUERY_SIGNALS)
            if _is_doc_relevant_query:
                try:
                    from app.db.session import get_db_session
                    from app.db.models import UploadedDocument
                    with get_db_session() as db:
                        docs = db.query(UploadedDocument).filter(UploadedDocument.session_id == session_id).all()
                        if docs:
                            doc_texts = []
                            for d in docs:
                                doc_words = set(re.findall(r'\b\w+\b', d.extracted_text.lower()))
                                q_words = set(re.findall(r'\b\w+\b', q_lower))
                                overlap = len(doc_words & q_words)
                                if overlap > 2 or len(docs) == 1:
                                    doc_texts.append(
                                        f"### Uploaded Document: {d.filename} ({d.file_type})\n"
                                        f"{d.extracted_text[:12000]}"
                                    )
                            if doc_texts:
                                context_parts.append("UPLOADED SESSION DOCUMENT CONTEXT:\n" + "\n\n".join(doc_texts))
                except Exception as e:
                    logger.warning("Error loading session uploaded documents: %s", e)

        context_str = "\n\n---\n\n".join(context_parts) if context_parts else ""

        task_type = "general_qa"
        if getattr(query_analysis, "domain", None) == QueryDomain.SOFTWARE_ENGINEERING or getattr(query_analysis, "intent", None) in (
            QueryIntent.CODE_IMPLEMENTATION,
            QueryIntent.CODE_DEBUGGING,
            QueryIntent.SYSTEM_ARCHITECTURE,
        ):
            task_type = "coding"
        elif getattr(query_analysis, "intent", None) == QueryIntent.DEEP_RESEARCH or mode == "deep_research":
            task_type = "deep_research"
        elif mode == "chat":
            task_type = "fast_response"

        provider = get_llm_provider(override=provider_override, task_type=task_type)
        from app.models.continuity import get_state_continuity_manager
        continuity_mgr = get_state_continuity_manager()
        prepared_history, _ = continuity_mgr.prepare_turn(
            session_id=session_id,
            history=history,
            active_model=provider.get_model_name(),
            active_provider=provider.get_provider_id(),
        )

        registry = get_tool_registry()
        tool_specs = [t.to_openai_spec() for t in registry.list_tools()]

        t_llm_start = time.perf_counter()
        llm_req = LLMRequest(
            prompt=content,
            system_prompt=system_prompt,
            context=context_str,
            history=prepared_history,
            tools=tool_specs,
            images=images,
        )
        llm_res = provider.generate(llm_req)


        # Tool calling loop
        if isinstance(llm_res, LLMResponse) and llm_res.tool_calls:
            registry = get_tool_registry()
            tool_outputs = []
            for tc in llm_res.tool_calls:
                call = ToolCall.from_dict(tc)
                res = registry.execute(call.name, call.arguments, call_id=call.id)
                tool_outputs.append(f"Tool `{call.name}` output: {res.to_content_str()}")

            synth_req = LLMRequest(
                prompt=f"{content}\n\n[TOOL EXECUTION RESULTS]:\n" + "\n".join(tool_outputs),
                system_prompt=system_prompt,
                context=context_str,
                history=history,
                images=images,
            )
            llm_res = provider.generate(synth_req)

        raw_llm_response = llm_res.content if isinstance(llm_res, LLMResponse) else str(llm_res)

        # Code execution verification for runnable Python blocks
        if classification.capability in [AgentCapability.CODING, AgentCapability.DEBUGGING] or "```python" in raw_llm_response:
            py_blocks = re.findall(r'```python\s*(.*?)\s*```', raw_llm_response, re.DOTALL)
            if py_blocks:
                from app.coding.sandbox import SandboxExecutionEngine
                sandbox = SandboxExecutionEngine()
                first_code = py_blocks[0].strip()
                if len(first_code) > 5 and not first_code.startswith("..."):
                    try:
                        exec_res = sandbox.execute_python_sync(first_code, timeout_seconds=5.0)
                        if exec_res.success:
                            raw_llm_response += f"\n\n> ⚡ **Code Execution Verified** (exit_code=0)"
                            if exec_res.stdout:
                                raw_llm_response += f"\n> Output: `{exec_res.stdout[:200]}`"
                    except Exception as e:
                        logger.debug("Sync sandbox verification skipped: %s", e)

        llm_ms = round((time.perf_counter() - t_llm_start) * 1000, 2)


        # 8. Artifact parsing and multi-stage sanitization
        extracted_artifacts: List[ArtifactModel] = []
        artifact_summaries: List[ArtifactSummary] = []

        def artifact_replacer(match):
            art_type = match.group("type").strip().lower()
            art_title = match.group("title").strip() or "Growth Artifact"
            raw_body = match.group("content").strip()
            clean_body = sanitize_artifact_content(raw_body)

            art_record = ArtifactModel(
                session_id=session_id,
                artifact_type=art_type,
                title=art_title,
                raw_content=raw_body,
                sanitized_content=clean_body,
                status="sanitized",
            )
            extracted_artifacts.append(art_record)
            return f"\n\n> 🛠️ **Generated Operational Artifact**: *{art_title}* (Rendered in Growth Canvas)\n"

        cleaned_content = ARTIFACT_REGEX.sub(artifact_replacer, raw_llm_response)

        # 9. Persist assistant message and link artifacts
        total_ms = round((time.perf_counter() - start_time) * 1000, 2)
        assistant_msg = MessageModel(
            session_id=session_id,
            role="assistant",
            content=cleaned_content.strip(),
            mode=mode,
            model=provider.get_model_name(),
            latency_ms=total_ms,
            citations=json.dumps([c.model_dump() for c in citations]),
        )
        self.db.add(assistant_msg)
        self.db.flush()

        for art in extracted_artifacts:
            art.message_id = assistant_msg.id
            self.db.add(art)
            self.db.flush()
            artifact_summaries.append(
                ArtifactSummary(
                    id=art.id,
                    artifact_type=art.artifact_type,
                    title=art.title,
                    status=art.status,
                    created_at=art.created_at.isoformat() if art.created_at else None,
                )
            )

        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(assistant_msg)

        metrics = LatencyMetrics(
            ttft_ms=round(retrieval_ms + 120.0, 2),
            retrieval_ms=retrieval_ms,
            llm_ms=llm_ms,
            total_ms=total_ms,
        )

        # Evaluate response quality gate
        try:
            quality_res = evaluate_response(
                query=content,
                response=assistant_msg.content,
                evidence_snippets=[c.excerpt for c in citations if c.excerpt],
                citations=[c.model_dump() for c in citations],
            )
            q_score = round(quality_res.overall_score, 3)
            q_passed = quality_res.passed
            logger.info(f"Quality gate evaluated: score={q_score}, passed={q_passed}")
        except Exception as e:
            logger.warning(f"Quality gate evaluation failed: {e}")
            q_score = None
            q_passed = None

        return MessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            mode=assistant_msg.mode,
            model=assistant_msg.model,
            latency_ms=assistant_msg.latency_ms,
            intelligence_mode=intelligence_mode,
            capability=classification.capability.value,
            research_depth=research_depth_val,
            evidence_strength=evidence_strength_val,
            category_breakdown=category_breakdown_val,
            latency_metrics=metrics,
            citations=citations,
            artifacts=artifact_summaries,
            quality_score=q_score,
            quality_passed=q_passed,
            follow_up_suggestions=orchestrated_context.follow_up_suggestions,
            created_at=assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
        )

    async def execute_turn_stream(
        self,
        session_id: str,
        content: str,
        mode: str = "research",
        research_mode: str = "auto",
        provider_override: Optional[str] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Asynchronous SSE generator streaming real-time tokens, phase updates, citations, and TTFT metrics."""
        start_time = time.perf_counter()

        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            yield f"data: {json.dumps({'event': 'error', 'error': f'Session {session_id} not found'})}\n\n"
            return

        # Fetch & compact history via UnifiedContextManager
        all_messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.desc())
            .limit(20)
            .all()
        )
        raw_history = [{"role": m.role, "content": m.content} for m in reversed(all_messages)]
        context_mgr = get_unified_context_manager()
        orchestrated_context = context_mgr.build_orchestrated_context(
            session_id=session_id,
            user_query=content,
            raw_history=raw_history,
        )
        history = orchestrated_context.llm_history

        # Persist user message
        user_msg = MessageModel(session_id=session_id, role="user", content=content, mode=mode, model="user")
        self.db.add(user_msg)
        self.db.commit()

        yield f"data: {json.dumps({'event': 'phase', 'phase': 'understanding', 'message': 'Analyzing query domain and intent...'})}\n\n"

        # Strict Phase 1 Relevance Gating Pipeline:
        relevance_router = get_relevance_router()
        query_analysis = relevance_router.analyze_query(content)
        history = relevance_router.relevance_filter.sanitize_history_for_turn(query_analysis, history)

        # Step A: Intent Understanding & Capability Classification
        engine = get_query_understanding_engine()
        classification = engine.analyze(
            query=content,
            user_mode_override=research_mode,
            session_history=history,
        )

        # Reconcile classification with strict relevance analysis (Rules 1, 3, 4, 5, 6)
        if not query_analysis.allow_lenny_retrieval:
            classification.lenny_relevant = False
            if classification.capability in [AgentCapability.LENNY_RESEARCH, AgentCapability.HYBRID_RESEARCH]:
                if query_analysis.domain == QueryDomain.GOVERNMENT or query_analysis.is_time_sensitive:
                    classification.capability = AgentCapability.WEB_RESEARCH
                    classification.domain = query_analysis.domain.value
                    classification.requires_web = True
                    classification.time_sensitive = True
                else:
                    classification.capability = AgentCapability.GENERAL_QA
                    classification.domain = query_analysis.domain.value
                    classification.requires_web = False
        elif query_analysis.intent == QueryIntent.LENNY_PODCAST_ADVISORY:
            classification.capability = AgentCapability.LENNY_RESEARCH
            classification.lenny_relevant = True

        cap_name = classification.capability.value.replace("_", " ")
        yield f"data: {json.dumps({'event': 'phase', 'phase': 'relevance_filter', 'intent': query_analysis.intent.value, 'domain': query_analysis.domain.value, 'entities': query_analysis.entities, 'time_sensitive': query_analysis.is_time_sensitive, 'lenny_allowed': query_analysis.allow_lenny_retrieval})}\n\n"
        yield f"data: {json.dumps({'event': 'phase', 'phase': 'understanding', 'message': f'Analyzing intent: {cap_name}...'})}\n\n"
        await asyncio.sleep(0.01)

        # Step B: Retrieval & Evidence Setup
        t_ret_start = time.perf_counter()
        cache_key = f"ret:{content.strip().lower()}"
        ext_cache_key = f"{research_mode}:{content.strip().lower()}"

        cached_retrieval: Optional[RetrievalResult] = _RETRIEVAL_CACHE.get(cache_key)
        cached_external = _RETRIEVAL_CACHE.get(ext_cache_key)

        loop = asyncio.get_event_loop()

        async def _do_retrieval() -> RetrievalResult:
            if cached_retrieval:
                return cached_retrieval
            result = await loop.run_in_executor(None, lambda: retrieve_evidence(query=content, db=self.db, top_k=4))
            _RETRIEVAL_CACHE.set(cache_key, result)
            return result

        async def _do_external():
            if cached_external:
                return cached_external
            router = get_search_router()
            result = await router.execute_research_async(content, user_mode=research_mode)
            _RETRIEVAL_CACHE.set(ext_cache_key, result)
            return result

        context_parts: List[str] = []
        citations: List[CitationSchema] = []
        retrieval_res = None
        ext_res = None

        if classification.capability == AgentCapability.LENNY_RESEARCH and query_analysis.allow_lenny_retrieval:
            intelligence_mode = "lenny"
            yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': 'Searching Lenny\'s Podcast archive...'})}\n\n"
            retrieval_res = await _do_retrieval()

            if not retrieval_res.grounded or not retrieval_res.evidence:
                # No transcript evidence found - reroute to general QA instead of refusing
                classification.capability = AgentCapability.GENERAL_QA
                classification.lenny_relevant = False
                intelligence_mode = "real_world"
            for ev in retrieval_res.evidence:
                context_parts.append(f"[Source ID: {ev.chunk_id}] Guest: {ev.guest} | Episode: {ev.title}\n{ev.excerpt}")
                citations.append(
                    CitationSchema(
                        chunk_id=ev.chunk_id,
                        guest=ev.guest,
                        title=ev.title,
                        similarity=round(ev.similarity, 4),
                        excerpt=ev.excerpt,
                        source_type="transcript",
                        source_category="transcript",
                        evidence_strength="Strong",
                        why_useful="Verified transcript excerpt from Lenny's Podcast archive.",
                    )
                )

        elif classification.capability == AgentCapability.HYBRID_RESEARCH and query_analysis.allow_lenny_retrieval:
            intelligence_mode = "hybrid"
            yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': 'Combining Lenny insights + live multi-source research...'})}\n\n"
            retrieval_res, ext_res = await asyncio.gather(
                _do_retrieval(),
                _do_external(),
            )
            if retrieval_res and retrieval_res.evidence:
                for ev in retrieval_res.evidence:
                    context_parts.append(f"[Transcript Source: {ev.guest} - {ev.title}]\n{ev.excerpt}")
                    citations.append(
                        CitationSchema(
                            chunk_id=ev.chunk_id,
                            guest=ev.guest,
                            title=ev.title,
                            similarity=round(ev.similarity, 4),
                            excerpt=ev.excerpt,
                            source_type="transcript",
                            source_category="transcript",
                            evidence_strength="Strong",
                            why_useful="Verified transcript excerpt from Lenny's Podcast archive.",
                        )
                    )
            if ext_res is not None:
                context_parts.append(f"CURRENT 2026 BENCHMARKS & OPERATIONAL CONTEXT:\n{ext_res.synthesis_context}")
                sources_list = getattr(ext_res, 'used_sources', getattr(ext_res, 'sources', []))
                for src in sources_list:
                    citations.append(
                        CitationSchema(
                            chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                            guest=src.domain,
                            title=src.title,
                            similarity=getattr(src, 'authority_score', getattr(src, 'credibility_score', 0.9)),
                            excerpt=src.snippet,
                            source_type="external",
                            url=src.url,
                            domain=src.domain,
                            source_category=getattr(src, 'category', SourceCategory.REFERENCE).value if hasattr(getattr(src, 'category', None), 'value') else str(getattr(src, 'category', 'reference')),
                            evidence_strength=getattr(ext_res, 'evidence_strength', EvidenceStrength.MODERATE).value if hasattr(getattr(ext_res, 'evidence_strength', None), 'value') else "Moderate",
                            why_useful=getattr(src, 'why_useful', f"Evidence source on {src.domain}."),
                        )
                    )

        elif classification.capability == AgentCapability.DEEP_RESEARCH:
            intelligence_mode = "real_world"
            retrieval_res = None
            # Stream progressive deep research events
            deep_engine = get_deep_research_engine()
            deep_result = None

            async for evt in deep_engine.stream_research_events(content, depth_override="deep"):
                phase = evt.get("phase", "searching")
                if phase == "planning":
                    yield f"data: {json.dumps({'event': 'phase', 'phase': 'planning', 'message': evt.get('message', 'Planning research...')})}\n\n"
                    sub_queries = evt.get("sub_queries", [])
                    if sub_queries:
                        yield f"data: {json.dumps({'event': 'research_plan', 'depth': evt.get('depth', 'deep'), 'sub_queries': sub_queries})}\n\n"
                elif phase == "searching":
                    yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': evt.get('message', 'Searching sources...')})}\n\n"
                elif phase == "reading":
                    yield f"data: {json.dumps({'event': 'phase', 'phase': 'reading', 'message': evt.get('message', 'Reading primary sources...')})}\n\n"
                elif phase == "cross_checking":
                    yield f"data: {json.dumps({'event': 'phase', 'phase': 'cross_checking', 'message': evt.get('message', 'Cross-checking sources...')})}\n\n"
                elif phase == "synthesizing":
                    yield f"data: {json.dumps({'event': 'phase', 'phase': 'synthesis', 'message': evt.get('message', 'Synthesizing report...')})}\n\n"
                elif phase == "complete":
                    deep_result = evt.get("result")

            if deep_result is not None:
                context_parts.append(f"DEEP RESEARCH REPORT:\n{deep_result.context_str}")
                ev_str = deep_result.evidence_strength.value if hasattr(deep_result.evidence_strength, 'value') else str(deep_result.evidence_strength)
                for src in deep_result.used_sources:
                    citations.append(
                        CitationSchema(
                            chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                            guest=src.domain,
                            title=src.title,
                            similarity=src.authority_score,
                            excerpt=src.snippet,
                            source_type="external",
                            url=src.url,
                            domain=src.domain,
                            source_category=src.category.value if hasattr(src.category, 'value') else str(src.category),
                            evidence_strength=ev_str,
                            why_useful=getattr(src, 'why_useful', f"Deep research source: {src.domain}"),
                        )
                    )
            ext_res = None  # deep research handled separately

        elif classification.capability == AgentCapability.WEB_RESEARCH:
            intelligence_mode = "real_world"
            planner = ResearchPlanner()
            plan = planner.plan_research(content, user_mode=research_mode)
            if plan.depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP_MULTI_QUERY]:
                yield f"data: {json.dumps({'event': 'research_plan', 'depth': plan.depth.value, 'domain': plan.domain, 'sub_queries': plan.sub_queries, 'categories': [c.value for c in plan.target_categories]})}\n\n"
                for sq in plan.sub_queries[:3]:
                    yield f"data: {json.dumps({'event': 'research_progress', 'step': 'searching', 'query': sq})}\n\n"

            yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': f'Researching verified sources across {classification.domain}...'})}\n\n"
            ext_res = await _do_external()
            retrieval_res = None

            if ext_res is not None:
                context_parts.append(f"VERIFIED REAL-WORLD KNOWLEDGE CONTEXT:\n{ext_res.synthesis_context}")
                sources_list = getattr(ext_res, 'used_sources', getattr(ext_res, 'sources', []))
                for src in sources_list:
                    citations.append(
                        CitationSchema(
                            chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                            guest=src.domain,
                            title=src.title,
                            similarity=getattr(src, 'authority_score', getattr(src, 'credibility_score', 0.9)),
                            excerpt=src.snippet,
                            source_type="external",
                            url=src.url,
                            domain=src.domain,
                            source_category=getattr(src, 'category', SourceCategory.REFERENCE).value if hasattr(getattr(src, 'category', None), 'value') else str(getattr(src, 'category', 'reference')),
                            evidence_strength=getattr(ext_res, 'evidence_strength', EvidenceStrength.MODERATE).value if hasattr(getattr(ext_res, 'evidence_strength', None), 'value') else "Moderate",
                            why_useful=getattr(src, 'why_useful', f"Evidence source on {src.domain}."),
                        )
                    )

        elif classification.capability in [AgentCapability.CODING, AgentCapability.DEBUGGING, AgentCapability.ARCHITECTURE]:
            intelligence_mode = "real_world"
            retrieval_res = None
            workspace_keywords = ["repo", "codebase", "test", "directory", "project", "folder", "structure", "inspect", "files"]
            if any(k in content.lower() for k in workspace_keywords):
                yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': 'Inspecting local repository workspace...'})}\n\n"
                try:
                    coding_agent = get_coding_agent()
                    repo_ctx = coding_agent.build_context_for_llm(goal=content)
                    if repo_ctx:
                        context_parts.append(f"LOCAL WORKSPACE & REPOSITORY CONTEXT:\n{repo_ctx}")
                except Exception as e:
                    logger.warning(f"Error gathering coding agent workspace context: {e}")

            if classification.requires_web:
                yield f"data: {json.dumps({'event': 'phase', 'phase': 'retrieval', 'message': 'Consulting official technical documentation...'})}\n\n"
                ext_res = await _do_external()
                if ext_res is not None:
                    context_parts.append(f"TECHNICAL DOCUMENTATION CONTEXT:\n{ext_res.synthesis_context}")
                    sources_list = getattr(ext_res, 'used_sources', getattr(ext_res, 'sources', []))
                    for src in sources_list:
                        citations.append(
                            CitationSchema(
                                chunk_id=f"ext_{abs(hash(src.url)) % 1000000}",
                                guest=src.domain,
                                title=src.title,
                                similarity=getattr(src, 'authority_score', getattr(src, 'credibility_score', 0.9)),
                                excerpt=src.snippet,
                                source_type="external",
                                url=src.url,
                                domain=src.domain,
                                source_category=getattr(src, 'category', SourceCategory.REFERENCE).value if hasattr(getattr(src, 'category', None), 'value') else str(getattr(src, 'category', 'reference')),
                                evidence_strength=getattr(ext_res, 'evidence_strength', EvidenceStrength.MODERATE).value if hasattr(getattr(ext_res, 'evidence_strength', None), 'value') else "Moderate",
                                why_useful=getattr(src, 'why_useful', f"Evidence source on {src.domain}."),
                            )
                        )
            else:
                ext_res = None
                yield f"data: {json.dumps({'event': 'phase', 'phase': 'reasoning', 'message': f'Synthesizing {cap_name}...'})}\n\n"

        else:  # GENERAL_QA, WRITING, PLANNING, etc.
            intelligence_mode = "real_world"
            retrieval_res = None
            ext_res = None
            yield f"data: {json.dumps({'event': 'phase', 'phase': 'reasoning', 'message': 'Synthesizing response...'})}\n\n"

        # Strict Context Relevance Filter (Rules 7 & 8)
        citations = relevance_router.relevance_filter.filter_evidence_chunks(query_analysis, citations)
        if not query_analysis.allow_lenny_retrieval:
            context_parts = [
                cp for cp in context_parts
                if not any(bad in cp.lower() for bad in ["[source id:", "[transcript source:", "brian chesky", "lenny rachitsky"])
            ]

        # Smart Document Context Injection — only inject when query is document-relevant
        # This prevents document content contaminating unrelated answers
        _DOC_QUERY_SIGNALS = [
            "document", "file", "upload", "uploaded", "pdf", "docx", "txt", "csv",
            "summarize", "summary", "section", "chapter", "page", "extract",
            "analyze", "analyse", "what does it say", "according to", "in the document",
            "the attachment", "my file", "the report", "the spec",
        ]
        q_lower = content.lower()
        if session_id:
            _is_doc_relevant_query = any(sig in q_lower for sig in _DOC_QUERY_SIGNALS)
            if _is_doc_relevant_query:
                try:
                    from app.db.session import get_db_session
                    from app.db.models import UploadedDocument
                    with get_db_session() as db:
                        docs = db.query(UploadedDocument).filter(UploadedDocument.session_id == session_id).all()
                        if docs:
                            doc_texts = []
                            for d in docs:
                                # Score document relevance against query (simple keyword overlap)
                                doc_words = set(re.findall(r'\b\w+\b', d.extracted_text.lower()))
                                q_words = set(re.findall(r'\b\w+\b', q_lower))
                                overlap = len(doc_words & q_words)
                                if overlap > 2 or len(docs) == 1:
                                    doc_texts.append(
                                        f"### Uploaded Document: {d.filename} ({d.file_type})\n"
                                        f"{d.extracted_text[:12000]}"
                                    )
                            if doc_texts:
                                context_parts.append("UPLOADED SESSION DOCUMENT CONTEXT:\n" + "\n\n".join(doc_texts))
                except Exception as e:
                    logger.warning("Error loading session uploaded documents: %s", e)

        retrieval_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)
        context_str = "\n\n---\n\n".join(context_parts) if context_parts else ""

        # Emit routing & citations to UI immediately
        depth_val = getattr(getattr(ext_res, 'plan', None), 'depth', classification.research_depth)
        if hasattr(depth_val, 'value'):
            depth_val = depth_val.value
        ev_strength = getattr(ext_res, 'evidence_strength', EvidenceStrength.STRONG)
        if hasattr(ev_strength, 'value'):
            ev_strength = ev_strength.value
        cat_counts = getattr(ext_res, 'category_counts', {}) if ext_res else {}

        yield f"data: {json.dumps({'event': 'routing', 'intelligence_mode': intelligence_mode, 'capability': classification.capability.value, 'research_depth': depth_val, 'evidence_strength': ev_strength, 'category_breakdown': cat_counts, 'sources_count': len(citations)})}\n\n"
        yield f"data: {json.dumps({'event': 'citations', 'citations': [c.model_dump() for c in citations]})}\n\n"

        # Step D: Streaming Inference
        if classification.capability == AgentCapability.CODING:
            synth_msg = "Formulating code solution..."
        elif classification.capability == AgentCapability.DEBUGGING:
            synth_msg = "Diagnosing root cause and verifying fix..."
        elif classification.capability == AgentCapability.ARCHITECTURE:
            synth_msg = "Synthesizing architecture blueprints..."
        elif classification.capability == AgentCapability.LENNY_RESEARCH:
            synth_msg = "Synthesizing insights from Lenny's podcast archive..."
        elif classification.capability in [AgentCapability.WEB_RESEARCH, AgentCapability.DEEP_RESEARCH]:
            synth_msg = "Synthesizing research evidence..."
        else:
            synth_msg = "Formulating direct answer..."

        yield f"data: {json.dumps({'event': 'phase', 'phase': 'synthesis', 'message': synth_msg})}\n\n"

        if mode in ["ship30", "experiment", "playbook", "strategy"]:
            system_prompt = get_skill_prompt(mode)
        elif classification.capability == AgentCapability.CODING:
            system_prompt = CODING_SYSTEM_PROMPT
        elif classification.capability == AgentCapability.DEBUGGING:
            system_prompt = DEBUGGING_SYSTEM_PROMPT
        elif classification.capability == AgentCapability.ARCHITECTURE:
            system_prompt = ARCHITECTURE_SYSTEM_PROMPT
        elif classification.capability == AgentCapability.GENERAL_QA:
            system_prompt = GENERAL_QA_SYSTEM_PROMPT
        elif classification.capability in [AgentCapability.WEB_RESEARCH, AgentCapability.DEEP_RESEARCH]:
            system_prompt = RESEARCH_SYSTEM_PROMPT
        elif classification.capability == AgentCapability.LENNY_RESEARCH:
            system_prompt = LENNY_PODCAST_SYSTEM_PROMPT
        elif classification.capability == AgentCapability.HYBRID_RESEARCH:
            base_prompt = get_skill_prompt(mode)
            system_prompt = (
                f"{base_prompt}\n\n"
                "HYBRID STRUCTURAL REQUIREMENT: You must structure your answer into 3 clearly marked sections:\n"
                "1. '### 🎙️ 1. Lenny's Perspective (Transcript Evidence)'\n"
                "2. '### 🌐 2. Current Market & Operational Context (2026 Benchmarks)'\n"
                "3. '### 💡 3. Strategic Synthesis & Tactical Action Plan'\n"
                "Never misattribute external benchmarks to Lenny's guests."
            )
        else:
            system_prompt = GENERAL_QA_SYSTEM_PROMPT

        task_type = "general_qa"
        if getattr(query_analysis, "domain", None) == QueryDomain.SOFTWARE_ENGINEERING or getattr(query_analysis, "intent", None) in (
            QueryIntent.CODE_IMPLEMENTATION,
            QueryIntent.CODE_DEBUGGING,
            QueryIntent.SYSTEM_ARCHITECTURE,
        ):
            task_type = "coding"
        elif getattr(query_analysis, "intent", None) == QueryIntent.DEEP_RESEARCH or mode == "deep_research":
            task_type = "deep_research"
        elif mode == "chat":
            task_type = "fast_response"

        provider = get_llm_provider(override=provider_override, task_type=task_type)
        from app.models.continuity import get_state_continuity_manager
        continuity_mgr = get_state_continuity_manager()
        prepared_history, model_transition = continuity_mgr.prepare_turn(
            session_id=session_id,
            history=history,
            active_model=provider.get_model_name(),
            active_provider=provider.get_provider_id(),
        )
        if model_transition:
            yield f"data: {json.dumps({'event': 'model_transition', 'from_model': model_transition.from_model, 'to_model': model_transition.to_model})}\n\n"

        t_llm_start = time.perf_counter()
        accumulated_chunks = []
        ttft_ms = None

        # Emit early model event so UI can display active model badge immediately
        yield f"data: {json.dumps({'event': 'model', 'model_id': provider.get_model_name(), 'provider': provider.get_provider_id()})}\n\n"

        # ── TRUE REACT STREAMING TOOL LOOP ─────────────────────────────────────────
        # Step 1: Call generate() with full tool specs so the LLM can decide to use tools.
        # Step 2: For each tool_call in response, execute the tool and stream real SSE events.
        # Step 3: Feed tool results back to the LLM for synthesis.
        # Step 4: Stream the final synthesis response token-by-token.
        # This loop runs up to MAX_TOOL_ITERATIONS to prevent infinite loops.
        MAX_TOOL_ITERATIONS = 5
        registry = get_tool_registry()
        tool_specs = [t.to_openai_spec() for t in registry.list_tools()]

        react_history = list(prepared_history)
        react_context = context_str
        tool_iteration = 0
        final_synthesis_text: Optional[str] = None

        while tool_iteration < MAX_TOOL_ITERATIONS:
            tool_iteration += 1
            llm_req_react = LLMRequest(
                prompt=content,
                system_prompt=system_prompt,
                context=react_context,
                history=react_history,
                tools=tool_specs,
                images=images,
            )
            try:
                loop_provider = provider
                react_res = loop_provider.generate(llm_req_react)
            except Exception as e:
                logger.warning("ReAct tool loop generate() failed: %s", e)
                break

            if not isinstance(react_res, LLMResponse):
                final_synthesis_text = str(react_res)
                break

            # No tool calls → this is the final answer → stream it
            if not react_res.tool_calls:
                final_synthesis_text = react_res.content
                break

            # Execute each tool call and emit real SSE events
            tool_results_context_parts = []
            for tc in react_res.tool_calls:
                try:
                    call = ToolCall.from_dict(tc)
                except Exception:
                    continue
                yield f"data: {json.dumps({'event': 'tool_call', 'tool': call.name, 'args': call.arguments})}\n\n"
                tool_res = registry.execute(call.name, call.arguments, call_id=call.id)
                yield f"data: {json.dumps({'event': 'tool_result', 'tool': call.name, 'result': tool_res.to_dict()})}\n\n"
                tool_results_context_parts.append(
                    f"Tool `{call.name}` was invoked with args={json.dumps(call.arguments)}.\n"
                    f"Result: {tool_res.to_content_str()}"
                )

            # Append tool results to context for next iteration
            if tool_results_context_parts:
                tool_block = "[TOOL EXECUTION RESULTS]:\n" + "\n\n".join(tool_results_context_parts)
                react_context = (react_context + "\n\n" + tool_block).strip() if react_context else tool_block
            # Continue loop — model may call more tools or produce final answer

        # ── STREAM FINAL SYNTHESIS RESPONSE ────────────────────────────────────────
        # If the ReAct loop produced a final text, stream it token-by-token.
        # If somehow no final text, fall back to generate_stream().
        token_count = 0
        if final_synthesis_text:
            # Simulate streaming from the accumulated final text
            words = re.findall(r'\S+|\s+', final_synthesis_text)
            for word in words:
                if ttft_ms is None:
                    ttft_ms = round((time.perf_counter() - start_time) * 1000, 2)
                token_count += 1
                accumulated_chunks.append(word)
                yield f"data: {json.dumps({'event': 'token', 'token': word})}\n\n"
                if token_count % 20 == 0:
                    await asyncio.sleep(0.001)
        else:
            # Fallback: plain streaming without tool loop
            for chunk in provider.generate_stream(
                system_prompt=system_prompt,
                user_prompt=content,
                context=context_str,
                history=prepared_history,
            ):
                if ttft_ms is None:
                    ttft_ms = round((time.perf_counter() - start_time) * 1000, 2)
                token_count += 1
                accumulated_chunks.append(chunk)
                yield f"data: {json.dumps({'event': 'token', 'token': chunk})}\n\n"
                await asyncio.sleep(0.001)

        llm_ms = round((time.perf_counter() - t_llm_start) * 1000, 2)
        total_ms = round((time.perf_counter() - start_time) * 1000, 2)
        full_text = "".join(accumulated_chunks)
        generation_sec = max(0.001, llm_ms / 1000.0)
        tokens_per_sec = round(token_count / generation_sec, 2)

        # Step E2: Code Execution Verification (if runnable Python blocks generated)
        execution_verified = False
        execution_telemetry = None
        if classification.capability in [AgentCapability.CODING, AgentCapability.DEBUGGING] or "```python" in full_text:
            py_blocks = re.findall(r'```python\s*(.*?)\s*```', full_text, re.DOTALL)
            if py_blocks:
                from app.coding.sandbox import SandboxExecutionEngine
                sandbox = SandboxExecutionEngine()
                first_code = py_blocks[0].strip()
                if len(first_code) > 5 and not first_code.startswith("..."):
                    try:
                        exec_res = await sandbox.execute_python(first_code, timeout_seconds=5.0)
                        execution_verified = exec_res.success
                        if exec_res.success:
                            full_text += f"\n\n> ⚡ **Code Execution Verified** (exit_code=0)"
                            if exec_res.stdout:
                                full_text += f"\n> Output: `{exec_res.stdout[:200]}`"
                        execution_telemetry = {
                            "language": "python",
                            "exit_code": exec_res.exit_code,
                            "stdout": exec_res.stdout[:500],
                            "stderr": exec_res.stderr[:300],
                            "duration_ms": round(exec_res.duration_ms, 2),
                            "verified": exec_res.verified,
                        }
                        yield f"data: {json.dumps({'event': 'execution_verification', **execution_telemetry})}\n\n"
                    except Exception as e:
                        logger.debug("Sandbox execution telemetry skipped: %s", e)

        # Step E: Parse Artifacts and Persist
        extracted_artifacts: List[ArtifactModel] = []
        artifact_summaries: List[ArtifactSummary] = []

        def artifact_replacer(match):
            art_type = match.group("type").strip().lower()
            art_title = match.group("title").strip() or "Growth Artifact"
            raw_body = match.group("content").strip()
            clean_body = sanitize_artifact_content(raw_body)

            art_record = ArtifactModel(
                session_id=session_id,
                artifact_type=art_type,
                title=art_title,
                raw_content=raw_body,
                sanitized_content=clean_body,
                status="sanitized",
            )
            extracted_artifacts.append(art_record)
            return f"\n\n> 🛠️ **Generated Operational Artifact**: *{art_title}* (Rendered in Growth Canvas)\n"

        cleaned_content = ARTIFACT_REGEX.sub(artifact_replacer, full_text)

        assistant_msg = MessageModel(
            session_id=session_id,
            role="assistant",
            content=cleaned_content.strip(),
            mode=mode,
            model=provider.get_model_name(),
            latency_ms=total_ms,
            citations=json.dumps([c.model_dump() for c in citations]),
        )
        self.db.add(assistant_msg)
        self.db.flush()

        for art in extracted_artifacts:
            art.message_id = assistant_msg.id
            self.db.add(art)
            self.db.flush()
            artifact_summaries.append(
                ArtifactSummary(
                    id=art.id,
                    artifact_type=art.artifact_type,
                    title=art.title,
                    status=art.status,
                    created_at=art.created_at.isoformat() if art.created_at else None,
                )
            )

        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        if artifact_summaries:
            yield f"data: {json.dumps({'event': 'artifacts', 'artifacts': [a.model_dump() for a in artifact_summaries]})}\n\n"

        # Quality evaluation event
        try:
            quality_res = evaluate_response(
                query=content,
                response=assistant_msg.content,
                evidence_snippets=[c.excerpt for c in citations if c.excerpt],
                citations=[c.model_dump() for c in citations],
            )
            yield f"data: {json.dumps({'event': 'quality', 'score': round(quality_res.overall_score, 3), 'passed': quality_res.passed, 'suggestions': quality_res.improvement_suggestions})}\n\n"
        except Exception as e:
            logger.warning(f"Quality evaluation failed: {e}")

        metrics_payload = {
            "ttft_ms": ttft_ms or round(retrieval_ms + 120.0, 2),
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms,
            "total_ms": total_ms,
            "token_count": token_count,
            "tokens_per_sec": tokens_per_sec,
            "model": provider.get_model_name(),
            "provider": provider.get_provider_id(),
        }
        yield f"data: {json.dumps({'event': 'metrics', 'metrics': metrics_payload})}\n\n"
        yield f"data: {json.dumps({'event': 'done', 'message_id': assistant_msg.id, 'capability': classification.capability.value, 'intelligence_mode': intelligence_mode, 'metrics': metrics_payload, 'execution_verified': execution_verified, 'execution_telemetry': execution_telemetry, 'follow_up_suggestions': orchestrated_context.follow_up_suggestions})}\n\n"
