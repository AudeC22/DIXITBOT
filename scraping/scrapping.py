# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (CS search -> /abs -> /html) -> 1 HTML bundle + 1 JSON  # # 🎯 Objectif
# ✅ FIX v2: extraction /abs et /pdf ULTRA-robuste (liens relatifs OU absolus, plusieurs layouts).  # # ✅
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gestion des chemins/dossiers
import re  # # 🔎 Regex (ID, versions, watermark)
import json  # # 🧾 Export JSON
import time  # # ⏱️ Politesse (sleep)
import random  # # 🎲 Jitter (éviter rythme robot)
import datetime  # # 🕒 Timestamp fichiers
from typing import Dict, Any, List, Tuple  # # 🧩 Typage

import requests  # # 🌐 HTTP (GET)
from bs4 import BeautifulSoup  # # 🍲 Parsing HTML (select)

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Recherche Computer Science
DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Stockage raw (HTML bundle + JSON)
MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Max global demandé
PAGE_SIZE = 50  # # 📄 Pagination arXiv (50)

# ============================================================  # # 📌 Séparateur
# ✅ A) Helpers (dossiers, timestamps, “vide”, politesse, GET)
# ============================================================  # # 📌 Séparateur

def ensure_dir(path: str) -> None:  # # 📁 Créer dossier si besoin
    os.makedirs(path, exist_ok=True)  # # ✅

def now_iso_for_filename() -> str:  # # 🕒 Timestamp pour nom fichier
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260113_154500

def is_empty(value: Any) -> bool:  # # 🧪 Définition du “vide”
    if value is None:  # # ✅ None
        return True  # # ✅
    if isinstance(value, str):  # # 🧾 Si string
        v = value.strip()  # # 🧹
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
    headers = {"User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/Final/1.2"}  # # 🪪 UA simple
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    return resp.text, resp.status_code  # # 📄 HTML + code HTTP

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver un fichier texte
    ensure_dir(folder)  # # 📁
    path = os.path.join(folder, filename)  # # 🧩
    with open(path, "w", encoding="utf-8") as f:  # # ✍️
        f.write(content)  # # 🧾
    return path  # # 📌

def normalize_to_abs_url(href: str) -> str:  # # 🔗 Normaliser href -> URL complète /abs
    if not href:  # # 🚫
        return ""  # # ✅
    h = href.strip()  # # 🧹
    if h.startswith("//"):  # # 🌐 URL sans schéma
        h = "https:" + h  # # ✅
    if h.startswith("/"):  # # ✅ relatif
        return ARXIV_BASE + h  # # 🔗
    return h  # # ✅ déjà absolu

def normalize_to_pdf_url(href: str) -> str:  # # 📄 Normaliser href -> URL complète /pdf
    return normalize_to_abs_url(href)  # # 📄 même logique

# ============================================================  # # 📌 Séparateur
# 🔎 B) URL builder (tri compatible arXiv)
# ============================================================  # # 📌 Séparateur

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # 🔗 Construire URL search/cs
    q = requests.utils.quote(query)  # # 🔎 Encoder requête
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # 🔗 Base
    s = (sort or "relevance").strip().lower()  # # 🧠
    if s in {"submitted_date", "submitted", "recent"}:  # # 🗓️
        return base + "&order=-announced_date_first"  # # ✅
    return base  # # ✅ relevance

def abs_url(arxiv_id: str) -> str:  # # 🔗 URL /abs
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # ✅

def pdf_url(arxiv_id: str) -> str:  # # 📄 URL /pdf
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # ✅

def html_url(arxiv_id: str, version: str = "") -> str:  # # 🌐 URL /html
    return f"{ARXIV_BASE}/html/{arxiv_id}{version}"  # # ✅

# ============================================================  # # 📌 Séparateur
# 🧩 C) Parsing SEARCH page (liste) — ✅ FIX v2 ULTRA robuste
# ============================================================  # # 📌 Séparateur

