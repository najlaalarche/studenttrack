import { useState } from "react";
import Login from "./components/Login.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import DashboardEtudiant from "./pages/etudiant/DashboardEtudiant.jsx";
import DashboardProfesseur from "./pages/professeur/DashboardProfesseur.jsx";
import DashboardAdmin from "./pages/admin/DashboardAdmin.jsx";

const SESSION_KEY = "studenttrack_session";

function readStoredSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.role) return parsed;
  } catch {
    localStorage.removeItem(SESSION_KEY);
  }
  return null;
}

function writeSession(role, data, page_admin) {
  const payload = { role, data };
  if (role === "administration") payload.page_admin = page_admin || "overview";
  localStorage.setItem(SESSION_KEY, JSON.stringify(payload));
}

// Détection route /reset-password?token=xxx (sans react-router)
function getResetToken() {
  if (window.location.pathname === "/reset-password") {
    return new URLSearchParams(window.location.search).get("token") || "";
  }
  return null;
}

export default function App() {
  const resetToken = getResetToken(); // null = pas sur cette route, "" = route sans token

  const stored = readStoredSession();
  const [session, setSession]   = useState(stored ? { role: stored.role, data: stored.data || {} } : null);
  const [adminPage, setAdminPage] = useState(stored?.page_admin || "overview");

  function handleLogin(role, data) {
    setSession({ role, data });
    setAdminPage("overview");
    writeSession(role, data, "overview");
  }

  function handleLogout() {
    setSession(null);
    localStorage.removeItem(SESSION_KEY);
  }

  function handleAdminPageChange(page) {
    setAdminPage(page);
    writeSession("administration", {}, page);
  }

  function goToLogin() {
    // Nettoyer l'URL et revenir à la page de connexion
    window.history.replaceState(null, "", "/");
    window.location.reload();
  }

  // Route /reset-password
  if (resetToken !== null) {
    return <ResetPassword token={resetToken} onBackToLogin={goToLogin} />;
  }

  if (!session) return <Login onLogin={handleLogin} />;

  if (session.role === "etudiant") {
    return <DashboardEtudiant email={session.data.email} onLogout={handleLogout} />;
  }

  if (session.role === "professeur") {
    return (
      <DashboardProfesseur
        professeur={session.data}
        onLogout={handleLogout}
      />
    );
  }

  if (session.role === "administration") {
    return (
      <DashboardAdmin
        onLogout={handleLogout}
        initialPage={adminPage}
        onPageChange={handleAdminPageChange}
      />
    );
  }

  return <Login onLogin={handleLogin} />;
}
