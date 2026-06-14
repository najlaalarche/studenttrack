import { useEffect, useState, useCallback } from "react";

const BASE = "http://localhost:5050";
const LIMIT = 20;

const INPUT = {
  width: "100%", padding: "8px 12px", borderRadius: 6, fontSize: 13,
  border: "1px solid #E2E8F0", outline: "none", color: "#1e293b",
  backgroundColor: "#fff", boxSizing: "border-box",
};
const LABEL = { fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 4, display: "block" };
const S = {
  th: { padding: "10px 14px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td: { padding: "11px 14px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

function StatutBadge({ statut }) {
  const cfg = {
    EXCLU:    { bg: "rgba(239,68,68,0.1)",   border: "rgba(239,68,68,0.3)",   color: "#dc2626" },
    AVERTI:   { bg: "rgba(245,158,11,0.1)",  border: "rgba(245,158,11,0.3)",  color: "#d97706" },
    AUTORISE: { bg: "rgba(141,198,63,0.08)", border: "rgba(141,198,63,0.3)",  color: "#5a9e14" },
  }[statut] || { bg: "#f1f5f9", border: "#e2e8f0", color: "#64748b" };
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 99, backgroundColor: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color, textTransform: "uppercase" }}>
      {statut}
    </span>
  );
}

function genEmail(prenom, nom) {
  const clean = s => s.toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  return prenom && nom ? `${clean(prenom)}.${clean(nom)}@esith.net` : "";
}

