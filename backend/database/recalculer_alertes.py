"""
Recalcule les alertes en repartant des données actuelles via la même logique que l'API
(load_absences_df → calculer_profils → upsert_alertes).

Note : le calcul groupe les absences par NOM de module (pas par id), ce qui signifie que
si un étudiant a des absences dans deux modules portant le même nom (ex. "Espagnol" S1+S2),
elles sont cumulées. Ce comportement est intentionnel et cohérent avec le reste du système.

Usage :
    python backend/database/recalculer_alertes.py
    # ou, depuis app.py, appeler recalculer_alertes(id_module=X) après un PUT volume_heures
"""
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"


def recalculer_alertes(id_module: int | None = None) -> tuple[int, int]:
    """
    Recalcule toutes les alertes (ou celles liées à id_module) et met à jour la table.
    Retourne (nb_corrigées, nb_traitées).
    Utilise la même logique que l'API : DataFrame → calculer_profils → upsert.
    """
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.ingestion.reader import load_absences_df
    from backend.analysis.engine import calculer_profils, upsert_alertes

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Snapshot avant
    before = {
        r["id"]: (r["taux_nj"], r["taux_total"], r["statut"])
        for r in conn.execute("SELECT id, taux_nj, taux_total, statut FROM alertes").fetchall()
    }
    conn.close()

    df_abs = load_absences_df()
    profils = calculer_profils(df_abs)
    upsert_alertes(profils)

    # Snapshot après
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    after = {
        r["id"]: (r["taux_nj"], r["taux_total"], r["statut"])
        for r in conn.execute("SELECT id, taux_nj, taux_total, statut FROM alertes").fetchall()
    }
    conn.close()

    corrected = 0
    for aid, (tnj_b, ttot_b, stat_b) in before.items():
        if aid not in after:
            continue
        tnj_a, ttot_a, stat_a = after[aid]
        if (abs((tnj_a or 0) - (tnj_b or 0)) > 0.05
                or abs((ttot_a or 0) - (ttot_b or 0)) > 0.05
                or stat_a != stat_b):
            corrected += 1
            print(
                f"  Corrigé alerte id={aid}"
                f"  |  taux_nj {tnj_b}→{tnj_a}"
                f"  |  taux_total {ttot_b}→{ttot_a}"
                f"  |  statut {stat_b}→{stat_a}"
            )

    return corrected, len(before)


if __name__ == "__main__":
    print(f"[recalculer_alertes] Base : {DB_PATH}")
    nb_corr, nb_tot = recalculer_alertes()
    print(f"[recalculer_alertes] {nb_corr}/{nb_tot} alertes recalculées.")
    if nb_corr == 0:
        print("[recalculer_alertes] Aucune incohérence — tout est à jour.")
