const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [messages, setMessages] = useState([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const editInputRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Carregar sessoes ao montar
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

  useEffect(() => {
    if (editingSessionId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingSessionId]);

  const loadSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
    } catch {
      // Ignorar erros de carregamento
    }
  };

  const switchSession = useCallback(async (sessionId) => {
    if (busy) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setBusy(false);
    }

    try {
      const data = await getSessionMessages(sessionId);
      setCurrentSessionId(sessionId);
      if (data.messages && data.messages.length > 0) {
        setMessages(
          data.messages.map((m) => ({
            id: createMessageId(),
            role: m.role,
            content: m.content,
          }))
        );
      } else {
        setMessages([]);
      }
    } catch {
      setError("Erro ao carregar mensagens da sessao.");
    }
  }, [busy]);

  const handleNewSession = async () => {
    if (busy) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setBusy(false);
    }
    try {
      const data = await createSession();
      setCurrentSessionId(data.id);
      setMessages([
        {
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        },
      ]);
      await loadSessions();
    } catch {
      setError("Erro ao criar nova sessao.");
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([
          {
            id: createMessageId(),
            role: "assistant",
            content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
          },
        ]);
      }
      await loadSessions();
    } catch {
      setError("Erro ao deletar sessao.");
    }
  };

  const startEditTitle = (e, sessionId, currentTitle) => {
    e.stopPropagation();
    setEditingSessionId(sessionId);
    setEditTitleValue(currentTitle || "");
  };

  const saveTitle = async (sessionId) => {
    const title = editTitleValue.trim();
    if (!title) {
      setEditingSessionId(null);
      return;
    }
    try {
      await updateSessionTitle(sessionId, title);
      setEditingSessionId(null);
      await loadSessions();
    } catch {
      setError("Erro ao atualizar titulo.");
      setEditingSessionId(null);
    }
  };

  const handleTitleKeyDown = (e, sessionId) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveTitle(sessionId);
    } else if (e.key === "Escape") {
      setEditingSessionId(null);
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
      const returnedSessionId = await sendMessageStream({
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
      });

      if (returnedSessionId && returnedSessionId !== currentSessionId) {
        setCurrentSessionId(returnedSessionId);
      }

      await loadSessions();

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

  const { user, loading, authScreen, setAuthScreen, logout } = useAuth();

  // Se ainda carregando autenticação, não renderiza nada
  if (loading) return null;

  // Se não autenticado, mostra tela de login/register
  if (!user) {
    return (
      <div className="app-layout">
        <main className="app-shell">
          <AuthScreen />
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-header">
          <button className="sidebar-new-btn" onClick={handleNewSession}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="8" y1="3" x2="8" y2="13" />
              <line x1="3" y1="8" x2="13" y2="8" />
            </svg>
            Nova conversa
          </button>
        </div>
        <div className="sidebar-list">
          {sessions.length === 0 && (
            <div className="sidebar-empty">Nenhuma conversa ainda.</div>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`sidebar-item ${currentSessionId === s.id ? "active" : ""}`}
              onClick={() => switchSession(s.id)}
            >
              <div className="sidebar-item-content">
                {editingSessionId === s.id ? (
                  <input
                    ref={editInputRef}
                    className="sidebar-edit-input"
                    value={editTitleValue}
                    onChange={(e) => setEditTitleValue(e.target.value)}
                    onBlur={() => saveTitle(s.id)}
                    onKeyDown={(e) => handleTitleKeyDown(e, s.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span
                    className="sidebar-item-title"
                    onDoubleClick={(e) => startEditTitle(e, s.id, s.title)}
                  >
                    {s.title || "Nova conversa"}
                  </span>
                )}
                <span className="sidebar-item-count">{s.message_count}</span>
              </div>
              <button
                className="sidebar-delete-btn"
                onClick={(e) => handleDeleteSession(e, s.id)}
                title="Deletar conversa"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <line x1="3" y1="3" x2="11" y2="11" />
                  <line x1="11" y1="3" x2="3" y2="11" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Overlay para fechar sidebar em mobile */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Conteudo principal */}
      <main className="app-shell">
        <header className="app-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <line x1="3" y1="5" x2="17" y2="5" />
              <line x1="3" y1="10" x2="17" y2="10" />
              <line x1="3" y1="15" x2="17" y2="15" />
            </svg>
          </button>
          <div className="brand">ChatLLM Lab</div>
          <div className="header-right">
            <span className="header-email">{user.email}</span>
            <button className="header-logout-btn" onClick={logout} title="Sair">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" />
                <polyline points="10,12 14,8 10,4" />
                <line x1="14" y1="8" x2="6" y2="8" />
              </svg>
            </button>
          </div>
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

function Root() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Root />);

