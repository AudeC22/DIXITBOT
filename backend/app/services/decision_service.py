from typing import Any, Dict, List


def should_scrape_arxiv(kb_results: List[Dict[str, Any]], min_relevant_count: int = 2) -> bool:
    """Returns True if KB results are insufficient and arXiv scrape is needed."""
    return len(kb_results) < min_relevant_count
