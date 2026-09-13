# System Architecture & Technical Design Specification
# The Lenny Growth Assistant

**Document Version:** 2.0.0 (Stage 2 — Engineering Architecture & Technical Design)  
**Status:** Approved for Design System (Stage 3) & Implementation Planning  
**Role:** Staff Backend, Systems & AI Security Architect  
**Review Standard:** gstack `/plan-eng-review` Architectural Gate  

---

## 1. System Topology & Service Boundaries

The Lenny Growth Assistant is built as a hardened four-tier containerized topology. The architecture enforces strict separation of concerns, asynchronous non-blocking I/O, and defense-in-depth isolation.

```mermaid
graph TD
    subgraph Client Tier [Frontend - Next.js / React 19 + Tailwind v4 + Motion]
        WebClient[Web Browser Client]
        ChatUI[Chat Stream & Composer]
        CitationUI[Citation & Evidence Drawer]
        ArtifactUI[Sandboxed Growth Canvas]
    end

    subgraph Ingress & Application Tier [Backend - FastAPI Async Service]
        FastAPIApp[FastAPI Core Server :8000]
        CORS[CORS & Security Middleware]
        ReqLogger[Structured JSON Telemetry Logger]
        APIRouter[REST API Router /api/v1]
        SessionService[Session & Context Manager]
        AgentEngine[Agent Skill Orchestrator]
        SanitizerService[Artifact Sanitization Engine]
    end

    subgraph Data & Storage Tier [PostgreSQL 16 + pgvector :5432]
        PGCore[(PostgreSQL Relational Storage)]
        SessionsTable[(sessions & messages)]
        ArtifactsTable[(artifacts storage)]
        PGVector[(pgvector 768-dim Index)]
        ChunksTable[(transcript_chunks & embeddings)]
    end

    subgraph Model & Inference Tier [Dual-Model Provider Abstraction]
        ProviderBridge[LLM Provider Bridge Interface]
        OllamaDaemon[Local Ollama Daemon :11434 / llama3.2]
        AnthropicAPI[Cloud Anthropic API / Claude 3.5 Sonnet]
        OpenAIAPI[Cloud OpenAI API / GPT-4o]
    end

    WebClient --> ChatUI
    WebClient --> CitationUI
    WebClient --> ArtifactUI

    ChatUI -->|HTTP / SSE| FastAPIApp
    FastAPIApp --> CORS
    CORS --> ReqLogger
    ReqLogger --> APIRouter
    
    APIRouter --> SessionService
    APIRouter --> AgentEngine
    APIRouter --> SanitizerService
    
    SessionService --> SessionsTable
    SanitizerService --> ArtifactsTable
    
    AgentEngine --> ChunksTable
    AgentEngine --> ProviderBridge
    
    ProviderBridge --> OllamaDaemon
    ProviderBridge --> AnthropicAPI
    ProviderBridge --> OpenAIAPI
```

---

## 2. Database Schema Specification (PostgreSQL 16 + pgvector)

The database utilizes relational integrity for conversational history paired with the `pgvector` extension for cosine-similarity transcript retrieval.

```mermaid
erDiagram
    SESSIONS ||--o{ MESSAGES : contains
    SESSIONS ||--o{ ARTIFACTS : produces
    MESSAGES ||--o{ ARTIFACTS : triggers
    TRANSCRIPTS ||--o{ TRANSCRIPT_CHUNKS : splits_into

    SESSIONS {
        uuid id PK
        string title
        timestamp created_at
        timestamp updated_at
        jsonb metadata
    }

    MESSAGES {
        uuid id PK
        uuid session_id FK
        string role
        text content
        string mode
        string model
        float latency_ms
        jsonb citations
        timestamp created_at
    }

    TRANSCRIPTS {
        uuid id PK
        string title
        string guest
        string episode_url
        timestamp published_date
        int chunk_count
        string content_hash
        timestamp created_at
    }

    TRANSCRIPT_CHUNKS {
        uuid id PK
        uuid transcript_id FK
        int chunk_index
        text content
        vector_768 embedding
        int token_count
        jsonb metadata
        timestamp created_at
    }

    ARTIFACTS {
        uuid id PK
        uuid session_id FK
        uuid message_id FK
        string artifact_type
        string title
        text raw_content
        text sanitized_content
        string status
        timestamp created_at
    }
```

