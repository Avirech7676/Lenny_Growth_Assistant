"""Specialized Lenny Podcast & Growth Knowledge Search Tool."""

import time
from typing import Dict, Any, Optional

from app.tools.base import Tool, ToolResult
from app.retrieval.retriever import retrieve_evidence
from app.db.session import get_db_session


class LennySearchTool(Tool):
    name = "lenny_search"
    description = (
        "Query the specialized Lenny's Podcast and Newsletter transcript archive. "
        "Use ONLY when questions explicitly reference Lenny, podcast guests, or podcast frameworks."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic, guest name, or framework to retrieve from the podcast archive.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of transcript excerpts to retrieve (1 to 8).",
                "default": 4,
            },
            "guest": {
                "type": "string",
                "description": "Optional guest filter (e.g., 'Brian Chesky', 'Shreyas Doshi', 'Elena Verna').",
            }
        },
        "required": ["query"],
    }
    timeout_seconds = 10.0

    async def execute(self, query: str, top_k: int = 4, guest: Optional[str] = None, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            with get_db_session() as db:
                result = retrieve_evidence(query=query, db=db, top_k=top_k)

            sources_data = []
            citations_data = []
            formatted_chunks = []

            for ev in result.evidence:
                if guest and guest.lower() not in ev.guest.lower():
                    continue

                sources_data.append({
                    "chunk_id": ev.chunk_id,
                    "guest": ev.guest,
                    "title": ev.title,
                    "similarity": round(ev.similarity, 4),
                    "excerpt": ev.excerpt,
                    "source_type": "transcript",
                })
                citations_data.append({
                    "chunk_id": ev.chunk_id,
                    "guest": ev.guest,
                    "title": ev.title,
                    "similarity": round(ev.similarity, 4),
                    "excerpt": ev.excerpt,
                    "source_type": "transcript",
                })
                formatted_chunks.append(f"[Source: {ev.guest} - {ev.title}]\n{ev.excerpt}")

            duration_ms = (time.perf_counter() - t0) * 1000
            output_text = "\n\n---\n\n".join(formatted_chunks) if formatted_chunks else "No matching transcript excerpts found."

            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"query": query, "top_k": top_k, "guest": guest},
                output=output_text,
                sources=sources_data,
                citations=citations_data,
                metadata={
                    "grounded": result.grounded,
                    "top_similarity": result.top_similarity,
                    "chunks_retrieved": len(sources_data),
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"query": query},
                output="",
                error_message=f"Lenny archive search failed: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
