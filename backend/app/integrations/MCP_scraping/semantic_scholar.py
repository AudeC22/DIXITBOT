import os
import time
import requests
from typing import Dict, Any, List

# =========================
# CONFIGURATION
# =========================

SEMANTIC_BASE = "https://api.semanticscholar.org/graph/v1"

# --- Rate limit: 1 request / second (global)
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
_last_call_ts = 0.0


def _rate_limit_sleep() -> None:
    """Ensure at most 1 request per second (global, cumulative)."""
    global _last_call_ts
    now = time.monotonic()
    elapsed = now - _last_call_ts
    wait = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


def _load_dotenv_if_exists(path: str = ".env") -> None:
    """
    Minimal .env loader (no dependency).
    Format:
        SEMANTIC_SCHOLAR_API_KEY=xxxxx
    """
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# Load .env if present (Windows + Mac)
_load_dotenv_if_exists()

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# Only send header if key exists
HEADERS = {"x-api-key": API_KEY} if API_KEY else {}

# =========================
# CORE FUNCTION
# =========================

def search_papers(
    query: str,
    year_from: int = 2020,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search papers using Semantic Scholar search API.
    Rate-limited to 1 request/second.
    """

    url = f"{SEMANTIC_BASE}/paper/search"

    params = {
        "query": f"{query} year:{year_from}-",
        "fields": (
            "paperId,"
            "title,"
            "abstract,"
            "year,"
            "citationCount,"
            "authors,"
            "url,"
            "openAccessPdf"
        ),
        "limit": limit
    }

    # --- Rate limit enforcement
    _rate_limit_sleep()
    response = requests.get(url, params=params, headers=HEADERS)

    # --- Handle rate limit (429)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        sleep_s = float(retry_after) if retry_after and retry_after.isdigit() else 1.0
        time.sleep(sleep_s)
        _rate_limit_sleep()
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
    print("API key loaded:", bool(API_KEY))

    result = search_papers(
        query="machine learning",
        year_from=2020,
        limit=5
    )

    if not result.get("ok"):
        print("\n❌ Request failed")
        print("Status code:", result.get("status_code"))
        print("Error:", result.get("error"))
        raise SystemExit(1)

    print("\n✅ Request OK")
    print("Total found:", result.get("total"))
    print("Returned:", len(result.get("papers", [])))

    for paper in result.get("papers", []):
        print("\n" + "-" * 60)
        print("Title:", paper.get("title"))
        print("Year:", paper.get("year"))
        print("Citations:", paper.get("citationCount"))

        authors = paper.get("authors", [])
        if authors:
            print("Authors:", ", ".join(a["name"] for a in authors[:3]))

        pdf = paper.get("openAccessPdf")
        if pdf and pdf.get("url"):
            print("PDF:", pdf["url"])
