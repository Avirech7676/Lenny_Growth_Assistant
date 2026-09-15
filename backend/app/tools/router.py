"""Centralized Tool Router managing registration, permission gating, timeout control, and execution."""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional

from app.tools.base import Tool, ToolResult
from app.tools.web_search import WebSearchTool
from app.tools.web_fetch import WebFetchTool
from app.tools.code_sandbox import CodeExecutionTool
from app.tools.file_reader import FileReadTool
from app.tools.calculator import CalculatorTool
from app.tools.lenny_search import LennySearchTool
from app.tools.artifact_generator import ArtifactGeneratorTool

logger = logging.getLogger(__name__)


class ToolRouter:
    """Orchestrates available platform tools with timeout control and output normalization."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the 7 core built-in tools of the platform."""
        defaults = [
            WebSearchTool(),
            WebFetchTool(),
            CodeExecutionTool(),
            FileReadTool(),
            CalculatorTool(),
            LennySearchTool(),
            ArtifactGeneratorTool(),
        ]
        for t in defaults:
            self.register(t)

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool '%s'", tool.name)

    def get(self, name: str) -> Optional[Tool]:
        """Fetch tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_tool_specs(self, format: str = "openai") -> List[Dict[str, Any]]:
        """Return tool declarations formatted for the target model provider API."""
        fmt = format.lower()
        specs = []
        for t in self._tools.values():
            if fmt in ("openai", "groq"):
                specs.append(t.to_openai_spec())
            elif fmt == "anthropic":
                specs.append(t.to_anthropic_spec())
            elif fmt == "gemini":
                specs.append(t.to_gemini_spec())
            else:
                specs.append(t.to_openai_spec())
        return specs

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        caller_permissions: Optional[List[str]] = None,
    ) -> ToolResult:
        """Execute a tool with parameter validation, permission check, and timeout enforcement."""
        t0 = time.perf_counter()
        tool = self.get(name)

        if not tool:
            return ToolResult(
                tool_name=name,
                status="error",
                input_params=arguments,
                error_message=f"Tool '{name}' is not registered in the ToolRouter.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        # Permission check
        if tool.requires_permissions:
            caller_perms = set(caller_permissions or [])
            missing = [p for p in tool.requires_permissions if p not in caller_perms]
            if missing:
                return ToolResult(
                    tool_name=name,
                    status="rejected",
                    input_params=arguments,
                    error_message=f"Permission denied: Missing required permissions: {', '.join(missing)}",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )

        # Enforce timeout
        try:
            result = await asyncio.wait_for(
                tool.execute(**arguments),
                timeout=tool.timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=name,
                status="timeout",
                input_params=arguments,
                error_message=f"Tool '{name}' timed out after {tool.timeout_seconds} seconds.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            logger.exception("Unexpected error executing tool '%s'", name)
            return ToolResult(
                tool_name=name,
                status="error",
                input_params=arguments,
                error_message=f"Internal tool execution error: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )


_TOOL_ROUTER = ToolRouter()


def get_tool_router() -> ToolRouter:
    """Access the singleton ToolRouter instance."""
    return _TOOL_ROUTER
