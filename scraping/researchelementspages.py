# 📚 Importation des bibliothèques
import re  # # ✅ Pour nettoyer/normaliser du texte via regex
import requests  # # ✅ Pour télécharger le HTML d'une page web via HTTP
import pandas as pd  # # ✅ Pour structurer les résultats et exporter en Excel
from bs4 import BeautifulSoup, Tag  # # ✅ Pour parser le HTML et manipuler les balises

# 🌐 Téléchargement HTML
def fetch_html(url: str, timeout: int = 30) -> str:
    # ✅ Télécharge le HTML brut d'une page web (URL) et renvoie le texte HTML
    headers = {  # # ✅ En-têtes HTTP pour éviter certains blocages (user-agent)
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=timeout)  # # ✅ Requête GET
    resp.raise_for_status()  # # ✅ Stoppe avec une erreur si HTTP != 200
    return resp.text  # # ✅ Retourne le HTML

# 🧼 Nettoyage texte
def clean_text(s: str) -> str:
    # ✅ Nettoie un texte : supprime espaces multiples et retours à la ligne inutiles
    if not s:  # # ✅ Si chaîne vide ou None
        return ""  # # ✅ Renvoie vide
    s = re.sub(r"\s+", " ", s)  # # ✅ Remplace toute suite d'espaces/retours par 1 espace
    return s.strip()  # # ✅ Supprime espaces début/fin

# 🧭 Construire un CSS selector robuste
def css_selector(el: Tag) -> str:
    # ✅ Construit un sélecteur CSS "le plus précis possible"
    # ✅ Priorité : id (unique) > tag + classes > tag + nth-of-type
    if not isinstance(el, Tag):  # # ✅ Vérifie que c'est une balise
        return ""  # # ✅ Sinon renvoie vide

    parts = []  # # ✅ Liste des morceaux du selector (du bas vers le haut)
    cur = el  # # ✅ On part de l'élément ciblé

    while cur and isinstance(cur, Tag) and cur.name != "[document]":  # # ✅ Remonte l'arbre DOM
        if cur.get("id"):  # # ✅ Si l'élément a un id
            parts.append(f'{cur.name}#{cur.get("id")}')  # # ✅ id = unique => on peut s'arrêter
            break  # # ✅ Stoppe la remontée
        else:
            cls = cur.get("class", [])  # # ✅ Récupère la liste de classes
            cls = [c for c in cls if c and isinstance(c, str)]  # # ✅ Filtre sécurité
            base = cur.name  # # ✅ Base du sélecteur = nom de balise
            if cls:  # # ✅ Si classes présentes
                base += "." + ".".join(cls[:3])  # # ✅ Ajoute jusqu'à 3 classes (évite selectors énormes)
            else:
                # ✅ Pas de classes : on ajoute un nth-of-type pour être stable dans le parent
                if cur.parent and isinstance(cur.parent, Tag):  # # ✅ Vérifie parent
                    siblings_same_tag = [sib for sib in cur.parent.find_all(cur.name, recursive=False)]  # # ✅ Frères même tag
                    if len(siblings_same_tag) > 1:  # # ✅ Si plusieurs frères identiques
                        idx = siblings_same_tag.index(cur) + 1  # # ✅ nth-of-type commence à 1
                        base += f":nth-of-type({idx})"  # # ✅ Ajoute nth-of-type
            parts.append(base)  # # ✅ Ajoute ce niveau au selector

        cur = cur.parent  # # ✅ Remonte d'un niveau

    parts.reverse()  # # ✅ On a construit du bas vers le haut, on inverse
    return " > ".join(parts)  # # ✅ CSS final

# 🧭 Construire un XPath simple (lisible)
def xpath_selector(el: Tag) -> str:
    # ✅ Construit un XPath simple : /html/body/.../tag[n]
    if not isinstance(el, Tag):  # # ✅ Vérifie que c'est une balise
        return ""  # # ✅ Sinon vide

    parts = []  # # ✅ Morceaux XPath
    cur = el  # # ✅ Point de départ

    while cur and isinstance(cur, Tag) and cur.name != "[document]":  # # ✅ Remonte DOM
        if cur.get("id"):  # # ✅ Si id, on ancre ici (plus stable)
            parts.append(f'//*[@id="{cur.get("id")}"]')  # # ✅ XPath par id
            break  # # ✅ Stop
        if cur.parent and isinstance(cur.parent, Tag):  # # ✅ Si parent valide
            same = [sib for sib in cur.parent.find_all(cur.name, recursive=False)]  # # ✅ Frères même tag
            if len(same) > 1:  # # ✅ Si plusieurs, on met l'index
                idx = same.index(cur) + 1  # # ✅ Index XPath commence à 1
                parts.append(f"{cur.name}[{idx}]")  # # ✅ tag + [n]
            else:
                parts.append(cur.name)  # # ✅ tag seul
        else:
            parts.append(cur.name)  # # ✅ tag seul
        cur = cur.parent  # # ✅ Remonte

    parts.reverse()  # # ✅ Inverse pour obtenir chemin racine -> feuille
    if parts and parts[0].startswith('//*[@id="'):  # # ✅ Si ancré par id
        return "/".join(parts)  # # ✅ XPath ancré
    return "/" + "/".join(parts)  # # ✅ XPath absolu

