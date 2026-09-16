# Stage 8 — RAG / Retrieval Engine Transcript

**Date:** 2026-09-13  
**Agent Role:** Lead AI & RAG Engineer  
**Governance Standard:** gstack Stage 8 Retrieval Gate  

---

## 1. RAG Retrieval Architecture

### 1.1 Hybrid Scoring & Candidate Ranking (`backend/app/retrieval/retriever.py`)
- **Pipeline**:
  1. Query normalization (strips redundant spaces, lowercases tokens).
  2. Dense vector embedding generation via `generate_embedding(query)` (768-dim normalized unit vector).
  3. Hybrid scoring:
     $$\text{Hybrid Score} = 0.70 \times \text{Cosine Sim} + 0.30 \times \text{Lexical Overlap}$$
     where lexical overlap filters common stop words and computes match ratio over meaningful content tokens.
  4. Candidate sorting by hybrid score descending.

### 1.2 Epistemic Cutoff Gate (Refusal Injunction)
- **Problem**: Out-of-domain queries (e.g. baking sourdough bread, crypto arbitrage) must NEVER hallucinate or return random startup advice.
- **Solution**: The engine enforces a strict epistemic grounding rule:
  - Requires content-keyword overlap ($> 0.0$) AND hybrid similarity $\ge 0.28$, OR vector similarity $\ge 0.50$.
  - Queries lacking grounding fail the gate immediately (`grounded = False`, `evidence = []`, `context_text = ""`), enabling the assistant to return the transparent refusal message without generating ungrounded tokens.

### 1.3 Context Builder & Observability
- Selected chunks are formatted into structured prompt context blocks:
  `[Chunk #1 | Guest: Brian Chesky | Episode: ... | Similarity: 0.88]\n<excerpt>`
- Every retrieval query writes an audit record to `retrieval_logs` table (`query`, `top_similarity`, `chunks_count`, `latency_ms`, `grounded`).
- Direct REST endpoint: `POST /api/v1/retrieve`.

---

## 2. Automated Test Execution Evidence

Executed `pytest backend/tests/ -v`:

```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\avina\OneDrive\Desktop\Lenny_Growth_Assistant
plugins: anyio-4.14.1, langsmith-0.12.4
collected 25 items

backend/tests/test_api.py::test_health_endpoint PASSED                   [  4%]
backend/tests/test_api.py::test_health_db_endpoint PASSED                [  8%]
backend/tests/test_api.py::test_health_llm_endpoint PASSED               [ 12%]
backend/tests/test_api.py::test_request_telemetry_headers PASSED         [ 16%]
backend/tests/test_api.py::test_session_crud_and_messages PASSED         [ 20%]
backend/tests/test_api.py::test_validation_error_handling PASSED         [ 24%]
backend/tests/test_api.py::test_retrieve_endpoint PASSED                 [ 28%]
backend/tests/test_ingestion.py::test_parse_transcript PASSED            [ 32%]
backend/tests/test_ingestion.py::test_chunking_with_overlap PASSED       [ 36%]
backend/tests/test_ingestion.py::test_embedding_dimensions_and_normalization PASSED [ 40%]
backend/tests/test_ingestion.py::test_semantic_similarity_separation PASSED [ 44%]
backend/tests/test_ingestion.py::test_ingestion_idempotency PASSED       [ 48%]
backend/tests/test_persistence.py::test_database_ping PASSED             [ 52%]
backend/tests/test_persistence.py::test_session_lifecycle PASSED         [ 56%]
backend/tests/test_persistence.py::test_message_persistence_and_citations PASSED [ 60%]
backend/tests/test_persistence.py::test_transcript_and_vector_chunks PASSED [ 64%]
backend/tests/test_persistence.py::test_artifact_lifecycle PASSED        [ 68%]
backend/tests/test_persistence.py::test_cascade_delete_integrity PASSED  [ 72%]
backend/tests/test_retrieval.py::test_query_normalization PASSED         [ 76%]
backend/tests/test_retrieval.py::test_grounded_chesky_retrieval PASSED   [ 80%]
backend/tests/test_retrieval.py::test_grounded_shreyas_retrieval PASSED  [ 84%]
backend/tests/test_retrieval.py::test_out_of_domain_epistemic_refusal PASSED [ 88%]
backend/tests/test_empty_query_handling PASSED                            [ 92%]
backend/tests/test_retrieval_observability_logging PASSED                 [ 96%]
backend/tests/test_api_retrieve_endpoint PASSED                           [100%]

======================= 25 passed, 1 warning in 10.13s ========================
```

### Verified Behaviors:
- **Brian Chesky query**: Returns Airbnb 2020 turnaround and orchestra model chunks with top similarity $\ge 0.80$.
- **Shreyas Doshi query**: Returns LNO framework and ruthless prioritization chunks.
- **Out-of-domain query**: Trips the epistemic cutoff gate; returns `grounded=False` and empty evidence list.
- **Telemetry**: Successfully writes query string and round-trip latency to `retrieval_logs`.
- **API integration**: `POST /api/v1/retrieve` returns structured JSON response adhering to OpenAPI spec.
