"""
Authentification JWT de l'API StudentTrack.

- create_token(role, ...) : JWT HS256 signé avec JWT_SECRET_KEY (.env), valide 8 h
- @require_auth           : exige "Authorization: Bearer <token>" valide → g.user, sinon 401
- @require_role(...)      : à placer sous @require_auth ; 403 si le rôle ne correspond pas
                            (l'admin passe toujours)
- @public                 : marque explicitement un endpoint sans authentification
- verifier_protection(app): au démarrage, refuse de lancer l'API si un endpoint /api/ n'est
                            ni @require_auth ni @public (évite d'oublier une route)
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

ALGO           = "HS256"
DUREE_VALIDITE = timedelta(hours=8)
ROLES          = {"etudiant", "professeur", "admin"}

_SECRET = os.environ.get("JWT_SECRET_KEY", "")
if not _SECRET:
    # Sans clé configurée, les tokens ne survivent pas à un redémarrage de l'API
    _SECRET = secrets.token_hex(32)
    print("[auth] ATTENTION : JWT_SECRET_KEY absent du .env — clé temporaire générée")


def create_token(role: str, email: str = "", id_etudiant: int | None = None,
                 id_professeur: int | None = None) -> str:
    if role not in ROLES:
        raise ValueError(f"rôle inconnu : {role}")
    now = datetime.now(timezone.utc)
    payload = {"role": role, "email": email, "iat": now, "exp": now + DUREE_VALIDITE}
    if id_etudiant is not None:
        payload["id_etudiant"] = int(id_etudiant)
    if id_professeur is not None:
        payload["id_professeur"] = int(id_professeur)
    return jwt.encode(payload, _SECRET, algorithm=ALGO)


def _erreur(message: str, code: int):
    return jsonify({"erreur": message, "error": message}), code


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":  # pré-vol CORS
            return f(*args, **kwargs)
        entete = request.headers.get("Authorization", "")
        if not entete.startswith("Bearer "):
            return _erreur("Authentification requise", 401)
        try:
            g.user = jwt.decode(entete[7:].strip(), _SECRET, algorithms=[ALGO])
        except jwt.ExpiredSignatureError:
            return _erreur("Session expirée, veuillez vous reconnecter", 401)
        except jwt.InvalidTokenError:
            return _erreur("Token invalide", 401)
        if g.user.get("role") not in ROLES:
            return _erreur("Token invalide", 401)
        return f(*args, **kwargs)
    wrapper._auth = "protege"
    return wrapper


def require_role(*roles: str):
    def decorateur(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = getattr(g, "user", {}).get("role")
            if role != "admin" and role not in roles:
                return _erreur("Accès refusé", 403)
            return f(*args, **kwargs)
        wrapper._auth = getattr(f, "_auth", None)
        return wrapper
    return decorateur


def public(f):
    f._auth = "public"
    return f


def acces_etudiant_refuse(id_etudiant) -> bool:
    """Un étudiant ne peut consulter que ses propres données ; professeur et admin : tout."""
    user = getattr(g, "user", {})
    return user.get("role") == "etudiant" and str(user.get("id_etudiant")) != str(id_etudiant)


def verifier_protection(app):
    oublis = sorted(
        rule.rule for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/")
        and getattr(app.view_functions[rule.endpoint], "_auth", None) not in ("protege", "public")
    )
    if oublis:
        raise RuntimeError(f"Endpoints sans @require_auth ni @public : {', '.join(oublis)}")
