"""Helpers partagés entre app.py et les routes d'import (backend/api/imports/)."""
import os
import secrets
import sqlite3
import string
import tempfile
import unicodedata
from pathlib import Path

import bcrypt
from flask import jsonify, request

ROOT    = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "studenttrack.db"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Cache mémoire des profils (df_abs, profils) — mettre CACHE["data"] = None après un import
CACHE: dict = {"data": None}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """Hache en bcrypt (sel intégré). Stocker avec password_version='bcrypt'."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def gen_email(prenom: str, nom: str) -> str:
    def clean(s):
        s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
        return s.lower().strip().replace(" ", "-")
    return f"{clean(prenom)}.{clean(nom)}@esith.net"


def gen_mot_de_passe(longueur: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(longueur))


def cle_colonne(h) -> str:
    h = unicodedata.normalize("NFD", str(h)).encode("ascii", "ignore").decode()
    return h.strip().lower()


def html_credentials(prenom: str, nom: str, email: str, mot_de_passe: str, reset: bool = False,
                     role: str = "Professeur", temporaire: bool = False) -> str:
    conseil = ("Ce mot de passe est <strong>temporaire</strong> : vous devrez en choisir un nouveau"
               " à votre première connexion." if temporaire
               else "Nous vous recommandons de conserver ce mot de passe en lieu sûr.")
    titre  = "Réinitialisation de mot de passe" if reset else "Bienvenue sur StudentTrack"
    intro  = "Votre mot de passe StudentTrack a été réinitialisé." if reset else (
        "Un compte StudentTrack a été créé pour vous."
    )
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
  <h2 style="color:#1a3a6b">{titre}</h2>
  <p>Madame/Monsieur <strong>{prenom} {nom}</strong>,</p>
  <p>{intro} Voici vos identifiants de connexion :</p>
  <p style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:16px 20px;margin:20px 0">
    <strong>Email :</strong> {email}<br>
    <strong>Mot de passe :</strong> <code style="font-size:14px">{mot_de_passe}</code>
  </p>
  <p>Connectez-vous sur la plateforme en choisissant le rôle <strong>{role}</strong>
  et en saisissant ces identifiants.</p>
  <p style="margin:24px 0">
    <a href="{FRONTEND_URL}/"
       style="background:#8DC63F;color:#fff;padding:12px 24px;text-decoration:none;
              border-radius:6px;display:inline-block;font-weight:700">
      {"Se connecter" if reset else "Première connexion"}
    </a>
  </p>
  <p style="color:#64748b;font-size:12px">{conseil}</p>
  <hr style="border:none;border-top:1px solid #E2E8F0;margin:24px 0">
  <p style="color:#94a3b8;font-size:11px">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>
</div>"""


# ── Fichiers uploadés ─────────────────────────────────────────────────────────

def traiter_fichier_excel(traitement, extensions=(".xlsx", ".xlsb")):
    """Sauve le fichier uploadé (champ 'file') dans un fichier temporaire et applique
    traitement(path, nom_original). Retourne (résultat, None) ou (None, réponse d'erreur)."""
    if "file" not in request.files:
        return None, (jsonify({"error": "Aucun fichier fourni"}), 400)
    uploaded = request.files["file"]
    ext = Path(uploaded.filename or "").suffix.lower()
    if ext not in extensions:
        formats = " ou ".join(extensions)
        return None, (jsonify({"error": f"Format non supporté — utilisez un fichier {formats}"}), 400)

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        uploaded.save(tmp)
        tmp.close()
        return traitement(tmp.name, uploaded.filename), None
    except Exception as e:
        return None, (jsonify({"error": f"Fichier illisible : {e}"}), 400)
    finally:
        tmp.close()
        os.unlink(tmp.name)


def traiter_fichier_xlsx(traitement):
    """.xlsx uniquement."""
    return traiter_fichier_excel(traitement, extensions=(".xlsx",))
