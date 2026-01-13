# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (search/cs) -> 1 HTML (bundle) + 1 JSON (raw)  # # 🎯 Objectif du script
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gestion des chemins/dossiers
import re  # # 🔎 Regex (id, versions, etc.)
import json  # # 🧾 Export JSON
import time  # # ⏱️ Politesse (sleep)
import random  # # 🎲 Jitter (éviter rythme robot)
import datetime  # # 🕒 Timestamp fichiers
from typing import Dict, Any, List, Optional, Tuple  # # 🧩 Typage pour clarté

import requests  # # 🌐 HTTP (GET)
from bs4 import BeautifulSoup  # # 🍲 Parsing HTML
from pypdf import PdfReader  # # 📄 Extraction PDF (1er essai)
from pdfminer.high_level import extract_text  # # 📄 Extraction PDF (fallback)
from io import BytesIO  # # 🧠 Parser PDF en mémoire (pas de fichier PDF)

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Recherche CS (HTML)
DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Stockage raw (HTML+JSON)
MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Max global demandé
PAGE_SIZE = 50  # # 📄 Pagination arXiv (50)

# ============================================================  # # 📌 Séparateur
# ✅ A) Helpers (dossiers, timestamps, “vide”, politesse, GET)
# ============================================================  # # 📌 Séparateur

def ensure_dir(path: str) -> None:  # # 📁 Créer dossier si besoin
    os.makedirs(path, exist_ok=True)  # # ✅

def now_iso_for_filename() -> str:  # # 🕒 Timestamp pour nom fichier
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260113_154500

def is_empty(value: Any) -> bool:  # # 🧪 Définition du “vide” demandée
    if value is None:  # # ✅ None
        return True  # # ✅ vide
    if isinstance(value, str):  # # 🧾 Si string
        v = value.strip()  # # 🧹 Nettoyage
        if v == "":  # # ✅ vide si ""
            return True  # # ✅
        if v.lower() in {"n/a", "null", "none"}:  # # ✅ vide si "N/A", "null", "None" (string)
            return True  # # ✅
    if isinstance(value, list):  # # 📦 Si liste
        return len(value) == 0  # # ✅ vide si liste vide
    return False  # # ❌ sinon non vide

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # ⏳

def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # 🌐 GET HTML (texte)
    headers = {"User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/1.0"}  # # 🪪 UA simple
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    return resp.text, resp.status_code  # # 📄 HTML + code HTTP

def http_get_bytes(session: requests.Session, url: str, timeout_s: int = 60) -> Tuple[bytes, int]:  # # 🌐 GET binaire (PDF)
    headers = {"User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/1.0"}  # # 🪪 UA simple
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    return resp.content, resp.status_code  # # 📦 bytes + code HTTP

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver un fichier texte (bundle HTML / JSON)
    ensure_dir(folder)  # # 📁
    path = os.path.join(folder, filename)  # # 🧩
    with open(path, "w", encoding="utf-8") as f:  # # ✍️
        f.write(content)  # # 🧾
    return path  # # 📌

# ============================================================  # # 📌 Séparateur
# 🔎 B) URL builder (tri compatible arXiv)
# ============================================================  # # 📌 Séparateur

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # 🔗 Construire URL search/cs
    q = requests.utils.quote(query)  # # 🔎 Encoder requête
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # 🔗 Base URL
    s = (sort or "relevance").strip().lower()  # # 🧠 Normaliser sort
    if s in {"submitted_date", "submitted", "recent"}:  # # 🗓️ “les plus récents”
        return base + "&order=-announced_date_first"  # # ✅ Valeur qui fonctionne (HTML search)
    if s in {"last_updated_date", "updated", "last_updated"}:  # # 🔁 “dernières mises à jour”
        return base + "&order=-last_updated_date"  # # ✅ Valeur utilisée par arXiv
    # ✅ Par défaut “relevance” => on NE met pas order (évite 400 sur -relevance)
    return base  # # ✅

