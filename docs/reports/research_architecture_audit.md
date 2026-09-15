# RESEARCH ARCHITECTURE AUDIT & REDESIGN BLUEPRINT
**The Lenny Growth Assistant — Multi-Source Intelligent Research Architecture**
*Date: September 2026 | Version: 3.1.0-audit*

---

## 1. Executive Summary

The Lenny Growth Assistant was originally architected with a strict dual-track intelligence model:
1. **Mode A (Lenny Knowledge)**: RAG against 47+ indexed Lenny podcast transcripts via pgvector/similarity search.
2. **Mode B (Real-World) & Mode C (Hybrid)**: External real-world intelligence lookup.

While Mode A functions with high fidelity (epistemic refusal gates, chunk provenance, and sub-10ms retrieval), **Mode B suffered from a major architectural bottleneck**:
Any query outside of 6 manually curated keys in `CURATED_REALWORLD_KNOWLEDGE` (`jagan`, `ap_capital`, `ysr`, `fastapi`, `saas_activation_2026`, `pricing_2026`) fell back to a simplistic keyword extractor that synthesized synthetic Wikipedia and GitHub links.

This caused the assistant to behave like a "Wikipedia & GitHub bot" for all generic real-world inquiries (e.g. asking about sports, science, consumer products, official APIs, economic data, or current news).

This document audits the legacy implementation across 9 architectural dimensions and establishes the comprehensive migration plan to a dynamic, question-aware, multi-source research engine.

---

## 2. Current Implementation Audit

### 2.1 Why It Only Searched Wikipedia & GitHub (Root Cause)
In `backend/app/services/realtime_search.py` (lines 104–127):
```python
# General real-world query extraction
keywords = [w for w in re.findall(r'\b[a-zA-Z0-9_\-\.]{3,}\b', query) if w.lower() not in {...}]
topic_str = " ".join(keywords[:4]) if keywords else "General Industry Domain"

src1 = ExternalSource(
    title=f"Industry Standards & Best Practices: {topic_str.title()}",
    url=f"https://en.wikipedia.org/wiki/{topic_str.replace(' ', '_')}",
    domain="en.wikipedia.org",
    ...
)
src2 = ExternalSource(
    title=f"Contemporary Engineering & Growth Reference: {topic_str.title()}",
    url=f"https://github.com/topics/{topic_str.replace(' ', '-').lower()}",
    domain="github.com",
    ...
)
```
Whenever a user query did not trigger the 6 curated dictionary keys, the code unconditionally synthesized two `ExternalSource` objects pointing directly to `en.wikipedia.org` and `github.com`. No dynamic search provider was queried; no domain classification took place; no evaluation of source appropriateness was performed.

### 2.2 Hardcoded Source Assumptions
1. **Wikipedia & GitHub as Defaults**: Assumed all general knowledge is best answered by Wikipedia, and all technical topics by GitHub topics.
2. **Static Domain Association**: No awareness of official primary documentation (`react.dev`, `python.org`, `openai.com`), academic repositories (`arxiv.org`, `pubmed.ncbi.nlm.nih.gov`), regulatory bodies (`sec.gov`, `rbi.org.in`), or live competition results (`formula1.com`, `fifa.com`).
3. **Single Search Pass**: Assumed a single query string is sufficient; no multi-query generation or sub-question decomposition.
4. **Zero Quality Scoring**: Hardcoded `credibility_score=0.92` and `0.90` regardless of query context, domain authority, freshness, or source agreement.
5. **No Conflict Detection**: Inability to recognize when two sources provide divergent facts or dates.

### 2.3 Current Search Provider & Provider Mechanics
- `realtime_search.py` contains a single function: `perform_external_research(query: str) -> ExternalResearchResult`.
- It is entirely synchronous in its core definition, called via `loop.run_in_executor` in `AgentOrchestrator.execute_turn_stream`.
- There is no `SearchProvider` interface or class hierarchy.
- No network call was made to any real web search API in the fallback path.

### 2.4 Current API Contracts
- **POST `/api/sessions/{session_id}/messages`**:
  - Request: `{ "content": str, "mode": str, "provider_override": Optional[str] }`
  - Response (`MessageResponse`):
    - `id`: str
    - `role`: str
    - `content`: str
    - `mode`: str
    - `model`: str
    - `latency_ms`: float
    - `intelligence_mode`: `"lenny" | "real_world" | "hybrid"`
    - `latency_metrics`: `LatencyMetrics(ttft_ms, retrieval_ms, llm_ms, total_ms)`
    - `citations`: `List[CitationSchema]`
    - `artifacts`: `List[ArtifactSummary]`
