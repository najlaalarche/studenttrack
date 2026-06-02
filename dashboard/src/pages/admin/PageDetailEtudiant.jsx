import { useEffect, useState } from "react";
import { getEtudiant } from "../../api.js";
import KpiCard from "../../components/KpiCard.jsx";
import ModuleBar from "../../components/ModuleBar.jsx";
import StatutBadge from "../../components/StatutBadge.jsx";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine, Legend,
} from "recharts";

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

function RiskRadar({ profil }) {
  const mods  = profil.modules || [];
  const maxNj = mods.length > 0 ? Math.max(...mods.map(m => m.taux_nj)) : 0;
  const color = maxNj >= 50 ? "#EF4444" : maxNj >= 20 ? "#F59E0B" : "#8DC63F";
  const data  = mods.map(m => ({
    subject: m.module.length > 16 ? m.module.substring(0, 16) + "…" : m.module,
    value:  parseFloat(m.taux_nj.toFixed(1)),
    seuil:  20,
  }));
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "16px 16px 8px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", height: "100%" }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#1a3a6b", marginBottom: 4 }}>Absences NJ par module</div>
      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data} margin={{ top: 15, right: 30, bottom: 15, left: 30 }}>
          <PolarGrid stroke="#E2E8F0" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 10 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 9 }} tickCount={6} />
          <Radar name="Seuil 20%" dataKey="seuil" stroke="#F59E0B" fill="none" strokeDasharray="4 4" strokeWidth={1.5} />
          <Radar name="Abs NJ %" dataKey="value" stroke={color} fill={color} fillOpacity={0.3} strokeWidth={2} />
          <Tooltip formatter={(v, name) => name === "Seuil 20%" ? [null, null] : [`${v}%`, "Abs NJ"]} contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ModulesBarChart({ modules }) {
  const data = modules.map(m => ({
    name: m.module.length > 14 ? m.module.substring(0, 14) + "…" : m.module,
    "Abs NJ":    parseFloat(m.taux_nj.toFixed(1)),
    "Abs Total": parseFloat(m.taux_total.toFixed(1)),
  }));
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 20px 12px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b", marginBottom: 12 }}>Taux d'absence par module</div>
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} domain={[0, 100]} unit="%" />
          <Tooltip formatter={(v) => `${v}%`} contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" }} />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
          <ReferenceLine y={20} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: "20%", fill: "#d97706", fontSize: 10, position: "right" }} />
          <ReferenceLine y={50} stroke="#EF4444" strokeDasharray="4 4" label={{ value: "50%", fill: "#dc2626", fontSize: 10, position: "right" }} />
          <Bar dataKey="Abs NJ"    fill="#F59E0B" radius={[3, 3, 0, 0]} maxBarSize={24} />
          <Bar dataKey="Abs Total" fill="#EF4444" radius={[3, 3, 0, 0]} maxBarSize={24} />
        </BarChart>
      </ResponsiveContainer>
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

      {/* KPIs + Radar */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24, alignItems: "stretch" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, flex: 1 }}>
          <KpiCard label="Abs. NJ"        value={p.total_abs_nj}       color="#d97706" icon="⚠" />
          <KpiCard label="Abs. just."     value={p.total_abs_just}     color="#8DC63F" icon="✓" />
          <KpiCard label="Score risque"   value={`${p.score_global}/100`} color={scoreColor} icon="◎" />
          <KpiCard label="Moyenne"        value={p.moyenne_generale ? Number(p.moyenne_generale).toFixed(2) : "—"} color="#1a3a6b" icon="◐" />
          <KpiCard label="Total absences" value={p.total_absences}     color="#64748b" icon="≡" />
        </div>
        <div style={{ width: 280, flexShrink: 0 }}>
          <RiskRadar profil={p} />
        </div>
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
        <div>
          {(p.modules ?? []).length > 0 && <ModulesBarChart modules={p.modules} />}
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
