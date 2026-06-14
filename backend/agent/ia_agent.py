import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "studenttrack.db"
EMAILS_LOG_FILE = ROOT / "data" / "emails_log.json"  # kept as fallback
load_dotenv(ROOT / ".env")

BREVO_API_KEY     = os.environ.get("BREVO_API_KEY", "")
EMAIL_SENDER      = os.environ.get("EMAIL_SENDER", "")
EMAIL_SENDER_NAME = os.environ.get("EMAIL_SENDER_NAME", "StudentTrack ESITH")
EMAIL_ADMIN       = os.environ.get("EMAIL_ADMIN", "")


@dataclass
class DecisionIA:
    doit_alerter: bool
    action: str
    destinataire: str
    email_sujet: str
    email_corps: str
    explication: str
    genere_le: str


# ── JSON emails log (anti-doublon fallback) ───────────────────────────────────

def _load_emails_log() -> dict:
    if not EMAILS_LOG_FILE.exists():
        return {}
    return json.loads(EMAILS_LOG_FILE.read_text(encoding="utf-8"))


def _save_emails_log(data: dict):
    EMAILS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAILS_LOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_alerte_id(conn: sqlite3.Connection, id_etudiant: str, id_module: int) -> int | None:
    try:
        id_et = int(id_etudiant)
    except (ValueError, TypeError):
        return None
    row = conn.execute(
        "SELECT id FROM alertes WHERE id_etudiant = ? AND id_module = ?",
        (id_et, id_module),
    ).fetchone()
    return row[0] if row else None


def _log_email_to_db(conn: sqlite3.Connection, alerte_id: int | None, destinataire: str,
                     sujet: str, type_email: str, envoye: bool):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO emails_log (id_alerte, destinataire, sujet, type_email, envoye, envoye_le)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (alerte_id, destinataire, sujet, type_email, envoye, now if envoye else None),
    )


def _update_alerte_flags(conn: sqlite3.Connection, alerte_id: int, type_email: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if type_email == "avert":
        conn.execute(
            "UPDATE alertes SET avert_envoye = 1, updated_at = ? WHERE id = ?", (now, alerte_id)
        )
    elif type_email == "exclu":
        conn.execute(
            "UPDATE alertes SET exclu_envoye = 1, updated_at = ? WHERE id = ?", (now, alerte_id)
        )


# ── Envoi Brevo ───────────────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, body_html: str) -> bool:
    import requests

    if not BREVO_API_KEY:
        print("[send_email] BREVO_API_KEY manquant — email non envoyé")
        return False

    payload = {
        "sender": {"name": EMAIL_SENDER_NAME, "email": EMAIL_SENDER},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": body_html,
    }
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            print(f"[send_email] OK -> {to_email} | {subject}")
            return True
        print(f"[send_email] Erreur {r.status_code} -> {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[send_email] Exception : {e}")
        return False


def _html_avertissement(nom: str, prenom: str, module: str, taux_nj: float) -> str:
    return (
        f'<h2 style="color:#1a3a6b">Avertissement — Absences ESITH</h2>'
        f"<p>Madame/Monsieur <strong>{prenom} {nom}</strong>,</p>"
        f"<p>Votre taux d'absences non justifiées dans le module <strong>{module}</strong>"
        f" a atteint <strong>{taux_nj:.1f}%</strong>.</p>"
        f"<p>Le seuil critique est fixé à <strong>50%</strong>. Merci de régulariser votre situation.</p>"
        f'<br><p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>'
    )


def _html_exclusion(nom: str, prenom: str, module: str, taux_total: float) -> str:
    return (
        f'<h2 style="color:#ef4444">Exclusion d\'examen — ESITH Casablanca</h2>'
        f"<p>Madame/Monsieur <strong>{prenom} {nom}</strong>,</p>"
        f"<p>Votre taux d'absences total dans le module <strong>{module}</strong>"
        f" a atteint <strong>{taux_total:.1f}%</strong>.</p>"
        f"<p>Conformément au règlement, vous ne pouvez pas passer l'examen de ce module.</p>"
        f'<br><p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>'
    )


# ── Décision IA ───────────────────────────────────────────────────────────────

def _mock_decision(profil) -> DecisionIA:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    action = profil.action_recommandee

    if action == "NOTIFY_EXCLUSION":
        modules_exclu = [m for m in profil.modules if m.statut_exam == "EXCLU"]
        mod = modules_exclu[0] if modules_exclu else None
        mod_nom = mod.module if mod else "Inconnu"
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant+administration",
            email_sujet=f"Exclusion d'examen — {mod_nom} — ESITH Casablanca",
            email_corps=_html_exclusion(profil.nom, profil.prenom, mod_nom, mod.taux_total if mod else 0),
            explication=f"Taux total {mod.taux_total:.1f}% >= 50% dans {mod_nom}" if mod else "",
            genere_le=now,
        )

    if action == "WARN_STUDENT":
        modules_avert = [m for m in profil.modules if m.statut_exam == "AVERTI"]
        mod = modules_avert[0] if modules_avert else None
        mod_nom = mod.module if mod else "Inconnu"
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant",
            email_sujet=f"Avertissement absences — {mod_nom} — ESITH Casablanca",
            email_corps=_html_avertissement(profil.nom, profil.prenom, mod_nom, mod.taux_nj if mod else 0),
            explication=f"Taux NJ {mod.taux_nj:.1f}% >= 20% dans {mod_nom}" if mod else "",
            genere_le=now,
        )

    return DecisionIA(
        doit_alerter=False, action="AUCUNE", destinataire="",
        email_sujet="", email_corps="",
        explication="Aucun seuil atteint", genere_le=now,
    )


