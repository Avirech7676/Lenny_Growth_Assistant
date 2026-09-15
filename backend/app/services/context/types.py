"""Data contracts and schemas for Phase 8 Context Management.

Defines the 5-layer context architecture:
1. recent context (verbatim turns)
2. relevant historical context (compacted and semantic-filtered)
3. task state (operational objective, continuity, follow-up depth)
4. relevant files (attached user files or inspected codebase files)
5. relevant research (fresh live search / Lenny RAG evidence)
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class TransitionType(str, Enum):
    """Classification of turn-to-turn conversational flow."""
    CONTINUITY = "continuity"         # Direct follow-up, elaboration, refinement of current task
    TOPIC_SWITCH = "topic_switch"     # Explicit or semantic pivot to an unrelated domain/topic
    NEW_TOPIC = "new_topic"           # Fresh query with no ties to previous context


@dataclass
class TaskState:
    """Explicit operational state tracked across conversational turns."""
    topic: str = "General Consultation"
    goal: str = "Provide grounded, high-signal assistance"
    status: str = "active"             # 'active', 'refined', 'completed'
    follow_up_depth: int = 0           # 0 for root query, increments with each follow-up
    active_artifacts: List[str] = field(default_factory=list)  # Active code, diagrams, schemas
    working_code_language: Optional[str] = None
    last_domain: Optional[str] = None
    last_user_query: Optional[str] = None
    last_transition: Optional[TransitionType] = None
    layer_type: str = "task_state"


@dataclass
class ContextLayer:
    """A single decoupled layer within the assembled prompt context."""
    layer_name: str                    # 'recent_context', 'relevant_historical_context', 'task_state', 'relevant_files', 'relevant_research'
    title: str
    token_estimate: int
    content: str
    is_active: bool = True

    @property
    def layer_type(self) -> str:
        return self.layer_name


@dataclass
class OrchestratedContext:
    """Result of multi-layer context compilation for LLM prompt execution."""
    session_id: str
    user_query: str
    transition_type: TransitionType
    task_state: TaskState
    layers: List[ContextLayer] = field(default_factory=list)
    llm_history: List[Dict[str, str]] = field(default_factory=list)
    assembled_prompt_context: str = ""
    follow_up_suggestions: List[str] = field(default_factory=list)
    was_compacted: bool = False
    total_tokens_estimated: int = 0

    @property
    def recent_context(self) -> Optional[ContextLayer]:
        return next((l for l in self.layers if l.layer_name == "recent_context"), None)

    @property
    def relevant_history(self) -> Optional[ContextLayer]:
        return next((l for l in self.layers if l.layer_name == "relevant_historical_context"), None)

    @property
    def relevant_files(self) -> Optional[ContextLayer]:
        return next((l for l in self.layers if l.layer_name == "relevant_files"), None)

    @property
    def relevant_research(self) -> Optional[ContextLayer]:
        return next((l for l in self.layers if l.layer_name == "relevant_research"), None)

    @property
    def active_task(self) -> TaskState:
        return self.task_state

    @property
    def is_compacted(self) -> bool:
        return self.was_compacted

    @property
    def total_tokens(self) -> int:
        return self.total_tokens_estimated

    @property
    def compaction_summary(self) -> Optional[str]:
        hist = self.relevant_history
        return hist.content if hist else None

    def to_prompt_context(self) -> str:
        return self.assembled_prompt_context

