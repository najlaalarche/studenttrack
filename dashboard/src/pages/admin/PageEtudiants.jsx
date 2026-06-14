import { useEffect, useState } from "react";
import { getEtudiants, getFilieres, getModules } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

const RISQUES   = ["Tous", "faible", "modéré", "critique"];
const STATUTS_F = ["Tous", "AUTORISE", "AVERTI", "EXCLU"];

const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", whiteSpace: "nowrap", backgroundColor: "#F8FAFC" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

const selectStyle = {
  padding: "7px 12px", borderRadius: 6, fontSize: 12,
  backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0",
  color: "#1e293b", outline: "none", cursor: "pointer", minWidth: 150,
};

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

function FilterBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
      backgroundColor: active ? "#1a3a6b" : "#FFFFFF",
      color: active ? "#fff" : "#64748b",
      border: `1px solid ${active ? "#1a3a6b" : "#E2E8F0"}`,
    }}>{children}</button>
  );
}

export default function PageEtudiants({ onSelectEtudiant }) {
  const [liste, setListe]       = useState([]);
  const [filieres, setFilieres] = useState([]);
  const [modules, setModules]   = useState([]);
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(true);

  const [filtreFiliere, setFiltreFiliere] = useState("Tous");
  const [filtreAnnee, setFiltreAnnee]     = useState("Tous");
  const [filtreModule, setFiltreModule]   = useState("Tous");
  const [filtreRisque, setFiltreRisque]   = useState("Tous");
  const [filtreStatut, setFiltreStatut]   = useState("Tous");
  const [search, setSearch]               = useState("");

  useEffect(() => {
    Promise.all([getEtudiants(), getFilieres(), getModules()])
      .then(([data, fils, mods]) => {
        if (data.erreur) throw new Error();
        setListe(data);
        setFilieres(Array.isArray(fils) ? fils : []);
        setModules(Array.isArray(mods) ? mods : []);
      })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626", padding: 16 }}>{error}</p>;

  const promotions = [...new Set(liste.map(e => e.annee).filter(Boolean))].sort();

  const displayed = liste.filter(e => {
    if (filtreFiliere !== "Tous" && e.filiere !== filtreFiliere) return false;
    if (filtreAnnee !== "Tous" && e.annee !== filtreAnnee) return false;
    if (filtreModule !== "Tous") {
      if (!(e.modules ?? []).some(m => m.module === filtreModule)) return false;
    }
    if (filtreRisque !== "Tous" && e.niveau_risque !== filtreRisque) return false;
    if (filtreStatut !== "Tous") {
      const globalSt = e.nb_modules_exclu > 0 ? "EXCLU" : e.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";
      if (globalSt !== filtreStatut) return false;
    }
    if (search) {
      const q = search.toLowerCase();
      if (!(e.nom.toLowerCase().includes(q) || e.prenom.toLowerCase().includes(q) || e.email.toLowerCase().includes(q))) return false;
    }
    return true;
  });

  const hasActiveFilters =
    filtreFiliere !== "Tous" || filtreAnnee !== "Tous" || filtreModule !== "Tous" ||
    filtreRisque !== "Tous" || filtreStatut !== "Tous" || search !== "";

  function resetFilters() {
    setFiltreFiliere("Tous");
    setFiltreAnnee("Tous");
    setFiltreModule("Tous");
    setFiltreRisque("Tous");
    setFiltreStatut("Tous");
    setSearch("");
  }

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 24 }}>Étudiants</h2>

      <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "16px 20px", marginBottom: 20 }}>
        {/* Ligne 1 : recherche + dropdowns */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 14 }}>
          <input
            placeholder="Rechercher par nom ou email…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ ...selectStyle, minWidth: 220 }}
          />
          <select value={filtreFiliere} onChange={e => setFiltreFiliere(e.target.value)} style={selectStyle}>
            <option value="Tous">Toutes les filières</option>
            {filieres.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          <select value={filtreAnnee} onChange={e => setFiltreAnnee(e.target.value)} style={selectStyle}>
            <option value="Tous">Toutes les promotions</option>
            {promotions.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={filtreModule} onChange={e => setFiltreModule(e.target.value)} style={selectStyle}>
            <option value="Tous">Tous les modules</option>
            {modules.map(m => {
              const nom = typeof m === "string" ? m : m.nom;
              return <option key={nom} value={nom}>{nom}</option>;
            })}
          </select>
        </div>

        {/* Ligne 2 : boutons risque + statut + reset + compteur */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "#64748b", marginRight: 4, fontWeight: 600 }}>RISQUE</span>
            {RISQUES.map(r => <FilterBtn key={r} active={filtreRisque === r} onClick={() => setFiltreRisque(r)}>{r}</FilterBtn>)}
          </div>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "#64748b", marginRight: 4, fontWeight: 600 }}>STATUT</span>
            {STATUTS_F.map(s => <FilterBtn key={s} active={filtreStatut === s} onClick={() => setFiltreStatut(s)}>{s}</FilterBtn>)}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: "auto" }}>
            {hasActiveFilters && (
              <button onClick={resetFilters} style={{
                padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
                backgroundColor: "#FFFFFF", color: "#dc2626", border: "1px solid #fca5a5",
              }}>
                Réinitialiser les filtres
              </button>
            )}
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>
              {displayed.length} étudiant(s) trouvé(s)
            </span>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "auto", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>{["Nom", "Filière", "Abs. NJ", "Score", "Risque", "Moyenne", "Mods ⚠", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {displayed.length === 0
              ? <tr><td colSpan={8} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucun résultat</td></tr>
              : displayed.map((e, i) => {
                const globalSt = e.nb_modules_exclu > 0 ? "EXCLU" : e.nb_modules_averti > 0 ? "AVERTI" : "AUTORISE";
                return (
                  <tr
                    key={e.id_etudiant}
                    onClick={() => onSelectEtudiant(e.id_etudiant)}
                    style={{ cursor: "pointer", backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}
                    onMouseEnter={el => el.currentTarget.style.backgroundColor = "#eef2fb"}
                    onMouseLeave={el => el.currentTarget.style.backgroundColor = i % 2 === 0 ? "#FFFFFF" : "#F8FAFC"}
                  >
                    <td style={S.td}>
                      <div style={{ fontWeight: 600, color: "#1e293b" }}>{e.prenom} {e.nom}</div>
                      <div style={{ fontSize: 11, color: "#64748b", marginTop: 1 }}>{e.email}</div>
                    </td>
                    <td style={{ ...S.td, color: "#64748b", fontSize: 12 }}>{e.annee}</td>
                    <td style={{ ...S.td, color: "#d97706", fontWeight: 600 }}>{e.total_abs_nj}</td>
                    <td style={{ ...S.td, fontWeight: 700, color: e.score_global >= 70 ? "#dc2626" : e.score_global >= 40 ? "#d97706" : "#5a9e14" }}>
                      {e.score_global}
                    </td>
                    <td style={{ ...S.td, fontSize: 12, color: e.niveau_risque === "critique" ? "#dc2626" : e.niveau_risque === "modéré" ? "#d97706" : "#5a9e14", fontWeight: 500, textTransform: "capitalize" }}>
                      {e.niveau_risque}
                    </td>
                    <td style={{ ...S.td, color: "#64748b" }}>
                      {e.moyenne_generale ? Number(e.moyenne_generale).toFixed(2) : "—"}
                    </td>
                    <td style={{ ...S.td, color: e.nb_modules_averti + e.nb_modules_exclu > 0 ? "#d97706" : "#64748b", fontWeight: 500 }}>
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
