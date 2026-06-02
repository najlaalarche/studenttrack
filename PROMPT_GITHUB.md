# StudentTrack — Push sur GitHub

Lis ce fichier entièrement puis exécute toutes les instructions dans l'ordre.

---

## ÉTAPE 1 — Créer le fichier .gitignore

Crée le fichier `.gitignore` à la racine du projet `studenttrack/` :

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.env
.venv
venv/

# Data sensible
data/dataset.xlsx
data/.last_state.json
data/*.xlsx
data/*.csv

# Logs
logs/
*.log

# Node / React
node_modules/
dashboard/dist/
dashboard/.vite/
dashboard/node_modules/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
```

---

## ÉTAPE 2 — Créer le fichier README.md

Crée le fichier `README.md` à la racine du projet :

```markdown
# StudentTrack 🎓

Système intelligent de suivi étudiant pour l'ESITH Casablanca.

Développé par le Club Cybotics — ESITH Casablanca.

## Description

StudentTrack analyse les données d'absences issues de Konosys et détecte automatiquement les étudiants en situation de risque. Il génère des alertes et des emails personnalisés via un agent IA.

## Fonctionnalités

- Lecture automatique du dataset Konosys (Excel multi-feuilles)
- Détection de delta — traite uniquement les nouvelles absences
- Calcul du taux d'absence par module (NJ et total)
- Score de risque global (absences + notes)
- Agent IA pour rédiger les emails d'alerte
- Dashboard avec 3 rôles : Étudiant, Professeur, Administration

## Règles métier

- Taux NJ >= 20% dans un module → AVERTISSEMENT
- Taux total (NJ + justifiées) >= 50% dans un module → EXCLUSION définitive
- 1 seul email par seuil franchi (anti-doublon)

## Structure

```
studenttrack/
├── config/
│   └── modules.json          # seuils configurables
├── data/
│   └── dataset.xlsx          # dataset Konosys (non versionné)
├── backend/
│   ├── ingestion/reader.py   # lecture + normalisation + delta
│   ├── analysis/engine.py    # calcul taux et statuts par module
│   ├── agent/ia_agent.py     # décision + rédaction email IA
│   └── api/app.py            # Flask API REST (port 5050)
├── dashboard/                # React + Vite + Tailwind
├── logs/
├── requirements.txt
└── README.md
```

## Installation

### Backend

```bash
pip install -r requirements.txt
python backend/api/app.py
```

L'API tourne sur http://localhost:5050

### Frontend

```bash
cd dashboard
npm install
npm run dev
```

Le dashboard tourne sur http://localhost:5173

## Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | /api/stats | KPIs globaux |
| GET | /api/etudiants | Liste tous les profils |
| GET | /api/etudiant/<id> | Profil + absences + notes |
| GET | /api/alertes | Profils en alerte + décision IA |
| GET | /api/modules | Liste des modules |
| GET | /api/filieres | Liste des filières |
| POST | /api/sync | Relit le dataset |

## Connexion dashboard

| Rôle | Comment se connecter |
|------|---------------------|
| Étudiant | Email ESITH (ex: nadia.zouiten@esith.ma) |
| Professeur | Nom + sélection du module |
| Administration | Accès direct |

## Agent IA

L'agent IA fonctionne en mode simulation par défaut.
Pour activer la vraie IA Claude :

```bash
$env:ANTHROPIC_API_KEY = "votre-clé-api"
python backend/api/app.py
```

## Technologies

- Backend : Python, Flask, Pandas
- Frontend : React, Vite, Tailwind CSS
- IA : Anthropic Claude API (optionnel)
- Données : Excel (Konosys)
```

---

## ÉTAPE 3 — Créer un fichier data/.gitkeep

Pour que le dossier `data/` soit versionné sans son contenu :

```bash
New-Item -ItemType File data/.gitkeep
```

Ajouter dans `.gitignore` une exception pour garder .gitkeep :
```
!data/.gitkeep
```

---

## ÉTAPE 4 — Initialiser Git et faire le premier commit

```bash
git init
git add .
git commit -m "feat: initial commit — StudentTrack MVP"
```

---

## ÉTAPE 5 — Pousser sur GitHub

### Option A — avec GitHub CLI (si gh est installé)
```bash
gh repo create studenttrack --public --push --source=.
```

### Option B — manuellement
1. Aller sur https://github.com/new
2. Créer un repo nommé `studenttrack` (Public, sans README)
3. Copier l'URL du repo
4. Exécuter :
```bash
git remote add origin https://github.com/TON_USERNAME/studenttrack.git
git branch -M main
git push -u origin main
```

Remplacer TON_USERNAME par le vrai nom d'utilisateur GitHub.

---

## ÉTAPE 6 — Vérifier

Ouvrir https://github.com/TON_USERNAME/studenttrack et vérifier que :
- Tous les fichiers sont présents
- Le README s'affiche correctement
- Le fichier dataset.xlsx n'est PAS présent (confidentiel)
- Le dossier node_modules n'est PAS présent

---

## NOTES IMPORTANTES

- Ne jamais versionner le fichier dataset.xlsx (données personnelles étudiants)
- Ne jamais versionner la clé API Anthropic
- Le dossier data/ est versionné vide grâce au fichier .gitkeep
