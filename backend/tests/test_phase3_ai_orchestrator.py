"""Comprehensive Test Suite for Phase 3: Unified AI Orchestrator.

Tests:
1. IntentUnderstanding semantic intent parsing across diverse domains.
2. Multi-capability routing across all 14 capabilities.
3. Compound multi-capability request deconstruction (e.g. Research + Coding + Verification).
4. TaskPlanner execution plan DAG generation.
5. VerificationEngine code syntax validation and grounding check.
6. Full end-to-end processing across 20+ representative requests.
"""

import os
import sys
import pytest

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.orchestrator.types import (
    Capability,
    IntentProfile,
    ExecutionPlan,
    VerificationResult,
    OrchestratorRequest,
    OrchestratorResponse,
)
from app.orchestrator.intent import IntentUnderstanding
from app.orchestrator.capability_router import CapabilityRouter
from app.orchestrator.planner import TaskPlanner
from app.orchestrator.verification import VerificationEngine
from app.orchestrator.orchestrator import AIOrchestrator, get_ai_orchestrator


@pytest.fixture
def intent_engine():
    return IntentUnderstanding()


@pytest.fixture
def router():
    return CapabilityRouter()


@pytest.fixture
def planner():
    return TaskPlanner()


@pytest.fixture
def verifier():
    return VerificationEngine()


@pytest.fixture
def orchestrator():
    return get_ai_orchestrator()


# ============================================================================
# REPRESENTATIVE REQUEST 1: GENERAL_QA (Conceptual Science)
# ============================================================================
def test_query_01_general_qa_science(intent_engine, router):
    q = "Explain how quantum entanglement works in simple terms."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.GENERAL_QA in caps
    assert Capability.CODING not in caps
    assert Capability.LENNY_RESEARCH not in caps


# ============================================================================
# REPRESENTATIVE REQUEST 2: GENERAL_QA (Mathematics)
# ============================================================================
def test_query_02_general_qa_math(intent_engine, router):
    q = "What is the mathematical definition and formula for a Fourier Transform?"
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.GENERAL_QA in caps
    assert Capability.RESEARCH not in caps


# ============================================================================
# REPRESENTATIVE REQUEST 3: RESEARCH (Current Government / Politics)
# ============================================================================
def test_query_03_research_government_cm(intent_engine, router):
    q = "Who is the current Chief Minister of Andhra Pradesh?"
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.RESEARCH in caps
    assert Capability.LENNY_RESEARCH not in caps
    assert intent.is_time_sensitive is True
    assert "Andhra Pradesh" in intent.entities


# ============================================================================
# REPRESENTATIVE REQUEST 4: RESEARCH (Latest Software Version)
# ============================================================================
def test_query_04_research_current_event(intent_engine, router):
    q = "What is the latest stable release of React in 2026?"
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.RESEARCH in caps
    assert intent.is_time_sensitive is True


# ============================================================================
# REPRESENTATIVE REQUEST 5: DEEP_RESEARCH (Multi-source DB Comparison)
# ============================================================================
def test_query_05_deep_research_comparison(intent_engine, router):
    q = "Compare PostgreSQL vs MongoDB for high-write time-series workloads in 2026."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DEEP_RESEARCH in caps


# ============================================================================
# REPRESENTATIVE REQUEST 6: DEEP_RESEARCH (Market Analysis)
# ============================================================================
def test_query_06_deep_research_market(intent_engine, router):
    q = "Comprehensive deep research on AI agent framework enterprise adoption in 2026."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DEEP_RESEARCH in caps


# ============================================================================
# REPRESENTATIVE REQUEST 7: CODING (Algorithm Implementation)
# ============================================================================
def test_query_07_coding_algorithm(intent_engine, router):
    q = "Write a C++ program to reverse a string in-place."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.CODING in caps
    assert "C++" in intent.entities


# ============================================================================
# REPRESENTATIVE REQUEST 8: CODING (Data Script)
# ============================================================================
def test_query_08_coding_script(intent_engine, router):
    q = "Write a Python script to parse nginx access logs and count HTTP 500 errors."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.CODING in caps
    assert "Python" in intent.entities


