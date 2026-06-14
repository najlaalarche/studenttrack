"""
Génère 50 étudiants fictifs supplémentaires avec des absences réalistes.
Répartition : 60% AUTORISE | 25% AVERTI | 15% EXCLU
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"

NOMS = [
    "EL IDRISSI", "BENALI", "ALAMI", "CHERKAOUI", "MANSOURI", "TAHIRI",
    "BOUCHAIB", "NACIRI", "RHAJAOUI", "KASSIMI", "ZOUAOUI", "BENOMAR",
    "LAHLOU", "BENCHEKROUN", "BERRADA", "KETTANI", "EL OUAZZANI",
    "SERGHINI", "BENBRAHIM", "FILALI", "GUERRAOUI", "HAJJI", "IMRANI",
    "JABRI", "KHALIL", "LAMRANI", "MOUJAHID", "NAJI", "OUHABI", "QASMI",
    "RAISSOUNI", "SAHLI", "TOUIL", "YAACOUBI", "ZIANI", "ABOUBI",
    "BELKADI", "CHRAIBI", "DARIF", "ENNAJI", "FIHRI", "GHAZI", "HASSANI",
    "IDRISI", "JAMALI", "KARIMI", "LYAZIDI", "MEKNASSI", "OUAZZANI", "BAHJA",
]

PRENOMS_M = [
    "Youssef", "Mohammed", "Mehdi", "Amine", "Omar", "Hassan", "Rachid",
    "Karim", "Adil", "Badr", "Hamza", "Ismail", "Khalid", "Nour",
    "Soufian", "Taoufik", "Oussama", "Saad", "Redouane", "Jawad",
    "Ayoub", "Tariq", "Bilal", "Iliass", "Zakaria",
]

PRENOMS_F = [
    "Fatima", "Zineb", "Hajar", "Samira", "Nadia", "Amina", "Khadija",
    "Meryem", "Sara", "Leila", "Houda", "Imane", "Nawal", "Yasmine",
    "Rim", "Hind", "Soukaina", "Loubna", "Ghita", "Salma",
    "Dounia", "Safae", "Chaima", "Ikram", "Maroua",
]

NIVEAU_SEMESTRES = {
    "1ère année": ["S1", "S2"],
    "2ème année": ["S3", "S4"],
    "3ème année": ["S5", "S6"],
}

DATE_START = date(2024, 9, 1)
DATE_END   = date(2025, 5, 31)

random.seed(42)


def _random_date() -> str:
    delta = (DATE_END - DATE_START).days
    return (DATE_START + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def _make_email(prenom: str, nom: str) -> str:
    p = prenom.lower().replace(" ", "-").replace("'", "")
    n = nom.lower().replace(" ", "-").replace("'", "")
    return f"{p}.{n}@esith.net"


def _insert_absence(conn, cursor_id: int, id_etudiant: int, id_module: int,
                    module_nom: str, duree: float, justifiee: bool) -> None:
    konosys = f"GEN-{cursor_id:06d}"
    conn.execute(
        "INSERT OR IGNORE INTO absences"
        " (id_absence_konosys, id_etudiant, id_module, module_nom, date_absence,"
        " seance, heure, duree_heures, justifiee, motif)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (konosys, id_etudiant, id_module, module_nom, _random_date(),
         "Séance 1", "08:00", duree, justifiee, None),
    )


def generate(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row

    # Charger les filières disponibles avec leurs niveaux
    filieres = conn.execute("SELECT id, code, niveau FROM filieres ORDER BY code, niveau").fetchall()
    if not filieres:
        print("[gen] Aucune filière trouvée — lancez d'abord migrate.py")
        return

    # Pour chaque (filiere, niveau), récupérer les modules disponibles
    mods_by_filiere: dict[int, list] = {}
    for f in filieres:
        rows = conn.execute(
            "SELECT id, nom, semestre, volume_heures FROM modules WHERE id_filiere = ? AND volume_heures > 0",
            (f["id"],),
        ).fetchall()
        if rows:
            mods_by_filiere[f["id"]] = [dict(r) for r in rows]

    # Choisir uniquement les filières qui ont des modules
    filieres_avec_mods = [f for f in filieres if f["id"] in mods_by_filiere]
    if not filieres_avec_mods:
        print("[gen] Aucune filière avec modules trouvée")
        return

    NB_ETUDIANTS = 50
    # 60% AUTORISE / 20% AVERTI / 12% EXCLU / 8% CRITIQUE (score >= 70)
    profils_cibles = (
        ["AUTORISE"] * 30 +
        ["AVERTI"]   * 10 +
        ["EXCLU"]    *  6 +
        ["CRITIQUE"] *  4
    )
    random.shuffle(profils_cibles)

    # Noms déjà utilisés pour éviter les doublons d'email
    used_emails: set[str] = set()
    existing = conn.execute("SELECT email FROM etudiants").fetchall()
    for r in existing:
        used_emails.add(r["email"])

    id_insc_counter = 200001
    abs_id_counter  = 900001
    nb_created = 0

    for cible in profils_cibles:
        # Choisir une filière aléatoire avec modules
        filiere_row = random.choice(filieres_avec_mods)
        id_filiere  = filiere_row["id"]
        niveau      = filiere_row["niveau"]
        code        = filiere_row["code"]

        semestres = NIVEAU_SEMESTRES.get(niveau, ["S1", "S2"])
        semestre  = random.choice(semestres)

        # Générer un nom unique
        for _ in range(100):
            is_female = random.random() < 0.45
            prenom = random.choice(PRENOMS_F if is_female else PRENOMS_M)
            nom    = random.choice(NOMS)
            email  = _make_email(prenom, nom)
            if email not in used_emails:
                used_emails.add(email)
                break
        else:
            # Fallback si tous les noms sont pris
            prenom = f"Etudiant{nb_created}"
            nom    = "ESITH"
            email  = f"etudiant{nb_created}.esith@esith.net"
            used_emails.add(email)

        cursus           = f"{semestre}-{code}"
        session_programme = f"{niveau} - Génie Industriel"

        # Insérer l'étudiant
        cur = conn.execute(
            "INSERT OR IGNORE INTO etudiants"
            " (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, cursus, session_programme)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id_insc_counter, nom, prenom, email, id_filiere, cursus, session_programme),
        )
        if cur.rowcount == 0:
            id_insc_counter += 1
            continue

        id_etudiant = conn.execute(
            "SELECT id FROM etudiants WHERE id_inscriptionsessionprogramme = ?", (id_insc_counter,)
        ).fetchone()["id"]
        id_insc_counter += 1

        # Sélectionner 4-6 modules de la filière
        all_mods = mods_by_filiere[id_filiere]
        nb_mods  = min(random.randint(4, 6), len(all_mods))
        chosen_mods = random.sample(all_mods, nb_mods)

        # Générer les absences selon le profil cible
        for i, mod in enumerate(chosen_mods):
            vol     = mod["volume_heures"]
            id_mod  = mod["id"]
            nom_mod = mod["nom"]

            if cible == "AUTORISE":
                # taux_nj < 20%, taux_total < 50%
                max_nj_h    = vol * 0.18
                max_just_h  = vol * 0.28
                heures_nj   = round(random.uniform(0, max_nj_h), 1)
                heures_just = round(random.uniform(0, max_just_h), 1)

            elif cible == "AVERTI":
                if i == 0:
                    # Premier module : taux_nj >= 20% et < 50%
                    heures_nj   = round(random.uniform(vol * 0.20, vol * 0.48), 1)
                    heures_just = round(random.uniform(0, vol * 0.10), 1)
                else:
                    # Autres : profil normal
                    heures_nj   = round(random.uniform(0, vol * 0.15), 1)
                    heures_just = round(random.uniform(0, vol * 0.10), 1)

            elif cible == "EXCLU":
                if i == 0:
                    # taux_total >= 50%, mais score peut rester < 70
                    heures_nj   = round(random.uniform(vol * 0.25, vol * 0.45), 1)
                    heures_just = round(random.uniform(vol * 0.10, vol * 0.25), 1)
                    while (heures_nj + heures_just) < vol * 0.50:
                        heures_just += 1.5
                else:
                    heures_nj   = round(random.uniform(0, vol * 0.15), 1)
                    heures_just = round(random.uniform(0, vol * 0.10), 1)

            else:  # CRITIQUE — score >= 70 : taux_nj >= 65%, taux_total >= 80%
                if i == 0:
                    heures_nj   = round(random.uniform(vol * 0.65, vol * 0.80), 1)
                    heures_just = round(random.uniform(vol * 0.15, vol * 0.20), 1)
                    # Cap à volume_heures
                    total = heures_nj + heures_just
                    if total > vol:
                        ratio = vol / total
                        heures_nj   = round(heures_nj   * ratio, 1)
                        heures_just = round(heures_just * ratio, 1)
                else:
                    heures_nj   = round(random.uniform(0, vol * 0.15), 1)
                    heures_just = round(random.uniform(0, vol * 0.08), 1)

            # Insérer des absences par tranches de 1-3h
            duree_seance = 1.5  # heures par séance

            h_nj_restant = heures_nj
            while h_nj_restant > 0:
                h = min(duree_seance, h_nj_restant)
                if h < 0.5:
                    break
                _insert_absence(conn, abs_id_counter, id_etudiant, id_mod, nom_mod, h, False)
                abs_id_counter += 1
                h_nj_restant   -= h

            h_just_restant = heures_just
            while h_just_restant > 0:
                h = min(duree_seance, h_just_restant)
                if h < 0.5:
                    break
                _insert_absence(conn, abs_id_counter, id_etudiant, id_mod, nom_mod, h, True)
                abs_id_counter += 1
                h_just_restant -= h

        nb_created += 1

    conn.commit()
    print(f"[gen] {nb_created} étudiants fictifs créés")


def print_summary(conn: sqlite3.Connection) -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.ingestion.reader import load_absences_df
    from backend.analysis.engine import calculer_profils, filtrer_alertes

    total = conn.execute("SELECT COUNT(*) FROM etudiants").fetchone()[0]
    print(f"\n{'='*55}")
    print(f"Total étudiants en base : {total}")

    df = load_absences_df()
    profils = calculer_profils(df)

    autorise = sum(1 for p in profils if p.action_recommandee == "AUCUNE")
    averti   = sum(1 for p in profils if p.action_recommandee == "WARN_STUDENT")
    exclu    = sum(1 for p in profils if p.action_recommandee == "NOTIFY_EXCLUSION")

    faible   = sum(1 for p in profils if p.niveau_risque == "faible")
    modere   = sum(1 for p in profils if p.niveau_risque == "modéré")
    critique = sum(1 for p in profils if p.niveau_risque == "critique")

    print(f"\nRépartition statut (étudiants avec absences) :")
    print(f"  AUTORISE : {autorise}")
    print(f"  AVERTI   : {averti}")
    print(f"  EXCLU    : {exclu}")
    print(f"\nRépartition niveau de risque :")
    print(f"  faible   : {faible}")
    print(f"  modéré   : {modere}")
    print(f"  critique : {critique}")
    print(f"{'='*55}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[gen] Base SQLite introuvable : {DB_PATH}")
        print("[gen] Lancez d'abord : python backend/database/migrate.py")
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    generate(conn)
    print_summary(conn)
    conn.close()
