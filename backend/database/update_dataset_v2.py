"""
update_dataset_v2.py — Mise à jour du dataset Modules_Volumes_Horaires_ESITH.xlsx
Applique les Bloc_Competence officiels 2025-2026 et ajoute la filière ITTI.
Sortie : data/samples/Modules_Volumes_Horaires_ESITH_V2.xlsx
"""

import unicodedata, re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parents[2]
INPUT   = ROOT / "data" / "samples" / "Modules_Volumes_Horaires_ESITH.xlsx"
OUTPUT  = ROOT / "data" / "samples" / "Modules_Volumes_Horaires_ESITH_V2.xlsx"


# ---------------------------------------------------------------------------
# Normalisation pour la correspondance fuzzy
# ---------------------------------------------------------------------------
def _nrm(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _nrm(a), _nrm(b)).ratio()


def _best_bloc(module_nom: str, mapping: dict[str, str]) -> str | None:
    """Retourne le bloc le mieux correspondant (seuil 0.60), ou None."""
    nm = _nrm(module_nom)
    best_score, best_bloc = 0.0, None
    for key, bloc in mapping.items():
        nk = _nrm(key)
        # correspondance exacte ou inclusion
        if nm == nk or nm in nk or nk in nm:
            return bloc
        s = SequenceMatcher(None, nm, nk).ratio()
        if s > best_score:
            best_score, best_bloc = s, bloc
    return best_bloc if best_score >= 0.60 else None


# ---------------------------------------------------------------------------
# CATALOGUE : (filiere, niveau) → {module_nom → bloc_competence}
# Les filières GI-BDM/EO/SL 1ère année utilisent la clé "GI" (Tronc Commun)
# ---------------------------------------------------------------------------
CATALOGUE: dict[tuple, dict[str, str]] = {}


def _add(filiere: str, niveau: str, bloc: str, modules: list[str]):
    key = (filiere, niveau)
    CATALOGUE.setdefault(key, {})
    for m in modules:
        CATALOGUE[key][m] = bloc


# --- 1. IMS 1ère année ---
_add("IMS", "1ère année", "Mécanique & Résistance des Matériaux", [
    "Mécanique des Fluides et des Solides", "Résistance des Matériaux",
])
_add("IMS", "1ère année", "Digital skills 1", [
    "Python Niveau 1", "Excel Avancé",
])
_add("IMS", "1ère année", "Systèmes Électroniques et Electrotechnique", [
    "Électronique", "Électrotechnique",
])
_add("IMS", "1ère année", "Mathématiques et Algorithmes pour l'IA et l'Industrie 4.0", [
    "Algorithmes pour l'IA",
    "Statistiques Avancées et Apprentissage Automatique",
    "Probabilités et Modélisation Stochastique pour l'IA",
])
_add("IMS", "1ère année", "Langue et communication 1", [
    "Anglais_S1", "Communication en français", "Espagnol_S1",
])
_add("IMS", "1ère année", "Dessin Industriel & Conception de mécanismes", [
    "Dessin Industriel (DAO)", "Conception de mécanismes (CAO)",
    "Projet 1 : Conception et dimensionnement d'une machine industrielle",
    "Automatisation de la Conception par IA",
])
_add("IMS", "1ère année", "Introduction à l'analyse des données", [
    "Data Analysis", "Big Data et Analytique",
])
_add("IMS", "1ère année", "Développement Logiciel et Bases de Données", [
    "Programmation Orientée Objet (C++)", "BDD : conception et développement (SQL)",
])
_add("IMS", "1ère année", "Digital skills 2", [
    "Programmation Python Avancée", "Programmation en Langage R",
])
_add("IMS", "1ère année", "Langue et communication 2", [
    "Anglais_S2", "Espagnol_S2",
])
_add("IMS", "1ère année", "Ingénierie des Systèmes Industriels", [
    "Organisation et gestion des entreprises",
    "Fiabilité Disponibilité et Maintenance",
    "Procédés industriels de Production",
])
_add("IMS", "1ère année", "Outils d'aide à la décision", [
    "Recherche Opérationnelle et IA",
    "Méthode de décision multicritères & Algorithmes Heuristiques",
    "Data science pour la prise de Décision",
])
_add("IMS", "1ère année", "Modélisation, Conception et Dimensionnement d'un procédé industriel", [
    "Projet 2 : Modélisation, Conception et Dimensionnement d'un procédé industriel",
])
_add("IMS", "1ère année", "Techniques Numériques Avancées et Systèmes Intelligents Appliqués", [
    "Estimation et commande numérique intelligente",
    "Traitement des Signaux et Systèmes",
    "Analyse Numérique",
])

