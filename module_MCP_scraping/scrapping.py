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


# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 📌 Résolution robuste des chemins
# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
def _find_project_root(start_dir: str) -> str:  # # 🔎 Trouver la racine projet # # Respect: écrit toujours dans /data_lake du projet | Étape: [E1] | Source: [S0]  # #
    cur = os.path.abspath(start_dir)  # # Normalise # # Respect: robustesse Windows/uvicorn | Étape: [E1] | Source: [S0]  # #
    while True:  # # Boucle remontée # # Respect: éviter chemins relatifs fragiles | Étape: [E1] | Source: [S0]  # #
        if os.path.isdir(os.path.join(cur, "data_lake")):  # # Marqueur data_lake # # Respect: cache raw attendu par le projet | Étape: [E2] | Source: [S2]  # #
            return cur  # # Racine OK # # Respect: écriture stable | Étape: [E1] | Source: [S0]  # #
        if os.path.isfile(os.path.join(cur, "pyproject.toml")):  # # Marqueur projet # # Respect: structure projet | Étape: [E1] | Source: [S0]  # #
            return cur  # # Racine OK # # Respect: écriture stable | Étape: [E1] | Source: [S0]  # #
        if os.path.isfile(os.path.join(cur, "requirements.txt")):  # # Marqueur projet # # Respect: structure projet | Étape: [E1] | Source: [S0]  # #
            return cur  # # Racine OK # # Respect: écriture stable | Étape: [E1] | Source: [S0]  # #
        parent = os.path.dirname(cur)  # # Parent # # Respect: progression contrôlée | Étape: [E1] | Source: [S0]  # #
        if parent == cur:  # # Sommet atteint # # Respect: éviter boucle infinie | Étape: [E1] | Source: [S0]  # #
            return os.path.abspath(start_dir)  # # Fallback: dossier actuel # # Respect: cohérence minimale | Étape: [E2] | Source: [S6]  # #
        cur = parent  # # Continue # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #


# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧭 Constantes arXiv  # #  | Étape: [E1] | Source: [S0]  # #
# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
ARXIV_BASE = "https://arxiv.org"  # # Base URL # # Respect: source publique | Étape: [E2] | Source: [S3]  # #
ARXIV_SEARCH_CS = f"{ARXIV_BASE}/search/cs"  # # ✅ Endpoint CS HTML # # Respect: périmètre CS directement | Étape: [E1] | Source: [S0]  # #

_THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))  # # Dossier du script # # Respect: déterminisme | Étape: [E1] | Source: [S0]  # #
PROJECT_ROOT = _find_project_root(_THIS_FILE_DIR)  # # Racine projet # # Respect: écrit au bon endroit | Étape: [E1] | Source: [S0]  # #
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data_lake", "raw", "cache")  # # Cache raw # # Respect: stockage dans raw/cache | Étape: [E2] | Source: [S2]  # #

MAX_RESULTS_HARD_LIMIT = 100  # # Cap anti-massif # # Respect: pas d'aspirateur | Étape: [E1] | Source: [S0]  # #
PAGE_SIZE = 50  # # Taille page arXiv # # Respect: contrôle volume | Étape: [E1] | Source: [S0]  # #

# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧯 Robustesse HTTP  # #  | Étape: [E2] | Source: [S3]  # #
# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
HTTP_RETRY_STATUS = {429, 500, 502, 503, 504}  # # Codes à retry # # Respect: agent robuste (ne pas casser au 1er incident) | Étape: [E2] | Source: [S3]  # #
HTTP_RETRY_MAX = 2  # # Nombre de retries # # Respect: fréquence raisonnable (pas de spam) | Étape: [E2] | Source: [S3]  # #
HTTP_TIMEOUT_S = 30  # # Timeout # # Respect: robustesse (évite blocage) | Étape: [E2] | Source: [S3]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🎯 Thèmes demandés -> sous-catégories arXiv autorisées  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
THEME_TO_ARXIV_SUBCATS: Dict[str, List[str]] = {  # # Mapping thème->codes # # Respect: périmètre strict + cross-lists fréquentes | Étape: [E1] | Source: [S0]  # #
    "ai_ml": [  # # IA/ML/LLM/Agents/Vision/Multimodal # # Respect: couvre ML même si classé en stat.ML / eess.IV | Étape: [E1] | Source: [S0]  # #
        "cs.AI",  # # Artificial Intelligence # # Respect: IA/Agents | Étape: [E1] | Source: [S0]  # #
        "cs.LG",  # # Machine Learning (CS) # # Respect: ML | Étape: [E1] | Source: [S0]  # #
        "cs.CL",  # # Computation and Language (NLP/LLM) # # Respect: LLM/NLP | Étape: [E1] | Source: [S0]  # #
        "cs.CV",  # # Computer Vision and Pattern Recognition # # Respect: Vision/Multimodal | Étape: [E1] | Source: [S0]  # #
        "cs.MA",  # # Multiagent Systems # # Respect: Agents | Étape: [E1] | Source: [S0]  # #
        "cs.NE",  # # Neural and Evolutionary Computing # # Respect: Deep learning (historique) | Étape: [E1] | Source: [S0]  # #
        "stat.ML",  # # Machine Learning (Stats) # # Respect: cross-list très fréquent (évite 0 résultats) | Étape: [E1] | Source: [S0]  # #
        "eess.IV",  # # Image and Video Processing # # Respect: Vision parfois hors CS | Étape: [E1] | Source: [S0]  # #
    ],
    "algo_ds": ["cs.DS", "cs.CC"],  # # Algo/DS/Complexité # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
    "net_sys": ["cs.NI", "cs.DC", "cs.OS"],  # # Réseau/Distrib/OS # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
    "cyber_crypto": ["cs.CR"],  # # Crypto/Sécu # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
    "pl_se": ["cs.PL", "cs.SE", "cs.LO"],  # # Langages/SE/Logique # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
    "hci_data": ["cs.HC", "cs.IR", "cs.DB", "cs.MM"],  # # HCI/IR/DB/MM # # Respect: périmètre demandé | Étape: [E1] | Source: [S0]  # #
}

# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧠 Keywords fallback (si pas de thème explicite)  # #  | Étape: [E2] | Source: [S6]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
THEME_KEYWORDS: Dict[str, List[str]] = {  # # Support # # Respect: filtrage pertinence si catégories manquantes | Étape: [E1] | Source: [S0]  # #
    "ai_ml": ["machine learning", "deep learning", "llm", "agent", "transformer", "multimodal", "computer vision"],
    "algo_ds": ["algorithm", "data structure", "complexity", "graph", "optimization"],
    "net_sys": ["network", "distributed", "operating system", "cloud", "systems"],
    "cyber_crypto": ["security", "privacy", "cryptography", "attack", "defense", "malware"],
    "pl_se": ["programming language", "compiler", "software engineering", "static analysis", "type system"],
    "hci_data": ["human-computer interaction", "information retrieval", "database", "multimedia", "ranking", "search"],
}

# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
# 📦 Champs renvoyés (minimal)  # #  | Étape: [E1] | Source: [S0]  # #
# ===============================  # #  | Étape: [E1] | Source: [S0]  # #
SUPPORTED_FIELDS = [  # # Champs stables | Étape: [E1] | Source: [S1]  # #
    "arxiv_id",  # # Identifiant arXiv = ID unique du papier | Étape: [E1] | Source: [S1]  # #
    "title",  # # Titre = nom du papier | Étape: [E1] | Source: [S0]  # #
    "authors",  # # Auteurs = liste des auteurs | Étape: [E1] | Source: [S0]  # #
    "abstract",
    "method",  # # Methode (FR: section "Méthode") # # Étape: [E1] | Source: [S8]  # #
    "references",  # # References (FR: section "Références") # # Étape: [E1]# #  # # Résumé = abstract du papier | Étape: [E1] | Source: [S8]  # #
    "submitted_date",  # # Date de soumission = quand le papier a été soumis | Étape: [E1] | Source: [S1]  # #
    "abs_url",  # # Lien fiche = URL /abs (page détails) | Étape: [E1] | Source: [S1]  # #
    "pdf_url",  # # Lien PDF = URL /pdf (téléchargement) | Étape: [E1] | Source: [S1]  # #
    "doi",  # # DOI = identifiant éditeur (si présent) | Étape: [E1] | Source: [S0]  # #
    "versions",  # # Versions = historique v1,v2, | Étape: [E1] | Source: [S0]  # #
    "last_updated_raw",  # # Dernière maj = dernière ligne de l’historique | Étape: [E1] | Source: [S1]  # #
    "primary_category",  # # Catégorie principale = thème arXiv principal | Étape: [E1] | Source: [S0]  # #
    "all_categories",  # # Toutes catégories = tags arXiv du papier | Étape: [E1] | Source: [S0]  # #
    "missing_fields",  # # Champs manquants = ce qui n’a pas été trouvé | Étape: [E2] | Source: [S3]  # #
    "errors",  # # Erreurs item = erreurs liées à ce papier | Étape: [E2] | Source: [S3]  # #
]


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧩 Helpers base  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def ensure_dir(path: str) -> None:  # # Créer dossier # # Respect: cache disque demandé | Étape: [E2] | Source: [S2]  # #
    os.makedirs(path, exist_ok=True)  # # OK si existe # # Robustesse | Étape: [E1] | Source: [S0]  # #


def now_iso_for_filename() -> str:  # # Timestamp filename # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # Format stable # # Respect: noms de fichiers traçables | Étape: [E1] | Source: [S0]  # #


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


def abs_url(arxiv_id: str) -> str:  # # /abs # # Respect: sortie utile | Étape: [E1] | Source: [S0]  # #
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # Construit URL # # Respect: champs minimaux utiles | Étape: [E1] | Source: [S0]  # #


def pdf_url(arxiv_id: str) -> str:  # # /pdf # # Respect: sortie utile | Étape: [E1] | Source: [S0]  # #
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # Construit URL # # Respect: champs minimaux utiles | Étape: [E1] | Source: [S0]  # #


def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # Missing fields # # Respect: debug qualité | Étape: [E1] | Source: [S0]  # #
    missing: List[str] = []  # # Init # # Respect: structuration | Étape: [E1] | Source: [S0]  # #
    for f in SUPPORTED_FIELDS:  # # Parcours # # Respect: champs stables | Étape: [E1] | Source: [S1]  # #
        if is_empty(item.get(f)):  # # Si vide # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
            missing.append(f)  # # Ajoute # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
    return missing  # # Retour # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #


def _detect_weird_page_signals(html: str) -> Dict[str, bool]:  # # Analyse anti-bot/consent # # Respect: robustesse + transparence | Étape: [E2] | Source: [S6]  # #
    h = (html or "").lower()  # # Lower # # Respect: détection robuste | Étape: [E1] | Source: [S0]  # #
    return {  # # Drapeaux # # Respect: diagnostic clair | Étape: [E2] | Source: [S6]  # #
        "contains_we_are_sorry": ("we are sorry" in h),  # # Message blocage # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
        "contains_robot": ("robot" in h),  # # Mention robot # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
        "contains_captcha": ("captcha" in h),  # # CAPTCHA # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
        "contains_consent": ("consent" in h or "cookie" in h),  # # Consent/cookies # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
        "contains_no_results": ("no results found" in h),  # # Aucun résultat # # Respect: diagnostic | Étape: [E2] | Source: [S6]  # #
    }


