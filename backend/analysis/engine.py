from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

SEUIL_ALERTE    = 20.0
SEUIL_EXCLUSION = 50.0


@dataclass
class StatutModule:
    module:              str
    total_seances:       int
    nb_abs_nj:           int
    nb_abs_just:         int
    nb_abs_total:        int
    taux_nj:             float
    taux_total:          float
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
    # Scores depuis Scoring_Risque
    moyenne_generale:     float = 0.0
    score_notes:          float = 0.0
    score_absences:       float = 0.0
    score_global:         float = 0.0
    niveau_risque_scoring: str  = "VERT"
    # Scores calculés localement (compatibilité dashboard)
    score_risque:         float = 0.0
    niveau_risque:        str   = "faible"
    niveau_alerte:        int   = 0
    action_recommandee:   str   = "AUCUNE"
    # Notes par module
    notes_modules:        list  = field(default_factory=list)


def _calculer_statut_module(module_nom: str, grp_mod: pd.DataFrame) -> StatutModule:
    nb_nj   = int((~grp_mod["justifiee"]).sum())
    nb_just = int(grp_mod["justifiee"].sum())
    nb_tot  = nb_nj + nb_just

    total_seances = int(grp_mod["total_seances_module"].iloc[0]) if len(grp_mod) > 0 else 1
    if total_seances <= 0:
        total_seances = 1

    taux_nj    = round(nb_nj    / total_seances * 100, 2)
    taux_total = round(nb_tot   / total_seances * 100, 2)

    if taux_total >= SEUIL_EXCLUSION:
        statut = "EXCLU"
        alerte = f"Exclu : {taux_total:.1f}% des séances manquées"
    elif taux_nj >= SEUIL_ALERTE:
        statut = "AVERTI"
        alerte = f"Averti : {taux_nj:.1f}% NJ (seuil {SEUIL_ALERTE:.0f}%)"
    else:
        statut = "AUTORISE"
        alerte = ""

    return StatutModule(
        module=module_nom,
        total_seances=total_seances,
        nb_abs_nj=nb_nj,
        nb_abs_just=nb_just,
        nb_abs_total=nb_tot,
        taux_nj=taux_nj,
        taux_total=taux_total,
        seuil_alerte=SEUIL_ALERTE,
        seuil_exclusion=SEUIL_EXCLUSION,
        statut_exam=statut,
        avert_email_envoye=False,
        exclu_email_envoye=False,
        alerte_module=alerte,
    )


