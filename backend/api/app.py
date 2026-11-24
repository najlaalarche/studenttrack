import dataclasses
import hashlib
import io
import json
import os
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import numpy as np
import pandas as pd
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
load_dotenv(ROOT / ".env")

import sys
sys.path.insert(0, str(ROOT))

from backend.ingestion.reader import load_absences_df, detect_delta
from backend.analysis.engine import calculer_profils, filtrer_alertes, upsert_alertes
from backend.agent.ia_agent import (
    traiter_alertes, envoyer_alerte_auto,
    _html_avertissement as html_avertissement,
    _html_exclusion     as html_exclusion,
    send_email          as _send_email,
)
from backend.agent.email_agent import init_alerts_db, process_student_alerts, get_alert_history
from backend.agent.groq_agent import analyser as analyser_ia, IAIndisponible
from backend.database.import_notes import ensure_notes_schema
from backend.database.import_planning import (
    resume_planning, ensure_planning_schema, get_date_debut, numero_semaine,
)
from backend.database.groupe import ensure_groupe_column, groupe_depuis_cursus, normaliser_groupe
from backend.database.import_performance import (
    import_performance, performance_etudiant, ensure_performance_schema, annee_scolaire_courante,
    moyennes_par_etudiant,
)
from backend.analysis.indicateurs import taux_absence_cumulatif, taux_absence_global
from backend.api.auth import (
    create_token, require_auth, require_role, public, acces_etudiant_refuse, verifier_protection,
)
from backend.api.imports.common import (
    CACHE as _cache,
    hash_password as _hash_password, gen_email as _gen_email, gen_mot_de_passe as _gen_mot_de_passe,
    html_credentials as _html_credentials, cle_colonne as _cle_colonne,
    traiter_fichier_xlsx as _traiter_fichier_xlsx,
)
from backend.api.imports.import_etudiants import import_etudiants_csv, _gen_mot_de_passe_temporaire
from backend.api.imports.import_absences import import_absences_csv
from backend.api.imports.import_planning import import_planning_route
from backend.api.imports.import_notes import import_notes_route, import_notes_preview
from backend.api.imports.import_modules import import_modules_route

app = Flask(__name__)
CORS(app)
init_alerts_db()

# Création de la table password_resets si elle n'existe pas
def _init_password_resets():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_etudiant INTEGER NOT NULL,
            token       TEXT    UNIQUE NOT NULL,
            expires_at  DATETIME NOT NULL,
            used        BOOLEAN DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_etudiant) REFERENCES etudiants(id)
        )
    """)
    conn.commit()
    conn.close()

_init_password_resets()


def _init_professeurs():
    conn = sqlite3.connect(DB_PATH)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "professeurs" in tables:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(professeurs)").fetchall()}
        if "password_hash" not in cols:
            # Old schema without auth — drop and recreate
            conn.execute("DROP TABLE IF EXISTS professeur_modules")
            conn.execute("DROP TABLE IF EXISTS professeurs")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS professeurs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nom           TEXT NOT NULL,
            prenom        TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login    DATETIME
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS professeur_modules (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            id_professeur INTEGER NOT NULL,
            id_module     INTEGER NOT NULL,
            FOREIGN KEY (id_professeur) REFERENCES professeurs(id),
            FOREIGN KEY (id_module)     REFERENCES modules(id),
            UNIQUE(id_professeur, id_module)
        )
    """)
    conn.commit()
    conn.close()

_init_professeurs()


def _init_users_must_change_password():
    """Comptes créés par import CSV : mot de passe temporaire à changer à la 1re connexion."""
    conn = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "must_change_password" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    conn.close()

_init_users_must_change_password()


def _init_password_version():
    """Colonne password_version ('sha256' | 'bcrypt') sur users et professeurs.
    Les comptes existants sont en SHA-256 : ils passent en bcrypt à leur prochaine connexion."""
    conn = sqlite3.connect(DB_PATH)
    for table in ("users", "professeurs"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if cols and "password_version" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN password_version TEXT NOT NULL DEFAULT 'sha256'")
    conn.commit()
    conn.close()

_init_password_version()

_conn = sqlite3.connect(DB_PATH)
ensure_groupe_column(_conn)  # etudiants.groupe (ALTER TABLE) + remplissage depuis cursus
ensure_notes_schema(_conn)
ensure_planning_schema(_conn)
ensure_performance_schema(_conn)
_conn.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _verify_password(password: str, stored_hash: str, version: str | None) -> bool:
    """Vérifie selon l'algo du compte : bcrypt, ou SHA-256 non salé (anciens comptes)."""
    if not stored_hash:
        return False
    if version == "bcrypt" or stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
        except ValueError:
            return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy, stored_hash)


def _needs_rehash(stored_hash: str, version: str | None) -> bool:
    return not (version == "bcrypt" and stored_hash.startswith("$2"))


def _to_python(obj):
    if isinstance(obj, np.integer):  return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.bool_):    return bool(obj)
    if isinstance(obj, np.ndarray):  return obj.tolist()
    if isinstance(obj, float) and obj != obj: return None
    return obj


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list): return [_serialize(i) for i in obj]
    if isinstance(obj, dict): return {k: _serialize(v) for k, v in obj.items()}
    return _to_python(obj)



# ── Cache mémoire ─────────────────────────────────────────────────────────────



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
            m for m in profil_data.get("modules", [])
            if str(m.get("module", "")) in modules_du_delta
        ]
        if profil_data["modules"]:
            results.extend(process_student_alerts(profil_data, notify_staff=False))

    return {
        "processed": len(profils_touches),
        "sent":    sum(1 for r in results if r.get("sent")),
        "failed":  sum(1 for r in results if not r.get("sent") and r.get("reason") != "doublon"),
        "skipped": sum(1 for r in results if r.get("reason") == "doublon"),
        "results": results,
    }


# ── Auth helpers ──────────────────────────────────────────────────────────────

COMPTE_INTROUVABLE = "Compte introuvable. Contactez l'administration."


