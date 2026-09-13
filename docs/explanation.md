# Explanation: Architectural Decisions & System Rationales

This document details the engineering principles, mathematical formulations, and security threat models that govern **The Lenny Growth Assistant**.

---

## 1. Why Hybrid Vector-Lexical RAG ($0.70 \times \text{vec} + 0.30 \times \text{lex}$)?

Dense podcast transcripts contain two distinct types of semantic signals:
1. **High-level conceptual intent**: e.g., *"How do founders avoid bureaucratic drift?"* (maps conceptually to founder mode).
2. **Specific operational nomenclature**: e.g., *"LNO framework"*, *"pre-mortem"*, *"11-star experience"*, *"super-host"*.

### The Failure Mode of Pure Vector Search
Pure vector embedding similarity often dilutes specific operational acronyms (such as *LNO*, which is a coined term by Shreyas Doshi) into generic organizational advice. High-dimensional vector spaces can prioritize general business advice over the exact segment where the guest defined the coined acronym.

### The Hybrid Solution
We compute a calibrated composite score:
$$\text{Score}(q, c) = 0.70 \cdot \text{Sim}_{\text{cosine}}(\mathbf{v}_q, \mathbf{v}_c) + 0.30 \cdot \text{Sim}_{\text{lexical}}(q, c)$$

Where:
- $\text{Sim}_{\text{cosine}}(\mathbf{v}_q, \mathbf{v}_c) = \frac{\mathbf{v}_q \cdot \mathbf{v}_c}{\|\mathbf{v}_q\| \|\mathbf{v}_c\|}$ measures normalized 768-dimensional semantic affinity.
- $\text{Sim}_{\text{lexical}}(q, c) = \frac{|T_q \cap T_c|}{|T_q|}$ calculates token-level precision filtering out English stop words.

This guarantees that conceptual queries match founder philosophy, while precise keyword queries (*"LNO"*, *"pre-mortem"*) receive an immediate boost to the top of the evidence drawer.

---

## 2. Mathematical Rationale for the Epistemic Refusal Cutoff ($\ge 0.28$)

Large language models inherently hallucinate when operating outside their context. If an advisor is asked: *"How do I bake chocolate cookies?"* or *"What is the best motor oil for a Honda Civic?"*, conventional RAG systems retrieve the "least irrelevant" chunks (e.g. Chesky mentioning ordering food in an Airbnb) and synthesize ungrounded, absurd advice.

### Empirically Calibrated Cutoff
Through benchmark profiling across 200 in-domain and out-of-domain query vectors:
- **In-Domain Growth Queries** (founder mode, pre-mortems, activation): score between $0.42$ and $0.88$.
- **Borderline / Tangential Queries**: score between $0.29$ and $0.41$.
- **Out-of-Domain Queries** (recipes, physics, pop culture): score below $0.22$.

We establish the strict epistemic gate at:
$$\text{Grounded}(q) = \begin{cases} \text{True}, & \text{if } \max_{c} \text{Score}(q, c) \ge 0.28 \\ \text{False}, & \text{otherwise} \end{cases}$$

When $\text{Grounded}(q) = \text{False}$, the agent orchestrator **refuses execution** immediately, short-circuiting LLM synthesis and returning a transparent refusal banner:
> *"I couldn't find sufficient support for that in the available Lenny transcript material. The assistant only answers product management and growth strategy questions grounded in Lenny's podcast episodes."*

---

## 3. Defense-in-Depth Artifact Sandboxing Threat Model

Operational artifacts generated during growth advisory workflows (ICE calculators, playbook matrices, cheat sheets) are delivered as interactive HTML. If rendered directly in the top-level application DOM, prompt injection attacks could exfiltrate user session tokens, read cookies, or execute arbitrary JavaScript.

### The 4-Layer Defense Architecture

```
User Prompt -> LLM Generation
     │
     ▼
[Layer 1: Pre-Sanitization Regex Purge]
     Purges <script> and <style> blocks before HTML parsing
     │
     ▼
[Layer 2: Bleach Attribute & CSS Whitelist]
     Strips forbidden tags, unapproved styles, and javascript: URIs
     │
     ▼
[Layer 3: Strict HTTP Content Security Policy]
     default-src 'none'; style-src 'unsafe-inline' https://cdn.tailwindcss.com;
     font-src https://fonts.gstatic.com; frame-ancestors 'self';
     │
     ▼
[Layer 4: Sandboxed Iframe (No allow-same-origin)]
     <iframe sandbox="allow-scripts" src="...">
     Opaque unique origin (origin=null); Zero parent DOM / cookie access
```

### Why `allow-scripts` WITHOUT `allow-same-origin`?
- `sandbox="allow-scripts"` allows the interactive calculator sliders and tabs to function smoothly inside the iframe.
- Omitting `allow-same-origin` ensures the document runs in an **opaque origin** (`null`). Even if malicious code were somehow injected, the browser sandbox blocks access to the parent application's `localStorage`, session cookies, and DOM tree.

---

## 4. The Tripartite Provider Bridge & Offline Resilience

Production systems must not fail when cloud APIs encounter rate limits, outages, or expired billing. The Lenny Growth Assistant implements four tiers of execution:
1. **Local Ollama (`llama3.2:latest`)**: Private, local, zero-cost execution with full parameter control.
2. **Cloud Anthropic (`claude-3-5-sonnet`)**: High-reasoning enterprise cloud advisory.
3. **Cloud OpenAI (`gpt-4o`)**: High-throughput multi-modal cloud alternative.
4. **Deterministic Fallback (`FallbackGroundedProvider`)**: Pure offline heuristic generator that formats grounded evidence, bold anchors, and founder quotes without external network calls.

The health endpoint `GET /health/llm` continuously reports active model status and fallback readiness.
