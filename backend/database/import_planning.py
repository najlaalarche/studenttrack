"""
Import du planning hebdomadaire (export Konosys, ex. planning_SEM_19_OCTOBRE.xlsx) dans planning_seances.

Colonnes attendues :
  id_seance, dateSeance, numDay, HD, HF, DureeMin, DureeMinDecimal, Salle, Prof,
  Groupe, Module, CodeModule, TypeSeance, Cursus, AppelFait

numero_semaine est calculé par rapport à la date de début d'année scolaire (table parametres) :
la semaine (lundi → dimanche) qui contient cette date est la semaine 1.
Anti-doublon sur id_seance : une séance déjà importée est ignorée.

Usage : python backend/database/import_planning.py planning_SEM_19_OCTOBRE.xlsx [AAAA-MM-JJ]
"""
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"

CLE_DATE_DEBUT = "date_debut_annee_scolaire"

# nom normalisé de la colonne Excel -> colonne de planning_seances
_COLONNES = {
    "idseance":        "id_seance",
    "dateseance":      "date_seance",
    "dureemindecimal": "duree_heures",
    "dureemin":        "duree_min",
    "groupe":          "groupe",
    "module":          "module",
    "codemodule":      "code_module",
    "typeseance":      "type_seance",
    "cursus":          "cursus",
    "appelfait":       "appel_fait",
}


# ── Schéma / paramètres ──────────────────────────────────────────────────────

def ensure_planning_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS planning_seances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_seance TEXT UNIQUE,
            date_seance DATE,
            numero_semaine INTEGER,
            duree_heures FLOAT,
            groupe TEXT,
            module TEXT,
            code_module TEXT,
            type_seance TEXT,
            cursus TEXT,
            appel_fait TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_planning_groupe ON planning_seances(groupe)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            cle TEXT PRIMARY KEY,
            valeur TEXT
        )
    """)
    conn.commit()


def date_debut_par_defaut(today: date | None = None) -> date:
    """1er septembre de l'année scolaire en cours."""
    today = today or date.today()
    return date(today.year if today.month >= 9 else today.year - 1, 9, 1)


def get_date_debut(conn: sqlite3.Connection) -> date:
    row = conn.execute("SELECT valeur FROM parametres WHERE cle=?", (CLE_DATE_DEBUT,)).fetchone()
    if row and row[0]:
        return date.fromisoformat(row[0])
    return date_debut_par_defaut()


def numero_semaine(d: date, debut: date) -> int:
    lundi_s1 = debut - timedelta(days=debut.weekday())
    return (d - lundi_s1).days // 7 + 1


def set_date_debut(conn: sqlite3.Connection, debut: date) -> bool:
    """Enregistre la date de début et renumérote les séances déjà importées. Retourne True si elle a changé."""
    row = conn.execute("SELECT valeur FROM parametres WHERE cle=?", (CLE_DATE_DEBUT,)).fetchone()
    if row and row[0] == debut.isoformat():
        return False
    conn.execute(
        "INSERT INTO parametres (cle, valeur) VALUES (?, ?) ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
        (CLE_DATE_DEBUT, debut.isoformat()),
    )
    rows = conn.execute("SELECT id, date_seance FROM planning_seances").fetchall()
    conn.executemany(
        "UPDATE planning_seances SET numero_semaine=? WHERE id=?",
        [(numero_semaine(date.fromisoformat(d), debut), i) for i, d in rows if d],
    )
    conn.commit()
    return True


# ── Lecture du fichier ───────────────────────────────────────────────────────

