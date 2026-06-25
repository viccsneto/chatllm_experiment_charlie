const { createContext, useContext, useState, useEffect } = React;

const AuthContext = createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authScreen, setAuthScreen] = useState(null); // null | "login" | "register"

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const email = localStorage.getItem("user_email");
    const userId = localStorage.getItem("user_id");
    if (token && email) {
      setUser({ email, id: parseInt(userId || "0") });
      // Validar token com /me
      getMe().then((me) => {
        if (me) {
          setUser({ email: me.email, id: me.id });
        } else {
          setUser(null);
          localStorage.removeItem("access_token");
          localStorage.removeItem("user_email");
          localStorage.removeItem("user_id");
        }
      }).catch(() => {
        // Se falhar, mantém o usuário mesmo assim
      });
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const data = await loginUser(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("user_email", data.email);
    localStorage.setItem("user_id", data.user_id);
    setUser({ email: data.email, id: data.user_id });
    setAuthScreen(null);
  };

  const register = async (email, password) => {
    const data = await registerUser(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("user_email", data.email);
    localStorage.setItem("user_id", data.user_id);
    setUser({ email: data.email, id: data.user_id });
    setAuthScreen(null);
  };

  const logout = async () => {
    await logoutUser();
    setUser(null);
    setAuthScreen(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, authScreen, setAuthScreen, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}

// --- Tela de Login / Register ---

function AuthScreen() {
  const { authScreen, setAuthScreen, login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isLogin = authScreen === "login";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Preencha todos os campos.");
      return;
    }
    setBusy(true);
    try {
      if (isLogin) {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password);
      }
    } catch (err) {
      setError(err.message || "Erro inesperado.");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setAuthScreen(isLogin ? "register" : "login");
    setError("");
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <div className="auth-brand">ChatLLM Lab</div>
        <h2>{isLogin ? "Entrar" : "Criar conta"}</h2>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={busy}
            autoFocus
            autoComplete="email"
          />
          <input
            type="password"
            placeholder="Senha (mín. 6 caracteres)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
          <button type="submit" disabled={busy}>
            {busy ? "Aguarde..." : isLogin ? "Entrar" : "Cadastrar"}
          </button>
        </form>
        <p className="auth-switch">
          {isLogin ? "Não tem conta?" : "Já tem conta?"}{" "}
          <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>
            {isLogin ? "Cadastre-se" : "Faça login"}
          </a>
        </p>
      </div>
    </div>
  );
}