#==============================================
# Utile pour le scrapping + QA --> appel du script + appel Ollama (Qwen3)
#==============================================

# 🚀 FastAPI
from fastapi import FastAPI  # # Framework API # #
from pydantic import BaseModel  # # Validation payload # #

# 🌐 HTTP client (API REST Ollama)
import requests  # # Appels HTTP vers Ollama # #

# 🧹 Nettoyage texte
import re  # # Regex pour normaliser espaces # #

# 🕷️ Import de ton scraper (CHEMIN CORRIGÉ)
from module_MCP_scraping.scrapping import scrape_arxiv_cs  # # ✅ Import correct selon ton projet # #

app = FastAPI()  # # 🧠 API

#==============================================
# 1) Endpoint existant : Scrape arXiv
#==============================================

class ArxivScrapeRequest(BaseModel):  # # 🧾 Schéma de requête
    query: str  # # 🔎 Mots-clés
    max_results: int = 50  # # 🎯 Limite (capée à 100)
    sort: str = "relevance"  # # 🧭 relevance | submitted_date
    subcategory: str | None = None  # # 🧩 Ex cs.LG

@app.post("/scrape/arxiv")  # # 🛣️ Endpoint scrapping
def scrape_arxiv(req: ArxivScrapeRequest):  # # 🎯 Handler
    try:  # # 🧯 Protection
        return scrape_arxiv_cs(  # # 🚀 Appel scraper
            query=req.query,  # # 🔎
            max_results=req.max_results,  # # 🎯
            sort=req.sort,  # # 🧭
            subcategory=req.subcategory,  # # 🧩
            polite_min_s=1.5,  # # 😇
            polite_max_s=2.0,  # # 😇
            data_lake_raw_dir="data_lake/raw/cache",  # # 💾 (comme ton besoin cache)
        )  # # ✅ Fin appel
    except Exception as e:  # # ❌ Si crash
        return {"ok": False, "error": str(e)}  # # 🧾 Erreur structurée

#==============================================
# 2) Nouveau endpoint : Question -> Scraping -> Qwen3 -> Réponse
#==============================================

class AskRequest(BaseModel):  # # 🧾 Requête QA
    question: str  # # ❓ Question utilisateur
    max_results: int = 3  # # 🎯 Nombre de papiers à utiliser
    sort: str = "relevance"  # # 🧭 Tri arXiv
    subcategory: str | None = None  # # 🧩 Option
    model: str = "qwen3:1.7b"  # # 🤖 Modèle Ollama

def _clean(s: str) -> str:  # # 🧹 Nettoyage simple
    s = (s or "").strip()  # # Trim
    s = re.sub(r"\s+", " ", s)  # # Espaces multiples -> 1
    return s  # # Retour

def _build_context(items: list, max_chars: int = 14000) -> str:  # # 🧾 Contexte compact
    chunks = []  # # Liste blocs
    total = 0  # # Compteur
    for i, it in enumerate(items, start=1):  # # Parcours items
        block = (  # # Bloc par papier
            f"[PAPER {i}]\n"
            f"arxiv_id: {_clean(it.get('arxiv_id',''))}\n"
            f"title: {_clean(it.get('title',''))}\n"
            f"submitted_date: {_clean(it.get('submitted_date',''))}\n"
            f"published_date: {_clean(it.get('published_date',''))}\n"
            f"abs_url: {_clean(it.get('abs_url',''))}\n"
            f"pdf_url: {_clean(it.get('pdf_url',''))}\n"
            f"abstract: {_clean(it.get('abstract',''))}\n"
        )
        if total + len(block) > max_chars:  # # Limite
            break  # # Stop
        chunks.append(block)  # # Ajouter
        total += len(block)  # # Compter
    return "\n".join(chunks)  # # Retour

def _ollama_generate(prompt: str, model: str) -> str:  # # 🔌 Appel Ollama
    url = "http://localhost:11434/api/generate"  # # Endpoint local Ollama
    payload = {  # # Corps JSON
        "model": model,  # # Modèle
        "prompt": prompt,  # # Prompt
        "stream": False,  # # Pas de streaming
    }
    r = requests.post(url, json=payload, timeout=300)  # # POST
    r.raise_for_status()  # # Erreur si HTTP != 200
    data = r.json()  # # JSON réponse
    return (data.get("response") or "").strip()  # # Texte

@app.post("/ask")  # # 🛣️ Endpoint QA
def ask(req: AskRequest):  # # 🎯 Handler QA
    try:  # # 🧯 Protection
        question = _clean(req.question)  # # Nettoyer
        if not question:  # # Si vide
            return {"ok": False, "error": "Question vide."}  # # Retour

        # 1) Scraping arXiv (query = question, MVP)
        results = scrape_arxiv_cs(  # # Scrape
            query=question,  # # 🔎
            max_results=req.max_results,  # # 🎯
            sort=req.sort,  # # 🧭
            subcategory=req.subcategory,  # # 🧩
            polite_min_s=1.5,  # # 😇
            polite_max_s=2.0,  # # 😇
            data_lake_raw_dir="data_lake/raw/cache",  # # 💾
        )

        items = results.get("items") or []  # # Items
        if not items:  # # Rien
            return {"ok": True, "question": question, "answer": "Aucun papier trouvé.", "items": []}  # # Retour

        # 2) Construire contexte compact
        context = _build_context(items, max_chars=14000)  # # Contexte

        # 3) Construire prompt réponse
        prompt = (  # # Prompt final
            "Tu es un assistant de recherche.\n"
            "Tu dois répondre UNIQUEMENT à partir du CONTEXTE fourni.\n"
            "Si une info n'est pas dans le contexte, dis: \"Je ne peux pas l'affirmer avec ce contexte\".\n"
            "\n"
            "Format demandé:\n"
            "1) Réponse courte (3-6 lignes)\n"
            "2) Points clés (5 bullets)\n"
            "3) Papiers cités (liste: arxiv_id + title)\n"
            "\n"
            f"QUESTION:\n{question}\n\n"
            f"CONTEXTE:\n{context}\n"
        )

        # 4) Appel Qwen3 via Ollama
        answer = _ollama_generate(prompt=prompt, model=req.model)  # # Appel

        # 5) Retour items minimalistes (pour UI)
        items_min = [  # # Liste simplifiée
            {"arxiv_id": it.get("arxiv_id", ""), "title": it.get("title", ""), "abs_url": it.get("abs_url", "")}
            for it in items
        ]

        return {  # # Réponse API
            "ok": True,  # # Statut
            "question": question,  # # Question
            "query_used": question,  # # Query
            "count": len(items_min),  # # Count
            "answer": answer,  # # Réponse LLM
            "items": items_min,  # # Papiers
        }

    except Exception as e:  # # ❌ Si crash
        return {"ok": False, "error": str(e)}  # # Erreur

#==============================================
# End util pour le script scrapping
#==============================================