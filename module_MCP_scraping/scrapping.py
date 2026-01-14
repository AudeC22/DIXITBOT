# ============================================================  # #
# Scraper arXiv CS (ciblé thématique + sortie structurée)     # #
# Objectif :                                                     # #
# - Scraping ciblé sur les thèmes demandés (pas "aspirateur")     # #
# - Sortie JSON structurée (pas de HTML brut envoyé au LLM)       # #
# - Extraction minimale : title/authors/abstract/dates/urls/doi    # #
# - Cache + politesse + robustesse                               # #
#   => on cherche via /search/cs puis on filtre via Subjects       # #
# ============================================================  # #

# ===============================  # #
# 📚 Importations                 # #
# ===============================  # #
import os  # # Gestion chemins/dossiers # # Respect: cache local stable (sortie disque attendue)
import re  # # Regex parsing IDs + catégories # # Respect: extraction ciblée (pas "tout le texte")
import json  # # Export JSON # # Respect: sortie structurée JSON
import time  # # Politesse (sleep) # # Respect: éviter spam requêtes
import random  # # Jitter # # Respect: fréquence raisonnable
import datetime  # # Timestamp fichiers # # Respect: traçabilité des fichiers
from typing import Dict, Any, List, Tuple, Optional  # # Typage # # Respect: tool prévisible

import requests  # # HTTP GET # # Respect: scraping HTML public
from bs4 import BeautifulSoup, Tag  # # Parser HTML # # Respect: extraction ciblée d'éléments utiles


# ===============================  # #
# 📌 Résolution robuste des chemins
# ===============================  # #
def _find_project_root(start_dir: str) -> str:  # # 🔎 Trouver la racine projet # # Respect: écrit toujours dans /data_lake du projet
    cur = os.path.abspath(start_dir)  # # Normalise # # Respect: robustesse Windows/uvicorn
    while True:  # # Boucle remontée # # Respect: éviter chemins relatifs fragiles
        if os.path.isdir(os.path.join(cur, "data_lake")):  # # Marqueur data_lake # # Respect: cache raw attendu par le projet
            return cur  # # Racine OK # # Respect: écriture stable
        if os.path.isfile(os.path.join(cur, "pyproject.toml")):  # # Marqueur projet # # Respect: structure projet
            return cur  # # Racine OK # # Respect: écriture stable
        if os.path.isfile(os.path.join(cur, "requirements.txt")):  # # Marqueur projet # # Respect: structure projet
            return cur  # # Racine OK # # Respect: écriture stable
        parent = os.path.dirname(cur)  # # Parent # # Respect: progression contrôlée
        if parent == cur:  # # Sommet atteint # # Respect: éviter boucle infinie
            return os.path.abspath(start_dir)  # # Fallback: dossier actuel # # Respect: cohérence minimale
        cur = parent  # # Continue # # Respect: robustesse


# ===============================  # #
# 🧭 Constantes arXiv             # #
# ===============================  # #
ARXIV_BASE = "https://arxiv.org"  # # Base URL # # Respect: source publique
ARXIV_SEARCH_CS = f"{ARXIV_BASE}/search/cs"  # # ✅ Endpoint CS HTML # # Respect: périmètre CS directement

_THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))  # # Dossier du script # # Respect: déterminisme
PROJECT_ROOT = _find_project_root(_THIS_FILE_DIR)  # # Racine projet # # Respect: écrit au bon endroit
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data_lake", "raw", "cache")  # # Cache raw # # Respect: stockage dans raw/cache

MAX_RESULTS_HARD_LIMIT = 100  # # Cap anti-massif # # Respect: pas d'aspirateur
PAGE_SIZE = 50  # # Taille page arXiv # # Respect: contrôle volume

# ===============================  # #
# 🧯 Robustesse HTTP              # #
# ===============================  # #
HTTP_RETRY_STATUS = {429, 500, 502, 503, 504}  # # Codes à retry # # Respect: agent robuste (ne pas casser au 1er incident)
HTTP_RETRY_MAX = 2  # # Nombre de retries # # Respect: fréquence raisonnable (pas de spam)
HTTP_TIMEOUT_S = 30  # # Timeout # # Respect: robustesse (évite blocage)


