import { useState } from "react";
import { getModules } from "../api.js";

const ROLES = [
  { key: "etudiant",       icon: "🎓", label: "Étudiant",       desc: "Consulter mon profil d'absences" },
  { key: "professeur",     icon: "👨‍🏫", label: "Professeur",     desc: "Absences de mes modules" },
  { key: "administration", icon: "🏛",  label: "Administration", desc: "Tableau de bord complet" },
];

const ESITH_BG   = "https://www.esith.ac.ma/wp-content/uploads/2021/01/esith-home.jpg";
const ESITH_LOGO = "https://www.esith.ac.ma/wp-content/uploads/2021/01/logo-esith.png";
const GREEN      = "#8DC63F";
const GREEN_DARK = "#7ab032";

export default function Login({ onLogin }) {
  const [selected, setSelected]       = useState(null);
  const [email, setEmail]             = useState("");
  const [nom, setNom]                 = useState("");
  const [module, setModule]           = useState("");
  const [modules, setModules]         = useState([]);
  const [loadingMods, setLoadingMods] = useState(false);
  const [error, setError]             = useState("");

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
      onLogin("professeur", { module, nom: nom.trim() });
    } else {
      onLogin("administration", {});
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundImage: `url(${ESITH_BG})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
      padding: "16px",
      position: "relative",
    }}>
      {/* Overlay sombre */}
      <div style={{
        position: "fixed", inset: 0,
        backgroundColor: "rgba(0,0,0,0.50)",
        zIndex: 0,
      }} />

      {/* Card */}
      <div style={{
        position: "relative", zIndex: 1,
        backgroundColor: "rgba(255,255,255,0.93)",
        borderRadius: 14,
        padding: "40px 36px",
        width: "100%",
        maxWidth: 460,
        boxShadow: "0 10px 48px rgba(0,0,0,0.40)",
      }}>

        {/* Logo ESITH */}
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <img
            src={ESITH_LOGO}
            alt="ESITH Logo"
            style={{ height: 68, objectFit: "contain" }}
            onError={(e) => { e.target.style.display = "none"; }}
          />
        </div>

        {/* Titre */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ fontSize: 21, fontWeight: 700, color: "#1a1a1a", margin: 0, lineHeight: 1.2 }}>
            Bienvenue sur StudentTrack
          </h1>
          <p style={{ marginTop: 7, fontSize: 13, color: "#555", margin: "7px 0 0" }}>
            Système intelligent de suivi étudiant
          </p>
        </div>

        {/* Sélection rôle */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 22 }}>
          {ROLES.map((r) => {
            const isSelected = selected === r.key;
            return (
              <button
                key={r.key}
                onClick={() => handleSelectRole(r.key)}
                style={{
                  textAlign: "center",
                  padding: "14px 8px",
                  borderRadius: 8,
                  backgroundColor: isSelected ? GREEN : "#f5f5f5",
                  border: `2px solid ${isSelected ? GREEN : "#e0e0e0"}`,
                  cursor: "pointer",
                  color: isSelected ? "#fff" : "#333",
                  transition: "all 0.15s",
                  outline: "none",
                }}
              >
                <div style={{ fontSize: 22, marginBottom: 6 }}>{r.icon}</div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{r.label}</div>
                <div style={{ fontSize: 11, marginTop: 3, opacity: 0.75, lineHeight: 1.3 }}>{r.desc}</div>
              </button>
            );
          })}
        </div>

        {/* Formulaire selon rôle */}
        {selected && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

            {selected === "etudiant" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#444" }}>Email ESITH</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="prenom.nom@esith.net"
                  onKeyDown={(e) => e.key === "Enter" && handleConnect()}
                  style={{
                    padding: "10px 12px", borderRadius: 6, fontSize: 13,
                    border: "1.5px solid #ccc", outline: "none",
                    color: "#1a1a1a", backgroundColor: "#fff",
                  }}
                />
              </div>
            )}

            {selected === "professeur" && (
              <>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "#444" }}>Nom</label>
                  <input
                    type="text"
                    value={nom}
                    onChange={(e) => setNom(e.target.value)}
                    placeholder="Votre nom"
                    style={{
                      padding: "10px 12px", borderRadius: 6, fontSize: 13,
                      border: "1.5px solid #ccc", outline: "none",
                      color: "#1a1a1a", backgroundColor: "#fff",
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "#444" }}>Module</label>
                  {loadingMods ? (
                    <p style={{ fontSize: 12, color: "#888", margin: 0 }}>Chargement des modules…</p>
                  ) : (
                    <select
                      value={module}
                      onChange={(e) => setModule(e.target.value)}
                      style={{
                        padding: "10px 12px", borderRadius: 6, fontSize: 13,
                        border: "1.5px solid #ccc", outline: "none",
                        color: "#1a1a1a", backgroundColor: "#fff",
                      }}
                    >
                      {modules.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  )}
                </div>
              </>
            )}

            {selected === "administration" && (
              <p style={{ fontSize: 13, color: "#666", textAlign: "center", margin: 0 }}>
                Accès complet — aucune authentification requise.
              </p>
            )}

            {error && (
              <p style={{ fontSize: 12, color: "#dc2626", margin: 0 }}>{error}</p>
            )}

            <button
              onClick={handleConnect}
              style={{
                marginTop: 4, width: "100%", padding: "11px",
                borderRadius: 6, backgroundColor: GREEN,
                color: "#fff", fontWeight: 700, fontSize: 14,
                border: "none", cursor: "pointer", letterSpacing: "0.02em",
                transition: "background-color 0.15s",
              }}
              onMouseEnter={(e) => { e.target.style.backgroundColor = GREEN_DARK; }}
              onMouseLeave={(e) => { e.target.style.backgroundColor = GREEN; }}
            >
              Se connecter →
            </button>
          </div>
        )}

        <p style={{ textAlign: "center", fontSize: 11, color: "#999", marginTop: 24, marginBottom: 0 }}>
          Club Cybotics — ESITH Casablanca
        </p>
      </div>
    </div>
  );
}
