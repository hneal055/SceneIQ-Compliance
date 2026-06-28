"""
Daily monitoring digest â€” generates and sends a summary of new monitoring
events to all users who have reportFrequency = 'daily' or 'weekly' (on the
appropriate day) in their NotificationPreference.

Called by the APScheduler daily job defined in src/utils/scheduler.py.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from src.utils.database import prisma
from src.services.email_service import send_email

logger = logging.getLogger(__name__)

# How many hours back to include events for
DAILY_WINDOW_HOURS  = 25   # slight buffer so nothing falls through the gap
WEEKLY_WINDOW_HOURS = 7 * 24 + 1


def _severity_badge(severity: str) -> str:
    return {
        "critical": '<span style="background:#dc2626;color:white;padding:2px 8px;border-radius:4px;font-size:12px">CRITICAL</span>',
        "warning":  '<span style="background:#d97706;color:white;padding:2px 8px;border-radius:4px;font-size:12px">WARNING</span>',
        "info":     '<span style="background:#2563eb;color:white;padding:2px 8px;border-radius:4px;font-size:12px">INFO</span>',
    }.get(severity, "")


def _build_html(events: list, window_label: str) -> str:
    if not events:
        body = "<p style='color:#6b7280'>No new regulatory events in this period.</p>"
    else:
        rows = []
        for ev in events:
            source_name = ev.source.name if ev.source else "Unknown source"
            pub = ev.publishedAt.strftime("%b %d") if ev.publishedAt else ""
            link = f'<a href="{ev.url}" style="color:#2563eb">{ev.title}</a>' if ev.url else ev.title
            rows.append(f"""
              <tr style="border-bottom:1px solid #e5e7eb">
                <td style="padding:10px 8px">{_severity_badge(ev.severity)}</td>
                <td style="padding:10px 8px;font-size:14px">{link}<br>
                    <span style="color:#9ca3af;font-size:12px">{source_name}</span></td>
                <td style="padding:10px 8px;color:#9ca3af;font-size:12px;white-space:nowrap">{pub}</td>
              </tr>
            """)
        body = f"""
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
              <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280">SEVERITY</th>
              <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280">EVENT</th>
              <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280">DATE</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        """

    critical_count = sum(1 for e in events if e.severity == "critical")
    warning_count  = sum(1 for e in events if e.severity == "warning")

    banner_color = "#dc2626" if critical_count else ("#d97706" if warning_count else "#2563eb")
    banner_label = (
        f"{critical_count} critical alert{'s' if critical_count != 1 else ''}"
        if critical_count else
        f"{warning_count} warning{'s' if warning_count != 1 else ''}"
        if warning_count else
        f"{len(events)} info update{'s' if len(events) != 1 else ''}"
    ) if events else "No new events"

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:system-ui,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:32px 16px">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">

        <!-- Header -->
        <tr><td style="background:{banner_color};padding:24px 32px">
          <h1 style="margin:0;color:white;font-size:20px">SceneIQ</h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,.8);font-size:14px">
            {window_label} Monitoring Digest â€” {banner_label}
          </p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:24px 32px">
          {body}
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb">
          <p style="margin:0;font-size:12px;color:#9ca3af">
            You're receiving this because you enabled monitoring digests in SceneIQ.
            Manage preferences in <strong>Settings â†’ Email Reports</strong>.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


async def send_daily_digest() -> None:
    """
    Called once daily by APScheduler.
    Sends digest to every active NotificationPreference where reportFrequency
    is 'daily', and to 'weekly' subscribers on Mondays (weekday == 0).
    """
    now = datetime.now(timezone.utc)
    is_monday = now.weekday() == 0

    try:
        prefs = await prisma.notificationPreference.find_many(
            where={"active": True},
            include={"user": True},
        )
    except Exception as exc:
        logger.error(f"[digest] Failed to load notification preferences: {exc}")
        return

    recipients: list[tuple] = []   # (emailAddress, window_hours, window_label, juris_filter)
    for pref in prefs:
        freq = getattr(pref, "reportFrequency", "never") or "never"
        if freq == "daily":
            recipients.append((pref.emailAddress, DAILY_WINDOW_HOURS, "Daily", pref.jurisdictions))
        elif freq == "weekly" and is_monday:
            recipients.append((pref.emailAddress, WEEKLY_WINDOW_HOURS, "Weekly", pref.jurisdictions))

    if not recipients:
        logger.debug("[digest] No recipients for this run")
        return

    for email, window_hours, label, jurisdictions in recipients:
        cutoff = now - timedelta(hours=window_hours)
        try:
            where_clause: dict = {
                "createdAt": {"gte": cutoff},
                "isRead": False,
            }
            events = await prisma.monitoringEvent.find_many(
                where=where_clause,
                include={"source": True},
                order={"severity": "asc"},   # critical first
            )
        except Exception as exc:
            logger.error(f"[digest] Failed to load events for {email}: {exc}")
            continue

        critical = sum(1 for e in events if e.severity == "critical")
        subject = (
            f"ðŸš¨ SceneIQ Alert: {critical} critical regulatory update{'s' if critical > 1 else ''}"
            if critical else
            f"SceneIQ {label} Digest â€” {len(events)} new event{'s' if len(events) != 1 else ''}"
        )
        html = _build_html(events, label)
        send_email(email, subject, html)
        logger.info(f"[digest] Sent {label} digest to {email} ({len(events)} events)")