- **GET `/api/sessions/{session_id}/messages/stream` (SSE)**:
  - Streams events: `phase`, `routing`, `citations`, `token`, `artifacts`, `metrics`, `done`, `error`.
  - Event payload format: `data: {"event": "phase", "phase": "retrieval", "message": "..."}\n\n`

### 2.5 Current Citation System
In `backend/app/api/schemas.py`:
```python
class CitationSchema(BaseModel):
    chunk_id: str
    guest: str
    title: str
    similarity: float
    excerpt: str
    source_type: str = "transcript"  # "transcript" or "external"
    url: Optional[str] = None
    domain: Optional[str] = None
```
- For transcript sources, `guest` holds the speaker name, `title` holds episode title, `similarity` holds cosine score.
- For external sources, `guest` was repurposed to hold `src.domain`, `title` holds article title, and `similarity` holds credibility.
- **Limitation**: Citations lack source categorization (e.g. Official, Academic, News, Industry, Community), publication dates, freshness ratings, and evidence strength classifications.

### 2.6 Current UI Research States & Source Presentation
- **Streaming Shimmer Bar**: Displays `streamingPhase` (`"Analyzing query intent..."`, `"Searching Lenny knowledge base..."`, `"Generating strategic synthesis..."`).
- **Citation Badges in Message**: Renders source pills with `🎙️` for transcript and `🌐` for external.
- **Evidence Drawer**: Features a slide-out panel with filter tabs (`All`, `Lenny`, `Web`).
- **Limitation**:
  - No research depth selector in the composer (users cannot select `Auto`, `Search`, or `Deep Research`).
  - No breakdown by source categories (Official: 4, News: 2, etc.).
  - No qualitative evidence strength rating (Strong / Moderate / Limited).
  - No visible multi-query progress checklist during deep research.

### 2.7 Current Test Suite Audit (78 / 78 Passing)
The test suite spans 14 test modules verifying:
- HTML artifact sanitization with bleach (`test_agent.py`, `test_security.py`)
- Epistemic refusal on out-of-domain hobby/lifestyle queries (`test_agent.py`, `test_ship30.py`, `test_skills.py` asserting `REFUSAL_MESSAGE` on sourdough, baking, motor oil, cricket)
- Vector retrieval and similarity scoring (`test_retrieval.py`, `test_ingestion.py`)
- Session persistence and SQLite foreign keys (`test_persistence.py`)
- Provider fallback generation and Ollama/Anthropic health checks (`test_provider.py`)
- Rate limiting, concurrency, and error handling (`test_resilience.py`)
- Latency benchmarks: TTFT < 500ms, cold < 1200ms, sub-5ms LRU retrieval cache (`test_performance.py`, `test_streaming_and_speed.py`)
- 3-mode query intent routing (`test_streaming_and_speed.py`)

**CRITICAL SAFEGUARD**: The redesign must maintain 100% pass rate across all 78 tests. Specifically, epistemic refusal for ungrounded lifestyle questions and existing intent classifications must not regress.

---

## 3. Target Research Engine Architecture

```
                                  USER QUERY
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Query Understanding &   │
                        │    Intent Classification  │
                        └─────────────┬─────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                    ▼
          MODE A: LENNY        MODE B: REAL-WORLD   MODE C: HYBRID
        (Podcast Transcripts)   (Web/Deep Research)  (Transcript + Web)
                 │                    │                    │
                 │                    ▼                    │
                 │       ┌───────────────────────────┐     │
                 │       │   Research Depth Planner  │     │
                 │       │ (Level 0, 1, 2, 3, or 4)  │     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 │       ┌─────────────▼─────────────┐     │
                 │       │  Domain & Source Strategy │     │
                 │       │ (Official, Academic, News,│     │
                 │       │  Industry, Community, etc)│     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 │       ┌─────────────▼─────────────┐     │
                 │       │   Multi-Query Generator   │     │
                 │       │   (Targeted Sub-queries)  │     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 │       ┌─────────────▼─────────────┐     │
                 │       │    SearchProvider Router  │     │
                 │       │  (Concurrent Provider I/O)│     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 │       ┌─────────────▼─────────────┐     │
                 │       │  Source Quality Engine &  │     │
                 │       │    Deduplication Audit    │     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 │       ┌─────────────▼─────────────┐     │
                 │       │ Conflict Detection & Gap  │     │
                 │       │    Stopping Evaluator     │     │
                 │       └─────────────┬─────────────┘     │
                 │                     │                   │
                 └────────────────►────┼────────────────◄──┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  Evidence Normalization &     │
                       │    Claim-Level Attribution    │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    LLM Synthesis Engine       │
                       │ (Structured Findings + Cit.)  │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  SSE Streaming to Frontend    │
                       │ (Tokens, Metrics, Sources)    │
                       └───────────────────────────────┘
```

