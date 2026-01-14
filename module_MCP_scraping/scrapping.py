# ============================================================  # #  
# arXiv Scraper (CS search -> /abs -> /html) -> 1 HTML bundle + 1 JSON  # # 
# Objectif  # # 
# - Extraction: search results + /abs (doi, versions, html link) + /html (date, licence, sections, refs)  # # 
# - Sortie: JSON (items enrichis) + 1 fichier HTML "bundle" (debug) dans data_lake/raw  # # 
# ============================================================  # # 

# ===============================  # # 
# Importations  # # 
import os  # # Gestion des chemins/dossiers
import re  # # Regex (ID, dates, versions)
import json  # # Export JSON
import time  # # Politesse (sleep)
import random  # # Jitter pour eviter un rythme trop "robot"
import datetime  # # Timestamp fichiers
from typing import Dict, Any, List, Tuple, Optional  # # Typage pour clarte

import requests  # # HTTP GET (telecharger pages)
from bs4 import BeautifulSoup, Tag  # # Parser HTML + manipuler balises

# ===============================  # # 
# Constantes arXiv  # # 
ARXIV_BASE = "https://arxiv.org"  # # Domaine arXiv
ARXIV_SEARCH_CS = f"{ARXIV_BASE}/search/cs"  # # Endpoint recherche Computer Science
DEFAULT_RAW_DIR = os.path.join("data_lake", "raw", "cache")  # # Stockage raw/cache (bundle + json)
MAX_RESULTS_HARD_LIMIT = 100  # # Limite globale demandee
PAGE_SIZE = 50  # # Taille page arXiv (pagination)

# ===============================  # # 
# Champs supportes (ce qu’on renvoie dans JSON)  # # 
SUPPORTED_FIELDS = [  # # Liste de champs (pour missing_fields)
    "arxiv_id",  # # Identifiant (ex: 2601.07830v1)
    "title",  # # Titre
    "authors",  # # Auteurs
    "abstract",  # # Abstract (depuis search et/ou /abs)
    "submitted_date",  # # "Submitted ..." (depuis search)
    "abs_url",  # # URL /abs
    "pdf_url",  # # URL /pdf (arXiv)
    "doi",  # # DOI (souvent sur /abs, parfois dans references)
    "versions",  # # Liste versions (v1, v2...) depuis /abs
    "last_updated_raw",  # # Derniere version raw (depuis /abs)
    "html_url",  # # URL HTML experimental (depuis /abs OU construit)
    "published_date",  # # Date watermark sur /html (ex: 28 Nov 2025)
    "license",  # # Licence affichee sur /html (ex: arXiv.org perpetual non-exclusive license)
    "sections",  # # Titres + contenus (comme dans le resultat de research elements page Excel)
    "content_text",  # # Texte global concatene (fallback)
    "references",  # # References (raw + liens)
    "references_dois",  # # Liste DOI trouves dans les references
]

# ============================================================  # # 
# A) Helpers (dossiers, timestamps, “vide”, politesse, GET)  # # 
# ============================================================  # # 

def ensure_dir(path: str) -> None:  # # Creer dossier si besoin
    os.makedirs(path, exist_ok=True)  # # Cree (sans erreur si existe)

def now_iso_for_filename() -> str:  # # Timestamp pour noms de fichiers
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # Exemple: 20260114_101500

def is_empty(value: Any) -> bool:  # # Definition du “vide”
    if value is None:  # # None
        return True  # # vide
    if isinstance(value, str):  # # Si string
        v = value.strip()  # # Trim
        if v == "":  # # vide si ""
            return True  # # vide
        if v.lower() in {"n/a", "null", "none"}:  # # vide si "N/A", "null", "None" (string)
            return True  # # vide
    if isinstance(value, list):  # # Si liste
        return len(value) == 0  # # vide si liste vide
    return False  # # sinon non vide

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # Attendre entre min et max secondes

def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # GET HTML -> (texte, status)
    headers = {  # # Headers
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/2.0",  # # User-Agent
        "Accept-Language": "en-US,en;q=0.9",  # # Langue (stabilite parsing)
    }  # # Fin headers
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # GET
    return resp.text, resp.status_code  # # Retourner HTML + code

def save_text_file(folder: str, filename: str, content: str) -> str:  # # Sauver texte dans un fichier
    ensure_dir(folder)  # # Assurer dossier
    path = os.path.join(folder, filename)  # # Construire chemin
    with open(path, "w", encoding="utf-8") as f:  # # Ouvrir en ecriture UTF-8
        f.write(content)  # # Ecrire contenu
    return path  # # Retourner chemin