# ============================================================================
# REPRESENTATIVE REQUEST 9: DEBUGGING (Stack Trace)
# ============================================================================
def test_query_09_debugging_stack_trace(intent_engine, router):
    q = "Debug this Python traceback: IndexError: list index out of range at line 42."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DEBUGGING in caps


# ============================================================================
# REPRESENTATIVE REQUEST 10: DEBUGGING (API Failure)
# ============================================================================
def test_query_10_debugging_api_failure(intent_engine, router):
    q = "Fix this error: why is my API returning 500 when sending invalid JSON payload?"
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DEBUGGING in caps


# ============================================================================
# REPRESENTATIVE REQUEST 11: CODE_REVIEW (Security Audit)
# ============================================================================
def test_query_11_code_review_security(intent_engine, router):
    q = "Perform a code review of this JWT token verification function for security flaws."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.CODE_REVIEW in caps


# ============================================================================
# REPRESENTATIVE REQUEST 12: CODE_REVIEW (PR Inspection)
# ============================================================================
def test_query_12_code_review_pr(intent_engine, router):
    q = "Review this PR for potential memory leaks and query efficiency anti-patterns."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.CODE_REVIEW in caps


# ============================================================================
# REPRESENTATIVE REQUEST 13: ARCHITECTURE (Multi-Tenant Schema)
# ============================================================================
def test_query_13_architecture_database(intent_engine, router):
    q = "Design a multi-tenant database schema architecture for a B2B SaaS platform with row-level security."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.ARCHITECTURE in caps


# ============================================================================
# REPRESENTATIVE REQUEST 14: ARCHITECTURE (Distributed Pipeline)
# ============================================================================
def test_query_14_architecture_microservices(intent_engine, router):
    q = "Architect an event-driven payment processing pipeline using microservices and distributed queues."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.ARCHITECTURE in caps


# ============================================================================
# REPRESENTATIVE REQUEST 15: DATA_ANALYSIS (Cohort Retention)
# ============================================================================
def test_query_15_data_analysis_retention(intent_engine, router):
    q = "Calculate the 6-month cohort retention and churn rate given these monthly active user numbers."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DATA_ANALYSIS in caps


# ============================================================================
# REPRESENTATIVE REQUEST 16: DATA_ANALYSIS (SaaS Unit Economics)
# ============================================================================
def test_query_16_data_analysis_unit_economics(intent_engine, router):
    q = "Analyze our CAC, payback period, and LTV metrics based on our $50/month seat pricing."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DATA_ANALYSIS in caps


# ============================================================================
# REPRESENTATIVE REQUEST 17: DOCUMENT_ANALYSIS (Report Insights)
# ============================================================================
def test_query_17_document_analysis_pdf(intent_engine, router):
    q = "Extract key growth risks and competitive moats from this quarterly earnings transcript document."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.DOCUMENT_ANALYSIS in caps


# ============================================================================
# REPRESENTATIVE REQUEST 18: WRITING (Ship 30 Viral Essay)
# ============================================================================
def test_query_18_writing_viral_essay(intent_engine, router):
    q = "Draft a Ship 30 for 30 viral essay on why high-agency founders reject conventional empowerment."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.WRITING in caps


# ============================================================================
# REPRESENTATIVE REQUEST 19: PLANNING (Growth Experiment Roadmap)
# ============================================================================
def test_query_19_planning_experiment_roadmap(intent_engine, router):
    q = "Create a 6-week growth experiment roadmap with ICE score prioritization for our onboarding funnel."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.PLANNING in caps


# ============================================================================
# REPRESENTATIVE REQUEST 20: ARTIFACT_GENERATION (Growth Canvas Dashboard)
# ============================================================================
def test_query_20_artifact_generation_canvas(intent_engine, router):
    q = "Generate an interactive Growth Canvas dashboard visualizing user conversion drop-off."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.ARTIFACT_GENERATION in caps


# ============================================================================
# REPRESENTATIVE REQUEST 21: LENNY_RESEARCH (Founder Mode)
# ============================================================================
def test_query_21_lenny_research_chesky(intent_engine, router):
    q = "What did Brian Chesky say about founder mode and managing product on Lenny's podcast?"
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)
    assert Capability.LENNY_RESEARCH in caps
    assert intent.requires_lenny_knowledge is True
    assert "Brian Chesky" in intent.entities


