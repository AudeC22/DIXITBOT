# ===============================  # #
# 🔢 RÉFÉRENTIEL (Étapes + Sources)  # #
# ===============================  # #
# ✅ But (1 phrase, simple) : on rend la sortie du tool prévisible et on évite que tout casse si arXiv change un détail.  # #
#
# 📌 Étapes (codes à réutiliser dans les hashtags, pour éviter la redondance)
# [E1] NORMALISATION/DECOUPLAGE : transformer/standardiser les données (format stable) pour que FastAPI lise sans surprise.  # #
# [E2] ROBUSTESSE : continuer à fonctionner malgré HTML qui change, pages bizarres, ou résultats manquants (fallback + diag).  # #
# [E3] GESTION_ERREUR : capturer les erreurs (HTTP/timeouts/exceptions) et retourner ok=False + errors[] au lieu de crasher.  # #
# [E4] SCRAPING_ETHIQUE : limiter la fréquence, mettre un User-Agent, ne pas spammer le site (politesse).  # #
# [E5] STRUCTURATION : préparer un contexte/sections propres (ex: method/references) sans envoyer du HTML brut au LLM.  # #
# [E6] TOOL : exécution du scraping en tant qu'outil externe (appelé par l'orchestrateur).  # #
#
# 📚 Sources prof (codes)
# [S1] Guide_Scraping_HTML_Python_IA_BOT (1).pdf — extrait : « Toujours produire une sortie structurée (JSON) ».  # #
# [S2] Guide_Scraping_HTML_Python_IA_BOT (1).pdf — extrait : « Mettre en cache les résultats ».  # #
# [S3] Guide_Scraping_HTML_Python_IA_BOT (1).pdf — extrait : « Gérer les erreurs (try/except, timeouts) ».  # #
# [S4] Guide_Scraping_HTML_Python_IA_BOT (1).pdf — extrait : « Toujours définir un User-Agent ».  # #
# [S5] Kick-Off-IA-Bot-Agent-Conversationnel-Intelligent.pdf — extrait : « Scrappez à faible fréquence. Évitez absolument le spam de requêtes ».  # #
# [S6] Kick-Off-IA-Bot-Agent-Conversationnel-Intelligent.pdf — extrait : « Gestion des erreurs : ... stratégies de fallback. ».  # #
# [S7] Projet-IA-BOT-Concevoir-un-agent-pas-un-simple-chatbot (1).pdf — extrait : « Pas de gestion d'erreur ... timeouts. Un agent robuste gère l'incertitude ».  # #
# [S8] Projet-IA-BOT-Concevoir-un-agent-pas-un-simple-chatbot (1).pdf — extrait : « Chaque tool a un contrat clair : inputs structurés et outputs normalisés ».  # #
#
# 🧾 À propos des “numéros d’erreur” (ce que ça veut dire)
# - 200 = OK (la page a été récupérée)  # #
# - 429 = Too Many Requests (le site te “rate-limit”, donc on ralentit / on retry)  # #
# - 500/502/503/504 = erreurs serveur (souvent temporaires, on peut retry)  # #
# - codes internes ex: "http_429_search" = notre libellé lisible : "type d’erreur" + "où" (search/abs/html).  # #

# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# Scraper arXiv CS (ciblé thématique + sortie structurée)  # #  | Étape: [E1] | Source: [S1]  # #
# Objectif :  # #  | Étape: [E1] | Source: [S0]  # #
# - Scraping ciblé sur les thèmes demandés (pas "aspirateur")  # #  | Étape: [E1] | Source: [S0]  # #
# - Sortie JSON structurée (pas de HTML brut envoyé au LLM)  # #  | Étape: [E1] | Source: [S1]  # #
# - Extraction minimale : title/authors/abstract/dates/urls/doi  # #  | Étape: [E1] | Source: [S8]  # #
# - Cache + politesse + robustesse  # #  | Étape: [E4] | Source: [S2]  # #
#   => on cherche via /search/cs puis on filtre via Subjects  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #

# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 📚 Importations  # #  | Étape: [E1] | Source: [S0]  # #
# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
import os  # # Gestion chemins/dossiers # # Respect: cache local stable (sortie disque attendue) | Étape: [E2] | Source: [S2]  # #
import re  # # Regex parsing IDs + catégories # # Respect: extraction ciblée (pas "tout le texte") | Étape: [E1] | Source: [S8]  # #
import json  # # Export JSON # # Respect: sortie structurée JSON | Étape: [E1] | Source: [S1]  # #
import time  # # Politesse (sleep) # # Respect: éviter spam requêtes | Étape: [E4] | Source: [S5]  # #
import random  # # Jitter # # Respect: fréquence raisonnable | Étape: [E1] | Source: [S0]  # #
import datetime  # # Timestamp fichiers # # Respect: traçabilité des fichiers | Étape: [E1] | Source: [S0]  # #
from typing import Dict, Any, List, Tuple, Optional  # # Typage # # Respect: tool prévisible | Étape: [E1] | Source: [S0]  # #

import requests  # # HTTP GET # # Respect: scraping HTML public | Étape: [E2] | Source: [S3]  # #
from bs4 import BeautifulSoup, Tag  # # Parser HTML # # Respect: extraction ciblée d'éléments utiles | Étape: [E1] | Source: [S8]  # #


# ===============================  # #  | Étape: [E1] | Source: [S0] 
# 📌 Résolution robuste des chemins  
# ===============================  

def _find_project_root(start_dir: str) -> str:  # # Définit une fonction qui retrouve la racine du projet à partir d’un dossier de départ (évite d'écrire les fichiers au mauvais endroit) | Étape: [E1] | Source: [S0]  # #
    cur = os.path.abspath(start_dir)  # # Convertit start_dir en chemin absolu : abspath transforme un chemin relatif en chemin complet utilisable partout | Étape: [E1] | Source: [S0]  # #
    while True:  # # Lance une boucle infinie pour remonter dossier par dossier jusqu’à trouver un “marqueur” de racine | Étape: [E1] | Source: [S0]  # #
        if os.path.isdir(os.path.join(cur, "data_lake")):  # # Vérifie si le dossier "data_lake" existe ici : join construit le chemin cur/data_lake, isdir confirme que c’est un dossier | Étape: [E2] | Source: [S2]  # #
            return cur  # # Stoppe la fonction et renvoie cur : return termine la fonction immédiatement avec la racine trouvée | Étape: [E1] | Source: [S0]  # #
        if os.path.isfile(os.path.join(cur, "pyproject.toml")):  # # Vérifie si "pyproject.toml" existe ici : isfile teste la présence d’un fichier marqueur de projet | Étape: [E1] | Source: [S0]  # #
            return cur  # # Renvoie cur comme racine dès qu’un marqueur de projet est trouvé (sortie immédiate) | Étape: [E1] | Source: [S0]  # #
        if os.path.isfile(os.path.join(cur, "requirements.txt")):  # # Vérifie si "requirements.txt" existe : isfile confirme qu’on est probablement à la racine (dépendances Python) | Étape: [E1] | Source: [S0]  # #
            return cur  # # Renvoie cur comme racine si requirements.txt est trouvé (sortie immédiate) | Étape: [E1] | Source: [S0]  # #
        parent = os.path.dirname(cur)  # # Calcule le dossier parent : dirname enlève le dernier segment du chemin (remonte d’un niveau) | Étape: [E1] | Source: [S0]  # #
        if parent == cur:  # # Teste si on est arrivé tout en haut (plus possible de remonter) : parent==cur signifie “racine disque atteinte” | Étape: [E1] | Source: [S0]  # #
            return os.path.abspath(start_dir)  # # Fallback : renvoie le chemin absolu du start_dir (abspath le rend stable même si relatif) | Étape: [E2] | Source: [S6]  # #
        cur = parent  # # Met à jour cur avec le parent pour continuer la remontée dans la boucle | Étape: [E1] | Source: [S0]  # #



# ===============================  # #  | Étape: [E1] | Source: [S0] 
# 🧭 Constantes arXiv 
# ===============================  

ARXIV_BASE = "https://arxiv.org"  # # Définit l’URL de base d’arXiv : on la réutilise pour construire toutes les autres URLs sans les réécrire | Étape: [E2] | Source: [S3]  # #
ARXIV_SEARCH_CS = f"{ARXIV_BASE}/search/cs"  # # Construit l’URL du endpoint de recherche Computer Science : f-string insère ARXIV_BASE dans la chaîne | Étape: [E1] | Source: [S0]  # #

_THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))  # # Récupère le dossier réel du fichier Python : abspath calcule le chemin complet de __file__, dirname garde seulement le dossier | Étape: [E1] | Source: [S0]  # #
PROJECT_ROOT = _find_project_root(_THIS_FILE_DIR)  # # Appelle la fonction de remontée pour trouver la racine du projet (évite d’écrire dans le mauvais dossier si le CWD change) | Étape: [E1] | Source: [S0]  # #
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data_lake", "raw", "cache")  # # Construit le chemin du dossier de cache raw : join assemble proprement les segments (compatible Windows) | Étape: [E2] | Source: [S2]  # #

MAX_RESULTS_HARD_LIMIT = 100  # # Fixe un plafond dur du nombre de résultats pour éviter un scraping trop massif (sécurité/performance) | Étape: [E1] | Source: [S0]  # #
PAGE_SIZE = 50  # # Fixe la taille d’une page arXiv à 50 : sert à paginer proprement sans dépasser la limite attendue | Étape: [E1] | Source: [S0]  # #


# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧯 Robustesse HTTP 
# ===============================
HTTP_RETRY_STATUS = {429, 500, 502, 503, 504}  # # Codes à retry # # Respect: agent robuste (ne pas casser au 1er incident) | Étape: [E2] | Source: [S3]  # #
HTTP_RETRY_MAX = 2  # # Nombre de retries/reessai # # Respect: fréquence raisonnable (pas de spam) | Étape: [E2] | Source: [S3]  # #
HTTP_TIMEOUT_S = 30  # # Timeout # # Respect: robustesse (évite blocage) | Étape: [E2] | Source: [S3]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # # Début de bloc “grand titre” : sert juste de repère visuel dans le fichier
# 🎯 Thèmes demandés -> sous-catégories arXiv autorisées  # #  | Étape: [E1] | Source: [S0]  # # Annonce que l’on va définir la table qui relie un thème (ex: ai_ml) aux catégories arXiv autorisées
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # # Fin de l’en-tête “grand titre” (lisibilité)

