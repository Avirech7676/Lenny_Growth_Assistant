# 🎥 The Lenny Growth Assistant — 2 to 3 Minute Demo Video Script

**Take-Home Assessment Deliverable #8**  
**Role:** Forward Deployed Engineer  
**Submission Form:** [https://forms.gle/LgotDHNVxW1mbzNE7](https://forms.gle/LgotDHNVxW1mbzNE7)  
**Target Duration:** 2 minutes 30 seconds  
**Setup Requirement:** Screen recording with **Webcam / Face Camera enabled in corner** (via Loom, OBS Studio, or Zoom).

---

## ⏱️ Video Timeline & Teleprompter Script

### [0:00 - 0:35] Part 1: Problem Framing & Engineering Mission
- **Screen:** Show your face clearly on webcam + browser open at `http://localhost:3000`.
- **Spoken Script:**
  > *"Hi everyone! I’m presenting The Lenny Growth Assistant, built for the Forward Deployed Engineer assessment.*
  >
  > *Product and growth teams struggle with two acute problems: first, hundreds of hours of high-signal podcast transcripts remain locked in audio and text files; second, generic LLMs hallucinate on niche growth queries and fail to produce shippable, interactive operational tools.*
  >
  > *My goal was to build an executive-grade AI assistant grounded strictly in Lenny’s transcript repository, running locally on Ollama without external dependencies, and safely rendering interactive growth artifacts inside an origin-isolated sandbox."*

---

### [0:35 - 1:15] Part 2: Grounded Q&A, Evidence Citations & Follow-Up Context
- **Screen:** Type or click starter prompt: *"How does Brian Chesky run product reviews at Airbnb?"*
- **Action:**
  1. Watch tokens stream in real time (<250ms TTFT).
  2. Point to the bold anchor quotes and timestamped citations (`[Citation 1]`).
  3. Click to open the **Evidence Drawer** on the right to show the raw transcript chunk and similarity score.
  4. Type follow-up: *"How does he contrast this with traditional delegation?"*
- **Spoken Script:**
  > *"Here, when I ask how Brian Chesky runs product reviews, our hybrid retriever queries 768-dimensional embeddings in PostgreSQL with lexical re-ranking. The model provides direct quotes about running the company like an orchestra, complete with timestamped citations. In the Evidence Drawer, evaluators can trace every claim back to the exact transcript chunk.*
  >
  > *Notice that follow-up context is preserved seamlessly across turns."*

---

### [1:15 - 1:40] Part 3: Epistemic Refusal Gate (Zero Hallucination)
- **Screen:** Type out-of-domain prompt: *"How do I bake chocolate cookies with sea salt?"*
- **Action:** Show the system refuse cleanly with the transparent banner.
- **Spoken Script:**
  > *"Now watch what happens when I ask an out-of-domain question: 'How do I bake chocolate cookies?'.*
  >
  > *Instead of inventing founder baking anecdotes or falling back to unverified web search, our Epistemic Refusal Gate triggers instantly at our similarity cutoff of 0.28. It transparently admits that Lenny's transcripts do not support this answer. Zero hallucination is guaranteed."*

---

### [1:40 - 2:05] Part 4: Ship 30 Essay & Interactive Growth Canvas
- **Screen:** Click *"Ship 30 Essay"* mode or prompt: *"Design a referral growth experiment for B2B SaaS with an interactive calculator artifact"*.
- **Action:**
  1. Show the split-screen **Growth Canvas** slide in from the right.
  2. Interact with the live HTML calculator inside the iframe (adjust sliders, recalculate ICE scores).
- **Spoken Script:**
  > *"Next, the system supports dedicated operational skills. Here, it transforms growth advice into a structured Ship 30 for 30 essay, and automatically generates an interactive ICE Prioritization Calculator rendered natively in our Growth Canvas.*
  >
  > *The artifact is fully interactive—I can adjust impact and confidence sliders right here beside the chat."*

---

### [2:05 - 2:40] Part 5: Local Ollama Demonstration & Core Technical Trade-Off
- **Screen:** Open header model dropdown and switch to `llama3.2` (or show Ollama local execution logs in terminal).
- **Spoken Script:**
  > *"Crucially, the entire system runs locally. In the header dropdown, I switch the active model to `llama3.2` powered by a local Ollama daemon. If an evaluator is offline with zero API keys, our deterministic grounded synthesizer takes over automatically.*
  >
  > *Finally, our key technical trade-off: **Client-Side Iframe Isolation vs. Native Dynamic Component Rendering**.*
  >
  > *We deliberately chose an origin-isolated iframe with strict Content Security Policy (`default-src 'none'`) and `sandbox="allow-scripts"` without `allow-same-origin`. While rendering native React components would have been easier, native components create severe XSS attack vectors from untrusted LLM output. Our iframe approach guarantees complete DOM and cookie isolation while preserving 100% interactivity.*
  >
  > *Thank you, and I look forward to working together!"*

---

## 📋 Evaluator Video Checklist (Before Uploading)

- [ ] **Camera Enabled**: Candidate face is visible throughout the video.
- [ ] **Duration**: Between 2:00 and 3:00 minutes.
- [ ] **Problem Explained**: Explicitly stated in the first 30 seconds.
- [ ] **Live UI Demonstrated**: Grounded Q&A, Evidence Drawer, and Growth Canvas shown.
- [ ] **Local Ollama Demonstrated**: Switched or demonstrated running locally.
- [ ] **Technical Trade-Off Stated**: Iframe sandboxing vs native components explained.
- [ ] **Upload**: Uploaded as Unlisted or Public to YouTube or Loom and URL pasted into [Submission Form](https://forms.gle/LgotDHNVxW1mbzNE7).
