from typing import Any, Dict, List, Optional
import json
from pathlib import Path

def _kb_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data_lake" / "kb.json"

def search_kb(query: str, top_k: int = 5, min_score: float = 0.1, source: str = "kb.json") -> Dict[str, Any]:
    """
    Simule une recherche dans kb.json.
    En vrai, utilise un embedding ou un index (ex: FAISS, ChromaDB).
    Ici, recherche simple par mots-clés.
    """
    kb_file = _kb_path()
    if not kb_file.exists():
        return {"ok": False, "errors": ["KB_FILE_NOT_FOUND"], "results": []}

    try:
        with open(kb_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"ok": False, "errors": [f"KB_LOAD_ERROR: {str(e)}"], "results": []}

    # Simule une recherche : filtre par query dans title ou abstract
    results = []
    query_lower = query.lower()
    for item in data.get("items", []):
        title = (item.get("title") or "").lower()
        abstract = (item.get("abstract") or "").lower()
        if query_lower in title or query_lower in abstract:
            score = 0.8  # Score fictif
            text = f"Title: {item.get('title')}\nAbstract: {item.get('abstract')}"
            if score >= min_score:
                results.append({"id": item.get("id"), "text": text, "score": score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
    return {"ok": True, "results": results}