### 2.1 SQL DDL & Index Definitions
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Sessions Table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL DEFAULT 'New Growth Session',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL, -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    mode VARCHAR(64) DEFAULT 'research', -- 'research' | 'ship30' | 'experiment' | 'playbook'
    model VARCHAR(64) NOT NULL, -- 'llama3.2' | 'claude-3-5-sonnet-latest'
    latency_ms DOUBLE PRECISION DEFAULT 0.0,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcripts Table
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    guest VARCHAR(128) NOT NULL,
    episode_url VARCHAR(512),
    published_date TIMESTAMP WITH TIME ZONE,
    chunk_count INT DEFAULT 0,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcript Chunks Table with 768-dim embeddings
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    token_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector Cosine Similarity Index (IVFFlat)
CREATE INDEX idx_chunks_embedding ON transcript_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Relational Indexes
CREATE INDEX idx_messages_session ON messages(session_id, created_at ASC);
CREATE INDEX idx_chunks_transcript ON transcript_chunks(transcript_id, chunk_index);

-- Artifacts Table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    artifact_type VARCHAR(32) NOT NULL, -- 'html' | 'markdown' | 'calc'
    title VARCHAR(255) NOT NULL,
    raw_content TEXT NOT NULL,
    sanitized_content TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'sanitized', -- 'sanitized' | 'rejected'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 3. End-to-End Request Flow & Agent Routing

The agent layer avoids monolithic system prompts by implementing a bounded intent dispatcher that routes incoming queries to specialized skills.

```mermaid
sequenceDiagram
    autonumber
    actor User as Product Operator
    participant UI as Web Frontend
    participant API as FastAPI Router
    participant SessionMgr as Session Manager
    participant Orch as Agent Skill Orchestrator
    participant Retriever as RAG Retriever
    participant PG as PostgreSQL / pgvector
    participant Bridge as Model Provider Bridge
    participant LLM as Active LLM (Ollama / Cloud)
    participant Verifier as Grounding Verifier
    participant Sanitizer as HTML Sanitizer

    User->>UI: Enters query ("How did Brian Chesky handle Airbnb's 2020 crisis?")
    UI->>API: POST /api/v1/sessions/{id}/messages (prompt, mode="research")
    API->>SessionMgr: Load last 6 conversation turns
    SessionMgr->>PG: SELECT * FROM messages WHERE session_id = ?
    PG-->>SessionMgr: Return message thread
    
    API->>Orch: Dispatch to Orchestrator(prompt, mode, history)
    Orch->>Retriever: Query vector store
    Retriever->>PG: Search transcript_chunks (cosine similarity)
    PG-->>Retriever: Return Top-K chunks with similarity scores
    
    Retriever-->>Orch: Candidates (Max similarity: S)
    
    alt Cosine Similarity S < 0.65 (Out of Domain / Insufficient Evidence)
        Orch-->>API: Epistemic Refusal ("The available podcast transcripts do not cover...")
        API->>PG: Persist Refusal Message
        API-->>UI: Return Refusal JSON with 0 hallucination
        UI-->>User: Render transparent boundary notification
    else Cosine Similarity S >= 0.65 (Grounded Knowledge Found)
        Orch->>Bridge: Format prompt with system context + chunks + user query
        Bridge->>LLM: Stream inference (llama3.2 / claude-3-5-sonnet)
        LLM-->>Bridge: Yield streamed response tokens
        Bridge-->>Orch: Complete structured response
        
        Orch->>Verifier: Verify citations match retrieved chunk IDs
        Verifier-->>Orch: Verification Passed
        
        opt Response contains generated HTML/Markdown Artifact
            Orch->>Sanitizer: Extract & sanitize artifact
            Sanitizer->>PG: INSERT INTO artifacts (...)
            Sanitizer-->>Orch: Return sanitized artifact metadata
        end
        
        Orch->>SessionMgr: Save assistant message & telemetry
        SessionMgr->>PG: INSERT INTO messages (...)
        Orch-->>API: Payload (content, citations, artifacts, latency_ms)
        API-->>UI: 200 OK + Telemetry
        UI-->>User: Render response, citation pills, and artifact canvas
    end
```

