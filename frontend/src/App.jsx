const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

const WELCOME_MESSAGE = {
  id: createMessageId(),
  role: "assistant",
  content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
};

function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Load sessions on mount
  useEffect(() => {
    fetchSessions()
      .then((data) => {
        setSessions(data);
        setLoadingSessions(false);
      })
      .catch(() => setLoadingSessions(false));
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

  const onStop = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  }, []);

  const loadSessionMessages = useCallback(async (sessionId) => {
    try {
      const data = await fetchSessionMessages(sessionId);
      setCurrentSessionId(sessionId);
      setMessages([
        ...data.map((msg) => ({
          id: createMessageId(),
          role: msg.role,
          content: msg.content,
        })),
      ]);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await fetchSessions();
      setSessions(data);
    } catch {
      // silent
    }
  }, []);

  const handleNewSession = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
    setCurrentSessionId(null);
    setError("");
    setText("");
  }, []);

  const handleSelectSession = useCallback(
    async (sessionId) => {
      if (busy) {
        abortControllerRef.current?.abort();
        setBusy(false);
      }
      await loadSessionMessages(sessionId);
    },
    [busy, loadSessionMessages]
  );

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
        sessionId: currentSessionId,
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
          if (newSessionId && !currentSessionId) {
            setCurrentSessionId(newSessionId);
          }
          refreshSessions();
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
      refreshSessions();
    }
  };

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <button className="new-session-btn" onClick={handleNewSession}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <line x1="7" y1="1" x2="7" y2="13" />
              <line x1="1" y1="7" x2="13" y2="7" />
            </svg>
            Nova conversa
          </button>
        </div>
        <div className="sidebar-sessions">
          {loadingSessions ? (
            <div className="sidebar-loading">Carregando...</div>
          ) : sessions.length === 0 ? (
            <div className="sidebar-empty">Nenhuma sessao</div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                className={`session-item ${s.id === currentSessionId ? "active" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                title={s.title}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true" style={{ flexShrink: 0 }}>
                  <path d="M2 2h10v7a1 1 0 0 1-1 1H5l-3 3V2z" />
                </svg>
                <span className="session-title">{s.title}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <main className="app-shell">
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label={sidebarOpen ? "Fechar sidebar" : "Abrir sidebar"}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <rect x="1" y="3" width="14" height="1.5" rx="0.75" />
              <rect x="1" y="7.25" width="14" height="1.5" rx="0.75" />
              <rect x="1" y="11.5" width="14" height="1.5" rx="0.75" />
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
        />

        <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

