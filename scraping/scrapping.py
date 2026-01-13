# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (search -> abs -> html -> pdf fallback) -> JSON + sauvegarde data_lake/raw  # # 🎯 Objectif
# ✅ But: récupérer "tous les champs" (même si certains restent vides => on trace l’erreur + URL possible)  # # 🧾 Règle
# ✅ Pipeline: SEARCH (liste) -> ABS (métadonnées fiables) -> HTML (si dispo) -> PDF (fallback)  # # 🧠 Logique
# ✅ Sortie: JSON + flag missing_fields[] + url_hint_if_missing  # # 🧾 Résultat
# ✅ Politesse: sleep 1.5–2.0s entre requêtes  # # 😇
# ✅ Limite: max_results <= 100 + message si atteint  # # 🚧
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gérer chemins et dossiers
import re  # # 🔎 Regex (ID, dates, repérage sections "References")
import json  # # 🧾 Export JSON
import time  # # ⏱️ Pause polie
import random  # # 🎲 Jitter anti-robot
import datetime  # # 🕒 Timestamp pour fichiers
from typing import Dict, Any, List, Optional, Tuple  # # 🧩 Typage
import requests  # # 🌐 HTTP GET
from bs4 import BeautifulSoup  # # 🍲 Parsing HTML + select

# 🧠 PDF parsing (fallback)  # # 📄
# - pypdf = simple et rapide  # # ✅
# - pdfminer.six = plus robuste quand pypdf échoue  # # 🧰
from pypdf import PdfReader  # # 📄 Extraction texte PDF (rapide)
from pdfminer.high_level import extract_text as pdfminer_extract_text  # # 📄 Extraction texte PDF (robuste)
from io import BytesIO  # # 🧪 PDF en mémoire (pas de stockage sur disque)

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine
ARXIV_SEARCH_ALL = "https://arxiv.org/search"  # # 🔎 Search tous domaines
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Search Computer Science

DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Stockage JSON (et HTML si activé)
MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Hard limit
PAGE_SIZE = 50  # # 📄 Pagination (50 est un bon compromis)

SAVE_RAW_HTML = True  # # 💾 Sauver HTML search + abs + html (debug/traçabilité) | False = pas de HTML
SAVE_ABS_PAGES = True  # # 💾 Sauver /abs (utile pour debug)
SAVE_HTML_PAGES = True  # # 💾 Sauver /html si dispo (utile pour debug)


# ============================================================
# ✅ 0) Définition du "vide" (règle utilisateur) + missing_fields
# ============================================================

def is_empty(value: Any) -> bool:  # # 🧪 Définir si une valeur est considérée "vide"
    if value is None:  # # ✅ None = vide
        return True  # # ✅
    if isinstance(value, str):  # # ✅ Si string
        v = value.strip()  # # 🧹 Nettoyage
        if v == "":  # # ✅ "" = vide
            return True  # # ✅
        if v.lower() in ("n/a", "null", "none"):  # # ✅ "N/A" / "null" / "None" (string) = vide
            return True  # # ✅
        return False  # # ✅ Non vide
    if isinstance(value, list):  # # ✅ Si liste
        if len(value) == 0:  # # ✅ Liste vide = vide
            return True  # # ✅
        return False  # # ✅ Non vide
    if isinstance(value, dict):  # # ✅ Si dict
        if len(value) == 0:  # # ✅ Dict vide = vide
            return True  # # ✅
        return False  # # ✅ Non vide
    return False  # # ✅ Par défaut, on considère non vide


def compute_missing_fields(item: Dict[str, Any], required_fields: List[str]) -> List[str]:  # # 🧾 Calculer la liste des champs manquants
    missing: List[str] = []  # # 📦 Liste manquants
    for f in required_fields:  # # 🔁 Pour chaque champ attendu
        if is_empty(item.get(f)):  # # ❌ Si vide selon la règle
            missing.append(f)  # # ➕ Ajouter
    return missing  # # 📤 Retour


# ============================================================
# 🌐 A) Utils — dossiers + politesse + timestamps
# ============================================================

