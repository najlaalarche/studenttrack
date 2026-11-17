const BASE = "http://localhost:5050";

// ── JWT ─────────────────────────────────────────────────────────────────────
// Le token reçu à la connexion est gardé dans localStorage et joint à chaque appel.
const TOKEN_KEY   = "studenttrack_token";
const SESSION_KEY = "studenttrack_session";  // même clé que App.jsx

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
  try { if (token) localStorage.setItem(TOKEN_KEY, token); } catch { /* stockage indisponible */ }
}

export function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* stockage indisponible */ }
}

// fetch + "Authorization: Bearer <token>". Un 401 hors /api/auth/ (token absent, invalide ou
// expiré) ferme la session et renvoie à l'écran de connexion.
export async function apiFetch(url, options = {}) {
  const token   = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && !url.includes("/api/auth/")) {
    clearToken();
    try { localStorage.removeItem(SESSION_KEY); } catch { /* stockage indisponible */ }
    window.location.href = "/";
    return new Promise(() => {});  // la page se recharge : on ne rend pas la main à l'appelant
  }
  return res;
}

const _get = (path) => apiFetch(`${BASE}${path}`).then(r => r.json());

export const getStats     = () => _get(`/api/stats`);
export const getStatsTauxAbsence = () => _get(`/api/stats/taux-absence`);
export const getStatsParFiliere   = () => _get(`/api/stats/par-filiere`);
export const getEtudiants = () => _get(`/api/etudiants`);
export const getEtudiant  = (id) => _get(`/api/etudiant/${id}`);
export const getTauxAbsence = (id) => _get(`/api/etudiant/${id}/taux-absence`);
// null si aucune moyenne brute/nette importée (404)
export const getPerformance = (id) => apiFetch(`${BASE}/api/etudiant/${id}/performance`).then(r => r.ok ? r.json() : null);
export const getAlertes   = () => _get(`/api/alertes`);
export const postSync     = () => apiFetch(`${BASE}/api/sync`, { method: "POST" }).then(r => r.json());
export const getModules       = () => _get(`/api/modules`);
export const getFilieres      = () => _get(`/api/filieres`);
export const getModuleClasses = (module) => _get(`/api/module-classes?module=${encodeURIComponent(module)}`);
// [{ semaine: "1", heures }] — heures d'absence d'un module, toutes les semaines du semestre (1 ou 2)
export const getAbsencesParSemaine = (module, filiere, semestre) =>
  _get(`/api/absences/par-semaine?module=${encodeURIComponent(module)}&filiere=${encodeURIComponent(filiere)}&semestre=${semestre}`);

// { ajoutes, comptes_crees, ignores, erreurs[], emails_envoyes, emails_echoues[] } — emails envoyés par Brevo
export const importEtudiantsCsv = (file) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch(`${BASE}/api/etudiants/import-csv`, { method: "POST", body }).then(r => r.json());
};

export const importProfesseursCsv = (file) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch(`${BASE}/api/professeurs/import-csv`, { method: "POST", body }).then(r => r.json());
};

const _post = (url, body) =>
  apiFetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(r => r.json());

// { analyse } — en cas d'indisponibilité, analyse contient le message d'erreur
export const postAnalyseIA      = (role, data) => _post("/api/ia/analyse", { role, data });
export const authCheckEmail    = (email) => _post("/api/auth/check-email", { email });
// Les 3 connexions renvoient un JWT : il est mémorisé ici
const _login = (url, body) => _post(url, body).then(res => { if (res?.success) setToken(res.token); return res; });

export const authLogin         = (email, password) => _login("/api/auth/login", { email, password });
export const authAdminLogin    = (password) => _login("/api/auth/admin-login", { password });
export const authForgotPassword = (email) => _post("/api/auth/forgot-password", { email });
export const authResetPassword  = (token, new_password) => _post("/api/auth/reset-password", { token, new_password });
// Changement du mot de passe temporaire : renvoie un nouveau token sans restriction
export const authChangePassword = (current_password, new_password) =>
  _login("/api/auth/change-password", { current_password, new_password });

export const authProfesseurLogin = (email, password) =>
  _login("/api/auth/professeur-login", { email, password });
