import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class DecisionIA:
    doit_alerter: bool
    action: str
    destinataire: str       # "etudiant" | "etudiant+administration"
    email_sujet: str
    email_corps: str
    explication: str
    genere_le: str


def _mock_decision(profil) -> DecisionIA:
    """Mode simulation sans clé API."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    action = profil.action_recommandee

    if action == "NOTIFY_EXCLUSION":
        modules_exclu = [m for m in profil.modules if m.statut_exam == "EXCLU"]
        mod = modules_exclu[0] if modules_exclu else None
        mod_nom = mod.module if mod else "Inconnu"
        taux = f"{mod.taux_total:.1f}" if mod else "??"

        sujet = f"Exclusion d'examen — {mod_nom} — ESITH Casablanca"
        corps = (
            f"Madame, Monsieur {profil.prenom} {profil.nom},\n\n"
            f"Nous vous informons que votre taux d'absences total (justifiées et non\n"
            f"justifiées) dans le module {mod_nom} a atteint {taux}%.\n\n"
            f"Conformément au règlement de l'ESITH, ayant manqué plus de 50% du volume\n"
            f"horaire de ce module, vous ne pouvez pas vous présenter à l'examen.\n\n"
            f"Cette décision est définitive.\n\n"
            f"Cordialement,\n"
            f"Service de la Scolarité — ESITH Casablanca — StudentTrack"
        )
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant+administration",
            email_sujet=sujet,
            email_corps=corps,
            explication=f"Taux total {taux}% >= 50% dans {mod_nom}",
            genere_le=now,
        )

    if action == "WARN_STUDENT":
        modules_avert = [m for m in profil.modules if m.statut_exam == "AVERTI"]
        mod = modules_avert[0] if modules_avert else None
        mod_nom = mod.module if mod else "Inconnu"
        taux = f"{mod.taux_nj:.1f}" if mod else "??"

        sujet = f"Avertissement absences — {mod_nom} — ESITH Casablanca"
        corps = (
            f"Madame, Monsieur {profil.prenom} {profil.nom},\n\n"
            f"Nous vous informons que votre taux d'absences non justifiées dans le module\n"
            f"{mod_nom} a atteint {taux}% (seuil d'avertissement : 20%).\n\n"
            f"Si cette situation n'est pas régularisée, vous risquez de ne plus pouvoir\n"
            f"passer l'examen de ce module.\n\n"
            f"Nous vous invitons à contacter le service de la scolarité.\n\n"
            f"Cordialement,\n"
            f"Service de la Scolarité — ESITH Casablanca — StudentTrack"
        )
        return DecisionIA(
            doit_alerter=True,
            action=action,
            destinataire="etudiant",
            email_sujet=sujet,
            email_corps=corps,
            explication=f"Taux NJ {taux}% >= 20% dans {mod_nom}",
            genere_le=now,
        )

    return DecisionIA(
        doit_alerter=False,
        action="AUCUNE",
        destinataire="",
        email_sujet="",
        email_corps="",
        explication="Aucun seuil atteint",
        genere_le=now,
    )


def _decision_via_api(profil, client) -> DecisionIA:
    """Appel réel à Claude pour générer la décision et l'email."""
    import json

    modules_resume = [
        {
            "module": m.module,
            "statut": m.statut_exam,
            "taux_nj": m.taux_nj,
            "taux_total": m.taux_total,
        }
        for m in profil.modules
    ]

    prompt = f"""Tu es le système StudentTrack de l'ESITH Casablanca.

Voici le profil d'un étudiant :
- Nom : {profil.prenom} {profil.nom}
- Email : {profil.email}
- Score risque : {profil.score_risque}/100 ({profil.niveau_risque})
- Modules : {json.dumps(modules_resume, ensure_ascii=False)}
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
    # Extraire le JSON si entouré de backticks
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return DecisionIA(genere_le=now, **{k: data[k] for k in DecisionIA.__dataclass_fields__ if k != "genere_le"})


def analyser_et_rediger(profil) -> DecisionIA:
    """Analyse le profil et génère la décision (IA ou simulation)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            return _decision_via_api(profil, client)
        except Exception as e:
            print(f"[ia_agent] Erreur API Claude : {e} — bascule en simulation")

    return _mock_decision(profil)


def traiter_alertes(profils: list) -> list[dict]:
    """Traite tous les profils en alerte et retourne les décisions."""
    results = []
    for profil in profils:
        if profil.action_recommandee != "AUCUNE":
            decision = analyser_et_rediger(profil)
            results.append({"profil": profil, "decision": decision})
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))

    from backend.analysis.engine import ProfilEtudiant, StatutModule, calculer_profils, filtrer_alertes
    import pandas as pd

    # Données fictives
    data = {
        "id_etudiant": ["1", "1", "2"],
        "nom": ["Dupont", "Dupont", "Martin"],
        "prenom": ["Alice", "Alice", "Bob"],
        "email": ["alice.dupont@esith.net"] * 2 + ["bob.martin@esith.net"],
        "semestre": ["S1"] * 3,
        "cursus": ["S1-Génie Textile"] * 3,
        "module": ["Anglais", "Anglais", "Physique E1"],
        "justifiee": [False, False, False],
        "duree_heures": [8.0, 9.0, 25.0],
        "date_absence": pd.to_datetime(["2026-01-10", "2026-01-17", "2026-01-24"]),
    }
    df = pd.DataFrame(data)

    profils = calculer_profils(df)
    alertes = filtrer_alertes(profils)

    print(f"[ia_agent] {len(alertes)} étudiant(s) en alerte")
    resultats = traiter_alertes(alertes)
    for r in resultats:
        d = r["decision"]
        p = r["profil"]
        print(f"\n--- {p.prenom} {p.nom} ---")
        print(f"Action      : {d.action}")
        print(f"Destinataire: {d.destinataire}")
        print(f"Sujet       : {d.email_sujet}")
        print(f"Explication : {d.explication}")
        print(f"Corps :\n{d.email_corps}")
