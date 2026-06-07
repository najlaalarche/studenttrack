import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

EMAILS_LOG_FILE = ROOT / "data" / "emails_log.json"

BREVO_API_KEY     = os.environ.get("BREVO_API_KEY", "")
EMAIL_SENDER      = os.environ.get("EMAIL_SENDER", "")
EMAIL_SENDER_NAME = os.environ.get("EMAIL_SENDER_NAME", "StudentTrack ESITH")
EMAIL_ADMIN       = os.environ.get("EMAIL_ADMIN", "")


@dataclass
class DecisionIA:
    doit_alerter: bool
    action: str
    destinataire: str       # "etudiant" | "etudiant+administration"
    email_sujet: str
    email_corps: str
    explication: str
    genere_le: str


# ─── Emails log (anti-doublon) ──────────────────────────────────────────────

def _load_emails_log() -> dict:
    if not EMAILS_LOG_FILE.exists():
        return {}
    return json.loads(EMAILS_LOG_FILE.read_text(encoding="utf-8"))


def _save_emails_log(data: dict):
    EMAILS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAILS_LOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Envoi email via Brevo ───────────────────────────────────────────────────

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
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=15,
        )
        if r.status_code in (200, 201):
            print(f"[send_email] OK -> {to_email} | {subject}")
            return True
        else:
            print(f"[send_email] Erreur {r.status_code} -> {r.text[:200]}")
            return False
    except Exception as e:
        print(f"[send_email] Exception : {e}")
        return False


def _html_avertissement(nom: str, prenom: str, module: str, taux_nj: float) -> str:
    return f"""<h2 style="color:#1a3a6b">Avertissement — Absences ESITH</h2>
<p>Madame/Monsieur <strong>{prenom} {nom}</strong>,</p>
<p>Votre taux d'absences non justifiées dans le module <strong>{module}</strong> a atteint <strong>{taux_nj:.1f}%</strong>.</p>
<p>Le seuil critique est fixé à <strong>50%</strong>. Merci de régulariser votre situation.</p>
<br>
<p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>"""


def _html_exclusion(nom: str, prenom: str, module: str, taux_total: float) -> str:
    return f"""<h2 style="color:#ef4444">Exclusion d'examen — ESITH Casablanca</h2>
<p>Madame/Monsieur <strong>{prenom} {nom}</strong>,</p>
<p>Votre taux d'absences total dans le module <strong>{module}</strong> a atteint <strong>{taux_total:.1f}%</strong>.</p>
<p>Conformément au règlement, vous ne pouvez pas passer l'examen de ce module.</p>
<br>
<p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>"""


# ─── Décision IA (mock ou API Claude) ───────────────────────────────────────

def _mock_decision(profil) -> DecisionIA:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    action = profil.action_recommandee

    if action == "NOTIFY_EXCLUSION":
        modules_exclu = [m for m in profil.modules if m.statut_exam == "EXCLU"]
        mod = modules_exclu[0] if modules_exclu else None
        mod_nom = mod.module if mod else "Inconnu"
        taux = f"{mod.taux_total:.1f}" if mod else "??"
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant+administration",
            email_sujet=f"Exclusion d'examen — {mod_nom} — ESITH Casablanca",
            email_corps=_html_exclusion(profil.nom, profil.prenom, mod_nom, mod.taux_total if mod else 0),
            explication=f"Taux total {taux}% >= 50% dans {mod_nom}",
            genere_le=now,
        )

    if action == "WARN_STUDENT":
        modules_avert = [m for m in profil.modules if m.statut_exam == "AVERTI"]
        mod = modules_avert[0] if modules_avert else None
        mod_nom = mod.module if mod else "Inconnu"
        taux = f"{mod.taux_nj:.1f}" if mod else "??"
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant",
            email_sujet=f"Avertissement absences — {mod_nom} — ESITH Casablanca",
            email_corps=_html_avertissement(profil.nom, profil.prenom, mod_nom, mod.taux_nj if mod else 0),
            explication=f"Taux NJ {taux}% >= 20% dans {mod_nom}",
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


# ─── Traitement des alertes avec envoi email ─────────────────────────────────

def traiter_alertes(profils: list) -> list[dict]:
    emails_log = _load_emails_log()
    results = []

    for profil in profils:
        if profil.action_recommandee == "AUCUNE":
            continue

        decision = analyser_et_rediger(profil)
        emails_sent = []

        for mod in profil.modules:
            # Clé anti-doublon
            key_avert = f"{profil.id_etudiant}_{mod.module}_avert"
            key_exclu  = f"{profil.id_etudiant}_{mod.module}_exclu"

            if mod.statut_exam == "AVERTI" and key_avert not in emails_log:
                html = _html_avertissement(profil.nom, profil.prenom, mod.module, mod.taux_nj)
                sujet = f"Avertissement absences — {mod.module} — ESITH Casablanca"
                sent = send_email(profil.email, sujet, html)
                if sent:
                    emails_log[key_avert] = {
                        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "email": profil.email,
                        "taux_nj": mod.taux_nj,
                    }
                    emails_sent.append({"type": "avert", "module": mod.module, "sent": True})
                else:
                    emails_sent.append({"type": "avert", "module": mod.module, "sent": False})

            elif mod.statut_exam == "AVERTI" and key_avert in emails_log:
                print(f"[traiter_alertes] Email déjà envoyé pour {profil.email} / {mod.module} (avert)")

            if mod.statut_exam == "EXCLU" and key_exclu not in emails_log:
                html = _html_exclusion(profil.nom, profil.prenom, mod.module, mod.taux_total)
                sujet = f"Exclusion d'examen — {mod.module} — ESITH Casablanca"
                sent = send_email(profil.email, sujet, html)
                if sent:
                    emails_log[key_exclu] = {
                        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "email": profil.email,
                        "taux_total": mod.taux_total,
                    }
                    emails_sent.append({"type": "exclu", "module": mod.module, "sent": True})
                else:
                    emails_sent.append({"type": "exclu", "module": mod.module, "sent": False})

            elif mod.statut_exam == "EXCLU" and key_exclu in emails_log:
                print(f"[traiter_alertes] Email déjà envoyé pour {profil.email} / {mod.module} (exclu)")

        results.append({"profil": profil, "decision": decision, "emails_sent": emails_sent})

    _save_emails_log(emails_log)
    return results


# ─── Point d'entrée direct ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))

    from backend.ingestion.reader import load_dataset
    from backend.analysis.engine import calculer_profils

    dataset_path = ROOT / "data" / "dataset.xlsx"
    if not dataset_path.exists():
        print(f"[ia_agent] dataset.xlsx introuvable dans {dataset_path}")
        sys.exit(1)

    print("[ia_agent] Chargement du dataset…")
    df_abs, df_notes, df_etudiants, df_scoring = load_dataset(dataset_path)
    profils = calculer_profils(df_abs, df_notes, df_etudiants, df_scoring)

    # Filtrer les étudiants avec une action à effectuer (pas uniquement par score)
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
                print(f"    [{mod.statut_exam}] {mod.module} — NJ:{mod.nb_abs_nj}/{mod.total_seances} ({mod.taux_nj:.1f}%)")
        for e in r.get("emails_sent", []):
            status = "envoyé" if e["sent"] else "ECHEC"
            print(f"    Email {e['type'].upper()} -> {status}")
