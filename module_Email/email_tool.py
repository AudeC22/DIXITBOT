# ============================================================  # #
# 📧 Email Tool (LOCAL SMTP via MailHog)                         # #
# - Objectif: envoyer l'historique d'une conversation par email  # #
# - Cible: serveur SMTP local (MailHog: 127.0.0.1:1025)          # #
# ============================================================  # #

from __future__ import annotations  # # Active annotations forward (py3.10+) # #

import json  # # Lire config.json # #
import os  # # Chemins fichiers # #
import smtplib  # # Client SMTP (envoi email) # #
import html  # # Échapper le texte dans HTML # #
from dataclasses import dataclass  # # Structure simple config # #
from email.message import EmailMessage  # # Construire email MIME # #
from email.utils import formataddr  # # "Nom <email>" # #
from pathlib import Path  # # Chemins robustes # #
from typing import Any, Dict, List, Optional  # # Typage # #


# ===============================  # #
# 🧩 Modèle de config SMTP         # #
# ===============================  # #
@dataclass  # # Crée une classe de données simple # #
class SmtpConfig:  # # Contient les paramètres SMTP # #
    host: str  # # Serveur SMTP (MailHog = 127.0.0.1) # #
    port: int  # # Port SMTP (MailHog = 1025) # #
    use_tls: bool  # # TLS (False pour MailHog local) # #
    username: str  # # User SMTP (souvent vide en local) # #
    password: str  # # Password SMTP (souvent vide en local) # #
    from_email: str  # # Expéditeur email # #
    from_name: str  # # Nom expéditeur # #


# ===============================  # #
# 📌 Chargement config.json        # #
# ===============================  # #
def load_email_config(config_path: str | None = None) -> SmtpConfig:  # # Charge la config SMTP depuis config.json # #
    base_dir = Path(__file__).resolve().parent  # # Dossier module_Email # #
    path = Path(config_path).resolve() if config_path else (base_dir / "config.json")  # # Chemin config # #
    if not path.exists():  # # Si config absente # #
        raise FileNotFoundError(f"config.json introuvable: {path}")  # # Erreur claire # #

    raw = json.loads(path.read_text(encoding="utf-8"))  # # Lit JSON UTF-8 # #
    smtp = raw.get("smtp", {})  # # Récupère bloc smtp # #

    return SmtpConfig(  # # Retourne une config typed # #
        host=str(smtp.get("host", "127.0.0.1")),  # # Host défaut # #
        port=int(smtp.get("port", 1025)),  # # Port défaut # #
        use_tls=bool(smtp.get("use_tls", False)),  # # TLS défaut # #
        username=str(smtp.get("username", "")),  # # User défaut # #
        password=str(smtp.get("password", "")),  # # Pass défaut # #
        from_email=str(smtp.get("from_email", "dixitbot@local.test")),  # # From défaut # #
        from_name=str(smtp.get("from_name", "DIXITBOT (local)")),  # # Nom défaut # #
    )  # # Fin config # #


# ===============================  # #
# 🧱 Formatage conversation         # #
# ===============================  # #
def _format_conversation_as_text(messages: List[Dict[str, Any]]) -> str:  # # Construit une version texte lisible # #
    lines: List[str] = []  # # Stocke les lignes # #
    for m in messages:  # # Parcourt chaque message # #
        role = str(m.get("role", "")).strip()  # # Rôle (user/assistant) # #
        content = str(m.get("content", "")).strip()  # # Contenu # #
        ts = str(m.get("timestamp", "")).strip()  # # Timestamp optionnel # #
        head = f"[{role}]" + (f" ({ts})" if ts else "")  # # En-tête # #
        lines.append(head)  # # Ajoute en-tête # #
        lines.append(content)  # # Ajoute contenu # #
        lines.append("")  # # Ligne vide # #
    return "\n".join(lines).strip()  # # Retour texte # #


