"""Automated evaluation test suite for RAG retrieval engine."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import get_db_session
from app.db.models import RetrievalLog
from app.retrieval.retriever import retrieve_evidence, normalize_query

client = TestClient(app)

def test_query_normalization():
    """Verify whitespace stripping and query cleanup."""
    raw = "   How   did   Brian   Chesky   handle   crisis?  \n "
    normalized = normalize_query(raw)
    assert normalized == "How did Brian Chesky handle crisis?"

def test_grounded_chesky_retrieval():
    """Verify relevant query retrieves Brian Chesky transcript chunks with high confidence."""
    db = get_db_session()
    try:
        query = "How did Brian Chesky reorganize Airbnb in the 2020 pandemic crisis?"
        result = retrieve_evidence(query=query, db=db, top_k=3)

        assert result.grounded is True
        assert result.top_similarity >= 0.28
        assert len(result.evidence) > 0
        # Check that Brian Chesky is the primary guest
        assert result.evidence[0].guest == "Brian Chesky"
        assert "Airbnb" in result.evidence[0].excerpt or "2020" in result.evidence[0].excerpt or "orchestra" in result.evidence[0].excerpt
    finally:
        db.close()

def test_grounded_shreyas_retrieval():
    """Verify LNO framework query retrieves Shreyas Doshi chunks."""
    db = get_db_session()
    try:
        query = "What is Shreyas Doshi's LNO framework for ruthless executive prioritization?"
        result = retrieve_evidence(query=query, db=db, top_k=3)

        assert result.grounded is True
        assert result.top_similarity >= 0.28
        assert len(result.evidence) > 0
        assert any(ev.guest == "Shreyas Doshi" for ev in result.evidence)
        assert any("LNO" in ev.excerpt or "Leverage" in ev.excerpt for ev in result.evidence)
    finally:
        db.close()

def test_out_of_domain_epistemic_refusal():
    """Verify off-topic query fails the epistemic threshold and refuses cleanly."""
    db = get_db_session()
    try:
        query = "What is the best recipe for baking authentic sourdough bread in a Dutch oven?"
        result = retrieve_evidence(query=query, db=db, top_k=3)

        # Off-topic query should trip the epistemic cutoff gate
        assert result.grounded is False
        assert len(result.evidence) == 0
        assert result.context_text == ""
    finally:
        db.close()

def test_empty_query_handling():
    """Verify whitespace query is handled safely without error."""
    db = get_db_session()
    try:
        result = retrieve_evidence(query="   ", db=db)
        assert result.grounded is False
        assert len(result.evidence) == 0
    finally:
        db.close()

def test_retrieval_observability_logging():
    """Verify queries record telemetry in retrieval_logs table."""
    db = get_db_session()
    try:
        initial_count = db.query(RetrievalLog).count()
        query = "Founder Mode and CEO in the details"
        retrieve_evidence(query=query, db=db, top_k=2)

        new_count = db.query(RetrievalLog).count()
        assert new_count == initial_count + 1

        latest = db.query(RetrievalLog).order_by(RetrievalLog.created_at.desc()).first()
        assert latest is not None
        assert "Founder Mode" in latest.query
        assert latest.latency_ms >= 0.0
    finally:
        db.close()

def test_api_retrieve_endpoint():
    """Verify /api/v1/retrieve endpoint returns real grounded citations."""
    response = client.post(
        "/api/v1/retrieve",
        json={"query": "Brian Chesky founder mode and orchestra model", "top_k": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert len(data["chunks"]) > 0
    assert data["chunks"][0]["guest"] == "Brian Chesky"
    assert "similarity" in data["chunks"][0]