def find_abs_and_pdf_hrefs(li: BeautifulSoup) -> Tuple[str, str]:  # # 🔎 Trouver href /abs et /pdf (tous layouts)
    # ✅ 1) Essais rapides via sélecteurs connus
    candidates = []  # # 📦
    for sel in [  # # 🧠 Sélecteurs souvent utilisés
        'p.list-title a[href*="/abs/"]',  # # 🔎
        'p.list-title a[title*="Abstract"]',  # # 🔎
        'span.list-identifier a[href*="/abs/"]',  # # 🔎 ancien layout
        'a[href*="/abs/"]',  # # 🔎 fallback global
    ]:  # # ✅
        a = li.select_one(sel)  # # 🔎
        if a and (a.get("href") or "").strip():  # # ✅
            candidates.append((a.get("href") or "").strip())  # # ➕

    abs_href = ""  # # 🔗
    pdf_href = ""  # # 📄

    # ✅ 2) Si pas trouvé, on parcourt TOUS les <a href> et on match avec regex (absolu OU relatif)
    all_hrefs = [(a.get("href") or "").strip() for a in li.select("a[href]")]  # # 🔗
    all_hrefs = [h for h in all_hrefs if h]  # # 🧹
    all_hrefs = candidates + all_hrefs  # # ✅ on met les “bons” candidats en premier

    # ✅ Regex: accepte /abs/... OU https://arxiv.org/abs/... OU http(s)://.../abs/...
    for h in all_hrefs:  # # 🔁
        if not abs_href and re.search(r"/abs/[^?#/]+", h):  # # 🔗
            abs_href = h  # # ✅
        if not pdf_href and re.search(r"/pdf/[^?#/]+", h):  # # 📄
            pdf_href = h  # # ✅
        if abs_href and pdf_href:  # # ✅
            break  # # ✅

    return abs_href, pdf_href  # # 📤

def extract_arxiv_id_from_any(href: str) -> str:  # # 🆔 Extraire l’ID depuis un href /abs ou /pdf
    if not href:  # # 🚫
        return ""  # # ✅
    m = re.search(r"/abs/([^?#/]+)", href)  # # 🔎
    if m:  # # ✅
        return m.group(1).strip()  # # 🆔
    m2 = re.search(r"/pdf/([^?#/]+)", href)  # # 🔎
    if m2:  # # ✅
        return m2.group(1).strip()  # # 🆔
    return ""  # # ❌

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML -> items
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    items: List[Dict[str, Any]] = []  # # 📦

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚
        title_el = li.select_one("p.title")  # # 🏷️
        authors_el = li.select_one("p.authors")  # # 👥
        abstract_el = li.select_one("span.abstract-full")  # # 🧾
        submitted_el = li.select_one("p.is-size-7")  # # 🗓️

        abs_href, pdf_href = find_abs_and_pdf_hrefs(li)  # # ✅ FIX v2
        arxiv_id = extract_arxiv_id_from_any(abs_href or pdf_href)  # # 🆔

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 👥
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹

        submitted_date = ""  # # 🗓️
        if submitted_el:  # # ✅
            txt = submitted_el.get_text(" ", strip=True)  # # 🧾
            m3 = re.search(r"Submitted\s+(.+?)(?:;|$)", txt, flags=re.IGNORECASE)  # # 🔎
            if m3:  # # ✅
                submitted_date = m3.group(1).strip()  # # 🗓️

        abs_full = normalize_to_abs_url(abs_href)  # # 🔗
        pdf_full = normalize_to_pdf_url(pdf_href)  # # 📄

        # ✅ Si on a l’ID, on GARANTIT les URLs (même si arXiv n’a pas mis les liens)
        if arxiv_id and is_empty(abs_full):  # # ✅
            abs_full = abs_url(arxiv_id)  # # 🔗
        if arxiv_id and is_empty(pdf_full):  # # ✅
            pdf_full = pdf_url(arxiv_id)  # # 📄

        items.append({  # # 📦
            "arxiv_id": arxiv_id,  # # 🆔
            "title": title,  # # 🏷️
            "authors": authors,  # # 👥
            "abstract": abstract,  # # 🧾
            "submitted_date": submitted_date,  # # 🗓️
            "abs_url": abs_full,  # # 🔗
            "pdf_url": pdf_full,  # # 📄
        })  # # ✅

    return items  # # 📤

# ============================================================  # # 📌 Séparateur
# 📌 D) Parsing /abs (versions + doi + lien HTML experimental)
# ============================================================  # # 📌 Séparateur

def parse_abs_page(html: str) -> Dict[str, Any]:  # # 🧩 /abs -> dict
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    out: Dict[str, Any] = {"doi": "", "versions": [], "last_updated_raw": "", "html_experimental_url": ""}  # # 📦

    doi_a = soup.select_one('td.tablecell.doi a[href*="doi.org"]')  # # 🔎
    if doi_a:  # # ✅
        out["doi"] = doi_a.get_text(" ", strip=True)  # # 🧾

    html_a = soup.select_one('div.full-text a[href*="/html/"]')  # # 🔎
    if html_a:  # # ✅
        href = (html_a.get("href") or "").strip()  # # 🧾
        out["html_experimental_url"] = (ARXIV_BASE + href) if href.startswith("/") else href  # # ✅

    versions: List[Dict[str, str]] = []  # # 📦
    for li in soup.select("div.submission-history li"):  # # 🔁
        txt = li.get_text(" ", strip=True)  # # 🧾
        m = re.search(r"\[(v\d+)\]\s*(.*)$", txt)  # # 🔎
        if m:  # # ✅
            versions.append({"version": m.group(1), "raw": m.group(2).strip()})  # # 📦
    out["versions"] = versions  # # 🔁
    out["last_updated_raw"] = versions[-1]["raw"] if versions else ""  # # 🗓️

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🌐 E) Parsing /html (watermark date + contenu + références)
# ============================================================  # # 📌 Séparateur

