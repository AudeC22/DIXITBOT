from typing import List, Optional

from pydantic import BaseModel


class ArxivMetadataParams(BaseModel):
    query: str
    theme: Optional[str] = None
    max_results: int = 8
    sort: str = "relevance"


class ArxivMetadataItem(BaseModel):
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    submitted_date: str
    categories: List[str] = []
    abs_url: str
    pdf_url: str


class ToolResponse(BaseModel):
    tool: str
    ok: bool
    items: List[ArxivMetadataItem] = []
    scraped_at: str
    errors: List[str] = []
