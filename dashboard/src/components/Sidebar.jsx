const NAV = [
  { key: "overview",             icon: "◈", label: "Vue d'ensemble" },
  { key: "etudiants",            icon: "⊞", label: "Étudiants" },
  { key: "alertes",              icon: "◉", label: "Historique des Alertes" },
  { key: "importation",          icon: "↑", label: "Importation CSV" },
  { key: "gestion-etudiants",    icon: "✦", label: "Gestion Étudiants" },
  { key: "gestion-professeurs",  icon: "◆", label: "Gestion Professeurs" },
  { key: "sync",                 icon: "↻", label: "Synchronisation" },
];

export default function Sidebar({ active, onNav, onLogout, userName }) {
  return (
    <aside style={{
      position: "fixed", top: 0, left: 0, height: "100vh",
      width: 220, display: "flex", flexDirection: "column",
      padding: "20px 12px",
      backgroundColor: "#FFFFFF",
      borderRight: "1px solid #E2E8F0",
      zIndex: 20,
    }}>
      {/* Logo + titre */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 20px" }}>
        <img
          src="/logo-esith.png"
          alt="ESITH"
          style={{ height: 32, width: 32, objectFit: "contain", flexShrink: 0 }}
          onError={(e) => { e.target.style.display = "none"; }}
        />
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#8DC63F", lineHeight: 1 }}>
            ESITH
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#1a3a6b", lineHeight: 1.2 }}>StudentTrack</div>
        </div>
      </div>

      <div style={{ height: 1, backgroundColor: "#E2E8F0", marginBottom: 12 }} />

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
                backgroundColor: isActive ? "#eef2fb" : "transparent",
                color: isActive ? "#1a3a6b" : "#64748b",
                fontWeight: isActive ? 600 : 400,
                fontSize: 13,
                border: "none", cursor: "pointer", textAlign: "left", width: "100%",
                borderLeft: isActive ? "3px solid #1a3a6b" : "3px solid transparent",
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.backgroundColor = "#f1f5f9"; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.backgroundColor = "transparent"; }}
            >
              <span style={{ fontSize: 14, opacity: isActive ? 1 : 0.6 }}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: 12 }}>
        {userName && (
          <div style={{ padding: "6px 10px", fontSize: 12, color: "#1a3a6b", fontWeight: 500, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {userName}
          </div>
        )}
        <button
          onClick={onLogout}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "8px 10px", borderRadius: 6, width: "100%",
            backgroundColor: "transparent", color: "#64748b",
            fontSize: 12, border: "none", cursor: "pointer",
          }}
          onMouseEnter={e => e.currentTarget.style.color = "#1a3a6b"}
          onMouseLeave={e => e.currentTarget.style.color = "#64748b"}
        >
          <span>←</span><span>Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}
