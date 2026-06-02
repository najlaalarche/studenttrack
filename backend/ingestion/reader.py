import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LAST_STATE_FILE = DATA_DIR / ".last_state.json"

SEUIL_ALERTE    = 20
SEUIL_EXCLUSION = 50


def load_dataset(path: str | Path) -> tuple:
    """Charge les 4 feuilles du dataset Excel et retourne (df_abs, df_notes, df_etudiants, df_scoring)."""
    path = Path(path)
    df_abs       = pd.read_excel(path, sheet_name="Absences")
    df_notes     = pd.read_excel(path, sheet_name="Notes")
    df_etudiants = pd.read_excel(path, sheet_name="Etudiants")
    df_scoring   = pd.read_excel(path, sheet_name="Scoring_Risque")

    # --- Normalisation df_abs ---
    df_abs["justifiee"]            = df_abs["Excuse"].astype(str).str.strip().str.lower() == "oui"
    df_abs["duree_heures"]         = pd.to_numeric(df_abs["DureeDecimal"], errors="coerce").fillna(0.0)
    df_abs["date_absence"]         = pd.to_datetime(df_abs["DATE"], dayfirst=True, errors="coerce")
    df_abs["id_etudiant"]          = df_abs["id_etudiant"].astype(str)
    df_abs["id_absence"]           = df_abs["id_absence"].astype(str)
    df_abs["motif"]                = df_abs["Motif"].fillna("").astype(str).str.replace(".", "", regex=False).str.strip()
    df_abs["total_seances_module"] = pd.to_numeric(df_abs["Total_Seances_Module"], errors="coerce").fillna(1).astype(int)
    df_abs["module"]               = df_abs["Module"].astype(str)
    df_abs["filiere"]              = df_abs["Filiere"].astype(str)
    df_abs["code_filiere"]         = df_abs["Code_Filiere"].astype(str)
    df_abs["annee"]                = df_abs["Annee"].astype(str)
    df_abs["cursus"]               = df_abs["Cursus"].astype(str)
    df_abs["seance"]               = df_abs["Seance"].astype(str)
    df_abs["nom"]                  = df_abs["Nom"].astype(str)
    df_abs["prenom"]               = df_abs["Prenom"].astype(str)

    # Merger l'email réel depuis la feuille Etudiants
    df_etudiants["id_etudiant"] = df_etudiants["id_etudiant"].astype(str)
    email_map = df_etudiants.set_index("id_etudiant")["Email_Etudiant"].to_dict()
    df_abs["email"] = df_abs["id_etudiant"].map(email_map).fillna("inconnu@esith.ma")

    # --- Normalisation df_notes ---
    df_notes["id_etudiant"] = df_notes["id_etudiant"].astype(str)
    for col in ["Note_CC", "Note_Examen", "Note_Finale"]:
        df_notes[col] = pd.to_numeric(df_notes[col], errors="coerce")

    # --- Normalisation df_scoring ---
    df_scoring["id_etudiant"] = df_scoring["id_etudiant"].astype(str)
    for col in ["Score_Global_Risque", "Score_Absences", "Score_Notes", "Moyenne_Generale",
                "Total_Seances", "Total_Absences", "Pct_Absences_Global"]:
        if col in df_scoring.columns:
            df_scoring[col] = pd.to_numeric(df_scoring[col], errors="coerce").fillna(0.0)

    return df_abs, df_notes, df_etudiants, df_scoring


def detect_delta(df_abs: pd.DataFrame) -> tuple:
    """Détecte les nouvelles lignes d'absence par rapport au dernier état connu."""
    current_ids = set(df_abs["id_absence"].astype(str).tolist())

    if LAST_STATE_FILE.exists():
        known_ids = set(json.loads(LAST_STATE_FILE.read_text(encoding="utf-8")))
        new_ids = current_ids - known_ids
        new_rows = df_abs[df_abs["id_absence"].astype(str).isin(new_ids)].copy()
        has_changes = len(new_rows) > 0
    else:
        new_rows = df_abs.copy()
        has_changes = True

    LAST_STATE_FILE.write_text(json.dumps(list(current_ids)), encoding="utf-8")
    return new_rows, has_changes


def get_etudiant_info(id_etudiant: str, df_etudiants: pd.DataFrame) -> dict:
    """Retourne les infos d'un étudiant depuis la feuille Etudiants."""
    row = df_etudiants[df_etudiants["id_etudiant"].astype(str) == str(id_etudiant)]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "nom":     str(r.get("Nom", "")),
        "prenom":  str(r.get("Prenom", "")),
        "email":   str(r.get("Email_Etudiant", "")),
        "filiere": str(r.get("Filiere", "")),
        "annee":   str(r.get("Annee", "")),
        "genre":   str(r.get("Genre", "")),
        "email_parent":     str(r.get("Email_Parent", "")),
        "telephone_parent": str(r.get("Telephone_Parent", "")),
    }


if __name__ == "__main__":
    dataset_path = DATA_DIR / "dataset.xlsx"
    if not dataset_path.exists():
        print(f"[reader] dataset.xlsx introuvable dans {DATA_DIR}")
    else:
        df_abs, df_notes, df_etudiants, df_scoring = load_dataset(dataset_path)
        print(f"[reader] Absences    : {len(df_abs)} lignes")
        print(f"[reader] Notes       : {len(df_notes)} lignes")
        print(f"[reader] Etudiants   : {len(df_etudiants)} lignes")
        print(f"[reader] Scoring     : {len(df_scoring)} lignes")
        print("\n--- Colonnes Absences ---")
        print(list(df_abs.columns))
        print("\n--- Exemple email ---")
        print(df_abs[["id_etudiant", "nom", "prenom", "email"]].drop_duplicates().head(5))

        delta, changed = detect_delta(df_abs)
        print(f"\n[reader] Nouvelles lignes : {len(delta)} | Changements : {changed}")

        info = get_etudiant_info("20001", df_etudiants)
        print(f"\n[reader] Info étudiant 20001 : {info}")
