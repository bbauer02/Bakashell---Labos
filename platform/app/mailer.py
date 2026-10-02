"""Envoi d'e-mails par un serveur SMTP (Brevo, OVH…), configuré par variables d'environnement.

Sans configuration (SMTP_HOST vide), la plateforme n'envoie rien, et ce qui en dépend (inscription des enseignants
par e-mail) est désactivé. Les identifiants ne vivent que dans le .env du serveur.

    SMTP_HOST=smtp-relay.brevo.com   SMTP_PORT=587 (STARTTLS) ou 465 (SSL)
    SMTP_USER=…   SMTP_PASSWORD=…   MAIL_FROM=Bakashell <noreply@bakashell.fr>
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

log = logging.getLogger("linux-lab")

TIMEOUT = 20


def _config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "sender": os.environ.get("MAIL_FROM", "").strip(),
    }


def configured() -> bool:
    c = _config()
    return bool(c["host"] and c["sender"])


def send(to: str, subject: str, text: str, html: str = None) -> bool:
    """Envoie un e-mail (texte, et HTML s'il est fourni). Retourne False en cas d'échec (journalisé)."""
    c = _config()
    if not (c["host"] and c["sender"]):
        log.warning("E-mail non envoyé à %s : SMTP non configuré", to)
        return False
    msg = EmailMessage()
    msg["From"] = c["sender"]
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=c["sender"].rsplit("@", 1)[-1].strip("> "))
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    try:
        if c["port"] == 465:
            server = smtplib.SMTP_SSL(c["host"], c["port"], timeout=TIMEOUT, context=context)
        else:
            server = smtplib.SMTP(c["host"], c["port"], timeout=TIMEOUT)
            server.starttls(context=context)
        with server:
            if c["user"]:
                server.login(c["user"], c["password"])
            server.send_message(msg)
        log.info("E-mail envoyé à %s : %s", to, subject)
        return True
    except (smtplib.SMTPException, OSError) as e:
        log.error("Échec de l'envoi d'un e-mail à %s : %s", to, e)
        return False