# --- 2. IMS 2ème année ---
_add("IMS", "2ème année", "Langue et communication 3", [
    "Anglais_S3", "Espagnol_S3",
])
_add("IMS", "2ème année", "Comptabilité et Contrôle de Gestion", [
    "Comptabilité", "Économie", "Coût de Revient / contrôle de gestion",
])
_add("IMS", "2ème année", "Robotique et FAO", [
    "Fabrication Assistée par Ordinateurs (FAO)", "Robotique",
    "Projet 3 : Réalisation d'une machine industrielle E2",
])
_add("IMS", "2ème année", "Systèmes Embarqués et Capteurs", [
    "Calculateurs embarqués",
    "Communication et Réseaux pour Systèmes Embarqués",
    "Capteurs & Instrumentations",
])
_add("IMS", "2ème année", "Programmation Orientée Objet et Développement avancé", [
    "Développement web et Mobile",
    "Programmation Orientée Objet (Niveau 2 : Java)",
    "IA pour Applications Web et Mobiles",
])
_add("IMS", "2ème année", "Modules Complémentaire", [
    "Apprentissage Automatique et Intelligence Artificielle",
])
_add("IMS", "2ème année", "Modélisation & Management des Systèmes Industriels", [
    "Modélisation des Processus d'Entreprise",
    "Management Industriel et Logistique",
    "Analyse de Données pour la Performance Industrielle",
])
_add("IMS", "2ème année", "Initiation au Machine Learning et IA Générative", [
    "Generative AI",
])
_add("IMS", "2ème année", "Langue et communication 4", [
    "Communication_S4", "Anglais_S4",
])
_add("IMS", "2ème année", "Management de la Maintenance", [
    "Projet 4 : Gestion et Prototypage de Projets Pluritechnique",
    "Maintenance Prédictive", "Total Productive Maintenance",
])
_add("IMS", "2ème année", "Management de la Sécurité et de l'Ergonomie", [
    "Cybersécurité et Gestion des Risques",
    "Sécurité Fonctionnelle et Opérationnelle",
    "Ergonomie et Conception des Postes QSE",
])
_add("IMS", "2ème année", "Optimisation des Procédés et Expérimentation Industrielle", [
    "Plan d'Expérience", "SPC 4.0", "Digitalisation et Optimisation des Procédés",
])
_add("IMS", "2ème année", "Gestion de Projet et Méthodologies Agiles", [
    "Démarche Scrum", "Gestion de Projet Logiciel",
])
_add("IMS", "2ème année", "Soft skills 1", [
    "Entreprenariat et propriété intellectuelle",
])
_add("IMS", "2ème année", "Systèmes de Communication et Temps Réel", [
    "Réseaux de Communication et Protocoles Temps Réel",
    "Sécurité et Fiabilité dans les Systèmes Temps Réel",
    "Systèmes Temps Réel et Commande des Processus",
])

# --- 4. GI-BDM 2ème année ---
_add("GI-BDM", "2ème année", "Langue et communication 3", [
    "Anglais_S3", "Espagnol_S3",
])
_add("GI-BDM", "2ème année", "Maintenance et fiabilité", [
    "Management de la maintenance / TPM",
    "Sûreté de fonctionnement : Analyse de données", "GMAO",
])
_add("GI-BDM", "2ème année", "Management Industriel", [
    "Gestion de production", "Logistique", "Marketing", "Technique de négociation",
])
_add("GI-BDM", "2ème année", "Produit et Processus Textile", [
    "Textile Amont : Filature", "Textile Amont : Maille", "Textile Aval : Ennoblissement",
    "Textile Amont : Tissage", "Textile Aval : Habillement",
])
_add("GI-BDM", "2ème année", "Achat & Approvisionnement", [
    "Gestion des Stocks et approvisionnement",
    "Gestion des achats et sourcing -Vente-Négociation",
])
_add("GI-BDM", "2ème année", "Système d'Information & Sciences de données", [
    "Architecture et ERP", "Programmation Python Niveau 3",
    "Bases de données & Big Data",
])
_add("GI-BDM", "2ème année", "Intelligence artificielle", [
    "Machine Learning", "Iot & Cloud Computing & Cybersécurité",
    "Sciences de Données et IA",
])
_add("GI-BDM", "2ème année", "Data Driven Business", [
    "Marketing opérationnel", "Outils achat et sourcing électronique",
    "Science de données (BI) & Deep learning",
])
_add("GI-BDM", "2ème année", "Langue et communication 4", [
    "Communication_S4", "Anglais_S4",
])
_add("GI-BDM", "2ème année", "Management opérationnel", [
    "Techniques de résolution de problèmes",
    "Etude et méthodologie d'enquête",
    "Generative IA / Insight consommateur",
])
_add("GI-BDM", "2ème année", "Soft skills 1", [
    "Gestion de projets - Projet Tutoré",
    "Entreprenariat et propriété intellectuelle",
])
_add("GI-BDM", "2ème année", "Intelligence Marché", [
    "Communication 360° et Content Marketing",
    "Marketing stratégique", "Comportement du Consommateur",
])
_add("GI-BDM", "2ème année", "Management de l'Innovation 1", [
    "Conception industrielle", "Hygiène et Sécurité",
])
_add("GI-BDM", "2ème année", "Online Multichannel Marketing", [
    "Gestion de campagne E-mailing", "E-Commerce/E-Business",
])

