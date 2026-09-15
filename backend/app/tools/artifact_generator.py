"""Artifact Generator Tool for safe visual UI widgets, frameworks, and documents."""

import time
from typing import Dict, Any

from app.tools.base import Tool, ToolResult
from app.utils.sanitize import sanitize_artifact_content


class ArtifactGeneratorTool(Tool):
    name = "artifact_generator"
    description = (
        "Generate a structured visual artifact (interactive HTML widget, table, checklist, "
        "or calculator) rendered in the canvas viewer with sanitization protection."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Human-readable title of the artifact.",
            },
            "artifact_type": {
                "type": "string",
                "enum": ["html", "markdown", "calculator", "checklist", "matrix"],
                "description": "Format/category of the operational artifact.",
                "default": "html",
            },
            "content": {
                "type": "string",
                "description": "HTML or Markdown body of the artifact.",
            },
        },
        "required": ["title", "content"],
    }
    timeout_seconds = 5.0

    async def execute(self, title: str, content: str, artifact_type: str = "html", **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            sanitized = sanitize_artifact_content(content)
            tag_representation = f'<artifact type="{artifact_type}" title="{title}">\n{sanitized}\n</artifact>'
            duration_ms = (time.perf_counter() - t0) * 1000

            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"title": title, "artifact_type": artifact_type},
                output=tag_representation,
                metadata={
                    "title": title,
                    "artifact_type": artifact_type,
                    "raw_length": len(content),
                    "sanitized_length": len(sanitized),
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"title": title},
                output="",
                error_message=f"Artifact sanitization error: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
