# Début scraping main
# ============================================================  # #
# 🚀 FastAPI Orchestrateur (Scraping arXiv + Qwen3 via Ollama)   # #
# - Objectif : exposer /health, /scrape/arxiv, /ask              # #
# - Robustesse : imports stables même si uvicorn change le CWD   # #
# - ✅ CORRECTION: on NE passe PAS debug_max_chars au scraper     # #
#   car scrape_arxiv_cs_scoped(...) ne le supporte pas            # #
# ============================================================  # #

# ===============================  # #
# 📚 Imports standard              # #
# ===============================  # #
import os  # # Gestion chemins # # Étape: NORMALISATION/DECOUPLAGE (chemins stables)
import sys  # # sys.path pour imports robustes # # Étape: NORMALISATION/DECOUPLAGE (évite crash import)
import re  # # Nettoyage texte # # Étape: NORMALISATION/DECOUPLAGE (prompt/context propre)
from pathlib import Path  # # Chemins robustes # # Étape: NORMALISATION/DECOUPLAGE (Windows-friendly)
from typing import Any, Dict, List, Optional  # # Typage # # Étape: NORMALISATION/DECOUPLAGE (contrat stable)

# ===============================  # #
# 🚀 FastAPI + Pydantic            # #
# ===============================  # #
from fastapi import FastAPI  # # Framework API # # Étape: ORCHESTRATION (endpoints)
from pydantic import BaseModel, Field  # # Validation payload # # Étape: ORCHESTRATION (contrat d’entrée)

# ===============================  # #
# 🌐 HTTP (Ollama)                 # #
# ===============================  # #
import requests  # # Appels HTTP # # Étape: ORCHESTRATION (appel LLM local)

# ===============================  # #
# 🧱 Bootstrap chemins (IMPORTANT) # #
# ===============================  # #
_THIS_FILE = Path(__file__).resolve()  # # Chemin absolu du fichier # # Étape: NORMALISATION/DECOUPLAGE (évite CWD)
_THIS_DIR = _THIS_FILE.parent  # # Dossier du main # # Étape: NORMALISATION/DECOUPLAGE

# 👉 On suppose que le project root est soit le dossier courant, soit son parent (selon ton arborescence).
#    On force l’ajout dans sys.path pour que `module_MCP_scraping...` soit importable même sous uvicorn.
_CANDIDATES = [  # # Liste candidats racine # # Étape: NORMALISATION/DECOUPLAGE
    _THIS_DIR,  # # Candidat 1: dossier main.py # # Étape: NORMALISATION/DECOUPLAGE
    _THIS_DIR.parent,  # # Candidat 2: parent # # Étape: NORMALISATION/DECOUPLAGE
]
PROJECT_ROOT = None  # # Init # # Étape: NORMALISATION/DECOUPLAGE
for c in _CANDIDATES:  # # Boucle candidats # # Étape: NORMALISATION/DECOUPLAGE
    if (c / "data_lake").exists() or (c / "module_MCP_scraping").exists():  # # Marqueurs projet # # Étape: NORMALISATION/DECOUPLAGE
        PROJECT_ROOT = c  # # Fixe root # # Étape: NORMALISATION/DECOUPLAGE
        break  # # Stop # # Étape: NORMALISATION/DECOUPLAGE

if PROJECT_ROOT is None:  # # Si non trouvé # # Étape: NORMALISATION/DECOUPLAGE
    PROJECT_ROOT = _THIS_DIR  # # Fallback # # Étape: NORMALISATION/DECOUPLAGE

if str(PROJECT_ROOT) not in sys.path:  # # Si pas déjà dans sys.path # # Étape: NORMALISATION/DECOUPLAGE
    sys.path.insert(0, str(PROJECT_ROOT))  # # Ajoute au début # # Étape: NORMALISATION/DECOUPLAGE

# ===============================  # #
# 🕷️ Import du scraper (robuste)  # #
# ===============================  # #
# ⚠️ Ici, on importe la fonction attendue par l’API.
# Si ton module/nom diffère, adapte UNIQUEMENT la ligne import ci-dessous.
try:  # # Essai import # # Étape: ROBUSTESSE (erreur claire)
    from module_MCP_scraping.scrapping import scrape_arxiv_cs_scoped  # # Import scraper # # Étape: TOOL (scraping)
