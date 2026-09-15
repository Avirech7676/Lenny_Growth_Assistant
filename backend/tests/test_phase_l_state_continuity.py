"""Phase L Test Suite: Multi-Turn Model State Continuity and Compaction.

Validates:
1. SessionState initialization, turn tracking, and artifact reference preservation.
2. Cross-model transition detection across turns (Gemini -> Groq -> OpenAI).
3. Compaction threshold triggers based on conversation length.
4. Structured conversational memory summary (<conversation_summary>) generation.
5. Sliding-window verbatim turn preservation (keeping recent turns in full fidelity).
6. State continuity preparation and role normalization.
"""

import sys
import os
import pytest

# Ensure backend root is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.continuity import (
    ModelTransition,
    SessionState,
    StateContinuityManager,
    get_state_continuity_manager,
)


def test_session_state_creation_and_turn_recording():
    """Verify StateContinuityManager initializes and updates session state."""
    mgr = StateContinuityManager()
    session_id = "test-session-001"

    state = mgr.get_or_create_state(session_id)
    assert state.session_id == session_id
    assert state.total_turns == 0
    assert state.current_model is None

    # Record Turn 1
    transition1 = mgr.record_turn(session_id, active_model="gemini-3.5-flash", active_provider="gemini")
    assert transition1 is None  # First turn, no transition yet
    assert state.total_turns == 1
    assert state.current_model == "gemini-3.5-flash"
    assert state.current_provider == "gemini"


def test_cross_model_transition_detection():
    """Verify switching models mid-session creates a clear ModelTransition record."""
    mgr = StateContinuityManager()
    session_id = "test-session-002"

    # Turn 1: Gemini
    mgr.record_turn(session_id, active_model="gemini-3.5-flash", active_provider="gemini")

    # Turn 2: Switch to Groq
    transition = mgr.record_turn(session_id, active_model="llama-3.3-70b-versatile", active_provider="groq")
    assert transition is not None
    assert transition.from_model == "gemini-3.5-flash"
    assert transition.to_model == "llama-3.3-70b-versatile"
    assert transition.from_provider == "gemini"
    assert transition.to_provider == "groq"

    # Turn 3: Same model, no transition
    no_trans = mgr.record_turn(session_id, active_model="llama-3.3-70b-versatile", active_provider="groq")
    assert no_trans is None

    # Verify history of transitions in session state
    state = mgr.get_or_create_state(session_id)
    assert len(state.model_transitions) == 1
    assert state.total_turns == 3


def test_compaction_threshold():
    """Verify needs_compaction triggers only when history exceeds turn threshold."""
    mgr = StateContinuityManager(compaction_threshold_turns=6)

    # 4 turns: within threshold
    short_history = [{"role": "user", "content": f"Turn {i}"} for i in range(4)]
    assert mgr.needs_compaction(short_history) is False

    # 8 turns: exceeds threshold
    long_history = [{"role": "user", "content": f"Turn {i}"} for i in range(8)]
    assert mgr.needs_compaction(long_history) is True


def test_compact_history_structure():
    """Verify compact_history formats older turns into <conversation_summary> while keeping recent turns."""
    mgr = StateContinuityManager(compaction_threshold_turns=6, verbatim_recent_turns=3)
    session_id = "test-session-003"

    history = [
        {"role": "user", "content": "I want to analyze retention metrics for our B2B SaaS product."},
        {"role": "assistant", "content": "Let's examine net revenue retention and cohort churn over 12 months."},
        {"role": "user", "content": "Our CAC payback period is currently 18 months, which feels too high."},
        {"role": "assistant", "content": "An 18-month payback is stretched. Let's aim for 12 months using expansion loops."},
        {"role": "user", "content": "What pricing changes should we consider to improve ACV?"},
        {"role": "assistant", "content": "Consider adding usage-based tiers and enterprise governance add-ons."},
        {"role": "user", "content": "Can you summarize the top priority for this quarter?"},
        {"role": "assistant", "content": "The top priority is reducing churn in the 30-day onboarding window."},
        # Recent turns:
        {"role": "user", "content": "How should we instrument the onboarding funnel?"},
        {"role": "assistant", "content": "Track activation milestone events: workspace created, invite sent, first data query."},
        {"role": "user", "content": "What tool do you recommend for product analytics?"},
    ]

    compacted_hist, summary = mgr.compact_history(history, session_id=session_id)

    # Compaction must have occurred
    assert summary is not None
    assert len(summary) > 0

    # Summary block must be injected in first message
    first_msg = compacted_hist[0]
    assert "<conversation_summary>" in first_msg["content"]
    assert "</conversation_summary>" in first_msg["content"]

    # Recent turns must be preserved at the end of compacted history
    assert compacted_hist[-1]["content"] == "What tool do you recommend for product analytics?"
    assert compacted_hist[-2]["content"] == "Track activation milestone events: workspace created, invite sent, first data query."


def test_prepare_turn_full_pipeline():
    """Verify prepare_turn standardizes roles, tracks model switch, and applies compaction."""
    mgr = StateContinuityManager(compaction_threshold_turns=4, verbatim_recent_turns=2)
    session_id = "test-session-004"

    # History with non-standard roles
    raw_history = [
        {"role": "client", "content": "Initial inquiry."},
        {"role": "bot", "content": "Initial response."},
        {"role": "user", "content": "Turn 2 question."},
        {"role": "assistant", "content": "Turn 2 answer."},
        {"role": "user", "content": "Turn 3 question."},
        {"role": "assistant", "content": "Turn 3 answer."},
    ]

    # Turn 1 on Gemini
    hist_prepared, trans1 = mgr.prepare_turn(
        session_id=session_id,
        history=raw_history,
        active_model="gemini-3.5-flash",
        active_provider="gemini",
    )
    assert trans1 is None
    # All roles standardized to user/assistant
    for m in hist_prepared:
        assert m["role"] in ("user", "assistant", "system")

    # Turn 2: switch to OpenAI
    _, trans2 = mgr.prepare_turn(
        session_id=session_id,
        history=hist_prepared,
        active_model="gpt-4o",
        active_provider="openai",
    )
    assert trans2 is not None
    assert trans2.from_model == "gemini-3.5-flash"
    assert trans2.to_model == "gpt-4o"


def test_artifact_reference_continuity():
    """Verify artifacts referenced across turns are tracked in session state."""
    mgr = StateContinuityManager()
    session_id = "test-session-005"

    sample_artifacts = [
        {"id": "art_1", "title": "B2B Retention Strategy", "type": "playbook"},
        {"id": "art_2", "title": "Onboarding Experiment", "type": "experiment"},
    ]

    mgr.record_turn(
        session_id=session_id,
        active_model="gemini-3.5-flash",
        active_provider="gemini",
        artifacts=sample_artifacts,
    )

    state = mgr.get_or_create_state(session_id)
    assert len(state.referenced_artifacts) == 2
    assert state.referenced_artifacts[0]["title"] == "B2B Retention Strategy"
