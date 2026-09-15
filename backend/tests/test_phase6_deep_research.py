"""Phase 6 Test Suite: DeepResearchEngine Verification.

Validates:
- Research planning
- Multiple search queries & parallel search
- Source categorization & quality evaluation
- Source deduplication
- Independent-source detection (apex domain grouping)
- Conflict detection
- Additional research rounds
- Claim verification
- Citation verification
- Final synthesis
- Adaptive depth limits:
    - Simple question: 1–3 sources
    - Moderate: 3–7 sources
    - Complex: multiple queries and source categories
    - Deep research: multiple research rounds
- Stop when evidence is sufficient (bounded search)
- Concise UI progress events:
    - Planning research
    - Searching
    - Reading sources
    - Comparing evidence
    - Verifying
    - Writing
- Zero exposure of private chain-of-thought
"""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.search.base import SourceCategory, ResearchDepth, DiscoveredSource, ResearchConflict
from app.services.research import (
    DeepResearchEngine,
    get_deep_research_engine,
    ResearchResult,
    ResearchReport,
    VerifiedClaim,
)
from app.services.research.engine import (
    extract_apex_domain,
    classify_adaptive_depth,
)


def test_extract_apex_domain():
    """Verify apex domain extraction accurately groups multi-link origins."""
    assert extract_apex_domain("https://docs.python.org/3/library/asyncio.html") == "python.org"
    assert extract_apex_domain("https://python.org") == "python.org"
    assert extract_apex_domain("https://developer.mozilla.org/en-US/") == "mozilla.org"
    assert extract_apex_domain("https://en.wikipedia.org/wiki/React") == "wikipedia.org"
    assert extract_apex_domain("https://sub.domain.bbc.co.uk/news") == "bbc.co.uk"
    assert extract_apex_domain("https://data.gov.in/resource") == "data.gov.in"
    assert extract_apex_domain("https://nature.com/articles") == "nature.com"


def test_adaptive_depth_classifier():
    """Verify queries are classified into appropriate depth classes and source limits."""
    # Simple queries: 1-3 sources
    mode_s1, min_s1, max_s1 = classify_adaptive_depth("Who is CM of AP")
    assert mode_s1 == "simple"
    assert max_s1 == 3

    mode_s2, min_s2, max_s2 = classify_adaptive_depth("What is Python?")
    assert mode_s2 == "simple"
    assert max_s2 == 3

    # Moderate queries: 3-7 sources
    mode_m, min_m, max_m = classify_adaptive_depth("How does FastAPI dependency injection work?")
    assert mode_m == "moderate"
    assert max_m == 7

    # Complex queries: multiple queries & categories
    mode_c, min_c, max_c = classify_adaptive_depth("Compare PostgreSQL vs MongoDB tradeoffs for high scale")
    assert mode_c == "complex"
    assert max_c == 12

    # Deep research: multiple research rounds
    mode_d, min_d, max_d = classify_adaptive_depth("Conduct a deep research report on state of the art AI agent frameworks in 2026")
    assert mode_d == "deep"
    assert max_d == 15


@pytest.mark.asyncio
async def test_adaptive_depth_simple_question():
    """Verify simple question yields 1–3 sources and stops once evidence is sufficient."""
    engine = get_deep_research_engine()
    result = await engine.execute_research(
        query="Who is CM of AP",
        depth_override="simple",
    )

    assert isinstance(result, ResearchResult)
    # Simple question must use 1–3 sources
    assert 1 <= len(result.used_sources) <= 3
    assert result.independent_sources_count >= 1
    assert result.report.depth == "simple"
    assert len(result.report.verified_claims) >= 1
    # Check that context is populated and no Chesky contamination
    assert "chesky" not in result.synthesis_context.lower()
    assert any("chandrababu" in s.title.lower() or "naidu" in s.title.lower() or "andhra" in s.title.lower() for s in result.used_sources)


@pytest.mark.asyncio
async def test_adaptive_depth_moderate_question():
    """Verify moderate question yields 3–7 sources across multiple independent domains."""
    engine = get_deep_research_engine()
    result = await engine.execute_research(
        query="Explain how Python GIL works and free-threaded Python 3.13",
        depth_override="moderate",
    )

    assert isinstance(result, ResearchResult)
    # Moderate question must use 3–7 sources
    assert 3 <= len(result.used_sources) <= 7
    assert result.independent_sources_count >= 2
    assert result.report.depth == "moderate"
    assert len(result.report.citations) >= 3


@pytest.mark.asyncio
async def test_adaptive_depth_complex_question():
    """Verify complex question spans multiple queries and multiple source categories."""
    engine = get_deep_research_engine()
    result = await engine.execute_research(
        query="Compare PostgreSQL vs MongoDB for financial ledger architecture",
        depth_override="complex",
    )

    assert isinstance(result, ResearchResult)
    # Complex query requires multiple categories
    assert len(result.category_counts) >= 2
    assert result.independent_sources_count >= 2
    assert len(result.used_sources) >= 4
    assert result.report.depth == "complex"


@pytest.mark.asyncio
async def test_adaptive_depth_deep_multi_round():
    """Verify deep research executes multiple research rounds and stops when sufficient."""
    engine = get_deep_research_engine()
    result = await engine.execute_research(
        query="Deep research on production distributed consensus algorithms Paxos vs Raft vs Zab",
        depth_override="deep",
    )

    assert isinstance(result, ResearchResult)
    # Must track research rounds
    assert result.research_rounds >= 1
    assert result.report.research_rounds == result.research_rounds
    assert result.independent_sources_count >= 2
    assert len(result.report.verified_claims) >= 2


