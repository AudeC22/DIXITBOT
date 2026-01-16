import os
import time
import requests
from typing import Dict, Any, List

# =========================
# CONFIGURATION
# =========================

SEMANTIC_BASE = "https://api.semanticscholar.org/graph/v1"

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "SEMANTIC_SCHOLAR_API_KEY is not set. "
        "Export it with: export SEMANTIC_SCHOLAR_API_KEY='your_key_here'"
    )

HEADERS = {
    "x-api-key": API_KEY
}

# =========================
# CORE FUNCTION
# =========================

def search_papers(
    query: str,
    year_from: int = 2020,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search papers using Semantic Scholar bulk search API.

    Args:
        query (str): Search query (keywords)
        year_from (int): Minimum publication year
        limit (int): Max number of papers to return (<= 100 recommended)

    Returns:
        Dict with:
            - ok (bool)
            - total (int)
            - papers (List[Dict])
            - error (optional)
    """

    url = f"{SEMANTIC_BASE}/paper/search/bulk"

    params = {
        "query": query,
        "fields": (
            "paperId,"
            "title,"
            "abstract,"
            "publicationDate,"
            "citationCount,"
            "authors,"
            "url,"
            "openAccessPdf"
        ),
        "year": f"{year_from}-",
        "limit": limit
    }

    response = requests.get(url, params=params, headers=HEADERS)

    if response.status_code != 200:
        return {
            "ok": False,
            "status_code": response.status_code,
            "error": response.text
        }

    data = response.json()

    return {
        "ok": True,
        "total": data.get("total", 0),
        "papers": data.get("data", [])
    }

# =========================
# LOCAL TEST
# =========================

if __name__ == "__main__":
    print("🔎 Testing Semantic Scholar API...\n")

    result = search_papers(
        query="machine learning",
        year_from=2020,
        limit=5
    )

    print("OK:", result["ok"])
    print("Total found:", result.get("total"))
    print("Returned:", len(result.get("papers", [])))

    for paper in result.get("papers", []):
        print("\n" + "-" * 60)
        print("Title:", paper.get("title"))
        print("Date:", paper.get("publicationDate"))
        print("Citations:", paper.get("citationCount"))

        authors = paper.get("authors", [])
        if authors:
            print("Authors:", ", ".join(a["name"] for a in authors[:3]))

        pdf = paper.get("openAccessPdf")
        if pdf and pdf.get("url"):
            print("PDF:", pdf["url"])
