import { useEffect, useState, useCallback } from "react";

const BASE = "http://localhost:5050";

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
const MSG_STYLE = {
  success: { bg: "#f0fdf4", border: "#bbf7d0", color: "#166534" },
  error:   { bg: "#fef2f2", border: "#fecaca", color: "#dc2626" },
};

function genEmail(prenom, nom) {
  const clean = s =>
    s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  return prenom && nom ? `${clean(prenom)}.${clean(nom)}@esith.net` : "";
}

function ModuleSelector({ allModules, selectedIds, onToggle, search, onSearchChange }) {
  const q = search.toLowerCase();
  const filtered = q
    ? allModules.filter(m => m.nom.toLowerCase().includes(q) || (m.filiere || "").toLowerCase().includes(q))
    : allModules;

  const byFiliere = {};
  for (const m of filtered) {
    const key = m.filiere || "(sans filière)";
    if (!byFiliere[key]) byFiliere[key] = [];
    byFiliere[key].push(m);
  }

  return (
    <div style={{ border: "1px solid #E2E8F0", borderRadius: 6, maxHeight: 280, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "8px 10px", borderBottom: "1px solid #E2E8F0", flexShrink: 0 }}>
        <input
          placeholder="Filtrer par nom de module ou filière…"
          value={search}
          onChange={e => onSearchChange(e.target.value)}
          style={{ ...INPUT, fontSize: 12, padding: "6px 10px" }}
        />
      </div>
      <div style={{ overflowY: "auto", flex: 1 }}>
        {Object.keys(byFiliere).length === 0 ? (
          <div style={{ padding: "16px 14px", fontSize: 12, color: "#94a3b8", textAlign: "center" }}>Aucun module trouvé</div>
        ) : (
          Object.entries(byFiliere).sort(([a], [b]) => a.localeCompare(b)).map(([filiere, mods]) => (
            <div key={filiere}>
              <div style={{ padding: "5px 12px", fontSize: 10, fontWeight: 700, color: "#64748b", textTransform: "uppercase", background: "#F8FAFC", letterSpacing: "0.06em", borderBottom: "1px solid #F1F5F9" }}>
                {filiere}
              </div>
              {mods.map(m => (
                <label key={m.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 16px", cursor: "pointer", fontSize: 12, color: "#1e293b" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#F8FAFC"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(m.id)}
                    onChange={() => onToggle(m.id)}
                    style={{ cursor: "pointer", accentColor: "#1a3a6b" }}
                  />
                  <span>{m.nom}</span>
                  {m.semestre && m.semestre !== "S0" && (
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>{m.semestre}</span>
                  )}
                </label>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function PageGestionProfesseurs() {
  const [allModules, setAllModules]               = useState([]);
  const [form, setForm]                           = useState({ nom: "", prenom: "" });
  const [selectedModuleIds, setSelectedModuleIds] = useState(new Set());
  const [moduleSearch, setModuleSearch]           = useState("");
  const [editingId, setEditingId]                 = useState(null);
  const [expandedId, setExpandedId]               = useState(null);
  const [msg, setMsg]                             = useState(null);
  const [saving, setSaving]                       = useState(false);
  const [resettingId, setResettingId]             = useState(null);
  const [liste, setListe]                         = useState([]);
  const [search, setSearch]                       = useState("");
  const [loading, setLoading]                     = useState(true);

  useEffect(() => {
    fetch(`${BASE}/api/modules/all`)
      .then(r => r.json())
      .then(data => setAllModules(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  const loadList = useCallback(() => {
    setLoading(true);
    fetch(`${BASE}/api/professeurs`)
      .then(r => r.json())
      .then(data => setListe(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  const filteredListe = liste.filter(p =>
    !search ||
    `${p.prenom} ${p.nom}`.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  const emailGenere = genEmail(form.prenom, form.nom);

  function resetForm() {
    setForm({ nom: "", prenom: "" });
    setSelectedModuleIds(new Set());
    setModuleSearch("");
    setEditingId(null);
  }

  function handleEdit(prof) {
    setForm({ nom: prof.nom, prenom: prof.prenom });
    setSelectedModuleIds(new Set(prof.modules.map(m => m.id)));
    setModuleSearch("");
    setEditingId(prof.id);
    setMsg(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toggleModule(id) {
    setSelectedModuleIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.nom.trim() || !form.prenom.trim()) {
      setMsg({ type: "error", text: "Nom et prénom sont requis." });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      const body   = { nom: form.nom.trim(), prenom: form.prenom.trim(), module_ids: [...selectedModuleIds] };
      const url    = editingId ? `${BASE}/api/professeurs/${editingId}` : `${BASE}/api/professeurs/ajouter`;
      const method = editingId ? "PUT" : "POST";
      const res    = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(r => r.json());

      if (res.success) {
        const extra = !editingId && res.email_envoye
          ? ` — un email avec ses identifiants a été envoyé à ${res.professeur?.email}`
          : !editingId && !res.email_envoye
          ? ` — ⚠ Email non envoyé (vérifiez la configuration Brevo)`
          : "";
        setMsg({
          type: "success",
          text: editingId
            ? "✓ Professeur modifié avec succès."
            : `✓ Professeur ajouté : ${form.prenom} ${form.nom}${extra}`,
        });
        resetForm();
        loadList();
      } else {
        setMsg({ type: "error", text: res.error || "Erreur lors de l'enregistrement" });
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de connexion au serveur." });
    } finally {
      setSaving(false);
    }
  }

  async function handleResetPassword(prof) {
    if (!window.confirm(`Réinitialiser le mot de passe de ${prof.prenom} ${prof.nom} et envoyer un email ?`)) return;
    setResettingId(prof.id);
    try {
      const res = await fetch(`${BASE}/api/professeurs/${prof.id}/reset-password`, { method: "POST" }).then(r => r.json());
      if (res.success) {
        setMsg({
          type: "success",
          text: res.email_envoye
            ? `✓ Nouveau mot de passe envoyé à ${prof.email}`
            : `✓ Mot de passe réinitialisé — ⚠ email non envoyé (vérifiez Brevo)`,
        });
      } else {
        setMsg({ type: "error", text: res.error || "Erreur lors de la réinitialisation" });
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de connexion." });
    } finally {
      setResettingId(null);
    }
  }

  async function handleDelete(prof) {
    if (!window.confirm(`Supprimer ${prof.prenom} ${prof.nom} et retirer tous ses modules ?`)) return;
    try {
      const res = await fetch(`${BASE}/api/professeurs/${prof.id}`, { method: "DELETE" }).then(r => r.json());
      if (res.success) {
        setMsg({ type: "success", text: `✓ ${prof.prenom} ${prof.nom} supprimé.` });
        if (editingId === prof.id) resetForm();
        loadList();
      } else {
        setMsg({ type: "error", text: res.error || "Erreur de suppression." });
      }
    } catch {
      setMsg({ type: "error", text: "Erreur de connexion." });
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1a3a6b", marginBottom: 24 }}>Gestion des Professeurs</h2>

      {/* Formulaire */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: 24, marginBottom: 28, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", maxWidth: 560 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#1a3a6b", margin: "0 0 18px" }}>
          {editingId ? "Modifier le professeur" : "Ajouter un professeur"}
        </h3>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={LABEL}>Nom</label>
              <input style={INPUT} placeholder="ex: Bennani" value={form.nom}
                onChange={e => setForm(f => ({ ...f, nom: e.target.value }))} />
            </div>
            <div>
              <label style={LABEL}>Prénom</label>
              <input style={INPUT} placeholder="ex: Khalid" value={form.prenom}
                onChange={e => setForm(f => ({ ...f, prenom: e.target.value }))} />
            </div>
          </div>

          {/* Email auto-généré */}
          <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: "10px 14px" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "#64748b" }}>Email généré (lecture seule) : </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#1a3a6b" }}>{emailGenere || "—"}</span>
          </div>

          {/* Info mot de passe */}
          {!editingId && (
            <div style={{ backgroundColor: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 6, padding: "10px 14px", fontSize: 12, color: "#1d4ed8" }}>
              ℹ Un mot de passe aléatoire sera généré automatiquement et envoyé par email au professeur.
            </div>
          )}

          <div>
            <label style={LABEL}>
              Modules enseignés
              {selectedModuleIds.size > 0 && (
                <span style={{ marginLeft: 8, fontWeight: 700, color: "#1a3a6b" }}>
                  ({selectedModuleIds.size} sélectionné{selectedModuleIds.size > 1 ? "s" : ""})
                </span>
              )}
            </label>
            {allModules.length === 0 ? (
              <div style={{ fontSize: 12, color: "#dc2626" }}>⚠ Impossible de charger les modules — vérifiez que le backend est démarré</div>
            ) : (
              <ModuleSelector
                allModules={allModules}
                selectedIds={selectedModuleIds}
                onToggle={toggleModule}
                search={moduleSearch}
                onSearchChange={setModuleSearch}
              />
            )}
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="submit" disabled={saving} style={{
              padding: "9px 18px", borderRadius: 6, fontSize: 13, fontWeight: 600,
              cursor: saving ? "not-allowed" : "pointer",
              backgroundColor: saving ? "#a0aec0" : "#1a3a6b", color: "#fff", border: "none",
            }}>
              {saving ? "Enregistrement…" : editingId ? "Enregistrer les modifications" : "Ajouter le professeur"}
            </button>
            {editingId && (
              <button type="button" onClick={resetForm} style={{
                padding: "9px 14px", borderRadius: 6, fontSize: 13, cursor: "pointer",
                backgroundColor: "transparent", color: "#64748b", border: "1px solid #E2E8F0",
              }}>
                Annuler
              </button>
            )}
          </div>
        </form>

        {msg && (
          <div style={{
            marginTop: 14, padding: "10px 14px", borderRadius: 6, fontSize: 13,
            backgroundColor: MSG_STYLE[msg.type]?.bg,
            border: `1px solid ${MSG_STYLE[msg.type]?.border}`,
            color: MSG_STYLE[msg.type]?.color,
          }}>
            {msg.text}
          </div>
        )}
      </div>

      {/* Tableau */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "#1a3a6b", margin: 0 }}>Professeurs enregistrés</h3>
          <span style={{ fontSize: 12, color: "#64748b" }}>{liste.length} au total</span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher par nom ou email…"
            style={{ ...INPUT, maxWidth: 240, marginLeft: "auto" }}
          />
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: "center" }}>
            <div style={{ width: 20, height: 20, border: "2px solid #E2E8F0", borderTop: "2px solid #1a3a6b", borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Nom / Prénom", "Email", "Modules", "Actions"].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredListe.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>
                      {liste.length === 0 ? "Aucun professeur enregistré" : "Aucun résultat"}
                    </td>
                  </tr>
                ) : filteredListe.map((prof, i) => (
                  <>
                    <tr key={prof.id} style={{ backgroundColor: i % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                      <td style={S.td}>
                        <div style={{ fontWeight: 600 }}>{prof.prenom} {prof.nom}</div>
                      </td>
                      <td style={{ ...S.td, fontSize: 12, color: "#64748b" }}>{prof.email}</td>
                      <td style={S.td}>
                        <button
                          onClick={() => setExpandedId(expandedId === prof.id ? null : prof.id)}
                          style={{
                            padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer",
                            border: "1px solid #E2E8F0",
                            backgroundColor: expandedId === prof.id ? "#eef2fb" : "transparent",
                            color: "#1a3a6b",
                          }}
                        >
                          {prof.modules.length} module{prof.modules.length !== 1 ? "s" : ""} {expandedId === prof.id ? "▲" : "▼"}
                        </button>
                      </td>
                      <td style={S.td}>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button onClick={() => handleEdit(prof)}
                            style={{ padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer", backgroundColor: "transparent", color: "#1a3a6b", border: "1px solid rgba(26,58,107,0.35)" }}>
                            Modifier
                          </button>
                          <button
                            onClick={() => handleResetPassword(prof)}
                            disabled={resettingId === prof.id}
                            style={{ padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: resettingId === prof.id ? "not-allowed" : "pointer", backgroundColor: "transparent", color: "#d97706", border: "1px solid rgba(217,119,6,0.35)" }}>
                            {resettingId === prof.id ? "Envoi…" : "Réinit. mot de passe"}
                          </button>
                          <button onClick={() => handleDelete(prof)}
                            style={{ padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer", backgroundColor: "transparent", color: "#dc2626", border: "1px solid rgba(239,68,68,0.35)" }}>
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedId === prof.id && (
                      <tr key={`${prof.id}-modules`} style={{ backgroundColor: "#F0F4FF" }}>
                        <td colSpan={4} style={{ ...S.td, paddingTop: 10, paddingBottom: 10 }}>
                          {prof.modules.length === 0 ? (
                            <span style={{ fontSize: 12, color: "#94a3b8" }}>Aucun module assigné</span>
                          ) : (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                              {prof.modules.map(m => (
                                <span key={m.id} style={{
                                  fontSize: 11, padding: "3px 9px", borderRadius: 99,
                                  backgroundColor: "#e0e7ff", color: "#3730a3",
                                  fontWeight: 600, border: "1px solid #c7d2fe",
                                }}>
                                  {m.nom}{m.semestre && m.semestre !== "S0" ? ` · ${m.semestre}` : ""}{m.filiere ? ` · ${m.filiere}` : ""}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
