"""
Schedule Parser API endpoints.

Wires the broadcast_scheduler service module into FastAPI:
  - POST   /schedule/upload          parse a CSV / XML / BXF / JSON file and save segments
  - GET    /schedule/events          list saved segments (paginated, filterable)
  - DELETE /schedule/events/{id}     delete a single segment

Auth is applied at the router-aggregation layer (src/api/routes.py); no need
to repeat it here. All DB calls are wrapped in try/except so a transient
database problem cannot crash the API.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.services.broadcast_scheduler.parsers.csv_parser import parse_csv_file
from src.services.broadcast_scheduler.parsers.xml_parser import parse_xml_file
from src.services.broadcast_scheduler.parsers.json_parser import parse_json_file
from src.services.broadcast_scheduler.processors.transformer import transform_schedule
from src.services.broadcast_scheduler.processors.validator import validate_schedule
from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["Schedule Parser"])


# File-extension -> parser-function dispatch table. .bxf is a SMPTE XML
# variant, so it shares the XML parser.
_PARSERS = {
    ".csv": ("csv", parse_csv_file),
    ".xml": ("xml", parse_xml_file),
    ".bxf": ("xml", parse_xml_file),
    ".json": ("json", parse_json_file),
}


# Picks the parser for a given filename suffix. Returns a (source_format,
# parser_callable) tuple, or (None, None) if the extension is unsupported.
def _dispatch_parser(filename: str):
    ext = Path(filename).suffix.lower()
    return _PARSERS.get(ext, (None, None))


# Builds the dict shape the upload endpoint persists to the schedule_events
# table. Lives in its own helper so the upload endpoint stays readable.
def _segment_to_row(segment, schedule, source_format: str) -> dict:
    return {
        "channel": (segment.channel or schedule.channel_name or "unknown"),
        "scheduleDate": schedule.schedule_date,
        "sourceFile": schedule.source_filename or "",
        "sourceFormat": source_format,
        "title": segment.title or "",
        "episodeTitle": segment.episode_title,
        "episodeNumber": segment.episode_number,
        "seriesNumber": segment.series_number,
        "txTime": segment.tx_time,
        "duration": segment.duration,
        "genre": segment.genre,
        "rightsStart": segment.rights_start,
        "rightsEnd": segment.rights_end,
        "assetId": segment.asset_id,
        "daypart": getattr(segment, "daypart", None),  # <--- ADD THIS LINE
    }


@router.post("/upload", summary="Upload and parse a schedule file")
async def upload_schedule(file: UploadFile = File(...)):
    """
    Accepts a single CSV / XML / BXF / JSON schedule file, parses it via the
    broadcast_scheduler service module, persists each segment as a row in
    the schedule_events table, and returns a summary.
    """
    filename = file.filename or ""
    source_format, parser_fn = _dispatch_parser(filename)
    if parser_fn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {Path(filename).suffix!r}. "
                "Supported: .csv, .xml, .bxf, .json"
            ),
        )

    # Save the upload to a real temp file so the parser can read it from
    # disk (the parsers expect a path, not a file-like object).
    suffix = Path(filename).suffix
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
    except OSError as exc:
        logger.exception("schedule upload: tempfile write failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not buffer upload: {exc}",
        )

    try:
        schedule = parser_fn(tmp_path)
        if schedule is None:
            logger.warning("schedule upload: parser returned None for %s", filename)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse {filename!r} — see server log for details.",
            )

        # Stamp the original upload name onto the Schedule so saved rows
        # carry it (not the random tempfile name).
        schedule.source_filename = filename

        transform_schedule(schedule)
        issues = validate_schedule(schedule)
        errors = [i for i in issues if i["level"] == "error"]
        warnings = [i for i in issues if i["level"] == "warning"]

        # Persist segments. Try/except is per-segment so one bad row doesn't
        # drop the whole upload.
        events_saved = 0
        for segment in schedule.segments:
            try:
                await prisma.scheduleevent.create(
                    data=_segment_to_row(segment, schedule, source_format)
                )
                events_saved += 1
            except Exception:
                logger.exception(
                    "schedule upload: failed to save segment from %s", filename
                )

        logger.info(
            "schedule upload OK: file=%s format=%s segments=%d errors=%d warnings=%d saved=%d",
            filename,
            source_format,
            len(schedule.segments),
            len(errors),
            len(warnings),
            events_saved,
        )

        return {
            "channel": schedule.channel_name,
            "date": schedule.schedule_date,
            "source_format": source_format,
            "segments_parsed": len(schedule.segments),
            "errors": errors,
            "warnings": warnings,
            "events_saved": events_saved,
        }
    finally:
        # Always clean up the temp file, even on exception.
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "schedule upload: tempfile cleanup failed for %s", tmp_path
            )


@router.get("/events", summary="List saved schedule events")
async def list_schedule_events(
    channel: Optional[str] = None,
    date: Optional[str] = None,
    source_format: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    """Paginated list of ScheduleEvent rows. All filter parameters are optional."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 500:
        page_size = 50

    where: dict = {}
    if channel:
        where["channel"] = channel
    if date:
        where["scheduleDate"] = date
    if source_format:
        where["sourceFormat"] = source_format

    try:
        total = await prisma.scheduleevent.count(where=where or None)
        events = await prisma.scheduleevent.find_many(
            where=where or None,
            order={"importedAt": "desc"},
            skip=(page - 1) * page_size,
            take=page_size,
        )
    except Exception as exc:
        logger.exception("schedule events: list query failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not list schedule events: {exc}",
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "events": events,
    }


@router.delete("/events/{event_id}", summary="Delete a schedule event")
async def delete_schedule_event(event_id: str):
    """Deletes a single ScheduleEvent by ID."""
    try:
        existing = await prisma.scheduleevent.find_unique(where={"id": event_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ScheduleEvent {event_id} not found",
            )
        await prisma.scheduleevent.delete(where={"id": event_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("schedule events: delete failed for %s", event_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete schedule event: {exc}",
        )

    return {"deleted": True, "id": event_id}
