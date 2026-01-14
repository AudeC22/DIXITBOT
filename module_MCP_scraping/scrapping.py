# ============================================================  # #
# ✅ Scraper arXiv CS (ciblé thématique + sortie structurée)     # #
# Objectif :                                                     # #
# - Scraping ciblé sur les thèmes demandés (pas "aspirateur")     # #
# - Sortie JSON structurée (pas de HTML brut envoyé au LLM)       # #
# - Extraction minimale : title/authors/abstract/dates/urls/doi    # #
# - Cache + politesse + robustesse                               # #
# - ✅ CORRECTION: on ne met PAS "cat:cs.XX" dans la query HTML    # #
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
            return cur  # # Racine OK
        if os.path.isfile(os.path.join(cur, "requirements.txt")):  # # Marqueur projet # # Respect: structure projet
            return cur  # # Racine OK

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


# ============================================================  # #
# 🎯 Thèmes demandés -> sous-catégories arXiv CS autorisées      # #
# ============================================================  # #
THEME_TO_ARXIV_SUBCATS: Dict[str, List[str]] = {  # # Mapping thème->codes # # Respect: périmètre strict
    "ai_ml": ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.MA", "cs.NE"],  # # IA/ML/NLP/CV/Agents/Neural
    "algo_ds": ["cs.DS", "cs.CC"],  # # Algo/DS/Complexité
    "net_sys": ["cs.NI", "cs.DC", "cs.OS"],  # # Réseau/Distrib/OS
    "cyber_crypto": ["cs.CR"],  # # Crypto/Sécu
    "pl_se": ["cs.PL", "cs.SE", "cs.LO"],  # # Langages/SE/Logique
    "hci_data": ["cs.HC", "cs.IR", "cs.DB", "cs.MM"],  # # HCI/IR/DB/MM
}

