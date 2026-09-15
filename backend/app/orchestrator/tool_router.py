"""Tool Router for AI Orchestrator.

Resolves and dispatches execution tools needed by TaskSteps in an ExecutionPlan:
- Search engines (direct web & autonomous deep research)
- Transcript / vector database retrieval
- Workspace code & file inspection
- Interactive artifact extraction & Growth Canvas sanitization
- AST parsing & syntax validation
"""

from typing import Dict, Any, Optional, List
import logging
from app.orchestrator.types import TaskStep, Capability

logger = logging.getLogger(__name__)


class ToolRouter:
    """Manages tool availability, binding, and invocation dispatch."""

    def __init__(self):
        self._available_tools = [
            "search_engine",
            "deep_research_engine",
            "transcript_retriever",
            "code_generator",
            "code_debugger",
            "code_linter",
            "architecture_designer",
            "metrics_calculator",
            "document_parser",
            "prose_composer",
            "roadmap_planner",
            "canvas_builder",
            "syntax_validator",
            "code_sandbox",
            "repo_inspector",
        ]

    def get_available_tools(self) -> List[str]:
        return list(self._available_tools)

    def route_tool_for_step(self, step: TaskStep) -> Optional[str]:
        """Verify tool compatibility and return active tool identifier."""
        if not step.tool_required:
            return None
        if step.tool_required in self._available_tools:
            return step.tool_required
        logger.warning("Requested tool '%s' not recognized; defaulting to standard tool.", step.tool_required)
        return "general_tool"
