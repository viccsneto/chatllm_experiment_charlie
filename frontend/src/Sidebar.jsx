function Sidebar({ sessions, activeSessionKey, onSelect, onNew, onDelete }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="sidebar-btn-new" onClick={onNew} type="button">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <line x1="7" y1="1" x2="7" y2="13" />
            <line x1="1" y1="7" x2="13" y2="7" />
          </svg>
          Novo chat
        </button>
      </div>
      <div className="sidebar-list">
        {sessions.length === 0 && (
          <div style={{ padding: '16px 12px', color: 'var(--muted)', fontSize: '0.85rem', textAlign: 'center' }}>
            Nenhuma sessao ainda
          </div>
        )}
        {sessions.map((s) => (
          <div
            key={s.session_key}
            className={`sidebar-item${s.session_key === activeSessionKey ? ' active' : ''}`}
            onClick={() => onSelect(s.session_key)}
          >
            <span className="sidebar-item-title">
              {s.title || 'Nova sessao'}
            </span>
            <button
              className="sidebar-item-delete"
              onClick={(e) => { e.stopPropagation(); onDelete(s.session_key); }}
              type="button"
              title="Deletar sessao"
              aria-label="Deletar sessao"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="1" y1="1" x2="11" y2="11" />
                <line x1="11" y1="1" x2="1" y2="11" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}