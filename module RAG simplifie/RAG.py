# ============================================================  # # 📌 Séparateur visuel (lisibilité)
# 📚 Documentation Navigator (RAG simplifié)                     # # 🎯 Objectif : chercher un extrait de doc (local) par "sens"
# ✅ TF-IDF + cosine similarity (scikit-learn)                   # # 🧠 Recherche sémantique simplifiée, sans base vectorielle
# ============================================================  # # 📌 Séparateur visuel (lisibilité)

# ==============================  # # 📌 Début imports
# 📚 Importation des bibliothèques  # # 🧠 Modules nécessaires au moteur de recherche
# ==============================  # # 📌 Séparateur

from typing import List, Dict, Any, Optional, Tuple  # # 🧩 Typage : rend le code plus clair et robuste
import re  # # 🔎 Regex : pour nettoyer la requête (optionnel mais utile)

from sklearn.feature_extraction.text import TfidfVectorizer  # # 🧠 TF-IDF : transforme texte -> vecteurs
from sklearn.metrics.pairwise import cosine_similarity  # # 📐 Similarité cosinus : mesure proximité entre vecteurs

# ==============================  # # 📌 Séparateur
# 🧱 Base documentaire locale (mini dataset)  # # ✅ Simule une doc type PyTorch / Scikit-learn
# ==============================  # # 📌 Séparateur

DOCS_DB: List[Dict[str, Any]] = [  # # 📦 Liste de dictionnaires : “base de données” simple
    {  # # 🧾 Entrée 1 (PyTorch)
        "library": "pytorch",  # # 🏷️ Bibliothèque : sert à filtrer (option library)
        "name": "torch.nn.Linear",  # # 🏷️ Nom de la fonction / classe
        "signature": "torch.nn.Linear(in_features, out_features, bias=True)",  # # 🧾 Signature pour contexte
        "description": (  # # 🧾 Description textuelle (servira au TF-IDF)
            "Couche linéaire (affine) : y = xA^T + b. "
            "Utilisée dans les réseaux fully-connected. "
            "Paramètres : in_features, out_features, bias."
        ),
    },
    {  # # 🧾 Entrée 2 (PyTorch)
        "library": "pytorch",  # # 🏷️ Bibliothèque
        "name": "torch.nn.CrossEntropyLoss",  # # 🏷️ Nom
        "signature": "torch.nn.CrossEntropyLoss(weight=None, ignore_index=-100, reduction='mean')",  # # 🧾 Signature
        "description": (  # # 🧾 Description
            "Fonction de perte pour classification multi-classes. "
            "Combine log-softmax et negative log-likelihood. "
            "Attendu : logits (non normalisés) et labels entiers."
        ),
    },
    {  # # 🧾 Entrée 3 (Scikit-learn)
        "library": "scikit-learn",  # # 🏷️ Bibliothèque
        "name": "sklearn.model_selection.train_test_split",  # # 🏷️ Nom
        "signature": "train_test_split(*arrays, test_size=None, train_size=None, random_state=None, shuffle=True)",  # # 🧾 Signature
        "description": (  # # 🧾 Description
            "Sépare des tableaux en ensembles d'entraînement et de test. "
            "Paramètres importants : test_size, random_state, shuffle. "
            "Renvoie X_train, X_test, y_train, y_test, etc."
        ),
    },
    {  # # 🧾 Entrée 4 (Scikit-learn)
        "library": "scikit-learn",  # # 🏷️ Bibliothèque
        "name": "sklearn.feature_extraction.text.TfidfVectorizer",  # # 🏷️ Nom
        "signature": "TfidfVectorizer(analyzer='word', ngram_range=(1,1), stop_words=None)",  # # 🧾 Signature
        "description": (  # # 🧾 Description
            "Convertit une collection de documents texte en matrice TF-IDF. "
            "Utile pour la recherche d'information et le text mining. "
            "Options : stop_words, ngram_range, min_df, max_df."
        ),
    },
]  # # ✅ Fin dataset

# ==============================  # # 📌 Séparateur
# 🧼 Utilitaires (nettoyage + normalisation)  # # 🎯 Améliore un peu la robustesse
# ==============================  # # 📌 Séparateur

def _normalize_text(text: str) -> str:  # # 🧼 Nettoie une chaîne pour stabiliser la recherche
    text = text or ""  # # ✅ Évite None : si text est None -> ""
    text = text.strip()  # # 🧹 Enlève espaces début/fin
    text = re.sub(r"\s+", " ", text)  # # 🧽 Remplace multi-espaces / retours lignes -> 1 espace
    return text  # # 📤 Renvoie texte normalisé

def _build_corpus(docs: List[Dict[str, Any]]) -> List[str]:  # # 🧠 Construit le texte qui sera vectorisé
    corpus: List[str] = []  # # 📦 Liste des documents (texte)
    for d in docs:  # # 🔁 Parcourt chaque entrée doc
        lib = _normalize_text(str(d.get("library", "")))  # # 🏷️ Récupère bibliothèque
        name = _normalize_text(str(d.get("name", "")))  # # 🏷️ Récupère nom
        sig = _normalize_text(str(d.get("signature", "")))  # # 🧾 Récupère signature
        desc = _normalize_text(str(d.get("description", "")))  # # 🧾 Récupère description
        merged = f"{lib} {name} {sig} {desc}"  # # 🔗 Fusion : on met tout dans un seul “document” texte
        corpus.append(merged)  # # ➕ Ajoute au corpus
    return corpus  # # 📤 Renvoie corpus texte

