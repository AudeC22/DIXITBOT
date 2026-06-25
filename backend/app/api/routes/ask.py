import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.ollama_client import OllamaClient
from app.integrations import mcp
from app.services.kb_service import search_kb
from app.services.decision_service import should_scrape_arxiv
from app.services.prompt_service import (
    build_kb_context,
    build_arxiv_context,
    build_strict_prompt,
    normalize_sources,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(..., description="Question utilisateur")
    theme: Optional[str] = Field(default=None, description="Thème arXiv (optionnel)")
    kb_top_k: int = Field(default=5, ge=1, le=20)
    kb_min_score: float = Field(default=0.12, ge=0.0, le=1.0)

    scrape_max_results: int = Field(default=8, ge=1, le=30)
    scrape_sort: str = Field(default="relevance", description="relevance|submitted_date")

    model: str = Field(default="qwen3:1.7b", description="Modèle Ollama")
    debug: bool = Field(default=False, description="Retourne infos debug")


@router.post("/ask")
def ask(req: AskRequest) -> Dict[str, Any]:
    try:
        kb_response = search_kb(req.question, req.kb_top_k, req.kb_min_score)
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        raise HTTPException(503, f"Service KB indisponible: {e}")

    if not kb_response.get("ok", False):
        logger.error(f"KB search returned an error: {kb_response.get('errors')}")
        raise HTTPException(503, f"Service KB indisponible: {kb_response.get('errors')}")

    kb_results = kb_response.get("results", [])
    used_arxiv = should_scrape_arxiv(kb_results)

    arxiv_items: List[Dict[str, Any]] = []
    if used_arxiv:
        tool_response = mcp.run_tool("arxiv_metadata", {
            "query": req.question,
            "theme": req.theme,
            "max_results": req.scrape_max_results,
            "sort": req.scrape_sort
        })
        if not tool_response.ok:
            logger.error(f"arXiv tool returned an error: {tool_response.errors}")
            raise HTTPException(503, f"Service arXiv indisponible: {tool_response.errors}")
        arxiv_items = [item.dict() for item in tool_response.items]

    context = build_kb_context(kb_results)
    if arxiv_items:
        context += "\n\n" + build_arxiv_context(arxiv_items)

    prompt = build_strict_prompt(req.question, context)

    try:
        client = OllamaClient()
        answer = client.generate(prompt, model=req.model)
    except Exception as e:
        logger.error(f"Ollama generate failed: {e}")
        raise HTTPException(503, f"Service Ollama indisponible: {e}")

    sources = normalize_sources(kb_results, arxiv_items)

    return {
        "ok": True,
        "answer": answer,
        "used_arxiv": used_arxiv,
        "sources": sources,
        "kb_hits": len(kb_results),
        "arxiv_hits": len(arxiv_items),
    }