def ensure_dir(path: str) -> None:  # # 📁 Assurer que le dossier existe
    os.makedirs(path, exist_ok=True)  # # ✅ Crée le dossier si absent

def now_iso_for_filename() -> str:  # # 🕒 Timestamp format fichier
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260113_113012

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # ⏳ Attente aléatoire

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver texte (HTML/JSON)
    ensure_dir(folder)  # # 📁 Dossier
    path = os.path.join(folder, filename)  # # 🧩 Chemin
    with open(path, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir
        f.write(content)  # # 🧾 Écrire
    return path  # # 📌 Retour


# ============================================================
# 🌐 B) GET — robuste (HTML + bytes) + erreurs tracées
# ============================================================

def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, str]:  # # 🌐 GET HTML
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DIXITBOT-arXivScraper/2.0)"}  # # 🪪 UA
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    resp.raise_for_status()  # # ❌ HTTP error
    return resp.text, resp.url  # # 📄 HTML + URL finale

def http_get_bytes(session: requests.Session, url: str, timeout_s: int = 60) -> Tuple[bytes, str, str]:  # # 🌐 GET bytes (PDF)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DIXITBOT-arXivScraper/2.0)"}  # # 🪪 UA
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    resp.raise_for_status()  # # ❌ HTTP error
    content_type = resp.headers.get("Content-Type", "")  # # 🧾 Content-Type
    return resp.content, resp.url, content_type  # # 📦 bytes + URL finale + type


# ============================================================
# 🔎 C) URL builder (search + sort)
# ============================================================

def normalize_sort_to_order(sort: str) -> str:  # # 🧭 Convertir sort -> param order arXiv
    sort = (sort or "").strip().lower()  # # 🧹 Normaliser
    if sort in ("relevance", "pertinence", ""):  # # ✅ "relevance" => order vide (sinon 400)
        return ""  # # ✅
    if sort in ("submitted_date", "submission_date", "recent", "recent_submitted"):  # # ✅
        return "-submitted_date"  # # ✅
    if sort in ("announced_date", "announcement_date", "announced", "recent_announced"):  # # ✅
        return "-announced_date_first"  # # ✅
    if sort in ("last_updated_date", "updated", "last_updated"):  # # ✅ tri local (après /abs)
        return ""  # # ✅
    return ""  # # ✅ default relevance

def build_search_url(query: str, start: int, size: int, sort: str, archive: str) -> str:  # # 🔗 Construire URL search
    q = requests.utils.quote(query)  # # 🔎 Encoder query
    base = ARXIV_SEARCH_CS if (archive or "").lower() == "cs" else ARXIV_SEARCH_ALL  # # 🧭 Endpoint
    order = normalize_sort_to_order(sort)  # # 🧭 order
    order_part = f"&order={requests.utils.quote(order)}" if order != "" else "&order="  # # ✅ order vide si relevance
    return f"{base}?query={q}&searchtype=all&abstracts=show{order_part}&size={size}&start={start}"  # # 🌐 URL

def build_abs_url(arxiv_id: str) -> str:  # # 🔗 URL /abs
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # ✅

def build_pdf_url(arxiv_id: str) -> str:  # # 📄 URL /pdf
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # ✅

def build_html_url(arxiv_id: str) -> str:  # # 🌐 URL /html (pas toujours dispo)
    return f"{ARXIV_BASE}/html/{arxiv_id}"  # # ✅


# ============================================================
# 🧩 D) Parsing SEARCH page (liste)
# ============================================================

def safe_text(el) -> str:  # # 🧼 Texte propre
    return el.get_text(" ", strip=True) if el else ""  # # ✅

def abs_id_from_abs_url(abs_url: str) -> str:  # # 🆔 Extraire ID depuis /abs/...
    m = re.search(r"/abs/([^?#/]+)", abs_url or "")  # # 🔎
    return m.group(1) if m else ""  # # ✅

