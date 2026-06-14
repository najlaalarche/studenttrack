import { useState } from "react";
import Login from "./components/Login.jsx";
import DashboardEtudiant from "./pages/etudiant/DashboardEtudiant.jsx";
import DashboardProfesseur from "./pages/professeur/DashboardProfesseur.jsx";
import DashboardAdmin from "./pages/admin/DashboardAdmin.jsx";

export default function App() {
  const [session, setSession] = useState(null); // { role, data }

  function handleLogin(role, data) {
    setSession({ role, data });
  }

  function handleLogout() {
    setSession(null);
  }

  if (!session) return <Login onLogin={handleLogin} />;

  if (session.role === "etudiant") {
    return <DashboardEtudiant email={session.data.email} onLogout={handleLogout} />;
  }

  if (session.role === "professeur") {
    return <DashboardProfesseur module={session.data.module} semestre={session.data.semestre || "Tous"} filiere={session.data.filiere || ""} onLogout={handleLogout} />;
  }

  if (session.role === "administration") {
    return <DashboardAdmin onLogout={handleLogout} />;
  }

  return <Login onLogin={handleLogin} />;
}
