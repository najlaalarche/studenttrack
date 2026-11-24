"""POST /api/import-notes et /api/import-notes/preview — moyennes Konosys (.xlsx / .xlsb).
La logique de lecture/insertion reste dans backend/database/import_notes.py (aussi utilisée en CLI)."""
from flask import jsonify

from backend.api.auth import require_auth, require_role
from backend.api.imports.common import CACHE, traiter_fichier_excel
from backend.database.import_notes import import_notes, preview_notes


@require_auth
@require_role("admin")
def import_notes_preview():
    apercu, err = traiter_fichier_excel(lambda path, _nom: preview_notes(path))
    return err or jsonify(apercu)


@require_auth
@require_role("admin")
def import_notes_route():
    stats, err = traiter_fichier_excel(lambda path, nom: import_notes(path, source_name=nom))
    if err:
        return err
    CACHE["data"] = None  # la moyenne affichée dans les profils vient des notes
    return jsonify(stats)
