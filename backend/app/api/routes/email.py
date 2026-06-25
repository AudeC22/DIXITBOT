import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrations import mcp

router = APIRouter()
logger = logging.getLogger(__name__)


class SendEmailRequest(BaseModel):
    recipient_email: str = Field(..., description="Adresse email du destinataire")
    subject: str = Field(..., description="Sujet de l'email")
    conversation_history: List[Dict[str, str]] = Field(..., description="Historique de la conversation")


@router.post("/send-email")
def send_email(req: SendEmailRequest) -> Dict[str, Any]:
    tool_response = mcp.run_tool("send_email", {
        "recipient_email": req.recipient_email,
        "subject": req.subject,
        "conversation_history": req.conversation_history,
    })

    if not tool_response.ok:
        logger.error(f"send_email tool returned an error: {tool_response.errors}")
        raise HTTPException(503, f"Service email indisponible: {tool_response.errors}")

    return {"ok": True, "sent_at": tool_response.scraped_at}