# ============================================================  # #
# 🧠 Keywords fallback (si pas de thème explicite)               # #
# ============================================================  # #
THEME_KEYWORDS: Dict[str, List[str]] = {  # # Support # # Respect: filtrage pertinence
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
# 🧩 Helpers base                                             # #
# ============================================================  # #
def ensure_dir(path: str) -> None:  # # Créer dossier # # Respect: cache disque demandé
    os.makedirs(path, exist_ok=True)  # # OK si existe # # Robustesse


def now_iso_for_filename() -> str:  # # Timestamp filename # # Respect: traçabilité
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # Format stable


def is_empty(value: Any) -> bool:  # # Détection "vide" # # Respect: qualité sortie JSON
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return True
        if v.lower() in {"n/a", "null", "none"}:
            return True
    if isinstance(value, list):
        return len(value) == 0
    return False


def sleep_polite(min_s: float = 1.2, max_s: float = 2.0) -> None:  # # Politesse # # Respect: fréquence raisonnable
    time.sleep(random.uniform(min_s, max_s))  # # Jitter # # Respect: anti-spam


def save_text_file(folder: str, filename: str, content: str) -> str:  # # Sauvegarde # # Respect: cache local visible
    ensure_dir(folder)  # # Assurer dossier
    path = os.path.join(folder, filename)  # # Chemin
    with open(path, "w", encoding="utf-8") as f:  # # UTF-8
        f.write(content)  # # Écriture
    return path  # # Retour chemin


def normalize_url(href: str) -> str:  # # Normalise URL # # Respect: champs propres
    if not href:
        return ""
    h = href.strip()
    if h.startswith("//"):
        return "https:" + h
    if h.startswith("/"):
        return ARXIV_BASE + h
    return h


def abs_url(arxiv_id: str) -> str:  # # /abs # # Respect: sortie utile
    return f"{ARXIV_BASE}/abs/{arxiv_id}"


def pdf_url(arxiv_id: str) -> str:  # # /pdf # # Respect: sortie utile
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"


def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # Missing fields # # Respect: debug qualité
    missing: List[str] = []
    for f in SUPPORTED_FIELDS:
        if is_empty(item.get(f)):
            missing.append(f)
    return missing


def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # GET HTML # # Respect: scraping public + timeout
    headers = {  # # Headers # # Respect: requête propre
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/4.0",  # # UA clair # # Respect: scraping propre
        "Accept-Language": "en-US,en;q=0.9",  # # Langue stable # # Robustesse
    }
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # GET # # Robustesse timeout
    return resp.text, resp.status_code  # # HTML + code


# ============================================================  # #
# 🔎 Construction URL search/cs (SANS cat: dans query)           # #
# ============================================================  # #
def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # URL CS HTML # # Respect: scope CS
    q = requests.utils.quote((query or "").strip())  # # Encode query # # Respect: requête propre
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # URL stable
    s = (sort or "relevance").strip().lower()
    if s in {"submitted_date", "submitted", "recent"}:
        return base + "&order=-announced_date_first"  # # Tri récents
    return base  # # relevance par défaut


# ============================================================  # #
# 🧲 Extraction catégories depuis "Subjects:" (ex: (... cs.CV))   # #
# ============================================================  # #
_RE_CAT = re.compile(r"\((cs\.[A-Z]{2})\)")  # # Regex cat # # Respect: filtrage thématique fiable


def extract_categories_from_result(li: Tag) -> Tuple[str, List[str]]:  # # Lit "Subjects" # # Respect: filtrage après scraping CS
    txt = li.get_text(" ", strip=True)  # # Texte global du bloc résultat # # Minimal (juste pour extraire cat)
    cats = _RE_CAT.findall(txt)  # # Extrait tous les (cs.XX) # # Respect: mapping demandé
    cats = list(dict.fromkeys(cats))  # # Dédoublonne en gardant l'ordre # # Respect: sortie propre
    primary = cats[0] if cats else ""  # # Premier = catégorie principale # # Respect: structuration
    return primary, cats  # # Retour


# ============================================================  # #
# 🧾 Parsing page search/cs -> items minimaux                     # #
# ============================================================  # #
def parse_search_page(html: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:  # # Parse + diag # # Respect: robustesse
    soup = BeautifulSoup(html, "lxml")  # # Parse # # Respect: extraction ciblée
    title = soup.title.get_text(" ", strip=True) if soup.title else ""  # # Titre page # # Debug anti-bot
    diag: Dict[str, Any] = {"page_title": title}  # # Diagnostic # # Respect: traçabilité

    # ✅ Fallback important : même si les classes changent, on vérifie d'abord la présence de /abs/
    has_abs = ("/abs/" in html)  # # Indicateur principal # # Respect: éviter faux positifs
    diag["has_abs_links"] = has_abs  # # Stocke diag # # Respect: debug

    items: List[Dict[str, Any]] = []  # # Liste résultats

    # Sélecteur principal (structure arXiv actuelle)
    result_nodes = soup.select("ol.breathe-horizontal li.arxiv-result")  # # Résultats # # Respect: extraction ciblée
    diag["selector_count_arxiv_result"] = len(result_nodes)  # # Debug

    # Fallback : si la structure change, on tente un fallback basé sur liens /abs/
    if not result_nodes and has_abs:  # # Si pas trouvé mais /abs/ présent # # Respect: robustesse aux changements HTML
        diag["fallback_mode"] = "abs_links"  # # Indique fallback # # Respect: traçabilité
        # On reconstruit une pseudo-liste depuis les liens /abs/
        abs_ids = re.findall(r"/abs/([0-9]+\.[0-9]+|[a-z-]+/[0-9]+)", html)  # # IDs simples # # Robustesse
        abs_ids = list(dict.fromkeys(abs_ids))[:50]  # # Dédoublonne + limite # # Respect: contrôle volume
        for arxiv_id in abs_ids:
            items.append({
                "arxiv_id": arxiv_id,
                "title": "",
                "authors": [],
                "abstract": "",
                "submitted_date": "",
                "abs_url": abs_url(arxiv_id),
                "pdf_url": pdf_url(arxiv_id),
                "primary_category": "",
                "all_categories": [],
            })
        return items, diag  # # Retour fallback

    # Mode normal : parsing des blocs résultat
    for li in result_nodes:  # # Parcours résultats # # Respect: extraction minimale
        title_el = li.select_one("p.title")  # # Title # # Respect: champs essentiels
        authors_el = li.select_one("p.authors")  # # Authors # # Respect: champs essentiels
        abstract_el = li.select_one("span.abstract-full")  # # Abstract # # Respect: champs essentiels
        submitted_el = li.select_one("p.is-size-7")  # # Submitted date # # Respect: champs essentiels

        # Liens /abs + /pdf
        abs_a = li.select_one('p.list-title a[href*="/abs/"]')  # # Lien abs # # Respect: identifiant stable
        pdf_a = li.select_one('p.list-title a[href*="/pdf/"]')  # # Lien pdf # # Respect: lien utile
        abs_href = normalize_url(abs_a.get("href") if abs_a else "")  # # Normalise # # Respect: sortie propre
        pdf_href = normalize_url(pdf_a.get("href") if pdf_a else "")  # # Normalise

        # arxiv_id
        arxiv_id = ""  # # Init # # Respect: structuration
        m = re.search(r"/abs/([^?#/]+)", abs_href) if abs_href else None  # # Parse id # # Respect: extraction précise
        if m:
            arxiv_id = m.group(1).strip()

        # Texte
        title_txt = title_el.get_text(" ", strip=True) if title_el else ""  # # Titre # # Extraction minimale
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # Auteurs
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # Split # # Structuré
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # Abstract
        abstract = abstract.replace("△ Less", "").strip()  # # Nettoyage léger # # Respect: pas de bruit inutile

        submitted_date = ""  # # Init date
        if submitted_el:
            txt = submitted_el.get_text(" ", strip=True)
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)
            if m3:
                submitted_date = m3.group(1).strip()

        # Catégories depuis "Subjects"
        primary_cat, all_cats = extract_categories_from_result(li)  # # Catégories # # Respect: filtrage thématique demandé

        # URLs fallback
        if arxiv_id and is_empty(abs_href):
            abs_href = abs_url(arxiv_id)
        if arxiv_id and is_empty(pdf_href):
            pdf_href = pdf_url(arxiv_id)

        items.append({
            "arxiv_id": arxiv_id,
            "title": title_txt,
            "authors": authors,
            "abstract": abstract,
            "submitted_date": submitted_date,
            "abs_url": abs_href,
            "pdf_url": pdf_href,
            "primary_category": primary_cat,
            "all_categories": all_cats,
        })

    return items, diag  # # Retour items + diagnostic


# ============================================================  # #
# 🔎 Parsing /abs (DOI + versions + abstract fallback)           # #
# ============================================================  # #
def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # Parse /abs # # Respect: enrichissement minimal seulement
    soup = BeautifulSoup(abs_html, "lxml")
    out: Dict[str, Any] = {"doi": "", "versions": [], "last_updated_raw": "", "abstract": ""}

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # DOI # # Respect: champ utile
    if doi_a:
        out["doi"] = doi_a.get_text(" ", strip=True)

    abs_el = soup.select_one("blockquote.abstract")  # # Abstract # # Respect: contenu essentiel
    if abs_el:
        txt = abs_el.get_text(" ", strip=True)
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()
        out["abstract"] = txt

    versions: List[Dict[str, str]] = []
    for li in soup.select("div.submission-history li"):
        txt = li.get_text(" ", strip=True)
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)
        if m:
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})
    out["versions"] = versions
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""

    return out


