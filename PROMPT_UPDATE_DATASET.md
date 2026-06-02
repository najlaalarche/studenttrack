# StudentTrack — Mise à jour Dataset

Lis ce fichier entièrement puis exécute toutes les instructions dans l'ordre.

---

## CONTEXTE

Le dataset a été remplacé par un nouveau fichier Excel avec 4 feuilles.
Le fichier est dans `data/dataset.xlsx`.

---

## STRUCTURE DU NOUVEAU DATASET

### Feuille "Absences" (4978 lignes, 19 colonnes)
```
id_absence, Nom, Prenom, Seance, DATE, Heure, Duree, DureeDecimal,
SessionProgramme, Cursus, Module, Excuse, Motif,
id_inscriptionsessionprogramme, id_etudiant, Filiere, Code_Filiere,
Annee, Total_Seances_Module
```

Nouveautés importantes :
- `id_etudiant` : identifiant propre (ex: 20001) — différent de id_inscriptionsessionprogramme
- `Filiere` : nom complet (ex: "Génie Industriel")
- `Code_Filiere` : code court (ex: "GI")
- `Annee` : promotion (ex: "GI1")
- `Total_Seances_Module` : nombre total de séances du module — CLEF pour calculer le taux

### Feuille "Notes" (1200 lignes, 13 colonnes)
```
id_etudiant, Nom, Prenom, Filiere, Code_Filiere, Annee, Semestre,
Module, Note_CC, Note_Examen, Note_Finale, Mention, Statut
```

### Feuille "Etudiants" (149 lignes, 11 colonnes)
```
id_etudiant, id_inscriptionsessionprogramme, Nom, Prenom, Genre,
Filiere, Code_Filiere, Annee, Email_Etudiant, Email_Parent, Telephone_Parent
```

Email réel disponible : ex. `nadia.zouiten@esith.ma`

### Feuille "Scoring_Risque" (149 lignes, 14 colonnes)
```
id_etudiant, Nom, Prenom, Filiere, Code_Filiere, Annee,
Total_Seances, Total_Absences, Pct_Absences_Global,
Moyenne_Generale, Score_Absences, Score_Notes, Score_Global_Risque, Niveau_Risque
```

---

## MODIFICATIONS À FAIRE

### 1. Mettre à jour backend/ingestion/reader.py

Remplacer la fonction `load_dataset()` pour lire les 4 feuilles :

```python
def load_dataset(path):
    # Lire les 4 feuilles
    df_abs      = pd.read_excel(path, sheet_name="Absences")
    df_notes    = pd.read_excel(path, sheet_name="Notes")
    df_etudiants= pd.read_excel(path, sheet_name="Etudiants")
    df_scoring  = pd.read_excel(path, sheet_name="Scoring_Risque")
    return df_abs, df_notes, df_etudiants, df_scoring
```

Normalisation de df_abs :
- `justifiee` = True si `Excuse.strip().lower() == "oui"`
- `duree_heures` = float(DureeDecimal)
- `date_absence` = datetime(DATE, dayfirst=True)
- `id_etudiant` = str(id_etudiant)
- `id_absence` = str(id_absence)
- `motif` = remplacer "." par "" et strip()
- `total_seances_module` = int(Total_Seances_Module)
- Garder : Module, Filiere, Code_Filiere, Annee, Cursus, Seance

Email : lire depuis df_etudiants (colonne Email_Etudiant) et merger sur id_etudiant
Ne plus générer l'email depuis Nom+Prénom — utiliser l'email réel du dataset.

Mettre à jour `detect_delta()` — fonctionne pareil sur df_abs avec id_absence.

Ajouter fonction `get_etudiant_info(id_etudiant, df_etudiants)` :
- Retourne dict avec nom, prenom, email, filiere, annee depuis df_etudiants

---

### 2. Mettre à jour backend/analysis/engine.py

#### Supprimer complètement
- L'import et lecture de `config/modules.json`
- La fonction `_volume_module()`
- Le champ `confirme` dans StatutModule
- Le champ `excuse_chef_utilisee` dans StatutModule

#### Nouvelle logique taux par module

Le taux se calcule maintenant depuis les séances (pas les heures) :

```python
# Pour chaque module d'un étudiant :
nb_seances_absentes_nj    = nombre de lignes NJ dans ce module
nb_seances_absentes_just  = nombre de lignes justifiées dans ce module
nb_seances_absentes_total = nb_seances_absentes_nj + nb_seances_absentes_just
total_seances_module      = df_abs[df_abs.module == module]["total_seances_module"].iloc[0]

taux_nj    = nb_seances_absentes_nj    / total_seances_module * 100
taux_total = nb_seances_absentes_total / total_seances_module * 100

# Seuils
SEUIL_ALERTE    = 20   # taux_nj >= 20%    → AVERTI
SEUIL_EXCLUSION = 50   # taux_total >= 50% → EXCLU
```

#### Règle statut (inchangée)
```python
if taux_total >= 50:
    statut = "EXCLU"      # définitif, justifié ou non
elif taux_nj >= 20:
    statut = "AVERTI"     # peut régulariser dans Konosys
else:
    statut = "AUTORISE"
```

