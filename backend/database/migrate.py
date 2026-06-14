import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
MODULES_FILE = ROOT / "data" / "Modules_Volumes_Horaires_ESITH.xlsx"
ABSENCES_FILE = ROOT / "data" / "Absences_ESITH_14etudiants.xlsx"

FILIERE_MAPPING = {
    "INGTC": "IMS",
    "MPTH":  "MPTH",
    "ELOG":  "ELOG",
    "BDM":   "GI-BDM",
    "EO":    "GI-EO",
    "SL":    "GI-SL",
    "GAS":   "GAS",
    "GCL":   "GCL",
    "GPT":   "GPT",
    "GPH":   "GPH",
    "CTM":   "CTM",
    "DEH":   "DEH",
    "MDM":   "MDM",
    "HSE":   "HSE",
    "IMS":   "IMS",
}

# Longest match first to avoid "IMS" matching "INGTC" prefix
_MAPPING_KEYS = sorted(FILIERE_MAPPING.keys(), key=len, reverse=True)


def create_database():
    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"[migrate] Base créée : {DB_PATH}")


def import_modules():
    df = pd.read_excel(MODULES_FILE)
    conn = sqlite3.connect(DB_PATH)
    filieres_created = 0

    for _, row in df.iterrows():
        code = str(row["Filiere"]).strip()
        niveau = str(row["Niveau"]).strip()
        cur = conn.execute(
            "INSERT OR IGNORE INTO filieres (nom, code, niveau) VALUES (?, ?, ?)",
            (code, code, niveau),
        )
        if cur.rowcount > 0:
            filieres_created += 1

    conn.commit()

    filiere_id_map = {}
    for row in conn.execute("SELECT id, code, niveau FROM filieres"):
        filiere_id_map[(row[1], row[2])] = row[0]

    modules_created = 0
    for _, row in df.iterrows():
        code = str(row["Filiere"]).strip()
        niveau = str(row["Niveau"]).strip()
        id_filiere = filiere_id_map.get((code, niveau))

        nom_raw = str(row["Module"]).strip()
        semestre = str(row["Semestre"]).strip()
        # Strip "_S\d+" suffix from module name (e.g. "Anglais_S1" -> "Anglais", semestre="S1")
        m_suf = re.match(r"^(.+)_S(\d+)$", nom_raw)
        nom = m_suf.group(1) if m_suf else nom_raw
        if m_suf:
            semestre = f"S{m_suf.group(2)}"
        bloc = str(row["Bloc_Competence"]).strip() if pd.notna(row.get("Bloc_Competence")) else None
        volume = int(row["Volume_Horaire_h"]) if pd.notna(row.get("Volume_Horaire_h")) else 48
        credits = int(row["Credits"]) if pd.notna(row.get("Credits")) else None

        conn.execute(
            "INSERT INTO modules (nom, id_filiere, semestre, bloc_competence, volume_heures, credits)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (nom, id_filiere, semestre, bloc, volume, credits),
        )
        modules_created += 1

    conn.commit()
    conn.close()
    return filieres_created, modules_created


def parse_cursus(cursus: str, session_programme: str):
    """Retourne (semestre, code_filiere_module, niveau)."""
    m = re.match(r"S(\d+)-(.+)", str(cursus).strip())
    if not m:
        return None, None, None

    semestre = f"S{m.group(1)}"
    suffix = m.group(2)

    code_prefix = None
    for key in _MAPPING_KEYS:
        if suffix.startswith(key):
            code_prefix = key
            break

    if code_prefix is None:
        m2 = re.match(r"([A-Za-z]+)", suffix)
        code_prefix = m2.group(1) if m2 else suffix

    code_filiere = FILIERE_MAPPING.get(code_prefix)

    niveau = None
    sp = str(session_programme)
    m_niv = re.search(r"(\d)[eè][mr]e ann[eé]e", sp)
    if m_niv:
        n = m_niv.group(1)
        if n == "1":
            niveau = "1ère année"
        elif n == "2":
            niveau = "2ème année"
        elif n == "3":
            niveau = "3ème année"

    return semestre, code_filiere, niveau


