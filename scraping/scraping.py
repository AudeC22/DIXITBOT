# ============================================================
# 🕷️ arXiv Scraper (search/cs) -> JSON + sauvegarde data_lake/raw
# ============================================================

import os  # # 📁 Gestion des chemins/dossiers
import re  # # 🔎 Regex pour extraire les versions/dates
import json  # # 🧾 Export JSON
import time  # # ⏱️ Politesse (sleep 1.5–2s)
import random  # # 🎲 Jitter pour éviter un rythme trop “robot”
import datetime  # # 🕒 Timestamp ISO pour logs + fichiers
from typing import Dict, Any, List, Optional, Tuple  # # 🧩 Typage pour clarté
import requests  # # 🌐 Requêtes HTTP
from bs4 import BeautifulSoup  # # 🧠 Parsing HTML (simple et robuste)

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Base URL arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Page de recherche (computer science)

# ------------------------------
# 🧠 Helpers
# ------------------------------

def _sleep_polite(min_s: float = 1.5, max_s: float = 2.0) -> None:  # # 😇 Pause polie entre requêtes
    time.sleep(random.uniform(min_s, max_s))  # # ⏳ Attendre un temps aléatoire dans l’intervalle

def _now_iso() -> str:  # # 🕒 Timestamp ISO
    return datetime.datetime.now(datetime.timezone.utc).isoformat()  # # ✅ Heure UTC ISO 8601

def _safe_mkdir(path: str) -> None:  # # 📁 Crée un dossier si nécessaire
    os.makedirs(path, exist_ok=True)  # # ✅ Ne plante pas si déjà existant

def _http_get(url: str, session: requests.Session, timeout_s: int = 30) -> str:  # # 🌐 GET robuste
    headers = {  # # 🪪 Headers “navigateur” pour éviter certains refus basiques
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) arXivScraper/1.0",  # # 👤 UA simple
        "Accept": "text/html,application/xhtml+xml",  # # 📥 On veut du HTML
    }  # # ✅ Fin headers
    resp = session.get(url, headers=headers, timeout=timeout_s)  # # 🚀 Appel HTTP
    resp.raise_for_status()  # # ❌ Lève une erreur si 4xx/5xx
    return resp.text  # # 📄 Retourne le HTML

def _parse_search_results(html: str) -> List[Dict[str, Any]]:  # # 🧩 Parse la liste de résultats
    soup = BeautifulSoup(html, "lxml")  # # 🍲 Parse HTML via lxml
    items = []  # # 📦 Liste finale des papers
    for li in soup.select("ol.breathe-horizontal li.arxiv-result"):  # # 📚 Chaque résultat arXiv
        title_el = li.select_one("p.title")  # # 🏷️ Titre
        authors_el = li.select_one("p.authors")  # # 👥 Auteurs
        abstract_el = li.select_one("span.abstract-full")  # # 🧾 Abstract (souvent “full” caché)
        link_abs_el = li.select_one('p.list-title a[href^="/abs/"]')  # # 🔗 Lien /abs/xxxx
        link_pdf_el = li.select_one('a[href^="/pdf/"]')  # # 📄 Lien PDF

        title = (title_el.get_text(" ", strip=True) if title_el else "")  # # ✅ Texte titre
        authors_txt = (authors_el.get_text(" ", strip=True) if authors_el else "")  # # ✅ Texte auteurs
        authors = [a.strip() for a in authors_txt.replace("Authors:", "").split(",") if a.strip()]  # # 🧠 Split simple

        abstract = ""  # # 🧾 Abstract
        if abstract_el:  # # ✅ Si trouvé
            abstract = abstract_el.get_text(" ", strip=True).replace("△ Less", "").strip()  # # 🧹 Nettoyage minimal

        abs_url = ""  # # 🔗 URL abstract
        if link_abs_el and link_abs_el.get("href"):  # # ✅ Lien existant
            abs_url = ARXIV_BASE + link_abs_el["href"]  # # 🌍 Absolutise

        pdf_url = ""  # # 📄 URL PDF
        if link_pdf_el and link_pdf_el.get("href"):  # # ✅ Lien existant
            pdf_url = ARXIV_BASE + link_pdf_el["href"]  # # 🌍 Absolutise

        arxiv_id = ""  # # 🆔 arXiv ID
        m = re.search(r"/abs/([^/]+)$", abs_url)  # # 🔎 Extrait l’ID depuis /abs/
        if m:  # # ✅ Match
            arxiv_id = m.group(1)  # # 🆔 ID

        items.append({  # # ➕ Ajoute un item “résultat”
            "arxiv_id": arxiv_id,  # # 🆔 Identifiant
            "title": title,  # # 🏷️ Titre
            "authors": authors,  # # 👥 Liste auteurs
            "abstract": abstract,  # # 🧾 Résumé
            "abs_url": abs_url,  # # 🔗 Page abstract
            "pdf_url": pdf_url,  # # 📄 PDF direct (si besoin, on renvoie le lien)
        })  # # ✅ Fin dict item
    return items  # # 📤 Renvoie la liste

