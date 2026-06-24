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
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const currentSessionIdRef = useRef(null);
  const needsMessageLoadRef = useRef(false);

  useEffect(() => {
    currentSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  const chatHistory = useMemo(
    () => messages.filter((msg) => (msg.role === "user" || msg.role === "assistant") && msg.content.trim()),
    [messages]
  );

  // Nao cria sessao inicial — so e criada no primeiro envio de mensagem
  useEffect(() => {
    setInitialLoading(false);
  }, []);

  // Verifica se ja existe token salvo
  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem("token");
      if (!token) {
        setAuthLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
        } else {
          localStorage.removeItem("token");
        }
      } catch {
        localStorage.removeItem("token");
      } finally {
        setAuthLoading(false);
      }
    }
    checkAuth();
  }, []);

  const loadSessionMessages = useCallback(async (sessionId) => {
    if (!sessionId) return;
    try {
      const msgs = await fetchSessionMessages(sessionId);
      if (msgs.length > 0) {
        setMessages(
          msgs.map((m) => ({
            id: createMessageId(),
            role: m.role,
            content: m.content,
          }))
        );
      } else {
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        }]);
      }
    } catch {
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
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

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const handleSelectSession = useCallback((sessionId) => {
    if (sessionId === null) {
      // Cria nova sessao via API (para poder carregar historico depois)
      const token = localStorage.getItem("token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      fetch(`${API_BASE}/api/sessions`, { method: "POST", headers })
        .then((r) => r.json())
        .then((data) => {
          setCurrentSessionId(data.id);
        })
        .catch(() => {});
      return;
    }
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    needsMessageLoadRef.current = true;
    setCurrentSessionId(sessionId);
  }, []);

  // Carrega mensagens quando usuario troca de sessao explicitamente
  useEffect(() => {
    if (!currentSessionId || !needsMessageLoadRef.current) return;
    needsMessageLoadRef.current = false;
    loadSessionMessages(currentSessionId);
  }, [currentSessionId, loadSessionMessages]);

  const handleNewSession = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    setMessages([{
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    }]);
    needsMessageLoadRef.current = false;
    setCurrentSessionId(null);
  }, []);

  const handleSessionIdFromStream = useCallback((sessionId) => {
    if (!currentSessionIdRef.current) {
      setCurrentSessionId(sessionId);
    }
  }, []);

  // Forca refresh da sidebar apos titulo ser definido
  const handleSessionTitle = useCallback(() => {
    setSidebarRefresh((n) => n + 1);
  }, []);

  const handleLoginSuccess = useCallback((data) => {
    setUser({ email: data.email, display_name: data.display_name || null });
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setMessages([{
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    }]);
    setCurrentSessionId(null);
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
        session_id: currentSessionIdRef.current,
        signal: abortController.signal,
        onSessionId: handleSessionIdFromStream,
        onSessionTitle: handleSessionTitle,
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

      setSidebarRefresh((n) => n + 1);

      if (currentSessionIdRef.current) {
        loadSessionMessages(currentSessionIdRef.current);
      }

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

  if (authLoading || initialLoading) {
    return (
      <main className="app-shell">
        <div className="app-loading">Carregando...</div>
      </main>
    );
  }

  if (!user) {
    return <AuthForm onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-layout">
      <Sidebar
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        refreshTrigger={sidebarRefresh}
      />

      <main className="app-shell">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
          <button className="logout-btn" onClick={handleLogout}>Sair</button>
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

