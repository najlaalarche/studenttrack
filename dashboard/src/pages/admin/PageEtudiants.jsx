import { useEffect, useState } from "react";
import { getEtudiants } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

const RISQUES   = ["Tous", "faible", "modéré", "critique"];
const STATUTS_F = ["Tous", "AVERTI", "EXCLU"];

const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748B", textAlign: "left", borderBottom: "1px solid #1E1E2E", whiteSpace: "nowrap" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #1E1E2E" },
};

function Spinner() {
  return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
    <div style={{ width: 24, height: 24, border: "2px solid #1E1E2E", borderTop: "2px solid #6366F1", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
  </div>;
}

function FilterBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
      backgroundColor: active ? "#6366F1" : "#16161F",
      color: active ? "#fff" : "#64748B",
      border: `1px solid ${active ? "#6366F1" : "#1E1E2E"}`,
    }}>{children}</button>
  );
}

export default function PageEtudiants({ onSelectEtudiant }) {
  const [liste, setListe]       = useState([]);
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [filtreRisque, setFiltreRisque] = useState("Tous");
  const [filtreStatut, setFiltreStatut] = useState("Tous");
  const [search, setSearch]     = useState("");

  useEffect(() => {
    getEtudiants()
      .then(data => { if (data.erreur) throw new Error(); setListe(data); })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#EF4444", padding: 16 }}>{error}</p>;

  const displayed = liste.filter(e => {
    if (filtreRisque !== "Tous" && e.niveau_risque !== filtreRisque) return false;
    if (filtreStatut !== "Tous") {
      if (!(e.modules ?? []).some(m => m.statut_exam === filtreStatut)) return false;
    }
    if (search) {
      const q = search.toLowerCase();
      if (!(e.nom.toLowerCase().includes(q) || e.prenom.toLowerCase().includes(q) || e.email.toLowerCase().includes(q))) return false;
    }
    return true;
  });

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#F8FAFC", marginBottom: 24 }}>Étudiants</h2>

      {/* Filtres */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 20, alignItems: "center" }}>
        <input
          placeholder="Rechercher…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ padding: "7px 12px", borderRadius: 6, fontSize: 12, backgroundColor: "#16161F", border: "1px solid #1E1E2E", color: "#F8FAFC", outline: "none", minWidth: 180 }}
        />
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "#64748B", marginRight: 4, fontWeight: 500 }}>RISQUE</span>
          {RISQUES.map(r => <FilterBtn key={r} active={filtreRisque === r} onClick={() => setFiltreRisque(r)}>{r}</FilterBtn>)}
        </div>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "#64748B", marginRight: 4, fontWeight: 500 }}>STATUT</span>
          {STATUTS_F.map(s => <FilterBtn key={s} active={filtreStatut === s} onClick={() => setFiltreStatut(s)}>{s}</FilterBtn>)}
        </div>
        <span style={{ fontSize: 12, color: "#64748B", marginLeft: "auto" }}>{displayed.length} résultat(s)</span>
      </div>

      <div style={{ backgroundColor: "#16161F", border: "1px solid #1E1E2E", borderRadius: 8, overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ backgroundColor: "#111118" }}>
            <tr>{["Nom", "Filière", "Abs. NJ", "Score", "Risque", "Moyenne", "Mods ⚠", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {displayed.length === 0
              ? <tr><td colSpan={8} style={{ ...S.td, textAlign: "center", color: "#64748B" }}>Aucun résultat</td></tr>
              : displayed.map((e, i) => {
                const globalSt = e.nb_modules_exclu > 0 ? "EXCLU" : e.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";
                return (
                  <tr
                    key={e.id_etudiant}
                    onClick={() => onSelectEtudiant(e.id_etudiant)}
                    style={{ cursor: "pointer", backgroundColor: i % 2 ? "transparent" : "#111118" }}
                    onMouseEnter={el => el.currentTarget.style.backgroundColor = "#1E1E2E"}
                    onMouseLeave={el => el.currentTarget.style.backgroundColor = i % 2 ? "transparent" : "#111118"}
                  >
                    <td style={S.td}>
                      <div style={{ fontWeight: 500, color: "#F8FAFC" }}>{e.prenom} {e.nom}</div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 1 }}>{e.email}</div>
                    </td>
                    <td style={{ ...S.td, color: "#94A3B8", fontSize: 12 }}>{e.annee}</td>
                    <td style={{ ...S.td, color: "#F97316", fontWeight: 500 }}>{e.total_abs_nj}</td>
                    <td style={{ ...S.td, fontWeight: 600, color: e.score_global >= 70 ? "#EF4444" : e.score_global >= 40 ? "#F97316" : "#22C55E" }}>
                      {e.score_global}
                    </td>
                    <td style={{ ...S.td, fontSize: 12, color: e.niveau_risque === "critique" ? "#EF4444" : e.niveau_risque === "modéré" ? "#F97316" : "#22C55E", textTransform: "capitalize" }}>
                      {e.niveau_risque}
                    </td>
                    <td style={{ ...S.td, color: "#94A3B8" }}>
                      {e.moyenne_generale ? Number(e.moyenne_generale).toFixed(2) : "—"}
                    </td>
                    <td style={{ ...S.td, color: e.nb_modules_averti + e.nb_modules_exclu > 0 ? "#F97316" : "#64748B", fontWeight: 500 }}>
                      {e.nb_modules_averti + e.nb_modules_exclu}
                    </td>
                    <td style={S.td}><StatutBadge statut={globalSt} /></td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
