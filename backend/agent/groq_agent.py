"""
Analyse automatique des statistiques par LLM via l'API Groq (compatible OpenAI).

  - GROQ_API_KEY : clé API Groq (.env) — https://console.groq.com/keys
  - GROQ_MODEL   : modèle (défaut openai/gpt-oss-20b ; llama-3.1-8b-instant n'est plus proposé par Groq)
"""
import json
import os

import requests

GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
TIMEOUT_S    = 30
MAX_DONNEES  = 8000     # caractères de JSON transmis au modèle

MSG_INDISPONIBLE = "Le service d'analyse IA n'est pas disponible pour le moment."

PROMPTS_SYSTEME = {
    "admin": (
        "Tu es un assistant pédagogique pour l'ESITH Casablanca. Analyse les données de suivi des "
        "absences et génère un résumé bienveillant et factuel en français (5-7 phrases max) à "
        "destination de l'administration. Identifie les points critiques et les tendances."
    ),
    "etudiant": (
        "Tu es un assistant pédagogique bienveillant. Analyse les données d'absence et de performance "
        "de cet étudiant et génère un message d'encouragement personnalisé en français (4-5 phrases) "
        "qui explique sa situation, l'alerte si nécessaire et le motive à s'améliorer."
    ),
}

CONSIGNES = (
    "Réponds uniquement par le texte demandé, sans titre ni liste à puces, "
    "et n'invente aucun chiffre absent des données."
)


class IAIndisponible(Exception):
    """Clé absente, Groq injoignable ou réponse inexploitable."""


def analyser(role: str, donnees: dict) -> str:
    if role not in PROMPTS_SYSTEME:
        raise ValueError(f"rôle inconnu : {role}")
    if not GROQ_API_KEY:
        print("[groq] GROQ_API_KEY manquant dans .env — analyse IA désactivée")
        raise IAIndisponible(MSG_INDISPONIBLE)

    contenu = json.dumps(donnees, ensure_ascii=False, indent=2)[:MAX_DONNEES]
    corps = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": PROMPTS_SYSTEME[role]},
            {"role": "user",   "content": f"Données (JSON) :\n{contenu}\n\n{CONSIGNES}"},
        ],
        "temperature": 0.3,
        "max_tokens":  800,
    }
    if "gpt-oss" in GROQ_MODEL:
        # modèle à raisonnement : limite la réflexion interne pour garder des tokens pour la réponse
        corps["reasoning_effort"] = "low"
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=corps,
            timeout=TIMEOUT_S,
        )
    except requests.RequestException as exc:  # réseau coupé, timeout…
        print(f"[groq] injoignable : {exc}")
        raise IAIndisponible(MSG_INDISPONIBLE) from exc

    if r.status_code != 200:  # 401 clé invalide, 429 quota, 5xx…
        print(f"[groq] HTTP {r.status_code} : {r.text[:200]}")
        raise IAIndisponible(MSG_INDISPONIBLE)

    try:
        texte = (r.json()["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        texte = ""
    if not texte:
        raise IAIndisponible(MSG_INDISPONIBLE)
    return texte