def import_etudiants_et_absences():
    df = pd.read_excel(ABSENCES_FILE)
    conn = sqlite3.connect(DB_PATH)

    # Build filiere id map: code -> {niveau -> id}
    filiere_map: dict[str, dict] = {}
    for row in conn.execute("SELECT id, code, niveau FROM filieres"):
        filiere_map.setdefault(row[1], {})[row[2]] = row[0]

    # Build module lookup: (nom, id_filiere, semestre) -> id and (nom, id_filiere) -> id
    mod_exact: dict[tuple, int] = {}
    mod_loose: dict[tuple, int] = {}
    mod_name: dict[str, int] = {}
    for row in conn.execute("SELECT id, nom, id_filiere, semestre FROM modules"):
        mod_exact[(row[1], row[2], row[3])] = row[0]
        mod_loose[(row[1], row[2])] = row[0]
        mod_name[row[1]] = row[0]

    df["id_insc"] = df["id_inscriptionsessionprogramme"].astype(int)
    etudiants_created = 0
    etudiant_id_map: dict[int, int] = {}

    for id_insc, grp in df.groupby("id_insc"):
        row0 = grp.iloc[0]
        nom = str(row0["Nom"]).strip()
        prenom = str(row0["Prenom"]).strip()
        cursus = str(row0["Cursus"]).strip()
        sp = str(row0["SessionProgramme"]).strip()

        semestre, code_filiere, niveau = parse_cursus(cursus, sp)

        id_filiere = None
        if code_filiere:
            niv_map = filiere_map.get(code_filiere, {})
            if niveau:
                id_filiere = niv_map.get(niveau)
            if id_filiere is None and niv_map:
                id_filiere = next(iter(niv_map.values()))

        email = (
            f"{prenom.lower().replace(' ', '-')}"
            f".{nom.lower().replace(' ', '-')}@esith.net"
        )

        cur = conn.execute(
            "INSERT OR IGNORE INTO etudiants"
            " (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, cursus, session_programme)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (int(id_insc), nom, prenom, email, id_filiere, cursus, sp),
        )
        if cur.rowcount > 0:
            etudiants_created += 1

        row_db = conn.execute(
            "SELECT id FROM etudiants WHERE id_inscriptionsessionprogramme = ?", (int(id_insc),)
        ).fetchone()
        if row_db:
            etudiant_id_map[int(id_insc)] = row_db[0]

    conn.commit()

    absences_created = 0
    modules_not_found: list[str] = []
    module_id_cache: dict[tuple, int] = {}

    for _, row in df.iterrows():
        id_insc = int(row["id_insc"])
        id_etudiant = etudiant_id_map.get(id_insc)
        if id_etudiant is None:
            continue

        id_absence_konosys = str(int(row["id_absence"]))
        module_nom_raw = str(row["Module"]).strip()
        # Strip "_S\d+" suffix to match clean names in modules table
        m_suf2 = re.match(r"^(.+)_S(\d+)$", module_nom_raw)
        module_nom = m_suf2.group(1) if m_suf2 else module_nom_raw

        # Get etudiant cursus info for module lookup
        et_row = conn.execute(
            "SELECT id_filiere, cursus, session_programme FROM etudiants WHERE id = ?",
            (id_etudiant,),
        ).fetchone()
        id_filiere = et_row[0] if et_row else None
        semestre, _, _ = parse_cursus(et_row[1] if et_row else "", et_row[2] if et_row else "")

        cache_key = (module_nom, id_filiere, semestre)
        id_module = module_id_cache.get(cache_key, -1)

        if id_module == -1:
            if id_filiere and semestre and (module_nom, id_filiere, semestre) in mod_exact:
                id_module = mod_exact[(module_nom, id_filiere, semestre)]
            elif id_filiere and (module_nom, id_filiere) in mod_loose:
                id_module = mod_loose[(module_nom, id_filiere)]
            elif module_nom in mod_name:
                id_module = mod_name[module_nom]
            else:
                if module_nom not in modules_not_found:
                    modules_not_found.append(module_nom)
                cur2 = conn.execute(
                    "INSERT INTO modules (nom, id_filiere, semestre, volume_heures) VALUES (?, ?, ?, 48)",
                    (module_nom, id_filiere, semestre or "S0"),
                )
                id_module = cur2.lastrowid
                mod_name[module_nom] = id_module
                conn.commit()

            module_id_cache[cache_key] = id_module

        try:
            date_val = str(row["DATE"]).strip()
            try:
                date_absence = pd.to_datetime(date_val, dayfirst=True).strftime("%Y-%m-%d")
            except Exception:
                date_absence = date_val

            duree = float(row["DureeDecimal"]) if pd.notna(row.get("DureeDecimal")) else 0.0
            justifiee = str(row.get("Excuse", "")).strip().lower() == "oui"
            motif = str(row.get("Motif", "")).strip()
            if motif in (".", "nan", ""):
                motif = None
            seance = str(row.get("Seance", "")).strip()
            heure = str(row.get("Heure", "")).strip()

            conn.execute(
                "INSERT OR IGNORE INTO absences"
                " (id_absence_konosys, id_etudiant, id_module, module_nom, date_absence,"
                " seance, heure, duree_heures, justifiee, motif)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id_absence_konosys, id_etudiant, id_module, module_nom, date_absence,
                 seance, heure, duree, justifiee, motif),
            )
            absences_created += 1
        except Exception as e:
            print(f"[migrate] Erreur absence {id_absence_konosys}: {e}")

    conn.commit()
    conn.close()
    return etudiants_created, absences_created, modules_not_found


def print_summary(filieres_created, modules_created, etudiants_created, absences_created, modules_not_found):
    print("\n" + "=" * 55)
    print(f"[migrate] Filières créées    : {filieres_created}")
    print(f"[migrate] Modules importés   : {modules_created}")
    print(f"[migrate] Étudiants importés : {etudiants_created}")
    print(f"[migrate] Absences importées : {absences_created}")
    print(f"[migrate] Modules non trouvés (volume défaut 48h) : {len(modules_not_found)}")
    for m in modules_not_found:
        print(f"  - {m}")
    print("=" * 55)


def run():
    print("[migrate] Démarrage de la migration...")
    create_database()
    filieres_created, modules_created = import_modules()
    etudiants_created, absences_created, modules_not_found = import_etudiants_et_absences()
    print_summary(filieres_created, modules_created, etudiants_created, absences_created, modules_not_found)


if __name__ == "__main__":
    run()
