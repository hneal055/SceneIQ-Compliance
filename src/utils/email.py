"""
Async email utility â€” wraps stdlib smtplib in a thread executor.
Configure via environment variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM.
If SMTP_HOST is not set, all sends are silently no-ops with a warning log.
"""
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.utils.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body_html: str) -> bool:
    """
    Send an HTML email. Returns True on success, False if SMTP is not configured or send fails.
    Non-blocking â€” runs smtplib in a thread-pool executor.
    """
    if not settings.SMTP_HOST:
        logger.warning(f"SMTP not configured â€” skipping email to {to}: {subject}")
        return False

    smtp_from = settings.SMTP_FROM or settings.SMTP_USER

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = smtp_from
        msg["To"]      = to
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            if settings.SMTP_USER:
                srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            srv.sendmail(smtp_from, [to], msg.as_string())

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send)
        logger.info(f"âœ‰ï¸  Email sent â†’ {to}: {subject}")
        return True
    except Exception as exc:
        logger.error(f"âŒ Email send failed â†’ {to}: {exc}")
        return False


def build_monitoring_alert_html(
    event_title: str,
    event_url: str | None,
    source_name: str,
    jurisdiction: str | None,
    severity: str,
) -> str:
    """Return a minimal HTML body for a monitoring event alert email."""
    severity_color = {"critical": "#dc2626", "warning": "#d97706", "info": "#2563eb"}.get(severity, "#64748b")
    url_line = f'<p><a href="{event_url}" style="color:#2563eb;">Read full article â†’</a></p>' if event_url else ""
    jur_line = f"<p style='color:#64748b;font-size:13px;'>Jurisdiction: <strong>{jurisdiction}</strong></p>" if jurisdiction else ""
    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px;">
  <div style="border-left:4px solid {severity_color};padding-left:16px;margin-bottom:20px;">
    <p style="margin:0 0 4px;font-size:11px;font-weight:600;text-transform:uppercase;color:{severity_color};">
      {severity.upper()} â€” Regulatory Alert
    </p>
    <h2 style="margin:0;font-size:18px;color:#0f172a;">{event_title}</h2>
  </div>
  <p style="color:#64748b;font-size:13px;">Source: <strong>{source_name}</strong></p>
  {jur_line}
  {url_line}
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
  <p style="font-size:11px;color:#94a3b8;">
    You received this because you subscribed to regulatory monitoring alerts in SceneIQ.
  </p>
</div>
"""

