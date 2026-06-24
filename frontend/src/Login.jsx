const { useState } = React;

function Login({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const cleanedEmail = email.trim();
    const cleanedPass = password.trim();
    if (!cleanedEmail || !cleanedPass) return;

    setError("");
    setBusy(true);
    try {
      let result;
      if (mode === "login") {
        result = await login(cleanedEmail, cleanedPass);
      } else {
        result = await signup(cleanedEmail, cleanedPass);
      }
      onAuth(result.token, result.email);
    } catch (err) {
      setError(err.message || "Erro inesperado");
    } finally {
      setBusy(false);
    }
  };

  const toggleMode = () => {
    setMode((prev) => (prev === "login" ? "signup" : "login"));
    setError("");
  };

  return (
    <main className="app-shell">
      <div className="auth-screen">
        <div className="auth-card">
          <h1 className="auth-title">ChatLLM Lab</h1>
          <p className="auth-subtitle">
            {mode === "login" ? "Entre na sua conta" : "Crie sua conta"}
          </p>

          <form onSubmit={handleSubmit} className="auth-form">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              maxLength={255}
              disabled={busy}
              autoFocus
              className="auth-input"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Senha"
              maxLength={128}
              disabled={busy}
              className="auth-input"
              required
              minLength={6}
            />

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-btn" disabled={busy || !email.trim() || !password.trim()}>
              {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
            </button>
          </form>

          <p className="auth-toggle">
            {mode === "login" ? (
              <>
                Nao tem conta?{" "}
                <button className="auth-link" onClick={toggleMode} disabled={busy}>
                  Cadastre-se
                </button>
              </>
            ) : (
              <>
                Ja tem conta?{" "}
                <button className="auth-link" onClick={toggleMode} disabled={busy}>
                  Entre aqui
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </main>
  );
}