# Stage 1 — Product Strategy & 10-Star Experience Review

**Date:** 2026-09-13  
**Agent Role:** Product Strategist & Forward Deployed Engineer  
**Governance Framework:** gstack Product Review Gates (`/plan-ceo-review`, `/plan-design-review`, `/plan-devex-review`)  

---

## 1. Multi-Lens Product Review Execution

### 1.1 CEO & Founder Review (`/plan-ceo-review`)
- **Core Question**: What is the 10-star product experience hiding inside this assessment?
- **Finding**: Evaluators review dozens of standard chatbots that dump text into a markdown box. The 10-star experience for Lenny Growth Assistant is:
  1. **Instant Evidence Verification**: A slide-over **Evidence Drawer** showing the exact podcast quote, timestamp, and cosine similarity.
  2. **Unflinching Epistemic Honesty**: Refusing out-of-domain questions with transparent clarity rather than confabulating.
  3. **High-Agency Content Generation**: Generating a true, structured, ~1,250-word Ship 30 for 30 viral essay with bold anchors.
  4. **Interactive Growth Canvas**: Rendering interactive HTML calculators and frameworks in a safe, sandboxed split canvas.
- **Scope Decision (Hold Scope + High-Leverage Wedge)**:
  - Keep core scope tight: 4 bounded skills (Research, Ship 30, Experiment, Playbook).
  - Explicitly reject live web scraping and voice synthesis to avoid deployment flakiness and GPU bloat.

### 1.2 Senior Design Review (`/plan-design-review`)
- **Core Question**: How do we eliminate generic AI slop and deliver executive-grade clarity?
- **Finding**:
  - Ban generic purple gradient cards and 3-column feature grids.
  - Establish a tailored Slate (`#0A0E17`) & Electric Emerald (`#10B981`) aesthetic.
  - Implement a dual-pane split layout: Conversation stream on the left (with session sidebar), slide-out interactive Growth Canvas on the right.
  - Emphasize telemetry: model badge with live millisecond latency, similarity percentage pills, and citation badges.

### 1.3 Developer Experience Review (`/plan-devex-review`)
- **Core Question**: What makes evaluator onboarding flawless?
- **Finding**:
  - Time-To-Hello-World (TTHW) must be `< 3 minutes`.
  - Single command startup: `docker compose up --build`.
  - Zero required cloud API keys: Default out-of-the-box execution runs 100% on local Ollama (`llama3.2`).
  - Pre-seeded vector database: The Docker startup pipeline automatically embeds the initial transcripts so the evaluator does not wait for ingestion.

---

## 2. Selected Skills & Bounded Architecture

| Skill Identifier | Trigger Mode | Expected Output | Grounding Requirement |
|---|---|---|---|
| `Grounded Research` | `mode="research"` | Nuanced tactical Q&A with citation badges | 100% grounded in retrieved chunks ($\ge 0.65$ similarity) |
| `Ship 30 for 30` | `mode="ship30"` | ~1,250-word viral essay with hook, anchors, quotes, takeaways | Grounded in guest frameworks and quotes |
| `Growth Experiment` | `mode="experiment"`| Structured ICE test card with hypothesis, metric, and smoke test | Grounded in guest case studies |
| `Growth Playbook` | `mode="playbook"` | Multi-stage Acquisition/Activation/Retention/Monetization plan | Grounded in guest tactical playbooks |
| `Artifact Sandbox` | `mode="artifact"` | Complete, standalone HTML/CSS calculator or framework widget | Sanitized with DOMPurify, isolated in `<iframe>` |

---

## 3. Epistemic Refusal Contract

When a user submits a query:
1. Retrieval engine searches `transcript_chunks` using cosine distance.
2. If top similarity score is $< 0.65$, the orchestrator immediately halts generation and returns:
   > *"I couldn't find sufficient support for that in the available Lenny transcript material. The assistant only answers questions grounded in Lenny's podcast episodes."*
3. Zero tokens are generated from base model priors, guaranteeing strict epistemic honesty.
