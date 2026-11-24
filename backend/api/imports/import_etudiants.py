"""POST /api/etudiants/import-csv — liste des étudiants (début d'année).

CSV : nom, prenom, groupe  (ex. groupe "IMS2G1", "CTM2G1", "D&M2G1") — autres colonnes ignorées.
- email généré : prenom.nom@esith.net
- groupe stocké tel quel dans etudiants.groupe (jointure avec planning_seances.groupe)
- filière + niveau déduits du groupe (IMS2G1 -> IMS 2ème année) ; si inconnus, l'étudiant est
  quand même créé, sans filière, et signalé dans "avertissements"

- étudiant inconnu                          -> créé + compte + email d'identifiants
- étudiant déjà en base (même email, ou même nom dans le même groupe / la même filière) sans compte
                                            -> groupe mis à jour, compte créé + email d'identifiants
- étudiant qui a déjà un compte             -> ignoré
Le mot de passe envoyé est temporaire : il doit être changé à la première connexion.
"""
import io
from collections import defaultdict
from datetime import datetime

import pandas as pd
from flask import jsonify, request

from backend.agent.ia_agent import send_email
from backend.api.auth import require_auth, require_role
from backend.api.imports.common import (
    CACHE, cle_colonne, db, gen_email, gen_mot_de_passe, hash_password, html_credentials,
)
from backend.database.groupe import ensure_groupe_column, filiere_depuis_groupe, normaliser_groupe
from backend.database.import_notes import cle_nom, id_inscription_provisoire
from backend.database.import_performance import annee_scolaire_courante

COLONNES_REQUISES = {"nom", "prenom", "groupe"}


def _gen_mot_de_passe_temporaire() -> str:
    """8 caractères lettres + chiffres, avec au moins une lettre et un chiffre."""
    while True:
        mdp = gen_mot_de_passe(8)
        if any(c.isdigit() for c in mdp) and any(c.isalpha() for c in mdp):
            return mdp


@require_auth
@require_role("admin")
def import_etudiants_csv():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
    try:
        df = pd.read_csv(io.BytesIO(uploaded.read()), sep=None, engine="python",
                         dtype=str, encoding="utf-8-sig").fillna("")
    except Exception as exc:
        return jsonify({"success": False, "error": f"CSV illisible : {exc}"}), 400

    df.columns = [cle_colonne(c) for c in df.columns]
    manquantes = COLONNES_REQUISES - set(df.columns)
    if manquantes:
        return jsonify({"success": False,
                        "error": f"Colonnes manquantes : {', '.join(sorted(manquantes))}"}), 400

    conn = db()
    ensure_groupe_column(conn)
    filieres  = [dict(r) for r in conn.execute("SELECT id, code, niveau FROM filieres")]
    par_email = {}
    par_nom   = defaultdict(list)
    for r in conn.execute(
        "SELECT e.id, e.nom, e.prenom, LOWER(e.email) AS email, e.id_filiere, e.groupe,"
        " u.id AS id_user FROM etudiants e LEFT JOIN users u ON u.id_etudiant = e.id"
    ):
        r = dict(r)
        if r["email"]:
            par_email[r["email"]] = r
        par_nom[cle_nom(r["nom"], r["prenom"])].append(r)
    emails_users = {r[0].lower() for r in conn.execute("SELECT email FROM users")}

    annee_sco = annee_scolaire_courante()
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ajoutes, comptes_crees, ignores, erreurs, avertissements, a_notifier = [], [], [], [], [], []
    vus = set()

    for i, row in df.iterrows():
        ligne  = i + 2  # ligne 1 = en-têtes
        nom    = row["nom"].strip()
        prenom = row["prenom"].strip()
        groupe = normaliser_groupe(row["groupe"])
        if not nom or not prenom or not groupe:
            erreurs.append(f"Ligne {ligne} : nom, prénom ou groupe manquant")
            continue
        email = gen_email(prenom, nom)
        if email in vus:
            erreurs.append(f"Ligne {ligne} : {email} en double dans le fichier")
            continue
        vus.add(email)

        fil = filiere_depuis_groupe(filieres, groupe)
        if not fil:
            avertissements.append(f"Ligne {ligne} : filière introuvable pour le groupe « {groupe} »"
                                  f" — {prenom} {nom} importé sans filière")

        # Déjà en base ? par email, sinon même nom + prénom dans le même groupe (ou la même filière)
        et = par_email.get(email)
        if not et:
            homonymes = [c for c in par_nom.get(cle_nom(nom, prenom), [])
                         if c["groupe"] == groupe or (fil and c["id_filiere"] == fil["id"])]
            et = homonymes[0] if len(homonymes) == 1 else None

        if et and et["id_user"]:
            ignores.append(email)
            continue
        if email in emails_users:
            erreurs.append(f"Ligne {ligne} : {email} est déjà utilisé par un autre compte")
            continue

        if et:
            # Étudiant connu sans compte (créé par un import Konosys) : le groupe du CSV fait foi
            if et["email"] != email:
                if conn.execute("SELECT 1 FROM etudiants WHERE LOWER(email)=? AND id<>?",
                                (email, et["id"])).fetchone():
                    erreurs.append(f"Ligne {ligne} : {email} est déjà utilisé par un autre étudiant")
                    continue
                conn.execute("UPDATE etudiants SET email=? WHERE id=?", (email, et["id"]))
            conn.execute(
                "UPDATE etudiants SET groupe=?, id_filiere=COALESCE(?, id_filiere) WHERE id=?",
                (groupe, fil["id"] if fil else None, et["id"]),
            )
            id_et = et["id"]
            comptes_crees.append(email)
        else:
            session_programme = f"{groupe} {fil['niveau']} {annee_sco}" if fil else f"{groupe} {annee_sco}"
            cur = conn.execute(
                "INSERT INTO etudiants (id_inscriptionsessionprogramme, nom, prenom, email,"
                " id_filiere, session_programme, groupe) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id_inscription_provisoire(conn), nom, prenom, email,
                 fil["id"] if fil else None, session_programme, groupe),
            )
            id_et = cur.lastrowid
            ajoutes.append(email)

        mdp = _gen_mot_de_passe_temporaire()
        conn.execute(
            "INSERT INTO users (id_etudiant, email, password_hash, password_version, created_at, must_change_password)"
            " VALUES (?, ?, ?, 'bcrypt', ?, 1)",
            (id_et, email, hash_password(mdp), now),
        )
        emails_users.add(email)
        par_email[email] = {"id": id_et, "email": email, "id_user": True}
        a_notifier.append((prenom, nom, email, mdp))
    conn.commit()
    conn.close()
    CACHE["data"] = None

    # Envoi Brevo, comme l'import CSV professeurs
    emails_echoues = []
    for prenom, nom, email, mdp in a_notifier:
        try:
            envoye = send_email(email, "Vos identifiants StudentTrack — ESITH",
                                html_credentials(prenom, nom, email, mdp, role="Étudiant", temporaire=True))
        except Exception:
            envoye = False
        if not envoye:
            emails_echoues.append(email)
    return jsonify({
        "success":         True,
        "ajoutes":         len(ajoutes),
        "comptes_crees":   len(comptes_crees),
        "ignores":         len(ignores),
        "erreurs":         erreurs,
        "avertissements":  avertissements,
        "emails_envoyes":  len(a_notifier) - len(emails_echoues),
        "emails_echoues":  emails_echoues,
    })
