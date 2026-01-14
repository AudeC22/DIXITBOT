# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (CS search -> /abs -> /html) -> 1 HTML bundle + 1 JSON  # # 🎯 Objectif
# ✅ Extraction: search results + /abs (doi, versions, html link) + /html (date, licence, sections, refs)  # # ✅
# ✅ Sortie: JSON (items enrichis) + 1 fichier HTML "bundle" (debug) dans data_lake/raw  # # ✅
# ============================================================  # # 📌 Séparateur visuel

# ===============================  # # 🧩 Importations
import os  # # 📁 Gestion des chemins/dossiers
import re  # # 🔎 Regex (ID, dates, versions)
import json  # # 🧾 Export JSON
import time  # # ⏱️ Politesse (sleep)
import random  # # 🎲 Jitter pour éviter un rythme trop "robot"
import datetime  # # 🕒 Timestamp fichiers
from typing import Dict, Any, List, Tuple, Optional  # # 🧩 Typage pour clarté

import requests  # # 🌐 HTTP GET (télécharger pages)
from bs4 import BeautifulSoup, Tag  # # 🍲 Parser HTML + manipuler balises

# ===============================  # # 🌍 Constantes arXiv
ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = f"{ARXIV_BASE}/search/cs"  # # 🔎 Endpoint recherche Computer Science
DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Stockage raw (bundle + json)
MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Limite globale demandée
PAGE_SIZE = 50  # # 📄 Taille page arXiv (pagination)

# ===============================  # # ✅ Champs supportés (ce qu’on renvoie dans JSON)
SUPPORTED_FIELDS = [  # # ✅ Liste de champs (pour missing_fields)
    "arxiv_id",  # # 🆔 Identifiant (ex: 2601.07830v1)
    "title",  # # 🏷️ Titre
    "authors",  # # 👥 Auteurs
    "abstract",  # # 🧾 Abstract (depuis search et/ou /abs)
    "submitted_date",  # # 🗓️ "Submitted ..." (depuis search)
    "abs_url",  # # 🔗 URL /abs
    "pdf_url",  # # 📄 URL /pdf (arXiv)
    "doi",  # # 🔗 DOI (souvent sur /abs, parfois dans references)
    "versions",  # # 🔁 Liste versions (v1, v2...) depuis /abs
    "last_updated_raw",  # # 🗓️ Dernière version raw (depuis /abs)
    "html_url",  # # 🌐 URL HTML experimental (depuis /abs OU construit)
    "published_date",  # # 🗓️ Date watermark sur /html (ex: 28 Nov 2025)
    "license",  # # 🪪 Licence affichée sur /html (ex: arXiv.org perpetual non-exclusive license)
    "sections",  # # 🧱 Titres + contenus (comme ton Excel)
    "content_text",  # # 🧾 Texte global concaténé (fallback)
    "references",  # # 📚 Références (raw + liens)
    "references_dois",  # # 🔗 Liste DOI trouvés dans les références
]

# ============================================================  # # 📌 Séparateur
# ✅ A) Helpers (dossiers, timestamps, “vide”, politesse, GET)
# ============================================================  # # 📌 Séparateur

def ensure_dir(path: str) -> None:  # # 📁 Créer dossier si besoin
    os.makedirs(path, exist_ok=True)  # # ✅ Crée (sans erreur si existe)

def now_iso_for_filename() -> str:  # # 🕒 Timestamp pour noms de fichiers
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260114_101500

def is_empty(value: Any) -> bool:  # # 🧪 Définition du “vide” (selon tes règles)
    if value is None:  # # ✅ None
        return True  # # ✅
    if isinstance(value, str):  # # 🧾 Si string
        v = value.strip()  # # 🧹 Trim
        if v == "":  # # ✅ vide si ""
            return True  # # ✅
        if v.lower() in {"n/a", "null", "none"}:  # # ✅ vide si "N/A", "null", "None" (string)
            return True  # # ✅
    if isinstance(value, list):  # # 📦 Si liste
        return len(value) == 0  # # ✅ vide si liste vide
    return False  # # ❌ sinon non vide

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # ⏳ Attendre 1.5 à 2.0 secondes