def normalize_url(href: str) -> str:  # # Normaliser un href relatif/absolu
    if not href:  # # Si vide
        return ""  # # Retour vide
    h = href.strip()  # # Nettoyage
    if h.startswith("//"):  # # URL sans schema
        return "https:" + h  # # Ajouter https:
    if h.startswith("/"):  # # URL relative
        return ARXIV_BASE + h  # # Prefixer domaine
    return h  # # Deja absolu

def abs_url(arxiv_id: str) -> str:  # # Construire URL /abs
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # URL abs

def pdf_url(arxiv_id: str) -> str:  # # Construire URL /pdf
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # URL pdf

def html_url(arxiv_id: str) -> str:  # # Construire URL /html
    return f"{ARXIV_BASE}/html/{arxiv_id}"  # # URL html

def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # Calculer champs vides
    missing: List[str] = []  # # Liste champs manquants
    for f in SUPPORTED_FIELDS:  # # Pour chaque champ attendu
        if is_empty(item.get(f)):  # # Si vide
            missing.append(f)  # # Ajouter
    return missing  # # Retourner liste

# ============================================================  # # 
# B) URL builder (tri compatible arXiv)  # # 
# ============================================================  # # 

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # Construire URL search/cs
    q = requests.utils.quote(query)  # # Encoder requete (espaces etc.)
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # Base URL
    s = (sort or "relevance").strip().lower()  # # Normaliser sort
    if s in {"submitted_date", "submitted", "recent"}:  # # Tri recents (soumission)
        return base + "&order=-announced_date_first"  # # Parametre arXiv OK
    # "relevance" est le defaut du site : pas besoin de &order=-relevance (400)
    return base  # # Relevance default

# ============================================================  # # 
# C) Parsing SEARCH page (liste resultats)  # # 
# ============================================================  # # 

def find_abs_and_pdf_hrefs(li: Tag) -> Tuple[str, str]:  # # Trouver href /abs et /pdf dans un item search
    abs_href = ""  # # Href /abs
    pdf_href = ""  # # Href /pdf

    for a in li.select("a[href]"):  # # Parcourir tous les liens du bloc
        href = (a.get("href") or "").strip()  # # Lire href
        if not href:  # # Vide
            continue  # # Next
        if (not abs_href) and re.search(r"/abs/[^?#/]+", href):  # # Lien abstract
            abs_href = href  # # OK
        if (not pdf_href) and re.search(r"/pdf/[^?#/]+", href):  # # Lien pdf
            pdf_href = href  # # OK
        if abs_href and pdf_href:  # # Des qu’on a les deux
            break  # # Stop

    return abs_href, pdf_href  # # Retour

def extract_arxiv_id_from_any(href: str) -> str:  # # Extraire ID depuis /abs ou /pdf
    if not href:  # # Vide
        return ""  # # Retour vide
    m = re.search(r"/abs/([^?#/]+)", href)  # # Chercher /abs/<id>
    if m:  # # Trouve
        return m.group(1).strip()  # # Retour ID
    m2 = re.search(r"/pdf/([^?#/]+)", href)  # # Chercher /pdf/<id>
    if m2:  # # Trouve
        return m2.group(1).strip()  # # Retour ID
    return ""  # # Pas trouve

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # HTML search -> items (base)
    soup = BeautifulSoup(html, "lxml")  # # Parser HTML (lxml)
    items: List[Dict[str, Any]] = []  # # Liste resultats

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # Chaque resultat
        title_el = li.select_one("p.title")  # # Titre
        authors_el = li.select_one("p.authors")  # # Auteurs
        abstract_el = li.select_one("span.abstract-full")  # # Abstract
        submitted_el = li.select_one("p.is-size-7")  # # Bloc date soumis

        abs_href, pdf_href = find_abs_and_pdf_hrefs(li)  # # Liens
        arxiv_id = extract_arxiv_id_from_any(abs_href or pdf_href)  # # ID depuis lien

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # Texte titre
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # Texte auteurs brut
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # Liste auteurs
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # Texte abstract
        abstract = abstract.replace("△ Less", "").strip()  # # Nettoyage

        submitted_date = ""  # # Date "Submitted ..."
        if submitted_el:  # # Si present
            txt = submitted_el.get_text(" ", strip=True)  # # Texte
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # "Submitted X"
            if m3:  # # OK
                submitted_date = m3.group(1).strip()  # # Date

        abs_full = normalize_url(abs_href)  # # URL abs complete
        pdf_full = normalize_url(pdf_href)  # # URL pdf complete

        if arxiv_id and is_empty(abs_full):  # # Garantir abs_url si on a l'ID
            abs_full = abs_url(arxiv_id)  # # Construire
        if arxiv_id and is_empty(pdf_full):  # # Garantir pdf_url si on a l'ID
            pdf_full = pdf_url(arxiv_id)  # # Construire

        items.append({  # # Ajouter item
            "arxiv_id": arxiv_id,  # # ID
            "title": title,  # # Titre
            "authors": authors,  # # Auteurs
            "abstract": abstract,  # # Abstract
            "submitted_date": submitted_date,  # # Date soumis
            "abs_url": abs_full,  # # URL /abs
            "pdf_url": pdf_full,  # # URL /pdf
        })  # # Fin item

    return items  # # Retour items

