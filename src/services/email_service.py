"""
Email service â€” sends transactional and digest emails via SMTP.

Configuration (all via environment / .env):
  SMTP_HOST      e.g. smtp.sendgrid.net or smtp.gmail.com
  SMTP_PORT      587 (STARTTLS) or 465 (SSL)
  SMTP_USER      SMTP username / API key
  SMTP_PASSWORD  SMTP password / API secret
  SMTP_FROM      From address, e.g. noreply@pilotforge.io

If SMTP_HOST is blank the send is a no-op (logs the email instead).
This allows the rest of the codebase to call send_email() unconditionally
without crashing when SMTP is not configured.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.utils.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """
    Send a single email.

    Returns True on success, False on failure (never raises).
    Falls back to plain-text log when SMTP is not configured.
    """
    if not settings.SMTP_HOST:
        logger.info(
            f"[email no-op] to={to!r} subject={subject!r} "
            "(SMTP_HOST not configured â€” set in .env to enable real delivery)"
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to

    if text:
        msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as srv:
                srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                srv.sendmail(msg["From"], [to], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as srv:
                srv.ehlo()
                srv.starttls(context=context)
                srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                srv.sendmail(msg["From"], [to], msg.as_string())
        logger.info(f"[email sent] to={to!r} subject={subject!r}")
        return True
    except Exception as exc:
        logger.error(f"[email error] to={to!r}: {exc}")
        return False


def send_emails_bulk(recipients: list[str], subject: str, html: str, text: str | None = None) -> int:
    """Send the same email to multiple recipients. Returns success count."""
    return sum(send_email(r, subject, html, text) for r in recipients)



