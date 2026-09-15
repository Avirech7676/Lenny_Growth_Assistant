# OmniAI / Lenny Growth Assistant — System Architecture & Multi-Model Platform Runbook

## 1. Executive Summary & Root-Cause Resolution

The answering engine of **The Lenny Growth Assistant** has been comprehensively audited, re-architected, and upgraded into an enterprise-grade, evidence-grounded, multi-model AI platform. 

### Core Guarantees & Non-Negotiables Achieved
1. **Zero Synthetic / Hallucinated Sources**: Removed all programmatic URL fabrication (`standards.ietf.org`, `official.standards.org`). Real-world external answers strictly cite live, verified DuckDuckGo web results or provide direct factual responses.
2. **Zero Predetermined Corporate Boilerplate**: Removed hardcoded section headers (`"Executive Summary"`, `"Key Findings"`, `"Strategic Implications"`). System prompts dynamically tailor format and density strictly to the user's explicit question.
3. **Strict Domain Isolation & Relevance Filtering**: Non-Lenny queries (Coding, Algorithms, General Knowledge, Cinema) strictly filter out all Lenny transcript chunks, preventing false attribution to Brian Chesky, Airbnb, or Founder Mode.
4. **Autonomous Cross-Domain Context Hygiene**: Mid-conversation topic switches automatically detect domain divergence and isolate prior context, preventing topic bleeding across turns.
5. **Dynamic Multi-Model Platform Engine**: Live model discovery, task routing with multi-factor affinity scoring, token streaming with TTFT velocity telemetry, circuit breaker resilience with fallback cascades, cross-provider tool calling execution, context budgeting with priority-preserving compaction, and multi-turn state continuity.

---

## 2. Multi-Model Platform Architecture

```mermaid
graph TD
    User([User Query / UI Composer]) --> API[FastAPI /api/v1/messages/stream]
    API --> Intent[Relevance & Intent Classifier]
    
    subgraph "Query Understanding & Affinity Routing"
        Intent --> Domain[Query Domain & Complexity Analysis]
        Domain --> Scoring[Multi-Factor Affinity Scoring Engine]
        Scoring --> Router[Model Router / User Preference]
    end

    subgraph "Resilience & Circuit Breakers"
        Router --> Breaker{Circuit Breaker State?}
        Breaker -- Closed --> TargetModel[Target Provider & Model]
        Breaker -- Open/Degraded --> Cascade[Graceful Fallback Cascade]
        Cascade --> FallbackModel[Secondary Online Model / Local Fallback]
    end

    subgraph "Execution & State Management"
        TargetModel --> BudgetMgr[Context Window & Token Budget Manager]
        BudgetMgr --> ContinuityMgr[State Continuity & Compactor]
        ContinuityMgr --> ToolLoop[Tool Execution Loop (Calculator, Python, Web)]
        ToolLoop --> Inference[Streaming Inference Engine]
    end

    subgraph "Observability & Frontend Telemetry"
        Inference --> SSE[Server-Sent Events Stream]
        SSE --> ModelEvent[Early 'model' & 'model_transition' Events]
        SSE --> TokenStream[Token Chunks Stream]
        SSE --> Metrics[Metrics HUD: TTFT, tok/s, Total Latency]
        SSE --> UI[Header Model Platform Dropdown & Telemetry HUD]
    end
```

---

## 3. Platform Capabilities & 15-Phase Evolution

