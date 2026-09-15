"""Provider Health Probing, Circuit Breaker & Error Classification Engine.

Implements an active health tracking system for LLM providers and models:
- Error classification (transient vs quota vs outage vs 404 deprecation)
- Circuit breaker state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold & exponential cooldown
- Real-time provider health status aggregation
"""

import time
import re
import logging
from enum import Enum
from typing import Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"        # Normal operation: all requests pass through
    OPEN = "OPEN"            # Fail-fast: provider is failing, skip without network call
    HALF_OPEN = "HALF_OPEN"  # Testing: cooldown expired, allowing single probe request


class ErrorCategory(str, Enum):
    """Classified error categories for fine-grained failure handling."""
    TRANSIENT = "TRANSIENT"                  # Network timeout, socket disconnect, 503 spike (retryable)
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"      # 429 RateLimit, ResourceExhausted (immediate failover)
    NOT_FOUND = "NOT_FOUND"                  # 404 Model not found or deprecated (permanent failover)
    AUTH_FAILURE = "AUTH_FAILURE"            # 401 / 403 Invalid API key or permission denied
    SERVER_ERROR = "SERVER_ERROR"            # 500 Internal error, upstream provider crash
    UNKNOWN = "UNKNOWN"                      # Unclassified exception


class ErrorClassifier:
    """Classifies raw exceptions and status codes into structured ErrorCategory."""

    @staticmethod
    def classify(
        error: Union[Exception, str, None] = None,
        status_code: Optional[int] = None,
    ) -> Tuple[ErrorCategory, str]:
        """Examine error and HTTP status code to return category and clean explanation."""
        err_str = str(error or "").lower()

        # Status code checks first
        if status_code is not None:
            if status_code == 429:
                return ErrorCategory.QUOTA_EXHAUSTED, "HTTP 429: Rate limit or quota exhausted"
            if status_code == 404:
                return ErrorCategory.NOT_FOUND, "HTTP 404: Model not found or deprecated"
            if status_code in (401, 403):
                return ErrorCategory.AUTH_FAILURE, f"HTTP {status_code}: Authentication or permission failure"
            if status_code in (500, 502, 503, 504):
                return ErrorCategory.SERVER_ERROR, f"HTTP {status_code}: Upstream server error"

        # Content/Exception message checks
        # 1. Quota & Rate Limits
        if any(k in err_str for k in [
            "429", "rate limit", "ratelimit", "quota", "resource_exhausted",
            "resourceexhausted", "too many requests", "insufficient_quota", "quota_exceeded"
        ]):
            return ErrorCategory.QUOTA_EXHAUSTED, "Rate limit or quota exhausted"

        # 2. Model Not Found / Deprecated
        if any(k in err_str for k in [
            "404", "not found", "does not exist", "unsupported model", "deprecated model",
            "model_not_found", "model not found"
        ]):
            return ErrorCategory.NOT_FOUND, "Model not found or deprecated"

        # 3. Authentication Failures
        if any(k in err_str for k in [
            "401", "403", "unauthorized", "invalid api key", "invalid_api_key",
            "permission denied", "forbidden", "authentication"
        ]):
            return ErrorCategory.AUTH_FAILURE, "Authentication or API key invalid"

        # 4. Upstream Server Outages
        if any(k in err_str for k in [
            "500", "502", "503", "504", "bad gateway", "service unavailable",
            "gateway timeout", "upstream server", "internal server error", "overloaded",
            "high demand", "no capacity available", "no capacity", "unavailable (code 503)"
        ]):
            return ErrorCategory.SERVER_ERROR, "Upstream provider server error or overloaded (no capacity)"

        # 5. Transient Network / Socket Issues
        if any(k in err_str for k in [
            "timeout", "timed out", "connection reset", "remotedisconnected",
            "connection refused", "network unreachable", "dns", "ssl", "econnreset"
        ]):
            return ErrorCategory.TRANSIENT, "Transient network or socket timeout"

        return ErrorCategory.UNKNOWN, err_str or "Unknown error"


