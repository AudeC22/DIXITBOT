# ============================================================  # # 📌 Début du script
# 🧭 Analyse d’une page HTML arXiv (/html/xxxx) -> Sections -> Excel dans Téléchargements  # # 🎯 Objectif
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gérer les chemins Windows
import re  # # 🔎 Nettoyage/normalisation texte via regex
import json  # # 🧾 Sérialiser des listes/dicts (content_elements) dans une cellule Excel
import datetime  # # 🕒 Timestamp pour nommer les fichiers exportés
from pathlib import Path  # # 📂 Récupérer le dossier Téléchargements facilement
from typing import List, Dict, Any  # # 🧩 Typage pour clarté

import requests  # # 🌐 Télécharger le HTML via HTTP
import pandas as pd  # # 📊 Structurer les résultats et exporter en Excel
from bs4 import BeautifulSoup, Tag  # # 🍲 Parser HTML et manipuler des balises


# ============================================================  # # 📌 Séparateur
# 🌐 A) Télécharger le HTML d’une page  # # ✅ GET (requests)
# ============================================================  # # 📌 Séparateur

def fetch_html(url: str, timeout: int = 30) -> str:  # # 🌐 Télécharge le HTML brut d'une URL
    headers = {  # # 🪪 User-Agent pour éviter certains blocages
        "User-Agent": (  # # 🧾 Chaîne UA complète
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  # # 🪟 UA Windows
            "AppleWebKit/537.36 (KHTML, like Gecko) "  # # 🌐 Moteur
            "Chrome/120.0.0.0 Safari/537.36"  # # 🌐 Navigateur
        )
    }  # # ✅ Fin headers
    resp = requests.get(url, headers=headers, timeout=timeout)  # # ✅ Requête GET
    resp.raise_for_status()  # # ❌ Lève une erreur si HTTP != 200
    return resp.text  # # 📄 Retourne le HTML brut (string)


# ============================================================  # # 📌 Séparateur
# 🧼 B) Nettoyage texte  # # ✅ Uniformiser les espaces
# ============================================================  # # 📌 Séparateur

def clean_text(s: str) -> str:  # # 🧼 Nettoie le texte (espaces multiples, retours)
    if not s:  # # ✅ Si None ou chaîne vide
        return ""  # # ✅ Retourne vide
    s = re.sub(r"\s+", " ", s)  # # ✅ Remplace tout bloc d'espaces/retours par 1 espace
    return s.strip()  # # ✅ Supprime les espaces en début/fin


# ============================================================  # # 📌 Séparateur
# 🧭 C) Construire des sélecteurs (CSS + XPath)  # # ✅ Pour repérer où sont les infos
# ============================================================  # # 📌 Séparateur

def css_selector(el: Tag) -> str:  # # 🧭 Construit un sélecteur CSS le plus stable possible
    if not isinstance(el, Tag):  # # ✅ Sécurité : doit être une balise
        return ""  # # ✅ Sinon vide

    parts: List[str] = []  # # ✅ Morceaux de selector (de bas vers le haut)
    cur: Tag = el  # # ✅ Pointeur courant

    while cur and isinstance(cur, Tag) and cur.name != "[document]":  # # ✅ Remonte l'arbre DOM
        if cur.get("id"):  # # ✅ Si l’élément a un id
            parts.append(f"{cur.name}#{cur.get('id')}")  # # ✅ id = unique => ancrage fort
            break  # # ✅ On peut s'arrêter ici
        else:
            cls = cur.get("class", [])  # # ✅ Liste de classes
            cls = [c for c in cls if c and isinstance(c, str)]  # # ✅ Filtre sécurité
            base = cur.name  # # ✅ Base = nom de balise

            if cls:  # # ✅ Si classes présentes
                base += "." + ".".join(cls[:3])  # # ✅ Ajoute jusqu'à 3 classes (pas trop long)
            else:
                if cur.parent and isinstance(cur.parent, Tag):  # # ✅ Si parent valide
                    siblings_same = [sib for sib in cur.parent.find_all(cur.name, recursive=False)]  # # ✅ Frères même tag
                    if len(siblings_same) > 1:  # # ✅ Si plusieurs frères identiques
                        idx = siblings_same.index(cur) + 1  # # ✅ Index CSS nth-of-type commence à 1
                        base += f":nth-of-type({idx})"  # # ✅ Ajoute nth-of-type

            parts.append(base)  # # ✅ Ajoute ce niveau

        cur = cur.parent  # # ✅ Remonte d’un niveau

    parts.reverse()  # # ✅ Reconstruit du haut vers le bas
    return " > ".join(parts)  # # ✅ Retourne le selector CSS final


