"""RAG retrieval engine with hybrid vector-lexical scoring and epistemic cutoff."""

import json
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import settings
from app.core.logging import setup_logger
from app.db.models import TranscriptChunk, Transcript, RetrievalLog
from ingestion.embedder import generate_embedding, compute_cosine_similarity

logger = setup_logger("retriever")

@dataclass
class RetrievedEvidence:
    chunk_id: str
    guest: str
    title: str
    source_url: str
    similarity: float
    excerpt: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "guest": self.guest,
            "title": self.title,
            "source_url": self.source_url,
            "similarity": round(self.similarity, 4),
            "excerpt": self.excerpt,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }

@dataclass
class RetrievalResult:
    query: str
    evidence: List[RetrievedEvidence]
    top_similarity: float
    grounded: bool
    latency_ms: float
    context_text: str

def normalize_query(query: str) -> str:
    """Normalize query text, remove excessive whitespace and punctuation."""
    q = query.strip()
    q = re.sub(r"\s+", " ", q)
    return q

STOP_WORDS = {
    "what", "is", "the", "best", "for", "in", "a", "an", "and", "or", "of", "to", 
    "how", "do", "i", "with", "from", "on", "at", "by", "this", "that", "it", "are", "was"
}

def compute_lexical_overlap(query_tokens: set, text: str) -> float:
    """Compute normalized token overlap score between query content words and chunk text."""
    content_tokens = {t for t in query_tokens if t not in STOP_WORDS and len(t) > 2}
    if not content_tokens:
        return 0.0
    text_tokens = set(re.findall(r"\b\w+\b", text.lower()))
    if not text_tokens:
        return 0.0
    intersection = content_tokens.intersection(text_tokens)
    return len(intersection) / len(content_tokens)

def retrieve_evidence(
    query: str,
    db: SQLAlchemySession,
    top_k: int = 4,
    threshold: Optional[float] = None,
) -> RetrievalResult:
    """Retrieve grounded transcript chunks using hybrid cosine vector similarity and lexical ranking."""
    t0 = time.perf_counter()
    cutoff = threshold if threshold is not None else settings.COSINE_SIMILARITY_THRESHOLD
    clean_query = normalize_query(query)

    if not clean_query:
        return RetrievalResult(
            query=query,
            evidence=[],
            top_similarity=0.0,
            grounded=False,
            latency_ms=0.0,
            context_text="",
        )

    # 1. Generate query embedding vector
    query_vec = generate_embedding(clean_query)
    query_tokens = set(re.findall(r"\b\w+\b", clean_query.lower()))
    query_content_tokens = {t for t in query_tokens if t not in STOP_WORDS and len(t) > 2}

    # 2. Fetch transcript chunks from database
    chunks = db.query(TranscriptChunk).all()
    if not chunks:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return RetrievalResult(
            query=clean_query,
            evidence=[],
            top_similarity=0.0,
            grounded=False,
            latency_ms=latency_ms,
            context_text="",
        )

    # Fetch transcript map for fast title and URL lookup
    transcripts = {t.id: t for t in db.query(Transcript).all()}

    # 3. Score candidate chunks
    candidates = []
    for c in chunks:
        c_vec = json.loads(c.embedding_json)
        vec_sim = compute_cosine_similarity(query_vec, c_vec)
        lexical_sim = compute_lexical_overlap(query_content_tokens, c.content)
        
        # Hybrid score: 70% vector similarity + 30% content-word overlap
        hybrid_score = (0.70 * vec_sim) + (0.30 * lexical_sim)
        
        t_info = transcripts.get(c.transcript_id)
        guest = t_info.guest if t_info else "Lenny's Guest"
        title = t_info.title if t_info else "Lenny's Podcast"
        url = t_info.episode_url if t_info else "https://www.lennyspodcast.com"

        candidates.append((
            hybrid_score,
            vec_sim,
            lexical_sim,
            RetrievedEvidence(
                chunk_id=c.id,
                guest=guest,
                title=title,
                source_url=url,
                similarity=float(vec_sim),
                excerpt=c.content,
                token_count=c.token_count,
                metadata=json.loads(c.meta_info) if c.meta_info else {},
            )
        ))

    # 4. Sort by hybrid score descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    # 5. Evaluate top score against epistemic threshold
    top_hybrid, top_vec_sim, top_lexical, top_evidence = candidates[0]
    effective_score = max(top_hybrid, top_vec_sim)

    # Strict epistemic grounding criteria:
    # Must have either content keyword overlap (> 0.0) AND vector similarity >= 0.28, OR vector similarity >= 0.50
    grounded = (top_lexical > 0.0 and effective_score >= 0.28) or (top_vec_sim >= 0.50)

    if grounded:
        selected_evidence = [c[3] for c in candidates[:top_k] if (c[2] > 0.0 or c[1] >= 0.35)]
        context_blocks = []
        for idx, ev in enumerate(selected_evidence, 1):
            context_blocks.append(
                f"[Chunk #{idx} | Guest: {ev.guest} | Episode: {ev.title} | Similarity: {ev.similarity:.2f}]\n{ev.excerpt}"
            )
        context_text = "\n\n---\n\n".join(context_blocks)
    else:
        selected_evidence = []
        context_text = ""

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 6. Record observability telemetry into retrieval_logs table
    try:
        log_entry = RetrievalLog(
            query=clean_query[:500],
            top_similarity=float(effective_score),
            chunks_count=len(selected_evidence),
            latency_ms=latency_ms,
            grounded=grounded,
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.warning("Failed to record retrieval telemetry: %s", e)

    return RetrievalResult(
        query=clean_query,
        evidence=selected_evidence,
        top_similarity=float(effective_score),
        grounded=grounded,
        latency_ms=latency_ms,
        context_text=context_text,
    )
