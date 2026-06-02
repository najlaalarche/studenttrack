import { useState } from "react";
import { getModules } from "../api.js";

const ROLES = [
  { key: "etudiant",       icon: "🎓", label: "Étudiant",       desc: "Consulter mon profil d'absences" },
  { key: "professeur",     icon: "👨‍🏫", label: "Professeur",     desc: "Absences de mes modules" },
  { key: "administration", icon: "🏛", label: "Administration", desc: "Tableau de bord complet" },
];

export default function Login({ onLogin }) {
  const [selected, setSelected] = useState(null);
  const [email, setEmail]       = useState("");
  const [module, setModule]     = useState("");
  const [modules, setModules]   = useState([]);
  const [loadingMods, setLoadingMods] = useState(false);
  const [error, setError]       = useState("");

  async function handleSelectRole(key) {
    setSelected(key);
    setError("");
    if (key === "professeur" && modules.length === 0) {
      setLoadingMods(true);
      try {
        const mods = await getModules();
        setModules(Array.isArray(mods) ? mods : []);
        if (Array.isArray(mods) && mods.length > 0) setModule(mods[0]);
      } catch { setModules([]); }
      finally { setLoadingMods(false); }
    }
  }

  function handleConnect() {
    if (selected === "etudiant") {
      if (!email.trim()) { setError("Veuillez saisir votre email."); return; }
      onLogin("etudiant", { email: email.trim() });
    } else if (selected === "professeur") {
      onLogin("professeur", { module });
    } else {
      onLogin("administration", {});
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "32px 16px", backgroundColor: "#0A0A0F" }}>
      {/* Logo */}
      <div style={{ textAlign: "center", marginBottom: 48 }}>
        <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: "0.15em", textTransform: "uppercase", color: "#6366F1", marginBottom: 8 }}>
          ESITH Casablanca
        </div>
        <h1 style={{ fontSize: 36, fontWeight: 700, color: "#F8FAFC", margin: 0, letterSpacing: "-0.02em" }}>
          StudentTrack
        </h1>
        <p style={{ marginTop: 8, fontSize: 14, color: "#64748B" }}>
          Système intelligent de suivi étudiant
        </p>
      </div>

      {/* Cartes rôles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, width: "100%", maxWidth: 640 }}>
        {ROLES.map((r) => {
          const isSelected = selected === r.key;
          return (
            <button
              key={r.key}
              onClick={() => handleSelectRole(r.key)}
              style={{
                textAlign: "left",
                padding: "20px 18px",
                borderRadius: 8,
                backgroundColor: isSelected ? "#16161F" : "#111118",
                border: `1px solid ${isSelected ? "#6366F1" : "#1E1E2E"}`,
                cursor: "pointer",
                boxShadow: isSelected ? "0 0 0 1px #6366F133" : "none",
                transform: isSelected ? "translateY(-1px)" : "none",
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 10 }}>{r.icon}</div>
              <div style={{ fontWeight: 600, fontSize: 14, color: "#F8FAFC", marginBottom: 4 }}>{r.label}</div>
              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.4 }}>{r.desc}</div>
            </button>
          );
        })}
      </div>

      {/* Formulaire */}
      {selected && (
        <div style={{
          marginTop: 20, width: "100%", maxWidth: 380,
          padding: "24px",
          backgroundColor: "#16161F",
          border: "1px solid #1E1E2E",
          borderRadius: 8,
          boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
        }}>
          {selected === "etudiant" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: "#94A3B8" }}>Email ESITH</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="prenom.nom@esith.ma"
                onKeyDown={(e) => e.key === "Enter" && handleConnect()}
                style={{
                  padding: "10px 12px", borderRadius: 6, fontSize: 13, outline: "none",
                  backgroundColor: "#111118", border: "1px solid #1E1E2E", color: "#F8FAFC",
                }}
              />
            </div>
          )}

          {selected === "professeur" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: "#94A3B8" }}>Module</label>
              {loadingMods ? (
                <p style={{ fontSize: 12, color: "#64748B" }}>Chargement des modules…</p>
              ) : (
                <select
                  value={module}
                  onChange={(e) => setModule(e.target.value)}
                  style={{ padding: "10px 12px", borderRadius: 6, fontSize: 13, outline: "none", backgroundColor: "#111118", border: "1px solid #1E1E2E", color: "#F8FAFC" }}
                >
                  {modules.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              )}
            </div>
          )}

          {selected === "administration" && (
            <p style={{ fontSize: 13, color: "#64748B", textAlign: "center", margin: 0 }}>
              Accès complet — aucune authentification requise.
            </p>
          )}

          {error && <p style={{ fontSize: 12, color: "#EF4444", marginTop: 8 }}>{error}</p>}

          <button
            onClick={handleConnect}
            style={{
              marginTop: 16, width: "100%", padding: "10px", borderRadius: 6,
              backgroundColor: "#6366F1", color: "#fff", fontWeight: 600, fontSize: 13,
              border: "none", cursor: "pointer",
            }}
            onMouseEnter={e => e.target.style.backgroundColor = "#5558e3"}
            onMouseLeave={e => e.target.style.backgroundColor = "#6366F1"}
          >
            Connexion →
          </button>
        </div>
      )}
    </div>
  );
}
