"""Tests for Unified Tool Architecture, Security Defenses, and Tool Router.

Validates WebSearch, WebFetch, CodeExecution, FileRead, Calculator, LennySearch, and ArtifactGenerator tools.
"""

import sys
import os
import pytest
import asyncio
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.tools import (
    Tool,
    ToolResult,
    WebSearchTool,
    WebFetchTool,
    CodeExecutionTool,
    FileReadTool,
    CalculatorTool,
    LennySearchTool,
    ArtifactGeneratorTool,
    ToolRouter,
    get_tool_router,
)

client = TestClient(app)


def test_tool_router_initialization_and_specs():
    """Verify ToolRouter registers all 7 platform tools and generates provider specs."""
    router = get_tool_router()
    tools = router.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "web_search",
        "web_fetch",
        "code_execution",
        "file_read",
        "calculator",
        "lenny_search",
        "artifact_generator",
    }
    assert expected_tools.issubset(tool_names)

    # Verify OpenAI / Groq tool declarations
    openai_specs = router.get_tool_specs(format="openai")
    assert len(openai_specs) >= 7
    calc_spec = next(s for s in openai_specs if s["function"]["name"] == "calculator")
    assert "expression" in calc_spec["function"]["parameters"]["properties"]

    # Verify Anthropic tool declarations
    claude_specs = router.get_tool_specs(format="anthropic")
    assert len(claude_specs) >= 7
    code_spec = next(s for s in claude_specs if s["name"] == "code_execution")
    assert "code" in code_spec["input_schema"]["properties"]

    # Verify Gemini tool declarations
    gemini_specs = router.get_tool_specs(format="gemini")
    assert len(gemini_specs) >= 7


@pytest.mark.asyncio
async def test_calculator_tool_operations():
    """Verify safe arithmetic, percentages, and business metrics evaluation."""
    router = get_tool_router()

    # 1. Standard Arithmetic
    res1 = await router.execute("calculator", {"expression": "(100 * 25) / 5 + 50"})
    assert res1.is_success
    assert res1.output == 550.0

    # 2. Growth Business Metric: ICE Score
    res2 = await router.execute("calculator", {"expression": "ice(9, 8, 7)"})
    assert res2.is_success
    assert res2.output == 8.0

    # 3. Growth Business Metric: CAC Payback Months
    res3 = await router.execute("calculator", {"expression": "cac_payback(6000, 500, 80)"})
    assert res3.is_success
    assert res3.output == 15.0

    # 4. Rejection of arbitrary code execution
    res4 = await router.execute("calculator", {"expression": "__import__('os').system('ls')"})
    assert not res4.is_success
    assert "error" in res4.status.lower()


@pytest.mark.asyncio
async def test_code_execution_sandbox():
    """Verify Python code runner captures output and blocks forbidden system calls."""
    router = get_tool_router()

    # 1. Valid algorithmic execution
    snippet = (
        "def fib(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
        "print('FIB:', fib(7))\n"
    )
    res = await router.execute("code_execution", {"code": snippet, "timeout_seconds": 5})
    assert res.is_success
    assert "FIB: 13" in str(res.output)
    assert res.duration_ms > 0

    # 2. Security violation rejection (forbidden imports)
    malicious_code = "import ctypes\nctypes.string_at(0)"
    res_bad = await router.execute("code_execution", {"code": malicious_code})
    assert res_bad.status == "rejected"
    assert "prohibited" in res_bad.error_message.lower()


@pytest.mark.asyncio
async def test_file_read_tool_and_path_traversal():
    """Verify FileReadTool enforces strict boundaries against path traversal."""
    router = get_tool_router()

    # 1. Valid workspace file read
    res_valid = await router.execute("file_read", {"file_path": "pyrightconfig.json"})
    assert res_valid.is_success
    assert "include" in res_valid.output

    # 2. Directory listing
    res_dir = await router.execute("file_read", {"file_path": "backend"})
    assert res_dir.is_success
    assert "app" in res_dir.output

    # 3. Path traversal attack attempt
    res_traversal = await router.execute("file_read", {"file_path": "../../../../../etc/passwd"})
    assert res_traversal.status in ("rejected", "error")
    assert "denied" in str(res_traversal.error_message).lower() or "not exist" in str(res_traversal.error_message).lower()


@pytest.mark.asyncio
async def test_web_fetch_ssrf_protection():
    """Verify WebFetchTool defends against SSRF attacks on private networks."""
    router = get_tool_router()

    # 1. Loopback attack
    res_loopback = await router.execute("web_fetch", {"url": "http://127.0.0.1:8000/api/models"})
    assert res_loopback.status == "rejected"
    assert "SSRF Defense" in res_loopback.error_message

    # 2. Cloud metadata attack
    res_meta = await router.execute("web_fetch", {"url": "http://169.254.169.254/latest/meta-data"})
    assert res_meta.status == "rejected"
    assert "SSRF Defense" in res_meta.error_message

    # 3. Invalid scheme
    res_file = await router.execute("web_fetch", {"url": "file:///etc/passwd"})
    assert res_file.status == "rejected"


@pytest.mark.asyncio
async def test_web_search_tool():
    """Verify WebSearchTool returns rich sources and evidence strength."""
    from unittest.mock import patch
    from app.services.search.base import DiscoveredSource, SourceCategory, ResearchSynthesis, EvidenceStrength
    router = get_tool_router()
    sample_source = DiscoveredSource(
        title="Nara Chandrababu Naidu - Chief Minister of Andhra Pradesh",
        url="https://ap.gov.in/cm",
        domain="ap.gov.in",
        snippet="Nara Chandrababu Naidu serves as the Chief Minister of Andhra Pradesh.",
        category=SourceCategory.GOVERNMENT,
        authority_score=0.98,
    )
    with patch("app.services.search.router.SearchRouter.execute_research_async", return_value=ResearchSynthesis(
        query="Who is CM of AP",
        plan=None,
        discovered_sources=[sample_source],
        used_sources=[sample_source],
        category_counts={"Government": 1},
        evidence_strength=EvidenceStrength.STRONG,
        conflicts=[],
        synthesis_context="Nara Chandrababu Naidu is the Chief Minister of Andhra Pradesh.",
        latency_ms=10.0,
    )):
        res = await router.execute("web_search", {"query": "Who is CM of AP", "max_results": 4})
        assert res.is_success
        assert len(res.sources) > 0
        assert any("chandrababu" in s["title"].lower() or "naidu" in s["title"].lower() or "andhra" in s["title"].lower() for s in res.sources)


@pytest.mark.asyncio
async def test_lenny_search_tool():
    """Verify LennySearchTool queries transcript archives with guest filtering."""
    router = get_tool_router()
    res = await router.execute("lenny_search", {"query": "founder mode orchestra", "top_k": 3})
    assert res.is_success
    assert len(res.sources) > 0
    assert any("chesky" in s["guest"].lower() for s in res.sources)


@pytest.mark.asyncio
async def test_artifact_generator_tool():
    """Verify ArtifactGeneratorTool sanitizes and wraps content."""
    router = get_tool_router()
    malicious = "<div class='card'>Card Content<script>alert('xss')</script></div>"
    res = await router.execute("artifact_generator", {"title": "Test Card", "content": malicious, "artifact_type": "html"})
    assert res.is_success
    assert "<script>" not in res.output
    assert "Test Card" in res.output


def test_api_tools_endpoint():
    """Verify GET /api/tools returns all registered tools."""
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert data["count"] >= 7
    tool_names = [t["name"] for t in data["tools"]]
    assert "calculator" in tool_names
    assert "code_execution" in tool_names
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
