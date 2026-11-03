import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const ROUGE = "#dc2626";

const CARD = { backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 24px 12px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };

function TooltipSemaine({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const s = payload[0].payload;
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 6, padding: "8px 12px", fontSize: 12, color: "#1e293b", boxShadow: "0 2px 6px rgba(0,0,0,0.08)" }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{label}</div>
      <div><span style={{ color: ROUGE }}>●</span> Absence : <strong>{s.taux_absence}%</strong></div>
      <div style={{ color: "#64748b", marginTop: 4 }}>{s.heures_absent}h / {s.heures_planifiees}h planifiées (cumul)</div>
      <div style={{ color: "#94a3b8", marginTop: 2 }}>Cliquer pour le détail de la semaine</div>
    </div>
  );
}

// Classement des modules de la semaine cliquée (heures de cette semaine uniquement, pas le cumul)
function PanneauSemaine({ semaine, onClose }) {
  // absences_par_module : ajouté au backend ; repli sur le module n°1 si l'API n'a pas été redémarrée
  const modules = semaine.absences_par_module
    ?? (semaine.module_plus_absent ? [{ module: semaine.module_plus_absent, heures: semaine.heures_absent_module }] : []);
  return (
    <div style={{ position: "relative", marginTop: 8, marginBottom: 8, padding: "12px 40px 12px 16px", borderRadius: 6, backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", fontSize: 13, color: "#1e293b" }}>
      <button onClick={onClose} aria-label="Fermer" style={{ position: "absolute", top: 8, right: 10, background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 14 }}>✕</button>
      <div style={{ fontWeight: 700, marginBottom: modules.length ? 8 : 4 }}>{semaine.label} — Absences par module</div>
      {modules.length === 0 ? (
        <div style={{ color: "#64748b" }}>Aucune absence enregistrée cette semaine</div>
      ) : (
        <ol style={{ margin: 0, paddingLeft: 22, display: "flex", flexDirection: "column", gap: 4 }}>
          {modules.map(m => (
            <li key={m.module} style={{ paddingLeft: 2 }}>
              <span style={{ display: "flex", justifyContent: "space-between", gap: 16, maxWidth: 520 }}>
                <span>{m.module}</span>
                <strong style={{ color: ROUGE, whiteSpace: "nowrap" }}>{m.heures}h</strong>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// semaines : réponse de GET /api/etudiant/<id>/taux-absence (valeurs cumulées depuis la semaine 1)
export default function TauxAbsenceChart({ semaines }) {
  const data = semaines.map(s => ({ ...s, label: `Semaine ${s.semaine}` }));
  const [selection, setSelection] = useState(null);
  const choisie = data.find(s => s.label === selection) ?? null;

  if (data.length === 0) {
    return (
      <div style={CARD}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b", marginBottom: 8 }}>Taux d'absence cumulé</div>
        <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 8px" }}>
          Aucun planning importé pour votre groupe pour le moment.
        </p>
      </div>
    );
  }

  const derniere = data[data.length - 1];

  return (
    <div style={CARD}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12, gap: 12, flexWrap: "wrap" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b" }}>Taux d'absence cumulé</div>
        <div style={{ fontSize: 12, color: "#64748b" }}>
          À ce jour : <strong style={{ color: "#1e293b" }}>{derniere.taux_absence}%</strong> d'absence ·{" "}
          <strong style={{ color: "#1e293b" }}>{derniere.taux_presence}%</strong> de présence
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart
          data={data}
          margin={{ top: 8, right: 16, bottom: 0, left: -8 }}
          onClick={state => { if (state?.activeLabel) setSelection(state.activeLabel); }}
          style={{ cursor: "pointer" }}
        >
          <CartesianGrid stroke="#F1F5F9" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#E2E8F0" }} />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={v => `${v}%`} tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip content={<TooltipSemaine />} cursor={{ stroke: "#CBD5E1", strokeDasharray: "3 3" }} />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 4 }} iconType="plainline" />
          <Line type="monotone" dataKey="taux_absence"  name="Taux d'absence"  stroke={ROUGE} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: "#FFFFFF" }} activeDot={{ r: 6, stroke: "#FFFFFF", strokeWidth: 2 }} />
        </LineChart>
      </ResponsiveContainer>

      {choisie ? (
        <PanneauSemaine semaine={choisie} onClose={() => setSelection(null)} />
      ) : (
        <div style={{ fontSize: 11, color: "#94a3b8", margin: "4px 0 8px" }}>Cliquez sur une semaine pour voir les absences par module.</div>
      )}
    </div>
  );
}
