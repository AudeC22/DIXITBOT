# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (CS search -> /abs -> /html) -> 1 HTML bundle + 1 JSON  # # 🎯 Objectif
# ✅ Version "robuste + simple" : on ne garde QUE ce qu'on sait récupérer de façon fiable  # # ✅
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gestion des chemins/dossiers
import re  # # 🔎 Regex (ID, watermark)
import json  # # 🧾 Export JSON
import time  # # ⏱️ Politesse (sleep)
import random  # # 🎲 Jitter (éviter rythme robot)
import datetime  # # 🕒 Timestamp fichiers
from typing import Dict, Any, List, Tuple  # # 🧩 Typage

import requests  # # 🌐 HTTP (GET)
from bs4 import BeautifulSoup  # # 🍲 Parsing HTML (select)

# ============================================================  # # 📌 Séparateur
# 🌍 Constantes  # # 🧠 Paramètres globaux
# ============================================================  # # 📌 Séparateur

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Recherche Computer Science
DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Stockage raw (HTML bundle + JSON)
MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Max global demandé
PAGE_SIZE = 50  # # 📄 Pagination arXiv (50)

SUPPORTED_FIELDS = [  # # ✅ Champs effectivement supportés dans CETTE version
    "arxiv_id",  # # 🆔
    "title",  # # 🏷️
    "authors",  # # 👥
    "abstract",  # # 🧾
    "submitted_date",  # # 🗓️ (depuis search)
    "abs_url",  # # 🔗
    "pdf_url",  # # 📄 (PDF arXiv)
    "html_url",  # # 🌐 (HTML arXiv /html/<id>vN)
    "published_date",  # # 🗓️ (watermark /html)
    "doi",  # # 🔗 (trouvé dans /html via bibliographie)
    "license",  # # ⚖️ (license-tr /html)
    "references",  # # 📚 (liste structurée)
    "references_dois",  # # 🔗 (liste de DOI trouvés)
    "missing_fields",  # # 🚩
    "errors",  # # 🧾
    "url_hint_if_missing",  # # 🧭
]  # # ✅

# ============================================================  # # 📌 Séparateur
# ✅ A) Helpers (dossiers, timestamps, “vide”, politesse, GET)  # # 🧰
# ============================================================  # # 📌 Séparateur

def ensure_dir(path: str) -> None:  # # 📁 Créer dossier si besoin
    os.makedirs(path, exist_ok=True)  # # ✅

def now_iso_for_filename() -> str:  # # 🕒 Timestamp pour nom fichier
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260114_101500

def is_empty(value: Any) -> bool:  # # 🧪 Définition du “vide” (tes règles)
    if value is None:  # # ✅ None
        return True  # # ✅
    if isinstance(value, str):  # # 🧾 String
        v = value.strip()  # # 🧹
        if v == "":  # # ✅ vide si ""
            return True  # # ✅
        if v.lower() in {"n/a", "null", "none"}:  # # ✅ vide si "N/A", "null", "None" (string)
            return True  # # ✅
    if isinstance(value, list):  # # 📦 Liste
        return len(value) == 0  # # ✅ vide si liste vide
    return False  # # ❌ sinon non vide

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # ⏳

def http_get_text(session: requests.Session, url: str, timeout_s: int = 30) -> Tuple[str, int]:  # # 🌐 GET HTML (texte)
    headers = {  # # 🪪 UA "gentil" + clair
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DIXITBOT-arXivScraper/Final",  # # 🪪
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",  # # ✅
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",  # # ✅
    }  # # ✅
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 GET
    return resp.text, resp.status_code  # # 📄 HTML + code HTTP

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver un fichier texte
    ensure_dir(folder)  # # 📁
    path = os.path.join(folder, filename)  # # 🧩
    with open(path, "w", encoding="utf-8") as f:  # # ✍️
        f.write(content)  # # 🧾
    return path  # # 📌

def normalize_url(href: str) -> str:  # # 🔗 Normaliser href -> URL complète
    if not href:  # # 🚫
        return ""  # # ✅
    h = href.strip()  # # 🧹
    if h.startswith("//"):  # # 🌐 URL sans schéma
        return "https:" + h  # # ✅
    if h.startswith("/"):  # # ✅ relatif
        return ARXIV_BASE + h  # # 🔗
    return h  # # ✅ déjà absolu

