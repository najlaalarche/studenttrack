import os
import sqlite3
from datetime import datetime
from pathlib import Path

from backend.services.email_service import send_email
from backend.agent.email_templates import (
    template_etudiant_20,
    template_etudiant_30,
    template_etudiant_50,
    template_chef_filiere_30,
    template_chef_filiere_50,
    template_direction_50,
)

ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT / "logs"
DB_PATH = LOGS_DIR / "alerts.db"

CHEF_EMAIL = os.environ.get("CHEF_EMAIL", "chef.filiere@esith.ma")
DIRECTION_EMAIL = os.environ.get("DIRECTION_EMAIL", "direction@esith.ma")


def init_alerts_db():
    """Crée la table alerts_log si elle n'existe pas."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                module TEXT,
                seuil INTEGER,
                destinataire TEXT,
                to_email TEXT,
                subject TEXT,
                status TEXT,
                error TEXT,
                sent_at TEXT
            )
            """
        )
        conn.commit()


def _db_connect():
    init_alerts_db()
    return sqlite3.connect(DB_PATH)


def has_alert_been_sent(student_id, module, seuil, destinataire) -> bool:
    """Retourne True si cet email a déjà été envoyé (anti-doublon strict)."""
    with _db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM alerts_log WHERE student_id=? AND module=? AND seuil=? AND destinataire=? AND status='sent' LIMIT 1",
            (student_id, module, seuil, destinataire),
        )
        return cursor.fetchone() is not None


def log_alert(student_id, module, seuil, destinataire, to_email, subject, status, error=None):
    """Enregistre l'alerte en DB (succès ou échec)."""
    sent_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _db_connect() as conn:
        conn.execute(
            "INSERT INTO alerts_log (student_id, module, seuil, destinataire, to_email, subject, status, error, sent_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, module, seuil, destinataire, to_email, subject, status, error, sent_at),
        )
        conn.commit()


def get_alert_history(student_id: str | None = None) -> list[dict]:
    """Retourne l'historique des alertes envoyées ou tentées."""
    with _db_connect() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if student_id:
            cursor.execute(
                "SELECT id, student_id, module, seuil, destinataire, to_email, subject, status, error, sent_at FROM alerts_log WHERE student_id=? ORDER BY sent_at DESC",
                (str(student_id),),
            )
        else:
            cursor.execute(
                "SELECT id, student_id, module, seuil, destinataire, to_email, subject, status, error, sent_at FROM alerts_log ORDER BY sent_at DESC"
            )
        return [dict(row) for row in cursor.fetchall()]


def _normalize_student(etudiant):
    if isinstance(etudiant, dict):
        return {
            "id_etudiant": str(etudiant.get("id_etudiant", "")),
            "prenom": str(etudiant.get("prenom", "")),
            "nom": str(etudiant.get("nom", "")),
            "email": str(etudiant.get("email", "")),
            "filiere": str(etudiant.get("filiere", "")),
            "score_global": etudiant.get("score_global", 0),
            "annee_scolaire": etudiant.get("annee_scolaire", "2024-2025"),
            "modules": etudiant.get("modules", []),
        }
    return {
        "id_etudiant": str(getattr(etudiant, "id_etudiant", "")),
        "prenom": str(getattr(etudiant, "prenom", "")),
        "nom": str(getattr(etudiant, "nom", "")),
        "email": str(getattr(etudiant, "email", "")),
        "filiere": str(getattr(etudiant, "filiere", "")),
        "score_global": getattr(etudiant, "score_global", 0),
        "annee_scolaire": getattr(etudiant, "annee", "2024-2025"),
        "modules": getattr(etudiant, "modules", []),
    }


