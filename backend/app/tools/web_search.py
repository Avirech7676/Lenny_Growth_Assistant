"""Web Search Tool executing multi-source real-world searches with curated knowledge baseline."""

import time
from typing import Dict, Any, Optional
from app.tools.base import Tool, ToolResult
from app.services.search import get_search_router


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search current real-world web sources, official documentation, government records, "
        "and technical registries. Returns verified snippets, citations, and authority scores."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to research in real time."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (1-10).",
                "default": 5,
            },
            "category": {
                "type": "string",
                "description": "Target category (e.g., official, academic, news, technical, government).",
                "enum": ["official", "academic", "news", "technical", "government", "financial", "general"],
            }
        },
        "required": ["query"],
    }
    timeout_seconds = 15.0

    async def execute(self, query: str, max_results: int = 5, category: Optional[str] = None, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            router = get_search_router()
            synthesis = await router.execute_research_async(query, user_mode="search")

            sources_data = []
            for s in synthesis.used_sources[:max_results]:
                sources_data.append({
                    "title": s.title,
                    "url": s.url,
                    "domain": s.domain,
                    "snippet": s.snippet,
                    "authority": s.authority_score,
                    "category": s.category.value if hasattr(s.category, "value") else str(s.category),
                    "why_useful": getattr(s, "why_useful", ""),
                })

            duration_ms = (time.perf_counter() - t0) * 1000
            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"query": query, "max_results": max_results, "category": category},
                output=synthesis.synthesis_context,
                sources=sources_data,
                metadata={
                    "evidence_strength": synthesis.evidence_strength.value if hasattr(synthesis.evidence_strength, "value") else str(synthesis.evidence_strength),
                    "category_breakdown": synthesis.category_counts,
                    "total_discovered": len(synthesis.discovered_sources),
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"query": query},
                output="",
                error_message=f"Search failed: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
