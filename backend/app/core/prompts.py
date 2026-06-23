from typing import Optional


SYSTEM_PROMPT = """Tu es DIXITBOT, un assistant de revue de littérature scientifique (informatique).
Tu réponds en français, de manière structurée, claire, et tu cites les sources quand elles sont fournies.
Si tu n'as pas assez d'informations, tu le dis et tu proposes une prochaine étape (requête, mots-clés).
"""


def build_user_prompt(question: str, kb_context: Optional[str] = None) -> str:
    """
    Construit le prompt utilisateur en injectant le contexte KB (si disponible).
    kb_context = texte brut (ex: extraits d'articles, résumés, JSON "aplati", etc.)
    """
    question = question.strip()

    if kb_context and kb_context.strip():
        return f"""Voici du contexte (KB) à utiliser :

--- CONTEXTE KB ---
{kb_context.strip()}
--- FIN CONTEXTE ---

Question :
{question}

Consignes :
- Utilise le contexte KB en priorité
- Réponds avec des sections (Résumé, Points clés, Limites, Pistes)
- Si le contexte ne permet pas de répondre, dis-le clairement
"""
    return f"""Question :
{question}

Consignes :
- Réponds avec des sections (Résumé, Points clés, Limites, Pistes)
- Si tu manques d'info, propose des mots-clés de recherche
"""
