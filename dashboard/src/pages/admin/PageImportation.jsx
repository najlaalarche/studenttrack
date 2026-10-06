import { useRef, useState } from "react";

const BASE = "http://localhost:5050";

function Spinner({ text }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "32px 0" }}>
      <div style={{ width: 28, height: 28, border: "3px solid #E2E8F0", borderTop: "3px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      {text && <span style={{ fontSize: 13, color: "#64748b" }}>{text}</span>}
    </div>
  );
}

function parseCSV(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 2) return [];
  const seps = [";", ",", "\t"];
  let sep = ",";
  for (const s of seps) {
    if (lines[0].split(s).length >= 5) { sep = s; break; }
  }
  const headers = lines[0].split(sep).map(h => h.trim().replace(/^"|"$/g, ""));
  return lines.slice(1, 6).map(line => {
    const vals = line.split(sep).map(v => v.trim().replace(/^"|"$/g, ""));
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
  });
}

// État d'un import : POST du fichier, messages du spinner qui défilent, résultat ou erreur.
function useImport(steps) {
  const [loading, setLoading]   = useState(false);
  const [loadText, setLoadText] = useState("");
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  async function run(url, file) {
    setLoading(true);
    setError(null);
    setResult(null);
    let i = 0;
    setLoadText(steps[i]);
    const interval = setInterval(() => {
      i = (i + 1) % steps.length;
      setLoadText(steps[i]);
    }, 1400);

    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BASE}${url}`, { method: "POST", body: fd }).then(r => r.json());
      if (res.error) throw new Error(res.error);
      setResult(res);
    } catch (e) {
      setError(e.message || "Erreur lors de l'import.");
    } finally {
      clearInterval(interval);
      setLoading(false);
      setLoadText("");
    }
  }

  function reset() { setResult(null); setError(null); }

  return { loading, loadText, result, error, setError, run, reset };
}

export default function PageImportation() {
  return (
    <div>
      <ImportAbsences />
      <div style={{ marginTop: 40, paddingTop: 32, borderTop: "1px solid #E2E8F0" }}>
        <ImportNotes />
      </div>
    </div>
  );
}

function ImportAbsences() {
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);
  const imp = useImport([
    "Import en cours…",
    "Vérification des doublons…",
    "Calcul des taux d'absence…",
    "Envoi des emails automatiques…",
  ]);
  const { result } = imp;

  function handleFile(f) {
    setFile(f);
    setPreview(null);
    imp.reset();
    if (!f.name.toLowerCase().endsWith(".csv")) return;  // Excel = binaire : pas d'aperçu côté navigateur

    const reader = new FileReader();
    reader.onload = e => {
      const text = e.target.result;
      try {
        const rows = parseCSV(text);
        setPreview({ rows, headers: rows.length ? Object.keys(rows[0]) : [] });
      } catch {
        setPreview(null);
      }
    };
    reader.readAsText(f, "utf-8");
  }

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 8 }}>
        Importer les absences du jour
      </h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 24 }}>
        Format Konosys / Classeur1 — colonnes attendues :{" "}
        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#475569" }}>
          id_absence, Nom, Prenom, Seance, DATE, Heure, Duree, DureeDecimal, SessionProgramme, Cursus, Module, Excuse, Motif, id_inscriptionsessionprogramme
        </span>
      </p>

      <DropZone
        file={file}
        onFile={handleFile}
        accept=".csv,.xlsx,.xls"
        label="Glisser-déposer le fichier CSV"
        hint="ou cliquer pour sélectionner (.csv, .xlsx)"
      />
      {preview?.rows.length > 0
        ? <PreviewTable preview={preview} title="Aperçu — 5 premières lignes" />
        : file && <FichierSelectionne file={file} />}
      <ImportControls file={file} imp={imp} onImport={() => imp.run("/api/import-absences-csv", file)} />

      {result && (
        <ResultCard title="✓ Import terminé">
          <ResultLine icon="📄" label="Lignes traitées" value={result.lignes_traitees} color="#1e293b" />
          <ResultLine icon="➕" label="Nouvelles absences ajoutées" value={result.absences_ajoutees} color="#1a3a6b" />
          <ResultLine icon="⏭" label="Doublons ignorés" value={result.doublons_ignores} color="#64748b" />

          {result.etudiants_crees_auto?.length > 0 && (
            <InfoCard tone="green" title={`✓ ${result.etudiants_crees_auto.length} nouvel(s) étudiant(s) créé(s) automatiquement`}>
              {result.etudiants_crees_auto.map((e, i) => <div key={i}>→ {e.prenom} {e.nom}</div>)}
            </InfoCard>
          )}

          {result.etudiants_non_crees_filiere_inconnue?.length > 0 && (
            <InfoCard tone="amber" title={`⚠ ${result.etudiants_non_crees_filiere_inconnue.length} étudiant(s) non créé(s) — filière introuvable`}>
              {result.etudiants_non_crees_filiere_inconnue.map((e, i) => (
                <div key={i}>{e.prenom} {e.nom} · {e.session_programme || "SessionProgramme manquant"}</div>
              ))}
              <div style={{ marginTop: 4 }}>→ Créez-les manuellement dans <strong>Gestion Étudiants</strong></div>
            </InfoCard>
          )}

          {result.etudiants_homonymes?.length > 0 && (
            <InfoCard tone="amber" title={`⚠ ${result.etudiants_homonymes.length} étudiant(s) ignoré(s) — homonymes à départager`}>
              {result.etudiants_homonymes.map((e, i) => (
                <div key={i}>{e.prenom} {e.nom} · {e.session_programme || "—"}</div>
              ))}
              <div style={{ marginTop: 4 }}>→ Leurs absences n'ont pas été importées</div>
            </InfoCard>
          )}

          {result.modules_crees?.length > 0 && (
            <InfoCard tone="blue" title={`🔧 ${result.modules_crees.length} nouveau(x) module(s) créé(s) (48h par défaut, à vérifier)`}>
              {result.modules_crees.map(m => <div key={m}>→ "{m}"</div>)}
            </InfoCard>
          )}

          {result.alertes_declenchees > 0 && (
            <InfoCard tone="orange" title={`🔔 ${result.alertes_declenchees} alerte(s) déclenchée(s)`} />
          )}

          {result.emails_envoyes > 0 ? (
            <InfoCard tone="green" title={`📧 ${result.emails_envoyes} email(s) envoyé(s) automatiquement`} />
          ) : result.alertes_declenchees > 0 ? (
            <InfoCard tone="red" title="📧 0 email envoyé — vérifier la clé Brevo ou les flags anti-doublon" />
          ) : null}
        </ResultCard>
      )}
    </div>
  );
}

function ImportNotes() {
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);
  const [apercu, setApercu]   = useState(null);
  const imp = useImport([
    "Lecture du fichier Excel…",
    "Rapprochement des étudiants…",
    "Enregistrement des notes…",
    "Recalcul des scores de risque…",
  ]);
  const { result } = imp;

  // Fichier binaire (.xlsx/.xlsb) : l'aperçu est lu par le backend avec le même parseur que l'import
  async function handleFile(f) {
    setFile(f);
    setPreview(null);
    setApercu(null);
    imp.reset();
    try {
      const fd = new FormData();
      fd.append("file", f);
      const res = await fetch(`${BASE}/api/import-notes/preview`, { method: "POST", body: fd }).then(r => r.json());
      if (res.error) throw new Error(res.error);
      setApercu(res);
      setPreview({ rows: res.rows, headers: res.headers });
    } catch {
      setPreview(null);  // aperçu indisponible (API ancienne version, fichier illisible…) : l'import reste possible
    }
  }

  const titreApercu = apercu && [
    "Aperçu — 5 premières lignes",
    apercu.semestre, apercu.filiere, apercu.annee_universitaire,
    `${apercu.total} étudiant(s)`,
  ].filter(Boolean).join(" · ");

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 8 }}>
        Importer les notes
      </h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 24 }}>
        Export Konosys des moyennes (Excel) — seule la colonne{" "}
        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#475569" }}>Moyenne</span>{" "}
        est importée. Liaison par nom + prénom dans la même filière ; les étudiants inconnus sont créés automatiquement.
      </p>

      <DropZone
        file={file}
        onFile={handleFile}
        accept=".xlsx,.xlsb"
        label="📊 Glisser-déposer le fichier de notes Excel"
        hint="ou cliquer pour sélectionner (.xlsx, .xlsb)"
      />
      {preview?.rows.length > 0
        ? <PreviewTable preview={preview} title={titreApercu} />
        : file && <FichierSelectionne file={file} />}
      <ImportControls file={file} imp={imp} onImport={() => imp.run("/api/import-notes", file)} />

      {result && (
        <ResultCard title={`✓ Import des notes terminé${result.semestre ? ` — ${result.semestre} ${result.annee_universitaire}` : ""}`}>
          <ResultLine icon="📄" label="Étudiants traités" value={result.etudiants_traites} color="#1e293b" />
          <ResultLine icon="➕" label="Notes importées" value={result.notes_ajoutees} color="#1a3a6b" />
          <ResultLine icon="↻" label="Notes mises à jour" value={result.notes_mises_a_jour} color="#64748b" />
          <ResultLine icon="🔗" label="Étudiants liés automatiquement" value={result.etudiants_lies_auto} color="#1a3a6b" />

          {result.crees?.length > 0 && (
            <InfoCard tone="green" title={`✓ ${result.crees.length} nouvel(s) étudiant(s) créé(s) automatiquement`}>
              {result.crees.map(e => <div key={e.matricule}>→ {e.matricule} · {e.prenom} {e.nom}</div>)}
            </InfoCard>
          )}

          {result.non_trouves?.length > 0 && (
            <InfoCard tone="amber" title={`⚠ ${result.non_trouves.length} étudiant(s) à valider manuellement → voir data/rapprochement_a_valider.csv`}>
              {result.non_trouves.map(e => <div key={e.matricule}>{e.matricule} · {e.prenom} {e.nom} — {e.raison}</div>)}
            </InfoCard>
          )}
        </ResultCard>
      )}
    </div>
  );
}

// ── Composants partagés par les deux imports ─────────────────────────────────

function DropZone({ file, onFile, accept, label, hint }) {
  const fileRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  }

  return (
    <>
      <div
        style={{
          border: `2px dashed ${dragging ? "#1a3a6b" : "#CBD5E1"}`,
          borderRadius: 10,
          padding: "36px 24px",
          textAlign: "center",
          cursor: "pointer",
          backgroundColor: dragging ? "#eef2fb" : "#F8FAFC",
          transition: "all 0.15s",
        }}
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div style={{ fontSize: 32, marginBottom: 8 }}>↑</div>
        {file ? (
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#1a3a6b" }}>{file.name}</div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
              {(file.size / 1024).toFixed(1)} Ko — cliquer pour changer
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#1a3a6b" }}>{label}</div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{hint}</div>
          </div>
        )}
      </div>
      <input
        ref={fileRef}
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={e => { if (e.target.files[0]) onFile(e.target.files[0]); e.target.value = ""; }}
      />
    </>
  );
}

function FichierSelectionne({ file }) {
  return (
    <div style={{ marginTop: 20, backgroundColor: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: "12px 16px", fontSize: 13, color: "#166534" }}>
      ✓ Fichier sélectionné : <strong>{file.name}</strong> — aperçu disponible après import
    </div>
  );
}

function PreviewTable({ preview, title }) {
  if (!preview || preview.rows.length === 0) return null;
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 8 }}>{title}</div>
      <div style={{ overflowX: "auto", backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
          <thead>
            <tr>
              {preview.headers.map(h => (
                <th key={h} style={{ padding: "8px 12px", backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0", fontWeight: 600, color: "#64748b", textAlign: "left", whiteSpace: "nowrap" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, i) => (
              <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                {preview.headers.map(h => (
                  <td key={h} style={{ padding: "7px 12px", borderBottom: "1px solid #F1F5F9", color: "#475569", whiteSpace: "nowrap", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {row[h] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Bouton d'import + spinner + message d'erreur
function ImportControls({ file, imp, onImport }) {
  return (
    <>
      {file && !imp.loading && (
        <div style={{ marginTop: 20 }}>
          <button
            onClick={onImport}
            style={{
              padding: "10px 24px", borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: "pointer",
              backgroundColor: "#1a3a6b", color: "#fff", border: "none",
            }}
          >
            ↑ Importer et traiter
          </button>
        </div>
      )}

      {imp.loading && (
        <div style={{ marginTop: 20, backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24 }}>
          <Spinner text={imp.loadText} />
        </div>
      )}

      {imp.error && (
        <div style={{ marginTop: 20, backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "14px 18px", fontSize: 13, color: "#dc2626" }}>
          {imp.error}
        </div>
      )}
    </>
  );
}

function ResultCard({ title, children }) {
  return (
    <div style={{ marginTop: 24, backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: "#5a9e14", marginBottom: 20 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>
    </div>
  );
}

const TONES = {
  green:  { bg: "#f0fdf4", border: "#86efac", title: "#166534", text: "#15803d" },
  amber:  { bg: "#fffbeb", border: "#fde68a", title: "#92400e", text: "#78350f" },
  blue:   { bg: "#eff6ff", border: "#bfdbfe", title: "#1e40af", text: "#1d4ed8" },
  orange: { bg: "#fff7ed", border: "#fed7aa", title: "#c2410c", text: "#c2410c" },
  red:    { bg: "#fef2f2", border: "#fecaca", title: "#dc2626", text: "#dc2626" },
};

function InfoCard({ tone, title, children }) {
  const t = TONES[tone];
  return (
    <div style={{ backgroundColor: t.bg, border: `1px solid ${t.border}`, borderRadius: 6, padding: "12px 14px" }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: t.title, marginBottom: children ? 6 : 0 }}>{title}</div>
      {children && <div style={{ fontSize: 12, color: t.text }}>{children}</div>}
    </div>
  );
}

function ResultLine({ icon, label, value, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 18, width: 24, textAlign: "center" }}>{icon}</span>
      <span style={{ fontSize: 13, color: "#64748b" }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 700, color, marginLeft: "auto" }}>{value}</span>
    </div>
  );
}
