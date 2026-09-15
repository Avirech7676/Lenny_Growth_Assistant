"""Unified Cross-Provider Tool Calling and Function Invocation Engine.

Provides canonical ToolDefinition, ToolCall, ToolResult, ToolRegistry,
and schema converters for OpenAI, Gemini, Anthropic, and Groq.
"""

import sys
import os
import json
import uuid
import time
import logging
import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Canonical schema for a tool that can be invoked by LLMs across all providers."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[..., Any]] = None
    timeout_seconds: float = 15.0

    def to_openai_spec(self) -> Dict[str, Any]:
        """Convert canonical definition to OpenAI / Groq tool specification format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_gemini_spec(self) -> Dict[str, Any]:
        """Convert canonical definition to Google Gemini function declaration format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def to_anthropic_spec(self) -> Dict[str, Any]:
        """Convert canonical definition to Anthropic Claude tool block format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


@dataclass
class ToolCall:
    """Normalized representation of a model's request to execute a tool."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:12]}")
    raw_arguments: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard dictionary representation compatible with all providers."""
        args_str = self.raw_arguments if self.raw_arguments is not None else json.dumps(self.arguments)
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": args_str,
            },
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Construct normalized ToolCall from diverse provider dictionary formats."""
        call_id = data.get("id") or f"call_{uuid.uuid4().hex[:12]}"
        name = ""
        args: Dict[str, Any] = {}
        raw_args = None

        if "function" in data and isinstance(data["function"], dict):
            fn = data["function"]
            name = fn.get("name", "")
            raw_val = fn.get("arguments", "{}")
            if isinstance(raw_val, dict):
                args = raw_val
                raw_args = json.dumps(raw_val)
            elif isinstance(raw_val, str):
                raw_args = raw_val
                try:
                    args = json.loads(raw_val)
                except Exception:
                    args = {"raw": raw_val}
        else:
            name = data.get("name", "")
            args_val = data.get("arguments", data.get("input", {}))
            if isinstance(args_val, dict):
                args = args_val
                raw_args = json.dumps(args_val)
            elif isinstance(args_val, str):
                raw_args = args_val
                try:
                    args = json.loads(args_val)
                except Exception:
                    args = {"raw": args_val}

        return cls(id=call_id, name=name, arguments=args, raw_arguments=raw_args)


@dataclass
class ToolResult:
    """Standardized tool execution result."""
    tool_name: str
    status: str = "success"  # "success", "error", "rejected", "timeout"
    output: Any = None
    call_id: Optional[str] = None
    input_params: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "name": self.tool_name,
            "status": self.status,
            "call_id": self.call_id,
            "input_params": self.input_params,
            "output": self.output,
            "error_message": self.error_message,
            "duration_ms": round(self.duration_ms, 2),
            "metadata": self.metadata,
        }

    def to_content_str(self) -> str:
        """Format output as human/LLM-readable text."""
        if self.is_success:
            if isinstance(self.output, str):
                return self.output
            try:
                return json.dumps(self.output, indent=2)
            except Exception:
                return str(self.output)
        return f"Tool Execution Error ({self.status}): {self.error_message or 'Unknown error'}"


def to_openai_tools(tools: Union[List[ToolDefinition], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert any list of tools or definitions into OpenAI function format."""
    specs = []
    for t in tools:
        if isinstance(t, ToolDefinition):
            specs.append(t.to_openai_spec())
        elif isinstance(t, dict):
            if "type" in t and "function" in t:
                specs.append(t)
            elif "name" in t:
                params = t.get("parameters") or t.get("input_schema") or {"type": "object", "properties": {}}
                specs.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": params,
                    },
                })
            else:
                specs.append(t)
        elif hasattr(t, "to_openai_spec"):
            specs.append(t.to_openai_spec())
    return specs


def to_gemini_tools(tools: Union[List[ToolDefinition], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert any list of tools or definitions into Gemini function declaration format."""
    specs = []
    for t in tools:
        if isinstance(t, ToolDefinition):
            specs.append(t.to_gemini_spec())
        elif isinstance(t, dict):
            if "function" in t and isinstance(t["function"], dict):
                fn = t["function"]
                specs.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
                })
            elif "name" in t:
                params = t.get("parameters") or t.get("input_schema") or {"type": "object", "properties": {}}
                specs.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": params,
                })
            else:
                specs.append(t)
        elif hasattr(t, "to_gemini_spec"):
            specs.append(t.to_gemini_spec())
    return specs