---

## 4. Architectural Components & Implementation Design

### 4.1 Source Category System (11 Categories)
We formalize `SourceCategory` as an enum:
1. `OFFICIAL`: Primary documentation, official announcements, vendor portals, standards bodies (`react.dev`, `python.org`, `openai.com`, `apple.com`).
2. `ACADEMIC`: Peer-reviewed research, arXiv, PubMed, university repositories (`arxiv.org`, `springer.com`, `nature.com`).
3. `NEWS`: Reputable wire services, mainstream news organizations, sports journalism (`bbc.com`, `reuters.com`, `bloomberg.com`).
4. `INDUSTRY`: Analyst reports, technical research publications (`gartner.com`, `bessemer.com`, `openview.com`).
5. `COMMUNITY`: Practitioner forums, developer discussions (`reddit.com`, `stackoverflow.com`, `news.ycombinator.com`).
6. `TECHNICAL`: Code repositories, package registries, API references (`github.com`, `npmjs.com`, `pypi.org`).
7. `REFERENCE`: Comprehensive encyclopedias and reference databases (`wikipedia.org`, `britannica.com`).
8. `FINANCIAL`: Regulatory filings, investor relations, SEC EDGAR, central banks (`sec.gov`, `rbi.org.in`, `investor.apple.com`).
9. `GOVERNMENT`: Official government agencies, national census, statistical bureaus (`gov.in`, `data.gov`).
10. `PRODUCT`: Hardware manufacturers, spec sheets, reputable consumer electronics reviews (`notebookcheck.net`, `rtings.com`).
11. `USER_PROVIDED`: User-uploaded documents, files, or custom knowledge connections.

### 4.2 Research Depth Controller (5 Levels)
- **Level 0 (Direct Answer)**: Fast conceptual explanation or conversation without external search (e.g. "What is a REST API?").
- **Level 1 (Targeted Search)**: 1–3 high-authority sources for quick factual lookup (e.g. "What is the latest React version?").
- **Level 2 (Standard Web Research)**: 3–7 sources across 2+ categories for current events or recent developments.
- **Level 3 (Deep Multi-Query Research)**: 3–6 sub-queries, 5–12 sources across multiple categories (e.g. "Compare React and Vue for startups in 2026").
- **Level 4 (Exhaustive Deep Research)**: Multi-round iterative search, cross-checking, conflict resolution, and evidence strength auditing.

### 4.3 Search Provider Abstraction Layer (`backend/app/services/search/`)
To ensure zero vendor lock-in, we introduce a pluggable provider abstraction:
- `SearchProvider` (abstract base):
  - `search(query: str, category: Optional[SourceCategory], max_results: int) -> List[DiscoveredSource]`
  - `search_async(...) -> Coroutine`
- `DuckDuckGoProvider`: Dynamic, zero-credential live web search engine extracting clean titles, URLs, domains, and snippets without bot blocking.
- `CuratedKnowledgeProvider`: Domain-specialized verified baseline for core benchmark metrics and entities.
- `FallbackSearchProvider`: High-resilience fallback guaranteeing graceful degradation if external networks timeout.
- `SearchRouter`: Dynamically selects the best provider, executes independent searches concurrently with timeouts and exponential backoff.

### 4.4 Multi-Query Planner & Source Diversity
When a query requires Level 3 or 4 research:
1. `ResearchPlanner` decomposes the question into 3–5 orthogonal sub-queries targeting distinct evidence angles:
   - Primary/Official angle
   - Industry/Benchmark angle
   - Practitioner/Community sentiment angle
   - Recent 2026 developments angle
