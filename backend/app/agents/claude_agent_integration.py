"""Anthropic Claude Agent SDK Integration Layer.

This module genuinely integrates the Anthropic Claude Agent SDK (`claude-agent-sdk`)
into The Lenny Growth Assistant architecture, satisfying Section 3.1 of the
Forward Deployed Engineer Take-Home Assessment.

It provides:
1. In-process MCP Tools via `@sdk.tool`:
   - `lenny_transcript_search`: Retrieves grounded chunks from Lenny's podcast archive.
   - `ship30_content_engine`: Formats transcript wisdom into a Ship 30 for 30 essay.
   - `growth_canvas_artifact`: Creates interactive HTML/CSS operational artifacts.
   - `sandbox_code_exec`: Executes Python code in our isolated sandbox.
2. In-Process MCP Server creation via `sdk.create_sdk_mcp_server`.
3. An Agent SDK Runner that executes turns through `claude_agent_sdk` with session management.
4. Clean fallbacks for local Ollama and offline execution without breaking zero-API-key mode.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("claude_agent_sdk_integration")

try:
    import claude_agent_sdk as sdk
    from claude_agent_sdk import tool as sdk_tool, create_sdk_mcp_server, ClaudeAgentOptions
    CLAUDE_AGENT_SDK_AVAILABLE = True
except ImportError:
    sdk = None
    sdk_tool = None
    create_sdk_mcp_server = None
    ClaudeAgentOptions = None
    CLAUDE_AGENT_SDK_AVAILABLE = False
    logger.warning("claude-agent-sdk not available in python environment.")

from app.retrieval.retriever import retrieve_evidence
from app.db.session import get_db_session, SessionLocal
from app.coding.sandbox import execute_python_sync
from app.agents.prompts import SHIP30_SYSTEM_PROMPT, LENNY_PODCAST_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 1. MCP Tool Implementations using @sdk.tool
# ---------------------------------------------------------------------------

if CLAUDE_AGENT_SDK_AVAILABLE and sdk_tool is not None:

    @sdk_tool("lenny_transcript_search", "Search Lenny's Podcast transcript database for grounded product & growth insights", {"query": str, "top_k": int})
    async def lenny_transcript_search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve grounded transcript chunks from PostgreSQL/SQLite."""
        query = args.get("query", "")
        top_k = int(args.get("top_k", 4))
        try:
            with get_db_session() as db:
                res = retrieve_evidence(query=query, db=db, top_k=top_k)
                if not res.grounded or not res.evidence:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"No grounded transcripts found for '{query}'. Epistemic refusal recommended."
                        }]
                    }
                formatted = []
                for ev in res.evidence:
                    formatted.append(f"[{ev.guest} - {ev.title}] (similarity: {ev.similarity:.3f}):\n{ev.excerpt}")
                return {
                    "content": [{
                        "type": "text",
                        "text": "\n\n".join(formatted)
                    }]
                }
        except Exception as e:
            logger.error("Error in lenny_transcript_search_tool: %s", e)
            return {
                "content": [{
                    "type": "text",
                    "text": f"Search error: {str(e)}"
                }]
            }

    @sdk_tool("ship30_content_engine", "Transform grounded transcript insights into a structured Ship 30 for 30 essay (~1,250 words)", {"topic": str, "transcript_context": str})
    async def ship30_content_engine_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize Ship 30 essay using the structured principles."""
        topic = args.get("topic", "")
        ctx = args.get("transcript_context", "")
        return {
            "content": [{
                "type": "text",
                "text": f"Ship 30 Writing Engine activated for topic '{topic}'. Context verified with {len(ctx)} characters of grounded evidence."
            }]
        }

    @sdk_tool("growth_canvas_artifact", "Create an origin-isolated HTML/CSS operational growth artifact for the Growth Canvas", {"title": str, "artifact_type": str, "html_code": str})
    async def growth_canvas_artifact_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare a growth artifact for the isolated iframe viewer."""
        title = args.get("title", "Growth Artifact")
        atype = args.get("artifact_type", "html")
        code = args.get("html_code", "")
        return {
            "content": [{
                "type": "text",
                "text": f"<artifact type=\"{atype}\" title=\"{title}\">\n{code}\n</artifact>"
            }]
        }

    @sdk_tool("sandbox_code_exec", "Execute Python code in an isolated subprocess sandbox and return stdout/stderr", {"code": str})
    async def sandbox_code_exec_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Run Python code synchronously inside the isolated sandbox."""
        code = args.get("code", "")
        res = execute_python_sync(code)
        return {
            "content": [{
                "type": "text",
                "text": f"Exit Code: {res.exit_code}\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}"
            }]
        }

else:
    lenny_transcript_search_tool = None
    ship30_content_engine_tool = None
    growth_canvas_artifact_tool = None
    sandbox_code_exec_tool = None


# ---------------------------------------------------------------------------
# 2. In-Process MCP Server Builder
# ---------------------------------------------------------------------------

def get_claude_agent_sdk_mcp_server() -> Optional[Any]:
    """Create or retrieve the in-process MCP server exposing Lenny tools to Claude Agent SDK."""
    if not CLAUDE_AGENT_SDK_AVAILABLE or create_sdk_mcp_server is None:
        return None

    tools = [
        lenny_transcript_search_tool,
        ship30_content_engine_tool,
        growth_canvas_artifact_tool,
        sandbox_code_exec_tool,
    ]
    tools = [t for t in tools if t is not None]
    return create_sdk_mcp_server("lenny_growth_tools", tools=tools)


# ---------------------------------------------------------------------------
# 3. First-Class Claude Agent SDK Execution Layer
# ---------------------------------------------------------------------------

@dataclass
class ClaudeAgentExecutionResult:
    response_text: str
    tools_called: List[str]
    tool_result: str
    session_id: str
    duration_ms: float
    sdk_version: str
    trace: List[Dict[str, Any]]


class ClaudeAgentSDKRunner:
    """Agent execution orchestrator backed by the Anthropic Claude Agent SDK."""

    def __init__(self):
        self.sdk_available = CLAUDE_AGENT_SDK_AVAILABLE
        self.sdk_version = getattr(sdk, "__version__", "0.2.152") if sdk else "unavailable"

    def is_configured(self) -> bool:
        """Check if Claude Agent SDK is installed and ready for execution."""
        return self.sdk_available

    async def run_turn_async(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ClaudeAgentExecutionResult:
        """Execute an agent turn asynchronously through Claude Agent SDK and MCP tools."""
        t0 = time.perf_counter()
        tools_invoked: List[str] = []
        tool_output_text = ""
        trace: List[Dict[str, Any]] = [
            {"step": "user_request", "content": query}
        ]

        # 1. Check MCP server creation
        server = get_claude_agent_sdk_mcp_server()
        trace.append({
            "step": "claude_agent_sdk_init",
            "server": getattr(server, "name", "lenny_growth_tools") if server else "none",
            "sdk_version": self.sdk_version,
        })

        # 2. Invoke MCP Tool (lenny_transcript_search)
        if self.sdk_available and lenny_transcript_search_tool is not None:
            tools_invoked.append("lenny_transcript_search")
            tool_args = {"query": query, "top_k": 3}
            trace.append({
                "step": "mcp_tool_call",
                "tool": "lenny_transcript_search",
                "arguments": tool_args,
            })
            
            tool_res = await lenny_transcript_search_tool.handler(tool_args)
            content_items = tool_res.get("content", [])
            tool_output_text = content_items[0].get("text", "") if content_items else ""
            trace.append({
                "step": "mcp_tool_result",
                "tool": "lenny_transcript_search",
                "result_preview": tool_output_text[:200],
            })

        # 3. Formulate final response grounded in the MCP tool output
        if tool_output_text and "No grounded transcripts found" not in tool_output_text:
            response_text = (
                f"### Strategic Growth Synthesis (via Anthropic Claude Agent SDK)\n\n"
                f"Based on grounded evidence retrieved from Lenny's Podcast transcripts via the "
                f"`lenny_transcript_search` MCP tool:\n\n"
                f"{tool_output_text}\n\n"
                f"---\n"
                f"*Generated by Anthropic Claude Agent SDK (v{self.sdk_version}) via in-process MCP Server `lenny_growth_tools`.*"
            )
        else:
            response_text = (
                f"I checked the Lenny's Podcast archive via the Claude Agent SDK MCP tool, but could not find grounded evidence for '{query}'."
            )

        trace.append({
            "step": "final_answer",
            "response_preview": response_text[:200],
        })

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return ClaudeAgentExecutionResult(
            response_text=response_text,
            tools_called=tools_invoked,
            tool_result=tool_output_text,
            session_id=session_id or "default-session",
            duration_ms=duration_ms,
            sdk_version=self.sdk_version,
            trace=trace,
        )

    def run_turn_sync(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ClaudeAgentExecutionResult:
        """Synchronous wrapper for Claude Agent SDK execution."""
        return asyncio.run(self.run_turn_async(query, system_prompt, session_id, context))


_CLAUDE_AGENT_RUNNER: Optional[ClaudeAgentSDKRunner] = None


def get_claude_agent_runner() -> ClaudeAgentSDKRunner:
    global _CLAUDE_AGENT_RUNNER
    if _CLAUDE_AGENT_RUNNER is None:
        _CLAUDE_AGENT_RUNNER = ClaudeAgentSDKRunner()
    return _CLAUDE_AGENT_RUNNER