def parse_submitted_line(text_line: str) -> Tuple[str, str]:  # # 🗓️ Extraire submitted_date / announced
    text_line = (text_line or "").strip()  # # 🧹
    submitted = ""  # # 🗓️
    announced = ""  # # 🗓️
    m1 = re.search(r"Submitted\s+(.+?);", text_line, flags=re.IGNORECASE)  # # 🔎
    if m1:  # # ✅
        submitted = m1.group(1).strip()  # # 🗓️
    m2 = re.search(r"originally announced\s+(.+?)\.", text_line, flags=re.IGNORECASE)  # # 🔎
    if m2:  # # ✅
        announced = m2.group(1).strip()  # # 🗓️
    return submitted, announced  # # 📤

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML -> items
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    items: List[Dict[str, Any]] = []  # # 📦

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Result
        title_el = li.select_one("p.title")  # # 🏷️
        authors_links = li.select("p.authors a")  # # 👥
        abstract_el = li.select_one("span.abstract-full")  # # 🧾
        abs_link_el = li.select_one('p.list-title a[href*="/abs/"]')  # # 🔗
        pdf_link_el = li.select_one('p.list-title a[href*="/pdf/"]')  # # 📄
        submitted_el = li.select_one("p.is-size-7")  # # 🗓️
        tag_els = li.select("div.tags span.tag")  # # 🏷️

        title = safe_text(title_el)  # # 🏷️

        authors: List[str] = []  # # 👥
        for a in authors_links:  # # 🔁
            t = safe_text(a)  # # 🧾
            if t:  # # ✅
                authors.append(t)  # # ➕

        abstract = safe_text(abstract_el).replace("△ Less", "").strip()  # # 🧾

        abs_url = abs_link_el.get("href", "").strip() if abs_link_el else ""  # # 🔗
        pdf_url = pdf_link_el.get("href", "").strip() if pdf_link_el else ""  # # 📄

        if abs_url and abs_url.startswith("/"):  # # ✅
            abs_url = ARXIV_BASE + abs_url  # # 🔗
        if pdf_url and pdf_url.startswith("/"):  # # ✅
            pdf_url = ARXIV_BASE + pdf_url  # # 🔗

        arxiv_id = abs_id_from_abs_url(abs_url)  # # 🆔

        submitted_line = safe_text(submitted_el)  # # 🗓️
        submitted_date, announced = parse_submitted_line(submitted_line)  # # 🗓️

        categories: List[str] = []  # # 🏷️
        for t in tag_els:  # # 🔁
            tag_txt = safe_text(t)  # # 🧾
            if tag_txt:  # # ✅
                categories.append(tag_txt)  # # ➕

        # ✅ Structure "tous champs" (même si vide)  # # 🧾
        items.append({  # # 📦
            "arxiv_id": arxiv_id or "N/A",  # # 🆔
            "title": title or "N/A",  # # 🏷️
            "authors": authors or [],  # # 👥
            "abstract": abstract or "N/A",  # # 🧾
            "categories": categories or [],  # # 🏷️
            "submitted_date": submitted_date or "N/A",  # # 🗓️
            "announced": announced or "N/A",  # # 🗓️
            "abs_url": abs_url or "N/A",  # # 🔗
            "pdf_url": pdf_url or "N/A",  # # 📄
            # --- Champs enrichis plus tard (on pré-crée pour "rien d'optionnel")  # # 🧾
            "doi": "N/A",  # # 🔗
            "license": "N/A",  # # ⚖️
            "journal_ref": "N/A",  # # 📚
            "comments": "N/A",  # # 💬
            "versions": [],  # # 🗓️
            "last_updated_raw": "N/A",  # # 🗓️
            "subjects_raw": "N/A",  # # 🏷️
            "html_url": "N/A",  # # 🌐
            "content_html": "N/A",  # # 🧾
            "references": [],  # # 📚
            "affiliations": [],  # # 🧾 (pas toujours dispo)
            "full_text": "N/A",  # # 🧾 (texte extrait)
            "source": "arxiv_search",  # # 🧾
            "errors": [],  # # 🧾
            "fill_sources": [],  # # 🧠 Liste des sources qui ont rempli des champs (abs/html/pdf/pypdf/pdfminer)
        })  # # ✅

    return items  # # 📤


# ============================================================
# 📄 E) Parse ABS page (détails fiables)
# ============================================================

