"""Automated persistence and database tests for The Lenny Growth Assistant."""

import sys
import os
import json
import uuid
import numpy as np
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import get_db_session, init_db, ping_db
from app.db.models import Session, Message, Transcript, TranscriptChunk, Artifact, RetrievalLog

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database tables are initialized before running tests."""
    init_db()
    yield

def test_database_ping():
    """Verify database reachability."""
    assert ping_db() is True

def test_session_lifecycle():
    """Verify session creation, read, and serialization."""
    db = get_db_session()
    try:
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            title="Strategic Prioritization Session",
            meta_info=json.dumps({"evaluator_demo": True}),
        )
        db.add(session)
        db.commit()

        # Retrieve session
        retrieved = db.query(Session).filter(Session.id == session_id).first()
        assert retrieved is not None
        assert retrieved.title == "Strategic Prioritization Session"
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

        # Verify dictionary serialization
        data = retrieved.to_dict()
        assert data["id"] == session_id
        assert data["metadata"]["evaluator_demo"] is True
    finally:
        db.close()

def test_message_persistence_and_citations():
    """Verify storing user and assistant turns with grounding citations."""
    db = get_db_session()
    try:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, title="Founder Mode Discussion")
        db.add(session)
        db.commit()

        # Add user message
        user_msg = Message(
            session_id=session_id,
            role="user",
            content="How did Brian Chesky reorganize Airbnb in 2020?",
            mode="research",
            model="user",
        )
        db.add(user_msg)
        db.commit()

        # Add grounded assistant response
        citations_data = [
            {
                "chunk_id": "chunk-101",
                "guest": "Brian Chesky",
                "similarity": 0.885,
                "excerpt": "We combined product management with product marketing...",
            }
        ]
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content="Brian Chesky reorganized Airbnb by shifting from decentralized PMs to an orchestra model...",
            mode="research",
            model="llama3.2:latest",
            latency_ms=1240.5,
            citations=json.dumps(citations_data),
        )
        db.add(assistant_msg)
        db.commit()

        # Query messages for session
        messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[1].latency_ms == 1240.5
        
        parsed_citations = json.loads(messages[1].citations)
        assert len(parsed_citations) == 1
        assert parsed_citations[0]["guest"] == "Brian Chesky"
    finally:
        db.close()

def test_transcript_and_vector_chunks():
    """Verify transcript ingestion and vector chunk storage."""
    db = get_db_session()
    try:
        content_hash = "hash_" + str(uuid.uuid4())[:8]
        transcript = Transcript(
            title="Leading Through Crisis",
            guest="Brian Chesky",
            episode_url="https://www.lennyspodcast.com/brian-chesky",
            chunk_count=2,
            content_hash=content_hash,
        )
        db.add(transcript)
        db.commit()

        # Generate mock 768-dimensional normalized embedding vectors
        v1 = np.random.randn(768)
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.random.randn(768)
        v2 = v2 / np.linalg.norm(v2)

        chunk1 = TranscriptChunk(
            transcript_id=transcript.id,
            chunk_index=0,
            content="When COVID hit in March 2020, our business dropped by 80%...",
            embedding_json=json.dumps(v1.tolist()),
            token_count=180,
            meta_info=json.dumps({"guest": "Brian Chesky", "topic": "2020 crisis"}),
        )
        chunk2 = TranscriptChunk(
            transcript_id=transcript.id,
            chunk_index=1,
            content="I decided to run the company like an orchestra...",
            embedding_json=json.dumps(v2.tolist()),
            token_count=195,
            meta_info=json.dumps({"guest": "Brian Chesky", "topic": "orchestra model"}),
        )
        db.add_all([chunk1, chunk2])
        db.commit()

        # Verify chunks
        retrieved_chunks = db.query(TranscriptChunk).filter(TranscriptChunk.transcript_id == transcript.id).all()
        assert len(retrieved_chunks) == 2
        assert json.loads(retrieved_chunks[0].meta_info)["topic"] == "2020 crisis"

        # Cosine similarity calculation test
        query_v = np.random.randn(768)
        query_v = query_v / np.linalg.norm(query_v)
        
        c1_v = np.array(json.loads(retrieved_chunks[0].embedding_json))
        c2_v = np.array(json.loads(retrieved_chunks[1].embedding_json))
        
        sim1 = float(np.dot(query_v, c1_v))
        sim2 = float(np.dot(query_v, c2_v))
        
        assert -1.0 <= sim1 <= 1.0
        assert -1.0 <= sim2 <= 1.0
    finally:
        db.close()

def test_artifact_lifecycle():
    """Verify operational artifact persistence and schema."""
    db = get_db_session()
    try:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, title="Artifact Test Session")
        db.add(session)
        db.commit()

        artifact = Artifact(
            session_id=session_id,
            artifact_type="html",
            title="Interactive LNO Prioritization Calculator",
            raw_content="<div class='calculator'>Raw content</div>",
            sanitized_content="<div class='calculator'>Safe sanitized content</div>",
            status="sanitized",
        )
        db.add(artifact)
        db.commit()

        retrieved_art = db.query(Artifact).filter(Artifact.session_id == session_id).first()
        assert retrieved_art is not None
        assert retrieved_art.title == "Interactive LNO Prioritization Calculator"
        assert retrieved_art.status == "sanitized"
        assert "<div class='calculator'>" in retrieved_art.sanitized_content
    finally:
        db.close()

def test_cascade_delete_integrity():
    """Verify that deleting a session cascades to its messages and artifacts."""
    db = get_db_session()
    try:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, title="Ephemeral Session")
        db.add(session)
        db.commit()

        msg = Message(session_id=session_id, role="user", content="Temporary message")
        art = Artifact(
            session_id=session_id,
            artifact_type="markdown",
            title="Temp Artifact",
            raw_content="test",
            sanitized_content="test",
        )
        db.add_all([msg, art])
        db.commit()

        # Confirm existence
        assert db.query(Message).filter(Message.session_id == session_id).count() == 1
        assert db.query(Artifact).filter(Artifact.session_id == session_id).count() == 1

        # Delete session
        db.delete(session)
        db.commit()

        # Confirm cascading deletion
        assert db.query(Session).filter(Session.id == session_id).first() is None
        assert db.query(Message).filter(Message.session_id == session_id).count() == 0
        assert db.query(Artifact).filter(Artifact.session_id == session_id).count() == 0
    finally:
        db.close()
