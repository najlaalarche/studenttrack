import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getAbsencesParSemaine, getModules } from "../api.js";

const FILIERES = [
  { code: "IMS",    label: "IMS" },
  { code: "GI-BDM", label: "GI-BDM" },
  { code: "GI-EO",  label: "EO" },
];
const SEMESTRES = ["S1", "S2"];
const HAUTEUR = 350;

const SELECT = "h-9 rounded-md border border-[#e2e8f0] bg-white px-3 text-xs text-[#1e293b] outline-none focus:border-[#1a3a6b] cursor-pointer";
const LABEL  = "mb-1 block text-[11px] font-semibold uppercase tracking-wide text-gray-500";

// Couleur relative au max de la période affichée
const couleurBarre = (h, max) => {
  const r = max > 0 ? h / max : 0;
  return r > 0.5 ? "#ef4444" : r >= 0.2 ? "#f59e0b" : "#22c55e";
};

function Toggle({ value, onChange }) {
  return (
    <div className="inline-flex h-9 overflow-hidden rounded-md border border-[#e2e8f0] bg-white">
      {SEMESTRES.map(s => (
        <button
          key={s}
          onClick={() => onChange(s)}
          className={`px-4 text-xs font-semibold transition-colors ${
            value === s ? "bg-[#1a3a6b] text-white" : "text-gray-500 hover:bg-gray-50"
          }`}
        >{s}</button>
      ))}
    </div>
  );
}

function EtatVide({ children, erreur }) {
  return (
    <div
      className={`flex items-center justify-center rounded-lg border border-dashed border-[#e2e8f0] bg-white px-6 text-center text-sm ${erreur ? "text-[#dc2626]" : "text-gray-500"}`}
      style={{ height: HAUTEUR + 34 }}
    >
      {children}
    </div>
  );
}

export default function AbsencesModuleChart() {
  const [modules, setModules]   = useState([]);
  const [filiere, setFiliere]   = useState(FILIERES[0].code);
  const [module, setModule]     = useState("");
  const [semestre, setSemestre] = useState("S1");
  const [absences, setAbsences] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  useEffect(() => {
    getModules().then(d => setModules(Array.isArray(d) ? d : [])).catch(() => setModules([]));
  }, []);

  useEffect(() => {
    if (!module) { setAbsences([]); return; }
    let annule = false;
    setLoading(true); setError(null);
    getAbsencesParSemaine(module, filiere, semestre.slice(1))
      .then(d => { if (!annule) setAbsences(Array.isArray(d) ? d : []); })
      .catch(() => { if (!annule) setError("Impossible de charger les absences de ce module."); })
      .finally(() => { if (!annule) setLoading(false); });
    return () => { annule = true; };
  }, [module, filiere, semestre]);

  const modulesFiliere = modules.filter(m => (m.filieres ?? []).includes(filiere));

  const data = absences.map(a => ({ semaine: a.semaine, label: `S${a.semaine}`, heures: a.heures }));
  const max = Math.max(0, ...data.map(d => d.heures));

  return (
    <section className="mb-6 rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-6 shadow-sm">
      <h3 className="mb-4 border-l-[3px] border-[#1a3a6b] pl-3 text-sm font-semibold uppercase tracking-wide text-gray-700">
        Absences par module — détail hebdomadaire
      </h3>

      <div className="mb-5 flex flex-wrap items-end gap-4">
        <div>
          <label className={LABEL}>Filière</label>
          <select value={filiere} onChange={e => { setFiliere(e.target.value); setModule(""); }} className={`${SELECT} w-36`}>
            {FILIERES.map(f => <option key={f.code} value={f.code}>{f.label}</option>)}
          </select>
        </div>
        <div className="min-w-[260px] flex-1">
          <label className={LABEL}>Module</label>
          <select value={module} onChange={e => setModule(e.target.value)} className={`${SELECT} w-full`}>
            <option value="">Sélectionner un module…</option>
            {modulesFiliere.map(m => <option key={m.nom} value={m.nom}>{m.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={LABEL}>Semestre</label>
          <Toggle value={semestre} onChange={setSemestre} />
        </div>
      </div>

      {!module ? (
        <EtatVide>Sélectionnez une filière puis un module pour afficher les absences hebdomadaires.</EtatVide>
      ) : loading ? (
        <EtatVide>Chargement…</EtatVide>
      ) : error ? (
        <EtatVide erreur>{error}</EtatVide>
      ) : max === 0 ? (
        <EtatVide>Aucune absence enregistrée pour ce module sur le semestre {semestre}.</EtatVide>
      ) : (
        <div className="rounded-lg border border-[#e2e8f0] bg-white p-4">
          <ResponsiveContainer width="100%" height={HAUTEUR}>
            <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} interval={0} />
              <YAxis allowDecimals={false} tickFormatter={v => `${v} h`} tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={v => [`${v} h`, "Heures d'absence"]}
                labelFormatter={(_, p) => p?.[0] ? `Semaine ${p[0].payload.semaine}` : ""}
                cursor={{ fill: "rgba(26,58,107,0.05)" }}
                contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e2e8f0" }}
              />
              <Bar dataKey="heures" radius={[4, 4, 0, 0]} maxBarSize={28}>
                {data.map(d => <Cell key={d.semaine} fill={couleurBarre(d.heures, max)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
