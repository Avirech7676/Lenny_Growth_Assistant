"""Tests for Layer 6: Response Quality Gate & Verification Pipeline."""

import pytest
from app.services.quality.gate import (
    ResponseQualityGate,
    QualityGateResult,
    evaluate_response,
    get_quality_gate,
)


def test_quality_gate_high_quality_response():
    gate = ResponseQualityGate()
    query = "Who is the Chief Minister of Andhra Pradesh?"
    response = (
        "As of 2024–2026, N. Chandrababu Naidu is the Chief Minister of Andhra Pradesh, "
        "having assumed office on June 12, 2024 following the TDP-led alliance victory."
    )
    evidence = [
        "N. Chandrababu Naidu took oath as the Chief Minister of Andhra Pradesh on June 12, 2024."
    ]
    citations = [
        {"domain": "wikipedia.org", "url": "https://en.wikipedia.org/wiki/Chief_Minister_of_Andhra_Pradesh"}
    ]

    result = gate.evaluate(query=query, response=response, evidence_snippets=evidence, citations=citations)

    assert isinstance(result, QualityGateResult)
    assert result.passed is True
    assert result.overall_score >= 0.55
    assert len(result.dimensions) == 5

    dim_names = [d.dimension for d in result.dimensions]
    assert "relevance" in dim_names
    assert "grounding" in dim_names
    assert "completeness" in dim_names
    assert "currentness" in dim_names
    assert "citation_integrity" in dim_names


def test_quality_gate_detects_hallucinations():
    gate = ResponseQualityGate()
    query = "Where can I find growth statistics?"
    response = (
        "According to http://example.com/fake-study, 99% of startups grow by 1000%. "
        "A 2019 study showed that Lorem ipsum works best."
    )

    result = gate.evaluate(query=query, response=response)

    assert len(result.hallucination_flags) > 0
    # Should penalize overall score
    assert len(result.improvement_suggestions) > 0


def test_quality_gate_empty_response():
    gate = ResponseQualityGate()
    result = gate.evaluate(query="Hello", response="")

    assert result.passed is False
    assert result.overall_score == 0.0


def test_quality_gate_stale_response_warning():
    gate = ResponseQualityGate()
    query = "Who is the current Prime Minister of the UK in 2026?"
    response = "In 2015, David Cameron was the Prime Minister."

    result = gate.evaluate(query=query, response=response)
    currentness_dim = next(d for d in result.dimensions if d.dimension == "currentness")
    assert currentness_dim.score < 0.8
    assert any("201" in issue for issue in currentness_dim.issues)


def test_quality_gate_to_dict():
    result = evaluate_response(
        query="Explain product-led growth",
        response="Product-led growth (PLG) is a business methodology where user acquisition, expansion, conversion, and retention are driven primarily by the product itself."
    )
    d = result.to_dict()
    assert "overall_score" in d
    assert "passed" in d
    assert "dimensions" in d
    assert "evaluation_ms" in d
    assert isinstance(d["dimensions"], list)