# ============================================================  # #
# 🧠 Filtrage thématique (par catégories cs.XX + keywords)        # #
# ============================================================  # #
def _allowed_subcats_for_theme(theme: Optional[str]) -> List[str]:  # # Allowed cats # # Respect: scope strict
    if theme and theme in THEME_TO_ARXIV_SUBCATS:
        return THEME_TO_ARXIV_SUBCATS[theme]
    # Si pas de thème, on autorise l'union (mais toujours limitée aux 6 thèmes)
    return sorted({c for lst in THEME_TO_ARXIV_SUBCATS.values() for c in lst})


def _keyword_filter(items: List[Dict[str, Any]], theme: Optional[str]) -> List[Dict[str, Any]]:  # # Keyword fallback # # Respect: pertinence
    if not theme or theme not in THEME_KEYWORDS:
        return items
    kws = [k.lower() for k in THEME_KEYWORDS[theme]]
    out: List[Dict[str, Any]] = []
    for it in items:
        blob = ((it.get("title") or "") + " " + (it.get("abstract") or "")).lower()
        if any(k in blob for k in kws):
            out.append(it)
    return out


def filter_items_by_subcats(items: List[Dict[str, Any]], allowed_subcats: List[str]) -> List[Dict[str, Any]]:  # # Filtre cat # # Respect: périmètre thèmes
    allowed = set(allowed_subcats)
    out: List[Dict[str, Any]] = []
    for it in items:
        cats = it.get("all_categories") or []
        if any(c in allowed for c in cats):
            out.append(it)
    return out


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
) -> Dict[str, Any]:

    # ===============================  # #
    # 🧱 Préparation paramètres        # #
    # ===============================  # #
    max_results = int(max_results)  # # Cast # # Robustesse
    if max_results < 1:
        max_results = 1
    if max_results > MAX_RESULTS_HARD_LIMIT:
        max_results = MAX_RESULTS_HARD_LIMIT  # # Cap # # Respect: éviter scraping massif

    if not os.path.isabs(data_lake_raw_dir):  # # Si relatif # # Robustesse
        data_lake_raw_dir = os.path.abspath(os.path.join(PROJECT_ROOT, data_lake_raw_dir))  # # Base projet

    ensure_dir(data_lake_raw_dir)  # # Dossier cache # # Respect: cache local visible
    ts = now_iso_for_filename()  # # Timestamp # # Traçabilité
    session = requests.Session()  # # Session HTTP # # Performance / robustesse

    # ===============================  # #
    # 🎯 Allowed categories            # #
    # ===============================  # #
    allowed_subcats = _allowed_subcats_for_theme(theme)  # # Liste cs.XX # # Respect: périmètre thèmes

    # ===============================  # #
    # 🔎 Pagination search/cs          # #
    # ===============================  # #
    collected: List[Dict[str, Any]] = []  # # Items bruts CS
    bundle_parts: List[str] = []  # # HTML debug (cache local)
    start = 0  # # Pagination
    last_search_url = ""  # # Debug
    last_search_http = None  # # Debug
    diag_last: Dict[str, Any] = {}  # # Debug parse

    while len(collected) < max_results:  # # Tant qu'on veut des résultats # # Respect: contrôle volume
        search_url = build_search_url(query=user_query, start=start, size=PAGE_SIZE, sort=sort)  # # ✅ Query simple
        last_search_url = search_url  # # Trace
        html, code = http_get_text(session=session, url=search_url, timeout_s=30)  # # GET
        last_search_http = code  # # Trace

        # Sauvegarde HTML debug (local) sans l'envoyer au LLM # # Respect: "pas de HTML brut au LLM"
        bundle_parts.append(f"<!-- SEARCH URL: {search_url} | HTTP {code} -->\n")
        bundle_parts.append(html[:200000])  # # Coupe à 200k max (debug, pas massif)
        bundle_parts.append("\n<!-- END SEARCH -->\n")

        if code != 200:  # # Si HTTP pas OK # # Robustesse
            break  # # Stop # # Respect: pas de boucle folle

        page_items, diag = parse_search_page(html)  # # Parse résultats
        diag_last = diag  # # Trace diag

        if not page_items:  # # Aucun résultat parsé
            break  # # Stop

        collected.extend(page_items)  # # Ajoute
        start += PAGE_SIZE  # # Page suivante
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse

    collected = collected[:max_results]  # # Tronque # # Respect: limite demandée

    # ===============================  # #
    # 🧪 Diagnostic anti-page-résultats # #
    # ===============================  # #
    anti_bot_or_weird_page = False  # # Flag
    if diag_last.get("has_abs_links") is False:  # # Si pas de /abs/ # # Ton cas actuel
        anti_bot_or_weird_page = True  # # Active flag # # Respect: robustesse + transparence

    # ===============================  # #
    # 🧹 Filtrage par catégories cs.XX  # #
    # ===============================  # #
    filtered = filter_items_by_subcats(collected, allowed_subcats=allowed_subcats)  # # Filtre thème # # Respect: scope demandé

    # Fallback keyword (si activé) : utile quand Subjects manquent
    if enable_keyword_filter:  # # Si activé # # Respect: pertinence
        filtered = _keyword_filter(filtered, theme=theme)  # # Filtre keywords

    # ===============================  # #
    # 🔎 Enrich /abs                   # #
    # ===============================  # #
    if enrich_abs:  # # Si enrichissement # # Respect: utile mais minimal
        for it in filtered:
            it["doi"] = ""  # # Init
            it["versions"] = []  # # Init
            it["last_updated_raw"] = ""  # # Init
            it["errors"] = []  # # Init

            url_abs = it.get("abs_url") or ""  # # URL
            if not url_abs:
                continue

            abs_html, abs_code = http_get_text(session=session, url=url_abs, timeout_s=30)  # # GET /abs
            bundle_parts.append(f"<!-- ABS URL: {url_abs} | HTTP {abs_code} -->\n")
            bundle_parts.append(abs_html[:200000])  # # Debug local
            bundle_parts.append("\n<!-- END ABS -->\n")

            if abs_code == 200:
                abs_data = parse_abs_page(abs_html)
                it["doi"] = abs_data.get("doi", "")
                it["versions"] = abs_data.get("versions", [])
                it["last_updated_raw"] = abs_data.get("last_updated_raw", "")
                if is_empty(it.get("abstract")) and not is_empty(abs_data.get("abstract")):
                    it["abstract"] = abs_data.get("abstract", "")
            else:
                it["errors"].append(f"abs_http_{abs_code}")

            sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Politesse

    # Missing fields
    for it in filtered:
        it["missing_fields"] = compute_missing_fields(it)

    # ===============================  # #
    # 💾 Sauvegardes cache raw         # #
    # ===============================  # #
    bundle_name = f"scrape_arxiv_cs_bundle_{ts}.html"  # # Nom html # # Respect: cache debug
    bundle_path = save_text_file(data_lake_raw_dir, bundle_name, "\n".join(bundle_parts))  # # Save html

    result: Dict[str, Any] = {  # # Résultat final # # Respect: sortie structurée JSON
        "ok": True,
        "user_query": user_query,
        "theme": theme,
        "allowed_subcats": allowed_subcats,
        "sort": sort,
        "requested_max_results": max_results,
        "count_collected_cs": len(collected),
        "count_after_theme_filter": len(filtered),
        "items": filtered,
        "bundle_html_file": bundle_path,
        "supported_fields": SUPPORTED_FIELDS,
        # 🔎 Debug important pour ton cas
        "project_root": PROJECT_ROOT,
        "raw_cache_dir": data_lake_raw_dir,
        "cwd_runtime": os.getcwd(),
        "last_search_url": last_search_url,
        "last_search_http": last_search_http,
        "parse_diag_last": diag_last,
        "anti_bot_or_weird_page": anti_bot_or_weird_page,
    }

    json_name = f"scrape_arxiv_cs_{ts}.json"  # # Nom json # # Respect: cache résultat
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # Path json
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    result["saved_to"] = json_path  # # Pour retrouver le fichier
    return result


