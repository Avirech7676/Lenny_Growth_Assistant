"""Ingestion pipeline script to parse, chunk, embed, and index transcripts."""

import sys
import os
import glob
import json
import time
import argparse
import uuid

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.logging import setup_logger
from app.db.session import get_db_session, init_db
from app.db.models import Transcript, TranscriptChunk
from ingestion.parser import parse_transcript_file
from ingestion.chunker import chunk_transcript
from ingestion.embedder import generate_embedding

logger = setup_logger("ingestion_pipeline")

def run_ingestion(transcripts_dir: str = "data/transcripts", force: bool = False) -> int:
    """Run full idempotent ingestion pipeline over all transcript files in directory."""
    init_db()
    db = get_db_session()

    pattern = os.path.join(transcripts_dir, "*.md")
    files = glob.glob(pattern)

    if not files:
        logger.warning("No markdown transcript files found in: %s", transcripts_dir)
        return 0

    logger.info("Found %d transcript file(s) for ingestion in %s.", len(files), transcripts_dir)
    total_chunks_indexed = 0
    cache_records = []

    for file_path in files:
        t0 = time.perf_counter()
        parsed = parse_transcript_file(file_path)
        logger.info("Processing '%s' (Guest: %s)...", parsed.title, parsed.guest)

        # Check idempotency via content_hash
        existing = db.query(Transcript).filter(Transcript.content_hash == parsed.content_hash).first()
        if existing and not force:
            logger.info("Skipping '%s' — already ingested with hash %s", parsed.title, parsed.content_hash[:8])
            # Load existing chunks into cache record
            chunks = db.query(TranscriptChunk).filter(TranscriptChunk.transcript_id == existing.id).all()
            for c in chunks:
                cache_records.append({
                    "id": c.id,
                    "guest": parsed.guest,
                    "title": parsed.title,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "embedding": json.loads(c.embedding_json),
                    "token_count": c.token_count,
                    "metadata": json.loads(c.meta_info) if c.meta_info else {},
                })
            total_chunks_indexed += len(chunks)
            continue

        if existing and force:
            logger.info("Force re-ingestion: deleting existing transcript record %s", existing.id)
            db.delete(existing)
            db.commit()

        # Chunk transcript
        chunks = chunk_transcript(parsed, target_chunk_tokens=250, overlap_tokens=40)
        logger.info("Split '%s' into %d chunks.", parsed.title, len(chunks))

        # Create Transcript record
        transcript_record = Transcript(
            title=parsed.title,
            guest=parsed.guest,
            episode_url=f"https://www.lennyspodcast.com/{os.path.splitext(os.path.basename(file_path))[0]}",
            chunk_count=len(chunks),
            content_hash=parsed.content_hash,
        )
        db.add(transcript_record)
        db.commit()
        db.refresh(transcript_record)

        # Generate embeddings and insert chunks
        chunk_models = []
        for chunk in chunks:
            embedding = generate_embedding(chunk.content)
            chunk_id = str(uuid.uuid4())
            chunk_model = TranscriptChunk(
                id=chunk_id,
                transcript_id=transcript_record.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding_json=json.dumps(embedding),
                token_count=chunk.token_count,
                meta_info=json.dumps(chunk.metadata),
            )
            chunk_models.append(chunk_model)
            cache_records.append({
                "id": chunk_id,
                "guest": parsed.guest,
                "title": parsed.title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "embedding": embedding,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            })

        db.add_all(chunk_models)
        db.commit()

        total_chunks_indexed += len(chunk_models)
        elapsed_s = time.perf_counter() - t0
        logger.info("Indexed %d chunks for '%s' in %.2fs.", len(chunk_models), parsed.title, elapsed_s)

    # Save cached vector index to data/transcripts_cache.json
    cache_path = os.path.join(os.path.dirname(transcripts_dir), "transcripts_cache.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_records, f, indent=2)
        logger.info("Exported %d cached chunk vectors to %s", len(cache_records), cache_path)
    except Exception as e:
        logger.warning("Failed to write vector cache: %s", e)

    db.close()
    logger.info("Ingestion complete. Total chunks in index: %d", total_chunks_indexed)
    return total_chunks_indexed


def sync_transcripts_from_chatprd(target_dir: str = "data/transcripts", episodes: list = None) -> int:
    """Download verified episode transcripts directly from Lenny's Podcast / Newsletter transcript repository.
    
    Source: https://github.com/ChatPRD/lennys-podcast-transcripts
    """
    import urllib.request
    os.makedirs(target_dir, exist_ok=True)
    episodes = episodes or ["brian-chesky", "shreyas-doshi", "shreyas-doshi-live"]
    downloaded = 0
    for ep in episodes:
        raw_url = f"https://raw.githubusercontent.com/ChatPRD/lennys-podcast-transcripts/main/episodes/{ep}/transcript.md"
        dest = os.path.join(target_dir, f"{ep}.md")
        try:
            logger.info("Fetching '%s' from https://github.com/ChatPRD/lennys-podcast-transcripts...", ep)
            urllib.request.urlretrieve(raw_url, dest)
            logger.info("Synced '%s' to %s", ep, dest)
            downloaded += 1
        except Exception as e:
            logger.warning("Could not sync '%s' from ChatPRD: %s", ep, e)
    return downloaded


# Export alias for callers
ingest_all_transcripts = run_ingestion

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest podcast transcripts into vector store.")
    parser.add_argument("--dir", default="data/transcripts", help="Path to transcripts directory")
    parser.add_argument("--force", action="store_true", help="Force re-ingest and overwrite existing records")
    parser.add_argument("--sync-chatprd", action="store_true", help="Sync latest transcripts from https://github.com/ChatPRD/lennys-podcast-transcripts")
    args = parser.parse_args()

    if args.sync_chatprd:
        sync_transcripts_from_chatprd(target_dir=args.dir)

    run_ingestion(transcripts_dir=args.dir, force=args.force)
