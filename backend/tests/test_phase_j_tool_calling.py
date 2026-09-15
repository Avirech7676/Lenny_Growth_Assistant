"""Phase J Test Suite: Cross-Provider Tool Calling Execution.

Validates:
1. Unified ToolDefinition schema converters (OpenAI, Gemini, Anthropic).
2. ToolCall and ToolResult normalization across formats.
3. ToolRegistry registration, lookups, and multi-format spec generation.
4. Epistemic sandbox and calculator tool execution.
5. Cross-provider tool call handling and execution synthesis.
"""

import sys
import os
import json
import pytest

# Ensure backend root is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.tools import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    ToolRegistry,
    get_tool_registry,
    to_openai_tools,
    to_gemini_tools,
    to_anthropic_tools,
)
from app.models.base import LLMRequest, LLMResponse
from app.models.provider import LLMProvider, FallbackGroundedProvider


def test_tool_definition_specs():
    """Test canonical ToolDefinition transforms to OpenAI, Gemini, and Anthropic schemas."""
    tool = ToolDefinition(
        name="unit_converter",
        description="Converts units of measurement.",
        parameters={
            "type": "object",
            "properties": {
                "val": {"type": "number", "description": "Numeric value"},
                "unit": {"type": "string", "enum": ["m", "ft", "km", "mi"]},
            },
            "required": ["val", "unit"],
        },
    )

    # OpenAI format
    openai_spec = tool.to_openai_spec()
    assert openai_spec["type"] == "function"
    assert openai_spec["function"]["name"] == "unit_converter"
    assert openai_spec["function"]["description"] == "Converts units of measurement."
    assert "properties" in openai_spec["function"]["parameters"]

    # Gemini format
    gemini_spec = tool.to_gemini_spec()
    assert gemini_spec["name"] == "unit_converter"
    assert gemini_spec["description"] == "Converts units of measurement."
    assert "properties" in gemini_spec["parameters"]

    # Anthropic format
    anthropic_spec = tool.to_anthropic_spec()
    assert anthropic_spec["name"] == "unit_converter"
    assert anthropic_spec["description"] == "Converts units of measurement."
    assert "properties" in anthropic_spec["input_schema"]


def test_tool_call_normalization():
    """Test ToolCall parsing from diverse provider response schemas."""
    # 1. OpenAI format
    raw_openai = {
        "id": "call_abc123",
        "type": "function",
        "function": {
            "name": "calculator",
            "arguments": '{"expression": "40 + 2"}',
        },
    }
    tc1 = ToolCall.from_dict(raw_openai)
    assert tc1.id == "call_abc123"
    assert tc1.name == "calculator"
    assert tc1.arguments == {"expression": "40 + 2"}

    # 2. Direct format (Gemini / Anthropic / internal)
    raw_direct = {
        "id": "call_xyz789",
        "name": "python_sandbox",
        "arguments": {"code": "print('hello')"},
    }
    tc2 = ToolCall.from_dict(raw_direct)
    assert tc2.id == "call_xyz789"
    assert tc2.name == "python_sandbox"
    assert tc2.arguments == {"code": "print('hello')"}

    # 3. Serialization to standard dict
    d2 = tc2.to_dict()
    assert d2["id"] == "call_xyz789"
    assert d2["function"]["name"] == "python_sandbox"
    assert json.loads(d2["function"]["arguments"]) == {"code": "print('hello')"}
    assert d2["name"] == "python_sandbox"


def test_tool_result_contract():
    """Test ToolResult status, dictionary serialization, and string formatting."""
    res_success = ToolResult(
        tool_name="calculator",
        status="success",
        output=42.0,
        call_id="call_1",
        input_params={"expression": "6 * 7"},
        duration_ms=1.25,
    )
    assert res_success.is_success is True
    assert res_success.to_content_str() == "42.0"
    dict_res = res_success.to_dict()
    assert dict_res["tool_name"] == "calculator"
    assert dict_res["status"] == "success"
    assert dict_res["output"] == 42.0

    res_err = ToolResult(
        tool_name="calculator",
        status="error",
        error_message="Division by zero",
        call_id="call_2",
    )
    assert res_err.is_success is False
    assert "Division by zero" in res_err.to_content_str()


