from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.scrape_service import scrape_arxiv

router = APIRouter()


class ArxivScrapeRequest(BaseModel):
    query: str = Field(..., description="Texte de recherche (keywords)")
    theme: Optional[str] = Field(default=None, description="ai_ml|algorithms_data_structures|networks_systems|cybersecurity_cryptography|programming_software_engineering|human_data_interaction")
    max_results: int = Field(default=10, ge=1, le=50)
    sort: str = Field(default="relevance", description="relevance|submitted_date")


@router.post("/arxiv")
def scrape_arxiv_route(req: ArxivScrapeRequest) -> Dict[str, Any]:
    sort = "relevance" if req.sort == "relevance" else "submitted_date"
    return scrape_arxiv(query=req.query, theme=req.theme, max_results=req.max_results, sort=sort)
