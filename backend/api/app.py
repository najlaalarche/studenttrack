import dataclasses
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
load_dotenv()

import sys
sys.path.insert(0, str(ROOT))

from backend.ingestion.reader import load_absences_df, detect_delta
from backend.analysis.engine import calculer_profils, filtrer_alertes, upsert_alertes
from backend.agent.ia_agent import traiter_alertes
from backend.agent.email_agent import init_alerts_db, process_student_alerts, get_alert_history

app = Flask(__name__)
CORS(app)
init_alerts_db()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _to_python(obj):
    if isinstance(obj, np.integer):  return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.bool_):    return bool(obj)
    if isinstance(obj, np.ndarray):  return obj.tolist()
    if isinstance(obj, float) and obj != obj: return None  # NaN
    return obj


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list): return [_serialize(i) for i in obj]
    if isinstance(obj, dict): return {k: _serialize(v) for k, v in obj.items()}
    return _to_python(obj)


# ── Cache mémoire ─────────────────────────────────────────────────────────────

_cache: dict = {"data": None}


def _charger_tout():
    if not DB_PATH.exists():
        return None, []
    df_abs = load_absences_df()
    profils = calculer_profils(df_abs)
    upsert_alertes(profils)
    return df_abs, profils


def _get_data():
    if _cache["data"] is None:
        _cache["data"] = _charger_tout()
    return _cache["data"]


def _envoyer_alertes_etudiants_apres_sync(profils: list, nouvelles_absences: pd.DataFrame) -> dict:
    if nouvelles_absences is None or nouvelles_absences.empty:
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0, "results": []}

    ids_touches = set(nouvelles_absences["id_etudiant"].astype(str).tolist())
    modules_touches = (
        nouvelles_absences.assign(id_etudiant=nouvelles_absences["id_etudiant"].astype(str))
        .groupby("id_etudiant")["module"]
        .apply(lambda values: set(values.astype(str)))
        .to_dict()
    )
    profils_touches = [p for p in filtrer_alertes(profils) if p.id_etudiant in ids_touches]
    results = []

    for profil in profils_touches:
        profil_data = _serialize(profil)
        modules_du_delta = modules_touches.get(profil.id_etudiant, set())
        profil_data["modules"] = [
            module
            for module in profil_data.get("modules", [])
            if str(module.get("module", "")) in modules_du_delta
        ]
        if profil_data["modules"]:
            results.extend(process_student_alerts(profil_data, notify_staff=False))

    return {
        "processed": len(profils_touches),
        "sent": sum(1 for r in results if r.get("sent")),
        "failed": sum(1 for r in results if not r.get("sent") and r.get("reason") != "doublon"),
        "skipped": sum(1 for r in results if r.get("reason") == "doublon"),
        "results": results,
    }


# ── Auth (SQLite users) ───────────────────────────────────────────────────────

