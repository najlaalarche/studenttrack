import { useState } from "react";
import { getModules, getModuleClasses, authCheckEmail, authRegister, authLogin } from "../api";

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

  // Professeur state
  const [nom, setNom] = useState("");
  const [module, setModule] = useState("");
  const [filiere, setFiliere] = useState("");
  const [modules, setModules] = useState([]);
  const [filieresForModule, setFilieresForModule] = useState([]);
  const [loadingModules, setLoadingModules] = useState(false);
  const [loadingClasses, setLoadingClasses] = useState(false);

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
    setFilieresForModule([]);
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

  const handleModuleChange = async (selectedModule) => {
    setModule(selectedModule);
    setFiliere("");
    setFilieresForModule([]);
    if (!selectedModule) return;
    setLoadingClasses(true);
    try {
      const data = await getModuleClasses(selectedModule);
      setFilieresForModule(data.filieres || []);
    } catch {
      setFilieresForModule([]);
    }
    setLoadingClasses(false);
  };

  const handleProfesseur = () => {
    if (!nom.trim() || !module) {
      setError("Veuillez renseigner votre nom et sélectionner un module");
      return;
    }
    onLogin("professeur", { nom, module, filiere });
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

        {role === "etudiant" && step === "2a" && (
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
                onClick={() => setError("Contactez l'administration pour réinitialiser votre mot de passe.")}
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

        {/* ---- PROFESSEUR ---- */}
        {role === "professeur" && (
          <div style={{ marginBottom: 16 }}>
            <InputField
              label="Votre nom"
              type="text"
              placeholder="Nom et prénom"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
            />
            <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
              Module
            </label>
            {loadingModules ? (
              <div style={{ fontSize: 12, color: "#94a3b8" }}>Chargement des modules...</div>
            ) : (
              <select
                value={module}
                onChange={(e) => handleModuleChange(e.target.value)}
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
                  marginBottom: 14,
                }}
              >
                <option value="">Sélectionner un module</option>
                {modules.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            )}

            {module && (
              <>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
                  Filière <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optionnel)</span>
                </label>
                {loadingClasses ? (
                  <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 14 }}>Chargement des filières...</div>
                ) : (
                  <select
                    value={filiere}
                    onChange={(e) => setFiliere(e.target.value)}
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
                      marginBottom: 14,
                    }}
                  >
                    <option value="">Toutes les filières</option>
                    {filieresForModule.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                )}
              </>
            )}

            {error && <div style={{ marginTop: 4 }}><ErrorBox msg={error} /></div>}
            <div style={{ marginTop: 8 }}>
              <button
                onClick={handleProfesseur}
                style={btnStyle(false)}
                onMouseEnter={(e) => (e.target.style.background = GREEN_DARK)}
                onMouseLeave={(e) => (e.target.style.background = GREEN)}
              >
                Se connecter →
              </button>
            </div>
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
