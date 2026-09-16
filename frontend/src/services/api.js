/**
 * API client service connecting the Growth Canvas frontend to the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    if (response.status === 204) {
      return null;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage = data?.error || data?.detail || `API request failed with status ${response.status}`;
      const err = new Error(errorMessage);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (err) {
    console.error(`[API Error] ${options.method || 'GET'} ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Health diagnostics
  getHealth: () => request('/health'),
  getDBHealth: () => request('/health/db'),
  getLLMHealth: () => request('/health/llm'),

  // Sessions
  listSessions: () => request('/api/v1/sessions'),
  searchSessions: (query) => request(`/api/v1/sessions/search?q=${encodeURIComponent(query)}`),
  createSession: (title = 'New Growth Session', metadata = {}) =>
    request('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify({ title, metadata }),
    }),
  updateSession: (sessionId, title, metadata = null) =>
    request(`/api/v1/sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title, metadata }),
    }),
  getSession: (sessionId) => request(`/api/v1/sessions/${sessionId}`),
  deleteSession: (sessionId) =>
    request(`/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
    }),

  // Messages & Agent Conversation
  getSessionMessages: (sessionId) =>
    request(`/api/v1/sessions/${sessionId}/messages`),
  postMessage: (sessionId, content, mode = 'research', researchMode = 'auto', providerOverride = null) =>
    request(`/api/v1/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        mode,
        research_mode: researchMode,
        provider_override: providerOverride,
      }),
    }),
  editUserMessage: (sessionId, messageId, content, mode = 'research', researchMode = 'auto', providerOverride = null) =>
    request(`/api/v1/sessions/${sessionId}/messages/${messageId}`, {
      method: 'PUT',
      body: JSON.stringify({
        content,
        mode,
        research_mode: researchMode,
        provider_override: providerOverride,
      }),
    }),
  regenerateMessage: (sessionId, messageId, providerOverride = null, researchMode = null) =>
    request(`/api/v1/sessions/${sessionId}/messages/${messageId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({
        provider_override: providerOverride,
        research_mode: researchMode,
      }),
    }),

  postMessageStream: async (sessionId, content, mode = 'research', researchMode = 'auto', providerOverride = null, handlers = {}, signal = null) => {
    const {
      onPhase,
      onRouting,
      onModel,
      onModelTransition,
      onToken,
      onCitations,
      onArtifacts,
      onMetrics,
      onDone,
      onError,
      onResearchPlan,
      onResearchProgress,
      onResearchSummary,
      onFollowUpSuggestions,
    } = handlers;

    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}/messages/stream`, {
        method: 'POST',
        signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          content,
          mode,
          research_mode: researchMode,
          provider_override: providerOverride,
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.error || `HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop();

        for (const block of blocks) {
          const trimmed = block.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              const evType = data.event;
              if (evType === 'phase' && onPhase) onPhase(data.phase, data.message);
              else if (evType === 'tool_call' && handlers.onToolCall) handlers.onToolCall(data);
              else if (evType === 'tool_result' && handlers.onToolResult) handlers.onToolResult(data);
              else if (evType === 'execution_verification' && handlers.onExecutionVerification) handlers.onExecutionVerification(data);
              else if (evType === 'research_plan' && onResearchPlan) onResearchPlan(data);
              else if (evType === 'research_progress' && onResearchProgress) onResearchProgress(data);
              else if (evType === 'research_summary' && onResearchSummary) onResearchSummary(data);
              else if (evType === 'routing' && onRouting) onRouting(data);
              else if (evType === 'model' && onModel) onModel(data);
              else if (evType === 'model_transition' && onModelTransition) onModelTransition(data);
              else if (evType === 'token' && onToken) onToken(data.token);
              else if (evType === 'citations' && onCitations) onCitations(data.citations);
              else if (evType === 'artifacts' && onArtifacts) onArtifacts(data.artifacts);
              else if (evType === 'quality' && handlers.onQuality) handlers.onQuality(data);
              else if (evType === 'metrics' && onMetrics) onMetrics(data.metrics);
              else if (evType === 'done' && onDone) onDone(data);
              else if (evType === 'error' && onError) onError(data.error || 'Streaming error');
            } catch (pErr) {
              console.warn('[SSE Parse Warning]', pErr);
            }
          }
        }
      }
    } catch (err) {
      console.error('[SSE Stream Error]', err);
      if (onError) onError(err);
      throw err;
    }
  },

  // Artifacts
  getArtifact: (artifactId) => request(`/api/v1/artifacts/${artifactId}`),
  getArtifactIframeUrl: (artifactId) => `/api/v1/artifacts/${artifactId}/iframe`,

  // Direct Retrieval Telemetry
  retrieveEvidence: (query, topK = 5) =>
    request('/api/v1/retrieve', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),

  // Model Platform & Live Discovery
  listModels: (provider = null, availableOnly = false) => {
    const params = new URLSearchParams();
    if (provider) params.append('provider', provider);
    if (availableOnly) params.append('available_only', 'true');
    const qs = params.toString();
    return request(`/api/models${qs ? `?${qs}` : ''}`);
  },
  discoverModels: (provider = null) =>
    request('/api/models/discover', {
      method: 'POST',
      body: JSON.stringify({ provider }),
    }),
  listTools: () => request('/api/tools'),
};
