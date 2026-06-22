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
  const [sessions, setSessions] = useState([]);
  const [activeSessionKey, setActiveSessionKey] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // ── Load sessions on mount ──────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const list = await listSessions();
        setSessions(list);
        if (list.length > 0) {
          setActiveSessionKey(list[0].session_key);
        }
      } catch (e) {
        console.error("Erro ao carregar sessoes:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // ── Load messages when active session changes ───────────────
  useEffect(() => {
    if (!activeSessionKey) {
      setMessages([WELCOME_MESSAGE]);
      return;
    }
    (async () => {
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(activeSessionKey)}/messages`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.length === 0) {
          setMessages([WELCOME_MESSAGE]);
        } else {
          setMessages(
            data.map((m) => ({
              id: `msg-${m.id}`,
              role: m.role,
              content: m.content,
            }))
          );
        }
      } catch (e) {
        console.error("Erro ao carregar mensagens:", e);
      }
    })();
  }, [activeSessionKey]);

  // ── Auto-scroll ─────────────────────────────────────────────
  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // ── Refresh session list ────────────────────────────────────
  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch (e) {
      console.error("Erro ao atualizar sessoes:", e);
    }
  }, []);

  // ── New session ─────────────────────────────────────────────
  const handleNewSession = useCallback(async () => {
    if (busy) return;
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionKey(session.session_key);
    } catch (e) {
      setError("Erro ao criar nova sessao.");
    }
  }, [busy]);

  // ── Select session ──────────────────────────────────────────
  const handleSelectSession = useCallback(
    (sessionKey) => {
      if (busy) {
        abortControllerRef.current?.abort();
        abortControllerRef.current = null;
        setBusy(false);
      }
      setActiveSessionKey(sessionKey);
    },
    [busy]
  );

  // ── Delete session ──────────────────────────────────────────
  const handleDeleteSession = useCallback(
    async (sessionKey) => {
      if (busy) return;
      try {
        await deleteSession(sessionKey);
        setSessions((prev) => prev.filter((s) => s.session_key !== sessionKey));
        if (activeSessionKey === sessionKey) {
          const remaining = sessions.filter((s) => s.session_key !== sessionKey);
          if (remaining.length > 0) {
            setActiveSessionKey(remaining[0].session_key);
          } else {
            setActiveSessionKey(null);
          }
        }
      } catch (e) {
        setError("Erro ao deletar sessao.");
      }
    },
    [busy, activeSessionKey, sessions]
  );

  // ── Stop generation ─────────────────────────────────────────
  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  // ── Chat history for the API ────────────────────────────────
  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // ── Submit message ──────────────────────────────────────────
  const onSubmit = async (event) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");

    // If no active session, create one implicitly
    let currentSessionKey = activeSessionKey;
    if (!currentSessionKey) {
      try {
        const session = await createSession();
        setSessions((prev) => [session, ...prev]);
        currentSessionKey = session.session_key;
        setActiveSessionKey(currentSessionKey);
      } catch (e) {
        setError("Erro ao criar sessao para enviar mensagem.");
        return;
      }
    }

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
        session_key: currentSessionKey,
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
        onDone: async () => {
          // Refresh session list to get updated title
          await refreshSessions();
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

  if (loading) {
    return (
      <main className="app-shell">
        <div style={{ margin: "auto", color: "var(--muted)" }}>Carregando...</div>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Sidebar
        sessions={sessions}
        activeSessionKey={activeSessionKey}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="app-main">
        <header className="app-header">
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

        <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

