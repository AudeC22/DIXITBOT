# ============================================================
# 🕷️ SCRAPER arXiv — Structure pédagogique (GET -> SELECT -> STORE)
# ============================================================

import os  # # 📁 Gérer dossiers/chemins
import re  # # 🔎 Extraire des infos avec regex
import json  # # 🧾 Sauvegarder en JSON
import time  # # ⏱️ Pause polie entre requêtes
import random  # # 🎲 Jitter pour rythme naturel
import requests  # # 🌐 Faire des GET HTTP
from bs4 import BeautifulSoup  # # 🧠 Parser HTML et sélectionner des balises

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 URL recherche Computer Science

# ============================================================
# 🧱 A) STOCKAGE DES PAGES (HTML BRUT) — "on garde tous les GET"
# ============================================================

def store_raw_html(raw_dir: str, filename: str, html_text: str) -> str:  # # 💾 Stocker un HTML brut sur disque
    os.makedirs(raw_dir, exist_ok=True)  # # 📁 Créer le dossier si besoin
    path = os.path.join(raw_dir, filename)  # # 🧩 Construire le chemin complet
    with open(path, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir un fichier texte
        f.write(html_text)  # # 🧾 Écrire le HTML brut
    return path  # # 📌 Retourner le chemin du fichier sauvegardé

# ============================================================
# 🌐 B) GET — télécharger le HTML d’une page
# ============================================================

def http_get(url: str, session: requests.Session, timeout_s: int = 30) -> str:  # # 🌐 GET = télécharger la page en HTML
    headers = {"User-Agent": "Mozilla/5.0 arXivScraper/1.0"}  # # 🪪 User-Agent simple pour éviter refus basiques
    response = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 Faire la requête HTTP GET
    response.raise_for_status()  # # ❌ Lever erreur si status 4xx/5xx
    return response.text  # # 📄 Retourner le contenu HTML brut

def sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie
    time.sleep(random.uniform(min_s, max_s))  # # ⏳ Attendre un peu (anti-spam)

# ============================================================
# 🔎 C) SELECT — extraire titres/auteurs/abstracts depuis la page search
# ============================================================

def parse_search_page(html: str) -> list:  # # 🧩 Transformer un HTML search -> liste d’articles
    soup = BeautifulSoup(html, "lxml")  # # 🍲 PARSE : convertir HTML en objet navigable
    papers = []  # # 📦 STOCKAGE : liste de dictionnaires (futur JSON)

    for item in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 SELECT : chaque résultat dans la liste
        title_el = item.select_one("p.title")  # # 🏷️ SELECT : balise titre
        authors_el = item.select_one("p.authors")  # # 👥 SELECT : balise auteurs
        abstract_el = item.select_one("span.abstract-full")  # # 🧾 SELECT : balise abstract complet
        abs_link_el = item.select_one('p.list-title a[href^="/abs/"]')  # # 🔗 SELECT : lien /abs/
        pdf_link_el = item.select_one('a[href^="/pdf/"]')  # # 📄 SELECT : lien /pdf/

        title = title_el.get_text(" ", strip=True) if title_el else ""  # # 🏷️ EXTRACTION : texte du titre
        authors_txt = authors_el.get_text(" ", strip=True) if authors_el else ""  # # 👥 EXTRACTION : texte auteurs
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 🧠 Nettoyage auteurs

        abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""  # # 🧾 EXTRACTION : texte abstract
        abstract = abstract.replace("△ Less", "").strip()  # # 🧹 Nettoyage petit artefact

        abs_url = ARXIV_BASE + abs_link_el["href"] if abs_link_el and abs_link_el.get("href") else ""  # # 🔗 EXTRACTION : URL abstract
        pdf_url = ARXIV_BASE + pdf_link_el["href"] if pdf_link_el and pdf_link_el.get("href") else ""  # # 📄 EXTRACTION : URL PDF

        arxiv_id = ""  # # 🆔 Préparer l’ID
        m = re.search(r"/abs/([^/]+)$", abs_url)  # # 🔎 EXTRACTION : arXiv ID depuis /abs/
        if m:  # # ✅ Si match
            arxiv_id = m.group(1)  # # 🆔 Stocker l’ID

        papers.append({  # # 📦 STOCKAGE : dict = 1 article structuré
            "arxiv_id": arxiv_id,  # # 🆔
            "title": title,  # # 🏷️
            "authors": authors,  # # 👥
            "abstract": abstract,  # # 🧾 ✅ Oui : on récupère l’abstract ici
            "abs_url": abs_url,  # # 🔗
            "pdf_url": pdf_url,  # # 📄 (si demande PDF -> on renvoie le lien)
        })  # # ✅ Fin dict

    return papers  # # 📤 Retourne la liste de résultats

# ============================================================
# 🧠 D) PIPELINE — enchaîner GET -> SELECT -> STORE -> JSON
# ============================================================

def scrape_arxiv_cs(query: str, max_results: int = 10, raw_dir: str = "data_lake/raw") -> dict:  # # 🚀 Fonction principale
    session = requests.Session()  # # 🔌 Créer une session HTTP (plus efficace)
    max_results = min(int(max_results), 100)  # # 🚧 Limite max 100 demandée

    # 🔗 Construire l’URL search (page 1)
    url = f"{ARXIV_SEARCH_CS}?query={requests.utils.quote(query)}&searchtype=all&abstracts=show&size=50&start=0"  # # 🔎 URL search

    html_search = http_get(url, session=session)  # # 🌐 GET : télécharger HTML de la page search
    store_raw_html(raw_dir, "arxiv_search_page_0.html", html_search)  # # 💾 STOCKAGE : garder le HTML brut

    papers = parse_search_page(html_search)  # # 🔎 SELECT : extraire les champs depuis le HTML
    papers = papers[:max_results]  # # ✂️ Appliquer la limite (MVP)

    result = {  # # 🧾 JSON final (API-friendly)
        "ok": True,  # # ✅
        "query": query,  # # 🔎
        "max_results": max_results,  # # 🎯
        "count": len(papers),  # # 🔢
        "hit_limit_100": (max_results == 100),  # # 🚧 Indicateur limite
        "message_if_limit": "Limite 100 atteinte (max_results)." if max_results == 100 else "",  # # 🧾 Message
        "items": papers,  # # 📚 Résultats
    }  # # ✅ Fin JSON

    out_json = os.path.join(raw_dir, "arxiv_raw.json")  # # 📁 Chemin JSON raw
    with open(out_json, "w", encoding="utf-8") as f:  # # ✍️ Ouvrir fichier JSON
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾 Sauvegarder

    return result  # # 📤 Retourner au backend

# ============================================================
# 🧪 TEST LOCAL (facultatif) — exécuter le scraper seul
# ============================================================

RUN_LOCAL_TEST = True  # # ✅ Mets True pour tester | Mets False pour désactiver (ou commente la ligne avec #)

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️ Lance le test seulement si le fichier est exécuté directement

    print("🚀 Lancement du scraping arXiv (test local)...")  # # 🖨️ Message début

    results = scrape_arxiv_cs(  # # 🕷️ Appel de TA fonction principale (nom correct)
        query="multimodal transformer",  # # 🔎 Exemple requête
        max_results=5,  # # 🎯 Petit test
        sort="relevance",  # # 🧭 Tri
        subcategory="cs.AI",  # # 🧩 Sous-catégorie (optionnel)
        polite_min_s=1.5,  # # 😇 Politesse
        polite_max_s=2.0,  # # 😇 Politesse
        data_lake_raw_dir="data_lake/raw",  # # 💾 Dossier raw
    )  # # ✅ Fin appel

    print(f"✅ OK: {results.get('count')} articles récupérés")  # # 🖨️ Nombre récupéré
    print(f"💾 JSON sauvegardé: {results.get('saved_to')}")  # # 📌 Où est le fichier raw

    # 👀 Aperçu d’un article (le premier)
    items = results.get("items", [])  # # 📦 Récupérer la liste
    if items:  # # ✅ Si non vide
        print("🧾 Aperçu 1er article:")  # # 🖨️
        print(json.dumps(items[0], indent=2, ensure_ascii=False))  # # 🧾 Afficher 1er item en JSON
