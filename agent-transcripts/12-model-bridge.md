# Stage 12 — Model Abstraction & Offline Strategy Transcript

**Date:** 2026-09-13  
**Agent Role:** DevOps & AI Systems Infrastructure Engineer  
**Governance Standard:** gstack Stage 12 Model Abstraction & Offline Strategy  

---

## 1. Multi-Model Architecture & Fallback Strategy

### 1.1 Tripartite Provider Abstraction (`backend/app/models/provider.py`)
- **`OllamaProvider` (Primary Local Inference)**:
  - Connects to `http://localhost:11434` running `llama3.2:latest`.
  - Non-blocking tags probe with fast 1.0s timeout.
  - Automatically fails over to `FallbackGroundedProvider` if the local daemon is offline.
- **`AnthropicProvider` (Cloud Reasoning)**:
  - Anthropic Python SDK client targeting Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`).
  - Gracefully falls over to deterministic grounded synthesis if `ANTHROPIC_API_KEY` is not supplied or returns an authentication/rate error.
- **`OpenAIProvider` (Cloud Completion)**:
  - OpenAI client targeting GPT-4o (`gpt-4o`).
  - Supports streaming or atomic responses with automatic fallback when keys are absent.
- **`FallbackGroundedProvider` (Deterministic Offline Synthesizer)**:
  - Zero-latency local synthesizer producing grounded answers, Ship 30 essays, ICE experiment specs, and 4-pillar playbooks.
  - Ensures automated tests, CI pipelines, and bare-metal local dev environments function 100% reliably without external daemon requirements.

### 1.2 Telemetry & Health Monitoring
- `check_llm_health()`:
  - Dynamically measures round-trip inference ping latency.
  - Reports provider status (`healthy` / `degraded`), model slug, and fallback readiness.
  - Exposed via `GET /health/llm` adhering to the `LLMHealthResponse` Pydantic schema.
- Per-request runtime overrides:
  - Users can pass `provider_override="ollama"`, `provider_override="anthropic"`, or `provider_override="openai"` in `MessageCreate` to switch models dynamically per conversational turn.

---

## 2. Automated Test Execution Evidence

Executed `python -m pytest backend/tests/ -v`:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\avina\OneDrive\Desktop\Lenny_Growth_Assistant
plugins: anyio-4.14.1, langsmith-0.12.4
collecting ... collected 49 items

backend/tests/test_agent.py::test_html_sanitization PASSED               [  2%]
backend/tests/test_agent.py::test_agent_grounded_research PASSED         [  4%]
backend/tests/test_agent.py::test_agent_epistemic_refusal PASSED         [  6%]
backend/tests/test_agent.py::test_agent_ship30_skill_generation PASSED   [  8%]
backend/tests/test_agent.py::test_agent_experiment_mode_and_artifact PASSED [ 10%]
backend/tests/test_agent.py::test_agent_multi_turn_history PASSED        [ 12%]
backend/tests/test_api.py::test_health_endpoint PASSED                   [ 14%]
backend/tests/test_api.py::test_health_db_endpoint PASSED                [ 16%]
backend/tests/test_api.py::test_health_llm_endpoint PASSED               [ 18%]
backend/tests/test_api.py::test_request_telemetry_headers PASSED         [ 20%]
backend/tests/test_api.py::test_session_crud_and_messages PASSED         [ 22%]
backend/tests/test_api.py::test_validation_error_handling PASSED         [ 24%]
backend/tests/test_api.py::test_retrieve_endpoint PASSED                 [ 26%]
backend/tests/test_ingestion.py::test_parse_transcript PASSED            [ 28%]
backend/tests/test_ingestion.py::test_chunking_with_overlap PASSED       [ 30%]
backend/tests/test_ingestion.py::test_embedding_dimensions_and_normalization PASSED [ 32%]
backend/tests/test_ingestion.py::test_semantic_similarity_separation PASSED [ 34%]
backend/tests/test_ingestion.py::test_ingestion_idempotency PASSED       [ 36%]
backend/tests/test_persistence.py::test_database_ping PASSED             [ 38%]
backend/tests/test_persistence.py::test_session_lifecycle PASSED         [ 40%]
backend/tests/test_persistence.py::test_message_persistence_and_citations PASSED [ 42%]
backend/tests/test_persistence.py::test_transcript_and_vector_chunks PASSED [ 44%]
backend/tests/test_persistence.py::test_artifact_lifecycle PASSED        [ 46%]
backend/tests/test_persistence.py::test_cascade_delete_integrity PASSED  [ 48%]
backend/tests/test_provider.py::test_provider_instantiation_and_model_names PASSED [ 51%]
backend/tests/test_provider.py::test_runtime_provider_overrides PASSED   [ 53%]
backend/tests/test_provider.py::test_offline_fallback_resilience PASSED  [ 55%]
backend/tests/test_provider.py::test_health_llm_endpoint_response PASSED [ 57%]
backend/tests/test_provider.py::test_per_request_override_via_api PASSED [ 59%]
backend/tests/test_retrieval.py::test_query_normalization PASSED         [ 61%]
backend/tests/test_retrieval.py::test_grounded_chesky_retrieval PASSED   [ 63%]
backend/tests/test_retrieval.py::test_grounded_shreyas_retrieval PASSED  [ 65%]
backend/tests/test_retrieval.py::test_out_of_domain_epistemic_refusal PASSED [ 67%]
backend/tests/test_retrieval.py::test_empty_query_handling PASSED        [ 69%]
backend/tests/test_retrieval.py::test_retrieval_observability_logging PASSED [ 71%]
backend/tests/test_retrieval.py::test_api_retrieve_endpoint PASSED       [ 73%]
backend/tests/test_ship30.py::test_ship30_essay_structure_analysis PASSED [ 75%]
backend/tests/test_ship30.py::test_ship30_incomplete_essay_diagnostic PASSED [ 77%]
backend/tests/test_ship30.py::test_ship30_cheat_sheet_artifact_generation PASSED [ 79%]
backend/tests/test_ship30.py::test_ship30_live_shreyas_integration PASSED [ 81%]
backend/tests/test_ship30.py::test_ship30_live_chesky_integration PASSED [ 83%]
backend/tests/test_skills.py::test_experiment_validation_complete PASSED [ 85%]
backend/tests/test_skills.py::test_experiment_validation_incomplete PASSED [ 87%]
backend/tests/test_ice_calculator_artifact_generation PASSED             [ 89%]
backend/tests/test_skills.py::test_playbook_validation_complete PASSED   [ 91%]
backend/tests/test_skills.py::test_playbook_validation_incomplete PASSED [ 93%]
backend/tests/test_skills.py::test_playbook_matrix_artifact_generation PASSED [ 95%]
backend/tests/test_skills.py::test_live_experiment_api_turn PASSED       [ 97%]
backend/tests/test_skills.py::test_live_playbook_api_turn PASSED         [100%]

======================= 49 passed, 1 warning in 37.17s ========================
```
