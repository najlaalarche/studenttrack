# StudentTrack — Instructions pour Claude Code

Lis ce fichier entièrement puis exécute toutes les instructions dans l'ordre.

---

## CONTEXTE

Projet Python : **StudentTrack** — système intelligent de suivi étudiant pour l'ESITH Casablanca.

L'école utilise Konosys pour gérer les absences. On reçoit un dataset Excel mis à jour régulièrement avec les colonnes :
`id_absence, Nom, Prenom, Seance, DATE, Heure, Duree, DureeDecimal, SessionProgramme, Cursus, Module, Excuse, Motif, id_inscriptionsessionprogramme`

- `Excuse` = "Oui" / "Non"
- `DureeDecimal` = heures décimales (1.5, 3.0...)
- `id_inscriptionsessionprogramme` = identifiant unique étudiant
- Email généré : `prenom.nom@esith.net` (tout en minuscules)

---

## RÈGLES MÉTIER

### Statut par module — deux calculs indépendants

```
taux_nj    = heures_NJ / volume_module * 100
taux_total = (heures_NJ + heures_justifiees) / volume_module * 100

si taux_total >= 50% → EXCLU   (définitif, justifié ou non)
si taux_nj    >= 20% → AVERTI  (peut encore régulariser dans Konosys)
sinon                → AUTORISE
```

### Emails — anti-doublon strict
- `AVERTI`  → 1 seul email à l'étudiant (jamais renvoyé pour le même module)
- `EXCLU`   → 1 seul email à l'étudiant + administration (jamais renvoyé)
- Stocker dans la DB si l'email a déjà été envoyé pour ce seuil

### Volumes horaires (config/modules.json)
- Module MAJEUR (spécialité) : 48h estimé
- Module COMPLEMENTAIRE (langues) : 35h estimé
- Seuils : alerte_pct=20, exclusion_pct=50

---

## STRUCTURE À CRÉER

```
studenttrack/
├── config/
│   └── modules.json
├── data/
│   └── dataset.xlsx          ← déjà présent, ne pas toucher
├── backend/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── reader.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── ia_agent.py
│   └── api/
│       ├── __init__.py
│       └── app.py
├── logs/
└── requirements.txt
```

---

## FICHIER 1 — config/modules.json

```json
{
  "_info": "Volumes estimés selon CNPN ESITH — mettre confirme:true dès réception des valeurs officielles",
  "_seuils": {
    "alerte_pct": 20,
    "exclusion_pct": 50
  },
  "_types": {
    "MAJEUR":         { "volume_defaut": 48 },
    "COMPLEMENTAIRE": { "volume_defaut": 35 }
  },
  "modules": {
    "Physique E1":                                                    { "type": "MAJEUR",         "volume_heures": 48, "confirme": false },
    "Dessins Techniques E1":                                          { "type": "MAJEUR",         "volume_heures": 48, "confirme": false },
    "Développement et transformation des patrons pour femmes E2":     { "type": "MAJEUR",         "volume_heures": 48, "confirme": false },
    "Espagnol":                                                       { "type": "COMPLEMENTAIRE", "volume_heures": 35, "confirme": false },
    "Anglais":                                                        { "type": "COMPLEMENTAIRE", "volume_heures": 35, "confirme": false }
  }
}
```

---

## FICHIER 2 — backend/ingestion/reader.py

Fonctions à créer :

### `load_dataset(path) -> pd.DataFrame`
- Charge le fichier Excel
- Renomme les colonnes vers le modèle interne :
  - `id_inscriptionsessionprogramme` → `id_etudiant`
  - `DATE` → `date_absence`
  - `DureeDecimal` → `duree_heures`
  - `Excuse` → `justifiee_raw`
  - `Module` → `module`
  - `Cursus` → `cursus`
  - `Nom` → `nom`, `Prenom` → `prenom`
  - `Motif` → `motif`, `Seance` → `seance`
- Normalise :
  - `justifiee` = True si `justifiee_raw.strip().lower() == "oui"`
  - `duree_heures` = float
  - `date_absence` = datetime (dayfirst=True)
  - `id_etudiant` = str
  - `motif` = remplacer "." par ""
- Génère `email` depuis `generer_email(prenom, nom)`
- Extrait `semestre` depuis Cursus avec regex `^(S\d+)`

### `generer_email(prenom, nom) -> str`
- Retourne `prenom.lower().nom.lower()@esith.net`
- Si nom ou prénom vide → `inconnu@esith.net`
- Remplacer les espaces par `-`

### `detect_delta(df) -> tuple[pd.DataFrame, bool]`
- Lit `data/.last_state.json` (liste des id_absence déjà connus)
- Compare avec les id_absence actuels
- Retourne (nouvelles_lignes_df, has_changes)
- Si premier lancement → tout est nouveau
- Sauvegarde le nouvel état dans `.last_state.json`

---

## FICHIER 3 — backend/analysis/engine.py

### Dataclass `StatutModule`
```python
module: str
volume_heures: float
confirme: bool
type_module: str
heures_nj: float
heures_just: float
taux_nj: float           # % absences NJ sur volume
taux_total: float        # % absences totales sur volume
seuil_alerte_h: float    # 20% du volume
seuil_exclusion_h: float # 50% du volume
statut_exam: str         # AUTORISE | AVERTI | EXCLU
avert_email_envoye: bool # anti-doublon
exclu_email_envoye: bool # anti-doublon
alerte_module: str       # message court
```

