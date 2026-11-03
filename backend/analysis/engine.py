import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"

SEUIL_ALERTE    = 20.0
SEUIL_EXCLUSION = 50.0


@dataclass
class StatutModule:
    module:              str
    id_module:           int
    semestre:            str
    total_seances:       int    # = volume_heures
    nb_abs_nj:           int
    nb_abs_just:         int
    nb_abs_total:        int
    taux_nj:             float  # heures_nj / volume_heures * 100
    taux_total:          float  # (heures_nj + heures_just) / volume_heures * 100
    seuil_alerte:        float
    seuil_exclusion:     float
    statut_exam:         str
    avert_email_envoye:  bool
    exclu_email_envoye:  bool
    alerte_module:       str


@dataclass
class ProfilEtudiant:
    id_etudiant:          str
    nom:                  str
    prenom:               str
    email:                str
    filiere:              str
    code_filiere:         str
    annee:                str
    cursus:               str
    total_abs_nj:         int
    total_abs_just:       int
    total_absences:       int
    derniere_absence:     str
    modules:              list = field(default_factory=list)
    nb_modules_exclu:     int  = 0
    nb_modules_averti:    int  = 0
    module_plus_grave:    str  = ""
    moyenne_generale:     float | None = None
    action_recommandee:   str   = "AUCUNE"
    notes_modules:        list  = field(default_factory=list)


def _get_email_flags(id_etudiant_int: int, id_module: int) -> tuple[bool, bool]:
    """Lit les flags d'envoi depuis la table alertes."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT avert_envoye, exclu_envoye FROM alertes WHERE id_etudiant=? AND id_module=?",
            (id_etudiant_int, id_module),
        ).fetchone()
        conn.close()
        if row:
            return bool(row[0]), bool(row[1])
    except Exception:
        pass
    return False, False


def _charger_moyennes() -> dict[int, float]:
    """Moyenne la plus récente (année universitaire puis semestre) par étudiant."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id_etudiant, moyenne_generale FROM notes"
            " WHERE moyenne_generale IS NOT NULL"
            " ORDER BY annee_universitaire, CAST(SUBSTR(semestre, 2) AS INTEGER), imported_at"
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:  # table notes absente
        return {}
    return {id_et: float(moy) for id_et, moy in rows}  # la dernière ligne l'emporte


