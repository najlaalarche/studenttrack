# StudentTrack — Dashboard Frontend

Lis ce fichier entièrement puis exécute toutes les instructions dans l'ordre.

---

## CONTEXTE

Le backend Flask tourne sur http://localhost:5050 en mode simulation (sans clé API).
Crée le frontend React du dashboard StudentTrack avec 3 rôles distincts.

---

## STACK

- React + Vite
- Tailwind CSS
- fetch() vers l'API Flask sur http://localhost:5050

---

## 3 RÔLES

### ÉTUDIANT
- Se connecte avec son email (prenom.nom@esith.net)
- Voit UNIQUEMENT son propre profil :
  - Absences par module avec taux NJ et taux total
  - Barre de progression avec marqueurs à 20% et 50%
  - Statut par module : AUTORISE / AVERTI / EXCLU
  - Historique de ses absences (tableau)

### PROFESSEUR
- Se connecte, choisit son module
- Voit UNIQUEMENT les étudiants de ses modules :
  - Liste étudiants avec taux absence par module
  - Qui est AVERTI / EXCLU dans son module
  - Pas accès aux autres modules

### ADMINISTRATION
- Accès complet :
  - Dashboard global : KPIs, nb alertes, nb exclus
  - Liste tous les étudiants avec score risque et statuts
  - Page alertes : emails générés par IA, boutons Valider/Rejeter
  - Page détail étudiant : modules + historique complet
  - Statut volumes horaires (confirmés ou estimés)

---

## STRUCTURE À CRÉER

```
dashboard/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── api.js                    ← toutes les fonctions fetch()
    ├── components/
    │   ├── Login.jsx             ← écran de sélection de rôle
    │   ├── Sidebar.jsx           ← navigation admin/prof
    │   ├── ModuleBar.jsx         ← barre progression avec seuils 20% et 50%
    │   ├── StatutBadge.jsx       ← badge AUTORISE/AVERTI/EXCLU
    │   └── KpiCard.jsx           ← carte KPI
    ├── pages/
    │   ├── etudiant/
    │   │   └── DashboardEtudiant.jsx
    │   ├── professeur/
    │   │   └── DashboardProfesseur.jsx
    │   └── admin/
    │       ├── DashboardAdmin.jsx
    │       ├── PageEtudiants.jsx
    │       ├── PageAlertes.jsx
    │       └── PageDetailEtudiant.jsx
    └── index.css
```

---

## FICHIER — src/api.js

Toutes les fonctions fetch vers l'API :

```javascript
const BASE = "http://localhost:5050";

export const getStats = () => fetch(`${BASE}/api/stats`).then(r => r.json());
export const getEtudiants = () => fetch(`${BASE}/api/etudiants`).then(r => r.json());
export const getEtudiant = (id) => fetch(`${BASE}/api/etudiant/${id}`).then(r => r.json());
export const getAlertes = () => fetch(`${BASE}/api/alertes`).then(r => r.json());
export const postSync = () => fetch(`${BASE}/api/sync`, { method: "POST" }).then(r => r.json());
```

---

## FICHIER — src/components/Login.jsx

Écran d'accueil avec 3 boutons de sélection de rôle.

- Titre : "StudentTrack" avec sous-titre "ESITH Casablanca"
- 3 cartes cliquables :
  - 🎓 Étudiant → affiche un champ email à saisir → bouton Connexion
  - 👨‍🏫 Professeur → affiche champ nom + liste déroulante module → bouton Connexion
  - 🏫 Administration → bouton accès direct sans saisie
- Props : `onLogin(role, data)` → appelé quand l'utilisateur se connecte

---

## FICHIER — src/components/ModuleBar.jsx

Barre de progression par module avec deux marqueurs visuels.

Props :
- `taux_nj` : float (% absences NJ)
- `taux_total` : float (% absences totales)
- `seuil_alerte` : 20
- `seuil_exclusion` : 50

Rendu :
- Barre de fond grise
- Fill orange = taux_nj
- Fill rouge superposé = taux_total (si > taux_nj)
- Ligne verticale orange à 20%
- Ligne verticale rouge à 50%
- Labels sous la barre : 0% | 20% ⚠ | 50% 🚫 | 100%

---

## FICHIER — src/components/StatutBadge.jsx

Badge coloré selon le statut.

