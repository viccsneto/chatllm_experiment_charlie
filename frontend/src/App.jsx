const { useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const initialLoadDone = useRef(false);

  // Check auth status on mount
  useEffect(() => {
    (async () => {
      const u = await fetchMe();
      if (u) {
        setUser(u);
        await loadSessions();
      }
      setAuthLoading(false);
    })();
  }, []);

  // Load messages when switching sessions
  useEffect(() => {
    if (currentSessionId && initialLoadDone.current) {
      loadMessages(currentSessionId);
    }
  }, [currentSessionId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  async function loadSessions() {
    try {
      const list = await fetchSessions();
      setSessions(list);
    } catch {
      // silent
    }
  }

  async function loadMessages(sessionId) {
    try {
      const msgs = await fetchSessionMessages(sessionId);
      setMessages(
        msgs.map((m) => ({
          id: createMessageId(),
          role: m.role,
          content: m.content,
        }))
      );
    } catch {
      setError("Falha ao carregar mensagens da sessao.");
    }
  }

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  const handleAuth = (u) => {
    setUser(u);
    loadSessions();
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleNewChat = async () => {
    abortControllerRef.current?.abort();
    setBusy(false);
    setError("");
    try {
      const newSession = await createSession();
      setCurrentSessionId(newSession.id);
      setMessages([]);
      setText("");
      await loadSessions();
    } catch (err) {
      setError("Falha ao criar nova sessao.");
    }
  };

  const handleSelectSession = (sessionId) => {
    if (busy) return;
    abortControllerRef.current?.abort();
    setBusy(false);
    setError("");
    setCurrentSessionId(sessionId);
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (busy) return;
    try {
      await deleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      await loadSessions();
    } catch {
      setError("Falha ao deletar sessao.");
    }
  };

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    if (!currentSessionId) {
      try {
        const newSession = await createSession();
        setCurrentSessionId(newSession.id);
        await loadSessions();
      } catch {
        setError("Falha ao criar sessao.");
        return;
      }
    }

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
        session_id: currentSessionId,
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
        onDone: (sid) => {
          if (sid && sid !== currentSessionId) {
            setCurrentSessionId(sid);
          }
          loadSessions();
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
      initialLoadDone.current = true;
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <main className="app-shell">
        <div className="auth-container">
          <div className="auth-box">
            <p style={{ textAlign: "center", color: "var(--muted)" }}>Carregando...</p>
          </div>
        </div>
      </main>
    );
  }

  // Show auth screen if not logged in
  if (!user) {
    return <Auth onAuth={handleAuth} />;
  }

  return (
    <main className={`app-shell ${sidebarOpen ? "sidebar-visible" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="8" y1="2" x2="8" y2="14" />
              <line x1="2" y1="8" x2="14" y2="8" />
            </svg>
            Nova conversa
          </button>
        </div>
        <nav className="session-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === currentSessionId ? "active" : ""}`}
              onClick={() => handleSelectSession(s.id)}
            >
              <span className="session-title">{s.title || "Nova conversa"}</span>
              <button
                className="session-delete"
                onClick={(e) => handleDeleteSession(e, s.id)}
                title="Deletar sessao"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <line x1="2" y1="2" x2="10" y2="10" />
                  <line x1="10" y1="2" x2="2" y2="10" />
                </svg>
              </button>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="sidebar-user">{user.email}</span>
          <button className="logout-btn" onClick={handleLogout}>Sair</button>
        </div>
      </aside>

      <div className="main-area">
        <header className="app-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <line x1="4" y1="5" x2="16" y2="5" />
              <line x1="4" y1="10" x2="16" y2="10" />
              <line x1="4" y1="15" x2="16" y2="15" />
            </svg>
          </button>
          <div className="brand">ChatLLM Lab</div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messages.length === 0 && !busy && (
              <div className="empty-state">
                <p>Inicie uma nova conversa ou selecione uma sessao existente.</p>
              </div>
            )}
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
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

