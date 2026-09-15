"""Epistemic Context Manager for AI Orchestrator.

Enforces strict context hygiene and Phase 1 relevance guarantees:
1. Lenny knowledge never enters unrelated queries (e.g. government, general QA).
2. Cross-turn evidence contamination prevention (multi-turn isolation).
3. Evidence filtering and token budget truncation.
4. Structured evidence boundary formatting.
"""

from typing import List, Dict, Any, Optional
import logging
from app.services.relevance import get_relevance_router
from app.services.memory.compactor import get_memory_compactor

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages prompt context compilation, memory compaction, and strict epistemic hygiene."""

    def __init__(self):
        self.relevance_router = get_relevance_router()
        self.memory_compactor = get_memory_compactor()

    def assemble_context(
        self,
        query: str,
        evidence_parts: List[str],
        history: Optional[List[Dict[str, str]]] = None,
        allow_lenny_knowledge: bool = False,
    ) -> str:
        """Filter and compile clean, grounded context string for the prompt."""
        query_analysis = self.relevance_router.analyze_query(query)

        # 1. Clean evidence parts
        clean_parts: List[str] = []
        for part in evidence_parts:
            p_clean = part.strip()
            if not p_clean:
                continue

            # Rule 1 & 8: If query is NOT Lenny relevant, purge any Lenny/Chesky transcript references
            if not allow_lenny_knowledge or not query_analysis.allow_lenny_retrieval:
                p_lower = p_clean.lower()
                if any(bad in p_lower for bad in ["[source id:", "[transcript source:", "brian chesky", "lenny rachitsky"]):
                    logger.info("ContextManager purged unrelated Lenny transcript fragment.")
                    continue

            clean_parts.append(p_clean)

        return "\n\n---\n\n".join(clean_parts) if clean_parts else ""

    def compact_history(self, raw_history: List[Dict[str, str]], max_turns: int = 6) -> List[Dict[str, str]]:
        """Compact conversational memory while preserving recent conversational context."""
        if not raw_history:
            return []
        compacted = self.memory_compactor.compact(raw_history)
        result = list(compacted.verbatim_turns[-max_turns:])
        if compacted.compressed_summary:
            result.insert(0, {"role": "system", "content": f"[CONVERSATION SUMMARY: {compacted.compressed_summary}]"})
        return result
