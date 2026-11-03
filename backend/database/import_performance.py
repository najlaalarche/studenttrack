"""
Import des moyennes brute / nette (pénalité d'absence) dans notes_performance.

Colonnes attendues (1ère feuille, la ligne d'en-têtes est la première qui contient "Matricule") :
  Matricule | Moyenne Brute | Moyenne Nette | Moyenne S1 | Moyenne S2 | Moyenne Année Scolaire

Liaison étudiant par matricule (etudiants.matricule puis inscriptions.matricule).
Un matricule inconnu est quand même enregistré (id_etudiant NULL) et signalé : il sera
rattaché dès que le matricule sera renseigné sur la fiche étudiant.
Ré-import du même matricule pour la même année scolaire = mise à jour.

Usage : python backend/database/import_performance.py moyennes.xlsx [2026-2027]
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"

sys.path.insert(0, str(ROOT))
from backend.database.import_notes import _read_rows, _normalize  # noqa: E402

# en-tête normalisé (sans accents ni espaces) -> colonne de notes_performance
_COLONNES = {
    "matricule":            "matricule",
    "matriculeetudiant":    "matricule",
    "moyennebrute":         "moyenne_brute",
    "moyennenette":         "moyenne_nette",
    "moyennes1":            "moyenne_s1",
    "moyennes2":            "moyenne_s2",
    "moyenneanneescolaire": "moyenne_annee",
    "moyenneannee":         "moyenne_annee",
}
_MOYENNES = ["moyenne_brute", "moyenne_nette", "moyenne_s1", "moyenne_s2", "moyenne_annee"]


def ensure_performance_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_etudiant INTEGER REFERENCES etudiants(id),
            matricule TEXT,
            moyenne_brute FLOAT,
            moyenne_nette FLOAT,
            moyenne_s1 FLOAT,
            moyenne_s2 FLOAT,
            moyenne_annee FLOAT,
            annee_scolaire TEXT,
            date_import DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(matricule, annee_scolaire)
        )
    """)
    conn.commit()


def annee_scolaire_courante(today: date | None = None) -> str:
    today = today or date.today()
    debut = today.year if today.month >= 9 else today.year - 1
    return f"{debut}-{debut + 1}"


def taux_performance_perdue(brute, nette) -> float | None:
    """((brute - nette) / brute) × 100 — part de la moyenne perdue à cause des absences."""
    if brute is None or nette is None or brute <= 0:
        return None
    return round((brute - nette) / brute * 100, 2)


def _clef(h) -> str:
    return _normalize(h).replace(" ", "")


def _note(v) -> float | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        n = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return n if 0 <= n <= 20 else None


def _parse(path) -> list[dict]:
    rows = _read_rows(Path(path))
    for i, row in enumerate(rows):
        cles = [_clef(c) if c is not None else "" for c in row]
        if any(_COLONNES.get(c) == "matricule" for c in cles):
            index = {_COLONNES[c]: j for j, c in enumerate(cles) if c in _COLONNES}
            break
    else:
        raise ValueError("Ligne d'en-têtes introuvable (colonne « Matricule » absente)")
    manquantes = {"moyenne_brute", "moyenne_nette"} - set(index)
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(manquantes))}")

    lignes = []
    for row in rows[i + 1:]:
        val = lambda col: row[index[col]] if col in index and index[col] < len(row) else None  # noqa: E731
        mat = val("matricule")
        if mat is None or not str(mat).strip():
            continue
        if isinstance(mat, float) and mat.is_integer():
            mat = int(mat)
        lignes.append({"matricule": str(mat).strip().upper(), **{c: _note(val(c)) for c in _MOYENNES}})
    return lignes


def _id_etudiant(conn, matricule: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM etudiants WHERE UPPER(TRIM(matricule))=?", (matricule,)
    ).fetchone() or conn.execute(
        "SELECT id_etudiant FROM inscriptions WHERE UPPER(TRIM(matricule))=? ORDER BY id DESC", (matricule,)
    ).fetchone()
    return row[0] if row else None


