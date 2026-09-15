# Root-Cause Audit: Current AI Answering System Failure

**Document Status**: Complete Forensic Audit  
**Date**: September 2026  
**Scope**: Root-cause analysis of generic, nonsensical, and predetermined responses across general-purpose queries.

---

## 1. Executive Summary & Core Root Causes

When a user submits legitimate general-purpose queries such as:
- `"What is the time complexity of merge sort?"`
- `"who is rebal star prabhas"`

The application returns generic corporate/business management language (e.g. *"Standard implementations prioritize clarity, measurable feedback loops, and robust documentation"*) or synthetic domain evidence headers (e.g. *"Verified domain evidence retrieved... Strategic Implications & Recommendation"* with fake IETF/Arxiv citations).

The forensic audit reveals **four interlocking root causes** that form an execution trap:

1. **Active LLM Provider Call Fails Silently (HTTP 404)**:
   - In `backend/app/core/config.py` (line 33), the configured model was `GEMINI_MODEL = "gemini-1.5-flash"`.
   - In the current Google GenAI API (`v1beta`), `gemini-1.5-flash` returns `404 NOT_FOUND` (*"models/gemini-1.5-flash is not found for API version v1beta, or is not supported for generateContent"*).
   - In `backend/app/models/provider.py` (`GeminiProvider.generate` and `generate_stream`), the exception is caught after retries, logged as a warning, and execution silently falls through to `FallbackGroundedProvider()`.

2. **Hardcoded Universal Template in `FallbackGroundedProvider`**:
   - In `backend/app/models/provider.py` (lines 1816–1832), if a query does not match hardcoded string checks (like `"recursion"` or `"write a python"`), it falls into the `UNIVERSAL REAL-WORLD INTELLIGENCE FALLBACK`.
   - This block formats the query into a fixed corporate template:
     ```markdown
     # {Title}
     > 🌐 Source: Domain knowledge base & established standards
     ### Direct Answer
     Regarding {clean_q}:
     1. Definition & Core Concept: {clean_q} represents an established principle across contemporary industry, technology, and organizational architecture.
     2. Key Findings & Evidence:
        - Standard implementations prioritize clarity, measurable feedback loops, and robust documentation.
        - Empirical validation out-performs speculative assumptions across real-world deployments.
     3. Implications & Best Practices:
        - Establish transparent metrics and clear operational accountability.
        - Benchmark against peer organizations and top-quartile industry performers.
     ```
   - This is the exact text the user observed for *"What is the time complexity of merge sort?"*.

3. **Synthetic / Mock Search Source Generation**:
   - In `backend/app/services/search/web_provider.py` (lines 441–472), when DuckDuckGo Lite is blocked or returns non-200 (DDG Lite returns HTTP 403 bot-detection), the search provider invokes `_get_domain_fallback(query)`.
   - `_get_domain_fallback` generates fake sources with synthetic URLs on `ietf.org`, `arxiv.org`, and `engineering.guide`:
     ```python
     DiscoveredSource(
         title=f"Technical Reference & Standards for {query[:30]}",
         url=f"https://standards.ietf.org/doc/{abs(hash(query)) % 10000}",
         domain="ietf.org",
         snippet=f"Authoritative technical specification and protocol overview covering {query}.",
         category=SourceCategory.TECHNICAL,
         ...
     )
     ```
   - For `"who is rebal star prabhas"`, it generated a fake source claiming `standards.ietf.org` hosts a technical specification for Prabhas!
   - In `backend/app/services/realtime_search.py` (lines 90–100), another fake source generator creates `https://official.standards.org/reference` if search yields no results.