# --- 5. GI-EO 2ème année ---
_add("GI-EO", "2ème année", "Achat & Approvisionnement", [
    "Gestion des Stocks et approvisionnement",
    "Gestion des achats et sourcing -Vente-Négociation",
])
_add("GI-EO", "2ème année", "Langue et communication 3", [
    "Anglais_S3", "Espagnol_S3",
])
_add("GI-EO", "2ème année", "Maintenance et fiabilité", [
    "Sûreté de fonctionnement : Analyse de données",
    "Management de la maintenance / TPM", "GMAO",
])
_add("GI-EO", "2ème année", "Management Industriel", [
    "Gestion de production", "Logistique", "Marketing",
])
_add("GI-EO", "2ème année", "Produit et Processus Textile", [
    "Textile Amont : Maille", "Textile Aval : Ennoblissement",
    "Textile Amont : Filature", "Textile Amont : Tissage",
    "Textile Aval : Habillement", "Conditionnement Textile",
])
_add("GI-EO", "2ème année", "Intelligence artificielle", [
    "Machine Learning", "Sciences de Données et IA",
])
_add("GI-EO", "2ème année", "Système d'Information & Sciences de données", [
    "Bases de données & Big Data", "Programmation Python Niveau 3",
    "Architecture et ERP",
])
_add("GI-EO", "2ème année", "Langue et communication 4", [
    "Communication_S4", "Anglais_S4",
])
_add("GI-EO", "2ème année", "Systèmes de contrôle interne, HSE et RSE", [
    "Contrôle de gestion",
    "Hygiène, Sécurité et Environnement",
    "Systèmes de Management de la Qualité Iso 9001",
])
_add("GI-EO", "2ème année", "Engineering : Bureau d'étude & Bureau de méthode", [
    "Bureau de Méthode dans l'industrie de l'habillement",
    "Bureau d'Etude dans l'industrie de l'habillement",
])
_add("GI-EO", "2ème année", "Supply Chain Management", [
    "Planification, Ordonnancement-Lancement",
    "Commerce international", "Logistique Aval",
])
_add("GI-EO", "2ème année", "Technologies de la couture industrielle", [
    "Typologie des machines",
    "Processus Coupe-Préparation",
    "Processus Montage-Repassage-Conditionnement",
])
_add("GI-EO", "2ème année", "Soft skills 1", [
    "Gestion de projets - Projet Tutoré",
    "Entreprenariat et propriété intellectuelle",
])
_add("GI-EO", "2ème année", "Technologies d'autres industries manufacturières", [
    "Industrie de la coiffe automobile et Industrie du cuir",
    "Industrie du Délavage et du Finissage",
])

# --- 6. GI-SL 2ème année ---
_add("GI-SL", "2ème année", "Achat & Approvisionnement", [
    "Gestion de la demande et prévisions des ventes",
    "Gestion des achats et sourcing -Vente-Négociation",
    "Gestion des Stocks et approvisionnement",
])
_add("GI-SL", "2ème année", "Intelligence artificielle", [
    "Machine Learning", "Iot & Cloud Computing & Cybersécurité",
    "Sciences de Données et IA",
])
_add("GI-SL", "2ème année", "Langue et communication 3", [
    "Espagnol_S3", "Anglais_S3",
])
_add("GI-SL", "2ème année", "Maintenance et fiabilité", [
    "Sûreté de fonctionnement : Analyse de données",
    "Management de la maintenance / TPM",
])
_add("GI-SL", "2ème année", "Produit et Processus Textile", [
    "Textile Aval : Habillement", "Textile Amont : Filature",
    "Textile Amont : Maille",
])
_add("GI-SL", "2ème année", "Management Industriel", [
    "Gestion de production", "Logistique", "Marketing",
])
_add("GI-SL", "2ème année", "Système d'Information & Sciences de données", [
    "Bases de données & Big Data", "Programmation Python Niveau 3",
    "Architecture et ERP",
])
_add("GI-SL", "2ème année", "Conception et organisation de postes de travail", [
    "Organisation et optimisation d'un poste de travail",
    "Gestion des opérations de production", "Coût de revient",
])
_add("GI-SL", "2ème année", "Méthodes et techniques d'optimisation", [
    "Programmation en Nombres entiers",
    "Modélisation des systèmes et des processus",
    "Modélisation des processus décisionnels",
])
_add("GI-SL", "2ème année", "Langue et communication 4", [
    "Communication_S4", "Anglais_S4",
])
_add("GI-SL", "2ème année", "Pilotage des flux", [
    "Modélisation des flux et amélioration des performances industrielles",
    "Six Sigma (SPC)",
])
_add("GI-SL", "2ème année", "Gestion de l'Entreposage et de la manutention", [
    "Gestion de l'entreposage E1", "DDMRP", "Gestion de l'entreposage E2",
])
_add("GI-SL", "2ème année", "Soft skills 1", [
    "Gestion de projets", "Entreprenariat et propriété intellectuelle",
    "Projet Tutoré",
])
_add("GI-SL", "2ème année", "Management de la Distribution et Transport", [
    "Management du Transport National",
    "Management de la Distribution", "Digitalisation du Transport",
])

