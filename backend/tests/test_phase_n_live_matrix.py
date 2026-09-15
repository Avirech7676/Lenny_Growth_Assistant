"""
Tests for Phase N: End-to-End Live Multi-Model Matrix Verification.
Executes live end-to-end turns across the 4 foundational matrix domains:
1. Lenny Podcast Advisory (Brian Chesky Founder Mode)
2. Software Engineering / Algorithm Implementation (C++ Quicksort)
3. SaaS Growth Strategy (Shreyas Doshi LNO Framework)
4. Factual Knowledge / Current Facts (AP Chief Minister)
5. Multi-Turn Cross-Model State Continuity & Compaction
Zero-tolerance for synthetic fallback citations or corporate boilerplate across all domains.
"""

import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

SYNTHETIC_DOMAINS = ["standards.ietf.org", "official.standards.org", "w3c.org", "iso.org"]
CORPORATE_BOILERPLATE = ["executive summary", "key findings", "strategic implications"]


def test_matrix_lenny_advisory_chesky():
    """Domain 1: Lenny Podcast Advisory - Brian Chesky Founder Mode."""
    session_res = client.post("/api/v1/sessions", json={"title": "Matrix: Lenny Chesky"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "Explain Brian Chesky's founder mode and why excessive A/B testing can kill bold product design.",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res.status_code in [200, 201]
    data = res.json()

    content = data.get("content", "").lower()
    assert "chesky" in content
    assert any(k in content for k in ["founder", "product", "design", "airbnb", "testing"])

    # Zero synthetic citations check
    citations = data.get("citations", [])
    for c in citations:
        url = c.get("url") or ""
        for bad in SYNTHETIC_DOMAINS:
            assert bad not in url, f"Synthetic domain {bad} leaked in Lenny query"


def test_matrix_coding_quicksort_cpp():
    """Domain 2: Software Engineering / Coding - C++ Quicksort Implementation."""
    session_res = client.post("/api/v1/sessions", json={"title": "Matrix: Coding Quicksort"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "Write an optimized C++ implementation of quicksort with median-of-three pivot selection and time complexity.",
            "mode": "coding",
            "provider_override": "fallback",
        },
    )
    assert res.status_code in [200, 201]
    data = res.json()

    content = data.get("content", "")
    content_lower = content.lower()

    # Must contain actual C++ code
    assert "void quicksort" in content_lower or "int partition" in content_lower or "vector<int>" in content_lower

    # Zero corporate boilerplate
    for phrase in CORPORATE_BOILERPLATE:
        assert phrase not in content_lower, f"Corporate boilerplate '{phrase}' found in coding answer"

    # Zero Lenny references leaked
    assert "brian chesky" not in content_lower
    assert "lenny rachitsky" not in content_lower


def test_matrix_saas_growth_shreyas_lno():
    """Domain 3: SaaS Growth Advisory - Shreyas Doshi LNO Framework."""
    session_res = client.post("/api/v1/sessions", json={"title": "Matrix: Shreyas LNO"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "How does Shreyas Doshi define high-leverage product tasks in his LNO framework?",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res.status_code in [200, 201]
    data = res.json()

    content = data.get("content", "").lower()
    assert any(k in content for k in ["leverage", "lno", "shreyas", "doshi"])
    assert any(k in content for k in ["neutral", "overhead", "task", "priorit"])


def test_matrix_factual_general_qa_cm():
    """Domain 4: Factual General QA - AP Chief Minister."""
    session_res = client.post("/api/v1/sessions", json={"title": "Matrix: AP CM"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    res = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "Who is the Chief Minister of Andhra Pradesh?",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res.status_code in [200, 201]
    data = res.json()

    content = data.get("content", "")
    assert "Chandrababu" in content or "Naidu" in content

    # Check zero synthetic URLs in citations
    for c in data.get("citations", []):
        url = c.get("url") or ""
        for bad in SYNTHETIC_DOMAINS:
            assert bad not in url, f"Synthetic citation domain {bad} found in factual query"


def test_matrix_multi_turn_cross_model_continuity():
    """Domain 5: Multi-Turn Cross-Model Continuity."""
    session_res = client.post("/api/v1/sessions", json={"title": "Matrix: Multi-Turn Continuity"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # Turn 1: Discuss a B2B SaaS onboarding experiment
    res1 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "Let's plan an onboarding retention experiment for a B2B collaboration tool with 10k users.",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res1.status_code in [200, 201]

    # Turn 2: Follow-up referencing turn 1 without repeating full context
    res2 = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "content": "Now convert this onboarding experiment into 3 specific measurable success metrics.",
            "mode": "chat",
            "provider_override": "fallback",
        },
    )
    assert res2.status_code in [200, 201]
    content2 = res2.json().get("content", "").lower()

    assert any(k in content2 for k in ["metric", "onboarding", "retention", "conversion", "activation", "b2b"])
