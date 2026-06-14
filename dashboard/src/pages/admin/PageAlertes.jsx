import { useEffect, useState } from "react";

const BASE = "http://localhost:5050";

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function StatutBadge({ statut }) {
  const cfg = {
    EXCLU:    { bg: "rgba(239,68,68,0.1)",   border: "rgba(239,68,68,0.35)",   color: "#dc2626" },
    AVERTI:   { bg: "rgba(245,158,11,0.1)",  border: "rgba(245,158,11,0.35)",  color: "#d97706" },
    AUTORISE: { bg: "rgba(141,198,63,0.1)",  border: "rgba(141,198,63,0.35)",  color: "#5a9e14" },
  }[statut] || { bg: "#f1f5f9", border: "#e2e8f0", color: "#64748b" };
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 99,
      backgroundColor: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color,
      textTransform: "uppercase", letterSpacing: "0.05em",
    }}>{statut}</span>
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

export default function PageHistoriqueAlertes() {
  const [alertes, setAlertes]         = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [filtreStatut, setFiltreStatut] = useState("Tous");
  const [filtreEnvoi, setFiltreEnvoi] = useState("Tous");

  useEffect(() => {
    fetch(`${BASE}/api/alertes`)
      .then(r => r.json())
      .then(data => {
        if (data.erreur) throw new Error(data.erreur);
        setAlertes(Array.isArray(data) ? data : []);
      })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  const displayed = alertes.filter(a => {
    if (filtreStatut !== "Tous" && a.statut !== filtreStatut) return false;
    if (filtreEnvoi === "Envoyé" && !a.envoye_auto) return false;
    if (filtreEnvoi === "En attente" && a.envoye_auto) return false;
    return true;
  });

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626", padding: 16 }}>{error}</p>;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>
          Historique des Alertes
        </h2>
        <span style={{ fontSize: 12, color: "#64748b" }}>{alertes.length} alerte(s) au total</span>
      </div>

      {/* Filtres */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>Statut</span>
          {["Tous", "AVERTI", "EXCLU"].map(s => (
            <FilterBtn key={s} active={filtreStatut === s} onClick={() => setFiltreStatut(s)}>{s}</FilterBtn>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>Envoi</span>
          {["Tous", "Envoyé", "En attente"].map(s => (
            <FilterBtn key={s} active={filtreEnvoi === s} onClick={() => setFiltreEnvoi(s)}>{s}</FilterBtn>
          ))}
        </div>
        <span style={{ fontSize: 12, color: "#64748b", alignSelf: "center", marginLeft: "auto" }}>
          {displayed.length} résultat(s)
        </span>
      </div>

      {displayed.length === 0 && (
        <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "40px 24px", textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>Aucune alerte dans l'historique.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {displayed.map(a => (
          <div key={a.id_alerte} style={{
            backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0",
            borderRadius: 8, padding: "24px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            borderLeft: a.statut === "EXCLU" ? "4px solid #ef4444" : a.statut === "AVERTI" ? "4px solid #f59e0b" : "4px solid #8DC63F",
          }}>
            {/* En-tête */}
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "#1e293b" }}>{a.prenom} {a.nom}</span>
                  <StatutBadge statut={a.statut} />
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  {a.email}
                  {a.filiere ? ` · ${a.filiere}` : ""}
                  {a.module_nom ? ` · ${a.module_nom}` : ""}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>
                  NJ : {(a.taux_nj ?? 0).toFixed(1)}% &nbsp;|&nbsp; Total : {(a.taux_total ?? 0).toFixed(1)}%
                </div>
              </div>

              {/* Badge envoi */}
              {a.envoye_auto ? (
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: "5px 12px", borderRadius: 99, whiteSpace: "nowrap",
                  backgroundColor: "rgba(141,198,63,0.12)", border: "1px solid rgba(141,198,63,0.4)", color: "#5a9e14",
                }}>
                  ✓ Envoyé automatiquement{a.envoye_le ? ` le ${a.envoye_le.slice(0, 16)}` : ""}
                </span>
              ) : (
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: "5px 12px", borderRadius: 99,
                  backgroundColor: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.35)", color: "#d97706",
                }}>
                  ⏳ En attente
                </span>
              )}
            </div>

            {/* Aperçu email */}
            <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: "14px 16px" }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 4 }}>Sujet</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", marginBottom: 12 }}>{a.email_sujet || "—"}</div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 6 }}>Corps</div>
              <div
                style={{ fontSize: 13, lineHeight: 1.65, color: "#475569" }}
                dangerouslySetInnerHTML={{ __html: a.email_corps || "—" }}
              />
            </div>

            {a.updated_at && (
              <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 10, fontStyle: "italic" }}>
                Mise à jour : {a.updated_at.slice(0, 16)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
