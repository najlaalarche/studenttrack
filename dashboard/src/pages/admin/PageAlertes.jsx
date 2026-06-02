import { useEffect, useState } from "react";
import { getAlertes } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

const STATUT_COLORS = {
  "En attente": { bg: "rgba(26,58,107,0.08)",  border: "rgba(26,58,107,0.25)",  color: "#1a3a6b" },
  "Validé":     { bg: "rgba(141,198,63,0.1)",  border: "rgba(141,198,63,0.35)", color: "#5a9e14" },
  "Rejeté":     { bg: "rgba(239,68,68,0.1)",   border: "rgba(239,68,68,0.3)",   color: "#dc2626" },
};

export default function PageAlertes() {
  const [alertes, setAlertes] = useState([]);
  const [statuts, setStatuts] = useState({});
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAlertes()
      .then(data => { if (data.erreur) throw new Error(); setAlertes(data); })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  function setStatut(id, val) { setStatuts(p => ({ ...p, [id]: val })); }

  if (loading) return <Spinner />;
  if (error)   return <p style={{ fontSize: 13, color: "#dc2626", padding: 16 }}>{error}</p>;
  if (!alertes.length) return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 16 }}>Alertes</h2>
      <p style={{ fontSize: 13, color: "#64748b" }}>Aucune alerte en cours.</p>
    </div>
  );

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>Alertes — Décisions IA</h2>
        <span style={{ fontSize: 12, color: "#64748b" }}>{alertes.length} alerte(s)</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {alertes.map(({ profil: p, decision: d }) => {
          const statut = statuts[p.id_etudiant] ?? "En attente";
          const sc = STATUT_COLORS[statut];
          return (
            <div key={p.id_etudiant} style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
              {/* En-tête */}
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <span style={{ fontSize: 15, fontWeight: 700, color: "#1e293b" }}>{p.prenom} {p.nom}</span>
                    <StatutBadge statut={d.action === "NOTIFY_EXCLUSION" ? "EXCLU" : "AVERTI"} />
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>{p.email} · Score {p.score_global}/100 · {p.niveau_risque}</div>
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 99, backgroundColor: sc.bg, border: `1px solid ${sc.border}`, color: sc.color }}>
                  {statut}
                </span>
              </div>

              {/* Email IA */}
              <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: "16px 18px", marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 6 }}>Sujet</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", marginBottom: 14 }}>{d.email_sujet || "—"}</div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 6 }}>Corps</div>
                <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", lineHeight: 1.65, color: "#475569", margin: 0, fontFamily: "inherit" }}>{d.email_corps || "—"}</pre>
              </div>

              <div style={{ fontSize: 11, color: "#94a3b8", fontStyle: "italic", marginBottom: 16 }}>
                IA : {d.explication || "—"} — généré le {d.genere_le}
              </div>

              {statut === "En attente" ? (
                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={() => setStatut(p.id_etudiant, "Validé")} style={{
                    padding: "8px 16px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer",
                    backgroundColor: "#8DC63F", color: "#fff", border: "none",
                  }}>✓ Valider &amp; Envoyer</button>
                  <button onClick={() => setStatut(p.id_etudiant, "Rejeté")} style={{
                    padding: "8px 16px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer",
                    backgroundColor: "transparent", color: "#dc2626", border: "1px solid rgba(239,68,68,0.4)",
                  }}>✕ Rejeter</button>
                </div>
              ) : (
                <button onClick={() => setStatut(p.id_etudiant, "En attente")} style={{
                  padding: "6px 12px", borderRadius: 6, fontSize: 11, cursor: "pointer",
                  backgroundColor: "#F8FAFC", color: "#64748b", border: "1px solid #E2E8F0",
                }}>Annuler</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
