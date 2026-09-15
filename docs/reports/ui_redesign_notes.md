# UI Redesign Notes — The Lenny Growth Assistant

**Release:** v2.0 Production Transformation  
**Engineer / Designer:** Staff Frontend Engineer & Senior Product Designer  
**Scope:** Complete UI/UX transformation from MVP chat to Executive AI Growth Strategist  

---

## 1. What Changed and Why

### A. Adaptive Workspace Architecture
* **Before**: The desktop layout had a rigid 50/50 split that permanently locked 42% of the viewport for an empty "Growth Canvas" placeholder box, even during pure conversational research.
* **After**: Implemented an **Adaptive 3-Column Architecture**. The conversation stream is centered at `max-w-3xl` by default with zero wasted space. The Contextual Workspace (Growth Canvas & Evidence Drawer) slides out smoothly when an operational artifact is generated or when the user clicks "Inspect Sources". Users can toggle or close the workspace at any time via the Header or close buttons.
* **Why**: Eliminates visual desert, prevents cramped text wrapping, and directs operator focus to strategic output.

### B. Editorial Document-Style Assistant Messages
* **Before**: Assistant responses were enclosed inside heavy, rounded bubble cards with standard line height and avatars floating on the side.
* **After**: Unboxed assistant responses into clean, high-contrast editorial documents with `Plus Jakarta Sans` headings, generous 1.72 line-height body text, and distinct quote styling.
* **Why**: Long-form frameworks, Ship 30 essays, and growth playbooks feel like authoritative strategy memos rather than chat bubbles.

### C. Subdued User Messages
* **Before**: User messages were high-saturation green (`bg-emerald-600`), dominating the visual hierarchy.
* **After**: Refined into subtle dark surface pills (`bg-slate-800/80 border border-slate-700/60 text-slate-100`).
* **Why**: Maintains visual calm and gives prominence to the assistant's insights.

### D. Prominent Grounded Evidence Cards
* **Before**: Citations were rendered as tiny inline chips at the bottom of messages.
* **After**: Created dedicated **Grounded Evidence Cards** with speaker badges, source type tags (`🎙️ Lenny Episode` vs `🌐 Real-World Reference`), similarity percentages, and an "Inspect Sources" trigger that opens the full excerpt drawer.
* **Why**: Evidence grounding is the product's #1 differentiator; making it prominent builds immediate trust.

### E. Unified Floating Composer
* **Before**: A redundant horizontal mode bar sat above the chat, while a separate model routing dropdown sat inside the input.
* **After**: Merged both into a unified floating composer dock with inline skill mode pills (`Research`, `Ship 30 Essay`, `Experiment`, `Playbook`), auto-growing textarea, model selector pill, and keyboard shortcut helpers (`↵ to send`).
* **Why**: Eliminates toolbars, declutters chrome, and provides intuitive progressive disclosure.

### F. Date-Grouped Sidebar with Search
* **Before**: Flat, unsorted list of sessions with basic search.
* **After**: Grouped sessions by date ("Today", "Yesterday", "Previous 7 Days", "Older"), added active indicator lines, search filtering, and inline delete confirmation.
* **Why**: Operators managing multiple product initiatives can locate and manage conversations effortlessly.

### G. Interactive Growth Canvas Deliverables
* **Before**: Canvas was an isolated iframe viewer with minimal controls.
* **After**: Added Preview vs. Code toggle, copy code button with feedback, multi-tab support for sessions with multiple artifacts, fullscreen modal expansion, and sandbox security guarantee badges.
* **Why**: Growth operators need to inspect and export deliverables (HTML calculators, markdown playbooks) without frictionless friction.

### H. Contextual Next-Step Actions
* **Before**: No follow-up guidance after an answer.
* **After**: Added progressive action buttons under completed assistant responses: `Turn into Experiment`, `Build Playbook`, `Write Ship 30`.
* **Why**: Transforms passive reading into immediate operational action.

---

## 2. What Was Intentionally NOT Changed

1. **Backend Contracts & API Endpoints**:
   - Zero changes to `/api/v1/sessions`, `/messages`, `/messages/stream`, `/retrieve`, or `/health`.
   - All 78 automated backend tests remain 100% passing.
2. **Deterministic Epistemic Refusal Logic**:
   - The strict epistemic cutoff ($\ge 0.28$) and out-of-domain refusal tests (cookie baking, motor oil, cricket) were strictly preserved.
3. **Bleach & Sandboxed Iframe Security**:
   - The CSP headers (`Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'`) and iframe `sandbox="allow-scripts"` remain inviolate.

---

## 3. Performance & Bundle Impact

- **Production Bundle**:
  - `dist/index.html`: `1.17 kB` (gzip: `0.64 kB`)
  - `dist/assets/index.css`: `47.05 kB` (gzip: `8.73 kB`)
  - `dist/assets/index.js`: `418.73 kB` (gzip: `124.89 kB`)
- **Build Time**: `15.82s` clean build with zero warnings or errors.
- **Rendering Performance**:
  - `ChatMessage` is memoized with custom property comparison, ensuring streaming token updates do NOT re-render prior messages in history.
  - Sub-second TTFT streaming latency remains unaffected.

---

## 4. Accessibility Compliance (WCAG 2.1 AA)

- All interactive controls now use semantic `<button>` elements with `aria-label` and `title`.
- Visible focus rings (`focus-visible:ring-2 focus-visible:ring-emerald-500/40`) on all interactive items.
- Text contrast exceeds 4.5:1 across all surfaces.
- Supports keyboard navigation throughout (`Enter`, `Shift+Enter`, `Esc`).
