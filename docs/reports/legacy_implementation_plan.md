# Implementation Plan & Engineering Roadmap
# The Lenny Growth Assistant

**Current Sprint Lifecycle:** 30-Stage Autonomous Delivery (gstack & Antigravity Governance)  
**Active Stage:** Stage 0 — Discovery, Requirements & Repository Baseline  
**Next Stage:** Stage 1 — Product Strategy & 10-Star Experience  

---

## 1. Stage-by-Stage Engineering Matrix

| Stage | Stage Name | Focus & Core Deliverables | Target Verification | Status |
|---|---|---|---|---|
| **Stage 0** | **Discovery & Baseline** | Map requirements, inspect skills & environment, produce baseline PRD, architecture, design, and roadmap. | Acceptance criteria review; zero source code written. | **IN PROGRESS (Active)** |
| **Stage 1** | **Product Strategy** | Define 10-star evaluator journey, epistemic trust model, core user flows, and differentiated decision skills. | Update PRD with evaluator journey and non-negotiables. | PENDING |
| **Stage 2** | **System Architecture** | Concrete schema, API contracts, Mermaid data flows, security boundaries, and failure topologies. | Review architecture against assignment requirements. | PENDING |
| **Stage 3** | **Design System** | UI/UX Pro Max tokens, typography scales, layout blueprints, motion rules, and anti-slop checks. | Design review against 3 master dials. | PENDING |
| **Stage 4** | **Repo Foundation** | Monorepo scaffolding, linting, Docker configs, dev scripts, and .env.example. | DevEx review & clean directory tree. | PENDING |
| **Stage 5** | **Database & Persistence** | PostgreSQL 16 + pgvector schema, Alembic/SQL migrations, CRUD models for sessions/messages/artifacts. | Actual container connect, insert, and read tests. | PENDING |
| **Stage 6** | **FastAPI Foundation** | REST endpoints (`/health*`, `/sessions`, `/retrieve`, `/artifacts`), Pydantic validation, structured errors. | Automated pytest suite for all endpoints. | PENDING |
| **Stage 7** | **Ingestion Pipeline** | Transcript parser, metadata extractor, chunking with overlap, vector embeddings, and refresh pipeline. | Run ingestion on curated podcast transcripts. | PENDING |
| **Stage 8** | **RAG / Retrieval Engine**| Cosine similarity search, keyword boosting, candidate reranker, context builder, and similarity cutoff gate. | Precision/recall test on known queries; refusal test. | PENDING |
| **Stage 9** | **Agent Layer & Routing** | Orchestrator with bounded skills (Research, Ship30, Playbook, Artifact, Grounding Verifier). | Unit tests for intent routing and skill boundaries. | PENDING |
| **Stage 10**| **Ship 30 for 30 Skill** | Dedicated ~1,250-word viral essay writer with hook, progression, scannable anchors, and verified citations. | Automated word count, structure, and citation test. | PENDING |
| **Stage 11**| **Decision-Support Skills**| Growth Experiment Generator, Playbook Generator, and Challenge My Thinking engine. | Automated generation and schema validation tests. | PENDING |
| **Stage 12**| **Model Abstraction** | Provider interface supporting local Ollama (`llama3.2`) and Cloud Anthropic/OpenAI without code changes. | End-to-end inference verification across providers. | PENDING |
| **Stage 13**| **Artifact Generation** | Complete Markdown and HTML/CSS generator with full-output enforcement (zero placeholders/TODOs). | Validation of generated HTML and Markdown structures. | PENDING |
| **Stage 14**| **Secure Artifact Viewer**| Defense-in-depth isolation: DOMPurify sanitization + sandboxed `<iframe>` (`sandbox="allow-scripts"`). | XSS injection test suite (scripts, event handlers). | PENDING |
| **Stage 15**| **Frontend Implementation**| React/Tailwind v4 split-canvas UI, streaming chat, source drawer, telemetry pills, and responsive layout. | UI verification at 375px, 768px, and 1440px. | PENDING |
| **Stage 16**| **Full E2E Integration** | Connect Browser -> Frontend -> FastAPI -> Postgres -> Agent -> Retriever -> Ollama -> Viewer. | Matrix of all 8 core integration connections passing. | PENDING |
| **Stage 17**| **Resilience Engineering** | Deliberate chaos testing: Ollama offline, DB failure, missing API keys, oversized payloads, timeouts. | Verify graceful error states and structured logs. | PENDING |
| **Stage 18**| **Security Review** | OWASP Top 10 + STRIDE threat modeling, secret scanning, SQL injection, prompt injection mitigation. | Security audit report with zero unhandled findings. | PENDING |
| **Stage 19**| **Code Review & Quality** | Staff engineer code audit, dead code pruning, type checking, and complexity reduction. | Static analysis and linting clean pass. | PENDING |
| **Stage 20**| **Automated Testing** | Comprehensive test pyramid: unit, integration, retrieval, agent routing, and persistence tests. | Full test suite execution with high coverage. | PENDING |
| **Stage 21**| **Real Browser QA** | Headless and visual browser automation testing full user flows and edge cases. | Playwright test run passing with zero console errors. | PENDING |
| **Stage 22**| **Performance Review** | Measure TTFT, retrieval latency, model inference latency, and bundle size. | Benchmarks documented in OPERATIONS.md. | PENDING |
| **Stage 23**| **Documentation & Handoff**| Complete README, PRD, architecture, design, OPERATIONS, TESTING, and TROUBLESHOOTING docs. | Evaluator documentation audit pass. | PENDING |
| **Stage 24**| **Agent Transcripts** | Maintain audit trail in `agent-transcripts/` capturing decisions, failures, root causes, and fixes. | Complete transcript log files generated. | PENDING |
| **Stage 25**| **Release Candidate** | Feature freeze, release checklist verification, and pre-release test execution. | All items in RELEASE_CHECKLIST.md verified. | PENDING |
| **Stage 26**| **Fresh-Clone Evaluator Test**| Clone into clean temporary directory, run `docker compose up`, verify evaluator demo flow end-to-end. | Zero manual fixes required on clean clone. | PENDING |
| **Stage 27**| **Release & Deployment** | Final packaging, Git tags, Docker image build verification, and release artifacts. | Clean git tree and production container build. | PENDING |
| **Stage 28**| **Post-Deploy Canary** | SRE monitoring check: HTTP 5xx, console errors, database connection health, and model stability. | 10-minute continuous health verification. | PENDING |
| **Stage 29**| **Retrospective & Handoff**| Produce `FINAL_HANDOFF.md` detailing architecture, operational guide, evaluator demo path, and lessons. | Final project sign-off. | PENDING |

---

## 2. Hard Gates & Verification Protocol

1. **Gate 0 (Discovery Complete)**: Discovery artifacts (`PRD.md`, `architecture.md`, `design.md`, `IMPLEMENTATION_PLAN.md`, `PROJECT_STATUS.md`) committed and approved.
2. **Gate 1 (Foundation & DB)**: PostgreSQL 16 + pgvector running, migrations executed, persistence tested.
3. **Gate 2 (RAG & Grounding)**: Ingestion completed, similarity threshold $\ge 0.65$ enforced, zero hallucinations verified.
4. **Gate 3 (Agent & Model Bridge)**: Dual-model bridge tested with local Ollama (`llama3.2`) and Anthropic Claude.
5. **Gate 4 (Artifact Security)**: XSS injection vectors neutralized by DOMPurify + sandboxed iframe.
6. **Gate 5 (Browser QA & Fresh-Clone)**: Evaluator demo reproduced on fresh clone with one Docker command.
