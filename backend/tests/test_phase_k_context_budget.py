"""Phase K Test Suite: Dynamic Context Window Adaptation and Token Budgeting.

Validates:
1. Fast, monotonic token estimation heuristics across text domains.
2. Model-specific context window resolution (Gemini 1M, Claude 200K, GPT-4o 128K, Ollama 8K).
3. Detailed ContextBudget computation with output headroom reservation.
4. Priority-preserving compaction (preserves system prompt and query, prunes old history).
5. Context snippet trimming and compaction under extreme token constraints.
6. Provider-level integration of fit_request across all multi-provider adapters.
"""

import sys
import os
import pytest

# Ensure backend root is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.budget import (
    estimate_tokens,
    ContextBudget,
    TokenBudgetManager,
    get_budget_manager,
)
from app.models.base import LLMRequest, LLMResponse
from app.models.provider import (
    GeminiProvider,
    OpenAIProvider,
    GroqProvider,
    OllamaProvider,
    FallbackGroundedProvider,
)


def test_token_estimation_accuracy():
    """Verify estimate_tokens returns 0 for empty and reasonable counts for text."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("   \n\t  ") == 0

    # Short query
    short_q = "What is the capital of France?"
    t_short = estimate_tokens(short_q)
    assert 5 <= t_short <= 20

    # Longer paragraph
    para = "The quick brown fox jumps over the lazy dog. " * 10
    t_para = estimate_tokens(para)
    assert t_para > t_short
    assert 80 <= t_para <= 250


def test_model_context_window_resolution():
    """Verify get_model_context_window returns correct capacities for diverse model architectures."""
    mgr = TokenBudgetManager()

    # Gemini massive 1M context (1,000,000 to 1,048,576 tokens)
    assert mgr.get_model_context_window("gemini-3.5-flash", "gemini") >= 1000000
    assert mgr.get_model_context_window("gemini-3.1-flash-lite-preview", "gemini") >= 1000000


    # Anthropic 200K context
    assert mgr.get_model_context_window("claude-3-5-sonnet-20241022", "anthropic") == 200000

    # OpenAI 128K context
    assert mgr.get_model_context_window("gpt-4o", "openai") == 128000
    assert mgr.get_model_context_window("gpt-4o-mini", "openai") == 128000

    # Groq high-speed context
    assert mgr.get_model_context_window("llama-3.3-70b-versatile", "groq") == 128000
    assert mgr.get_model_context_window("mixtral-8x7b-32768", "groq") == 32768

    # Local Ollama compact context
    assert mgr.get_model_context_window("llama3.2:latest", "ollama") == 8192

    # Custom override
    mgr.set_custom_limit("custom-tiny-model", 2048)
    assert mgr.get_model_context_window("custom-tiny-model", "custom") == 2048


def test_compute_budget_breakdown():
    """Verify ContextBudget calculates segment allocations and available headroom."""
    mgr = TokenBudgetManager()
    req = LLMRequest(
        prompt="Explain vector search indexing.",
        system_prompt="You are an expert AI growth strategist.",
        context="Vector embeddings represent text as high-dimensional floats.",
        history=[
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there! How can I help you today?"},
        ],
    )

    budget = mgr.compute_budget(req, model_id="gpt-4o", provider="openai")
    assert budget.max_context_window == 128000
    assert budget.reserved_output_tokens == 4096
    assert budget.max_input_tokens == 128000 - 4096
    assert budget.system_prompt_tokens > 0
    assert budget.user_prompt_tokens > 0
    assert budget.context_tokens > 0
    assert budget.history_tokens > 0
    assert budget.total_input_tokens < budget.max_input_tokens
    assert budget.available_tokens > 100000
    assert budget.is_truncated is False


def test_fit_request_preserves_prompt_and_prunes_history():
    """Verify priority preservation: system prompt and user query are protected while old history is pruned."""
    mgr = TokenBudgetManager()
    mgr.set_custom_limit("compact-model", 400)

    # Create large 20-turn conversation history
    flat_history = []
    for i in range(10):
        flat_history.append({"role": "user", "content": f"Turn {i}: I have a question about marketing channel {i} and acquisition metrics."})
        flat_history.append({"role": "assistant", "content": f"Answer {i}: Channel {i} has CAC of ${i*10} and LTV of ${i*50}."})


    req = LLMRequest(
        prompt="What is the most cost-effective channel overall?",
        system_prompt="You are an executive product strategist.",
        history=flat_history,
    )

    fitted_req, budget = mgr.fit_request(req, model_id="compact-model", provider="ollama")

    # Budget must be flagged as truncated
    assert budget.is_truncated is True
    assert "Pruned" in budget.truncation_reason

    # System prompt and current user prompt must remain identical
    assert fitted_req.prompt == req.prompt
    assert fitted_req.system_prompt == req.system_prompt

    # History must be pruned
    assert len(fitted_req.history) < len(flat_history)

    # Total input tokens must fit inside max_input_tokens
    assert budget.total_input_tokens <= budget.max_input_tokens


def test_fit_request_context_trimming():
    """Verify evidence context is gracefully trimmed when context snippets exceed allowance."""
    mgr = TokenBudgetManager()
    mgr.set_custom_limit("tiny-context-model", 350)

    huge_context = "\n\n".join([
        f"Paragraph {i}: Detailed case study on user acquisition, viral loops, and churn reduction for company {i}."
        for i in range(30)
    ])

    req = LLMRequest(
        prompt="Summarize the case studies.",
        system_prompt="You are a growth researcher.",
        context=huge_context,
        history=[],
    )

    fitted_req, budget = mgr.fit_request(req, model_id="tiny-context-model", provider="ollama")

    assert budget.is_truncated is True
    assert "Trimmed context snippets" in budget.truncation_reason
    assert len(fitted_req.context) < len(huge_context)
    assert budget.total_input_tokens <= budget.max_input_tokens


def test_provider_fit_request_integration():
    """Verify provider.fit_request() works directly on provider instances."""
    mgr = get_budget_manager()
    mgr.set_custom_limit("gemini-custom-cap", 500)

    gemini = GeminiProvider(model="gemini-custom-cap")
    assert gemini.get_model_name() == "gemini-custom-cap"

    huge_history = [{"role": "user", "content": f"Turn {i} " + "data "*20} for i in range(15)]
    req = LLMRequest(
        prompt="Final question",
        system_prompt="System",
        history=huge_history,
    )

    fitted_req, budget = gemini.fit_request(req)
    assert budget.is_truncated is True
    assert len(fitted_req.history) < len(huge_history)
    assert budget.total_input_tokens <= budget.max_input_tokens

    # Context budget computation method
    b_info = gemini.get_context_budget(req)
    assert b_info.max_context_window == 500
