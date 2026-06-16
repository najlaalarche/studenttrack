import dataclasses
import hashlib
import io
import json
import os
import sqlite3
import unicodedata
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
load_dotenv(ROOT / ".env")

import sys
sys.path.insert(0, str(ROOT))

from backend.ingestion.reader import load_absences_df, detect_delta
from backend.analysis.engine import calculer_profils, filtrer_alertes, upsert_alertes
from backend.agent.ia_agent import (
    traiter_alertes, envoyer_alerte_auto,
    _html_avertissement as html_avertissement,
    _html_exclusion     as html_exclusion,
)
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
    if isinstance(obj, float) and obj != obj: return None
    return obj


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list): return [_serialize(i) for i in obj]
    if isinstance(obj, dict): return {k: _serialize(v) for k, v in obj.items()}
    return _to_python(obj)


def _gen_email(prenom: str, nom: str) -> str:
    def clean(s):
        s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
        return s.lower().strip().replace(" ", "-")
    return f"{clean(prenom)}.{clean(nom)}@esith.net"


import re as _re

def _find_filiere_for_csv(conn, session_programme: str, cursus: str):
    """Déduit id_filiere depuis SessionProgramme/Cursus du CSV Konosys. Retourne int ou None."""
    def _norm(s):
        return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()

    sp  = (session_programme or "").strip()
    cur = (cursus or "").strip()

    # 1. Étudiant existant avec même session_programme → réutilise son id_filiere
    if sp and _norm(sp) != "nan":
        row = conn.execute(
            "SELECT id_filiere FROM etudiants"
            " WHERE session_programme=? AND id_filiere IS NOT NULL LIMIT 1",
            (sp,),
        ).fetchone()
        if row:
            return int(row[0])

    # 2. Extraire le code groupe : depuis Cursus (S3-BDM2G2 → BDM2G2) ou premier token du SP
    group_code = ""
    if cur and _norm(cur) != "nan" and "-" in cur:
        group_code = cur.split("-", 1)[1]          # BDM2G2
    elif sp and _norm(sp) != "nan" and sp.split():
        group_code = sp.split()[0]                  # BDM2G2

    if not group_code:
        return None

    # 3. Correspondance directe sur code filière
    row = conn.execute(
        "SELECT id FROM filieres WHERE UPPER(code)=UPPER(?)", (group_code,)
    ).fetchone()
    if row:
        return int(row[0])

    # 4. Préfixe alpha (BDM2G2 → BDM, IMS2G1 → IMS, EO2G2_B → EO)
    m = _re.match(r"^([A-Za-z]+(?:-[A-Za-z]+)*)", group_code)
    if not m:
        return None
    prefix = m.group(1).upper()

    # Détecter le niveau dans SessionProgramme (1 ou 2)
    niveau_num = None
    m_niv = _re.search(r"\b([12])[eè]", _norm(sp))
    if m_niv:
        niveau_num = m_niv.group(1)

    candidates = conn.execute(
        "SELECT id, code, niveau FROM filieres"
        " WHERE UPPER(code) LIKE ? OR UPPER(code) LIKE ? OR UPPER(code)=?",
        (f"%{prefix}%", f"GI-{prefix}%", prefix),
    ).fetchall()

    if not candidates:
        return None
    if len(candidates) == 1:
        return int(candidates[0][0])

    # Filtrer par niveau si détecté
    if niveau_num:
        filtered = [c for c in candidates if c[2] and c[2].startswith(niveau_num)]
        if filtered:
            return int(min(filtered, key=lambda c: len(c[1]))[0])

    # Prendre la filière au code le plus court (code de base)
    return int(min(candidates, key=lambda c: len(c[1]))[0])


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
    return {"success": True, "etudiant": {
        "id_etudiant": str(et_row["id"]),
        "nom":    et_row["nom"],
        "prenom": et_row["prenom"],
        "email":  et_row["email"],
        "filiere": et_row["code_filiere"] or "",
        "annee":   et_row["annee"] or "",
    }}


# ── Routes — Stats / Profils ──────────────────────────────────────────────────

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

    return jsonify({"profil": _serialize(profil), "absences": absences, "notes": [], "scoring": {}})


# ── Routes — Alertes (historique, lecture seule) ──────────────────────────────

@app.route("/api/alertes")
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


# ── Routes — Import CSV absences ──────────────────────────────────────────────

