const API_BASE = window.location.origin;

async function sendMessageStream({ message, history, session_id, onDelta, onSessionId, onSessionTitle, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

      if (payload.session_id && onSessionId) {
        onSessionId(payload.session_id);
      }

      if (payload.session_title && onSessionTitle) {
        onSessionTitle(payload.session_id, payload.session_title);
      }
    }
  }
}

async function fetchSessionMessages(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error("Erro ao carregar mensagens da sessao");
  const data = await response.json();
  return data.messages || [];
}