def _decision_via_api(profil, client) -> DecisionIA:
    import json as _json

    modules_resume = [
        {"module": m.module, "statut": m.statut_exam, "taux_nj": m.taux_nj, "taux_total": m.taux_total}
        for m in profil.modules
    ]
    prompt = f"""Tu es le système StudentTrack de l'ESITH Casablanca.

Voici le profil d'un étudiant :
- Nom : {profil.prenom} {profil.nom}
- Email : {profil.email}
- Score risque : {profil.score_risque}/100 ({profil.niveau_risque})
- Modules : {_json.dumps(modules_resume, ensure_ascii=False)}
- Action recommandée : {profil.action_recommandee}

Génère une décision JSON avec exactement ces clés :
{{
  "doit_alerter": true/false,
  "action": "NOTIFY_EXCLUSION" | "WARN_STUDENT" | "AUCUNE",
  "destinataire": "etudiant" | "etudiant+administration",
  "email_sujet": "...",
  "email_corps": "...",
  "explication": "..."
}}

Rédige l'email en français, formel, au nom du Service de la Scolarité — ESITH Casablanca.
Réponds uniquement avec le JSON, sans aucun texte autour."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = _json.loads(raw)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return DecisionIA(genere_le=now, **{k: data[k] for k in DecisionIA.__dataclass_fields__ if k != "genere_le"})


def analyser_et_rediger(profil) -> DecisionIA:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            return _decision_via_api(profil, client)
        except Exception as e:
            print(f"[ia_agent] Erreur API Claude : {e} — bascule en simulation")
    return _mock_decision(profil)


# ── Envoi automatique (déclenché par import CSV) ──────────────────────────────

def envoyer_alerte_auto(id_etudiant: int, id_module: int, conn: sqlite3.Connection) -> list[dict]:
    """Envoie l'email si seuil franchi ET pas déjà envoyé. Sans validation humaine."""
    alerte = conn.execute(
        "SELECT id, statut, taux_nj, taux_total, avert_envoye, exclu_envoye"
        " FROM alertes WHERE id_etudiant=? AND id_module=?",
        (id_etudiant, id_module),
    ).fetchone()
    if not alerte:
        return []

    alerte_id    = alerte[0]
    statut       = alerte[1]
    taux_nj      = float(alerte[2] or 0)
    taux_total   = float(alerte[3] or 0)
    avert_envoye = bool(alerte[4])
    exclu_envoye = bool(alerte[5])

    et = conn.execute("SELECT nom, prenom, email FROM etudiants WHERE id=?", (id_etudiant,)).fetchone()
    if not et:
        return []
    nom, prenom, email_et = et[0], et[1], et[2]

    mod = conn.execute("SELECT nom FROM modules WHERE id=?", (id_module,)).fetchone()
    mod_nom = mod[0] if mod else "Module inconnu"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    if statut == "AVERTI" and not avert_envoye:
        html  = _html_avertissement(nom, prenom, mod_nom, taux_nj)
        sujet = f"Avertissement absences — {mod_nom} — ESITH Casablanca"
        sent  = send_email(email_et, sujet, html)
        if sent:
            conn.execute(
                "UPDATE alertes SET avert_envoye=1, updated_at=? WHERE id=?", (now, alerte_id)
            )
            _log_email_to_db(conn, alerte_id, email_et, sujet, "avert", True)
            conn.commit()
        results.append({"sent": sent, "type": "avert", "module": mod_nom})

    elif statut == "EXCLU" and not exclu_envoye:
        html  = _html_exclusion(nom, prenom, mod_nom, taux_total)
        sujet = f"Exclusion d'examen — {mod_nom} — ESITH Casablanca"
        sent_et = send_email(email_et, sujet, html)
        if sent_et:
            conn.execute(
                "UPDATE alertes SET exclu_envoye=1, updated_at=? WHERE id=?", (now, alerte_id)
            )
            _log_email_to_db(conn, alerte_id, email_et, sujet, "exclu", True)
        if EMAIL_ADMIN:
            sent_adm = send_email(EMAIL_ADMIN, sujet, html)
            if sent_adm:
                _log_email_to_db(conn, alerte_id, EMAIL_ADMIN, sujet, "exclu_admin", True)
        conn.commit()
        results.append({"sent": sent_et, "type": "exclu", "module": mod_nom})

    return results