### Dataclass `ProfilEtudiant`
```python
id_etudiant: str
nom: str
prenom: str
email: str
semestre: str
cursus: str
total_heures_nj: float
total_heures_just: float
total_absences: int
derniere_absence: str
modules: list            # list[StatutModule]
nb_modules_exclu: int
nb_modules_averti: int
module_plus_grave: str
score_risque: float      # 0-100
niveau_risque: str       # faible | modéré | critique
niveau_alerte: int       # 0 | 1 | 2 | 3
action_recommandee: str
```

### Logique statut par module
```python
taux_nj    = heures_nj / volume * 100
taux_total = (heures_nj + heures_just) / volume * 100

if taux_total >= exclusion_pct:   # 50%
    statut = "EXCLU"
elif taux_nj >= alerte_pct:       # 20%
    statut = "AVERTI"
else:
    statut = "AUTORISE"
```

### Score global
```python
score_heures = fonction progressive : 0h=0, 10h=40, 20h=70, 30h+=100
score_module = EXCLU:100 | AVERTI:55 | AUTORISE:0  (pire module)
score_global = min(score_heures * 0.40 + score_module * 0.60, 100)
```

### Actions
```python
"NOTIFY_EXCLUSION" → au moins 1 module EXCLU
"WARN_STUDENT"     → au moins 1 module AVERTI (et aucun EXCLU)
"AUCUNE"           → tous AUTORISE
```

### Fonctions
- `calculer_profils(df) -> list[ProfilEtudiant]`
- `filtrer_alertes(profils) -> list[ProfilEtudiant]` (niveau_alerte > 0)

---

## FICHIER 4 — backend/agent/ia_agent.py

### Dataclass `DecisionIA`
```python
doit_alerter: bool
action: str
destinataire: str        # "etudiant" | "etudiant+administration"
email_sujet: str
email_corps: str
explication: str
genere_le: str
```

### Comportement
- Utilise `anthropic` SDK, model `claude-sonnet-4-6`
- Lire la clé depuis `os.environ.get("ANTHROPIC_API_KEY", "")`
- Si pas de clé → mode simulation avec `_mock_decision(profil)`
- Retourner JSON parsé depuis la réponse

### Templates email simulation

**WARN_STUDENT :**
```
Objet : Avertissement absences — [Module] — ESITH Casablanca

Madame, Monsieur [Prénom] [Nom],

Nous vous informons que votre taux d'absences non justifiées dans le module
[Module] a atteint [X]% (seuil d'avertissement : 20%).

Si cette situation n'est pas régularisée, vous risquez de ne plus pouvoir
passer l'examen de ce module.

Nous vous invitons à contacter le service de la scolarité.

Cordialement,
Service de la Scolarité — ESITH Casablanca — StudentTrack
```

**NOTIFY_EXCLUSION :**
```
Objet : Exclusion d'examen — [Module] — ESITH Casablanca

Madame, Monsieur [Prénom] [Nom],

Nous vous informons que votre taux d'absences total (justifiées et non
justifiées) dans le module [Module] a atteint [X]%.

Conformément au règlement de l'ESITH, ayant manqué plus de 50% du volume
horaire de ce module, vous ne pouvez pas vous présenter à l'examen.

Cette décision est définitive.

Cordialement,
Service de la Scolarité — ESITH Casablanca — StudentTrack
```

### Fonctions
- `analyser_et_rediger(profil: ProfilEtudiant) -> DecisionIA`
- `traiter_alertes(profils: list) -> list[dict]`

---

## FICHIER 5 — backend/api/app.py

Flask + flask-cors. Tous les endpoints retournent du JSON.

```
GET  /api/stats          → { total_etudiants, total_alertes, critique, modere, faible, total_heures_nj }
GET  /api/etudiants      → liste de tous les profils sérialisés
GET  /api/etudiant/<id>  → { profil, absences[] }
GET  /api/alertes        → profils en alerte + décision IA
POST /api/sync           → relit le dataset et retourne { nouvelles_lignes, changed }
```

Serialisation : convertir les dataclasses avec `dataclasses.asdict()`.
Convertir les types numpy (np.float64, np.bool_) en types Python natifs.

Port : 5050

---

## FICHIER 6 — requirements.txt

```
flask
flask-cors
pandas
openpyxl
anthropic
```

---

## INSTRUCTIONS D'EXÉCUTION

1. Crée toute la structure de dossiers
2. Crée les fichiers dans cet ordre : modules.json → reader.py → engine.py → ia_agent.py → app.py → requirements.txt
3. Installe les dépendances : `pip install -r requirements.txt`
4. Teste chaque fichier individuellement :
   - `python backend/ingestion/reader.py`
   - `python backend/analysis/engine.py`
   - `python backend/agent/ia_agent.py`
5. Lance l'API : `python backend/api/app.py`
6. Vérifie que `http://localhost:5050/api/stats` répond correctement

Chaque fichier doit avoir un bloc `if __name__ == "__main__"` pour les tests.
Utilise des dataclasses Python standard (pas Pydantic).
Code propre, commenté, modulaire.
