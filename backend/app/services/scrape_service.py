from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.parse
import xml.etree.ElementTree as ET

import requests


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _raw_cache_dir() -> Path:
    p = _backend_dir() / "data_lake" / "raw" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


_THEME_TO_ARXIV_CAT = {
    "ai_ml": "cs.AI",
    "algorithms_data_structures": "cs.DS",
    "networks_systems": "cs.NI",
    "cybersecurity_cryptography": "cs.CR",
    "programming_software_engineering": "cs.SE",
    "human_data_interaction": "cs.HC",
}


def _clean(s: Optional[str]) -> str:
    return " ".join((s or "").strip().split())


def scrape_arxiv(
    query: str,
    theme: Optional[str] = None,
    max_results: int = 10,
    sort: str = "relevance",
) -> Dict[str, Any]:
    """
    Scrape via arXiv API: http://export.arxiv.org/api/query
    """
    q = _clean(query)
    if not q:
        return {"ok": False, "errors": ["EMPTY_QUERY"], "items": []}

    cat = _THEME_TO_ARXIV_CAT.get(theme or "", None)

    # arXiv API query format:
    # search_query=all:<terms> AND cat:cs.AI
    parts = [f'all:{urllib.parse.quote(q)}']
    if cat:
        parts.append(f"cat:{cat}")
    search_query = "+AND+".join(parts)

    order_by = "relevance" if sort == "relevance" else "submittedDate"
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query={search_query}"
        f"&start=0&max_results={max_results}"
        f"&sortBy={order_by}&sortOrder=descending"
    )

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return {"ok": False, "errors": [f"ARXIV_HTTP_ERROR: {str(e)}"], "items": [], "last_search_url": url}

    # parse atom xml
    try:
        root = ET.fromstring(r.text)
    except Exception as e:
        return {"ok": False, "errors": [f"ARXIV_XML_PARSE_ERROR: {str(e)}"], "items": [], "last_search_url": url}

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        arxiv_id = _clean(entry.findtext("atom:id", default="", namespaces=ns)).split("/")[-1]
        title = _clean(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = _clean(entry.findtext("atom:summary", default="", namespaces=ns))
        published = _clean(entry.findtext("atom:published", default="", namespaces=ns))

        abs_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            rel = link.attrib.get("rel", "")
            href = link.attrib.get("href", "")
            typ = link.attrib.get("type", "")
            if rel == "alternate" and href:
                abs_url = href
            if typ == "application/pdf" and href:
                pdf_url = href

        items.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "submitted_date": published,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "abstract": abstract,
                "theme": theme,
            }
        )

    # save raw
    ts = int(time.time())
    out_path = _raw_cache_dir() / f"arxiv_raw_{ts}.json"
    payload = {
        "ok": True,
        "query_used": q,
        "theme": theme,
        "sort": sort,
        "count": len(items),
        "items": items,
        "last_search_url": url,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {**payload, "saved_to": str(out_path)}
