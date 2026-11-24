import { useEffect, useState } from "react";
import { getStats, getStatsParFiliere, getStatsTauxAbsence, postSync } from "../../api.js";
import Sidebar from "../../components/Sidebar.jsx";
import AbsencesModuleChart from "../../components/AbsencesModuleChart.jsx";
import { useAnalyseIA, BoutonAnalyseIA, CarteAnalyseIA } from "../../components/AnalyseIA.jsx";
import PageEtudiants from "./PageEtudiants.jsx";
import PageAlertes from "./PageAlertes.jsx";
import PageDetailEtudiant from "./PageDetailEtudiant.jsx";
import PageImportation from "./PageImportation.jsx";
import PageImportPlanning from "./PageImportPlanning.jsx";
import PageGestionEtudiants from "./PageGestionEtudiants.jsx";
import PageGestionProfesseurs from "./PageGestionProfesseurs.jsx";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend, LineChart, Line,
} from "recharts";

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

const SECTION = "bg-white rounded-xl shadow-sm p-6 mb-6";
const VIDE = "flex items-center justify-center text-center text-sm text-gray-500";

function SectionTitre({ children }) {
  return (
    <h3 className="mb-4 border-l-4 border-[#1e3a5f] pl-3 text-sm font-semibold uppercase tracking-wide text-gray-700">
      {children}
    </h3>
  );
}

// Tuile KPI compacte : icône teintée à gauche, couleur d'accent propre à chaque indicateur
function KpiTile({ label, value, color, icon }) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-xl bg-white px-4 py-3 shadow-sm" style={{ borderLeft: `3px solid ${color}` }}>
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-base font-bold"
        style={{ backgroundColor: `${color}1a`, color }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="truncate text-[11px] font-semibold uppercase tracking-wide text-gray-500" title={label}>{label}</div>
        <div className="text-xl font-bold leading-tight" style={{ color }}>{value ?? "—"}</div>
      </div>
    </div>
  );
}

// Une couleur fixe par filière (ordre alphabétique) ; au-delà de 8 filières, mêmes teintes en pointillés
const COULEURS_FILIERES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];

const couleurTaux = t => (t > 50 ? "#EF4444" : t >= 20 ? "#F59E0B" : "#8DC63F");

const ONGLETS = [
  { key: "general", label: "Vue générale" },
  { key: "filiere", label: "Par filière" },
  { key: "module",  label: "Par module" },
];