| Phase | Subsystem | Technical Implementation | Verified Coverage |
|---|---|---|---|
| **Phase A** | Root-Cause Audit | Full audit of answer generation pipeline, identifying synthetic fallbacks, entity dictionaries, and prompt constraints. | [`ANSWER_GENERATION_ROOT_CAUSE.md`](file:///c:/Users/avina/OneDrive/Desktop/Lenny_Growth_Assistant/ANSWER_GENERATION_ROOT_CAUSE.md) |
| **Phase B** | Fake Citation & Template Removal | Deleted synthetic domain generator; cleared hardcoded government dictionaries; replaced corporate templates. | `test_phase_b_repair.py` (4/4 passed) |
| **Phase C** | Query Understanding & Isolation | Term-boundary regex for Lenny guests; computer science & algorithm domain classification; strict universal Lenny chunk isolation; conversation context divergence reset. | `test_phase_c_routing.py` (5/5 passed) |
| **Phase D** | Direct LLM Answering Flow | Refactored `GENERAL_QA_SYSTEM_PROMPT`, `RESEARCH_SYSTEM_PROMPT`, `CODING_SYSTEM_PROMPT`; dynamic domain-aware synthesis phase messages. | `test_phase_d_answering.py` (5/5 passed) |
| **Phase E** | Dynamic Provider Abstraction | Extended `LLMProvider` contract with `supports_streaming`, `supports_tools`, `with_model`; created dynamic `ProviderRegistry`. | `test_phase_e_provider_registry.py` (5/5 passed) |
| **Phase F** | Live Model Discovery | Runtime inspection for Google Gemini (`Client.models.list`), Local Ollama (`/api/tags`), Groq, and OpenAI; exposed `/api/models/discover`. | `test_phase_f_model_discovery.py` (6/6 passed) |
| **Phase G** | Model Routing & Affinity Scoring | Heuristic constraint evaluation across coding suitability, reasoning, latency class, context window requirements, and explicit overrides. | `test_phase_g_model_routing.py` (8/8 passed) |
| **Phase H** | Dynamic Streaming & Telemetry | Structured SSE streaming (`phase` $\rightarrow$ `routing` $\rightarrow$ `citations` $\rightarrow$ `model` $\rightarrow$ `token` $\rightarrow$ `metrics` $\rightarrow$ `done`); computed TTFT and token velocity (`tokens_per_sec`). | `test_phase_h_streaming_telemetry.py` (4/4 passed) |
| **Phase I** | Circuit Breakers & Cascade | Error categorization (Quota 429, Timeout, High Demand 503, Network); automatic circuit breaker trips and graceful multi-provider fallback cascades. | `test_phase_i_health_cascade.py` (6/6 passed) |
| **Phase J** | Cross-Provider Tool Calling | Tool registry with schemas for `calculator`, `python_sandbox`, `web_search`, `transcript_search`; schema converters for OpenAI, Gemini, Anthropic; agent execution loop. | `test_phase_j_tool_calling.py` (8/8 passed) |
| **Phase K** | Token Budgeting & Compaction | Model context window resolution (1M Gemini, 128k Groq/GPT-4o, 8k Ollama); priority-preserving compaction preserving system prompt & user query while trimming history. | `test_phase_k_context_budget.py` (6/6 passed) |
| **Phase L** | Multi-Turn State Continuity | Cross-model state transitions tracked via `StateContinuityManager`; structured memory compaction (`<conversation_summary>`) for sessions $> 8$ turns. | `test_phase_l_state_continuity.py` (6/6 passed) |
| **Phase M** | Frontend Model Platform UI | Dynamic Header Model Selector; "Refresh Models" live discovery button; ChatInput quick model switcher; Message Model Badges; Interactive Telemetry HUD Popover. | `test_phase_m_model_ui.py` (5/5 passed) |
| **Phase N** | Live Query Matrix Verification | Verified live matrix across Lenny Podcast Advisory, C++ Quicksort implementation, Shreyas Doshi LNO SaaS framework, and AP Chief Minister factual QA. | `test_phase_n_live_matrix.py` (5/5 passed) |
| **Phase O** | Production Hardening & Compliance | Zero secret leakage across public JSON endpoints; CORS & security headers; XSS artifact sanitization; 100% regression pass rate. | `test_phase_o_production_hardening.py` (5/5 passed) |

---

## 4. REST API Endpoint Reference

### Models & Discovery
- `GET /api/models` (or `GET /api/v1/models`):
  - **Query Params**: `provider` (optional), `available_only` (bool), `discover` (bool).
  - **Returns**: Array of models with `model_id`, `provider`, `display_name`, `context_window`, `is_available`, and capability flags.
- `POST /api/models/discover` (or `POST /api/v1/models/discover`):
  - Triggers live model discovery against local Ollama, Gemini, Groq, and OpenAI APIs.
  - **Returns**: Discovered counts, provider status map, and list of newly available models.
- `GET /api/tools`:
  - Lists all registered tools with name, description, and input parameters schema.

### Conversations & Streaming
- `POST /api/v1/sessions/{id}/messages/stream`:
  - SSE endpoint for token streaming.
  - **Events emitted**:
    1. `phase`: Current orchestration step.
    2. `routing`: Resolved intelligence mode, domain, and depth.
    3. `citations`: Grounded evidence sources (transcript or verified web).
    4. `model`: Early event with `model_id` and `provider`.
    5. `model_transition` (optional): Emitted if active model changed mid-session.
    6. `token`: Streaming content chunk.
    7. `artifacts` (optional): Generated interactive artifacts.
    8. `metrics`: Observability payload (`ttft_ms`, `tokens_per_sec`, `token_count`, `total_ms`).
    9. `done`: Completion signal with message ID and follow-up suggestions.

---

## 5. Operations & Production Runbook

### Service Startup
- **Backend Service**:
  ```powershell
  $env:PYTHONPATH='.;backend'
  python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
  ```
- **Frontend Service**:
  ```powershell
  cd frontend
  npm run dev
  ```

### Health Diagnostics
- `GET http://127.0.0.1:8000/health`: General service status, version, UTC timestamp.
- `GET http://127.0.0.1:8000/health/db`: Database connection status and engine (`postgresql+pgvector` or `sqlite_fallback`).
- `GET http://127.0.0.1:8000/health/llm`: Provider status across Gemini, Groq, Ollama, OpenAI, Anthropic, active circuits, and fallback availability.

### Running Regression Tests
```powershell
python -m pytest backend/tests/test_phase_b_repair.py backend/tests/test_phase_c_routing.py backend/tests/test_phase_d_answering.py backend/tests/test_phase_e_provider_registry.py backend/tests/test_phase_f_model_discovery.py backend/tests/test_phase_g_model_routing.py backend/tests/test_phase_h_streaming_telemetry.py backend/tests/test_phase_i_health_cascade.py backend/tests/test_phase_j_tool_calling.py backend/tests/test_phase_k_context_budget.py backend/tests/test_phase_l_state_continuity.py backend/tests/test_phase_m_model_ui.py backend/tests/test_phase_n_live_matrix.py backend/tests/test_phase_o_production_hardening.py backend/tests/test_model_providers.py backend/tests/test_agent.py -v
```
