from typing import Dict, List, Optional

from pydantic import BaseModel


class SendEmailParams(BaseModel):
    recipient_email: str
    subject: str
    conversation_history: List[Dict[str, str]]
    # chaque élément attendu : {"role": ..., "content": ..., "timestamp": ...}


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