# ============================================================  # #
# ✅ Alias compatibilité avec ton main.py                         # #
# ============================================================  # #
def scrape_arxiv_cs(
    query: str,
    max_results: int = 50,
    sort: str = "relevance",
    polite_min_s: float = 1.2,
    polite_max_s: float = 2.0,
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,
    theme: Optional[str] = None,
) -> Dict[str, Any]:
    return scrape_arxiv_cs_scoped(
        user_query=query,
        theme=theme,
        max_results=max_results,
        sort=sort,
        polite_min_s=polite_min_s,
        polite_max_s=polite_max_s,
        data_lake_raw_dir=data_lake_raw_dir,
        enrich_abs=True,
        enable_keyword_filter=True,
    )


# ============================================================  # #
# ✅ TEST LOCAL                                                  # #
# ============================================================  # #
RUN_LOCAL_TEST = True  # # Mets True si tu veux tester en direct

if __name__ == "__main__" and RUN_LOCAL_TEST:
    res = scrape_arxiv_cs_scoped(
        user_query="multimodal transformer misogyny detection",
        theme="ai_ml",
        max_results=5,
        sort="relevance",
        data_lake_raw_dir=DEFAULT_RAW_DIR,
        enrich_abs=True,
    )
    print(json.dumps({k: res.get(k) for k in ["count_collected_cs", "count_after_theme_filter", "saved_to", "bundle_html_file", "anti_bot_or_weird_page"]}, indent=2))