def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # GET HTML robuste (attrape timeouts/erreurs réseau) | Étape: [E2] | Source: [S3]  # #
    headers = {  # # Headers HTTP (UA + langue) | Étape: [E2] | Source: [S0]  # #
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/4.1",  # # User-Agent clair (évite être pris pour un bot anonyme) | Étape: [E2] | Source: [S4]  # #
        "Accept-Language": "en-US,en;q=0.9",  # # Langue stable pour parser le HTML de façon prévisible | Étape: [E2] | Source: [S0]  # #
    }
    try:  # # Try HTTP (ne pas faire crasher le tool) | Étape: [E2] | Source: [S3]  # #
        resp = session.get(url, headers=headers, timeout=timeout_s)  # # GET avec timeout (évite rester bloqué) | Étape: [E2] | Source: [S3]  # #
        return resp.text, resp.status_code  # # Retour (HTML, code HTTP) pour diagnostic + contrat stable | Étape: [E1] | Source: [S1]  # #
    except requests.RequestException as e:  # # Erreur réseau/timeout | Étape: [E2] | Source: [S0]  # #
        return f"REQUEST_EXCEPTION: {str(e)}", 0  # # Code 0 = erreur locale (pas HTTP) | Étape: [E2] | Source: [S3]  # #


def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # URL CS HTML # # Respect: scope CS | Étape: [E1] | Source: [S0]  # #
    q = requests.utils.quote((query or "").strip())  # # Encode query # # Respect: requête propre | Étape: [E1] | Source: [S0]  # #
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # URL stable # # Respect: HTML public | Étape: [E1] | Source: [S0]  # #
    s = (sort or "relevance").strip().lower()  # # Normalise tri # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
    if s in {"submitted_date", "submitted", "recent"}:  # # Tri récents # # Respect: option projet | Étape: [E1] | Source: [S0]  # #
        return base + "&order=-announced_date_first"  # # Ajoute param # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
    return base  # # relevance par défaut # # Respect: comportement stable | Étape: [E1] | Source: [S0]  # #


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
    if not result_nodes and diag["has_abs_links"]:  # # Pas de noeuds mais /abs/ présent # # Respect: robustesse HTML | Étape: [E2] | Source: [S6]  # #
        diag["fallback_mode"] = "abs_links"  # # Indique fallback # # Respect: traçabilité | Étape: [E2] | Source: [S6]  # #
        abs_ids = _RE_ARXIV_ID.findall(html or "")  # # IDs # # Respect: extraction stable | Étape: [E1] | Source: [S8]  # #
        abs_ids = list(dict.fromkeys(abs_ids))[:PAGE_SIZE]  # # Dédoublonne + limite # # Respect: contrôle volume | Étape: [E1] | Source: [S0]  # #
        for arxiv_id in abs_ids:  # # Parcours # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
            items.append({  # # Item minimal # # Respect: pas de HTML brut au LLM | Étape: [E1] | Source: [S1]  # #
                "arxiv_id": arxiv_id,  # # ID # # Respect: identifiant | Étape: [E1] | Source: [S0]  # #
                "title": "",  # # Vide # # Respect: minimal | Étape: [E1] | Source: [S0]  # #
                "authors": [],  # # Vide # # Respect: minimal | Étape: [E1] | Source: [S0]  # #
                "abstract": "",  # # Vide # # Respect: minimal | Étape: [E1] | Source: [S0]  # #
                "submitted_date": "",  # # Vide # # Respect: minimal | Étape: [E1] | Source: [S0]  # #
                "abs_url": abs_url(arxiv_id),  # # URL # # Respect: utile | Étape: [E1] | Source: [S0]  # #
                "pdf_url": pdf_url(arxiv_id),  # # URL # # Respect: utile | Étape: [E1] | Source: [S0]  # #
                "primary_category": "",  # # Vide # # Respect: filtrage possible plus tard | Étape: [E1] | Source: [S0]  # #
                "all_categories": [],  # # Vide # # Respect: filtrage possible plus tard | Étape: [E1] | Source: [S0]  # #
            })
        return items, diag  # # Retour # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #

    # Mode normal
    for li in result_nodes:  # # Parcours # # Respect: extraction minimale | Étape: [E1] | Source: [S8]  # #
        title_el = li.select_one("p.title")  # # Titre # # Respect: champs essentiels | Étape: [E1] | Source: [S0]  # #
        authors_el = li.select_one("p.authors")  # # Auteurs # # Respect: champs essentiels | Étape: [E1] | Source: [S0]  # #
        abstract_el = li.select_one("span.abstract-full")  # # Abstract # # Respect: champs essentiels | Étape: [E1] | Source: [S0]  # #
        submitted_el = li.select_one("p.is-size-7")  # # Date # # Respect: champs essentiels | Étape: [E1] | Source: [S0]  # #

        abs_a = li.select_one('p.list-title a[href*="/abs/"]')  # # Lien abs # # Respect: stable | Étape: [E1] | Source: [S0]  # #
        pdf_a = li.select_one('p.list-title a[href*="/pdf/"]')  # # Lien pdf # # Respect: utile | Étape: [E1] | Source: [S0]  # #
        abs_href = normalize_url(abs_a.get("href") if abs_a else "")  # # Normalise # # Respect: sortie propre | Étape: [E1] | Source: [S0]  # #
        pdf_href = normalize_url(pdf_a.get("href") if pdf_a else "")  # # Normalise # # Respect: sortie propre | Étape: [E1] | Source: [S0]  # #

        arxiv_id = ""  # # Init # # Respect: structuration | Étape: [E1] | Source: [S0]  # #
        m = re.search(r"/abs/([^?#/]+)", abs_href) if abs_href else None  # # Parse ID # # Respect: extraction précise | Étape: [E1] | Source: [S8]  # #
        if m:  # # Si match # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
            arxiv_id = m.group(1).strip()  # # ID # # Respect: structuration | Étape: [E1] | Source: [S0]  # #

        title_txt = title_el.get_text(" ", strip=True) if title_el else ""  # # Titre # # Respect: extraction minimale | Étape: [E1] | Source: [S8]  # #
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # Auteurs # # Respect: extraction minimale | Étape: [E1] | Source: [S8]  # #
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # Liste # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # Abstract # # Respect: extraction minimale | Étape: [E1] | Source: [S8]  # #
        abstract = abstract.replace("△ Less", "").strip()  # # Nettoyage # # Respect: réduire bruit | Étape: [E1] | Source: [S0]  # #

        submitted_date = ""  # # Init # # Respect: structuration | Étape: [E1] | Source: [S0]  # #
        if submitted_el:  # # Si présent # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
            txt = submitted_el.get_text(" ", strip=True)  # # Texte # # Respect: extraction minimale | Étape: [E1] | Source: [S8]  # #
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # Regex # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
            if m3:  # # Si match # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
                submitted_date = m3.group(1).strip()  # # Date # # Respect: structuration | Étape: [E1] | Source: [S0]  # #

        primary_cat, all_cats = extract_categories_from_result(li)  # # Cats # # Respect: filtrage thématique demandé | Étape: [E1] | Source: [S8]  # #

        if arxiv_id and is_empty(abs_href):  # # Fallback # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #
            abs_href = abs_url(arxiv_id)  # # Construit # # Respect: sortie utile | Étape: [E1] | Source: [S0]  # #
        if arxiv_id and is_empty(pdf_href):  # # Fallback # # Respect: robustesse | Étape: [E2] | Source: [S6]  # #
            pdf_href = pdf_url(arxiv_id)  # # Construit # # Respect: sortie utile | Étape: [E1] | Source: [S0]  # #

        items.append({  # # Ajout item # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
            "arxiv_id": arxiv_id,  # # ID # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "title": title_txt,  # # Title # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "authors": authors,  # # Authors # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "abstract": abstract,  # # Abstract
            "method": "",  # # Methode (FR: section "Méthode") # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
            "references": [],  # # Références (FR: bibliographie) # # Étape: [ROBUSTESSE_PARSING]# # # # Respect: minimal utile (pas HTML brut) | Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
            "submitted_date": submitted_date,  # # Date # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "abs_url": abs_href,  # # URL # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "pdf_url": pdf_href,  # # URL # # Respect: minimal utile | Étape: [E1] | Source: [S0]  # #
            "primary_category": primary_cat,  # # Cat # # Respect: filtrage thèmes | Étape: [E1] | Source: [S0]  # #
            "all_categories": all_cats,  # # Cats # # Respect: filtrage thèmes | Étape: [E1] | Source: [S0]  # #
        })

    return items, diag  # # Retour # # Respect: robustesse + traçabilité | Étape: [E2] | Source: [S6]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🔎 Parsing /abs (DOI + versions + abstract fallback)  # #  | Étape: [E2] | Source: [S6]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # Parse /abs # # Respect: enrichissement minimal seulement | Étape: [E1] | Source: [S0]  # #
    soup = BeautifulSoup(abs_html, "lxml")  # # Parse # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
    out: Dict[str, Any] = {"doi": "", "versions": [], "last_updated_raw": "", "abstract": ""}  # # Init # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # DOI # # Respect: champ utile | Étape: [E1] | Source: [S0]  # #
    if doi_a:  # # Si DOI # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        out["doi"] = doi_a.get_text(" ", strip=True)  # # Valeur # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #

    abs_el = soup.select_one("blockquote.abstract")  # # Abstract # # Respect: essentiel | Étape: [E1] | Source: [S0]  # #
    if abs_el:  # # Si présent # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        txt = abs_el.get_text(" ", strip=True)  # # Texte # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()  # # Nettoyage # # Respect: réduire bruit | Étape: [E1] | Source: [S0]  # #
        out["abstract"] = txt  # # Stocke # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #

    versions: List[Dict[str, str]] = []  # # Init # # Respect: structuration | Étape: [E1] | Source: [S0]  # #
    for li in soup.select("div.submission-history li"):  # # Versions # # Respect: extraction utile | Étape: [E1] | Source: [S8]  # #
        txt = li.get_text(" ", strip=True)  # # Texte # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # Parse # # Respect: extraction ciblée | Étape: [E1] | Source: [S8]  # #
        if m:  # # Si match # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # Ajoute # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
    out["versions"] = versions  # # Stocke # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # Last # # Respect: champ utile | Étape: [E1] | Source: [S0]  # #

    return out  # # Retour # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #


# ============================================================  # #  
# 🧩 Parsing /html arXiv : Method + References (ciblé)           # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
# ============================================================  # #

def extract_html_url_from_abs(abs_html: str, arxiv_id: str) -> str:  # # Trouver le lien /html (si dispo) # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
    soup = BeautifulSoup(abs_html, "lxml")  # # Parser HTML # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
    a = soup.select_one('a[href^="/html/"], a[href*="/html/"]')  # # Cherche un lien HTML # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
    if not a:  # # Si aucun lien # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
        return ""  # # Pas de /html disponible # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
    href = (a.get("href") or "").strip()  # # Récupère href # # Étape: [E1] | Source: [S1]  # #
    if not href:  # # Si vide # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
        return ""  # # Vide # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
    return normalize_url(href)  # # Normalise en URL absolue # # Étape: [E1] | Source: [S1]  # #


def parse_arxiv_html_method_and_references(html: str) -> tuple[str, list[str]]:  # # Extraire 2 blocs (method+refs) # # Étape: [E5] | Source: [S8]  # #
    soup = BeautifulSoup(html, "lxml")  # # Parser HTML # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #

    method_text = ""  # # Texte Method # # Étape: [E5] | Source: [S8]  # #
    references: list[str] = []  # # Liste refs # # Étape: [E5] | Source: [S8]  # #

    # ✅ Références : structure LaTeX HTML arXiv (biblist)         # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
    for li in soup.select("ol.ltx_biblist li, div.ltx_bibliography li"):  # # Liste bib # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
        t = li.get_text(" ", strip=True)  # # Texte ref # # Étape: [E5] | Source: [S0]  # #
        if t:  # # Si non vide # # Étape: [E5] | Source: [S0]  # #
            references.append(t)  # # Ajoute # # Étape: [E5] | Source: [S8]  # #

    # ✅ Méthode : on cherche un titre qui ressemble à “method”     # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
    for sec in soup.select("section.ltx_section, div.ltx_section, section"):  # # Sections # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
        title_el = sec.select_one(".ltx_title, h1, h2, h3, h4")  # # Titre section # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #
        if not title_el:  # # Pas de titre # # Étape: [ROBUSTESSE_PARSING] | Source: [S6]  # #
            continue  # # Suivant
        title_txt = title_el.get_text(" ", strip=True).lower()  # # Normalise # # Étape: [E1] | Source: [S0]  # #
        if any(k in title_txt for k in ["method", "methods", "methodology", "approach"]):  # # Match method # # Étape: [ROBUSTESSE_PARSING] | Source: [S8]  # #
            # On récupère le texte de la section sans le titre      # # Étape: [E5] | Source: [S0]  # #
            tmp = sec.get_text(" ", strip=True)  # # Texte complet # # Étape: [E5] | Source: [S0]  # #
            tmp = re.sub(r"^\s*" + re.escape(title_el.get_text(" ", strip=True)) + r"\s*", "", tmp, flags=re.IGNORECASE)  # # Retire titre # # Étape: [E5] | Source: [S0]  # #
            method_text = tmp.strip()  # # Stocke # # Étape: [E5] | Source: [S8]  # #
            break  # # Stop au premier match # # Étape: [ROBUSTESSE_PARSING] | Source: [S0]  # #

    return method_text, references  # # Retour 2 blocs # # Étape: [E1] | Source: [S1]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# 🧠 Filtrage thématique (par catégories + keywords)  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def _allowed_subcats_for_theme(theme: Optional[str]) -> List[str]:  # # Allowed cats # # Respect: scope strict | Étape: [E1] | Source: [S0]  # #
    if theme and theme in THEME_TO_ARXIV_SUBCATS:  # # Si thème # # Respect: scope demandé | Étape: [E1] | Source: [S0]  # #
        return THEME_TO_ARXIV_SUBCATS[theme]  # # Retour liste # # Respect: périmètre strict | Étape: [E1] | Source: [S0]  # #
    return sorted({c for lst in THEME_TO_ARXIV_SUBCATS.values() for c in lst})  # # Union # # Respect: limité aux 6 thèmes | Étape: [E1] | Source: [S0]  # #