4. **Rigid Research Response Synthesis Forcing Corporate Templates**:
   - In `backend/app/models/provider.py` (lines 1684–1710), when research context is passed into `FallbackGroundedProvider`, it forces all answers into:
     ```markdown
     ### Direct Conclusion
     Based on dynamic multi-source research, **{user_prompt}** is supported by verified documentation and authoritative reference data.
     ### Key Findings
     1. Verified domain evidence retrieved for {user_prompt}. [^1]
     2. Multiple authoritative sources corroborate active standard industry implementations. [^2]
     ### What the Evidence Says
     ### Strategic Implications & Recommendation
     - Verify Against Primary Authorities: For mission-critical decisions...
     - Continuous Monitoring: Track upstream announcements and developer adoption metrics...
     ```
   - Even when real LLM generation is attempted, `RESEARCH_SYSTEM_PROMPT` in `backend/app/agents/prompts.py` (lines 18–28) instructs the model to force every research query into *"Direct Conclusion -> Key Findings -> Evidence Breakdown -> Variations/Caveats -> Sources"*.

---

## 2. Exact Files Responsible

| File Path | Lines | Nature of Issue |
|---|---|---|
| `backend/app/core/config.py` | Line 33 | Hardcoded stale model identifier `GEMINI_MODEL = "gemini-1.5-flash"` causing 404 in Google GenAI API. |
| `backend/app/models/provider.py` | Lines 688–751 | `GeminiProvider.generate` silently catches model failure and delegates to `FallbackGroundedProvider`. |
| `backend/app/models/provider.py` | Lines 753–777 | `GeminiProvider.generate_stream` catches failure and yields chunks from `FallbackGroundedProvider.generate_stream`. |
| `backend/app/models/provider.py` | Lines 1680–1710 | `FallbackGroundedProvider._execute_deterministic` forcing fake "Key Findings" and "Strategic Implications". |
| `backend/app/models/provider.py` | Lines 1735–1780 | Hardcoded code templates (reverse string, dummy functions) instead of calling a real coding LLM. |
| `backend/app/models/provider.py` | Lines 1816–1832 | `UNIVERSAL REAL-WORLD INTELLIGENCE FALLBACK` generating corporate jargon for all unmatched queries. |
| `backend/app/services/search/web_provider.py` | Lines 441–472 | `DuckDuckGoProvider._get_domain_fallback` synthesizing fake URLs on `standards.ietf.org` and `arxiv.org`. |
| `backend/app/services/search/curated_provider.py` | Lines 12–90 | Hardcoded static entity dictionary (`ysr`, `jagan`, `cm_ap`, `ap_capital`, `fastapi`, `saas_activation_2026`, `pricing_2026`). |
| `backend/app/services/realtime_search.py` | Lines 90–100 | Fake fallback source `https://official.standards.org/reference` when research returns no results. |
| `backend/app/agents/prompts.py` | Lines 18–28 | `RESEARCH_SYSTEM_PROMPT` prescribing rigid corporate structure regardless of query nature. |
| `backend/app/agents/orchestrator.py` | Line 940 | Hardcoded status message `"Generating strategic synthesis..."` emitted via SSE. |
| `frontend/src/App.jsx` | Line 14, 149, 160 | `activeMode` default initialized to `'research'` instead of general-purpose `'chat'`. |

---

## 3. Exact Functions & Components Responsible

### A. `GeminiProvider.generate` & `generate_stream` (`backend/app/models/provider.py`)
- **Signature**: `def generate(self, request, *args, **kwargs)` / `def generate_stream(...)`
- **Fault**: Catches Google GenAI API exceptions (such as `404 NOT_FOUND` for `gemini-1.5-flash`), logs a warning, and silently switches to `FallbackGroundedProvider`. The system never surfaces the provider error or dynamically falls back to an active model (such as `gemini-2.5-flash` or `gemini-flash-latest`).

### B. `FallbackGroundedProvider._execute_deterministic` (`backend/app/models/provider.py`)
- **Signature**: `def _execute_deterministic(self, system_prompt: str, user_prompt: str, context: str, history: List[Dict]) -> str`
- **Fault**: Contains a ladder of string matching. If a query matches neither Lenny transcripts nor specific keywords (`"what is python"`, `"recursion"`, `"write code"`), it executes lines 1818–1832, outputting generic corporate boilerplate. If context is provided from research, it outputs lines 1684–1710 with fake findings and strategic implications.

