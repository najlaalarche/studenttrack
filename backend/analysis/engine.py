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
    moyenne_generale:     float = 0.0
    score_notes:          float = 0.0
    score_absences:       float = 0.0
    score_global:         float = 0.0
    niveau_risque_scoring: str  = "VERT"
    score_risque:         float = 0.0
    niveau_risque:        str   = "faible"
    niveau_alerte:        int   = 0
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

    for id_etudiant, groupe in df_abs.groupby("id_etudiant"):
        row0 = groupe.iloc[0]
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

        # ── Score de base : pire taux NJ (module le plus problématique) ──────
        if statuts_modules:
            pire_taux_nj = max(s.taux_nj for s in statuts_modules)
        else:
            pire_taux_nj = 0.0

        if pire_taux_nj >= 50:
            score_base = 100.0
        elif pire_taux_nj >= 33:
            score_base = 85.0
        elif pire_taux_nj >= 20:
            score_base = 60.0
        elif pire_taux_nj >= 10:
            score_base = 35.0
        else:
            score_base = round(pire_taux_nj * 3, 2)

        # ── Règles EXCLU / AVERTI ──────────────────────────────────────────
        if nb_exclu > 0:
            score_risque  = max(score_base, 70.0)
            niveau_risque = "critique"
            niveau_alerte = 3
        elif nb_averti > 0:
            score_risque  = max(score_base, 40.0)
            niveau_risque = "critique" if score_risque >= 70 else "modéré"
            niveau_alerte = 3 if score_risque >= 70 else 2
        else:
            score_risque = score_base
            if score_risque >= 70:
                niveau_risque = "critique"
                niveau_alerte = 3
            elif score_risque >= 40:
                niveau_risque = "modéré"
                niveau_alerte = 2
            else:
                niveau_risque = "faible"
                niveau_alerte = 0

        score_global = score_risque

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
            score_global=score_global,
            score_risque=score_risque,
            niveau_risque_scoring="ROUGE" if nb_exclu > 0 else ("ORANGE" if nb_averti > 0 else "VERT"),
            niveau_risque=niveau_risque,
            niveau_alerte=niveau_alerte,
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

    # ── Résumé par niveau ────────────────────────────────────────────────
    critiques = [p for p in profils if p.niveau_risque == "critique"]
    moderes   = [p for p in profils if p.niveau_risque == "modéré"]
    faibles   = [p for p in profils if p.niveau_risque == "faible"]

    print("=== RÉSUMÉ DES NIVEAUX DE RISQUE ===")
    print(f"  Critique  (score >= 70) : {len(critiques)} étudiant(s)")
    print(f"  Modéré    (40-69)       : {len(moderes)} étudiant(s)")
    print(f"  Faible    (< 40)        : {len(faibles)} étudiant(s)")

    # ── Vérification EXCLU -> critique ──────────────────────────────────
    print("\n=== VERIFICATION EXCLU -> critique ===")
    erreurs_exclu = [p for p in profils if p.nb_modules_exclu > 0 and p.niveau_risque != "critique"]
    if erreurs_exclu:
        print(f"  [ERREUR] {len(erreurs_exclu)} etudiant(s) avec EXCLU mais pas en critique !")
        for p in erreurs_exclu:
            print(f"    {p.prenom} {p.nom} | score={p.score_risque} | {p.niveau_risque}")
    else:
        print(f"  [OK] Tous les etudiants avec module EXCLU sont en 'critique'")

    # ── Vérification AVERTI -> modéré minimum ───────────────────────────
    print("\n=== VERIFICATION AVERTI -> modere minimum ===")
    erreurs_averti = [
        p for p in profils
        if p.nb_modules_averti > 0 and p.nb_modules_exclu == 0 and p.niveau_risque == "faible"
    ]
    if erreurs_averti:
        print(f"  [ERREUR] {len(erreurs_averti)} etudiant(s) avec AVERTI mais en 'faible' !")
        for p in erreurs_averti:
            print(f"    {p.prenom} {p.nom} | score={p.score_risque} | {p.niveau_risque}")
    else:
        print(f"  [OK] Tous les etudiants avec module AVERTI sont en 'modere' minimum")

    # ── Vérification Najlaa Larche ───────────────────────────────────────
    print("\n=== VÉRIFICATION NAJLAA LARCHE ===")
    najlaa = next(
        (p for p in profils if "larche" in p.nom.lower() or "najlaa" in p.prenom.lower()),
        None,
    )
    if najlaa:
        print(f"  Étudiant  : {najlaa.prenom} {najlaa.nom}")
        print(f"  Score     : {najlaa.score_risque}")
        print(f"  Niveau    : {najlaa.niveau_risque}")
        print(f"  Modules EXCLU : {najlaa.nb_modules_exclu}")
        for m in najlaa.modules:
            if m.statut_exam != "AUTORISE":
                print(f"    [{m.statut_exam}] {m.module} — NJ:{m.taux_nj:.1f}% / total:{m.taux_total:.1f}%")
        attendu_ok = najlaa.score_risque >= 70 and najlaa.niveau_risque == "critique"
        print(f"  Attendu score>=70, critique → {'[OK]' if attendu_ok else '[ERREUR]'}")
    else:
        print("  [INFO] Najlaa Larche introuvable dans les données")

    # ── Détail complet ───────────────────────────────────────────────────
    print("\n=== DÉTAIL PAR ÉTUDIANT ===")
    for p in profils:
        print(f"  {p.prenom} {p.nom} | score={p.score_risque} | {p.niveau_risque} | {p.action_recommandee}")
        for m in p.modules:
            if m.statut_exam != "AUTORISE":
                print(f"    [{m.statut_exam}] {m.module} — NJ:{m.nb_abs_nj} ({m.taux_nj:.1f}%) | total:{m.taux_total:.1f}% / {m.total_seances}h")