# ── Traitement des alertes ────────────────────────────────────────────────────

def traiter_alertes(profils: list) -> list[dict]:
    emails_log = _load_emails_log()
    db_conn = sqlite3.connect(DB_PATH) if DB_PATH.exists() else None
    results = []

    for profil in profils:
        if profil.action_recommandee == "AUCUNE":
            continue

        decision = analyser_et_rediger(profil)
        emails_sent = []

        for mod in profil.modules:
            id_module = getattr(mod, "id_module", 0)
            alerte_id = _get_alerte_id(db_conn, profil.id_etudiant, id_module) if db_conn else None

            key_avert = f"{profil.id_etudiant}_{mod.module}_avert"
            key_exclu  = f"{profil.id_etudiant}_{mod.module}_exclu"

            if mod.statut_exam == "AVERTI" and key_avert not in emails_log:
                html  = _html_avertissement(profil.nom, profil.prenom, mod.module, mod.taux_nj)
                sujet = f"Avertissement absences — {mod.module} — ESITH Casablanca"
                sent  = send_email(profil.email, sujet, html)
                if sent:
                    emails_log[key_avert] = {
                        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "email": profil.email, "taux_nj": mod.taux_nj,
                    }
                    if db_conn:
                        _log_email_to_db(db_conn, alerte_id, profil.email, sujet, "avert", True)
                        if alerte_id:
                            _update_alerte_flags(db_conn, alerte_id, "avert")
                        db_conn.commit()
                emails_sent.append({"type": "avert", "module": mod.module, "sent": sent})

            elif mod.statut_exam == "AVERTI":
                print(f"[traiter_alertes] Email déjà envoyé pour {profil.email} / {mod.module} (avert)")

            if mod.statut_exam == "EXCLU" and key_exclu not in emails_log:
                html  = _html_exclusion(profil.nom, profil.prenom, mod.module, mod.taux_total)
                sujet = f"Exclusion d'examen — {mod.module} — ESITH Casablanca"
                sent  = send_email(profil.email, sujet, html)
                if sent:
                    emails_log[key_exclu] = {
                        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "email": profil.email, "taux_total": mod.taux_total,
                    }
                    if db_conn:
                        _log_email_to_db(db_conn, alerte_id, profil.email, sujet, "exclu", True)
                        if alerte_id:
                            _update_alerte_flags(db_conn, alerte_id, "exclu")
                        db_conn.commit()
                emails_sent.append({"type": "exclu", "module": mod.module, "sent": sent})

            elif mod.statut_exam == "EXCLU":
                print(f"[traiter_alertes] Email déjà envoyé pour {profil.email} / {mod.module} (exclu)")

        results.append({"profil": profil, "decision": decision, "emails_sent": emails_sent})

    _save_emails_log(emails_log)
    if db_conn:
        db_conn.close()
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))

    from backend.ingestion.reader import load_absences_df
    from backend.analysis.engine import calculer_profils

    if not DB_PATH.exists():
        print(f"[ia_agent] Base SQLite introuvable : {DB_PATH}")
        sys.exit(1)

    print("[ia_agent] Chargement depuis SQLite…")
    df_abs = load_absences_df()
    profils = calculer_profils(df_abs)

    en_alerte = [p for p in profils if p.action_recommandee != "AUCUNE"]
    print(f"[ia_agent] {len(en_alerte)} étudiant(s) nécessitent une action")

    resultats = traiter_alertes(en_alerte)
    print(f"\n[ia_agent] Résumé :")
    for r in resultats:
        p = r["profil"]
        d = r["decision"]
        print(f"  {p.prenom} {p.nom} ({p.email}) — {d.action}")
        for mod in p.modules:
            if mod.statut_exam != "AUTORISE":
                print(f"    [{mod.statut_exam}] {mod.module} — NJ:{mod.nb_abs_nj} ({mod.taux_nj:.1f}%)")
