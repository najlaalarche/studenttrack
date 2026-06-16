import { useState } from "react";
import { authResetPassword } from "../api";

const GREEN      = "#8DC63F";
const GREEN_DARK = "#6fa52e";

function PasswordStrength({ password }) {
  if (!password) return null;
  const score =
    (password.length >= 8 ? 1 : 0) +
    (/[A-Z]/.test(password) ? 1 : 0) +
    (/\d/.test(password) ? 1 : 0) +
    (/[^A-Za-z0-9]/.test(password) ? 1 : 0);
  const levels = [
    { label: "Faible", color: "#ef4444" },
    { label: "Moyen",  color: "#f59e0b" },
    { label: "Fort",   color: GREEN },
  ];
  const { label, color } = levels[score <= 1 ? 0 : score <= 3 ? 1 : 2];
  return (
    <div style={{ marginTop: 6, marginBottom: 4 }}>
      <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ flex: 1, height: 4, borderRadius: 2,
            background: i <= (score <= 1 ? 0 : score <= 3 ? 1 : 2) ? color : "#e2e8f0" }} />
        ))}
      </div>
      <div style={{ fontSize: 11, color, fontWeight: 600 }}>{label}</div>
    </div>
  );
}

export default function ResetPassword({ token, onBackToLogin }) {
  const [password, setPassword]       = useState("");
  const [confirm, setConfirm]         = useState("");
  const [showPw, setShowPw]           = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [success, setSuccess]         = useState(false);
  const [error, setError]             = useState("");

  if (!token) {
    return (
      <div style={wrapStyle}>
        <div style={cardStyle}>
          <Logo />
          <div style={{ textAlign: "center", color: "#ef4444", fontSize: 14, marginBottom: 20 }}>
            Lien invalide — aucun token trouvé dans l'URL.
          </div>
          <button onClick={onBackToLogin} style={btnStyle(false)}>
            Aller à la connexion
          </button>
        </div>
      </div>
    );
  }

  const handleReset = async () => {
    setError("");
    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (password !== confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    setLoading(true);
    try {
      const res = await authResetPassword(token, password);
      if (res.success) {
        setSuccess(true);
      } else {
        setError(res.error || "Erreur lors de la réinitialisation.");
      }
    } catch {
      setError("Impossible de joindre le serveur. Vérifiez que le backend est démarré.");
    }
    setLoading(false);
  };

  return (
    <div style={wrapStyle}>
      <div style={cardStyle}>
        <Logo />
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a2a4a", textAlign: "center", marginBottom: 6 }}>
          Nouveau mot de passe
        </h2>
        <p style={{ fontSize: 12, color: "#64748b", textAlign: "center", marginBottom: 24 }}>
          Choisissez un mot de passe sécurisé pour votre compte StudentTrack.
        </p>

        {success ? (
          <>
            <div style={{ backgroundColor: "#f0fdf4", border: "1px solid #86efac",
              borderRadius: 8, padding: "16px", marginBottom: 20, textAlign: "center" }}>
              <div style={{ fontSize: 22, marginBottom: 8 }}>✓</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#166534", marginBottom: 6 }}>
                Mot de passe réinitialisé !
              </div>
              <div style={{ fontSize: 12, color: "#15803d" }}>
                Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.
              </div>
            </div>
            <button onClick={onBackToLogin} style={btnStyle(false)}>
              Aller à la connexion →
            </button>
          </>
        ) : (
          <>
            {/* Champ mot de passe */}
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Nouveau mot de passe</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="Minimum 8 caractères"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={inputStyle}
                />
                <span onClick={() => setShowPw(v => !v)}
                  style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                    fontSize: 16, cursor: "pointer", color: "#94a3b8" }}>
                  {showPw ? "👁" : "🙈"}
                </span>
              </div>
              <PasswordStrength password={password} />
            </div>

            {/* Confirmation */}
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Confirmer le mot de passe</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showConfirm ? "text" : "password"}
                  placeholder="Répéter le mot de passe"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleReset()}
                  style={inputStyle}
                />
                <span onClick={() => setShowConfirm(v => !v)}
                  style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                    fontSize: 16, cursor: "pointer", color: "#94a3b8" }}>
                  {showConfirm ? "👁" : "🙈"}
                </span>
              </div>
            </div>

            {error && (
              <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 14, padding: "8px 12px",
                background: "#fef2f2", borderRadius: 6, border: "1px solid #fecaca" }}>
                {error}
                {error.includes("invalide ou expiré") && (
                  <div style={{ marginTop: 6 }}>
                    <span onClick={onBackToLogin}
                      style={{ color: GREEN_DARK, cursor: "pointer", textDecoration: "underline" }}>
                      Demander un nouveau lien
                    </span>
                  </div>
                )}
              </div>
            )}

            <button onClick={handleReset} disabled={loading} style={btnStyle(loading)}>
              {loading ? "Réinitialisation..." : "Réinitialiser mon mot de passe →"}
            </button>

            <div style={{ textAlign: "center", marginTop: 12 }}>
              <span onClick={onBackToLogin}
                style={{ fontSize: 12, color: "#64748b", cursor: "pointer", textDecoration: "underline" }}>
                ← Retour à la connexion
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Logo() {
  return (
    <div style={{ textAlign: "center", marginBottom: 20 }}>
      <img src="/logo-esith.png" alt="ESITH"
        style={{ height: 64, objectFit: "contain", display: "block", margin: "0 auto" }} />
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
  position: "relative",
  zIndex: 10,
  background: "rgba(255,255,255,0.97)",
  borderRadius: 16,
  padding: "36px 44px",
  width: 420,
  maxWidth: "90vw",
  boxShadow: "0 25px 60px rgba(0,0,0,0.35)",
};

const labelStyle = {
  fontSize: 12, fontWeight: 600, color: "#374151",
  display: "block", marginBottom: 6,
};

const inputStyle = {
  width: "100%", padding: "10px 42px 10px 14px", borderRadius: 8,
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