### C. `DuckDuckGoProvider._get_domain_fallback` (`backend/app/services/search/web_provider.py`)
- **Signature**: `def _get_domain_fallback(self, query: str) -> List[DiscoveredSource]`
- **Fault**: When live search fails (DDG Lite returns HTTP 403 bot detection), it invents synthetic source objects with fabricated URLs like `https://standards.ietf.org/doc/{hash}`.

### D. `QueryUnderstandingEngine.analyze` (`backend/app/services/capability/intent_router.py`)
- **Signature**: `def analyze(self, query: str, user_mode_override: Optional[str] = None, session_history: Optional[List[Dict[str, str]]] = None) -> IntentClassification`
- **Fault**: Uses keyword matching on phrases like `"who is"`, `"who won"` to force `AgentCapability.WEB_RESEARCH`, which triggers the search engine and then the synthetic evidence fallback when the provider 404s.

---

## 4. End-to-End Execution Data Flow (As-Is vs. To-Be)

### As-Is Failure Flow: Example 1 — "What is the time complexity of merge sort?"

```
USER QUERY: "What is the time complexity of merge sort?"
        │
        ▼
Orchestrator: classify intent via QueryUnderstandingEngine
        │  Matches: neither coding keyword nor "who is"
        ▼  Classified as: AgentCapability.GENERAL_QA (no web research)
        │
Orchestrator: calls get_llm_provider("gemini")
        │
        ▼
GeminiProvider: attempts client.models.generate_content(model="gemini-1.5-flash")
        │
        ▼
Google GenAI API: Returns 404 NOT_FOUND ("models/gemini-1.5-flash is not found")
        │
        ▼
GeminiProvider: Exception caught -> silently invokes FallbackGroundedProvider
        │
        ▼
FallbackGroundedProvider._execute_deterministic()
        │  Query is not "python", not "recursion", not "reverse a string"
        ▼  Falls into UNIVERSAL REAL-WORLD INTELLIGENCE FALLBACK
        │
        ▼
OUTPUT:
"# What Is The Time Complexity Of Merge Sort
 > Source: Domain knowledge base & established standards
 1. Definition & Core Concept: What is the time complexity of merge sort represents
    an established principle across contemporary industry, technology, and organizational architecture.
 2. Key Findings & Evidence:
    - Standard implementations prioritize clarity, measurable feedback loops, and robust documentation.
    - Empirical validation out-performs speculative assumptions across real-world deployments.
 3. Implications & Best Practices:
    - Establish transparent metrics and clear operational accountability."
```

### As-Is Failure Flow: Example 2 — "who is rebal star prabhas"

```
USER QUERY: "who is rebal star prabhas"
        │
        ▼
Orchestrator: QueryUnderstandingEngine sees "who is" -> classifies as WEB_RESEARCH
        │
        ▼
SearchRouter: executes DuckDuckGoProvider.search("who is rebal star prabhas")
        │
        ▼
DuckDuckGo Lite: Returns HTTP 403 Forbidden (bot detection)
        │
        ▼
DuckDuckGoProvider: calls _get_domain_fallback("who is rebal star prabhas")
        │  Fabricates source: title="Technical Reference & Standards for who is rebal star prabhas"
        │  url="https://standards.ietf.org/doc/4777", domain="ietf.org"
        ▼
Orchestrator: packages fake source context into context_str -> calls GeminiProvider
        │
        ▼
GeminiProvider: model="gemini-1.5-flash" -> 404 NOT_FOUND -> FallbackGroundedProvider
        │
        ▼
FallbackGroundedProvider._execute_deterministic(): sees context is present
        │  Forces output into lines 1684-1710:
        ▼
OUTPUT:
"# Who Is Rebal Star Prabhas
 > Research Engine: Synthesized from verified real-world sources and public records.
 ### Direct Conclusion
 Based on dynamic multi-source research, who is rebal star prabhas is supported
 by verified documentation and authoritative reference data.
 ### Key Findings
 1. Verified domain evidence retrieved for who is rebal star prabhas. [^1]
 2. Multiple authoritative sources corroborate active standard industry implementations. [^2]
 ### Strategic Implications & Recommendation
 - Verify Against Primary Authorities: For mission-critical decisions...
 - Continuous Monitoring: Track upstream announcements and developer adoption metrics..."
```

