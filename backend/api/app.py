import dataclasses
import hashlib
import json
from pathlib import Path
import os

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv()

PASSWORDS_FILE = ROOT / "backend" / "data" / "passwords.json"


def _load_passwords() -> dict:
    if not PASSWORDS_FILE.exists():
        return {}
    return json.loads(PASSWORDS_FILE.read_text(encoding="utf-8"))


def _save_passwords(data: dict):
    PASSWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSWORDS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

import sys
sys.path.insert(0, str(ROOT))

from backend.ingestion.reader import load_dataset, detect_delta
from backend.analysis.engine import calculer_profils, filtrer_alertes
from backend.agent.ia_agent import traiter_alertes
from backend.agent.email_agent import init_alerts_db, process_student_alerts, get_alert_history

app = Flask(__name__)
CORS(app)
init_alerts_db()

DATASET_PATH = ROOT / "data" / "dataset.xlsx"


def _to_python(obj):
    if isinstance(obj, (np.integer,)):      return int(obj)
    if isinstance(obj, (np.floating,)):     return float(obj)
    if isinstance(obj, (np.bool_,)):        return bool(obj)
    if isinstance(obj, np.ndarray):         return obj.tolist()
    if isinstance(obj, float) and (obj != obj): return None  # NaN
    return obj


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):  return [_serialize(i) for i in obj]
    if isinstance(obj, dict):  return {k: _serialize(v) for k, v in obj.items()}
    return _to_python(obj)


# Cache en mémoire — rechargé à chaque /api/sync
_cache = {"data": None}


def _charger_tout():
    if not DATASET_PATH.exists():
        return None, None, None, None, []
    df_abs, df_notes, df_etudiants, df_scoring = load_dataset(DATASET_PATH)
    profils = calculer_profils(df_abs, df_notes, df_etudiants, df_scoring)
    return df_abs, df_notes, df_etudiants, df_scoring, profils


def _get_data():
    if _cache["data"] is None:
        _cache["data"] = _charger_tout()
    return _cache["data"]


@app.route("/api/stats")
def stats():
    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable ou vide"}), 404

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
    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404
    return jsonify(_serialize(profils))


@app.route("/api/etudiant/<id_etudiant>")
def etudiant(id_etudiant: str):
    df_abs, df_notes, df_etudiants, df_scoring, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404

    profil = next((p for p in profils if p.id_etudiant == id_etudiant), None)
    if not profil:
        return jsonify({"erreur": "Étudiant non trouvé"}), 404

    # Absences
    absences = []
    if df_abs is not None:
        mask = df_abs["id_etudiant"] == id_etudiant
        abs_df = df_abs[mask].copy()
        abs_df["date_str"] = abs_df["date_absence"].dt.strftime("%Y-%m-%d")
        cols = ["date_str", "module", "duree_heures", "justifiee", "motif", "seance"]
        absences = abs_df[cols].rename(columns={"date_str": "date_absence"}).to_dict(orient="records")
        absences = _serialize(absences)

    # Notes
    notes = []
    if df_notes is not None:
        notes_df = df_notes[df_notes["id_etudiant"] == id_etudiant]
        notes = _serialize(notes_df.to_dict(orient="records"))

    # Scoring
    scoring = {}
    if df_scoring is not None:
        sc_df = df_scoring[df_scoring["id_etudiant"] == id_etudiant]
        if not sc_df.empty:
            scoring = _serialize(sc_df.iloc[0].to_dict())

    return jsonify({
        "profil":   _serialize(profil),
        "absences": absences,
        "notes":    notes,
        "scoring":  scoring,
    })


@app.route("/api/alertes")
def alertes():
    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404

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

    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404

    profil = next((p for p in profils if p.id_etudiant == str(student_id)), None)
    if not profil:
        return jsonify({"erreur": "Étudiant non trouvé"}), 404

    contacts = {
        "chef_email": payload.get("chef_email"),
        "direction_email": payload.get("direction_email"),
    }
    results = process_student_alerts(_serialize(profil), contacts)
    total_sent = sum(1 for r in results if r.get("sent"))
    return jsonify({"results": results, "total_sent": total_sent})


@app.route("/api/alerts/send-all", methods=["POST"])
def send_all_alerts():
    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404

    en_alerte = filtrer_alertes(profils)
    all_results = []
    for profil in en_alerte:
        results = process_student_alerts(_serialize(profil), {
            "chef_email": os.environ.get("CHEF_EMAIL"),
            "direction_email": os.environ.get("DIRECTION_EMAIL"),
        })
        all_results.extend(results)

    total_sent = sum(1 for r in all_results if r.get("sent"))
    failed = sum(1 for r in all_results if not r.get("sent"))
    return jsonify({"processed": len(en_alerte), "sent": total_sent, "failed": failed, "results": all_results})


