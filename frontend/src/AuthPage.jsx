const { useState } = React;

function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const resetForm = () => {
    setName("");
    setEmail("");
    setPassword("");
    setError("");
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    resetForm();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "signup") {
        const result = await apiSignup(name, email, password);
        localStorage.setItem("auth_token", result.token);
        localStorage.setItem("user_name", result.name);
        localStorage.setItem("user_email", result.email);
        onAuthSuccess(result);
      } else {
        const result = await apiLogin(email, password);
        localStorage.setItem("auth_token", result.token);
        localStorage.setItem("user_name", result.name);
        localStorage.setItem("user_email", result.email);
        onAuthSuccess(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <h2 className="auth-subtitle">
          {mode === "login" ? "Entrar" : "Criar conta"}
        </h2>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "signup" && (
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nome"
              maxLength={255}
              required
              disabled={loading}
            />
          )}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            maxLength={255}
            required
            disabled={loading}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Senha"
            minLength={4}
            maxLength={128}
            required
            disabled={loading}
          />
          <button type="submit" disabled={loading || !email.trim() || !password.trim() || (mode === "signup" && !name.trim())}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? (
            <>
              Nao tem conta?{" "}
              <button className="auth-link-btn" onClick={() => switchMode("signup")}>
                Cadastre-se
              </button>
            </>
          ) : (
            <>
              Ja tem conta?{" "}
              <button className="auth-link-btn" onClick={() => switchMode("login")}>
                Fazer login
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}