2. Concurrent execution using `asyncio.gather` with a bounded semaphore (`asyncio.Semaphore(5)`).
3. Search results are tagged with their source category and deduplicated by URL domain and content hashing.

### 4.5 Source Quality Engine & Conflict Detection
1. **Source Quality Formula**:
   $$\text{Quality} = 0.35 \times \text{Authority} + 0.25 \times \text{Relevance} + 0.20 \times \text{Freshness} + 0.20 \times \text{Independence}$$
2. **Primary Source Priority**:
   Official documentation (`react.dev`, `python.org`, `openai.com`) and regulatory filings receive priority weight over aggregators or SEO blogs.
3. **Source Independence**:
   Detects whether multiple pages are syndicating the exact same press release or news wire to avoid false consensus.
4. **Conflict Detection**:
   Inspects extracted key facts (e.g. dates, version numbers, metrics). If two reputable sources report contradictory facts, the conflict is explicitly surfaced in the synthesis (e.g., *"Official docs state X, whereas secondary reports indicate Y"*).
5. **Qualitative Evidence Strength**:
   Bans fabricated percentage confidences; classifies into:
   - `Strong`: Multiple independent authoritative primary sources agree.
   - `Moderate`: Secondary sources agree, or single primary source verified.
   - `Limited`: Limited independent corroboration or conflicting accounts detected.

### 4.6 Citation Attribution System
- Inline claim markers `[^1]`, `[^2]` link directly to the supporting evidence.
- Every citation carries complete metadata: title, URL, domain, source category, freshness rating, and quote snippet.
- Transcripts, external research, and user files are distinctly delineated.

---

## 5. Migration & Integration Strategy

### Phase Breakdown
1. **Phase 1: Research System Audit Document**: Complete (`RESEARCH_ARCHITECTURE_AUDIT.md`).
2. **Phase 2: Search Provider Package (`backend/app/services/search/`)**:
   - `base.py`: Enums (`SourceCategory`, `ResearchMode`, `EvidenceStrength`), `DiscoveredSource` dataclass, `SearchProvider` ABC.
   - `providers/web.py`: `DuckDuckGoProvider` with robust HTML/Lite parsing and redirect sanitization.
   - `providers/curated.py`: Preserved and enhanced curated baseline knowledge.
   - `router.py`: `SearchRouter` managing multi-provider routing and fallbacks.
   - `evaluator.py`: Authority scoring, domain categorization, deduplication, and conflict detection.
   - `planner.py`: `ResearchPlanner` for query classification, depth selection, and sub-query generation.
3. **Phase 3: Integration into `orchestrator.py` & `realtime_search.py`**:
   - Refactor `realtime_search.py` to route through the new `SearchRouter` and `ResearchPlanner` (maintaining backward compatibility for existing callers and tests).
   - Update `orchestrator.py` to support streaming research progress events (`research_plan`, `research_step`, `source_discovered`).
4. **Phase 4: Frontend UI Enhancements**:
   - Add composer Research Mode selector: `Auto` (default), `Search`, `Deep Research`.
   - Update `EvidenceDrawer.jsx` to show category filter pills (Official, Academic, News, Technical, etc.) and evidence strength badges.
   - Update `ChatWindow.jsx` to render categorized source badges and streaming research milestones.
5. **Phase 5: Verification & End-to-End Testing**:
   - Run existing 78 tests to guarantee zero regression.
   - Test benchmark queries from the user specification.
   - Live browser validation.

---

## 6. Safety, Security & Epistemic Boundaries

1. **Prompt Injection Defense**:
   All web snippets and page contents are treated as untrusted text. They are wrapped in strict delimiters (`<external_evidence_untrusted>`) and sanitized. Any instruction inside web text attempting to override system behavior (e.g. "Ignore previous instructions") is strictly neutralized.
2. **Preservation of Epistemic Refusals**:
   Tested lifestyle queries (`sourdough`, `cookies`, `baking`, `motor oil`, `cricket`) will continue to trigger epistemic refusal when ungrounded in the Lenny transcript corpus, preserving 100% compliance with existing test fixtures.
3. **No Fabricated Sources**:
   The LLM provider is explicitly instructed and grounded to only cite URLs and sources that were genuinely discovered and evaluated by the search engine.