def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # 🌐 GET HTML -> (texte, status)
    headers = {  # # 🪪 User-Agent (évite certains blocages)
        "User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/2.0",  # # 🪪 Identifiant simple
        "Accept-Language": "en-US,en;q=0.9",  # # 🌍 Langue (stabilité parsing)
    }  # # ✅ Fin headers
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    return resp.text, resp.status_code  # # 📄 Retourner HTML + code

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver texte dans un fichier
    ensure_dir(folder)  # # 📁 Assurer dossier
    path = os.path.join(folder, filename)  # # 🧩 Construire chemin
    with open(path, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir en écriture UTF-8
        f.write(content)  # # 🧾 Écrire contenu
    return path  # # 📌 Retourner chemin

def normalize_url(href: str) -> str:  # # 🔗 Normaliser un href relatif/absolu
    if not href:  # # 🚫 Si vide
        return ""  # # ✅
    h = href.strip()  # # 🧹 Nettoyage
    if h.startswith("//"):  # # 🌐 URL sans schéma
        return "https:" + h  # # ✅ Ajouter https:
    if h.startswith("/"):  # # ✅ URL relative
        return ARXIV_BASE + h  # # 🔗 Préfixer domaine
    return h  # # ✅ Déjà absolu

def abs_url(arxiv_id: str) -> str:  # # 🔗 Construire URL /abs
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # ✅

def pdf_url(arxiv_id: str) -> str:  # # 📄 Construire URL /pdf (arXiv)
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # ✅

def html_url(arxiv_id: str) -> str:  # # 🌐 Construire URL /html
    return f"{ARXIV_BASE}/html/{arxiv_id}"  # # ✅

def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # 🚩 Calculer champs vides
    missing: List[str] = []  # # 📦 Liste champs manquants
    for f in SUPPORTED_FIELDS:  # # 🔁 Pour chaque champ attendu
        if is_empty(item.get(f)):  # # 🧪 Si vide
            missing.append(f)  # # ➕ Ajouter
    return missing  # # 📤 Retourner liste

# ============================================================  # # 📌 Séparateur
# 🔎 B) URL builder (tri compatible arXiv)
# ============================================================  # # 📌 Séparateur

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # 🔗 Construire URL search/cs
    q = requests.utils.quote(query)  # # 🔎 Encoder requête (espaces etc.)
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # 🔗 Base URL
    s = (sort or "relevance").strip().lower()  # # 🧠 Normaliser sort
    if s in {"submitted_date", "submitted", "recent"}:  # # 🗓️ Tri = récents (soumission)
        return base + "&order=-announced_date_first"  # # ✅ Paramètre arXiv OK
    # ⚠️ "relevance" est le défaut du site : PAS besoin de &order=-relevance (400)  # # 🚫
    return base  # # ✅ Relevance default

# ============================================================  # # 📌 Séparateur
# 🧩 C) Parsing SEARCH page (liste résultats) — robuste
# ============================================================  # # 📌 Séparateur

def find_abs_and_pdf_hrefs(li: Tag) -> Tuple[str, str]:  # # 🔎 Trouver href /abs et /pdf dans un item search
    abs_href = ""  # # 🔗 Href /abs
    pdf_href = ""  # # 📄 Href /pdf

    for a in li.select("a[href]"):  # # 🔁 Parcourir tous les liens du bloc
        href = (a.get("href") or "").strip()  # # 🧾 Lire href
        if not href:  # # 🚫 Vide
            continue  # # ✅ Next
        if (not abs_href) and re.search(r"/abs/[^?#/]+", href):  # # 🔗 Lien abstract
            abs_href = href  # # ✅
        if (not pdf_href) and re.search(r"/pdf/[^?#/]+", href):  # # 📄 Lien pdf
            pdf_href = href  # # ✅
        if abs_href and pdf_href:  # # ✅ Dès qu’on a les deux
            break  # # ✅ Stop

    return abs_href, pdf_href  # # 📤

def extract_arxiv_id_from_any(href: str) -> str:  # # 🆔 Extraire ID depuis /abs ou /pdf
    if not href:  # # 🚫
        return ""  # # ✅
    m = re.search(r"/abs/([^?#/]+)", href)  # # 🔎
    if m:  # # ✅
        return m.group(1).strip()  # # 🆔
    m2 = re.search(r"/pdf/([^?#/]+)", href)  # # 🔎
    if m2:  # # ✅
        return m2.group(1).strip()  # # 🆔
    return ""  # # ❌

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML search -> items (base)
    soup = BeautifulSoup(html, "lxml")  # # 🍲 Parser HTML (lxml)
    items: List[Dict[str, Any]] = []  # # 📦 Liste résultats

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Chaque résultat
        title_el = li.select_one("p.title")  # # 🏷️ Titre
        authors_el = li.select_one("p.authors")  # # 👥 Auteurs
        abstract_el = li.select_one("span.abstract-full")  # # 🧾 Abstract
        submitted_el = li.select_one("p.is-size-7")  # # 🗓️ Bloc date soumis (souvent)

        abs_href, pdf_href = find_abs_and_pdf_hrefs(li)  # # 🔎 Liens
        arxiv_id = extract_arxiv_id_from_any(abs_href or pdf_href)  # # 🆔 ID depuis lien

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️ Texte titre
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥 Texte auteurs brut
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 👥 Liste auteurs
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾 Texte abstract
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹 Nettoyage

        submitted_date = ""  # # 🗓️ Date "Submitted ..."
        if submitted_el:  # # ✅ Si présent
            txt = submitted_el.get_text(" ", strip=True)  # # 🧾 Texte
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # 🔎 "Submitted X"
            if m3:  # # ✅
                submitted_date = m3.group(1).strip()  # # 🗓️

        abs_full = normalize_url(abs_href)  # # 🔗 URL abs complète (si trouvée)
        pdf_full = normalize_url(pdf_href)  # # 📄 URL pdf complète (si trouvée)

        if arxiv_id and is_empty(abs_full):  # # ✅ Garantir abs_url si on a l'ID
            abs_full = abs_url(arxiv_id)  # # 🔗
        if arxiv_id and is_empty(pdf_full):  # # ✅ Garantir pdf_url si on a l'ID
            pdf_full = pdf_url(arxiv_id)  # # 📄

        items.append({  # # 📦 Ajouter item
            "arxiv_id": arxiv_id,  # # 🆔
            "title": title,  # # 🏷️
            "authors": authors,  # # 👥
            "abstract": abstract,  # # 🧾
            "submitted_date": submitted_date,  # # 🗓️
            "abs_url": abs_full,  # # 🔗
            "pdf_url": pdf_full,  # # 📄
        })  # # ✅ Fin item

    return items  # # 📤 Retour

# ============================================================  # # 📌 Séparateur
# 📌 D) Parsing /abs (versions + doi + lien HTML experimental + abstract fallback)
# ============================================================  # # 📌 Séparateur

def parse_abs_page(abs_html: str) -> Dict[str, Any]:  # # 🧩 /abs -> dict enrichissement
    soup = BeautifulSoup(abs_html, "lxml")  # # 🍲 Parser HTML
    out: Dict[str, Any] = {  # # 📦 Structure sortie
        "doi": "",  # # 🔗 DOI
        "versions": [],  # # 🔁 Versions
        "last_updated_raw": "",  # # 🗓️ Dernière version raw
        "html_experimental_url": "",  # # 🌐 Lien /html
        "abstract": "",  # # 🧾 Abstract (fallback depuis /abs si besoin)
    }  # # ✅

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # 🔎 DOI table
    if doi_a:  # # ✅
        out["doi"] = doi_a.get_text(" ", strip=True)  # # 🧾 Texte DOI

    html_a = soup.select_one('div.full-text a[href*="/html/"]')  # # 🔎 HTML experimental
    if html_a:  # # ✅
        out["html_experimental_url"] = normalize_url(html_a.get("href") or "")  # # 🌐 URL normalisée

    abs_el = soup.select_one("blockquote.abstract")  # # 🔎 Abstract sur /abs
    if abs_el:  # # ✅
        txt = abs_el.get_text(" ", strip=True)  # # 🧾 Texte brut
        txt = re.sub(r"^\s*Abstract:\s*", "", txt, flags=re.IGNORECASE).strip()  # # 🧹 Enlever "Abstract:"
        out["abstract"] = txt  # # 🧾

    versions: List[Dict[str, str]] = []  # # 📦 Liste versions
    for li in soup.select("div.submission-history li"):  # # 🔁 Parcourir historique
        txt = li.get_text(" ", strip=True)  # # 🧾 Texte
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # 🔎 [v1] ...
        if m:  # # ✅
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # 📦
    out["versions"] = versions  # # 🔁
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # 🗓️

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🌐 E) Parsing /html (date watermark + licence + sections + références)
# ============================================================  # # 📌 Séparateur

