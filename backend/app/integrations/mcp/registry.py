from datetime import datetime, timezone
from typing import Any, Dict

from app.integrations.mcp.schemas import ArxivMetadataParams, ToolResponse
from app.integrations.mcp.tools import get_arxiv_metadata

AVAILABLE_TOOLS = {
    "arxiv_metadata": get_arxiv_metadata,
}

_PARAM_SCHEMAS = {
    "arxiv_metadata": ArxivMetadataParams,
}


def run_tool(name: str, params: Dict[str, Any]) -> ToolResponse:
    """Dispatch un tool par son nom. Retourne ToolResponse uniforme."""
    scraped_at = datetime.now(timezone.utc).isoformat()

    if name not in AVAILABLE_TOOLS:
        return ToolResponse(tool=name, ok=False, items=[], scraped_at=scraped_at, errors=[f"unknown tool: {name}"])

    schema = _PARAM_SCHEMAS[name]
    try:
        validated_params = schema(**params)
    except Exception as e:
        return ToolResponse(tool=name, ok=False, items=[], scraped_at=scraped_at, errors=[f"invalid params: {e}"])

    return AVAILABLE_TOOLS[name](validated_params)
