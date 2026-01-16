from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.kb_service import search_kb
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
    question = (req.question or "").strip()
    if not question:
        return {"ok": False, "errors": ["EMPTY_QUESTION"], "answer": "", "sources": []}

    # 1) Try KB first
    kb = search_kb(
        query=question,
        top_k=req.kb_top_k,
        min_score=req.kb_min_score,
        source=req.kb_source,
    )

    kb_results: List[Dict[str, Any]] = kb.get("results") or []
    use_kb = bool(kb.get("ok")) and len(kb_results) > 0

    decision = "kb_used" if use_kb else "scrape_used"

    # 2) If KB not enough -> scrape arXiv
    scrape_payload: Dict[str, Any] = {"ok": True, "items": []}
    if not use_kb:
        scrape_payload = scrape_arxiv(
            query=question,
            theme=req.theme,
            max_results=req.scrape_max_results,
            sort=req.scrape_sort,
        )

    # 3) Build context
    if use_kb:
        context = build_kb_context(kb_results, max_chars=12000)
        sources = [{"type": "kb", "id": r.get("id"), "score": r.get("score")} for r in kb_results]
    else:
        items = scrape_payload.get("items") or []
        context = build_arxiv_context(items, max_chars=12000)
        sources = [{"type": "arxiv", "arxiv_id": it.get("arxiv_id"), "title": it.get("title"), "abs_url": it.get("abs_url")} for it in items]

    if not context.strip():
        # rien à donner au LLM
        return {
            "ok": False,
            "errors": ["NO_CONTEXT_AVAILABLE"],
            "decision": decision,
            "answer": "Je n'ai pas assez de contexte pour répondre.",
            "sources": sources,
            "kb": kb if req.debug else None,
            "scrape": scrape_payload if req.debug else None,
        }

    prompt = build_strict_prompt(question, context)

    # 4) LLM (Ollama)
    try:
        answer = ollama_generate(prompt=prompt, model=req.model, timeout_s=240)
    except Exception as e:
        return {
            "ok": False,
            "errors": [f"OLLAMA_ERROR: {str(e)}"],
            "decision": decision,
            "answer": "",
            "sources": sources,
            "kb": kb if req.debug else None,
            "scrape": scrape_payload if req.debug else None,
        }

    out: Dict[str, Any] = {
        "ok": True,
        "decision": decision,
        "question": question,
        "answer": answer,
        "sources": sources,
    }

    if req.debug:
        out["debug"] = {
            "kb": kb,
            "scrape": scrape_payload,
            "prompt_chars": len(prompt),
        }

    return out
