import { useEffect, useState } from "react";
import { getEtudiants, getEtudiant } from "../../api.js";
import KpiCard from "../../components/KpiCard.jsx";
import ModuleBar from "../../components/ModuleBar.jsx";
import StatutBadge from "../../components/StatutBadge.jsx";

const S = {
  page:    { minHeight: "100vh", backgroundColor: "#F0F4F8", padding: "40px 32px", maxWidth: 900, margin: "0 auto" },
  card:    { backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 24px", marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  label:   { fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b" },
  section: { fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 16 },
  th:      { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td:      { padding: "11px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

function Spinner() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#F0F4F8" }}>
      <div style={{ width: 28, height: 28, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

export default function DashboardEtudiant({ email, onLogout }) {
  const [profil, setProfil]     = useState(null);
  const [absences, setAbsences] = useState([]);
  const [notes, setNotes]       = useState([]);
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [tab, setTab]           = useState("modules");

  useEffect(() => {
    async function load() {
      try {
        const liste = await getEtudiants();
        if (liste.erreur) throw new Error();
        const found = liste.find(e => e.email === email);
        if (!found) { setError("Aucun étudiant trouvé avec cet email."); return; }
        const detail = await getEtudiant(found.id_etudiant);
        setProfil(detail.profil);
        setAbsences(detail.absences ?? []);
        setNotes(detail.notes ?? []);
      } catch {
        setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050.");
      } finally { setLoading(false); }
    }
    load();
  }, [email]);

  if (loading) return <Spinner />;

  if (error) return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, backgroundColor: "#F0F4F8" }}>
      <p style={{ fontSize: 13, color: "#dc2626", textAlign: "center", maxWidth: 400 }}>{error}</p>
      <button onClick={onLogout} style={{ fontSize: 12, padding: "8px 16px", borderRadius: 6, backgroundColor: "#FFFFFF", color: "#64748b", border: "1px solid #E2E8F0", cursor: "pointer" }}>Retour</button>
    </div>
  );

  const globalStatut = profil.nb_modules_exclu > 0 ? "EXCLU" : profil.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 28px", marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <img src="/logo-esith.png" alt="ESITH" style={{ height: 36, objectFit: "contain" }} onError={e => e.target.style.display = "none"} />
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>{profil.prenom} {profil.nom}</h1>
            <StatutBadge statut={globalStatut} />
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>{profil.email}</div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>{profil.filiere} · {profil.annee}</div>
        </div>
        <button onClick={onLogout} style={{ fontSize: 12, padding: "6px 12px", borderRadius: 6, backgroundColor: "#F8FAFC", color: "#64748b", border: "1px solid #E2E8F0", cursor: "pointer" }}>
          Déconnexion
        </button>
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        <KpiCard label="Absences NJ"     value={profil.total_abs_nj}      color="#d97706" icon="⚠" />
        <KpiCard label="Abs. justifiées" value={profil.total_abs_just}    color="#8DC63F" icon="✓" />
        <KpiCard label="Score risque"    value={`${profil.score_global}/100`} color={profil.score_global >= 70 ? "#dc2626" : profil.score_global >= 40 ? "#d97706" : "#5a9e14"} icon="◎" />
        <KpiCard label="Moyenne"         value={profil.moyenne_generale ? profil.moyenne_generale.toFixed(2) : "—"} color="#1a3a6b" icon="◐" />
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
          {profil.modules.map(m => (
            <div key={m.module} style={S.card}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{m.module}</span>
                <StatutBadge statut={m.statut_exam} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <ModuleBar taux_nj={m.taux_nj} taux_total={m.taux_total} />
              </div>
              <div style={{ display: "flex", gap: 24, fontSize: 12 }}>
                <span style={{ color: "#64748b" }}>Séances NJ : <strong style={{ color: "#d97706" }}>{m.nb_abs_nj}/{m.total_seances} ({m.taux_nj.toFixed(1)}%)</strong></span>
                <span style={{ color: "#64748b" }}>Total : <strong style={{ color: "#dc2626" }}>{m.taux_total.toFixed(1)}%</strong></span>
              </div>
              {m.alerte_module && (
                <div style={{ marginTop: 10, padding: "6px 10px", borderRadius: 4, backgroundColor: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", fontSize: 12, color: "#d97706" }}>
                  {m.alerte_module}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab Historique */}
      {tab === "historique" && (
        <div style={{ ...S.card, padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["Date", "Module", "Durée", "Justifiée", "Motif"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {absences.length === 0
                ? <tr><td colSpan={5} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucune absence</td></tr>
                : absences.map((a, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                    <td style={{ ...S.td, fontWeight: 500 }}>{a.date_absence ?? "—"}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{a.module}</td>
                    <td style={{ ...S.td, color: "#d97706" }}>{a.duree_heures}h</td>
                    <td style={S.td}><span style={{ color: a.justifiee ? "#5a9e14" : "#dc2626", fontWeight: 500 }}>{a.justifiee ? "Oui" : "Non"}</span></td>
                    <td style={{ ...S.td, color: "#64748b" }}>{a.motif || "—"}</td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {/* Tab Notes */}
      {tab === "notes" && (
        <div style={{ ...S.card, padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["Module", "CC", "Examen", "Finale", "Mention", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {notes.length === 0
                ? <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucune note</td></tr>
                : notes.map((n, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                    <td style={{ ...S.td, fontWeight: 600 }}>{n.Module ?? n.module}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{n.Note_CC != null ? Number(n.Note_CC).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{n.Note_Examen != null ? Number(n.Note_Examen).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, fontWeight: 700, color: Number(n.Note_Finale) >= 10 ? "#5a9e14" : "#dc2626" }}>
                      {n.Note_Finale != null ? Number(n.Note_Finale).toFixed(1) : "—"}
                    </td>
                    <td style={{ ...S.td, color: "#64748b" }}>{n.Mention || "—"}</td>
                    <td style={S.td}><span style={{ color: n.Statut === "Admis" ? "#5a9e14" : "#dc2626", fontSize: 12, fontWeight: 500 }}>{n.Statut || "—"}</span></td>
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
