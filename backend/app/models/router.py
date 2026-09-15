"""Intelligent Model Router for dynamic, capability-based LLM provider and model selection.

Routes incoming tasks to optimal models based on task type, latency targets, context window,
multimodal needs, cost, configured provider availability, and user overrides.
"""

from typing import Optional, List, Dict, Any, Union, Generator
from dataclasses import dataclass, field
import logging

from app.core.config import settings
from app.models.base import LLMRequest, LLMResponse, ProviderStatus, normalize_request
from app.models.registry import get_model_registry, ModelMetadata

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Detailed record of the model router's decision."""
    provider: str
    model_id: str
    rationale: str
    fallback_chain: List[str] = field(default_factory=list)
    metadata: Optional[ModelMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "rationale": self.rationale,
            "fallback_chain": self.fallback_chain,
            "model_display_name": self.metadata.display_name if self.metadata else self.model_id,
            "context_window": self.metadata.context_window if self.metadata else 128000,
            "supports_tools": self.metadata.supports_tools if self.metadata else True,
        }


class ModelRouter:
    """Selects the best available model based on task demands, cost, speed, and configured keys."""

    def __init__(self):
        self.registry = get_model_registry()

    def route(
        self,
        task_type: str = "general_qa",
        user_preference: Optional[str] = None,
        context_tokens: int = 1000,
        requires_tools: bool = False,
        requires_vision: bool = False,
        requires_web: bool = False,
        low_latency: bool = False,
    ) -> RoutingDecision:
        """Dynamically determine optimal provider and model."""
        pref = (user_preference or getattr(settings, "MODEL", None) or settings.LLM_PROVIDER or "auto").strip().lower()

        # Step 1: Check if user requested a specific provider or model
        if pref not in ("auto", "default", ""):
            decision = self._handle_user_preference(
                pref=pref,
                task_type=task_type,
                requires_vision=requires_vision,
            )
            if decision:
                return decision

        # Step 2: Auto-routing matrix based on task type and availability
        return self._auto_route(
            task_type=task_type,
            context_tokens=context_tokens,
            requires_tools=requires_tools,
            requires_vision=requires_vision,
            requires_web=requires_web,
            low_latency=low_latency,
        )

    def _handle_user_preference(
        self,
        pref: str,
        task_type: str,
        requires_vision: bool,
    ) -> Optional[RoutingDecision]:
        """Validate and honor user's explicit provider or model choice."""
        from app.models.health import get_health_tracker
        tracker = get_health_tracker()

        # Check if pref is a known model_id directly
        model_meta = self.registry.get(pref)
        if model_meta:
            if model_meta.availability and tracker.is_available(model_meta.provider, model_meta.model_id):
                chain = self._build_fallback_chain(exclude=model_meta.provider)
                return RoutingDecision(
                    provider=model_meta.provider,
                    model_id=model_meta.model_id,
                    rationale=f"Explicit user model selection: {model_meta.display_name}",
                    fallback_chain=chain,
                    metadata=model_meta,
                )
            else:
                logger.warning("User requested model '%s' is unavailable or circuit is OPEN. Falling back to auto-routing.", pref)
                return None

        # Check if pref is a provider name
        valid_providers = ["openai", "anthropic", "gemini", "groq", "ollama", "fallback"]
        if pref in valid_providers:
            if not tracker.is_available(pref):
                logger.warning("User requested provider '%s' circuit is OPEN. Falling back to auto-routing.", pref)
                return None
            default_m = self.registry.get_default_model_for_provider(pref)
            if default_m and tracker.is_available(pref, default_m.model_id):
                chain = self._build_fallback_chain(exclude=pref)
                prov_display = {
                    "openai": "OpenAI",
                    "anthropic": "Anthropic",
                    "gemini": "Google Gemini",
                    "groq": "Groq",
                    "ollama": "Ollama",
                    "fallback": "Fallback",
                }.get(pref, pref.capitalize())
                return RoutingDecision(
                    provider=pref,
                    model_id=default_m.model_id,
                    rationale=f"Explicit user provider selection: {prov_display}",
                    fallback_chain=chain,
                    metadata=default_m,
                )

        return None

    def score_model(
        self,
        model: ModelMetadata,
        task_type: str = "general_qa",
        context_tokens: int = 1000,
        requires_tools: bool = False,
        requires_vision: bool = False,
        requires_web: bool = False,
        low_latency: bool = False,
    ) -> float:
        """Calculate quantitative affinity score (0.0 to 1.0+) of a model for a specific task."""
        # 1. Strict constraints
        if not self.registry.check_availability(model.provider):
            return -1.0
        from app.models.health import get_health_tracker
        tracker = get_health_tracker()
        if not tracker.is_available(model.provider, model.model_id):
            return -1.0
        if requires_vision and not model.supports_vision:
            return -1.0
        if context_tokens > model.context_window:
            return -1.0
        if task_type in ("coding", "debugging", "architecture") and not model.supports_code:
            return -1.0

        # 2. Task fitness score (0.0 to 1.0)
        if task_type in ("coding", "debugging", "architecture"):
            s_task = model.coding_suitability
        elif task_type in ("deep_research", "research", "web_research"):
            s_task = model.reasoning_suitability
            if model.supports_reasoning:
                s_task = min(1.0, s_task * 1.1)
        elif task_type in ("fast_response", "chat"):
            s_task = (model.coding_suitability + model.reasoning_suitability) / 2.0
        else:
            s_task = (model.coding_suitability + model.reasoning_suitability) / 2.0

        # 3. Latency score (0.0 to 1.0)
        lat_map = {
            "ultra_fast": 1.0,
            "fast": 0.8,
            "moderate": 0.5,
            "slow": 0.2,
        }
        s_lat = lat_map.get(model.relative_latency, 0.5)

        # 4. Cost score (0.0 to 1.0)
        cost_map = {
            "free": 1.0,
            "low": 0.85,
            "medium": 0.6,
            "high": 0.3,
        }
        s_cost = cost_map.get(model.relative_cost, 0.6)

        # 5. Context score (0.0 to 1.0)
        s_ctx = min(1.0, max(0.2, model.context_window / 1000000.0))

        # 6. Task-specific weights
        if task_type in ("coding", "debugging", "architecture"):
            w_task, w_lat, w_cost, w_ctx = 0.75, 0.15, 0.05, 0.05
        elif task_type in ("deep_research", "research", "web_research"):
            w_task, w_lat, w_cost, w_ctx = 0.55, 0.10, 0.05, 0.30
        elif low_latency or task_type == "fast_response":
            w_task, w_lat, w_cost, w_ctx = 0.20, 0.65, 0.10, 0.05
        else:
            w_task, w_lat, w_cost, w_ctx = 0.40, 0.35, 0.15, 0.10

        score = (w_task * s_task) + (w_lat * s_lat) + (w_cost * s_cost) + (w_ctx * s_ctx)

        # Bonuses
        if model.status == ProviderStatus.HEALTHY.value:
            score += 0.05
        if requires_tools and model.supports_tools:
            score += 0.05
        if context_tokens > 120000 and model.context_window >= 1000000:
            score += 0.30

        return round(score, 4)

    def _auto_route(
        self,
        task_type: str,
        context_tokens: int,
        requires_tools: bool,
        requires_vision: bool,
        requires_web: bool,
        low_latency: bool,
    ) -> RoutingDecision:
        """Intelligently score available models and select the best candidate."""
        available_models = [
            m for m in self.registry.list_models(available_only=False)
            if self.registry.check_availability(m.provider)
        ]
        scored: List[tuple[float, ModelMetadata]] = []

        for m in available_models:
            if m.provider == "fallback" and len(available_models) > 1:
                continue
            s = self.score_model(
                model=m,
                task_type=task_type,
                context_tokens=context_tokens,
                requires_tools=requires_tools,
                requires_vision=requires_vision,
                requires_web=requires_web,
                low_latency=low_latency,
            )
            if s >= 0:
                scored.append((s, m))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            top_score, best_model = scored[0]
            chain = self._build_fallback_chain(exclude=best_model.provider)
            task_desc = f"massive context ({context_tokens:,} tokens)" if context_tokens > 120000 else task_type
            rationale = (
                f"Auto-routed to {best_model.display_name} for {task_desc} "
                f"(affinity score: {top_score}, latency: {best_model.relative_latency}, context: {best_model.context_window:,})"
            )
            return RoutingDecision(
                provider=best_model.provider,
                model_id=best_model.model_id,
                rationale=rationale,
                fallback_chain=chain,
                metadata=best_model,
            )

        # Fallback to Grounded Synthesizer
        fb_meta = self.registry.get("grounded-synthesizer-v2")
        return RoutingDecision(
            provider="fallback",
            model_id="grounded-synthesizer-v2",
            rationale="No external cloud API keys or local Ollama available; using resilient grounded fallback synthesizer.",
            fallback_chain=[],
            metadata=fb_meta,
        )

    def _build_fallback_chain(self, exclude: str) -> List[str]:
        """Construct an ordered failover sequence of available providers."""
        from app.models.health import get_health_tracker
        tracker = get_health_tracker()
        candidates = ["gemini", "groq", "openai", "anthropic", "ollama", "fallback"]
        chain = []
        for c in candidates:
            if c != exclude.lower():
                if c == "fallback" or (self.registry.check_availability(c) and tracker.is_available(c)):
                    chain.append(c)
        return chain

    def execute(
        self,
        request: Union[LLMRequest, str],
        task_type: str = "general_qa",
        user_preference: Optional[str] = None,
        context_tokens: int = 1000,
        requires_tools: bool = False,
        requires_vision: bool = False,
        *args,
        **kwargs,
    ) -> LLMResponse:
        """Route and execute request with automatic retry, circuit breaker tracking, and provider fallback."""
        import time
        from app.models.provider import ProviderRegistry
        from app.models.health import get_health_tracker
        tracker = get_health_tracker()
        req, _ = normalize_request(request, *args, **kwargs)
        decision = self.route(
            task_type=task_type,
            user_preference=user_preference,
            context_tokens=context_tokens,
            requires_tools=requires_tools or bool(req.tools),
            requires_vision=requires_vision,
        )

        candidates = [decision.provider] + [p for p in decision.fallback_chain if p != decision.provider]
        if "fallback" not in candidates:
            candidates.append("fallback")

        fallback_occurred = False
        for prov_name in candidates:
            if not tracker.is_available(prov_name):
                logger.info("Provider '%s' circuit is OPEN. Skipping in fallback cascade.", prov_name)
                fallback_occurred = True
                continue

            prov = ProviderRegistry.get(prov_name)
            h = prov.health_check()
            if h.get("status") == ProviderStatus.NOT_CONFIGURED.value:
                logger.info("Provider '%s' is NOT_CONFIGURED. Trying next provider in fallback chain.", prov_name)
                continue

            t0 = time.perf_counter()
            try:
                res = prov.generate(req)
                lat_ms = (time.perf_counter() - t0) * 1000.0
                tracker.record_success(prov_name, prov.get_model_name(), latency_ms=lat_ms)

                if isinstance(res, LLMResponse):
                    if fallback_occurred or prov_name == "fallback":
                        res.status = "FALLBACK"
                    return res
                return LLMResponse(
                    content=str(res),
                    model=prov.get_model_name(),
                    provider=prov_name,
                    status="FALLBACK" if (fallback_occurred or prov_name == "fallback") else "SUCCESS",
                )
            except Exception as e:
                tracker.record_failure(prov_name, prov.get_model_name(), error=e)
                fallback_occurred = True
                logger.warning("Provider '%s' execution failed (%s). Moving to next candidate in cascade.", prov_name, e)

        fb = ProviderRegistry.get("fallback")
        res = fb.generate(req)
        if isinstance(res, LLMResponse):
            res.status = "FALLBACK"
            return res
        return LLMResponse(
            content=str(res),
            model=fb.get_model_name(),
            provider="fallback",
            status="FALLBACK",
        )

    def execute_stream(
        self,
        request: Union[LLMRequest, str],
        task_type: str = "general_qa",
        user_preference: Optional[str] = None,
        context_tokens: int = 1000,
        requires_tools: bool = False,
        requires_vision: bool = False,
        *args,
        **kwargs,
    ) -> Generator[str, None, None]:
        """Route and stream request with circuit breaker tracking and provider fallback."""
        from app.models.provider import ProviderRegistry
        from app.models.health import get_health_tracker
        tracker = get_health_tracker()
        req, _ = normalize_request(request, *args, **kwargs)
        decision = self.route(
            task_type=task_type,
            user_preference=user_preference,
            context_tokens=context_tokens,
            requires_tools=requires_tools or bool(req.tools),
            requires_vision=requires_vision,
        )

        candidates = [decision.provider] + [p for p in decision.fallback_chain if p != decision.provider]
        if "fallback" not in candidates:
            candidates.append("fallback")

        for prov_name in candidates:
            if not tracker.is_available(prov_name):
                logger.info("Provider '%s' circuit is OPEN. Skipping in fallback stream cascade.", prov_name)
                continue

            prov = ProviderRegistry.get(prov_name)
            h = prov.health_check()
            if h.get("status") == ProviderStatus.NOT_CONFIGURED.value:
                continue
            try:
                yielded = False
                for chunk in prov.generate_stream(req):
                    if not yielded:
                        tracker.record_success(prov_name, prov.get_model_name())
                    yielded = True
                    yield chunk
                if yielded:
                    return
            except Exception as e:
                tracker.record_failure(prov_name, prov.get_model_name(), error=e)
                logger.warning("Provider '%s' stream failed (%s). Falling back.", prov_name, e)

        fb = ProviderRegistry.get("fallback")
        for chunk in fb.generate_stream(req):
            yield chunk


_MODEL_ROUTER = ModelRouter()

def get_model_router() -> ModelRouter:
    """Access the singleton ModelRouter instance."""
    return _MODEL_ROUTER

