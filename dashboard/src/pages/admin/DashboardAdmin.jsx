import { useEffect, useState } from "react";
import { getStats, postSync } from "../../api.js";
import Sidebar from "../../components/Sidebar.jsx";
import KpiCard from "../../components/KpiCard.jsx";
import PageEtudiants from "./PageEtudiants.jsx";
import PageAlertes from "./PageAlertes.jsx";
import PageDetailEtudiant from "./PageDetailEtudiant.jsx";

function Spinner() {
  return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
    <div style={{ width: 24, height: 24, border: "2px solid #1E1E2E", borderTop: "2px solid #6366F1", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
  </div>;
}

function VueEnsemble() {
  const [stats, setStats]   = useState(null);
  const [error, setError]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(d => { if (d.erreur) throw new Error(); setStats(d); })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#EF4444" }}>{error}</p>;

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#F8FAFC", marginBottom: 24 }}>Vue d'ensemble</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
        <KpiCard label="Total étudiants"    value={stats.total_etudiants} color="#6366F1" icon="⊞" />
        <KpiCard label="En alerte"          value={stats.total_alertes}   color="#F97316" icon="◉" />
        <KpiCard label="Niveau critique"    value={stats.critique}        color="#EF4444" icon="▲" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        <KpiCard label="Niveau modéré"     value={stats.modere}          color="#F97316" icon="◐" />
        <KpiCard label="Niveau faible"     value={stats.faible}          color="#22C55E" icon="◯" />
        <KpiCard label="Total abs. NJ"     value={stats.total_abs_nj}    color="#94A3B8" icon="≡" />
      </div>
    </div>
  );
}

function PageSync() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  async function handleSync() {
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await postSync();
      if (data.erreur) throw new Error(data.erreur);
      setResult(data);
    } catch { setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#F8FAFC", marginBottom: 24 }}>Synchronisation</h2>
      <div style={{ backgroundColor: "#16161F", border: "1px solid #1E1E2E", borderRadius: 8, padding: "24px", maxWidth: 440 }}>
        <p style={{ fontSize: 13, color: "#64748B", marginBottom: 20, lineHeight: 1.6 }}>
          Relit le dataset Konosys (dataset.xlsx) et détecte les nouvelles lignes d'absences.
        </p>
        <button onClick={handleSync} disabled={loading} style={{
          padding: "9px 18px", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: "pointer",
          backgroundColor: loading ? "#1E1E2E" : "#6366F1", color: loading ? "#64748B" : "#fff", border: "none",
        }}>
          {loading ? "Synchronisation en cours…" : "↻ Lancer la synchronisation"}
        </button>
        {error && <p style={{ fontSize: 12, color: "#EF4444", marginTop: 12 }}>{error}</p>}
        {result && (
          <div style={{ marginTop: 14, fontSize: 13, color: "#22C55E" }}>
            ✓ {result.nouvelles_lignes} nouvelle(s) ligne(s){!result.changed && " — aucun changement"}.
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardAdmin({ onLogout }) {
  const [page, setPage]       = useState("overview");
  const [selected, setSelected] = useState(null);

  function handleNav(key) { setPage(key); setSelected(null); }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0A0A0F" }}>
      <Sidebar
        active={selected ? "etudiants" : page}
        onNav={handleNav}
        onLogout={onLogout}
        userName="Administration"
      />
      <main style={{ marginLeft: 220, padding: "40px 36px", minHeight: "100vh" }}>
        {page === "overview"  && !selected && <VueEnsemble />}
        {page === "etudiants" && !selected && <PageEtudiants onSelectEtudiant={id => setSelected(id)} />}
        {page === "alertes"   && !selected && <PageAlertes />}
        {page === "sync"      && !selected && <PageSync />}
        {selected && <PageDetailEtudiant id_etudiant={selected} onBack={() => { setSelected(null); setPage("etudiants"); }} />}
      </main>
    </div>
  );
}
