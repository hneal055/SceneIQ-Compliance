"""
RSS/Atom feed ingestion service.

Fetches each MonitoringSource that has a configured feedUrl, parses it with
feedparser, deduplicates entries by SHA-256 content hash, and persists new
items to the MonitoringEvent table.

feedparser.parse() is synchronous and blocking, so it is dispatched to a
thread-pool executor to avoid stalling the asyncio event loop.
"""
import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser  # type: ignore

from src.utils.database import prisma

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _content_hash(title: str, url: Optional[str], published_raw: str) -> str:
    """SHA-256 fingerprint used for deduplication."""
    raw = f"{title.strip()}|{url or ''}|{published_raw}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _parse_published(entry) -> Optional[datetime]:
    """Return a timezone-aware datetime from a feedparser entry, or None."""
    struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if struct:
        try:
            return datetime(*struct[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _severity_from_entry(title: str, summary: str) -> str:
    """Infer severity from keywords in the title/summary."""
    text = (title + " " + summary).lower()
    if any(kw in text for kw in ("expir", "terminat", "eliminat", "sunset", "suspend", "cap reached", "fully utilized")):
        return "critical"
    if any(kw in text for kw in ("proposed", "review", "update", "guidance", "amendment", "change", "new rule")):
        return "warning"
    return "info"


# â”€â”€ Core ingestion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def ingest_source(source_id: str) -> int:
    """
    Fetch and parse one source's RSS/Atom feed.
    Returns the count of new MonitoringEvent records created.
    """
    source = await prisma.monitoringSource.find_unique(where={"id": source_id})
    if not source or not source.feedUrl or not source.active:
        return 0

    logger.info(f"Fetching feed: {source.name} ({source.feedUrl})")

    # Run blocking feedparser call off the event loop
    loop = asyncio.get_event_loop()
    try:
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, source.feedUrl),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"Feed timeout for {source.name} ({source.feedUrl})")
        return 0
    except Exception as exc:
        logger.warning(f"Feed fetch error for {source.name}: {exc}")
        return 0

    if feed.bozo and not feed.entries:
        logger.warning(f"Malformed or empty feed for {source.name}: {getattr(feed, 'bozo_exception', 'unknown')}")
        await prisma.monitoringSource.update(
            where={"id": source_id},
            data={"lastFetched": datetime.now(timezone.utc)},
        )
        return 0

    new_count = 0
    for entry in feed.entries[:25]:
        title       = _strip_html(getattr(entry, "title", "") or "").strip() or "(no title)"
        url         = getattr(entry, "link", None) or None
        raw_summary = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
        summary     = _strip_html(raw_summary)[:600] or None
        published_raw = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
        published   = _parse_published(entry)
        hash_val    = _content_hash(title, url, published_raw)

        # Skip duplicates
        existing = await prisma.monitoringEvent.find_first(where={"contentHash": hash_val})
        if existing:
            continue

        severity = _severity_from_entry(title, summary or "")

        await prisma.monitoringEvent.create(data={
            "sourceId":    source_id,
            "title":       title[:255],
            "summary":     summary,
            "url":         url,
            "contentHash": hash_val,
            "severity":    severity,
            "publishedAt": published,
        })
        new_count += 1

        # Fire email notifications for matching subscribers (best-effort, non-blocking)
        try:
            await _notify_subscribers(
                title=title[:255],
                url=url,
                source_name=source.name,
                jurisdiction=source.jurisdiction,
                severity=severity,
            )
        except Exception as exc:
            logger.warning(f"Notification dispatch failed for event '{title[:60]}': {exc}")

    await prisma.monitoringSource.update(
        where={"id": source_id},
        data={"lastFetched": datetime.now(timezone.utc)},
    )

    if new_count:
        logger.info(f"âœ… {source.name}: {new_count} new event(s) ingested")
    else:
        logger.info(f"â„¹ï¸  {source.name}: no new events")

    return new_count


async def _notify_subscribers(
    title: str,
    url: Optional[str],
    source_name: str,
    jurisdiction: Optional[str],
    severity: str,
) -> None:
    """
    Send email alerts to all active NotificationPreference records whose
    jurisdiction filter matches (or is empty, meaning subscribe to all).
    """
    from src.utils.email import send_email, build_monitoring_alert_html  # lazy import

    prefs = await prisma.notificationPreference.find_many(where={"active": True})
    if not prefs:
        return

    html = build_monitoring_alert_html(
        event_title=title,
        event_url=url,
        source_name=source_name,
        jurisdiction=jurisdiction,
        severity=severity,
    )
    subject = f"[SceneIQ] Regulatory Alert: {title[:80]}"

    for pref in prefs:
        # Empty jurisdictions list = subscribe to everything
        if pref.jurisdictions and jurisdiction and jurisdiction.upper() not in [j.upper() for j in pref.jurisdictions]:
            continue
        await send_email(to=pref.emailAddress, subject=subject, body_html=html)


async def ingest_all_sources() -> int:
    """
    Poll every active MonitoringSource that has a feedUrl configured.
    Returns the total count of new events created across all sources.
    Called by APScheduler on its cron interval and by the manual API trigger.
    """
    sources = await prisma.monitoringSource.find_many(
        where={"active": True, "feedUrl": {"not": None}},
        order={"createdAt": "asc"},
    )

    if not sources:
        logger.info("No active sources with feedUrl configured â€” ingestion skipped")
        return 0

    logger.info(f"Starting feed ingestion for {len(sources)} source(s)")
    total = 0
    for source in sources:
        try:
            total += await ingest_source(source.id)
        except Exception as exc:
            logger.error(f"Ingestion error for source {source.name}: {exc}", exc_info=True)

    logger.info(f"Feed ingestion complete â€” {total} new event(s) from {len(sources)} source(s)")
    return total




