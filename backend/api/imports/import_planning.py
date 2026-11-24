"""POST /api/import-planning — planning hebdomadaire Konosys (.xlsx) → planning_seances.
La logique de lecture/insertion reste dans backend/database/import_planning.py (aussi utilisée en CLI)."""
from datetime import datetime

from flask import jsonify, request

from backend.api.auth import require_auth, require_role
from backend.api.imports.common import traiter_fichier_xlsx
from backend.database.import_planning import import_planning


@require_auth
@require_role("admin")
def import_planning_route():
    date_debut = None
    if request.form.get("date_debut"):
        try:
            date_debut = datetime.strptime(request.form["date_debut"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Date de début invalide (format AAAA-MM-JJ)"}), 400
    stats, err = traiter_fichier_xlsx(lambda path, _nom: import_planning(path, date_debut))
    return err or jsonify(stats)
