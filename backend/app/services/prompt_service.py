from __future__ import annotations

from typing import Any, Dict, List


def build_kb_context(results: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    chunks: List[str] = []
    total = 0
    for i, r in enumerate(results, start=1):
        block = (
            f"[KB {i}] id={r.get('id','')}\n"
            f"score={r.get('score','')}\n"
            f"text:\n{(r.get('text','') or '').strip()}\n"
        )
        if total + len(block) > max_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks)


def build_arxiv_context(items: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    chunks: List[str] = []
    total = 0
    for i, it in enumerate(items, start=1):
        block = (
            f"[PAPER {i}]\n"
            f"arxiv_id: {it.get('arxiv_id','')}\n"
            f"title: {it.get('title','')}\n"
            f"submitted_date: {it.get('submitted_date','')}\n"
            f"abs_url: {it.get('abs_url','')}\n"
            f"pdf_url: {it.get('pdf_url','')}\n"
            f"abstract: {it.get('abstract','')}\n"
        )
        if total + len(block) > max_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks)


def build_strict_prompt(question: str, context: str) -> str:
    return (
        "Tu es un assistant de recherche.\n"
        "Tu dois répondre UNIQUEMENT à partir du CONTEXTE fourni.\n"
        "Si une info n'est pas dans le contexte, dis: \"Je ne peux pas l'affirmer avec ce contexte\".\n"
        "\n"
        "Format demandé:\n"
        "1) Réponse courte (3-6 lignes)\n"
        "2) Points clés (5 bullets)\n"
        "3) Sources (liste courte)\n"
        "\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXTE:\n{context}\n"
    )
