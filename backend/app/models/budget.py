"""Proactive Dynamic Context Window Adaptation and Token Budgeting Engine.

Prevents context length exceeded errors across multi-provider models by:
1. Accurately estimating prompt token consumption across segments.
2. Looking up model-specific context window constraints.
3. Dynamically allocating token budgets across system instructions, user queries,
   retrieved evidence context, conversation history, and generation reserve.
4. Applying priority-based sliding window compaction when budgets are exceeded.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

# Calibrated provider & model family default context windows
DEFAULT_CONTEXT_WINDOWS: Dict[str, int] = {
    # Gemini
    "gemini": 1000000,
    "gemini-3.5-flash": 1000000,
    "gemini-3.1-flash-lite-preview": 1000000,
    "gemini-3.6-flash": 1000000,
    "gemini-flash-latest": 1000000,
    "gemini-2.5-flash": 1000000,
    "gemini-1.5-pro": 2000000,
    # Anthropic
    "anthropic": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-opus-20240229": 200000,
    # OpenAI
    "openai": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "o1": 200000,
    "o3-mini": 200000,
    # Groq
    "groq": 128000,
    "llama-3.3-70b-versatile": 128000,
    "llama-3.1-8b-instant": 128000,
    "mixtral-8x7b-32768": 32768,
    # Ollama / Local Small Models
    "ollama": 8192,
    "llama3.2:latest": 8192,
    "llama3.1": 8192,
    "mistral": 8192,
    "phi3": 4096,
    "qwen2.5-coder": 32768,
    # Fallback
    "fallback": 4096,
    "grounded-synthesizer-v2": 4096,
}


def estimate_tokens(text: Optional[str]) -> int:
    """Fast, accurate token estimation using character/word heuristics with special token margin."""
    if not text or not text.strip():
        return 0
    words = len(text.split())
    chars = len(text)
    # Average ~4 characters per token, ~1.3 tokens per word, plus 4 overhead tokens
    return max(1, chars // 4, int(words * 1.3)) + 4


@dataclass
class ContextBudget:
    """Detailed breakdown of token allocation across prompt segments."""
    max_context_window: int
    reserved_output_tokens: int
    max_input_tokens: int
    system_prompt_tokens: int = 0
    user_prompt_tokens: int = 0
    context_tokens: int = 0
    history_tokens: int = 0
    total_input_tokens: int = 0
    available_tokens: int = 0
    is_truncated: bool = False
    truncation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_context_window": self.max_context_window,
            "reserved_output_tokens": self.reserved_output_tokens,
            "max_input_tokens": self.max_input_tokens,
            "system_prompt_tokens": self.system_prompt_tokens,
            "user_prompt_tokens": self.user_prompt_tokens,
            "context_tokens": self.context_tokens,
            "history_tokens": self.history_tokens,
            "total_input_tokens": self.total_input_tokens,
            "available_tokens": self.available_tokens,
            "is_truncated": self.is_truncated,
            "truncation_reason": self.truncation_reason,
        }


class TokenBudgetManager:
    """Manages context window quotas, token budgets, and priority-preserving compaction."""

    def __init__(self):
        self._custom_limits: Dict[str, int] = {}

    def set_custom_limit(self, model_or_provider: str, context_window: int) -> None:
        """Override context window limit for testing or custom deployments."""
        self._custom_limits[model_or_provider.lower().strip()] = context_window

    def get_model_context_window(self, model_id: Optional[str] = None, provider: Optional[str] = None) -> int:
        """Resolve maximum context window from custom limits, ModelRegistry, or calibrated defaults."""
        m_key = (model_id or "").lower().strip()
        p_key = (provider or "").lower().strip()

        # 1. Custom overrides
        if m_key in self._custom_limits:
            return self._custom_limits[m_key]
        if p_key in self._custom_limits:
            return self._custom_limits[p_key]

        # 2. Query ModelRegistry if available
        try:
            from app.models.registry import get_model_registry
            reg = get_model_registry()
            meta = reg.get_model(model_id) if model_id else None
            if meta and meta.context_window > 0:
                return meta.context_window
        except Exception:
            pass

        # 3. Direct model matching in defaults
        if m_key in DEFAULT_CONTEXT_WINDOWS:
            return DEFAULT_CONTEXT_WINDOWS[m_key]

        # 4. Partial substring match in defaults
        for k, v in DEFAULT_CONTEXT_WINDOWS.items():
            if k in m_key:
                return v

        # 5. Provider-level default
        if p_key in DEFAULT_CONTEXT_WINDOWS:
            return DEFAULT_CONTEXT_WINDOWS[p_key]

        # 6. Global conservative default
        return 8192

    def compute_budget(
        self,
        request: Any,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
    ) -> ContextBudget:
        """Calculate complete token budget breakdown for a given request and target model."""
        max_context = self.get_model_context_window(model_id, provider)

        # Output reserve: explicit request override, max_output_tokens arg, or 25% of context capped at 4096
        req_max = getattr(request, "max_tokens", None)
        reserved_output = max_output_tokens or req_max or min(4096, max(256, max_context // 4))

        # Max input capacity leaving headroom for output
        max_input = max(256, max_context - reserved_output)

        sys_tokens = estimate_tokens(getattr(request, "system_prompt", None))
        usr_tokens = estimate_tokens(getattr(request, "prompt", None))
        ctx_tokens = estimate_tokens(getattr(request, "context", None))

        hist_tokens = 0
        history = getattr(request, "history", []) or []
        for msg in history:
            hist_tokens += estimate_tokens(msg.get("content", ""))

        total_input = sys_tokens + usr_tokens + ctx_tokens + hist_tokens
        avail = max(0, max_input - total_input)

        return ContextBudget(
            max_context_window=max_context,
            reserved_output_tokens=reserved_output,
            max_input_tokens=max_input,
            system_prompt_tokens=sys_tokens,
            user_prompt_tokens=usr_tokens,
            context_tokens=ctx_tokens,
            history_tokens=hist_tokens,
            total_input_tokens=total_input,
            available_tokens=avail,
            is_truncated=(total_input > max_input),
        )

    def fit_request(
        self,
        request: Any,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Tuple[Any, ContextBudget]:
        """Ensure LLMRequest fits within the model's context window.

        Priority Preservation Rules:
        1. System Prompt & Current User Prompt are IMMUTABLE and preserved in full.
        2. If total tokens exceed input budget, conversation history is pruned first
           using a sliding window (retaining most recent messages).
        3. If still exceeding, evidence context snippets are gracefully trimmed
           from the end, preserving primary insights and citations.
        """
        budget = self.compute_budget(request, model_id, provider)

        if not budget.is_truncated:
            return request, budget

        # Budget exceeded - apply priority compaction
        import copy
        fitted_req = copy.copy(request)
        reasons: List[str] = []

        max_input = budget.max_input_tokens
        base_tokens = budget.system_prompt_tokens + budget.user_prompt_tokens

        # Check edge case: even system + user prompt exceeds input budget
        if base_tokens >= max_input:
            fitted_req.history = []
            fitted_req.context = ""
            reasons.append("Extreme token pressure: cleared history and context to protect user query.")
            final_budget = self.compute_budget(fitted_req, model_id, provider)
            final_budget.is_truncated = True
            final_budget.truncation_reason = "; ".join(reasons)
            return fitted_req, final_budget

        remaining_for_hist_and_ctx = max_input - base_tokens

        # Step 1: Compact conversation history (Sliding window keeping newest turns)
        history = list(getattr(request, "history", []) or [])
        fitted_history: List[Dict[str, str]] = []
        curr_hist_tokens = 0
        # Allocate up to 30% of remaining for history if context is also present
        has_context = bool(getattr(request, "context", None) and str(request.context).strip())
        history_allowance = int(remaining_for_hist_and_ctx * 0.3) if has_context else remaining_for_hist_and_ctx

        # Traverse backwards from newest to oldest
        for msg in reversed(history):
            m_tokens = estimate_tokens(msg.get("content", ""))
            if curr_hist_tokens + m_tokens <= history_allowance:
                fitted_history.insert(0, msg)
                curr_hist_tokens += m_tokens
            else:
                break

        if len(fitted_history) < len(history):
            pruned_count = len(history) - len(fitted_history)
            reasons.append(f"Pruned {pruned_count} older history turns via sliding window")

        fitted_req.history = fitted_history

        # Step 2: Fit evidence context
        context_str = getattr(request, "context", "") or ""
        remaining_for_ctx = max(0, remaining_for_hist_and_ctx - curr_hist_tokens)
        ctx_tokens = estimate_tokens(context_str)

        if ctx_tokens > remaining_for_ctx:
            # Context needs trimming
            # Break by paragraphs or chunks
            chunks = context_str.split("\n\n")
            fitted_chunks: List[str] = []
            running_ctx_tokens = 0

            for c in chunks:
                c_tok = estimate_tokens(c)
                if running_ctx_tokens + c_tok <= remaining_for_ctx:
                    fitted_chunks.append(c)
                    running_ctx_tokens += c_tok
                else:
                    # Partial trim of the final chunk if room remains
                    leftover_tokens = remaining_for_ctx - running_ctx_tokens
                    if leftover_tokens > 20:
                        char_limit = leftover_tokens * 3
                        fitted_chunks.append(c[:char_limit] + " ... [trimmed for context budget]")
                    break

            fitted_req.context = "\n\n".join(fitted_chunks)
            reasons.append(f"Trimmed context snippets from {ctx_tokens} to ~{running_ctx_tokens} tokens")

        final_budget = self.compute_budget(fitted_req, model_id, provider)
        final_budget.is_truncated = True
        final_budget.truncation_reason = "; ".join(reasons)
        return fitted_req, final_budget


_BUDGET_MANAGER: Optional[TokenBudgetManager] = None


def get_budget_manager() -> TokenBudgetManager:
    """Return platform singleton TokenBudgetManager."""
    global _BUDGET_MANAGER
    if _BUDGET_MANAGER is None:
        _BUDGET_MANAGER = TokenBudgetManager()
    return _BUDGET_MANAGER
