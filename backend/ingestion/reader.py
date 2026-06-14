import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
LAST_STATE_FILE = ROOT / "data" / ".last_state.json"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_absences_df() -> pd.DataFrame:
    """Retourne un DataFrame avec toutes les absences jointes étudiants + modules + filières."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            a.id_absence_konosys   AS id_absence,
            a.id_module            AS id_module_db,
            CAST(e.id AS TEXT)     AS id_etudiant,
            e.nom,
            e.prenom,
            e.email,
            e.cursus,
            e.session_programme,
            COALESCE(m.nom, a.module_nom)   AS module,
            COALESCE(m.volume_heures, 48)   AS volume_heures,
            COALESCE(m.semestre, 'S0')      AS semestre,
            COALESCE(f.code,  '')           AS code_filiere,
            COALESCE(f.nom,   '')           AS filiere,
            COALESCE(f.niveau,'')           AS annee,
            a.duree_heures,
            a.justifiee,
            a.date_absence,
            a.seance,
            a.motif
        FROM absences a
        JOIN etudiants e ON a.id_etudiant = e.id
        LEFT JOIN modules  m ON a.id_module    = m.id
        LEFT JOIN filieres f ON m.id_filiere   = f.id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["justifiee"]    = df["justifiee"].astype(bool)
    df["duree_heures"] = pd.to_numeric(df["duree_heures"], errors="coerce").fillna(0.0)
    df["date_absence"] = pd.to_datetime(df["date_absence"], errors="coerce")
    df["id_etudiant"]  = df["id_etudiant"].astype(str)
    df["id_absence"]   = df["id_absence"].astype(str)
    df["motif"]        = df["motif"].fillna("").astype(str)
    df["module"]       = df["module"].astype(str)
    df["filiere"]      = df["filiere"].astype(str)
    df["code_filiere"] = df["code_filiere"].astype(str)
    df["annee"]        = df["annee"].astype(str)
    df["cursus"]       = df["cursus"].fillna("").astype(str)
    df["seance"]       = df["seance"].fillna("").astype(str)
    df["nom"]          = df["nom"].astype(str)
    df["prenom"]       = df["prenom"].astype(str)
    df["volume_heures"] = pd.to_numeric(df["volume_heures"], errors="coerce").fillna(48).astype(int)
    df["id_module_db"] = pd.to_numeric(df["id_module_db"], errors="coerce").fillna(0).astype(int)

    return df


def detect_delta() -> tuple:
    """Détecte les nouvelles absences depuis le dernier état connu."""
    df = load_absences_df()
    current_ids = set(df["id_absence"].astype(str).tolist())

    if LAST_STATE_FILE.exists():
        known_ids = set(json.loads(LAST_STATE_FILE.read_text(encoding="utf-8")))
        new_ids = current_ids - known_ids
        new_rows = df[df["id_absence"].astype(str).isin(new_ids)].copy()
        has_changes = len(new_rows) > 0
    else:
        new_rows = df.copy()
        has_changes = True

    LAST_STATE_FILE.write_text(json.dumps(list(current_ids)), encoding="utf-8")
    return new_rows, has_changes


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[reader] Base SQLite introuvable : {DB_PATH}")
    else:
        df = load_absences_df()
        print(f"[reader] Absences : {len(df)} lignes")
        print(f"[reader] Étudiants uniques : {df['id_etudiant'].nunique()}")
        print(df[["id_etudiant", "nom", "prenom", "email"]].drop_duplicates().head(5))
        delta, changed = detect_delta()
        print(f"[reader] Nouvelles lignes : {len(delta)} | Changements : {changed}")
