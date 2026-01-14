#==============================================
# Utile pour le scrapping + QA --> appel du scraper + appel Ollama (Qwen3)
#==============================================

# 🚀 FastAPI
from fastapi import FastAPI  # # Framework API # #
from pydantic import BaseModel  # # Validation payload # #

# 🌐 HTTP client (API REST Ollama)
import requests  # # Appels HTTP vers Ollama # #

# 🧹 Nettoyage texte
import re  # # Regex pour normaliser espaces # #

# 🕷️ Import du scraper SCOPED (ciblé thématique)
from module_MCP_scraping.scrapping import scrape_arxiv_cs_scoped  # # ✅ IMPORTANT: version "scoped" # #

app = FastAPI()  # # 🧠 API

#==============================================
# 0) Healthcheck
#==============================================

@app.get("/health")  # # ✅ Vérifier que l'API tourne
def health():  # # Handler
    return {"ok": True}  # # Réponse simple

#==============================================
# 1) Endpoint : Scrape arXiv (SCOPED)
#==============================================

class ArxivScrapeRequest(BaseModel):  # # 🧾 Schéma de requête
    query: str  # # 🔎 Mots-clés utilisateur
    theme: str | None = None  # # 🎯 ai_ml|algo_ds|net_sys|cyber_crypto|pl_se|hci_data
    max_results: int = 20  # # 🎯 Limite (capée à 100)
    sort: str = "relevance"  # # 🧭 relevance | submitted_date
    debug_max_chars: int = 50000  # # 🧪 debug HTML coupé

@app.post("/scrape/arxiv")  # # 🛣️ Endpoint scrapping
def scrape_arxiv(req: ArxivScrapeRequest):  # # 🎯 Handler
    try:
        return scrape_arxiv_cs_scoped(
            user_query=req.query,
            theme=req.theme,
            max_results=req.max_results,
            sort=req.sort,
            data_lake_raw_dir="data_lake/raw/cache",  # # 💾 écrit dans le projet
            enrich_abs=True,
            enable_post_filter=True,
            debug_max_chars=req.debug_max_chars,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}

#==============================================
# 2) Endpoint : Question -> Scraping -> Qwen3 -> Réponse
#==============================================

class AskRequest(BaseModel):  # # 🧾 Requête QA
    question: str  # # ❓ Question utilisateur
    theme: str | None = "ai_ml"  # # 🎯 Par défaut IA/ML (modifiable)
    max_results: int = 3  # # 🎯 Nb papiers
    sort: str = "relevance"  # # 🧭 Tri
    model: str = "qwen3:1.7b"  # # 🤖 Modèle Ollama
    debug: bool = False  # # 🧪 Si True, renvoie aussi infos debug (paths, HTTP, etc.)

def _clean(s: str) -> str:  # # 🧹 Nettoyage
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _build_context(items: list, max_chars: int = 14000) -> str:  # # 🧾 Contexte compact
    chunks = []
    total = 0
    for i, it in enumerate(items, start=1):
        block = (
            f"[PAPER {i}]\n"
            f"arxiv_id: {_clean(it.get('arxiv_id',''))}\n"
            f"title: {_clean(it.get('title',''))}\n"
            f"submitted_date: {_clean(it.get('submitted_date',''))}\n"
            f"abs_url: {_clean(it.get('abs_url',''))}\n"
            f"pdf_url: {_clean(it.get('pdf_url',''))}\n"
            f"doi: {_clean(it.get('doi',''))}\n"
            f"abstract: {_clean(it.get('abstract',''))}\n"
        )
        if total + len(block) > max_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks)

def _ollama_generate(prompt: str, model: str) -> str:  # # 🔌 Appel Ollama
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()

@app.post("/ask")  # # 🛣️ Endpoint QA
def ask(req: AskRequest):  # # 🎯 Handler QA
    try:
        question = _clean(req.question)
        if not question:
            return {"ok": False, "error": "Question vide."}

        # 1) Scraping ciblé (SCOPED)
        results = scrape_arxiv_cs_scoped(
            user_query=question,
            theme=req.theme,
            max_results=req.max_results,
            sort=req.sort,
            data_lake_raw_dir="data_lake/raw/cache",
            enrich_abs=True,
            enable_post_filter=True,
            debug_max_chars=50000,
        )

        items = results.get("items") or []
        if not items:
            # ✅ On renvoie aussi saved_to/bundle pour diagnostiquer facilement
            out = {
                "ok": True,
                "question": question,
                "answer": "Aucun papier trouvé (ou parsing impossible). Regarde le bundle HTML et last_search_http.",
                "count": 0,
            }
            if req.debug:
                out["debug"] = {
                    "saved_to": results.get("saved_to"),
                    "bundle_html_file": results.get("bundle_html_file"),
                    "last_search_http": results.get("last_search_http"),
                    "last_search_url": results.get("last_search_url"),
                    "raw_cache_dir": results.get("raw_cache_dir"),
                }
            return out

        # 2) Contexte compact
        context = _build_context(items, max_chars=14000)

        # 3) Prompt strict (anti-hallucination)
        prompt = (
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
        answer = _ollama_generate(prompt=prompt, model=req.model)

        # 5) Items minimalistes
        items_min = [
            {"arxiv_id": it.get("arxiv_id", ""), "title": it.get("title", ""), "abs_url": it.get("abs_url", "")}
            for it in items
        ]

        out = {
            "ok": True,
            "question": question,
            "theme": req.theme,
            "query_used": results.get("scoped_query"),
            "count": len(items_min),
            "answer": answer,
            "items": items_min,
        }

        if req.debug:
            out["debug"] = {
                "saved_to": results.get("saved_to"),
                "bundle_html_file": results.get("bundle_html_file"),
                "last_search_http": results.get("last_search_http"),
                "last_search_url": results.get("last_search_url"),
                "raw_cache_dir": results.get("raw_cache_dir"),
            }

        return out

    except Exception as e:
        return {"ok": False, "error": str(e)}
