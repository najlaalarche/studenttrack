const BASE = "http://localhost:5050";

export const getStats     = () => fetch(`${BASE}/api/stats`).then(r => r.json());
export const getEtudiants = () => fetch(`${BASE}/api/etudiants`).then(r => r.json());
export const getEtudiant  = (id) => fetch(`${BASE}/api/etudiant/${id}`).then(r => r.json());
export const getAlertes   = () => fetch(`${BASE}/api/alertes`).then(r => r.json());
export const postSync     = () => fetch(`${BASE}/api/sync`, { method: "POST" }).then(r => r.json());
export const getModules   = () => fetch(`${BASE}/api/modules`).then(r => r.json());
export const getFilieres  = () => fetch(`${BASE}/api/filieres`).then(r => r.json());
