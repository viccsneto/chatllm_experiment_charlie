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
  const [authenticated, setAuthenticated] = useState(null);
  const [userEmail, setUserEmail] = useState("");
  const [sessions, setSessions] = useState([]);
  const [activeSessionKey, setActiveSessionKey] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem("token");
      if (!token) { setAuthenticated(false); return; }
      try {
        const data = await verifyToken();
        if (data) { setUserEmail(data.email); setAuthenticated(true); }
        else { setAuthenticated(false); }
      } catch { setAuthenticated(false); }
    })();
  }, []);

  useEffect(() => {
    if (authenticated !== true) return;
    (async () => {
      try {
        const list = await listSessions();
        setSessions(list);
        if (list.length > 0) setActiveSessionKey(list[0].session_key);
      } catch (e) { console.error("Erro ao carregar sessoes:", e); }
    })();
  }, [authenticated]);

  useEffect(() => {
    if (!activeSessionKey) { setMessages([WELCOME_MESSAGE]); return; }
    (async () => {
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(activeSessionKey)}/messages`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.length === 0) setMessages([WELCOME_MESSAGE]);
        else setMessages(data.map((m) => ({ id: `msg-${m.id}`, role: m.role, content: m.content })));
      } catch (e) { console.error("Erro ao carregar mensagens:", e); }
    })();
  }, [activeSessionKey]);

  useEffect(() => { messagesRef.current?.scrollTo(0, messagesRef.current.scrollHeight); }, [messages]);
  useEffect(() => { return () => abortControllerRef.current?.abort(); }, []);

  const handleAuthSuccess = useCallback(() => {
    setUserEmail(localStorage.getItem("email") || "");
    setAuthenticated(true);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("email");
    setAuthenticated(false);
    setSessions([]);
    setActiveSessionKey(null);
    setMessages([WELCOME_MESSAGE]);
    setError("");
    abortControllerRef.current?.abort();
    setBusy(false);
  }, []);

  const refreshSessions = useCallback(async () => {
    try { setSessions(await listSessions()); }
    catch (e) { console.error("Erro ao atualizar sessoes:", e); }
  }, []);

  const handleNewSession = useCallback(async () => {
    if (busy) return;
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionKey(session.session_key);
    } catch (e) { setError("Erro ao criar nova sessao."); }
  }, [busy]);

  const handleSelectSession = useCallback((sessionKey) => {
    if (busy) { abortControllerRef.current?.abort(); setBusy(false); }
    setActiveSessionKey(sessionKey);
  }, [busy]);

  const handleDeleteSession = useCallback(async (sessionKey) => {
    if (busy) return;
    try {
      await deleteSession(sessionKey);
      setSessions((prev) => prev.filter((s) => s.session_key !== sessionKey));
      if (activeSessionKey === sessionKey) {
        const remaining = sessions.filter((s) => s.session_key !== sessionKey);
        setActiveSessionKey(remaining.length > 0 ? remaining[0].session_key : null);
      }
    } catch (e) { setError("Erro ao deletar sessao."); }
  }, [busy, activeSessionKey, sessions]);

  const onStop = () => { abortControllerRef.current?.abort(); setBusy(false); };

  const chatHistory = useMemo(
    () => messages.filter((m) => m.role === "user" || m.role === "assistant"), [messages]
  );

  const onSubmit = async (event) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;
    setError("");
    let currentSessionKey = activeSessionKey;
    if (!currentSessionKey) {
      try {
        const session = await createSession();
        setSessions((prev) => [session, ...prev]);
        currentSessionKey = session.session_key;
        setActiveSessionKey(currentSessionKey);
      } catch (e) { setError("Erro ao criar sessao."); return; }
    }
    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();
    setMessages((prev) => [...prev, userMessage, { id: assistantMessageId, role: "assistant", content: "" }]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    try {
      await sendMessageStream({
        message: cleaned, history: chatHistory, session_key: currentSessionKey,
        signal: abortController.signal,
        onDelta: (delta) => setMessages((prev) => prev.map((m) =>
          m.id === assistantMessageId ? { ...m, content: `${m.content}${delta}` } : m
        )),
        onDone: async () => { await refreshSessions(); },
      });
      setMessages((prev) => prev.map((m) =>
        m.id === assistantMessageId && !m.content.trim()
          ? { ...m, content: "Nao foi possivel obter resposta do modelo agora." } : m
      ));
    } catch (err) {
      const aborted = err?.name === "AbortError";
      setError(aborted ? "" : err.message || "Falha inesperada.");
      setMessages((prev) => prev.map((m) =>
        m.id === assistantMessageId
          ? { ...m, content: m.content.trim() ? m.content : (aborted ? "Resposta interrompida." : "Nao foi possivel obter resposta do modelo agora.") } : m
      ));
    } finally { setBusy(false); }
  };

  if (authenticated === null) return (
    <main className="app-shell"><div style={{ margin: "auto", color: "var(--muted)" }}>Carregando...</div></main>
  );
  if (!authenticated) return <LoginScreen onAuthSuccess={handleAuthSuccess} />;
  return (
    <main className="app-shell">
      <Sidebar
        sessions={sessions} activeSessionKey={activeSessionKey}
        onSelect={handleSelectSession} onNew={handleNewSession} onDelete={handleDeleteSession}
      />
      <div className="app-main">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
          <div className="header-spacer" />
          <span className="header-email">{userEmail}</span>
          <button className="logout-btn" onClick={handleLogout} type="button">Sair</button>
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
        <Composer text={text} busy={busy} error={error} onChangeText={setText} onSubmit={onSubmit} onStop={onStop} />
        <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