---

## 4. API Specifications & Contracts

All endpoints use Pydantic v2 schemas for strict type safety and auto-generated OpenAPI documentation.

### 4.1 Health & Diagnostics
- **`GET /api/v1/health`**: Overall service uptime and system health.
- **`GET /api/v1/health/db`**: PostgreSQL connection pool status and query latency.
- **`GET /api/v1/health/llm`**: Active model provider connectivity (`ollama` or `anthropic`) and round-trip response time.

```json
// Response Schema: GET /api/v1/health/llm
{
  "status": "healthy",
  "provider": "ollama",
  "active_model": "llama3.2:latest",
  "latency_ms": 42.1,
  "fallback_ready": true,
  "fallback_provider": "anthropic"
}
```

### 4.2 Sessions & Messages
- **`POST /api/v1/sessions`**: Create a new conversation thread.
- **`GET /api/v1/sessions`**: List conversation sessions sorted by `updated_at`.
- **`GET /api/v1/sessions/{id}`**: Get full session details and metadata.
- **`GET /api/v1/sessions/{id}/messages`**: Fetch message history for a session.
- **`POST /api/v1/sessions/{id}/messages`**: Submit a user prompt to the agent orchestrator.

```json
// Request Schema: POST /api/v1/sessions/{id}/messages
{
  "content": "Explain Shreyas Doshi's LNO framework and how to apply it.",
  "mode": "ship30", // "research" | "ship30" | "experiment" | "playbook"
  "provider_override": null // optional: "ollama" | "anthropic"
}

// Response Schema: POST /api/v1/sessions/{id}/messages
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "session_id": "3b7defe3-3ca9-45af-ba50-249c0953efcb",
  "role": "assistant",
  "content": "# The Perfectionist Trap: Why High Performers Fail...",
  "mode": "ship30",
  "model": "llama3.2:latest",
  "latency_ms": 3210.5,
  "citations": [
    {
      "chunk_id": "4b19c28e-89a2-4a7b-a2c3-1d87128f2dd5",
      "guest": "Shreyas Doshi",
      "title": "High-Agency Product Leadership",
      "similarity": 0.884,
      "excerpt": "LNO classifies your daily and weekly work into three distinct buckets..."
    }
  ],
  "artifacts": [
    {
      "id": "e4f0a2d1-93b8-4c12-8819-2a4b8c9d0e1f",
      "artifact_type": "html",
      "title": "Interactive LNO Priority Calculator",
      "status": "sanitized"
    }
  ],
  "created_at": "2026-09-13T21:30:00Z"
}
```

### 4.3 Artifact Endpoints
- **`GET /api/v1/artifacts/{id}`**: Retrieve sanitized artifact content and metadata for iframe rendering.

---

## 5. Dual-Model Provider Bridge Architecture

The model layer abstracts local and cloud LLMs behind a uniform protocol so that switching models requires zero application code modifications.

```mermaid
classDiagram
    class BaseLLMProvider {
        <<interface>>
        +generate(messages: list, system_prompt: str, temperature: float) str
        +stream(messages: list, system_prompt: str, temperature: float) AsyncGenerator
        +health_check() HealthStatus
        +get_model_name() str
    }

    class OllamaProvider {
        -base_url: str
        -model_name: str
        -timeout_seconds: float
        +generate(...) str
        +stream(...) AsyncGenerator
        +health_check() HealthStatus
    }

    class AnthropicProvider {
        -api_key: str
        -model_name: str
        +generate(...) str
        +stream(...) AsyncGenerator
        +health_check() HealthStatus
    }

    class OpenAIProvider {
        -api_key: str
        -model_name: str
        +generate(...) str
        +stream(...) AsyncGenerator
        +health_check() HealthStatus
    }

    class LLMBridge {
        -active_provider: BaseLLMProvider
        -fallback_provider: BaseLLMProvider
        +get_active_provider() BaseLLMProvider
        +switch_provider(provider_name: str)
        +execute_with_fallback(fn)
    }

    BaseLLMProvider <|-- OllamaProvider
    BaseLLMProvider <|-- AnthropicProvider
    BaseLLMProvider <|-- OpenAIProvider
    LLMBridge --> BaseLLMProvider
```

