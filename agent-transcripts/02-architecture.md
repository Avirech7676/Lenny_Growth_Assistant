# Stage 2 — System Architecture & Technical Design Review

**Date:** 2026-09-13  
**Agent Role:** Staff Systems & AI Architect  
**Governance Framework:** gstack Architectural Review Gate (`/plan-eng-review`)  

---

## 1. Engineering Review & Technical Consensus

### 1.1 Persistence & Vector Retrieval Design
- **Decision**: Use PostgreSQL 16 with the native `pgvector` extension instead of introducing a separate standalone vector database (e.g. Pinecone, Qdrant, Chroma).
- **Rationale**: PostgreSQL 16 allows relational data (chat sessions, message threads, execution timestamps, and user metadata) and vector embeddings (`transcript_chunks`) to reside in a single ACID-compliant database. This eliminates dual-write race conditions, minimizes operational overhead, and enables atomic cascading deletes when a session or transcript is purged.
- **Index Strategy**: IVFFlat index with cosine similarity (`vector_cosine_ops`, `lists=100`).

### 1.2 Dual-Model Provider Bridge
- **Decision**: Define a provider-independent `BaseLLMProvider` interface with concrete implementations for `OllamaProvider` (local `llama3.2`), `AnthropicProvider` (`claude-3-5-sonnet`), and `OpenAIProvider` (`gpt-4o`).
- **Rationale**: The assignment mandates local Ollama for the final demo while supporting cloud models via configuration. Decoupling the orchestrator from model SDK specifics ensures zero application code changes when switching models or configuring fallback behavior.

### 1.3 Defense-in-Depth HTML Artifact Security
- **Decision**: A four-stage pipeline:
  1. Backend tag extraction and Bleach/sanitizer filtering.
  2. Frontend client-side DOMPurify validation.
  3. Dynamic Blob URL generation.
  4. Sandboxed `<iframe>` rendering with `sandbox="allow-scripts"` (strictly omitting `allow-same-origin` and `allow-top-navigation`).
- **Rationale**: Untrusted LLM-generated code could attempt cross-site scripting (XSS), cookie exfiltration, or window redirection. Omitting `allow-same-origin` guarantees that even if malicious JavaScript runs, it has zero access to the host application's DOM, tokens, or local storage.

### 1.4 API Contract & Error Discipline
- **Decision**: Standardize on Pydantic v2 schemas for all request/response bodies, with structured HTTP status codes (200 OK, 400 Bad Request, 404 Not Found, 503 DB Unavailable, 504 Gateway Timeout) and correlated `request_id` tracking.