def _check_email_db(email: str) -> dict:
    """Un étudiant ne peut se connecter que si l'administration lui a créé un compte
    (import CSV ou ajout manuel) : pas d'auto-inscription."""
    conn = _db()
    row = conn.execute(
        "SELECT e.prenom, u.password_hash FROM etudiants e"
        " JOIN users u ON u.id_etudiant = e.id"
        " WHERE LOWER(e.email) = LOWER(?)",
        (email,),
    ).fetchone()
    conn.close()
    if not row or not row["password_hash"]:
        return {"exists": False, "has_password": False, "prenom": "", "error": COMPTE_INTROUVABLE}
    return {"exists": True, "has_password": True, "prenom": row["prenom"]}


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
        return {"success": False, "error": COMPTE_INTROUVABLE}
    u_row = conn.execute(
        "SELECT id, password_hash, password_version, must_change_password FROM users WHERE id_etudiant = ?",
        (et_row["id"],),
    ).fetchone()
    if not u_row:
        conn.close()
        return {"success": False, "error": COMPTE_INTROUVABLE}
    if not _verify_password(password, u_row["password_hash"], u_row["password_version"]):
        conn.close()
        return {"success": False, "error": "Mot de passe incorrect"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, u_row["id"]))
    if _needs_rehash(u_row["password_hash"], u_row["password_version"]):
        # Migration progressive SHA-256 → bcrypt, le mot de passe en clair étant connu ici
        conn.execute(
            "UPDATE users SET password_hash = ?, password_version = 'bcrypt' WHERE id = ?",
            (_hash_password(password), u_row["id"]),
        )
    conn.commit()
    conn.close()
    return {"success": True, "etudiant": {
        "id_etudiant": str(et_row["id"]),
        "nom":    et_row["nom"],
        "prenom": et_row["prenom"],
        "email":  et_row["email"],
        "filiere": et_row["code_filiere"] or "",
        "annee":   et_row["annee"] or "",
        "must_change_password": bool(u_row["must_change_password"]),
    }}


# ── Routes — Stats / Profils ──────────────────────────────────────────────────

@app.route("/api/stats")
@require_auth
@require_role("admin")
def stats():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    alertes = filtrer_alertes(profils)
    return jsonify({
        "total_etudiants": len(profils),
        "total_alertes":   len(alertes),
        "exclu":    sum(1 for p in profils if p.nb_modules_exclu > 0),
        "averti":   sum(1 for p in profils if p.nb_modules_exclu == 0 and p.nb_modules_averti > 0),
        "autorise": sum(1 for p in profils if p.nb_modules_exclu == 0 and p.nb_modules_averti == 0),
        "total_abs_nj": sum(p.total_abs_nj for p in profils),
    })


@app.route("/api/stats/par-filiere")
@require_auth
@require_role("admin")
def stats_par_filiere():
    """Statut global des étudiants (même règle que /api/stats), par code filière."""
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    par_filiere: dict = defaultdict(lambda: {"exclu": 0, "averti": 0, "autorise": 0})
    for p in profils:
        cle = "exclu" if p.nb_modules_exclu > 0 else "averti" if p.nb_modules_averti > 0 else "autorise"
        par_filiere[p.code_filiere or "—"][cle] += 1
    return jsonify([{"filiere": f, **c} for f, c in sorted(par_filiere.items())])


@app.route("/api/ia/analyse", methods=["POST"])
@require_auth
def ia_analyse():
    """Résumé en langage naturel des statistiques envoyées, généré par un LLM (API Groq)."""
    payload = request.get_json(silent=True) or {}
    role    = payload.get("role")
    donnees = payload.get("data")
    if role not in ("admin", "etudiant") or not isinstance(donnees, dict):
        return jsonify({"erreur": "Paramètres attendus : role (admin|etudiant) et data (objet)"}), 400
    # le prompt « administration » est réservé aux comptes admin
    if role == "admin" and g.user.get("role") != "admin":
        return jsonify({"erreur": "Accès refusé"}), 403
    try:
        return jsonify({"analyse": analyser_ia(role, donnees)})
    except IAIndisponible as exc:  # l'app continue : le message d'indisponibilité tient lieu d'analyse
        return jsonify({"analyse": str(exc)})


@app.route("/api/stats/taux-absence")
@require_auth
@require_role("admin")
def stats_taux_absence():
    conn = _db()
    try:
        return jsonify(taux_absence_global(conn))
    finally:
        conn.close()


@app.route("/api/etudiants")
@require_auth
@require_role("professeur")
def etudiants():
    df_abs, profils = _get_data()
    if not profils:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    conn = _db()
    try:
        moyennes = moyennes_par_etudiant(conn)
    finally:
        conn.close()
    result = _serialize(profils)
    for e in result:
        m = moyennes.get(int(e["id_etudiant"]), {})
        e["moyenne_brute"] = m.get("moyenne_brute")
        e["moyenne_nette"] = m.get("moyenne_nette")
    return jsonify(result)


_SEMAINES_SEMESTRE = {"1": (1, 16), "2": (17, 32)}


@app.route("/api/absences/par-semaine")
@require_auth
@require_role("admin")
def absences_par_semaine():
    """Heures d'absence (justifiées + NJ) d'un module, groupées par semaine scolaire.
    semestre=1 -> semaines 1→16, semestre=2 -> semaines 17→32 ; toutes les semaines sont renvoyées."""
    module   = (request.args.get("module")  or "").strip()
    filiere  = (request.args.get("filiere") or "").strip()
    semestre = (request.args.get("semestre") or "1").strip().upper().lstrip("S")
    if not module:
        return jsonify({"erreur": "Paramètre module requis"}), 400
    if semestre not in _SEMAINES_SEMESTRE:
        return jsonify({"erreur": "Paramètre semestre invalide (1 ou 2)"}), 400
    debut_sem, fin_sem = _SEMAINES_SEMESTRE[semestre]
    conn = _db()
    try:
        ensure_planning_schema(conn)
        debut = get_date_debut(conn)
        rows = conn.execute(
            """SELECT a.date_absence, a.duree_heures
               FROM absences a
               JOIN etudiants e ON a.id_etudiant = e.id
               LEFT JOIN modules  m ON a.id_module = m.id
               LEFT JOIN filieres f ON f.id = COALESCE(m.id_filiere, e.id_filiere)
               WHERE COALESCE(m.nom, a.module_nom) = ? AND (? = '' OR f.code = ?)""",
            (module, filiere, filiere),
        ).fetchall()
    finally:
        conn.close()
    heures = defaultdict(float)
    for d, duree in rows:
        try:
            semaine = numero_semaine(datetime.fromisoformat(str(d)[:10]).date(), debut)
        except ValueError:
            continue
        heures[semaine] += duree or 0
    return jsonify([{"semaine": str(s), "heures": round(heures.get(s, 0), 2)}
                    for s in range(debut_sem, fin_sem + 1)])


