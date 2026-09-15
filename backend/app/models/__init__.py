"""Multi-Model Provider, Registry, and Dynamic Router Package."""

from app.models.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderStatus,
    normalize_request,
)
from app.models.provider import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    OllamaProvider,
    FallbackGroundedProvider,
    ProviderRegistry,
    get_llm_provider,
    check_llm_health,
)
from app.models.registry import (
    ModelMetadata,
    ModelRegistry,
    get_model_registry,
)
from app.models.router import (
    ModelRouter,
    RoutingDecision,
    get_model_router,
)
from app.models.health import (
    CircuitState,
    ErrorCategory,
    ErrorClassifier,
    ModelHealthRecord,
    ProviderHealthTracker,
    get_health_tracker,
)
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
from app.models.budget import (
    estimate_tokens,
    ContextBudget,
    TokenBudgetManager,
    get_budget_manager,
)
from app.models.continuity import (
    ModelTransition,
    SessionState,
    StateContinuityManager,
    get_state_continuity_manager,
)

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ProviderStatus",
    "normalize_request",
    "BaseLLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "GroqProvider",
    "OllamaProvider",
    "FallbackGroundedProvider",
    "ProviderRegistry",
    "get_llm_provider",
    "check_llm_health",
    "ModelMetadata",
    "ModelRegistry",
    "get_model_registry",
    "ModelRouter",
    "RoutingDecision",
    "get_model_router",
    "CircuitState",
    "ErrorCategory",
    "ErrorClassifier",
    "ModelHealthRecord",
    "ProviderHealthTracker",
    "get_health_tracker",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
    "to_openai_tools",
    "to_gemini_tools",
    "to_anthropic_tools",
    "estimate_tokens",
    "ContextBudget",
    "TokenBudgetManager",
    "get_budget_manager",
    "ModelTransition",
    "SessionState",
    "StateContinuityManager",
    "get_state_continuity_manager",
]