@app.route("/api/import-absences-csv", methods=["POST"])
def import_absences_csv():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400
    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "Fichier vide"}), 400

    # Lecture CSV/Excel
    try:
        fname = uploaded.filename.lower()
        if fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded)
        else:
            raw = uploaded.read().decode("utf-8-sig", errors="replace")
            df = None
            for sep in [";", ",", "\t"]:
                try:
                    tmp = pd.read_csv(io.StringIO(raw), sep=sep)
                    if len(tmp.columns) >= 5:
                        df = tmp
                        break
                except Exception:
                    continue
            if df is None:
                df = pd.read_csv(io.StringIO(raw))
    except Exception as e:
        return jsonify({"error": f"Erreur lecture fichier : {e}"}), 400

    df.columns = [str(c).strip() for c in df.columns]

    stats = {
        "lignes_traitees": 0,
        "absences_ajoutees": 0,
        "doublons_ignores": 0,
        "etudiants_crees_auto": [],                  # [{prenom, nom}]
        "etudiants_non_crees_filiere_inconnue": [],  # [{id_inscr, session_programme}]
        "modules_crees": [],
        "alertes_declenchees": 0,
        "emails_envoyes": 0,
    }

    conn = _db()
    etudiants_modules_touches: set = set()

    for _, row in df.iterrows():
        stats["lignes_traitees"] += 1

        id_absence = str(row.get("id_absence", "")).strip()
        if not id_absence or id_absence == "nan":
            id_absence = ""

        id_inscr = str(row.get("id_inscriptionsessionprogramme", "")).strip()
        if not id_inscr or id_inscr == "nan":
            continue

        et = conn.execute(
            "SELECT id, id_filiere FROM etudiants WHERE id_inscriptionsessionprogramme=?",
            (id_inscr,),
        ).fetchone()
        if not et:
            nom_csv    = str(row.get("Nom",    "")).strip()
            prenom_csv = str(row.get("Prenom", "")).strip()
            sp_csv     = str(row.get("SessionProgramme", "")).strip()
            cursus_csv = str(row.get("Cursus", "")).strip()

            id_filiere_auto = _find_filiere_for_csv(conn, sp_csv, cursus_csv)

            if not nom_csv or not prenom_csv or id_filiere_auto is None:
                if not any(x["id_inscr"] == id_inscr for x in stats["etudiants_non_crees_filiere_inconnue"]):
                    stats["etudiants_non_crees_filiere_inconnue"].append({
                        "id_inscr": id_inscr,
                        "session_programme": sp_csv,
                    })
                continue

            email_auto = _gen_email(prenom_csv, nom_csv)
            cur_ins = conn.execute(
                "INSERT INTO etudiants"
                " (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, session_programme, cursus)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id_inscr, nom_csv, prenom_csv, email_auto,
                 id_filiere_auto, sp_csv or None, cursus_csv or None),
            )
            conn.commit()
            et = conn.execute(
                "SELECT id, id_filiere FROM etudiants WHERE id=?", (cur_ins.lastrowid,)
            ).fetchone()
            if not any(x["prenom"] == prenom_csv and x["nom"] == nom_csv
                       for x in stats["etudiants_crees_auto"]):
                stats["etudiants_crees_auto"].append({"prenom": prenom_csv, "nom": nom_csv})

        id_etudiant = int(et[0])
        id_filiere  = et[1]

        # Doublon check par (id_absence_konosys, id_etudiant) — clé composée obligatoire
        # car Konosys réutilise les mêmes IDs séquentiels par export (pas globalement uniques)
        if id_absence:
            if conn.execute(
                "SELECT id FROM absences WHERE id_absence_konosys=? AND id_etudiant=?",
                (id_absence, id_etudiant),
            ).fetchone():
                stats["doublons_ignores"] += 1
                continue

        module_nom = str(row.get("Module", "")).strip()
        if not module_nom or module_nom == "nan":
            continue

        mod = conn.execute(
            "SELECT id FROM modules WHERE nom=? AND (id_filiere=? OR id_filiere IS NULL) LIMIT 1",
            (module_nom, id_filiere),
        ).fetchone() or conn.execute(
            "SELECT id FROM modules WHERE nom=? LIMIT 1", (module_nom,)
        ).fetchone()

        if mod:
            id_module = int(mod[0])
        else:
            cur = conn.execute(
                "INSERT INTO modules (nom, id_filiere, semestre, volume_heures) VALUES (?, ?, 'S0', 48)",
                (module_nom, id_filiere),
            )
            id_module = cur.lastrowid
            if module_nom not in stats["modules_crees"]:
                stats["modules_crees"].append(module_nom)

        # Parse date
        try:
            d = pd.to_datetime(str(row.get("DATE", "")), dayfirst=False, errors="coerce")
            date_str = d.strftime("%Y-%m-%d") if not pd.isnull(d) else str(row.get("DATE", ""))
        except Exception:
            date_str = str(row.get("DATE", ""))

        # Parse durée
        try:
            duree = float(str(row.get("DureeDecimal", row.get("Duree", "0"))).replace(",", ".").strip())
        except Exception:
            duree = 0.0

        excuse_val = str(row.get("Excuse", "Non")).strip().lower()
        justifiee  = excuse_val in ("oui", "yes", "true", "1", "o")

        seance = str(row.get("Seance", "")).strip()
        heure  = str(row.get("Heure",  "")).strip()
        motif  = str(row.get("Motif",  "")).strip()

        conn.execute(
            "INSERT INTO absences"
            " (id_absence_konosys, id_etudiant, id_module, module_nom, date_absence,"
            "  seance, heure, duree_heures, justifiee, motif)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id_absence or None, id_etudiant, id_module, module_nom, date_str,
             seance, heure, duree, justifiee, motif),
        )
        stats["absences_ajoutees"] += 1
        etudiants_modules_touches.add((id_etudiant, id_module))

    conn.commit()

    # Recalcul taux + envoi automatique
    for id_etudiant, id_module in etudiants_modules_touches:
        tr = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN NOT justifiee THEN duree_heures ELSE 0.0 END), 0),
                COALESCE(SUM(duree_heures), 0),
                COALESCE(MAX(m.volume_heures), 48)
            FROM absences a
            LEFT JOIN modules m ON a.id_module = m.id
            WHERE a.id_etudiant=? AND a.id_module=?
        """, (id_etudiant, id_module)).fetchone()

        heures_nj    = float(tr[0])
        heures_total = float(tr[1])
        volume       = max(int(tr[2]), 1)
        taux_nj      = round(heures_nj    / volume * 100, 2)
        taux_total   = round(heures_total / volume * 100, 2)

        if taux_total >= 50:
            statut = "EXCLU"
        elif taux_nj >= 20:
            statut = "AVERTI"
        else:
            statut = "AUTORISE"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO alertes (id_etudiant, id_module, statut, taux_nj, taux_total, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_etudiant, id_module) DO UPDATE SET
                statut=excluded.statut, taux_nj=excluded.taux_nj,
                taux_total=excluded.taux_total, updated_at=excluded.updated_at
        """, (id_etudiant, id_module, statut, taux_nj, taux_total, now))
        conn.commit()

        if statut in ("AVERTI", "EXCLU"):
            stats["alertes_declenchees"] += 1
            results = envoyer_alerte_auto(id_etudiant, id_module, conn)
            stats["emails_envoyes"] += sum(1 for r in results if r.get("sent"))

    conn.close()
    _cache["data"] = None
    return jsonify(stats)