@app.route("/api/etudiant/<id_etudiant>")
@require_auth
def etudiant(id_etudiant: str):
    if acces_etudiant_refuse(id_etudiant):
        return jsonify({"erreur": "Accès refusé"}), 403
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

    conn = _db()
    notes = [dict(r) for r in conn.execute(
        """SELECT semestre, moyenne_generale, annee_universitaire, source_fichier, imported_at
           FROM notes WHERE id_etudiant=?
           ORDER BY annee_universitaire, CAST(SUBSTR(semestre, 2) AS INTEGER)""",
        (int(id_etudiant),),
    ).fetchall()]
    conn.close()
    for n in notes:
        n["statut"] = "Validé" if n["moyenne_generale"] >= 10 else "Non validé"

    return jsonify({"profil": _serialize(profil), "absences": absences, "notes": notes})


def _etudiant_existe(conn, id_etudiant: str) -> bool:
    return id_etudiant.isdigit() and conn.execute(
        "SELECT 1 FROM etudiants WHERE id=?", (int(id_etudiant),)
    ).fetchone() is not None


@app.route("/api/etudiant/<id_etudiant>/taux-absence")
@require_auth
def etudiant_taux_absence(id_etudiant: str):
    if acces_etudiant_refuse(id_etudiant):
        return jsonify({"erreur": "Accès refusé"}), 403
    conn = _db()
    try:
        if not _etudiant_existe(conn, id_etudiant):
            return jsonify({"erreur": "Étudiant non trouvé"}), 404
        return jsonify(taux_absence_cumulatif(conn, int(id_etudiant))["semaines"])
    finally:
        conn.close()


@app.route("/api/etudiant/<id_etudiant>/performance")
@require_auth
def etudiant_performance(id_etudiant: str):
    if acces_etudiant_refuse(id_etudiant):
        return jsonify({"erreur": "Accès refusé"}), 403
    conn = _db()
    try:
        if not _etudiant_existe(conn, id_etudiant):
            return jsonify({"erreur": "Étudiant non trouvé"}), 404
        perf = performance_etudiant(conn, int(id_etudiant))
        if perf is None:
            return jsonify({"erreur": "Aucune moyenne brute/nette importée pour cet étudiant"}), 404
        return jsonify(perf)
    finally:
        conn.close()


# ── Routes — Alertes (historique, lecture seule) ──────────────────────────────

@app.route("/api/alertes")
@require_auth
@require_role("admin")
def alertes():
    """Historique des alertes — lecture seule, pas d'envoi à chaque GET."""
    conn = _db()
    rows = conn.execute("""
        SELECT al.id, al.statut, al.taux_nj, al.taux_total,
               al.avert_envoye, al.exclu_envoye, al.updated_at,
               e.id AS id_etudiant, e.nom, e.prenom, e.email, e.cursus,
               COALESCE(f.code,'') AS filiere,
               COALESCE(m.nom,'—') AS module_nom
        FROM alertes al
        JOIN etudiants e ON al.id_etudiant = e.id
        LEFT JOIN modules  m ON al.id_module  = m.id
        LEFT JOIN filieres f ON m.id_filiere  = f.id
        WHERE al.statut != 'AUTORISE'
        ORDER BY al.updated_at DESC
    """).fetchall()

    result = []
    for r in rows:
        id_alerte  = r[0]
        statut     = r[1]
        taux_nj    = float(r[2] or 0)
        taux_total = float(r[3] or 0)
        envoye_auto = bool(r[4]) or bool(r[5])

        log = conn.execute(
            "SELECT envoye_le FROM emails_log WHERE id_alerte=? AND envoye=1"
            " AND type_email IN ('avert','exclu') ORDER BY id LIMIT 1",
            (id_alerte,),
        ).fetchone()
        envoye_le = log[0] if log else None

        mod_nom = r[13]
        nom, prenom = r[8], r[9]
        if statut == "EXCLU":
            email_sujet = f"Exclusion d'examen — {mod_nom} — ESITH Casablanca"
            email_corps = html_exclusion(nom, prenom, mod_nom, taux_total)
        else:
            email_sujet = f"Avertissement absences — {mod_nom} — ESITH Casablanca"
            email_corps = html_avertissement(nom, prenom, mod_nom, taux_nj)

        result.append({
            "id_alerte":   id_alerte,
            "statut":      statut,
            "taux_nj":     taux_nj,
            "taux_total":  taux_total,
            "id_etudiant": str(r[7]),
            "nom":         nom,
            "prenom":      prenom,
            "email":       r[10],
            "cursus":      r[11] or "",
            "filiere":     r[12],
            "module_nom":  mod_nom,
            "email_sujet": email_sujet,
            "email_corps": email_corps,
            "envoye_auto": envoye_auto,
            "envoye_le":   envoye_le,
            "updated_at":  r[6],
        })

    conn.close()
    return jsonify(result)


# ── Routes — Gestion étudiants ────────────────────────────────────────────────

@app.route("/api/sessions-programme")
@require_auth
@require_role("admin")
def sessions_programme():
    """Retourne les session_programme distincts depuis etudiants (rétrocompat)."""
    conn = _db()
    rows = conn.execute(
        "SELECT DISTINCT session_programme FROM etudiants"
        " WHERE session_programme IS NOT NULL AND session_programme != ''"
        " ORDER BY session_programme"
    ).fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])


