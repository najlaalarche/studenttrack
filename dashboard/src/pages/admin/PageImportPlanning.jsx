import { useEffect, useState } from "react";
import {
  BASE, useImport, DropZone, FichierSelectionne, ImportControls, ResultCard, InfoCard, ResultLine,
} from "./PageImportation.jsx";
import { apiFetch } from "../../api.js";

const S = {
  th: { padding: "8px 12px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td: { padding: "8px 12px", fontSize: 12, borderBottom: "1px solid #F1F5F9", color: "#475569" },
};

const fmtDate = iso => (iso ? iso.split("-").reverse().join("/") : "—");

export default function PageImportPlanning() {
  const [file, setFile]           = useState(null);
  const [resume, setResume]       = useState(null);
  const [dateDebut, setDateDebut] = useState("");
  const imp = useImport([
    "Lecture du planning…",
    "Calcul des numéros de semaine…",
    "Vérification des doublons…",
  ]);
  const { result } = imp;

  function charger() {
    apiFetch(`${BASE}/api/planning`).then(r => r.json())
      .then(r => { setResume(r); setDateDebut(d => d || r.date_debut); })
      .catch(() => setResume(null));
  }

  useEffect(charger, []);
  useEffect(() => { if (result) charger(); }, [result]);

  const dateModifiee = resume && dateDebut && dateDebut !== resume.date_debut;

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 8 }}>
        Importer le planning hebdomadaire
      </h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 20 }}>
        Export Konosys des séances planifiées (ex. <span style={{ fontFamily: "monospace", fontSize: 12 }}>planning_SEM_19_OCTOBRE.xlsx</span>) — colonnes attendues :{" "}
        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#475569" }}>
          id_seance, dateSeance, numDay, HD, HF, DureeMin, DureeMinDecimal, Salle, Prof, Groupe, Module, CodeModule, TypeSeance, Cursus, AppelFait
        </span>
        . Les séances déjà importées (même <span style={{ fontFamily: "monospace", fontSize: 12 }}>id_seance</span>) sont ignorées.
      </p>

      <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "14px 18px", marginBottom: 20 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "#1e293b", fontWeight: 600 }}>
          Début de l'année scolaire (semaine 1)
          <input
            type="date"
            value={dateDebut}
            onChange={e => setDateDebut(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #CBD5E1", fontSize: 13, fontWeight: 400 }}
          />
        </label>
        <div style={{ fontSize: 12, color: dateModifiee ? "#d97706" : "#64748b", marginTop: 6 }}>
          {dateModifiee
            ? "⚠ Date modifiée : toutes les séances déjà importées seront renumérotées lors du prochain import."
            : "La semaine (lundi → dimanche) qui contient cette date est la semaine 1."}
        </div>
      </div>

      <DropZone
        file={file}
        onFile={f => { setFile(f); imp.reset(); }}
        accept=".xlsx"
        label="📅 Glisser-déposer le fichier planning"
        hint="ou cliquer pour sélectionner (.xlsx)"
      />
      {file && <FichierSelectionne file={file} />}
      <ImportControls file={file} imp={imp} onImport={() => imp.run("/api/import-planning", file, dateDebut ? { date_debut: dateDebut } : {})} />

      {result && (
        <ResultCard title="✓ Import du planning terminé">
          <ResultLine icon="📄" label="Lignes traitées" value={result.lignes_traitees} color="#1e293b" />
          <ResultLine icon="➕" label="Séances ajoutées" value={result.seances_ajoutees} color="#1a3a6b" />
          <ResultLine icon="⏭" label="Doublons ignorés" value={result.doublons_ignores} color="#64748b" />
          {result.semaines?.length > 0 && (
            <InfoCard tone="green" title={`Semaine(s) concernée(s) : ${result.semaines.map(s => `S${s}`).join(", ")}`}>
              {result.groupes.length} groupe(s) : {result.groupes.join(" · ")}
            </InfoCard>
          )}
          {result.lignes_invalides > 0 && (
            <InfoCard tone="amber" title={`⚠ ${result.lignes_invalides} ligne(s) ignorée(s) — id_seance, date, groupe ou durée manquant`} />
          )}
          {result.hors_annee > 0 && (
            <InfoCard tone="amber" title={`⚠ ${result.hors_annee} séance(s) antérieure(s) au début d'année (${fmtDate(result.date_debut)}) ignorée(s)`} />
          )}
        </ResultCard>
      )}

      {resume?.par_semaine?.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b", marginBottom: 10 }}>
            Planning en base — {resume.total_seances} séance(s), {resume.total_groupes} groupe(s)
          </div>
          <div style={{ backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "hidden", maxWidth: 560 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr>{["Semaine", "Du", "Au", "Séances", "Heures"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {resume.par_semaine.map(s => (
                  <tr key={s.semaine}>
                    <td style={{ ...S.td, fontWeight: 600, color: "#1e293b" }}>Semaine {s.semaine}</td>
                    <td style={S.td}>{fmtDate(s.du)}</td>
                    <td style={S.td}>{fmtDate(s.au)}</td>
                    <td style={S.td}>{s.seances}</td>
                    <td style={S.td}>{s.heures}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
