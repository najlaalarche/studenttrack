import { useState } from "react";
import { getModules } from "../api";

export default function Login({ onLogin }) {
  const [role, setRole] = useState(null);
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [module, setModule] = useState("");
  const [modules, setModules] = useState([]);
  const [error, setError] = useState("");
  const [loadingModules, setLoadingModules] = useState(false);

  const handleSelectRole = async (selectedRole) => {
    setRole(selectedRole);
    setError("");
    if (selectedRole === "professeur") {
      setLoadingModules(true);
      try {
        const data = await getModules();
        setModules(data);
      } catch {
        setModules([]);
      }
      setLoadingModules(false);
    }
    if (selectedRole === "administration") {
      onLogin("administration", {});
    }
  };

  const handleSubmit = () => {
    if (role === "etudiant") {
      if (!email.includes("@esith.net")) {
        setError("Veuillez entrer un email valide (@esith.net)");
        return;
      }
      onLogin("etudiant", { email });
    } else if (role === "professeur") {
      if (!nom.trim() || !module) {
        setError("Veuillez renseigner votre nom et sélectionner un module");
        return;
      }
      onLogin("professeur", { nom, module });
    }
  };

  const roles = [
    {
      id: "etudiant",
      icon: "🎓",
      label: "Étudiant",
      desc: "Consulter mon profil d'absences",
    },
    {
      id: "professeur",
      icon: "👨‍🏫",
      label: "Professeur",
      desc: "Absences de mes modules",
    },
    {
      id: "administration",
      icon: "🏫",
      label: "Administration",
      desc: "Tableau de bord complet",
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundImage: "url('/esith-bg.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Overlay sombre */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.45)",
        }}
      />

      {/* Card login */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          background: "rgba(255,255,255,0.97)",
          borderRadius: 16,
          padding: "40px 44px",
          width: 460,
          maxWidth: "90vw",
          boxShadow: "0 25px 60px rgba(0,0,0,0.35)",
        }}
      >
        {/* Logo ESITH */}
        <div style={{ textAlign: "center", marginBottom: 20, padding: "10px 0", backgroundColor: "transparent" }}>
          <img
            src="/logo-esith.png"
            alt="ESITH"
            style={{ height: 72, objectFit: "contain", display: "block", margin: "0 auto" }}
          />
        </div>

        {/* Titre */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#1a2a4a",
              margin: 0,
              marginBottom: 6,
            }}
          >
            Bienvenue sur StudentTrack
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            Système intelligent de suivi étudiant
          </p>
        </div>

        {/* Sélection rôle */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 10,
            marginBottom: 24,
          }}
        >
          {roles.map((r) => (
            <div
              key={r.id}
              onClick={() => handleSelectRole(r.id)}
              style={{
                border: `2px solid ${role === r.id ? "#8DC63F" : "#e2e8f0"}`,
                borderRadius: 10,
                padding: "14px 10px",
                textAlign: "center",
                cursor: "pointer",
                background: role === r.id ? "#f0fde4" : "#fff",
                transition: "all 0.15s",
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 6 }}>{r.icon}</div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: role === r.id ? "#4a7c14" : "#374151",
                  marginBottom: 4,
                }}
              >
                {r.label}
              </div>
              <div style={{ fontSize: 10, color: "#94a3b8", lineHeight: 1.4 }}>
                {r.desc}
              </div>
            </div>
          ))}
        </div>

        {/* Formulaire étudiant */}
        {role === "etudiant" && (
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "#374151",
                display: "block",
                marginBottom: 6,
              }}
            >
              Email ESITH
            </label>
            <input
              type="email"
              placeholder="prenom.nom@esith.net"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 8,
                border: "1.5px solid #cbd5e1",
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
                color: "#1e293b",
              }}
            />
          </div>
        )}

        {/* Formulaire professeur */}
        {role === "professeur" && (
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "#374151",
                display: "block",
                marginBottom: 6,
              }}
            >
              Votre nom
            </label>
            <input
              type="text"
              placeholder="Nom et prénom"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 8,
                border: "1.5px solid #cbd5e1",
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
                marginBottom: 10,
                color: "#1e293b",
              }}
            />
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "#374151",
                display: "block",
                marginBottom: 6,
              }}
            >
              Module
            </label>
            {loadingModules ? (
              <div style={{ fontSize: 12, color: "#94a3b8" }}>
                Chargement des modules...
              </div>
            ) : (
              <select
                value={module}
                onChange={(e) => setModule(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1.5px solid #cbd5e1",
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                  color: "#1e293b",
                  background: "#fff",
                }}
              >
                <option value="">Sélectionner un module</option>
                {modules.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Erreur */}
        {error && (
          <div
            style={{
              fontSize: 12,
              color: "#ef4444",
              marginBottom: 12,
              padding: "8px 12px",
              background: "#fef2f2",
              borderRadius: 6,
              border: "1px solid #fecaca",
            }}
          >
            {error}
          </div>
        )}

        {/* Bouton connexion */}
        {role && role !== "administration" && (
          <button
            onClick={handleSubmit}
            style={{
              width: "100%",
              padding: "12px",
              background: "#8DC63F",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.02em",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => (e.target.style.background = "#6fa52e")}
            onMouseLeave={(e) => (e.target.style.background = "#8DC63F")}
          >
            Se connecter →
          </button>
        )}

        {/* Footer */}
        <div
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 11,
            color: "#94a3b8",
          }}
        >
          Club Cybotics — ESITH Casablanca
        </div>
      </div>
    </div>
  );
}
