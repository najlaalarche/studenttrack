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

export default function PageImportation() {
  const fileRef = useRef(null);
  const [file, setFile]         = useState(null);
  const [preview, setPreview]   = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [loadText, setLoadText] = useState("");
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  function handleFile(f) {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);

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

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  async function handleImport() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const steps = [
      "Import en cours…",
      "Vérification des doublons…",
      "Calcul des taux d'absence…",
      "Envoi des emails automatiques…",
    ];
    let i = 0;
    setLoadText(steps[i]);
    const interval = setInterval(() => {
      i = (i + 1) % steps.length;
      setLoadText(steps[i]);
    }, 1400);

    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BASE}/api/import-absences-csv`, {
        method: "POST",
        body: fd,
      }).then(r => r.json());

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

  const dropZoneStyle = {
    border: `2px dashed ${dragging ? "#1a3a6b" : "#CBD5E1"}`,
    borderRadius: 10,
    padding: "36px 24px",
    textAlign: "center",
    cursor: "pointer",
    backgroundColor: dragging ? "#eef2fb" : "#F8FAFC",
    transition: "all 0.15s",
  };

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

      {/* Drop zone */}
      <div
        style={dropZoneStyle}
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
            <div style={{ fontSize: 14, fontWeight: 600, color: "#1a3a6b" }}>Glisser-déposer le fichier CSV</div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>ou cliquer pour sélectionner (.csv, .xlsx)</div>
          </div>
        )}
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        style={{ display: "none" }}
        onChange={e => handleFile(e.target.files[0])}
      />

      {/* Aperçu */}
      {preview && preview.rows.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 8 }}>
            Aperçu — 5 premières lignes
          </div>
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
      )}

      {/* Bouton import */}
      {file && !loading && (
        <div style={{ marginTop: 20 }}>
          <button
            onClick={handleImport}
            style={{
              padding: "10px 24px", borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: "pointer",
              backgroundColor: "#1a3a6b", color: "#fff", border: "none",
            }}
          >
            ↑ Importer et traiter
          </button>
        </div>
      )}

      {loading && (
        <div style={{ marginTop: 20, backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24 }}>
          <Spinner text={loadText} />
        </div>
      )}

      {error && (
        <div style={{ marginTop: 20, backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "14px 18px", fontSize: 13, color: "#dc2626" }}>
          {error}
        </div>
      )}

      {/* Résultat */}
      {result && (
        <div style={{ marginTop: 24, backgroundColor: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#5a9e14", marginBottom: 20 }}>
            ✓ Import terminé
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <ResultLine icon="📄" label="Lignes traitées" value={result.lignes_traitees} color="#1e293b" />
            <ResultLine icon="➕" label="Nouvelles absences ajoutées" value={result.absences_ajoutees} color="#1a3a6b" />
            <ResultLine icon="⏭" label="Doublons ignorés" value={result.doublons_ignores} color="#64748b" />

            {result.etudiants_inconnus?.length > 0 && (
              <div style={{ backgroundColor: "#fffbeb", border: "1px solid #fde68a", borderRadius: 6, padding: "12px 14px" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#92400e", marginBottom: 4 }}>
                  ⚠ {result.etudiants_inconnus.length} étudiant(s) non trouvé(s)
                </div>
                <div style={{ fontSize: 12, color: "#78350f" }}>
                  ID inscription : {result.etudiants_inconnus.join(", ")}
                </div>
                <div style={{ fontSize: 12, color: "#78350f", marginTop: 4 }}>
                  → Ajoutez-les dans <strong>Gestion Étudiants</strong>
                </div>
              </div>
            )}

            {result.modules_crees?.length > 0 && (
              <div style={{ backgroundColor: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 6, padding: "12px 14px" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1e40af", marginBottom: 4 }}>
                  🔧 {result.modules_crees.length} nouveau(x) module(s) créé(s) (48h par défaut, à vérifier)
                </div>
                {result.modules_crees.map(m => (
                  <div key={m} style={{ fontSize: 12, color: "#1d4ed8" }}>→ "{m}"</div>
                ))}
              </div>
            )}

            {result.alertes_declenchees > 0 && (
              <div style={{ backgroundColor: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 6, padding: "12px 14px" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#c2410c" }}>
                  🔔 {result.alertes_declenchees} alerte(s) déclenchée(s)
                </div>
              </div>
            )}

            {result.emails_envoyes > 0 ? (
              <div style={{ backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 6, padding: "12px 14px" }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#166534" }}>
                  📧 {result.emails_envoyes} email(s) envoyé(s) automatiquement
                </div>
              </div>
            ) : result.alertes_declenchees > 0 ? (
              <div style={{ backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, padding: "12px 14px" }}>
                <div style={{ fontSize: 13, color: "#dc2626" }}>
                  📧 0 email envoyé — vérifier la clé Brevo ou les flags anti-doublon
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
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
