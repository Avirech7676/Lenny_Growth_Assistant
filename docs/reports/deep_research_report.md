# Phase 6 Report: DeepResearchEngine

## Executive Overview
In **Phase 6**, the autonomous, epistemic-grade **DeepResearchEngine** was implemented to deliver structured, model-independent deep research capabilities. The engine moves far beyond brute-force web querying by introducing **adaptive research depth**, **independent-source origin detection**, **multi-round gap filling and conflict resolution**, **sufficiency-based early stopping**, **grounded claim/citation verification**, and **concise UI progress streaming** that strictly prevents any private chain-of-thought exposure.

---

## Architecture & Core Innovations

```
User Research Request
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. ADAPTIVE DEPTH CLASSIFICATION & PLANNING            │
│   • Simple: 1–3 sources (1 query, fast stop)           │
│   • Moderate: 3–7 sources (2–3 queries)                │
│   • Complex: Multi-query, multi-category               │
│   • Deep: Multi-round iterative investigation          │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 2. PARALLEL MULTI-QUERY SEARCH & DEDUPLICATION         │
│   • Canonical URL normalization (query param stripping) │
│   • Deduplication across multi-query batches           │
│   • Multi-provider execution (Curated + Web Providers) │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 3. INDEPENDENT-SOURCE DETECTION (Apex Domain Grouping) │
│   • Extracts registered apex domain / publisher        │
│   • Groups subdomains (e.g. docs.python.org &          │
│     python.org -> 1 independent origin: python.org)    │
│   • Prevents artificial consensus inflation            │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 4. SOURCE CATEGORIZATION & QUALITY EVALUATION          │
│   • 11 canonical categories (OFFICIAL, TECHNICAL,      │
│     ACADEMIC, NEWS, INDUSTRY, COMMUNITY, etc.)         │
│   • Authority scoring based on domain reputation & TLD │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 5. CONFLICT DETECTION & SUFFICIENCY EVALUATION         │
│   • Detects contradictions in dates, figures, status   │
│   • Stop Condition: Early termination when evidence    │
│     is sufficient (bounded search; no endless scraping)│
└────────────────────────────────────────────────────────┘
         │
    Insufficient or Conflicts?
    ├── Yes (Deep Mode) ──> [Round 2/3 Targeted Gap Query] ──┐
    │                                                        │
    └── No (Sufficient) ─────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 6. CLAIM & CITATION VERIFICATION                       │
│   • Claims backed by independent source corroboration  │
│   • Validated citations mapped to verified primary URLs│
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 7. FINAL SYNTHESIS & CONCISE UI PROGRESS STREAMING     │
│   • Structured ResearchReport artifact & context string│
│   • Exact 6 UI progress events (Zero CoT exposure)     │
└────────────────────────────────────────────────────────┘
```

---

## 1. Adaptive Research Depth

The engine dynamically classifies and limits research depth:

| Depth Mode | Trigger Characteristics | Source Target | Search Strategy | Sufficiency Stop Rule |
| :--- | :--- | :--- | :--- | :--- |
| **Simple** | Direct lookup, definitions, versions, single-fact queries (*e.g. "Who is CM of AP", "What is Python"*) | **1–3 sources** | 1 focused query | $\ge 1$ high-authority or $\ge 2$ agreeing sources with 0 conflicts $\to$ Stop immediately |
| **Moderate** | Explanatory, conceptual, operational queries (*e.g. "How does Python GIL work?"*) | **3–7 sources** | 2–3 orthogonal queries | $\ge 3$ sources across $\ge 2$ independent domains with 0 conflicts $\to$ Stop |
| **Complex** | Comparative evaluations, architecture tradeoffs, multi-entity queries (*e.g. "Compare Postgres vs Mongo for ledger"*) | **7–12 sources** | 3–5 queries covering architecture, benchmarks, and tradeoffs | $\ge 5$ sources across $\ge 2$ categories and $\ge 3$ independent domains with 0 conflicts $\to$ Stop |
| **Deep** | Explicit deep research requests, systematic audits, or ambiguous topics requiring iterative probe | **Multiple research rounds** (up to 3 rounds) | Round 1 initial scan $\to$ Round 2 targeted gap/conflict resolution queries | Corroborated evidence across $\ge 3$ independent domains after Round 2 $\to$ Stop |