def parse_html_page(html: str) -> Dict[str, Any]:  # # 🧩 /html -> dict
    soup = BeautifulSoup(html, "lxml")  # # 🍲
    out: Dict[str, Any] = {"published_date": "", "content_text": "", "references": [], "references_dois": []}  # # 📦

    wm = soup.select_one("#watermark-tr")  # # 🔎
    if wm:  # # ✅
        wm_text = wm.get_text(" ", strip=True)  # # 🧾
        m = re.search(r"\]\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", wm_text)  # # 🔎
        if m:  # # ✅
            out["published_date"] = m.group(1).strip()  # # 🗓️

    doc = soup.select_one("article.ltx_document")  # # 🔎
    if doc:  # # ✅
        out["content_text"] = doc.get_text("\n", strip=True)  # # 🧾
    else:  # # 🛟
        main = soup.select_one("main") or soup.select_one("body")  # # 🧾
        out["content_text"] = main.get_text("\n", strip=True) if main else ""  # # 🧾

    bib_container = soup.select_one(".ltx_bibliography")  # # 🔎
    if bib_container:  # # ✅
        references: List[Dict[str, Any]] = []  # # 📦
        doi_list: List[str] = []  # # 🔗
        for bi in bib_container.select(".ltx_bibitem, li, div"):  # # 🔁
            txt = bi.get_text(" ", strip=True)  # # 🧾
            if not txt:  # # 🚫
                continue  # # ✅
            links = [a.get("href", "").strip() for a in bi.select("a[href]")]  # # 🔗
            links = [l for l in links if l]  # # 🧹
            dois = [l for l in links if "doi.org/" in l]  # # 🔗
            for d in dois:  # # 🔁
                if d not in doi_list:  # # ✅
                    doi_list.append(d)  # # ➕
            pdf_links = [l for l in links if ("/doi/pdf" in l) or l.lower().endswith(".pdf")]  # # 📄
            references.append({"raw_text": txt, "urls": links, "dois": dois, "pdf_links": pdf_links})  # # 📦
        out["references"] = references  # # 📚
        out["references_dois"] = doi_list  # # 🔗

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🚀 F) Fonction principale (1 HTML bundle + 1 JSON)
# ============================================================  # # 📌 Séparateur

SUPPORTED_FIELDS = [  # # ✅ Champs supportés
    "arxiv_id", "title", "authors", "abstract", "submitted_date",
    "abs_url", "pdf_url",
    "doi", "versions", "last_updated_raw",
    "html_url", "published_date", "content_text",
    "references", "references_dois",
]  # # ✅

def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # 🚩 Champs vides
    missing: List[str] = []  # # 📦
    for f in SUPPORTED_FIELDS:  # # 🔁
        if is_empty(item.get(f)):  # # 🧪
            missing.append(f)  # # ➕
    return missing  # # 📤