THEME_TO_ARXIV_SUBCATS: Dict[str, List[str]] = {  # # Crée un dictionnaire typé (clé=thème, valeur=liste de catégories) : permet de filtrer les résultats arXiv selon le thème choisi | Étape: [E1] | Source: [S0]  # #
    "ai_ml": [  # # Liste des catégories autorisées pour le thème IA/ML : on regroupe ici les sujets arXiv qui couvrent LLM, vision, multimodal, agents | Étape: [E1] | Source: [S0]  # #
        "cs.AI",    # # Catégorie arXiv “Artificial Intelligence” : correspond aux papiers IA/agents/raisonnement | Étape: [E1] | Source: [S0]  # #
        "cs.LG",    # # Catégorie “Machine Learning (CS)” : correspond aux papiers ML côté informatique | Étape: [E1] | Source: [S0]  # #
        "cs.CL",    # # Catégorie “Computation and Language” : correspond aux papiers NLP/LLM/traitement du langage | Étape: [E1] | Source: [S0]  # #
        "cs.CV",    # # Catégorie “Computer Vision” : correspond aux papiers vision / image / multimodal | Étape: [E1] | Source: [S0]  # #
        "cs.MA",    # # Catégorie “Multiagent Systems” : correspond aux systèmes multi-agents (agents qui coopèrent) | Étape: [E1] | Source: [S0]  # #
        "cs.NE",    # # Catégorie “Neural and Evolutionary Computing” : correspond aux approches réseaux neuronaux / deep learning (historique) | Étape: [E1] | Source: [S0]  # #
        "stat.ML",  # # Catégorie “Machine Learning (Stats)” : correspond aux cross-lists fréquentes ML côté statistiques (évite de rater des papiers) | Étape: [E1] | Source: [S0]  # #
        "eess.IV",  # # Catégorie “Image and Video Processing” : correspond à vision/image parfois classée hors CS (évite de rater des papiers vision) | Étape: [E1] | Source: [S0]  # #
    ],
    "algo_ds": ["cs.DS", "cs.CC"],  # # Déclare les catégories autorisées pour “Algorithmique & Data Structures” : cs.DS=structures de données, cs.CC=complexité | Étape: [E1] | Source: [S0]  # #
    "net_sys": ["cs.NI", "cs.DC", "cs.OS"],  # # Déclare les catégories autorisées pour “Réseaux & Systèmes” : cs.NI=réseau, cs.DC=distribué, cs.OS=systèmes d’exploitation | Étape: [E1] | Source: [S0]  # #
    "cyber_crypto": ["cs.CR"],  # # Déclare les catégories autorisées pour “Cybersécurité & Crypto” : cs.CR=cryptographie et sécurité | Étape: [E1] | Source: [S0]  # #
    "pl_se": ["cs.PL", "cs.SE", "cs.LO"],  # # Déclare les catégories autorisées pour “Langages & Génie logiciel” : cs.PL=langages, cs.SE=génie logiciel, cs.LO=logique en CS | Étape: [E1] | Source: [S0]  # #
    "hci_data": ["cs.HC", "cs.IR", "cs.DB", "cs.MM"],  # # Déclare les catégories autorisées pour “HCI & Données” : cs.HC=interaction, cs.IR=recherche d’info, cs.DB=bases de données, cs.MM=multimédia | Étape: [E1] | Source: [S0]  # #
}  # # Ferme le dictionnaire : cette table sera utilisée plus loin pour filtrer/valider les catégories extraites depuis la page arXiv | Étape: [E1] | Source: [S0]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧠 Keywords fallback (si le site est modifié et que l'on perd les catégories (cs.AI etc.), on cherche via des mots-clés (AI/transformer/LLM…)  # #  
# ============================================================  
THEME_KEYWORDS: Dict[str, List[str]] = {  # # Support # # Respect: filtrage pertinence si catégories manquantes | Étape: [E1] | Source: [S0]  # #
    "ai_ml": ["machine learning", "deep learning", "llm", "agent", "transformer", "multimodal", "computer vision"],
    "algo_ds": ["algorithm", "data structure", "complexity", "graph", "optimization"],
    "net_sys": ["network", "distributed", "operating system", "cloud", "systems"],
    "cyber_crypto": ["security", "privacy", "cryptography", "attack", "defense", "malware"],
    "pl_se": ["programming language", "compiler", "software engineering", "static analysis", "type system"],
    "hci_data": ["human-computer interaction", "information retrieval", "database", "multimedia", "ranking", "search"],
}

# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 📦 Champs renvoyés (minimal)  
# =============================== 
SUPPORTED_FIELDS = [  # # Liste Python = "contrat" des champs renvoyés (format standard et prévisible) pour découpler le scraping du reste | Étape: [E1] | Source: [S1]  # #
    "arxiv_id",  # # Champ JSON arxiv_id = identifiant unique arXiv du papier (FR: ID du papier) utilisé pour relier /abs et /pdf | Étape: [E1] | Source: [S1]  # #
    "title",  # # Champ JSON title = titre du papier (FR: nom du papier) pour l'affichage et le contexte LLM | Étape: [E1] | Source: [S1]  # #
    "authors",  # # Champ JSON authors = liste des auteurs (FR: auteurs) pour attribuer le travail et contextualiser la source | Étape: [E1] | Source: [S1]  # #
    "abstract",  # # Champ JSON abstract = résumé du papier (FR: résumé) pour comprendre rapidement le contenu sans HTML brut | Étape: [E1] | Source: [S1]  # #
    "method",  # # Champ JSON method = section Méthode (FR: "Méthode") extraite de /html pour enrichir sans aspirer toute la page | Étape: [E1] | Source: [S8]  # #
    "references",  # # Champ JSON references = section Références (FR: "Références") pour garder les sources citées (utile QA) | Étape: [E1] | Source: [S8]  # #
    "submitted_date",  # # Champ JSON submitted_date = date de soumission (FR: date d'envoi à arXiv) pour la traçabilité temporelle | Étape: [E1] | Source: [S1]  # #
    "abs_url",  # # Champ JSON abs_url = lien arXiv /abs (FR: page détails) pour relire/diagnostiquer la source | Étape: [E1] | Source: [S1]  # #
    "pdf_url",  # # Champ JSON pdf_url = lien arXiv /pdf (FR: téléchargement PDF) pour accéder au document complet | Étape: [E1] | Source: [S1]  # #
    "doi",  # # Champ JSON doi = identifiant DOI (FR: identifiant éditeur) si présent, pour relier à la publication officielle | Étape: [E1] | Source: [S1]  # #
    "versions",  # # Champ JSON versions = historique des versions v1,v2... (FR: versions) pour savoir ce qui a changé | Étape: [E1] | Source: [S1]  # #
    "last_updated_raw",  # # Champ JSON last_updated_raw = dernière mise à jour brute (FR: dernière maj) depuis l'historique arXiv | Étape: [E1] | Source: [S1]  # #
    "primary_category",  # # Champ JSON primary_category = catégorie principale (FR: thème principal) ex: cs.AI pour filtrer thématiquement | Étape: [E1] | Source: [S1]  # #
    "all_categories",  # # Champ JSON all_categories = toutes les catégories (FR: tags/thèmes) pour gérer cross-list et filtrage robuste | Étape: [E1] | Source: [S1]  # #
    "missing_fields",  # # Champ JSON missing_fields = liste des champs non trouvés (FR: champs manquants) pour diagnostiquer sans planter | Étape: [E2] | Source: [S3]  # #
    "errors",  # # Champ JSON errors = erreurs liées à cet item (FR: erreurs papier) pour remonter les soucis proprement | Étape: [E2] | Source: [S3]  # #
]



# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧩 Helpers base  # # Regroupe des petites fonctions utilitaires réutilisées partout (évite duplication et erreurs) | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def ensure_dir(path: str) -> None:  # # Fonction ensure_dir = garantit que le dossier existe avant d’écrire des fichiers (cache/exports) | Étape: [E2] | Source: [S2]  # #
    os.makedirs(path, exist_ok=True)  # # Crée le dossier path ; exist_ok=True = ne lève pas d’erreur si déjà présent (évite crash) | Étape: [E2] | Source: [S2]  # #


def now_iso_for_filename() -> str:  # # Fonction now_iso_for_filename = génère un timestamp lisible pour nommer les fichiers sans collision | Étape: [E1] | Source: [S0]  # #
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # strftime = formate la date/heure en texte "YYYYMMDD_HHMMSS" pour tracer quand le fichier a été produit | Étape: [E1] | Source: [S0]  # #

def is_empty(value: Any) -> bool:  # # Détection "vide" # # Respect: qualité sortie JSON | Étape: [E1] | Source: [S1]  # #
    if value is None:  # # None # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
        return True  # # Vide # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
    if isinstance(value, str):  # # String # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
        v = value.strip()  # # Trim # # Respect: nettoyage | Étape: [E1] | Source: [S0]  # #
        if v == "":  # # Vide # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
            return True  # # Vide | Étape: [E1] | Source: [S0]  # #
        if v.lower() in {"n/a", "null", "none"}:  # # Marqueurs # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
            return True  # # Vide | Étape: [E1] | Source: [S0]  # #
    if isinstance(value, list):  # # Liste # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
        return len(value) == 0  # # Vide si liste vide # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
    return False  # # Non vide # # Respect: qualité | Étape: [E1] | Source: [S0]  # #


def sleep_polite(min_s: float = 1.2, max_s: float = 2.0) -> None:  # # Politesse # # Respect: fréquence raisonnable | Étape: [E4] | Source: [S5]  # #
    time.sleep(random.uniform(min_s, max_s))  # # Jitter # # Respect: anti-spam | Étape: [E4] | Source: [S5]  # #


