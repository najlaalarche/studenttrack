import { useEffect, useState } from "react";
import { getEtudiant } from "../../api.js";
import KpiCard from "../../components/KpiCard.jsx";
import ModuleBar from "../../components/ModuleBar.jsx";
import StatutBadge from "../../components/StatutBadge.jsx";

const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

export default function PageDetailEtudiant({ id_etudiant, onBack }) {
  const [data, setData]       = useState(null);
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState("modules");

  useEffect(() => {
    getEtudiant(id_etudiant)
      .then(d => { if (d.erreur) throw new Error(d.erreur); setData(d); })
      .catch(e => setError(e.message || "Connexion au serveur impossible."))
      .finally(() => setLoading(false));
  }, [id_etudiant]);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626" }}>{error}</p>;

  const { profil: p, absences = [], notes = [] } = data;
  const globalStatut = p.nb_modules_exclu > 0 ? "EXCLU" : p.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";
  const scoreColor   = p.score_global >= 70 ? "#dc2626" : p.score_global >= 40 ? "#d97706" : "#5a9e14";

  return (
    <div>
      <button onClick={onBack} style={{ fontSize: 12, color: "#1a3a6b", background: "none", border: "none", cursor: "pointer", marginBottom: 20, display: "flex", alignItems: "center", gap: 6, padding: 0, fontWeight: 500 }}>
        ← Retour aux étudiants
      </button>

      {/* Header */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "24px 28px", marginBottom: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>{p.prenom} {p.nom}</h2>
            <StatutBadge statut={globalStatut} size="lg" />
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>{p.email}</div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>{p.filiere} · {p.annee} · {p.cursus}</div>
        </div>
        {p.niveau_risque_scoring && (
          <div style={{
            padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600,
            backgroundColor: p.niveau_risque_scoring === "ROUGE" ? "rgba(239,68,68,0.1)" : p.niveau_risque_scoring === "ORANGE" ? "rgba(245,158,11,0.1)" : "rgba(141,198,63,0.1)",
            color: p.niveau_risque_scoring === "ROUGE" ? "#dc2626" : p.niveau_risque_scoring === "ORANGE" ? "#d97706" : "#5a9e14",
            border: `1px solid ${p.niveau_risque_scoring === "ROUGE" ? "rgba(239,68,68,0.3)" : p.niveau_risque_scoring === "ORANGE" ? "rgba(245,158,11,0.3)" : "rgba(141,198,63,0.3)"}`,
          }}>
            {p.niveau_risque_scoring}
          </div>
        )}
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
        <KpiCard label="Abs. NJ"        value={p.total_abs_nj}       color="#d97706" icon="⚠" />
        <KpiCard label="Abs. just."     value={p.total_abs_just}     color="#8DC63F" icon="✓" />
        <KpiCard label="Score risque"   value={`${p.score_global}/100`} color={scoreColor} icon="◎" />
        <KpiCard label="Moyenne"        value={p.moyenne_generale ? Number(p.moyenne_generale).toFixed(2) : "—"} color="#1a3a6b" icon="◐" />
        <KpiCard label="Total absences" value={p.total_absences}     color="#64748b" icon="≡" />
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20 }}>
        {["modules", "historique", "notes"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "7px 14px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
            backgroundColor: tab === t ? "#1a3a6b" : "#FFFFFF",
            color: tab === t ? "#fff" : "#64748b",
            border: `1px solid ${tab === t ? "#1a3a6b" : "#E2E8F0"}`,
          }}>
            {t === "modules" ? "Modules" : t === "historique" ? "Historique" : "Notes"}
          </button>
        ))}
      </div>

      {/* Tab Modules */}
      {tab === "modules" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {(p.modules ?? []).map(m => (
            <div key={m.module} style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{m.module}</span>
                <StatutBadge statut={m.statut_exam} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <ModuleBar taux_nj={m.taux_nj} taux_total={m.taux_total} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, fontSize: 12 }}>
                <div><span style={{ color: "#64748b" }}>NJ : </span><strong style={{ color: "#d97706" }}>{m.nb_abs_nj}/{m.total_seances} ({m.taux_nj.toFixed(1)}%)</strong></div>
                <div><span style={{ color: "#64748b" }}>Total : </span><strong style={{ color: "#dc2626" }}>{m.taux_total.toFixed(1)}%</strong></div>
                <div><span style={{ color: "#64748b" }}>Seuil alerte : </span><strong style={{ color: "#d97706" }}>{m.seuil_alerte}%</strong></div>
                <div><span style={{ color: "#64748b" }}>Seuil exclu : </span><strong style={{ color: "#dc2626" }}>{m.seuil_exclusion}%</strong></div>
              </div>
              {m.alerte_module && (
                <div style={{ marginTop: 12, padding: "8px 12px", borderRadius: 4, backgroundColor: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", fontSize: 12, color: "#d97706" }}>
                  {m.alerte_module}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab Historique */}
      {tab === "historique" && (
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "auto", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr>{["Date", "Module", "Durée", "Justifiée", "Motif", "Séance"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {absences.length === 0
                ? <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucune absence</td></tr>
                : absences.map((a, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                    <td style={{ ...S.td, fontWeight: 500 }}>{a.date_absence ?? "—"}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{a.module}</td>
                    <td style={{ ...S.td, color: "#d97706" }}>{a.duree_heures}h</td>
                    <td style={S.td}><span style={{ color: a.justifiee ? "#5a9e14" : "#dc2626", fontWeight: 500 }}>{a.justifiee ? "Oui" : "Non"}</span></td>
                    <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{a.motif || "—"}</td>
                    <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{a.seance || "—"}</td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {/* Tab Notes */}
      {tab === "notes" && (
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "auto", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr>{["Module", "Semestre", "CC", "Examen", "Finale", "Mention", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {notes.length === 0
                ? <tr><td colSpan={7} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucune note</td></tr>
                : notes.map((n, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                    <td style={{ ...S.td, fontWeight: 600 }}>{n.Module}</td>
                    <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{n.Semestre}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{n.Note_CC != null ? Number(n.Note_CC).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{n.Note_Examen != null ? Number(n.Note_Examen).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, fontWeight: 700, color: Number(n.Note_Finale) >= 10 ? "#5a9e14" : "#dc2626" }}>
                      {n.Note_Finale != null ? Number(n.Note_Finale).toFixed(1) : "—"}
                    </td>
                    <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{n.Mention || "—"}</td>
                    <td style={S.td}><span style={{ color: n.Statut === "Admis" ? "#5a9e14" : "#dc2626", fontSize: 12, fontWeight: 600 }}>{n.Statut || "—"}</span></td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