# --- 7. GI Tronc Commun 1ère année (applied to GI-BDM/EO/SL 1ère année) ---
for _fil in ("GI-BDM", "GI-EO", "GI-SL"):
    _add(_fil, "1ère année", "Digital skills 1", [
        "Algorithme", "Programmation Python 1",
    ])
    _add(_fil, "1ère année", "Électronique", [
        "Electronique Appliquée", "Capteurs et instrumentations",
        "Informatique Industriel /API", "Electronique Appliquée TP",
    ])
    _add(_fil, "1ère année", "Electrotechnique et Régulation", [
        "Électrotechnique", "Régulation Industrielle", "Electrotechnique TP",
    ])
    _add(_fil, "1ère année", "Langue et communication 1", [
        "Communication en français", "Anglais", "Anglais_S1", "Espagnol_S1",
    ])
    _add(_fil, "1ère année", "Mathématiques et statistiques", [
        "Mathématiques appliquées", "Statistique appliquée", "Prévisions",
    ])
    _add(_fil, "1ère année", "Mécaniques & Matériaux", [
        "Mécanique appliquée", "Mécanique des fluides", "Résistance des Matériaux",
    ])
    _add(_fil, "1ère année", "Conception Industrielle", [
        "Dessin industriel/DAO", "FAO/CAO",
    ])
    _add(_fil, "1ère année", "Langue et communication 2", [
        "Anglais_S2", "Espagnol_S2",
    ])
    _add(_fil, "1ère année", "Organisation des entreprises", [
        "Comptabilité Générale", "Business Fundamental",
        "Organisation et gestion des entreprises",
    ])
    _add(_fil, "1ère année", "Transformation Digitale", [
        "Transformation Digitale & Technologies émergentes",
        "Gestion de base de données",
    ])
    _add(_fil, "1ère année", "Digital skills 2", [
        "Programmation Python 2", "Excel Avancé", "Excel Avancé_S2",
    ])
    _add(_fil, "1ère année", "Spécialité Métier", [
        "Operational manufacturing", "Smart Logistic & supply chain management",
        "Business & Data development",
    ])
    _add(_fil, "1ère année", "Chimie TC", [
        "Chimie", "Matières Textiles",
    ])
    _add(_fil, "1ère année", "Conception et Outil d'aide à la décision", [
        "Décisions multicritères", "Statistique appliquée 2",
        "Recherche opérationnelle",
    ])

# --- 8. CTM 1ère et 2ème année ---
_add("CTM", "1ère année", "Chimie Minérale", [
    "Cristallographie", "Chimie minérale descriptive",
])
_add("CTM", "1ère année", "Mécanique des fluides et transfert thermique", [
    "Mécanique des Fluides", "Mécanique des fluides", "Transferts thermiques",
])
_add("CTM", "1ère année", "Chimie Générale", [
    "Atomistique", "Chimie des solutions", "Chimie des solutions TP",
])
_add("CTM", "1ère année", "Digital skills 1", [
    "Algorithme", "Programmation Python 1",
])
_add("CTM", "1ère année", "Mathématiques appliquées", [
    "Mathématique", "Statistiques",
])
_add("CTM", "1ère année", "Thermochimie et Electrochimie", [
    "Thermochimie", "Électrochimie", "Thermochimie TP",
])
_add("CTM", "1ère année", "Langue et communication 1", [
    "Anglais_S1", "Communication en français",
    "Communication : Study skills", "Espagnol_S1",
])
_add("CTM", "1ère année", "Management de la qualité, de la sécurité et de l'environnement", [
    "Management de la qualité", "Hygiène, Santé et Sécurité",
])
_add("CTM", "1ère année", "Chimie Organique Fonctionnelle 1", [
    "Chimie Organique générale", "Synthèse et Fonctions",
])
_add("CTM", "1ère année", "Langue et communication 2", [
    "Anglais_S2", "Espagnol_S2",
])
_add("CTM", "1ère année", "Chimie Théorique", [
    "Spectroscopie", "Théorie des Groupes",
])
_add("CTM", "1ère année", "Chimie Analytique", [
    "Méthodes d'Analyses et Interprétation", "Méthodes de Séparation",
])
_add("CTM", "1ère année", "Digital skills 2", [
    "Gestion de base de données", "Excel Avancé",
])
_add("CTM", "1ère année", "Elaboration des matériaux", [
    "Elaboration des matériaux",
])

_add("CTM", "2ème année", "Chimie des polymères 1", [
    "Chimie des polymères", "Chimie des polymères TP",
])
_add("CTM", "2ème année", "Chimie Organique Fonctionnelle 2", [
    "Chimie Organique Avancée", "Chimie Organique Industrielle",
])
_add("CTM", "2ème année", "Innovation et propriété intellectuelle", [
    "Propriété industrielle", "Recherche et Innovation",
])
_add("CTM", "2ème année", "Intelligence artificielle", [
    "Machine Learning", "Sciences de Données et IA",
    "IoT & Cloud Computing & Cybersécurité",
])
_add("CTM", "2ème année", "Langue et communication 3", [
    "Anglais", "Espagnol",
])
_add("CTM", "2ème année", "Chimie minérale industrielle", [
    "Traitement des minerais", "Chimie du solide",
    "Traitement des métaux et alliages",
])
_add("CTM", "2ème année", "Génie des Procédés", [
    "Procédés chimiques", "Génie de la réaction chimique",
])
_add("CTM", "2ème année", "Langue et communication 4", [
    "Communication", "Anglais_S4",
])
_add("CTM", "2ème année", "Environnement et développement durable", [
    "Développement durable", "Gestion environnemental",
])
_add("CTM", "2ème année", "Gestion de projet et des entreprises", [
    "Gestion de projets", "Entreprenariat",
])
_add("CTM", "2ème année", "Métrologie Chimique", [
    "La chaîne de mesure", "Validation des méthodes",
])
_add("CTM", "2ème année", "Nanomatériaux et technologies", ["Nanomatériaux"])
_add("CTM", "2ème année", "Catalyse et physicochimie des surfaces", ["Chimie catalytique"])
_add("CTM", "2ème année", "Chimie appliquée", [
    "Chimie du textile", "Chimie du cuir",
])

