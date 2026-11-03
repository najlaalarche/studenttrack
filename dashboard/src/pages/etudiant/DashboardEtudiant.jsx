import { useEffect, useState } from "react";
import { LayoutDashboard, BookOpen, Clock, LogOut } from "lucide-react";
import { getEtudiant, getTauxAbsence, getPerformance } from "../../api.js";
import KpiCard from "../../components/KpiCard.jsx";
import ModuleBar from "../../components/ModuleBar.jsx";
import StatutBadge from "../../components/StatutBadge.jsx";
import TauxAbsenceChart from "../../components/TauxAbsenceChart.jsx";
import PerformanceTile from "../../components/PerformanceTile.jsx";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip,
} from "recharts";

const S = {
  main:  { marginLeft: 220, padding: "40px 36px", minHeight: "100vh", backgroundColor: "#FFFFFF" },
  inner: { maxWidth: 1280, margin: "0 auto" },  // = max-w-7xl
  titre: { fontSize: 18, fontWeight: 700, color: "#1a3a6b", margin: "0 0 24px" },
  card:  { backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 24px", marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  th:    { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td:    { padding: "11px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

function ModulesRadar({ profil }) {
  const mods   = profil.modules || [];
  const maxNj  = mods.length > 0 ? Math.max(...mods.map(m => m.taux_nj)) : 0;
  const color  = maxNj >= 50 ? "#EF4444" : maxNj >= 20 ? "#F59E0B" : "#8DC63F";
  const data   = mods.map(m => ({
    subject: m.module.length > 16 ? m.module.substring(0, 16) + "…" : m.module,
    value:  parseFloat(m.taux_nj.toFixed(1)),
    seuil:  20,
  }));
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "16px 16px 8px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", height: "100%" }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#1a3a6b", marginBottom: 4 }}>Absences NJ par module</div>
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={data} margin={{ top: 10, right: 24, bottom: 10, left: 24 }}>
          <PolarGrid stroke="#E2E8F0" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 9 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 9 }} tickCount={6} />
          <Radar name="Seuil 20%" dataKey="seuil" stroke="#F59E0B" fill="none" strokeDasharray="4 4" strokeWidth={1.5} />
          <Radar name="Abs NJ %" dataKey="value" stroke={color} fill={color} fillOpacity={0.3} strokeWidth={2} />
          <Tooltip formatter={(v, name) => name === "Seuil 20%" ? [null, null] : [`${v}%`, "Abs NJ"]} contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

const NAV = [
  { key: "overview",   Icon: LayoutDashboard, label: "Vue d'ensemble" },
  { key: "modules",    Icon: BookOpen,        label: "Modules" },
  { key: "historique", Icon: Clock,           label: "Historique" },
];

const SEMESTRES = [
  { id: "S1", label: "Semestre 1", dispo: true },
  { id: "S2", label: "Semestre 2", dispo: false },
];

