"""
Simulation d'un semestre complet (16 semaines, 28/09/2026 → 16/01/2027) pour la démo.

1. Sauvegarde data/studenttrack.db puis vide absences, etudiants, notes_performance, planning_seances
   (+ alertes, emails_log, notes, inscriptions, password_resets des anciens étudiants).
   modules, filieres, professeurs, users et parametres sont conservés.
2. Crée 40 étudiants : IMS2G1 (15), GI-BDM2G1 (15), EO2G1 (10). Les 4 titulaires d'un compte users
   sont recréés avec le même email et leur compte est rattaché au nouvel id.
3. Réutilise 5 modules S3 existants par filière (2ème année).
4. Génère les absences : 20 % EXCLU, 25 % AVERTI, 55 % AUTORISÉ.
5. Écrit 16 fichiers planning + notes_performance_S1.xlsx dans simulation_s1/, puis les importe
   avec les mêmes fonctions que l'interface (import_planning / import_performance).

Usage : python backend/database/simulation_s1.py
"""
import math
import random
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
OUT_DIR = ROOT / "simulation_s1"

sys.path.insert(0, str(ROOT))
from backend.database.import_notes import _gen_email  # noqa: E402
from backend.database.import_planning import import_planning  # noqa: E402
from backend.database.import_performance import import_performance  # noqa: E402

random.seed(2026)

DEBUT       = date(2026, 9, 28)   # lundi semaine 1
NB_SEMAINES = 16
ANNEE       = "2026-2027"
DUREE       = 2.0                 # heures par séance

# groupe, code filière, préfixe matricule, effectif, (EXCLU, AVERTI, AUTORISE), modules S3 réutilisés
GROUPES = [
    ("IMS2G1", "IMS", "IMS", 15, (3, 4, 8), [
        "Anglais", "Robotique", "Développement web et Mobile",
        "Programmation Orientée Objet (Niveau 2 : Java)", "Communication et Réseaux pour Systèmes Embarqués",
    ]),
    ("GI-BDM2G1", "GI-BDM", "BDM", 15, (3, 4, 8), [
        "Anglais", "Gestion de production", "Management de la maintenance / TPM",
        "Logistique", "Bases de données & Big Data",
    ]),
    ("EO2G1", "GI-EO", "EO", 10, (2, 2, 6), [
        "Anglais", "Gestion de production", "Logistique",
        "Machine Learning", "Management de la maintenance / TPM",
    ]),
]

NOMS = [
    ("Benali", "Yassine"), ("El Idrissi", "Salma"), ("Bennani", "Omar"), ("Tazi", "Imane"),
    ("Alaoui", "Mehdi"), ("Chraibi", "Kawtar"), ("Berrada", "Hamza"), ("El Fassi", "Nisrine"),
    ("Amrani", "Ayoub"), ("Ouazzani", "Hiba"), ("Lahlou", "Zakaria"), ("Sefrioui", "Meryem"),
    ("Kettani", "Anouar"), ("Benjelloun", "Ghita"), ("Saidi", "Soufiane"), ("Rami", "Chaimae"),
    ("El Mansouri", "Adil"), ("Bouzidi", "Oumaima"), ("Haddad", "Reda"), ("Naciri", "Sara"),
    ("Ait Lahcen", "Brahim"), ("Moussaoui", "Fatima Zahra"), ("Lamrani", "Ilyas"), ("Zerouali", "Douae"),
    ("El Khattabi", "Achraf"), ("Bakkali", "Asmae"), ("Cherkaoui", "Nabil"), ("Hajji", "Yousra"),
    ("Ziani", "Taha"), ("Belhaj", "Rim"), ("Fikri", "Othmane"), ("Essaadi", "Wiam"),
    ("Mernissi", "Karim"), ("Tahiri", "Lina"), ("Daoudi", "Amine"), ("Rifai", "Siham"),
]

CRENEAUX = [("08:30", "10:30"), ("10:45", "12:45"), ("14:00", "16:00")]
SALLES   = ["A101", "A102", "B201", "B204", "C305", "Labo 1", "Labo 2"]
PROFS    = ["M. Bensaid", "Mme Kabbaj", "M. El Ouardi", "Mme Squalli", "M. Hilali",
            "Mme Raji", "M. Tounsi", "Mme Filali", "M. Jebli", "Mme Sbai"]
MOTIFS   = ["Maladie", "Certificat médical", "Raison familiale", "Convocation administrative"]