def _keyword_filter(items: List[Dict[str, Any]], theme: Optional[str]) -> List[Dict[str, Any]]:  # # Keyword fallback # # Respect: pertinence | Étape: [E2] | Source: [S6]  # #
    if not theme or theme not in THEME_KEYWORDS:  # # Si pas de thème # # Respect: logique simple | Étape: [E1] | Source: [S0]  # #
        return items  # # Pas de filtre # # Respect: ne pas inventer | Étape: [E1] | Source: [S1]  # #
    kws = [k.lower() for k in THEME_KEYWORDS[theme]]  # # Lower # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
    out: List[Dict[str, Any]] = []  # # Init # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
    for it in items:  # # Parcours # # Respect: traitement contrôlé | Étape: [E1] | Source: [S1]  # #
        blob = ((it.get("title") or "") + " " + (it.get("abstract") or "")).lower()  # # Texte # # Respect: filtrage minimal | Étape: [E1] | Source: [S0]  # #
        if any(k in blob for k in kws):  # # Match # # Respect: pertinence | Étape: [E1] | Source: [S0]  # #
            out.append(it)  # # Ajoute # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
    return out  # # Retour # # Respect: filtrage explicite | Étape: [E1] | Source: [S0]  # #


def filter_items_by_subcats(items: List[Dict[str, Any]], allowed_subcats: List[str]) -> List[Dict[str, Any]]:  # # Filtre cat # # Respect: périmètre | Étape: [E1] | Source: [S1]  # #
    allowed = set(allowed_subcats)  # # Set # # Respect: performance | Étape: [E1] | Source: [S0]  # #
    out: List[Dict[str, Any]] = []  # # Init # # Respect: sortie structurée | Étape: [E1] | Source: [S1]  # #
    for it in items:  # # Parcours # # Respect: traitement contrôlé | Étape: [E1] | Source: [S1]  # #
        cats = it.get("all_categories") or []  # # Cats # # Respect: filtrage thématique | Étape: [E1] | Source: [S0]  # #
        if not cats:  # # Si extraction ratée # # Respect: robustesse (éviter faux négatif) | Étape: [E1] | Source: [S8]  # #
            out.append(it)  # # Conserver # # Respect: ne pas jeter sans preuve | Étape: [E1] | Source: [S0]  # #
            continue  # # Next # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        if any(c in allowed for c in cats):  # # Match # # Respect: scope demandé | Étape: [E1] | Source: [S0]  # #
            out.append(it)  # # Garder # # Respect: périmètre strict | Étape: [E1] | Source: [S0]  # #
    return out  # # Retour # # Respect: filtrage explicite | Étape: [E1] | Source: [S0]  # #


# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
# ✅ Fonction principale  # #  | Étape: [E1] | Source: [S0]  # #
# ============================================================  # #  | Étape: [E1] | Source: [S0]  # #
def scrape_arxiv_cs_scoped(
    user_query: str,  # # Query user # # Respect: besoin informationnel | Étape: [E1] | Source: [S0]  # #
    theme: Optional[str] = None,  # # Thème # # Respect: scope demandé | Étape: [E1] | Source: [S0]  # #
    max_results: int = 20,  # # Limite # # Respect: pas massif | Étape: [E1] | Source: [S0]  # #
    sort: str = "relevance",  # # Tri # # Respect: contrôle | Étape: [E1] | Source: [S0]  # #
    polite_min_s: float = 1.2,  # # Politesse # # Respect: faible fréquence | Étape: [E4] | Source: [S5]  # #
    polite_max_s: float = 2.0,  # # Politesse # # Respect: faible fréquence | Étape: [E4] | Source: [S5]  # #
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Cache # # Respect: écrire dans raw/cache | Étape: [E2] | Source: [S2]  # #
    enrich_abs: bool = True,  # # Enrich /abs # # Respect: utile (doi/versions) | Étape: [E1] | Source: [S0]  # #
    enable_keyword_filter: bool = True,  # # Keyword fallback # # Respect: pertinence | Étape: [E2] | Source: [S6]  # #
) -> Dict[str, Any]:  # # Retour structuré # # Respect: sortie JSON | Étape: [E1] | Source: [S1]  # #

    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    # 🧱 Préparation paramètres  # #  | Étape: [E1] | Source: [S0]  # #
    # ===============================  # #  | Étape: [E1] | Source: [S0]  # #
    max_results = int(max_results)  # # Cast # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
    if max_results < 1:  # # Borne basse # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
        max_results = 1  # # Fix # # Respect: robustesse | Étape: [E1] | Source: [S0]  # #
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # Cap # # Respect: pas massif | Étape: [E1] | Source: [S0]  # #
        max_results = MAX_RESULTS_HARD_LIMIT  # # Fix # # Respect: pas aspirateur | Étape: [E1] | Source: [S0]  # #

    if not os.path.isabs(data_lake_raw_dir):  # # Si relatif # # Respect: éviter écrire "ailleurs" | Étape: [E2] | Source: [S2]  # #
        data_lake_raw_dir = os.path.abspath(os.path.join(PROJECT_ROOT, data_lake_raw_dir))  # # Base projet # # Respect: cache local attendu | Étape: [E2] | Source: [S2]  # #

    ensure_dir(data_lake_raw_dir)  # # Dossier cache # # Respect: cache local visible | Étape: [E2] | Source: [S2]  # #
    ts = now_iso_for_filename()  # # Timestamp # # Respect: traçabilité | Étape: [E1] | Source: [S0]  # #
    session = requests.Session()  # # Crée session HTTP | Étape: [E2] | Source: [S3]  # #

    errors_global: List[str] = []  # # Erreurs globales tool (contrat stable) | Étape: [E1]# #  # # Session HTTP # # Respect: performance + robustesse | Étape: [E1] | Source: [S1]  # #

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