---

## 5. Answers to the 12 Mandatory Root-Cause Inquiries

### 1. Exact Source of Incorrect Responses
The incorrect responses originate from **`FallbackGroundedProvider._execute_deterministic`** in `backend/app/models/provider.py` (lines 1684–1710 and 1816–1832). This deterministic fallback provider was invoked because `GeminiProvider` failed with an HTTP 404 error when attempting to call `gemini-1.5-flash`.

### 2. Exact Files Responsible
- `backend/app/core/config.py` (line 33)
- `backend/app/models/provider.py` (lines 688–777, 1680–1710, 1735–1780, 1816–1832)
- `backend/app/services/search/web_provider.py` (lines 441–472)
- `backend/app/services/search/curated_provider.py` (lines 12–90)
- `backend/app/services/realtime_search.py` (lines 90–100)
- `backend/app/agents/prompts.py` (lines 18–28)
- `frontend/src/App.jsx` (lines 14, 149, 160)

### 3. Exact Function/Component Responsible
- `GeminiProvider.generate` & `generate_stream` in `backend/app/models/provider.py`
- `FallbackGroundedProvider._execute_deterministic` in `backend/app/models/provider.py`
- `DuckDuckGoProvider._get_domain_fallback` in `backend/app/services/search/web_provider.py`
- `CuratedKnowledgeProvider` in `backend/app/services/search/curated_provider.py`

### 4. Why the User's Question is Being Ignored
The LLM call never actually executes against a real, working model due to the 404 on the stale model identifier. The application catches this error and routes the question into a deterministic fallback module. That fallback does not use an LLM; it uses hardcoded Python `if/elif` string checks. When the question does not match the hardcoded strings, it falls into a canned corporate template that substitutes `{clean_q}` into phrases like *"{clean_q} represents an established principle across contemporary industry, technology, and organizational architecture."*

### 5. Whether Retrieval is Wrong
- **Lenny Retrieval**: The Lenny transcript retrieval engine is **correctly isolated**. In `AgentOrchestrator`, Lenny retrieval is strictly gated behind `query_analysis.allow_lenny_retrieval`. Non-Lenny queries like merge sort and Prabhas are correctly blocked from accessing the transcript vector store. Unrelated Lenny context was NOT injected into these queries.
- **Web Search Retrieval**: The live search retrieval **fails due to HTTP 403 bot detection on DuckDuckGo Lite**, and instead of surfacing search unavailability, it invokes a fallback that synthesizes fake source records.

### 6. Whether Prompts are Wrong
- `GENERAL_QA_SYSTEM_PROMPT` in `backend/app/agents/prompts.py` is sound.
- `RESEARCH_SYSTEM_PROMPT` is overly rigid, commanding the model to format answers into *"Direct Conclusion -> Key Findings -> Evidence Breakdown -> Variations/Caveats -> Sources"* and forcing strategic recommendations into factual queries.

### 7. Whether Model Routing is Wrong
`ModelRouter` in `backend/app/models/router.py` defaults to routing auto requests to Gemini. However:
- It does not perform dynamic capability or health checks on model names before routing.
- It assumes `gemini-1.5-flash` is valid without querying Google's Model Service catalog (`client.models.list()`).
- It lacks automatic discovery of installed local Ollama models or live provider catalogs.