def parse_abs_page(html: str) -> Dict[str, Any]:  # # 🧩 /abs -> dict
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    data: Dict[str, Any] = {}  # # 📦

    title_el = soup.select_one("h1.title")  # # 🏷️
    data["title_abs"] = safe_text(title_el).replace("Title:", "").strip() if title_el else "N/A"  # # 🏷️

    authors: List[str] = []  # # 👥
    for a in soup.select("div.authors a"):  # # 🔁
        t = safe_text(a)  # # 🧾
        if t:  # # ✅
            authors.append(t)  # # ➕
    data["authors_abs"] = authors  # # 👥

    abs_el = soup.select_one("blockquote.abstract")  # # 🧾
    data["abstract_abs"] = safe_text(abs_el).replace("Abstract:", "").strip() if abs_el else "N/A"  # # 🧾

    subj_el = soup.select_one("td.tablecell.subjects")  # # 🏷️
    data["subjects_raw"] = safe_text(subj_el) if subj_el else "N/A"  # # 🏷️

    def meta_text(selector: str) -> str:  # # 🧰 Lire texte d'un champ metadata
        el = soup.select_one(selector)  # # 🔎
        return safe_text(el) if el else "N/A"  # # ✅

    data["comments"] = meta_text("td.tablecell.comments")  # # 💬
    data["journal_ref"] = meta_text("td.tablecell.jref")  # # 📚
    data["doi"] = meta_text("td.tablecell.doi")  # # 🔗

    license_el = soup.select_one("td.tablecell.license a")  # # ⚖️
    data["license"] = license_el.get("href", "").strip() if license_el else meta_text("td.tablecell.license")  # # ⚖️

    history_el = soup.select_one("div.submission-history")  # # 🗓️
    versions: List[Dict[str, str]] = []  # # 🗓️
    if history_el:  # # ✅
        for li in history_el.select("li"):  # # 🔁
            line = safe_text(li)  # # 🧾
            m = re.search(r"\[(v\d+)\]\s*(.+)$", line)  # # 🔎
            if m:  # # ✅
                versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # ➕
            elif line:  # # ✅
                versions.append({"version": "", "raw": line})  # # ➕
    data["versions"] = versions  # # 🗓️
    data["last_updated_raw"] = versions[-1]["raw"] if versions else "N/A"  # # 🗓️

    return data  # # 📤


# ============================================================
# 🌐 F) Parse HTML arXiv /html (si dispo)
# ============================================================

def parse_html_page(html: str) -> Dict[str, Any]:  # # 🧩 /html -> content + refs best effort
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    data: Dict[str, Any] = {}  # # 📦

    # 🧾 Contenu texte (best effort)  # # 🧾
    main = soup.select_one("main") or soup.select_one("body")  # # 🧾
    text = safe_text(main) if main else ""  # # 🧾
    data["content_html"] = text if text else "N/A"  # # 🧾

    # 📚 Références (best effort)  # # 📚
    refs: List[str] = []  # # 📦
    # - certains /html ont un bloc References / Bibliography  # # 🧠
    for h in soup.select("h1, h2, h3"):  # # 🔁
        t = safe_text(h).lower()  # # 🧾
        if "reference" in t or "bibliograph" in t:  # # ✅
            # On prend le texte du parent proche comme approximation  # # 🧠
            parent = h.parent  # # 📌
            parent_text = safe_text(parent) if parent else ""  # # 🧾
            if parent_text:  # # ✅
                refs = extract_references_from_text(parent_text)  # # 📚
            break  # # ✅
    data["references_from_html"] = refs  # # 📚

    return data  # # 📤


# ============================================================
# 📄 G) PDF parsing en mémoire (pypdf puis pdfminer)
# ============================================================

