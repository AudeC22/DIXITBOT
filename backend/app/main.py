#==============================================
# Utile pour le scrapping --> appel du script
#==============================================
from fastapi import FastAPI  # # 🚀 FastAPI
from pydantic import BaseModel  # # 🧾 Validation payload
from scraping.scrapping import scrape_arxiv_cs  # # 🕷️ Import de ton scraper

app = FastAPI()  # # 🧠 API

class ArxivScrapeRequest(BaseModel):  # # 🧾 Schéma de requête
    query: str  # # 🔎 Mots-clés
    max_results: int = 50  # # 🎯 Limite (capée à 100)
    sort: str = "relevance"  # # 🧭 relevance | submitted_date | last_updated_date
    subcategory: str | None = None  # # 🧩 Ex cs.LG

@app.post("/scrape/arxiv")  # # 🛣️ Endpoint demandé
def scrape_arxiv(req: ArxivScrapeRequest):  # # 🎯 Handler
    try:  # # 🧯 Protection
        return scrape_arxiv_cs(  # # 🚀 Appel scraper
            query=req.query,  # # 🔎
            max_results=req.max_results,  # # 🎯
            sort=req.sort,  # # 🧭
            subcategory=req.subcategory,  # # 🧩
            polite_min_s=1.5,  # # 😇
            polite_max_s=2.0,  # # 😇
            data_lake_raw_dir="data_lake/raw",  # # 💾
        )  # # ✅ Fin appel
    except Exception as e:  # # ❌ Si crash
        return {"ok": False, "error": str(e)}  # # 🧾 Erreur structurée
#==============================================
# End util pour le script scrapping
#==============================================