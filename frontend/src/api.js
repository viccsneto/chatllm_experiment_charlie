const API_BASE = window.location.origin;

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(url, options = {}) {
  const headers = { ...authHeaders(), ...options.headers };
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_id");
    window.location.reload();
  }
  return response;
}

async function registerUser(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Erro ao cadastrar.");
  }
  return response.json();
}

async function loginUser(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Erro ao fazer login.");
  }
  return response.json();
}

async function logoutUser() {
  const headers = authHeaders();
  if (!headers.Authorization) return;
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers,
  });
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_email");
  localStorage.removeItem("user_id");
}

async function getMe() {
  const headers = authHeaders();
  if (!headers.Authorization) return null;
  const response = await apiFetch(`${API_BASE}/api/auth/me`, { headers });
  if (!response.ok) return null;
  return response.json();
}

async function sendMessageStream({ message, history, sessionId, signal, onDelta }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, session_id: sessionId }),
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
  let sessionIdReturned = null;

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

      if (payload.session_id) {
        sessionIdReturned = payload.session_id;
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }
    }
  }

  return sessionIdReturned;
}

async function listSessions() {
  const response = await apiFetch(`${API_BASE}/api/sessions`);
  if (!response.ok) throw new Error("Erro ao listar sessoes.");
  return response.json();
}

async function createSession() {
  const response = await apiFetch(`${API_BASE}/api/sessions`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Erro ao criar sessao.");
  return response.json();
}

async function getSessionMessages(sessionId) {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error("Erro ao carregar mensagens da sessao.");
  return response.json();
}

async function deleteSession(sessionId) {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Erro ao deletar sessao.");
}

async function updateSessionTitle(sessionId, title) {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/title`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error("Erro ao atualizar titulo.");
  return response.json();
}
