"""Conversational Memory Compactor.

Implements sliding-window context management with token budgeting:
- Keeps recent N turns verbatim
- Extracts key facts and decisions from older turns
- Purges low-signal chit-chat noise
- Preserves code blocks and artifacts in a structured summary
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Token estimation: ~4 chars per token (approximation safe for all models)
CHARS_PER_TOKEN = 4

# Budget constants
DEFAULT_VERBATIM_TURNS = 6          # Keep last N turns verbatim
DEFAULT_MAX_CONTEXT_TOKENS = 6000   # Max context tokens passed to LLM
DEFAULT_SUMMARY_MAX_TOKENS = 1200   # Max tokens for compressed older history


@dataclass
class ExtractedFact:
    """A key fact, decision, or important piece of context extracted from conversation history."""
    fact: str
    source_turn: int
    category: str  # 'decision', 'fact', 'preference', 'code', 'error', 'plan'
    confidence: float = 1.0


@dataclass
class CompactedContext:
    """Result of context compaction: verbatim recent turns + compressed older summary."""
    verbatim_turns: List[Dict[str, str]]         # Recent turns, full content
    extracted_facts: List[ExtractedFact]          # Key facts from older turns
    compressed_summary: str                       # Prose summary of older history
    total_turns_processed: int
    verbatim_token_estimate: int
    summary_token_estimate: int
    was_compacted: bool                           # True if old context was compressed


class MemoryCompactor:
    """Sliding-window context compactor for production-grade conversation history management."""

    def __init__(
        self,
        verbatim_turns: int = DEFAULT_VERBATIM_TURNS,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        summary_max_tokens: int = DEFAULT_SUMMARY_MAX_TOKENS,
    ):
        self.verbatim_turns = verbatim_turns
        self.max_context_tokens = max_context_tokens
        self.summary_max_tokens = summary_max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Fast token estimation using character count heuristic."""
        return max(1, len(text) // CHARS_PER_TOKEN)

    def compact(self, history: List[Dict[str, str]]) -> CompactedContext:
        """Compact conversation history: keep recent verbatim, summarize older turns.

        Args:
            history: List of {'role': str, 'content': str} message dicts, oldest first.

        Returns:
            CompactedContext with verbatim recent turns and compressed older history.
        """
        if not history:
            return CompactedContext(
                verbatim_turns=[],
                extracted_facts=[],
                compressed_summary="",
                total_turns_processed=0,
                verbatim_token_estimate=0,
                summary_token_estimate=0,
                was_compacted=False,
            )

        total = len(history)

        # If history fits within verbatim_turns limit, no compaction needed
        if total <= self.verbatim_turns:
            verbatim = history
            total_tokens = sum(self.estimate_tokens(m["content"]) for m in verbatim)
            return CompactedContext(
                verbatim_turns=verbatim,
                extracted_facts=[],
                compressed_summary="",
                total_turns_processed=total,
                verbatim_token_estimate=total_tokens,
                summary_token_estimate=0,
                was_compacted=False,
            )

        # Split: recent (verbatim) + older (compress)
        older_turns = history[:-self.verbatim_turns]
        recent_turns = history[-self.verbatim_turns:]

        # Extract key facts from older turns
        facts = self._extract_key_facts(older_turns)

        # Build compressed summary prose
        compressed_summary = self._build_summary(older_turns, facts)

        # Token estimates
        verbatim_tokens = sum(self.estimate_tokens(m["content"]) for m in recent_turns)
        summary_tokens = self.estimate_tokens(compressed_summary)

        # If verbatim recent turns alone exceed budget, trim from oldest-recent first
        while verbatim_tokens > self.max_context_tokens and len(recent_turns) > 2:
            removed = recent_turns.pop(0)
            verbatim_tokens -= self.estimate_tokens(removed["content"])
            # Add removed turn's content to facts
            extra_facts = self._extract_key_facts([removed])
            facts.extend(extra_facts)

        return CompactedContext(
            verbatim_turns=recent_turns,
            extracted_facts=facts,
            compressed_summary=compressed_summary,
            total_turns_processed=total,
            verbatim_token_estimate=verbatim_tokens,
            summary_token_estimate=summary_tokens,
            was_compacted=True,
        )

    def _extract_key_facts(self, turns: List[Dict[str, str]]) -> List[ExtractedFact]:
        """Extract key facts, decisions, and important content from a turn sequence."""
        facts: List[ExtractedFact] = []

        for i, msg in enumerate(turns):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content or len(content) < 15:
                continue

            # Skip pure chit-chat / trivial acknowledgements
            if self._is_chit_chat(content):
                continue

            # Extract code blocks as high-priority facts
            code_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)
            for cb in code_blocks[:2]:  # max 2 code blocks per turn
                if len(cb.strip()) > 30:
                    facts.append(ExtractedFact(
                        fact=f"CODE: {cb.strip()[:200]}...",
                        source_turn=i,
                        category="code",
                        confidence=1.0,
                    ))

            # Extract decisions and conclusions
            decision_patterns = [
                r'(?:I will|I\'ll|let\'s|we should|the plan is|decided to|going to)\s+([^.!?\n]{20,120})',
                r'(?:confirmed:|conclusion:|result:|decided:|agreed:)\s*([^.\n]{20,120})',
            ]
            for pat in decision_patterns:
                matches = re.findall(pat, content, re.IGNORECASE)
                for m in matches[:2]:
                    facts.append(ExtractedFact(
                        fact=m.strip(),
                        source_turn=i,
                        category="decision",
                        confidence=0.9,
                    ))

            # Extract errors and issues raised
            error_patterns = [
                r'(?:error|exception|failed|bug|issue|problem)[\s:]+([^\n.]{20,120})',
            ]
            for pat in error_patterns:
                matches = re.findall(pat, content, re.IGNORECASE)
                for m in matches[:1]:
                    facts.append(ExtractedFact(
                        fact=f"ERROR: {m.strip()}",
                        source_turn=i,
                        category="error",
                        confidence=0.85,
                    ))

            # Extract file paths and technical details from assistant responses
            if role == "assistant":
                path_matches = re.findall(r'[a-zA-Z]:\\[\w\\\/\-\.]+\.\w+|/[\w/\-\.]+\.\w+', content)
                for p in path_matches[:3]:
                    facts.append(ExtractedFact(
                        fact=f"FILE: {p}",
                        source_turn=i,
                        category="fact",
                        confidence=0.8,
                    ))

        # Deduplicate facts by text similarity (simple substring check)
        deduped: List[ExtractedFact] = []
        seen: List[str] = []
        for f in facts:
            normalized = f.fact[:60].lower()
            if not any(normalized in s or s in normalized for s in seen):
                deduped.append(f)
                seen.append(normalized)

        return deduped[:20]  # cap at 20 facts

    def _build_summary(self, older_turns: List[Dict[str, str]], facts: List[ExtractedFact]) -> str:
        """Build a compressed prose summary of older conversation turns."""
        if not older_turns:
            return ""

        lines = []

        # Count turn types
        user_turns = [m for m in older_turns if m.get("role") == "user"]
        assistant_turns = [m for m in older_turns if m.get("role") == "assistant"]

        lines.append(
            f"[CONVERSATION HISTORY SUMMARY — {len(older_turns)} earlier turns, "
            f"{len(user_turns)} user messages, {len(assistant_turns)} assistant responses]"
        )

        # Add first user message as topic context
        if user_turns:
            first_q = user_turns[0]["content"][:150].strip()
            lines.append(f"Initial topic: {first_q}")

        # Add extracted facts grouped by category
        if facts:
            by_cat: Dict[str, List[str]] = {}
            for f in facts:
                by_cat.setdefault(f.category, []).append(f.fact)

            if by_cat.get("decision"):
                lines.append("Key decisions made: " + "; ".join(by_cat["decision"][:4]))
            if by_cat.get("error"):
                lines.append("Errors encountered: " + "; ".join(by_cat["error"][:3]))
            if by_cat.get("fact"):
                lines.append("Key files/references: " + "; ".join(by_cat["fact"][:4]))
            if by_cat.get("code"):
                lines.append(f"Code was discussed ({len(by_cat['code'])} snippet(s))")

        return "\n".join(lines)

    def _is_chit_chat(self, content: str) -> bool:
        """Detect low-signal chit-chat messages that can be safely pruned."""
        stripped = content.strip().lower()
        if len(stripped) < 20:
            return True  # Very short messages are almost always chit-chat

        chit_chat_patterns = [
            r'^(ok|okay|yes|no|sure|thanks|thank you|got it|understood|great|perfect|alright|cool|nice)[\s.!]*$',
            r'^(continue|go ahead|proceed|sounds good|looks good|that\'s right|correct)[\s.!]*$',
            r'^(hi|hello|hey|howdy|good morning|good afternoon|good evening)[\s.!]*$',
        ]
        for pat in chit_chat_patterns:
            if re.match(pat, stripped):
                return True
        return False

    def build_llm_history(self, compacted: CompactedContext) -> List[Dict[str, str]]:
        """Build final history list suitable for LLM input from CompactedContext.

        Prepends a system-summary message if compaction occurred, then returns verbatim recent turns.
        """
        result: List[Dict[str, str]] = []

        if compacted.was_compacted and compacted.compressed_summary:
            result.append({
                "role": "system",
                "content": compacted.compressed_summary,
            })

        result.extend(compacted.verbatim_turns)
        return result


# ─── Singleton ────────────────────────────────────────────────────────────────
_COMPACTOR = MemoryCompactor()


def get_memory_compactor() -> MemoryCompactor:
    """Access the singleton MemoryCompactor."""
    return _COMPACTOR