@app.route("/api/session-programmes")
@require_auth
@require_role("admin")
def session_programmes_list():
    """Retourne les 27 filières comme options de session — source unique pour le formulaire."""
    conn = _db()
    rows = conn.execute(
        "SELECT id, nom, code, niveau FROM filieres ORDER BY code, niveau"
    ).fetchall()
    conn.close()
    return jsonify([
        {"id": r[0], "nom": r[1], "code": r[2], "niveau": r[3]}
        for r in rows
    ])


@app.route("/api/etudiants/paginated")
@require_auth
@require_role("admin")
def etudiants_paginated():
    page   = max(1, int(request.args.get("page",  1)))
    limit  = max(1, min(100, int(request.args.get("limit", 20))))
    search = request.args.get("search", "").strip()
    offset = (page - 1) * limit

    conn = _db()
    if search:
        q      = f"%{search.lower()}%"
        where  = " WHERE (LOWER(e.nom) LIKE ? OR LOWER(e.prenom) LIKE ? OR LOWER(e.email) LIKE ?)"
        params = [q, q, q]
    else:
        where, params = "", []

    total = conn.execute(f"SELECT COUNT(*) FROM etudiants e{where}", params).fetchone()[0]
    rows  = conn.execute(
        f"""SELECT e.id, e.nom, e.prenom, e.email, e.cursus, e.session_programme,
                COALESCE(f.code,'') AS filiere, COALESCE(f.niveau,'') AS niveau,
                (SELECT statut FROM alertes al WHERE al.id_etudiant=e.id
                 ORDER BY CASE statut WHEN 'EXCLU' THEN 2 WHEN 'AVERTI' THEN 1 ELSE 0 END DESC
                 LIMIT 1) AS statut_global
            FROM etudiants e LEFT JOIN filieres f ON e.id_filiere=f.id{where}
            ORDER BY e.nom, e.prenom LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    conn.close()

    return jsonify({
        "etudiants": [
            {
                "id": r[0], "nom": r[1], "prenom": r[2], "email": r[3],
                "cursus": r[4] or "", "session_programme": r[5] or "",
                "filiere": r[6], "niveau": r[7],
                "statut_global": r[8] or "AUTORISE",
            }
            for r in rows
        ],
        "total": total,
        "page":  page,
        "total_pages": max(1, -(-total // limit)),
    })


@app.route("/api/etudiants/ajouter", methods=["POST"])
@require_auth
@require_role("admin")
def etudiants_ajouter():
    p            = request.get_json(silent=True) or {}
    nom          = (p.get("nom")   or "").strip()
    prenom       = (p.get("prenom") or "").strip()
    id_inscr     = (p.get("id_inscriptionsessionprogramme") or "").strip()
    session_prog = (p.get("session_programme") or "").strip()
    cursus       = (p.get("cursus") or "").strip()

    if not nom or not prenom:
        return jsonify({"success": False, "error": "Nom et prénom requis"}), 400

    email = _gen_email(prenom, nom)
    conn  = _db()

    # id_filiere : priorité au paramètre direct, sinon dérivé du session_programme
    id_filiere = p.get("id_filiere") or None
    if id_filiere:
        id_filiere = int(id_filiere)
    elif session_prog:
        row = conn.execute(
            "SELECT id_filiere FROM etudiants WHERE session_programme=? AND id_filiere IS NOT NULL LIMIT 1",
            (session_prog,),
        ).fetchone()
        if row:
            id_filiere = row[0]

    if id_inscr:
        exist = conn.execute(
            "SELECT id, nom, prenom FROM etudiants WHERE id_inscriptionsessionprogramme=?",
            (id_inscr,),
        ).fetchone()
        if exist:
            conn.close()
            return jsonify({
                "success": False, "exists": True,
                "etudiant_existant": {"id": exist[0], "nom": exist[1], "prenom": exist[2]},
            })

    groupe = normaliser_groupe(p.get("groupe")) or groupe_depuis_cursus(cursus, session_prog)
    cur = conn.execute(
        "INSERT INTO etudiants (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, cursus,"
        " session_programme, groupe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (id_inscr or None, nom, prenom, email, id_filiere, cursus or None, session_prog or None, groupe),
    )
    new_id = cur.lastrowid

    # Compte créé par l'admin : mot de passe temporaire à changer à la 1re connexion
    mdp = _gen_mot_de_passe_temporaire()
    conn.execute(
        "INSERT INTO users (id_etudiant, email, password_hash, password_version, created_at, must_change_password)"
        " VALUES (?, ?, ?, 'bcrypt', ?, 1)",
        (new_id, email.lower(), _hash_password(mdp), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    _cache["data"] = None

    try:
        email_envoye = bool(_send_email(email, "Vos identifiants StudentTrack — ESITH",
                                        _html_credentials(prenom, nom, email, mdp, role="Étudiant", temporaire=True)))
    except Exception:
        email_envoye = False
    return jsonify({"success": True, "email_envoye": email_envoye,
                    "etudiant": {"id": new_id, "nom": nom, "prenom": prenom, "email": email}})


@app.route("/api/etudiants/<int:et_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def etudiants_update(et_id: int):
    p            = request.get_json(silent=True) or {}
    nom          = (p.get("nom")   or "").strip()
    prenom       = (p.get("prenom") or "").strip()
    session_prog = (p.get("session_programme") or "").strip()
    cursus       = (p.get("cursus") or "").strip()

    conn  = _db()
    exist = conn.execute("SELECT nom, prenom, email FROM etudiants WHERE id=?", (et_id,)).fetchone()
    if not exist:
        conn.close()
        return jsonify({"success": False, "error": "Étudiant non trouvé"}), 404

    new_nom    = nom    or exist[0]
    new_prenom = prenom or exist[1]
    new_email  = _gen_email(new_prenom, new_nom) if (nom and nom != exist[0]) or (prenom and prenom != exist[1]) else exist[2]

    id_filiere = None
    if session_prog:
        row = conn.execute(
            "SELECT id_filiere FROM etudiants WHERE session_programme=? AND id_filiere IS NOT NULL LIMIT 1",
            (session_prog,),
        ).fetchone()
        if row:
            id_filiere = row[0]

    sets = ["nom=?", "prenom=?", "email=?"]
    vals = [new_nom, new_prenom, new_email]
    if cursus:
        sets.append("cursus=?"); vals.append(cursus)
    if session_prog:
        sets.append("session_programme=?"); vals.append(session_prog)
    if id_filiere:
        sets.append("id_filiere=?"); vals.append(id_filiere)
    groupe = normaliser_groupe(p.get("groupe")) or (
        groupe_depuis_cursus(cursus, session_prog) if (cursus or session_prog) else None)
    if groupe:
        sets.append("groupe=?"); vals.append(groupe)
    vals.append(et_id)

    conn.execute(f"UPDATE etudiants SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()
    _cache["data"] = None
    return jsonify({"success": True})


@app.route("/api/etudiants/<int:et_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def etudiants_delete(et_id: int):
    conn = _db()
    if not conn.execute("SELECT id FROM etudiants WHERE id=?", (et_id,)).fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Étudiant non trouvé"}), 404

    alerte_ids = [r[0] for r in conn.execute("SELECT id FROM alertes WHERE id_etudiant=?", (et_id,)).fetchall()]
    if alerte_ids:
        conn.execute(f"DELETE FROM emails_log WHERE id_alerte IN ({','.join('?'*len(alerte_ids))})", alerte_ids)
    conn.execute("DELETE FROM alertes  WHERE id_etudiant=?", (et_id,))
    conn.execute("DELETE FROM absences WHERE id_etudiant=?", (et_id,))
    conn.execute("DELETE FROM users    WHERE id_etudiant=?", (et_id,))
    conn.execute("DELETE FROM etudiants WHERE id=?",         (et_id,))
    conn.commit()
    conn.close()
    _cache["data"] = None
    return jsonify({"success": True})


# ── Routes — Anciens endpoints conservés ─────────────────────────────────────

@app.route("/api/modules")
@require_auth
@require_role("professeur")
def modules():
    if not DB_PATH.exists():
        return jsonify({"erreur": "Base SQLite introuvable"}), 404
    conn = _db()
    rows = conn.execute(
        "SELECT m.nom, f.code AS filiere, m.semestre"
        " FROM modules m LEFT JOIN filieres f ON m.id_filiere = f.id ORDER BY m.nom"
    ).fetchall()
    conn.close()
    by_nom: dict = defaultdict(lambda: {"filieres": set(), "semestres": set()})
    for r in rows:
        nom = r["nom"]
        if r["filiere"]:  by_nom[nom]["filieres"].add(r["filiere"])
        if r["semestre"] and r["semestre"] not in ("S0", ""): by_nom[nom]["semestres"].add(r["semestre"])
    return jsonify([
        {"nom": nom, "filieres": sorted(d["filieres"]), "semestres": sorted(d["semestres"])}
        for nom, d in sorted(by_nom.items())
    ])


@app.route("/api/filieres")
@require_auth
@require_role("professeur")
def filieres():
    df_abs, profils = _get_data()
    if df_abs is None:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    return jsonify(sorted(df_abs["filiere"].dropna().unique().tolist()))


@app.route("/api/filieres-par-module/<nom_module>")
@require_auth
@require_role("professeur")
def filieres_par_module(nom_module: str):
    if not DB_PATH.exists():
        return jsonify([]), 404
    conn = _db()
    rows = conn.execute(
        "SELECT DISTINCT f.code FROM modules m LEFT JOIN filieres f ON m.id_filiere = f.id"
        " WHERE m.nom = ? AND f.code IS NOT NULL ORDER BY f.code",
        (nom_module,),
    ).fetchall()
    conn.close()
    return jsonify([r["code"] for r in rows])


@app.route("/api/modules/all")
@require_auth
@require_role("admin")
def modules_all():
    conn = _db()
    rows = conn.execute(
        "SELECT m.id, m.nom, m.semestre, m.volume_heures, f.code AS filiere"
        " FROM modules m LEFT JOIN filieres f ON m.id_filiere = f.id ORDER BY m.nom"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/filieres/all")
@require_auth
@require_role("admin")
def filieres_all():
    conn = _db()
    rows = conn.execute("SELECT id, nom, code, niveau FROM filieres ORDER BY code, niveau").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/module-classes")
@require_auth
@require_role("professeur")
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
        "filieres":   sorted(set(r["code"]   for r in rows if r["code"])),
        "promotions": sorted(set(r["niveau"]  for r in rows if r["niveau"])),
    })


# ── Routes — Auth ─────────────────────────────────────────────────────────────

@app.route("/api/auth/check-email", methods=["POST"])
@public
def auth_check_email():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email requis"}), 400
    return jsonify(_check_email_db(email))


@app.route("/api/auth/login", methods=["POST"])
@public
def auth_login():
    payload  = request.get_json(silent=True) or {}
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400
    result = _login_db(email, password)
    if not result["success"]:
        return jsonify(result), 401
    et = result["etudiant"]
    result["token"] = create_token("etudiant", email=et["email"], id_etudiant=et["id_etudiant"],
                                   must_change_password=et["must_change_password"])
    return jsonify(result)


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
@require_role("etudiant")
def auth_change_password():
    """Changement de mot de passe par l'étudiant connecté (obligatoire après un mot de passe temporaire).
    Renvoie un nouveau token sans la restriction « mot de passe temporaire »."""
    payload  = request.get_json(silent=True) or {}
    actuel   = payload.get("current_password") or ""
    nouveau  = payload.get("new_password") or ""
    id_et    = g.user.get("id_etudiant")
    if id_et is None:
        return jsonify({"success": False, "error": "Réservé aux comptes étudiants"}), 403
    if len(nouveau) < 8:
        return jsonify({"success": False, "error": "Le mot de passe doit contenir au moins 8 caractères"}), 400
    if nouveau == actuel:
        return jsonify({"success": False, "error": "Le nouveau mot de passe doit être différent de l'ancien"}), 400

    conn = _db()
    u_row = conn.execute(
        "SELECT password_hash, password_version FROM users WHERE id_etudiant = ?", (id_et,)
    ).fetchone()
    if not u_row or not _verify_password(actuel, u_row["password_hash"], u_row["password_version"]):
        conn.close()
        return jsonify({"success": False, "error": "Mot de passe actuel incorrect"}), 400
    conn.execute(
        "UPDATE users SET password_hash = ?, password_version = 'bcrypt', must_change_password = 0"
        " WHERE id_etudiant = ?",
        (_hash_password(nouveau), id_et),
    )
    conn.commit()
    conn.close()
    return jsonify({
        "success": True,
        "token": create_token("etudiant", email=g.user.get("email", ""), id_etudiant=id_et),
    })


@app.route("/api/auth/admin-login", methods=["POST"])
@public
def auth_admin_login():
    payload  = request.get_json(silent=True) or {}
    password = payload.get("password", "")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_pw:
        return jsonify({"success": False, "error": "ADMIN_PASSWORD non configuré dans .env"}), 500
    if secrets.compare_digest(password, admin_pw):
        return jsonify({"success": True, "token": create_token("admin")})
    return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401


# ── Password reset helpers ────────────────────────────────────────────────────

def _get_etudiant_by_email(email: str):
    conn = _db()
    row = conn.execute(
        "SELECT id, nom, prenom, email FROM etudiants WHERE LOWER(email)=?",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()
    return row


def _save_reset_token(id_etudiant: int, token: str, expires_at: str):
    conn = _db()
    # Invalider les anciens tokens non utilisés pour cet étudiant
    conn.execute(
        "UPDATE password_resets SET used=1 WHERE id_etudiant=? AND used=0",
        (id_etudiant,),
    )
    conn.execute(
        "INSERT INTO password_resets (id_etudiant, token, expires_at) VALUES (?, ?, ?)",
        (id_etudiant, token, expires_at),
    )
    conn.commit()
    conn.close()


def _get_valid_reset_token(token: str):
    conn = _db()
    row = conn.execute(
        "SELECT id, id_etudiant FROM password_resets"
        " WHERE token=? AND used=0 AND expires_at > datetime('now')",
        (token,),
    ).fetchone()
    conn.close()
    return row


def _mark_token_used(token: str):
    conn = _db()
    conn.execute("UPDATE password_resets SET used=1 WHERE token=?", (token,))
    conn.commit()
    conn.close()


def _update_user_password(id_etudiant: int, password_hash: str) -> bool:
    """Met à jour le mot de passe d'un compte existant. Ne crée jamais de compte :
    seule l'administration en crée (import CSV, ajout manuel)."""
    conn = _db()
    cur = conn.execute(
        "UPDATE users SET password_hash=?, password_version='bcrypt', must_change_password=0"
        " WHERE id_etudiant=?",
        (password_hash, id_etudiant),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def _has_user_account(id_etudiant: int) -> bool:
    conn = _db()
    row = conn.execute("SELECT 1 FROM users WHERE id_etudiant=?", (id_etudiant,)).fetchone()
    conn.close()
    return row is not None


@app.route("/api/auth/forgot-password", methods=["POST"])
@public
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email   = (payload.get("email") or "").strip().lower()
    generic = {"success": True, "message": "Si cet email existe, un lien a été envoyé."}

    if not email:
        return jsonify(generic)

    etudiant = _get_etudiant_by_email(email)
    if not etudiant or not _has_user_account(etudiant["id"]):
        return jsonify(generic)

    token      = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    _save_reset_token(etudiant["id"], token, expires_at)

    reset_link = f"http://localhost:5173/reset-password?token={token}"
    html_body  = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
      <h2 style="color:#1a3a6b">Réinitialisation de mot de passe — StudentTrack</h2>
      <p>Madame/Monsieur <strong>{etudiant['prenom']} {etudiant['nom']}</strong>,</p>
      <p>Vous avez demandé la réinitialisation de votre mot de passe StudentTrack.</p>
      <p>Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe
         (lien valide <strong>1 heure</strong>) :</p>
      <p style="margin:24px 0">
        <a href="{reset_link}"
           style="background:#8DC63F;color:#fff;padding:12px 24px;
                  text-decoration:none;border-radius:6px;display:inline-block;
                  font-weight:700">
          Réinitialiser mon mot de passe
        </a>
      </p>
      <p style="color:#64748b;font-size:12px">
        Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
        Votre mot de passe actuel reste inchangé.
      </p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:11px">
        Service de la Scolarité — ESITH Casablanca — StudentTrack
      </p>
    </div>
    """
    _send_email(
        etudiant["email"],
        "Réinitialisation de mot de passe — StudentTrack",
        html_body,
    )
    return jsonify(generic)


@app.route("/api/auth/reset-password", methods=["POST"])
@public
def reset_password_route():
    payload      = request.get_json(silent=True) or {}
    token        = (payload.get("token")        or "").strip()
    new_password = (payload.get("new_password") or "")

    if not token:
        return jsonify({"success": False, "error": "Token manquant"}), 400

    reset_entry = _get_valid_reset_token(token)
    if not reset_entry:
        return jsonify({
            "success": False,
            "error": "Lien invalide ou expiré. Demandez un nouveau lien.",
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "success": False,
            "error": "Le mot de passe doit contenir au moins 8 caractères.",
        }), 400

    if not _update_user_password(reset_entry["id_etudiant"], _hash_password(new_password)):
        return jsonify({"success": False, "error": COMPTE_INTROUVABLE}), 400
    _mark_token_used(token)
    return jsonify({"success": True, "message": "Mot de passe réinitialisé avec succès."})


# ── Routes — Import planning hebdomadaire / moyennes brute-nette ──────────────

@app.route("/api/planning")
@require_auth
@require_role("admin")
def planning_resume():
    return jsonify(resume_planning())


@app.route("/api/import-performance", methods=["POST"])
@require_auth
@require_role("admin")
def import_performance_route():
    annee = (request.form.get("annee_scolaire") or "").strip() or annee_scolaire_courante()
    stats, err = _traiter_fichier_xlsx(lambda path, _nom: import_performance(path, annee))
    return err or jsonify(stats)


# ── Routes — Sync ─────────────────────────────────────────────────────────────

@app.route("/api/sync", methods=["POST"])
@require_auth
@require_role("admin")
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
        "changed":          bool(changed),
        "email_alerts":     email_alerts,
    })


@app.route("/api/alerts/history")
@require_auth
@require_role("admin")
def alerts_history():
    student_id = request.args.get("student_id")
    return jsonify({"alerts": get_alert_history(student_id)})


# ── Routes — Gestion Professeurs ──────────────────────────────────────────────

def _prof_modules(conn, prof_id: int) -> list:
    return [dict(r) for r in conn.execute(
        """SELECT m.id, m.nom, m.semestre, COALESCE(f.code,'') AS filiere
           FROM professeur_modules pm
           JOIN modules m ON pm.id_module = m.id
           LEFT JOIN filieres f ON m.id_filiere = f.id
           WHERE pm.id_professeur = ?
           ORDER BY f.code, m.nom""",
        (prof_id,),
    ).fetchall()]


@app.route("/api/professeurs")
@require_auth
@require_role("admin")
def get_professeurs():
    conn = _db()
    profs = conn.execute(
        "SELECT id, nom, prenom, email FROM professeurs ORDER BY nom, prenom"
    ).fetchall()
    result = [
        {"id": p["id"], "nom": p["nom"], "prenom": p["prenom"],
         "email": p["email"], "modules": _prof_modules(conn, p["id"])}
        for p in profs
    ]
    conn.close()
    return jsonify(result)


@app.route("/api/professeurs/ajouter", methods=["POST"])
@require_auth
@require_role("admin")
def professeurs_ajouter():
    p          = request.get_json(silent=True) or {}
    nom        = (p.get("nom")    or "").strip()
    prenom     = (p.get("prenom") or "").strip()
    module_ids = [int(x) for x in (p.get("module_ids") or [])
                  if str(x).lstrip("-").isdigit()]

    if not nom or not prenom:
        return jsonify({"success": False, "error": "Nom et prénom requis"}), 400

    email = _gen_email(prenom, nom)
    conn  = _db()

    if conn.execute("SELECT id FROM professeurs WHERE email=?", (email,)).fetchone():
        conn.close()
        return jsonify({"success": False,
                        "error": f"Un professeur avec l'email {email} existe déjà"}), 400

    mdp     = _gen_mot_de_passe()
    pw_hash = _hash_password(mdp)
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur     = conn.execute(
            "INSERT INTO professeurs (nom, prenom, email, password_hash, password_version, created_at)"
            " VALUES (?, ?, ?, ?, 'bcrypt', ?)",
            (nom, prenom, email, pw_hash, now),
        )
        prof_id = cur.lastrowid
        for mid in module_ids:
            conn.execute(
                "INSERT OR IGNORE INTO professeur_modules (id_professeur, id_module) VALUES (?, ?)",
                (prof_id, mid),
            )
        conn.commit()
    except Exception as exc:
        conn.close()
        return jsonify({"success": False, "error": str(exc)}), 400

    email_envoye = False
    try:
        _send_email(
            email,
            "Vos identifiants StudentTrack — ESITH Casablanca",
            _html_credentials(prenom, nom, email, mdp),
        )
        email_envoye = True
    except Exception:
        pass

    conn.close()
    return jsonify({
        "success":      True,
        "professeur":   {"id": prof_id, "nom": nom, "prenom": prenom, "email": email},
        "email_envoye": email_envoye,
    })


def _modules_pour(conn, module: str, filiere: str) -> list[int]:
    """Ids des modules portant ce nom dans cette filière (toutes promotions).
    La filière accepte le code exact ('GI-EO') ou son suffixe ('EO')."""
    filiere = filiere.upper()
    return [r[0] for r in conn.execute(
        """SELECT m.id FROM modules m JOIN filieres f ON m.id_filiere = f.id
           WHERE LOWER(TRIM(m.nom)) = LOWER(?) AND (UPPER(f.code) = ? OR UPPER(f.code) LIKE ?)""",
        (module.strip(), filiere, f"%-{filiere}"),
    ).fetchall()]


@app.route("/api/professeurs/import-csv", methods=["POST"])
@require_auth
@require_role("admin")
def professeurs_import_csv():
    """CSV nom, prenom, email, module, filiere — une ligne par module enseigné.
    Les emails déjà en base sont ignorés ; chaque nouveau professeur reçoit ses identifiants."""
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
    try:
        df = pd.read_csv(io.BytesIO(uploaded.read()), sep=None, engine="python",
                         dtype=str, encoding="utf-8-sig").fillna("")
    except Exception as exc:
        return jsonify({"success": False, "error": f"CSV illisible : {exc}"}), 400

    df.columns = [_cle_colonne(c) for c in df.columns]
    manquantes = {"nom", "prenom", "email", "module", "filiere"} - set(df.columns)
    if manquantes:
        return jsonify({"success": False,
                        "error": f"Colonnes manquantes : {', '.join(sorted(manquantes))}"}), 400

    # Regroupe les lignes par email : un professeur peut enseigner plusieurs modules
    profs: dict[str, dict] = {}
    for _, row in df.iterrows():
        email = row["email"].strip().lower()
        if not email:
            continue
        p = profs.setdefault(email, {"nom": row["nom"].strip(), "prenom": row["prenom"].strip(), "modules": []})
        if row["module"].strip():
            p["modules"].append((row["module"].strip(), row["filiere"].strip()))

    conn = _db()
    existants = {r[0].lower() for r in conn.execute("SELECT email FROM professeurs").fetchall()}
    ajoutes, ignores, erreurs, modules_introuvables, a_notifier = [], [], [], [], []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for email, p in profs.items():
        if email in existants:
            ignores.append(email)
            continue
        if not p["nom"] or not p["prenom"]:
            erreurs.append(f"{email} : nom ou prénom manquant")
            continue
        mdp = _gen_mot_de_passe()
        cur = conn.execute(
            "INSERT INTO professeurs (nom, prenom, email, password_hash, password_version, created_at)"
            " VALUES (?, ?, ?, ?, 'bcrypt', ?)",
            (p["nom"], p["prenom"], email, _hash_password(mdp), now),
        )
        for module, filiere in p["modules"]:
            ids = _modules_pour(conn, module, filiere)
            if not ids:
                modules_introuvables.append(f"{module} ({filiere or '—'}) — {email}")
            for mid in ids:
                conn.execute(
                    "INSERT OR IGNORE INTO professeur_modules (id_professeur, id_module) VALUES (?, ?)",
                    (cur.lastrowid, mid),
                )
        ajoutes.append(email)
        a_notifier.append((p["prenom"], p["nom"], email, mdp))
    conn.commit()
    conn.close()

    emails_echoues = []
    for prenom, nom, email, mdp in a_notifier:
        try:
            envoye = _send_email(email, "Vos identifiants StudentTrack — ESITH Casablanca",
                                 _html_credentials(prenom, nom, email, mdp))
        except Exception:
            envoye = False
        if not envoye:
            emails_echoues.append(email)

    return jsonify({
        "success":              True,
        "ajoutes":              len(ajoutes),
        "ignores":              len(ignores),
        "erreurs":              erreurs,
        "modules_introuvables": modules_introuvables,
        "emails_echoues":       emails_echoues,
    })


@app.route("/api/professeurs/<int:prof_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def professeurs_update(prof_id: int):
    p          = request.get_json(silent=True) or {}
    nom        = (p.get("nom")    or "").strip()
    prenom     = (p.get("prenom") or "").strip()
    module_ids = [int(x) for x in (p.get("module_ids") or [])
                  if str(x).lstrip("-").isdigit()]

    conn = _db()
    if not conn.execute("SELECT id FROM professeurs WHERE id=?", (prof_id,)).fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Professeur non trouvé"}), 404

    sets, vals = [], []
    if nom:    sets.append("nom=?");    vals.append(nom)
    if prenom: sets.append("prenom=?"); vals.append(prenom)
    if sets:
        vals.append(prof_id)
        conn.execute(f"UPDATE professeurs SET {', '.join(sets)} WHERE id=?", vals)

    conn.execute("DELETE FROM professeur_modules WHERE id_professeur=?", (prof_id,))
    for mid in module_ids:
        conn.execute(
            "INSERT OR IGNORE INTO professeur_modules (id_professeur, id_module) VALUES (?, ?)",
            (prof_id, mid),
        )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/professeurs/<int:prof_id>/reset-password", methods=["POST"])
@require_auth
@require_role("admin")
def professeurs_reset_password(prof_id: int):
    conn = _db()
    prof = conn.execute(
        "SELECT nom, prenom, email FROM professeurs WHERE id=?", (prof_id,)
    ).fetchone()
    if not prof:
        conn.close()
        return jsonify({"success": False, "error": "Professeur non trouvé"}), 404

    mdp     = _gen_mot_de_passe()
    pw_hash = _hash_password(mdp)
    conn.execute("UPDATE professeurs SET password_hash=?, password_version='bcrypt' WHERE id=?", (pw_hash, prof_id))
    conn.commit()

    nom, prenom, email = prof["nom"], prof["prenom"], prof["email"]
    email_envoye = False
    try:
        _send_email(
            email,
            "Réinitialisation de mot de passe — StudentTrack",
            _html_credentials(prenom, nom, email, mdp, reset=True),
        )
        email_envoye = True
    except Exception:
        pass

    conn.close()
    return jsonify({"success": True, "email_envoye": email_envoye})


@app.route("/api/professeurs/<int:prof_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def professeurs_delete(prof_id: int):
    conn = _db()
    if not conn.execute("SELECT id FROM professeurs WHERE id=?", (prof_id,)).fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Professeur non trouvé"}), 404

    conn.execute("DELETE FROM professeur_modules WHERE id_professeur=?", (prof_id,))
    conn.execute("DELETE FROM professeurs WHERE id=?", (prof_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/auth/professeur-login", methods=["POST"])
@public
def auth_professeur_login():
    payload  = request.get_json(silent=True) or {}
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email et mot de passe requis"}), 400

    conn = _db()
    prof = conn.execute(
        "SELECT id, nom, prenom, email, password_hash, password_version FROM professeurs WHERE LOWER(email)=?",
        (email,),
    ).fetchone()

    if not prof:
        conn.close()
        return jsonify({"success": False, "error": COMPTE_INTROUVABLE}), 401
    if not _verify_password(password, prof["password_hash"], prof["password_version"]):
        conn.close()
        return jsonify({"success": False, "error": "Email ou mot de passe incorrect"}), 401

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE professeurs SET last_login=? WHERE id=?", (now, prof["id"]))
    if _needs_rehash(prof["password_hash"], prof["password_version"]):
        # Migration progressive SHA-256 → bcrypt
        conn.execute(
            "UPDATE professeurs SET password_hash=?, password_version='bcrypt' WHERE id=?",
            (_hash_password(password), prof["id"]),
        )
    mods = _prof_modules(conn, prof["id"])
    conn.commit()
    conn.close()

    return jsonify({
        "success":    True,
        "token":      create_token("professeur", email=prof["email"], id_professeur=prof["id"]),
        "professeur": {
            "id":      prof["id"],
            "nom":     prof["nom"],
            "prenom":  prof["prenom"],
            "email":   prof["email"],
            "modules": mods,
        },
    })


# ── Routes — Imports (backend/api/imports/) ───────────────────────────────────

app.add_url_rule("/api/etudiants/import-csv", view_func=import_etudiants_csv, methods=["POST"])
app.add_url_rule("/api/import-absences-csv",  view_func=import_absences_csv,  methods=["POST"])
app.add_url_rule("/api/import-planning",      view_func=import_planning_route, methods=["POST"])
app.add_url_rule("/api/import-notes/preview", view_func=import_notes_preview, methods=["POST"])
app.add_url_rule("/api/import-notes",         view_func=import_notes_route,   methods=["POST"])
app.add_url_rule("/api/import-modules",       view_func=import_modules_route, methods=["POST"])


verifier_protection(app)  # aucun endpoint /api/ sans @require_auth ni @public


if __name__ == "__main__":
    print(f"[api] Base SQLite : {DB_PATH}")
    print(f"[api] Base présente : {DB_PATH.exists()}")
    print("[api] Démarrage sur http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