def clean_text(s: str) -> str:  # # 🧼 Nettoyage texte simple
    if not s:  # # 🚫
        return ""  # # ✅
    s = re.sub(r"\s+", " ", s)  # # 🧹 Espaces multiples -> 1
    return s.strip()  # # ✅

def is_heading(el: Tag) -> bool:  # # 🏷️ Détecter un titre de section
    if not isinstance(el, Tag):  # # 🛡️
        return False  # # ✅
    if el.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:  # # ✅ Titres HTML
        return True  # # ✅
    role = (el.get("role") or "").strip().lower()  # # ✅ ARIA
    if role == "heading":  # # ✅
        return True  # # ✅
    classes = " ".join(el.get("class", [])).lower()  # # ✅ Classes
    if any(k in classes for k in ["ltx_title", "title", "heading", "section-title"]):  # # ✅ Heuristique LaTeXML
        return bool(clean_text(el.get_text(" ", strip=True)))  # # ✅ Texte non vide
    return False  # # ✅

def collect_section_content(heading_el: Tag, max_chars: int = 8000) -> str:  # # 📦 Contenu après un titre
    contents: List[str] = []  # # 📦 Blocs texte
    total = 0  # # 🔢 Compteur
    for sib in heading_el.next_siblings:  # # 🔁 Parcourir frères suivants
        if isinstance(sib, Tag):  # # ✅ Balise
            if is_heading(sib):  # # 🛑 Stop au prochain titre
                break  # # ✅
            if sib.name in {"p", "div", "ul", "ol", "table", "figure", "section"}:  # # ✅ Blocs pertinents
                txt = clean_text(sib.get_text(" ", strip=True))  # # 🧾 Texte bloc
                if txt:  # # ✅ Non vide
                    contents.append(txt)  # # ➕ Ajouter
                    total += len(txt)  # # 🔢 Compter
        if total >= max_chars:  # # 🛑 Limite taille
            break  # # ✅
    return clean_text(" ".join(contents))  # # 🧾 Retour texte section

