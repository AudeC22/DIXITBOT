from typing import List


def build_kb_context(snippets: List[str], max_chars: int = 6000) -> str:
    """
    Transforme une liste d'extraits (snippets) en un contexte texte compact.
    Tu brancheras ici ce que tu récupères de ton KB (json, fichiers, etc.)
    """
    cleaned = [s.strip() for s in snippets if s and s.strip()]
    if not cleaned:
        return ""

    out_parts = []
    total = 0
    for i, s in enumerate(cleaned, start=1):
        chunk = f"[KB#{i}] {s}\n"
        if total + len(chunk) > max_chars:
            break
        out_parts.append(chunk)
        total += len(chunk)

    return "\n".join(out_parts).strip()