```
AUTORISE  → fond vert   #10B981
AVERTI    → fond orange #F59E0B
EXCLU     → fond rouge  #EF4444
```

---

## FICHIER — src/pages/etudiant/DashboardEtudiant.jsx

Reçoit l'email de l'étudiant en prop.
Appelle `GET /api/etudiants` et filtre par email pour trouver l'étudiant.
Puis appelle `GET /api/etudiant/<id>` pour le détail.

Sections :
1. Header : nom, email, filière, semestre
2. Résumé : 3 KPIs (heures NJ, score risque, nb modules touchés)
3. Modules : une carte par module avec ModuleBar + StatutBadge + taux NJ + taux total
4. Historique : tableau des absences (date, module, durée, justifiée, motif)

---

## FICHIER — src/pages/professeur/DashboardProfesseur.jsx

Reçoit le module choisi en prop.
Appelle `GET /api/etudiants` et filtre par module.

Sections :
1. Header : "Module : [nom]" + nb étudiants
2. Résumé : nb AUTORISE / AVERTI / EXCLU dans ce module
3. Tableau étudiants :
   - Colonnes : Nom | Email | Taux NJ | Taux Total | Statut | Dernière absence
   - Tri par statut (EXCLU en premier)
   - Filtre par statut (boutons en haut)

---

## FICHIER — src/pages/admin/DashboardAdmin.jsx

Page principale admin avec sidebar de navigation.

Navigation sidebar :
- Vue d'ensemble
- Étudiants
- Alertes
- Synchronisation

Chaque item charge la page correspondante dans le contenu principal.

---

## FICHIER — src/pages/admin/PageEtudiants.jsx

Appelle `GET /api/etudiants`.

Tableau complet :
- Colonnes : ID | Nom | Email | Semestre | Heures NJ | Score | Risque | Modules ⚠ | Action
- Clic sur une ligne → ouvre PageDetailEtudiant
- Filtre par niveau risque (faible/modéré/critique)
- Filtre par statut module (AVERTI/EXCLU)

---

## FICHIER — src/pages/admin/PageAlertes.jsx

Appelle `GET /api/alertes`.

Pour chaque alerte :
- Carte avec : nom étudiant, score, action recommandée
- Section email IA :
  - Sujet de l'email
  - Corps de l'email (texte complet)
  - Explication de la décision IA
- Boutons : ✓ Valider & Envoyer | ✕ Rejeter
- Badge statut : En attente / Validé / Rejeté

---

## FICHIER — src/pages/admin/PageDetailEtudiant.jsx

Reçoit l'id_etudiant en prop.
Appelle `GET /api/etudiant/<id>`.

Sections :
1. Header étudiant avec StatutBadge global
2. KPIs : heures NJ, heures just., total absences, score
3. Tabs : Modules | Historique
   - Tab Modules : carte par module avec ModuleBar, taux NJ, taux total, statut, seuils
   - Tab Historique : tableau de toutes les absences

---

## DESIGN

```
Couleurs :
  bg:       #0B0F1A
  surface:  #111827
  card:     #1A2235
  border:   #1F2D45
  blue:     #3B82F6
  green:    #10B981   ← AUTORISE
  orange:   #F59E0B   ← AVERTI
  red:      #EF4444   ← EXCLU
  text:     #F1F5F9
  sub:      #94A3B8
  muted:    #475569

Font : DM Sans (Google Fonts)
Border radius : 12px pour les cartes
Sidebar : fixe à gauche, 220px de large
```

---

## GESTION DES ERREURS

- Si l'API ne répond pas → afficher "Connexion au serveur impossible. Vérifiez que le backend tourne sur le port 5050."
- Si étudiant non trouvé → "Aucun étudiant trouvé avec cet email."
- Loading state sur tous les appels API (spinner ou skeleton)

---

## INSTRUCTIONS D'EXÉCUTION

1. Crée le dossier `dashboard/` dans `studenttrack/`
2. Initialise le projet : `npm create vite@latest . -- --template react`
3. Installe les dépendances : `npm install` puis `npm install -D tailwindcss postcss autoprefixer` puis `npx tailwindcss init -p`
4. Configure Tailwind dans `tailwind.config.js` et `index.css`
5. Crée tous les fichiers dans l'ordre indiqué
6. Lance : `npm run dev`
7. Vérifie que l'app s'ouvre sur http://localhost:5173
8. Teste les 3 rôles : étudiant, professeur, administration
