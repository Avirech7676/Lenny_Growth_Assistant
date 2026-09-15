"""Standard internal tool interface and normalized ToolResult contract.

Enforces uniform schemas, timeout handling, permission models, and multi-provider format adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized, provider-agnostic tool execution result."""
    tool_name: str
    status: str                         # "success", "error", "timeout", "rejected"
    input_params: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    sources: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status,
            "input_params": self.input_params,
            "output": self.output,
            "sources": self.sources or [],
            "citations": self.citations or [],
            "metadata": self.metadata,
            "duration_ms": round(self.duration_ms, 2),
            "error_message": self.error_message,
        }

    @property
    def is_success(self) -> bool:
        return self.status == "success"


class Tool(ABC):
    """Abstract Base Class for all tools in the general-purpose assistant platform."""

    name: str = "base_tool"
    description: str = "Base tool description"
    input_schema: Dict[str, Any] = {"type": "object", "properties": {}}
    timeout_seconds: float = 15.0
    requires_permissions: List[str] = []
    is_mutation: bool = False

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool logic safely and return a normalized ToolResult."""
        pass

    def to_openai_spec(self) -> Dict[str, Any]:
        """Format tool specification for OpenAI and Groq function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }

    def to_anthropic_spec(self) -> Dict[str, Any]:
        """Format tool specification for Anthropic Claude tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def to_gemini_spec(self) -> Dict[str, Any]:
        """Format tool specification for Google Gemini function declarations."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }
