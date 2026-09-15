"""Tests for Phase I: Provider Health Probing & Dynamic Fallback Cascade.

Verifies:
1. Error classification (429 quota, 404 deprecation, 503 outage / no capacity, 401 auth, transient timeout).
2. Circuit breaker state machine (CLOSED -> OPEN on threshold, cooldown, HALF_OPEN probe, recovery to CLOSED).
3. Immediate circuit breaker trip on quota exhaustion (429) or no capacity (503).
4. ModelRouter affinity bypass of models with OPEN circuit breakers.
5. End-to-end fallback cascade execution across providers.
6. check_llm_health() reporting of circuit breaker state and telemetry.
"""

import sys
import os
import time
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.health import (
    CircuitState,
    ErrorCategory,
    ErrorClassifier,
    ModelHealthRecord,
    ProviderHealthTracker,
    get_health_tracker,
)
from app.models.router import get_model_router, ModelRouter
from app.models.provider import check_llm_health, ProviderRegistry, FallbackGroundedProvider
from app.models.base import LLMRequest, LLMResponse, ProviderStatus


def test_error_classifier_categories():
    """Verify ErrorClassifier accurately categorizes diverse HTTP codes and exception strings."""
    # 1. Quota Exhaustion (429)
    cat, reason = ErrorClassifier.classify(status_code=429)
    assert cat == ErrorCategory.QUOTA_EXHAUSTED
    assert "429" in reason

    cat, _ = ErrorClassifier.classify("RESOURCE_EXHAUSTED: quota exceeded for quota group")
    assert cat == ErrorCategory.QUOTA_EXHAUSTED

    # 2. Not Found / Deprecated (404)
    cat, reason = ErrorClassifier.classify(status_code=404)
    assert cat == ErrorCategory.NOT_FOUND
    assert "404" in reason

    cat, _ = ErrorClassifier.classify("Model gemini-1.0-pro does not exist or is deprecated")
    assert cat == ErrorCategory.NOT_FOUND

    # 3. Auth Failure (401 / 403)
    cat, _ = ErrorClassifier.classify(status_code=401)
    assert cat == ErrorCategory.AUTH_FAILURE

    cat, _ = ErrorClassifier.classify("Invalid API key provided: unauthorized")
    assert cat == ErrorCategory.AUTH_FAILURE

    # 4. Server Error & Capacity Outage (503 / no capacity)
    cat, _ = ErrorClassifier.classify(status_code=503)
    assert cat == ErrorCategory.SERVER_ERROR

    cat, reason = ErrorClassifier.classify("Error: UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash on the server")
    assert cat == ErrorCategory.SERVER_ERROR
    assert "no capacity" in reason.lower() or "overloaded" in reason.lower()

    # 5. Transient Network / Timeout
    cat, _ = ErrorClassifier.classify(Exception("Connection reset by peer: RemoteDisconnected"))
    assert cat == ErrorCategory.TRANSIENT

    cat, _ = ErrorClassifier.classify("Request timed out after 30000ms")
    assert cat == ErrorCategory.TRANSIENT


def test_circuit_breaker_state_transitions():
    """Verify circuit breaker transitions: CLOSED -> OPEN after 3 failures -> HALF_OPEN after cooldown -> CLOSED."""
    record = ModelHealthRecord(
        provider="mock_prov",
        model_id="mock_model",
        failure_threshold=3,
        base_cooldown_seconds=0.1,  # Fast 100ms cooldown for testing
    )

    # Initial state: CLOSED and available
    assert record.circuit_state == CircuitState.CLOSED
    assert record.is_available() is True

    # 1st failure: remains CLOSED
    record.record_failure(ErrorCategory.TRANSIENT, "Timeout 1")
    assert record.consecutive_failures == 1
    assert record.circuit_state == CircuitState.CLOSED
    assert record.is_available() is True

    # 2nd failure: remains CLOSED
    record.record_failure(ErrorCategory.TRANSIENT, "Timeout 2")
    assert record.consecutive_failures == 2
    assert record.circuit_state == CircuitState.CLOSED
    assert record.is_available() is True

    # 3rd failure: reaches threshold -> OPENS
    record.record_failure(ErrorCategory.TRANSIENT, "Timeout 3")
    assert record.consecutive_failures == 3
    assert record.circuit_state == CircuitState.OPEN
    assert record.is_available() is False

    # During cooldown: remains OPEN and unavailable
    assert record.is_available() is False

    # Wait for cooldown to expire
    time.sleep(0.12)

    # Cooldown expired: transitions to HALF_OPEN to allow probe request
    assert record.is_available() is True
    assert record.circuit_state == CircuitState.HALF_OPEN

    # Probe succeeds: closes circuit back to CLOSED and resets consecutive failures
    record.record_success(latency_ms=45.2)
    assert record.circuit_state == CircuitState.CLOSED
    assert record.consecutive_failures == 0
    assert record.total_successes == 1
    assert record.is_available() is True


