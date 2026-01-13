# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (search/cs) -> JSON + sauvegarde data_lake/raw  # # 🎯 Objectif du script
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gérer les chemins et dossiers
import re  # # 🔎 Extraire des infos via regex (ID, dates, versions)
import json  # # 🧾 Exporter en JSON
import time  # # ⏱️ Pause polie entre requêtes
import random  # # 🎲 Jitter pour éviter un rythme trop "robot"
import datetime  # # 🕒 Générer timestamps pour fichiers
from typing import Dict, Any, List, Optional  # # 🧩 Typage pour clarté
import requests  # # 🌐 Faire des requêtes HTTP GET
from bs4 import BeautifulSoup  # # 🍲 Parser HTML et sélectionner des balises

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Endpoint recherche Computer Science

DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Dossier de stockage raw
DEFAULT_META_DIR = os.path.join("data_lake", "metadata")  # # 🧾 Dossier metadata sources

MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Limite globale demandée (max 100)
PAGE_SIZE = 50  # # 📄 arXiv permet size=50 en général (pratique pour paginer)


# ============================================================
# 🌐 B) GET — Politesse + GET robuste + stockage HTML brut
# ============================================================

def ensure_dir(path: str) -> None:  # # 📁 Assurer que le dossier existe
    os.makedirs(path, exist_ok=True)  # # ✅ Crée le dossier si absent

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie entre requêtes
    time.sleep(random.uniform(min_s, max_s))  # # ⏳ Attendre un temps aléatoire

def http_get(session: requests.Session, url: str, timeout_s: int = 30) -> str:  # # 🌐 GET = télécharger le HTML
    headers = {"User-Agent": "Mozilla/5.0 DIXITBOT-arXivScraper/1.0"}  # # 🪪 User-Agent simple
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 Requête GET
    resp.raise_for_status()  # # ❌ Erreur si 4xx/5xx
    return resp.text  # # 📄 Retourner le HTML brut