---

## 2. Independent-Source Detection

To eliminate consensus inflation where a single publisher produces multiple URLs, the engine implements apex domain parsing via `extract_apex_domain(url_or_domain)`:
- `docs.python.org/3/library/asyncio.html` and `python.org/downloads/` $\to$ Both resolve to apex domain `python.org` (counts as **1 independent origin**).
- `data.gov.in` and `bbc.co.uk` properly respect two-part ccTLDs (`gov.in`, `co.uk`).
- Verified claims track `independent_sources: List[str]` containing only distinct apex domains that corroborate each proposition.

---

## 3. Evidence Sufficiency Stopping Condition

The engine enforces strict bounded exploration:
- **Never searches the entire internet indefinitely**.
- Stops immediately as soon as authority, independent domain diversity, and contradiction-free thresholds are met.
- Simple questions complete in a single rapid round (1–3 sources).
- Deep research bounds iterations to a maximum of 3 targeted rounds, stopping early on round 2 if sufficient evidence is established.

---

## 4. Concise UI Progress Streaming (Zero CoT Leakage)

The streaming interface (`execute_research_stream` / `stream_research_events`) emits strictly high-level, human-readable UI progress updates:

1. `Planning research`
2. `Searching`
3. `Reading sources`
4. `Comparing evidence`
5. `Verifying`
6. `Writing`

### Privacy & Chain-of-Thought Guardrail
- Automated tests strictly inspect every emitted event payload for forbidden internal reasoning tokens (`chain_of_thought`, `scratchpad`, `thought:`, `inner_thought`, `private reasoning`, `deliberation`, `hidden_state`, `system_prompt`).
- Zero internal reasoning tokens or model scratchpads are exposed to clients.

---

## 5. Verification Results

### Dedicated Phase 6 Test Suite (`test_phase6_deep_research.py`)
```
============================= test session starts =============================
backend/tests/test_phase6_deep_research.py::test_extract_apex_domain PASSED [ 10%]
backend/tests/test_phase6_deep_research.py::test_adaptive_depth_classifier PASSED [ 20%]
backend/tests/test_phase6_deep_research.py::test_adaptive_depth_simple_question PASSED [ 30%]
backend/tests/test_phase6_deep_research.py::test_adaptive_depth_moderate_question PASSED [ 40%]
backend/tests/test_phase6_deep_research.py::test_adaptive_depth_complex_question PASSED [ 50%]
backend/tests/test_phase6_deep_research.py::test_adaptive_depth_deep_multi_round PASSED [ 60%]
backend/tests/test_phase6_deep_research.py::test_independent_source_detection_and_deduplication PASSED [ 70%]
backend/tests/test_phase6_deep_research.py::test_conflict_detection_and_resolution PASSED [ 80%]
backend/tests/test_phase6_deep_research.py::test_sufficiency_stopping_condition PASSED [ 90%]
backend/tests/test_phase6_deep_research.py::test_concise_ui_progress_events_no_cot PASSED [100%]
======================= 10 passed, 1 warning in 18.51s ========================
```

### Full Application Regression Suite
```
================= 262 passed, 2 warnings in 213.59s (0:03:33) =================
```
- **Total Tests Passed**: **262 / 262 (100%)**
- **Regressions**: **0**

---

## Conclusion
Phase 6 is fully implemented, verified, and integrated with the AI Orchestrator and backend services. The DeepResearchEngine provides robust, epistemic-grade research with bounded adaptive depth, multi-round verification, independent source detection, and concise UI progress streaming.