except Exception as e:  # # Si import échoue # # Étape: ROBUSTESSE
    scrape_arxiv_cs_scoped = None  # # Placeholder # # Étape: ROBUSTESSE
    _SCRAPER_IMPORT_ERROR = str(e)  # # Stocke erreur # # Étape: ROBUSTESSE

# ===============================  # #
# 🧠 FastAPI app                   # #
# ===============================  # #
app = FastAPI(  # # Crée l’app # # Étape: ORCHESTRATION
    title="DIXITBOT API",  # # Titre swagger # # Étape: ORCHESTRATION
    version="1.0.0",  # # Version # # Étape: ORCHESTRATION
)

# ===============================  # #
# 🧹 Helpers                       # #
# ===============================  # #
def _clean(s: str) -> str:  # # Nettoyage texte # # Étape: NORMALISATION/DECOUPLAGE (input stable)
    s = (s or "").strip()  # # Trim # # Étape: NORMALISATION/DECOUPLAGE
    s = re.sub(r"\s+", " ", s)  # # Espaces multiples -> 1 # # Étape: NORMALISATION/DECOUPLAGE
    return s  # # Retour # # Étape: NORMALISATION/DECOUPLAGE

def _ollama_generate(prompt: str, model: str) -> str:  # # Appel Ollama # # Étape: ORCHESTRATION (LLM)
    url = "http://localhost:11434/api/generate"  # # Endpoint Ollama # # Étape: ORCHESTRATION
    payload = {  # # JSON body # # Étape: NORMALISATION/DECOUPLAGE (contrat stable)
        "model": model,  # # Modèle # # Étape: ORCHESTRATION
        "prompt": prompt,  # # Prompt # # Étape: ORCHESTRATION
        "stream": False,  # # Sans streaming # # Étape: ORCHESTRATION
    }
    r = requests.post(url, json=payload, timeout=300)  # # POST # # Étape: ROBUSTESSE (timeout)
    r.raise_for_status()  # # Lève si erreur HTTP # # Étape: ROBUSTESSE
    data = r.json()  # # Parse JSON # # Étape: NORMALISATION/DECOUPLAGE
    return (data.get("response") or "").strip()  # # Retour texte # # Étape: NORMALISATION/DECOUPLAGE

def _build_context(items: List[Dict[str, Any]], max_chars: int = 14000) -> str:  # # Contexte compact # # Étape: STRUCTURATION (anti-hallucination)
    chunks: List[str] = []  # # Blocs # # Étape: STRUCTURATION
    total = 0  # # Compteur # # Étape: STRUCTURATION
    for i, it in enumerate(items, start=1):  # # Parcours # # Étape: STRUCTURATION
        block = (  # # Bloc papier # # Étape: STRUCTURATION
            f"[PAPER {i}]\n"
            f"arxiv_id: {_clean(it.get('arxiv_id',''))}\n"
            f"title: {_clean(it.get('title',''))}\n"
            f"submitted_date: {_clean(it.get('submitted_date',''))}\n"
            f"abs_url: {_clean(it.get('abs_url',''))}\n"
            f"pdf_url: {_clean(it.get('pdf_url',''))}\n"
            f"doi: {_clean(it.get('doi',''))}\n"
            f"abstract: {_clean(it.get('abstract',''))}\n"
        )
        if total + len(block) > max_chars:  # # Stop si trop long # # Étape: STRUCTURATION
            break  # # Sort # # Étape: STRUCTURATION
        chunks.append(block)  # # Ajout # # Étape: STRUCTURATION
        total += len(block)  # # Compte # # Étape: STRUCTURATION
    return "\n".join(chunks)  # # Retour # # Étape: STRUCTURATION

