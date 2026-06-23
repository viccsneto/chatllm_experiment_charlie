const API_BASE = window.location.origin;

const JSON_HEADERS = { "Content-Type": "application/json" };

// ── Auth ──────────────────────────────────────────────────────────────────────

async function register(email, password, confirmPassword) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "include",
    body: JSON.stringify({ email, password, confirm_password: confirmPassword }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.[0]?.msg || body?.detail || "Erro no cadastro");
  }
  return await res.json();
}

async function login(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail || "Email ou senha invalidos");
  }
  return await res.json();
}

async function logout() {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

async function fetchMe() {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  return await res.json();
}

// ── Chat ──────────────────────────────────────────────────────────────────────

async function sendMessageStream({ message, history, session_id, onDelta, onDone, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "include",
    body: JSON.stringify({ message, history, session_id }),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body?.detail || "Erro ao enviar mensagem para o servidor.";
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const line = rawEvent
        .split("\n")
        .find((part) => part.startsWith("data:"));
      if (!line) continue;

      const payloadText = line.slice(5).trim();
      if (!payloadText) continue;

      let payload;
      try {
        payload = JSON.parse(payloadText);
      } catch {
        continue;
      }

      if (payload.error) {
        throw new Error(payload.error);
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }

      if (payload.done && onDone) {
        onDone(payload.session_id);
      }
    }
  }
}

async function fetchSessions() {
  const res = await fetch(`${API_BASE}/api/sessions`, { credentials: "include" });
  if (!res.ok) throw new Error("Falha ao carregar sessoes");
  const data = await res.json();
  return data.sessions;
}

async function createSession() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "include",
  });
  if (!res.ok) throw new Error("Falha ao criar sessao");
  return await res.json();
}

async function fetchSessionMessages(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, { credentials: "include" });
  if (!res.ok) throw new Error("Falha ao carregar mensagens");
  const data = await res.json();
  return data.messages;
}

async function deleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Falha ao deletar sessao");
}