### 8. Whether the LLM Response is Being Overwritten
The real LLM response is **not being overwritten**—the real LLM call **never succeeded** in the first place because the API threw a 404. The catch block in `GeminiProvider` intercepted the exception and generated the deterministic fallback output instead.

### 9. Whether Frontend is Rendering Stale/Mock Data
The frontend (`App.jsx` and `ChatWindow.jsx`) is **NOT generating mock responses**. It faithfully renders the Server-Sent Events (SSE) token stream emitted by the backend. However:
- `App.jsx` line 14 defaults `activeMode` to `'research'`, which passes `mode: 'research'` to the backend on initial query submissions instead of `'chat'`.

### 10. Whether Backend is Returning a Template
**YES.** `FallbackGroundedProvider._execute_deterministic` in `backend/app/models/provider.py` (lines 1816–1832) returns a literal string template containing:
*"1. Definition & Core Concept: {clean_q} represents an established principle across contemporary industry..."*
*"2. Key Findings & Evidence: Standard implementations prioritize clarity, measurable feedback loops, and robust documentation..."*

### 11. Whether Citations are Synthetic
**YES.** When live search fails, `DuckDuckGoProvider._get_domain_fallback` creates synthetic citations pointing to:
- `https://standards.ietf.org/doc/{hash}`
- `https://arxiv.org/abs/{hash}`
- `https://engineering.guide/article/{hash}`
- `https://official.standards.org/reference`

### 12. Proposed Fix
1. **Dynamic Model Discovery & Catalog Validation**: Replace hardcoded model strings with live catalog discovery (`client.models.list()` for Gemini, `/api/tags` for Ollama, and respective official model catalogs for Anthropic/OpenAI/Groq).
2. **Eliminate Fake / Synthetic Generation**:
   - Completely remove `UNIVERSAL REAL-WORLD INTELLIGENCE FALLBACK` and canned string branches.
   - Remove fake URL synthesis (`standards.ietf.org`, `engineering.guide`, `standards.org`). If search yields no results or is unavailable, report real status or rely on the LLM's verified knowledge base.
   - Remove hardcoded entity dictionaries from `curated_provider.py` and `realtime_search.py`.
3. **Dynamic Response Composer**: Build a task-adaptive `ResponseComposer` that formats responses naturally according to intent (conceptual explanation, biography, code block, research report, debug analysis).
4. **Resilient Provider Fallback Chain**: If a selected model fails, fail over to a healthy configured provider (e.g. Gemini -> Anthropic -> OpenAI -> Groq -> Ollama) rather than generating canned fake text. If all providers are down, return an honest error message.
5. **Real Search Integration**: Implement resilient search using real HTTP search APIs with valid User-Agents and multi-provider fallbacks.
6. **Frontend Default Alignment**: Default `activeMode` to `'chat'` and dynamically display active models from the backend registry.

---

## 6. Where Predetermined Answers and Fake Research Originate

```
[Repository Root]
├── backend/app/models/provider.py
│   ├── Lines 1684–1710: Fake findings & strategic implications template
│   ├── Lines 1713–1734: Hardcoded "what is python" response
│   ├── Lines 1735–1780: Hardcoded C++ and Python reverse_string / solution snippets
│   ├── Lines 1795–1814: Hardcoded "understanding recursion" response
│   └── Lines 1816–1832: UNIVERSAL REAL-WORLD INTELLIGENCE FALLBACK ("measurable feedback loops...")
├── backend/app/services/search/web_provider.py
│   ├── Lines 375–440: Hardcoded query keyword mappings (f1, fifa, laptop)
│   └── Lines 441–472: Synthetic IETF/Arxiv citation generator
├── backend/app/services/search/curated_provider.py
│   └── Lines 12–90: Hardcoded entity dict (ysr, jagan, cm_ap, amaravati, fastapi, saas_activation)
└── backend/app/services/realtime_search.py
    └── Lines 90–100: Synthetic `https://official.standards.org/reference` source generator
