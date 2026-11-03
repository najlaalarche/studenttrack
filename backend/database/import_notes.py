"""
Import des moyennes (export Konosys) dans la table notes.

Structure attendue du fichier (.xlsx ou .xlsb) :
  - une ligne "Infos Générales : S1-<programme> 2025-2025"
  - une ligne d'en-têtes : MatriculeEtudiant, Nom, Prenom, Nb Module Validé, [modules...], Moyenne
  - les lignes étudiants en dessous
Seule la colonne "Moyenne" est importée.

Liaison : Nom + Prénom normalisés dans la même filière (1 candidat → lié).
Aucun candidat → étudiant créé automatiquement. Homonymes → rapprochement_a_valider.csv.

Usage : python backend/database/import_notes.py data/samples/notes_ims_avec_donnees.xlsx
"""
import csv
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
RAPPROCHEMENT_CSV = ROOT / "data" / "logs" / "rapprochement_a_valider.csv"

_STOPWORDS = {"ingenieur", "et", "des", "de", "du", "la", "le", "les", "en", "d", "l", "a"}


# ── Schéma ───────────────────────────────────────────────────────────────────

def ensure_notes_schema(conn: sqlite3.Connection):
    """Ajoute etudiants.matricule + tables inscriptions/notes (idempotent)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(etudiants)").fetchall()}
    if "matricule" not in cols:
        conn.execute("ALTER TABLE etudiants ADD COLUMN matricule TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_etudiant INTEGER NOT NULL REFERENCES etudiants(id),
            id_inscriptionsessionprogramme INTEGER UNIQUE,
            matricule TEXT,
            semestre TEXT NOT NULL,
            annee_universitaire TEXT NOT NULL,
            session_programme TEXT,
            id_filiere INTEGER REFERENCES filieres(id),
            UNIQUE(id_etudiant, semestre, annee_universitaire)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_etudiant INTEGER NOT NULL REFERENCES etudiants(id),
            moyenne_generale REAL CHECK (moyenne_generale BETWEEN 0 AND 20),
            semestre TEXT,
            annee_universitaire TEXT NOT NULL,
            source_fichier TEXT,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(id_etudiant, semestre, annee_universitaire)
        )
    """)
    conn.commit()


# ── Lecture du fichier ───────────────────────────────────────────────────────

def _read_rows(path: Path) -> list[list]:
    """Retourne toutes les lignes de la 1ère feuille sous forme de listes de valeurs."""
    if path.suffix.lower() == ".xlsb":
        from pyxlsb import open_workbook
        rows = []
        with open_workbook(str(path)) as wb:
            with wb.get_sheet(1) as sheet:
                for row in sheet.rows():
                    rows.append([c.v for c in row])
        return rows
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    wb.close()
    return rows


def _normalize(s) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.replace("-", " ")).strip().lower()


def _parse_infos(text: str) -> dict:
    """'Infos Générales : S1-Ingénieur Informatique et ... 2025-2025' → semestre, programme, année."""
    m = re.search(r"(S\d+)\s*-\s*(.+?)\s+(\d{4}\s*-\s*\d{4})\s*$", text.split(":", 1)[-1].strip())
    if not m:
        return {"semestre": None, "programme": text.strip(), "annee": None}
    return {"semestre": m.group(1).upper(), "programme": m.group(2).strip(),
            "annee": m.group(3).replace(" ", "")}


def _filiere_ids(conn, programme: str) -> list[int]:
    """Ids des filières (tous niveaux) correspondant au libellé du programme."""
    codes = {r[0]: r[0].replace("GI-", "") for r in conn.execute("SELECT DISTINCT code FROM filieres")}
    words = _normalize(programme).upper().split()
    found = next((c for c, short in codes.items() if short in words or c in words), None)
    if not found:
        acronyme = "".join(w[0] for w in _normalize(programme).split() if w not in _STOPWORDS).upper()
        found = next((c for c, short in codes.items() if short == acronyme), None)
    if not found:
        return []
    return [r[0] for r in conn.execute("SELECT id FROM filieres WHERE code=?", (found,))]