def test_quota_and_capacity_immediate_circuit_trip():
    """Verify 429 quota exhaustion or 503 no capacity immediately trips circuit without waiting for 3 failures."""
    tracker = ProviderHealthTracker()

    # Quota exhaustion failure
    tracker.record_failure(
        provider="gemini",
        model_id="gemini-3.5-flash-test",
        status_code=429,
        error="ResourceExhausted quota exceeded",
    )

    rec = tracker.get_record("gemini", "gemini-3.5-flash-test")
    # Must immediately open on 1st failure
    assert rec.consecutive_failures == 1
    assert rec.circuit_state == CircuitState.OPEN
    assert tracker.is_available("gemini", "gemini-3.5-flash-test") is False

    # Server 503 capacity exhaustion failure
    tracker.record_failure(
        provider="gemini",
        model_id="gemini-3.8-preview",
        error="Error: UNAVAILABLE (code 503): No capacity available for model gemini-3.8-preview on the server",
    )
    rec_cap = tracker.get_record("gemini", "gemini-3.8-preview")
    assert rec_cap.circuit_state == CircuitState.OPEN
    assert tracker.is_available("gemini", "gemini-3.8-preview") is False


def test_model_router_bypasses_open_circuits():
    """Verify ModelRouter.route() detects OPEN circuit breaker on a top model and automatically routes to healthy candidate."""
    tracker = get_health_tracker()
    tracker.reset()

    router = get_model_router()

    # Normal routing to best available model
    decision_normal = router.route(task_type="general_qa")
    assert decision_normal.provider in ("gemini", "fallback")

    # Trip circuit breaker for gemini-3.5-flash
    tracker.record_failure(
        provider="gemini",
        model_id="gemini-3.5-flash",
        status_code=429,
        error="Rate limit reached",
    )

    # Router should now bypass gemini-3.5-flash and select next healthiest model (e.g. gemini-3.5-flash-lite or fallback)
    decision_after_trip = router.route(task_type="general_qa")
    assert decision_after_trip.model_id != "gemini-3.5-flash"
    assert tracker.is_available("gemini", "gemini-3.5-flash") is False

    # Cleanup
    tracker.reset()


def test_router_execute_fallback_cascade():
    """Verify ModelRouter.execute() cascades through candidates and marks response when fallback occurs."""
    tracker = get_health_tracker()
    tracker.reset()

    router = get_model_router()

    # Trip circuit on all external providers to force deterministic cascade to fallback
    for p in ["openai", "anthropic", "gemini", "groq", "ollama"]:
        tracker.record_failure(
            provider=p,
            model_id=None,
            status_code=503,
            error="Simulated upstream outage for cascade test",
        )

    req = LLMRequest(prompt="What is product-market fit?", system_prompt="Answer directly.")
    response = router.execute(req, task_type="general_qa")

    assert isinstance(response, LLMResponse)
    assert response.provider == "fallback"
    assert response.status == "FALLBACK"
    assert len(response.content) > 10

    # Cleanup
    tracker.reset()


def test_health_endpoint_reports_circuit_breakers():
    """Verify check_llm_health() includes circuit breaker telemetry."""
    tracker = get_health_tracker()
    tracker.reset()

    # Record 1 success and 1 failure to populate records
    tracker.record_success("gemini", "gemini-3.5-flash", latency_ms=120.5)
    tracker.record_failure("gemini", "gemini-3.8-flash-test", status_code=503, error="No capacity available")

    health_data = check_llm_health()

    assert "circuit_breakers" in health_data
    cb = health_data["circuit_breakers"]
    assert "gemini:gemini-3.5-flash" in cb
    assert "gemini:gemini-3.8-flash-test" in cb

    # Verify active healthy model
    assert cb["gemini:gemini-3.5-flash"]["circuit_state"] == CircuitState.CLOSED.value
    assert cb["gemini:gemini-3.5-flash"]["total_successes"] == 1

    # Verify tripped model
    assert cb["gemini:gemini-3.8-flash-test"]["circuit_state"] == CircuitState.OPEN.value
    assert cb["gemini:gemini-3.8-flash-test"]["consecutive_failures"] == 1

    # Cleanup
    tracker.reset()
