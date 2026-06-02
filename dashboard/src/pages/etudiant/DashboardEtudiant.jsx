import { useEffect, useState } from "react";
import { getEtudiants, getEtudiant } from "../../api.js";
import KpiCard from "../../components/KpiCard.jsx";
import ModuleBar from "../../components/ModuleBar.jsx";
import StatutBadge from "../../components/StatutBadge.jsx";

const S = {
  page:    { minHeight: "100vh", backgroundColor: "#0A0A0F", padding: "40px 32px", maxWidth: 900, margin: "0 auto" },
  card:    { backgroundColor: "#16161F", border: "1px solid #1E1E2E", borderRadius: 8, padding: "20px 24px", marginBottom: 12 },
  label:   { fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748B" },
  section: { fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748B", marginBottom: 16 },
  th:      { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748B", textAlign: "left", borderBottom: "1px solid #1E1E2E" },
  td:      { padding: "11px 16px", fontSize: 13, borderBottom: "1px solid #1E1E2E" },
};

function Spinner() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#0A0A0F" }}>
      <div style={{ width: 28, height: 28, border: "2px solid #1E1E2E", borderTop: "2px solid #6366F1", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
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
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, backgroundColor: "#0A0A0F" }}>
      <p style={{ fontSize: 13, color: "#EF4444", textAlign: "center", maxWidth: 400 }}>{error}</p>
      <button onClick={onLogout} style={{ fontSize: 12, padding: "8px 16px", borderRadius: 6, backgroundColor: "#16161F", color: "#94A3B8", border: "1px solid #1E1E2E", cursor: "pointer" }}>Retour</button>
    </div>
  );

  const globalStatut = profil.nb_modules_exclu > 0 ? "EXCLU" : profil.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#F8FAFC", margin: 0 }}>{profil.prenom} {profil.nom}</h1>
            <StatutBadge statut={globalStatut} />
          </div>
          <div style={{ fontSize: 13, color: "#94A3B8" }}>{profil.email}</div>
          <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>{profil.filiere} · {profil.annee}</div>
        </div>
        <button onClick={onLogout} style={{ fontSize: 12, padding: "6px 12px", borderRadius: 6, backgroundColor: "#16161F", color: "#64748B", border: "1px solid #1E1E2E", cursor: "pointer" }}>
          Déconnexion
        </button>
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 32 }}>
        <KpiCard label="Absences NJ"   value={profil.total_abs_nj}      color="#F97316" icon="⚠" />
        <KpiCard label="Abs. justifiées" value={profil.total_abs_just}  color="#22C55E" icon="✓" />
        <KpiCard label="Score risque"  value={`${profil.score_global}/100`} color={profil.score_global >= 70 ? "#EF4444" : profil.score_global >= 40 ? "#F97316" : "#22C55E"} icon="◎" />
        <KpiCard label="Moyenne"       value={profil.moyenne_generale ? profil.moyenne_generale.toFixed(2) : "—"} color="#6366F1" icon="◐" />
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20 }}>
        {["modules", "historique", "notes"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "7px 14px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
            backgroundColor: tab === t ? "#6366F1" : "#16161F",
            color: tab === t ? "#fff" : "#64748B",
            border: `1px solid ${tab === t ? "#6366F1" : "#1E1E2E"}`,
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
                <span style={{ fontSize: 14, fontWeight: 600, color: "#F8FAFC" }}>{m.module}</span>
                <StatutBadge statut={m.statut_exam} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <ModuleBar taux_nj={m.taux_nj} taux_total={m.taux_total} />
              </div>
              <div style={{ display: "flex", gap: 24, fontSize: 12 }}>
                <span style={{ color: "#64748B" }}>Séances NJ : <strong style={{ color: "#F97316" }}>{m.nb_abs_nj}/{m.total_seances} ({m.taux_nj.toFixed(1)}%)</strong></span>
                <span style={{ color: "#64748B" }}>Total : <strong style={{ color: "#EF4444" }}>{m.taux_total.toFixed(1)}%</strong></span>
              </div>
              {m.alerte_module && (
                <div style={{ marginTop: 10, padding: "6px 10px", borderRadius: 4, backgroundColor: "rgba(249,115,22,0.08)", border: "1px solid rgba(249,115,22,0.2)", fontSize: 12, color: "#F97316" }}>
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
            <thead style={{ backgroundColor: "#111118" }}>
              <tr>{["Date", "Module", "Durée", "Justifiée", "Motif"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {absences.length === 0
                ? <tr><td colSpan={5} style={{ ...S.td, textAlign: "center", color: "#64748B" }}>Aucune absence</td></tr>
                : absences.map((a, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 ? "transparent" : "#111118" }}>
                    <td style={{ ...S.td, color: "#F8FAFC" }}>{a.date_absence ?? "—"}</td>
                    <td style={{ ...S.td, color: "#94A3B8" }}>{a.module}</td>
                    <td style={{ ...S.td, color: "#F97316" }}>{a.duree_heures}h</td>
                    <td style={S.td}><span style={{ color: a.justifiee ? "#22C55E" : "#EF4444" }}>{a.justifiee ? "Oui" : "Non"}</span></td>
                    <td style={{ ...S.td, color: "#64748B" }}>{a.motif || "—"}</td>
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
            <thead style={{ backgroundColor: "#111118" }}>
              <tr>{["Module", "CC", "Examen", "Finale", "Mention", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {notes.length === 0
                ? <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#64748B" }}>Aucune note</td></tr>
                : notes.map((n, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 ? "transparent" : "#111118" }}>
                    <td style={{ ...S.td, color: "#F8FAFC" }}>{n.Module ?? n.module}</td>
                    <td style={{ ...S.td, color: "#94A3B8" }}>{n.Note_CC != null ? Number(n.Note_CC).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, color: "#94A3B8" }}>{n.Note_Examen != null ? Number(n.Note_Examen).toFixed(1) : "—"}</td>
                    <td style={{ ...S.td, fontWeight: 600, color: Number(n.Note_Finale) >= 10 ? "#22C55E" : "#EF4444" }}>
                      {n.Note_Finale != null ? Number(n.Note_Finale).toFixed(1) : "—"}
                    </td>
                    <td style={{ ...S.td, color: "#94A3B8" }}>{n.Mention || "—"}</td>
                    <td style={S.td}><span style={{ color: n.Statut === "Admis" ? "#22C55E" : "#EF4444", fontSize: 12 }}>{n.Statut || "—"}</span></td>
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