# ===============================  # #
# 0) Healthcheck                   # #
# ===============================  # #
@app.get("/health")  # # Endpoint health # # Étape: ORCHESTRATION
def health() -> Dict[str, Any]:  # # Handler # # Étape: ORCHESTRATION
    if scrape_arxiv_cs_scoped is None:  # # Si scraper non importé # # Étape: ROBUSTESSE
        return {  # # Retour # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False,  # # KO # # Étape: NORMALISATION/DECOUPLAGE
            "service": "api",  # # Service # # Étape: NORMALISATION/DECOUPLAGE
            "scraper_import_ok": False,  # # Flag # # Étape: NORMALISATION/DECOUPLAGE
            "scraper_error": _SCRAPER_IMPORT_ERROR,  # # Détail # # Étape: ROBUSTESSE
            "project_root": str(PROJECT_ROOT),  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
            "cwd": os.getcwd(),  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
        }
    return {  # # OK # # Étape: NORMALISATION/DECOUPLAGE
        "ok": True,  # # OK # # Étape: NORMALISATION/DECOUPLAGE
        "service": "api",  # # Service # # Étape: NORMALISATION/DECOUPLAGE
        "scraper_import_ok": True,  # # Flag # # Étape: NORMALISATION/DECOUPLAGE
        "project_root": str(PROJECT_ROOT),  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
        "cwd": os.getcwd(),  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
    }

# ===============================  # #
# 1) /scrape/arxiv                 # #
# ===============================  # #
class ArxivScrapeRequest(BaseModel):  # # Input scraping # # Étape: NORMALISATION/DECOUPLAGE (contrat d’entrée)
    query: str = Field(..., description="Texte de recherche (keywords)")  # # Query # # Étape: NORMALISATION/DECOUPLAGE
    theme: Optional[str] = Field(default=None, description="ai_ml|algo_ds|net_sys|cyber_crypto|pl_se|hci_data")  # # Theme # # Étape: NORMALISATION/DECOUPLAGE
    max_results: int = Field(default=20, ge=1, le=100)  # # Limite # # Étape: NORMALISATION/DECOUPLAGE
    sort: str = Field(default="relevance", description="relevance|submitted_date")  # # Tri # # Étape: NORMALISATION/DECOUPLAGE
    # ✅ CORRECTION: on retire debug_max_chars ici car le scraper ne l’accepte pas

@app.post("/scrape/arxiv")  # # Endpoint scrape # # Étape: ORCHESTRATION
def scrape_arxiv(req: ArxivScrapeRequest) -> Dict[str, Any]:  # # Handler # # Étape: ORCHESTRATION
    if scrape_arxiv_cs_scoped is None:  # # Si scraper indisponible # # Étape: ROBUSTESSE
        return {  # # Retour # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False,  # # KO # # Étape: NORMALISATION/DECOUPLAGE
            "errors": [f"SCRAPER_IMPORT_ERROR: {_SCRAPER_IMPORT_ERROR}"],  # # Liste erreurs # # Étape: NORMALISATION/DECOUPLAGE (contrat stable)
            "items": [],  # # Items vide # # Étape: NORMALISATION/DECOUPLAGE
        }

    try:  # # Try # # Étape: ROBUSTESSE
        # ✅ data_lake_raw_dir relatif => ton scraper le rend ABSOLU (et écrit dans le projet)
        result = scrape_arxiv_cs_scoped(  # # Appel tool # # Étape: TOOL (scraping)
            user_query=req.query,  # # Query # # Étape: TOOL
            theme=req.theme,  # # Theme # # Étape: TOOL
            max_results=req.max_results,  # # Limite # # Étape: TOOL
            sort=req.sort,  # # Tri # # Étape: TOOL
            data_lake_raw_dir="data_lake/raw/cache",  # # Cache raw # # Étape: NORMALISATION/DECOUPLAGE (sortie prévisible)
            enrich_abs=True,  # # Enrich /abs # # Étape: TOOL
            enable_keyword_filter=True,  # # Filtre fallback # # Étape: TOOL
            # ✅ CORRECTION: debug_max_chars supprimé (sinon "unexpected keyword argument")
        )
        return result  # # Retour direct (contrat tool) # # Étape: NORMALISATION/DECOUPLAGE
    except Exception as e:  # # Catch # # Étape: ROBUSTESSE
        return {  # # Retour erreur # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False,  # # KO # # Étape: NORMALISATION/DECOUPLAGE
            "errors": [f"SCRAPE_EXCEPTION: {str(e)}"],  # # Erreurs globales # # Étape: NORMALISATION/DECOUPLAGE
            "items": [],  # # Items vide # # Étape: NORMALISATION/DECOUPLAGE
        }

