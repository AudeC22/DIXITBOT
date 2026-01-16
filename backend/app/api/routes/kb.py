from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

# sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter()

# Dossier KB : backend/data_lake/KB/
KB_DIR = Path(__file__).resolve().parents[3] / "data_lake" / "KB"

# Index en mémoire (chargé au démarrage / à la première requête)
_VECTORIZER: Optional[TfidfVectorizer] = None
_DOCS: List[Dict[str, Any]] = []  # [{"id":..., "text":..., "meta":...}, ...]
_TFIDF_MATRIX = None  # sparse matrix
_CURRENT_SOURCE: Optional[str] = None  # pour éviter de réindexer si source identique


# ---------------------------
# Utils: flatten JSON -> docs
# ---------------------------
def _is_primitive(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None


def _normalize_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def _make_doc(doc_id: str, title: str, body: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    title = _normalize_text(title)
    body = _normalize_text(body)
    text = f"{title}\n{body}".strip() if title else body
    return {"id": doc_id, "text": text, "meta": meta}


def _extract_docs_from_json(data: Any) -> List[Dict[str, Any]]:
    """
    Transforme ton JSON imbriqué en "docs" textuels indexables.
    On crée des docs pour les objets qui ont (label/description/keywords/examples).
    """
    docs: List[Dict[str, Any]] = []

    def walk(node: Any, path: List[str]) -> None:
        # Liste
        if isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, path + [f"[{i}]"])
            return

        # Dict
        if isinstance(node, dict):
            keys = set(node.keys())

            # Id candidates
            doc_key = None
            for k in ["concept_id", "theme_id", "step_id", "id", "name", "label_en", "label_fr"]:
                if k in node and isinstance(node[k], str) and node[k].strip():
                    doc_key = node[k].strip()
                    break

            # Title candidates
            title_parts: List[str] = []
            for k in ["label_fr", "label_en", "role", "name"]:
                if k in node and isinstance(node[k], str) and node[k].strip():
                    title_parts.append(node[k].strip())

            # Body candidates (strings)
            body_parts: List[str] = []
            for k in ["description", "description_fr", "description_en", "tone", "scope"]:
                if k in node and isinstance(node[k], str) and node[k].strip():
                    body_parts.append(node[k].strip())

            # Lists of strings
            for k in [
                "keywords_seed_en",
                "subtopics_seed_en",
                "example_questions_fr",
                "behavior",
                "capabilities",
                "objectifs",
                "target_users",
                "sujets_autorises",
                "sujets_interdits",
                "intentions_exemples",
            ]:
                if k in node and isinstance(node[k], list):
                    vals = [str(x).strip() for x in node[k] if _is_primitive(x) and str(x).strip()]
                    if vals:
                        body_parts.append(f"{k}: " + " | ".join(vals))

            title = " — ".join(title_parts).strip()
            body = "\n".join(body_parts).strip()

            # Critères pour créer un doc
            if (title or body) and (
                ("description" in keys)
                or ("description_fr" in keys)
                or ("theme_id" in keys)
                or ("concept_id" in keys)
                or ("step_id" in keys)
                or ("agent_persona" in keys)
                or ("research_methodology" in keys)
            ):
                doc_id = doc_key or "/".join(path) or "root"
                meta = {
                    "path": "/".join(path) if path else "root",
                    "keys": sorted(list(keys)),
                }
                docs.append(_make_doc(doc_id=str(doc_id), title=title, body=body, meta=meta))

            # Continue de parcourir
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    walk(v, path + [k])
            return

        # Primitive: rien
        return

    walk(data, [])
    docs = [d for d in docs if d["text"].strip()]
    return docs


def _get_kb_path(source: str) -> Path:
    # Sécurité minimale: empêche ../
    safe_name = Path(source).name
    return KB_DIR / safe_name


def _build_index(kb_path: Path, source: str) -> None:
    global _VECTORIZER, _DOCS, _TFIDF_MATRIX, _CURRENT_SOURCE

    if not kb_path.exists():
        _VECTORIZER = None
        _DOCS = []
        _TFIDF_MATRIX = None
        _CURRENT_SOURCE = source
        return

    data = json.loads(kb_path.read_text(encoding="utf-8"))
    docs = _extract_docs_from_json(data)

    if not docs:
        _VECTORIZER = None
        _DOCS = []
        _TFIDF_MATRIX = None
        _CURRENT_SOURCE = source
        return

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words=None,  # FR/EN mix, donc None
        ngram_range=(1, 2),
        max_features=50000,
    )

    texts = [d["text"] for d in docs]
    matrix = vectorizer.fit_transform(texts)

    _VECTORIZER = vectorizer
    _DOCS = docs
    _TFIDF_MATRIX = matrix
    _CURRENT_SOURCE = source


def _ensure_index(source: str) -> Path:
    kb_path = _get_kb_path(source)

    # Rebuild si:
    # - pas d'index
    # - source a changé
    if _VECTORIZER is None or _TFIDF_MATRIX is None or not _DOCS or (_CURRENT_SOURCE != source):
        _build_index(kb_path, source)

    return kb_path


# ---------------------------
# API schemas
# ---------------------------
class KBQuery(BaseModel):
    query: str = Field(..., description="Texte de recherche")
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.10, ge=0.0, le=1.0)
    source: str = Field(default="knowledge_base.json", description="Nom du fichier KB dans data_lake/KB")


# ---------------------------
# Routes
# ---------------------------
@router.get("/status")
def kb_status(source: str = "knowledge_base.json") -> Dict[str, Any]:
    kb_path = _ensure_index(source)
    return {
        "ok": True,
        "kb_dir": str(KB_DIR),
        "kb_path": str(kb_path),
        "kb_exists": kb_path.exists(),
        "docs_count": len(_DOCS),
        "indexed": _VECTORIZER is not None and _TFIDF_MATRIX is not None,
        "source": source,
    }


@router.post("/search")
def kb_search(payload: KBQuery) -> Dict[str, Any]:
    kb_path = _ensure_index(payload.source)

    if _VECTORIZER is None or _TFIDF_MATRIX is None or not _DOCS:
        return {
            "ok": False,
            "query": payload.query,
            "error": "KB_NOT_INDEXED",
            "kb_path": str(kb_path),
            "results": [],
            "fallback_required": True,
        }

    q = _normalize_text(payload.query)
    if not q:
        return {"ok": False, "query": payload.query, "error": "EMPTY_QUERY", "results": [], "fallback_required": True}

    q_vec = _VECTORIZER.transform([q])
    sims = cosine_similarity(q_vec, _TFIDF_MATRIX).ravel()

    ranked_idx = sims.argsort()[::-1]
    results: List[Dict[str, Any]] = []

    for idx in ranked_idx[: payload.top_k]:
        score = float(sims[idx])
        if score < payload.min_score:
            continue

        doc = _DOCS[idx]
        results.append(
            {
                "id": doc["id"],
                "score": round(score, 4),
                "text": doc["text"][:1200],  # évite une réponse énorme
                "meta": doc["meta"],
            }
        )

    best_score = float(sims[ranked_idx[0]]) if len(ranked_idx) else 0.0

    return {
        "ok": True,
        "query": q,
        "top_k": payload.top_k,
        "min_score": payload.min_score,
        "best_score": round(best_score, 4),
        "kb_path": str(kb_path),
        "fallback_required": len(results) == 0,
        "results": results,
    }