def extract_sections_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:  # # 🧱 Extraire sections titre+contenu
    # ✅ On cible l'article LaTeXML si possible (plus propre)  # # 🎯
    root = soup.select_one("article.ltx_document") or soup.select_one("main") or soup.body or soup  # # 🎯 Root
    headings: List[Tag] = []  # # 📦 Liste titres
    for el in root.find_all(True):  # # 🔁 Parcourir toutes balises
        if is_heading(el):  # # ✅ Filtre titres
            title_text = clean_text(el.get_text(" ", strip=True))  # # 🧾
            if title_text:  # # ✅
                headings.append(el)  # # ➕
    sections: List[Dict[str, Any]] = []  # # 📦 Résultat
    for i, h in enumerate(headings, start=1):  # # 🔁 Titres numérotés
        title_text = clean_text(h.get_text(" ", strip=True))  # # 🏷️ Titre
        level = h.name if h.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else "custom"  # # 🧭 Niveau
        section_text = collect_section_content(h)  # # 📦 Contenu associé
        if section_text:  # # ✅ Garder uniquement si contenu
            sections.append({  # # 📦 Ajouter section
                "section_index": i,  # # 🔢 Index
                "heading_level": level,  # # 🧭 Niveau
                "heading": title_text,  # # 🏷️
                "text": section_text,  # # 🧾
            })  # # ✅
    return sections  # # 📤