```

---

## 7. Where Lenny Context is Injected & Verified Boundary

- **Location**: `backend/app/agents/orchestrator.py` (lines 235–255 and 706–747)
- **Gating Mechanism**:
  ```python
  query_analysis = relevance_router.analyze_query(content)
  if (classification.capability == AgentCapability.LENNY_RESEARCH and query_analysis.allow_lenny_retrieval) or is_off_topic_test:
      # Only here are Lenny transcripts retrieved
  ```
- **Finding**: Lenny transcript vector retrieval is **already properly gated** for non-Lenny queries. The irrelevant responses observed for merge sort and Prabhas did **NOT** come from Lenny transcripts. They came from `FallbackGroundedProvider` and synthetic search fallbacks.

---

## 8. Where Model Responses are Generated & Why They Were Bypassed

- **Generation Site**:
  - Synchronous: `backend/app/agents/orchestrator.py` (lines 487–495)
  - Streaming: `backend/app/agents/orchestrator.py` (lines 969–985)
- **Why Bypassed**:
  - `provider = get_llm_provider(override=provider_override)` returned `GeminiProvider`.
  - `GeminiProvider` used `self.model = settings.GEMINI_MODEL`, which was `"gemini-1.5-flash"`.
  - The Google GenAI v1beta API rejected this with `404 NOT_FOUND`.
  - Lines 744–751 and 772–776 caught the 404 exception and redirected to `FallbackGroundedProvider`.

---

## 9. Where Responses are Transformed & Template-Forced

1. **In `FallbackGroundedProvider`**:
   - Directly injects title headers, `Key Findings`, `What the Evidence Says`, and `Strategic Implications & Recommendation`.
2. **In `RESEARCH_SYSTEM_PROMPT`** (`backend/app/agents/prompts.py` lines 18–28):
   - Instructs the model: *"For complex inquiries, provide: Direct Conclusion -> Key Findings -> Evidence Breakdown -> Variations/Caveats -> Sources."*
3. **In `AgentOrchestrator` Status Stream** (`backend/app/agents/orchestrator.py` line 940):
   - Emits `'message': 'Generating strategic synthesis...'` even for simple math or coding questions.

---

## 10. Frontend Data Verification

- **Is the frontend generating mock data?** **NO.**
  - Inspected `frontend/src/App.jsx`, `ChatWindow.jsx`, and `services/api.js`.
  - The frontend sets up an `EventSource` / `fetch` reader against `/api/chat/stream` and appends incoming tokens directly to the message state.
  - The markdown renderer (`renderMarkdown`) formats whatever text the backend delivers.
- **Frontend Defect**:
  - In `frontend/src/App.jsx` (line 14), `activeMode` is initialized to `'research'`. This causes every new session to send `mode: "research"` until changed by the user.

---

## 11. Proposed Corrected Architecture

```
                                  USER QUERY
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Conversation Manager    │
                        │ (Context, Memory, History)│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    Intent Understanding   │
                        │  & Capability Matcher     │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │  Context Relevance Gate   │
                        │(Filter irrelevant history/│
                        │   transcripts/evidence)   │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │       Task Planner        │
                        │ (Direct / Research / Code)│
                        └─────────────┬─────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
     [Direct Knowledge]                           [External Actions]
   - Math / Algorithms                          - Real-time Web Search
   - Logic / Definitions                        - Local Codebase Tools
   - Stable Explanations                        - File Extraction (PDF/CSV)
               │                                - Lenny Archive (only if requested)
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    Model Registry &       │
                        │    Dynamic Discovery      │
                        │ (Discovers live models:   │
                        │  Gemini, Ollama, OpenAI,  │
                        │  Anthropic, Groq)         │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │     Model Router &        │
                        │     Resilient Chain       │
                        │ (Routes to best live model│
                        │  with failover fallback)  │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │     Response Composer     │
                        │ (Dynamic format: direct,  │
                        │  code, bio, report)       │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    Quality Gate Check     │
                        │ (Answers actual question? │
                        │  No fake citations?       │
                        │  No corporate filler?)    │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                                    USER
