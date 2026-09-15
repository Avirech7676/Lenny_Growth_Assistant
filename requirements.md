# Project Dependencies & Technical Requirements (`requirements.md`)

## System Environment
- **Operating System**: Windows / Linux / macOS
- **Python Runtime**: Python 3.10+ (tested on Python 3.14)
- **Node Runtime**: Node.js v18+ (tested on Node.js v20+)
- **Primary Database**: PostgreSQL 16 with `pgvector` extension (with transparent local SQLite fallback)

---

## Backend Python Requirements (`backend/requirements.txt`)

All backend dependencies are defined in [`backend/requirements.txt`](file:///c:/Users/avina/OneDrive/Desktop/Lenny_Growth_Assistant/backend/requirements.txt) with flexible `>=` compatibility constraints to ensure seamless installation across diverse environments without triggering source compilation errors on Windows.

| Package | Version Requirement | Installed Version | Role & Functional Responsibility |
|---|---|---|---|
| `fastapi` | `>=0.115.0` | `0.139.0` | High-performance ASGI web framework providing API routing, dependency injection, and SSE streaming. |
| `uvicorn[standard]` | `>=0.34.0` | `0.49.0` | Production ASGI web server engine with websockets, httptools, and uvloop/asyncio support. |
| `starlette` | `>=0.40.0` | `1.3.1` | Underlying ASGI toolkit powering FastAPI requests, responses, status codes, and exceptions. |
| `pydantic` | `>=2.10.0` | `2.13.4` | Data validation, serializing request/response schemas, and type enforcement. |
| `pydantic-settings` | `>=2.7.0` | `2.15.0` | Hierarchical environment configuration management supporting `.env` parsing. |
| `python-dotenv` | `>=1.0.0` | `1.2.2` | Loads environment variables from `.env` files into application runtime. |
| `sqlalchemy` | `>=2.0.30` | `2.0.52` | Modern ORM for session management, migrations, transcript chunk queries, and SQLite fallback. |
| `psycopg2-binary` | `>=2.9.10` | `2.9.13` | Standalone PostgreSQL database driver with prebuilt binary wheels for Windows. |
| `pgvector` | `>=0.3.6` | `0.5.0` | Vector similarity search extension for PostgreSQL storing transcript embeddings. |
| `httpx` | `>=0.28.0` | `0.28.1` | Next-generation asynchronous HTTP client used for real-world web research and scraping. |
| `bleach` | `>=6.2.0` | `6.4.0` | Defense-in-depth HTML sanitization protecting against prompt injection and XSS. |
| `python-multipart` | `>=0.0.20` | `0.0.32` | Streaming form data and file upload parser for FastAPI endpoints. |
| `requests` | `>=2.32.0` | `2.34.2` | Synchronous HTTP library utilized for Ollama bridge health checks and fallbacks. |
| `numpy` | `>=1.26.0` | `2.4.6` | Numerical vector math, cosine similarity calculations, and array normalization. |
| `tiktoken` | `>=0.7.0` | `0.14.0` | BPE tokenizer for measuring transcript chunk context windows and token constraints. |
| `anthropic` | `>=0.40.0` | `1.5.0` | Official Anthropic Python SDK for Claude 3.5 Sonnet cloud intelligence. |
| `openai` | `>=1.57.0` | `3.5.0` | Official OpenAI Python SDK for GPT-4o cloud inference and embeddings. |
| `groq` | `>=0.11.0` | `0.11.0` | High-speed LPU inference SDK for Groq Llama 3.3 70B models. |
| `google-genai` | `>=0.1.0` | `0.1.0` | Next-generation official Google GenAI SDK for Gemini 2.5 / 3.x models. |
| `pypdf` | `>=4.0.0` | `4.3.1` | Native PDF document parsing and text extraction engine. |
| `python-docx` | `>=1.1.0` | `1.1.2` | Microsoft Word (`.docx`) document processing and table extraction. |
| `openpyxl` | `>=3.1.0` | `3.1.5` | Excel spreadsheet (`.xlsx`, `.csv`) data analytics and sheet parsing. |
| `pytest` | `>=8.3.0` | `9.1.1` | Automated test runner for unit, integration, performance, and resilience tests. |
| `pytest-asyncio` | `>=0.25.0` | `1.4.0` | Pytest plugin for testing asynchronous FastAPI endpoints and SSE streams. |

---

## Frontend Web Requirements (`frontend/package.json`)

| Package | Installed Version | Role & Functional Responsibility |
|---|---|---|
| `react` | `^19.0.0` | Core declarative UI component library. |
| `react-dom` | `^19.0.0` | DOM renderer for React components. |
| `vite` | `^6.0.0` | Next-generation frontend build tool and hot-module dev server. |
| `tailwindcss` | `^4.0.0` | Utility-first CSS engine implementing dark mode, glassmorphism, and responsive layout. |
| `@phosphor-icons/react` | `^2.1.0` | Curated executive SVG icon set for navigation, source categories, and status indicators. |
| `marked` | `^15.0.0` | GFM markdown parser rendering executive advisory prose and tables. |
| `dompurify` | `^3.2.0` | Client-side HTML sanitizer ensuring zero XSS in rendered markdown. |

---

## Installation & Setup Instructions

### 1. Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 3. Run Automated Tests
```bash
python -m pytest backend/tests/ -v
```

### 4. Start Local Development Services
```bash
# Terminal 1: Backend API Server
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2: Frontend Dev Server
cd frontend
npm run dev
```

---

## Technical Notes on Dependency Resolution

1. **`psycopg2-binary` Wheel Resolution on Windows**:
   - Pinned versions like `psycopg2-binary==2.9.10` do not offer precompiled binary wheels for newer Python releases (e.g. Python 3.14), triggering source compilation failures if PostgreSQL client headers (`pg_config`) are absent.
   - Using `psycopg2-binary>=2.9.10` allows pip to resolve compatible prebuilt wheels (`2.9.13`), eliminating build dependencies.

2. **Package Hierarchy & Path Resolution**:
   - `backend/__init__.py` and `backend/app/__init__.py` inject the backend directory into `sys.path` so that both `import app...` and `import backend.app...` resolve uniformly in IDEs and test runners.

3. **Multi-Model Provider Imports**:
   - `anthropic`, `openai`, `groq`, and `google-genai` are imported with graceful handling in `backend/app/models/provider.py` to support offline and containerized environments.