def _check_email_db(email: str) -> dict:
    conn = _db()
    et_row = conn.execute(
        "SELECT id, nom, prenom FROM etudiants WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    if not et_row:
        conn.close()
        return {"exists": False, "has_password": False, "prenom": ""}
    u_row = conn.execute(
        "SELECT password_hash FROM users WHERE id_etudiant = ?", (et_row["id"],)
    ).fetchone()
    conn.close()
    return {
        "exists": True,
        "has_password": u_row is not None and bool(u_row["password_hash"]),
        "prenom": et_row["prenom"],
    }


def _register_db(email: str, password: str) -> dict:
    conn = _db()
    et_row = conn.execute(
        "SELECT id FROM etudiants WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    if not et_row:
        conn.close()
        return {"success": False, "error": "Email non reconnu"}
    existing = conn.execute(
        "SELECT id FROM users WHERE id_etudiant = ?", (et_row["id"],)
    ).fetchone()
    if existing:
        conn.close()
        return {"success": False, "error": "Un mot de passe existe déjà"}
    pw_hash = _hash_password(password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO users (id_etudiant, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (et_row["id"], email.lower(), pw_hash, now),
    )
    conn.commit()
    conn.close()
    return {"success": True}


def _login_db(email: str, password: str) -> dict:
    conn = _db()
    et_row = conn.execute(
        "SELECT e.id, e.nom, e.prenom, e.email, e.cursus, e.session_programme,"
        " f.code AS code_filiere, f.niveau AS annee"
        " FROM etudiants e"
        " LEFT JOIN filieres f ON e.id_filiere = f.id"
        " WHERE LOWER(e.email) = LOWER(?)",
        (email,),
    ).fetchone()
    if not et_row:
        conn.close()
        return {"success": False, "error": "Email non reconnu"}
    u_row = conn.execute(
        "SELECT id, password_hash FROM users WHERE id_etudiant = ?", (et_row["id"],)
    ).fetchone()
    if not u_row:
        conn.close()
        return {"success": False, "error": "Aucun compte trouvé pour cet email"}
    if u_row["password_hash"] != _hash_password(password):
        conn.close()
        return {"success": False, "error": "Mot de passe incorrect"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, u_row["id"]))
    conn.commit()
    conn.close()
    etudiant_info = {
        "id_etudiant": str(et_row["id"]),
        "nom":    et_row["nom"],
        "prenom": et_row["prenom"],
        "email":  et_row["email"],
        "filiere": et_row["code_filiere"] or "",
        "annee":   et_row["annee"] or "",
    }
    return {"success": True, "etudiant": etudiant_info}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def stats():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    alertes = filtrer_alertes(profils)
    return jsonify({
        "total_etudiants": len(profils),
        "total_alertes":   len(alertes),
        "critique": sum(1 for p in profils if p.niveau_risque == "critique"),
        "modere":   sum(1 for p in profils if p.niveau_risque == "modéré"),
        "faible":   sum(1 for p in profils if p.niveau_risque == "faible"),
        "total_abs_nj": sum(p.total_abs_nj for p in profils),
    })


@app.route("/api/etudiants")
def etudiants():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    return jsonify(_serialize(profils))


@app.route("/api/etudiant/<id_etudiant>")
def etudiant(id_etudiant: str):
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404

    profil = next((p for p in profils if p.id_etudiant == id_etudiant), None)
    if not profil:
        return jsonify({"erreur": "Étudiant non trouvé"}), 404

    absences = []
    if df_abs is not None:
        mask = df_abs["id_etudiant"] == id_etudiant
        abs_df = df_abs[mask].copy()
        abs_df["date_str"] = abs_df["date_absence"].dt.strftime("%Y-%m-%d")
        cols = ["date_str", "module", "duree_heures", "justifiee", "motif", "seance"]
        absences = _serialize(
            abs_df[cols].rename(columns={"date_str": "date_absence"}).to_dict(orient="records")
        )

    return jsonify({
        "profil":   _serialize(profil),
        "absences": absences,
        "notes":    [],
        "scoring":  {},
    })


@app.route("/api/alertes")
def alertes():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    en_alerte = filtrer_alertes(profils)
    resultats = traiter_alertes(en_alerte)
    return jsonify([
        {"profil": _serialize(r["profil"]), "decision": _serialize(r["decision"])}
        for r in resultats
    ])


@app.route("/api/alerts/send", methods=["POST"])
def send_alert():
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    if not student_id:
        return jsonify({"erreur": "student_id requis"}), 400
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    profil = next((p for p in profils if p.id_etudiant == str(student_id)), None)
    if not profil:
        return jsonify({"erreur": "Étudiant non trouvé"}), 404
    contacts = {
        "chef_email":      payload.get("chef_email"),
        "direction_email": payload.get("direction_email"),
    }
    results = process_student_alerts(_serialize(profil), contacts)
    return jsonify({"results": results, "total_sent": sum(1 for r in results if r.get("sent"))})


@app.route("/api/alerts/send-all", methods=["POST"])
def send_all_alerts():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    en_alerte = filtrer_alertes(profils)
    all_results = []
    for profil in en_alerte:
        results = process_student_alerts(_serialize(profil), {
            "chef_email":      os.environ.get("CHEF_EMAIL"),
            "direction_email": os.environ.get("DIRECTION_EMAIL"),
        })
        all_results.extend(results)
    total_sent = sum(1 for r in all_results if r.get("sent"))
    failed = sum(1 for r in all_results if not r.get("sent"))
    return jsonify({"processed": len(en_alerte), "sent": total_sent, "failed": failed, "results": all_results})


@app.route("/api/alerts/history")
def alerts_history():
    student_id = request.args.get("student_id")
    return jsonify({"alerts": get_alert_history(student_id)})


@app.route("/api/modules")
def modules():
    """Retourne [{nom, filieres, semestres}] depuis la table modules (705 entrées dédupliquées par nom)."""
    if not DB_PATH.exists():
        return jsonify({"erreur": "Base SQLite introuvable"}), 404
    conn = _db()
    rows = conn.execute(
        "SELECT m.nom, f.code AS filiere, m.semestre"
        " FROM modules m LEFT JOIN filieres f ON m.id_filiere = f.id"
        " ORDER BY m.nom"
    ).fetchall()
    conn.close()
    by_nom: dict = defaultdict(lambda: {"filieres": set(), "semestres": set()})
    for r in rows:
        nom = r["nom"]
        if r["filiere"]:
            by_nom[nom]["filieres"].add(r["filiere"])
        if r["semestre"] and r["semestre"] not in ("S0", ""):
            by_nom[nom]["semestres"].add(r["semestre"])
    result = [
        {"nom": nom, "filieres": sorted(data["filieres"]), "semestres": sorted(data["semestres"])}
        for nom, data in sorted(by_nom.items())
    ]
    return jsonify(result)


@app.route("/api/filieres")
def filieres():
    df_abs, profils = _get_data()
    if df_abs is None:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    fils = sorted(df_abs["filiere"].dropna().unique().tolist())
    return jsonify(fils)


@app.route("/api/filieres-par-module/<nom_module>")
def filieres_par_module(nom_module: str):
    """Retourne les filières qui ont ce module dans leur programme."""
    if not DB_PATH.exists():
        return jsonify([]), 404
    conn = _db()
    rows = conn.execute(
        "SELECT DISTINCT f.code FROM modules m"
        " LEFT JOIN filieres f ON m.id_filiere = f.id"
        " WHERE m.nom = ? AND f.code IS NOT NULL ORDER BY f.code",
        (nom_module,),
    ).fetchall()
    conn.close()
    return jsonify([r["code"] for r in rows])


@app.route("/api/modules/all")
def modules_all():
    conn = _db()
    rows = conn.execute(
        "SELECT m.id, m.nom, m.semestre, m.volume_heures, f.code AS filiere"
        " FROM modules m LEFT JOIN filieres f ON m.id_filiere = f.id ORDER BY m.nom"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/filieres/all")
def filieres_all():
    conn = _db()
    rows = conn.execute("SELECT id, nom, code, niveau FROM filieres ORDER BY code, niveau").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/module-classes")
def module_classes():
    module_name = request.args.get("module", "")
    if not DB_PATH.exists():
        return jsonify({"filieres": [], "promotions": []}), 404
    conn = _db()
    rows = conn.execute(
        "SELECT DISTINCT f.code, f.niveau FROM modules m"
        " LEFT JOIN filieres f ON m.id_filiere = f.id"
        " WHERE m.nom = ? AND f.code IS NOT NULL",
        (module_name,),
    ).fetchall()
    conn.close()
    return jsonify({
        "filieres":   sorted(set(r["code"]  for r in rows if r["code"])),
        "promotions": sorted(set(r["niveau"] for r in rows if r["niveau"])),
    })


@app.route("/api/auth/check-email", methods=["POST"])
def auth_check_email():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email requis"}), 400
    return jsonify(_check_email_db(email))


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    payload = request.get_json(silent=True) or {}
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Le mot de passe doit contenir au moins 8 caractères"}), 400
    result = _register_db(email, password)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400
    result = _login_db(email, password)
    if not result["success"]:
        return jsonify(result), 401
    return jsonify(result)


@app.route("/api/import-csv", methods=["POST"])
def import_csv():
    """Stub — pour futurs imports d'absences Konosys."""
    return jsonify({"message": "Import CSV non encore implémenté", "todo": True}), 200


@app.route("/api/sync", methods=["POST"])
def sync():
    if not DB_PATH.exists():
        return jsonify({"erreur": "Base SQLite introuvable"}), 404
    _cache["data"] = None
    nouvelles, changed = detect_delta()
    _cache["data"] = _charger_tout()
    df_abs, profils = _cache["data"]
    if changed:
        email_alerts = _envoyer_alertes_etudiants_apres_sync(profils, nouvelles)
    else:
        email_alerts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0, "results": []}
    return jsonify({
        "nouvelles_lignes": len(nouvelles),
        "changed": bool(changed),
        "email_alerts": email_alerts,
    })


if __name__ == "__main__":
    print(f"[api] Base SQLite : {DB_PATH}")
    print(f"[api] Base présente : {DB_PATH.exists()}")
    print("[api] Démarrage sur http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