# ============================================================  # #
# 🎯 Thèmes demandés -> sous-catégories arXiv autorisées         # #
# ============================================================  # #
THEME_TO_ARXIV_SUBCATS: Dict[str, List[str]] = {  # # Mapping thème->codes # # Respect: périmètre strict + cross-lists fréquentes
    "ai_ml": [  # # IA/ML/LLM/Agents/Vision/Multimodal # # Respect: couvre ML même si classé en stat.ML / eess.IV
        "cs.AI",   # # Artificial Intelligence # # Respect: IA/Agents
        "cs.LG",   # # Machine Learning (CS) # # Respect: ML
        "cs.CL",   # # Computation and Language (NLP/LLM) # # Respect: LLM/NLP
        "cs.CV",   # # Computer Vision and Pattern Recognition # # Respect: Vision/Multimodal
        "cs.MA",   # # Multiagent Systems # # Respect: Agents
        "cs.NE",   # # Neural and Evolutionary Computing # # Respect: Deep learning (historique)
        "stat.ML", # # Machine Learning (Stats) # # Respect: cross-list très fréquent (évite 0 résultats)
        "eess.IV", # # Image and Video Processing # # Respect: Vision parfois hors CS
    ],
    "algo_ds": ["cs.DS", "cs.CC"],  # # Algo/DS/Complexité # # Respect: périmètre demandé
    "net_sys": ["cs.NI", "cs.DC", "cs.OS"],  # # Réseau/Distrib/OS # # Respect: périmètre demandé
    "cyber_crypto": ["cs.CR"],  # # Crypto/Sécu # # Respect: périmètre demandé
    "pl_se": ["cs.PL", "cs.SE", "cs.LO"],  # # Langages/SE/Logique # # Respect: périmètre demandé
    "hci_data": ["cs.HC", "cs.IR", "cs.DB", "cs.MM"],  # # HCI/IR/DB/MM # # Respect: périmètre demandé
}

# ============================================================  # #
# 🧠 Keywords fallback (si pas de thème explicite)               # #
# ============================================================  # #
THEME_KEYWORDS: Dict[str, List[str]] = {  # # Support # # Respect: filtrage pertinence si catégories manquantes
    "ai_ml": ["machine learning", "deep learning", "llm", "agent", "transformer", "multimodal", "computer vision"],
    "algo_ds": ["algorithm", "data structure", "complexity", "graph", "optimization"],
    "net_sys": ["network", "distributed", "operating system", "cloud", "systems"],
    "cyber_crypto": ["security", "privacy", "cryptography", "attack", "defense", "malware"],
    "pl_se": ["programming language", "compiler", "software engineering", "static analysis", "type system"],
    "hci_data": ["human-computer interaction", "information retrieval", "database", "multimedia", "ranking", "search"],
}

# ===============================  # #
# 📦 Champs renvoyés (minimal)    # #
# ===============================  # #
SUPPORTED_FIELDS = [  # # Champs stables # # Respect: sortie structurée
    "arxiv_id",
    "title",
    "authors",
    "abstract",
    "submitted_date",
    "abs_url",
    "pdf_url",
    "doi",
    "versions",
    "last_updated_raw",
    "primary_category",
    "all_categories",
    "missing_fields",
    "errors",
]


# ============================================================  # #
# 🧩 Helpers base                                                # #
# ============================================================  # #
def ensure_dir(path: str) -> None:  # # Créer dossier # # Respect: cache disque demandé
    os.makedirs(path, exist_ok=True)  # # OK si existe # # Robustesse


def now_iso_for_filename() -> str:  # # Timestamp filename # # Respect: traçabilité
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # Format stable # # Respect: noms de fichiers traçables


def is_empty(value: Any) -> bool:  # # Détection "vide" # # Respect: qualité sortie JSON
    if value is None:  # # None # # Respect: qualité
        return True  # # Vide # # Respect: qualité
    if isinstance(value, str):  # # String # # Respect: qualité
        v = value.strip()  # # Trim # # Respect: nettoyage
        if v == "":  # # Vide # # Respect: qualité
            return True  # # Vide
        if v.lower() in {"n/a", "null", "none"}:  # # Marqueurs # # Respect: qualité
            return True  # # Vide
    if isinstance(value, list):  # # Liste # # Respect: qualité
        return len(value) == 0  # # Vide si liste vide # # Respect: qualité
    return False  # # Non vide # # Respect: qualité


def sleep_polite(min_s: float = 1.2, max_s: float = 2.0) -> None:  # # Politesse # # Respect: fréquence raisonnable
    time.sleep(random.uniform(min_s, max_s))  # # Jitter # # Respect: anti-spam


def save_text_file(folder: str, filename: str, content: str) -> str:  # # Sauvegarde # # Respect: cache local visible
    ensure_dir(folder)  # # Assurer dossier # # Respect: cache disque
    path = os.path.join(folder, filename)  # # Chemin # # Respect: cohérence
    with open(path, "w", encoding="utf-8") as f:  # # UTF-8 # # Respect: robustesse encodage
        f.write(content)  # # Écriture # # Respect: traçabilité/debug
    return path  # # Retour chemin # # Respect: utilisateur peut retrouver le fichier


def normalize_url(href: str) -> str:  # # Normalise URL # # Respect: champs propres
    if not href:  # # Si vide # # Respect: robustesse
        return ""  # # Retour vide # # Respect: robustesse
    h = href.strip()  # # Trim # # Respect: sortie propre
    if h.startswith("//"):  # # Schéma manquant # # Respect: robustesse
        return "https:" + h  # # Force https # # Respect: sortie valide
    if h.startswith("/"):  # # Relatif # # Respect: robustesse
        return ARXIV_BASE + h  # # Absolu # # Respect: sortie valide
    return h  # # Déjà absolu # # Respect: sortie valide