def xpath_selector(el: Tag) -> str:  # # 🧭 Construit un XPath lisible et stable
    if not isinstance(el, Tag):  # # ✅ Sécurité : doit être une balise
        return ""  # # ✅ Sinon vide

    parts: List[str] = []  # # ✅ Morceaux XPath
    cur: Tag = el  # # ✅ Pointeur courant

    while cur and isinstance(cur, Tag) and cur.name != "[document]":  # # ✅ Remonte DOM
        if cur.get("id"):  # # ✅ Si id
            parts.append(f'//*[@id="{cur.get("id")}"]')  # # ✅ Ancrage par id
            break  # # ✅ Stop (id suffit)
        if cur.parent and isinstance(cur.parent, Tag):  # # ✅ Si parent valide
            same = [sib for sib in cur.parent.find_all(cur.name, recursive=False)]  # # ✅ Frères même tag
            if len(same) > 1:  # # ✅ Si plusieurs
                idx = same.index(cur) + 1  # # ✅ Index XPath commence à 1
                parts.append(f"{cur.name}[{idx}]")  # # ✅ tag[n]
            else:
                parts.append(cur.name)  # # ✅ tag simple
        else:
            parts.append(cur.name)  # # ✅ tag simple (fallback)
        cur = cur.parent  # # ✅ Remonte

    parts.reverse()  # # ✅ Chemin racine -> feuille
    if parts and parts[0].startswith('//*[@id="'):  # # ✅ Si ancrage id
        return "/".join(parts)  # # ✅ XPath ancré
    return "/" + "/".join(parts)  # # ✅ XPath absolu


# ============================================================  # # 📌 Séparateur
# 🏷️ D) Détecter un "titre" (heading)  # # ✅ h1..h6 + heuristiques
# ============================================================  # # 📌 Séparateur

def is_heading(el: Tag) -> bool:  # # 🏷️ Détermine si une balise est un titre de section
    if not isinstance(el, Tag):  # # ✅ Sécurité
        return False  # # ✅

    if el.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:  # # ✅ Titres HTML standards
        return True  # # ✅

    role = (el.get("role") or "").strip().lower()  # # ✅ ARIA role éventuel
    if role == "heading":  # # ✅ Certains sites utilisent role=heading
        return True  # # ✅

    classes = " ".join(el.get("class", [])).lower()  # # ✅ Classes concaténées
    if any(k in classes for k in ["title", "heading", "section-title", "ltx_title"]):  # # ✅ Heuristique (LaTeXML incluse)
        return bool(clean_text(el.get_text(" ", strip=True)))  # # ✅ Exige un texte non vide

    return False  # # ✅ Pas un titre


# ============================================================  # # 📌 Séparateur
# 📦 E) Récupérer le contenu d’une section (jusqu’au prochain titre)  # # ✅ parsing simple
# ============================================================  # # 📌 Séparateur

def collect_section_content(heading_el: Tag, max_chars: int = 6000) -> Dict[str, Any]:  # # 📦 Contenu associé à un titre
    contents: List[str] = []  # # ✅ Stocke les blocs de texte
    content_elements: List[Dict[str, Any]] = []  # # ✅ Stocke les infos "où est le contenu" dans le DOM

    for sib in heading_el.next_siblings:  # # ✅ Parcourt les frères suivants
        if isinstance(sib, Tag):  # # ✅ Ignore les strings/espaces
            if is_heading(sib):  # # ✅ Stop si prochain titre
                break  # # ✅ Fin de section

            if sib.name in {"p", "div", "ul", "ol", "table", "figure", "section"}:  # # ✅ Balises utiles
                txt = clean_text(sib.get_text(" ", strip=True))  # # ✅ Texte du bloc
                if txt:  # # ✅ Ignore vide
                    contents.append(txt)  # # ✅ Ajoute au contenu
                    content_elements.append({  # # ✅ Ajoute la localisation DOM
                        "content_tag": sib.name,  # # ✅ Balise
                        "content_id": sib.get("id", ""),  # # ✅ id
                        "content_class": " ".join(sib.get("class", [])),  # # ✅ classes
                        "content_css": css_selector(sib),  # # ✅ CSS selector
                        "content_xpath": xpath_selector(sib),  # # ✅ XPath
                    })  # # ✅ Fin dict

        if sum(len(c) for c in contents) > max_chars:  # # ✅ Coupe si trop long (évite sections énormes)
            break  # # ✅ Stop

    section_text = clean_text(" ".join(contents))  # # ✅ Concatène tout le texte de la section
    return {  # # ✅ Retour structuré
        "section_text": section_text,  # # ✅ Texte complet section
        "content_elements": content_elements,  # # ✅ Où se trouvent les blocs dans la page
    }  # # ✅ Fin return


