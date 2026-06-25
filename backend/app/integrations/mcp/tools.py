from datetime import datetime, timezone

from app.integrations.mcp.schemas import ArxivMetadataItem, ArxivMetadataParams, ToolResponse
from app.services.scrape_service import scrape_arxiv


def get_arxiv_metadata(params: ArxivMetadataParams) -> ToolResponse:
    """Tool Niveau 1 - métadonnées arXiv. Wrappe scrape_service."""
    scraped_at = datetime.now(timezone.utc).isoformat()

    try:
        result = scrape_arxiv(
            query=params.query,
            theme=params.theme,
            max_results=params.max_results,
            sort=params.sort,
        )
    except Exception as e:
        return ToolResponse(tool="arxiv_metadata", ok=False, items=[], scraped_at=scraped_at, errors=[str(e)])

    if not result.get("ok", False):
        return ToolResponse(
            tool="arxiv_metadata",
            ok=False,
            items=[],
            scraped_at=scraped_at,
            errors=result.get("errors", ["unknown error"]),
        )

    items = [
        ArxivMetadataItem(
            arxiv_id=it.get("arxiv_id", ""),
            title=it.get("title", ""),
            authors=it.get("authors", []),
            abstract=it.get("abstract", ""),
            submitted_date=it.get("submitted_date", ""),
            categories=[],
            abs_url=it.get("abs_url", ""),
            pdf_url=it.get("pdf_url", ""),
        )
        for it in result.get("items", [])
    ]

    return ToolResponse(tool="arxiv_metadata", ok=True, items=items, scraped_at=scraped_at, errors=[])
