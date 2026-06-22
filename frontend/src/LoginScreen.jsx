const { useState } = React;

function LoginScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const cleaned = email.trim().toLowerCase();
    if (!cleaned || !password) {
      setError("Preencha email e senha.");
      return;
    }

    setLoading(true);
    try {
      const fn = mode === "login" ? loginUser : registerUser;
      const data = await fn(cleaned, password);
      localStorage.setItem("token", data.token);
      localStorage.setItem("email", data.email);
      onAuthSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <h2 className="auth-subtitle">
          {mode === "login" ? "Entrar" : "Criar conta"}
        </h2>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            placeholder="Seu email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            autoFocus
            disabled={loading}
          />
          <input
            type="password"
            placeholder="Sua senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            disabled={loading}
          />
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <div className="auth-switch">
          {mode === "login" ? (
            <button
              type="button"
              className="auth-link"
              onClick={() => { setMode("register"); setError(""); }}
            >
              Não tenho conta
            </button>
          ) : (
            <button
              type="button"
              className="auth-link"
              onClick={() => { setMode("login"); setError(""); }}
            >
              Já tenho conta
            </button>
          )}
        </div>
      </div>
    </div>
  );
}