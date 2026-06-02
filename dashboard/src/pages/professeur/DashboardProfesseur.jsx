import { useEffect, useState } from "react";
import { getEtudiants } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

const STATUTS = ["Tous", "AUTORISE", "AVERTI", "EXCLU"];

const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748B", textAlign: "left", borderBottom: "1px solid #1E1E2E" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #1E1E2E" },
};

function Spinner() {
  return <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#0A0A0F" }}>
    <div style={{ width: 28, height: 28, border: "2px solid #1E1E2E", borderTop: "2px solid #6366F1", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
  </div>;
}

export default function DashboardProfesseur({ module: moduleProp, onLogout }) {
  const [rows, setRows]     = useState([]);
  const [filtre, setFiltre] = useState("Tous");
  const [error, setError]   = useState(null);
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
    <div style={{ minHeight: "100vh", backgroundColor: "#0A0A0F", padding: "40px 32px", maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366F1", marginBottom: 4 }}>Module</div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#F8FAFC", margin: 0 }}>{moduleProp}</h1>
          <p style={{ fontSize: 13, color: "#64748B", margin: "4px 0 0" }}>{rows.length} étudiant(s)</p>
        </div>
        <button onClick={onLogout} style={{ fontSize: 12, padding: "6px 12px", borderRadius: 6, backgroundColor: "#16161F", color: "#64748B", border: "1px solid #1E1E2E", cursor: "pointer" }}>
          Déconnexion
        </button>
      </div>

      {error && <p style={{ color: "#EF4444", fontSize: 13, marginBottom: 20 }}>{error}</p>}

      {/* Résumé */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Autorisés", count: counts.AUTORISE, color: "#22C55E" },
          { label: "Avertis",   count: counts.AVERTI,   color: "#F97316" },
          { label: "Exclus",    count: counts.EXCLU,    color: "#EF4444" },
        ].map(s => (
          <div key={s.label} style={{ backgroundColor: "#16161F", border: "1px solid #1E1E2E", borderRadius: 8, padding: "16px 20px", textAlign: "center" }}>
            <div style={{ fontSize: 26, fontWeight: 700, color: s.color }}>{s.count}</div>
            <div style={{ fontSize: 11, color: "#64748B", marginTop: 4, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.07em" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filtres */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {STATUTS.map(s => (
          <button key={s} onClick={() => setFiltre(s)} style={{
            padding: "6px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
            backgroundColor: filtre === s ? "#6366F1" : "#16161F",
            color: filtre === s ? "#fff" : "#64748B",
            border: `1px solid ${filtre === s ? "#6366F1" : "#1E1E2E"}`,
          }}>{s}</button>
        ))}
        <span style={{ fontSize: 12, color: "#64748B", alignSelf: "center", marginLeft: 8 }}>{displayed.length} résultat(s)</span>
      </div>

      {/* Tableau */}
      <div style={{ backgroundColor: "#16161F", border: "1px solid #1E1E2E", borderRadius: 8, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ backgroundColor: "#111118" }}>
            <tr>{["Nom", "Filière", "Séances NJ", "Taux NJ", "Taux Total", "Statut", "Dernière absence"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {displayed.length === 0
              ? <tr><td colSpan={7} style={{ ...S.td, textAlign: "center", color: "#64748B" }}>Aucun étudiant</td></tr>
              : displayed.map(({ etudiant: e, modInfo: m }, i) => (
                <tr key={e.id_etudiant} style={{ backgroundColor: i % 2 ? "transparent" : "#111118" }}>
                  <td style={{ ...S.td }}>
                    <div style={{ fontWeight: 500, color: "#F8FAFC" }}>{e.prenom} {e.nom}</div>
                    <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{e.email}</div>
                  </td>
                  <td style={{ ...S.td, color: "#94A3B8", fontSize: 12 }}>{e.annee}</td>
                  <td style={{ ...S.td, color: "#F97316", fontWeight: 500 }}>{m.nb_abs_nj}/{m.total_seances}</td>
                  <td style={{ ...S.td, color: "#F97316" }}>{m.taux_nj.toFixed(1)}%</td>
                  <td style={{ ...S.td, color: "#EF4444" }}>{m.taux_total.toFixed(1)}%</td>
                  <td style={S.td}><StatutBadge statut={m.statut_exam} /></td>
                  <td style={{ ...S.td, color: "#64748B", fontSize: 12 }}>{e.derniere_absence || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
