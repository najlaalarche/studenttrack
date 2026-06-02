import { useEffect, useState } from "react";
import { getEtudiants } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

const STATUTS = ["Tous", "AUTORISE", "AVERTI", "EXCLU"];

const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

function Spinner() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#F0F4F8" }}>
      <div style={{ width: 28, height: 28, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

export default function DashboardProfesseur({ module: moduleProp, onLogout }) {
  const [rows, setRows]       = useState([]);
  const [filtre, setFiltre]   = useState("Tous");
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const liste = await getEtudiants();
        if (liste.erreur) throw new Error();
        const filtered = [];
        for (const etudiant of liste) {
          const modInfo = (etudiant.modules ?? []).find(m => m.module === moduleProp);
          if (modInfo) filtered.push({ etudiant, modInfo });
        }
        const ordre = { EXCLU: 0, AVERTI: 1, AUTORISE: 2 };
        filtered.sort((a, b) => (ordre[a.modInfo.statut_exam] ?? 3) - (ordre[b.modInfo.statut_exam] ?? 3));
        setRows(filtered);
      } catch { setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."); }
      finally { setLoading(false); }
    }
    load();
  }, [moduleProp]);

  const displayed = filtre === "Tous" ? rows : rows.filter(r => r.modInfo.statut_exam === filtre);
  const counts = { AUTORISE: 0, AVERTI: 0, EXCLU: 0 };
  rows.forEach(r => { counts[r.modInfo.statut_exam] = (counts[r.modInfo.statut_exam] ?? 0) + 1; });

  if (loading) return <Spinner />;

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F0F4F8", padding: "40px 32px", maxWidth: 1000, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <img src="/logo-esith.png" alt="ESITH" style={{ height: 40, objectFit: "contain" }} onError={e => e.target.style.display = "none"} />
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#8DC63F", marginBottom: 2 }}>Module</div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>{moduleProp}</h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: "2px 0 0" }}>{rows.length} étudiant(s)</p>
          </div>
        </div>
        <button onClick={onLogout} style={{ fontSize: 12, padding: "7px 14px", borderRadius: 6, backgroundColor: "#FFFFFF", color: "#64748b", border: "1px solid #E2E8F0", cursor: "pointer" }}>
          Déconnexion
        </button>
      </div>

      {error && <p style={{ color: "#dc2626", fontSize: 13, marginBottom: 20 }}>{error}</p>}

      {/* Résumé */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Autorisés", count: counts.AUTORISE, color: "#8DC63F", border: "#8DC63F" },
          { label: "Avertis",   count: counts.AVERTI,   color: "#d97706", border: "#F59E0B" },
          { label: "Exclus",    count: counts.EXCLU,    color: "#dc2626", border: "#EF4444" },
        ].map(s => (
          <div key={s.label} style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderLeft: `4px solid ${s.border}`, borderRadius: 8, padding: "16px 20px", textAlign: "center", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.count}</div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filtres */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {STATUTS.map(s => (
          <button key={s} onClick={() => setFiltre(s)} style={{
            padding: "6px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
            backgroundColor: filtre === s ? "#1a3a6b" : "#FFFFFF",
            color: filtre === s ? "#fff" : "#64748b",
            border: `1px solid ${filtre === s ? "#1a3a6b" : "#E2E8F0"}`,
          }}>{s}</button>
        ))}
        <span style={{ fontSize: 12, color: "#64748b", alignSelf: "center", marginLeft: 8 }}>{displayed.length} résultat(s)</span>
      </div>

      {/* Tableau */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "hidden", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>{["Nom", "Filière", "Séances NJ", "Taux NJ", "Taux Total", "Statut", "Dernière absence"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {displayed.length === 0
              ? <tr><td colSpan={7} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucun étudiant</td></tr>
              : displayed.map(({ etudiant: e, modInfo: m }, i) => (
                <tr key={e.id_etudiant} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                  <td style={S.td}>
                    <div style={{ fontWeight: 600, color: "#1e293b" }}>{e.prenom} {e.nom}</div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>{e.email}</div>
                  </td>
                  <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{e.annee}</td>
                  <td style={{ ...S.td, color: "#d97706", fontWeight: 600 }}>{m.nb_abs_nj}/{m.total_seances}</td>
                  <td style={{ ...S.td, color: "#d97706" }}>{m.taux_nj.toFixed(1)}%</td>
                  <td style={{ ...S.td, color: "#dc2626" }}>{m.taux_total.toFixed(1)}%</td>
                  <td style={S.td}><StatutBadge statut={m.statut_exam} /></td>
                  <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{e.derniere_absence || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
