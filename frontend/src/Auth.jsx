const { useState } = React;

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (mode === "register" && password !== confirmPassword) {
      setError("Senhas nao conferem");
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, confirmPassword);
      }
      const user = await fetchMe();
      if (user) onAuth(user);
    } catch (err) {
      setError(err.message || "Erro inesperado");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setError("");
  };

  return (
    <main className="app-shell">
      <div className="auth-container">
        <div className="auth-box">
          <h1 className="auth-title">ChatLLM Lab</h1>
          <h2 className="auth-subtitle">
            {mode === "login" ? "Entrar" : "Criar conta"}
          </h2>

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="auth-email">Email</label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoFocus
              />
            </div>

            <div className="auth-field">
              <label htmlFor="auth-password">Senha</label>
              <input
                id="auth-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "Minimo 8 caracteres" : "Sua senha"}
                minLength={8}
                required
              />
            </div>

            {mode === "register" && (
              <div className="auth-field">
                <label htmlFor="auth-confirm">Confirmar senha</label>
                <input
                  id="auth-confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repita a senha"
                  minLength={8}
                  required
                />
              </div>
            )}

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-submit" disabled={loading}>
              {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? (
              <>Nao tem conta? <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>Cadastre-se</a></>
            ) : (
              <>Ja tem conta? <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>Faca login</a></>
            )}
          </p>
        </div>
      </div>
    </main>
  );
}