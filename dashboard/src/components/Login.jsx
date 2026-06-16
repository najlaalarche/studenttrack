import { useState } from "react";
import { authProfesseurLogin, authCheckEmail, authRegister, authLogin, authAdminLogin, authForgotPassword } from "../api";

const GREEN = "#8DC63F";
const GREEN_DARK = "#6fa52e";

function PasswordStrength({ password }) {
  const len = password.length;
  const hasUpper = /[A-Z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);
  const score = (len >= 8 ? 1 : 0) + (hasUpper ? 1 : 0) + (hasDigit ? 1 : 0) + (hasSpecial ? 1 : 0);

  if (!password) return null;

  const levels = [
    { label: "Faible", color: "#ef4444" },
    { label: "Moyen", color: "#f59e0b" },
    { label: "Fort", color: GREEN },
  ];
  const level = score <= 1 ? 0 : score <= 3 ? 1 : 2;
  const { label, color } = levels[level];

  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: i <= level ? color : "#e2e8f0",
              transition: "background 0.2s",
            }}
          />
        ))}
      </div>
      <div style={{ fontSize: 11, color, fontWeight: 600 }}>{label}</div>
    </div>
  );
}

function InputField({ label, type, placeholder, value, onChange, onKeyDown, rightEl }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
        {label}
      </label>
      <div style={{ position: "relative" }}>
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          style={{
            width: "100%",
            padding: "10px 14px",
            paddingRight: rightEl ? 40 : 14,
            borderRadius: 8,
            border: "1.5px solid #cbd5e1",
            fontSize: 14,
            outline: "none",
            boxSizing: "border-box",
            color: "#1e293b",
          }}
        />
        {rightEl && (
          <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)" }}>
            {rightEl}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Login({ onLogin }) {
  const [role, setRole] = useState(null);

  // Étudiant auth state
  const [step, setStep] = useState(1); // 1=email, 2a=login, 2b=register, 2c=not-found
  const [email, setEmail] = useState("");
  const [prenom, setPrenom] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  // Administration state
  const [adminPassword, setAdminPassword] = useState("");
  const [showAdminPassword, setShowAdminPassword] = useState(false);

  // Forgot-password state
  const [forgotMode, setForgotMode]           = useState(false);
  const [forgotEmail, setForgotEmail]         = useState("");
  const [forgotSent, setForgotSent]           = useState(false);
  const [forgotLoading, setForgotLoading]     = useState(false);

  // Professeur state
  const [profEmail, setProfEmail]           = useState("");
  const [profPassword, setProfPassword]     = useState("");
  const [showProfPassword, setShowProfPassword] = useState(false);

  const [error, setError] = useState("");

  const handleSelectRole = async (selectedRole) => {
    setRole(selectedRole);
    setError("");
    setStep(1);
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setPrenom("");
    setFiliere("");
    setSemestre("Tous");
    if (selectedRole === "professeur") {
      setProfEmail("");
      setProfPassword("");
      setShowProfPassword(false);
    }
    if (selectedRole === "administration") {
      setAdminPassword("");
      setShowAdminPassword(false);
    }
  };

  const handleCheckEmail = async () => {
    if (!email.includes("@esith.net")) {
      setError("Veuillez entrer un email valide (@esith.net)");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await authCheckEmail(email);
      setPrenom(res.prenom || "");
      if (!res.exists) {
        setStep("2c");
      } else if (res.has_password) {
        setStep("2a");
      } else {
        setStep("2b");
      }
    } catch {
      setError("Erreur de connexion au serveur");
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await authLogin(email, password);
      if (res.success) {
        onLogin("etudiant", { email, ...res.etudiant });
      } else {
        setError(res.error || "Échec de la connexion");
      }
    } catch {
      setError("Erreur de connexion au serveur");
    }
    setLoading(false);
  };

  const handleRegister = async () => {
    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await authRegister(email, password);
      if (res.success) {
        const loginRes = await authLogin(email, password);
        if (loginRes.success) {
          onLogin("etudiant", { email, ...loginRes.etudiant });
        }
      } else {
        setError(res.error || "Erreur lors de la création du compte");
      }
    } catch {
      setError("Erreur de connexion au serveur");
    }
    setLoading(false);
  };

const handleAdminLogin = async () => {
    if (!adminPassword) { setError("Veuillez saisir le mot de passe"); return; }
    setError("");
    setLoading(true);
    try {
      const res = await authAdminLogin(adminPassword);
      if (res.success) {
        onLogin("administration", {});
      } else {
        setError(res.error || "Mot de passe incorrect");
      }
    } catch {
      setError("Erreur de connexion au serveur");
    }
    setLoading(false);
  };

  const handleProfesseur = async () => {
    if (!profEmail.includes("@")) { setError("Veuillez entrer un email valide"); return; }
    if (!profPassword) { setError("Veuillez saisir votre mot de passe"); return; }
    setError("");
    setLoading(true);
    try {
      const res = await authProfesseurLogin(profEmail.trim().toLowerCase(), profPassword);
      if (res.success) {
        onLogin("professeur", res.professeur);
      } else {
        setError(res.error || "Email ou mot de passe incorrect");
      }
    } catch {
      setError("Erreur de connexion au serveur");
    }
    setLoading(false);
  };

  const handleForgotPassword = async () => {
    if (!forgotEmail.includes("@")) {
      setError("Veuillez entrer un email valide");
      return;
    }
    setForgotLoading(true);
    setError("");
    try {
      await authForgotPassword(forgotEmail.trim().toLowerCase());
    } catch { /* ignore — réponse générique côté serveur */ }
    setForgotSent(true);
    setForgotLoading(false);
  };

  const EyeIcon = ({ visible }) => (
    <span
      onClick={() => {}}
      style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8", userSelect: "none" }}
    >
      {visible ? "👁" : "🙈"}
    </span>
  );

  const roles = [
    { id: "etudiant", icon: "🎓", label: "Étudiant", desc: "Consulter mon profil d'absences" },
    { id: "professeur", icon: "👨‍🏫", label: "Professeur", desc: "Absences de mes modules" },
    { id: "administration", icon: "🏫", label: "Administration", desc: "Tableau de bord complet" },
  ];

  const btnStyle = (disabled) => ({
    width: "100%",
    padding: "12px",
    background: disabled ? "#a0aec0" : GREEN,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 700,
    cursor: disabled ? "not-allowed" : "pointer",
    letterSpacing: "0.02em",
    transition: "background 0.15s",
  });

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
      <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)" }} />

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
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 20, padding: "10px 0", backgroundColor: "transparent" }}>
          <img
            src="/logo-esith.png"
            alt="ESITH"
            style={{ height: 72, objectFit: "contain", display: "block", margin: "0 auto" }}
          />
        </div>

        {/* Titre */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#1a2a4a", margin: 0, marginBottom: 6 }}>
            Bienvenue sur StudentTrack
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            Système intelligent de suivi étudiant
          </p>
        </div>

        {/* Sélection rôle */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 24 }}>
          {roles.map((r) => (
            <div
              key={r.id}
              onClick={() => handleSelectRole(r.id)}
              style={{
                border: `2px solid ${role === r.id ? GREEN : "#e2e8f0"}`,
                borderRadius: 10,
                padding: "14px 10px",
                textAlign: "center",
                cursor: "pointer",
                background: role === r.id ? "#f0fde4" : "#fff",
                transition: "all 0.15s",
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 6 }}>{r.icon}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: role === r.id ? "#4a7c14" : "#374151", marginBottom: 4 }}>
                {r.label}
              </div>
              <div style={{ fontSize: 10, color: "#94a3b8", lineHeight: 1.4 }}>{r.desc}</div>
            </div>
          ))}
        </div>

        {/* ---- ÉTUDIANT ---- */}
        {role === "etudiant" && step === 1 && (
          <>
            <InputField
              label="Email ESITH"
              type="email"
              placeholder="prenom.nom@esith.net"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCheckEmail()}
            />
            {error && <ErrorBox msg={error} />}
            <button
              onClick={handleCheckEmail}
              disabled={loading}
              style={btnStyle(loading)}
            >
              {loading ? "Vérification..." : "Continuer →"}
            </button>
          </>
        )}

        {role === "etudiant" && step === "2a" && !forgotMode && (
          <>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#1a2a4a", marginBottom: 16 }}>
              Bon retour {prenom ? prenom : ""} !
            </div>
            <InputField
              label="Mot de passe"
              type={showPassword ? "text" : "password"}
              placeholder="Votre mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              rightEl={
                <span
                  onClick={() => setShowPassword((v) => !v)}
                  style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8" }}
                >
                  {showPassword ? "👁" : "🙈"}
                </span>
              }
            />
            <div style={{ textAlign: "right", marginTop: -8, marginBottom: 14 }}>
              <span
                onClick={() => { setForgotMode(true); setForgotEmail(email); setForgotSent(false); setError(""); }}
                style={{ fontSize: 12, color: GREEN_DARK, cursor: "pointer", textDecoration: "underline" }}
              >
                Mot de passe oublié ?
              </span>
            </div>
            {error && <ErrorBox msg={error} />}
            <button onClick={handleLogin} disabled={loading} style={btnStyle(loading)}>
              {loading ? "Connexion..." : "Se connecter →"}
            </button>
            <BackLink onClick={() => { setStep(1); setError(""); setPassword(""); }} />
          </>
        )}

        {role === "etudiant" && step === "2a" && forgotMode && (
          <>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#1a2a4a", marginBottom: 4 }}>
              Mot de passe oublié
            </div>
            {!forgotSent ? (
              <>
                <p style={{ fontSize: 12, color: "#64748b", marginBottom: 14 }}>
                  Entrez votre adresse email ESITH. Vous recevrez un lien pour créer un nouveau mot de passe.
                </p>
                <InputField
                  label="Email ESITH"
                  type="email"
                  placeholder="prenom.nom@esith.net"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleForgotPassword()}
                />
                {error && <ErrorBox msg={error} />}
                <button onClick={handleForgotPassword} disabled={forgotLoading} style={btnStyle(forgotLoading)}>
                  {forgotLoading ? "Envoi..." : "Envoyer le lien →"}
                </button>
              </>
            ) : (
              <div style={{ backgroundColor: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: "14px 16px", marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: "#166534", fontWeight: 600, marginBottom: 6 }}>
                  Email envoyé
                </div>
                <div style={{ fontSize: 12, color: "#15803d", lineHeight: 1.6 }}>
                  Si cet email existe dans notre système, un lien de réinitialisation a été envoyé.
                  Vérifiez votre boîte mail (et le dossier spam).
                </div>
              </div>
            )}
            <div style={{ textAlign: "center", marginTop: 12 }}>
              <span
                onClick={() => { setForgotMode(false); setForgotSent(false); setError(""); }}
                style={{ fontSize: 12, color: "#64748b", cursor: "pointer", textDecoration: "underline" }}
              >
                ← Retour à la connexion
              </span>
            </div>
          </>
        )}

        {role === "etudiant" && step === "2b" && (
          <>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#1a2a4a", marginBottom: 4 }}>
              Première connexion — créez votre mot de passe
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 16 }}>{email}</div>
            <InputField
              label="Nouveau mot de passe"
              type={showPassword ? "text" : "password"}
              placeholder="Minimum 8 caractères"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              rightEl={
                <span
                  onClick={() => setShowPassword((v) => !v)}
                  style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8" }}
                >
                  {showPassword ? "👁" : "🙈"}
                </span>
              }
            />
            <PasswordStrength password={password} />
            <div style={{ marginTop: 14 }}>
              <InputField
                label="Confirmer le mot de passe"
                type={showConfirm ? "text" : "password"}
                placeholder="Répéter le mot de passe"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRegister()}
                rightEl={
                  <span
                    onClick={() => setShowConfirm((v) => !v)}
                    style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8" }}
                  >
                    {showConfirm ? "👁" : "🙈"}
                  </span>
                }
              />
            </div>
            {error && <ErrorBox msg={error} />}
            <button onClick={handleRegister} disabled={loading} style={btnStyle(loading)}>
              {loading ? "Création..." : "Créer mon mot de passe →"}
            </button>
            <BackLink onClick={() => { setStep(1); setError(""); setPassword(""); setConfirmPassword(""); }} />
          </>
        )}

        {role === "etudiant" && step === "2c" && (
          <>
            <ErrorBox msg="Cet email n'est pas reconnu dans le système ESITH" />
            <BackLink onClick={() => { setStep(1); setError(""); }} />
          </>
        )}

        {/* ---- ADMINISTRATION ---- */}
        {role === "administration" && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#1a2a4a", marginBottom: 12 }}>
              Accès Administration
            </div>
            <InputField
              label="Mot de passe"
              type={showAdminPassword ? "text" : "password"}
              placeholder="Mot de passe administration"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdminLogin()}
              rightEl={
                <span
                  onClick={() => setShowAdminPassword((v) => !v)}
                  style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8" }}
                >
                  {showAdminPassword ? "👁" : "🙈"}
                </span>
              }
            />
            {error && <ErrorBox msg={error} />}
            <button onClick={handleAdminLogin} disabled={loading} style={btnStyle(loading)}>
              {loading ? "Vérification..." : "Accéder →"}
            </button>
          </div>
        )}

        {/* ---- PROFESSEUR ---- */}
        {role === "professeur" && (
          <div style={{ marginBottom: 16 }}>
            <InputField
              label="Email"
              type="email"
              placeholder="prenom.nom@esith.net"
              value={profEmail}
              onChange={(e) => setProfEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleProfesseur()}
            />
            <InputField
              label="Mot de passe"
              type={showProfPassword ? "text" : "password"}
              placeholder="Votre mot de passe"
              value={profPassword}
              onChange={(e) => setProfPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleProfesseur()}
              rightEl={
                <span
                  onClick={() => setShowProfPassword((v) => !v)}
                  style={{ fontSize: 16, cursor: "pointer", color: "#94a3b8" }}
                >
                  {showProfPassword ? "👁" : "🙈"}
                </span>
              }
            />
            <div style={{ textAlign: "right", marginTop: -6, marginBottom: 14 }}>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                Mot de passe oublié ? Contactez l'administration.
              </span>
            </div>
            {error && <ErrorBox msg={error} />}
            <button onClick={handleProfesseur} disabled={loading} style={btnStyle(loading)}>
              {loading ? "Connexion…" : "Se connecter →"}
            </button>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 24, fontSize: 11, color: "#94a3b8" }}>
          ESITH Casablanca
        </div>
      </div>
    </div>
  );
}

function ErrorBox({ msg }) {
  return (
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
      {msg}
    </div>
  );
}

function BackLink({ onClick }) {
  return (
    <div style={{ textAlign: "center", marginTop: 12 }}>
      <span
        onClick={onClick}
        style={{ fontSize: 12, color: "#64748b", cursor: "pointer", textDecoration: "underline" }}
      >
        ← Changer d'email
      </span>
    </div>
  );
}