# ===============================  # #
# 2) /ask (scrape -> context -> LLM)# #
# ===============================  # #
class AskRequest(BaseModel):  # # Input ask # # Étape: NORMALISATION/DECOUPLAGE
    question: str = Field(..., description="Question utilisateur")  # # Question # # Étape: NORMALISATION/DECOUPLAGE
    theme: Optional[str] = Field(default="ai_ml", description="Thème arXiv CS")  # # Theme # # Étape: NORMALISATION/DECOUPLAGE
    max_results: int = Field(default=3, ge=1, le=10)  # # Papiers # # Étape: NORMALISATION/DECOUPLAGE
    sort: str = Field(default="relevance", description="relevance|submitted_date")  # # Tri # # Étape: NORMALISATION/DECOUPLAGE
    model: str = Field(default="qwen3:1.7b", description="Modèle Ollama")  # # Model # # Étape: NORMALISATION/DECOUPLAGE
    debug: bool = Field(default=False, description="Renvoie infos debug")  # # Debug # # Étape: NORMALISATION/DECOUPLAGE

@app.post("/ask")  # # Endpoint QA # # Étape: ORCHESTRATION
def ask(req: AskRequest) -> Dict[str, Any]:  # # Handler # # Étape: ORCHESTRATION
    if scrape_arxiv_cs_scoped is None:  # # Si scraper indispo # # Étape: ROBUSTESSE
        return {  # # Retour # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False,  # # KO # # Étape: NORMALISATION/DECOUPLAGE
            "errors": [f"SCRAPER_IMPORT_ERROR: {_SCRAPER_IMPORT_ERROR}"],  # # Erreurs # # Étape: NORMALISATION/DECOUPLAGE
            "items": [],  # # Items # # Étape: NORMALISATION/DECOUPLAGE
        }

    question = _clean(req.question)  # # Nettoie # # Étape: NORMALISATION/DECOUPLAGE
    if not question:  # # Vide # # Étape: NORMALISATION/DECOUPLAGE
        return {"ok": False, "errors": ["EMPTY_QUESTION"], "items": []}  # # Contrat stable # # Étape: NORMALISATION/DECOUPLAGE

    # 1) Scraping
    try:  # # Try # # Étape: ROBUSTESSE
        results = scrape_arxiv_cs_scoped(  # # Tool # # Étape: TOOL
            user_query=question,  # # Query # # Étape: TOOL
            theme=req.theme,  # # Theme # # Étape: TOOL
            max_results=req.max_results,  # # Limite # # Étape: TOOL
            sort=req.sort,  # # Tri # # Étape: TOOL
            data_lake_raw_dir="data_lake/raw/cache",  # # Cache # # Étape: NORMALISATION/DECOUPLAGE
            enrich_abs=True,  # # Enrich # # Étape: TOOL
            enable_keyword_filter=True,  # # Filtre # # Étape: TOOL
            # ✅ CORRECTION: debug_max_chars supprimé
        )
    except Exception as e:  # # Catch # # Étape: ROBUSTESSE
        return {"ok": False, "errors": [f"SCRAPE_EXCEPTION: {str(e)}"], "items": []}  # # Contrat stable # # Étape: NORMALISATION/DECOUPLAGE

    items = results.get("items") or []  # # Items # # Étape: NORMALISATION/DECOUPLAGE
    errors_global = results.get("errors") or []  # # Erreurs tool # # Étape: NORMALISATION/DECOUPLAGE

    if not items:  # # Si rien # # Étape: ROBUSTESSE
        out = {  # # Sortie stable # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False if errors_global else True,  # # KO si erreurs tool # # Étape: NORMALISATION/DECOUPLAGE
            "question": question,  # # Echo # # Étape: NORMALISATION/DECOUPLAGE
            "answer": "Aucun papier trouvé (ou parsing impossible). Regarde le bundle HTML.",  # # Message # # Étape: NORMALISATION/DECOUPLAGE
            "items": [],  # # Items vide # # Étape: NORMALISATION/DECOUPLAGE
            "errors": errors_global,  # # Erreurs globales # # Étape: NORMALISATION/DECOUPLAGE
        }
        if req.debug:  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
            out["debug"] = {  # # Bloc debug # # Étape: NORMALISATION/DECOUPLAGE
                "saved_to": results.get("saved_to"),  # # JSON # # Étape: NORMALISATION/DECOUPLAGE
                "bundle_html_file": results.get("bundle_html_file"),  # # HTML # # Étape: NORMALISATION/DECOUPLAGE
                "last_search_http": results.get("last_search_http"),  # # HTTP # # Étape: NORMALISATION/DECOUPLAGE
                "last_search_url": results.get("last_search_url"),  # # URL # # Étape: NORMALISATION/DECOUPLAGE
                "raw_cache_dir": results.get("raw_cache_dir"),  # # Dir # # Étape: NORMALISATION/DECOUPLAGE
            }
        return out  # # Retour # # Étape: NORMALISATION/DECOUPLAGE

    # 2) Context compact (anti-hallucination)
    context = _build_context(items, max_chars=14000)  # # Build context # # Étape: STRUCTURATION

    # 3) Prompt strict
    prompt = (  # # Prompt # # Étape: STRUCTURATION (contraintes)
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

    # 4) LLM
    try:  # # Try # # Étape: ROBUSTESSE
        answer = _ollama_generate(prompt=prompt, model=req.model)  # # Ollama # # Étape: ORCHESTRATION
    except Exception as e:  # # Catch # # Étape: ROBUSTESSE
        return {  # # Retour # # Étape: NORMALISATION/DECOUPLAGE
            "ok": False,  # # KO # # Étape: NORMALISATION/DECOUPLAGE
            "question": question,  # # Echo # # Étape: NORMALISATION/DECOUPLAGE
            "items": [],  # # Items # # Étape: NORMALISATION/DECOUPLAGE
            "errors": errors_global + [f"OLLAMA_EXCEPTION: {str(e)}"],  # # Erreurs # # Étape: NORMALISATION/DECOUPLAGE
        }

    # 5) Réponse API
    items_min = [  # # Simplifié # # Étape: NORMALISATION/DECOUPLAGE
        {"arxiv_id": it.get("arxiv_id", ""), "title": it.get("title", ""), "abs_url": it.get("abs_url", "")}  # # Champs # # Étape: NORMALISATION/DECOUPLAGE
        for it in items  # # Loop # # Étape: NORMALISATION/DECOUPLAGE
    ]

    out = {  # # Sortie # # Étape: NORMALISATION/DECOUPLAGE
        "ok": True,  # # OK # # Étape: NORMALISATION/DECOUPLAGE
        "question": question,  # # Echo # # Étape: NORMALISATION/DECOUPLAGE
        "theme": req.theme,  # # Theme # # Étape: NORMALISATION/DECOUPLAGE
        "query_used": results.get("query_used") or results.get("user_query") or question,  # # Trace # # Étape: NORMALISATION/DECOUPLAGE
        "count": len(items_min),  # # Count # # Étape: NORMALISATION/DECOUPLAGE
        "answer": answer,  # # Answer # # Étape: NORMALISATION/DECOUPLAGE
        "items": items_min,  # # Items # # Étape: NORMALISATION/DECOUPLAGE
        "errors": errors_global,  # # Erreurs tool (si warnings) # # Étape: NORMALISATION/DECOUPLAGE
    }

    if req.debug:  # # Debug # # Étape: NORMALISATION/DECOUPLAGE
        out["debug"] = {  # # Bloc # # Étape: NORMALISATION/DECOUPLAGE
            "saved_to": results.get("saved_to"),  # # JSON # # Étape: NORMALISATION/DECOUPLAGE
            "bundle_html_file": results.get("bundle_html_file"),  # # HTML # # Étape: NORMALISATION/DECOUPLAGE
            "last_search_http": results.get("last_search_http"),  # # HTTP # # Étape: NORMALISATION/DECOUPLAGE
            "last_search_url": results.get("last_search_url"),  # # URL # # Étape: NORMALISATION/DECOUPLAGE
            "raw_cache_dir": results.get("raw_cache_dir"),  # # Dir # # Étape: NORMALISATION/DECOUPLAGE
            "project_root": str(PROJECT_ROOT),  # # Root # # Étape: NORMALISATION/DECOUPLAGE
            "cwd": os.getcwd(),  # # CWD # # Étape: NORMALISATION/DECOUPLAGE
        }

    return out  # # Retour # # Étape: NORMALISATION/DECOUPLAGE

# ==========================
# End scrapping main
# ==========================