### Fallback Policy:
If the local Ollama daemon fails or times out ($> 15.0$s), and an `ANTHROPIC_API_KEY` is configured in `.env`, the `LLMBridge` automatically executes the query against Anthropic Claude 3.5 Sonnet, logging an operational telemetry warning.

---

## 6. Secure Artifact Isolation Architecture

Untrusted LLM-generated HTML poses severe risks: session hijacking, DOM manipulation, and cross-site scripting (XSS). The architecture establishes a multi-stage defense pipeline:

```mermaid
graph TD
    subgraph Stage 1: LLM Generation
        RawTokens[LLM Response Stream] --> Parser[XML Tag Extractor <artifact>]
        Parser --> RawHTML[Raw HTML/CSS Snippet]
    end

    subgraph Stage 2: Backend Sanitization
        RawHTML --> BleachSanitizer[Python Bleach / Sanitizer whitelist]
        BleachSanitizer --> SafeHTMLDB[(Store in DB: sanitized_content)]
    end

    subgraph Stage 3: Client Validation
        SafeHTMLDB --> ClientDOMPurify[DOMPurify in Frontend]
        ClientDOMPurify --> BlobDoc[Constructed Blob / srcdoc]
    end

    subgraph Stage 4: Sandboxed Browser Execution
        BlobDoc --> SandboxedIframe[iframe sandbox='allow-scripts']
        SandboxedIframe -.-> Block1[BLOCKED: window.parent access]
        SandboxedIframe -.-> Block2[BLOCKED: document.cookie & storage]
        SandboxedIframe -.-> Block3[BLOCKED: top-level window.location redirect]
        SandboxedIframe -.-> Block4[BLOCKED: unsafe network origins]
        SandboxedIframe ==> SafeRun[ALLOWED: Interactive calculation & canvas rendering]
    end
```

---

## 7. Deployment Topology (Docker Compose)

The production deployment consists of 4 lightweight, interdependent containers running within an isolated internal bridge network:

```mermaid
graph LR
    subgraph Host Machine [Port Mappings]
        Port3000[Host Port 3000]
        Port8000[Host Port 8000]
        Port5432[Host Port 5432]
        Port11434[Host Port 11434]
    end

    subgraph Docker Network: lenny-network
        FrontendContainer[lenny_growth_frontend: Nginx / React Build]
        BackendContainer[lenny_growth_backend: FastAPI Uvicorn]
        DBContainer[lenny_growth_db: PostgreSQL 16 + pgvector]
        OllamaContainer[lenny_growth_ollama: Ollama Daemon]
    end

    Port3000 --> FrontendContainer
    Port8000 --> BackendContainer
    Port5432 --> DBContainer
    Port11434 --> OllamaContainer

    FrontendContainer -->|API Proxy / Direct| BackendContainer
    BackendContainer -->|Async pgvector queries| DBContainer
    BackendContainer -->|HTTP REST queries| OllamaContainer
```

---

## 8. Observability & Structured JSON Telemetry

Every request generates a correlated structured log entry. Sensitive credentials (API keys, connection strings) are strictly excluded.

```json
{
  "timestamp": "2026-09-13T21:30:04.120Z",
  "request_id": "req_8f12a3b4c5",
  "session_id": "3b7defe3-3ca9-45af-ba50-249c0953efcb",
  "endpoint": "/api/v1/sessions/3b7defe3-3ca9-45af-ba50-249c0953efcb/messages",
  "mode": "ship30",
  "model": "llama3.2:latest",
  "provider": "ollama",
  "retrieval": {
    "top_similarity": 0.884,
    "chunks_retrieved": 4,
    "latency_ms": 28.4
  },
  "generation": {
    "tokens_emitted": 1248,
    "latency_ms": 3182.1,
    "ttft_ms": 480.2
  },
  "artifacts_generated": 1,
  "status_code": 200
}
```
