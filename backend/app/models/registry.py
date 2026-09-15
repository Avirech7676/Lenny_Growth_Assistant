"""Centralized Model Capability Registry tracking operational metadata across all providers.

Tracks at minimum:
1. provider
2. model
3. context length
4. streaming
5. tool calling
6. vision
7. coding suitability
8. reasoning suitability
9. latency class
10. availability
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

from app.core.config import settings
from app.models.base import ProviderStatus

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Rich metadata record describing an AI model's operational characteristics."""
    provider: str
    model_id: str
    display_name: str
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 128000
    supports_tools: bool = True
    supports_web: bool = True
    supports_vision: bool = False
    supports_code: bool = True
    supports_streaming: bool = True
    supports_reasoning: bool = True
    supports_structured_output: bool = True
    coding_suitability: float = 0.8
    reasoning_suitability: float = 0.8
    relative_cost: str = "medium"         # "free", "low", "medium", "high"
    relative_latency: str = "fast"        # "ultra_fast", "fast", "moderate", "slow"
    availability: bool = False
    status: str = ProviderStatus.NOT_CONFIGURED.value

    # Aliases explicitly matching specification names
    @property
    def model(self) -> str:
        return self.model_id

    @property
    def context_length(self) -> int:
        return self.context_window

    @property
    def streaming(self) -> bool:
        return self.supports_streaming

    @property
    def tool_calling(self) -> bool:
        return self.supports_tools

    @property
    def vision(self) -> bool:
        return self.supports_vision

    @property
    def latency_class(self) -> str:
        return self.relative_latency

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model_id,
            "model_id": self.model_id,
            "display_name": self.display_name,
            "capabilities": self.capabilities,
            "context_length": self.context_window,
            "context_window": self.context_window,
            "streaming": self.supports_streaming,
            "supports_streaming": self.supports_streaming,
            "tool_calling": self.supports_tools,
            "supports_tools": self.supports_tools,
            "vision": self.supports_vision,
            "supports_vision": self.supports_vision,
            "coding_suitability": self.coding_suitability,
            "reasoning_suitability": self.reasoning_suitability,
            "supports_code": self.supports_code,
            "supports_reasoning": self.supports_reasoning,
            "supports_structured_output": self.supports_structured_output,
            "relative_cost": self.relative_cost,
            "latency_class": self.relative_latency,
            "relative_latency": self.relative_latency,
            "availability": self.availability,
            "is_available": self.availability,
            "status": self.status,
        }


