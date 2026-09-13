# Reference: API Contracts, Database Schema & Configuration

This document contains authoritative technical reference specifications for **The Lenny Growth Assistant**.

---

## 1. REST API Endpoints Catalog

Base URL: `http://localhost:8000` (or through frontend proxy at `http://localhost:3000/api`)

### Health & Observability Endpoints

| Method | Endpoint | Description | Request Schema | Response Schema | Status Code |
|---|---|---|---|---|---|
| `GET` | `/health` | Service uptime and version info | None | `HealthResponse` | `200 OK` |
| `GET` | `/health/db` | Database connection pool ping | None | `DBHealthResponse` | `200 OK` / `503 Unavailable` |
| `GET` | `/health/llm` | Active LLM model & provider state | None | `LLMHealthResponse` | `200 OK` |

### Session Management Endpoints

| Method | Endpoint | Description | Request Body | Response Schema | Status Code |
|---|---|---|---|---|---|
| `POST` | `/api/v1/sessions` | Create new conversation session | `SessionCreate` | `SessionResponse` | `201 Created` |
| `GET` | `/api/v1/sessions` | List all sessions (newest first) | None | `List[SessionResponse]` | `200 OK` |
| `GET` | `/api/v1/sessions/{id}` | Get session details & artifacts | None | `SessionDetailResponse` | `200 OK` / `404 Not Found` |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session & cascade children | None | None | `204 No Content` / `404 Not Found` |

### Conversation & Messaging Endpoints

| Method | Endpoint | Description | Request Body | Response Schema | Status Code |
|---|---|---|---|---|---|
| `GET` | `/api/v1/sessions/{id}/messages` | Get session message history | None | `List[MessageResponse]` | `200 OK` / `404 Not Found` |
| `POST` | `/api/v1/sessions/{id}/messages` | Post prompt & trigger inference | `MessageCreate` | `MessageResponse` | `201 Created` / `422 Unprocessable` |

### Operational Artifact Endpoints

| Method | Endpoint | Description | Request Body | Response Schema / Type | Status Code |
|---|---|---|---|---|---|
| `GET` | `/api/v1/artifacts/{id}` | Fetch sanitized artifact record | None | `ArtifactResponse` | `200 OK` / `404 Not Found` |
| `GET` | `/api/v1/artifacts/{id}/iframe` | Render sandboxed HTML page | None | `text/html` (HTML5) | `200 OK` / `404 Not Found` |

### Retrieval Telemetry Endpoint

| Method | Endpoint | Description | Request Body | Response Schema | Status Code |
|---|---|---|---|---|---|
| `POST` | `/api/v1/retrieve` | Direct hybrid retrieval test | `RetrieveRequest` | `RetrieveResponse` | `200 OK` |

---

## 2. Telemetry Headers

Every HTTP response emits the following headers:
- `X-Request-ID`: Unique request correlation identifier (e.g. `req_e642bf189a`).
- `X-Response-Time-MS`: Round-trip server processing latency in milliseconds.

Artifact iframe responses additionally emit strict security headers:
- `Content-Security-Policy`: `default-src 'none'; style-src 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; font-src https://fonts.gstatic.com data:; img-src data: https:; script-src 'unsafe-inline' https://cdn.tailwindcss.com; frame-ancestors 'self'; base-uri 'none'; form-action 'none';`
- `X-Content-Type-Options`: `nosniff`
- `X-Frame-Options`: `SAMEORIGIN`
- `Referrer-Policy`: `no-referrer`
- `Cache-Control`: `no-cache, no-store, must-revalidate`

---

## 3. Database Schema Reference (PostgreSQL 16 + pgvector)

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Sessions Table
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    meta_info TEXT DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 2. Messages Table
CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    mode VARCHAR(32) NOT NULL DEFAULT 'research',
    model VARCHAR(64) NOT NULL,
    latency_ms FLOAT DEFAULT 0.0,
    citations TEXT DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 3. Transcripts Table
CREATE TABLE transcripts (
    id VARCHAR(36) PRIMARY KEY,
    guest VARCHAR(128) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_url VARCHAR(512),
    raw_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 4. Transcript Chunks Table
CREATE TABLE transcript_chunks (
    id VARCHAR(36) PRIMARY KEY,
    transcript_id VARCHAR(36) NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    token_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON transcript_chunks USING ivfflat (embedding vector_cosine_ops);

-- 5. Artifacts Table
CREATE TABLE artifacts (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id VARCHAR(36) REFERENCES messages(id) ON DELETE SET NULL,
    artifact_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    raw_content TEXT NOT NULL,
    sanitized_content TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'sanitized',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 6. Retrieval Logs Table
CREATE TABLE retrieval_logs (
    id VARCHAR(36) PRIMARY KEY,
    query TEXT NOT NULL,
    top_similarity FLOAT NOT NULL,
    chunks_count INTEGER NOT NULL,
    latency_ms FLOAT NOT NULL,
    grounded BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

---

## 4. Environment Variables Configuration Matrix

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://lenny_user:...@localhost:5432/lenny_growth_db` | Primary PostgreSQL connection string |
| `LLM_PROVIDER` | `ollama` | Active provider: `ollama`, `anthropic`, `openai`, `fallback` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama daemon endpoint |
| `OLLAMA_MODEL` | `llama3.2:latest` | Default local model |
| `OLLAMA_EMBED_MODEL`| `nomic-embed-text:latest` | Default embedding model |
| `ANTHROPIC_API_KEY` | None | API key for Anthropic Claude models |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-latest` | Default Anthropic model |
| `OPENAI_API_KEY` | None | API key for OpenAI models |
| `OPENAI_MODEL` | `gpt-4o` | Default OpenAI model |
| `COSINE_SIMILARITY_THRESHOLD` | `0.28` | Epistemic refusal cutoff gate threshold |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed cross-origin frontend domains |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
