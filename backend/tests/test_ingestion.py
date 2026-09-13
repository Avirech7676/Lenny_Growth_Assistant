"""Automated ingestion pipeline and chunking tests."""

import sys
import os
import numpy as np
import pytest

# Add paths to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ingestion.parser import parse_transcript_file
from ingestion.chunker import chunk_transcript
from ingestion.embedder import generate_embedding, compute_cosine_similarity, EMBEDDING_DIM
from ingestion.ingest import run_ingestion
from app.db.session import get_db_session
from app.db.models import Transcript, TranscriptChunk

SAMPLE_TRANSCRIPT = "data/transcripts/brian-chesky-airbnb.md"

def test_parse_transcript():
    """Verify parsing headers and dialogue turns from markdown transcript."""
    parsed = parse_transcript_file(SAMPLE_TRANSCRIPT)
    assert parsed.guest == "Brian Chesky"
    assert "Crisis" in parsed.title
    assert len(parsed.dialogue_turns) >= 2
    assert len(parsed.content_hash) == 64

def test_chunking_with_overlap():
    """Verify semantic chunker respects token bounds and generates sequential chunks."""
    parsed = parse_transcript_file(SAMPLE_TRANSCRIPT)
    chunks = chunk_transcript(parsed, target_chunk_tokens=200, overlap_tokens=30)
    
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].metadata["guest"] == "Brian Chesky"
    # Ensure text is populated
    assert len(chunks[0].content) > 50

def test_embedding_dimensions_and_normalization():
    """Verify embeddings are 768-dimensional normalized unit vectors."""
    text = "Brian Chesky combined product management with product marketing at Airbnb."
    vec = generate_embedding(text)
    
    assert len(vec) == EMBEDDING_DIM
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-4

def test_semantic_similarity_separation():
    """Verify relevant query produces higher similarity than off-topic query."""
    chesky_text = "Brian Chesky eliminated traditional product managers and restructured Airbnb."
    related_query = "How did Brian Chesky reorganize product management at Airbnb?"
    unrelated_query = "What ingredients are required to bake chocolate chip cookies?"

    chesky_vec = generate_embedding(chesky_text)
    related_vec = generate_embedding(related_query)
    unrelated_vec = generate_embedding(unrelated_query)

    sim_related = compute_cosine_similarity(chesky_vec, related_vec)
    sim_unrelated = compute_cosine_similarity(chesky_vec, unrelated_vec)

    assert sim_related > sim_unrelated
    assert sim_related >= 0.25

def test_ingestion_idempotency():
    """Verify running ingestion multiple times does not produce duplicate chunks."""
    # First ingestion run
    count1 = run_ingestion(transcripts_dir="data/transcripts", force=False)
    assert count1 > 0

    # Second ingestion run (idempotent skip)
    db = get_db_session()
    transcripts_count1 = db.query(Transcript).count()
    chunks_count1 = db.query(TranscriptChunk).count()
    db.close()

    count2 = run_ingestion(transcripts_dir="data/transcripts", force=False)
    
    db = get_db_session()
    transcripts_count2 = db.query(Transcript).count()
    chunks_count2 = db.query(TranscriptChunk).count()
    db.close()

    assert transcripts_count1 == transcripts_count2
    assert chunks_count1 == chunks_count2