@app.route("/api/alerts/history")
def alerts_history():
    student_id = request.args.get("student_id")
    alerts = get_alert_history(student_id)
    return jsonify({"alerts": alerts})


@app.route("/api/modules")
def modules():
    df_abs, _, _, _, _ = _get_data()
    if df_abs is None:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404
    mods = sorted(df_abs["module"].dropna().unique().tolist())
    return jsonify(mods)


@app.route("/api/filieres")
def filieres():
    df_abs, _, _, _, _ = _get_data()
    if df_abs is None:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404
    fils = sorted(df_abs["filiere"].dropna().unique().tolist())
    return jsonify(fils)


@app.route("/api/module-classes")
def module_classes():
    module_name = request.args.get("module", "")
    _, _, _, _, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404
    matching = [p for p in profils if any(m.module == module_name for m in p.modules)]
    return jsonify({
        "filieres":   sorted(set(p.filiere for p in matching if p.filiere)),
        "promotions": sorted(set(p.annee   for p in matching if p.annee)),
    })


@app.route("/api/auth/check-email", methods=["POST"])
def auth_check_email():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower().replace("@esith.ma", "@esith.net")
    if not email:
        return jsonify({"error": "email requis"}), 400

    _, _, df_etudiants, _, _ = _get_data()
    if df_etudiants is None:
        return jsonify({"error": "dataset introuvable"}), 404

    emails_dataset = (
        df_etudiants["Email_Etudiant"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.replace("@esith.ma", "@esith.net", regex=False)
        .tolist()
    )
    exists = email in emails_dataset

    passwords = _load_passwords()
    has_password = email in passwords

    prenom = ""
    if exists:
        mask = (
            df_etudiants["Email_Etudiant"]
            .fillna("")
            .str.strip()
            .str.lower()
            .str.replace("@esith.ma", "@esith.net", regex=False)
        ) == email
        row = df_etudiants[mask]
        if not row.empty:
            prenom = str(row.iloc[0].get("Prenom", ""))

    return jsonify({"exists": exists, "has_password": has_password, "prenom": prenom})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower().replace("@esith.ma", "@esith.net")
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Le mot de passe doit contenir au moins 8 caractères"}), 400

    _, _, df_etudiants, _, _ = _get_data()
    if df_etudiants is None:
        return jsonify({"success": False, "error": "dataset introuvable"}), 404

    emails_dataset = (
        df_etudiants["Email_Etudiant"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.replace("@esith.ma", "@esith.net", regex=False)
        .tolist()
    )
    if email not in emails_dataset:
        return jsonify({"success": False, "error": "Email non reconnu"}), 400

    passwords = _load_passwords()
    if email in passwords:
        return jsonify({"success": False, "error": "Un mot de passe existe déjà"}), 400

    passwords[email] = _hash_password(password)
    _save_passwords(passwords)
    return jsonify({"success": True})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower().replace("@esith.ma", "@esith.net")
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400

    passwords = _load_passwords()
    if email not in passwords:
        return jsonify({"success": False, "error": "Aucun compte trouvé pour cet email"}), 401
    if passwords[email] != _hash_password(password):
        return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401

    _, _, df_etudiants, _, profils = _get_data()
    etudiant_info = {}
    if df_etudiants is not None:
        mask = (
            df_etudiants["Email_Etudiant"]
            .fillna("")
            .str.strip()
            .str.lower()
            .str.replace("@esith.ma", "@esith.net", regex=False)
        ) == email
        row = df_etudiants[mask]
        if not row.empty:
            r = row.iloc[0]
            id_etudiant = str(r.get("id_etudiant", ""))
            etudiant_info = {
                "id_etudiant": id_etudiant,
                "nom":    str(r.get("Nom", "")),
                "prenom": str(r.get("Prenom", "")),
                "email":  email,
                "filiere": str(r.get("Filiere", "")),
                "annee":   str(r.get("Annee", "")),
            }

    return jsonify({"success": True, "etudiant": etudiant_info})


@app.route("/api/sync", methods=["POST"])
def sync():
    if not DATASET_PATH.exists():
        return jsonify({"erreur": "dataset.xlsx introuvable"}), 404
    _cache["data"] = None  # invalider le cache
    df_abs, _, _, _, _ = _charger_tout()
    nouvelles, changed = detect_delta(df_abs)
    _cache["data"] = _charger_tout()  # recharger avec le nouvel état
    return jsonify({
        "nouvelles_lignes": len(nouvelles),
        "changed": bool(changed),
    })


if __name__ == "__main__":
    print(f"[api] Dataset : {DATASET_PATH}")
    print(f"[api] Dataset présent : {DATASET_PATH.exists()}")
    print("[api] Démarrage sur http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
