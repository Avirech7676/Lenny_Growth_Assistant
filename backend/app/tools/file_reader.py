"""File Read Tool with path traversal defense for inspectable repository files."""

import os
import time
from typing import Dict, Any

from app.tools.base import Tool, ToolResult

# Permitted workspace root directory
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


class FileReadTool(Tool):
    name = "file_read"
    description = (
        "Read contents of a workspace file (code, markdown, text, json, csv). "
        "Enforces strict path traversal defenses to prevent unauthorized system directory access."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative or absolute path to the file within the project workspace.",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum lines of content to read (1 to 500).",
                "default": 200,
            }
        },
        "required": ["file_path"],
    }
    timeout_seconds = 10.0

    async def execute(self, file_path: str, max_lines: int = 200, **kwargs) -> ToolResult:
        t0 = time.perf_counter()

        # Resolve path and verify boundary
        clean_path = os.path.normpath(file_path)
        if not os.path.isabs(clean_path):
            clean_path = os.path.join(WORKSPACE_ROOT, clean_path)

        target_real = os.path.realpath(clean_path)
        workspace_real = os.path.realpath(WORKSPACE_ROOT)

        # Path traversal guard
        if not target_real.startswith(workspace_real):
            return ToolResult(
                tool_name=self.name,
                status="rejected",
                input_params={"file_path": file_path},
                output="",
                error_message="Access denied: Path points outside the allowed project workspace (Path Traversal Defense).",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        if not os.path.exists(target_real):
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"file_path": file_path},
                output="",
                error_message=f"File '{file_path}' does not exist.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        if os.path.isdir(target_real):
            # If directory, return listing of children
            children = os.listdir(target_real)[:100]
            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"file_path": file_path},
                output="\n".join(children),
                metadata={"is_directory": True, "items_count": len(children)},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        try:
            with open(target_real, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)

            duration_ms = (time.perf_counter() - t0) * 1000
            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"file_path": file_path, "max_lines": max_lines},
                output=content,
                metadata={
                    "lines_read": len(lines),
                    "file_size_bytes": os.path.getsize(target_real),
                    "canonical_path": target_real,
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"file_path": file_path},
                output="",
                error_message=f"Could not read file: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