def _extract_modules_en_alerte(student) -> list[dict]:
    modules = []
    for module in student.get("modules", []):
        if isinstance(module, dict):
            statut = module.get("statut_exam", "")
            nom = module.get("module") or module.get("nom")
            taux_nj = module.get("taux_nj", 0)
            taux_total = module.get("taux_total", 0)
        else:
            statut = getattr(module, "statut_exam", "")
            nom = getattr(module, "module", None)
            taux_nj = getattr(module, "taux_nj", 0)
            taux_total = getattr(module, "taux_total", 0)

        if statut in {"AVERTI", "EXCLU"} and nom:
            modules.append({"nom": nom, "taux_nj": float(taux_nj), "taux_total": float(taux_total)})
    return modules


def _build_template_data(student, module_name, taux, seuil):
    return {
        "student_name": f"{student.get('prenom', '')} {student.get('nom', '')}".strip(),
        "student_id": student.get("id_etudiant", ""),
        "filiere": student.get("filiere", ""),
        "module_name": module_name,
        "taux_absence": f"{taux}%",
        "seuil": f"{seuil}%",
        "score_global": student.get("score_global", 0),
        "date_alerte": datetime.now().strftime("%Y-%m-%d"),
        "annee_scolaire": student.get("annee_scolaire", "2024-2025"),
    }


def _select_template(destinataire: str, seuil: int):
    if destinataire == "etudiant" and seuil == 20:
        return template_etudiant_20
    if destinataire == "etudiant" and seuil == 30:
        return template_etudiant_30
    if destinataire == "etudiant" and seuil == 50:
        return template_etudiant_50
    if destinataire == "chef_filiere" and seuil == 30:
        return template_chef_filiere_30
    if destinataire == "chef_filiere" and seuil == 50:
        return template_chef_filiere_50
    if destinataire == "direction" and seuil == 50:
        return template_direction_50
    raise ValueError(f"Template inconnu pour destinataire={destinataire} seuil={seuil}")


def _send_single_alert(student, module_name, seuil, destinataire, to_email, taux) -> dict:
    template_fn = _select_template(destinataire, seuil)
    subject, html = template_fn(_build_template_data(student, module_name, taux, seuil))
    student_id = student.get("id_etudiant", "")

    if has_alert_been_sent(student_id, module_name, seuil, destinataire):
        log_alert(student_id, module_name, seuil, destinataire, to_email, subject, "failed", "doublon")
        return {
            "destinataire": destinataire,
            "seuil": seuil,
            "module": module_name,
            "sent": False,
            "reason": "doublon",
        }

    result = send_email(to_email, subject, html)
    status = "sent" if result["success"] else "failed"
    log_alert(student_id, module_name, seuil, destinataire, to_email, subject, status, result.get("error"))
    return {
        "destinataire": destinataire,
        "seuil": seuil,
        "module": module_name,
        "sent": result["success"],
        "reason": None if result["success"] else result.get("error"),
    }


def process_student_alerts(etudiant: dict, contacts: dict | None = None) -> list[dict]:
    """Analyse un profil étudiant et envoie les emails nécessaires."""
    student = _normalize_student(etudiant)
    contacts = contacts or {}
    chef_email = contacts.get("chef_email") or CHEF_EMAIL
    direction_email = contacts.get("direction_email") or DIRECTION_EMAIL
    student_email = student.get("email")

    results = []
    modules = _extract_modules_en_alerte(student)

    for module in modules:
        module_name = module["nom"]
        taux_nj = module["taux_nj"]
        taux_total = module["taux_total"]

        if taux_nj >= 20:
            results.append(_send_single_alert(student, module_name, 20, "etudiant", student_email, taux_nj))

        if taux_nj >= 30:
            results.append(_send_single_alert(student, module_name, 30, "etudiant", student_email, taux_nj))
            results.append(_send_single_alert(student, module_name, 30, "chef_filiere", chef_email, taux_nj))

        if taux_total >= 50:
            results.append(_send_single_alert(student, module_name, 50, "etudiant", student_email, taux_total))
            results.append(_send_single_alert(student, module_name, 50, "chef_filiere", chef_email, taux_total))
            results.append(_send_single_alert(student, module_name, 50, "direction", direction_email, taux_total))

    return results


if __name__ == "__main__":
    init_alerts_db()
    print(f"[email_agent] DB initialisée dans {DB_PATH}")