def test_tool_registry_defaults_and_custom_registration():
    """Test ToolRegistry initializes with default tools and supports custom tools."""
    reg = ToolRegistry()
    tools = [t.name for t in reg.list_tools()]

    # Verify core tools are registered
    assert "calculator" in tools
    assert "python_sandbox" in tools
    assert "code_execution" in tools
    assert "web_search" in tools
    assert "transcript_search" in tools
    assert "lenny_search" in tools

    # Test custom tool registration
    custom_tool = ToolDefinition(
        name="custom_echo",
        description="Echoes input",
        parameters={"type": "object", "properties": {"msg": {"type": "string"}}},
        handler=lambda msg: f"Echo: {msg}",
    )
    reg.register(custom_tool)
    assert reg.get("custom_echo") is not None

    # Test multi-provider spec generation
    openai_specs = reg.get_specs("openai")
    gemini_specs = reg.get_specs("gemini")
    anthropic_specs = reg.get_specs("anthropic")

    assert len(openai_specs) == len(reg.list_tools())
    assert all("function" in s for s in openai_specs)
    assert all("parameters" in s for s in gemini_specs)
    assert all("input_schema" in s for s in anthropic_specs)


def test_tool_execution_calculator():
    """Test executing calculator expressions through ToolRegistry."""
    reg = get_tool_registry()
    result = reg.execute("calculator", {"expression": "2 ** 8 + 10"})
    assert result.is_success is True
    assert result.output == 266.0

    # Test growth metrics (CAGR formula: cagr(100, 200, 2))
    result_cagr = reg.execute("calculator", {"expression": "cagr(100, 200, 2)"})
    assert result_cagr.is_success is True
    assert round(result_cagr.output, 4) == round((2 ** 0.5) - 1, 4)


def test_tool_execution_python_sandbox():
    """Test executing sandboxed python code through ToolRegistry."""
    reg = get_tool_registry()
    result = reg.execute("python_sandbox", {"code": "print('SANDBOX_ACTIVE_123')"})
    assert result.is_success is True
    assert "SANDBOX_ACTIVE_123" in str(result.output)

    # Test security violation is rejected
    result_unsafe = reg.execute("python_sandbox", {"code": "import ctypes\nctypes.string_at(0)"})
    assert result_unsafe.status == "rejected"
    assert "prohibited" in str(result_unsafe.error_message).lower()


def test_schema_converter_functions():
    """Test to_openai_tools, to_gemini_tools, and to_anthropic_tools helpers."""
    raw_tools = [
        ToolDefinition(name="tool_a", description="A", parameters={"type": "object"}),
        {"name": "tool_b", "description": "B", "parameters": {"type": "object"}},
        {"type": "function", "function": {"name": "tool_c", "description": "C", "parameters": {"type": "object"}}},
    ]

    openai_converted = to_openai_tools(raw_tools)
    assert len(openai_converted) == 3
    assert all(t.get("type") == "function" for t in openai_converted)

    gemini_converted = to_gemini_tools(raw_tools)
    assert len(gemini_converted) == 3
    assert all("name" in t and "parameters" in t for t in gemini_converted)

    anthropic_converted = to_anthropic_tools(raw_tools)
    assert len(anthropic_converted) == 3
    assert all("name" in t and "input_schema" in t for t in anthropic_converted)


def test_orchestrator_tool_loop_mock():
    """Test tool execution loop in orchestrator with a mock tool-calling provider."""
    class MockToolProvider(LLMProvider):
        def __init__(self):
            self.calls = 0

        def get_model_name(self) -> str:
            return "mock-tool-model"

        def health_check(self):
            return {"status": "HEALTHY", "healthy": True}

        def generate(self, request=None, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                # First turn: returns tool call request
                return LLMResponse(
                    content="",
                    model=self.get_model_name(),
                    provider="mock",
                    tool_calls=[{
                        "id": "call_calc_1",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": json.dumps({"expression": "150 * 3"}),
                        },
                    }],
                )
            # Second turn: receives tool output and returns final synthesis
            return LLMResponse(
                content="The calculated total is 450.",
                model=self.get_model_name(),
                provider="mock",
            )

        def generate_stream(self, *args, **kwargs):
            yield "The calculated total is 450."

    provider = MockToolProvider()
    req = LLMRequest(prompt="What is 150 * 3?")
    first_res = provider.generate(req)

    assert first_res.tool_calls is not None
    assert len(first_res.tool_calls) == 1

    reg = get_tool_registry()
    tool_outputs = []
    for tc in first_res.tool_calls:
        call = ToolCall.from_dict(tc)
        res = reg.execute(call.name, call.arguments, call_id=call.id)
        assert res.is_success is True
        assert res.output == 450.0
        tool_outputs.append(f"Tool `{call.name}` output: {res.to_content_str()}")

    synth_prompt = f"{req.prompt}\n\n[TOOL RESULTS]:\n" + "\n".join(tool_outputs)
    final_res = provider.generate(LLMRequest(prompt=synth_prompt))
    assert "450" in final_res.content