def calculer_profils(
    df_abs: pd.DataFrame,
    df_notes: pd.DataFrame,
    df_etudiants: pd.DataFrame,
    df_scoring: pd.DataFrame,
) -> list[ProfilEtudiant]:
    profils = []

    # Index scoring par id_etudiant pour lookup rapide
    scoring_idx = df_scoring.set_index("id_etudiant") if not df_scoring.empty else pd.DataFrame()
    notes_idx   = df_notes.groupby("id_etudiant")

    for id_etudiant, groupe in df_abs.groupby("id_etudiant"):
        row0 = groupe.iloc[0]
        nom         = str(row0.get("nom", ""))
        prenom      = str(row0.get("prenom", ""))
        email       = str(row0.get("email", "inconnu@esith.net"))
        filiere     = str(row0.get("filiere", ""))
        code_filiere= str(row0.get("code_filiere", ""))
        annee       = str(row0.get("annee", ""))
        cursus      = str(row0.get("cursus", ""))

        total_nj   = int((~groupe["justifiee"]).sum())
        total_just = int(groupe["justifiee"].sum())
        total_abs  = len(groupe)

        dates_valides = groupe["date_absence"].dropna()
        derniere = str(dates_valides.max().date()) if not dates_valides.empty else ""

        # Statut par module
        statuts_modules = []
        for module_nom, grp_mod in groupe.groupby("module"):
            sm = _calculer_statut_module(module_nom, grp_mod)
            statuts_modules.append(sm)

        nb_exclu  = sum(1 for s in statuts_modules if s.statut_exam == "EXCLU")
        nb_averti = sum(1 for s in statuts_modules if s.statut_exam == "AVERTI")

        ordre = {"EXCLU": 2, "AVERTI": 1, "AUTORISE": 0}
        plus_grave = max(statuts_modules, key=lambda s: ordre[s.statut_exam], default=None)
        module_grave_nom = plus_grave.module if plus_grave else ""

        # Scoring depuis la feuille Scoring_Risque
        sid = str(id_etudiant)
        if not scoring_idx.empty and sid in scoring_idx.index:
            sr = scoring_idx.loc[sid]
            score_global   = float(sr.get("Score_Global_Risque", 0))
            score_abs      = float(sr.get("Score_Absences", 0))
            score_notes_v  = float(sr.get("Score_Notes", 0))
            moyenne_gen    = float(sr.get("Moyenne_Generale", 0))
            niveau_scoring = str(sr.get("Niveau_Risque", "VERT"))
        else:
            score_global   = 0.0
            score_abs      = 0.0
            score_notes_v  = 0.0
            moyenne_gen    = 0.0
            niveau_scoring = "VERT"

        # Niveau risque unifié pour le dashboard
        if score_global >= 70:
            niveau_risque = "critique"
            niveau_alerte = 3
        elif score_global >= 40:
            niveau_risque = "modéré"
            niveau_alerte = 2
        elif score_global > 0:
            niveau_risque = "faible"
            niveau_alerte = 1
        else:
            niveau_risque = "faible"
            niveau_alerte = 0

        if nb_exclu > 0:
            action = "NOTIFY_EXCLUSION"
        elif nb_averti > 0:
            action = "WARN_STUDENT"
        else:
            action = "AUCUNE"

        # Notes par module
        notes_modules = []
        try:
            grp_notes = notes_idx.get_group(sid)
            for _, nr in grp_notes.iterrows():
                notes_modules.append({
                    "module":      str(nr.get("Module", "")),
                    "note_cc":     float(nr["Note_CC"])     if pd.notna(nr.get("Note_CC"))     else None,
                    "note_examen": float(nr["Note_Examen"]) if pd.notna(nr.get("Note_Examen")) else None,
                    "note_finale": float(nr["Note_Finale"]) if pd.notna(nr.get("Note_Finale")) else None,
                    "mention":     str(nr.get("Mention", "")),
                    "statut":      str(nr.get("Statut", "")),
                })
        except KeyError:
            pass

        profils.append(ProfilEtudiant(
            id_etudiant=sid,
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
            moyenne_generale=round(moyenne_gen, 2),
            score_notes=round(score_notes_v, 2),
            score_absences=round(score_abs, 2),
            score_global=round(score_global, 2),
            niveau_risque_scoring=niveau_scoring,
            score_risque=round(score_global, 2),
            niveau_risque=niveau_risque,
            niveau_alerte=niveau_alerte,
            action_recommandee=action,
            notes_modules=notes_modules,
        ))

    return profils


def filtrer_alertes(profils: list) -> list:
    return [p for p in profils if p.niveau_alerte > 0]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.ingestion.reader import load_dataset

    dataset_path = ROOT / "data" / "dataset.xlsx"
    if not dataset_path.exists():
        print("[engine] dataset.xlsx introuvable")
    else:
        df_abs, df_notes, df_etudiants, df_scoring = load_dataset(dataset_path)
        profils = calculer_profils(df_abs, df_notes, df_etudiants, df_scoring)
        alertes = filtrer_alertes(profils)

        print(f"[engine] {len(profils)} profils | {len(alertes)} alertes")
        for p in profils[:5]:
            print(f"  {p.prenom} {p.nom} | score={p.score_global} | {p.niveau_risque} | {p.action_recommandee}")
            for m in p.modules:
                print(f"    [{m.statut_exam}] {m.module} — NJ:{m.nb_abs_nj}/{m.total_seances} ({m.taux_nj:.1f}%)")

        # Vérification étudiant 20001
        nadia = next((p for p in profils if p.id_etudiant == "20001"), None)
        if nadia:
            print(f"\n[engine] Nadia Zouiten : {nadia.prenom} {nadia.nom} | email={nadia.email}")
        else:
            print("\n[engine] Étudiant 20001 non trouvé dans les absences")