# --- 9. HSE 1ère année ---
_add("HSE", "1ère année", "Notions Environnement et Développement durable", [
    "Notions Environnement", "Développement durable_Notions",
    "Développement durable",
])
_add("HSE", "1ère année", "Introduction à l'Hygiène, Sécurité et Environnement", [
    "Acteurs, documents HSE", "Introduction HSE",
])
_add("HSE", "1ère année", "Soft Skills", [
    "Study skills", "Life skills", "Study et Life Skills",
])
_add("HSE", "1ère année", "Langues étrangères 1", [
    "Anglais_S1", "Espagnol_S1", "Anglais - Espagnol_S1",
])
_add("HSE", "1ère année", "Dangers inhérents à l'opérateur humain et au milieu de travail", [
    "Ergonomie",
    "Dangers inhérents à l'opérateur humain et au milieu de travail",
])
_add("HSE", "1ère année", "Dangers inhérents aux équipements et aux installations", [
    "Dangers inhérents aux équipements et aux installations",
    "Dangers inhérents aux systèmes chimiques",
    "Dangers inhérents aux équipements et aux installations E1",
    "Dangers inhérents aux équipements et aux installations E2",
])
_add("HSE", "1ère année", "Gestion des risques : Concept et théorie", [
    "Sûreté de fonctionnement", "Gestion de Projet",
    "Risques transférés aux Assurances",
])
_add("HSE", "1ère année", "Sécurité : approches, techniques et réglementation", [
    "Sécurité : approches, techniques et réglementation",
])
_add("HSE", "1ère année", "Digital Skills", [
    "Statistiques et analyse des données",
    "Digital Skills (Excel avancé)", "IA générative",
])
_add("HSE", "1ère année", "Gestion du risque environnemental", [
    "Prévention et traitement de la pollution",
    "Efficacité Energétique", "Métrologie Environnementale",
    "Eco-conception et Analyse de cycle de vie",
])
_add("HSE", "1ère année", "Incendie - Explosion", ["Incendie"])
_add("HSE", "1ère année", "Dangers inhérents aux rayonnements et aux systèmes biologiques", [
    "Dangers inhérents aux systèmes biologiques",
    "Dangers inhérents aux rayonnements ionisants et non ionisants",
])
_add("HSE", "1ère année", "Culture entrepreneuriale", ["Entreprenariat et Leadership"])
_add("HSE", "1ère année", "Méthodologie de la recherche scientifique", [
    "Méthodologie de la recherche scientifique",
])

# --- 10. MPTH 1ère année ---
_add("MPTH", "1ère année", "Langues étrangères 1", [
    "Anglais_S1", "Espagnol_S1",
])
_add("MPTH", "1ère année", "Soft Skills", ["Study et Life Skills"])
_add("MPTH", "1ère année", "Concept Marketing", [
    "Marketing de la mode",
    "Diagnostic du marché et Analyse des tendances",
])
_add("MPTH", "1ère année", "Mode et Tendance", [
    "Économie Mondiale et Géopolitique Textile Habillement",
    "L'Histoire, actualité et tendance de la Mode",
    "Sociologie de la mode et histoire des marques",
])
_add("MPTH", "1ère année", "Techniques et Outils de Management des Entreprises", [
    "Comptabilité et gestion des coûts",
    "Droit Commercial et Droit du Travail",
    "Organisation et gestion des entreprises",
])
_add("MPTH", "1ère année", "Technologie Textile 1", [
    "Tissage", "Fibres, Fils et Matières Textiles", "Filature",
    "Confection & Industrialisation",
    "Ennoblissement : Teinture, Impression, Colorimétrie", "Maille",
])
_add("MPTH", "1ère année", "Techniques de Création et Design", [
    "Infographie 1 / Graphisme", "Design",
])
_add("MPTH", "1ère année", "Logistique Textile-Habillement", [
    "Gestion des Approvisionnements et stocks",
    "Commerce international & Techniques imports et exports",
    "Management des achats et Sourcing",
])
_add("MPTH", "1ère année", "Stratégie Marketing Textile-Habillement", [
    "Plan Marketing Développement Produit",
    "Comportement du consommateur", "Démarche Stratégie Marketing",
])
_add("MPTH", "1ère année", "Création et Conception de produit", [
    "Création 2D et 3D", "Créativité et innovation",
])
_add("MPTH", "1ère année", "Culture entrepreneuriale", ["Entreprenariat et Leadership"])
_add("MPTH", "1ère année", "Méthodologie de la recherche scientifique", [
    "Méthodologie de la recherche scientifique",
])
_add("MPTH", "1ère année", "Produits et Matériaux textiles", [
    "Accessoires Textile et cuir", "Textiles Innovants",
])
_add("MPTH", "1ère année", "Digital Skills", [
    "Digital Skills (Excel avancé)", "IA générative",
])

