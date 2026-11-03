import { useEffect, useState } from "react";
import { getEtudiants, getFilieres, getModules } from "../../api.js";

const STATUTS_F = ["Tous", "AUTORISE", "AVERTI", "EXCLU"];
const LABEL_STATUT = { AUTORISE: "Rien à signaler" };

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

const fmtMoyenne = v => (v === null || v === undefined ? "—" : Number(v).toFixed(2));

// Nombre de modules par statut : 🔴 exclu · 🟡 averti · 🟢 rien à signaler (grisé si 0)
function CompteursStatut({ etudiant: e }) {
  const exclu  = e.nb_modules_exclu ?? 0;
  const averti = e.nb_modules_averti ?? 0;
  const rien   = Math.max(0, (e.modules ?? []).length - exclu - averti);
  const items = [
    { n: exclu,  label: "Exclu",           color: "#dc2626", bg: "rgba(239,68,68,0.1)",  border: "rgba(239,68,68,0.3)" },
    { n: averti, label: "Averti",          color: "#d97706", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" },
    { n: rien,   label: "Rien à signaler", color: "#5a9e14", bg: "rgba(141,198,63,0.1)", border: "rgba(141,198,63,0.35)" },
  ];
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "nowrap" }}>
      {items.map(it => {
        const vide = it.n === 0;
        return (
          <span key={it.label} title={`${it.n} module(s) — ${it.label}`} style={{
            display: "inline-flex", alignItems: "center", gap: 4, whiteSpace: "nowrap",
            padding: "2px 7px", borderRadius: 99, fontSize: 11, fontWeight: 600,
            color: vide ? "#94a3b8" : it.color,
            backgroundColor: vide ? "#F1F5F9" : it.bg,
            border: `1px solid ${vide ? "#E2E8F0" : it.border}`,
          }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: vide ? "#CBD5E1" : it.color }} />
            {it.n} {it.label}
          </span>
        );
      })}
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
    filtreStatut !== "Tous" || search !== "";

  function resetFilters() {
    setFiltreFiliere("Tous");
    setFiltreAnnee("Tous");
    setFiltreModule("Tous");
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

        {/* Ligne 2 : boutons statut + reset + compteur */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "#64748b", marginRight: 4, fontWeight: 600 }}>STATUT</span>
            {STATUTS_F.map(s => <FilterBtn key={s} active={filtreStatut === s} onClick={() => setFiltreStatut(s)}>{LABEL_STATUT[s] ?? s}</FilterBtn>)}
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
            <tr>{["Nom", "Filière", "Abs. NJ", "Moy. Brute", "Moy. Nette", "Mods ⚠", "Statut"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {displayed.length === 0
              ? <tr><td colSpan={7} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucun résultat</td></tr>
              : displayed.map((e, i) => {
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
                    <td style={{ ...S.td, color: "#64748b" }}>{fmtMoyenne(e.moyenne_brute)}</td>
                    <td style={{ ...S.td, color: "#64748b" }}>{fmtMoyenne(e.moyenne_nette)}</td>
                    <td style={{ ...S.td, color: e.nb_modules_averti + e.nb_modules_exclu > 0 ? "#d97706" : "#64748b", fontWeight: 500 }}>
                      {e.nb_modules_averti + e.nb_modules_exclu}
                    </td>
                    <td style={S.td}><CompteursStatut etudiant={e} /></td>
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