# ── Routes — Gestion étudiants ────────────────────────────────────────────────

@app.route("/api/sessions-programme")
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

    cur = conn.execute(
        "INSERT INTO etudiants (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, cursus, session_programme)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (id_inscr or None, nom, prenom, email, id_filiere, cursus or None, session_prog or None),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    _cache["data"] = None
    return jsonify({"success": True, "etudiant": {"id": new_id, "nom": nom, "prenom": prenom, "email": email}})


@app.route("/api/etudiants/<int:et_id>", methods=["PUT"])
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
    vals.append(et_id)

    conn.execute(f"UPDATE etudiants SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()
    _cache["data"] = None
    return jsonify({"success": True})


@app.route("/api/etudiants/<int:et_id>", methods=["DELETE"])
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
def filieres():
    df_abs, profils = _get_data()
    if df_abs is None:
        return jsonify({"erreur": "Base SQLite vide ou introuvable"}), 404
    return jsonify(sorted(df_abs["filiere"].dropna().unique().tolist()))


@app.route("/api/filieres-par-module/<nom_module>")
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
        "filieres":   sorted(set(r["code"]   for r in rows if r["code"])),
        "promotions": sorted(set(r["niveau"]  for r in rows if r["niveau"])),
    })


# ── Routes — Auth ─────────────────────────────────────────────────────────────

@app.route("/api/auth/check-email", methods=["POST"])
def auth_check_email():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email requis"}), 400
    return jsonify(_check_email_db(email))


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    payload  = request.get_json(silent=True) or {}
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
    payload  = request.get_json(silent=True) or {}
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    if not email or not password:
        return jsonify({"success": False, "error": "email et mot de passe requis"}), 400
    result = _login_db(email, password)
    if not result["success"]:
        return jsonify(result), 401
    return jsonify(result)


@app.route("/api/auth/admin-login", methods=["POST"])
def auth_admin_login():
    payload  = request.get_json(silent=True) or {}
    password = payload.get("password", "")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_pw:
        return jsonify({"success": False, "error": "ADMIN_PASSWORD non configuré dans .env"}), 500
    if password == admin_pw:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401


# ── Routes — Sync ─────────────────────────────────────────────────────────────

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
        "changed":          bool(changed),
        "email_alerts":     email_alerts,
    })


@app.route("/api/alerts/history")
def alerts_history():
    student_id = request.args.get("student_id")
    return jsonify({"alerts": get_alert_history(student_id)})


if __name__ == "__main__":
    print(f"[api] Base SQLite : {DB_PATH}")
    print(f"[api] Base présente : {DB_PATH.exists()}")
    print("[api] Démarrage sur http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
