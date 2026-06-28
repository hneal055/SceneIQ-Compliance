"""
Monitoring API endpoints â€” regulatory feed events and sources.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# â”€â”€ Request / response models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SourceCreate(BaseModel):
    name: str
    url: str
    feedUrl: Optional[str] = None
    sourceType: str = "rss"
    jurisdiction: Optional[str] = None


class EventsResponse(BaseModel):
    total: int
    unread: int
    events: list


# â”€â”€ Events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/events", summary="List monitoring events")
async def list_events(
    limit: int = 20,
    skip: int = 0,
    unread_only: bool = False,
):
    where = {"isRead": False} if unread_only else {}
    events = await prisma.monitoringEvent.find_many(
        where=where,
        include={"source": True},
        order={"createdAt": "desc"},
        take=limit,
        skip=skip,
    )
    total = await prisma.monitoringEvent.count(where=where)
    unread = await prisma.monitoringEvent.count(where={"isRead": False})
    return {"total": total, "unread": unread, "events": events}


@router.get("/events/unread-count", summary="Unread event count")
async def unread_count():
    count = await prisma.monitoringEvent.count(where={"isRead": False})
    return {"count": count}


@router.patch("/events/{event_id}/read", summary="Mark event as read")
async def mark_read(event_id: str):
    event = await prisma.monitoringEvent.find_unique(where={"id": event_id})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    updated = await prisma.monitoringEvent.update(
        where={"id": event_id},
        data={"isRead": True},
    )
    return updated


@router.post("/events/mark-all-read", summary="Mark all events as read")
async def mark_all_read():
    result = await prisma.monitoringEvent.update_many(
        where={"isRead": False},
        data={"isRead": True},
    )
    return {"updated": result.count}


# â”€â”€ Sources â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/sources", summary="List monitoring sources")
async def list_sources():
    sources = await prisma.monitoringSource.find_many(
        order={"createdAt": "asc"},
    )
    return {"total": len(sources), "sources": sources}


@router.post("/sources", status_code=status.HTTP_201_CREATED, summary="Add monitoring source")
async def create_source(data: SourceCreate):
    source = await prisma.monitoringSource.create(
        data={
            "name": data.name,
            "url": data.url,
            "feedUrl": data.feedUrl,
            "sourceType": data.sourceType,
            "jurisdiction": data.jurisdiction,
        }
    )
    logger.info(f"Monitoring source created: {source.name}")
    return source


# â”€â”€ Manual ingestion trigger â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/ingest", summary="Manually trigger feed ingestion across all active sources")
async def trigger_ingest():
    """
    Runs the same ingestion job the scheduler fires every 4 hours.
    Useful for testing, seeding, or forcing an immediate refresh.
    """
    from src.services.feed_ingestion import ingest_all_sources
    new_events = await ingest_all_sources()
    return {"status": "ok", "new_events": new_events}