# ==============================  # # 📌 Séparateur
# 🧠 Moteur “RAG simplifié” : TF-IDF + cosine similarity  # # 🎯 Trouver l'extrait le plus pertinent
# ==============================  # # 📌 Séparateur

def lookup_docs(query: str, library: Optional[str] = None) -> Dict[str, Any]:  # # 🚀 Fonction principale demandée
    query_norm = _normalize_text(query)  # # 🧼 Normalise la requête utilisateur
    if query_norm == "":  # # 🚫 Si requête vide
        return {  # # 📤 Retourne une réponse propre (pas d'exception)
            "ok": False,  # # ❌ Indique échec (requête vide)
            "error": "query_empty",  # # 🧾 Code erreur
            "message": "La requête est vide. Donne une question ou un mot-clé.",  # # 🗣️ Message clair
            "match": None,  # # 🧾 Pas de match
            "confidence": 0.0,  # # 📉 Score nul
        }  # # ✅ Fin retour

    # --- Filtrage par bibliothèque (optionnel) ---  # # 🧠 Respecte le paramètre library si donné
    docs = DOCS_DB  # # 📦 Par défaut : on cherche dans toute la base
    if library is not None and _normalize_text(library) != "":  # # ✅ Si un filtre library est demandé
        lib_norm = _normalize_text(library).lower()  # # 🧼 Normalise la bibliothèque (minuscule)
        docs = [d for d in DOCS_DB if _normalize_text(str(d.get("library", ""))).lower() == lib_norm]  # # 🔎 Filtre strict

    if len(docs) == 0:  # # 🚫 Si aucune doc ne correspond à la bibliothèque
        return {  # # 📤 Réponse propre
            "ok": False,  # # ❌
            "error": "library_not_found",  # # 🧾
            "message": f"Aucune documentation trouvée pour library='{library}'.",  # # 🗣️
            "match": None,  # # 🧾
            "confidence": 0.0,  # # 📉
        }  # # ✅

    # --- Vectorisation TF-IDF ---  # # 🧠 Transforme texte -> vecteurs pour comparer “par sens”
    corpus = _build_corpus(docs)  # # 📚 Construit corpus texte depuis docs filtrées
    vectorizer = TfidfVectorizer(stop_words=None)  # # 🧠 Vectorizer (simple, débutant-friendly)
    X = vectorizer.fit_transform(corpus)  # # ✅ Matrice TF-IDF (docs)
    q_vec = vectorizer.transform([query_norm])  # # ✅ Vecteur TF-IDF de la requête

    # --- Similarité cosinus ---  # # 📐 Compare la requête à chaque doc
    sims = cosine_similarity(q_vec, X)[0]  # # 📊 sims = tableau 1D (score par doc)
    best_idx = int(sims.argmax())  # # 🥇 Index du meilleur score
    best_score = float(sims[best_idx])  # # 🎯 Score du meilleur match (0..1 approximatif)
    best_doc = docs[best_idx]  # # 📌 Doc correspondante

    # --- Score de confiance (simple) ---  # # 🧠 Interprétation pédagogique
    # ⚠️ TF-IDF n'est pas une “vraie” sémantique profonde : le score reste indicatif.  # # 📝 Note
    confidence = best_score  # # ✅ On expose directement le cosine score comme “confidence”

    # --- Retour structuré ---  # # 📦 Format clair pour FastAPI / MCP / LLM
    return {  # # 📤 Résultat final
        "ok": True,  # # ✅ Succès
        "query": query_norm,  # # 🔎 Requête normalisée
        "library_filter": _normalize_text(library) if library is not None else None,  # # 🏷️ Filtre appliqué (ou None)
        "match": {  # # 🧾 Extrait trouvé
            "library": best_doc.get("library", ""),  # # 🏷️ Bibliothèque
            "name": best_doc.get("name", ""),  # # 🏷️ Nom
            "signature": best_doc.get("signature", ""),  # # 🧾 Signature
            "description": best_doc.get("description", ""),  # # 🧾 Description
        },
        "confidence": round(confidence, 4),  # # 📈 Score arrondi pour lisibilité
    }  # # ✅ Fin retour

# ==============================  # # 📌 Séparateur
# 🧪 Test local (désactivable en 1 ligne)  # # ✅ Permet de tester immédiatement
# ==============================  # # 📌 Séparateur

RUN_LOCAL_TEST = True  # # ✅ Mets True pour tester | mets False pour couper (attention: False avec F majuscule)

if __name__ == "__main__" and RUN_LOCAL_TEST:  # # ▶️ Exécute uniquement si lancé en script direct
    print("🚀 Test Documentation Navigator (RAG simplifié)")  # # 🖨️ Log
    r1 = lookup_docs("comment séparer mon dataset en train et test ?", library="scikit-learn")  # # 🔎 Test 1
    print(r1)  # # 🖨️ Affiche résultat
    r2 = lookup_docs("quelle loss pour classification multi classe avec logits ?", library="pytorch")  # # 🔎 Test 2
    print(r2)  # # 🖨️ Affiche résultat
    r3 = lookup_docs("vectorisation tf idf pour texte")  # # 🔎 Test 3 (sans filtre library)
    print(r3)  # # 🖨️ Affiche résultat
