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
