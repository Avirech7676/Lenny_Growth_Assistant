"""Tests for the Model-Independent Deep Research Engine and Source Filtering.

Validates multi-query planning, source crawling, constraint filtering, conflict detection,
and model-agnostic synthesis across all providers.
"""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.search.base import SourceCategory, ResearchDepth, DiscoveredSource
from app.services.research import (
    DeepResearchEngine,
    get_deep_research_engine,
    parse_research_constraints,
    apply_source_filters,
    ResearchResult,
    ResearchReport,
)
from app.models.provider import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    FallbackGroundedProvider,
)


@pytest.mark.asyncio
async def test_deep_research_engine_execution():
    """Verify DeepResearchEngine executes multi-source research and returns a structured ResearchResult."""
    engine = get_deep_research_engine()
    result = await engine.execute_research(
        query="Who is CM of AP",
        depth_override="search",
    )

    assert isinstance(result, ResearchResult)
    assert result.query == "Who is CM of AP"
    assert len(result.used_sources) > 0
    assert len(result.synthesis_context) > 50

    # Verify structured report is populated
    assert result.report is not None
    assert isinstance(result.report, ResearchReport)
    assert len(result.report.key_findings) > 0
    assert len(result.report.verified_claims) > 0
    assert result.report.evidence_strength in ("Strong", "Moderate", "Limited")

    # Verify zero Brian Chesky contamination
    assert "chesky" not in result.synthesis_context.lower()
    assert any("chandrababu" in s.title.lower() or "naidu" in s.title.lower() or "andhra" in s.title.lower() for s in result.used_sources)


def test_source_filtering_constraints():
    """Verify constraint parser detects user instructions and filters sources accordingly."""
    # 1. Official sources only
    c1 = parse_research_constraints("Research React 19 from official documentation only")
    assert c1.only_official is True

    # 2. Exclude Reddit
    c2 = parse_research_constraints("Compare Next.js vs Remix and exclude reddit")
    assert "reddit.com" in c2.excluded_domains

    # 3. Academic papers
    c3 = parse_research_constraints("Research quantum computing using academic papers")
    assert c3.only_academic is True

    # 4. Filter application
    sources = [
        DiscoveredSource(title="Official React Docs", url="https://react.dev", domain="react.dev", snippet="React 19 release", category=SourceCategory.OFFICIAL, authority_score=0.98),
        DiscoveredSource(title="Reddit Discussion", url="https://reddit.com/r/react", domain="reddit.com", snippet="Discussion thread", category=SourceCategory.COMMUNITY, authority_score=0.5),
        DiscoveredSource(title="ACM Paper", url="https://acm.org/paper", domain="acm.org", snippet="Academic research", category=SourceCategory.ACADEMIC, authority_score=0.92),
    ]

    filtered_reddit = apply_source_filters(sources, c2)
    assert not any(s.domain == "reddit.com" for s in filtered_reddit)
    assert len(filtered_reddit) == 2

    filtered_official = apply_source_filters(sources, c1)
    assert any(s.domain == "react.dev" for s in filtered_official)
    assert not any(s.domain == "reddit.com" for s in filtered_official)


@pytest.mark.asyncio
async def test_deep_research_streaming_events():
    """Verify execute_research_stream yields progressive phases for real-time UI tracking."""
    engine = get_deep_research_engine()
    phases = []

    async for event in engine.execute_research_stream("Compare PostgreSQL and MongoDB for high scale"):
        phases.append(event.get("phase"))
        if event.get("phase") == "complete":
            res = event.get("result")
            assert isinstance(res, ResearchResult)

    assert "planning" in phases
    assert "searching" in phases
    assert "reading" in phases
    assert "cross_checking" in phases
    assert "synthesizing" in phases
    assert "complete" in phases


@pytest.mark.asyncio
async def test_model_agnostic_synthesis():
    """Verify that ResearchResult context is synthesized cleanly by any model provider."""
    engine = get_deep_research_engine()
    research_res = await engine.execute_research("Who is CM of AP", depth_override="search")
    context = research_res.synthesis_context
    assert len(context) > 0

    prompt = "Synthesize a concise, factual answer based strictly on the verified research context."
    history = []

    # 1. Fallback / Deterministic Provider
    p_fallback = FallbackGroundedProvider()
    res_fb = p_fallback.generate(prompt, "Who is CM of AP?", context, history)
    assert "naidu" in res_fb.lower() or "chandrababu" in res_fb.lower()
    assert "chesky" not in res_fb.lower()

    # 2. Groq Provider (offline fallback path)
    p_groq = GroqProvider(api_key=None)
    res_groq = p_groq.generate(prompt, "Who is CM of AP?", context, history)
    assert "naidu" in res_groq.lower() or "chandrababu" in res_groq.lower()

    # 3. Gemini Provider (offline fallback path)
    p_gemini = GeminiProvider(api_key=None)
    res_gemini = p_gemini.generate(prompt, "Who is CM of AP?", context, history)
    assert "naidu" in res_gemini.lower() or "chandrababu" in res_gemini.lower()