def abs_url(arxiv_id: str) -> str:  # # /abs # # Respect: sortie utile
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # Construit URL # # Respect: champs minimaux utiles


def pdf_url(arxiv_id: str) -> str:  # # /pdf # # Respect: sortie utile
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # Construit URL # # Respect: champs minimaux utiles


def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # Missing fields # # Respect: debug qualité
    missing: List[str] = []  # # Init # # Respect: structuration
    for f in SUPPORTED_FIELDS:  # # Parcours # # Respect: champs stables
        if is_empty(item.get(f)):  # # Si vide # # Respect: diagnostic
            missing.append(f)  # # Ajoute # # Respect: diagnostic
    return missing  # # Retour # # Respect: sortie structurée


def _detect_weird_page_signals(html: str) -> Dict[str, bool]:  # # Analyse anti-bot/consent # # Respect: robustesse + transparence
    h = (html or "").lower()  # # Lower # # Respect: détection robuste
    return {  # # Drapeaux # # Respect: diagnostic clair
        "contains_we_are_sorry": ("we are sorry" in h),  # # Message blocage # # Respect: diagnostic
        "contains_robot": ("robot" in h),  # # Mention robot # # Respect: diagnostic
        "contains_captcha": ("captcha" in h),  # # CAPTCHA # # Respect: diagnostic
        "contains_consent": ("consent" in h or "cookie" in h),  # # Consent/cookies # # Respect: diagnostic
        "contains_no_results": ("no results found" in h),  # # Aucun résultat # # Respect: diagnostic
    }


def http_get_text(session: requests.Session, url: str, timeout_s: int = HTTP_TIMEOUT_S) -> Tuple[str, int]:  # # GET HTML # # Respect: scraping public + timeout + retry
    headers = {  # # Headers # # Respect: requête propre
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/4.1",  # # UA clair # # Respect: scraping propre
        "Accept-Language": "en-US,en;q=0.9",  # # Langue stable # # Robustesse
    }  # # Fin headers # # Respect: requête propre

    last_text = ""  # # Buffer # # Respect: debug/robustesse
    last_code = 0  # # Buffer # # Respect: debug/robustesse

    for attempt in range(HTTP_RETRY_MAX + 1):  # # Boucle retry # # Respect: robuste sans spam
        resp = session.get(url, headers=headers, timeout=timeout_s)  # # GET # # Respect: timeout
        last_text = resp.text  # # Stocke html # # Respect: debug
        last_code = resp.status_code  # # Stocke code # # Respect: debug
        if last_code not in HTTP_RETRY_STATUS:  # # Si pas à retry # # Respect: limiter requêtes
            break  # # Stop # # Respect: fréquence raisonnable
        if attempt < HTTP_RETRY_MAX:  # # Si on peut retry # # Respect: contrôle
            time.sleep(1.5 + attempt * 1.5)  # # Backoff léger # # Respect: éviter spam
    return last_text, last_code  # # HTML + code # # Respect: sortie contrôlée


# ============================================================  # #
# 🔎 Construction URL search/cs (SANS cat: dans query)           # #
# ============================================================  # #
def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # URL CS HTML # # Respect: scope CS
    q = requests.utils.quote((query or "").strip())  # # Encode query # # Respect: requête propre
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # URL stable # # Respect: HTML public
    s = (sort or "relevance").strip().lower()  # # Normalise tri # # Respect: contrôle
    if s in {"submitted_date", "submitted", "recent"}:  # # Tri récents # # Respect: option projet
        return base + "&order=-announced_date_first"  # # Ajoute param # # Respect: contrôle
    return base  # # relevance par défaut # # Respect: comportement stable


# ============================================================  # #
# 🧲 Extraction catégories depuis "Subjects" + tags (robuste)     # #
# ============================================================  # #
_RE_ANY_CAT = re.compile(r"\(((?:cs|stat|eess)\.[A-Z]{2})\)")  # # Regex cat # # Respect: inclut cross-lists (stat.ML/eess.IV)
_RE_ARXIV_ID = re.compile(r"/abs/([^?#/]+)")  # # Regex ID # # Respect: extraction stable


def extract_categories_from_result(li: Tag) -> Tuple[str, List[str]]:  # # Lit catégories # # Respect: filtrage thématique après search/cs
    cats: List[str] = []  # # Init # # Respect: structuration

    # (1) Méthode robuste: tags visibles (quand arXiv rend des badges)
    for span in li.select("span.tag"):  # # Parcours tags # # Respect: extraction ciblée
        t = (span.get_text(" ", strip=True) or "").strip()  # # Texte tag # # Respect: nettoyage
        if re.fullmatch(r"(?:cs|stat|eess)\.[A-Z]{2}", t):  # # Si ressemble à une cat # # Respect: filtrage fiable
            cats.append(t)  # # Ajoute # # Respect: structuration

    # (2) Méthode fallback: regex sur la ligne "Subjects: ... (cs.XX); ... (stat.ML)"
    if not cats:  # # Si tags absents # # Respect: robustesse
        txt = li.get_text(" ", strip=True)  # # Texte bloc (minimum) # # Respect: extraction juste pour cat
        cats = _RE_ANY_CAT.findall(txt)  # # Extrait cats # # Respect: mapping demandé

    # Dédoublonnage en gardant l'ordre
    cats = list(dict.fromkeys(cats))  # # Dédoublonne # # Respect: sortie propre
    primary = cats[0] if cats else ""  # # Premier # # Respect: structuration
    return primary, cats  # # Retour # # Respect: sortie structurée


