import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import GrowthCanvas from './components/GrowthCanvas';
import LandingPage from './components/LandingPage';
import Scene from './components/Scene';
import { api } from './services/api';

export default function App() {
  // Navigation & Layout state
  const [viewMode, setViewMode] = useState('landing'); // 'landing' | 'chat'
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [workspaceTab, setWorkspaceTab] = useState('artifacts'); // 'artifacts' | 'evidence'
  const [activeMode, setActiveMode] = useState('chat');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [isDiscovering, setIsDiscovering] = useState(false);

  // Data state
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [activeArtifactId, setActiveArtifactId] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [topSimilarity, setTopSimilarity] = useState(0);
  const [isGrounded, setIsGrounded] = useState(true);
  const [lastQuery, setLastQuery] = useState('');
  const [inputPrompt, setInputPrompt] = useState('');

  // Telemetry & UI status
  const [llmHealth, setLlmHealth] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingPhase, setStreamingPhase] = useState(null);
  const [researchProgress, setResearchProgress] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);

  // Phase 8: AbortController ref for stop generation
  const abortControllerRef = React.useRef(null);


  // Active Session Title lookup
  const activeSessionTitle = useMemo(() => {
    return sessions.find((s) => s.id === activeSessionId)?.title || '';
  }, [sessions, activeSessionId]);

  // 1. Initial Health Diagnostics, Sessions & Model Discovery Fetch
  const loadInitialData = useCallback(async () => {
    try {
      const [llmRes, dbRes, sessionList, modelRes] = await Promise.all([
        api.getLLMHealth().catch(() => null),
        api.getDBHealth().catch(() => null),
        api.listSessions().catch(() => []),
        api.listModels().catch(() => null),
      ]);

      if (llmRes) setLlmHealth(llmRes);
      if (dbRes) setDbHealth(dbRes);
      if (modelRes?.models) setAvailableModels(modelRes.models);

      const list = Array.isArray(sessionList) ? sessionList : (sessionList?.sessions || []);
      if (list.length > 0) {
        setSessions(list);
        setActiveSessionId(list[0].id);
      } else {
        const newSession = await api.createSession('New Session');
        setSessions([newSession]);
        setActiveSessionId(newSession.id);
      }
    } catch (err) {
      console.error('Failed to initialize workspace data:', err);
      setErrorBanner('Failed to load initial session data.');
    }
  }, []);

  // 1b. Live Dynamic Model Discovery Handler
  const handleDiscoverModels = async (provider = null) => {
    setIsDiscovering(true);
    try {
      await api.discoverModels(provider);
      const updated = await api.listModels().catch(() => null);
      if (updated?.models) {
        setAvailableModels(updated.models);
      }
    } catch (err) {
      console.error('Failed to trigger live model discovery:', err);
    } finally {
      setIsDiscovering(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // 2. Load Messages and Artifacts whenever active session changes
  const loadSessionDetails = useCallback(async (sessionId) => {
    if (!sessionId || (typeof sessionId === 'string' && sessionId.startsWith('session-'))) return;
    try {
      const [msgList, sessionDetail] = await Promise.all([
        api.getSessionMessages(sessionId).catch(() => []),
        api.getSession(sessionId).catch(() => null),
      ]);

      setMessages(msgList);

      if (sessionDetail?.artifacts && sessionDetail.artifacts.length > 0) {
        setArtifacts(sessionDetail.artifacts);
        setActiveArtifactId(sessionDetail.artifacts[sessionDetail.artifacts.length - 1].id);
      } else {
        setArtifacts([]);
        setActiveArtifactId(null);
      }

      // If last assistant message has citations, populate evidence
      const lastAssistantMsg = [...msgList].reverse().find((m) => m.role === 'assistant');
      if (lastAssistantMsg?.citations && lastAssistantMsg.citations.length > 0) {
        setEvidence(lastAssistantMsg.citations);
        const maxSim = Math.max(...lastAssistantMsg.citations.map((c) => c.similarity || 0), 0);
        setTopSimilarity(maxSim);
        setIsGrounded(maxSim >= 0.28 || lastAssistantMsg.intelligence_mode === 'real_world');
      } else {
        setEvidence([]);
      }
    } catch (err) {
      console.error(`Error loading session ${sessionId}:`, err);
    }
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadSessionDetails(activeSessionId);
    }
  }, [activeSessionId, loadSessionDetails]);

  // 3. New Session Handler - Instant 0ms Synchronous UI State
  const handleNewSession = useCallback(async () => {
    const tempSessionId = `session-${Date.now()}`;
    const newSessionPlaceholder = {
      id: tempSessionId,
      title: `Session ${sessions.length + 1}`,
      created_at: new Date().toISOString(),
      message_count: 0,
    };
    // Instant 0ms synchronous UI update:
    setSessions((prev) => [newSessionPlaceholder, ...prev]);
    setActiveSessionId(tempSessionId);
    setMessages([]);
    setArtifacts([]);
    setActiveArtifactId(null);
    setEvidence([]);
    setLastQuery('');
    setWorkspaceOpen(false);
    setStreamingPhase(null);
    setErrorBanner(null);
    setInputPrompt('');

    try {
      const created = await api.createSession(`Session ${sessions.length + 1}`);
      setSessions((prev) => [created, ...prev.filter((s) => s.id !== tempSessionId)]);
      setActiveSessionId(created.id);
    } catch (err) {
      console.error('Failed to create new session in backend:', err);
    }
  }, [sessions.length]);

  // 3b. Go Home Dashboard Handler
  const handleGoHome = async () => {
    try {
      const existingEmpty = sessions.find((s) => s.message_count === 0 || s.messages?.length === 0);
      if (existingEmpty) {
        setActiveSessionId(existingEmpty.id);
      } else {
        const newSession = await api.createSession(`Growth Session ${sessions.length + 1}`);
        setSessions([newSession, ...sessions]);
        setActiveSessionId(newSession.id);
      }
      setMessages([]);
      setArtifacts([]);
      setActiveArtifactId(null);
      setEvidence([]);
      setLastQuery('');
      setActiveMode('chat');
      setWorkspaceOpen(false);
      setStreamingPhase(null);
      setErrorBanner(null);
    } catch (err) {
      console.error('Failed to navigate to home dashboard:', err);
      setMessages([]);
      setArtifacts([]);
      setActiveArtifactId(null);
      setEvidence([]);
      setLastQuery('');
      setActiveMode('chat');
      setWorkspaceOpen(false);
      setStreamingPhase(null);
      setErrorBanner(null);
    }
  };

  // 4. Delete Session Handler
  const handleDeleteSession = async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  // 4b. Phase 8: Rename Session Handler
  const handleRenameSession = async (sessionId, newTitle) => {
    if (!sessionId || !newTitle.trim()) return;
    try {
      await api.updateSession(sessionId, newTitle.trim());
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle.trim() } : s))
      );
    } catch (err) {
      console.error('Failed to rename session:', err);
      setErrorBanner(`Failed to rename session: ${err.message || err}`);
    }
  };

  // 4c. Phase 8: Edit User Message Handler (Rewinds & branches conversation)
  const handleEditUserMessage = async (messageId, newContent) => {
    if (!activeSessionId || !messageId || !newContent.trim()) return;
    setIsLoading(true);
    setErrorBanner(null);
    setStreamingPhase('Updating message and refreshing context...');
    try {
      await api.editUserMessage(activeSessionId, messageId, newContent.trim());
      await loadSessionDetails(activeSessionId);
      const updatedList = await api.listSessions().catch(() => null);
      if (updatedList) setSessions(Array.isArray(updatedList) ? updatedList : (updatedList?.sessions || []));
    } catch (err) {
      console.error('Failed to edit message:', err);
      setErrorBanner(`Failed to edit message: ${err.message || err}`);
    } finally {
      setIsLoading(false);
      setStreamingPhase(null);
    }
  };

  // 4d. Phase 8: Regenerate Assistant Message Handler
  const handleRegenerate = async (messageId) => {
    if (!activeSessionId || !messageId) return;
    setIsLoading(true);
    setErrorBanner(null);
    setStreamingPhase('Regenerating response with refreshed context...');
    try {
      await api.regenerateMessage(activeSessionId, messageId);
      await loadSessionDetails(activeSessionId);
    } catch (err) {
      console.error('Failed to regenerate response:', err);
      setErrorBanner(`Failed to regenerate response: ${err.message || err}`);
    } finally {
      setIsLoading(false);
      setStreamingPhase(null);
    }
  };

  // 4e. Phase 8: Stop Generation Handler
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setStreamingPhase(null);
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming
          ? { ...m, isStreaming: false, content: (m.content || '') + '\n\n*[Generation stopped by user]*' }
          : m
      )
    );
  };

  // 5. Open Artifact in Context Workspace
  const handleOpenArtifact = (artId) => {
    setActiveArtifactId(artId);
    setWorkspaceTab('artifacts');
    setWorkspaceOpen(true);
  };

  // 6. Inspect Grounding Evidence
  const handleInspectEvidence = (cits) => {
    if (cits && cits.length > 0) {
      setEvidence(cits);
    }
    setWorkspaceTab('evidence');
    setWorkspaceOpen(true);
  };

  // 7. Send Message Handler (Streaming with SSE & Fast TTFT)
  const handleSendMessage = async (content, researchMode = 'auto') => {
    if (!content || isLoading) return;

    setErrorBanner(null);
    setLastQuery(content);
    setResearchProgress(null);

    // Phase 8: Initialize AbortController for Stop Generation
    const controller = new AbortController();
    abortControllerRef.current = controller;

    let targetSessionId = activeSessionId;
    if (!targetSessionId || (typeof targetSessionId === 'string' && targetSessionId.startsWith('session-'))) {
      try {
        const created = await api.createSession(content.slice(0, 32));
        targetSessionId = created.id;
        setSessions((prev) => [created, ...prev.filter((s) => s.id !== activeSessionId)]);
        setActiveSessionId(targetSessionId);
      } catch (e) {
        console.error('Failed to auto-create session:', e);
        return;
      }
    }

    // Auto-rename session if it is the first message and still has default title
    const currentSession = sessions.find((s) => s.id === targetSessionId);
    if (currentSession && (currentSession.title?.startsWith('Growth Session') || currentSession.title === 'Growth Advisory Kickoff')) {
      const meaningfulTitle = content.slice(0, 36).trim() + (content.length > 36 ? '...' : '');
      setSessions((prev) =>
        prev.map((s) => (s.id === targetSessionId ? { ...s, title: meaningfulTitle } : s))
      );
    }

    const tempUserMsg = {
      id: `user-${Date.now()}`,
      session_id: targetSessionId,
      role: 'user',
      content,
      mode: activeMode,
      created_at: new Date().toISOString(),
    };

    const tempAssistantId = `stream-${Date.now()}`;
    const tempAssistantMsg = {
      id: tempAssistantId,
      session_id: targetSessionId,
      role: 'assistant',
      content: '',
      mode: activeMode,
      isStreaming: true,
      citations: [],
      artifacts: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg, tempAssistantMsg]);
    setIsLoading(true);
    setStreamingPhase('Analyzing query & retrieving intelligence...');

    let accumulatedText = '';
    let currentCitations = [];
    let currentArtifacts = [];
    let currentRouting = null;

    try {
      await api.postMessageStream(
        targetSessionId,
        content,
        activeMode,
        researchMode,
        selectedProvider || null,
        {
          onPhase: (phase, message) => {
            setStreamingPhase(message || phase);
          },
          onResearchPlan: (planData) => {
            setResearchProgress({
              depth: planData.depth,
              domain: planData.domain,
              subQueries: planData.sub_queries || [],
              categories: planData.categories || [],
              steps: [],
            });
          },
          onResearchProgress: (progData) => {
            setResearchProgress((prev) =>
              prev
                ? {
                    ...prev,
                    steps: [...(prev.steps || []), progData.query || 'Searching...'],
                  }
                : null
            );
          },
          onResearchSummary: (sumData) => {
            setResearchProgress((prev) =>
              prev
                ? {
                    ...prev,
                    summary: sumData,
                  }
                : null
            );
          },
          onRouting: (data) => {
            const modeName = typeof data === 'object' ? data.intelligence_mode : data;
            currentRouting = modeName;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      intelligence_mode: modeName,
                      capability: data?.capability,
                      research_depth: data?.research_depth,
                      evidence_strength: data?.evidence_strength,
                      category_breakdown: data?.category_breakdown,
                    }
                  : m
              )
            );
          },
          onModel: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      model: data.model_id,
                      provider: data.provider,
                    }
                  : m
              )
            );
          },
          onModelTransition: (transData) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      model_transition: transData,
                    }
                  : m
              )
            );
          },
          onCitations: (cits) => {
            currentCitations = cits;
            setEvidence(cits);
            const maxSim = Math.max(...cits.map((c) => c.similarity || 0), 0);
            setTopSimilarity(maxSim);
            setIsGrounded(maxSim >= 0.28 || currentRouting === 'real_world');
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId ? { ...m, citations: cits } : m
              )
            );
          },
          onToken: (token) => {
            accumulatedText += token;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId ? { ...m, content: accumulatedText } : m
              )
            );
          },
          onArtifacts: (arts) => {
            currentArtifacts = arts;
            if (arts && arts.length > 0) {
              setArtifacts((prev) => [...prev, ...arts]);
              setActiveArtifactId(arts[arts.length - 1].id);
              setWorkspaceTab('artifacts');
              setWorkspaceOpen(true);
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId ? { ...m, artifacts: arts } : m
              )
            );
          },
          onQuality: (qData) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? { ...m, quality_score: qData.score, quality_passed: qData.passed }
                  : m
              )
            );
          },
          onMetrics: (metrics) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      latency_metrics: metrics,
                      model: metrics.model || m.model,
                      provider: metrics.provider || m.provider,
                      intelligence_mode: currentRouting || m.intelligence_mode,
                    }
                  : m
              )
            );
          },
          onDone: (doneData) => {
            setResearchProgress(null);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      isStreaming: false,
                      content: accumulatedText || doneData.content || m.content,
                      citations: currentCitations.length ? currentCitations : (doneData.citations || []),
                      artifacts: currentArtifacts.length ? currentArtifacts : (doneData.artifacts || []),
                      latency_metrics: doneData.metrics || doneData.latency_metrics || m.latency_metrics || null,
                      model: doneData.metrics?.model || m.model,
                      provider: doneData.metrics?.provider || m.provider,
                      model_transition: m.model_transition,
                      capability: doneData.capability || m.capability,
                      intelligence_mode: currentRouting || doneData.intelligence_mode || (doneData.capability === 'lenny_research' ? 'lenny' : 'real_world'),
                      follow_up_suggestions: doneData.follow_up_suggestions || [],
                    }
                  : m
              )
            );
            setStreamingPhase(null);
            loadSessionDetails(targetSessionId);
          },
          onError: (err) => {
            console.error('SSE Stream error received:', err);
            setErrorBanner(`Agent streaming interrupted: ${err.message || err}`);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      isStreaming: false,
                      content: accumulatedText || '⚠️ Error generating response. Please check server logs.',
                    }
                  : m
              )
            );
            setStreamingPhase(null);
          },
        },
        controller.signal
      );
      const updatedList = await api.listSessions().catch(() => null);
      if (updatedList) setSessions(Array.isArray(updatedList) ? updatedList : (updatedList?.sessions || []));
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted by user');
      } else {
        console.error('Failed in streaming turn:', err);
        setErrorBanner(err.message || 'An error occurred during response streaming.');
      }
    } finally {
      abortControllerRef.current = null;
      setIsLoading(false);
      setStreamingPhase(null);
    }
  };

  // Instant Zero-Lag Page Switching Callbacks
  const handleLaunchChat = useCallback((promptText = null, mode = null) => {
    setViewMode('chat');
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (promptText) {
      if (mode) setActiveMode(mode);
      // Pre-fill the input prompt so the user can inspect, edit, or submit when ready!
      // NEVER auto-execute!
      setInputPrompt(promptText);
    } else {
      // User clicked "Launch Growth Console" or "Open Growth Console":
      // Reset input prompt and open a fresh new chat session!
      setInputPrompt('');
      handleNewSession();
    }
  }, [handleNewSession]);

  const handleStarterPrompt = useCallback((promptText, mode) => {
    if (mode) setActiveMode(mode);
    setInputPrompt(promptText);
  }, []);

  const handleGoDashboard = useCallback(() => {
    setViewMode('landing');
  }, []);

  return (
    <div className="min-h-screen text-[#F8FAFC] flex flex-col antialiased selection:bg-zinc-800 selection:text-white font-sans relative bg-[#06080d]">
      {/* Complete Site-Wide Background UI: ThreeUI 3D StructureFlowCollection */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <Scene />
      </div>

      {/* Main Foreground Interface: Instantaneous 0ms Page Transmission */}
      <div className="relative z-10 flex-1 flex flex-col">
        {/* Full Overview Dashboard View */}
        <div
          id="overview-dashboard-view"
          className={viewMode === 'landing' ? 'block' : 'hidden'}
          style={{ display: viewMode === 'landing' ? 'block' : 'none' }}
        >
          <LandingPage
            onGoChat={() => handleLaunchChat()}
            onSelectPrompt={(promptText, mode) => {
              handleLaunchChat(promptText, mode);
            }}
          />
        </div>

        {/* Conversational Strategy Console View */}
        <div
          id="chat-console-view"
          className={viewMode === 'chat' ? 'flex-1 flex flex-col h-screen overflow-hidden' : 'hidden'}
          style={{ display: viewMode === 'chat' ? 'flex' : 'none' }}
        >
          {/* Top Application Header */}
          <Header
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            onNewSession={handleNewSession}
            onGoHome={handleGoHome}
            onGoLanding={handleGoDashboard}
            llmHealth={llmHealth}
            dbHealth={dbHealth}
            activeSessionTitle={activeSessionTitle}
            workspaceOpen={workspaceOpen}
            onToggleWorkspace={() => setWorkspaceOpen(!workspaceOpen)}
            artifactCount={artifacts.length}
            evidenceCount={evidence.length}
            selectedProvider={selectedProvider}
            onChangeProvider={setSelectedProvider}
            availableModels={availableModels}
            onDiscoverModels={handleDiscoverModels}
            isDiscovering={isDiscovering}
          />

          {/* Error Notification Banner */}
          {errorBanner && (
            <div className="bg-red-500/10 border-b border-red-500/25 text-red-400 text-xs px-4 py-2 flex items-center justify-between">
              <span>{errorBanner}</span>
              <button
                onClick={() => setErrorBanner(null)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Main Adaptive Workspace Body */}
          <div className="flex-1 flex overflow-hidden">
            {/* Sessions Sidebar */}
            <Sidebar
              isOpen={sidebarOpen}
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectSession={setActiveSessionId}
              onNewSession={handleNewSession}
              onDeleteSession={handleDeleteSession}
              onRenameSession={handleRenameSession}
            />

            {/* Central Chat & Contextual Workspace Area */}
            <main className="flex-1 flex overflow-hidden relative">
              {/* Conversational Stream (Spacious, Centered Document Layout) */}
              <section className="flex-1 flex flex-col min-w-0 h-[calc(100vh-3.5rem)] overflow-hidden">
                {/* Conversation Stream Window */}
                <ChatWindow
                  messages={messages}
                  isLoading={isLoading}
                  streamingPhase={streamingPhase}
                  researchProgress={researchProgress}
                  onSelectStarterPrompt={handleStarterPrompt}
                  onOpenArtifact={handleOpenArtifact}
                  onInspectEvidence={handleInspectEvidence}
                  onEditUserMessage={handleEditUserMessage}
                  onRegenerate={handleRegenerate}
                />

                {/* Unified Composer Dock */}
                <ChatInput
                  onSendMessage={handleSendMessage}
                  activeMode={activeMode}
                  onSelectMode={setActiveMode}
                  disabled={isLoading}
                  selectedProvider={selectedProvider}
                  onChangeProvider={setSelectedProvider}
                  onStopGeneration={handleStopGeneration}
                  availableModels={availableModels}
                  inputPrompt={inputPrompt}
                  onInputChange={setInputPrompt}
                />
              </section>

              {/* Contextual Workspace Pane (Desktop Slide-Over or Mobile Sheet) */}
              {workspaceOpen && (
                <section
                  className="fixed inset-y-14 right-0 z-40 w-full sm:w-[480px] lg:static lg:w-[460px] xl:w-[520px] h-[calc(100vh-3.5rem)] flex flex-col shadow-2xl lg:shadow-none animate-in slide-in-from-right duration-200"
                >
                  <GrowthCanvas
                    artifacts={artifacts}
                    activeArtifactId={activeArtifactId}
                    onSelectArtifact={setActiveArtifactId}
                    evidence={evidence}
                    topSimilarity={topSimilarity}
                    isGrounded={isGrounded}
                    query={lastQuery}
                    onClose={() => setWorkspaceOpen(false)}
                    initialTab={workspaceTab}
                  />
                </section>
              )}
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