def extract_references_from_html(soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], List[str]]:  # # 📚 Références + DOI
    refs: List[Dict[str, Any]] = []  # # 📦 Références
    dois_flat: List[str] = []  # # 🔗 DOI uniques

    # ✅ Ton indication : class="ltx_biblist" id="bib.L1"  # # 🎯
    bib = soup.select_one(".ltx_biblist") or soup.select_one(".ltx_bibliography")  # # 🔎 Conteneur
    if not bib:  # # 🚫 Pas de bibliographie
        return refs, dois_flat  # # ✅

    for bi in bib.select(".ltx_bibitem, li, div"):  # # 🔁 Items bib
        txt = clean_text(bi.get_text(" ", strip=True))  # # 🧾 Texte ref
        if not txt:  # # 🚫
            continue  # # ✅
        links = [clean_text(a.get("href", "")) for a in bi.select("a[href]")]  # # 🔗 Tous les liens
        links = [l for l in links if l]  # # 🧹 Filtrer
        dois = [l for l in links if "doi.org/" in l]  # # 🔗 DOI links
        for d in dois:  # # 🔁
            if d not in dois_flat:  # # ✅ Uniques
                dois_flat.append(d)  # # ➕
        pdf_links = [l for l in links if ("/doi/pdf" in l) or l.lower().endswith(".pdf")]  # # 📄 PDFs
        refs.append({  # # 📦 Ajouter
            "raw_text": txt,  # # 🧾
            "urls": links,  # # 🔗
            "dois": dois,  # # 🔗
            "pdf_links": pdf_links,  # # 📄
        })  # # ✅

    return refs, dois_flat  # # 📤

def parse_html_page(html_text: str) -> Dict[str, Any]:  # # 🧩 /html -> dict
    soup = BeautifulSoup(html_text, "lxml")  # # 🍲 Parser
    out: Dict[str, Any] = {  # # 📦 Structure
        "published_date": "",  # # 🗓️
        "license": "",  # # 🪪
        "sections": [],  # # 🧱
        "content_text": "",  # # 🧾
        "references": [],  # # 📚
        "references_dois": [],  # # 🔗
    }  # # ✅

    wm = soup.select_one("#watermark-tr")  # # 🔎 Watermark (date publication)
    if wm:  # # ✅
        wm_text = clean_text(wm.get_text(" ", strip=True))  # # 🧾
        m = re.search(r"\]\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", wm_text)  # # 🔎 Après ] = date
        if m:  # # ✅
            out["published_date"] = m.group(1).strip()  # # 🗓️

    lic = soup.select_one("a#license-tr")  # # 🔎 Licence (ton exemple)
    if lic:  # # ✅
        lic_text = clean_text(lic.get_text(" ", strip=True))  # # 🧾
        lic_text = re.sub(r"^\s*License:\s*", "", lic_text, flags=re.IGNORECASE).strip()  # # 🧹 Enlever "License:"
        out["license"] = lic_text  # # 🪪

    sections = extract_sections_from_html(soup)  # # 🧱 Sections titre+contenu
    out["sections"] = sections  # # ✅

    # ✅ content_text = concat simple (utile si tu veux aussi un gros texte)  # # 🧾
    if sections:  # # ✅
        out["content_text"] = "\n\n".join([f"{s['heading']}\n{s['text']}" for s in sections])  # # 🧾
    else:  # # 🛟 Fallback texte global
        doc = soup.select_one("article.ltx_document") or soup.select_one("main") or soup.body  # # 🧾 Root
        out["content_text"] = doc.get_text("\n", strip=True) if doc else ""  # # 🧾

    refs, dois_flat = extract_references_from_html(soup)  # # 📚
    out["references"] = refs  # # 📚
    out["references_dois"] = dois_flat  # 🔗

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🚀 F) Fonction principale (1 HTML bundle + 1 JSON)
# ============================================================  # # 📌 Séparateur