def abs_url(arxiv_id: str) -> str:  # # 🔗 URL /abs
    return f"{ARXIV_BASE}/abs/{arxiv_id}"  # # ✅

def pdf_url(arxiv_id: str) -> str:  # # 📄 URL /pdf
    return f"{ARXIV_BASE}/pdf/{arxiv_id}"  # # ✅

def html_url(arxiv_id_with_version: str) -> str:  # # 🌐 URL /html (arxiv_id peut déjà inclure vN)
    return f"{ARXIV_BASE}/html/{arxiv_id_with_version}"  # # ✅

# ============================================================  # # 📌 Séparateur
# 🔎 B) URL builder (tri)  # # 🧭
# ============================================================  # # 📌 Séparateur

def build_search_url(query: str, start: int, size: int, sort: str) -> str:  # # 🔗 Construire URL search/cs
    q = requests.utils.quote(query)  # # 🔎 Encoder requête
    base = f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&size={size}&start={start}"  # # 🔗 Base
    s = (sort or "relevance").strip().lower()  # # 🧠 Normaliser
    if s in {"submitted_date", "submitted", "recent"}:  # # 🗓️ Plus récents (soumission)
        return base + "&order=-announced_date_first"  # # ✅ (param arXiv connu)
    if s in {"last_updated_date", "updated", "last_updated"}:  # # 🔄 Dernières MAJ
        return base + "&order=-last_updated_date_first"  # # ✅ tentative (fallback si 400)
    # ✅ relevance : SURTOUT ne pas mettre &order=-relevance (ça provoque un HTTP 400)  # # ✅
    return base  # # ✅ relevance

# ============================================================  # # 📌 Séparateur
# 🧩 C) Parsing SEARCH page (liste) — très robuste  # # ✅
# ============================================================  # # 📌 Séparateur

def extract_arxiv_id_from_href(href: str) -> str:  # # 🆔 Extraire l’ID depuis un href /abs ou /pdf
    if not href:  # # 🚫
        return ""  # # ✅
    m = re.search(r"/abs/([^?#/]+)", href)  # # 🔎 /abs/<id>
    if m:  # # ✅
        return m.group(1).strip()  # # 🆔
    m2 = re.search(r"/pdf/([^?#/]+)", href)  # # 🔎 /pdf/<id>
    if m2:  # # ✅
        return m2.group(1).strip()  # # 🆔
    return ""  # # ❌

def find_first_href_matching(li: BeautifulSoup, pattern: str) -> str:  # # 🔎 Trouver le 1er href matchant un regex
    for a in li.select("a[href]"):  # # 🔁 Tous les liens du résultat
        href = (a.get("href") or "").strip()  # # 🧾
        if href and re.search(pattern, href):  # # ✅ match
            return href  # # ✅
    return ""  # # ❌