def _parse_file(path: Path) -> tuple[dict, list[dict]]:
    rows = _read_rows(path)
    infos, header_idx = {}, None
    for i, row in enumerate(rows):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not infos and any(c.lower().startswith("infos g") for c in cells):
            infos = _parse_infos(next(c for c in cells if c.lower().startswith("infos g")))
        if "MatriculeEtudiant" in cells:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("En-tête 'MatriculeEtudiant' introuvable dans le fichier")

    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    i_mat, i_nom, i_pre = header.index("MatriculeEtudiant"), header.index("Nom"), header.index("Prenom")
    i_moy = header.index("Moyenne") if "Moyenne" in header else len(header) - 1

    etudiants = []
    for row in rows[header_idx + 1:]:
        row = list(row) + [None] * (len(header) - len(row))
        mat = str(row[i_mat]).strip() if row[i_mat] is not None else ""
        if not mat:
            continue
        try:
            moyenne = round(float(str(row[i_moy]).replace(",", ".")), 2)
        except (TypeError, ValueError):
            moyenne = None
        etudiants.append({"matricule": mat, "nom": str(row[i_nom] or "").strip(),
                          "prenom": str(row[i_pre] or "").strip(), "moyenne": moyenne})
    return infos, etudiants


# ── Liaison / création étudiant ──────────────────────────────────────────────

def _gen_email(prenom: str, nom: str) -> str:
    """Même format que app._gen_email : prenom.nom@esith.net."""
    def clean(s):
        s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
        return s.lower().strip().replace(" ", "-")
    return f"{clean(prenom)}.{clean(nom)}@esith.net"


def cle_nom(nom, prenom) -> tuple[str, str]:
    """Clé de rapprochement étudiant : Nom + Prénom sans accents, minuscules, strip."""
    return _normalize(nom), _normalize(prenom)


def id_inscription_provisoire(conn) -> int:
    """id_inscriptionsessionprogramme est NOT NULL UNIQUE : id négatif en attendant le vrai id Konosys."""
    return min(0, conn.execute(
        "SELECT MIN(id_inscriptionsessionprogramme) FROM etudiants").fetchone()[0] or 0) - 1


def _chercher(conn, et: dict, filiere_ids: list[int]) -> list:
    """Étudiants de la même filière (tous niveaux) avec le même Nom + Prénom normalisés."""
    cible = cle_nom(et["nom"], et["prenom"])
    return [r for r in conn.execute("SELECT id, nom, prenom, id_filiere FROM etudiants")
            if r[3] in filiere_ids and cle_nom(r[1], r[2]) == cible]


