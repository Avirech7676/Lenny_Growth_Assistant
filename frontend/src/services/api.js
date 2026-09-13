/**
 * API client service connecting the Growth Canvas frontend to the FastAPI backend.
 */

const API_BASE = '';

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
  createSession: (title = 'New Growth Session', metadata = {}) =>
    request('/api/v1/sessions', {
      method: 'POST',
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
  postMessage: (sessionId, content, mode = 'research', providerOverride = null) =>
    request(`/api/v1/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        mode,
        provider_override: providerOverride,
      }),
    }),

  // Artifacts
  getArtifact: (artifactId) => request(`/api/v1/artifacts/${artifactId}`),
  getArtifactIframeUrl: (artifactId) => `/api/v1/artifacts/${artifactId}/iframe`,

  // Direct Retrieval Telemetry
  retrieveEvidence: (query, topK = 5) =>
    request('/api/v1/retrieve', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),
};