# --- 11. MDM 1ère année ---
_add("MDM", "1ère année", "Techniques et outils de gestion d'entreprise", [
    "Comptabilité générale", "Organisation et gestion des entreprises",
])
_add("MDM", "1ère année", "Marketing Management", [
    "Marketing", "Etudes marketing et panels",
])
_add("MDM", "1ère année", "Droit et fiscalité du commerce", [
    "Commerce international & Techniques imports et exports",
    "Droit commerciale", "Pratiques fiscales du commerce",
    "Histoire du commerce et évolution",
])
_add("MDM", "1ère année", "Marketing de la distribution", [
    "Transformation Digital dans le Retail",
    "Marketing de la Distribution",
])
_add("MDM", "1ère année", "Soft Skills", ["Study et Life Skills"])
_add("MDM", "1ère année", "Techniques du merchandising", [
    "Initiation au métier du Distributeur/ Merchandiseur",
    "Strategy of communication", "Merchandising Visuel",
])
_add("MDM", "1ère année", "Langues étrangères 1", [
    "Anglais_S1", "Espagnol_S1",
])
_add("MDM", "1ère année", "Stratégies de Distribution", [
    "Développement des réseaux de distribution",
    "Analyse stratégiques de la distribution",
])
_add("MDM", "1ère année", "Gestion financière", [
    "Management du point de vente", "Gestion de la trésorerie",
    "Produits et services bancaires", "Comptabilité Analytique et financière",
])
_add("MDM", "1ère année", "Logistique de la distribution", [
    "Logistique de l'activité commerciale",
    "Création et concept d'un site e-commerce",
    "Management des achats",
])
_add("MDM", "1ère année", "Étude des zones de chalandise", [
    "Développement et expansion de retails",
    "Etude des zones de chalandise",
])
_add("MDM", "1ère année", "Digital Skills", [
    "Digital Skills (Excel avancé)", "IA générative",
])
_add("MDM", "1ère année", "Culture entrepreneuriale et techniques de communication", [
    "Entreprenariat et Leadership",
])
_add("MDM", "1ère année", "Méthodologie de la recherche scientifique", [
    "Méthodologie de la recherche scientifique",
])

# --- 12. ELOG 1ère année ---
_add("ELOG", "1ère année", "Informatique et systèmes d'information", [
    "Algorithmique et Programmation Python 1",
    "Algorithmique et Programmation Python 2",
    "Concepts liés aux systèmes d'information",
])
_add("ELOG", "1ère année", "Logistique Interne", [
    "Notions générales de la logistique",
    "Logistique Interne", "Outils logistiques",
])
_add("ELOG", "1ère année", "Base de données et Réseaux", [
    "Développement d'application de bases de données E1",
    "Systèmes réseaux, Cloud networking",
])
_add("ELOG", "1ère année", "Langues étrangères 1", [
    "Anglais_S1", "Espagnol_S1",
])
_add("ELOG", "1ère année", "Soft Skills", ["Study et Life Skills"])
_add("ELOG", "1ère année", "Logistique Externe", [
    "Logistique Amont", "Gestion de la demande et prévisions",
    "Commerce International",
])
_add("ELOG", "1ère année", "Outils d'aide à la décision", [
    "Recherche opérationnelle", "Statistiques",
    "Aide multicritère à la décision",
])
_add("ELOG", "1ère année", "Achat et planification", [
    "SI- Planification", "E- Sourcing/achats",
])
_add("ELOG", "1ère année", "Entreposage et Transport", [
    "SI- Entreposage", "SI- Transport",
])
_add("ELOG", "1ère année", "Cahier des charges et Programmation", [
    "Programmation II, Django", "Programmation web CMS", "Cahier des charges",
])
_add("ELOG", "1ère année", "Comptabilité et finance", [
    "Comptabilité générale et analytique", "Finance",
])
_add("ELOG", "1ère année", "E commerce et Distribution", [
    "E-Commerce et web marchand", "Distribution",
])
_add("ELOG", "1ère année", "Méthodologie de la recherche scientifique", [
    "Méthodologie de la recherche scientifique",
])
_add("ELOG", "1ère année", "Culture entrepreneuriale", ["Entreprenariat et Leadership"])
_add("ELOG", "1ère année", "Design thinking -UX UI", ["Design thinking UX UI"])