# 🏷️ Détecter si une balise est un "titre"
def is_heading(el: Tag) -> bool:
    # ✅ Détermine si la balise est un titre : h1..h6 ou role="heading" ou classes typiques "title"
    if not isinstance(el, Tag):  # # ✅ Sécurité
        return False  # # ✅
    if el.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:  # # ✅ Standard HTML
        return True  # # ✅
    role = (el.get("role") or "").strip().lower()  # # ✅ Attribut ARIA role
    if role == "heading":  # # ✅ Certains sites utilisent div/span role=heading
        return True  # # ✅
    classes = " ".join(el.get("class", [])).lower()  # # ✅ Classes en texte
    if any(k in classes for k in ["title", "heading", "section-title", "ltx_title"]):  # # ✅ Heuristique (inclut LaTeXML)
        # ⚠️ On reste prudent : on exige aussi un texte non vide
        return bool(clean_text(el.get_text(" ", strip=True)))  # # ✅
    return False  # # ✅

# 📦 Collecter le contenu associé à un titre (jusqu'au prochain titre)
def collect_section_content(heading_el: Tag, max_chars: int = 6000) -> dict:
    # ✅ Récupère les éléments "contenu" après le titre, jusqu'au prochain titre
    contents = []  # # ✅ Stocke des blocs de contenu texte
    content_elements = []  # # ✅ Stocke des infos d'éléments (tag + selectors)

    # ✅ On parcourt les "next siblings" (frères suivants dans le DOM)
    for sib in heading_el.next_siblings:
        if isinstance(sib, Tag):  # # ✅ Ignore les strings/espaces
            if is_heading(sib):  # # ✅ Stop si on tombe sur le prochain titre
                break  # # ✅ Fin de section

            # ✅ On garde les blocs de contenu utiles (p, ul, ol, table, figure, div para, etc.)
            if sib.name in {"p", "div", "ul", "ol", "table", "figure", "section"}:
                txt = clean_text(sib.get_text(" ", strip=True))  # # ✅ Texte du bloc
                if txt:  # # ✅ Ignore vide
                    contents.append(txt)  # # ✅ Ajoute au contenu section
                    content_elements.append({  # # ✅ Ajoute la localisation exacte du bloc
                        "content_tag": sib.name,
                        "content_id": sib.get("id", ""),
                        "content_class": " ".join(sib.get("class", [])),
                        "content_css": css_selector(sib),
                        "content_xpath": xpath_selector(sib),
                    })

        # ✅ Coupe si on dépasse max_chars (évite sections énormes genre references)
        if sum(len(c) for c in contents) > max_chars:  # # ✅ Condition limite
            break  # # ✅

    section_text = clean_text(" ".join(contents))  # # ✅ Concatène le texte section
    return {  # # ✅ Retourne contenu + détails
        "section_text": section_text,
        "content_elements": content_elements,
    }

# 🔎 Analyse d'une page
def analyze_page(url: str) -> pd.DataFrame:
    # ✅ Analyse une page et produit un DataFrame : 1 ligne par titre + contenu associé
    html = fetch_html(url)  # # ✅ Télécharge le HTML
    soup = BeautifulSoup(html, "lxml")  # # ✅ Parse le HTML avec lxml (plus robuste)

    # ✅ On cible le contenu principal si possible (sinon toute la page)
    main = soup.find("main")  # # ✅ Beaucoup de sites structurent via <main>
    root = main if main else soup.body if soup.body else soup  # # ✅ Fallback

    headings = []  # # ✅ Liste des titres trouvés
    for el in root.find_all(True):  # # ✅ Parcours toutes les balises
        if is_heading(el):  # # ✅ Filtre titres
            title_text = clean_text(el.get_text(" ", strip=True))  # # ✅ Texte du titre
            if title_text:  # # ✅ Ignore titres vides
                headings.append(el)  # # ✅ Ajoute

    rows = []  # # ✅ Lignes Excel
    for i, h in enumerate(headings, start=1):  # # ✅ Boucle titres
        title_text = clean_text(h.get_text(" ", strip=True))  # # ✅ Texte titre
        level = h.name if h.name in {"h1","h2","h3","h4","h5","h6"} else "custom"  # # ✅ Niveau
        content_pack = collect_section_content(h)  # # ✅ Récup contenu jusqu'au prochain titre

        # ✅ Si