def extract_references_from_text(text: str) -> List[str]:  # # 📚 Heuristique simple pour sortir une liste de références
    if not text:  # # 🚫
        return []  # # ✅
    # 🔎 On repère une section References/Bibliography  # # 🧠
    idx = -1  # # 📍
    m = re.search(r"\b(references|bibliography)\b", text, flags=re.IGNORECASE)  # # 🔎
    if m:  # # ✅
        idx = m.start()  # # 📍
    if idx == -1:  # # ❌
        return []  # # ✅

    tail = text[idx:]  # # 🧾 Texte à partir de "References"
    # ✂️ On coupe si on voit une section suivante très probable (Appendix/Acknowledgements)  # # 🧠
    cut = re.split(r"\b(appendix|acknowledg|supplementary)\b", tail, flags=re.IGNORECASE)  # # ✂️
    refs_block = cut[0] if cut else tail  # # 🧾

    # 🧹 Nettoyage et split en lignes  # # 🧼
    lines = [l.strip() for l in refs_block.splitlines() if l.strip()]  # # 🧾
    # 🧠 Filtre: on enlève le titre "References" lui-même  # # 🧹
    lines = [l for l in lines if l.lower() not in ("references", "bibliography")]  # # 🧹
    # ✅ Limite soft pour éviter JSON énorme  # # 🚧
    return lines[:200]  # # 📚


def parse_pdf_with_pypdf(pdf_bytes: bytes) -> str:  # # 📄 Extraire texte via pypdf (rapide)
    try:  # # 🧯
        reader = PdfReader(BytesIO(pdf_bytes))  # # 📄 Lire PDF en mémoire
        chunks: List[str] = []  # # 📦
        for page in reader.pages:  # # 🔁
            t = page.extract_text() or ""  # # 🧾
            if t.strip():  # # ✅
                chunks.append(t)  # # ➕
        return "\n".join(chunks).strip()  # # 📤 Texte
    except Exception:  # # ❌
        return ""  # # 🛟

def parse_pdf_with_pdfminer(pdf_bytes: bytes) -> str:  # # 📄 Extraire texte via pdfminer (robuste)
    try:  # # 🧯
        return (pdfminer_extract_text(BytesIO(pdf_bytes)) or "").strip()  # # 📤
    except Exception:  # # ❌
        return ""  # # 🛟


# ============================================================
# 🧠 H) Enrich item: ABS -> HTML -> PDF fallback pour champs manquants
# ============================================================

REQUIRED_FIELDS = [  # # ✅ Liste "tous les champs" que tu veux (aucun optionnel)
    "arxiv_id", "title", "authors", "abstract", "categories",
    "submitted_date", "abs_url", "pdf_url",
    "doi", "license", "journal_ref", "comments",
    "versions", "last_updated_raw", "subjects_raw",
    "html_url", "content_html",
    "references", "affiliations",
    "full_text",
]  # # ✅

def ensure_all_keys(item: Dict[str, Any]) -> None:  # # 🧾 Garantir que tous les champs existent (même vides)
    for k in REQUIRED_FIELDS:  # # 🔁
        if k not in item:  # # ✅
            # 🧠 Valeurs par défaut cohérentes selon type  # # 🧠
            if k in ("authors", "categories", "versions", "references", "affiliations"):  # # ✅ List
                item[k] = []  # # ✅
            else:  # # ✅ String
                item[k] = "N/A"  # # ✅

def add_url_hint_for_missing(item: Dict[str, Any], missing_fields: List[str]) -> None:  # # 🧭 Ajouter un message si champ manquant
    if not missing_fields:  # # ✅
        item["url_hint_if_missing"] = ""  # # ✅ Rien
        return  # # ✅
    # ✅ Règle: "si erreur, écrire que la réponse est peut-être dans cette page: URL"  # # 📌
    abs_url = item.get("abs_url", "N/A")  # # 🔗
    pdf_url = item.get("pdf_url", "N/A")  # # 📄
    html_url = item.get("html_url", "N/A")  # # 🌐
    item["url_hint_if_missing"] = f"Certains champs sont manquants ({', '.join(missing_fields)}). La réponse est peut-être dans: abs={abs_url} | html={html_url} | pdf={pdf_url}"  # # 🧾

