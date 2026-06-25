import json
from datetime import datetime, timezone
from pathlib import Path

from app.integrations.mcp.schemas import ArxivMetadataItem, ArxivMetadataParams, SendEmailParams, ToolResponse
from app.services.email_service import send_email_smtp
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


def build_email_html_body(conversation_history):
    # Construit un corps HTML simple : une ligne par message, pas de template engine
    lines = []
    for message in conversation_history:
        role = message.get("role", "")
        content = message.get("content", "")
        lines.append(f"<p><b>{role}</b>: {content}</p>")
    html_body = "<html><body>" + "".join(lines) + "</body></html>"
    return html_body


def save_conversation_copy(conversation_history):
    # Sauvegarde une copie JSON de l'historique avant l'envoi de l'email
    backend_dir = Path(__file__).resolve().parents[3]
    folder = backend_dir / "data_lake" / "raw" / "conversation_history"
    folder.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    file_name = "email_" + now.strftime("%Y%m%d_%H%M%S") + ".json"
    file_path = folder / file_name

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(conversation_history, f, ensure_ascii=False, indent=2)


def send_email(params: SendEmailParams) -> ToolResponse:
    """Tool MCP - envoie l'historique de conversation par email.
    Wrappe email_service.send_email_smtp."""
    scraped_at = datetime.now(timezone.utc).isoformat()

    html_body = build_email_html_body(params.conversation_history)
    save_conversation_copy(params.conversation_history)

    try:
        send_email_smtp(params.recipient_email, params.subject, html_body)
    except Exception as e:
        return ToolResponse(tool="send_email", ok=False, items=[], scraped_at=scraped_at, errors=[str(e)])

    return ToolResponse(tool="send_email", ok=True, items=[], scraped_at=scraped_at, errors=[])
