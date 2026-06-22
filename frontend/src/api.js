const API_BASE = window.location.origin;

function getAuthHeaders() {
  const token = localStorage.getItem("token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function sendMessageStream({ message, history, session_key, onDelta, onDone, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ message, history, session_key }),
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
        onDone(payload.session_key);
      }
    }
  }
}

async function listSessions() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao listar sessoes.");
  const data = await res.json();
  return data.sessions;
}

async function createSession() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Erro ao criar sessao.");
  return res.json();
}

async function deleteSession(sessionKey) {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao deletar sessao.");
}

async function renameSession(sessionKey, title) {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Erro ao renomear sessao.");
  return res.json();
}

// ── Auth ────────────────────────────────────────────────────
async function registerUser(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao cadastrar.");
  return data;
}

async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao logar.");
  return data;
}

async function verifyToken() {
  const token = localStorage.getItem("token");
  if (!token) return null;
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    localStorage.removeItem("token");
    localStorage.removeItem("email");
    return null;
  }
  return res.json();
}
