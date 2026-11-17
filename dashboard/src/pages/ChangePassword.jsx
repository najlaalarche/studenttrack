import { useState } from "react";
import { authChangePassword } from "../api";

const GREEN = "#8DC63F";

// Première connexion avec un mot de passe temporaire (compte créé par import CSV) :
// l'étudiant doit choisir son propre mot de passe avant d'accéder au tableau de bord.
export default function ChangePassword({ prenom, onDone, onLogout }) {
  const [actuel, setActuel]   = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow]       = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const handleSubmit = async () => {
    setError("");
    if (!actuel) { setError("Saisissez le mot de passe temporaire reçu par email."); return; }
    if (nouveau.length < 8) { setError("Le nouveau mot de passe doit contenir au moins 8 caractères."); return; }
    if (nouveau !== confirm) { setError("Les mots de passe ne correspondent pas."); return; }
    if (nouveau === actuel) { setError("Le nouveau mot de passe doit être différent du mot de passe temporaire."); return; }
    setLoading(true);
    try {
      const res = await authChangePassword(actuel, nouveau);
      if (res.success) onDone();
      else setError(res.error || "Erreur lors du changement de mot de passe.");
    } catch {
      setError("Impossible de joindre le serveur. Vérifiez que le backend est démarré.");
    }
    setLoading(false);
  };

  const champ = (label, value, setValue, placeholder, onEnter) => (
    <div style={{ marginBottom: 14 }}>
      <label style={labelStyle}>{label}</label>
      <input
        type={show ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onEnter ? (e) => e.key === "Enter" && handleSubmit() : undefined}
        style={inputStyle}
      />
    </div>
  );

  return (
    <div style={wrapStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <img src="/logo-esith.png" alt="ESITH"
            style={{ height: 64, objectFit: "contain", display: "block", margin: "0 auto" }} />
        </div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a2a4a", textAlign: "center", marginBottom: 6 }}>
          {prenom ? `Bienvenue ${prenom}` : "Bienvenue"}
        </h2>
        <p style={{ fontSize: 12, color: "#64748b", textAlign: "center", marginBottom: 24 }}>
          Pour sécuriser votre compte, remplacez le mot de passe temporaire reçu par email
          par un mot de passe personnel.
        </p>

        {champ("Mot de passe temporaire", actuel, setActuel, "Reçu par email")}
        {champ("Nouveau mot de passe", nouveau, setNouveau, "Minimum 8 caractères")}
        {champ("Confirmer le nouveau mot de passe", confirm, setConfirm, "Répéter le mot de passe", true)}

        <label style={{ fontSize: 12, color: "#64748b", display: "flex", alignItems: "center", gap: 6, marginBottom: 16, cursor: "pointer" }}>
          <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} />
          Afficher les mots de passe
        </label>

        {error && (
          <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 14, padding: "8px 12px",
            background: "#fef2f2", borderRadius: 6, border: "1px solid #fecaca" }}>
            {error}
          </div>
        )}

        <button onClick={handleSubmit} disabled={loading} style={btnStyle(loading)}>
          {loading ? "Enregistrement..." : "Enregistrer mon mot de passe →"}
        </button>

        <div style={{ textAlign: "center", marginTop: 12 }}>
          <span onClick={onLogout}
            style={{ fontSize: 12, color: "#64748b", cursor: "pointer", textDecoration: "underline" }}>
            Se déconnecter
          </span>
        </div>
      </div>
    </div>
  );
}

const wrapStyle = {
  minHeight: "100vh",
  backgroundImage: "url('/esith-bg.jpg')",
  backgroundSize: "cover",
  backgroundPosition: "center",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: "'Inter', sans-serif",
};

const cardStyle = {
  background: "rgba(255,255,255,0.97)",
  borderRadius: 16,
  padding: "36px 44px",
  width: 420,
  maxWidth: "90vw",
  boxShadow: "0 25px 60px rgba(0,0,0,0.35)",
};

const labelStyle = { fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 };

const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8,
  border: "1.5px solid #cbd5e1", fontSize: 14, outline: "none",
  boxSizing: "border-box", color: "#1e293b",
};

const btnStyle = (disabled) => ({
  width: "100%", padding: "12px",
  background: disabled ? "#a0aec0" : GREEN,
  color: "#fff", border: "none", borderRadius: 8,
  fontSize: 14, fontWeight: 700,
  cursor: disabled ? "not-allowed" : "pointer",
});