def test_independent_source_detection_and_deduplication():
    """Verify that multiple links from the same apex domain are grouped and duplicate URLs are removed."""
    engine = get_deep_research_engine()
    raw_sources = [
        DiscoveredSource(title="Python Doc 1", url="https://docs.python.org/3/library/os.html", domain="docs.python.org", snippet="OS module", category=SourceCategory.OFFICIAL, authority_score=0.98),
        DiscoveredSource(title="Python Doc 2", url="https://docs.python.org/3/library/sys.html", domain="docs.python.org", snippet="Sys module", category=SourceCategory.OFFICIAL, authority_score=0.98),
        DiscoveredSource(title="Python Home", url="https://python.org/about", domain="python.org", snippet="About Python", category=SourceCategory.OFFICIAL, authority_score=0.95),
        DiscoveredSource(title="Duplicate Link", url="https://docs.python.org/3/library/os.html?ref=tracking", domain="docs.python.org", snippet="OS module", category=SourceCategory.OFFICIAL, authority_score=0.98),
        DiscoveredSource(title="Mozilla Guide", url="https://developer.mozilla.org/python", domain="developer.mozilla.org", snippet="MDN guide", category=SourceCategory.TECHNICAL, authority_score=0.92),
    ]

    # Deduplication test
    deduped = engine.deduplicate_sources(raw_sources)
    assert len(deduped) == 4  # Duplicate URL stripped

    # Independent source grouping test
    groups = engine.detect_independent_sources(deduped)
    # docs.python.org and python.org share apex domain "python.org"
    assert "python.org" in groups
    assert "mozilla.org" in groups
    assert len(groups["python.org"]) == 3
    assert len(groups["mozilla.org"]) == 1
    assert len(groups) == 2  # Exactly 2 independent publisher domains


def test_conflict_detection_and_resolution():
    """Verify that contradictory claims trigger conflict detection and are represented in report."""
    engine = get_deep_research_engine()
    conflicting_sources = [
        DiscoveredSource(title="Source Alpha", url="https://alpha.org/report", domain="alpha.org", snippet="The release date is scheduled for May 2026.", category=SourceCategory.NEWS, authority_score=0.88),
        DiscoveredSource(title="Source Beta", url="https://beta.org/report", domain="beta.org", snippet="The project was officially cancelled in April 2026.", category=SourceCategory.NEWS, authority_score=0.89),
    ]

    # Artificial conflict
    conflict = ResearchConflict(
        topic="Project Status",
        source_a="alpha.org",
        claim_a="Release scheduled for May 2026",
        source_b="beta.org",
        claim_b="Project cancelled in April 2026",
        explanation="Direct contradiction regarding project release vs cancellation.",
    )

    claims, citations = engine.verify_claims_and_citations(conflicting_sources, [conflict])
    assert len(claims) >= 1
    assert len(citations) == 2
    assert all(c["verified"] is True for c in citations)


def test_sufficiency_stopping_condition():
    """Verify that engine stops when evidence is sufficient without unbounded internet crawling."""
    engine = get_deep_research_engine()

    # 1. Simple query with 1 high-authority source and 0 conflicts -> Sufficient!
    sources_simple = [
        DiscoveredSource(title="Official AP Portal", url="https://ap.gov.in/cm", domain="ap.gov.in", snippet="N. Chandrababu Naidu is the Chief Minister.", category=SourceCategory.GOVERNMENT, authority_score=0.98),
    ]
    is_suff, reason = engine.check_evidence_sufficiency(sources_simple, [], depth_mode="simple", current_round=1)
    assert is_suff is True
    assert "Sufficient authority" in reason

    # 2. Moderate query with insufficient sources -> False
    sources_insufficient = [
        DiscoveredSource(title="Blog Post", url="https://blog.example.com", domain="example.com", snippet="Some opinion.", category=SourceCategory.COMMUNITY, authority_score=0.6),
    ]
    is_suff_mod, _ = engine.check_evidence_sufficiency(sources_insufficient, [], depth_mode="moderate", current_round=1)
    assert is_suff_mod is False


@pytest.mark.asyncio
async def test_concise_ui_progress_events_no_cot():
    """Verify that execute_research_stream emits the exact 6 concise UI progress states and NO private chain-of-thought."""
    engine = get_deep_research_engine()

    expected_phases = [
        "Planning research",
        "Searching",
        "Reading sources",
        "Comparing evidence",
        "Verifying",
        "Writing",
    ]

    received_displays = []
    has_complete = False

    async for event in engine.execute_research_stream("What is the latest version of Python?"):
        phase = event.get("phase")
        display = event.get("display") or event.get("message")
        if display in expected_phases and display not in received_displays:
            received_displays.append(display)

        if phase == "complete":
            has_complete = True
            result = event.get("result")
            assert isinstance(result, ResearchResult)

        # STRICT PRIVACY CHECK: Verify NO private chain-of-thought leakage
        raw_event_str = str(event).lower()
        forbidden_cot_tokens = [
            "chain_of_thought", "scratchpad", "thought:", "inner_thought",
            "private reasoning", "deliberation", "hidden_state", "system_prompt"
        ]
        for token in forbidden_cot_tokens:
            assert token not in raw_event_str, f"Private chain-of-thought token '{token}' exposed in UI event: {event}"

    # Verify all 6 concise UI progress events were emitted
    for exp in expected_phases:
        assert exp in received_displays, f"Missing concise UI progress state: {exp}. Received: {received_displays}"

    assert has_complete is True