def scrape_arxiv_cs(  # # 🚀
    query: str,
    max_results: int = 20,
    sort: str = "relevance",
    polite_min_s: float = 1.5,
    polite_max_s: float = 2.0,
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,
) -> Dict[str, Any]:

    max_results = int(max_results)  # # 🔢
    if max_results < 1:  # # 🚫
        max_results = 1  # # ✅
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅

    ts = now_iso_for_filename()  # # 🕒
    ensure_dir(data_lake_raw_dir)  # # 📁
    session = requests.Session()  # # 🔌
    bundle_parts: List[str] = []  # # 🧾 HTML bundle

    collected: List[Dict[str, Any]] = []  # # 📦
    start = 0  # # 📄

    while len(collected) < max_results:  # # 🔁
        search_url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort)  # # 🔗
        search_html, code = http_get_text(session=session, url=search_url)  # # 🌐
        bundle_parts.append(f"<!-- ===== SEARCH URL: {search_url} | HTTP {code} ===== -->\n")  # # 🧾
        bundle_parts.append(search_html)  # # 🧾
        bundle_parts.append("\n<!-- ===== END SEARCH ===== -->\n")  # # 🧾
        if code != 200:  # # ❌
            break  # # 🛑
        page_items = parse_search_page(search_html)  # # 🔎
        if not page_items:  # # 🛑
            break  # # ✅
        collected.extend(page_items)  # # ➕
        start += PAGE_SIZE  # # ➡️
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    collected = collected[:max_results]  # # ✂️

    for item in collected:  # # 🔁
        arxiv_id = item.get("arxiv_id", "")  # # 🆔
        item["doi"] = ""  # # 🔗
        item["versions"] = []  # # 🔁
        item["last_updated_raw"] = ""  # # 🗓️
        item["html_url"] = ""  # # 🌐
        item["published_date"] = ""  # # 🗓️
        item["content_text"] = ""  # # 🧾
        item["references"] = []  # # 📚
        item["references_dois"] = []  # # 🔗
        item["fallback_urls"] = []  # # 🔗
        item["errors"] = []  # # 🧾

        if arxiv_id:  # # ✅
            item["abs_url"] = item.get("abs_url") or abs_url(arxiv_id)  # # 🔗
            item["pdf_url"] = item.get("pdf_url") or pdf_url(arxiv_id)  # # 📄

        # ===== /abs =====
        if item.get("abs_url"):  # # ✅
            abs_html, abs_code = http_get_text(session=session, url=item["abs_url"])  # # 🌐
            bundle_parts.append(f"<!-- ===== ABS URL: {item['abs_url']} | HTTP {abs_code} ===== -->\n")  # # 🧾
            bundle_parts.append(abs_html)  # # 🧾
            bundle_parts.append("\n<!-- ===== END ABS ===== -->\n")  # # 🧾
            if abs_code == 200:  # # ✅
                abs_data = parse_abs_page(abs_html)  # # 🔎
                item["doi"] = abs_data.get("doi", "")  # # 🔗
                item["versions"] = abs_data.get("versions", [])  # # 🔁
                item["last_updated_raw"] = abs_data.get("last_updated_raw", "")  # # 🗓️
                item["html_url"] = abs_data.get("html_experimental_url", "")  # # 🌐
            else:  # # ❌
                item["errors"].append(f"abs_http_{abs_code}")  # # 🧾
                item["fallback_urls"].append(item["abs_url"])  # # 🔗
        else:  # # ❌
            item["errors"].append("missing_abs_url")  # # 🧾

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

        # ===== /html =====
        if not item.get("html_url") and arxiv_id:  # # ✅
            item["html_url"] = html_url(arxiv_id)  # # 🌐 tentative simple
        if item.get("html_url"):  # # ✅
            h_html, h_code = http_get_text(session=session, url=item["html_url"])  # # 🌐
            bundle_parts.append(f"<!-- ===== HTML URL: {item['html_url']} | HTTP {h_code} ===== -->\n")  # # 🧾
            bundle_parts.append(h_html)  # # 🧾
            bundle_parts.append("\n<!-- ===== END HTML ===== -->\n")  # # 🧾
            if h_code == 200:  # # ✅
                html_data = parse_html_page(h_html)  # # 🔎
                item["published_date"] = html_data.get("published_date", "")  # # 🗓️
                item["content_text"] = html_data.get("content_text", "")  # # 🧾
                item["references"] = html_data.get("references", [])  # # 📚
                item["references_dois"] = html_data.get("references_dois", [])  # # 🔗
            else:  # # ❌
                item["errors"].append(f"html_http_{h_code}")  # # 🧾
                item["fallback_urls"].append(item["html_url"])  # # 🔗

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

        item["missing_fields"] = compute_missing_fields(item)  # # 🚩
        if item["missing_fields"]:  # # ✅
            item["url_hint_if_missing"] = (
                f"Champs manquants: {', '.join(item['missing_fields'])}. "
                f"Tu peux vérifier ici: abs={item.get('abs_url','')} | html={item.get('html_url','')} | pdf={item.get('pdf_url','')}"
            )  # # 🧾
        else:  # # ✅
            item["url_hint_if_missing"] = ""  # # ✅

    bundle_html = "\n".join(bundle_parts)  # # 🧾
    html_name = f"arxiv_bundle_{ts}.html"  # # 🧾
    html_path = save_text_file(data_lake_raw_dir, html_name, bundle_html)  # # 💾

    result: Dict[str, Any] = {
        "ok": True,
        "query": query,
        "sort": sort,
        "count": len(collected),
        "max_results": max_results,
        "hit_limit_100": (max_results == MAX_RESULTS_HARD_LIMIT),
        "message_if_limit": "Limite 100 atteinte (max_results)." if (max_results == MAX_RESULTS_HARD_LIMIT) else "",
        "items": collected,
        "bundle_html_file": html_path,
        "supported_fields": SUPPORTED_FIELDS,
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

RUN_LOCAL_TEST = True  # # ✅ True = test ON | False = test OFF

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=5, sort="relevance")  # # 🕷️
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 🖨️
    print(f"💾 HTML bundle sauvegardé: {results.get('bundle_html_file')}")  # # 🖨️
