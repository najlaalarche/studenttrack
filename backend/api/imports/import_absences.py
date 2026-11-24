"""POST /api/import-absences-csv — export absences Konosys (.csv / .xlsx)."""
import io
import re
import unicodedata
from collections import defaultdict
from datetime import datetime

import pandas as pd
from flask import jsonify, request

from backend.agent.ia_agent import envoyer_alerte_auto
from backend.api.auth import require_auth, require_role
from backend.api.imports.common import CACHE, db, gen_email
from backend.database.groupe import ensure_groupe_column, groupe_depuis_cursus
from backend.database.import_notes import cle_nom, id_inscription_provisoire


def _cellule(row, col: str) -> str:
    """Valeur texte d'une cellule du fichier absences ('' si vide / NaN)."""
    v = row.get(col, "")
    return "" if pd.isna(v) else str(v).strip()


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
    m = re.match(r"^([A-Za-z]+(?:-[A-Za-z]+)*)", group_code)
    if not m:
        return None
    prefix = m.group(1).upper()

    # Détecter le niveau dans SessionProgramme (1 ou 2)
    niveau_num = None
    m_niv = re.search(r"\b([12])[eè]", _norm(sp))
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


@require_auth
@require_role("admin")
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
        "etudiants_non_crees_filiere_inconnue": [],  # [{id_inscr, nom, prenom, session_programme}]
        "etudiants_homonymes": [],                   # [{nom, prenom, session_programme}] — lignes ignorées
        "modules_crees": [],
        "alertes_declenchees": 0,
        "emails_envoyes": 0,
    }

    conn = db()
    ensure_groupe_column(conn)
    etudiants_modules_touches: set = set()

    # Index Nom + Prénom normalisés → étudiants (construit une fois pour tout le fichier)
    index_noms: dict = defaultdict(list)
    for r in conn.execute("SELECT id, nom, prenom, id_filiere, id_inscriptionsessionprogramme FROM etudiants"):
        index_noms[cle_nom(r["nom"], r["prenom"])].append(dict(r))
    codes_filiere = {r[0]: r[1] for r in conn.execute("SELECT id, code FROM filieres")}

    for _, row in df.iterrows():
        stats["lignes_traitees"] += 1

        id_absence = str(row.get("id_absence", "")).strip()
        if not id_absence or id_absence == "nan":
            id_absence = ""

        nom_csv    = _cellule(row, "Nom")
        prenom_csv = _cellule(row, "Prenom")
        sp_csv     = _cellule(row, "SessionProgramme")
        cursus_csv = _cellule(row, "Cursus")
        id_inscr   = _cellule(row, "id_inscriptionsessionprogramme")
        if id_inscr.endswith(".0"):  # pandas lit parfois les entiers en float
            id_inscr = id_inscr[:-2]
        if not nom_csv or not prenom_csv:
            continue

        # Recherche UNIQUEMENT par Nom + Prénom normalisés (sans accents, minuscules)
        candidats = index_noms.get(cle_nom(nom_csv, prenom_csv), [])
        if len(candidats) > 1:
            # Homonymes : on départage par la filière du fichier (code, tous niveaux)
            id_fil = _find_filiere_for_csv(conn, sp_csv, cursus_csv)
            code = codes_filiere.get(id_fil)
            candidats = [c for c in candidats if code and codes_filiere.get(c["id_filiere"]) == code]
            if len(candidats) != 1:
                if not any(x["nom"] == nom_csv and x["prenom"] == prenom_csv for x in stats["etudiants_homonymes"]):
                    stats["etudiants_homonymes"].append({"nom": nom_csv, "prenom": prenom_csv, "session_programme": sp_csv})
                continue

        if candidats:
            et = candidats[0]
            # Étudiant créé par l'import de notes (id provisoire < 0) : on lui attribue le vrai id Konosys
            if et["id_inscriptionsessionprogramme"] < 0 and id_inscr.isdigit() and not conn.execute(
                "SELECT 1 FROM etudiants WHERE id_inscriptionsessionprogramme=?", (int(id_inscr),)
            ).fetchone():
                conn.execute(
                    "UPDATE etudiants SET id_inscriptionsessionprogramme=?,"
                    " session_programme=COALESCE(?, session_programme), cursus=COALESCE(?, cursus),"
                    " groupe=COALESCE(NULLIF(groupe, ''), ?)"
                    " WHERE id=?",
                    (int(id_inscr), sp_csv or None, cursus_csv or None,
                     groupe_depuis_cursus(cursus_csv, sp_csv), et["id"]),
                )
                et["id_inscriptionsessionprogramme"] = int(id_inscr)
                conn.commit()
        else:
            id_filiere_auto = _find_filiere_for_csv(conn, sp_csv, cursus_csv)
            if id_filiere_auto is None:
                if not any(x["nom"] == nom_csv and x["prenom"] == prenom_csv
                           for x in stats["etudiants_non_crees_filiere_inconnue"]):
                    stats["etudiants_non_crees_filiere_inconnue"].append({
                        "id_inscr": id_inscr, "nom": nom_csv, "prenom": prenom_csv,
                        "session_programme": sp_csv,
                    })
                continue

            # id Konosys réel s'il est libre, sinon id provisoire (colonne NOT NULL UNIQUE)
            if id_inscr.isdigit() and not conn.execute(
                "SELECT 1 FROM etudiants WHERE id_inscriptionsessionprogramme=?", (int(id_inscr),)
            ).fetchone():
                id_insc_db = int(id_inscr)
            else:
                id_insc_db = id_inscription_provisoire(conn)

            email_auto = gen_email(prenom_csv, nom_csv)
            if conn.execute("SELECT 1 FROM etudiants WHERE email=?", (email_auto,)).fetchone():
                stats["etudiants_homonymes"].append({"nom": nom_csv, "prenom": prenom_csv,
                                                     "session_programme": f"email {email_auto} déjà utilisé"})
                continue
            cur_ins = conn.execute(
                "INSERT INTO etudiants"
                " (id_inscriptionsessionprogramme, nom, prenom, email, id_filiere, session_programme, cursus, groupe)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (id_insc_db, nom_csv, prenom_csv, email_auto,
                 id_filiere_auto, sp_csv or None, cursus_csv or None,
                 groupe_depuis_cursus(cursus_csv, sp_csv)),
            )
            conn.commit()
            et = {"id": cur_ins.lastrowid, "id_filiere": id_filiere_auto,
                  "id_inscriptionsessionprogramme": id_insc_db}
            index_noms[cle_nom(nom_csv, prenom_csv)] = [et]
            stats["etudiants_crees_auto"].append({"prenom": prenom_csv, "nom": nom_csv})

        id_etudiant = int(et["id"])
        id_filiere  = et["id_filiere"]

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
            d = pd.to_datetime(str(row.get("DATE", "")), dayfirst=True, errors="coerce")
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
    CACHE["data"] = None
    return jsonify(stats)