# ── 1. Remise à zéro ──────────────────────────────────────────────────────────

def sauvegarder() -> Path:
    dest = DB_PATH.parent / "backups" / f"studenttrack_backup_avant_simulation_s1_{datetime.now():%Y%m%d_%H%M%S}.db"
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(DB_PATH, dest)
    return dest


def vider(conn) -> list[dict]:
    """Vide les tables étudiants et dépendances ; renvoie les titulaires de compte à recréer."""
    comptes = [
        {"email": r[0], "nom": r[1], "prenom": r[2], "code": r[3]}
        for r in conn.execute(
            """SELECT u.email, e.nom, e.prenom, f.code FROM users u
               JOIN etudiants e ON e.id = u.id_etudiant LEFT JOIN filieres f ON f.id = e.id_filiere"""
        ).fetchall()
    ]
    for table in ["emails_log", "alertes", "notes", "inscriptions", "password_resets",
                  "absences", "notes_performance", "planning_seances", "etudiants"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    return comptes


# ── 2-3. Étudiants et modules ─────────────────────────────────────────────────

def _filiere_2a(conn, code: str) -> int:
    row = conn.execute("SELECT id FROM filieres WHERE code=? AND niveau LIKE '2%'", (code,)).fetchone()
    if not row:
        raise SystemExit(f"Filière {code} 2ème année introuvable")
    return row[0]


def _modules(conn, id_filiere: int, noms: list[str]) -> list[dict]:
    mods = []
    for nom in noms:
        row = conn.execute(
            "SELECT id, nom, volume_heures FROM modules WHERE id_filiere=? AND semestre='S3' AND nom=?",
            (id_filiere, nom),
        ).fetchone()
        if not row:
            raise SystemExit(f"Module S3 « {nom} » introuvable pour la filière {id_filiere}")
        mods.append({"id": row[0], "nom": row[1], "volume": row[2], "code": f"M{row[0]:04d}"})
    return mods


def _titre(s: str) -> str:
    """'JIRARI' / 'hamadi' -> 'Jirari' / 'Hamadi' ; 'El Fassi' inchangé."""
    return s.title() if s.isupper() or s.islower() else s


def creer_etudiants(conn, comptes: list[dict]) -> list[dict]:
    noms = list(NOMS)
    etudiants, n_insc = [], 2026000
    for groupe, code, prefixe, effectif, repartition, _ in GROUPES:
        id_filiere = _filiere_2a(conn, code)
        # titulaires d'un compte users de cette filière en premier (mêmes nom, prénom, email)
        identites = [(_titre(c["nom"]), _titre(c["prenom"]), c["email"]) for c in comptes if c["code"] == code]
        while len(identites) < effectif:
            nom, prenom = noms.pop(0)
            identites.append((nom, prenom, _gen_email(prenom, nom)))
        profils = ["EXCLU"] * repartition[0] + ["AVERTI"] * repartition[1] + ["AUTORISE"] * repartition[2]
        random.shuffle(profils)

        for i, ((nom, prenom, email), profil) in enumerate(zip(identites, profils), 1):
            n_insc += 1
            cur = conn.execute(
                """INSERT INTO etudiants (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere,
                                          cursus, session_programme, matricule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (n_insc, nom, prenom, email, id_filiere, f"S3-{groupe}",
                 f"{groupe} 2ème année {ANNEE}", f"{prefixe}25{i:02d}"),
            )
            etudiants.append({"id": cur.lastrowid, "nom": nom, "prenom": prenom, "email": email,
                              "groupe": groupe, "matricule": f"{prefixe}25{i:02d}", "profil": profil})

    # Comptes users : rattachés au nouvel id (même email)
    for c in comptes:
        et = next((e for e in etudiants if e["email"] == c["email"]), None)
        if et:
            conn.execute("UPDATE users SET id_etudiant=? WHERE email=?", (et["id"], c["email"]))
        else:
            print(f"  [!] compte {c['email']} non rattaché (filière {c['code']} hors simulation)")
    conn.commit()
    return etudiants


# ── 5. Planning (emploi du temps fixe, 2 séances × 2h par module et par semaine) ──

def generer_planning(modules_par_groupe: dict) -> list[list[dict]]:
    """Retourne une liste de 16 semaines, chacune = liste de séances (lignes du fichier Excel)."""
    semaines, n = [], 0
    types = ["CM", "TD", "TP"]
    for s in range(NB_SEMAINES):
        lundi, lignes = DEBUT + timedelta(weeks=s), []
        for g_idx, (groupe, mods) in enumerate(modules_par_groupe.items()):
            for m_idx, mod in enumerate(mods):
                # séance 1 : jour m_idx, créneau du matin ; séance 2 : deux jours plus tard l'après-midi
                for k, (jour, creneau) in enumerate([(m_idx, (m_idx + g_idx) % 2), ((m_idx + 2) % 5, 2)]):
                    n += 1
                    d = lundi + timedelta(days=jour)
                    hd, hf = CRENEAUX[creneau]
                    lignes.append({
                        "id_seance": f"SIM{n:06d}",
                        "dateSeance": d.strftime("%d/%m/%Y"),
                        "numDay": d.isoweekday(),
                        "HD": hd, "HF": hf,
                        "DureeMin": int(DUREE * 60), "DureeMinDecimal": DUREE,
                        "Salle": SALLES[(m_idx + g_idx + k) % len(SALLES)],
                        "Prof": PROFS[(g_idx * 5 + m_idx) % len(PROFS)],
                        "Groupe": groupe,
                        "Module": mod["nom"], "CodeModule": mod["code"],
                        "TypeSeance": "CM" if k == 0 else types[1 + (s + m_idx) % 2],
                        "Cursus": f"S3-{groupe}",
                        "AppelFait": "Oui",
                    })
        semaines.append(lignes)
    return semaines


# ── 4. Absences ───────────────────────────────────────────────────────────────

def _cible_nj(profil: str, volume: int, principal: bool) -> int:
    """Nombre de séances NJ (2h) pour un module, cohérent avec les seuils du moteur (sur volume_heures)."""
    seances = lambda taux: taux * volume / DUREE  # noqa: E731
    if profil == "EXCLU" and principal:
        return min(30, math.floor(seances(0.50)) + random.randint(1, 4))          # NJ > 50 %
    if profil in ("EXCLU", "AVERTI") and principal:
        return random.randint(math.ceil(seances(0.21)), math.floor(seances(0.45)))  # 20 % ≤ NJ < 50 %
    return random.randint(0, max(0, math.ceil(seances(0.19)) - 1) // 2)            # NJ < 20 %, plutôt bas


def generer_absences(conn, etudiants: list[dict], semaines: list[list[dict]], modules_par_groupe: dict) -> int:
    n = 0
    for et in etudiants:
        seances_et = [l for sem in semaines for l in sem if l["Groupe"] == et["groupe"]]
        mods = modules_par_groupe[et["groupe"]]
        principaux = set(random.sample(range(len(mods)), 2 if et["profil"] == "EXCLU" else 1))
        lignes_et = []
        for m_idx, mod in enumerate(mods):
            principal = m_idx in principaux and et["profil"] != "AUTORISE"
            # EXCLU : 1 module > 50 % NJ, le 2ème module principal en zone AVERTI
            profil_mod = et["profil"] if (et["profil"] != "EXCLU" or m_idx == min(principaux)) else "AVERTI"
            nb_nj = _cible_nj(profil_mod, mod["volume"], principal)
            nb_j  = random.randint(0, 2)
            # taux total < 50 % hors module EXCLU
            max_total = 30 if profil_mod == "EXCLU" and principal else math.floor(0.49 * mod["volume"] / DUREE)
            nb_j = max(0, min(nb_j, max_total - nb_nj))

            candidates = [l for l in seances_et if l["Module"] == mod["nom"]]
            # les étudiants en difficulté s'absentent de plus en plus au fil du semestre
            poids = [1 + (i / len(candidates)) * (2 if principal else 0) for i in range(len(candidates))]
            choisies = set()
            while len(choisies) < min(nb_nj + nb_j, len(candidates)):
                choisies.add(random.choices(range(len(candidates)), weights=poids)[0])
            choisies = sorted(choisies)
            random.shuffle(choisies)
            for k, idx in enumerate(choisies):
                lignes_et.append((candidates[idx], mod, k >= nb_nj))

        if not lignes_et:  # au moins une absence : le profil n'apparaît sinon pas dans /api/etudiants
            l = random.choice(seances_et)
            lignes_et.append((l, next(m for m in mods if m["nom"] == l["Module"]), True))

        for seance, mod, justifiee in lignes_et:
            n += 1
            d = datetime.strptime(seance["dateSeance"], "%d/%m/%Y").date()
            conn.execute(
                """INSERT INTO absences (id_absence_konosys, id_etudiant, id_module, module_nom, date_absence,
                                         seance, heure, duree_heures, justifiee, motif)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"SIM-ABS-{n:05d}", et["id"], mod["id"], mod["nom"], d.isoformat(),
                 f"Séance {seance['id_seance']}", f"{seance['HD']}-{seance['HF']}", DUREE,
                 int(justifiee), random.choice(MOTIFS) if justifiee else None),
            )
    conn.commit()
    return n