def _charger_identites(ids: set[int]) -> dict[int, dict]:
    """Identité des étudiants sans absence (mêmes champs que load_absences_df)."""
    if not ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""SELECT e.id, e.nom, e.prenom, e.email, COALESCE(e.cursus, '') AS cursus,
                   COALESCE(f.nom, '') AS filiere, COALESCE(f.code, '') AS code_filiere,
                   COALESCE(f.niveau, '') AS annee
            FROM etudiants e LEFT JOIN filieres f ON e.id_filiere = f.id
            WHERE e.id IN ({','.join('?' * len(ids))})""",
        tuple(ids),
    ).fetchall()
    conn.close()
    return {r["id"]: dict(r) for r in rows}


def _calculer_statut_module(module_nom: str, id_module: int, grp_mod: pd.DataFrame, id_etudiant_int: int) -> StatutModule:
    volume_heures = int(grp_mod["volume_heures"].iloc[0]) if len(grp_mod) > 0 else 48
    if volume_heures <= 0:
        volume_heures = 48

    semestre = str(grp_mod["semestre"].iloc[0]) if "semestre" in grp_mod.columns and len(grp_mod) > 0 else ""

    nj_mask  = ~grp_mod["justifiee"]
    jus_mask = grp_mod["justifiee"]

    heures_nj   = float(grp_mod.loc[nj_mask,  "duree_heures"].sum())
    heures_just = float(grp_mod.loc[jus_mask, "duree_heures"].sum())

    nb_nj   = int(nj_mask.sum())
    nb_just = int(jus_mask.sum())
    nb_tot  = nb_nj + nb_just

    taux_nj    = round(heures_nj                   / volume_heures * 100, 2)
    taux_total = round((heures_nj + heures_just)   / volume_heures * 100, 2)

    if taux_total >= SEUIL_EXCLUSION:
        statut = "EXCLU"
        alerte = f"Exclu : {taux_total:.1f}% du volume horaire manqué"
    elif taux_nj >= SEUIL_ALERTE:
        statut = "AVERTI"
        alerte = f"Averti : {taux_nj:.1f}% NJ (seuil {SEUIL_ALERTE:.0f}%)"
    else:
        statut = "AUTORISE"
        alerte = ""

    avert_flag, exclu_flag = _get_email_flags(id_etudiant_int, id_module)

    return StatutModule(
        module=module_nom,
        id_module=id_module,
        semestre=semestre,
        total_seances=volume_heures,
        nb_abs_nj=nb_nj,
        nb_abs_just=nb_just,
        nb_abs_total=nb_tot,
        taux_nj=taux_nj,
        taux_total=taux_total,
        seuil_alerte=SEUIL_ALERTE,
        seuil_exclusion=SEUIL_EXCLUSION,
        statut_exam=statut,
        avert_email_envoye=avert_flag,
        exclu_email_envoye=exclu_flag,
        alerte_module=alerte,
    )


def calculer_profils(df_abs: pd.DataFrame) -> list[ProfilEtudiant]:
    profils = []
    moyennes = _charger_moyennes()

    # Étudiants avec absences + étudiants n'ayant que des notes (ex. créés par l'import notes)
    groupes = list(df_abs.groupby("id_etudiant"))
    ids_avec_abs = {int(i) for i, _ in groupes if str(i).isdigit()}
    identites = _charger_identites(set(moyennes) - ids_avec_abs)
    groupes += [(str(i), df_abs.iloc[0:0]) for i in sorted(identites)]

    for id_etudiant, groupe in groupes:
        row0 = groupe.iloc[0] if len(groupe) else identites[int(id_etudiant)]
        nom          = str(row0.get("nom", ""))
        prenom       = str(row0.get("prenom", ""))
        email        = str(row0.get("email", "inconnu@esith.net"))
        filiere      = str(row0.get("filiere", ""))
        code_filiere = str(row0.get("code_filiere", ""))
        annee        = str(row0.get("annee", ""))
        cursus       = str(row0.get("cursus", ""))

        id_etudiant_int = int(id_etudiant) if str(id_etudiant).isdigit() else 0

        total_nj   = int((~groupe["justifiee"]).sum())
        total_just = int(groupe["justifiee"].sum())
        total_abs  = len(groupe)

        dates_valides = groupe["date_absence"].dropna()
        derniere = str(dates_valides.max().date()) if not dates_valides.empty else ""

        statuts_modules = []
        for module_nom, grp_mod in groupe.groupby("module"):
            id_module = int(grp_mod["id_module_db"].iloc[0]) if "id_module_db" in grp_mod.columns else 0
            sm = _calculer_statut_module(module_nom, id_module, grp_mod, id_etudiant_int)
            statuts_modules.append(sm)

        nb_exclu  = sum(1 for s in statuts_modules if s.statut_exam == "EXCLU")
        nb_averti = sum(1 for s in statuts_modules if s.statut_exam == "AVERTI")

        ordre = {"EXCLU": 2, "AVERTI": 1, "AUTORISE": 0}
        plus_grave = max(statuts_modules, key=lambda s: ordre[s.statut_exam], default=None)
        module_grave_nom = plus_grave.module if plus_grave else ""

        moyenne = moyennes.get(id_etudiant_int)

        if nb_exclu > 0:
            action = "NOTIFY_EXCLUSION"
        elif nb_averti > 0:
            action = "WARN_STUDENT"
        else:
            action = "AUCUNE"

        profils.append(ProfilEtudiant(
            id_etudiant=str(id_etudiant),
            nom=nom,
            prenom=prenom,
            email=email,
            filiere=filiere,
            code_filiere=code_filiere,
            annee=annee,
            cursus=cursus,
            total_abs_nj=total_nj,
            total_abs_just=total_just,
            total_absences=total_abs,
            derniere_absence=derniere,
            modules=statuts_modules,
            nb_modules_exclu=nb_exclu,
            nb_modules_averti=nb_averti,
            module_plus_grave=module_grave_nom,
            moyenne_generale=moyenne,
            action_recommandee=action,
        ))

    return profils


def filtrer_alertes(profils: list) -> list:
    return [p for p in profils if p.action_recommandee != "AUCUNE"]


def upsert_alertes(profils: list[ProfilEtudiant]):
    """Écrit ou met à jour la table alertes après calcul des profils."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    for profil in profils:
        id_etudiant_int = int(profil.id_etudiant) if profil.id_etudiant.isdigit() else 0
        for mod in profil.modules:
            if not mod.id_module:
                continue
            conn.execute(
                """INSERT INTO alertes (id_etudiant, id_module, statut, taux_nj, taux_total, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id_etudiant, id_module) DO UPDATE SET
                       statut     = excluded.statut,
                       taux_nj    = excluded.taux_nj,
                       taux_total = excluded.taux_total,
                       updated_at = excluded.updated_at""",
                (id_etudiant_int, mod.id_module, mod.statut_exam, mod.taux_nj, mod.taux_total, now),
            )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.ingestion.reader import load_absences_df

    if not DB_PATH.exists():
        print("[engine] Base SQLite introuvable")
        sys.exit(1)

    df_abs = load_absences_df()
    profils = calculer_profils(df_abs)
    upsert_alertes(profils)
    alertes = filtrer_alertes(profils)

    print(f"\n[engine] {len(profils)} profils recalculés | {len(alertes)} alertes\n")

    # ── Résumé par statut ────────────────────────────────────────────────
    print("=== RÉSUMÉ DES STATUTS ===")
    print(f"  EXCLU    (>= 1 module exclu)  : {sum(1 for p in profils if p.nb_modules_exclu > 0)} étudiant(s)")
    print(f"  AVERTI   (>= 1 module averti) : {sum(1 for p in profils if p.nb_modules_exclu == 0 and p.nb_modules_averti > 0)} étudiant(s)")
    print(f"  AUTORISE                      : {sum(1 for p in profils if p.action_recommandee == 'AUCUNE')} étudiant(s)")

    # ── Détail complet ───────────────────────────────────────────────────
    print("\n=== DÉTAIL PAR ÉTUDIANT ===")
    for p in profils:
        moy = f"{p.moyenne_generale:.2f}" if p.moyenne_generale is not None else "-"
        print(f"  {p.prenom} {p.nom} | modules={p.nb_modules_exclu}E/{p.nb_modules_averti}A/{len(p.modules)} "
              f"| moy={moy} | {p.action_recommandee}")
        for m in p.modules:
            if m.statut_exam != "AUTORISE":
                print(f"    [{m.statut_exam}] {m.module} — NJ:{m.nb_abs_nj} ({m.taux_nj:.1f}%) | total:{m.taux_total:.1f}% / {m.total_seances}h")