def save_text_file(folder: str, filename: str, content: str) -> str:  # # Sauvegarde # # Respect: cache local visible | Étape: [E2] | Source: [S2]  # #
    ensure_dir(folder)  # # Assurer dossier # # Respect: cache disque | Étape: [E2] | Source: [S2]  # #
    path = os.path.join(folder, filename)  # # Chemin # # Respect: cohérence | Étape: [E1] | Source: [S0]  # #
    with open(path, "w", encoding="utf-8") as f:  # # UTF-8 # # Respect: robustesse encodage | Étape: [E1] | Source: [S0]  # #
        f.write(content)  # # Écriture # # Respect: traçabilité/debug | Étape: [E1] | Source: [S0]  # #
    return path  # # Retour chemin # # Respect: utilisateur peut retrouver le fichier | Étape: [E1] | Source: [S0]  # #


def normalize_url(href: str) -> str:  # # Normalise URL # # Respect: champs propres | Étape: [E1] | Source: [S0]  # #
    if not href:  # # Si vide # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        return ""  # # Retour vide # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
    h = href.strip()  # # Trim # # Respect: sortie propre | Étape: [E1] | Source: [S0]  # #
    if h.startswith("//"):  # # Schéma manquant # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        return "https:" + h  # # Force https # # Respect: sortie valide | Étape: [E2] | Source: [S3]  # #
    if h.startswith("/"):  # # Relatif # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        return ARXIV_BASE + h  # # Absolu # # Respect: sortie valide | Étape: [E1] | Source: [S0]  # #
    return h  # # Déjà absolu # # Respect: sortie valide | Étape: [E1] | Source: [S0]  # #

def abs_url(arxiv_id: str) -> str:  # # Fonction abs_url = fabrique l’URL “fiche” /abs à partir de l’identifiant arXiv (utile si le HTML ne donne pas le lien complet) | Étape: [E1] | Source: [S0]  # #
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # f-string = insère arxiv_id dans le modèle d’URL pour obtenir ex: https://arxiv.org/abs/2601.08457 | Étape: [E1] | Source: [S0]  # #


def pdf_url(arxiv_id: str) -> str:  # # Fonction pdf_url = fabrique l’URL de téléchargement /pdf à partir de l’identifiant arXiv (fallback si le lien PDF est absent) | Étape: [E1] | Source: [S0]  # #
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # f-string = construit ex: https://arxiv.org/pdf/2601.08457 pour télécharger/ouvrir le PDF | Étape: [E1] | Source: [S0]  # #


def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # Fonction compute_missing_fields = liste les champs manquants d’un item (contrôle qualité) pour savoir ce que le parsing n’a pas trouvé | Étape: [E1] | Source: [S0]  # #
    missing: List[str] = []  # # On crée une liste vide “missing” qui va stocker les noms des champs absents (diagnostic) | Étape: [E1] | Source: [S0]  # #
    for f in SUPPORTED_FIELDS:  # # Boucle sur tous les champs attendus (contrat stable) pour vérifier chacun systématiquement | Étape: [E1] | Source: [S1]  # #
        if is_empty(item.get(f)):  # # is_empty() teste si la valeur est vide (None, "", liste vide…) → ici on l’utilise pour détecter un champ non rempli | Étape: [E2] | Source: [S6]  # #
            missing.append(f)  # # On ajoute le nom du champ manquant dans la liste pour pouvoir le renvoyer dans le JSON final | Étape: [E2] | Source: [S6]  # #
    return missing  # # On renvoie la liste des champs manquants → ça aide à debug sans casser le reste du pipeline | Étape: [E1] | Source: [S1]  # #


def _detect_weird_page_signals(html: str) -> Dict[str, bool]:  # # Fonction _detect_weird_page_signals = repère des “signaux” de page anormale (anti-bot, consentement, zéro résultat) pour diagnostiquer pourquoi le parsing échoue | Étape: [E2] | Source: [S6]  # #
    h = (html or "").lower()  # # lower() met tout en minuscules pour faire des tests “in” insensibles à la casse (plus robuste) | Étape: [E1] | Source: [S0]  # #
    return {  # # On renvoie un dict de drapeaux booléens (diagnostic lisible dans le JSON) | Étape: [E2] | Source: [S6]  # #
        "contains_we_are_sorry": ("we are sorry" in h),  # # True si on voit un message de blocage du site (souvent anti-bot) | Étape: [E2] | Source: [S6]  # #
        "contains_robot": ("robot" in h),  # # True si la page mentionne “robot” (indice de détection automatique) | Étape: [E2] | Source: [S6]  # #
        "contains_captcha": ("captcha" in h),  # # True si un CAPTCHA apparaît (le scraper ne peut pas résoudre ça) | Étape: [E2] | Source: [S6]  # #
        "contains_consent": ("consent" in h or "cookie" in h),  # # True si une page cookies/consent bloque le contenu (HTML différent) | Étape: [E2] | Source: [S6]  # #
        "contains_no_results": ("no results found" in h),  # # True si la page annonce “aucun résultat” (pas un bug de parsing) | Étape: [E2] | Source: [S6]  # #
    }  # # Fin dict diagnostic (pas d’effet sur scraping, juste une aide de debug) | Étape: [E2] | Source: [S6]  # #


def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # Fonction http_get_text = fait un GET HTTP et renvoie (HTML, code HTTP) sans faire crasher le tool si réseau/timeout | Étape: [E2] | Source: [S3]  # #
    headers = {  # # On prépare les en-têtes HTTP envoyés à arXiv (ça aide à être accepté + parsing stable) | Étape: [E2] | Source: [S0]  # #
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/4.1",  # # User-Agent = “carte d’identité” HTTP ; ici on met un UA clair pour éviter d’être vu comme un bot suspect | Étape: [E2] | Source: [S4]  # #
        "Accept-Language": "en-US,en;q=0.9",  # # Accept-Language = demande une page en anglais pour éviter des variations de texte selon la langue | Étape: [E2] | Source: [S0]  # #
    }  # # Fin headers | Étape: [E2] | Source: [S0]  # #
    try:  # # try = on encapsule l’appel réseau pour gérer proprement les erreurs au lieu de crasher tout le script | Étape: [E2] | Source: [S3]  # #
        resp = session.get(url, headers=headers, timeout=timeout_s)  # # session.get() exécute le GET ; timeout évite que ça bloque indéfiniment si le site répond mal | Étape: [E2] | Source: [S3]  # #
        return resp.text, resp.status_code  # # On renvoie le HTML + le status_code (200, 429, 500...) pour diagnostic + contrat stable | Étape: [E1] | Source: [S1]  # #
    except requests.RequestException as e:  # # requests.RequestException = toutes les erreurs réseau (timeout, DNS, connexion refusée, etc.) | Étape: [E2] | Source: [S0]  # #
        return f"REQUEST_EXCEPTION: {str(e)}", 0  # # On renvoie un “HTML” texte d’erreur + code 0 (0 = erreur locale, pas une réponse HTTP du serveur) | Étape: [E2] | Source: [S3]  # #

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # Fonction build_search_url = construit l’URL complète de recherche arXiv “/search/cs” avec query + pagination + tri (pour appeler arXiv de façon standard) | Étape: [E1] | Source: [S0]  # #
    q = requests.utils.quote((query or "").strip())  # # requests.utils.quote() encode la requête (espaces→%20, guillemets→%22…) pour qu’elle soit valide dans une URL HTTP | Étape: [E1] | Source: [S0]  # #
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # f-string = assemble l’URL “base” avec paramètres: query (mots-clés), size (nb résultats/page), start (offset pagination) | Étape: [E1] | Source: [S0]  # #
    s = (sort or "relevance").strip().lower()  # # On normalise le champ sort (par défaut “relevance”), trim + lower pour comparer sans se tromper (robuste aux entrées utilisateur) | Étape: [E1] | Source: [S0]  # #
    if s in {"submitted_date", "submitted", "recent"}:  # # Si l’utilisateur veut trier par date de soumission (ou un alias), on active le tri “récents d’abord” | Étape: [E1] | Source: [S0]  # #
        return base + "&order=-announced_date_first"  # # On ajoute le paramètre arXiv “order=-announced_date_first” pour renvoyer les papiers les plus récents en premier | Étape: [E1] | Source: [S0]  # #
    return base  # # Sinon, on retourne l’URL de base (tri “relevance” par défaut) pour garder un comportement stable et prévisible | Étape: [E1] | Source: [S0]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧲 Extraction catégories depuis "Subjects" + tags (robuste)  # #  | Étape: [E1] | Source: [S8]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
_RE_ANY_CAT = re.compile(r"\(((?:cs|stat|eess)\.[A-Z]{2})\)")  # # Regex cat # # Respect: inclut cross-lists (stat.ML/eess.IV) | Étape: [E1] | Source: [S0]  # #
_RE_ARXIV_ID = re.compile(r"/abs/([^?#/]+)")  # # Regex ID # # Respect: extraction stable | Étape: [E1] | Source: [S8]  # #


