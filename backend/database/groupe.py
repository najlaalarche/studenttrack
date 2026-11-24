"""
Colonne etudiants.groupe (ex. "IMS2G1", "GI-BDM2G1", "D&M2G1").

C'est la clé de jointure avec planning_seances.groupe pour le taux d'absence.
- ensure_groupe_column : ALTER TABLE (sans recréer la table) puis remplit les groupes vides
  depuis cursus / session_programme (étudiants créés par l'import Konosys ou la simulation).
- groupe_depuis_cursus : "S3-IMS2G1" -> "IMS2G1" ; à défaut 1er mot de SessionProgramme.
- filiere_depuis_groupe : "IMS2G1" -> ligne filieres (code IMS, niveau 2ème année).
"""
import re
import sqlite3

_RE_CURSUS = re.compile(r"^S\d+-(.+)$", re.IGNORECASE)
_RE_GROUPE = re.compile(r"^(.+?)(\d)")  # préfixe filière + chiffre du niveau


def normaliser_groupe(groupe: str | None) -> str:
    return re.sub(r"\s+", "", str(groupe or "")).upper()


def groupe_depuis_cursus(cursus: str | None, session_programme: str | None) -> str | None:
    m = _RE_CURSUS.match((cursus or "").strip())
    if m:
        return normaliser_groupe(m.group(1))
    if session_programme and session_programme.strip() and session_programme.strip().lower() != "nan":
        return normaliser_groupe(session_programme.split()[0])
    return None


def ensure_groupe_column(conn: sqlite3.Connection):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(etudiants)").fetchall()}
    if "groupe" not in cols:
        conn.execute("ALTER TABLE etudiants ADD COLUMN groupe TEXT")
    rows = conn.execute(
        "SELECT id, cursus, session_programme FROM etudiants WHERE groupe IS NULL OR groupe = ''"
    ).fetchall()
    maj = [(g, i) for i, cur, sp in rows if (g := groupe_depuis_cursus(cur, sp))]
    if maj:
        conn.executemany("UPDATE etudiants SET groupe=? WHERE id=?", maj)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etudiants_groupe ON etudiants(groupe)")
    conn.commit()


def filiere_depuis_groupe(filieres: list[dict], groupe: str) -> dict | None:
    """filieres : lignes {id, code, niveau}. "IMS2G1" -> IMS 2ème année ; "BDM2G1" ou
    "GI-BDM2G1" -> GI-BDM 2ème année. None si le préfixe ou le niveau est inconnu."""
    m = _RE_GROUPE.match(normaliser_groupe(groupe))
    if not m:
        return None
    prefixe, num = m.group(1).rstrip("-"), m.group(2)
    for f in filieres:
        fc = str(f["code"]).upper()
        if (fc == prefixe or fc.endswith(f"-{prefixe}")) and str(f["niveau"]).startswith(num):
            return f
    return None