def _format_conversation_as_html(messages: List[Dict[str, Any]]) -> str:  # # Construit une version HTML lisible # #
    blocks: List[str] = []  # # Stocke les blocs # #
    blocks.append("<h2>Conversation DIXITBOT</h2>")  # # Titre email # #
    blocks.append("<div style='font-family: Arial, sans-serif; line-height:1.4'>")  # # Wrapper # #

    for m in messages:  # # Parcourt messages # #
        role = html.escape(str(m.get("role", "")).strip())  # # Échappe rôle # #
        content = html.escape(str(m.get("content", "")).strip())  # # Échappe contenu # #
        ts = html.escape(str(m.get("timestamp", "")).strip())  # # Échappe timestamp # #
        badge = f"{role}" + (f" • {ts}" if ts else "")  # # Badge # #
        blocks.append(  # # Ajoute une “carte” message # #
            "<div style='margin:12px 0; padding:10px; border:1px solid #ddd; border-radius:8px'>"
            f"<div style='font-size:12px; color:#555; margin-bottom:6px'><b>{badge}</b></div>"
            f"<div style='white-space:pre-wrap'>{content}</div>"
            "</div>"
        )
    blocks.append("</div>")  # # Ferme wrapper # #
    return "\n".join(blocks)  # # Retour HTML # #


# ===============================  # #
# 🚀 Envoi email                    # #
# ===============================  # #
def send_conversation_email(  # # Fonction principale d’envoi # #
    recipient_email: str,  # # Email destinataire # #
    conversation_history: List[Dict[str, Any]],  # # Liste messages # #
    subject: str = "Conversation DIXITBOT",  # # Sujet email # #
    config_path: Optional[str] = None,  # # Chemin config optionnel # #
) -> Dict[str, Any]:  # # Retourne un dict “ok + diagnostics” # #

    if not recipient_email or "@" not in recipient_email:  # # Validation simple email # #
        return {"ok": False, "error": "INVALID_RECIPIENT_EMAIL"}  # # Erreur stable # #

    if not isinstance(conversation_history, list) or len(conversation_history) == 0:  # # Historique vide # #
        return {"ok": False, "error": "EMPTY_CONVERSATION_HISTORY"}  # # Erreur stable # #

    cfg = load_email_config(config_path=config_path)  # # Charge config SMTP # #

    msg = EmailMessage()  # # Crée message email # #
    msg["From"] = formataddr((cfg.from_name, cfg.from_email))  # # From "Nom <email>" # #
    msg["To"] = recipient_email  # # Destinataire # #
    msg["Subject"] = subject  # # Sujet # #

    text_body = _format_conversation_as_text(conversation_history)  # # Corps texte # #
    html_body = _format_conversation_as_html(conversation_history)  # # Corps HTML # #

    msg.set_content(text_body)  # # Ajoute version texte (fallback) # #
    msg.add_alternative(html_body, subtype="html")  # # Ajoute version HTML # #

    try:  # # Protège contre erreurs SMTP # #
        with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as server:  # # Connexion SMTP # #
            if cfg.use_tls:  # # Si TLS demandé # #
                server.starttls()  # # Active TLS # #
            if cfg.username:  # # Si auth configurée # #
                server.login(cfg.username, cfg.password)  # # Login SMTP # #
            server.send_message(msg)  # # Envoie l’email # #

        return {  # # Retour OK + diagnostics # #
            "ok": True,  # # Statut # #
            "recipient": recipient_email,  # # Echo # #
            "smtp_host": cfg.host,  # # Debug # #
            "smtp_port": cfg.port,  # # Debug # #
        }

    except Exception as e:  # # Catch global # #
        return {  # # Retour erreur stable # #
            "ok": False,  # # KO # #
            "error": "SMTP_SEND_FAILED",  # # Code erreur # #
            "detail": str(e),  # # Détail technique # #
            "smtp_host": cfg.host,  # # Debug # #
            "smtp_port": cfg.port,  # # Debug # #
        }