def _normalize(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _texte(v) -> str | None:
    if v is None or (isinstance(v, float) and v != v):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s or None


def _date(v) -> date | None:
    if v is None or (isinstance(v, float) and v != v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):  # numéro de série Excel
        return (datetime(1899, 12, 30) + timedelta(days=float(v))).date()
    d = pd.to_datetime(str(v).strip(), dayfirst=True, errors="coerce")
    return None if pd.isna(d) else d.date()


def _heures(v) -> float | None:
    if v is None or (isinstance(v, float) and v != v):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _lire(path) -> list[dict]:
    df = pd.read_excel(path, dtype=object)
    renommage = {c: _COLONNES[_normalize(c)] for c in df.columns if _normalize(c) in _COLONNES}
    manquantes = {"id_seance", "date_seance", "groupe"} - set(renommage.values())
    if "duree_heures" not in renommage.values() and "duree_min" not in renommage.values():
        manquantes.add("DureeMinDecimal")
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(manquantes))}")
    df = df.rename(columns=renommage)[list(renommage.values())]
    return df.to_dict(orient="records")


# ── Import ───────────────────────────────────────────────────────────────────

def import_planning(path, date_debut: date | None = None, db_path=None) -> dict:
    conn = sqlite3.connect(db_path or DB_PATH)
    ensure_planning_schema(conn)
    if date_debut:
        set_date_debut(conn, date_debut)
    debut = get_date_debut(conn)

    stats = {
        "lignes_traitees": 0, "seances_ajoutees": 0, "doublons_ignores": 0,
        "lignes_invalides": 0, "hors_annee": 0,
        "date_debut": debut.isoformat(), "semaines": [], "groupes": [],
    }
    semaines, groupes = set(), set()

    for row in _lire(path):
        stats["lignes_traitees"] += 1
        id_seance = _texte(row.get("id_seance"))
        d         = _date(row.get("date_seance"))
        groupe    = _texte(row.get("groupe"))
        duree     = _heures(row.get("duree_heures"))
        if duree is None and _heures(row.get("duree_min")) is not None:
            duree = _heures(row.get("duree_min")) / 60
        if not id_seance or not d or not groupe or not duree:
            stats["lignes_invalides"] += 1
            continue
        semaine = numero_semaine(d, debut)
        if semaine < 1:
            stats["hors_annee"] += 1
            continue

        cur = conn.execute(
            """INSERT OR IGNORE INTO planning_seances
               (id_seance, date_seance, numero_semaine, duree_heures, groupe, module,
                code_module, type_seance, cursus, appel_fait)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id_seance, d.isoformat(), semaine, round(duree, 2), groupe.upper(),
             _texte(row.get("module")), _texte(row.get("code_module")),
             _texte(row.get("type_seance")), _texte(row.get("cursus")),
             _texte(row.get("appel_fait"))),
        )
        if cur.rowcount:
            stats["seances_ajoutees"] += 1
            semaines.add(semaine)
            groupes.add(groupe.upper())
        else:
            stats["doublons_ignores"] += 1

    conn.commit()
    conn.close()
    stats["semaines"] = sorted(semaines)
    stats["groupes"]  = sorted(groupes)
    return stats


def resume_planning(db_path=None) -> dict:
    """Date de début configurée + contenu actuel de planning_seances (page admin)."""
    conn = sqlite3.connect(db_path or DB_PATH)
    ensure_planning_schema(conn)
    debut = get_date_debut(conn)
    nb, nb_groupes, s_min, s_max = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT groupe), MIN(numero_semaine), MAX(numero_semaine) FROM planning_seances"
    ).fetchone()
    par_semaine = [
        {"semaine": s, "seances": n, "heures": round(h or 0, 2), "du": du, "au": au}
        for s, n, h, du, au in conn.execute(
            """SELECT numero_semaine, COUNT(*), SUM(duree_heures), MIN(date_seance), MAX(date_seance)
               FROM planning_seances GROUP BY numero_semaine ORDER BY numero_semaine"""
        ).fetchall()
    ]
    conn.close()
    return {
        "date_debut": debut.isoformat(),
        "total_seances": nb, "total_groupes": nb_groupes,
        "semaine_min": s_min, "semaine_max": s_max,
        "par_semaine": par_semaine,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    debut_arg = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None
    print(import_planning(sys.argv[1], debut_arg))
