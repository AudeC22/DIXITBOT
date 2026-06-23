from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.kb_service import search_kb  # Remplacez par import absolu si nécessaire
from app.services.scrape_service import scrape_arxiv
from app.services.prompt_service import build_kb_context, build_arxiv_context, build_strict_prompt
from app.services.llm_service import ollama_generate

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., description="Question utilisateur")
    theme: Optional[str] = Field(default=None, description="Thème arXiv (optionnel)")
    kb_source: str = Field(default="kb.json", description="Fichier KB dans data_lake/KB")
    kb_top_k: int = Field(default=5, ge=1, le=20)
    kb_min_score: float = Field(default=0.12, ge=0.0, le=1.0)

    scrape_max_results: int = Field(default=8, ge=1, le=30)
    scrape_sort: str = Field(default="relevance", description="relevance|submitted_date")

    model: str = Field(default="qwen3:1.7b", description="Modèle Ollama")
    debug: bool = Field(default=False, description="Retourne infos debug")


@router.post("/ask")
def ask(req: AskRequest) -> Dict[str, Any]:
    # Version simplifiée sans IA
    return {
        "ok": True,
        "decision": "simplified",
        "question": req.question,
        "answer": "Réponse simplifiée : installe Ollama et un modèle pour activer l'IA.",
        "sources": []
    }