# ============================================================  # # 
# D) Parsing /abs (versions + doi + lien HTML experimental + abstract fallback)  # # 
# ============================================================  # # 

def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # /abs -> dict enrichissement
    soup = BeautifulSoup(abs_html, "lxml")  # # Parser HTML
    out: Dict[str, Any] = {  # # Structure sortie
        "doi": "",  # # DOI
        "versions": [],  # # Versions
        "last_updated_raw": "",  # # Derniere version raw
        "html_experimental_url": "",  # # Lien /html
        "abstract": "",  # # Abstract fallback
    }  # # Fin structure

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # DOI table
    if doi_a:  # # Si present
        out["doi"] = doi_a.get_text(" ", strip=True)  # # Texte DOI

    html_a = soup.select_one('div.full-text a[href*="/html/"]')  # # HTML experimental
    if html_a:  # # Si present
        out["html_experimental_url"] = normalize_url(html_a.get("href") or "")  # # URL normalisee

    abs_el = soup.select_one("blockquote.abstract")  # # Abstract /abs
    if abs_el:  # # Si present
        txt = abs_el.get_text(" ", strip=True)  # # Texte brut
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()  # # Enlever "Abstract:"
        out["abstract"] = txt  # # Enregistrer

    versions: List[Dict[str, str]] = []  # # Liste versions
    for li in soup.select("div.submission-history li"):  # # Historique
        txt = li.get_text(" ", strip=True)  # # Texte
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # [v1] ...
        if m:  # # OK
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # Ajouter
    out["versions"] = versions  # # Enregistrer
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # Dernier raw

    return out  # # Retour

# ============================================================  # # 
# E) Parsing /html (date watermark + licence + sections + references)  # # 
# ============================================================  # # 

def clean_text(s: str) -> str:  # # Nettoyage texte simple
    if not s:  # # Vide
        return ""  # # Retour vide
    s = re.sub(r"\s+", " ", s)  # # Espaces multiples -> 1
    return s.strip()  # # Trim

def is_heading(el: Tag) -> bool:  # # Detecter un titre de section
    if not isinstance(el, Tag):  # # Securite
        return False  # # Non
    if el.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:  # # Titres HTML
        return True  # # Oui
    role = (el.get("role") or "").strip().lower()  # # ARIA
    if role == "heading":  # # Role heading
        return True  # # Oui
    classes = " ".join(el.get("class", [])).lower()  # # Classes
    if any(k in classes for k in ["ltx_title", "title", "heading", "section-title"]):  # # Heuristique LaTeXML
        return bool(clean_text(el.get_text(" ", strip=True)))  # # Texte non vide
    return False  # # Non

def collect_section_content(heading_el: Tag, max_chars: int = 8000) -> str:  # # Contenu apres un titre
    contents: List[str] = []  # # Blocs texte
    total = 0  # # Compteur
    for sib in heading_el.next_siblings:  # # Freres suivants
        if isinstance(sib, Tag):  # # Si balise
            if is_heading(sib):  # # Stop au prochain titre
                break  # # Stop
            if sib.name in {"p", "div", "ul", "ol", "table", "figure", "section"}:  # # Blocs pertinents
                txt = clean_text(sib.get_text(" ", strip=True))  # # Texte bloc
                if txt:  # # Non vide
                    contents.append(txt)  # # Ajouter
                    total += len(txt)  # # Compter
        if total >= max_chars:  # # Limite taille
            break  # # Stop
    return clean_text(" ".join(contents))  # # Retour texte section