function Onglets({ actif, onChange }) {
  return (
    <div className="mb-6 flex gap-6 border-b border-gray-200 bg-white" role="tablist">
      {ONGLETS.map(o => (
        <button
          key={o.key}
          role="tab"
          aria-selected={actif === o.key}
          onClick={() => onChange(o.key)}
          className={`-mb-px border-b-2 px-1 pb-3 pt-1 text-sm font-medium transition-colors ${
            actif === o.key
              ? "border-[#1e3a5f] text-[#1e3a5f]"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// Filières affichées dans le tableau des statuts (code en base -> libellé)
const FILIERES_TABLEAU = [
  { code: "IMS",    label: "IMS" },
  { code: "GI-BDM", label: "GI-BDM" },
  { code: "GI-EO",  label: "EO" },
];

function TableauStatutsFiliere({ lignes }) {
  const parCode = Object.fromEntries((lignes ?? []).map(l => [l.filiere, l]));
  const colonnes = [
    { key: "exclu",    label: "🔴 Exclus",          color: "#dc2626" },
    { key: "averti",   label: "🟡 Avertis",         color: "#d97706" },
    { key: "autorise", label: "🟢 Rien à signaler", color: "#16a34a" },
  ];
  return (
    <section className="mb-6 overflow-hidden rounded-xl bg-white shadow-sm">
      <div className="p-6 pb-4">
        <SectionTitre>Répartition des statuts par filière</SectionTitre>
      </div>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-[#1e3a5f] text-white">
            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Filière</th>
            {colonnes.map(c => (
              <th key={c.key} className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {FILIERES_TABLEAU.map((f, i) => {
            const l = parCode[f.code];
            return (
              <tr key={f.code} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                <td className="px-6 py-3 font-semibold text-gray-700">{f.label}</td>
                {colonnes.map(c => (
                  <td key={c.key} className="px-6 py-3 text-center font-bold" style={{ color: l ? c.color : "#94a3b8" }}>
                    {l ? l[c.key] : "—"}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

const TOOLTIP_STYLE = { fontSize: 12, borderRadius: 6, border: "1px solid #E2E8F0" };
const HAUTEUR_TOP = 280;

// Pourcentage écrit dans la part (positionné à mi-rayon depuis cx/cy) ; masqué sous 6 %
const RADIAN = Math.PI / 180;
function labelPart({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.06) return null;
  const r = innerRadius + (outerRadius - innerRadius) / 2;
  const x = cx + r * Math.cos(-midAngle * RADIAN);
  const y = cy + r * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="#FFFFFF" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={700}>
      {Math.round(percent * 100)}%
    </text>
  );
}

function VueEnsemble() {
  const [stats, setStats]         = useState(null);
  const [tauxAbs, setTauxAbs]     = useState(null);
  const [parFiliereStats, setParFiliereStats] = useState(null);
  const [error, setError]         = useState(null);
  const [loading, setLoading]     = useState(true);
  const [onglet, setOnglet]       = useState("general");
  const ia = useAnalyseIA("admin");

  useEffect(() => {
    Promise.all([getStats(), getStatsTauxAbsence().catch(() => null), getStatsParFiliere().catch(() => null)])
      .then(([s, t, f]) => {
        if (s.erreur) throw new Error();
        setStats(s);
        setTauxAbs(t);
        setParFiliereStats(Array.isArray(f) ? f : null);
      })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626" }}>{error}</p>;

  // Taux d'absence cumulatif (planning importé) — dernière semaine disponible de chaque étudiant
  const top10 = (tauxAbs?.top10 ?? []).map(e => ({
    name: `${e.prenom} ${e.nom}`.length > 18 ? `${e.prenom} ${e.nom}`.substring(0, 18) + "…" : `${e.prenom} ${e.nom}`,
    taux: e.taux_absence,
    semaine: e.semaine,
    color: couleurTaux(e.taux_absence),
  }));
  const filieres   = tauxAbs?.filieres ?? [];
  const parFiliere = (tauxAbs?.par_filiere ?? []).map(s => ({ ...s, label: `Semaine ${s.semaine}` }));

  const pieData = [
    { name: "Rien à signaler", value: stats.autorise, color: "#22c55e" },
    { name: "Averti",          value: stats.averti,   color: "#eab308" },
    { name: "Exclu",           value: stats.exclu,    color: "#ef4444" },
  ].filter(d => d.value > 0);

  // Filière avec le plus d'étudiants exclus ou avertis
  const filiereAlerte = (parFiliereStats ?? []).reduce(
    (pire, f) => (!pire || f.exclu + f.averti > pire.exclu + pire.averti ? f : pire), null);

  function analyserIA() {
    ia.lancer({
      kpis: {
        total_etudiants:  stats.total_etudiants,
        en_alerte:        stats.total_alertes,
        exclus:           stats.exclu,
        avertis:          stats.averti,
        rien_a_signaler:  stats.autorise,
        total_absences_non_justifiees: stats.total_abs_nj,
      },
      top3_absenteistes: (tauxAbs?.top10 ?? []).slice(0, 3).map(e => ({
        nom: `${e.prenom} ${e.nom}`, filiere: e.filiere,
        taux_absence_cumule_pct: e.taux_absence, semaine: e.semaine,
      })),
      filiere_plus_en_alerte: filiereAlerte && {
        filiere: filiereAlerte.filiere, exclus: filiereAlerte.exclu,
        avertis: filiereAlerte.averti, rien_a_signaler: filiereAlerte.autorise,
      },
    });
  }

  const kpis = [
    { label: "Total étudiants", value: stats.total_etudiants, color: "#2563eb", icon: "⊞" },
    { label: "En alerte",       value: stats.total_alertes,   color: "#f97316", icon: "◉" },
    { label: "Exclus",          value: stats.exclu,           color: "#ef4444", icon: "▲" },
    { label: "Avertis",         value: stats.averti,          color: "#eab308", icon: "◐" },
    { label: "Rien à signaler", value: stats.autorise,        color: "#22c55e", icon: "✓" },
    { label: "Total abs. NJ",   value: stats.total_abs_nj,    color: "#64748b", icon: "≡" },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between gap-4">
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>Vue d'ensemble</h2>
        <BoutonAnalyseIA ia={ia} onClick={analyserIA} />
      </div>

      {/* KPIs — une seule ligne */}
      <div className="mb-6 grid grid-cols-6 gap-4">
        {kpis.map(k => <KpiTile key={k.label} {...k} />)}
      </div>

      <CarteAnalyseIA ia={ia} />

      <Onglets actif={onglet} onChange={setOnglet} />

      {/* Onglet 1 — Top 10 + répartition */}
      {onglet === "general" && (
      <div className="mb-6 grid grid-cols-2 gap-6">
        <section className="rounded-xl bg-white p-6 shadow-sm">
          <SectionTitre>Top 10 — taux d'absence cumulatif</SectionTitre>
          {top10.length === 0 ? (
            <div className={VIDE} style={{ height: HAUTEUR_TOP }}>Aucune donnée de planning disponible</div>
          ) : (
            <ResponsiveContainer width="100%" height={HAUTEUR_TOP}>
              <BarChart data={top10} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" width={130} tick={{ fill: "#1e293b", fontSize: 11 }} />
                <Tooltip
                  formatter={(v) => [`${v}%`, "Taux d'absence cumulatif"]}
                  labelFormatter={(name, p) => p?.[0] ? `${name} — semaine ${p[0].payload.semaine}` : name}
                  contentStyle={TOOLTIP_STYLE}
                />
                <Bar dataKey="taux" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {top10.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="rounded-xl bg-white p-6 shadow-sm">
          <SectionTitre>Répartition des statuts</SectionTitre>
          {pieData.length === 0 ? (
            <div className={VIDE} style={{ height: HAUTEUR_TOP }}>Aucun étudiant</div>
          ) : (
            <ResponsiveContainer width="100%" height={HAUTEUR_TOP}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="45%"
                  outerRadius={100}
                  dataKey="value"
                  nameKey="name"
                  label={labelPart}
                  labelLine={false}
                  stroke="#FFFFFF"
                  strokeWidth={2}
                >
                  {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip formatter={(v, name) => [`${v} étudiant(s)`, name]} contentStyle={TOOLTIP_STYLE} />
                <Legend
                  verticalAlign="bottom"
                  iconType="circle"
                  wrapperStyle={{ fontSize: 12 }}
                  formatter={(name, entry) => <span style={{ color: "#334155" }}>{name} ({entry.payload.value})</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>
      )}
      {onglet === "general" && <TableauStatutsFiliere lignes={parFiliereStats} />}

      {/* Onglet 2 — évolution par filière, pleine largeur */}
      {onglet === "filiere" && (
      <section className={SECTION}>
        <SectionTitre>Évolution du taux d'absence par filière</SectionTitre>
        {parFiliere.length === 0 ? (
          <div className={VIDE} style={{ height: 350 }}>Aucune donnée de planning disponible pour le moment.</div>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={parFiliere} margin={{ top: 8, right: 20, bottom: 0, left: -8 }}>
              <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#E2E8F0" }} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={v => `${v}%`} tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(v, name) => [`${v}%`, name]}
                itemSorter={item => -item.value}
                cursor={{ stroke: "#CBD5E1", strokeDasharray: "3 3" }}
                contentStyle={TOOLTIP_STYLE}
              />
              <Legend verticalAlign="top" align="right" iconType="plainline" wrapperStyle={{ fontSize: 12, paddingBottom: 12 }} />
              {filieres.map((f, i) => (
                <Line
                  key={f}
                  type="monotone"
                  dataKey={f}
                  name={f}
                  stroke={COULEURS_FILIERES[i % COULEURS_FILIERES.length]}
                  strokeDasharray={i >= COULEURS_FILIERES.length ? "6 4" : undefined}
                  strokeWidth={2}
                  dot={{ r: 3, strokeWidth: 2, fill: "#FFFFFF" }}
                  activeDot={{ r: 5, stroke: "#FFFFFF", strokeWidth: 2 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>
      )}

      {/* Onglet 3 — absences hebdomadaires par module */}
      {onglet === "module" && <AbsencesModuleChart />}
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
        {page === "import-planning"   && !selected && <PageImportPlanning />}
        {page === "gestion-etudiants"    && !selected && <PageGestionEtudiants />}
        {page === "gestion-professeurs"  && !selected && <PageGestionProfesseurs />}
        {page === "sync"                 && !selected && <PageSync />}
        {selected && <PageDetailEtudiant id_etudiant={selected} onBack={() => { setSelected(null); setPage("etudiants"); }} />}
      </main>
    </div>
  );
}