# ---------------------------------------------------------------------------
# Données ITTI — nouvelle filière (section 3 du PROMPT)
# ---------------------------------------------------------------------------
def _itti_rows() -> list[dict]:
    rows = []

    def row(niveau, sem, bloc, module, cr, vol):
        rows.append({
            "Filiere": "ITTI",
            "Niveau": niveau,
            "Semestre": sem,
            "Bloc_Competence": bloc,
            "Module": module,
            "Credits": cr,
            "Volume_Horaire_h": vol,
        })

    N1 = "1ère année"
    N2 = "2ème année"

    # S1
    for m, cr, vol in [("Algorithme", 5, 65), ("Programmation Python 1", 5, 65)]:
        row(N1, "S1", "Digital skills 1", m, cr, vol)
    for m, cr, vol in [("Electronique", 5, 65), ("Électrotechnique", 5, 65)]:
        row(N1, "S1", "Electronique et Électrotechnique", m, cr, vol)
    for m, cr, vol in [("Mécanique appliquée", 5, 65), ("Résistance des Matériaux", 5, 65),
                       ("Mécanique des fluides et rhéologie", 5, 65)]:
        row(N1, "S1", "Mécanique et Matériaux", m, cr, vol)
    for m, cr, vol in [("Métier et formation", 3, 25), ("Projet Textile 1 (Fil rouge Textile)", 3, 25)]:
        row(N1, "S1", "Projet Textile 1", m, cr, vol)
    for m, cr, vol in [("Matière Textile 1", 4, 36), ("Métrologie 1", 4, 36),
                       ("Tissage 1", 5, 65), ("Filature 1", 5, 65), ("Maille 1", 5, 65)]:
        row(N1, "S1", "Etoffe 1", m, cr, vol)
    for m, cr, vol in [("Chimie", 5, 65), ("Thermodynamique", 5, 65), ("Chimie des polymères", 5, 65)]:
        row(N1, "S1", "Chimie et thermodynamique", m, cr, vol)
    for m, cr, vol in [("Communication en français", 3, 27), ("Anglais_S1", 5, 65), ("Espagnol_S1", 3, 27)]:
        row(N1, "S1", "Communication et Langue 1", m, cr, vol)

    # S2
    for m, cr, vol in [("Chimie Organique", 5, 65), ("Chimie analytique", 5, 65),
                       ("Ennoblissement 1 : Traitement fibre naturel", 5, 65)]:
        row(N1, "S2", "Chimie et Ennoblissement 1", m, cr, vol)
    for m, cr, vol in [("Mathématiques", 5, 65), ("Automatique", 5, 65)]:
        row(N1, "S2", "Automatique/Mathématiques", m, cr, vol)
    for m, cr, vol in [("Anglais_S2", 5, 65), ("Espagnol_S2", 3, 27)]:
        row(N1, "S2", "Communication et Langue 2", m, cr, vol)
    for m, cr, vol in [("Organisation et gestion des entreprises", 4, 36), ("Comptabilité", 4, 36)]:
        row(N1, "S2", "Organisation d'entreprise", m, cr, vol)
    for m, cr, vol in [("Gestion de base de données", 4, 36), ("Excel Avancé", 3, 27)]:
        row(N1, "S2", "Digital skills 2", m, cr, vol)
    for m, cr, vol in [("Habillement 1", 4, 36), ("Tissage 2", 5, 65), ("Maille 2", 5, 65)]:
        row(N1, "S2", "Etoffe 2", m, cr, vol)
    row(N1, "S2", "Projet Textile 2", "Projet Textile 2 (Habillement)", 3, 25)

    # 2A S3
    for m, cr, vol in [("Ennoblissement 2 : Fibre synthétique/mélange", 5, 65),
                       ("Chimie : fibres produits", 5, 65)]:
        row(N2, "S3", "Chimie et ennoblissement 2", m, cr, vol)
    for m, cr, vol in [("Maille 3", 5, 65), ("Tissage 3", 5, 65),
                       ("Filature 2", 5, 65), ("Métrologie 2", 4, 36)]:
        row(N2, "S3", "Étoffe 3", m, cr, vol)
    for m, cr, vol in [("Machine Learning", 5, 65), ("Sciences de Données et IA", 5, 65),
                       ("IoT & Cloud Computing & Cybersécurité", 5, 65)]:
        row(N2, "S3", "Intelligence artificielle", m, cr, vol)
    for m, cr, vol in [("Anglais_S3", 5, 65), ("Espagnol_S3", 3, 27)]:
        row(N2, "S3", "Langue et communication 3", m, cr, vol)
    for m, cr, vol in [("Développement Durable / Efficacité énergétique", 4, 36),
                       ("Gestion de Production / Gestion des stocks", 4, 36),
                       ("Organisation et Management Industriel 4.0", 4, 36)]:
        row(N2, "S3", "Management Industriel", m, cr, vol)
    for m, cr, vol in [("Innovation et Recherche", 3, 25),
                       ("Projet Textile 3 : Traitement de surface - Enduction/Apprêt", 3, 25)]:
        row(N2, "S3", "Projet Textile 3", m, cr, vol)
    for m, cr, vol in [("Fibres et Matière technique", 5, 65), ("Non-tissé", 5, 65)]:
        row(N2, "S3", "Textile Technique", m, cr, vol)

    # 2A S4
    for m, cr, vol in [("Communication", 3, 27), ("Anglais_S4", 5, 65)]:
        row(N2, "S4", "Langue et communication 4", m, cr, vol)
    for m, cr, vol in [("Hygiène et Sécurité/ Environnement", 4, 36),
                       ("Gestion de la qualité/SPC", 4, 36)]:
        row(N2, "S4", "Qualité/HSE/RSE", m, cr, vol)
    for m, cr, vol in [("Dimensionnement de Structures (Filage et extrusion)", 5, 65),
                       ("Textiles Intelligents et sensoriels", 5, 65),
                       ("Textiles de renfort et composites", 5, 65)]:
        row(N2, "S4", "Matériaux TUT 1", m, cr, vol)
    for m, cr, vol in [("Contrôle de gestion et Coût de revient", 4, 36),
                       ("Finance & Mathématiques financières", 4, 36)]:
        row(N2, "S4", "Gestion/Finance", m, cr, vol)
    for m, cr, vol in [("Finissage", 5, 65), ("Polymère", 5, 65)]:
        row(N2, "S4", "Polymère et Finissage", m, cr, vol)
    for m, cr, vol in [("Entreprenariat et Propriété intellectuelle", 4, 36),
                       ("Gestion de projets", 3, 25)]:
        row(N2, "S4", "Soft skills 1", m, cr, vol)

    return rows


