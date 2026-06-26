const { useState, useEffect, useCallback } = React;

const API_BASE = window.location.origin;

function Sidebar({ currentSessionId, onSelectSession, onNewSession, refreshTrigger }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  const fetchSessions = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE}/api/sessions`, { headers });
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, currentSessionId, refreshTrigger]);

  const handleNewSession = async () => {
    onNewSession();
    await fetchSessions();
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      const token = localStorage.getItem("token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
        method: "DELETE",
        headers,
      });
      if (res.ok) {
        if (currentSessionId === sessionId) {
          onNewSession();
        }
        await fetchSessions();
      }
    } catch {
      // ignore
    }
  };

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        {!collapsed && <span className="sidebar-title">Sessoes</span>}
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Expandir sidebar" : "Recolher sidebar"}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            {collapsed ? (
              <path d="M6 2l6 6-6 6V2z" />
            ) : (
              <path d="M10 2L4 8l6 6V2z" />
            )}
          </svg>
        </button>
      </div>

      {!collapsed && (
        <>
          <button className="sidebar-new-btn" onClick={handleNewSession}>
            + Nova sessao
          </button>

          <nav className="sidebar-list" aria-label="Lista de sessoes">
            {loading && <div className="sidebar-loading">Carregando...</div>}
            {!loading && sessions.length === 0 && (
              <div className="sidebar-empty">Nenhuma sessao ainda</div>
            )}
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`sidebar-item ${session.id === currentSessionId ? "active" : ""}`}
                onClick={() => onSelectSession(session.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter") onSelectSession(session.id); }}
              >
                <span className="sidebar-item-title">
                  {session.title || "Nova sessao"}
                </span>
                <button
                  className="sidebar-item-delete"
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  aria-label={`Deletar sessao ${session.id}`}
                  title="Deletar sessao"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
                    <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="2" />
                  </svg>
                </button>
              </div>
            ))}
          </nav>
        </>
      )}
    </aside>
  );
}