def _creer(conn, et: dict, id_filiere: int, cursus: str, session_programme: str) -> int | None:
    """Crée l'étudiant ; None si l'email est déjà pris par un autre étudiant.

    Le fichier notes ne contient pas d'id_inscriptionsessionprogramme (NOT NULL UNIQUE) :
    on pose un id provisoire négatif, remplacé par le vrai lors du premier import d'absences.
    """
    email = _gen_email(et["prenom"], et["nom"])
    if conn.execute("SELECT 1 FROM etudiants WHERE email=?", (email,)).fetchone():
        return None
    return conn.execute(
        """INSERT INTO etudiants (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere,
                                  cursus, session_programme, matricule)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_inscription_provisoire(conn), et["nom"], et["prenom"], email, id_filiere, cursus, session_programme,
         et["matricule"]),
    ).lastrowid


# ── Aperçu (lecture seule) ───────────────────────────────────────────────────

def preview_notes(path, n: int = 5, db_path=None) -> dict:
    """Infos du fichier + n premières lignes, sans rien écrire en base."""
    infos, etudiants = _parse_file(Path(path))
    conn = sqlite3.connect(db_path or DB_PATH)
    filiere_ids = _filiere_ids(conn, infos.get("programme", ""))
    code = conn.execute("SELECT code FROM filieres WHERE id=?", (min(filiere_ids),)).fetchone()[0] \
        if filiere_ids else None
    conn.close()
    return {
        "semestre": infos.get("semestre"), "annee_universitaire": infos.get("annee"),
        "programme": infos.get("programme"), "filiere": code, "total": len(etudiants),
        "headers": ["MatriculeEtudiant", "Nom", "Prenom", "Moyenne"],
        "rows": [{"MatriculeEtudiant": e["matricule"], "Nom": e["nom"], "Prenom": e["prenom"],
                  "Moyenne": e["moyenne"]} for e in etudiants[:n]],
    }


# ── Import ───────────────────────────────────────────────────────────────────

def import_notes(path, source_name: str | None = None, db_path=None, csv_path=None) -> dict:
    path = Path(path)
    db_path, csv_path = db_path or DB_PATH, csv_path or RAPPROCHEMENT_CSV
    infos, etudiants = _parse_file(path)
    semestre, annee = infos.get("semestre"), infos.get("annee")
    if not annee:
        raise ValueError("Année universitaire introuvable dans la ligne 'Infos Générales'")

    conn = sqlite3.connect(db_path)
    ensure_notes_schema(conn)
    filiere_ids = _filiere_ids(conn, infos.get("programme", ""))
    if not filiere_ids:
        conn.close()
        raise ValueError(f"Filière introuvable pour le programme « {infos.get('programme')} »")
    id_filiere = min(filiere_ids)
    if semestre:
        # Niveau d'après le semestre : S1/S2 → 1ère année, S3/S4 → 2ème …
        niveau = (int(semestre[1:]) + 1) // 2
        row = conn.execute(
            f"SELECT id FROM filieres WHERE id IN ({','.join('?' * len(filiere_ids))}) AND niveau LIKE ?",
            (*filiere_ids, f"{niveau}%"),
        ).fetchone()
        if row:
            id_filiere = row[0]
    code_filiere = conn.execute("SELECT code FROM filieres WHERE id=?", (id_filiere,)).fetchone()[0]
    cursus = f"{semestre}-{code_filiere}" if semestre else code_filiere
    session_programme = f"{infos.get('programme')} {annee}"

    stats = {"etudiants_traites": 0, "notes_ajoutees": 0, "notes_mises_a_jour": 0,
             "etudiants_lies_auto": 0, "etudiants_crees": 0, "crees": [],
             "etudiants_non_trouves": 0, "non_trouves": [],
             "fichier_rapprochement_cree": False,
             "semestre": semestre, "annee_universitaire": annee}
    a_valider = []

    def a_valider_ajout(et, raison, candidats=()):
        stats["etudiants_non_trouves"] += 1
        stats["non_trouves"].append({**et, "raison": raison})
        a_valider.append({**et, "raison": raison, "candidats_proposes": " | ".join(
            f"id={c[0]} {c[1]} {c[2]} (filiere {c[3]})" for c in candidats)})

    for et in etudiants:
        stats["etudiants_traites"] += 1
        if et["moyenne"] is None or not 0 <= et["moyenne"] <= 20:
            a_valider_ajout(et, f"moyenne invalide ({et['moyenne']})")
            continue

        candidats = _chercher(conn, et, filiere_ids)
        if len(candidats) > 1:
            a_valider_ajout(et, "homonymes", candidats)
            continue
        if candidats:
            id_et = candidats[0][0]
            stats["etudiants_lies_auto"] += 1
            conn.execute("UPDATE etudiants SET matricule=? WHERE id=?", (et["matricule"], id_et))
        else:
            id_et = _creer(conn, et, id_filiere, cursus, session_programme)
            if id_et is None:
                a_valider_ajout(et, f"email {_gen_email(et['prenom'], et['nom'])} deja utilise "
                                    "par un etudiant d'une autre filiere")
                continue
            stats["etudiants_crees"] += 1
            stats["crees"].append({k: et[k] for k in ("matricule", "nom", "prenom")})

        existe = conn.execute(
            "SELECT 1 FROM notes WHERE id_etudiant=? AND semestre IS ? AND annee_universitaire=?",
            (id_et, semestre, annee),
        ).fetchone()
        conn.execute(
            """INSERT INTO notes (id_etudiant, moyenne_generale, semestre, annee_universitaire, source_fichier)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id_etudiant, semestre, annee_universitaire) DO UPDATE SET
                   moyenne_generale = excluded.moyenne_generale,
                   source_fichier   = excluded.source_fichier,
                   imported_at      = CURRENT_TIMESTAMP""",
            (id_et, et["moyenne"], semestre, annee, source_name or path.name),
        )
        stats["notes_mises_a_jour" if existe else "notes_ajoutees"] += 1

        if semestre:
            conn.execute(
                """INSERT INTO inscriptions (id_etudiant, matricule, semestre, annee_universitaire,
                                             session_programme, id_filiere)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id_etudiant, semestre, annee_universitaire) DO UPDATE SET
                       matricule         = excluded.matricule,
                       session_programme = excluded.session_programme,
                       id_filiere        = excluded.id_filiere""",
                (id_et, et["matricule"], semestre, annee, infos.get("programme"), id_filiere),
            )

    conn.commit()
    conn.close()

    if a_valider:
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, delimiter=";", fieldnames=[
                "matricule", "nom", "prenom", "moyenne", "raison", "candidats_proposes"])
            w.writeheader()
            w.writerows(a_valider)
        stats["fichier_rapprochement_cree"] = True
    elif Path(csv_path).exists():
        Path(csv_path).unlink()  # plus aucun cas douteux : on retire l'ancien rapport

    return stats


if __name__ == "__main__":
    import json
    fichier = sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "samples" / "notes_ims_avec_donnees.xlsx"
    print(json.dumps(import_notes(fichier), ensure_ascii=False, indent=2))
