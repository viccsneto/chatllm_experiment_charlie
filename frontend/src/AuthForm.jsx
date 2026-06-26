const { useState } = React;

const API_BASE = window.location.origin;

function AuthForm({ onLoginSuccess }) {
  const [mode, setMode] = useState("login"); // login | register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password.trim()) return;

    setBusy(true);
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body = mode === "login"
        ? { email: email.trim(), password }
        : { email: email.trim(), password, display_name: displayName.trim() || null };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Erro na autenticacao");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      onLoginSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setError("");
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <h2 className="auth-title">{mode === "login" ? "Entrar" : "Criar conta"}</h2>
        <p className="auth-subtitle">ChatLLM Lab</p>

        {error && <div className="note error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            maxLength={255}
            disabled={busy}
            autoFocus
            required
          />
          {mode === "register" && (
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Nome (opcional)"
              maxLength={100}
              disabled={busy}
            />
          )}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Senha"
            maxLength={128}
            disabled={busy}
            required
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          <button type="submit" disabled={busy || !email.trim() || !password.trim()}>
            {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <button className="auth-toggle" onClick={toggleMode} disabled={busy}>
          {mode === "login"
            ? "Nao tem conta? Cadastre-se"
            : "Ja tem conta? Faca login"}
        </button>
      </div>
    </div>
  );
}