def enrich_item(session: requests.Session, item: Dict[str, Any], polite_min_s: float, polite_max_s: float, raw_dir: str, ts: str, prefer_html_then_pdf: bool = True) -> Dict[str, Any]:  # # 🧠 Enrichir 1 item
    ensure_all_keys(item)  # # ✅ Tous champs présents

    arxiv_id = (item.get("arxiv_id") or "").strip()  # # 🆔
    if is_empty(arxiv_id):  # # ❌
        item["errors"].append("missing_arxiv_id")  # # 🧾
        item["missing_fields"] = compute_missing_fields(item, REQUIRED_FIELDS)  # # 🧾
        add_url_hint_for_missing(item, item["missing_fields"])  # # 🧭
        return item  # # 📤

    # 🔗 Fix URLs  # # 🔗
    item["abs_url"] = item.get("abs_url") if not is_empty(item.get("abs_url")) else build_abs_url(arxiv_id)  # # 🔗
    item["pdf_url"] = item.get("pdf_url") if not is_empty(item.get("pdf_url")) else build_pdf_url(arxiv_id)  # # 📄
    item["html_url"] = build_html_url(arxiv_id)  # # 🌐

    # =========================
    # 1) GET /abs + parse  # # 🧾
    # =========================
    try:  # # 🧯
        abs_html, final_abs = http_get_text(session=session, url=item["abs_url"])  # # 🌐 GET
        item["abs_url_final"] = final_abs  # # 🔁
        if SAVE_RAW_HTML and SAVE_ABS_PAGES:  # # 💾
            item["abs_page_saved"] = save_text_file(raw_dir, f"arxiv_abs_{ts}_{arxiv_id}.html", abs_html)  # # 💾
        abs_data = parse_abs_page(abs_html)  # # 🔎 SELECT
        # 🧠 Remplir champs (sans écraser si déjà rempli)  # # 🧠
        if is_empty(item.get("title")):  # # ✅
            item["title"] = abs_data.get("title_abs", "N/A")  # # 🏷️
        if is_empty(item.get("abstract")):  # # ✅
            item["abstract"] = abs_data.get("abstract_abs", "N/A")  # # 🧾
        if is_empty(item.get("authors")):  # # ✅
            item["authors"] = abs_data.get("authors_abs", [])  # # 👥

        # ✅ Champs méta  # # 🧾
        item["doi"] = abs_data.get("doi", item.get("doi", "N/A"))  # # 🔗
        item["license"] = abs_data.get("license", item.get("license", "N/A"))  # # ⚖️
        item["journal_ref"] = abs_data.get("journal_ref", item.get("journal_ref", "N/A"))  # # 📚
        item["comments"] = abs_data.get("comments", item.get("comments", "N/A"))  # # 💬
        item["versions"] = abs_data.get("versions", item.get("versions", []))  # # 🗓️
        item["last_updated_raw"] = abs_data.get("last_updated_raw", item.get("last_updated_raw", "N/A"))  # # 🗓️
        item["subjects_raw"] = abs_data.get("subjects_raw", item.get("subjects_raw", "N/A"))  # # 🏷️

        item["fill_sources"].append("abs")  # # 🧠
    except Exception as e:  # # ❌
        item["errors"].append(f"abs_fetch_failed: {type(e).__name__}")  # # 🧾

    sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    # =========================
    # 2) GET /html (B)  # # 🌐
    # =========================
    html_ok = False  # # 🧪
    if prefer_html_then_pdf:  # # ✅
        try:  # # 🧯
            html_page, final_html = http_get_text(session=session, url=item["html_url"])  # # 🌐 GET
            html_ok = True  # # ✅
            item["html_url_final"] = final_html  # # 🔁
            if SAVE_RAW_HTML and SAVE_HTML_PAGES:  # # 💾
                item["html_page_saved"] = save_text_file(raw_dir, f"arxiv_html_{ts}_{arxiv_id}.html", html_page)  # # 💾
            html_data = parse_html_page(html_page)  # # 🔎 SELECT
            if is_empty(item.get("content_html")):  # # ✅
                item["content_html"] = html_data.get("content_html", "N/A")  # # 🧾
            # 📚 Références depuis HTML  # # 📚
            refs_html = html_data.get("references_from_html", [])  # # 📚
            if is_empty(item.get("references")) and refs_html:  # # ✅
                item["references"] = refs_html  # # 📚
            item["fill_sources"].append("html")  # # 🧠
        except requests.exceptions.HTTPError as e:  # # ❌ (ex: 404)
            item["errors"].append(f"html_fetch_failed: HTTPError")  # # 🧾
            item["html_unavailable"] = True  # # ✅
        except Exception as e:  # # ❌
            item["errors"].append(f"html_fetch_failed: {type(e).__name__}")  # # 🧾
            item["html_unavailable"] = True  # # ✅

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    # =========================
    # 3) Fallback PDF (A) si champs manquants  # # 📄
    # =========================
    # ✅ On ne télécharge PAS le PDF sur disque : parsing en mémoire uniquement  # # ✅
    missing_before_pdf = compute_missing_fields(item, REQUIRED_FIELDS)  # # 🧾
    need_pdf = len(missing_before_pdf) > 0  # # ✅
    if need_pdf:  # # ✅
        try:  # # 🧯
            pdf_bytes, final_pdf, content_type = http_get_bytes(session=session, url=item["pdf_url"])  # # 📄 GET bytes
            item["pdf_url_final"] = final_pdf  # # 🔁
            item["pdf_content_type"] = content_type  # # 🧾
            # 3.1 pypdf  # # 📄
            text_pypdf = parse_pdf_with_pypdf(pdf_bytes)  # # 📄
            if text_pypdf:  # # ✅
                if is_empty(item.get("full_text")):  # # ✅
                    item["full_text"] = text_pypdf  # # 🧾
                if is_empty(item.get("references")):  # # ✅
                    refs = extract_references_from_text(text_pypdf)  # # 📚
                    if refs:  # # ✅
                        item["references"] = refs  # # 📚
                item["fill_sources"].append("pdf:pypdf")  # # 🧠

            # 3.2 pdfminer.six (uniquement si encore des champs manquants)  # # 🧰
            missing_after_pypdf = compute_missing_fields(item, REQUIRED_FIELDS)  # # 🧾
            if len(missing_after_pypdf) > 0:  # # ✅
                text_pdfminer = parse_pdf_with_pdfminer(pdf_bytes)  # # 📄
                if text_pdfminer:  # # ✅
                    # ✅ On comble uniquement ce qui manque  # # 🧠
                    if is_empty(item.get("full_text")):  # # ✅
                        item["full_text"] = text_pdfminer  # # 🧾
                    if is_empty(item.get("references")):  # # ✅
                        refs2 = extract_references_from_text(text_pdfminer)  # # 📚
                        if refs2:  # # ✅
                            item["references"] = refs2  # # 📚
                    item["fill_sources"].append("pdf:pdfminer")  # # 🧠
        except Exception as e:  # # ❌
            item["errors"].append(f"pdf_fetch_or_parse_failed: {type(e).__name__}")  # # 🧾

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    # ✅ Calcul final des champs manquants + hint URL  # # 🧾
    item["missing_fields"] = compute_missing_fields(item, REQUIRED_FIELDS)  # # 🧾
    add_url_hint_for_missing(item, item["missing_fields"])  # # 🧭

    return item  # # 📤


