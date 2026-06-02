const NAV = [
  { key: "overview",  icon: "◈", label: "Vue d'ensemble" },
  { key: "etudiants", icon: "⊞", label: "Étudiants" },
  { key: "alertes",   icon: "◉", label: "Alertes" },
  { key: "sync",      icon: "↻", label: "Synchronisation" },
];

export default function Sidebar({ active, onNav, onLogout, userName }) {
  return (
    <aside style={{
      position: "fixed", top: 0, left: 0, height: "100vh",
      width: 220, display: "flex", flexDirection: "column",
      padding: "20px 12px",
      backgroundColor: "#111118",
      borderRight: "1px solid #1E1E2E",
      zIndex: 20,
    }}>
      {/* Logo */}
      <div style={{ padding: "4px 8px 20px" }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#6366F1", marginBottom: 2 }}>
          ESITH
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#F8FAFC" }}>StudentTrack</div>
      </div>

      <div style={{ height: 1, backgroundColor: "#1E1E2E", marginBottom: 12 }} />

      {/* Nav */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map((item) => {
          const isActive = active === item.key;
          return (
            <button
              key={item.key}
              onClick={() => onNav(item.key)}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "8px 10px", borderRadius: 6,
                backgroundColor: isActive ? "#1E1E2E" : "transparent",
                color: isActive ? "#F8FAFC" : "#64748B",
                fontWeight: isActive ? 500 : 400,
                fontSize: 13,
                border: "none", cursor: "pointer", textAlign: "left", width: "100%",
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.backgroundColor = "#16161F"; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.backgroundColor = "transparent"; }}
            >
              <span style={{ fontSize: 14, opacity: 0.7 }}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ borderTop: "1px solid #1E1E2E", paddingTop: 12 }}>
        {userName && (
          <div style={{ padding: "6px 10px", fontSize: 12, color: "#94A3B8", marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {userName}
          </div>
        )}
        <button
          onClick={onLogout}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "8px 10px", borderRadius: 6, width: "100%",
            backgroundColor: "transparent", color: "#64748B",
            fontSize: 12, border: "none", cursor: "pointer",
          }}
          onMouseEnter={e => e.currentTarget.style.color = "#94A3B8"}
          onMouseLeave={e => e.currentTarget.style.color = "#64748B"}
        >
          <span>←</span><span>Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}