class ModelRegistry:
    """Centralized registry for AI models across all supported providers."""

    def __init__(self):
        self._models: Dict[str, ModelMetadata] = {}
        self._initialize_catalogs()

    def _initialize_catalogs(self) -> None:
        """Register primary standard models across all 5 supported providers + fallback."""
        # 1. OpenAI Models
        has_openai = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
        self.register(ModelMetadata(
            provider="openai",
            model_id=settings.OPENAI_MODEL or "gpt-4o",
            display_name="GPT-4o",
            capabilities=["chat", "general_qa", "reasoning", "coding", "research", "vision", "tools", "planning"],
            context_window=128000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.92,
            reasoning_suitability=0.95,
            relative_cost="medium",
            relative_latency="fast",
            availability=has_openai,
            status=ProviderStatus.HEALTHY.value if has_openai else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="openai",
            model_id="gpt-4o-mini",
            display_name="GPT-4o Mini",
            capabilities=["chat", "general_qa", "coding", "fast_response", "tools"],
            context_window=128000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.82,
            reasoning_suitability=0.80,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_openai,
            status=ProviderStatus.HEALTHY.value if has_openai else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="openai",
            model_id="o3-mini",
            display_name="OpenAI o3-mini",
            capabilities=["deep_reasoning", "mathematics", "coding", "scientific_analysis"],
            context_window=200000,
            supports_tools=True,
            supports_web=False,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.94,
            reasoning_suitability=0.97,
            relative_cost="medium",
            relative_latency="moderate",
            availability=has_openai,
            status=ProviderStatus.HEALTHY.value if has_openai else ProviderStatus.NOT_CONFIGURED.value,
        ))

        # 2. Anthropic Models
        has_anthropic = bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip())
        self.register(ModelMetadata(
            provider="anthropic",
            model_id=settings.ANTHROPIC_MODEL or "claude-3-5-sonnet-latest",
            display_name="Claude 3.5 Sonnet",
            capabilities=["chat", "general_qa", "coding", "architecture", "writing", "deep_research", "tools", "vision"],
            context_window=200000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.98,
            reasoning_suitability=0.98,
            relative_cost="medium",
            relative_latency="fast",
            availability=has_anthropic,
            status=ProviderStatus.HEALTHY.value if has_anthropic else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="anthropic",
            model_id="claude-3-5-haiku-latest",
            display_name="Claude 3.5 Haiku",
            capabilities=["chat", "general_qa", "fast_response", "tools", "coding"],
            context_window=200000,
            supports_tools=True,
            supports_web=True,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.85,
            reasoning_suitability=0.82,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_anthropic,
            status=ProviderStatus.HEALTHY.value if has_anthropic else ProviderStatus.NOT_CONFIGURED.value,
        ))

        # 3. Google Gemini Models
        has_gemini = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
        self.register(ModelMetadata(
            provider="gemini",
            model_id=settings.GEMINI_MODEL or "gemini-3.5-flash",
            display_name="Gemini 3.5 Flash",
            capabilities=["chat", "general_qa", "research", "multimodal", "fast_response", "tools", "vision"],
            context_window=1000000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.85,
            reasoning_suitability=0.88,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_gemini,
            status=ProviderStatus.HEALTHY.value if has_gemini else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="gemini",
            model_id="gemini-3.5-flash-lite",
            display_name="Gemini 3.5 Flash Lite",
            capabilities=["chat", "general_qa", "fast_response", "tools"],
            context_window=1000000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.82,
            reasoning_suitability=0.82,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_gemini,
            status=ProviderStatus.HEALTHY.value if has_gemini else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="gemini",
            model_id="gemini-3.1-flash-lite",
            display_name="Gemini 3.1 Flash Lite",
            capabilities=["chat", "general_qa", "fast_response", "tools"],
            context_window=1000000,
            supports_tools=True,
            supports_web=True,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.80,
            reasoning_suitability=0.80,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_gemini,
            status=ProviderStatus.HEALTHY.value if has_gemini else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="gemini",
            model_id="gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            capabilities=["chat", "deep_research", "long_context", "document_analysis", "multimodal", "tools", "vision"],
            context_window=2000000,
            supports_tools=True,
            supports_web=True,
            supports_vision=True,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.90,
            reasoning_suitability=0.94,
            relative_cost="medium",
            relative_latency="moderate",
            availability=has_gemini,
            status=ProviderStatus.HEALTHY.value if has_gemini else ProviderStatus.NOT_CONFIGURED.value,
        ))

        # 4. Groq Models (Ultra-Fast Llama-3.3)
        has_groq = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
        self.register(ModelMetadata(
            provider="groq",
            model_id=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            display_name="Llama 3.3 70B (Groq)",
            capabilities=["chat", "general_qa", "fast_response", "coding", "tools", "reasoning"],
            context_window=128000,
            supports_tools=True,
            supports_web=True,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.88,
            reasoning_suitability=0.89,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_groq,
            status=ProviderStatus.HEALTHY.value if has_groq else ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="groq",
            model_id="mixtral-8x7b-32768",
            display_name="Mixtral 8x7B (Groq)",
            capabilities=["chat", "fast_response", "general_qa", "tools"],
            context_window=32768,
            supports_tools=True,
            supports_web=True,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=True,
            coding_suitability=0.80,
            reasoning_suitability=0.82,
            relative_cost="low",
            relative_latency="ultra_fast",
            availability=has_groq,
            status=ProviderStatus.HEALTHY.value if has_groq else ProviderStatus.NOT_CONFIGURED.value,
        ))

        # 5. Ollama Models (Local, Private, Offline)
        self.register(ModelMetadata(
            provider="ollama",
            model_id=settings.OLLAMA_MODEL or "llama3.2:latest",
            display_name="Llama 3.2 Local (Ollama)",
            capabilities=["chat", "general_qa", "local_private", "offline"],
            context_window=8192,
            supports_tools=False,
            supports_web=False,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=False,
            supports_structured_output=False,
            coding_suitability=0.75,
            reasoning_suitability=0.74,
            relative_cost="free",
            relative_latency="moderate",
            availability=False,  # Updated dynamically by health check
            status=ProviderStatus.NOT_CONFIGURED.value,
        ))
        self.register(ModelMetadata(
            provider="ollama",
            model_id="qwen2.5-coder:latest",
            display_name="Qwen 2.5 Coder Local (Ollama)",
            capabilities=["coding", "debugging", "local_private", "offline"],
            context_window=32768,
            supports_tools=False,
            supports_web=False,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=False,
            coding_suitability=0.91,
            reasoning_suitability=0.85,
            relative_cost="free",
            relative_latency="moderate",
            availability=False,
            status=ProviderStatus.NOT_CONFIGURED.value,
        ))

        # 6. Fallback Grounded Synthesizer (Always Available Offline Anchor)
        self.register(ModelMetadata(
            provider="fallback",
            model_id="grounded-synthesizer-v2",
            display_name="Grounded Synthesizer (Deterministic Fallback)",
            capabilities=["chat", "general_qa", "offline_fallback", "coding", "research"],
            context_window=16384,
            supports_tools=True,
            supports_web=True,
            supports_vision=False,
            supports_code=True,
            supports_streaming=True,
            supports_reasoning=True,
            supports_structured_output=True,
            coding_suitability=0.80,
            reasoning_suitability=0.80,
            relative_cost="free",
            relative_latency="ultra_fast",
            availability=True,
            status=ProviderStatus.HEALTHY.value,
        ))

    def register(self, model: ModelMetadata) -> None:
        """Register or update a model record."""
        self._models[model.model_id] = model

    def get(self, model_id: str) -> Optional[ModelMetadata]:
        """Retrieve model metadata by model_id."""
        return self._models.get(model_id)

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Alias for get(model_id)."""
        return self.get(model_id)

    def list_models(self, provider: Optional[str] = None, available_only: bool = False) -> List[ModelMetadata]:
        """Return registered models, optionally filtered by provider and availability."""
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider.lower() == provider.lower()]
        if available_only:
            models = [m for m in models if m.availability]
        return models

    def get_default_model_for_provider(self, provider: str) -> Optional[ModelMetadata]:
        """Return the primary standard model for a given provider."""
        provider = provider.lower()
        prov_models = [m for m in self._models.values() if m.provider.lower() == provider]
        if not prov_models:
            return None
        available = [m for m in prov_models if m.availability]
        return available[0] if available else prov_models[0]

    def check_availability(self, provider: str) -> bool:
        """Check if any model under a provider is currently marked available."""
        prov_models = self.list_models(provider=provider)
        return any(m.availability for m in prov_models)

    def update_availability(self, provider: str, is_available: bool, status: str = "HEALTHY") -> None:
        """Update runtime availability status for all models of a provider."""
        for m in self._models.values():
            if m.provider.lower() == provider.lower():
                m.availability = is_available
                m.status = status

    def discover_live_models(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Dynamically query live provider APIs and local Ollama to discover available models."""
        target_provider = provider.lower().strip() if provider else None
        results: Dict[str, Any] = {
            "discovered_count": 0,
            "providers": {},
        }

        # 1. Gemini Discovery
        if not target_provider or target_provider == "gemini":
            gemini_models = self._discover_gemini()
            results["providers"]["gemini"] = [m.model_id for m in gemini_models]
            results["discovered_count"] += len(gemini_models)

        # 2. Ollama Discovery
        if not target_provider or target_provider == "ollama":
            ollama_models = self._discover_ollama()
            results["providers"]["ollama"] = [m.model_id for m in ollama_models]
            results["discovered_count"] += len(ollama_models)

        # 3. Groq Discovery
        if not target_provider or target_provider == "groq":
            groq_models = self._discover_groq()
            results["providers"]["groq"] = [m.model_id for m in groq_models]
            results["discovered_count"] += len(groq_models)

        # 4. OpenAI Discovery
        if not target_provider or target_provider == "openai":
            openai_models = self._discover_openai()
            results["providers"]["openai"] = [m.model_id for m in openai_models]
            results["discovered_count"] += len(openai_models)

        return results

    def _discover_gemini(self) -> List[ModelMetadata]:
        """Query Google GenAI API to discover active generation models."""
        if not settings.GEMINI_API_KEY:
            return []

        discovered: List[ModelMetadata] = []
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            for m in client.models.list():
                raw_name = getattr(m, "name", "")
                actions = getattr(m, "supported_actions", []) or []
                if "generateContent" not in actions:
                    continue
                clean_id = raw_name.replace("models/", "")
                # Exclude specialized audio, tts, robotics, embedding models
                if any(bad in clean_id for bad in ["embedding", "tts", "robotics", "transcribe", "native-audio", "live-translate", "computer-use"]):
                    continue

                display = getattr(m, "display_name", None) or clean_id
                input_limit = getattr(m, "input_token_limit", 1000000) or 1000000

                meta = ModelMetadata(
                    provider="gemini",
                    model_id=clean_id,
                    display_name=display,
                    capabilities=["chat", "general_qa", "research", "tools", "multimodal"],
                    context_window=input_limit,
                    supports_tools=True,
                    supports_web=True,
                    supports_vision=bool("image" in clean_id or "flash" in clean_id or "pro" in clean_id),
                    supports_code=True,
                    supports_streaming=True,
                    supports_reasoning=bool("pro" in clean_id),
                    supports_structured_output=True,
                    coding_suitability=0.88 if "pro" in clean_id else 0.85,
                    reasoning_suitability=0.92 if "pro" in clean_id else 0.85,
                    relative_cost="low" if "flash" in clean_id else "medium",
                    relative_latency="ultra_fast" if "flash" in clean_id else "moderate",
                    availability=True,
                    status=ProviderStatus.HEALTHY.value,
                )
                self.register(meta)
                discovered.append(meta)
        except Exception as e:
            logger.warning("Dynamic discovery failed for Google Gemini: %s", e)

        return discovered

    def _discover_ollama(self) -> List[ModelMetadata]:
        """Query local Ollama instance at /api/tags with short timeout."""
        import requests
        discovered: List[ModelMetadata] = []
        try:
            res = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                models = data.get("models", [])
                for item in models:
                    model_id = item.get("name", "")
                    if not model_id:
                        continue
                    display_name = f"{model_id.title()} Local (Ollama)"
                    is_code = any(k in model_id.lower() for k in ["code", "coder", "deepseek", "starcoder"])
                    meta = ModelMetadata(
                        provider="ollama",
                        model_id=model_id,
                        display_name=display_name,
                        capabilities=["chat", "general_qa", "local_private", "offline"] + (["coding"] if is_code else []),
                        context_window=32768 if is_code else 8192,
                        supports_tools=False,
                        supports_web=False,
                        supports_vision=False,
                        supports_code=is_code,
                        supports_streaming=True,
                        supports_reasoning=bool("r1" in model_id.lower() or "reason" in model_id.lower()),
                        supports_structured_output=False,
                        coding_suitability=0.90 if is_code else 0.75,
                        reasoning_suitability=0.85,
                        relative_cost="free",
                        relative_latency="moderate",
                        availability=True,
                        status=ProviderStatus.HEALTHY.value,
                    )
                    self.register(meta)
                    discovered.append(meta)
        except Exception as e:
            logger.debug("Local Ollama discovery skipped or offline: %s", e)

        return discovered

    def _discover_groq(self) -> List[ModelMetadata]:
        """Query Groq /openai/v1/models endpoint if key is configured."""
        if not settings.GROQ_API_KEY:
            return []
        import requests
        discovered: List[ModelMetadata] = []
        try:
            headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
            res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("data", []):
                    m_id = item.get("id", "")
                    if not m_id:
                        continue
                    meta = ModelMetadata(
                        provider="groq",
                        model_id=m_id,
                        display_name=f"{m_id.title()} (Groq)",
                        capabilities=["chat", "general_qa", "fast_response", "tools", "coding"],
                        context_window=item.get("context_window", 128000) or 128000,
                        supports_tools=True,
                        supports_web=True,
                        supports_vision=False,
                        supports_code=True,
                        supports_streaming=True,
                        supports_reasoning=True,
                        supports_structured_output=True,
                        coding_suitability=0.88,
                        reasoning_suitability=0.88,
                        relative_cost="low",
                        relative_latency="ultra_fast",
                        availability=True,
                        status=ProviderStatus.HEALTHY.value,
                    )
                    self.register(meta)
                    discovered.append(meta)
        except Exception as e:
            logger.debug("Groq dynamic discovery skipped: %s", e)
        return discovered

    def _discover_openai(self) -> List[ModelMetadata]:
        """Query OpenAI /v1/models endpoint if key is configured."""
        if not settings.OPENAI_API_KEY:
            return []
        import requests
        discovered: List[ModelMetadata] = []
        try:
            headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            res = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                relevant = [m.get("id") for m in data.get("data", []) if m.get("id") and any(k in m.get("id") for k in ["gpt-4", "o1", "o3", "chatgpt"])]
                for m_id in relevant[:10]:
                    meta = ModelMetadata(
                        provider="openai",
                        model_id=m_id,
                        display_name=f"OpenAI {m_id}",
                        capabilities=["chat", "general_qa", "coding", "tools", "reasoning"],
                        context_window=128000,
                        supports_tools=True,
                        supports_web=True,
                        supports_vision=True,
                        supports_code=True,
                        supports_streaming=True,
                        supports_reasoning=True,
                        supports_structured_output=True,
                        coding_suitability=0.92,
                        reasoning_suitability=0.94,
                        relative_cost="medium",
                        relative_latency="fast",
                        availability=True,
                        status=ProviderStatus.HEALTHY.value,
                    )
                    self.register(meta)
                    discovered.append(meta)
        except Exception as e:
            logger.debug("OpenAI dynamic discovery skipped: %s", e)
        return discovered


_MODEL_REGISTRY = ModelRegistry()

def get_model_registry() -> ModelRegistry:
    """Access the singleton ModelRegistry instance."""
    return _MODEL_REGISTRY
