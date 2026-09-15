"""Automated verification tests for Phase B: Purging fake/predetermined response generation."""

import pytest
from app.models.provider import GeminiProvider, FallbackGroundedProvider
from app.services.search.web_provider import DuckDuckGoProvider
from app.services.search.curated_provider import CURATED_ENTITIES
from app.core.config import settings


def test_merge_sort_no_corporate_boilerplate():
    """Verify merge sort returns algorithmic complexity without corporate feedback loops."""
    provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    res = provider.generate(
        system_prompt="You are a general-purpose AI assistant. Answer directly and concisely.",
        user_prompt="What is the time complexity of merge sort?"
    )
    text = res.content if hasattr(res, "content") else str(res)
    assert len(text) > 0

    # Must contain algorithmic complexity
    assert "log" in text.lower() or "o(n" in text.lower()

    # Must NOT contain canned corporate boilerplate
    forbidden = [
        "measurable feedback loops",
        "standard implementations prioritize clarity",
        "operational accountability",
        "strategic implications",
        "brian chesky",
        "lenny rachitsky",
        "peer organizations",
    ]
    for phrase in forbidden:
        assert phrase not in text.lower(), f"Response contained forbidden corporate filler: '{phrase}'"


def test_no_synthetic_sources_in_web_provider():
    """Verify live search returns real sources or empty list without fabricating fake IETF/Arxiv URLs."""
    p = DuckDuckGoProvider()
    sources = p.search("who is prabhas")
    
    # If sources were returned, they must be real domains
    for s in sources:
        assert not s.url.startswith("https://standards.ietf.org/doc/"), f"Found synthetic IETF URL: {s.url}"
        assert not s.url.startswith("https://arxiv.org/abs/"), f"Found synthetic Arxiv URL: {s.url}"
        assert not s.url.startswith("https://engineering.guide/article/"), f"Found synthetic guide URL: {s.url}"
        assert s.domain != "standards.org", f"Found synthetic standards.org domain: {s.url}"
        assert s.url.startswith("http"), f"Invalid URL format: {s.url}"


def test_curated_provider_no_hardcoded_government():
    """Verify curated entities dictionary has no hardcoded politician or government entries."""
    assert "cm_ap" not in CURATED_ENTITIES
    assert "ysr" not in CURATED_ENTITIES
    assert "jagan" not in CURATED_ENTITIES
    assert "ap_capital" not in CURATED_ENTITIES


def test_fallback_provider_no_corporate_template():
    """Verify FallbackGroundedProvider does not inject corporate boilerplate for arbitrary queries."""
    fb = FallbackGroundedProvider()
    res = fb.generate(
        system_prompt="You are an AI assistant.",
        user_prompt="What is quantum entanglement?",
        context="",
        history=[]
    )
    text = res.content if hasattr(res, "content") else str(res)

    assert "represents an established principle across contemporary industry" not in text
    assert "measurable feedback loops" not in text
    assert "peer organizations" not in text
    assert "strategic implications" not in text.lower()