#### Mettre à jour StatutModule
```python
@dataclass
class StatutModule:
    module:               str
    total_seances:        int     # total séances du module
    nb_abs_nj:            int     # séances NJ
    nb_abs_just:          int     # séances justifiées
    nb_abs_total:         int     # total absences
    taux_nj:              float   # % NJ
    taux_total:           float   # % total
    seuil_alerte:         float   # 20.0
    seuil_exclusion:      float   # 50.0
    statut_exam:          str     # AUTORISE | AVERTI | EXCLU
    avert_email_envoye:   bool
    exclu_email_envoye:   bool
    alerte_module:        str
```

#### Intégrer les notes dans ProfilEtudiant
```python
@dataclass
class ProfilEtudiant:
    # ... champs existants ...
    moyenne_generale:     float   # depuis Scoring_Risque ou calculée depuis Notes
    score_notes:          float   # depuis Scoring_Risque
    score_absences:       float   # depuis Scoring_Risque
    score_global:         float   # Score_Global_Risque depuis Scoring_Risque
    niveau_risque_scoring:str     # Niveau_Risque depuis Scoring_Risque (ROUGE/ORANGE/VERT)
    notes_modules:        list    # list de dicts {module, note_finale, mention, statut}
```

#### Score global
Utiliser directement `Score_Global_Risque` depuis la feuille Scoring_Risque si disponible.
Sinon calculer :
```python
score = min(score_absences * 0.60 + score_notes * 0.40, 100)
```

niveau_risque :
- Score >= 70 → "critique" (ROUGE)
- Score >= 40 → "modéré" (ORANGE)
- Score < 40  → "faible" (VERT)

---

### 3. Mettre à jour backend/api/app.py

Adapter pour passer les 4 DataFrames à `calculer_profils()`.

Ajouter endpoint :
```
GET /api/modules → liste tous les modules distincts (pour le dashboard professeur)
GET /api/filieres → liste toutes les filières distinctes
```

Ajouter dans `/api/etudiant/<id>` :
- Inclure les notes du module depuis df_notes
- Inclure le scoring depuis df_scoring

---

### 4. Mettre à jour config/modules.json

Ce fichier n'est plus nécessaire pour les volumes horaires.
Le garder uniquement pour les seuils configurables :

```json
{
  "_info": "Seuils configurables — les volumes viennent du dataset directement",
  "_seuils": {
    "alerte_pct": 20,
    "exclusion_pct": 50
  }
}
```

---

## DONNÉES EXEMPLE DU VRAI DATASET

Étudiant de test pour le login :
- Email : `nadia.zouiten@esith.ma`
- ID : 20001
- Filière : Génie Industriel GI1

Étudiant à risque ROUGE :
- Cherkaoui Salma (id: 20140) — 50% absences, moyenne 6.45, score 87.1
- Naciri Reda (id: 20125) — 51.5% absences, moyenne 8.57, score 82.9

---

## INSTRUCTIONS D'EXÉCUTION

1. Mettre à jour `reader.py` en premier
2. Mettre à jour `engine.py`
3. Mettre à jour `app.py`
4. Mettre à jour `config/modules.json`
5. Tester chaque fichier :
   - `python backend/ingestion/reader.py`
   - `python backend/analysis/engine.py`
   - `python backend/agent/ia_agent.py`
6. Relancer l'API : `python backend/api/app.py`
7. Vérifier `http://localhost:5050/api/stats` — doit retourner 149 étudiants
8. Vérifier `http://localhost:5050/api/etudiant/20001` — doit retourner Nadia Zouiten avec ses notes

Améliore le style du dashboard pour un rendu plus professionnel et moderne.

Inspire-toi du style des dashboards SaaS comme Linear, Notion ou Vercel.

Changements souhaités :

TYPOGRAPHIE
- Font principale : Inter (Google Fonts)
- Titres bien hiérarchisés, poids 600/700
- Textes secondaires plus lisibles

COULEURS
- Fond principal : #0A0A0F
- Surface cards : #111118
- Bordures subtiles : #1E1E2E
- Accent principal : #6366F1 (indigo)
- Vert : #22C55E (AUTORISE)
- Orange : #F97316 (AVERTI)  
- Rouge : #EF4444 (EXCLU)
- Texte principal : #F8FAFC
- Texte secondaire : #94A3B8

COMPOSANTS
- Cards avec légère ombre et border subtil
- Badges arrondis et bien contrastés
- Tableau avec hover effect propre
- Sidebar avec items actifs bien visibles
- Boutons avec états hover/active soignés
- Barres de progression plus élégantes avec gradient

LOGIN
- Centré avec logo StudentTrack en grand
- 3 cartes de rôle avec icônes et description courte
- Animation subtile au hover

HEADER
- Logo + nom de l'utilisateur connecté en haut à droite
- Bouton déconnexion discret

GENERAL
- Espacement généreux entre les sections
- Coins arrondis cohérents (8px pour les cards, 6px pour les badges)
- Transitions CSS douces (0.15s)
- Pas de couleurs trop criardes — palette sobre et professionnelle