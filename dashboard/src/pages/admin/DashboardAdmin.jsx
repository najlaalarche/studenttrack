import { useEffect, useState } from "react";
import { getStats, getEtudiants, postSync } from "../../api.js";
import Sidebar from "../../components/Sidebar.jsx";
import KpiCard from "../../components/KpiCard.jsx";
import PageEtudiants from "./PageEtudiants.jsx";
import PageAlertes from "./PageAlertes.jsx";
import PageDetailEtudiant from "./PageDetailEtudiant.jsx";
import PageImportation from "./PageImportation.jsx";
import PageGestionEtudiants from "./PageGestionEtudiants.jsx";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from "recharts";

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

const CHART_CARD = { backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 20px 12px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const CHART_TITLE = { fontSize: 13, fontWeight: 700, color: "#1a3a6b", marginBottom: 16 };

function VueEnsemble() {
  const [stats, setStats]         = useState(null);
  const [etudiants, setEtudiants] = useState([]);
  const [error, setError]         = useState(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([getStats(), getEtudiants()])
      .then(([s, e]) => {
        if (s.erreur) throw new Error();
        setStats(s);
        setEtudiants(Array.isArray(e) ? e : []);
      })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626" }}>{error}</p>;

  const top10 = [...etudiants]
    .sort((a, b) => b.score_risque - a.score_risque)
    .slice(0, 10)
    .map(e => ({
      name: `${e.prenom} ${e.nom}`.length > 18 ? `${e.prenom} ${e.nom}`.substring(0, 18) + "…" : `${e.prenom} ${e.nom}`,
      score: e.score_risque,
      color: e.score_risque >= 70 ? "#EF4444" : e.score_risque >= 40 ? "#F59E0B" : "#8DC63F",
    }));

  const pieData = [
    { name: "Faible",   value: stats.faible,   color: "#8DC63F" },
    { name: "Modéré",  value: stats.modere,   color: "#F59E0B" },
    { name: "Critique", value: stats.critique, color: "#EF4444" },
  ].filter(d => d.value > 0);

  const total = stats.faible + stats.modere + stats.critique;
  const renderLabel = ({ name, value }) => `${name} (${value} — ${total > 0 ? Math.round(value / total * 100) : 0}%)`;

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 24 }}>Vue d'ensemble</h2>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
        <KpiCard label="Total étudiants"  value={stats.total_etudiants} color="#1a3a6b" icon="⊞" />
        <KpiCard label="En alerte"        value={stats.total_alertes}   color="#F59E0B" icon="◉" />
        <KpiCard label="Niveau critique"  value={stats.critique}        color="#EF4444" icon="▲" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
        <KpiCard label="Niveau modéré"   value={stats.modere}          color="#F59E0B" icon="◐" />
        <KpiCard label="Niveau faible"   value={stats.faible}          color="#8DC63F" icon="◯" />
        <KpiCard label="Total abs. NJ"   value={stats.total_abs_nj}    color="#64748b" icon="≡" />
      </div>

      {/* Graphiques */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Bar chart Top 10 */}
        <div style={CHART_CARD}>
          <div style={CHART_TITLE}>Top étudiants à risque</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={top10} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} unit="" />
              <YAxis type="category" dataKey="name" width={130} tick={{ fill: "#1e293b", fontSize: 11 }} />
              <Tooltip formatter={(v) => [`${v}/100`, "Score risque"]} contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" }} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {top10.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart répartition */}
        <div style={CHART_CARD}>
          <div style={CHART_TITLE}>Répartition des risques</div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="45%"
                outerRadius={90}
                dataKey="value"
                label={renderLabel}
                labelLine={true}
              >
                {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v) => [`${v} étudiant(s)`, ""]} contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" }} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

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
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 24 }}>Synchronisation</h2>
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "24px", maxWidth: 440, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <p style={{ fontSize: 13, color: "#64748b", marginBottom: 20, lineHeight: 1.6 }}>
          Relit le dataset Konosys (dataset.xlsx) et détecte les nouvelles lignes d'absences.
        </p>
        <button
          onClick={handleSync}
          disabled={loading}
          style={{
            padding: "9px 18px", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: "pointer",
            backgroundColor: loading ? "#E2E8F0" : "#1a3a6b",
            color: loading ? "#64748b" : "#fff",
            border: "none",
          }}
        >
          {loading ? "Synchronisation en cours…" : "↻ Lancer la synchronisation"}
        </button>
        {error  && <p style={{ fontSize: 12, color: "#dc2626", marginTop: 12 }}>{error}</p>}
        {result && <div style={{ marginTop: 14, fontSize: 13, color: "#5a9e14" }}>✓ {result.nouvelles_lignes} nouvelle(s) ligne(s){!result.changed && " — aucun changement"}.</div>}
      </div>
    </div>
  );
}

export default function DashboardAdmin({ onLogout, initialPage = "overview", onPageChange }) {
  const [page, setPage]         = useState(initialPage);
  const [selected, setSelected] = useState(null);

  function handleNav(key) {
    setPage(key);
    setSelected(null);
    onPageChange?.(key);
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#FFFFFF" }}>
      <Sidebar active={selected ? "etudiants" : page} onNav={handleNav} onLogout={onLogout} userName="Administration" />
      <main style={{ marginLeft: 220, padding: "40px 36px", minHeight: "100vh" }}>
        {page === "overview"          && !selected && <VueEnsemble />}
        {page === "etudiants"         && !selected && <PageEtudiants onSelectEtudiant={id => setSelected(id)} />}
        {page === "alertes"           && !selected && <PageAlertes />}
        {page === "importation"       && !selected && <PageImportation />}
        {page === "gestion-etudiants" && !selected && <PageGestionEtudiants />}
        {page === "sync"              && !selected && <PageSync />}
        {selected && <PageDetailEtudiant id_etudiant={selected} onBack={() => { setSelected(null); setPage("etudiants"); }} />}
      </main>
    </div>
  );
}