# ============================================================================
# REPRESENTATIVE REQUEST 22: COMPOUND (Research + Coding + Verification)
# Example explicitly specified in Prompt:
# "Research current FastAPI authentication and implement it."
# ============================================================================
def test_query_22_compound_research_and_coding(intent_engine, router, planner):
    q = "Research current FastAPI authentication and implement it."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)

    # Must select both RESEARCH and CODING
    assert Capability.RESEARCH in caps
    assert Capability.CODING in caps

    # Plan must deconstruct into sequential steps
    plan = planner.plan(q, caps, intent)
    assert plan.is_compound is True
    assert len(plan.steps) >= 2
    step_caps = [s.capability for s in plan.steps]
    assert Capability.RESEARCH in step_caps
    assert Capability.CODING in step_caps


# ============================================================================
# REPRESENTATIVE REQUEST 23: COMPOUND (Data Analysis + Planning + Artifact)
# ============================================================================
def test_query_23_compound_data_plan_artifact(intent_engine, router, planner):
    q = "Analyze our churn metrics, create an experiment plan, and generate an interactive dashboard."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)

    assert Capability.DATA_ANALYSIS in caps
    assert Capability.PLANNING in caps
    assert Capability.ARTIFACT_GENERATION in caps

    plan = planner.plan(q, caps, intent)
    assert plan.is_compound is True
    assert len(plan.steps) >= 3


# ============================================================================
# REPRESENTATIVE REQUEST 24: COMPOUND (Review + Debug + Code)
# ============================================================================
def test_query_24_compound_review_debug_code(intent_engine, router, planner):
    q = "Review this code, find the security bug, and write the fix."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)

    assert Capability.CODE_REVIEW in caps
    assert Capability.DEBUGGING in caps
    assert Capability.CODING in caps

    plan = planner.plan(q, caps, intent)
    assert plan.is_compound is True


# ============================================================================
# REPRESENTATIVE REQUEST 25: COMPOUND (Lenny + Hybrid Market Research)
# ============================================================================
def test_query_25_compound_hybrid_lenny_market(intent_engine, router):
    q = "Combine Brian Chesky's turnaround principles with current 2026 SaaS activation benchmarks."
    intent = intent_engine.understand(q)
    caps = router.route(q, intent)

    assert Capability.HYBRID_TASK in caps or (Capability.RESEARCH in caps and Capability.LENNY_RESEARCH in caps)


# ============================================================================
# REPRESENTATIVE REQUEST 26: VERIFICATION ENGINE CODE SYNTAX CHECK
# ============================================================================
def test_verification_engine_code_validation(verifier):
    valid_code = "```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```"
    res_valid = verifier.verify("Implement add function", valid_code, [Capability.CODING], "", [])
    assert res_valid.code_syntax_valid is True
    assert res_valid.is_verified is True

    invalid_code = "```python\ndef broken(:\n    return\n```"
    res_invalid = verifier.verify("Implement function", invalid_code, [Capability.CODING], "", [])
    assert res_invalid.code_syntax_valid is False
    assert res_invalid.is_verified is False
    assert len(res_invalid.issues) > 0


# ============================================================================
# REPRESENTATIVE REQUEST 27: END-TO-END AI ORCHESTRATOR PASS
# ============================================================================
def test_orchestrator_end_to_end_pass(orchestrator):
    req = OrchestratorRequest(
        query="Research current FastAPI authentication and implement it.",
        session_id="test_orchestrator_session",
    )
    resp = orchestrator.process(req)

    assert isinstance(resp, OrchestratorResponse)
    assert Capability.RESEARCH in resp.selected_capabilities
    assert Capability.CODING in resp.selected_capabilities
    assert resp.plan.is_compound is True
    assert len(resp.content) > 50
    assert resp.verification is not None
    assert resp.total_latency_ms > 0
    assert "intent_understanding_ms" in resp.latency_breakdown
    assert "capability_routing_ms" in resp.latency_breakdown
    assert "task_planning_ms" in resp.latency_breakdown
    assert "inference_ms" in resp.latency_breakdown
    assert "verification_ms" in resp.latency_breakdown