# ============================================================  # # 📌 Séparateur
# 📄 C) Parsing page de recherche (on récupère déjà: titre, auteurs, abstract, pdf, abs, submitted)
# ============================================================  # # 📌 Séparateur

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML -> items
    soup = BeautifulSoup(html, "lxml")  # # 🍲 Parser HTML
    items: List[Dict[str, Any]] = []  # # 📦 Résultats

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Chaque résultat
        title_el = li.select_one("p.title")  # # 🏷️ Titre
        authors_el = li.select_one("p.authors")  # # 👥 Auteurs
        abstract_el = li.select_one("span.abstract-full")  # # 🧾 Abstract (full)
        abs_link_el = li.select_one('p.list-title a[href^="/abs/"]')  # # 🔗 /abs/
        pdf_link_el = li.select_one('p.list-title a[href^="/pdf/"]')  # # 📄 /pdf/
        submitted_el = li.select_one("p.is-size-7")  # # 🗓️ Bloc Submitted (search page)

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 👥
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹

        abs_url = (ARXIV_BASE + abs_link_el.get("href", "")) if abs_link_el else ""  # # 🔗
        pdf_url = (ARXIV_BASE + pdf_link_el.get("href", "")) if pdf_link_el else ""  # # 📄

        arxiv_id = ""  # # 🆔
        m = re.search(r"/abs/([^/]+)$", abs_url) if abs_url else None  # # 🔎
        if m:  # # ✅
            arxiv_id = m.group(1)  # # 🆔

        submitted_date = ""  # # 🗓️
        if submitted_el:  # # ✅
            txt = submitted_el.get_text(" ", strip=True)  # # 🧾
            m2 = re.search(r"Submitted\s+(\d+\s+\w+,\s+\d{4})", txt)  # # 🔎
            if m2:  # # ✅
                submitted_date = m2.group(1)  # # 🗓️

        items.append({  # # 📦 Item minimal
            "arxiv_id": arxiv_id,  # # 🆔
            "title": title,  # # 🏷️
            "authors": authors,  # # 👥
            "abstract": abstract,  # # 🧾
            "submitted_date": submitted_date,  # # 🗓️
            "abs_url": abs_url,  # # 🔗
            "pdf_url": pdf_url,  # # 📄
        })  # # ✅

    return items  # # 📤

# ============================================================  # # 📌 Séparateur
# 📌 D) Parsing page /abs (enrichissement “B”)
# ============================================================  # # 📌 Séparateur

def parse_abs_page(html: str, arxiv_id: str) -> Dict[str, Any]:  # # 🧩 /abs HTML -> dict
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    out: Dict[str, Any] = {}  # # 📦

    doi_el = soup.select_one('td.tablecell.arxivid a[href^="https://doi.org/"]')  # # 🔗 DOI (parfois)
    if doi_el:  # # ✅
        out["doi"] = doi_el.get_text(" ", strip=True)  # # 🧾

    license_el = soup.select_one('div.submission-history + div.metatable td.tablecell a[href*="license"]')  # # 📜 Licence (selon structure)
    if license_el:  # # ✅
        out["license"] = license_el.get_text(" ", strip=True)  # # 📜

    # 🏷️ Catégories / subjects
    subjects_el = soup.select_one("td.tablecell.subjects")  # # 🧠 Subjects
    if subjects_el:  # # ✅
        out["subjects"] = subjects_el.get_text(" ", strip=True)  # # 🧠

    # 💬 Comments / Journal ref
    comments_el = soup.select_one("td.tablecell.comments")  # # 💬
    if comments_el:  # # ✅
        out["comments"] = comments_el.get_text(" ", strip=True)  # # 💬
    jref_el = soup.select_one("td.tablecell.jref")  # # 📚
    if jref_el:  # # ✅
        out["journal_ref"] = jref_el.get_text(" ", strip=True)  # # 📚

    # 🔁 Submission history (versions + dates)
    versions: List[Dict[str, str]] = []  # # 📦
    for li in soup.select("div.submission-history li"):  # # 🔁 Chaque version
        txt = li.get_text(" ", strip=True)  # # 🧾
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # 🔎
        if m:  # # ✅
            versions.append({"version": m.group(1), "raw": m.group(2)})  # # 📦
    if versions:  # # ✅
        out["versions"] = versions  # # 🔁
        out["last_updated_date"] = versions[-1].get("raw", "")  # # 🗓️ Approx (texte brut)

    # 📄 PDF URL stable (au cas où search page l’a raté)
    out["pdf_url"] = f"{ARXIV_BASE}/pdf/{arxiv_id}" if arxiv_id else ""  # # 📄

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🧾 E) /html/<id> (tentative “C”) + extraction contenu
# ============================================================  # # 📌 Séparateur

def try_fetch_html_content(session: requests.Session, arxiv_id: str) -> Tuple[str, bool, str]:  # # 🌐 /html -> texte
    if not arxiv_id:  # # 🚫
        return "", True, ""  # # ✅ html_unavailable
    url = f"{ARXIV_BASE}/html/{arxiv_id}"  # # 🔗
    html, code = http_get_text(session=session, url=url)  # # 🌐 GET
    if code != 200:  # # ❌
        return "", True, url  # # ✅
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    main = soup.select_one("main")  # # 🎯 Contenu principal
    text = main.get_text("\n", strip=True) if main else soup.get_text("\n", strip=True)  # # 🧾
    return text, False, url  # # ✅

