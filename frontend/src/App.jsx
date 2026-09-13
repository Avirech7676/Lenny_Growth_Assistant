import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ModeSelector from './components/ModeSelector';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import GrowthCanvas from './components/GrowthCanvas';
import { api } from './services/api';

export default function App() {
  // Navigation & Layout state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeMode, setActiveMode] = useState('research');
  const [selectedProvider, setSelectedProvider] = useState('');

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

  // Telemetry & UI status
  const [llmHealth, setLlmHealth] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState(null);

  // 1. Initial Health Diagnostics & Sessions Fetch
  const loadInitialData = useCallback(async () => {
    try {
      const [llmRes, dbRes, sessionList] = await Promise.all([
        api.getLLMHealth().catch(() => null),
        api.getDBHealth().catch(() => null),
        api.listSessions().catch(() => []),
      ]);

      if (llmRes) setLlmHealth(llmRes);
      if (dbRes) setDbHealth(dbRes);

      if (Array.isArray(sessionList) && sessionList.length > 0) {
        setSessions(sessionList);
        setActiveSessionId(sessionList[0].id);
      } else {
        // Create initial session
        const newSession = await api.createSession('Growth Advisory Kickoff');
        setSessions([newSession]);
        setActiveSessionId(newSession.id);
      }
    } catch (err) {
      console.error('Failed to initialize workspace data:', err);
      setErrorBanner('Failed to load initial session data.');
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // 2. Load Messages and Artifacts whenever active session changes
  const loadSessionDetails = useCallback(async (sessionId) => {
    if (!sessionId) return;
    try {
      const [msgList, sessionDetail] = await Promise.all([
        api.getSessionMessages(sessionId).catch(() => []),
        api.getSession(sessionId).catch(() => null),
      ]);

      setMessages(msgList);

      if (sessionDetail?.artifacts) {
        setArtifacts(sessionDetail.artifacts);
        if (sessionDetail.artifacts.length > 0) {
          setActiveArtifactId(sessionDetail.artifacts[sessionDetail.artifacts.length - 1].id);
        }
      }

      // If last message has citations, populate evidence
      const lastAssistantMsg = [...msgList].reverse().find((m) => m.role === 'assistant');
      if (lastAssistantMsg?.citations && lastAssistantMsg.citations.length > 0) {
        setEvidence(lastAssistantMsg.citations);
        const maxSim = Math.max(...lastAssistantMsg.citations.map((c) => c.similarity || 0), 0);
        setTopSimilarity(maxSim);
        setIsGrounded(maxSim >= 0.28);
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

  // 3. New Session Handler
  const handleNewSession = async () => {
    try {
      const newSession = await api.createSession(`Growth Session ${sessions.length + 1}`);
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setArtifacts([]);
      setActiveArtifactId(null);
      setEvidence([]);
    } catch (err) {
      console.error('Failed to create new session:', err);
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

  // 5. Send Message Handler
  const handleSendMessage = async (content) => {
    if (!content || !activeSessionId || isLoading) return;

    setErrorBanner(null);
    setLastQuery(content);

    // Optimistically add user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      session_id: activeSessionId,
      role: 'user',
      content,
      mode: activeMode,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const response = await api.postMessage(
        activeSessionId,
        content,
        activeMode,
        selectedProvider || null
      );

      // Replace or append response
      setMessages((prev) => [...prev, response]);

      // Update artifacts if assistant generated any
      if (response.artifacts && response.artifacts.length > 0) {
        setArtifacts((prev) => [...prev, ...response.artifacts]);
        setActiveArtifactId(response.artifacts[response.artifacts.length - 1].id);
      }

      // Update Grounding Evidence
      if (response.citations && response.citations.length > 0) {
        setEvidence(response.citations);
        const maxSim = Math.max(...response.citations.map((c) => c.similarity || 0), 0);
        setTopSimilarity(maxSim);
        setIsGrounded(maxSim >= 0.28);
      } else {
        setEvidence([]);
        setIsGrounded(false);
      }

      // Refresh session title / list order if updated
      const updatedList = await api.listSessions().catch(() => null);
      if (updatedList) setSessions(updatedList);
    } catch (err) {
      console.error('Failed to send message:', err);
      setErrorBanner(err.message || 'An error occurred communicating with the agent.');
    } finally {
      setIsLoading(false);
    }
  };

  // Quick Starter prompt trigger
  const handleStarterPrompt = (promptText, mode) => {
    setActiveMode(mode);
    handleSendMessage(promptText);
  };

  return (
    <div className="min-h-screen bg-[#0A0E17] text-[#F8FAFC] flex flex-col antialiased selection:bg-emerald-500 selection:text-slate-950">
      {/* Top Header */}
      <Header
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        onNewSession={handleNewSession}
        llmHealth={llmHealth}
        dbHealth={dbHealth}
      />

      {/* Error Notification Banner */}
      {errorBanner && (
        <div className="bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs px-4 py-2 flex items-center justify-between">
          <span>{errorBanner}</span>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-slate-400 hover:text-white text-xs font-mono"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sessions Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
        />

        {/* Central Split View: Chat Window + Growth Canvas */}
        <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          {/* Left Column: Chat Conversation Stream */}
          <section className="flex-1 flex flex-col min-w-0 h-[calc(100vh-4rem)] border-r border-slate-800/80">
            {/* Mode Switcher Bar */}
            <div className="p-3 border-b border-slate-800/80 bg-slate-950/40">
              <ModeSelector
                activeMode={activeMode}
                onSelectMode={setActiveMode}
                disabled={isLoading}
              />
            </div>

            {/* Chat Stream */}
            <ChatWindow
              messages={messages}
              isLoading={isLoading}
              onSelectStarterPrompt={handleStarterPrompt}
              onOpenArtifact={(artId) => setActiveArtifactId(artId)}
              onInspectEvidence={(cits) => setEvidence(cits)}
            />

            {/* Prompt Input Bar */}
            <ChatInput
              onSendMessage={handleSendMessage}
              activeMode={activeMode}
              disabled={isLoading}
              selectedProvider={selectedProvider}
              onChangeProvider={setSelectedProvider}
            />
          </section>

          {/* Right Column: Growth Canvas (Sandboxed Iframe & Grounding Evidence) */}
          <section className="hidden lg:flex lg:w-1/2 xl:w-5/12 h-[calc(100vh-4rem)] flex-col">
            <GrowthCanvas
              artifacts={artifacts}
              activeArtifactId={activeArtifactId}
              onSelectArtifact={setActiveArtifactId}
              evidence={evidence}
              topSimilarity={topSimilarity}
              isGrounded={isGrounded}
              query={lastQuery}
            />
          </section>
        </main>
      </div>
    </div>
  );
}
