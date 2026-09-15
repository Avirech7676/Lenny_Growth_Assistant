"""Core Contracts for Multi-Provider LLM Platform.

Defines unified types, requests, responses, and abstract provider interface:
- LLMProvider
- LLMRequest
- LLMResponse
- ProviderStatus
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator, Union
from dataclasses import dataclass, field
from enum import Enum


class ProviderStatus(str, Enum):
    HEALTHY = "HEALTHY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class LLMRequest:
    """Unified request contract passed to any LLM provider."""
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[str]] = None
    structured_output_schema: Optional[Dict[str, Any]] = None
    stream: bool = False
    timeout_seconds: float = 30.0
    retry_attempts: int = 2

    @property
    def full_user_content(self) -> str:
        """Construct full prompt body including injected context if available."""
        if self.context and self.context.strip():
            return f"EVIDENCE & CONTEXT:\n{self.context}\n\nUSER QUESTION:\n{self.prompt}"
        return self.prompt


@dataclass
class LLMResponse:
    """Unified response contract returned by any LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    tool_calls: Optional[List[Dict[str, Any]]] = None
    structured_data: Optional[Dict[str, Any]] = None
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    status: str = "SUCCESS"

    def __str__(self) -> str:
        return self.content


def normalize_request(
    request_or_system: Union[LLMRequest, str, None] = None,
    *args,
    **kwargs
) -> tuple[LLMRequest, bool]:
    """
    Normalizes diverse call conventions into a unified LLMRequest.
    Returns (request: LLMRequest, is_legacy_signature: bool).
    """
    if isinstance(request_or_system, LLMRequest):
        return request_or_system, False

    if isinstance(request_or_system, str) and args:
        sys_p = request_or_system
        usr_p = str(args[0]) if len(args) > 0 else ""
        ctx = str(args[1]) if len(args) > 1 else kwargs.get("context")
        hist = args[2] if len(args) > 2 else kwargs.get("history", [])
        return LLMRequest(
            prompt=usr_p,
            system_prompt=sys_p,
            context=ctx,
            history=hist or [],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            tools=kwargs.get("tools"),
            structured_output_schema=kwargs.get("structured_output_schema"),
            stream=kwargs.get("stream", False),
            timeout_seconds=kwargs.get("timeout_seconds", 30.0),
            retry_attempts=kwargs.get("retry_attempts", 2),
        ), True

    if "user_prompt" in kwargs or "system_prompt" in kwargs:
        sys_p = kwargs.get("system_prompt") or (request_or_system if isinstance(request_or_system, str) else None)
        usr_p = kwargs.get("user_prompt") or kwargs.get("prompt") or ""
        ctx = kwargs.get("context")
        hist = kwargs.get("history", [])
        return LLMRequest(
            prompt=usr_p,
            system_prompt=sys_p,
            context=ctx,
            history=hist or [],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            tools=kwargs.get("tools"),
            structured_output_schema=kwargs.get("structured_output_schema"),
            stream=kwargs.get("stream", False),
            timeout_seconds=kwargs.get("timeout_seconds", 30.0),
            retry_attempts=kwargs.get("retry_attempts", 2),
        ), True

    if "prompt" in kwargs:
        usr_p = kwargs["prompt"]
        sys_p = kwargs.get("system_prompt")
        return LLMRequest(
            prompt=usr_p,
            system_prompt=sys_p,
            context=kwargs.get("context"),
            history=kwargs.get("history", []),
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            tools=kwargs.get("tools"),
            structured_output_schema=kwargs.get("structured_output_schema"),
            stream=kwargs.get("stream", False),
            timeout_seconds=kwargs.get("timeout_seconds", 30.0),
            retry_attempts=kwargs.get("retry_attempts", 2),
        ), False

    if isinstance(request_or_system, str):
        return LLMRequest(prompt=request_or_system), True

    return LLMRequest(prompt=""), False


class LLMProvider(ABC):
    """Abstract base contract for all multi-provider LLM adapters."""

    @abstractmethod
    def generate(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> Union[LLMResponse, str]:
        """Execute text generation. Accepts unified LLMRequest or legacy prompt arguments."""
        pass

    @abstractmethod
    def generate_stream(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> Generator[str, None, None]:
        """Progressively stream output tokens."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return provider health status (e.g. NOT_CONFIGURED, HEALTHY, ERROR)."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return active model identifier."""
        pass

    def is_configured(self) -> bool:
        """Fast configuration check without executing remote network calls."""
        h = self.health_check()
        return bool(h.get("healthy", False) or h.get("status") == ProviderStatus.HEALTHY.value)

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports real-time streaming."""
        return True

    @property
    def supports_tools(self) -> bool:
        """Whether this provider supports native tool/function calling."""
        return True

    @property
    def supports_vision(self) -> bool:
        """Whether this provider supports image and visual comprehension."""
        return False

    def with_model(self, model_id: str) -> "LLMProvider":
        """Return a provider instance configured for the specified model_id."""
        import copy
        new_inst = copy.copy(self)
        new_inst.model = model_id
        return new_inst

    def supports_feature(self, feature_name: str) -> bool:
        """Check if provider supports a specific capability (streaming, tools, vision, structured_output)."""
        f = feature_name.lower().strip()
        if f in ("streaming", "stream"):
            return self.supports_streaming
        elif f in ("tools", "tool_calling", "functions"):
            return self.supports_tools
        elif f in ("vision", "multimodal", "image"):
            return self.supports_vision
        elif f in ("structured_output", "json_mode", "json"):
            return True
        return False

    def get_metadata(self) -> Any:
        """Return model operational metadata from registry."""
        from app.models.registry import get_model_registry
        return get_model_registry().get_default_model_for_provider(self.get_provider_id())

    def get_provider_id(self) -> str:
        """Return canonical provider identifier string."""
        return self.__class__.__name__.replace("Provider", "").lower()

    def fit_request(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> tuple[LLMRequest, Any]:
        """Proactively bound request to this provider model's context window."""
        req, _ = normalize_request(request, *args, **kwargs)
        from app.models.budget import get_budget_manager
        return get_budget_manager().fit_request(
            req,
            model_id=self.get_model_name(),
            provider=self.get_provider_id(),
        )

    def get_context_budget(self, request: Union[LLMRequest, str, None] = None, *args, **kwargs) -> Any:
        """Compute token budget breakdown for this provider model."""
        req, _ = normalize_request(request, *args, **kwargs)
        from app.models.budget import get_budget_manager
        return get_budget_manager().compute_budget(
            req,
            model_id=self.get_model_name(),
            provider=self.get_provider_id(),
        )


