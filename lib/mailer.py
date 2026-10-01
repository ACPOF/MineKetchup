"""
Envoi de courriels par SMTP.

Volontairement minimal et sans dépendance à Streamlit : le script du rapport
hebdomadaire s'en sert aussi, depuis GitHub Actions.

Règle de conduite : un envoi qui échoue ne doit JAMAIS faire échouer ce qui
l'a déclenché. Une commande enregistrée reste enregistrée même si le courriel
ne part pas — `send()` renvoie un booléen et n'explose pas.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from lib import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15


def is_configured() -> bool:
    """Vrai si l'envoi de courriels est paramétré (hôte, utilisateur, mot de passe)."""
    return all(settings.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def sender() -> str:
    """Adresse d'expédition : SMTP_FROM si fourni, sinon l'utilisateur SMTP."""
    return settings.get("SMTP_FROM") or settings.get("SMTP_USER")


def _build(
    to: list[str],
    subject: str,
    html: str,
    text: str,
    reply_to: str = "",
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr(("Mine de Ketchup", sender()))
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    for filename, payload, mime in attachments or []:
        maintype, _, subtype = mime.partition("/")
        message.add_attachment(
            payload, maintype=maintype, subtype=subtype, filename=filename
        )
    return message


def send(
    to: list[str] | str,
    subject: str,
    html: str,
    text: str,
    reply_to: str = "",
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """Envoie un courriel. Retourne True si parti, False sinon — ne lève jamais."""
    recipients = [to] if isinstance(to, str) else list(to)
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        return False

    if not is_configured():
        logger.warning("Envoi de courriel ignoré : SMTP non configuré (%s)", subject)
        return False

    host = settings.get("SMTP_HOST")
    port = int(settings.get("SMTP_PORT", "587") or 587)
    user = settings.get("SMTP_USER")
    password = settings.get("SMTP_PASSWORD")
    # « ssl » = TLS dès la connexion (port 465), « starttls » = on chiffre après
    # la poignée de main (port 587). Déduit du port, mais réglable : certains
    # hébergeurs écoutent le TLS implicite sur un autre port.
    mode = (settings.get("SMTP_SECURITY") or ("ssl" if port == 465 else "starttls")).lower()

    try:
        message = _build(recipients, subject, html, text, reply_to, attachments)
        context = ssl.create_default_context()
        if mode == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS)
        with server:
            if mode != "ssl":
                # Jamais d'identifiants en clair : si le serveur ne sait pas
                # chiffrer, l'envoi échoue plutôt que de les exposer.
                server.starttls(context=context)
            server.login(user, password)
            server.send_message(message)
        logger.info("Courriel envoyé à %s — %s", ", ".join(recipients), subject)
        return True
    except Exception as exc:  # noqa: BLE001 — jamais bloquant pour l'appelant
        logger.error("Échec d'envoi à %s (%s) : %s", ", ".join(recipients), subject, exc)
        return False