# ---------------------------------------------------------------------------
# Logique principale
# ---------------------------------------------------------------------------
def main():
    df = pd.read_excel(INPUT)
    print(f"Chargement : {len(df)} lignes, colonnes = {list(df.columns)}")

    stats = {"updated": 0, "added": 0, "unchanged": 0}
    new_rows: list[dict] = []

    # Pour chaque (filiere, niveau) présent dans le CATALOGUE
    for (filiere, niveau), module_map in CATALOGUE.items():
        mask = (df["Filiere"] == filiere) & (df["Niveau"] == niveau)
        subset = df[mask]

        # Marquer les modules du df déjà traités
        matched_idx: set[int] = set()

        for off_module, off_bloc in module_map.items():
            best_idx, best_score = -1, 0.0
            for idx, row in subset.iterrows():
                if idx in matched_idx:
                    continue
                s = _sim(off_module, str(row["Module"]))
                if s > best_score:
                    best_score, best_idx = s, idx

            if best_idx >= 0 and best_score >= 0.60:
                old_bloc = df.at[best_idx, "Bloc_Competence"]
                if old_bloc != off_bloc:
                    df.at[best_idx, "Bloc_Competence"] = off_bloc
                    stats["updated"] += 1
                matched_idx.add(best_idx)
            else:
                # Module officiel absent du df → ajouter
                # Trouver les credits/volume médians du même (filiere, niveau)
                sample = subset[["Credits", "Volume_Horaire_h"]].median()
                cr  = int(round(sample.get("Credits", 5))) if not sample.empty else 5
                vol = int(round(sample.get("Volume_Horaire_h", 65))) if not sample.empty else 65
                if cr == 0: cr = 5
                if vol == 0: vol = 65
                sem = "S1"  # fallback; sera déduit si possible
                # Chercher un semestre cohérent depuis une ligne proche
                if not subset.empty:
                    sem = str(subset.iloc[0]["Semestre"])
                new_rows.append({
                    "Filiere": filiere, "Niveau": niveau, "Semestre": sem,
                    "Bloc_Competence": off_bloc, "Module": off_module,
                    "Credits": cr, "Volume_Horaire_h": vol,
                })
                stats["added"] += 1

        # Lignes non appariées dans le df : laisser leur Bloc_Competence inchangé
        for idx in subset.index:
            if idx not in matched_idx:
                stats["unchanged"] += 1

    # Ajouter les lignes ITTI
    itti = _itti_rows()
    for r in itti:
        new_rows.append(r)
    stats["itti"] = len(itti)

    # Construire le DataFrame final
    if new_rows:
        df_new = pd.DataFrame(new_rows, columns=df.columns.tolist())
        df_final = pd.concat([df, df_new], ignore_index=True)
    else:
        df_final = df

    # Trier
    order = {"1ère année": 1, "2ème année": 2, "3ème année": 3}
    df_final["_niv_ord"] = df_final["Niveau"].map(order).fillna(9)
    df_final = df_final.sort_values(["Filiere", "_niv_ord", "Semestre", "Bloc_Competence", "Module"]) \
                       .drop(columns=["_niv_ord"]) \
                       .reset_index(drop=True)

    df_final.to_excel(OUTPUT, index=False)

    print("\n=== Résumé ===")
    print(f"  Lignes Bloc_Competence mises à jour : {stats['updated']}")
    print(f"  Nouvelles lignes ajoutées (modules manquants) : {stats['added']}")
    print(f"  Lignes conservées sans modification    : {stats['unchanged']}")
    print(f"  Lignes ITTI ajoutées                  : {stats['itti']}")
    print(f"  Total lignes dans V2                  : {len(df_final)}")
    print(f"\n  Fichier sauvegardé : {OUTPUT}")

    # Vérification rapide
    print("\n=== Vérification Bloc_Competence (IMS 1A S1) ===")
    sample = df_final[(df_final["Filiere"]=="IMS") & (df_final["Niveau"]=="1ère année") & (df_final["Semestre"]=="S1")]
    for _, r in sample.iterrows():
        print(f"  [{r['Bloc_Competence']}] {r['Module']}")

    print("\n=== Vérification ITTI (S1) ===")
    itti_s1 = df_final[(df_final["Filiere"]=="ITTI") & (df_final["Semestre"]=="S1")]
    for _, r in itti_s1.iterrows():
        print(f"  [{r['Bloc_Competence']}] {r['Module']} | {r['Credits']}cr | {r['Volume_Horaire_h']}h")


if __name__ == "__main__":
    main()
