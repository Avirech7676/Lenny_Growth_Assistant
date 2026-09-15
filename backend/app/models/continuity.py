"""Multi-Turn Model State Continuity and Conversation Memory Compaction.

Provides cross-model session state continuity, topic-aware history compaction,
and artifact/entity tracking across dynamic model transitions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import logging
import time
import re

logger = logging.getLogger(__name__)


@dataclass
class ModelTransition:
    """Record of a model switch within a single multi-turn session."""
    session_id: str
    from_model: str
    to_model: str
    from_provider: str
    to_provider: str
    timestamp: float = field(default_factory=time.time)
    reason: str = "dynamic_routing"


@dataclass
class SessionState:
    """Session operational state maintaining continuity across diverse model architectures."""
    session_id: str
    current_model: Optional[str] = None
    current_provider: Optional[str] = None
    model_transitions: List[ModelTransition] = field(default_factory=list)
    compacted_summary: Optional[str] = None
    extracted_entities: List[str] = field(default_factory=list)
    referenced_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    total_turns: int = 0
    last_active_timestamp: float = field(default_factory=time.time)


class StateContinuityManager:
    """Coordinates cross-model conversation state continuity and memory compaction."""

    def __init__(self, compaction_threshold_turns: int = 8, verbatim_recent_turns: int = 4):
        self.compaction_threshold_turns = compaction_threshold_turns
        self.verbatim_recent_turns = verbatim_recent_turns
        self._session_states: Dict[str, SessionState] = {}

    def get_or_create_state(self, session_id: str) -> SessionState:
        """Fetch or initialize session state container."""
        if session_id not in self._session_states:
            self._session_states[session_id] = SessionState(session_id=session_id)
        return self._session_states[session_id]

    def record_turn(
        self,
        session_id: str,
        active_model: str,
        active_provider: str,
        artifacts: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[ModelTransition]:
        """Record model execution and track cross-model transitions."""
        state = self.get_or_create_state(session_id)
        transition = None

        if state.current_model and state.current_model != active_model:
            transition = ModelTransition(
                session_id=session_id,
                from_model=state.current_model,
                to_model=active_model,
                from_provider=state.current_provider or "unknown",
                to_provider=active_provider,
                timestamp=time.time(),
            )
            state.model_transitions.append(transition)
            logger.info(
                "Cross-model transition in session %s: %s (%s) -> %s (%s)",
                session_id, state.current_model, state.current_provider, active_model, active_provider
            )

        state.current_model = active_model
        state.current_provider = active_provider
        state.total_turns += 1
        state.last_active_timestamp = time.time()

        if artifacts:
            for a in artifacts:
                if a not in state.referenced_artifacts:
                    state.referenced_artifacts.append(a)

        return transition

    def needs_compaction(self, history: List[Dict[str, str]]) -> bool:
        """Check if history size exceeds compaction turn threshold."""
        return len(history) > self.compaction_threshold_turns

    def compact_history(
        self,
        history: List[Dict[str, str]],
        session_id: Optional[str] = None,
        existing_summary: Optional[str] = None,
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """Compact conversation history by summarizing older turns and keeping recent turns verbatim.

        Returns:
            Tuple of (compacted_history, structured_summary_prose)
        """
        if not self.needs_compaction(history):
            return history, existing_summary

        from app.services.memory.compactor import get_memory_compactor
        compactor = get_memory_compactor()
        compactor.verbatim_turns = self.verbatim_recent_turns
        compacted_res = compactor.compact(history)

        summary_text = compacted_res.compressed_summary
        if existing_summary and existing_summary.strip():
            summary_text = f"{existing_summary}\n\n[SUBSEQUENT TURNS SUMMARY]:\n{summary_text}"

        # If summary exists, format into an assistant memory block or inject into first message
        verbatim_turns = list(compacted_res.verbatim_turns)

        if summary_text and verbatim_turns:
            # Prepend a synthesized system context injection or summary message
            summary_msg = {
                "role": "user",
                "content": f"<conversation_summary>\n{summary_text}\n</conversation_summary>\n\nPlease proceed with the latest context above.",
            }
            ack_msg = {
                "role": "assistant",
                "content": "Understood. I have full context of our previous discussion and decisions.",
            }
            formatted_history = [summary_msg, ack_msg] + verbatim_turns
        else:
            formatted_history = verbatim_turns

        if session_id:
            state = self.get_or_create_state(session_id)
            state.compacted_summary = summary_text

        return formatted_history, summary_text

    def prepare_turn(
        self,
        session_id: str,
        history: List[Dict[str, str]],
        active_model: Optional[str] = None,
        active_provider: Optional[str] = None,
    ) -> Tuple[List[Dict[str, str]], Optional[ModelTransition]]:
        """Prepare history for model invocation with compaction and cross-model normalization."""
        state = self.get_or_create_state(session_id)
        transition = None

        if active_model and active_provider:
            transition = self.record_turn(session_id, active_model, active_provider)

        # Standardize message roles
        normalized_history = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant", "system"):
                role = "user"
            normalized_history.append({"role": role, "content": content})

        # Apply compaction if necessary
        compacted_hist, _ = self.compact_history(
            normalized_history,
            session_id=session_id,
            existing_summary=state.compacted_summary,
        )

        return compacted_hist, transition


_STATE_CONTINUITY_MANAGER: Optional[StateContinuityManager] = None


def get_state_continuity_manager() -> StateContinuityManager:
    """Return platform singleton StateContinuityManager."""
    global _STATE_CONTINUITY_MANAGER
    if _STATE_CONTINUITY_MANAGER is None:
        _STATE_CONTINUITY_MANAGER = StateContinuityManager()
    return _STATE_CONTINUITY_MANAGER