# ============================================================  # #
# 🧾 Parsing page search/cs -> items minimaux                     # #
# ============================================================  # #
def parse_search_page(html: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:  # # Parse + diag # # Respect: robustesse
    soup = BeautifulSoup(html, "lxml")  # # Parse # # Respect: extraction ciblée
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""  # # Titre page # # Respect: diagnostic
    weird = _detect_weird_page_signals(html)  # # Détection anti-bot/no-results # # Respect: robustesse

    diag: Dict[str, Any] = {  # # Diagnostic # # Respect: traçabilité
        "page_title": page_title,  # # Titre # # Respect: debug
        "has_abs_links": ("/abs/" in (html or "")),  # # Indicateur principal # # Respect: debug
        **weird,  # # Drapeaux # # Respect: debug
    }

    items: List[Dict[str, Any]] = []  # # Résultats # # Respect: sortie structurée

    # Sélecteur principal (arXiv actuel)
    result_nodes = soup.select("ol.breathe-horizontal li.arxiv-result")  # # Noeuds résultats # # Respect: extraction ciblée
    diag["selector_count_arxiv_result"] = len(result_nodes)  # # Compte # # Respect: debug

    # Fallback: si DOM change, on reconstruit via liens /abs/
    if not result_nodes and diag["has_abs_links"]:  # # Pas de noeuds mais /abs/ présent # # Respect: robustesse HTML
        diag["fallback_mode"] = "abs_links"  # # Indique fallback # # Respect: traçabilité
        abs_ids = _RE_ARXIV_ID.findall(html or "")  # # IDs # # Respect: extraction stable
        abs_ids = list(dict.fromkeys(abs_ids))[:PAGE_SIZE]  # # Dédoublonne + limite # # Respect: contrôle volume
        for arxiv_id in abs_ids:  # # Parcours # # Respect: sortie structurée
            items.append({  # # Item minimal # # Respect: pas de HTML brut au LLM
                "arxiv_id": arxiv_id,  # # ID # # Respect: identifiant
                "title": "",  # # Vide # # Respect: minimal
                "authors": [],  # # Vide # # Respect: minimal
                "abstract": "",  # # Vide # # Respect: minimal
                "submitted_date": "",  # # Vide # # Respect: minimal
                "abs_url": abs_url(arxiv_id),  # # URL # # Respect: utile
                "pdf_url": pdf_url(arxiv_id),  # # URL # # Respect: utile
                "primary_category": "",  # # Vide # # Respect: filtrage possible plus tard
                "all_categories": [],  # # Vide # # Respect: filtrage possible plus tard
            })
        return items, diag  # # Retour # # Respect: robustesse

    # Mode normal
    for li in result_nodes:  # # Parcours # # Respect: extraction minimale
        title_el = li.select_one("p.title")  # # Titre # # Respect: champs essentiels
        authors_el = li.select_one("p.authors")  # # Auteurs # # Respect: champs essentiels
        abstract_el = li.select_one("span.abstract-full")  # # Abstract # # Respect: champs essentiels
        submitted_el = li.select_one("p.is-size-7")  # # Date # # Respect: champs essentiels

        abs_a = li.select_one('p.list-title a[href*="/abs/"]')  # # Lien abs # # Respect: stable
        pdf_a = li.select_one('p.list-title a[href*="/pdf/"]')  # # Lien pdf # # Respect: utile
        abs_href = normalize_url(abs_a.get("href") if abs_a else "")  # # Normalise # # Respect: sortie propre
        pdf_href = normalize_url(pdf_a.get("href") if pdf_a else "")  # # Normalise # # Respect: sortie propre

        arxiv_id = ""  # # Init # # Respect: structuration
        m = re.search(r"/abs/([^?#/]+)", abs_href) if abs_href else None  # # Parse ID # # Respect: extraction précise
        if m:  # # Si match # # Respect: robustesse
            arxiv_id = m.group(1).strip()  # # ID # # Respect: structuration

        title_txt = title_el.get_text(" ", strip=True) if title_el else ""  # # Titre # # Respect: extraction minimale
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # Auteurs # # Respect: extraction minimale
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # Liste # # Respect: sortie structurée
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # Abstract # # Respect: extraction minimale
        abstract = abstract.replace("△ Less", "").strip()  # # Nettoyage # # Respect: réduire bruit

        submitted_date = ""  # # Init # # Respect: structuration
        if submitted_el:  # # Si présent # # Respect: robustesse
            txt = submitted_el.get_text(" ", strip=True)  # # Texte # # Respect: extraction minimale
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # Regex # # Respect: extraction ciblée
            if m3:  # # Si match # # Respect: robustesse
                submitted_date = m3.group(1).strip()  # # Date # # Respect: structuration

        primary_cat, all_cats = extract_categories_from_result(li)  # # Cats # # Respect: filtrage thématique demandé

        if arxiv_id and is_empty(abs_href):  # # Fallback # # Respect: robustesse
            abs_href = abs_url(arxiv_id)  # # Construit # # Respect: sortie utile
        if arxiv_id and is_empty(pdf_href):  # # Fallback # # Respect: robustesse
            pdf_href = pdf_url(arxiv_id)  # # Construit # # Respect: sortie utile

        items.append({  # # Ajout item # # Respect: sortie structurée
            "arxiv_id": arxiv_id,  # # ID # # Respect: minimal utile
            "title": title_txt,  # # Title # # Respect: minimal utile
            "authors": authors,  # # Authors # # Respect: minimal utile
            "abstract": abstract,  # # Abstract # # Respect: minimal utile (pas HTML brut)
            "submitted_date": submitted_date,  # # Date # # Respect: minimal utile
            "abs_url": abs_href,  # # URL # # Respect: minimal utile
            "pdf_url": pdf_href,  # # URL # # Respect: minimal utile
            "primary_category": primary_cat,  # # Cat # # Respect: filtrage thèmes
            "all_categories": all_cats,  # # Cats # # Respect: filtrage thèmes
        })

    return items, diag  # # Retour # # Respect: robustesse + traçabilité


# ============================================================  # #
# 🔎 Parsing /abs (DOI + versions + abstract fallback)           # #
# ============================================================  # #
def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # Parse /abs # # Respect: enrichissement minimal seulement
    soup = BeautifulSoup(abs_html, "lxml")  # # Parse # # Respect: extraction ciblée
    out: Dict[str, Any] = {"doi": "", "versions": [], "last_updated_raw": "", "abstract": ""}  # # Init # # Respect: sortie structurée

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # DOI # # Respect: champ utile
    if doi_a:  # # Si DOI # # Respect: robustesse
        out["doi"] = doi_a.get_text(" ", strip=True)  # # Valeur # # Respect: extraction ciblée

    abs_el = soup.select_one("blockquote.abstract")  # # Abstract # # Respect: essentiel
    if abs_el:  # # Si présent # # Respect: robustesse
        txt = abs_el.get_text(" ", strip=True)  # # Texte # # Respect: extraction ciblée
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()  # # Nettoyage # # Respect: réduire bruit
        out["abstract"] = txt  # # Stocke # # Respect: sortie structurée

    versions: List[Dict[str, str]] = []  # # Init # # Respect: structuration
    for li in soup.select("div.submission-history li"):  # # Versions # # Respect: extraction utile
        txt = li.get_text(" ", strip=True)  # # Texte # # Respect: extraction ciblée
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # Parse # # Respect: extraction ciblée
        if m:  # # Si match # # Respect: robustesse
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # Ajoute # # Respect: sortie structurée
    out["versions"] = versions  # # Stocke # # Respect: sortie structurée
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # Last # # Respect: champ utile

    return out  # # Retour # # Respect: sortie structurée


# ============================================================  # #
# 🧠 Filtrage thématique (par catégories + keywords)              # #
# ============================================================  # #
def _allowed_subcats_for_theme(theme: Optional[str]) -> List[str]:  # # Allowed cats # # Respect: scope strict
    if theme and theme in THEME_TO_ARXIV_SUBCATS:  # # Si thème # # Respect: scope demandé
        return THEME_TO_ARXIV_SUBCATS[theme]  # # Retour liste # # Respect: périmètre strict
    return sorted({c for lst in THEME_TO_ARXIV_SUBCATS.values() for c in lst})  # # Union # # Respect: limité aux 6 thèmes


def _keyword_filter(items: List[Dict[str, Any]], theme: Optional[str]) -> List[Dict[str, Any]]:  # # Keyword fallback # # Respect: pertinence
    if not theme or theme not in THEME_KEYWORDS:  # # Si pas de thème # # Respect: logique simple
        return items  # # Pas de filtre # # Respect: ne pas inventer
    kws = [k.lower() for k in THEME_KEYWORDS[theme]]  # # Lower # # Respect: robustesse
    out: List[Dict[str, Any]] = []  # # Init # # Respect: sortie structurée
    for it in items:  # # Parcours # # Respect: traitement contrôlé
        blob = ((it.get("title") or "") + " " + (it.get("abstract") or "")).lower()  # # Texte # # Respect: filtrage minimal
        if any(k in blob for k in kws):  # # Match # # Respect: pertinence
            out.append(it)  # # Ajoute # # Respect: sortie structurée
    return out  # # Retour # # Respect: filtrage explicite


def filter_items_by_subcats(items: List[Dict[str, Any]], allowed_subcats: List[str]) -> List[Dict[str, Any]]:  # # Filtre cat # # Respect: périmètre
    allowed = set(allowed_subcats)  # # Set # # Respect: performance
    out: List[Dict[str, Any]] = []  # # Init # # Respect: sortie structurée
    for it in items:  # # Parcours # # Respect: traitement contrôlé
        cats = it.get("all_categories") or []  # # Cats # # Respect: filtrage thématique
        if not cats:  # # Si extraction ratée # # Respect: robustesse (éviter faux négatif)
            out.append(it)  # # Conserver # # Respect: ne pas jeter sans preuve
            continue  # # Next # # Respect: robustesse
        if any(c in allowed for c in cats):  # # Match # # Respect: scope demandé
            out.append(it)  # # Garder # # Respect: périmètre strict
    return out  # # Retour # # Respect: filtrage explicite


# ============================================================  # #
# ✅ Fonction principale                                         # #
# ============================================================  # #
def scrape_arxiv_cs_scoped(
    user_query: str,  # # Query user # # Respect: besoin informationnel
    theme: Optional[str] = None,  # # Thème # # Respect: scope demandé
    max_results: int = 20,  # # Limite # # Respect: pas massif
    sort: str = "relevance",  # # Tri # # Respect: contrôle
    polite_min_s: float = 1.2,  # # Politesse # # Respect: faible fréquence
    polite_max_s: float = 2.0,  # # Politesse # # Respect: faible fréquence
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Cache # # Respect: écrire dans raw/cache
    enrich_abs: bool = True,  # # Enrich /abs # # Respect: utile (doi/versions)
    enable_keyword_filter: bool = True,  # # Keyword fallback # # Respect: pertinence
) -> Dict[str, Any]:  # # Retour structuré # # Respect: sortie JSON

    # ===============================  # #
    # 🧱 Préparation paramètres        # #
    # ===============================  # #
    max_results = int(max_results)  # # Cast # # Respect: robustesse
    if max_results < 1:  # # Borne basse # # Respect: robustesse
        max_results = 1  # # Fix # # Respect: robustesse
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # Cap # # Respect: pas massif
        max_results = MAX_RESULTS_HARD_LIMIT  # # Fix # # Respect: pas aspirateur

    if not os.path.isabs(data_lake_raw_dir):  # # Si relatif # # Respect: éviter écrire "ailleurs"
        data_lake_raw_dir = os.path.abspath(os.path.join(PROJECT_ROOT, data_lake_raw_dir))  # # Base projet # # Respect: cache local attendu

    ensure_dir(data_lake_raw_dir)  # # Dossier cache # # Respect: cache local visible
    ts = now_iso_for_filename()  # # Timestamp # # Respect: traçabilité
    session = requests.Session()  # # Session HTTP # # Respect: performance + robustesse

    # ===============================  # #
    # 🎯 Allowed categories            # #
    # ===============================  # #
    allowed_subcats = _allowed_subcats_for_theme(theme)  # # Liste cats # # Respect: périmètre thèmes

    # ===============================  # #
    # 🔎 Pagination search/cs          # #
    # ===============================  # #
    collected: List[Dict[str, Any]] = []  # # Items bruts CS # # Respect: collecte contrôlée
    bundle_parts: List[str] = []  # # HTML debug # # Respect: cache local (pas envoyé au LLM)
    start = 0  # # Pagination # # Respect: contrôle volume
    last_search_url = ""  # # Debug # # Respect: traçabilité
    last_search_http: Optional[int] = None  # # Debug # # Respect: traçabilité
    diag_last: Dict[str, Any] = {}  # # Debug # # Respect: traçabilité
    anti_bot_or_weird_page = False  # # Flag # # Respect: transparence

    while len(collected) < max_results:  # # Loop # # Respect: contrôle volume
        search_url = build_search_url(query=user_query, start=start, size=PAGE_SIZE, sort=sort)  # # URL # # Respect: query simple
        last_search_url = search_url  # # Trace # # Respect: debug
        html, code = http_get_text(session=session, url=search_url, timeout_s=HTTP_TIMEOUT_S)  # # GET # # Respect: timeout+retry
        last_search_http = code  # # Trace # # Respect: debug

        weird = _detect_weird_page_signals(html)  # # Signaux # # Respect: diagnostiquer consent/robot/no-results

        bundle_parts.append(f"<!-- SEARCH URL: {search_url} | HTTP {code} -->\n")  # # En-tête debug # # Respect: traçabilité
        bundle_parts.append(f"<!-- WEIRD: {json.dumps(weird)} -->\n")  # # Signaux debug # # Respect: traçabilité
        bundle_parts.append((html or "")[:200000])  # # Coupe 200k # # Respect: pas massif, cache debug local
        bundle_parts.append("\n<!-- END SEARCH -->\n")  # # Fin bloc # # Respect: traçabilité

        if code != 200:  # # HTTP KO # # Respect: robustesse
            break  # # Stop # # Respect: ne pas boucler
        if weird.get("contains_we_are_sorry") or weird.get("contains_robot") or weird.get("contains_captcha"):  # # Anti-bot # # Respect: robustesse
            anti_bot_or_weird_page = True  # # Flag # # Respect: transparence
            break  # # Stop # # Respect: ne pas insister

        page_items, diag = parse_search_page(html)  # # Parse # # Respect: extraction ciblée
        diag_last = diag  # # Trace # # Respect: debug

        if diag.get("contains_no_results"):  # # Aucun résultat # # Respect: robustesse
            break  # # Stop # # Respect: contrôle
        if not page_items:  # # Rien parsé # # Respect: robustesse
            break  # # Stop # # Respect: contrôle

        collected.extend(page_items)  # # Ajoute # # Respect: collecte contrôlée

        # ✅ CORRECTION IMPORTANTE : si la page a < PAGE_SIZE résultats, inutile d'aller à start+50
        if len(page_items) < PAGE_SIZE:  # # Dernière page probable # # Respect: éviter requêtes inutiles (et erreurs 500)
            break  # # Stop # # Respect: fréquence raisonnable

        start += PAGE_SIZE  # # Next page # # Respect: pagination contrôlée
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse # # Respect: éviter spam

    collected = collected[:max_results]  # # Tronque # # Respect: limite demandée

    # ===============================  # #
    # 🧹 Filtrage par catégories        # #
    # ===============================  # #
    filtered = filter_items_by_subcats(collected, allowed_subcats=allowed_subcats)  # # Filtre cats # # Respect: scope demandé
    if enable_keyword_filter:  # # Si activé # # Respect: pertinence
        filtered = _keyword_filter(filtered, theme=theme)  # # Filtre mots-clés # # Respect: fallback si cats manquent

    # ===============================  # #
    # 🔎 Enrich /abs                   # #
    # ===============================  # #
    if enrich_abs:  # # Si enrich # # Respect: enrichissement minimal
        for it in filtered:  # # Parcours # # Respect: traitement contrôlé
            it["doi"] = ""  # # Init # # Respect: champs stables
            it["versions"] = []  # # Init # # Respect: champs stables
            it["last_updated_raw"] = ""  # # Init # # Respect: champs stables
            it["errors"] = []  # # Init # # Respect: sortie structurée

            url_abs = it.get("abs_url") or ""  # # URL # # Respect: utile
            if not url_abs:  # # Si absent # # Respect: robustesse
                continue  # # Skip # # Respect: robustesse

            abs_html, abs_code = http_get_text(session=session, url=url_abs, timeout_s=HTTP_TIMEOUT_S)  # # GET /abs # # Respect: timeout+retry
            bundle_parts.append(f"<!-- ABS URL: {url_abs} | HTTP {abs_code} -->\n")  # # Debug # # Respect: traçabilité
            bundle_parts.append((abs_html or "")[:200000])  # # Coupe # # Respect: pas massif
            bundle_parts.append("\n<!-- END ABS -->\n")  # # Fin # # Respect: traçabilité

            if abs_code == 200:  # # OK # # Respect: robustesse
                abs_data = parse_abs_page(abs_html)  # # Parse # # Respect: extraction ciblée
                it["doi"] = abs_data.get("doi", "")  # # DOI # # Respect: champ utile
                it["versions"] = abs_data.get("versions", [])  # # Versions # # Respect: champ utile
                it["last_updated_raw"] = abs_data.get("last_updated_raw", "")  # # Last # # Respect: champ utile
                if is_empty(it.get("abstract")) and not is_empty(abs_data.get("abstract")):  # # Fallback abstract # # Respect: compléter sans bruit
                    it["abstract"] = abs_data.get("abstract", "")  # # Inject # # Respect: qualité
            else:  # # KO # # Respect: robustesse
                it["errors"].append(f"abs_http_{abs_code}")  # # Trace # # Respect: diagnostic

            sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse # # Respect: éviter spam

    # Missing fields
    for it in filtered:  # # Parcours # # Respect: diagnostic qualité
        it["missing_fields"] = compute_missing_fields(it)  # # Ajoute # # Respect: sortie structurée + debug

    # ===============================  # #
    # 💾 Sauvegardes cache raw         # #
    # ===============================  # #
    bundle_name = f"scrape_arxiv_cs_bundle_{ts}.html"  # # Nom # # Respect: cache debug
    bundle_path = save_text_file(data_lake_raw_dir, bundle_name, "\n".join(bundle_parts))  # # Save # # Respect: cache local visible

    result: Dict[str, Any] = {  # # Résultat # # Respect: sortie JSON structurée
        "ok": True,  # # Statut # # Respect: API stable
        "user_query": user_query,  # # Query # # Respect: traçabilité
        "theme": theme,  # # Thème # # Respect: traçabilité
        "allowed_subcats": allowed_subcats,  # # Périmètre # # Respect: scope explicite
        "sort": sort,  # # Tri # # Respect: contrôle
        "requested_max_results": max_results,  # # Limite # # Respect: pas massif
        "count_collected_cs": len(collected),  # # Collecte # # Respect: debug
        "count_after_theme_filter": len(filtered),  # # Après filtre # # Respect: debug
        "items": filtered,  # # Items # # Respect: sortie structurée
        "bundle_html_file": bundle_path,  # # HTML debug # # Respect: cache local (pas LLM)
        "supported_fields": SUPPORTED_FIELDS,  # # Schéma # # Respect: contrat clair
        # Debug important
        "project_root": PROJECT_ROOT,  # # Où est le projet # # Respect: traçabilité
        "raw_cache_dir": data_lake_raw_dir,  # # Où écrit-on # # Respect: visibilité
        "cwd_runtime": os.getcwd(),  # # CWD # # Respect: debug uvicorn
        "last_search_url": last_search_url,  # # Dernière URL # # Respect: debug
        "last_search_http": last_search_http,  # # Dernier HTTP # # Respect: debug
        "parse_diag_last": diag_last,  # # Dernier diag # # Respect: debug
        "anti_bot_or_weird_page": anti_bot_or_weird_page,  # # Flag # # Respect: transparence
    }  # # Fin result # # Respect: JSON propre

    json_name = f"scrape_arxiv_cs_{ts}.json"  # # Nom json # # Respect: cache résultat
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # Path # # Respect: cache local
    with open(json_path, "w", encoding="utf-8") as f:  # # Open # # Respect: robustesse encodage
        json.dump(result, f, ensure_ascii=False, indent=2)  # # Dump # # Respect: sortie structurée

    result["saved_to"] = json_path  # # Chemin # # Respect: retrouver facilement le fichier
    return result  # # Retour # # Respect: contrat clair


# ============================================================  # #
# ✅ Alias compatibilité avec ton main.py                         # #
# ============================================================  # #
def scrape_arxiv_cs(  # # Alias # # Respect: ne pas casser ton main.py existant
    query: str,  # # Query # # Respect: input simple
    max_results: int = 50,  # # Limite # # Respect: contrôle volume
    sort: str = "relevance",  # # Tri # # Respect: contrôle
    polite_min_s: float = 1.2,  # # Politesse # # Respect: fréquence raisonnable
    polite_max_s: float = 2.0,  # # Politesse # # Respect: fréquence raisonnable
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Cache # # Respect: écrit dans raw/cache
    theme: Optional[str] = None,  # # Thème # # Respect: scope
) -> Dict[str, Any]:  # # Retour structuré # # Respect: JSON
    return scrape_arxiv_cs_scoped(  # # Forward # # Respect: point d'entrée unique
        user_query=query,  # # Map # # Respect: cohérence
        theme=theme,  # # Map # # Respect: cohérence
        max_results=max_results,  # # Map # # Respect: cohérence
        sort=sort,  # # Map # # Respect: cohérence
        polite_min_s=polite_min_s,  # # Map # # Respect: cohérence
        polite_max_s=polite_max_s,  # # Map # # Respect: cohérence
        data_lake_raw_dir=data_lake_raw_dir,  # # Map # # Respect: cohérence
        enrich_abs=True,  # # On enrichit # # Respect: utile (doi/versions/abstract)
        enable_keyword_filter=True,  # # On garde fallback # # Respect: évite faux négatifs
    )


# ============================================================  # #
# ✅ TEST LOCAL                                                  # #
# ============================================================  # #
RUN_LOCAL_TEST = True  # # True = test ON # # Respect: debug local sans FastAPI

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # Entry # # Respect: exécution locale maîtrisée
    res = scrape_arxiv_cs_scoped(  # # Run # # Respect: test contrôlé
        user_query="multimodal transformer misogyny detection",  # # Exemple # # Respect: besoin informationnel
        theme="ai_ml",  # # Thème # # Respect: périmètre demandé
        max_results=5,  # # Limite # # Respect: pas massif
        sort="relevance",  # # Tri # # Respect: contrôle
        data_lake_raw_dir=DEFAULT_RAW_DIR,  # # Cache # # Respect: écrit au bon endroit
        enrich_abs=True,  # # Enrich # # Respect: utile
    )  # # Fin # # Respect: test
    print(json.dumps({  # # Print # # Respect: debug lisible
        "count_collected_cs": res.get("count_collected_cs"),  # # Info # # Respect: debug
        "count_after_theme_filter": res.get("count_after_theme_filter"),  # # Info # # Respect: debug
        "saved_to": res.get("saved_to"),  # # Info # # Respect: retrouver JSON
        "bundle_html_file": res.get("bundle_html_file"),  # # Info # # Respect: retrouver HTML
        "anti_bot_or_weird_page": res.get("anti_bot_or_weird_page"),  # # Info # # Respect: transparence
        "last_search_http": res.get("last_search_http"),  # # Info # # Respect: debug
        "parse_diag_last": res.get("parse_diag_last"),  # # Info # # Respect: debug
    }, ensure_ascii=False, indent=2))  # # Pretty # # Respect: lecture facile
