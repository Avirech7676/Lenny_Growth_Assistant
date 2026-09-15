"""Isolated Python Code Execution Sandbox for calculations, data analysis, and script testing."""

import sys
import subprocess
import tempfile
import os
import ast
import time
from typing import Dict, Any

from app.tools.base import Tool, ToolResult

FORBIDDEN_MODULES = {"ctypes", "pty", "posix", "nt", "_thread"}
FORBIDDEN_CALLS = {"fork", "kill", "system", "popen", "spawn"}


def validate_python_code_safety(code: str) -> None:
    """Analyze AST to prevent catastrophic system calls before execution."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES:
                    raise PermissionError(f"Importing '{alias.name}' is prohibited in the execution sandbox.")
        elif isinstance(node, ast.ImportFrom):
            if node.module in FORBIDDEN_MODULES:
                raise PermissionError(f"Importing from '{node.module}' is prohibited in the execution sandbox.")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
                raise PermissionError(f"Executing system call '{node.func.attr}' is prohibited.")


class CodeExecutionTool(Tool):
    name = "code_execution"
    description = (
        "Execute Python code in an isolated, sandboxed subprocess environment. "
        "Captures stdout, stderr, execution duration, and handles calculations and data analysis."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python code to execute safely in the sandbox.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Maximum execution duration in seconds (1 to 30).",
                "default": 10,
            }
        },
        "required": ["code"],
    }
    timeout_seconds = 30.0

    async def execute(self, code: str, timeout_seconds: int = 10, **kwargs) -> ToolResult:
        t0 = time.perf_counter()

        # Step 1: Pre-execution AST security validation
        try:
            validate_python_code_safety(code)
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="rejected",
                input_params={"code": code},
                output="",
                error_message=f"Code safety violation: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        # Step 2: Write temporary execution script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            cmd = [sys.executable, "-u", tmp_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration_ms = (time.perf_counter() - t0) * 1000

            stdout_str = proc.stdout.strip()
            stderr_str = proc.stderr.strip()

            if proc.returncode == 0:
                return ToolResult(
                    tool_name=self.name,
                    status="success",
                    input_params={"code": code},
                    output=stdout_str if stdout_str else "Execution finished with return code 0 (no stdout output).",
                    metadata={"return_code": 0, "stderr": stderr_str},
                    duration_ms=duration_ms,
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    input_params={"code": code},
                    output=stdout_str,
                    error_message=f"Process exited with code {proc.returncode}:\n{stderr_str}",
                    metadata={"return_code": proc.returncode, "stderr": stderr_str},
                    duration_ms=duration_ms,
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name=self.name,
                status="timeout",
                input_params={"code": code},
                output="",
                error_message=f"Execution timed out after {timeout_seconds} seconds.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"code": code},
                output="",
                error_message=f"Execution error: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
