"""
Taux d'absence cumulatif semaine par semaine (portail étudiant).

Taux semaine N = Σ heures d'absence S1→N / Σ heures planifiées du groupe S1→N × 100
  - heures planifiées : planning_seances (import hebdomadaire) pour le groupe de l'étudiant
  - absences : justifiées + non justifiées, numérotées avec la même date de début d'année
  - seules les semaines présentes dans le planning du groupe sont comptées
Taux de présence = 100 - taux d'absence.
"""
import re
import sqlite3
from collections import defaultdict
from datetime import date

from backend.database.import_planning import ensure_planning_schema, get_date_debut, numero_semaine

_SEPARATEURS_GROUPES = re.compile(r"[,;/+]")


def groupe_etudiant(cursus: str | None, session_programme: str | None) -> str | None:
    """'S3-IMS2G1' -> 'IMS2G1' ; à défaut 1er mot de SessionProgramme ('IMS2G1 2ème année 2025-2026')."""
    m = re.match(r"^S\d+-(.+)$", (cursus or "").strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip().upper()
    if session_programme and session_programme.strip():
        return session_programme.split()[0].strip().upper()
    return None


def _groupes_seance(groupe: str) -> set[str]:
    """Une séance commune peut lister plusieurs groupes ('IMS2G1, IMS2G2')."""
    return {g.strip().upper() for g in _SEPARATEURS_GROUPES.split(groupe or "") if g.strip()}


def taux_absence_cumulatif(conn: sqlite3.Connection, id_etudiant: int) -> dict | None:
    """None si l'étudiant n'existe pas ; sinon {"groupe", "date_debut", "semaines": [...]}."""
    ensure_planning_schema(conn)
    et = conn.execute(
        "SELECT cursus, session_programme FROM etudiants WHERE id=?", (id_etudiant,)
    ).fetchone()
    if not et:
        return None
    groupe = groupe_etudiant(et[0], et[1])
    debut = get_date_debut(conn)

    planifie = defaultdict(float)  # semaine -> heures planifiées
    if groupe:
        for semaine, duree, groupes in conn.execute(
            "SELECT numero_semaine, duree_heures, groupe FROM planning_seances WHERE groupe LIKE ?",
            (f"%{groupe}%",),
        ).fetchall():
            if groupe in _groupes_seance(groupes):
                planifie[semaine] += duree or 0

    absent = defaultdict(lambda: defaultdict(float))  # semaine -> module -> heures
    for d, module, duree in conn.execute(
        "SELECT date_absence, module_nom, duree_heures FROM absences WHERE id_etudiant=?", (id_etudiant,)
    ).fetchall():
        try:
            semaine = numero_semaine(date.fromisoformat(str(d)[:10]), debut)
        except ValueError:
            continue
        if semaine in planifie:
            absent[semaine][module] += duree or 0

    semaines, cumul_abs, cumul_plan = [], 0.0, 0.0
    for semaine in sorted(planifie):
        par_module = absent.get(semaine, {})
        cumul_abs  += sum(par_module.values())
        cumul_plan += planifie[semaine]
        taux = round(cumul_abs / cumul_plan * 100, 1) if cumul_plan else 0.0
        top = max(par_module.items(), key=lambda kv: kv[1], default=(None, 0.0))
        # classement de la semaine (non cumulatif) : plus d'heures d'abord, puis ordre alphabétique
        classement = sorted(par_module.items(), key=lambda kv: (-kv[1], kv[0]))
        semaines.append({
            "semaine":              semaine,
            "taux_absence":         taux,
            "taux_presence":        round(100 - taux, 1),
            "heures_absent":        round(cumul_abs, 2),
            "heures_planifiees":    round(cumul_plan, 2),
            "module_plus_absent":   top[0],
            "heures_absent_module": round(top[1], 2),
            "absences_par_module":  [{"module": m, "heures": round(h, 2)} for m, h in classement if h > 0],
        })
    return {"groupe": groupe, "date_debut": debut.isoformat(), "semaines": semaines}


def taux_absence_global(conn: sqlite3.Connection) -> dict:
    """Vue d'ensemble admin.

    top10       : 10 taux cumulés les plus élevés (dernière semaine disponible de chaque étudiant)
    par_filiere : par code filière, moyenne des taux cumulés des étudiants ayant un planning cette semaine
    """
    ensure_planning_schema(conn)
    if not conn.execute("SELECT 1 FROM planning_seances LIMIT 1").fetchone():
        return {"top10": [], "semaines": [], "filieres": [], "par_filiere": []}

    etudiants = conn.execute(
        """SELECT e.id, e.prenom, e.nom, COALESCE(f.code, '') AS code
           FROM etudiants e LEFT JOIN filieres f ON e.id_filiere = f.id"""
    ).fetchall()

    derniers = []
    taux_semaine = defaultdict(lambda: defaultdict(list))  # filière -> semaine -> [taux étudiants]
    for id_et, prenom, nom, code in etudiants:
        semaines = taux_absence_cumulatif(conn, id_et)["semaines"]
        if not semaines:
            continue
        derniere = semaines[-1]
        derniers.append({
            "id_etudiant": str(id_et), "prenom": prenom, "nom": nom, "filiere": code,
            "semaine": derniere["semaine"], "taux_absence": derniere["taux_absence"],
        })
        if code:
            for s in semaines:
                taux_semaine[code][s["semaine"]].append(s["taux_absence"])

    toutes_semaines = sorted({s for par_sem in taux_semaine.values() for s in par_sem})
    filieres = sorted(taux_semaine)
    par_filiere = [
        {"semaine": s, **{
            code: round(sum(v) / len(v), 1)
            for code in filieres if (v := taux_semaine[code].get(s))
        }}
        for s in toutes_semaines
    ]
    top10 = sorted(derniers, key=lambda d: d["taux_absence"], reverse=True)[:10]
    return {"top10": top10, "semaines": toutes_semaines, "filieres": filieres, "par_filiere": par_filiere}