def extract_categories_from_result(li: Tag) -> Tuple[str, List[str]]:  # # Lit catégories # # Respect: filtrage thématique après search/cs | Étape: [E1] | Source: [S8]  # #
    cats: List[str] = []  # # Init # # Respect: structuration | Étape: [E1] | Source: [S0]  # #

    # (1) Méthode robuste: tags visibles (quand arXiv rend des badges)
    for span in li.select("span.tag"):  # # Parcours tags # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
        t = (span.get_text(" ", strip=True) or "").strip()  # # Texte tag # # Respect: nettoyage | Étape: [E1] | Source: [S0]  # #
        if re.fullmatch(r"(?:cs|stat|eess)\.[A-Z]{2}", t):  # # Si ressemble à une cat # # Respect: filtrage fiable | Étape: [E1] | Source: [S0]  # #
            cats.append(t)  # # Ajoute # # Respect: structuration | Étape: [E1] | Source: [S0]  # #

    # (2) Méthode fallback: regex sur la ligne "Subjects:  (cs.XX);  (stat.ML)"
    if not cats:  # # Si tags absents # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        txt = li.get_text(" ", strip=True)  # # Texte bloc (minimum) # # Respect: extraction juste pour cat | Étape: [E1] | Source: [S8]  # #
        cats = _RE_ANY_CAT.findall(txt)  # # Extrait cats # # Respect: mapping demandé | Étape: [E1] | Source: [S0]  # #

    # Dédoublonnage en gardant l'ordre
    cats = list(dict.fromkeys(cats))  # # Dédoublonne # # Respect: sortie propre | Étape: [E1] | Source: [S0]  # #
    primary = cats[0] if cats else ""  # # Premier # # Respect: structuration | Étape: [E1] | Source: [S0]  # #
    return primary, cats  # # Retour # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧾 Parsing page search/cs -> items minimaux  # #  | Étape: [E1] | Source: [S1]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def parse_search_page(html: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:  # # Parse + diag # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #
    soup = BeautifulSoup(html, "lxml")  # # Parse # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""  # # Titre page # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
    weird = _detect_weird_page_signals(html)  # # Détection anti-bot/no-results # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #

    diag: Dict[str, Any] = {  # # Diagnostic # # Respect: traçabilité | Étape: [E2] | Source: [S6]  # #
        "page_title": page_title,  # # Titre # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "has_abs_links": ("/abs/" in (html or "")),  # # Indicateur principal # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        **weird,  # # Drapeaux # # Respect: debug | Étape: [E2] | Source: [S6]  # #
    }

    items: List[Dict[str, Any]] = []  # # Résultats # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #

    # Sélecteur principal (arXiv actuel)
    result_nodes = soup.select("ol.breathe-horizontal li.arxiv-result")  # # Noeuds résultats # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
    diag["selector_count_arxiv_result"] = len(result_nodes)  # # Compte # # Respect: debug | Étape: [E2] | Source: [S6]  # #
    # Fallback: si DOM change, on reconstruit via liens /abs/
    if not result_nodes and diag["has_abs_links"]:  # # Si le sélecteur principal ne trouve aucun bloc résultat MAIS que le HTML contient des liens “/abs/”, on active un plan B pour ne pas renvoyer 0 items juste à cause d’un changement de DOM | Étape: [E2] | Source: [S6]  # #
        diag["fallback_mode"] = "abs_links"  # # On note dans le diagnostic qu’on est passé en mode fallback “abs_links” (ça explique pourquoi certains champs sont vides) | Étape: [E2] | Source: [S6]  # #
        abs_ids = _RE_ARXIV_ID.findall(html or "")  # # findall() extrait tous les identifiants arXiv présents dans les URLs /abs/... du HTML, même si les classes HTML ont changé | Étape: [E1] | Source: [S8]  # #
        abs_ids = list(dict.fromkeys(abs_ids))[:PAGE_SIZE]  # # dict.fromkeys() retire les doublons en gardant l’ordre, puis on limite à PAGE_SIZE (=50) pour contrôler le volume et respecter la pagination | Étape: [E1] | Source: [S0]  # #
        for arxiv_id in abs_ids:  # # On parcourt chaque identifiant trouvé pour reconstruire des items minimaux (structure stable même sans parsing complet) | Étape: [E1] | Source: [S1]  # #
            items.append({  # # On ajoute un “item minimal” (dict) : on garde uniquement les champs indispensables et on laisse le reste vide plutôt que d’envoyer du HTML brut | Étape: [E1] | Source: [S1]  # #
                "arxiv_id": arxiv_id,  # # Identifiant arXiv (FR: l’ID unique du papier) : sert à construire les URLs et à référencer le papier même si le reste n’a pas été parsé | Étape: [E1] | Source: [S0]  # #
                "title": "",  # # Titre vide car indisponible en fallback (on préfère vide plutôt que faux) | Étape: [E1] | Source: [S0]  # #
                "authors": [],  # # Auteurs vides en fallback (liste vide = format stable côté API) | Étape: [E1] | Source: [S0]  # #
                "abstract": "",  # # Résumé (abstract) vide en fallback (on ne devine pas) | Étape: [E1] | Source: [S0]  # #
                "submitted_date": "",  # # Date de soumission vide en fallback (on la remplira plus tard via /abs si besoin) | Étape: [E1] | Source: [S0]  # #
                "abs_url": abs_url(arxiv_id),  # # abs_url() fabrique l’URL /abs/{id} (FR: page fiche du papier) pour pouvoir enrichir ensuite sans dépendre du HTML de recherche | Étape: [E1] | Source: [S0]  # #
                "pdf_url": pdf_url(arxiv_id),  # # pdf_url() fabrique l’URL /pdf/{id} (FR: lien direct PDF) pour garder une sortie utile même en mode fallback | Étape: [E1] | Source: [S0]  # #
                "primary_category": "",  # # Catégorie principale vide en fallback (on évite les faux labels) | Étape: [E1] | Source: [S0]  # #
                "all_categories": [],  # # Toutes catégories vides en fallback (liste stable côté API) | Étape: [E1] | Source: [S0]  # #
            })
        return items, diag  # # On retourne immédiatement (items + diag) : c’est un retour contrôlé/traçable plutôt qu’un crash ou un “0 résultat” incompréhensible | Étape: [E2] | Source: [S6]  # #

    # Mode normal
    for li in result_nodes:  # # On parcourt chaque bloc résultat “li.arxiv-result” pour extraire les champs utiles de façon ciblée (pas “tout le HTML”) | Étape: [E1] | Source: [S8]  # #
        title_el = li.select_one("p.title")  # # select_one() récupère la balise du titre (p.title) : extraction précise d’un champ essentiel | Étape: [E1] | Source: [S0]  # #
        authors_el = li.select_one("p.authors")  # # select_one() récupère la balise des auteurs (p.authors) : extraction précise d’un champ essentiel | Étape: [E1] | Source: [S0]  # #
        abstract_el = li.select_one("span.abstract-full")  # # select_one() récupère la balise du résumé complet (span.abstract-full) : extraction précise sans prendre toute la page | Étape: [E1] | Source: [S0]  # #
        submitted_el = li.select_one("p.is-size-7")  # # select_one() récupère le bloc “Submitted …” (p.is-size-7) : utile pour la date | Étape: [E1] | Source: [S0]  # #

        abs_a = li.select_one('p.list-title a[href*="/abs/"]')  # # select_one() récupère le lien vers /abs/ (FR: page fiche du papier), car c’est la source la plus stable pour récupérer l’ID arXiv | Étape: [E1] | Source: [S0]  # #
        pdf_a = li.select_one('p.list-title a[href*="/pdf/"]')  # # select_one() récupère le lien vers /pdf/ (FR: téléchargement du PDF), car c’est un lien utile à renvoyer à l’utilisateur | Étape: [E1] | Source: [S0]  # #
        abs_href = normalize_url(abs_a.get("href") if abs_a else "")  # # .get("href") lit l’attribut href, puis normalize_url() convertit en URL absolue (FR: URL propre et utilisable) | Étape: [E1] | Source: [S0]  # #
        pdf_href = normalize_url(pdf_a.get("href") if pdf_a else "")  # # Même logique pour le PDF : URL absolue pour éviter les liens relatifs qui cassent | Étape: [E1] | Source: [S0]  # #

        arxiv_id = ""  # # On initialise l’identifiant arXiv vide : on le remplira uniquement si on l’extrait proprement (évite valeurs fausses) | Étape: [E1] | Source: [S0]  # #
        m = re.search(r"/abs/([^?#/]+)", abs_href) if abs_href else None  # # re.search() cherche “/abs/{id}” dans l’URL pour isoler l’ID (ici on l’utilise pour extraire un identifiant stable) | Étape: [E1] | Source: [S8]  # #
        if m:  # # Si la regex a trouvé un ID, on sécurise le remplissage (sinon on garde vide) | Étape: [E1] | Source: [S0]  # #
            arxiv_id = m.group(1).strip()  # # group(1) récupère la partie capturée (= l’ID), strip() enlève les espaces parasites | Étape: [E1] | Source: [S0]  # #

        title_txt = title_el.get_text(" ", strip=True) if title_el else ""  # # get_text() récupère le texte du titre (FR: le nom du papier) ; strip=True nettoie pour éviter bruit/espaces | Étape: [E1] | Source: [S8]  # #
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # get_text() récupère la chaîne des auteurs (FR: noms), en mode “texte propre” | Étape: [E1] | Source: [S8]  # #
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # On transforme la chaîne en liste (split “,”), strip() nettoie chaque nom : sortie structurée stable pour l’API | Étape: [E1] | Source: [S1]  # #
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # get_text() récupère le résumé (abstract) complet quand disponible, sans prendre toute la page | Étape: [E1] | Source: [S8]  # #
        abstract = abstract.replace("△ Less", "").strip()  # # On enlève le texte UI “△ Less” et on strip() : réduit le bruit pour garder uniquement l’info utile | Étape: [E1] | Source: [S0]  # #

        submitted_date = ""  # # On initialise la date de soumission vide (on la remplit seulement si on l’extrait vraiment) | Étape: [E1] | Source: [S0]  # #
        if submitted_el:  # # Si le bloc date existe, on tente une extraction contrôlée (sinon on laisse vide) | Étape: [E1] | Source: [S0]  # #
            txt = submitted_el.get_text(" ", strip=True)  # # get_text() récupère la phrase “Submitted …” en texte propre, pour que la regex fonctionne de façon prévisible | Étape: [E1] | Source: [S8]  # #
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # re.search() extrait uniquement la portion date après “Submitted” (on cible l’info utile, pas toute la phrase) | Étape: [E1] | Source: [S8]  # #
            if m3:  # # Si la regex a trouvé une date, on la récupère ; sinon on laisse vide (robuste) | Étape: [E1] | Source: [S0]  # #
                submitted_date = m3.group(1).strip()  # # group(1) = date capturée ; strip() pour nettoyage final | Étape: [E1] | Source: [S0]  # #

        primary_cat, all_cats = extract_categories_from_result(li)  # # Appel de extract_categories_from_result() : on récupère catégories pour filtrer par thème (et rester “ciblé” sur les sujets demandés) | Étape: [E1] | Source: [S8]  # #

        if arxiv_id and is_empty(abs_href):  # # Si on a un ID mais pas d’URL /abs valide (rare), on applique un fallback pour garantir un lien utilisable | Étape: [E2] | Source: [S6]  # #
            abs_href = abs_url(arxiv_id)  # # abs_url() reconstruit une URL /abs/{id} correcte : sortie utile même si le HTML manquait le lien | Étape: [E1] | Source: [S0]  # #
        if arxiv_id and is_empty(pdf_href):  # # Si on a un ID mais pas d’URL PDF valide, on applique un fallback pour garantir le lien PDF | Étape: [E2] | Source: [S6]  # #
            pdf_href = pdf_url(arxiv_id)  # # pdf_url() reconstruit une URL /pdf/{id} correcte : sortie utile même si le HTML manquait le lien | Étape: [E1] | Source: [S0]  # #

        items.append({  # # On ajoute un dict “papier” à la liste items : c’est le format standard que l’API et le LLM consommeront (sans HTML brut) | Étape: [E1] | Source: [S1]  # #
            "arxiv_id": arxiv_id,  # # arxiv_id (FR: identifiant unique du papier) : clé de référence pour retrouver la fiche et le PDF | Étape: [E1] | Source: [S0]  # #
            "title": title_txt,  # # title (FR: titre du papier) : sert à afficher et à filtrer la pertinence | Étape: [E1] | Source: [S0]  # #
            "authors": authors,  # # authors (FR: liste des auteurs) : format liste pour être stable côté API | Étape: [E1] | Source: [S0]  # #
            "abstract": abstract,  # # abstract (FR: résumé) : texte principal utile, extrait proprement sans le HTML complet | Étape: [E1] | Source: [S0]  # #
            "method": "",  # # method (FR: “méthode”) : placeholder rempli plus tard via /html, pour ajouter la section “Méthode” sans aspirer toute la page | Étape: [E2] | Source: [S8]  # #
            "references": [],  # # references (FR: “références/bibliographie”) : placeholder liste, rempli plus tard via /html, pour garder uniquement la bibliographie sans HTML brut | Étape: [E2] | Source: [S8]  # #
            "submitted_date": submitted_date,  # # submitted_date (FR: date de soumission) : utile pour trier/évaluer la fraîcheur des papiers | Étape: [E1] | Source: [S0]  # #
            "abs_url": abs_href,  # # abs_url (FR: lien de la fiche /abs) : page de détails, base pour enrichissement DOI/versions | Étape: [E1] | Source: [S0]  # #
            "pdf_url": pdf_href,  # # pdf_url (FR: lien PDF /pdf) : téléchargement direct du papier | Étape: [E1] | Source: [S0]  # #
            "primary_category": primary_cat,  # # primary_category (FR: catégorie principale) : sert au filtrage thématique demandé | Étape: [E1] | Source: [S0]  # #
            "all_categories": all_cats,  # # all_categories (FR: toutes les catégories) : sert à détecter cross-listing et éviter de rater des papiers pertinents | Étape: [E1] | Source: [S0]  # #
        })

    return items, diag  # # On retourne (items, diag) : items = données structurées ; diag = explications debug (fallback/anti-bot/compteurs) pour robustesse et traçabilité | Étape: [E2] | Source: [S6]  # #

# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🔎 Parsing /abs (DOI + versions + abstract fallback)           # #  | Étape: [E2] | Source: [S6]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # La fonction lit le HTML de la page /abs et en extrait UNIQUEMENT des champs stables (doi, abstract, versions) pour enrichir l’item sans “aspirer” tout le site | Étape: [E1] | Source: [S0]  # #
    soup = BeautifulSoup(abs_html, "lxml")  # # BeautifulSoup(...,"lxml") transforme le HTML brut en arbre navigable pour pouvoir cibler des blocs précis (principe: extraction ciblée, pas du texte global) | Étape: [E1] | Source: [S8]  # #
    out: Dict[str, Any] = {"doi": "", "versions": [], "last_updated_raw": "", "abstract": ""}  # # On initialise un dict “contrat stable” avec valeurs vides (évite KeyError et garantit toujours les mêmes clés côté API) | Étape: [E1] | Source: [S1]  # #

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # select_one() cherche le premier lien DOI (éditeur) dans le tableau “doi” de arXiv : on vise un sélecteur précis pour éviter de prendre du bruit | Étape: [E1] | Source: [S0]  # #
    if doi_a:  # # Si le lien DOI existe, on remplit le champ ; sinon on laisse vide (robuste) | Étape: [E1] | Source: [S0]  # #
        out["doi"] = doi_a.get_text(" ", strip=True)  # # get_text(...,strip=True) récupère le texte lisible du lien DOI (FR: identifiant éditeur) sans espaces parasites | Étape: [E1] | Source: [S8]  # #

    abs_el = soup.select_one("blockquote.abstract")  # # select_one() cible le bloc “Abstract” de /abs (c’est la source la plus fiable si l’abstract manquait sur la page de recherche) | Étape: [E1] | Source: [S0]  # #
    if abs_el:  # # Si le bloc Abstract existe, on extrait son texte ; sinon on garde vide (pas d’invention) | Étape: [E1] | Source: [S0]  # #
        txt = abs_el.get_text(" ", strip=True)  # # get_text() extrait le contenu texte de l’Abstract en supprimant les retours/espaces inutiles | Étape: [E1] | Source: [S8]  # #
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()  # # re.sub() enlève le préfixe “Abstract:” (UI) pour ne garder que le contenu utile, puis strip() nettoie | Étape: [E1] | Source: [S0]  # #
        out["abstract"] = txt  # # On stocke l’abstract nettoyé dans le dict de sortie (contrat stable) | Étape: [E1] | Source: [S1]  # #

    versions: List[Dict[str, str]] = []  # # On prépare une liste structurée pour l’historique des versions (v1, v2…) au format dict, pour être facile à consommer par l’API | Étape: [E1] | Source: [S0]  # #
    for li in soup.select("div.submission-history li"):  # # soup.select() récupère toutes les lignes de l’historique de soumission (submission-history) pour extraire les versions proprement | Étape: [E1] | Source: [S8]  # #
        txt = li.get_text(" ", strip=True)  # # get_text() récupère le texte de chaque ligne (ex: “[v2] Tue, …”) sous forme propre | Étape: [E1] | Source: [S8]  # #
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # re.search() repère le numéro de version “[vX]” et le reste de la ligne (date/infos) pour structurer sans dépendre de micro-HTML | Étape: [E1] | Source: [S8]  # #
        if m:  # # Si la ligne correspond au pattern (sécurité), on ajoute une entrée version ; sinon on ignore (robuste) | Étape: [E1] | Source: [S0]  # #
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # On enregistre version=vX + raw=texte date ; group() récupère les groupes capturés ; strip() nettoie | Étape: [E1] | Source: [S1]  # #
    out["versions"] = versions  # # On attache la liste des versions au dict de sortie (contrat stable) | Étape: [E1] | Source: [S1]  # #
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # On prend la dernière entrée versions[-1] comme “dernière mise à jour” ; si liste vide, on met "" (évite crash) | Étape: [E1] | Source: [S0]  # #

    return out  # # On renvoie le dict d’enrichissement /abs (clé->valeur), utilisé ensuite pour compléter les items sans changer le main | Étape: [E1] | Source: [S1]  # #


# ============================================================  # #
# 🧩 Parsing /html arXiv : Method + References (ciblé)           # # Étape: [E5] | Source: [S8]  # #
# ============================================================  # #

def extract_html_url_from_abs(abs_html: str, arxiv_id: str) -> str:  # # La fonction cherche l’URL /html depuis la page /abs pour pouvoir récupérer “Method” et “References” (si disponibles) sans supposer que tous les papiers ont du HTML | Étape: [E5] | Source: [S8]  # #
    soup = BeautifulSoup(abs_html, "lxml")  # # Parser /abs en arbre HTML pour pouvoir trouver un lien “/html/...” via un sélecteur stable au lieu de regex fragile | Étape: [E5] | Source: [S0]  # #
    a = soup.select_one('a[href^="/html/"], a[href*="/html/"]')  # # select_one() prend le premier lien qui pointe vers /html (FR: version HTML du papier) s’il existe, sinon None | Étape: [E5] | Source: [S0]  # #
    if not a:  # # Si aucun lien /html n’est présent (fréquent), on retourne vide pour ne pas forcer une requête inutile | Étape: [E5] | Source: [S0]  # #
        return ""  # # Retour vide = “pas de HTML disponible”, le reste du pipeline garde method/references vides (contrat stable) | Étape: [E5] | Source: [S0]  # #
    href = (a.get("href") or "").strip()  # # .get("href") lit l’attribut href du lien, or "" évite None, strip() nettoie : on sécurise l’entrée avant normalisation | Étape: [E1] | Source: [S1]  # #
    if not href:  # # Si href est vide après nettoyage, on renvoie vide (robuste) | Étape: [E5] | Source: [S0]  # #
        return ""  # # Pas de lien utilisable | Étape: [E5] | Source: [S0]  # #
    return normalize_url(href)  # # normalize_url() transforme un lien relatif en URL absolue (FR: lien cliquable stable) | Étape: [E1] | Source: [S1]  # #


