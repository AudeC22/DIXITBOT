import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email_smtp(recipient_email, subject, html_body):
    """Envoie un email via smtplib vers le serveur SMTP configuré (MailHog)."""
    smtp_host = os.getenv("SMTP_HOST", "127.0.0.1")
    smtp_port = os.getenv("SMTP_PORT", "1025")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = "dixitbot@localhost"
    message["To"] = recipient_email

    # On ajoute une version texte brut simple, en plus du HTML
    text_part = MIMEText("Voir la version HTML de ce message.", "plain")
    html_part = MIMEText(html_body, "html")
    message.attach(text_part)
    message.attach(html_part)

    # Pas de try/except ici : si la connexion SMTP échoue, l'exception
    # remonte à l'appelant (cohérent avec le reste du projet).
    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
        server.sendmail(message["From"], recipient_email, message.as_string())
