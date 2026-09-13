# How-To Operational Recipes

This guide provides step-by-step practical recipes for configuring, operating, extending, and troubleshooting **The Lenny Growth Assistant**.

---

## 1. Ingesting Custom Transcripts

To expand the assistant's knowledge base with new episodes or transcripts:

### Step 1: Add Markdown Transcript
Place your markdown transcript in `data/transcripts/` using standard naming (e.g. `data/transcripts/elena-verna-b2b.md`). Include YAML frontmatter or title metadata:
```markdown
# Elena Verna on Product-Led Growth & Product-Led Sales

**Guest**: Elena Verna  
**Episode**: #120  

[00:01:20] Elena Verna: Product-led growth is an acquisition and retention model...
```

### Step 2: Run Ingestion Pipeline
Execute the ingestion script from the repository root:
```powershell
$env:PYTHONPATH=".;backend"
python -m ingestion.ingest
```
*The ingestion script will parse the markdown, chunk text into 250-token windows with 40-token overlap, compute 768-dimensional normalized embeddings, index into PostgreSQL/SQLite, and refresh `data/transcripts_cache.json`.*

---

## 2. Configuring LLM Providers

The assistant supports a tripartite provider bridge: Local Ollama, Cloud Anthropic, Cloud OpenAI, and Deterministic Fallback.

### Option A: Local Ollama (Zero-Cost & Private)
1. Install and start [Ollama](https://ollama.ai).
2. Pull the default models:
   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
3. Set environment in `.env`:
   ```ini
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2:latest
   ```

### Option B: Cloud Anthropic (Claude 3.5 Sonnet)
1. Add your API key in `.env`:
   ```ini
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ANTHROPIC_MODEL=claude-3-5-sonnet-latest
   ```

### Option C: Cloud OpenAI (GPT-4o)
1. Add your API key in `.env`:
   ```ini
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-proj-...
   OPENAI_MODEL=gpt-4o
   ```

### Option D: Deterministic Offline Fallback
If no external provider or API key is detected, the assistant automatically engages `FallbackGroundedProvider`, generating structured grounded answers without internet connectivity.

---

## 3. Running Automated Tests

All tests are located in `backend/tests/` and use `pytest`.

### Run All 72 Automated Tests:
```powershell
python -m pytest backend/tests/ -v
```

### Run Tests by Component:
- **Database & Persistence**:
  ```powershell
  python -m pytest backend/tests/test_persistence.py -v
  ```
- **RAG & Retrieval Grounding**:
  ```powershell
  python -m pytest backend/tests/test_retrieval.py -v
  ```
- **Agent Orchestrator**:
  ```powershell
  python -m pytest backend/tests/test_agent.py -v
  ```
- **Ship 30 for 30 Skill**:
  ```powershell
  python -m pytest backend/tests/test_ship30.py -v
  ```
- **Decision-Support Skills (ICE & Playbooks)**:
  ```powershell
  python -m pytest backend/tests/test_skills.py -v
  ```
- **Artifact Sandboxing & CSP**:
  ```powershell
  python -m pytest backend/tests/test_sandbox.py -v
  ```
- **Resilience & Chaos Engineering**:
  ```powershell
  python -m pytest backend/tests/test_resilience.py -v
  ```
- **Performance & Latency Benchmarks**:
  ```powershell
  python -m pytest backend/tests/test_performance.py -v
  ```
- **Security Audit & Secret Hygiene**:
  ```powershell
  python -m pytest backend/tests/test_security.py -v
  ```

---

## 4. Troubleshooting Common Issues

### Issue: "Primary database offline... Engaging local SQLite fallback"
- **Cause**: Docker Desktop or PostgreSQL is not currently running.
- **Resolution**: This is normal in bare-metal mode! The application automatically engages SQLite (`lenny_growth_local.db`) without crashing. To use PostgreSQL 16 + pgvector, start Docker Desktop and run `docker compose up -d db`.

### Issue: "ModuleNotFoundError: No module named 'ingestion'"
- **Cause**: Python path does not include the workspace root.
- **Resolution**: Ensure `PYTHONPATH` is set to `.;backend`:
  ```powershell
  $env:PYTHONPATH=".;backend"
  ```

### Issue: Port 8000 or 3000 Already in Use
- **Cause**: A previous server process is still bound to the port.
- **Resolution** (PowerShell):
  ```powershell
  # Find and kill process on port 8000
  $proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select -ExpandProperty OwningProcess
  if ($proc) { Stop-Process -Id $proc -Force }

  # Find and kill process on port 3000
  $proc3 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select -ExpandProperty OwningProcess
  if ($proc3) { Stop-Process -Id $proc3 -Force }
  ```