def parse_search_page(search_html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML -> items basiques
    soup = BeautifulSoup(search_html, "lxml")  # # 🍲 Parse
    items: List[Dict[str, Any]] = []  # # 📦

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Un résultat arXiv
        title_el = li.select_one("p.title")  # # 🏷️ Titre
        authors_el = li.select_one("p.authors")  # # 👥 Auteurs
        abstract_el = li.select_one("span.abstract-full")  # # 🧾 Abstract full
        meta_el = li.select_one("p.is-size-7")  # # 🗓️ Ligne 'Submitted ...'

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 👥
        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹

        submitted_date = ""  # # 🗓️
        if meta_el:  # # ✅
            meta_txt = meta_el.get_text(" ", strip=True)  # # 🧾
            m = re.search(r"Submitted\s+(.+?)(?:;|$)", meta_txt, flags=re.IGNORECASE)  # # 🔎
            if m:  # # ✅
                submitted_date = m.group(1).strip()  # # 🗓️

        abs_href = find_first_href_matching(li, r"/abs/[^?#/]+")  # # 🔗 /abs
        pdf_href = find_first_href_matching(li, r"/pdf/[^?#/]+")  # # 📄 /pdf
        arxiv_id = extract_arxiv_id_from_href(abs_href or pdf_href)  # # 🆔

        abs_full = normalize_url(abs_href)  # # 🔗
        pdf_full = normalize_url(pdf_href)  # # 📄

        if arxiv_id and is_empty(abs_full):  # # ✅
            abs_full = abs_url(arxiv_id)  # # 🔗
        if arxiv_id and is_empty(pdf_full):  # # ✅
            pdf_full = pdf_url(arxiv_id)  # # 📄

        items.append({  # # 📦 Item minimal issu de search
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
# 🌐 D) Parsing /html (watermark date + DOI + refs + licence)  # # ✅
# ============================================================  # # 📌 Séparateur

def parse_html_page(html_text: str, current_html_url: str) -> Dict[str, Any]:  # # 🧩 /html -> dict enrichi
    soup = BeautifulSoup(html_text, "lxml")  # # 🍲
    out: Dict[str, Any] = {  # # 📦
        "published_date": "",  # # 🗓️
        "doi": "",  # # 🔗
        "license": "",  # # ⚖️
        "references": [],  # # 📚
        "references_dois": [],  # # 🔗
        "html_base_url": current_html_url,  # # 🌐 base sans #S1
    }  # # ✅

    wm = soup.select_one("#watermark-tr")  # # 🔎 <div id="watermark-tr"> ... 28 Nov 2025</div>
    if wm:  # # ✅
        wm_text = wm.get_text(" ", strip=True)  # # 🧾
        m = re.search(r"\]\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", wm_text)  # # 🔎 après ]
        if m:  # # ✅
            out["published_date"] = m.group(1).strip()  # # 🗓️

    lic = soup.select_one("#license-tr")  # # 🔎 <a id="license-tr"...>License: ...</a>
    if lic:  # # ✅
        out["license"] = lic.get_text(" ", strip=True)  # # ⚖️

    bib = soup.select_one('.ltx_biblist[id^="bib."]')  # # 🔎 class="ltx_biblist" id="bib.L1"
    if bib:  # # ✅
        refs: List[Dict[str, Any]] = []  # # 📦
        dois_flat: List[str] = []  # # 🔗
        for ref in bib.select(".ltx_bibitem"):  # # 🔁 Chaque référence
            raw_text = ref.get_text(" ", strip=True)  # # 🧾
            if not raw_text:  # # 🚫
                continue  # # ✅
            hrefs = [normalize_url((a.get("href") or "").strip()) for a in ref.select("a[href]")]  # # 🔗
            hrefs = [h for h in hrefs if h]  # # 🧹
            doi_hrefs = [h for h in hrefs if "doi.org/" in h]  # # 🔗
            for d in doi_hrefs:  # # 🔁
                if d not in dois_flat:  # # ✅
                    dois_flat.append(d)  # # ➕
            refs.append({  # # 📦 Référence structurée
                "raw_text": raw_text,  # # 🧾
                "urls": hrefs,  # # 🔗
                "dois": doi_hrefs,  # # 🔗
            })  # # ✅
        out["references"] = refs  # # 📚
        out["references_dois"] = dois_flat  # # 🔗

    if is_empty(out["doi"]) and out["references_dois"]:  # # ✅
        out["doi"] = out["references_dois"][0]  # # 🔗

    toc_a = soup.select_one('li.ltx_tocentry a.ltx_ref[href*="/html/"][href*="#"]')  # # 🔎 href=".../html/...#S1"
    if toc_a:  # # ✅
        href = (toc_a.get("href") or "").strip()  # # 🧾
        if href:  # # ✅
            base = href.split("#", 1)[0]  # # ✂️
            out["html_base_url"] = normalize_url(base)  # # 🌐

    return out  # # 📤

# ============================================================  # # 📌 Séparateur
# 🧮 E) Champs manquants + hints  # # 🚩
# ============================================================  # # 📌 Séparateur

def compute_missing_fields(item: Dict[str, Any]) -> List[str]:  # # 🚩 Champs vides
    missing: List[str] = []  # # 📦
    for f in SUPPORTED_FIELDS:  # # 🔁
        if f in {"missing_fields", "errors", "url_hint_if_missing"}:  # # 🧠 champs calculés
            continue  # # ✅
        if is_empty(item.get(f)):  # # 🧪
            missing.append(f)  # # ➕
    return missing  # # 📤

# ============================================================  # # 📌 Séparateur
# 🚀 F) Fonction principale (1 HTML bundle + 1 JSON)  # # ✅
# ============================================================  # # 📌 Séparateur

def scrape_arxiv_cs(  # # 🚀 Fonction principale
    query: str,  # # 🔎
    max_results: int = 20,  # # 🎯
    sort: str = "relevance",  # # 🔀 relevance | submitted_date | last_updated_date
    polite_min_s: float = 1.5,  # # 😇
    polite_max_s: float = 2.0,  # # 😇
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # 💾
) -> Dict[str, Any]:  # # 📤 JSON final

    max_results = int(max_results)  # # 🔢
    if max_results < 1:  # # 🚫
        max_results = 1  # # ✅
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅

    ts = now_iso_for_filename()  # # 🕒
    ensure_dir(data_lake_raw_dir)  # # 📁
    session = requests.Session()  # # 🔌
    bundle_parts: List[str] = []  # # 🧾 HTML bundle (UN SEUL fichier)
    collected: List[Dict[str, Any]] = []  # # 📦 Résultats (liste)
    start = 0  # # 📄 Pagination offset
    last_search_url_used = ""  # # 🧾 debug

    while len(collected) < max_results:  # # 🔁
        search_url = build_search_url(query=query, start=start, size=PAGE_SIZE, sort=sort)  # # 🔗
        last_search_url_used = search_url  # # 🧾
        search_html, code = http_get_text(session=session, url=search_url)  # # 🌐

        if code == 400 and (sort or "").strip().lower() in {"last_updated_date", "updated", "last_updated"}:  # # 🧯
            search_url_retry = build_search_url(query=query, start=start, size=PAGE_SIZE, sort="submitted_date")  # # 🛟
            search_html, code = http_get_text(session=session, url=search_url_retry)  # # 🌐
            bundle_parts.append(f"<!-- NOTE: order=-last_updated_date_first a renvoyé 400, fallback submitted_date -->\n")  # # 🧾
            last_search_url_used = search_url_retry  # # 🧾

        bundle_parts.append(f"<!-- ===== SEARCH URL: {last_search_url_used} | HTTP {code} ===== -->\n")  # # 🧾
        bundle_parts.append(search_html)  # # 🧾
        bundle_parts.append("\n<!-- ===== END SEARCH ===== -->\n")  # # 🧾

        if code != 200:  # # ❌
            break  # # 🛑

        page_items = parse_search_page(search_html)  # # 🔎 extraction search
        if not page_items:  # # 🛑
            break  # # ✅

        collected.extend(page_items)  # # ➕
        start += PAGE_SIZE  # # ➡️ page suivante
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    collected = collected[:max_results]  # # ✂️

    for item in collected:  # # 🔁
        item["html_url"] = ""  # # 🌐 init
        item["published_date"] = ""  # # 🗓️ init
        item["doi"] = ""  # # 🔗 init
        item["license"] = ""  # # ⚖️ init
        item["references"] = []  # # 📚 init
        item["references_dois"] = []  # # 🔗 init
        item["errors"] = []  # # 🧾 init

        arxiv_id = (item.get("arxiv_id") or "").strip()  # # 🆔
        if is_empty(arxiv_id):  # # 🚫
            item["errors"].append("missing_arxiv_id_from_search")  # # 🧾
            item["missing_fields"] = compute_missing_fields(item)  # # 🚩
            item["url_hint_if_missing"] = "ID arXiv introuvable depuis la page de recherche : ouvre le HTML bundle et cherche un lien /abs/."  # # 🧭
            continue  # # ✅

        if is_empty(item.get("abs_url")):  # # 🔗
            item["abs_url"] = abs_url(arxiv_id)  # # 🔗
        if is_empty(item.get("pdf_url")):  # # 📄
            item["pdf_url"] = pdf_url(arxiv_id)  # # 📄

        item["html_url"] = html_url(arxiv_id)  # # 🌐

        html_text, html_code = http_get_text(session=session, url=item["html_url"])  # # 🌐
        bundle_parts.append(f"<!-- ===== HTML URL: {item['html_url']} | HTTP {html_code} ===== -->\n")  # # 🧾
        bundle_parts.append(html_text)  # # 🧾
        bundle_parts.append("\n<!-- ===== END HTML ===== -->\n")  # # 🧾

        if html_code != 200:  # # ❌
            item["errors"].append(f"html_http_{html_code}")  # # 🧾
            item["missing_fields"] = compute_missing_fields(item)  # # 🚩
            item["url_hint_if_missing"] = f"Page HTML indisponible ({html_code}). Vérifie l'abs: {item.get('abs_url','')}"  # # 🧭
            sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇
            continue  # # ✅

        html_data = parse_html_page(html_text=html_text, current_html_url=item["html_url"])  # # 🔎
        item["published_date"] = html_data.get("published_date", "")  # # 🗓️
        item["doi"] = html_data.get("doi", "")  # # 🔗
        item["license"] = html_data.get("license", "")  # # ⚖️
        item["references"] = html_data.get("references", [])  # # 📚
        item["references_dois"] = html_data.get("references_dois", [])  # # 🔗

        base_url = html_data.get("html_base_url", "")  # # 🌐
        if base_url and base_url.startswith("http"):  # # ✅
            item["html_url"] = base_url  # # 🌐

        item["missing_fields"] = compute_missing_fields(item)  # # 🚩
        if item["missing_fields"]:  # # ✅
            item["url_hint_if_missing"] = (  # # 🧭
                f"Champs manquants: {', '.join(item['missing_fields'])}. "  # # 🧾
                f"Vérifie HTML: {item.get('html_url','')} | ABS: {item.get('abs_url','')} | PDF: {item.get('pdf_url','')}"  # # 🔗
            )  # # ✅
        else:  # # ✅
            item["url_hint_if_missing"] = ""  # # ✅

        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇

    hit_limit_100 = (max_results == MAX_RESULTS_HARD_LIMIT)  # # 🚧
    message_if_limit = "Limite 100 atteinte (max_results)." if hit_limit_100 else ""  # # 🧾

    bundle_html = "\n".join(bundle_parts)  # # 🧾
    html_name = f"arxiv_bundle_{ts}.html"  # # 🧾
    html_path = save_text_file(data_lake_raw_dir, html_name, bundle_html)  # # 💾

    result: Dict[str, Any] = {  # # 📦 JSON final
        "ok": True,  # # ✅
        "query": query,  # # 🔎
        "sort": sort,  # # 🔀
        "count": len(collected),  # # 🔢
        "max_results": max_results,  # # 🎯
        "hit_limit_100": hit_limit_100,  # # 🚧
        "message_if_limit": message_if_limit,  # # 🧾
        "items": collected,  # # 📚
        "bundle_html_file": html_path,  # # 💾
        "supported_fields": SUPPORTED_FIELDS,  # # ✅
    }  # # ✅

    json_name = f"arxiv_raw_{ts}.json"  # # 🧾
    json_path = os.path.join(data_lake_raw_dir, json_name)  # # 📁
    with open(json_path, "w", encoding="utf-8") as f:  # # ✍️
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾

    result["saved_to"] = json_path  # # 📌
    return result  # # 📤

# ============================================================  # # 📌 Séparateur
# 🧪 TEST LOCAL (1 ligne ON/OFF)  # # ✅
# ============================================================  # # 📌 Séparateur

RUN_LOCAL_TEST = True  # # ✅ True = test ON | False = test OFF

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=5, sort="relevance")  # # 🕷️
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 🖨️
    print(f"💾 HTML bundle sauvegardé: {results.get('bundle_html_file')}")  # # 🖨️
    items = results.get("items", [])  # # 📦
    if items:  # # ✅
        print("🧾 Aperçu item[0] :")  # # 🖨️
        print(json.dumps(items[0], ensure_ascii=False, indent=2))  # # 🧾
