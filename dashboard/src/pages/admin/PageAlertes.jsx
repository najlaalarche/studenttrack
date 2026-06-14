import { useEffect, useState } from "react";
import { getAlertes } from "../../api.js";
import StatutBadge from "../../components/StatutBadge.jsx";

const BASE = "http://localhost:5050";

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
      <div style={{ width: 24, height: 24, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  );
}

function BtnSpinner() {
  return (
    <span style={{ display: "inline-block", width: 12, height: 12, border: "2px solid rgba(255,255,255,0.4)", borderTop: "2px solid #fff", borderRadius: "50%", animation: "spin 0.6s linear infinite", marginRight: 6 }} />
  );
}

export default function PageAlertes() {
  const [alertes, setAlertes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  // actions : { [id_alerte]: { loading, statut, envoye_le, error } }
  const [actions, setActions] = useState({});

  useEffect(() => {
    getAlertes()
      .then(data => {
        if (data.erreur) throw new Error();
        setAlertes(data);
        const init = {};
        for (const a of data) {
          if (a.id_alerte != null) {
            init[a.id_alerte] = {
              loading:   false,
              statut:    a.statut_validation || "en_attente",
              envoye_le: a.envoye_le || null,
              error:     null,
            };
          }
        }
        setActions(init);
      })
      .catch(() => setError("Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."))
      .finally(() => setLoading(false));
  }, []);

  function setAction(id, patch) {
    setActions(prev => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }

  async function handleValider(id_alerte, email_sujet, email_corps) {
    setAction(id_alerte, { loading: true, error: null });
    try {
      const res = await fetch(`${BASE}/api/alertes/${id_alerte}/valider`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email_sujet, email_corps }),
      }).then(r => r.json());

      if (res.success) {
        setAction(id_alerte, { loading: false, statut: "envoye", envoye_le: res.envoye_le, error: null });
      } else {
        setAction(id_alerte, { loading: false, error: res.error || "Échec de l'envoi" });
      }
    } catch {
      setAction(id_alerte, { loading: false, error: "Erreur de connexion au serveur" });
    }
  }

  async function handleRejeter(id_alerte) {
    setAction(id_alerte, { loading: true, error: null });
    try {
      await fetch(`${BASE}/api/alertes/${id_alerte}/rejeter`, { method: "POST" });
      setAction(id_alerte, { loading: false, statut: "rejete", envoye_le: null, error: null });
    } catch {
      setAction(id_alerte, { loading: false, error: "Erreur de connexion au serveur" });
    }
  }

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
        {alertes.map(({ profil: p, decision: d, id_alerte }) => {
          const act     = actions[id_alerte] || { loading: false, statut: "en_attente", envoye_le: null, error: null };
          const isTraite = act.statut === "envoye" || act.statut === "rejete";

          return (
            <div key={id_alerte ?? p.id_etudiant} style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>

              {/* En-tête */}
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <span style={{ fontSize: 15, fontWeight: 700, color: "#1e293b" }}>{p.prenom} {p.nom}</span>
                    <StatutBadge statut={d.action === "NOTIFY_EXCLUSION" ? "EXCLU" : "AVERTI"} />
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>{p.email} · Score {p.score_global}/100 · {p.niveau_risque}</div>
                </div>

                {/* Badge état validation */}
                {act.statut === "envoye" && (
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 99, backgroundColor: "rgba(141,198,63,0.1)", border: "1px solid rgba(141,198,63,0.35)", color: "#5a9e14", whiteSpace: "nowrap" }}>
                    ✓ Envoyé {act.envoye_le ? `le ${act.envoye_le.slice(0, 16)}` : ""}
                  </span>
                )}
                {act.statut === "rejete" && (
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 99, backgroundColor: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.25)", color: "#dc2626" }}>
                    ✕ Rejeté
                  </span>
                )}
                {act.statut === "en_attente" && (
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 99, backgroundColor: "rgba(26,58,107,0.08)", border: "1px solid rgba(26,58,107,0.25)", color: "#1a3a6b" }}>
                    En attente
                  </span>
                )}
              </div>

              {/* Email IA */}
              <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: "16px 18px", marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 6 }}>Sujet</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", marginBottom: 14 }}>{d.email_sujet || "—"}</div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 6 }}>Corps</div>
                <div
                  style={{ fontSize: 13, lineHeight: 1.65, color: "#475569" }}
                  dangerouslySetInnerHTML={{ __html: d.email_corps || "—" }}
                />
              </div>

              <div style={{ fontSize: 11, color: "#94a3b8", fontStyle: "italic", marginBottom: 16 }}>
                IA : {d.explication || "—"} — généré le {d.genere_le}
              </div>

              {/* Message d'erreur */}
              {act.error && (
                <div style={{ fontSize: 12, color: "#dc2626", backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, padding: "8px 12px", marginBottom: 12 }}>
                  {act.error}
                </div>
              )}

              {/* Boutons */}
              {!isTraite ? (
                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    onClick={() => handleValider(id_alerte, d.email_sujet, d.email_corps)}
                    disabled={act.loading || id_alerte == null}
                    style={{
                      display: "flex", alignItems: "center",
                      padding: "8px 16px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: act.loading ? "not-allowed" : "pointer",
                      backgroundColor: act.loading ? "#a0aec0" : "#8DC63F", color: "#fff", border: "none",
                    }}
                  >
                    {act.loading ? <><BtnSpinner />Envoi…</> : "✓ Valider & Envoyer"}
                  </button>
                  <button
                    onClick={() => handleRejeter(id_alerte)}
                    disabled={act.loading || id_alerte == null}
                    style={{
                      padding: "8px 16px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: act.loading ? "not-allowed" : "pointer",
                      backgroundColor: "transparent", color: "#dc2626", border: "1px solid rgba(239,68,68,0.4)",
                    }}
                  >
                    ✕ Rejeter
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setAction(id_alerte, { statut: "en_attente", envoye_le: null, error: null })}
                  style={{ padding: "6px 12px", borderRadius: 6, fontSize: 11, cursor: "pointer", backgroundColor: "#F8FAFC", color: "#64748b", border: "1px solid #E2E8F0" }}
                >
                  Modifier
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