# ============================================================  # # 📌 Séparateur
# 📄 F) Fallback PDF (tentative “D”) — parsing en mémoire (pas de stockage)
# ============================================================  # # 📌 Séparateur

def extract_pdf_text_in_memory(session: requests.Session, pdf_url: str) -> Tuple[str, str]:  # # 📄 PDF -> texte
    if not pdf_url:  # # 🚫
        return "", ""  # # ✅
    pdf_bytes, code = http_get_bytes(session=session, url=pdf_url)  # # 🌐 GET PDF bytes
    if code != 200 or not pdf_bytes:  # # ❌
        return "", pdf_url  # # ✅
    text = ""  # # 🧾
    try:  # # 🧪 1) pypdf
        reader = PdfReader(BytesIO(pdf_bytes))  # # 📄 Ouvrir en mémoire
        pages_text: List[str] = []  # # 📦
        for p in reader.pages:  # # 🔁 Pages
            t = p.extract_text() or ""  # # 🧾
            if t.strip():  # # ✅
                pages_text.append(t)  # # ➕
        text = "\n".join(pages_text).strip()  # # 🧾
    except Exception:  # # ❌
        text = ""  # # 🧾

    if len(text) < 500:  # # 🛟 Si pypdf trop pauvre -> pdfminer.six
        try:  # # 🧪 2) pdfminer
            text = extract_text(BytesIO(pdf_bytes)).strip()  # # 🧾
        except Exception:  # # ❌
            text = text  # # 🧾 (on garde ce qu’on a)

    return text, pdf_url  # # 📤

# ============================================================  # # 📌 Séparateur
# 🚀 G) Fonction principale (1 HTML bundle + 1 JSON)
# ============================================================  # # 📌 Séparateur