// Même gabarit que la sidebar admin (components/Sidebar.jsx) : fixe, 220px, fond blanc
function SidebarEtudiant({ profil, vue, onNav, semestre, onSemestre, onLogout }) {
  return (
    <aside style={{
      position: "fixed", top: 0, left: 0, height: "100vh", width: 220,
      display: "flex", flexDirection: "column", padding: "20px 12px",
      backgroundColor: "#FFFFFF", borderRight: "1px solid #E2E8F0", zIndex: 20,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 16px" }}>
        <img src="/logo-esith.png" alt="ESITH" style={{ height: 32, width: 32, objectFit: "contain", flexShrink: 0 }} onError={e => { e.target.style.display = "none"; }} />
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#8DC63F", lineHeight: 1 }}>ESITH</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#1a3a6b", lineHeight: 1.2 }}>StudentTrack</div>
        </div>
      </div>

      <div style={{ padding: "0 10px 14px" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{profil.prenom} {profil.nom}</div>
        <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>{profil.filiere}{profil.annee ? ` · ${profil.annee}` : ""}</div>
      </div>

      <div style={{ height: 1, backgroundColor: "#E2E8F0", marginBottom: 12 }} />

      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ key, Icon, label }) => {
          const actif = vue === key;
          return (
            <button
              key={key}
              onClick={() => onNav(key)}
              aria-current={actif ? "page" : undefined}
              style={{
                display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 6,
                backgroundColor: actif ? "#eef2fb" : "transparent",
                color: actif ? "#1a3a6b" : "#64748b", fontWeight: actif ? 600 : 400, fontSize: 13,
                border: "none", cursor: "pointer", textAlign: "left", width: "100%",
                borderLeft: actif ? "3px solid #1a3a6b" : "3px solid transparent",
              }}
              onMouseEnter={e => { if (!actif) e.currentTarget.style.backgroundColor = "#f1f5f9"; }}
              onMouseLeave={e => { if (!actif) e.currentTarget.style.backgroundColor = "transparent"; }}
            >
              <Icon size={16} strokeWidth={actif ? 2.25 : 1.75} />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Sélecteur de semestre — seul S1 est disponible pour l'instant */}
      <div role="group" aria-label="Semestre" style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", padding: "0 4px" }}>Semestre</div>
        {SEMESTRES.map(({ id, label, dispo }) => {
          const actif = semestre === id;
          return (
            <button
              key={id}
              type="button"
              disabled={!dispo}
              aria-pressed={actif}
              onClick={() => dispo && onSemestre(id)}
              style={{
                padding: "9px 12px", borderRadius: 6, fontSize: 13, fontWeight: 600, textAlign: "left",
                backgroundColor: actif ? "#1e3a5f" : "#F1F5F9",
                color: actif ? "#FFFFFF" : "#94a3b8",
                border: `1px solid ${actif ? "#1e3a5f" : "#E2E8F0"}`,
                cursor: dispo ? "pointer" : "not-allowed",
              }}
            >
              {label}
              {!dispo && <div style={{ fontSize: 10, fontWeight: 500, marginTop: 2 }}>Pas encore entamé</div>}
            </button>
          );
        })}
      </div>

      <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: 12 }}>
        <button
          onClick={onLogout}
          style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 6, width: "100%", backgroundColor: "transparent", color: "#64748b", fontSize: 12, border: "none", cursor: "pointer" }}
          onMouseEnter={e => e.currentTarget.style.color = "#1a3a6b"}
          onMouseLeave={e => e.currentTarget.style.color = "#64748b"}
        >
          <LogOut size={14} /><span>Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}

// Légende affichée une fois au-dessus de la liste des modules
function LegendeModules() {
  const pastille  = c => ({ display: "inline-block", width: 12, height: 8, borderRadius: 99, background: c, marginRight: 6, verticalAlign: "middle" });
  const pointille = c => ({ display: "inline-block", width: 0, height: 12, borderLeft: `2px dashed ${c}`, marginRight: 6, verticalAlign: "middle" });
  return (
    <div style={{ ...S.card, display: "flex", flexWrap: "wrap", gap: "8px 24px", fontSize: 12, color: "#475569", padding: "12px 20px" }}>
      <span><span style={pastille("linear-gradient(90deg, #F59E0B, #FBBF24)")} />🟠 Orange = taux d'absences non justifiées (NJ)</span>
      <span><span style={pastille("linear-gradient(90deg, #EF4444, #F87171)")} />🔴 Rouge = taux d'absences total (NJ + justifiées) — longueur totale de la barre</span>
      <span><span style={pointille("#d97706")} />Seuil AVERTI : 20 % NJ</span>
      <span><span style={pointille("#dc2626")} />Seuil EXCLU : 50 % total</span>
    </div>
  );
}

// ModuleBar + lignes pointillées des seuils (sans modifier le composant partagé avec l'admin)
function BarreAvecSeuils({ m }) {
  const seuils = [
    { pct: m.seuil_alerte ?? 20,    label: "Seuil AVERTI", couleur: "#d97706" },
    { pct: m.seuil_exclusion ?? 50, label: "Seuil EXCLU",  couleur: "#dc2626" },
  ];
  return (
    <div style={{ position: "relative", paddingTop: 18 }}>
      {seuils.map(s => (
        <div key={s.label} aria-hidden="true">
          <span style={{ position: "absolute", top: 0, left: `${s.pct}%`, transform: "translateX(-50%)", fontSize: 10, fontWeight: 600, color: s.couleur, whiteSpace: "nowrap" }}>
            {s.label}
          </span>
          <div style={{ position: "absolute", top: 13, left: `${s.pct}%`, height: 18, borderLeft: `1.5px dashed ${s.couleur}`, zIndex: 3 }} />
        </div>
      ))}
      <ModuleBar taux_nj={m.taux_nj} taux_total={m.taux_total} />
    </div>
  );
}

function Spinner() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF" }}>
      <div style={{ width: 28, height: 28, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

export default function DashboardEtudiant({ idEtudiant, onLogout }) {
  const [profil, setProfil]     = useState(null);
  const [absences, setAbsences] = useState([]);
  const [semaines, setSemaines] = useState([]);
  const [perf, setPerf]         = useState(null);
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [vue, setVue]           = useState("overview");
  const [semestre, setSemestre] = useState("S1");

  useEffect(() => {
    async function load() {
      try {
        // id issu de la connexion ; l'API refuse (403) les données d'un autre étudiant
        const [detail, taux, performance] = await Promise.all([
          getEtudiant(idEtudiant),
          getTauxAbsence(idEtudiant).catch(() => []),
          getPerformance(idEtudiant).catch(() => null),
        ]);
        if (!detail.profil) { setError(detail.erreur || "Aucun étudiant trouvé pour ce compte."); return; }
        setProfil(detail.profil);
        setAbsences(detail.absences ?? []);
        setSemaines(Array.isArray(taux) ? taux : []);
        setPerf(performance);
      } catch {
        setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050.");
      } finally { setLoading(false); }
    }
    load();
  }, [idEtudiant]);

  if (loading) return <Spinner />;

  if (error) return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, backgroundColor: "#FFFFFF" }}>
      <p style={{ fontSize: 13, color: "#dc2626", textAlign: "center", maxWidth: 400 }}>{error}</p>
      <button onClick={onLogout} style={{ fontSize: 12, padding: "8px 16px", borderRadius: 6, backgroundColor: "#F8FAFC", color: "#64748b", border: "1px solid #E2E8F0", cursor: "pointer" }}>Retour</button>
    </div>
  );

  const presence     = semaines.length > 0 ? semaines[semaines.length - 1].taux_presence : null;
  const absence      = semaines.length > 0 ? semaines[semaines.length - 1].taux_absence : null;

  const titres = { overview: "Vue d'ensemble", modules: "Modules", historique: "Historique des absences" };

  return (
    <div>
      <SidebarEtudiant
        profil={profil}
        vue={vue}
        onNav={setVue}
        semestre={semestre}
        onSemestre={setSemestre}
        onLogout={onLogout}
      />

      <main style={S.main}>
        <div style={S.inner}>
          <h2 style={S.titre}>{titres[vue]}</h2>

          {vue === "overview" && (
            <>
              <div className="w-full">
                <PerformanceTile perf={perf} />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" style={{ marginBottom: 24 }}>
                <KpiCard label="Absences NJ"     value={profil.total_abs_nj}      color="#d97706" icon="⚠" />
                <KpiCard label="Abs. justifiées" value={profil.total_abs_just}    color="#8DC63F" icon="✓" />
                <KpiCard label="Taux de présence" value={presence === null ? null : `${presence}%`} color={presence === null ? "#64748b" : presence >= 80 ? "#5a9e14" : presence >= 50 ? "#d97706" : "#dc2626"} sub="cumulé depuis la semaine 1" icon="◎" />
                <KpiCard label="Taux d'absence"   value={absence === null ? null : `${absence}%`} color={absence === null ? "#64748b" : "#dc2626"} sub="cumulé depuis la semaine 1" icon="✕" />
              </div>

              {/* Courbe (2/3) + radar (1/3) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ marginBottom: 24 }}>
                <div className="lg:col-span-2 min-w-0">
                  <TauxAbsenceChart semaines={semaines} />
                </div>
                <div className="lg:col-span-1 min-w-0">
                  <ModulesRadar profil={profil} />
                </div>
              </div>
            </>
          )}

          {vue === "modules" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <LegendeModules />
              {profil.modules.map(m => (
                <div key={m.module} style={S.card}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{m.module}</span>
                    <StatutBadge statut={m.statut_exam} />
                  </div>
                  <div style={{ marginBottom: 20 }}>
                    <BarreAvecSeuils m={m} />
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

          {vue === "historique" && (
            <div style={{ ...S.card, padding: 0, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr>{["Date", "Module", "Durée", "Justifiée", "Motif"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
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
        </div>
      </main>
    </div>
  );
}