def extract_sections_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:  # # Extraire sections titre+contenu
    root = soup.select_one("article.ltx_document") or soup.select_one("main") or soup.body or soup  # # Root
    headings: List[Tag] = []  # # Liste titres
    for el in root.find_all(True):  # # Parcourir toutes balises
        if is_heading(el):  # # Filtre titres
            title_text = clean_text(el.get_text(" ", strip=True))  # # Texte
            if title_text:  # # Non vide
                headings.append(el)  # # Ajouter

    sections: List[Dict[str, Any]] = []  # # Resultat
    for i, h in enumerate(headings, start=1):  # # Titres numerotes
        title_text = clean_text(h.get_text(" ", strip=True))  # # Titre
        level = h.name if h.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else "custom"  # # Niveau
        section_text = collect_section_content(h)  # # Contenu associe
        if section_text:  # # Garder uniquement si contenu
            sections.append({  # # Ajouter section
                "section_index": i,  # # Index
                "heading_level": level,  # # Niveau
                "heading": title_text,  # # Heading
                "text": section_text,  # # Texte
            })  # # Fin section
    return sections  # # Retour

def extract_references_from_html(soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], List[str]]:  # # References + DOI
    refs: List[Dict[str, Any]] = []  # # References
    dois_flat: List[str] = []  # # DOI uniques

    bib = soup.select_one(".ltx_biblist") or soup.select_one(".ltx_bibliography")  # # Conteneur
    if not bib:  # # Pas de bibliographie
        return refs, dois_flat  # # Retour vide

    for bi in bib.select(".ltx_bibitem, li, div"):  # # Items bib
        txt = clean_text(bi.get_text(" ", strip=True))  # # Texte ref
        if not txt:  # # Vide
            continue  # # Skip
        links = [clean_text(a.get("href", "")) for a in bi.select("a[href]")]  # # Tous les liens
        links = [l for l in links if l]  # # Filtrer
        dois = [l for l in links if "doi.org/" in l]  # # DOI links
        for d in dois:  # # Ajouter uniques
            if d not in dois_flat:
                dois_flat.append(d)
        pdf_links = [l for l in links if ("/doi/pdf" in l) or l.lower().endswith(".pdf")]  # # PDFs
        refs.append({  # # Ajouter
            "raw_text": txt,  # # Texte brut
            "urls": links,  # # URLs
            "dois": dois,  # # DOI
            "pdf_links": pdf_links,  # # PDFs
        })  # # Fin ref

    return refs, dois_flat  # # Retour

def parse_html_page(html_text: str) -> Dict[str, Any]:  # # /html -> dict
    soup = BeautifulSoup(html_text, "lxml")  # # Parser
    out: Dict[str, Any] = {  # # Structure
        "published_date": "",  # # Date
        "license": "",  # # Licence
        "sections": [],  # # Sections
        "content_text": "",  # # Texte global
        "references": [],  # # References
        "references_dois": [],  # # DOI refs
    }  # # Fin structure

    wm = soup.select_one("#watermark-tr")  # # Watermark
    if wm:  # # Si present
        wm_text = clean_text(wm.get_text(" ", strip=True))  # # Texte
        m = re.search(r"\]\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", wm_text)  # # Date
        if m:  # # OK
            out["published_date"] = m.group(1).strip()  # # Enregistrer

    lic = soup.select_one("a#license-tr")  # # Licence
    if lic:  # # Si present
        lic_text = clean_text(lic.get_text(" ", strip=True))  # # Texte
        lic_text = re.sub(r"^\s*License:\s*", "", lic_text, flags=re.IGNORECASE).strip()  # # Enlever "License:"
        out["license"] = lic_text  # # Enregistrer

    sections = extract_sections_from_html(soup)  # # Sections
    out["sections"] = sections  # # Enregistrer

    if sections:  # # Si sections
        out["content_text"] = "\n\n".join([f"{s['heading']}\n{s['text']}" for s in sections])  # # Concat
    else:  # # Fallback
        doc = soup.select_one("article.ltx_document") or soup.select_one("main") or soup.body  # # Root
        out["content_text"] = doc.get_text("\n", strip=True) if doc else ""  # # Texte brut

    refs, dois_flat = extract_references_from_html(soup)  # # References
    out["references"] = refs  # # Enregistrer
    out["references_dois"] = dois_flat  # # Enregistrer

    return out  # # Retour

# ============================================================  # # 
# F) Fonction principale (1 HTML bundle + 1 JSON)  # # 
# ============================================================  # # 