def scrape_arxiv_cs(  # # 🚀 Fonction principale (appel backend / test local)
    query: str,  # # 🔎 Mots-clés
    max_results: int = 20,  # # 🎯 Nombre d’articles
    sort: str = "relevance",  # # 🔁 relevance / submitted_date / last_updated_date
    polite_min_s: float = 1.5,  # # 😇
    polite_max_s: float = 2.0,  # # 😇
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # 💾
) -> Dict[str, Any]:  # # 🧾 JSON retour

    # 🔢 A) normalisation max_results
    max_results = int(max_results)  # # 🔢
    if max_results < 1:  # # 🚫
        max_results = 1  # # ✅
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅

    ts = now_iso_for_filename()  # # 🕒
    ensure_dir(data_lake_raw_dir)  # # 📁

    bundle_parts: List[str] = []  # # 🧾 Un SEUL fichier HTML final (bundle)
    session = requests.Session()  # # 🔌 Session HTTP

    # 🌐 B) 1) GET pages search (jusqu’à max_results)
    collected: List[Dict[str, Any]] = []  # # 📦
    start = 0  # # 📄
    while len(collected) < max_results:  # # 🔁
        search_url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort)  # # 🔗
        search_html, code = http_get_text(session=session, url=search_url)  # # 🌐 GET
        bundle_parts.append(f"<!-- ===== SEARCH URL: {search_url} | HTTP {code} ===== -->\n")  # # 🧾
        bundle_parts.append(search_html)  # # 🧾 Ajouter HTML brut
        bundle_parts.append("\n<!-- ===== END SEARCH ===== -->\n")  # # 🧾

        if code != 200:  # # ❌
            break  # # 🛑

        page_items = parse_search_page(search_html)  # # 🔎 SELECT
        if not page_items:  # # 🛑
            break  # # ✅
        collected.extend(page_items)  # # ➕
        start += PAGE_SIZE  # # ➡️
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

        if start > 1000:  # # 🛡️
            break  # # ✅

    collected = collected[:max_results]  # # ✂️

    # 🌐 C) 2) Enrichissement /abs + /html + fallback PDF (sans sauvegarder PDF)
    required_fields = [  # # ✅ “rien d’optionnel” => on tracke tout
        "arxiv_id", "title", "authors", "abstract", "submitted_date", "abs_url", "pdf_url",
        "doi", "license", "subjects", "comments", "journal_ref", "versions", "last_updated_date",
        "content_text", "refs_text"
    ]  # # 📋

    for item in collected:  # # 🔁 Articles
        arxiv_id = item.get("arxiv_id", "")  # # 🆔
        abs_url = item.get("abs_url", "")  # # 🔗
        pdf_url = item.get("pdf_url", "")  # # 📄

        item["doi"] = ""  # # 🧾
        item["license"] = ""  # # 📜
        item["subjects"] = ""  # # 🧠
        item["comments"] = ""  # # 💬
        item["journal_ref"] = ""  # # 📚
        item["versions"] = []  # # 🔁
        item["last_updated_date"] = ""  # # 🗓️
        item["content_text"] = ""  # # 🧾
        item["refs_text"] = ""  # # 🔗 (souvent dur à extraire, mais champ présent)
        item["html_unavailable"] = False  # # 🚫
        item["fallback_urls"] = []  # # 🔗 Pages utiles si échec

        # ✅ B) /abs
        if abs_url:  # # ✅
            abs_html, abs_code = http_get_text(session=session, url=abs_url)  # # 🌐 GET
            bundle_parts.append(f"<!-- ===== ABS URL: {abs_url} | HTTP {abs_code} ===== -->\n")  # # 🧾
            bundle_parts.append(abs_html)  # # 🧾
            bundle_parts.append("\n<!-- ===== END ABS ===== -->\n")  # # 🧾
            if abs_code == 200:  # # ✅
                enriched = parse_abs_page(abs_html, arxiv_id)  # # 🧩
                for k, v in enriched.items():  # # 🔁
                    item[k] = v  # # ✅
            else:  # # ❌
                item["fallback_urls"].append(abs_url)  # # 🔗
        else:  # # ❌
            item["fallback_urls"].append(f"{ARXIV_BASE}/abs/{arxiv_id}")  # # 🔗

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

        # ✅ C) /html
        html_text, html_unavailable, html_url = try_fetch_html_content(session=session, arxiv_id=arxiv_id)  # # 🌐
        item["html_unavailable"] = html_unavailable  # # 🚫
        if not html_unavailable and html_text:  # # ✅
            item["content_text"] = html_text  # # 🧾
        if html_url:  # # ✅
            item["fallback_urls"].append(html_url)  # # 🔗

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

        # ✅ D) Missing fields + fallback PDF (uniquement pour compléter)
        missing_fields: List[str] = []  # # 📦
        for f in required_fields:  # # 🔁
            if is_empty(item.get(f)):  # # 🧪
                missing_fields.append(f)  # # ➕
        item["missing_fields"] = missing_fields  # # 🚩

        if missing_fields:  # # ✅
            pdf_text, pdf_used_url = extract_pdf_text_in_memory(session=session, pdf_url=pdf_url)  # # 📄
            if pdf_used_url:  # # ✅
                item["fallback_urls"].append(pdf_used_url)  # # 🔗
            # 🧾 On ne remplit que les champs vides
            if is_empty(item.get("content_text")) and pdf_text:  # # ✅
                item["content_text"] = pdf_text  # # 🧾
            # 🔁 Recalcul missing_fields après fallback
            missing2: List[str] = []  # # 📦
            for f in required_fields:  # # 🔁
                if is_empty(item.get(f)):  # # 🧪
                    missing2.append(f)  # # ➕
            item["missing_fields"] = missing2  # # 🚩

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    # 💾 H) Sauvegardes finales : 1 HTML bundle + 1 JSON
    bundle_html = "\n".join(bundle_parts)  # # 🧾 Concat
    html_name = f"arxiv_bundle_{ts}.html"  # # 🧾
    html_path = save_text_file(data_lake_raw_dir, html_name, bundle_html)  # # 💾

    hit_limit_100 = (max_results == MAX_RESULTS_HARD_LIMIT)  # # 🚧
    message_if_limit = "Limite 100 atteinte (max_results)." if hit_limit_100 else ""  # # 🧾

    result: Dict[str, Any] = {  # # 🧾 JSON final
        "ok": True,  # # ✅
        "query": query,  # # 🔎
        "sort": sort,  # # 🔁
        "count": len(collected),  # # 🔢
        "max_results": max_results,  # # 🎯
        "hit_limit_100": hit_limit_100,  # # 🚧
        "message_if_limit": message_if_limit,  # # 🧾
        "items": collected,  # # 📚
        "bundle_html_file": html_path,  # # 💾 1 seul HTML
    }  # # ✅

    json_name = f"arxiv_raw_{ts}.json"  # # 🧾
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # 📁
    with open(json_path, "w", encoding="utf-8") as f:  # # ✍️
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾

    result["saved_to"] = json_path  # # 📌
    return result  # # 📤

# ============================================================  # # 📌 Séparateur
# 🧪 TEST LOCAL (1 ligne ON/OFF)
# ============================================================  # # 📌 Séparateur

RUN_LOCAL_TEST = True  # # ✅ True = test ON | False = test OFF (ou mets # devant la ligne)

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️ Exécuter seulement en local
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=5, sort="submitted_date")  # # 🕷️
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 🖨️
    print(f"💾 HTML bundle sauvegardé: {results.get('bundle_html_file')}")  # # 🖨️
