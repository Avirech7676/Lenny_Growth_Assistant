# Stage 7 — Transcript Ingestion Pipeline Transcript

**Date:** 2026-09-13  
**Agent Role:** AI & RAG Systems Engineer  
**Governance Standard:** gstack Stage 7 Ingestion Gate  

---

## 1. Ingestion Pipeline Architecture

### 1.1 Source Ingestion & Cleaning (`ingestion/parser.py`)
- **Sources**: Ingested curated Lenny Podcast transcripts from `data/transcripts/`:
  1. `brian-chesky-airbnb.md`: Brian Chesky on leading Airbnb through crisis, eliminating traditional PMs, and founder mode.
  2. `shreyas-doshi-product.md`: Shreyas Doshi on the LNO framework, high agency, and ruthless prioritization.
- **Extraction**:
  - Structured headers extracted (`Guest`, `Episode`, `Source`).
  - Dialogue turns parsed with speaker attribution (`Lenny Rachitsky:` vs `Guest:`).
  - SHA-256 fingerprint generated for each transcript file for idempotent updates.

### 1.2 Semantic Chunking Engine (`ingestion/chunker.py`)
- Target chunk size: 250 tokens (~1,000 characters).
- Sliding context overlap: 40 tokens (~160 characters) to preserve conversational nuance across speaker turn transitions.
- Each chunk preserves metadata: `{guest, title, source, chunk_index, token_count}`.

### 1.3 Dense Vector Embeddings (`ingestion/embedder.py`)
- Primary engine: Ollama `nomic-embed-text` generating 768-dimensional float embeddings.
- Offline deterministic fallback: Hashed multi-frequency trigonometric projection with unit normalization (`||v||_2 = 1.0`). Cached Ollama connectivity ensures zero per-chunk latency during offline evaluation.
- Vector persistence: Chunks stored in PostgreSQL `transcript_chunks` table with cosine index (`ivfflat`), backed by `data/transcripts_cache.json` for fast container pre-seeding.

---

## 2. Automated Test Execution Evidence

Executed `pytest backend/tests/ -v`:

```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\avina\OneDrive\Desktop\Lenny_Growth_Assistant
plugins: anyio-4.14.1, langsmith-0.12.4
collected 18 items

backend/tests/test_api.py::test_health_endpoint PASSED                   [  5%]
backend/tests/test_api.py::test_health_db_endpoint PASSED                [ 11%]
backend/tests/test_api.py::test_health_llm_endpoint PASSED               [ 16%]
backend/tests/test_api.py::test_request_telemetry_headers PASSED         [ 22%]
backend/tests/test_api.py::test_session_crud_and_messages PASSED         [ 27%]
backend/tests/test_api.py::test_validation_error_handling PASSED         [ 33%]
backend/tests/test_api.py::test_retrieve_endpoint PASSED                 [ 38%]
backend/tests/test_ingestion.py::test_parse_transcript PASSED            [ 44%]
backend/tests/test_ingestion.py::test_chunking_with_overlap PASSED       [ 50%]
backend/tests/test_ingestion.py::test_embedding_dimensions_and_normalization PASSED [ 55%]
backend/tests/test_ingestion.py::test_semantic_similarity_separation PASSED [ 61%]
backend/tests/test_ingestion.py::test_ingestion_idempotency PASSED       [ 66%]
backend/tests/test_persistence.py::test_database_ping PASSED             [ 72%]
backend/tests/test_persistence.py::test_session_lifecycle PASSED         [ 77%]
backend/tests/test_persistence.py::test_message_persistence_and_citations PASSED [ 83%]
backend/tests/test_persistence.py::test_transcript_and_vector_chunks PASSED [ 88%]
backend/tests/test_persistence.py::test_artifact_lifecycle PASSED        [ 94%]
backend/tests/test_persistence.py::test_cascade_delete_integrity PASSED  [100%]

======================== 18 passed, 1 warning in 8.47s ========================
```

### Verified Behaviors:
- **Parser**: Extracted guest, title, dialogue turns, and SHA-256 hash.
- **Chunker**: Preserved speaker continuity with 40-token sliding overlap.
- **Embedder**: Generated 768-dimensional normalized float vectors.
- **Semantic Separation**: Relevant query scored significantly higher cosine similarity than off-topic prompts.
- **Idempotency**: Successive runs without `--force` do not create duplicate database rows.
- **Export**: 13 chunks indexed and exported to `data/transcripts_cache.json`.