```

---

## 12. Migration Plan (Phases A through O)

- **PHASE A (Current)**: Forensic Root-Cause Audit (`ANSWER_GENERATION_ROOT_CAUSE.md`). **[COMPLETED - STOP HERE FOR USER REVIEW]**
- **PHASE B**: Remove fake/synthetic response generation, canned question ladders, and synthetic citation generators.
- **PHASE C**: Fix query understanding and context relevance routing (ensure clean separation between general QA, coding, search, and Lenny).
- **PHASE D**: Fix direct LLM answering (guarantee clean system prompt and direct response flow).
- **PHASE E**: Implement dynamic provider abstraction (`LLMProvider`, `ProviderRegistry`).
- **PHASE F**: Implement dynamic model discovery (discover live models from provider APIs and local Ollama).
- **PHASE G**: Implement intelligent model routing and resilient failover chains.
- **PHASE H**: Implement real web research with verified external sources (no fake citations).
- **PHASE I**: Implement dedicated coding and debugging capabilities.
- **PHASE J**: Implement file intelligence integration (PDF, CSV, code analysis).
- **PHASE K**: Implement deep research engine with cross-checking and multi-source synthesis.
- **PHASE L**: Implement response verification and quality gate.
- **PHASE M**: Implement ChatGPT-like conversational memory and follow-up management.
- **PHASE N**: Frontend UI updates (dynamic model selector, mode alignment to chat).
- **PHASE O**: Full E2E evaluation across the comprehensive regression test suite.

---

## 13. Test Plan

### Automated Regression Matrix

| Test ID | Query | Expected Output | Forbidden Content |
|---|---|---|---|
| **TEST-01** | `"What is the time complexity of merge sort?"` | $O(n \log n)$ best, average, worst; explanation of divide-and-conquer. | Brian Chesky, Lenny, startup, strategic implications, industry implementations. |
| **TEST-02** | `"Who is Prabhas?"` | Biography of Indian actor Prabhas (Telugu cinema, Baahubali, Kalki). | Merge sort, software architecture, Lenny, startup growth. |
| **TEST-03** | `"Who is the current CM of Andhra Pradesh?"` | Nara Chandrababu Naidu (assumed office June 2024). | Brian Chesky, Lenny, merge sort, stale political data. |
| **TEST-04** | `"What did Brian Chesky say on Lenny's Podcast?"` | Founder Mode, product reviews, un-scaling, transcript-grounded citations. | Refusal or generic Wikipedia summary. |
| **TEST-05** | `"Write a C++ program for binary search."` | Complete, runnable C++ code with complexity explanation. | Lazy placeholders (`// TODO`), generic business text. |
| **TEST-06** | `"What is the latest React version?"` | Current React version information verified from official documentation. | Stale hallucination, fake IETF standards link. |
| **TEST-07** | `"Research the current AI coding-agent market."` | Multi-source research report on coding assistants. | Canned corporate template with fake citations. |
| **TEST-08** | `"Explain quantum computing to a beginner."` | Clear educational explanation using qubits and superposition. | Unnecessary research templates, corporate jargon. |

### Adversarial Retrieval Test
1. Seed the vector store with 100+ Lenny podcast transcript chunks (Chesky, Elena Verna, Shreyas Doshi).
2. Submit general queries: `"What is merge sort?"` and `"Who is Prabhas?"`.
3. Assert with 100% strictness that zero transcript chunks and zero podcast names enter the LLM context or final response.

---

**AUDIT COMPLETE. STOPPING FOR USER REVIEW BEFORE PROCEEDING TO IMPLEMENTATION.**
