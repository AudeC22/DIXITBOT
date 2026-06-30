from typing import Any, Dict, List


def should_scrape_arxiv(kb_results: List[Dict[str, Any]], min_relevant_count: int = 2) -> bool:
    """Returns True if KB results are insufficient and arXiv scrape is needed."""
    return len(kb_results) < min_relevant_count


def classify_intent(client, question: str) -> str:
    system_prompt = (
        "Classify the user's question as exactly one of: social, metier. "
        "Reply with a single word: social or metier."
    )
    response = client.generate(
        question,
        system=system_prompt,
        temperature=0.0,
        num_predict=5,
    )
    return "social" if "social" in response.lower() else "metier"
