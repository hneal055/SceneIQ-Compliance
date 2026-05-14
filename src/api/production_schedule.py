"""
Production Schedule Engine API endpoints.

Wires every Phase 2–9 service module into FastAPI:
  POST   /production-schedule/{production_id}/import
  GET    /production-schedule/{production_id}/stripboard
  POST   /production-schedule/{production_id}/stripboard/assign
  GET    /production-schedule/{production_id}/dood
  GET    /production-schedule/{production_id}/dood/export
  GET    /production-schedule/{production_id}/call-sheet/{day_number}
  GET    /production-schedule/{production_id}/call-sheet/{day_number}/pdf
  GET    /production-schedule/{production_id}/jurisdiction-tracker
  POST   /production-schedule/{production_id}/compliance-bridge/push

Auth is applied at the router-aggregation layer (src/api/routes.py)
via `dependencies=[Depends(get_current_user)]`; no need to repeat it
here. All Prisma calls are wrapped in try/except so a transient DB
problem cannot crash the API.

Conventions in this file:
  - Importers / generators / trackers / bridge functions are
    pure-sync (see Phases 2–9); the router calls them directly
    without await.
  - Scene / ShootDay / CastMember / JurisdictionShootDays
    dataclasses are populated from Prisma rows via the small
    `_to_*` helpers near the bottom. Names are deliberately
    preserved (jurisdiction_id holds the raw jurisdiction name in
    the importer pipeline; the router resolves to FK ids only
    when persisting).
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from src.models.production_schedule import (
    AssignSceneBody,
    ImportResponse,
)
from src.services.production_schedule.bridge.compliance_bridge import (
    push_shoot_days_to_calculator,
)
from src.services.production_schedule.generators.call_sheet import (
    export_call_sheet_json,
    export_call_sheet_pdf,
    generate_call_sheet,
)
from src.services.production_schedule.generators.dood import (
    export_dood_csv,
    export_dood_pdf,
    generate_dood,
)
from src.services.production_schedule.generators.stripboard import (
    assign_scene_to_day,
    build_stripboard,
)
from src.services.production_schedule.importers.csv_importer import parse_csv_breakdown
from src.services.production_schedule.importers.fdx_importer import parse_fdx_file
from src.services.production_schedule.importers.mms_importer import parse_mms_file
from src.services.production_schedule.models.call_sheet import CallSheet
from src.services.production_schedule.models.cast_member import CastMember
from src.services.production_schedule.models.jurisdiction_shoot_days import (
    JurisdictionShootDays,
)
from src.services.production_schedule.models.scene import Scene
from src.services.production_schedule.models.shoot_day import ShootDay
from src.services.production_schedule.trackers.jurisdiction_tracker import (
    get_jurisdiction_summary,
)
from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/production-schedule", tags=["Production Schedule"])


# File-extension → importer-function dispatch. Mirrors the broadcast
# scheduler's pattern in src/api/schedule_parser.py.
_IMPORTERS = {
    ".csv": ("csv", parse_csv_breakdown),
    ".mms": ("mms", parse_mms_file),
    ".fdx": ("fdx", parse_fdx_file),
}


# =============================================================================
# 1. POST /{production_id}/import
# =============================================================================


@router.post(
    "/{production_id}/import",
    response_model=ImportResponse,
    summary="Upload and parse a script-breakdown file (.csv / .mms / .fdx)",
)
async def import_breakdown(production_id: str, file: UploadFile = File(...)):
    """Parse the uploaded breakdown via the matching importer, persist
    each Scene to the database, and return a summary."""
    production = await _load_production_or_404(production_id)

    filename = file.filename or ""
    source_format, importer_fn = _dispatch_importer(filename)
    if importer_fn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {Path(filename).suffix!r}. "
                "Supported: .csv, .mms, .fdx"
            ),
        )

    # Buffer the upload to disk so the importer (which expects a path)
    # can read it. NamedTemporaryFile mirrors schedule_parser.py.
    suffix = Path(filename).suffix
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
    except OSError as exc:
        logger.exception("production-schedule import: tempfile write failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not buffer upload: {exc}",
        )

    warnings: List[str] = []
    scenes_imported = 0
    jurisdictions_detected_set: set = set()

    try:
        scenes: List[Scene] = importer_fn(tmp_path)

        # Build a name → Jurisdiction.id lookup once so per-scene FK
        # resolution is O(1). The importer stashes jurisdiction NAMES
        # in scene.jurisdiction_id (raw pipeline convention).
        jur_rows = await prisma.jurisdiction.find_many()
        name_to_id = {j.name: j.id for j in jur_rows}

        for scene in scenes:
            raw_name = scene.jurisdiction_id
            if raw_name:
                jurisdictions_detected_set.add(raw_name)

            resolved_jid = name_to_id.get(raw_name) if raw_name else None
            if raw_name and resolved_jid is None:
                warnings.append(
                    f"Jurisdiction {raw_name!r} not found in DB — "
                    f"scene {scene.scene_number} persisted with no FK"
                )

            try:
                await prisma.scene.create(
                    data={
                        "productionId":   production.id,
                        "sceneNumber":    scene.scene_number,
                        "title":          scene.title,
                        "location":       scene.location,
                        "locationType":   scene.location_type,
                        "timeOfDay":      scene.time_of_day,
                        "pageCount":      scene.page_count,
                        "jurisdictionId": resolved_jid,
                        "castIds":        scene.cast_ids,
                        "notes":          scene.notes,
                    }
                )
                scenes_imported += 1
            except Exception:
                logger.exception(
                    "production-schedule import: failed to save scene %s",
                    scene.scene_number,
                )
                warnings.append(
                    f"Scene {scene.scene_number!r} could not be saved — see server log"
                )

        logger.info(
            "production-schedule import OK: file=%s format=%s parsed=%d saved=%d warnings=%d",
            filename, source_format, len(scenes), scenes_imported, len(warnings),
        )

        return ImportResponse(
            scenes_imported=scenes_imported,
            jurisdictions_detected=sorted(jurisdictions_detected_set),
            warnings=warnings,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "production-schedule import: tempfile cleanup failed for %s", tmp_path
            )


# =============================================================================
# 2. GET /{production_id}/stripboard
# =============================================================================


@router.get(
    "/{production_id}/stripboard",
    summary="Returns the full stripboard grid for a production",
)
async def get_stripboard(production_id: str):
    await _load_production_or_404(production_id)
    scenes, shoot_days = await _load_scenes_and_shoot_days(production_id)
    grid = build_stripboard(scenes, shoot_days)
    return _stripboard_to_json(grid)


# =============================================================================
# 3. POST /{production_id}/stripboard/assign
# =============================================================================


@router.post(
    "/{production_id}/stripboard/assign",
    summary="Assign a scene to a shoot day",
)
async def assign_scene(production_id: str, body: AssignSceneBody):
    await _load_production_or_404(production_id)

    # Verify the scene + shoot day both exist AND belong to this production.
    scene_row = await prisma.scene.find_unique(where={"id": body.scene_id})
    if scene_row is None or scene_row.productionId != production_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {body.scene_id!r} not found in production {production_id!r}",
        )

    shoot_day_row = await prisma.shootday.find_unique(where={"id": body.shoot_day_id})
    if shoot_day_row is None or shoot_day_row.productionId != production_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShootDay {body.shoot_day_id!r} not found in production {production_id!r}",
        )

    # Mutate the in-memory dataclass (for parity with Phase 5's pure
    # function), then write the new shoot_day_id back via Prisma.
    scene_dc = _row_to_scene(scene_row)
    day_dc = _row_to_shoot_day(shoot_day_row)
    assign_scene_to_day(scene_dc, day_dc)

    try:
        updated = await prisma.scene.update(
            where={"id": body.scene_id},
            data={"shootDayId": body.shoot_day_id},
        )
    except Exception as exc:
        logger.exception("stripboard assign failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not assign scene: {exc}",
        )

    # `body.position` is accepted but currently ignored — there is no
    # `position` column on Scene yet (schema flagged as MVP).
    return updated


# =============================================================================
# 4. GET /{production_id}/dood
# =============================================================================


@router.get(
    "/{production_id}/dood",
    summary="Returns the Day Out of Days grid",
)
async def get_dood(production_id: str):
    await _load_production_or_404(production_id)
    scenes, shoot_days = await _load_scenes_and_shoot_days(production_id)
    cast = await _load_cast(production_id)
    return generate_dood(production_id, cast, shoot_days, scenes)


# =============================================================================
# 5. GET /{production_id}/dood/export
# =============================================================================


@router.get(
    "/{production_id}/dood/export",
    summary="Download the DOOD as CSV or PDF (?format=csv|pdf)",
)
async def export_dood(
    production_id: str,
    format: str = Query("csv", pattern="^(csv|pdf)$"),  # noqa: A002 — match brief
):
    production = await _load_production_or_404(production_id)
    scenes, shoot_days = await _load_scenes_and_shoot_days(production_id)
    cast = await _load_cast(production_id)
    grid = generate_dood(production_id, cast, shoot_days, scenes)

    if format == "csv":
        file_path = export_dood_csv(grid, cast, shoot_days, production_id=production_id)
        return FileResponse(
            file_path,
            media_type="text/csv",
            filename=os.path.basename(file_path),
        )
    if format == "pdf":
        file_path = export_dood_pdf(
            grid,
            cast,
            shoot_days,
            production_id=production_id,
            production_title=production.title,
        )
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=os.path.basename(file_path),
        )

    # Defensive: Query's pattern= should already block this branch.
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported export format {format!r}. Use csv or pdf.",
    )


# =============================================================================
# 6. GET /{production_id}/call-sheet/{day_number}
# =============================================================================


@router.get(
    "/{production_id}/call-sheet/{day_number}",
    summary="Returns the call sheet for one shoot day as JSON",
)
async def get_call_sheet_json(production_id: str, day_number: int):
    call_sheet = await _build_call_sheet_for_day(production_id, day_number)
    return export_call_sheet_json(call_sheet)


# =============================================================================
# 7. GET /{production_id}/call-sheet/{day_number}/pdf
# =============================================================================


@router.get(
    "/{production_id}/call-sheet/{day_number}/pdf",
    summary="Download the call sheet for one shoot day as a PDF",
)
async def get_call_sheet_pdf(production_id: str, day_number: int):
    production = await _load_production_or_404(production_id)
    call_sheet = await _build_call_sheet_for_day(
        production_id, day_number, production=production
    )
    file_path = export_call_sheet_pdf(
        call_sheet,
        production_title=production.title,
    )
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )


# =============================================================================
# 8. GET /{production_id}/jurisdiction-tracker
# =============================================================================


@router.get(
    "/{production_id}/jurisdiction-tracker",
    summary="Per-jurisdiction shoot-day summary for a production",
)
async def get_jurisdiction_tracker(production_id: str):
    await _load_production_or_404(production_id)
    try:
        rows = await prisma.jurisdictionshootdays.find_many(
            where={"productionId": production_id},
        )
        jur_rows = await prisma.jurisdiction.find_many()
    except Exception as exc:
        logger.exception("jurisdiction-tracker load failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load jurisdiction tracker: {exc}",
        )

    records = [_row_to_jsd(r) for r in rows]
    return get_jurisdiction_summary(production_id, records, jurisdictions=jur_rows)


# =============================================================================
# 9. POST /{production_id}/compliance-bridge/push
# =============================================================================


@router.post(
    "/{production_id}/compliance-bridge/push",
    summary="Push verified shoot-day counts to the Incentive Calculator payload",
)
async def push_compliance(production_id: str):
    await _load_production_or_404(production_id)

    try:
        rows = await prisma.jurisdictionshootdays.find_many(
            where={"productionId": production_id},
        )
    except Exception as exc:
        logger.exception("compliance push: jurisdictionshootdays read failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load verified shoot-day records: {exc}",
        )

    records = [_row_to_jsd(r) for r in rows]
    payload = push_shoot_days_to_calculator(production_id, records)
    logger.info(
        "compliance-bridge push: production=%s verified_records=%d",
        production_id, len(records),
    )
    return payload


# =============================================================================
# Private helpers
# =============================================================================


# Picks the importer for a given filename suffix. Returns
# (source_format, importer_callable) or (None, None) if unsupported.
def _dispatch_importer(filename: str) -> Tuple[Optional[str], Optional[Any]]:
    ext = Path(filename).suffix.lower()
    return _IMPORTERS.get(ext, (None, None))


# Looks up a production by id and raises 404 if missing. Returns the
# Prisma row so callers can read fields off it (title, etc.).
async def _load_production_or_404(production_id: str):
    try:
        production = await prisma.production.find_unique(where={"id": production_id})
    except Exception as exc:
        logger.exception("production lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not look up production: {exc}",
        )
    if production is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production {production_id!r} not found",
        )
    return production


# Loads scenes + shoot days for a production, returning them as
# in-memory dataclass objects so the generators / trackers can chew on
# them directly.
async def _load_scenes_and_shoot_days(
    production_id: str,
) -> Tuple[List[Scene], List[ShootDay]]:
    try:
        scene_rows = await prisma.scene.find_many(where={"productionId": production_id})
        shoot_day_rows = await prisma.shootday.find_many(
            where={"productionId": production_id},
        )
    except Exception as exc:
        logger.exception("scene/shootday load failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load scenes/shoot days: {exc}",
        )
    return (
        [_row_to_scene(r) for r in scene_rows],
        [_row_to_shoot_day(r) for r in shoot_day_rows],
    )


# Loads cast members for a production as in-memory dataclasses.
async def _load_cast(production_id: str) -> List[CastMember]:
    try:
        rows = await prisma.castmember.find_many(
            where={"productionId": production_id},
        )
    except Exception as exc:
        logger.exception("castmember load failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load cast members: {exc}",
        )
    return [_row_to_cast_member(r) for r in rows]


# Loads the production + shoot day + its scenes and builds an in-memory
# CallSheet via the Phase 7 generator. Used by both call-sheet endpoints.
async def _build_call_sheet_for_day(
    production_id: str,
    day_number: int,
    production=None,
) -> CallSheet:
    if production is None:
        production = await _load_production_or_404(production_id)

    try:
        day_row = await prisma.shootday.find_first(
            where={"productionId": production_id, "dayNumber": day_number},
        )
    except Exception as exc:
        logger.exception("call-sheet: shoot-day lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not look up shoot day {day_number}: {exc}",
        )
    if day_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Shoot day {day_number} not found in production {production_id!r}"
            ),
        )

    try:
        scene_rows = await prisma.scene.find_many(where={"shootDayId": day_row.id})
    except Exception as exc:
        logger.exception("call-sheet: scenes lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load scenes for shoot day {day_number}: {exc}",
        )

    scenes = [_row_to_scene(r) for r in scene_rows]
    day_dc = _row_to_shoot_day(day_row)
    # crew_calls is empty for now — no Crew model exists yet. The
    # exporters handle the empty case gracefully.
    call_sheet = generate_call_sheet(day_dc, scenes, [], production)

    # Resolve Scene.cast_ids (CastMember.id FK array) into characterName
    # strings for the rendered snapshot. The generator stays pure (no
    # DB access) per the Phase 9 contract.
    cm_rows = await prisma.castmember.find_many(where={"productionId": production_id})
    id_to_name = {cm.id: cm.characterName for cm in cm_rows}
    for snap in call_sheet.scenes or []:
        ids = snap.get("cast") or []
        snap["cast"] = [id_to_name.get(i, i) for i in ids]
    return call_sheet


# -----------------------------------------------------------------------------
# Prisma row → dataclass conversion
# -----------------------------------------------------------------------------


def _row_to_scene(row) -> Scene:
    return Scene(
        id=row.id,
        production_id=row.productionId,
        scene_number=row.sceneNumber,
        title=row.title,
        location=row.location,
        location_type=row.locationType,
        time_of_day=row.timeOfDay,
        page_count=row.pageCount,
        jurisdiction_id=row.jurisdictionId,
        cast_ids=list(row.castIds or []),
        notes=row.notes,
        shoot_day_id=row.shootDayId,
    )


def _row_to_shoot_day(row) -> ShootDay:
    return ShootDay(
        id=row.id,
        production_id=row.productionId,
        day_number=row.dayNumber,
        date=row.date,
        jurisdiction_id=row.jurisdictionId,
        total_pages=row.totalPages,
        call_time=row.callTime,
        location=row.location,
        nearest_hospital=row.nearestHospital,
        notes=row.notes,
    )


def _row_to_cast_member(row) -> CastMember:
    # Prisma stores doodEntries as JSON; the dataclass expects a dict.
    raw_dood = row.doodEntries
    if raw_dood is None or isinstance(raw_dood, dict):
        dood_entries = raw_dood or {}
    else:
        # Defensive: prisma-client-py returns JSON as dict/list by
        # default, but tolerate a string just in case.
        dood_entries = {}
    return CastMember(
        id=row.id,
        production_id=row.productionId,
        character_name=row.characterName,
        actor_name=row.actorName,
        dood_entries=dood_entries,
        start_day=row.startDay,
        finish_day=row.finishDay,
    )


def _row_to_jsd(row) -> JurisdictionShootDays:
    return JurisdictionShootDays(
        id=row.id,
        production_id=row.productionId,
        jurisdiction_id=row.jurisdictionId,
        shoot_days=row.shootDays,
        verified_at=row.verifiedAt,
    )


# -----------------------------------------------------------------------------
# Stripboard dict → JSON-serialisable dict
# -----------------------------------------------------------------------------


# build_stripboard returns Scene OBJECTS inside the per-day "scenes"
# list. FastAPI's JSON encoder can't serialise dataclasses by default,
# so flatten via dataclasses.asdict() before returning.
def _stripboard_to_json(grid: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for day_number, bucket in grid.items():
        out[day_number] = {
            "date":         bucket["date"],
            "jurisdiction": bucket["jurisdiction"],
            "total_pages":  bucket["total_pages"],
            "scenes":       [asdict(s) for s in bucket["scenes"]],
        }
    return out