def parse_arxiv_html_method_and_references(html: str) -> tuple[str, list[str]]:  # # La fonction extrait DEUX blocs ciblés dans /html : “Method” (texte) + “References” (liste) pour répondre au prof sans scraper tout le contenu | Étape: [E5] | Source: [S8]  # #
    soup = BeautifulSoup(html, "lxml")  # # Parser le HTML /html en arbre afin de sélectionner des sections précises (robustesse si l’ordre du texte change) | Étape: [E5] | Source: [S0]  # #

    method_text = ""  # # On initialise la variable method_text à vide : si on ne trouve pas la section Method, on reste sur "" (contrat stable, pas d’invention) | Étape: [E5] | Source: [S8]  # #
    references: list[str] = []  # # On initialise la liste references : si aucune bibliographie trouvée, on renvoie [] (format stable côté API) | Étape: [E5] | Source: [S8]  # #

    # ✅ Références : structure LaTeX HTML arXiv (biblist)
    for li in soup.select("ol.ltx_biblist li, div.ltx_bibliography li"):  # # soup.select() récupère les entrées de bibliographie arXiv/LaTeX (deux structures possibles) pour tolérer des variantes HTML | Étape: [E5] | Source: [S6]  # #
        t = li.get_text(" ", strip=True)  # # get_text() extrait le texte d’une référence (auteurs, titre, venue) en évitant le HTML brut | Étape: [E5] | Source: [S0]  # #
        if t:  # # On vérifie que ce n’est pas vide pour éviter d’ajouter des entrées nulles | Étape: [E5] | Source: [S0]  # #
            references.append(t)  # # On ajoute la référence dans la liste (format “liste de strings” simple et stable) | Étape: [E5] | Source: [S8]  # #

    # ✅ Méthode : on cherche un titre qui ressemble à “method”
    for sec in soup.select("section.ltx_section, div.ltx_section, section"):  # # On parcourt les sections possibles (LaTeX arXiv + HTML générique) pour trouver une section “Method” même si la structure varie | Étape: [E5] | Source: [S6]  # #
        title_el = sec.select_one(".ltx_title, h1, h2, h3, h4")  # # On cherche le titre de section (classe LaTeX ou titres HTML) pour savoir de quoi parle la section | Étape: [E5] | Source: [S0]  # #
        if not title_el:  # # Si la section n’a pas de titre, on ne peut pas l’identifier => on passe à la suivante | Étape: [E5] | Source: [S6]  # #
            continue  # # Continue = on saute ce bloc et on garde le script robuste (pas d’erreur) | Étape: [E5] | Source: [S0]  # #
        title_txt = title_el.get_text(" ", strip=True).lower()  # # On récupère le titre en texte, on le met en lower() pour faire un match insensible à la casse (Method/METHOD/…) | Étape: [E1] | Source: [S0]  # #
        if any(k in title_txt for k in ["method", "methods", "methodology", "approach"]):  # # On teste si le titre contient des mots-clés “méthode” pour capturer la section Method même si le libellé varie | Étape: [E5] | Source: [S8]  # #
            tmp = sec.get_text(" ", strip=True)  # # On récupère le texte complet de la section (titre + contenu) sous forme propre, sans HTML brut | Étape: [E5] | Source: [S0]  # #
            tmp = re.sub(r"^\s*" + re.escape(title_el.get_text(" ", strip=True)) + r"\s*", "", tmp, flags=re.IGNORECASE)  # # re.sub() retire le titre au début du texte pour ne garder que le contenu “méthode” (plus propre pour l’agent) | Étape: [E5] | Source: [S0]  # #
            method_text = tmp.strip()  # # strip() final : on stocke le texte de méthode nettoyé | Étape: [E5] | Source: [S8]  # #
            break  # # break stoppe la boucle dès qu’on a trouvé la première section Method (évite de prendre plusieurs sections et de grossir inutilement) | Étape: [E5] | Source: [S0]  # #

    return method_text, references  # # On renvoie un tuple (method_text, references) : 2 blocs ciblés, simples, et prêts à être intégrés dans l’item JSON | Étape: [E1] | Source: [S1]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧠 Filtrage thématique (par catégories + keywords)             # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def _allowed_subcats_for_theme(theme: Optional[str]) -> List[str]:  # # Cette fonction décide quelles sous-catégories arXiv sont autorisées selon le thème demandé, pour garder un périmètre clair et stable | Étape: [E1] | Source: [S0]  # #
    if theme and theme in THEME_TO_ARXIV_SUBCATS:  # # Ici on vérifie si l’utilisateur a fourni un thème valide, afin d’appliquer le bon “filtre thématique” | Étape: [E1] | Source: [S0]  # #
        return THEME_TO_ARXIV_SUBCATS[theme]  # # Ici on renvoie directement la liste de catégories associée au thème (ex: ai_ml → cs.AI, cs.LG…) | Étape: [E1] | Source: [S0]  # #
    return sorted({c for lst in THEME_TO_ARXIV_SUBCATS.values() for c in lst})  # # Ici on renvoie l’union de toutes les catégories autorisées (toujours limité aux thèmes définis) quand aucun thème n’est fourni | Étape: [E1] | Source: [S0]  # #


def _keyword_filter(items: List[Dict[str, Any]], theme: Optional[str]) -> List[Dict[str, Any]]:  # # Cette fonction filtre les items via des mots-clés quand les catégories manquent ou sont instables, pour éviter de perdre tous les résultats si le parsing “Subjects” casse | Étape: [E2] | Source: [S6]  # #
    if not theme or theme not in THEME_KEYWORDS:  # # Ici on sort tout de suite si on n’a pas de thème exploitable (pas de filtrage keyword à appliquer) | Étape: [E1] | Source: [S0]  # #
        return items  # # Ici on renvoie la liste inchangée pour ne pas supprimer des items sans raison (comportement stable) | Étape: [E1] | Source: [S1]  # #
    kws = [k.lower() for k in THEME_KEYWORDS[theme]]  # # Ici on met les keywords en minuscules pour comparer sans dépendre de la casse (robustesse) | Étape: [E1] | Source: [S0]  # #
    out: List[Dict[str, Any]] = []  # # Ici on prépare une nouvelle liste de sortie (format structuré) pour stocker seulement les items qui matchent | Étape: [E1] | Source: [S1]  # #
    for it in items:  # # Ici on parcourt chaque item pour vérifier s’il contient un des mots-clés du thème | Étape: [E1] | Source: [S1]  # #
        blob = ((it.get("title") or "") + " " + (it.get("abstract") or "")).lower()  # # Ici on construit un “texte de test” (titre+abstract) en minuscules, car ce sont les champs les plus utiles pour un filtrage simple | Étape: [E1] | Source: [S0]  # #
        if any(k in blob for k in kws):  # # any() renvoie True si AU MOINS un keyword est présent ; ici ça sert à garder l’item si le sujet semble correspondre au thème | Étape: [E1] | Source: [S0]  # #
            out.append(it)  # # Ici on ajoute l’item à la sortie car il est jugé pertinent selon les mots-clés | Étape: [E1] | Source: [S1]  # #
    return out  # # Ici on renvoie la liste filtrée (explicite), utilisée comme fallback si les catégories sont inexploitables | Étape: [E1] | Source: [S0]  # #


def filter_items_by_subcats(items: List[Dict[str, Any]], allowed_subcats: List[str]) -> List[Dict[str, Any]]:  # # Cette fonction filtre les items par catégories arXiv (cs.AI, cs.CL, …) pour respecter le périmètre du thème demandé | Étape: [E1] | Source: [S1]  # #
    allowed = set(allowed_subcats)  # # set() sert ici à accélérer les tests “c in allowed” (plus rapide qu’une liste) | Étape: [E1] | Source: [S0]  # #
    out: List[Dict[str, Any]] = []  # # Ici on initialise la liste de sortie qui contiendra uniquement les items autorisés | Étape: [E1] | Source: [S1]  # #
    for it in items:  # # Ici on parcourt chaque item collecté depuis la page /search/cs | Étape: [E1] | Source: [S1]  # #
        cats = it.get("all_categories") or []  # # Ici on récupère les catégories de l’item (ou [] si absent) pour décider s’il doit être conservé | Étape: [E1] | Source: [S0]  # #
        if not cats:  # # Ici, si les catégories n’ont pas pu être extraites (HTML changé), on évite un faux négatif en conservant l’item | Étape: [E1] | Source: [S8]  # #
            out.append(it)  # # Ici on garde l’item car on n’a pas la preuve qu’il est hors périmètre (robustesse) | Étape: [E1] | Source: [S0]  # #
            continue  # # Ici on passe au suivant pour ne pas exécuter le test de matching sur une liste vide | Étape: [E1] | Source: [S0]  # #
        if any(c in allowed for c in cats):  # # any() teste si AU MOINS une catégorie de l’item est autorisée (utile quand il y a plusieurs tags/cross-lists) | Étape: [E1] | Source: [S0]  # #
            out.append(it)  # # Ici on ajoute l’item car il respecte le périmètre thématique | Étape: [E1] | Source: [S0]  # #
    return out  # # Ici on renvoie la liste filtrée finale par catégories | Étape: [E1] | Source: [S0]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# ✅ Fonction principale                                         # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def scrape_arxiv_cs_scoped(
    user_query: str,  # # Texte de recherche utilisateur (FR: requête) : c’est l’entrée principale qui pilote l’URL /search/cs | Étape: [E1] | Source: [S0]  # #
    theme: Optional[str] = None,  # # Thème optionnel (FR: catégorie logique) : permet d’activer un filtrage par sous-catégories arXiv | Étape: [E1] | Source: [S0]  # #
    max_results: int = 20,  # # Limite de résultats : empêche un scraping massif et contrôle le volume collecté | Étape: [E1] | Source: [S0]  # #
    sort: str = "relevance",  # # Tri : “relevance” ou “submitted_date”, pour choisir l’ordre des résultats sans changer le parsing | Étape: [E1] | Source: [S0]  # #
    polite_min_s: float = 1.2,  # # Politesse (min) : délai minimum entre requêtes pour éviter d’être agressif côté serveur | Étape: [E4] | Source: [S5]  # #
    polite_max_s: float = 2.0,  # # Politesse (max) : délai maximum (jitter) pour éviter un rythme “robotique” | Étape: [E4] | Source: [S5]  # #
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Dossier de sortie cache : garantit que JSON/HTML debug sont écrits dans raw/cache | Étape: [E2] | Source: [S2]  # #
    enrich_abs: bool = True,  # # Enrichissement /abs : active la récupération DOI + versions + abstract fallback via la page /abs | Étape: [E1] | Source: [S0]  # #
    enable_keyword_filter: bool = True,  # # Filtrage keywords : fallback utile si les catégories “Subjects” ne sont pas fiables / manquantes | Étape: [E2] | Source: [S6]  # #
) -> Dict[str, Any]:  # # La fonction renvoie toujours un dict JSON stable (contrat) pour que FastAPI puisse l’exposer sans surprise | Étape: [E1] | Source: [S1]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🧱 Préparation paramètres                                     # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    max_results = int(max_results)  # # int() force le type entier (sécurité) : évite de casser la pagination si on reçoit “5” en string | Étape: [E1] | Source: [S0]  # #
    if max_results < 1:  # # Ici on impose une borne basse pour ne jamais demander 0 résultat (cas qui casse la logique de boucle) | Étape: [E1] | Source: [S0]  # #
        max_results = 1  # # Ici on corrige automatiquement en 1 (comportement stable) | Étape: [E1] | Source: [S0]  # #
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # Ici on impose un cap dur pour empêcher un scraping massif par erreur | Étape: [E1] | Source: [S0]  # #
        max_results = MAX_RESULTS_HARD_LIMIT  # # Ici on applique le cap (anti-aspirateur) | Étape: [E1] | Source: [S0]  # #

    if not os.path.isabs(data_lake_raw_dir):  # # os.path.isabs() vérifie si le chemin est absolu ; ici ça évite d’écrire “au hasard” selon le CWD | Étape: [E2] | Source: [S2]  # #
        data_lake_raw_dir = os.path.abspath(os.path.join(PROJECT_ROOT, data_lake_raw_dir))  # # os.path.abspath() normalise vers un chemin absolu basé sur PROJECT_ROOT (sortie prévisible raw/cache) | Étape: [E2] | Source: [S2]  # #

    ensure_dir(data_lake_raw_dir)  # # ensure_dir() crée le dossier si nécessaire pour garantir que les fichiers JSON/HTML seront bien écrits (pas d’erreur “No such file”) | Étape: [E2] | Source: [S2]  # #
    ts = now_iso_for_filename()  # # now_iso_for_filename() fabrique un timestamp pour nommer les fichiers de manière unique et traçable | Étape: [E1] | Source: [S0]  # #
    session = requests.Session()  # # requests.Session() garde une session HTTP réutilisable (cookies/connexions) : ici ça rend les requêtes plus stables et plus efficaces | Étape: [E2] | Source: [S3]  # #

    errors_global: List[str] = []  # # Liste d’erreurs globales (FR: erreurs du tool) : utilisée pour signaler 429/500/timeout sans dépendre des erreurs “par item” | Étape: [E2] | Source: [S3]  # #

