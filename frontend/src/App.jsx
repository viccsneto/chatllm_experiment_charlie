const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const loadSessions = async () => {
    try {
      setLoadingSessions(true);
      const list = await fetchSessions();
      setSessions(list);
      if (list.length > 0 && !activeSessionId) {
        const latest = list[0];
        setActiveSessionId(latest.id);
        loadMessages(latest.id);
      } else if (list.length === 0) {
        // No sessions exist yet — show welcome, no session created
        setMessages([
          {
            id: createMessageId(),
            role: "assistant",
            content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
          },
        ]);
      }
    } catch (err) {
      console.error("Erro ao carregar sessoes:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadMessages = async (sessionId) => {
    try {
      const msgs = await fetchSessionMessages(sessionId);
      setMessages(
        msgs.map((m) => ({
          id: createMessageId(),
          role: m.role,
          content: m.content,
        }))
      );
    } catch (err) {
      console.error("Erro ao carregar mensagens:", err);
      setMessages([]);
    }
  };

  const handleSwitchSession = useCallback((sessionId) => {
    if (busy) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    setError("");
    setActiveSessionId(sessionId);
    loadMessages(sessionId);
    setSidebarOpen(false);
  }, [busy]);

  const handleNewSession = useCallback(async () => {
    if (busy) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    setError("");
    // Just clear the chat — session will be created on first message response
    setActiveSessionId(null);
    setMessages([
      {
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      },
    ]);
    setSidebarOpen(false);
  }, [busy]);

  const handleDeleteSession = useCallback(async (sessionId, event) => {
    event.stopPropagation();
    if (sessions.length <= 1) {
      setError("Nao e possivel excluir a unica sessao");
      return;
    }
    try {
      await deleteSession(sessionId);
      const updated = sessions.filter((s) => s.id !== sessionId);
      setSessions(updated);
      if (activeSessionId === sessionId) {
        const next = updated[0];
        setActiveSessionId(next.id);
        loadMessages(next.id);
      }
    } catch (err) {
      setError("Erro ao excluir sessao");
    }
  }, [sessions, activeSessionId]);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");
    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionId: activeSessionId,
        signal: abortController.signal,
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
        onDone: (newSessionId) => {
          if (newSessionId) {
            setActiveSessionId(newSessionId);
          }
          fetchSessions().then(setSessions).catch(() => {});
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );
    } catch (err) {
      const aborted = err?.name === "AbortError";
      if (!aborted) {
        setError(err.message || "Falha inesperada ao gerar resposta.");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content.trim() ? msg.content : "Nao foi possivel obter resposta do modelo agora." }
              : msg
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId && !msg.content.trim()
              ? { ...msg, content: "Resposta interrompida." }
              : msg
          )
        );
      }
    } finally {
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  if (loadingSessions) {
    return (
      <main className="app-shell">
        <div className="loading-screen">Carregando...</div>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar-header">
          <button className="sidebar-new-btn" onClick={handleNewSession} disabled={busy} title="Nova sessao">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="8" y1="2" x2="8" y2="14" />
              <line x1="2" y1="8" x2="14" y2="8" />
            </svg>
            Nova sessao
          </button>
          <button className="sidebar-close-btn" onClick={() => setSidebarOpen(false)} title="Fechar sidebar">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          </button>
        </div>
        <nav className="sidebar-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`sidebar-item ${s.id === activeSessionId ? "sidebar-item--active" : ""}`}
              onClick={() => handleSwitchSession(s.id)}
            >
              <span className="sidebar-item-title" title={s.title}>
                {s.title || "Nova sessao"}
              </span>
              <button
                className="sidebar-item-del"
                onClick={(e) => handleDeleteSession(s.id, e)}
                title="Excluir sessao"
              >
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <polyline points="3,6 5,6 5,14 11,14 11,6 13,6" />
                  <line x1="6" y1="2" x2="10" y2="2" />
                </svg>
              </button>
            </div>
          ))}
        </nav>
      </aside>
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      <div className="main-content">
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((prev) => !prev)}
            title="Alternar sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="4" x2="15" y2="4" />
              <line x1="3" y1="9" x2="15" y2="9" />
              <line x1="3" y1="14" x2="15" y2="14" />
            </svg>
          </button>
          <div className="brand">ChatLLM Lab</div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messages.map((msg) => (
              <article key={msg.id} className={`bubble ${msg.role}`}>
                <MessageContent content={msg.content} />
              </article>
            ))}
          </div>
        </section>

        <Composer
          text={text}
          busy={busy}
          error={error}
          onChangeText={setText}
          onSubmit={onSubmit}
          onStop={onStop}
          onFocusInput={() => setSidebarOpen(false)}
        />

        <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

