"""POST /api/import-modules — fichier des modules d'une filière (ex. data/samples/IMS.xlsx).

Colonnes : Filiere, Niveau, Semestre, Module, Volume_Horaire_h  (+ Bloc_Competence, Credits optionnels)
- Un module est identifié par (nom, filière + niveau, semestre) :
  existant -> volume / bloc / crédits mis à jour ; sinon -> créé.
- Comme migrate.py, le suffixe "_S<n>" du nom est retiré ("Anglais_S1" -> "Anglais", semestre S1).
- Une filière (code + niveau) absente de la base est créée.
"""
import re
import unicodedata

import pandas as pd
from flask import jsonify

from backend.api.auth import require_auth, require_role
from backend.api.imports.common import CACHE, db, traiter_fichier_xlsx

_COLONNES = {
    "filiere": "filiere", "niveau": "niveau", "semestre": "semestre", "module": "module",
    "volumehoraireh": "volume", "volumehoraire": "volume", "volume": "volume",
    "bloccompetence": "bloc", "credits": "credits",
}
_REQUISES = {"filiere", "niveau", "semestre", "module", "volume"}


def _cle(h) -> str:
    h = unicodedata.normalize("NFKD", str(h)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", h.lower())


def _texte(v) -> str:
    return "" if pd.isna(v) else str(v).strip()


def _entier(v) -> int | None:
    try:
        return int(round(float(str(v).replace(",", "."))))
    except (TypeError, ValueError):
        return None


def _lire(path) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=object)
    renommage = {c: _COLONNES[_cle(c)] for c in df.columns if _cle(c) in _COLONNES}
    manquantes = _REQUISES - set(renommage.values())
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(manquantes))}")
    return df.rename(columns=renommage)


def import_modules(path) -> dict:
    df = _lire(path)
    stats = {"lignes_traitees": 0, "modules_ajoutes": 0, "modules_mis_a_jour": 0,
             "inchanges": 0, "filieres_creees": [], "erreurs": []}

    conn = db()
    filieres = {(r["code"].upper(), str(r["niveau"])[:1]): r["id"]
                for r in conn.execute("SELECT id, code, niveau FROM filieres")}
    # Un même module peut être réparti sur plusieurs lignes (ex. "Projet 2" sur 3 lignes) :
    # on additionne les volumes pour que le résultat ne dépende pas de l'ordre des lignes.
    lignes: dict = {}
    for i, row in df.iterrows():
        ligne = i + 2  # ligne 1 = en-têtes
        stats["lignes_traitees"] += 1
        code, niveau = _texte(row["filiere"]).upper(), _texte(row["niveau"])
        nom, semestre = _texte(row["module"]), _texte(row["semestre"]).upper()
        volume = _entier(row["volume"])
        if not code or not niveau or not nom or not semestre:
            stats["erreurs"].append(f"Ligne {ligne} : filière, niveau, semestre ou module manquant")
            continue
        if volume is None or volume <= 0:
            stats["erreurs"].append(f"Ligne {ligne} : volume horaire invalide pour « {nom} »")
            continue
        m_suf = re.match(r"^(.+)_S(\d+)$", nom)
        if m_suf:
            nom, semestre = m_suf.group(1).strip(), f"S{m_suf.group(2)}"
        bloc    = _texte(row.get("bloc")) or None
        credits = _entier(row.get("credits")) if "credits" in df.columns else None
        cle = (code, niveau[:1], nom.lower(), semestre)
        if cle in lignes:
            prec = lignes[cle]
            prec["volume"] += volume
            prec["bloc"] = prec["bloc"] or bloc
            prec["credits"] = (prec["credits"] or 0) + credits if credits is not None else prec["credits"]
        else:
            lignes[cle] = {"code": code, "niveau": niveau, "nom": nom, "semestre": semestre,
                           "volume": volume, "bloc": bloc, "credits": credits}

    try:
        for l in lignes.values():
            code, niveau, nom, semestre = l["code"], l["niveau"], l["nom"], l["semestre"]
            volume, bloc, credits = l["volume"], l["bloc"], l["credits"]

            id_filiere = filieres.get((code, niveau[:1]))
            if id_filiere is None:
                id_filiere = conn.execute(
                    "INSERT INTO filieres (nom, code, niveau) VALUES (?, ?, ?)", (code, code, niveau)
                ).lastrowid
                filieres[(code, niveau[:1])] = id_filiere
                stats["filieres_creees"].append(f"{code} {niveau}")

            existant = conn.execute(
                "SELECT id, volume_heures, bloc_competence, credits FROM modules"
                " WHERE LOWER(TRIM(nom)) = LOWER(?) AND id_filiere = ? AND UPPER(semestre) = ?",
                (nom, id_filiere, semestre),
            ).fetchone()
            if existant is None:
                conn.execute(
                    "INSERT INTO modules (nom, id_filiere, semestre, bloc_competence, volume_heures, credits)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (nom, id_filiere, semestre, bloc, volume, credits),
                )
                stats["modules_ajoutes"] += 1
                continue
            nouveau = (volume, bloc or existant["bloc_competence"],
                       credits if credits is not None else existant["credits"])
            if nouveau == (existant["volume_heures"], existant["bloc_competence"], existant["credits"]):
                stats["inchanges"] += 1
                continue
            conn.execute(
                "UPDATE modules SET volume_heures=?, bloc_competence=?, credits=? WHERE id=?",
                (*nouveau, existant["id"]),
            )
            stats["modules_mis_a_jour"] += 1
        conn.commit()
    finally:
        conn.close()
    return stats


@require_auth
@require_role("admin")
def import_modules_route():
    stats, err = traiter_fichier_xlsx(lambda path, _nom: import_modules(path))
    if err:
        return err
    CACHE["data"] = None  # les taux d'absence dépendent du volume horaire des modules
    return jsonify(stats)