# ============================================================
# 🚀 I) Fonction principale scrape_arxiv (multi-pages + enrich)
# ============================================================

def scrape_arxiv(  # # 🚀 Fonction principale
    query: str,  # # 🔎 Requête utilisateur
    max_results: int = 20,  # # 🎯 Limite
    sort: str = "relevance",  # # 🧭 relevance | submitted_date | last_updated_date
    archive: str = "cs",  # # 🧭 cs | all
    polite_min_s: float = 1.5,  # # 😇
    polite_max_s: float = 2.0,  # # 😇
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # 💾 JSON output
) -> Dict[str, Any]:  # # 🧾 JSON

    max_results = int(max_results)  # # 🔢
    if max_results < 1:  # # 🚫
        max_results = 1  # # ✅
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅

    ensure_dir(data_lake_raw_dir)  # # 📁
    session = requests.Session()  # # 🔌
    ts = now_iso_for_filename()  # # 🕒

    collected: List[Dict[str, Any]] = []  # # 📦
    raw_search_pages: List[str] = []  # # 💾
    start = 0  # # 📄

    # 1) SEARCH pages  # # 🔎
    while len(collected) < max_results:  # # 🔁
        url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort, archive=archive)  # # 🔗
        html, final_url = http_get_text(session=session, url=url)  # # 🌐 GET
        if SAVE_RAW_HTML:  # # 💾
            p = save_text_file(data_lake_raw_dir, f"arxiv_search_{ts}_start_{start}.html", html)  # # 💾
            raw_search_pages.append(p)  # # 📌
        page_items = parse_search_page(html)  # # 🔎 SELECT
        if not page_items:  # # 🛑
            break  # # ✅
        collected.extend(page_items)  # # ➕
        start += PAGE_SIZE  # # ➡️
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇
        if start > 2000:  # # 🛡️
            break  # # ✅

    collected = collected[:max_results]  # # ✂️

    # 2) Enrich each item  # # 🧠
    enriched: List[Dict[str, Any]] = []  # # 📦
    for it in collected:  # # 🔁
        enriched.append(enrich_item(session=session, item=it, polite_min_s=polite_min_s, polite_max_s=polite_max_s, raw_dir=data_lake_raw_dir, ts=ts, prefer_html_then_pdf=True))  # # 🧠

    # 3) Tri local si last_updated_date  # # 🧭
    sort_norm = (sort or "").strip().lower()  # # 🧹
    if sort_norm in ("last_updated_date", "updated", "last_updated"):  # # ✅
        enriched.sort(key=lambda x: (x.get("last_updated_raw") or ""), reverse=True)  # # 🔁
    elif sort_norm in ("submitted_date", "submission_date", "recent", "recent_submitted"):  # # ✅
        enriched.sort(key=lambda x: (x.get("submitted_date") or ""), reverse=True)  # # 🔁

    hit_limit_100 = (max_results == MAX_RESULTS_HARD_LIMIT)  # # 🚧
    message_if_limit = "Limite 100 atteinte (max_results)." if hit_limit_100 else ""  # # 🧾

    result: Dict[str, Any] = {  # # 🧾
        "ok": True,  # # ✅
        "query": query,  # # 🔎
        "sort": sort,  # # 🧭
        "archive": archive,  # # 🧭
        "count": len(enriched),  # # 🔢
        "max_results": max_results,  # # 🎯
        "hit_limit_100": hit_limit_100,  # # 🚧
        "message_if_limit": message_if_limit,  # # 🧾
        "items": enriched,  # # 📚
        "raw_html_files": raw_search_pages,  # # 💾
        "why_html_files_exist": "On sauvegarde les HTML bruts pour debug/traçabilité. Mets SAVE_RAW_HTML=False si tu ne veux pas ces fichiers.",  # # 🧾
        "required_fields_definition": "Un champ est considéré vide si: None, '', 'N/A', 'null', 'None' (string). missing_fields[] liste ces champs.",  # # 🧾
    }  # # ✅

    out_json_path = os.path.join(data_lake_raw_dir, f"arxiv_raw_{ts}.json")  # # 📁
    with open(out_json_path, "w", encoding="utf-8") as f:  # # ✍️
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾

    result["saved_to"] = out_json_path  # # 📌
    return result  # # 📤


# ============================================================
# 🧪 J) Test local (1 variable)
# ============================================================

RUN_LOCAL_TEST = True  # # ✅ True = test ON | False = test OFF

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️
    results = scrape_arxiv(query="multimodal transformer", max_results=5, sort="relevance", archive="cs")  # # 🕷️
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 📌
    items = results.get("items", [])  # # 📦
    if items:  # # ✅
        print("🧾 Aperçu 1er article (missing_fields + hint):")  # # 🖨️
        print(json.dumps({  # # 🧾
            "arxiv_id": items[0].get("arxiv_id"),  # # 🆔
            "missing_fields": items[0].get("missing_fields"),  # # 🧾
            "url_hint_if_missing": items[0].get("url_hint_if_missing"),  # # 🧭
            "fill_sources": items[0].get("fill_sources"),  # # 🧠
        }, indent=2, ensure_ascii=False))  # # 🧾