#---------------------------------------------------------------------------------
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🎯 Allowed categories  # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    allowed_subcats = _allowed_subcats_for_theme(theme)  # # Liste cats # # Respect: périmètre thèmes | Étape: [E1] | Source: [S0]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🔎 Pagination search/cs  # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    collected: List[Dict[str, Any]] = []  # # Items bruts CS # # Respect: collecte contrôlée | Étape: [E1] | Source: [S1]  # #
    bundle_parts: List[str] = []  # # HTML debug # # Respect: cache local (pas envoyé au LLM) | Étape: [E2] | Source: [S2]  # #
    start = 0  # # Pagination # # Respect: contrôle volume | Étape: [E1] | Source: [S0]  # #
    last_search_url = ""  # # Debug # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
    last_search_http: Optional[int] = None  # # Debug # # Respect: traçabilité | Étape: [E2] | Source: [S3]  # #
    diag_last: Dict[str, Any] = {}  # # Debug # # Respect: traçabilité | Étape: [E2] | Source: [S6]  # #
    anti_bot_or_weird_page = False  # # Flag # # Respect: transparence | Étape: [E2] | Source: [S6]  # #

    while len(collected) < max_results:  # # Loop # # Respect: contrôle volume | Étape: [E1] | Source: [S0]  # #
        search_url = build_search_url(query=user_query, start=start, size=PAGE_SIZE, sort=sort)  # # URL # # Respect: query simple | Étape: [E1] | Source: [S0]  # #
        last_search_url = search_url  # # Trace # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        html, code = http_get_text(session=session, url=search_url, timeout_s=HTTP_TIMEOUT_S)  # # GET # # Respect: timeout+retry | Étape: [E2] | Source: [S3]  # #
        last_search_http = code  # # Trace # # Respect: debug | Étape: [E2] | Source: [S3]  # #

        weird = _detect_weird_page_signals(html)  # # Signaux # # Respect: diagnostiquer consent/robot/no-results | Étape: [E2] | Source: [S6]  # #

        bundle_parts.append(f"<!-- SEARCH URL: {search_url} | HTTP {code} -->\n")  # # En-tête debug # # Respect: traçabilité | Étape: [E2] | Source: [S3]  # #
        bundle_parts.append(f"<!-- WEIRD: {json.dumps(weird)} -->\n")  # # Signaux debug # # Respect: traçabilité | Étape: [E2] | Source: [S6]  # #
        bundle_parts.append((html or "")[:200000])  # # Coupe 200k # # Respect: pas massif, cache debug local | Étape: [E2] | Source: [S2]  # #
        bundle_parts.append("\n<!-- END SEARCH -->\n")  # # Fin bloc # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #

        if code != 200:  # # HTTP non-200 => erreur tool | Étape: [E2] | Source: [S3]  # #
            errors_global.append(f"SEARCH_HTTP_{code}")  # # Log erreur globale | Étape: [E2] | Source: [S0]  # #
            break  # # Stop # # Respect: ne pas boucler | Étape: [E1] | Source: [S0]  # #
        if weird.get("contains_we_are_sorry") or weird.get("contains_robot") or weird.get("contains_consent"):  # # Détecte page anti-bot/consent (évite faux parsing) | Étape: [E2] | Source: [S3]  # #
            anti_bot_or_weird_page = True  # # Marque page bizarre (pour diagnostic) | Étape: [E2] | Source: [S6]  # #
            errors_global.append("ANTI_BOT_OR_WEIRD_PAGE")  # # Erreur globale tool (contrat stable) | Étape: [E1] | Source: [S1]  # #
            break  # # Stop (on n'insiste pas) | Étape: [E2] | Source: [S0]  # #

        page_items, diag = parse_search_page(html)  # # Parse # # Respect: extraction ciblée | Étape: [E2] | Source: [S6]  # #
        diag_last = diag  # # Trace # # Respect: debug | Étape: [E2] | Source: [S6]  # #

        if diag.get("contains_no_results"):  # # Aucun résultat # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #
            break  # # Stop # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
        if not page_items:  # # Aucun résultat parsé => diag + erreur soft | Étape: [E2] | Source: [S0]  # #
            errors_global.append("NO_RESULTS_PARSED")  # # Indique parsing vide | Étape: [E2] | Source: [S6]  # #
            break  # # Stop # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #

        collected.extend(page_items)  # # Ajoute # # Respect: collecte contrôlée | Étape: [E1] | Source: [S1]  # #

        # ✅ CORRECTION IMPORTANTE : si la page a < PAGE_SIZE résultats, inutile d'aller à start+50
        if len(page_items) < PAGE_SIZE:  # # Dernière page probable # # Respect: éviter requêtes inutiles (et erreurs 500) | Étape: [E1] | Source: [S1]  # #
            break  # # Stop # # Respect: fréquence raisonnable | Étape: [E1] | Source: [S0]  # #

        start += PAGE_SIZE  # # Next page # # Respect: pagination contrôlée | Étape: [E1] | Source: [S0]  # #
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse # # Respect: éviter spam | Étape: [E4] | Source: [S5]  # #

    collected = collected[:max_results]  # # Tronque # # Respect: limite demandée | Étape: [E1] | Source: [S0]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🧹 Filtrage par catégories  # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    filtered = filter_items_by_subcats(collected, allowed_subcats=allowed_subcats)  # # Filtre cats # # Respect: scope demandé | Étape: [E1] | Source: [S1]  # #
    if enable_keyword_filter:  # # Si activé # # Respect: pertinence | Étape: [E1] | Source: [S0]  # #
        filtered = _keyword_filter(filtered, theme=theme)  # # Filtre mots-clés # # Respect: fallback si cats manquent | Étape: [E2] | Source: [S6]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🔎 Enrich /abs  # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    if enrich_abs:  # # Si enrich # # Respect: enrichissement minimal | Étape: [E1] | Source: [S0]  # #
        for it in filtered:  # # Parcours # # Respect: traitement contrôlé | Étape: [E1] | Source: [S0]  # #
            it["doi"] = ""  # # Init # # Respect: champs stables | Étape: [E1] | Source: [S0]  # #
            it["versions"] = []  # # Init # # Respect: champs stables | Étape: [E1] | Source: [S0]  # #
            it["last_updated_raw"] = ""
            it["method"] = ""  # # Méthode # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
            it["references"] = []  # # Références # # Étape: [ROBUSTESSE_PARSING]# #  # # Init # # Respect: champs stables | Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
            it["errors"] = []  # # Init # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #

            url_abs = it.get("abs_url") or ""  # # URL # # Respect: utile | Étape: [E1] | Source: [S0]  # #
            if not url_abs:  # # Si absent # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
                continue  # # Skip # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #

            abs_html, abs_code = http_get_text(session=session, url=url_abs, timeout_s=HTTP_TIMEOUT_S)  # # GET /abs # # Respect: timeout+retry | Étape: [E2] | Source: [S3]  # #
            bundle_parts.append(f"<!-- ABS URL: {url_abs} | HTTP {abs_code} -->\n")  # # Debug # # Respect: traçabilité | Étape: [E2] | Source: [S3]  # #
            bundle_parts.append((abs_html or "")[:200000])  # # Coupe # # Respect: pas massif | Étape: [E1] | Source: [S0]  # #
            bundle_parts.append("\n<!-- END ABS -->\n")  # # Fin # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #

            if abs_code == 200:  # # OK # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
                abs_data = parse_abs_page(abs_html)  # # Parse # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
                it["doi"] = abs_data.get("doi", "")  # # DOI # # Respect: champ utile | Étape: [E1] | Source: [S0]  # #
                it["versions"] = abs_data.get("versions", [])  # # Versions # # Respect: champ utile | Étape: [E1] | Source: [S0]  # #
                it["last_updated_raw"] = abs_data.get("last_updated_raw", "")  # # Last
                html_url = extract_html_url_from_abs(abs_html=abs_html, arxiv_id=it.get("arxiv_id", ""))  # # Cherche lien /html # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
                if html_url:  # # Si /html existe # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
                    html_full, html_code = http_get_text(session=session, url=html_url, timeout_s=30)  # # GET /html # # Étape: [ROBUSTESSE_PARSING] | Source: [S2]  # #
                    bundle_parts.append(f"<!-- HTML URL: {html_url} | HTTP {html_code} -->\n")  # # Trace # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
                    bundle_parts.append(html_full[:200000])  # # Cache debug # # Étape: [ROBUSTESSE_PARSING] | Source: [S2]  # #
                    bundle_parts.append("\n<!-- END HTML -->\n")  # # Fin # # Étape: [ROBUSTESSE_PARSING] | Source: [S2]  # #
                    if html_code == 200:  # # OK # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
                        method_txt, refs_list = parse_arxiv_html_method_and_references(html_full)  # # Parse sections # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
                        if method_txt:  # # Si trouvé # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
                            it["method"] = method_txt  # # Stocke # # Étape: [E1] | Source: [S1]  # #
                        if refs_list:  # # Si trouvé # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
                            it["references"] = refs_list  # # Stocke # # Étape: [E1] | Source: [S1]  # #
                    else:  # # KO # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
                        it["errors"].append(f"html_http_{html_code}")  # # Trace # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
 # # Respect: champ utile | Étape: [E1] | Source: [S0]  # #
                if is_empty(it.get("abstract")) and not is_empty(abs_data.get("abstract")):  # # Fallback abstract # # Respect: compléter sans bruit | Étape: [E2] | Source: [S6]  # #
                    it["abstract"] = abs_data.get("abstract", "")  # # Inject # # Respect: qualité | Étape: [E1] | Source: [S0]  # #
            else:  # # KO # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
                it["errors"].append(f"abs_http_{abs_code}")  # # Trace # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #

            sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse # # Respect: éviter spam | Étape: [E4] | Source: [S5]  # #

    # Missing fields
    for it in filtered:  # # Parcours # # Respect: diagnostic qualité | Étape: [E2] | Source: [S6]  # #
        it["missing_fields"] = compute_missing_fields(it)  # # Ajoute # # Respect: sortie structurée + debug | Étape: [E1] | Source: [S1]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 💾 Sauvegardes cache raw  # #  | Étape: [E2] | Source: [S2]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    bundle_name = f"scrape_arxiv_cs_bundle_{ts}.html"  # # Nom # # Respect: cache debug | Étape: [E2] | Source: [S2]  # #
    bundle_path = save_text_file(data_lake_raw_dir, bundle_name, "\n".join(bundle_parts))  # # Save # # Respect: cache local visible | Étape: [E2] | Source: [S2]  # #

    result: Dict[str, Any] = {  # # Résultat # # Respect: sortie JSON structurée | Étape: [E1] | Source: [S1]  # #
        "ok": (len(errors_global) == 0),  # # OK seulement si aucune erreur globale | Étape: [E1]# #  # # Statut # # Respect: API stable | Étape: [E1] | Source: [S0]  # #
        "user_query": user_query,  # # Query # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
        "theme": theme,  # # Thème # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
        "allowed_subcats": allowed_subcats,  # # Périmètre # # Respect: scope explicite | Étape: [E1] | Source: [S0]  # #
        "sort": sort,  # # Tri # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
        "requested_max_results": max_results,  # # Limite # # Respect: pas massif | Étape: [E1] | Source: [S0]  # #
        "count_collected_cs": len(collected),  # # Collecte # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "count_after_theme_filter": len(filtered),  # # Après filtre # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "items": filtered,  # # Items # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
        "bundle_html_file": bundle_path,  # # HTML debug # # Respect: cache local (pas LLM) | Étape: [E2] | Source: [S2]  # #
        "supported_fields": SUPPORTED_FIELDS,  # # Schéma # # Respect: contrat clair | Étape: [E1] | Source: [S1]  # #
        # Debug important
        "project_root": PROJECT_ROOT,  # # Où est le projet # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
        "raw_cache_dir": data_lake_raw_dir,  # # Où écrit-on # # Respect: visibilité | Étape: [E2] | Source: [S2]  # #
        "cwd_runtime": os.getcwd(),  # # CWD # # Respect: debug uvicorn | Étape: [E1] | Source: [S0]  # #
        "last_search_url": last_search_url,  # # Dernière URL # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "last_search_http": last_search_http,  # # Dernier code HTTP search (0 = erreur réseau) | Étape: [E2]# #  # # Dernier HTTP # # Respect: debug | Étape: [E2] | Source: [S3]  # #
        "parse_diag_last": diag_last,  # # Dernier diag # # Respect: debug | Étape: [E2] | Source: [S6]  # #
        "anti_bot_or_weird_page": anti_bot_or_weird_page,  # # Flag # # Respect: transparence | Étape: [E2] | Source: [S6]  # #
    }  # # Fin result # # Respect: JSON propre | Étape: [E1] | Source: [S1]  # #

    json_name = f"scrape_arxiv_cs_{ts}.json"  # # Nom json # # Respect: cache résultat | Étape: [E2] | Source: [S2]  # #
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # Path # # Respect: cache local | Étape: [E2] | Source: [S2]  # #
    with open(json_path, "w", encoding="utf-8") as f:  # # Open # # Respect: robustesse encodage | Étape: [E1] | Source: [S1]  # #
        json.dump(result, f, ensure_ascii=False, indent=2)  # # Dump # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #

    result["saved_to"] = json_path  # # Chemin # # Respect: retrouver facilement le fichier | Étape: [E1] | Source: [S1]  # #
    return result  # # Retour # # Respect: contrat clair | Étape: [E1] | Source: [S0]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# ✅ Alias compatibilité avec ton main.py  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def scrape_arxiv_cs(  # # Alias # # Respect: ne pas casser ton main.py existant | Étape: [E1] | Source: [S0]  # #
    query: str,  # # Query # # Respect: input simple | Étape: [E1] | Source: [S0]  # #
    max_results: int = 50,  # # Limite # # Respect: contrôle volume | Étape: [E1] | Source: [S0]  # #
    sort: str = "relevance",  # # Tri # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
    polite_min_s: float = 1.2,  # # Politesse # # Respect: fréquence raisonnable | Étape: [E4] | Source: [S5]  # #
    polite_max_s: float = 2.0,  # # Politesse # # Respect: fréquence raisonnable | Étape: [E4] | Source: [S5]  # #
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Cache # # Respect: écrit dans raw/cache | Étape: [E2] | Source: [S2]  # #
    theme: Optional[str] = None,  # # Thème # # Respect: scope | Étape: [E1] | Source: [S0]  # #
) -> Dict[str, Any]:  # # Retour structuré # # Respect: JSON | Étape: [E1] | Source: [S1]  # #
    return scrape_arxiv_cs_scoped(  # # Forward # # Respect: point d'entrée unique | Étape: [E1] | Source: [S0]  # #
        user_query=query,  # # Map # # Respect: cohérence | Étape: [E1] | Source: [S0]  # #
        theme=theme,  # # Map # # Respect: cohérence | Étape: [E1] | Source: [S0]  # #
        max_results=max_results,  # # Map # # Respect: cohérence | Étape: [E1] | Source: [S0]  # #
        sort=sort,  # # Map # # Respect: cohérence | Étape: [E1] | Source: [S0]  # #
        polite_min_s=polite_min_s,  # # Map # # Respect: cohérence | Étape: [E4] | Source: [S5]  # #
        polite_max_s=polite_max_s,  # # Map # # Respect: cohérence | Étape: [E4] | Source: [S5]  # #
        data_lake_raw_dir=data_lake_raw_dir,  # # Map # # Respect: cohérence | Étape: [E2] | Source: [S2]  # #
        enrich_abs=True,  # # On enrichit # # Respect: utile (doi/versions/abstract) | Étape: [E1] | Source: [S0]  # #
        enable_keyword_filter=True,  # # On garde fallback # # Respect: évite faux négatifs | Étape: [E2] | Source: [S6]  # #
    )


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# ✅ TEST LOCAL  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
RUN_LOCAL_TEST = True  # # True = test ON # # Respect: debug local sans FastAPI | Étape: [E1] | Source: [S0]  # #

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # Entry # # Respect: exécution locale maîtrisée | Étape: [E2] | Source: [S3]  # #
    res = scrape_arxiv_cs_scoped(  # # Run # # Respect: test contrôlé | Étape: [E1] | Source: [S0]  # #
        user_query="multimodal transformer misogyny detection",  # # Exemple # # Respect: besoin informationnel | Étape: [E1] | Source: [S0]  # #
        theme="ai_ml",  # # Thème # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
        max_results=5,  # # Limite # # Respect: pas massif | Étape: [E1] | Source: [S0]  # #
        sort="relevance",  # # Tri # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
        data_lake_raw_dir=DEFAULT_RAW_DIR,  # # Cache # # Respect: écrit au bon endroit | Étape: [E2] | Source: [S2]  # #
        enrich_abs=True,  # # Enrich # # Respect: utile | Étape: [E1] | Source: [S0]  # #
    )  # # Fin # # Respect: test | Étape: [E1] | Source: [S0]  # #
    print(json.dumps({  # # Print # # Respect: debug lisible | Étape: [E1] | Source: [S1]  # #
        "count_collected_cs": res.get("count_collected_cs"),  # # Info # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "count_after_theme_filter": res.get("count_after_theme_filter"),  # # Info # # Respect: debug | Étape: [E1] | Source: [S0]  # #
        "saved_to": res.get("saved_to"),  # # Info # # Respect: retrouver JSON | Étape: [E1] | Source: [S1]  # #
        "bundle_html_file": res.get("bundle_html_file"),  # # Info # # Respect: retrouver HTML | Étape: [E1] | Source: [S0]  # #
        "anti_bot_or_weird_page": res.get("anti_bot_or_weird_page"),  # # Info # # Respect: transparence | Étape: [E2] | Source: [S6]  # #
        "last_search_http": res.get("last_search_http"),  # # Info # # Respect: debug | Étape: [E2] | Source: [S3]  # #
        "parse_diag_last": res.get("parse_diag_last"),  # # Info # # Respect: debug | Étape: [E2] | Source: [S6]  # #
    }, ensure_ascii=False, indent=2))  # # Pretty # # Respect: lecture facile | Étape: [E1] | Source: [S0]  # #