@dataclass
class ModelHealthRecord:
    """Tracks circuit state and health metrics for a specific provider/model."""
    provider: str
    model_id: str
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_time: Optional[float] = None
    last_failure_reason: Optional[str] = None
    last_error_category: Optional[ErrorCategory] = None
    cooldown_until: Optional[float] = None
    last_latency_ms: Optional[float] = None
    failure_threshold: int = 3
    base_cooldown_seconds: float = 30.0

    def is_available(self) -> bool:
        """Evaluate if requests can be routed to this provider/model."""
        now = time.time()

        if self.circuit_state == CircuitState.CLOSED:
            return True

        if self.circuit_state == CircuitState.OPEN:
            if self.cooldown_until and now >= self.cooldown_until:
                logger.info(
                    "Circuit breaker cooldown expired for %s:%s. Transitioning to HALF_OPEN probe state.",
                    self.provider, self.model_id
                )
                self.circuit_state = CircuitState.HALF_OPEN
                return True
            return False

        if self.circuit_state == CircuitState.HALF_OPEN:
            # In HALF_OPEN state, allow the probe attempt
            return True

        return True

    def record_success(self, latency_ms: float = 0.0) -> None:
        """Record successful invocation, closing circuit and resetting failure counts."""
        self.total_successes += 1
        self.consecutive_failures = 0
        self.last_latency_ms = max(latency_ms, 0.1)
        self.cooldown_until = None

        if self.circuit_state != CircuitState.CLOSED:
            logger.info(
                "Circuit breaker CLOSED for %s:%s after successful probe (latency: %.2fms).",
                self.provider, self.model_id, latency_ms
            )
            self.circuit_state = CircuitState.CLOSED

    def record_failure(
        self,
        category: ErrorCategory,
        reason: str,
        cooldown_override: Optional[float] = None,
    ) -> None:
        """Record failure, incrementing counters and opening circuit breaker when appropriate."""
        now = time.time()
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = now
        self.last_failure_reason = reason
        self.last_error_category = category

        # Determine if circuit should open immediately
        should_open = False
        cooldown_duration = cooldown_override or self.base_cooldown_seconds

        if category == ErrorCategory.QUOTA_EXHAUSTED or (
            category == ErrorCategory.SERVER_ERROR and any(k in reason.lower() for k in ["no capacity", "503", "unavailable", "capacity"])
        ):
            # 429 quota or 503 capacity exhaustion: immediate open with longer cooldown (60s minimum)
            should_open = True
            cooldown_duration = max(cooldown_duration, 60.0)
        elif category in (ErrorCategory.NOT_FOUND, ErrorCategory.AUTH_FAILURE):
            # Permanent configuration or deprecation error: immediate open with long cooldown
            should_open = True
            cooldown_duration = 86400.0  # 24 hours
        elif self.consecutive_failures >= self.failure_threshold:
            # Multiple consecutive transient/server errors reached threshold
            should_open = True
            # Exponential backoff based on consecutive failures beyond threshold
            exponent = min(self.consecutive_failures - self.failure_threshold, 4)
            cooldown_duration = self.base_cooldown_seconds * (2 ** exponent)

        if should_open:
            self.circuit_state = CircuitState.OPEN
            self.cooldown_until = now + cooldown_duration
            logger.warning(
                "Circuit breaker OPENED for %s:%s. Category: %s. Reason: %s. Cooldown: %.1fs.",
                self.provider, self.model_id, category.value, reason, cooldown_duration
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize health record for telemetry and API responses."""
        now = time.time()
        remaining_cooldown = max(0.0, round(self.cooldown_until - now, 1)) if self.cooldown_until else 0.0
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "circuit_state": self.circuit_state.value,
            "is_available": self.is_available(),
            "consecutive_failures": self.consecutive_failures,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "last_error_category": self.last_error_category.value if self.last_error_category else None,
            "last_failure_reason": self.last_failure_reason,
            "cooldown_remaining_sec": remaining_cooldown,
            "last_latency_ms": self.last_latency_ms,
        }


class ProviderHealthTracker:
    """Central registry of provider and model circuit breakers and health metrics."""

    def __init__(self):
        self._records: Dict[str, ModelHealthRecord] = {}
        self.classifier = ErrorClassifier()

    def _key(self, provider: str, model_id: Optional[str] = None) -> str:
        prov = (provider or "unknown").strip().lower()
        mod = (model_id or "default").strip().lower()
        return f"{prov}:{mod}"

    def get_record(self, provider: str, model_id: Optional[str] = None) -> ModelHealthRecord:
        """Get or initialize health record for provider/model."""
        key = self._key(provider, model_id)
        if key not in self._records:
            self._records[key] = ModelHealthRecord(
                provider=provider.strip().lower(),
                model_id=(model_id or "default").strip().lower(),
            )
        return self._records[key]

    def is_available(self, provider: str, model_id: Optional[str] = None) -> bool:
        """Check if provider and model are available (circuit is not OPEN)."""
        prov_key = self._key(provider, None)
        model_key = self._key(provider, model_id)

        # Check provider-level circuit
        if prov_key in self._records and not self._records[prov_key].is_available():
            return False

        # Check model-level circuit
        if model_key in self._records and not self._records[model_key].is_available():
            return False

        return True

    def record_success(
        self,
        provider: str,
        model_id: Optional[str] = None,
        latency_ms: float = 0.0,
    ) -> None:
        """Mark model and provider as successful."""
        rec = self.get_record(provider, model_id)
        rec.record_success(latency_ms)

        # Also update provider-level record
        prov_rec = self.get_record(provider, None)
        prov_rec.record_success(latency_ms)

    def record_failure(
        self,
        provider: str,
        model_id: Optional[str] = None,
        error: Union[Exception, str, None] = None,
        status_code: Optional[int] = None,
        cooldown_override: Optional[float] = None,
    ) -> Tuple[ErrorCategory, str]:
        """Classify and record failure, triggering circuit breaker logic."""
        category, reason = self.classifier.classify(error, status_code)

        rec = self.get_record(provider, model_id)
        rec.record_failure(category, reason, cooldown_override)

        # If auth failure, or quota/server failure without specific model, also open provider-level circuit
        if category == ErrorCategory.AUTH_FAILURE or (category in (ErrorCategory.QUOTA_EXHAUSTED, ErrorCategory.SERVER_ERROR) and not model_id):
            prov_rec = self.get_record(provider, None)
            prov_rec.record_failure(category, reason, cooldown_override)

        return category, reason

    def reset_circuit(self, provider: str, model_id: Optional[str] = None) -> None:
        """Manually reset a circuit breaker to CLOSED state."""
        key = self._key(provider, model_id)
        if key in self._records:
            self._records[key].circuit_state = CircuitState.CLOSED
            self._records[key].consecutive_failures = 0
            self._records[key].cooldown_until = None

    def get_status_summary(self) -> Dict[str, Any]:
        """Return overall health status across all tracked models and providers."""
        return {
            key: record.to_dict()
            for key, record in self._records.items()
        }

    def reset(self) -> None:
        """Completely reset all tracking state (used in tests)."""
        self._records.clear()


# Singleton Instance
_HEALTH_TRACKER = ProviderHealthTracker()


def get_health_tracker() -> ProviderHealthTracker:
    """Access the singleton ProviderHealthTracker."""
    return _HEALTH_TRACKER