def save_text_file(folder: str, filename: str, content: str) -> str:  # # 💾 Sauver du texte (HTML/JSON) dans un fichier
    ensure_dir(folder)  # # 📁 Créer le dossier si besoin
    path = os.path.join(folder, filename)  # # 🧩 Construire le chemin complet
    with open(path, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir en écriture UTF-8
        f.write(content)  # # 🧾 Écrire le contenu
    return path  # # 📌 Retourner le chemin du fichier

def now_iso_for_filename() -> str:  # # 🕒 Timestamp format fichier
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # 🧾 Exemple: 20260113_104500

# ============================================================
# 🔎 C) 
# ============================================================

def build_search_url(query: str, start: int, size: int = PAGE_SIZE) -> str:  # # 🔗 Construire l’URL arXiv search
    q = requests.utils.quote(query)  # # 🔎 Encoder la requête (espaces, caractères spéciaux)
    return f"{ARXIV_SEARCH_CS}?query={q}&searchtype=all&abstracts=show&order=-announced_date_first&size={size}&start={start}"  # # 🌐 URL paginée


# ============================================================
# 🧪 4
# ============================================================

def parse_search_page(html: str) -> List[Dict[str, Any]]:  # # 🧩 HTML -> liste d’articles (données structurées)
    soup = BeautifulSoup(html, "lxml")  # # 🍲 Parser le HTML
    items: List[Dict[str, Any]] = []  # # 📦 Liste de résultats

    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Chaque résultat arXiv
        title_el = li.select_one("p.title")  # # 🏷️ Balise titre
        authors_el = li.select_one("p.authors")  # # 👥 Balise auteurs
        abstract_el = li.select_one("span.abstract-full")  # # 🧾 Balise abstract (full)
        abs_link_el = li.select_one('p.list-title a[href^="/abs/"]')  # # 🔗 Lien vers page détail /abs/
        pdf_link_el = li.select_one('a[href^="/pdf/"]')  # # 📄 Lien PDF

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️ Texte du titre
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥 Texte auteurs brut
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 👥 Liste auteurs

        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾 Texte abstract
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹 Nettoyage

        abs_url = (ARXIV_BASE + abs_link_el.get("href", "")) if abs_link_el else ""  # # 🔗 URL page /abs/
        pdf_url = (ARXIV_BASE + pdf_link_el.get("href", "")) if pdf_link_el else ""  # # 📄 URL PDF

        arxiv_id = ""  # # 🆔 ID arXiv (ex: 2401.12345)
        m = re.search(r"/abs/([^/]+)$", abs_url) if abs_url else None  # # 🔎 Extraire l’ID depuis l’URL
        if m:  # # ✅ Si trouvé
            arxiv_id = m.group(1)  # # 🆔 Stocker ID

        items.append({  # # 📦 Ajouter un résultat structuré
            "arxiv_id": arxiv_id,  # # 🆔 Identifiant
            "title": title,  # # 🏷️ Titre
            "authors": authors,  # # 👥 Auteurs
            "abstract": abstract,  # # 🧾 Abstract (oui, récupéré)
            "abs_url": abs_url,  # # 🔗 Lien détail
            "pdf_url": pdf_url,  # # 📄 Lien PDF direct
            "source": "arxiv_search_cs",  # # 🧾 Source
        })  # # ✅ Fin item

    return items  # # 📤 Retourner la liste d’articles

# SECTION 5 — Fonction principale scrape_arxiv_cs (multi-pages + limite 100 + JSON)

def scrape_arxiv_cs(  # # 🚀 Fonction principale appelée par test local ou backend
    query: str,  # # 🔎 Mots-clés
    max_results: int = 20,  # # 🎯 Nombre max d’articles à récupérer
    polite_min_s: float = 1.5,  # # 😇 Pause min
    polite_max_s: float = 2.0,  # # 😇 Pause max
    data_lake_raw_dir: str = DEFAULT_RAW_DIR,  # # 💾 Dossier raw
) -> Dict[str, Any]:  # # 🧾 Retour JSON (dict)

    max_results = int(max_results)  # # 🔢 Sécuriser type
    if max_results < 1:  # # 🚫 Cas invalide
        max_results = 1  # # ✅ Minimum 1
    if max_results > MAX_RESULTS_HARD_LIMIT:  # # 🚧 Appliquer limite 100
        max_results = MAX_RESULTS_HARD_LIMIT  # # ✅ Forcer 100

    session = requests.Session()  # # 🔌 Session HTTP réutilisable
    collected: List[Dict[str, Any]] = []  # # 📦 Résultats cumulés multi-pages
    raw_pages_saved: List[str] = []  # # 💾 Liste des fichiers HTML sauvegardés
    start = 0  # # 📄 Offset pagination
    ts = now_iso_for_filename()  # # 🕒 Timestamp pour nommer les fichiers

    while len(collected) < max_results:  # # 🔁 Tant qu’on n’a pas assez de résultats
        url = build_search_url(query=query, start=start, size=PAGE_SIZE)  # # 🔗 Construire URL page X
        html = http_get(session=session, url=url)  # # 🌐 GET : télécharger HTML

        html_file = f"arxiv_search_{ts}_start_{start}.html"  # # 🧾 Nom fichier HTML brut
        raw_path = save_text_file(data_lake_raw_dir, html_file, html)  # # 💾 Sauvegarder HTML brut
        raw_pages_saved.append(raw_path)  # # 📌 Mémoriser où on a stocké le GET

        page_items = parse_search_page(html)  # # 🔎 SELECT : extraire balises depuis le HTML
        if not page_items:  # # 🛑 Si la page ne renvoie rien, on stoppe
            break  # # ✅ Sortie boucle

        collected.extend(page_items)  # # ➕ Ajouter résultats de cette page
        start += PAGE_SIZE  # # ➡️ Passer à la page suivante
        sleep_polite(min_s=polite_min_s, max_s=polite_max_s)  # # 😇 Pause polie

        if start > 1000:  # # 🛡️ Sécurité anti-boucle infinie
            break  # # ✅ Stop

    collected = collected[:max_results]  # # ✂️ Couper à max_results exact

    hit_limit_100 = (max_results == MAX_RESULTS_HARD_LIMIT)  # # 🚧 Indicateur limite
    message_if_limit = "Limite 100 atteinte (max_results)." if hit_limit_100 else ""  # # 🧾 Message limite

    result: Dict[str, Any] = {  # # 🧾 JSON final
        "ok": True,  # # ✅ Succès
        "query": query,  # # 🔎 Requête
        "count": len(collected),  # # 🔢 Nombre d’items
        "max_results": max_results,  # # 🎯 Limite demandée
        "hit_limit_100": hit_limit_100,  # # 🚧 Limite 100 atteinte ?
        "message_if_limit": message_if_limit,  # # 🧾 Message
        "items": collected,  # # 📚 Résultats
        "raw_html_files": raw_pages_saved,  # # 💾 Où sont stockés tous les GET (HTML bruts)
        "source_url_example": build_search_url(query=query, start=0, size=PAGE_SIZE),  # # 🔗 Exemple URL
    }  # # ✅ Fin JSON

    out_json_name = f"arxiv_raw_{ts}.json"  # # 🧾 Nom JSON raw
    out_json_path = os.path.join(data_lake_raw_dir, out_json_name)  # # 📁 Chemin JSON
    ensure_dir(data_lake_raw_dir)  # # 📁 Assurer dossier
    with open(out_json_path, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir fichier JSON
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾 Écrire le JSON

    result["saved_to"] = out_json_path  # # 📌 Ajouter le chemin du JSON créé
    return result  # # 📤 Retourner au caller (test local / backend)

# SECTION 6 — Test local activable/désactivable avec 1 ligne

# ============================================================  # # 📌 Séparateur
# 🧪 TEST LOCAL (exécution directe) — une ligne à activer/désactiver  # # ✅ Objectif: tester sans backend
# ============================================================  # # 📌 Séparateur

RUN_LOCAL_TEST = True  # # ✅ True = test ON | False = test OFF (ou mets # devant la ligne)

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️ Lancer uniquement si exécuté directement
    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️ Log début
    results = scrape_arxiv_cs(query="multimodal transformer", max_results=5)  # # 🕷️ Appel scraper
    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️ Afficher le nombre
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 📌 Afficher chemin du JSON
    items = results.get("items", [])  # # 📦 Récupérer liste items
    if items:  # # ✅ Si liste non vide
        print("🧾 Aperçu 1er article:")  # # 🖨️ Log aperçu
        print(json.dumps(items[0], indent=2, ensure_ascii=False))  # # 🧾 Afficher 1 item