# ============================================================  # # 📌 Séparateur
# 🔎 F) Analyser une page et produire un DataFrame  # # ✅ 1 ligne = 1 titre + contenu
# ============================================================  # # 📌 Séparateur

def analyze_page(url: str) -> pd.DataFrame:  # # 🔎 Analyse une page et retourne un DataFrame
    html = fetch_html(url)  # # ✅ GET : télécharger le HTML
    soup = BeautifulSoup(html, "lxml")  # # ✅ Parse HTML avec lxml

    main = soup.find("main")  # # ✅ Essaie de cibler <main>
    root = main if main else soup.body if soup.body else soup  # # ✅ Fallback si <main> absent

    headings: List[Tag] = []  # # ✅ Liste des titres
    for el in root.find_all(True):  # # ✅ Parcourt toutes les balises
        if is_heading(el):  # # ✅ Filtre titres
            title_text = clean_text(el.get_text(" ", strip=True))  # # ✅ Texte titre
            if title_text:  # # ✅ Ignore vides
                headings.append(el)  # # ✅ Ajoute

    rows: List[Dict[str, Any]] = []  # # ✅ Lignes du futur Excel
    for i, h in enumerate(headings, start=1):  # # ✅ Pour chaque titre
        title_text = clean_text(h.get_text(" ", strip=True))  # # ✅ Texte du titre
        level = h.name if h.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else "custom"  # # ✅ Niveau

        content_pack = collect_section_content(h)  # # ✅ Récupère le contenu jusqu’au prochain titre

        if not content_pack.get("section_text"):  # # ✅ Si contenu vide
            continue  # # ✅ On saute (évite lignes inutiles)

        rows.append({  # # ✅ Ajoute une ligne
            "url": url,  # # ✅ URL analysée
            "heading_index": i,  # # ✅ Rang du titre
            "heading_level": level,  # # ✅ h1/h2/… ou custom
            "heading_text": title_text,  # # ✅ Texte du titre
            "heading_tag": h.name if hasattr(h, "name") else "",  # # ✅ Nom balise
            "heading_id": h.get("id", ""),  # # ✅ id
            "heading_class": " ".join(h.get("class", [])),  # # ✅ classes
            "heading_css": css_selector(h),  # # ✅ CSS selector du titre
            "heading_xpath": xpath_selector(h),  # # ✅ XPath du titre
            "section_text": content_pack.get("section_text", ""),  # # ✅ Texte de la section
            "content_elements": json.dumps(content_pack.get("content_elements", []), ensure_ascii=False),  # # ✅ JSON des blocs
        })  # # ✅ Fin dict

    df = pd.DataFrame(rows)  # # ✅ Convertit en DataFrame
    return df  # # ✅ Retour


# ============================================================  # # 📌 Séparateur
# 💾 G) Export Excel dans Téléchargements  # # ✅ C:\Users\<toi>\Downloads
# ============================================================  # # 📌 Séparateur

def export_to_downloads_excel(df: pd.DataFrame, filename_prefix: str = "page_analysis") -> str:  # # 💾 Exporte le DataFrame en xlsx
    downloads_dir = str(Path.home() / "Downloads")  # # ✅ Dossier Téléchargements Windows
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # # ✅ Timestamp pour nom unique
    out_path = os.path.join(downloads_dir, f"{filename_prefix}_{ts}.xlsx")  # # ✅ Chemin complet final
    df.to_excel(out_path, index=False)  # # ✅ Écrit l'Excel sans index
    return out_path  # # ✅ Retourne le chemin du fichier créé


# ============================================================  # # 📌 Séparateur
# 🧪 H) Test local (à lancer en direct)  # # ✅ python researchlementspages.py
# ============================================================  # # 📌 Séparateur

if __name__ == "__main__":  # # ▶️ Exécution directe uniquement
    test_url = "https://arxiv.org/html/2601.07830v1"  # # 🔗 Mets ici l’URL que tu veux analyser
    df = analyze_page(test_url)  # # ✅ Analyse la page
    out = export_to_downloads_excel(df, filename_prefix="arxiv_html_sections")  # # ✅ Export Excel
    print(f"✅ Excel créé dans Téléchargements : {out}")  # # 🖨️ Affiche le chemin
