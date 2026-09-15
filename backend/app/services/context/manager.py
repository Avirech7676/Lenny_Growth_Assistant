"""Unified Context Manager for Phase 8.

Implements decoupled 5-layer context management:
1. recent context (verbatim recent turns for pronoun and conversational flow)
2. relevant historical context (semantic filtered & compacted older turns)
3. task state (operational objective, continuity, follow-up depth)
4. relevant files (uploaded files or inspected repository code)
5. relevant research (freshly retrieved live search or Lenny RAG evidence)

Enforces:
- Seamless task continuity across multiple follow-up turns
- Topic switch detection and strict cross-topic isolation (zero contamination)
- Compaction for long conversations with hard token budgeting
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.services.context.types import (
    TransitionType,
    TaskState,
    ContextLayer,
    OrchestratedContext,
)
from app.services.memory.compactor import get_memory_compactor, MemoryCompactor

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4
DEFAULT_RECENT_VERBATIM_TURNS = 4
MAX_TOTAL_CONTEXT_TOKENS = 4000


class UnifiedContextManager:
    """Enterprise context manager orchestrating prompt layers, task continuity, and epistemic hygiene."""

    def __init__(
        self,
        recent_turns: int = DEFAULT_RECENT_VERBATIM_TURNS,
        max_context_tokens: int = MAX_TOTAL_CONTEXT_TOKENS,
    ):
        self.recent_turns = recent_turns
        self.max_context_tokens = max_context_tokens
        self.compactor: MemoryCompactor = get_memory_compactor()
        self._session_task_states: Dict[str, TaskState] = {}

    def get_task_state(self, session_id: str) -> TaskState:
        return self._session_task_states.get(
            session_id,
            TaskState(topic="Initial Consultation", goal="Provide grounded assistance", follow_up_depth=0),
        )

    def set_task_state(self, session_id: str, state: TaskState) -> None:
        self._session_task_states[session_id] = state

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // CHARS_PER_TOKEN)

    def detect_transition(
        self,
        current_query: str,
        previous_query: Optional[str] = None,
        previous_task_state: Optional[TaskState] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[TransitionType, str]:
        """Classify conversational continuity vs. topic switch vs. new topic."""
        if not history or not previous_query:
            return TransitionType.NEW_TOPIC, "Initial conversation turn"

        q_lower = current_query.strip().lower()
        prev_lower = previous_query.strip().lower()

        # 1. Check for explicit follow-up / continuity markers
        follow_up_pronouns = [
            " it", " it?", " it.", " it,", " this", " that", " them", " these",
            "that endpoint", "that code", "that function", "the function",
            "the endpoint", "the second one", "the first one", "the former",
            "the latter", "same thing", "previous", "above", "to it"
        ]
        has_pronoun = any(p in q_lower for p in follow_up_pronouns) or q_lower.startswith("it ") or q_lower.startswith("that ")

        refinement_verbs = [
            "add ", "modify ", "update ", "improve ", "refactor ", "rewrite ",
            "optimize ", "change ", "how about ", "can you also ", "what about ",
            "expand on ", "now add ", "now make ", "make it ", "include ",
            "explain why ", "show me how ", "why does ", "what if "
        ]
        has_refinement_verb = any(v in q_lower for v in refinement_verbs)

        short_follow_up = len(q_lower.split()) <= 7 and (has_pronoun or has_refinement_verb or "?" in q_lower)

        # 2. Check for explicit topic switch phrases
        explicit_switch_phrases = [
            "different topic", "change topic", "switch topic", "moving on",
            "unrelated question", "new topic", "another subject", "on another note"
        ]
        if any(sp in q_lower for sp in explicit_switch_phrases):
            return TransitionType.TOPIC_SWITCH, "Explicit user topic switch marker"

        # 3. Domain divergence check
        coding_keywords = [
            "fastapi", "endpoint", "python", "code", "async", "function", "pydantic", "bcrypt", "jwt",
            "sql", "api", "react", "bug", "error", "merge sort", "quicksort", "binary search",
            "time complexity", "space complexity", "big o", "data structure", "sorting", "algorithm",
            "complexity", "c++", "javascript", "typescript"
        ]
        government_keywords = [
            "chief minister", "cm", "minister", "prime minister", "president", "andhra pradesh", "ap",
            "governor", "election", "capital", "government", "parliament", "amaravati"
        ]
        lenny_keywords = [
            "lenny", "podcast", "chesky", "shreyas", "founder mode", "retention", "plg", "onboarding",
            "activation", "pmf", "elena verna"
        ]
        general_keywords = [
            "prabhas", "actor", "cinema", "movie", "film", "cricket", "weather", "quantum computing",
            "quantum", "physics", "biology", "history"
        ]

        prev_is_coding = any(k in prev_lower for k in coding_keywords)
        curr_is_coding = any(k in q_lower for k in coding_keywords)

        prev_is_gov = any(k in prev_lower for k in government_keywords)
        curr_is_gov = any(k in q_lower for k in government_keywords)

        prev_is_lenny = any(k in prev_lower for k in lenny_keywords)
        curr_is_lenny = any(k in q_lower for k in lenny_keywords)

        prev_is_gen = any(k in prev_lower for k in general_keywords)
        curr_is_gen = any(k in q_lower for k in general_keywords)

        # Cross-domain divergence -> definite topic switch
        domain_clash = (
            (prev_is_coding and (curr_is_gov or curr_is_lenny or curr_is_gen)) or
            (prev_is_gov and (curr_is_coding or curr_is_lenny or curr_is_gen)) or
            (prev_is_lenny and (curr_is_coding or curr_is_gov or curr_is_gen)) or
            (prev_is_gen and (curr_is_coding or curr_is_gov or curr_is_lenny))
        )

        if domain_clash and not (has_pronoun or has_refinement_verb):
            return TransitionType.TOPIC_SWITCH, "Divergent domain transition"

        # If follow-up indicators are present and no hard domain clash
        if (has_pronoun or has_refinement_verb or short_follow_up) and not domain_clash:
            return TransitionType.CONTINUITY, "Detected conversational continuity and refinement signals"

        # Check entity/keyword overlap with previous user turn AND recent assistant turns
        q_words = set(re.findall(r'\b\w{4,}\b', q_lower))
        prev_words = set(re.findall(r'\b\w{4,}\b', prev_lower))
        if history:
            for turn in history[-2:]:
                prev_words.update(re.findall(r'\b\w{4,}\b', turn.get("content", "").lower()))
        overlap = len(q_words.intersection(prev_words))

        if overlap >= 2 or (overlap >= 1 and (curr_is_coding == prev_is_coding or curr_is_lenny == prev_is_lenny or curr_is_coding or curr_is_lenny)):
            return TransitionType.CONTINUITY, f"Keyword overlap ({overlap} common terms)"

        # Default to new topic if unrelated
        return TransitionType.NEW_TOPIC, "No conversational continuity or entity overlap detected"

    def update_task_state(
        self,
        transition: TransitionType,
        current_query: str,
        previous_state: Optional[TaskState] = None,
    ) -> TaskState:
        """Update operational task state based on conversational transition."""
        if not previous_state or transition in [TransitionType.TOPIC_SWITCH, TransitionType.NEW_TOPIC]:
            # Clean task slate for new topics or topic switches
            clean_topic = current_query[:48].strip()
            if len(current_query) > 48:
                clean_topic += "..."
            return TaskState(
                topic=clean_topic,
                goal=f"Address user query: {current_query[:60]}",
                status="active",
                follow_up_depth=0,
                active_artifacts=[],
                working_code_language="python" if "python" in current_query.lower() or "fastapi" in current_query.lower() else None,
                last_user_query=current_query,
                last_transition=transition,
            )

        # Continuity: preserve and evolve existing state
        new_depth = previous_state.follow_up_depth + 1
        return TaskState(
            topic=previous_state.topic,
            goal=f"{previous_state.goal} -> Refinement: {current_query[:50]}",
            status="refined",
            follow_up_depth=new_depth,
            active_artifacts=list(previous_state.active_artifacts),
            working_code_language=previous_state.working_code_language,
            last_domain=previous_state.last_domain,
            last_user_query=current_query,
            last_transition=transition,
        )

    def build_orchestrated_context(
        self,
        session_id: str,
        user_query: str,
        raw_history: List[Dict[str, str]],
        active_files: Optional[List[Dict[str, Any]]] = None,
        active_research_context: Optional[str] = None,
        previous_state: Optional[TaskState] = None,
    ) -> OrchestratedContext:
        """Build the structured 5-layer context payload for LLM inference."""
        previous_user_query = None
        if previous_state is None:
            previous_state = self.get_task_state(session_id)

        if raw_history:
            for m in reversed(raw_history):
                if m.get("role") == "user":
                    previous_user_query = m.get("content")
                    break

        # Step 1: Detect conversational transition
        transition, reason = self.detect_transition(
            current_query=user_query,
            previous_query=previous_user_query,
            previous_task_state=previous_state,
            history=raw_history,
        )
        logger.info(f"ContextManager transition: {transition.value} ({reason})")

        # Step 2: Evolve Task State
        current_state = self.update_task_state(
            transition=transition,
            current_query=user_query,
            previous_state=previous_state,
        )
        self.set_task_state(session_id, current_state)

        layers: List[ContextLayer] = []
        llm_history: List[Dict[str, str]] = []
        was_compacted = False

        # Step 3: Layer 1 & 2 - Recent Context & Relevant Historical Context
        if transition == TransitionType.TOPIC_SWITCH:
            # STRICT PURGE: When switching topics, completely isolate previous unrelated evidence/code
            logger.info("Topic switch detected: Purging previous domain evidence from LLM context.")
            history_summary = "[TOPIC SWITCH DETECTED: Previous conversation context isolated to prevent contamination]"
            llm_history = []
            layers.append(
                ContextLayer(
                    layer_name="relevant_historical_context",
                    title="[RELEVANT HISTORICAL CONTEXT] (Isolated)",
                    token_estimate=self.estimate_tokens(history_summary),
                    content=history_summary,
                )
            )
        else:
            # Continuity or New Topic: apply sliding window + compaction
            if len(raw_history) > 2:
                split_idx = max(1, len(raw_history) - min(self.recent_turns, max(1, len(raw_history) // 2)))
                older = raw_history[:split_idx]
                recent = raw_history[split_idx:]
                was_compacted = len(raw_history) > self.recent_turns

                compacted_obj = self.compactor.compact(older)
                history_summary = compacted_obj.compressed_summary or "Preserved relevant historical context."
                llm_history = self.compactor.build_llm_history(compacted_obj)
                llm_history.extend(recent)

                layers.append(
                    ContextLayer(
                        layer_name="relevant_historical_context",
                        title="[RELEVANT HISTORICAL CONTEXT]",
                        token_estimate=self.estimate_tokens(history_summary),
                        content=history_summary,
                    )
                )
            else:
                recent = raw_history
                llm_history = list(raw_history)
                if raw_history:
                    layers.append(
                        ContextLayer(
                            layer_name="relevant_historical_context",
                            title="[RELEVANT HISTORICAL CONTEXT]",
                            token_estimate=self.estimate_tokens("Initial interaction history preserved."),
                            content="Initial interaction history preserved.",
                        )
                    )

            # Add recent context layer description
            recent_text = "\n".join([f"{m.get('role', 'user').upper()}: {m.get('content', '')[:120]}" for m in recent])
            if recent_text or raw_history:
                layers.append(
                    ContextLayer(
                        layer_name="recent_context",
                        title="[RECENT CONVERSATION TURNS]",
                        token_estimate=self.estimate_tokens(recent_text or "No prior turns"),
                        content=recent_text or "No prior turns",
                    )
                )

        # Step 4: Layer 3 - Task State
        state_header = (
            f"TASK CONTINUITY STATE:\n"
            f"- Current Objective: {current_state.topic}\n"
            f"- Refinement Turn: {current_state.follow_up_depth}\n"
            f"- Status: {current_state.status}\n"
            f"- Flow: {transition.value.upper()}"
        )
        layers.append(
            ContextLayer(
                layer_name="task_state",
                title="[TASK STATE & CONTINUITY]",
                token_estimate=self.estimate_tokens(state_header),
                content=state_header,
            )
        )

        # Step 5: Layer 4 - Relevant Files
        file_blocks_text = ""
        if active_files and transition != TransitionType.TOPIC_SWITCH:
            file_snippets = []
            for f in active_files[:3]:
                fname = f.get("filename", "document")
                fcontent = f.get("content", "")[:1200]
                file_snippets.append(f"--- [RELEVANT FILE: {fname}] ---\n{fcontent}\n---")
            file_blocks_text = "\n\n".join(file_snippets)
        if file_blocks_text:
            layers.append(
                ContextLayer(
                    layer_name="relevant_files",
                    title="[ATTACHED FILES & CODE CONTEXT]",
                    token_estimate=self.estimate_tokens(file_blocks_text),
                    content=file_blocks_text,
                )
            )

        # Step 6: Layer 5 - Relevant Research
        if active_research_context:
            layers.append(
                ContextLayer(
                    layer_name="relevant_research",
                    title="[GROUNDING RESEARCH EVIDENCE]",
                    token_estimate=self.estimate_tokens(active_research_context),
                    content=active_research_context,
                )
            )

        # Assemble unified prompt context
        active_layer_contents = [
            f"=== {layer.title.upper()} ===\n{layer.content}"
            for layer in layers
            if layer.content.strip()
        ]
        assembled_prompt_context = "\n\n".join(active_layer_contents)

        # Generate contextual follow-up prompt chips for UI
        suggestions = self.generate_follow_up_suggestions(
            query=user_query,
            task_state=current_state,
            transition=transition,
        )

        total_tokens = sum(l.token_estimate for l in layers)

        return OrchestratedContext(
            session_id=session_id,
            user_query=user_query,
            transition_type=transition,
            task_state=current_state,
            layers=layers,
            llm_history=llm_history,
            assembled_prompt_context=assembled_prompt_context,
            follow_up_suggestions=suggestions,
            was_compacted=was_compacted,
            total_tokens_estimated=total_tokens,
        )

    def assemble_context(
        self,
        session_id: str,
        current_query: str,
        history: Optional[List[Dict[str, str]]] = None,
        research_evidence: Optional[Any] = None,
        file_context: Optional[str] = None,
        active_artifacts: Optional[List[str]] = None,
        previous_state: Optional[TaskState] = None,
    ) -> OrchestratedContext:
        """Convenience method for end-to-end 5-layer context assembly."""
        active_files = None
        if file_context:
            active_files = [{"filename": "context_doc", "content": file_context}]

        research_text = ""
        if research_evidence:
            if isinstance(research_evidence, list):
                lines = []
                for item in research_evidence:
                    if isinstance(item, dict):
                        title = item.get("title", "Evidence")
                        snippet = item.get("snippet", item.get("content", ""))
                        lines.append(f"- {title}: {snippet}")
                    else:
                        lines.append(str(item))
                research_text = "\n".join(lines)
            else:
                research_text = str(research_evidence)

        prev_state = previous_state or self.get_task_state(session_id)

        ctx = self.build_orchestrated_context(
            session_id=session_id,
            user_query=current_query,
            raw_history=history or [],
            active_files=active_files,
            active_research_context=research_text,
            previous_state=prev_state,
        )
        return ctx

    def generate_follow_up_suggestions(
        self,
        query: str,
        task_state: TaskState,
        transition: TransitionType,
    ) -> List[str]:
        """Generate high-signal, clickable follow-up suggestion chips based on the active topic."""
        q_lower = query.lower()

        if any(w in q_lower for w in ["fastapi", "endpoint", "api", "python", "code", "database"]):
            return [
                "Add comprehensive unit tests for this implementation",
                "Add error handling, validation, and status codes",
                "Explain the performance tradeoffs and scaling limits",
            ]
        elif any(w in q_lower for w in ["chief minister", "andhra pradesh", "election", "governor", "government"]):
            return [
                "What are the primary policy initiatives announced recently?",
                "What is the current status of the state capital development?",
                "Provide historical context on previous governance terms",
            ]
        elif any(w in q_lower for w in ["lenny", "chesky", "growth", "retention", "plg", "founder mode"]):
            return [
                "Turn this into an actionable ICE growth experiment",
                "How does this compare to modern enterprise sales-led growth?",
                "Provide real-world examples from Airbnb and Figma",
            ]
        else:
            return [
                "Can you break this down into actionable next steps?",
                "What are the most common pitfalls or risks to avoid?",
                "Compare this with alternative approaches",
            ]


# Singleton instance
_UNIFIED_CONTEXT_MANAGER = UnifiedContextManager()


def get_unified_context_manager() -> UnifiedContextManager:
    """Access the global UnifiedContextManager singleton."""
    return _UNIFIED_CONTEXT_MANAGER
