"""
APScheduler setup for background feed ingestion and daily email digest.

Jobs:
  feed_ingestion   â€” every 4 hours, ingests all RSS/Atom monitoring sources
  daily_digest     â€” every day at 08:00 UTC, sends monitoring digest emails
                     (weekly subscribers receive theirs on Mondays)

Uses AsyncIOScheduler (runs jobs as coroutines on the FastAPI event loop).
Start/stop is hooked into the FastAPI lifespan in src/main.py.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")

INGEST_INTERVAL_HOURS = 4
DIGEST_HOUR_UTC       = 8    # 08:00 UTC daily


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def start_scheduler() -> None:
    """Register jobs and start the scheduler. Called once at application startup."""
    from src.services.feed_ingestion import ingest_all_sources
    from src.services.daily_digest   import send_daily_digest

    _scheduler.add_job(
        ingest_all_sources,
        trigger=IntervalTrigger(hours=INGEST_INTERVAL_HOURS),
        id="feed_ingestion",
        name="RSS/Atom Feed Ingestion",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,   # allow up to 5 min late before skipping
    )

    _scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=DIGEST_HOUR_UTC, minute=0, timezone="UTC"),
        id="daily_digest",
        name="Daily Monitoring Email Digest",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=1800,  # allow 30 min late
    )

    _scheduler.start()
    logger.info(
        f"âœ… Scheduler started â€” feed ingestion every {INGEST_INTERVAL_HOURS}h, "
        f"digest daily at {DIGEST_HOUR_UTC:02d}:00 UTC"
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Called at application shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("âœ… Scheduler stopped")