def _parse_abs_page_for_dates(html: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:  # # 🗓️ Soumission + update + version
    soup = BeautifulSoup(html, "lxml")  # # 🍲 Parse
    history = soup.select_one("div.submission-history")  # # 🧾 Bloc historique versions
    if not history:  # # ❓ Pas trouvé
        return None, None, None  # # 🧯 On renvoie des None

    txt = history.get_text(" ", strip=True)  # # 📄 Texte complet du bloc
    # Exemple typique: "Submitted on 9 Jan 2026 (v1), last revised 10 Jan 2026 (v2)"  # # 📝 Exemple
    submitted = None  # # 🗓️ Date soumission
    last_updated = None  # # 🔁 Date dernière mise à jour
    last_version = None  # # 🔢 Dernière version

    m_sub = re.search(r"Submitted\s+on\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})", txt)  # # 🔎 Soumission
    if m_sub:  # # ✅ Match
        submitted = m_sub.group(1)  # # 🗓️ Valeur brute

    m_rev = re.search(r"last\s+revised\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})\s+\(v(\d+)\)", txt)  # # 🔎 Dernière révision
    if m_rev:  # # ✅ Match
        last_updated = m_rev.group(1)  # # 🔁 Date
        last_version = int(m_rev.group(2))  # # 🔢 Version

    if last_version is None:  # # 🤔 Si pas de “last revised”, on récupère la dernière (vX) présente
        m_ver = re.findall(r"\(v(\d+)\)", txt)  # # 🔎 Toutes les versions
        if m_ver:  # # ✅ Au moins une
            last_version = int(m_ver[-1])  # # 🔢 Prend la dernière

    return submitted, last_updated, last_version  # # 📤 Renvoie

# ------------------------------
# 🕷️ Scrape principal
# ------------------------------

def scrape_arxiv_cs(  # # 🚀 Fonction appelée par l’endpoint FastAPI
    query: str,  # # 🔎 Mots-clés utilisateur
    max_results: int = 50,  # # 🎯 Limite totale (capée à 100)
    sort: str = "relevance",  # # 🧭 relevance | submitted_date | last_updated_date
    subcategory: Optional[str] = None,  # # 🧩 ex: cs.LG (si fourni)
    polite_min_s: float = 1.5,  # # 😇 Politesse min
    polite_max_s: float = 2.0,  # # 😇 Politesse max
    data_lake_raw_dir: str = "data_lake/raw",  # # 📁 Dossier raw
) -> Dict[str, Any]:  # # 🧾 Retour JSON final

    max_results = min(int(max_results), 100)  # # 🧱 Hard cap 100 comme demandé
    fetched_at = _now_iso()  # # 🕒 Timestamp
    _safe_mkdir(data_lake_raw_dir)  # # 📁 Crée le dossier raw si besoin

    # ⚙️ Mapping tri -> paramètres arXiv (le site a un tri natif)  # # 🧠
    order = ""  # # 🧭 Paramètre “order”
    if sort == "submitted_date":  # # 🗓️ Plus récents soumis
        order = "-announced_date_first"  # # ✅ Tri côté arXiv (announced date)
    elif sort == "relevance":  # # 🎯 Pertinence
        order = ""  # # ✅ arXiv est souvent “relevance” par défaut
    elif sort == "last_updated_date":  # # 🔁 Dernières mises à jour
        order = ""  # # ⚠️ arXiv ne donne pas toujours ce tri directement sur search -> on le recalculera après
    else:  # # ❌ Sort inconnu
        sort = "relevance"  # # ✅ Fallback

    # 🧩 Construction URL base (arXiv search utilise: query, searchtype, size, start, order…)  # # 🧠
    size = 50  # # 📄 On pagine par 50 (standard pratique)
    start = 0  # # 📌 Offset pagination
    collected: List[Dict[str, Any]] = []  # # 📦 Accumulateur
    hit_limit = False  # # 🚧 Flag “max_results atteint”

    session = requests.Session()  # # 🔌 Session HTTP (réutilise connexions)

    while len(collected) < max_results:  # # 🔁 Tant qu’on n’a pas assez de résultats
        url = (  # # 🔗 URL de recherche paginée
            f"{ARXIV_SEARCH_CS}"
            f"?query={requests.utils.quote(query)}"  # # 🔎 query encodée
            f"&searchtype=all"  # # ✅ “all” comme tu veux
            f"&abstracts=show"  # # 🧾 Afficher les abstracts
            f"&order={requests.utils.quote(order)}"  # # 🧭 Tri si applicable
            f"&size={size}"  # # 📄 Taille page
            f"&start={start}"  # # 📌 Pagination
        )  # # ✅ Fin URL

        if subcategory:  # # 🧩 Si une sous-catégorie est donnée
            url += f"&classification-computer_science=y&classification-physics_archives=all&classification-q_finance=all&classification-statistics=all&classification=q_biology=all&classification=q_economics=all&classification=q_eess=all&classification-mathematics=all&classification={requests.utils.quote(subcategory)}"  # # 🧩 Ajout filtre (simple)

        try:  # # 🧯 Gestion d’erreur réseau
            html = _http_get(url, session=session)  # # 🌐 Récupère HTML
        except Exception as e:  # # ❌ Si erreur HTTP/parsing
            return {  # # 📤 Retourne une erreur structurée
                "ok": False,  # # ❌
                "error": str(e),  # # 🧾 Message
                "query": query,  # # 🔎 Contexte
                "sort": sort,  # # 🧭 Contexte
                "max_results": max_results,  # # 🎯 Contexte
                "fetched_at": fetched_at,  # # 🕒 Contexte
            }  # # ✅ Fin erreur

        page_items = _parse_search_results(html)  # # 🧩 Parse les résultats de la page
        if not page_items:  # # 🛑 Plus rien à scraper
            break  # # ✅ Stop pagination

        # ➕ Ajout en respectant max_results  # # 🧠
        for it in page_items:  # # 🔁 Chaque item
            if len(collected) >= max_results:  # # 🚧 Si on a atteint la limite
                hit_limit = True  # # ✅ Flag
                break  # # 🛑 Stop
            collected.append(it)  # # ➕ Ajoute

        start += size  # # ➡️ Page suivante
        _sleep_polite(polite_min_s, polite_max_s)  # # 😇 Pause polie

    # 🧠 Récupération “contenu des pages” : on visite /abs/ pour dates/versions  # # 🧠
    for it in collected:  # # 🔁 Pour chaque paper collecté
        abs_url = it.get("abs_url", "")  # # 🔗 URL abstract
        if not abs_url:  # # ❓ Si pas de lien
            continue  # # ⏭️

        try:  # # 🧯 Protège l’appel
            html_abs = _http_get(abs_url, session=session)  # # 🌐 HTML page abstract
            sub_date, last_upd, last_ver = _parse_abs_page_for_dates(html_abs)  # # 🗓️ Extrait dates/versions
            it["submitted_date"] = sub_date  # # 🗓️ Ajoute champ
            it["last_updated_date"] = last_upd  # # 🔁 Ajoute champ
            it["last_version"] = last_ver  # # 🔢 Ajoute champ
        except Exception as e:  # # ❌ Si ça plante sur un article
            it["submitted_date"] = None  # # 🧯 Valeur neutre
            it["last_updated_date"] = None  # # 🧯 Valeur neutre
            it["last_version"] = None  # # 🧯 Valeur neutre
            it["warning"] = f"abs_fetch_failed: {str(e)}"  # # ⚠️ Trace courte

        _sleep_polite(polite_min_s, polite_max_s)  # # 😇 Pause polie

    # 🔁 Tri “last_updated_date” si demandé (re-tri local)  # # 🧠
    if sort == "last_updated_date":  # # 🔁 Si l’utilisateur veut les dernières mises à jour
        def _key(it: Dict[str, Any]) -> str:  # # 🧩 Clé de tri simple
            return it.get("last_updated_date") or ""  # # ✅ None -> ""
        collected.sort(key=_key, reverse=True)  # # 🔁 Tri descendant

    # 🧾 Construction résultat final  # # 🧠
    result = {  # # 📦 JSON final
        "ok": True,  # # ✅ Succès
        "query": query,  # # 🔎 Mots-clés
        "subcategory": subcategory,  # # 🧩 Sous-catégorie éventuelle
        "sort": sort,  # # 🧭 Tri demandé
        "max_results": max_results,  # # 🎯 Limite
        "count": len(collected),  # # 🔢 Nombre obtenu
        "hit_limit_100": bool(hit_limit or len(collected) >= 100),  # # 🚧 Indique si limite 100 touchée
        "message_if_limit": "Limite 100 atteinte (max_results)." if (hit_limit or len(collected) >= 100) else "",  # # 🧾 Message demandé
        "fetched_at": fetched_at,  # # 🕒 Timestamp
        "items": collected,  # # 📚 Résultats
    }  # # ✅ Fin JSON

    # 💾 Sauvegarde dans raw format JSON  # # 🧠
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", query)[:60]  # # 🧹 Nom de fichier propre
    out_path = os.path.join(data_lake_raw_dir, f"arxiv_cs_{safe_name}_{int(time.time())}.json")  # # 📁 Chemin
    with open(out_path, "w", encoding="utf-8") as f:  # # ✍️ Ouvre fichier
        json.dump(result, f, ensure_ascii=False, indent=2)  # # 🧾 Écrit JSON lisible

    result["saved_to"] = out_path  # # 📌 On renvoie aussi où on a sauvegardé
    return result  # # 📤 Retour final