def scrape_arxiv_cs(  # # Fonction principale
    query: str,  # # Requete utilisateur
    max_results: int = 20,  # # Nombre d’articles
    sort: str = "relevance",  # # relevance | submitted_date
    polite_min_s: float = 1.5,  # # Politesse min
    polite_max_s: float = 2.0,  # # Politesse max
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # Dossier de sortie
) -> Dict[str, Any]:  # # Retour JSON (dict)

    max_results = int(max_results)  # # Normaliser type
    if max_results < 1:  # # Si < 1
        max_results = 1  # # Forcer 1
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # Limite
        max_results = MAX_RESULTS_HARD_LIMIT  # # Forcer max

    ts = now_iso_for_filename()  # # Timestamp
    ensure_dir(data_lake_raw_dir)  # # Dossier raw
    session = requests.Session()  # # Session HTTP
    bundle_parts: List[str] = []  # # HTML bundle (debug)

    collected: List[Dict[str, Any]] = []  # # Items
    start = 0  # # Offset pagination

    # =====================  # # 
    # 1) Pagination search  # # 
    while len(collected) < max_results:  # # Tant qu’on n’a pas assez
        search_url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort)  # # URL search
        search_html, code = http_get_text(session=session, url=search_url)  # # GET search
        bundle_parts.append(f"<!-- ===== SEARCH URL: {search_url} | HTTP {code} ===== -->\n")  # # Debug
        bundle_parts.append(search_html)  # # HTML
        bundle_parts.append("\n<!-- ===== END SEARCH ===== -->\n")  # # Debug
        if code != 200:  # # Search KO
            break  # # Stop
        page_items = parse_search_page(search_html)  # # Parse search
        if not page_items:  # # Plus de resultats
            break  # # Stop
        collected.extend(page_items)  # # Ajouter page
        start += PAGE_SIZE  # # Page suivante
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Pause

    collected = collected[:max_results]  # # Couper au bon nombre

    # =====================  # # 
    # 2) Enrichissement /abs + /html  # # 
    for item in collected:  # # Pour chaque article
        arxiv_id = item.get("arxiv_id", "")  # # ID
        item["doi"] = ""  # # Init
        item["versions"] = []  # # Init
        item["last_updated_raw"] = ""  # # Init
        item["html_url"] = ""  # # Init
        item["published_date"] = ""  # # Init
        item["license"] = ""  # # Init
        item["sections"] = []  # # Init
        item["content_text"] = ""  # # Init
        item["references"] = []  # # Init
        item["references_dois"] = []  # # Init
        item["fallback_urls"] = []  # # Init
        item["errors"] = []  # # Init

        if arxiv_id:  # # Si ID
            item["abs_url"] = item.get("abs_url") or abs_url(arxiv_id)  # # Garantir abs
            item["pdf_url"] = item.get("pdf_url") or pdf_url(arxiv_id)  # # Garantir pdf

        # ----------  # # 
        # /abs  # # 
        if item.get("abs_url"):  # # Si URL /abs dispo
            abs_html, abs_code = http_get_text(session=session, url=item["abs_url"])  # # GET /abs
            bundle_parts.append(f"<!-- ===== ABS URL: {item['abs_url']} | HTTP {abs_code} ===== -->\n")  # # Debug
            bundle_parts.append(abs_html)  # # HTML
            bundle_parts.append("\n<!-- ===== END ABS ===== -->\n")  # # Debug
            if abs_code == 200:  # # OK
                abs_data = parse_abs_page(abs_html)  # # Parse /abs
                item["doi"] = abs_data.get("doi", "")  # # DOI
                item["versions"] = abs_data.get("versions", [])  # # Versions
                item["last_updated_raw"] = abs_data.get("last_updated_raw", "")  # # Last update
                item["html_url"] = abs_data.get("html_experimental_url", "")  # # HTML experimental
                if is_empty(item.get("abstract")) and not is_empty(abs_data.get("abstract")):  # # Fallback abstract
                    item["abstract"] = abs_data.get("abstract", "")  # # Abstract
            else:  # # KO
                item["errors"].append(f"abs_http_{abs_code}")  # # Log
                item["fallback_urls"].append(item["abs_url"])  # # Hint
        else:  # # Pas d’abs_url
            item["errors"].append("missing_abs_url")  # # Log

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Pause

        # ----------  # # 
        # /html  # # 
        if is_empty(item.get("html_url")) and arxiv_id:  # # Si /abs n’a pas donne html_url
            item["html_url"] = html_url(arxiv_id)  # # Construire /html/<id>
        if item.get("html_url"):  # # Si URL /html dispo
            h_html, h_code = http_get_text(session=session, url=item["html_url"])  # # GET /html
            bundle_parts.append(f"<!-- ===== HTML URL: {item['html_url']} | HTTP {h_code} ===== -->\n")  # # Debug
            bundle_parts.append(h_html)  # # HTML
            bundle_parts.append("\n<!-- ===== END HTML ===== -->\n")  # # Debug
            if h_code == 200:  # # OK
                html_data = parse_html_page(h_html)  # # Parse /html
                item["published_date"] = html_data.get("published_date", "")  # # Date
                item["license"] = html_data.get("license", "")  # # Licence
                item["sections"] = html_data.get("sections", [])  # # Sections
                item["content_text"] = html_data.get("content_text", "")  # # Texte
                item["references"] = html_data.get("references", [])  # # References
                item["references_dois"] = html_data.get("references_dois", [])  # # DOI
                if is_empty(item.get("doi")) and html_data.get("references_dois"):  # # DOI fallback depuis refs
                    first_doi_link = html_data["references_dois"][0]  # # Premier DOI
                    item["doi"] = first_doi_link  # # Enregistrer
            else:  # # KO
                item["errors"].append(f"html_http_{h_code}")  # # Log
                item["fallback_urls"].append(item["html_url"])  # # Hint
        else:  # # Pas d’html_url
            item["errors"].append("missing_html_url")  # # Log

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # Pause

        # ----------  # # 
        # Missing fields + hints  # # 
        item["missing_fields"] = compute_missing_fields(item)  # # Calcul
        if item["missing_fields"]:  # # Si manquants
            item["url_hint_if_missing"] = (  # # Construire message
                f"Champs manquants: {', '.join(item['missing_fields'])}. "
                f"Tu peux verifier ici: abs={item.get('abs_url','')} | html={item.get('html_url','')} | pdf={item.get('pdf_url','')}"
            )  # # Fin message
        else:  # # Rien
            item["url_hint_if_missing"] = ""  # # Vide

    # =====================  # # 
    # 3) Sauvegarde bundle + JSON  # # 
    bundle_html = "\n".join(bundle_parts)  # # Concat bundle
    bundle_name = f"scrappingresults_arxiv_bundle_{ts}.html"  # # Nom bundle
    bundle_path = save_text_file(data_lake_raw_dir, bundle_name, bundle_html)  # # Save bundle

    result: Dict[str, Any] = {  # # JSON final
        "ok": True,  # # OK
        "query": query,  # # Requete
        "sort": sort,  # # Tri
        "count": len(collected),  # # Nombre
        "max_results": max_results,  # # Max
        "hit_limit_100": (max_results == MAX_RESULTS_HARD_LIMIT),  # # Limite
        "message_if_limit": "Limite 100 atteinte (max_results)." if (max_results == MAX_RESULTS_HARD_LIMIT) else "",  # # Message
        "items": collected,  # # Items
        "bundle_html_file": bundle_path,  # # Fichier bundle
        "supported_fields": SUPPORTED_FIELDS,  # # Champs
    }  # # Fin JSON

    json_name = f"scrappingresults_arxiv_raw_{ts}.json"  # # Nom JSON
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # Chemin JSON
    with open(json_path, "w", encoding="utf-8") as f:  # # Ouvrir
        json.dump(result, f, ensure_ascii=False, indent=2)  # # Ecrire JSON

    result["saved_to"] = json_path  # # Ajouter chemin
    return result  # # Retour

# ============================================================  # # 
# TEST LOCAL (1 ligne ON/OFF)  # # 
# ============================================================  # # 

RUN_LOCAL_TEST = False  # # True = test ON | False = test OFF

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # Execution directe
    print("Lancement du scraping arXiv (test local)...")  # # Log
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=3, sort="relevance")  # # Run
    print(f"OK: {results.get('count')} articles recuperes")  # # Log
    print(f"JSON sauvegarde: {results.get('saved_to')}")  # # Log
    print(f"HTML bundle sauvegarde: {results.get('bundle_html_file')}")  # # Log
    if results.get("items"):  # # Si items
        print("Apercu item 1 (cles principales):")  # # Log
        first = results["items"][0]  # # Premier
        print(json.dumps({k: first.get(k) for k in ["arxiv_id","title","published_date","license"]}, ensure_ascii=False, indent=2))  # # Affichage