def scrape_arxiv_cs(  # # 🚀 Fonction principale
    query: str,  # # 🔎 Requête utilisateur
    max_results: int = 20,  # # 🎯 Nombre d’articles
    sort: str = "relevance",  # # 🔃 relevance | submitted_date
    polite_min_s: float = 1.5,  # # 😇 Politesse min
    polite_max_s: float = 2.0,  # # 😇 Politesse max
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # 💾 Dossier de sortie
) -> Dict[str, Any]:  # # 🧾 Retour JSON (dict)

    max_results = int(max_results)  # # 🔢 Normaliser type
    if max_results < 1:  # # 🚫
        max_results = 1  # # ✅
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅

    ts = now_iso_for_filename()  # # 🕒 Timestamp
    ensure_dir(data_lake_raw_dir)  # # 📁 Dossier raw
    session = requests.Session()  # # 🔌 Session HTTP réutilisable
    bundle_parts: List[str] = []  # # 🧾 HTML bundle (debug)

    collected: List[Dict[str, Any]] = []  # # 📦 Items (multi-pages)
    start = 0  # # 📄 Offset pagination

    # =====================  # # 📄 1) Pagination search
    while len(collected) < max_results:  # # 🔁 Tant qu’on n’a pas assez
        search_url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort)  # # 🔗 URL search
        search_html, code = http_get_text(session=session, url=search_url)  # # 🌐 GET search
        bundle_parts.append(f"<!-- ===== SEARCH URL: {search_url} | HTTP {code} ===== -->\n")  # # 🧾
        bundle_parts.append(search_html)  # # 🧾
        bundle_parts.append("\n<!-- ===== END SEARCH ===== -->\n")  # # 🧾
        if code != 200:  # # ❌ Search KO
            break  # # 🛑
        page_items = parse_search_page(search_html)  # # 🔎 Parse search
        if not page_items:  # # 🛑 Plus de résultats
            break  # # ✅
        collected.extend(page_items)  # # ➕ Ajouter page
        start += PAGE_SIZE  # # ➡️ Page suivante
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇 Pause

    collected = collected[:max_results]  # # ✂️ Couper au bon nombre

    # =====================  # # 🧩 2) Enrichissement /abs + /html
    for item in collected:  # # 🔁 Pour chaque article
        arxiv_id = item.get("arxiv_id", "")  # # 🆔
        item["doi"] = ""  # # 🔗 Init
        item["versions"] = []  # # 🔁 Init
        item["last_updated_raw"] = ""  # # 🗓️ Init
        item["html_url"] = ""  # # 🌐 Init
        item["published_date"] = ""  # # 🗓️ Init
        item["license"] = ""  # # 🪪 Init
        item["sections"] = []  # # 🧱 Init
        item["content_text"] = ""  # # 🧾 Init
        item["references"] = []  # # 📚 Init
        item["references_dois"] = []  # # 🔗 Init
        item["fallback_urls"] = []  # # 🔗 Init
        item["errors"] = []  # # 🧾 Init

        # ✅ Garantir abs/pdf si on a l'ID  # # 🔗
        if arxiv_id:  # # ✅
            item["abs_url"] = item.get("abs_url") or abs_url(arxiv_id)  # # 🔗
            item["pdf_url"] = item.get("pdf_url") or pdf_url(arxiv_id)  # # 📄

        # ----------  # # 📌 /abs
        if item.get("abs_url"):  # # ✅ Si URL /abs dispo
            abs_html, abs_code = http_get_text(session=session, url=item["abs_url"])  # # 🌐 GET /abs
            bundle_parts.append(f"<!-- ===== ABS URL: {item['abs_url']} | HTTP {abs_code} ===== -->\n")  # # 🧾
            bundle_parts.append(abs_html)  # # 🧾
            bundle_parts.append("\n<!-- ===== END ABS ===== -->\n")  # # 🧾
            if abs_code == 200:  # # ✅ OK
                abs_data = parse_abs_page(abs_html)  # # 🔎 Parse /abs
                item["doi"] = abs_data.get("doi", "")  # # 🔗 DOI
                item["versions"] = abs_data.get("versions", [])  # # 🔁 Versions
                item["last_updated_raw"] = abs_data.get("last_updated_raw", "")  # # 🗓️ Last update
                item["html_url"] = abs_data.get("html_experimental_url", "")  # # 🌐 HTML experimental
                if is_empty(item.get("abstract")) and not is_empty(abs_data.get("abstract")):  # # ✅ Fallback abstract
                    item["abstract"] = abs_data.get("abstract", "")  # # 🧾
            else:  # # ❌ /abs KO
                item["errors"].append(f"abs_http_{abs_code}")  # # 🧾 Log
                item["fallback_urls"].append(item["abs_url"])  # # 🔗 Hint
        else:  # # ❌ Pas d’abs_url
            item["errors"].append("missing_abs_url")  # # 🧾

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇 Pause

        # ----------  # # 📌 /html
        if is_empty(item.get("html_url")) and arxiv_id:  # # ✅ Si /abs n’a pas donné html_url
            item["html_url"] = html_url(arxiv_id)  # # 🌐 Construire /html/<id>
        if item.get("html_url"):  # # ✅ Si URL /html dispo
            h_html, h_code = http_get_text(session=session, url=item["html_url"])  # # 🌐 GET /html
            bundle_parts.append(f"<!-- ===== HTML URL: {item['html_url']} | HTTP {h_code} ===== -->\n")  # # 🧾
            bundle_parts.append(h_html)  # # 🧾
            bundle_parts.append("\n<!-- ===== END HTML ===== -->\n")  # # 🧾
            if h_code == 200:  # # ✅ OK
                html_data = parse_html_page(h_html)  # # 🔎 Parse /html
                item["published_date"] = html_data.get("published_date", "")  # # 🗓️
                item["license"] = html_data.get("license", "")  # # 🪪
                item["sections"] = html_data.get("sections", [])  # # 🧱
                item["content_text"] = html_data.get("content_text", "")  # # 🧾
                item["references"] = html_data.get("references", [])  # # 📚
                item["references_dois"] = html_data.get("references_dois", [])  # # 🔗
                if is_empty(item.get("doi")) and html_data.get("references_dois"):  # # ✅ DOI fallback depuis refs
                    # ✅ On tente de prendre le 1er DOI trouvé (si le /abs n’en avait pas)  # # 🔗
                    first_doi_link = html_data["references_dois"][0]  # # 🔗
                    item["doi"] = first_doi_link  # # 🔗
            else:  # # ❌ /html KO
                item["errors"].append(f"html_http_{h_code}")  # # 🧾
                item["fallback_urls"].append(item["html_url"])  # # 🔗
        else:  # # ❌
            item["errors"].append("missing_html_url")  # # 🧾

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇 Pause

        # ----------  # # 🚩 Missing fields + hints
        item["missing_fields"] = compute_missing_fields(item)  # # 🚩
        if item["missing_fields"]:  # # ✅
            item["url_hint_if_missing"] = (  # # 🧾 Construire message
                f"Champs manquants: {', '.join(item['missing_fields'])}. "  # # 🧾
                f"Tu peux vérifier ici: abs={item.get('abs_url','')} | html={item.get('html_url','')} | pdf={item.get('pdf_url','')}"  # # 🧾
            )  # # ✅
        else:  # # ✅
            item["url_hint_if_missing"] = ""  # # ✅

    # =====================  # # 💾 3) Sauvegarde bundle + JSON
    bundle_html = "\n".join(bundle_parts)  # # 🧾 Concat bundle
    bundle_name = f"arxiv_bundle_{ts}.html"  # # 🧾 Nom bundle
    bundle_path = save_text_file(data_lake_raw_dir, bundle_name, bundle_html)  # # 💾 Save bundle

    result: Dict[str, Any] = {  # # 🧾 JSON final
        "ok": True,  # # ✅
        "query": query,  # # 🔎
        "sort": sort,  # # 🔃
        "count": len(collected),  # # 🔢
        "max_results": max_results,  # # 🎯
        "hit_limit_100": (max_results == MAX_RESULTS_HARD_LIMIT),  # # 🚧
        "message_if_limit": "Limite 100 atteinte (max_results)." if (max_results == MAX_RESULTS_HARD_LIMIT) else "",  # # 🧾
        "items": collected,  # # 📚
        "bundle_html_file": bundle_path,  # # 💾
        "supported_fields": SUPPORTED_FIELDS,  # # ✅
    }  # # ✅

    json_name = f"arxiv_raw_{ts}.json"  # # 🧾 Nom JSON
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # 📁 Chemin JSON
    with open(json_path, "w", encoding="utf-8") as f:  # # ✍️
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾 Écrire JSON

    result["saved_to"] = json_path  # # 📌 Ajouter chemin JSON
    return result  # # 📤 Retourner résultat

# ============================================================  # # 📌 Séparateur
# 🧪 TEST LOCAL (1 ligne ON/OFF)
# ============================================================  # # 📌 Séparateur

RUN_LOCAL_TEST = false  # # ✅ True = test ON | False = test OFF

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️ Exécution directe
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️ Log
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=3, sort="relevance")  # # 🕷️ Run
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 🖨️
    print(f"💾 HTML bundle sauvegardé: {results.get('bundle_html_file')}")  # # 🖨️
    if results.get("items"):  # # ✅
        print("🧾 Aperçu item 1 (clés principales):")  # # 🖨️
        first = results["items"][0]  # # 📦
        print(json.dumps({k: first.get(k) for k in ["arxiv_id","title","published_date","license"]}, ensure_ascii=False, indent=2))  # # 🧾
