# Manual UI Test Plan (5-Minute Evaluator Guide)
**Platform:** The Lenny Growth Assistant  
**Target Audience:** Take-Home Evaluator & Forward Deployed Engineers  
**Duration:** ~5 Minutes  

This manual test plan guides an evaluator through the core user flows of the application to verify end-to-end functionality, model toggling, grounding refusal, content generation, and sandboxed artifact rendering.

---

## Pre-Flight Setup
1. Launch the full stack (via Docker or bare-metal):
   ```powershell
   # Bare-metal quickstart:
   .\scripts\run_local.ps1
   ```
   Or using Docker Compose:
   ```bash
   docker compose up -d --build
   ```
2. Open the web interface in your browser: [http://localhost:3000](http://localhost:3000).

---

## Test Scenario 1: Health & Dynamic Model Discovery
- **Objective:** Verify system status and multi-model configuration layer.
- **Action:**
  1. Observe the top navigation header.
  2. Click the model dropdown (currently showing **Auto Router** or active model).
  3. Click **Discover Models** (refresh icon).
- **Expected Outcome:**
  - Status indicators show green/healthy.
  - Dropdown lists discovered models across Google Gemini, Local Ollama, and Cloud providers.
  - Active model status badge displays real-time health.

---

## Test Scenario 2: In-Domain Grounded Q&A with Citations
- **Objective:** Verify transcript retrieval, accurate citations, and evidence grounding.
- **Action:**
  1. Click **New Session** in the sidebar.
  2. Send the query:
     > *"How did Brian Chesky rebuild Airbnb after its 80% revenue drop during COVID?"*
- **Expected Outcome:**
  - Response streams tokens in real-time.
  - Phase badge indicates: `Analyzing query` -> `Retrieving transcript knowledge` -> `Synthesizing insights`.
  - The answer details Chesky's leadership decisions (cutting performance marketing, doubling down on PR/brand, founders mode).
  - Explicit citations appear below the message (linking to Brian Chesky's episode).
  - Clicking a citation opens the **Evidence Drawer** showing the exact transcript excerpt and similarity score.

---

## Test Scenario 3: Epistemic Refusal Guarantee (Zero Hallucination)
- **Objective:** Verify that out-of-domain questions are transparently refused rather than answered with hallucinated founder stories.
- **Action:**
  1. In the same chat, send the following out-of-domain question:
     > *"What is the best sourdough bread recipe for high altitudes?"*
- **Expected Outcome:**
  - The system triggers the epistemic refusal banner.
  - The response transparently acknowledges that the question is outside Lenny's podcast scope.
  - Zero transcript citations are fabricated; 0% domain leakage from previous turns.

---

## Test Scenario 4: Ship 30 for 30 Content Skill (~1,250-Word Viral Essay)
- **Objective:** Verify the Ship 30 for 30 writing framework skill.
- **Action:**
  1. In the input prompt toolbar, switch mode from `Auto / Research` to `Ship 30 for 30`.
  2. Send the query:
     > *"Write a viral essay on Shreyas Doshi's LNO framework for ruthless prioritization."*
- **Expected Outcome:**
  - Generates an extensive, highly structured essay (~1,250 words).
  - Formats with:
    - A punchy, counterintuitive Hook attacking conventional roadmap bloat.
    - The Tension / Antagonist.
    - 3 Core Pillars (Leverage, Neutral, Overhead) with bold anchor sentences and direct guest quotes.
    - A 5-Point Actionable Takeaway checklist.
    - A punchy one-line closing outro.

---

## Test Scenario 5: Growth Canvas & Sandboxed Interactive Artifacts
- **Objective:** Verify side-by-side artifact generation and sandboxed iframe isolation.
- **Action:**
  1. In the input prompt toolbar, switch mode to `Growth Experiments`.
  2. Send the query:
     > *"Design a growth experiment to reduce onboarding drop-off and include an ICE calculator."*
- **Expected Outcome:**
  - Assistant produces a structured experiment specification (Hypothesis, OEC metrics, ICE Score, 48-hour smoke test).
  - Automatically extracts the `<artifact type="html" title="ICE Prioritization Calculator">` block.
  - The **Growth Canvas** panel opens beside the chat.
  - The interactive HTML calculator renders inside a sandboxed iframe (`sandbox="allow-scripts"` without `allow-same-origin`, with strict CSP `default-src 'none'`).
  - Sliders/inputs in the calculator work smoothly in real time.

---

## Test Scenario 6: Mandatory Local Ollama Model Toggle
- **Objective:** Verify that the platform runs offline on a local model without external API keys.
- **Action:**
  1. Ensure Ollama is running locally (`ollama serve` with `ollama run llama3.2`).
  2. In the top header model selector, select **Local Ollama (llama3.2)**.
  3. Send any product question (e.g. *"What are the best habits of top product leaders?"*).
- **Expected Outcome:**
  - Request routes to `http://localhost:11434/api/generate`.
  - Model badge displays `Ollama (llama3.2)`.
  - Response streams or renders locally with zero cloud API keys required.

---

## Summary Scorecard

| # | Test Scenario | Verified |
|---|---|:---:|
| 1 | System Health & Model Discovery | [x] |
| 2 | Grounded Q&A & Transcript Citations | [x] |
| 3 | Epistemic Refusal Banner | [x] |
| 4 | Ship 30 for 30 Viral Essay Engine | [x] |
| 5 | Interactive Growth Canvas & Security Sandbox | [x] |
| 6 | Local Ollama Toggle & Offline Execution | [x] |