def to_anthropic_tools(tools: Union[List[ToolDefinition], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert any list of tools or definitions into Anthropic tool format."""
    specs = []
    for t in tools:
        if isinstance(t, ToolDefinition):
            specs.append(t.to_anthropic_spec())
        elif isinstance(t, dict):
            if "function" in t and isinstance(t["function"], dict):
                fn = t["function"]
                specs.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })
            elif "name" in t:
                params = t.get("input_schema") or t.get("parameters") or {"type": "object", "properties": {}}
                specs.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": params,
                })
            else:
                specs.append(t)
        elif hasattr(t, "to_anthropic_spec"):
            specs.append(t.to_anthropic_spec())
    return specs


class ToolRegistry:
    """Registry managing available tools, format adapters, and safe sandboxed execution."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register canonical platform tools with lazy module loading."""
        try:
            from app.tools.calculator import CalculatorTool
            calc = CalculatorTool()
            self.register(ToolDefinition(
                name="calculator",
                description="Evaluate mathematical expressions and financial growth metrics (CAGR, LTV, CAC Payback, ICE, RICE).",
                parameters=calc.input_schema,
                handler=calc.execute,
                timeout_seconds=calc.timeout_seconds,
            ))
        except Exception as e:
            logger.warning("Could not register default calculator tool: %s", e)

        try:
            from app.tools.code_sandbox import CodeExecutionTool
            code_tool = CodeExecutionTool()
            # Register both canonical python_sandbox and code_execution alias
            self.register(ToolDefinition(
                name="python_sandbox",
                description="Execute Python code in an isolated subprocess sandbox. Returns stdout, stderr, and execution status.",
                parameters=code_tool.input_schema,
                handler=code_tool.execute,
                timeout_seconds=code_tool.timeout_seconds,
            ))
            self.register(ToolDefinition(
                name="code_execution",
                description="Execute Python code in an isolated subprocess sandbox. Returns stdout, stderr, and execution status.",
                parameters=code_tool.input_schema,
                handler=code_tool.execute,
                timeout_seconds=code_tool.timeout_seconds,
            ))
        except Exception as e:
            logger.warning("Could not register default code execution tool: %s", e)

        try:
            from app.tools.web_search import WebSearchTool
            web_tool = WebSearchTool()
            self.register(ToolDefinition(
                name="web_search",
                description="Search real-world web sources, official technical documentation, and registries in real time.",
                parameters=web_tool.input_schema,
                handler=web_tool.execute,
                timeout_seconds=web_tool.timeout_seconds,
            ))
        except Exception as e:
            logger.warning("Could not register default web search tool: %s", e)

        try:
            from app.tools.lenny_search import LennySearchTool
            lenny_tool = LennySearchTool()
            # Register both transcript_search and lenny_search alias
            self.register(ToolDefinition(
                name="transcript_search",
                description="Query the Lenny's Podcast and Newsletter transcript archive for growth frameworks and guest insights.",
                parameters=lenny_tool.input_schema,
                handler=lenny_tool.execute,
                timeout_seconds=lenny_tool.timeout_seconds,
            ))
            self.register(ToolDefinition(
                name="lenny_search",
                description="Query the Lenny's Podcast and Newsletter transcript archive for growth frameworks and guest insights.",
                parameters=lenny_tool.input_schema,
                handler=lenny_tool.execute,
                timeout_seconds=lenny_tool.timeout_seconds,
            ))
        except Exception as e:
            logger.warning("Could not register default transcript search tool: %s", e)

    def register(self, tool: Union[ToolDefinition, Any]) -> None:
        """Register a ToolDefinition or legacy Tool instance."""
        if isinstance(tool, ToolDefinition):
            self._tools[tool.name] = tool
        elif hasattr(tool, "name") and hasattr(tool, "execute"):
            params = getattr(tool, "input_schema", {"type": "object", "properties": {}})
            desc = getattr(tool, "description", "")
            timeout = getattr(tool, "timeout_seconds", 15.0)
            self._tools[tool.name] = ToolDefinition(
                name=tool.name,
                description=desc,
                parameters=params,
                handler=tool.execute,
                timeout_seconds=timeout,
            )
        else:
            raise ValueError(f"Object {tool} is not a valid ToolDefinition or Tool")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Fetch registered tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tools.values())

    def get_specs(self, provider: str = "openai") -> List[Dict[str, Any]]:
        """Return tool declarations formatted for the target provider."""
        fmt = provider.lower()
        tools_list = list(self._tools.values())
        if fmt in ("gemini", "google"):
            return to_gemini_tools(tools_list)
        elif fmt == "anthropic":
            return to_anthropic_tools(tools_list)
        else:
            return to_openai_tools(tools_list)

    async def execute_async(
        self,
        name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> ToolResult:
        """Execute a tool asynchronously with parameter validation and timeout enforcement."""
        t0 = time.perf_counter()
        tool = self.get(name)

        if not tool:
            return ToolResult(
                tool_name=name,
                call_id=call_id,
                status="error",
                input_params=arguments,
                error_message=f"Tool '{name}' is not registered in ToolRegistry.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        if not tool.handler:
            return ToolResult(
                tool_name=name,
                call_id=call_id,
                status="error",
                input_params=arguments,
                error_message=f"Tool '{name}' does not have an executable handler.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        try:
            handler = tool.handler
            if inspect.iscoroutinefunction(handler):
                out = await asyncio.wait_for(handler(**arguments), timeout=tool.timeout_seconds)
            else:
                out = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: handler(**arguments)),
                    timeout=tool.timeout_seconds,
                )

            dur = (time.perf_counter() - t0) * 1000

            # Normalize if handler returned ToolResult from app.tools.base
            if hasattr(out, "output") and hasattr(out, "status"):
                return ToolResult(
                    tool_name=name,
                    call_id=call_id,
                    status=getattr(out, "status", "success"),
                    input_params=arguments,
                    output=getattr(out, "output", out),
                    error_message=getattr(out, "error_message", None),
                    duration_ms=dur,
                    metadata=getattr(out, "metadata", {}),
                )

            return ToolResult(
                tool_name=name,
                call_id=call_id,
                status="success",
                input_params=arguments,
                output=out,
                duration_ms=dur,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=name,
                call_id=call_id,
                status="timeout",
                input_params=arguments,
                error_message=f"Tool '{name}' execution timed out after {tool.timeout_seconds} seconds.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            logger.exception("Error executing tool '%s': %s", name, e)
            return ToolResult(
                tool_name=name,
                call_id=call_id,
                status="error",
                input_params=arguments,
                error_message=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> ToolResult:
        """Synchronous wrapper for executing tools safely from any thread."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.execute_async(name, arguments, call_id))
                    return future.result()
            return loop.run_until_complete(self.execute_async(name, arguments, call_id))
        except RuntimeError:
            return asyncio.run(self.execute_async(name, arguments, call_id))


_TOOL_REGISTRY: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Return platform singleton ToolRegistry."""
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        _TOOL_REGISTRY = ToolRegistry()
    return _TOOL_REGISTRY
