const BASE = "http://localhost:5050";

export const getStats     = () => fetch(`${BASE}/api/stats`).then(r => r.json());
export const getEtudiants = () => fetch(`${BASE}/api/etudiants`).then(r => r.json());
export const getEtudiant  = (id) => fetch(`${BASE}/api/etudiant/${id}`).then(r => r.json());
export const getAlertes   = () => fetch(`${BASE}/api/alertes`).then(r => r.json());
export const postSync     = () => fetch(`${BASE}/api/sync`, { method: "POST" }).then(r => r.json());
export const getModules       = () => fetch(`${BASE}/api/modules`).then(r => r.json());
export const getFilieres      = () => fetch(`${BASE}/api/filieres`).then(r => r.json());
export const getModuleClasses = (module) => fetch(`${BASE}/api/module-classes?module=${encodeURIComponent(module)}`).then(r => r.json());

const _post = (url, body) =>
  fetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(r => r.json());

export const authCheckEmail    = (email) => _post("/api/auth/check-email", { email });
export const authRegister      = (email, password) => _post("/api/auth/register", { email, password });
export const authLogin         = (email, password) => _post("/api/auth/login", { email, password });
export const authAdminLogin    = (password) => _post("/api/auth/admin-login", { password });
export const authForgotPassword = (email) => _post("/api/auth/forgot-password", { email });
export const authResetPassword  = (token, new_password) => _post("/api/auth/reset-password", { token, new_password });
