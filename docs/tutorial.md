# Tutorial: 3-Minute Evaluator Test Flight

Welcome to **The Lenny Growth Assistant**! This step-by-step tutorial will guide an evaluator through experiencing the full 10-star product journey in less than 3 minutes.

---

## 1. Quickstart Launch (30 Seconds)

You can launch the entire stack using either Docker Compose or bare-metal execution.

### Option A: One-Command Startup Launcher (Recommended)
In PowerShell, execute:
```powershell
.\scripts\run_local.ps1
```
*The script automatically detects if Docker is running; if Docker Desktop is offline, it seamlessly activates local bare-metal mode with SQLite fallback.*

### Option B: Docker Compose
```bash
docker compose up -d --build
```

### Option C: Manual Bare-Metal Runtimes
**Terminal 1 (Backend):**
```powershell
$env:PYTHONPATH=".;backend"
python -m ingestion.ingest
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm install
npm run dev
```

Open your browser to: **[http://localhost:3000](http://localhost:3000)**.

---

## 2. Test Flight 1: Grounded Research Mode (45 Seconds)

1. Open the Growth Assistant dashboard. Notice the **Electric Emerald** status pill in the header showing provider health and active model (`lenny-synthesizer-v1` or `llama3.2:latest`).
2. In the top Mode Selector, ensure **🔍 Grounded Research** is selected.
3. Click on the first starter card:
   > *"Explain Brian Chesky's founder mode and why excessive A/B testing can kill bold product design."*
4. **Observe**:
   - The assistant synthesizes a structured tactical response with bold anchors and quoted wisdom.
   - Grounded citation badges appear under the response (e.g. `Chesky: 84% match`).
   - In the right-hand **Growth Canvas**, click the **Grounding Evidence** tab to see the exact transcript excerpts and similarity percentages.

---

## 3. Test Flight 2: Ship 30 for 30 Viral Essay (45 Seconds)

1. In the Mode Selector, click **✍️ Ship 30 Essay**.
2. Click the starter prompt:
   > *"Write a Ship 30 for 30 essay on Shreyas Doshi's LNO framework for product leader prioritization."*
3. **Observe**:
   - The essay renders with the mandatory 5 sections:
     1. **The Hook**: Counterintuitive opening attacking startup dogma.
     2. **The Tension**: Why traditional time management traps fail.
     3. **Three Core Pillars**: Leverage, Neutral, and Overhead tasks with bold anchor sentences and direct quotes.
     4. **The 5-Point Takeaway Checklist**: Immediate action items for 9 AM tomorrow.
     5. **The Punchy Outro**: Memorable closing one-liner.

---

## 4. Test Flight 3: Growth Experiment & Sandboxed Canvas (45 Seconds)

1. In the Mode Selector, click **🧪 Growth Experiments**.
2. Submit the following prompt in the chat input:
   > *"Generate an ICE growth experiment to improve signup-to-activation conversion by removing upfront credit card paywalls."*
3. **Observe**:
   - The assistant formats a structured experiment with Hypothesis, Primary Metric, Guardrail Metric, and calculated ICE score.
   - An **Operational Artifact** card appears in the chat message: `🛠️ Generated Operational Artifact: Activation Funnel ICE Test`.
   - In the right-hand **Growth Canvas**, the sandboxed iframe loads:
     - Styled according to `DESIGN.md` (Deep Slate `#0A0E17`, Electric Emerald `#10B981`, Plus Jakarta Sans / Inter).
     - Interactive ICE calculation sliders that update real-time.
     - Protected by Content Security Policy and origin isolation (`sandbox="allow-scripts"` without `allow-same-origin`).

---

## 5. Test Flight 4: Epistemic Refusal Gate (15 Seconds)

1. Switch to **🔍 Grounded Research** mode.
2. Submit an out-of-domain prompt:
   > *"How do I bake chocolate chip cookies from scratch?"*
3. **Observe**:
   - The system intercepts the query using the **Epistemic Refusal Gate** (cutoff < 0.28).
   - An amber warning banner appears:
     > *"I couldn't find sufficient support for that in the available Lenny transcript material. The assistant only answers product management and growth strategy questions grounded in Lenny's podcast episodes."*
   - Notice that the assistant refuses transparently rather than hallucinating founder advice or cookie recipes.

---

## 6. Next Steps

- Explore [How-To Guides](file:///c:/Users/avina/OneDrive/Desktop/Lenny_Growth_Assistant/docs/how-to.md) for custom transcript ingestion and cloud LLM keys.
- Read [Reference](file:///c:/Users/avina/OneDrive/Desktop/Lenny_Growth_Assistant/docs/reference.md) for full REST API specs.
- Read [Explanation](file:///c:/Users/avina/OneDrive/Desktop/Lenny_Growth_Assistant/docs/explanation.md) for deep-dive RAG math and sandbox threat modeling.
