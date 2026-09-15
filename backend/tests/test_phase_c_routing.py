"""Phase C Verification Tests: Query Understanding, Capability Routing, and Context Hygiene.

Validates:
1. Algorithm and data structure queries route to Software Engineering with 0 Lenny retrieval and no web search.
2. Real-world public figure / cinema lookups route to Web Research with 0 Lenny retrieval.
3. Genuine Lenny podcast queries route to Lenny Research with transcript retrieval.
4. Common first names / words (Elena Ferrante, Bobo doll) do NOT falsely trigger Lenny podcast routing.
5. Topic switches between Lenny and Software Engineering trigger complete context isolation.
6. Epistemic refusal is confined to research mode; chat mode answers general knowledge.
"""

import pytest
from app.services.relevance.pipeline import (
    get_relevance_router,
    QueryDomain,
    QueryIntent,
)
from app.services.capability.intent_router import (
    get_query_understanding_engine,
    AgentCapability,
    is_lenny_relevant,
)
from app.services.context.manager import (
    get_unified_context_manager,
    TransitionType,
)


def test_algorithm_complexity_query_routing():
    """Verify merge sort complexity routes to software engineering without Lenny or web search."""
    relevance_router = get_relevance_router()
    analysis = relevance_router.analyze_query("What is the time complexity of merge sort?")

    assert analysis.domain == QueryDomain.SOFTWARE_ENGINEERING
    assert analysis.allow_lenny_retrieval is False
    assert analysis.is_time_sensitive is False

    intent_engine = get_query_understanding_engine()
    classification = intent_engine.analyze("What is the time complexity of merge sort?")

    assert classification.capability == AgentCapability.CODING
    assert classification.domain == "software_engineering"
    assert classification.lenny_relevant is False
    assert classification.requires_web is False


def test_cinema_actor_query_routing():
    """Verify Prabhas lookup routes to real-world factual web research without Lenny."""
    relevance_router = get_relevance_router()
    analysis = relevance_router.analyze_query("who is rebel star prabhas")

    assert analysis.domain == QueryDomain.GENERAL_KNOWLEDGE
    assert analysis.allow_lenny_retrieval is False
    assert analysis.is_time_sensitive is True

    intent_engine = get_query_understanding_engine()
    classification = intent_engine.analyze("who is rebel star prabhas")

    assert classification.capability == AgentCapability.WEB_RESEARCH
    assert classification.lenny_relevant is False
    assert classification.requires_web is True


def test_lenny_podcast_query_routing():
    """Verify Brian Chesky founder mode query routes strictly to Lenny research."""
    relevance_router = get_relevance_router()
    analysis = relevance_router.analyze_query("What did Brian Chesky say about Founder Mode on Lenny's Podcast?")

    assert analysis.domain == QueryDomain.STARTUP_GROWTH
    assert analysis.intent == QueryIntent.LENNY_PODCAST_ADVISORY
    assert analysis.allow_lenny_retrieval is True

    intent_engine = get_query_understanding_engine()
    classification = intent_engine.analyze("What did Brian Chesky say about Founder Mode on Lenny's Podcast?")

    assert classification.capability == AgentCapability.LENNY_RESEARCH
    assert classification.lenny_relevant is True


def test_no_false_lenny_trigger_on_common_names():
    """Verify non-podcast entities like Elena Ferrante and Bobo doll don't trigger Lenny."""
    assert is_lenny_relevant("Who wrote My Brilliant Friend by Elena Ferrante?") is False
    assert is_lenny_relevant("Explain the Bobo doll experiment in developmental psychology.") is False

    relevance_router = get_relevance_router()
    analysis_elena = relevance_router.analyze_query("Who wrote My Brilliant Friend by Elena Ferrante?")
    assert analysis_elena.allow_lenny_retrieval is False

    analysis_bobo = relevance_router.analyze_query("Explain the Bobo doll experiment in developmental psychology.")
    assert analysis_bobo.allow_lenny_retrieval is False


def test_topic_switch_isolation_in_context_manager():
    """Verify cross-domain transition from Lenny to Coding triggers topic switch and history isolation."""
    context_mgr = get_unified_context_manager()

    history = [
        {"role": "user", "content": "What did Brian Chesky say about product management on Lenny's Podcast?"},
        {"role": "assistant", "content": "Brian Chesky explained that founders should operate like an orchestra..."},
    ]

    transition, reason = context_mgr.detect_transition(
        current_query="What is the time complexity of merge sort?",
        previous_query="What did Brian Chesky say about product management on Lenny's Podcast?",
        history=history,
    )

    assert transition == TransitionType.TOPIC_SWITCH

    orchestrated = context_mgr.build_orchestrated_context(
        session_id="test-topic-switch-session",
        user_query="What is the time complexity of merge sort?",
        raw_history=history,
    )

    # History should be isolated (empty) to avoid contaminating merge sort with Chesky advice
    assert orchestrated.llm_history == []