def import_performance(path, annee_scolaire: str | None = None, db_path=None) -> dict:
    annee = annee_scolaire or annee_scolaire_courante()
    lignes = _parse(path)

    conn = sqlite3.connect(db_path or DB_PATH)
    ensure_performance_schema(conn)
    stats = {"annee_scolaire": annee, "lignes_traitees": len(lignes),
             "ajoutees": 0, "mises_a_jour": 0, "non_trouves": [], "incompletes": []}

    for l in lignes:
        if l["moyenne_brute"] is None or l["moyenne_nette"] is None:
            stats["incompletes"].append(l["matricule"])
        id_et = _id_etudiant(conn, l["matricule"])
        if id_et is None:
            stats["non_trouves"].append(l["matricule"])
        existe = conn.execute(
            "SELECT 1 FROM notes_performance WHERE matricule=? AND annee_scolaire=?", (l["matricule"], annee)
        ).fetchone()
        conn.execute(
            """INSERT INTO notes_performance
               (id_etudiant, matricule, moyenne_brute, moyenne_nette, moyenne_s1, moyenne_s2,
                moyenne_annee, annee_scolaire, date_import)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(matricule, annee_scolaire) DO UPDATE SET
                   id_etudiant=excluded.id_etudiant, moyenne_brute=excluded.moyenne_brute,
                   moyenne_nette=excluded.moyenne_nette, moyenne_s1=excluded.moyenne_s1,
                   moyenne_s2=excluded.moyenne_s2, moyenne_annee=excluded.moyenne_annee,
                   date_import=CURRENT_TIMESTAMP""",
            (id_et, l["matricule"], *[l[c] for c in _MOYENNES], annee),
        )
        stats["mises_a_jour" if existe else "ajoutees"] += 1

    conn.commit()
    conn.close()
    return stats


def performance_etudiant(conn: sqlite3.Connection, id_etudiant: int) -> dict | None:
    """Dernière ligne de notes_performance de l'étudiant (par id ou par matricule)."""
    ensure_performance_schema(conn)
    row = conn.execute(
        f"""SELECT {', '.join(_MOYENNES)}, annee_scolaire, date_import FROM notes_performance
            WHERE id_etudiant = :id
               OR matricule IN (SELECT UPPER(TRIM(matricule)) FROM etudiants WHERE id = :id AND matricule IS NOT NULL)
            ORDER BY annee_scolaire DESC, date_import DESC LIMIT 1""",
        {"id": id_etudiant},
    ).fetchone()
    if not row:
        return None
    perf = dict(zip(_MOYENNES + ["annee_scolaire", "date_import"], row))
    perf["taux_performance_perdue"] = taux_performance_perdue(perf["moyenne_brute"], perf["moyenne_nette"])
    perf.update(_classements(conn, id_etudiant, perf))
    return perf


def moyennes_par_etudiant(conn: sqlite3.Connection) -> dict[int, dict]:
    """Dernière moyenne brute / nette de chaque étudiant (rattaché par id ou par matricule)."""
    ensure_performance_schema(conn)
    rows = conn.execute(
        """SELECT COALESCE(np.id_etudiant, e.id), np.moyenne_brute, np.moyenne_nette
           FROM notes_performance np
           LEFT JOIN etudiants e
                  ON np.id_etudiant IS NULL AND UPPER(TRIM(e.matricule)) = np.matricule
           ORDER BY np.annee_scolaire, np.date_import"""
    ).fetchall()
    # tri croissant : la ligne la plus récente écrase les précédentes
    return {id_et: {"moyenne_brute": brute, "moyenne_nette": nette}
            for id_et, brute, nette in rows if id_et is not None}


def _classements(conn: sqlite3.Connection, id_etudiant: int, perf: dict) -> dict:
    """Rang brut / net parmi les étudiants de la même filière (promotion) pour la même année scolaire.
    Ex aequo : même rang (1 + nombre d'étudiants strictement meilleurs)."""
    filiere = conn.execute("SELECT id_filiere FROM etudiants WHERE id=?", (id_etudiant,)).fetchone()
    filiere = filiere[0] if filiere else None
    lignes = conn.execute(
        """SELECT DISTINCT np.id, np.moyenne_brute, np.moyenne_nette
           FROM notes_performance np
           LEFT JOIN etudiants e
                  ON e.id = np.id_etudiant OR UPPER(TRIM(e.matricule)) = np.matricule
           WHERE np.annee_scolaire = :annee AND (:filiere IS NULL OR e.id_filiere = :filiere)""",
        {"annee": perf["annee_scolaire"], "filiere": filiere},
    ).fetchall()

    def rang(valeur, idx):
        notes = [l[idx] for l in lignes if l[idx] is not None]
        if valeur is None or not notes:
            return None, len(notes)
        return 1 + sum(1 for n in notes if n > valeur), len(notes)

    brut, eff_brut = rang(perf["moyenne_brute"], 1)
    net,  eff_net  = rang(perf["moyenne_nette"], 2)
    return {"classement_brut": brut, "effectif_brut": eff_brut,
            "classement_net":  net,  "effectif_net":  eff_net}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    print(import_performance(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