export default function PageGestionEtudiants() {
  const [sessions, setSessions] = useState([]);
  const [form, setForm]   = useState({ nom: "", prenom: "", id_inscr: "", session: "", cursus: "" });
  const [msg, setMsg]     = useState(null);
  const [saving, setSaving] = useState(false);

  const [liste, setListe]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState("");
  const [loadingList, setLoadingList] = useState(true);

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));
  const emailGenere = genEmail(form.prenom, form.nom);

  useEffect(() => {
    fetch(`${BASE}/api/sessions-programme`)
      .then(r => r.json()).then(setSessions).catch(() => {});
  }, []);

  const loadList = useCallback(() => {
    setLoadingList(true);
    fetch(`${BASE}/api/etudiants/paginated?page=${page}&limit=${LIMIT}&search=${encodeURIComponent(search)}`)
      .then(r => r.json())
      .then(data => { setListe(data.etudiants || []); setTotal(data.total || 0); })
      .catch(() => {})
      .finally(() => setLoadingList(false));
  }, [page, search]);

  useEffect(() => { loadList(); }, [loadList]);

  function field(key) {
    return {
      value: form[key],
      onChange: e => setForm(prev => ({ ...prev, [key]: e.target.value })),
    };
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.nom.trim() || !form.prenom.trim()) {
      setMsg({ type: "error", text: "Nom et prénom sont requis." });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      const res = await fetch(`${BASE}/api/etudiants/ajouter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nom: form.nom.trim(),
          prenom: form.prenom.trim(),
          id_inscriptionsessionprogramme: form.id_inscr.trim(),
          session_programme: form.session,
          cursus: form.cursus.trim(),
        }),
      }).then(r => r.json());

      if (res.exists) {
        const et = res.etudiant_existant;
        setMsg({
          type: "warn",
          text: `⚠ Cet ID existe déjà pour ${et.prenom} ${et.nom}.`,
          existant: et,
        });
      } else if (res.success) {
        const et = res.etudiant;
        setMsg({ type: "success", text: `✓ Étudiant ajouté : ${et.prenom} ${et.nom} (${et.email})` });
        setForm({ nom: "", prenom: "", id_inscr: "", session: "", cursus: "" });
        setPage(1);
        loadList();
      } else {
        setMsg({ type: "error", text: res.error || "Erreur lors de l'ajout" });
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de connexion au serveur." });
    } finally {
      setSaving(false);
    }
  }

  async function handleForceUpdate(existant) {
    setSaving(true);
    try {
      const res = await fetch(`${BASE}/api/etudiants/${existant.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nom: form.nom.trim(),
          prenom: form.prenom.trim(),
          session_programme: form.session,
          cursus: form.cursus.trim(),
        }),
      }).then(r => r.json());
      if (res.success) {
        setMsg({ type: "success", text: `✓ Étudiant mis à jour (ID ${existant.id})` });
        setForm({ nom: "", prenom: "", id_inscr: "", session: "", cursus: "" });
        loadList();
      } else {
        setMsg({ type: "error", text: res.error || "Erreur de mise à jour" });
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de connexion." });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(et) {
    if (!window.confirm(`Supprimer ${et.prenom} ${et.nom} et toutes ses absences/alertes ?`)) return;
    try {
      const res = await fetch(`${BASE}/api/etudiants/${et.id}`, { method: "DELETE" }).then(r => r.json());
      if (res.success) {
        setMsg({ type: "success", text: `✓ ${et.prenom} ${et.nom} supprimé.` });
        loadList();
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de suppression." });
    }
  }

  const msgStyle = {
    success: { bg: "#f0fdf4", border: "#bbf7d0", color: "#166534" },
    error:   { bg: "#fef2f2", border: "#fecaca", color: "#dc2626" },
    warn:    { bg: "#fffbeb", border: "#fde68a", color: "#92400e" },
  };

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 24 }}>Gestion des Étudiants</h2>

      {/* Formulaire d'ajout */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24, marginBottom: 28, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", maxWidth: 520 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#1a3a6b", marginBottom: 18, margin: "0 0 18px" }}>Ajouter un étudiant</h3>
        <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={LABEL}>Nom</label>
              <input style={INPUT} placeholder="ex: Larche" {...field("nom")} />
            </div>
            <div>
              <label style={LABEL}>Prénom</label>
              <input style={INPUT} placeholder="ex: Najlaa" {...field("prenom")} />
            </div>
          </div>

          <div>
            <label style={LABEL}>ID inscription (Konosys)</label>
            <input style={INPUT} placeholder="ex: 90001" {...field("id_inscr")} />
          </div>

          <div>
            <label style={LABEL}>Session Programme</label>
            <select
              style={{ ...INPUT, cursor: "pointer" }}
              value={form.session}
              onChange={e => setForm(prev => ({ ...prev, session: e.target.value }))}
            >
              <option value="">— Sélectionner —</option>
              {sessions.map(s => <option key={s} value={s}>{s}</option>)}
              <option value="__autre__">Autre…</option>
            </select>
            {form.session === "__autre__" && (
              <input
                style={{ ...INPUT, marginTop: 6 }}
                placeholder="Saisir manuellement"
                onChange={e => setForm(prev => ({ ...prev, session: e.target.value }))}
              />
            )}
          </div>

          <div>
            <label style={LABEL}>Cursus</label>
            <input style={INPUT} placeholder="ex: S3-BDM2G2" {...field("cursus")} />
          </div>

          <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: "10px 14px" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "#64748b" }}>Email généré (lecture seule) : </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#1a3a6b" }}>{emailGenere || "—"}</span>
          </div>

          <button
            type="submit"
            disabled={saving}
            style={{
              padding: "9px 18px", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
              backgroundColor: saving ? "#a0aec0" : "#1a3a6b", color: "#fff", border: "none", alignSelf: "flex-start",
            }}
          >
            {saving ? "Ajout en cours…" : "Ajouter l'étudiant"}
          </button>
        </form>

        {/* Message retour */}
        {msg && (
          <div style={{
            marginTop: 14, padding: "10px 14px", borderRadius: 6, fontSize: 13,
            backgroundColor: msgStyle[msg.type]?.bg,
            border: `1px solid ${msgStyle[msg.type]?.border}`,
            color: msgStyle[msg.type]?.color,
          }}>
            {msg.text}
            {msg.existant && (
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button
                  onClick={() => handleForceUpdate(msg.existant)}
                  style={{ padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer", backgroundColor: "#d97706", color: "#fff", border: "none" }}
                >
                  Mettre à jour quand même
                </button>
                <button
                  onClick={() => setMsg(null)}
                  style={{ padding: "5px 12px", borderRadius: 6, fontSize: 12, cursor: "pointer", backgroundColor: "transparent", color: "#64748b", border: "1px solid #e2e8f0" }}
                >
                  Annuler
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tableau étudiants */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>Étudiants enregistrés</h3>
          <span style={{ fontSize: 12, color: "#64748b" }}>{total} au total</span>
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            placeholder="Rechercher par nom ou email…"
            style={{ ...INPUT, maxWidth: 240, marginLeft: "auto" }}
          />
        </div>

        {loadingList ? (
          <div style={{ padding: 40, textAlign: "center" }}>
            <div style={{ width: 20, height: 20, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["ID", "Nom / Email", "Session / Cursus", "Filière", "Statut", "Action"].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {liste.length === 0 ? (
                  <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucun étudiant trouvé</td></tr>
                ) : liste.map((et, i) => (
                  <tr key={et.id} style={{ backgroundColor: i % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                    <td style={{ ...S.td, color: "#94a3b8", fontSize: 12 }}>{et.id}</td>
                    <td style={S.td}>
                      <div style={{ fontWeight: 600 }}>{et.prenom} {et.nom}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{et.email}</div>
                    </td>
                    <td style={{ ...S.td, fontSize: 12, color: "#64748b" }}>
                      <div>{et.session_programme || "—"}</div>
                      {et.cursus && <div style={{ color: "#94a3b8" }}>{et.cursus}</div>}
                    </td>
                    <td style={{ ...S.td, fontSize: 12, color: "#64748b" }}>
                      {et.filiere || "—"}{et.niveau ? ` · ${et.niveau}` : ""}
                    </td>
                    <td style={S.td}><StatutBadge statut={et.statut_global} /></td>
                    <td style={S.td}>
                      <button
                        onClick={() => handleDelete(et)}
                        style={{ padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer", backgroundColor: "transparent", color: "#dc2626", border: "1px solid rgba(239,68,68,0.35)" }}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              style={{ padding: "4px 10px", borderRadius: 6, fontSize: 12, cursor: page === 1 ? "not-allowed" : "pointer", backgroundColor: "#fff", border: "1px solid #E2E8F0", color: page === 1 ? "#94a3b8" : "#1a3a6b" }}>
              ‹ Préc.
            </button>
            <span style={{ fontSize: 12, color: "#64748b" }}>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              style={{ padding: "4px 10px", borderRadius: 6, fontSize: 12, cursor: page === totalPages ? "not-allowed" : "pointer", backgroundColor: "#fff", border: "1px solid #E2E8F0", color: page === totalPages ? "#94a3b8" : "#1a3a6b" }}>
              Suiv. ›
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