# ── 6. Notes de performance ───────────────────────────────────────────────────

def generer_notes(conn, etudiants: list[dict]) -> list[dict]:
    planifie = 2 * DUREE * 5 * NB_SEMAINES  # heures planifiées par étudiant sur le semestre
    lignes = []
    for et in etudiants:
        h_abs = conn.execute(
            "SELECT COALESCE(SUM(duree_heures), 0) FROM absences WHERE id_etudiant=?", (et["id"],)
        ).fetchone()[0]
        brute = round(random.uniform(8, 17), 2)
        # pénalité proportionnelle au taux d'absence global (×1,5) + léger bruit
        perte = min(0.6, (h_abs / planifie) * 1.5 + random.uniform(0, 0.02))
        nette = round(brute * (1 - perte), 2)
        lignes.append({"Matricule": et["matricule"], "Moyenne Brute": brute, "Moyenne Nette": nette,
                       "Moyenne S1": nette, "Moyenne S2": None, "Moyenne Annee Scolaire": None})
    return lignes


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Base introuvable : {DB_PATH}")
    print(f"Sauvegarde : {sauvegarder().name}")

    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob("*.xlsx"):
        f.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    comptes = vider(conn)

    modules_par_groupe = {g: _modules(conn, _filiere_2a(conn, code), noms) for g, code, *_, noms in GROUPES}
    etudiants = creer_etudiants(conn, comptes)
    semaines  = generer_planning(modules_par_groupe)
    nb_abs    = generer_absences(conn, etudiants, semaines, modules_par_groupe)
    notes     = generer_notes(conn, etudiants)
    conn.close()

    # Fichiers Excel puis import par le même code que l'interface admin
    for s, lignes in enumerate(semaines, 1):
        chemin = OUT_DIR / f"planning_S{s:02d}_{DEBUT + timedelta(weeks=s - 1):%d%m%Y}.xlsx"
        pd.DataFrame(lignes).to_excel(chemin, index=False)
        res = import_planning(chemin, DEBUT if s == 1 else None)
        assert res["seances_ajoutees"] == len(lignes), res
    chemin_notes = OUT_DIR / "notes_performance_S1.xlsx"
    pd.DataFrame(notes).to_excel(chemin_notes, index=False)
    res = import_performance(chemin_notes, ANNEE)
    assert not res["non_trouves"], res

    # Statuts + alertes, et absences marquées comme connues : la prochaine synchro n'enverra pas 40 emails
    from backend.ingestion.reader import load_absences_df, detect_delta
    from backend.analysis.engine import calculer_profils, upsert_alertes
    profils = calculer_profils(load_absences_df())
    upsert_alertes(profils)
    detect_delta()

    conn = sqlite3.connect(DB_PATH)
    print()
    for t in ["etudiants", "absences", "planning_seances", "notes_performance"]:
        print(f"{t} : {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]} lignes")
    conn.close()

    attendu = {e["id"]: e["profil"] for e in etudiants}
    obtenu  = {int(p.id_etudiant): ("EXCLU" if p.nb_modules_exclu else "AVERTI" if p.nb_modules_averti else "AUTORISE")
               for p in profils}
    ecarts = [i for i in attendu if attendu[i] != obtenu.get(i)]
    print(f"\nStatuts : EXCLU {sum(v == 'EXCLU' for v in obtenu.values())} · "
          f"AVERTI {sum(v == 'AVERTI' for v in obtenu.values())} · "
          f"AUTORISE {sum(v == 'AUTORISE' for v in obtenu.values())} "
          f"({'conformes au profil généré' if not ecarts else f'{len(ecarts)} écart(s)'})")
    print(f"Fichiers : {OUT_DIR}  ({NB_SEMAINES} plannings + {chemin_notes.name}) · {nb_abs} absences générées")


if __name__ == "__main__":
    main()
