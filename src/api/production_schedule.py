"""
Production Schedule Engine API endpoints.

Wires every Phase 2â€“9 service module into FastAPI:
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
    pure-sync (see Phases 2â€“9); the router calls them directly
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
    CreateShootDayBody,
    ImportResponse,
    UnassignSceneBody,
    UpdateShootDayBody,
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
    count_shoot_days_per_jurisdiction,
    get_jurisdiction_summary,
    verify_shoot_days,
)
from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/production-schedule", tags=["Production Schedule"])


# File-extension â†’ importer-function dispatch. Mirrors the broadcast
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

        # Build a name â†’ Jurisdiction.id lookup once so per-scene FK
        # resolution is O(1). The importer stashes jurisdiction NAMES
        # in scene.jurisdiction_id (raw pipeline convention).
        jur_rows = await prisma.jurisdiction.find_many()
        name_to_id = {j.name: j.id for j in jur_rows}

        # Phase 11.5 fix #2 â€” dedup by (productionId, sceneNumber).
        # Load existing scene numbers so re-uploads skip duplicates
        # instead of creating phantom rows.
        existing_scene_rows = await prisma.scene.find_many(
            where={"productionId": production.id},
        )
        existing_scene_numbers = {r.sceneNumber for r in existing_scene_rows}

        # Phase 11.5 fix #5 â€” collect unique cast names across all parsed
        # scenes, then ensure a CastMember row exists for each. Scene.castIds
        # is the FK array of CastMember.id values (matches DOOD generator
        # and the Phase 12 call-sheet resolution).
        unique_cast_names = []
        seen_names: set = set()
        for s in scenes:
            for cast_name in (s.cast_ids or []):
                if cast_name and cast_name not in seen_names:
                    seen_names.add(cast_name)
                    unique_cast_names.append(cast_name)

        existing_cm_rows = await prisma.cast_members.find_many(
            where={"productionId": production.id},
        )
        cast_name_to_id = {cm.characterName: cm.id for cm in existing_cm_rows}
        for cast_name in unique_cast_names:
            if cast_name not in cast_name_to_id:
                try:
                    cm = await prisma.cast_members.create(
                        data={
                            "productionId":  production.id,
                            "characterName": cast_name,
                        }
                    )
                    cast_name_to_id[cast_name] = cm.id
                except Exception:
                    logger.exception(
                        "production-schedule import: failed to create CastMember %s",
                        cast_name,
                    )
                    warnings.append(
                        f"Cast member {cast_name!r} could not be created â€” see server log"
                    )

        for scene in scenes:
            raw_name = scene.jurisdiction_id
            if raw_name:
                jurisdictions_detected_set.add(raw_name)

            resolved_jid = name_to_id.get(raw_name) if raw_name else None
            if raw_name and resolved_jid is None:
                warnings.append(
                    f"Jurisdiction {raw_name!r} not found in DB â€” "
                    f"scene {scene.scene_number} persisted with no FK"
                )

            # Fix #2 dedup check (also catches in-file duplicates by
            # adding to the set as we go).
            if scene.scene_number and scene.scene_number in existing_scene_numbers:
                warnings.append(
                    f"Scene {scene.scene_number!r} already exists for this production â€” skipped"
                )
                continue

            # Fix #5 â€” rewrite cast names â†’ CastMember.id values for storage.
            resolved_cast_ids = [
                cast_name_to_id[n]
                for n in (scene.cast_ids or [])
                if n in cast_name_to_id
            ]

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
                        "castIds":        resolved_cast_ids,
                        "notes":          scene.notes,
                    }
                )
                scenes_imported += 1
                if scene.scene_number:
                    existing_scene_numbers.add(scene.scene_number)
            except Exception:
                logger.exception(
                    "production-schedule import: failed to save scene %s",
                    scene.scene_number,
                )
                warnings.append(
                    f"Scene {scene.scene_number!r} could not be saved â€” see server log"
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
    summary="Returns the stripboard: scheduled days plus the Unscheduled bin",
)
async def get_stripboard(production_id: str):
    await _load_production_or_404(production_id)
    scenes, shoot_days = await _load_scenes_and_shoot_days(production_id)
    grid = build_stripboard(scenes, shoot_days)

    # Phase 11.5 fix #1 â€” resolve jurisdiction + cast IDs to display
    # names for the dashboard. Field NAMES are preserved; only values
    # swap. Matches the Phase 12 call-sheet resolution pattern.
    jur_rows = await prisma.jurisdiction.find_many()
    jur_id_to_name = {j.id: j.name for j in jur_rows}
    cm_rows = await prisma.cast_members.find_many(
        where={"productionId": production_id},
    )
    cm_id_to_name = {cm.id: cm.characterName for cm in cm_rows}
    return _stripboard_payload(scenes, shoot_days, grid, jur_id_to_name, cm_id_to_name)


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

    shoot_day_row = await prisma.shoot_days.find_unique(where={"id": body.shoot_day_id})
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

    # Phase 11.5 fix #3 â€” roll up the shoot-day count per jurisdiction
    # into JurisdictionShootDays. Wrapped in try/except so a rollup
    # failure doesn't break the primary assign action; the user's
    # action already succeeded by this point.
    try:
        await _rollup_jurisdiction_shoot_days(production_id)
    except Exception:
        logger.exception("stripboard assign: jurisdiction rollup failed")

    # `body.position` is accepted but currently ignored â€” there is no
    # `position` column on Scene yet (schema flagged as MVP).
    return updated


# =============================================================================
# 3b. POST /{production_id}/stripboard/unassign
# =============================================================================


@router.post(
    "/{production_id}/stripboard/unassign",
    summary="Move a scene back to the Unscheduled bin (clears its shoot day)",
)
async def unassign_scene(production_id: str, body: UnassignSceneBody):
    await _load_production_or_404(production_id)

    scene_row = await prisma.scene.find_unique(where={"id": body.scene_id})
    if scene_row is None or scene_row.productionId != production_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {body.scene_id!r} not found in production {production_id!r}",
        )

    try:
        updated = await prisma.scene.update(
            where={"id": body.scene_id},
            data={"shootDayId": None},
        )
    except Exception as exc:
        logger.exception("stripboard unassign failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not unassign scene: {exc}",
        )

    # Keep the jurisdiction rollup in sync; non-fatal if it fails.
    try:
        await _rollup_jurisdiction_shoot_days(production_id)
    except Exception:
        logger.exception("stripboard unassign: jurisdiction rollup failed")

    return updated


# =============================================================================
# 3c. POST /{production_id}/shoot-days   +   DELETE /{production_id}/shoot-days/{id}
# =============================================================================


@router.post(
    "/{production_id}/shoot-days",
    summary="Create a new (initially empty) shoot day; day_number is auto-assigned",
)
async def create_shoot_day(production_id: str, body: CreateShootDayBody):
    await _load_production_or_404(production_id)

    # Auto-assign the next day_number = max(existing) + 1. The
    # (productionId, dayNumber) unique constraint guarantees no collision
    # for a single create; concurrent creates are not expected in the MVP.
    try:
        existing = await prisma.shoot_days.find_many(
            where={"productionId": production_id},
        )
    except Exception as exc:
        logger.exception("create shoot day: existing-day load failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load existing shoot days: {exc}",
        )
    next_day_number = (max((d.dayNumber for d in existing), default=0)) + 1

    # Resolve the optional jurisdiction NAME â†’ FK id (same idiom as import).
    resolved_jid = None
    if body.jurisdiction_name:
        jur_rows = await prisma.jurisdiction.find_many()
        resolved_jid = {j.name: j.id for j in jur_rows}.get(body.jurisdiction_name)

    try:
        day = await prisma.shoot_days.create(
            data={
                "productionId":    production_id,
                "dayNumber":       next_day_number,
                "date":            body.date,
                "jurisdictionId":  resolved_jid,
                "callTime":        body.call_time,
                "location":        body.location,
                "nearestHospital": body.nearest_hospital,
                "notes":           body.notes,
            }
        )
    except Exception as exc:
        logger.exception("create shoot day failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create shoot day: {exc}",
        )

    logger.info(
        "shoot-day created: production=%s day_number=%d id=%s",
        production_id, next_day_number, day.id,
    )
    return day


@router.patch(
    "/{production_id}/shoot-days/{shoot_day_id}",
    summary="Update a shoot day's logistics (date, call time, location, hospital, notes)",
)
async def update_shoot_day(
    production_id: str, shoot_day_id: str, body: UpdateShootDayBody
):
    await _load_production_or_404(production_id)

    day_row = await prisma.shoot_days.find_unique(where={"id": shoot_day_id})
    if day_row is None or day_row.productionId != production_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShootDay {shoot_day_id!r} not found in production {production_id!r}",
        )

    # Resolve the optional jurisdiction NAME â†’ FK id (same idiom as create).
    # An empty/blank name clears the day's jurisdiction.
    resolved_jid = None
    if body.jurisdiction_name:
        jur_rows = await prisma.jurisdiction.find_many()
        resolved_jid = {j.name: j.id for j in jur_rows}.get(body.jurisdiction_name)

    # crew_calls is a full-replacement list; serialise to plain dicts for the
    # JSON column. None means "not supplied" â†’ leave the existing value alone.
    crew_calls_json = (
        [c.model_dump() for c in body.crew_calls]
        if body.crew_calls is not None
        else None
    )

    # The edit form sends every field, so overwrite them all (a blank value
    # clears the field). scene assignments are managed separately.
    data = {
        "date":            body.date,
        "jurisdictionId":  resolved_jid,
        "callTime":        body.call_time,
        "location":        body.location,
        "nearestHospital": body.nearest_hospital,
        "notes":           body.notes,
    }
    if crew_calls_json is not None:
        data["crewCalls"] = crew_calls_json

    try:
        updated = await prisma.shoot_days.update(where={"id": shoot_day_id}, data=data)
    except Exception as exc:
        logger.exception("update shoot day failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update shoot day: {exc}",
        )

    # A jurisdiction change shifts the per-jurisdiction shoot-day counts;
    # re-roll the tracker. Non-fatal if it fails â€” the edit already saved.
    try:
        await _rollup_jurisdiction_shoot_days(production_id)
    except Exception:
        logger.exception("update shoot day: jurisdiction rollup failed")

    logger.info("shoot-day updated: production=%s id=%s", production_id, shoot_day_id)
    return updated


@router.delete(
    "/{production_id}/shoot-days/{shoot_day_id}",
    summary="Delete a shoot day; its scenes return to the Unscheduled bin",
)
async def delete_shoot_day(production_id: str, shoot_day_id: str):
    await _load_production_or_404(production_id)

    day_row = await prisma.shoot_days.find_unique(where={"id": shoot_day_id})
    if day_row is None or day_row.productionId != production_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShootDay {shoot_day_id!r} not found in production {production_id!r}",
        )

    # Scene.shootDayId has onDelete: SetNull, so deleting the day
    # automatically returns its scenes to the Unscheduled bin.
    try:
        await prisma.shoot_days.delete(where={"id": shoot_day_id})
    except Exception as exc:
        logger.exception("delete shoot day failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete shoot day: {exc}",
        )

    try:
        await _rollup_jurisdiction_shoot_days(production_id)
    except Exception:
        logger.exception("delete shoot day: jurisdiction rollup failed")

    return {"deleted": shoot_day_id}


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
    grid = generate_dood(production_id, cast, shoot_days, scenes)

    # Resolve CastMember.id grid keys to character names for the
    # dashboard. Same idiom as the stripboard + call-sheet resolutions.
    # CSV / PDF exports already use cm.character_name internally â€”
    # only the JSON endpoint leaks raw IDs to the dashboard.
    cm_id_to_name = {cm.id: cm.character_name for cm in cast}
    return {cm_id_to_name.get(k, k): v for k, v in grid.items()}


# =============================================================================
# 5. GET /{production_id}/dood/export
# =============================================================================


@router.get(
    "/{production_id}/dood/export",
    summary="Download the DOOD as CSV or PDF (?format=csv|pdf)",
)
async def export_dood(
    production_id: str,
    format: str = Query("csv", pattern="^(csv|pdf)$"),  # noqa: A002 â€” match brief
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
# 9. POST /{production_id}/jurisdiction-tracker/verify     (Phase 11.5 fix #4)
# =============================================================================


@router.post(
    "/{production_id}/jurisdiction-tracker/verify",
    summary="Mark all jurisdiction shoot-day records for the production as verified",
)
async def verify_jurisdiction_tracker(production_id: str):
    await _load_production_or_404(production_id)
    try:
        rows = await prisma.jurisdictionshootdays.find_many(
            where={"productionId": production_id},
        )
    except Exception as exc:
        logger.exception("jurisdiction-tracker verify: read failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load shoot-day records: {exc}",
        )

    records = [_row_to_jsd(r) for r in rows]
    if not records:
        return {"verified": 0, "verified_at": None}

    # Pure compute: mutates records in place, returns the same list.
    verify_shoot_days(production_id, records)
    timestamp = records[0].verified_at

    for rec in records:
        try:
            await prisma.jurisdictionshootdays.update(
                where={"id": rec.id},
                data={"verifiedAt": timestamp},
            )
        except Exception:
            logger.exception(
                "jurisdiction-tracker verify: update failed for %s", rec.id
            )

    logger.info(
        "jurisdiction-tracker verify: production=%s verified=%d at=%s",
        production_id, len(records), timestamp,
    )
    return {"verified": len(records), "verified_at": timestamp}


# =============================================================================
# 10. POST /{production_id}/compliance-bridge/push
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

    # Phase 11.5 fix #4 â€” filter to verified-only rows in Python (the
    # prisma-client-py `{"not": None}` filter syntax doesn't work for
    # nullable DateTime; this is what failed in Phase 12). With
    # verifiedAt now nullable, this restores the Phase 9 design intent:
    # ComplianceBridge only pushes verified rows downstream.
    rows = [r for r in rows if r.verifiedAt is not None]

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
        shoot_day_rows = await prisma.shoot_days.find_many(
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


# Phase 11.5 fix #3 â€” recomputes shoot-day-per-jurisdiction counts
# and reconciles the JurisdictionShootDays table. Called from
# assign_scene; safe to call repeatedly. Pure compute is delegated to
# count_shoot_days_per_jurisdiction(); this function owns the Prisma
# upsert / delete.
async def _rollup_jurisdiction_shoot_days(production_id: str) -> None:
    day_rows = await prisma.shoot_days.find_many(
        where={"productionId": production_id},
    )
    day_dcs = [_row_to_shoot_day(r) for r in day_rows]
    counts = count_shoot_days_per_jurisdiction(production_id, day_dcs)

    existing = await prisma.jurisdictionshootdays.find_many(
        where={"productionId": production_id},
    )
    existing_by_jur = {r.jurisdictionId: r for r in existing}

    # Upsert each jurisdiction that has at least one shoot day pinned.
    for jur_id, count in counts.items():
        existing_row = existing_by_jur.get(jur_id)
        if existing_row is None:
            await prisma.jurisdictionshootdays.create(
                data={
                    "productionId":   production_id,
                    "jurisdictionId": jur_id,
                    "shootDays":      count,
                }
            )
        elif existing_row.shootDays != count:
            await prisma.jurisdictionshootdays.update(
                where={"id": existing_row.id},
                data={"shootDays": count},
            )

    # Drop any aggregate rows whose jurisdiction no longer has scenes.
    for jur_id, existing_row in existing_by_jur.items():
        if jur_id not in counts:
            await prisma.jurisdictionshootdays.delete(
                where={"id": existing_row.id},
            )


# Loads cast members for a production as in-memory dataclasses.
async def _load_cast(production_id: str) -> List[CastMember]:
    try:
        rows = await prisma.cast_members.find_many(
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
        day_row = await prisma.shoot_days.find_first(
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
    # Crew calls are stored per-day on ShootDay.crewCalls (edited from the
    # stripboard) and flow straight into the call sheet's Crew Calls table.
    call_sheet = generate_call_sheet(day_dc, scenes, day_dc.crew_calls, production)

    # Resolve Scene.cast_ids (CastMember.id FK array) into characterName
    # strings for the rendered snapshot. The generator stays pure (no
    # DB access) per the Phase 9 contract.
    cm_rows = await prisma.cast_members.find_many(where={"productionId": production_id})
    id_to_name = {cm.id: cm.characterName for cm in cm_rows}
    for snap in call_sheet.scenes or []:
        ids = snap.get("cast") or []
        snap["cast"] = [id_to_name.get(i, i) for i in ids]
    return call_sheet


# -----------------------------------------------------------------------------
# Prisma row â†’ dataclass conversion
# -----------------------------------------------------------------------------




@router.post(
    "/{production_id}/stripboard/auto-schedule",
    summary="Auto-create shoot days from unscheduled scenes based on pages per day",
)
async def auto_schedule(
    production_id: str,
    pages_per_day: float = Query(default=8.0, ge=1.0, le=20.0, description="Pages per shoot day (industry standard: 4-10)"),
):
    """
    Creates shoot days automatically from unscheduled scenes.
    Groups scenes into days based on page count (default 8 pages/day).
    Industry standard range: 4-10 pages per day.
    """
    try:
        # Load all unscheduled scenes
        scene_rows = await prisma.scene.find_many(
            where={"productionId": production_id, "shootDayId": None},
        )

        if not scene_rows:
            return {"days_created": 0, "scenes_assigned": 0, "message": "No unscheduled scenes found"}

        # Sort scenes numerically by scene number where possible
        def scene_sort_key(s):
            try:
                return (0, float(s.sceneNumber or 0))
            except (ValueError, TypeError):
                return (1, str(s.sceneNumber or ""))

        scene_rows = sorted(scene_rows, key=scene_sort_key)

        # Get current max day number
        existing_days = await prisma.shoot_days.find_many(
            where={"productionId": production_id},
            order={"dayNumber": "desc"},
        )
        next_day_number = (existing_days[0].dayNumber + 1) if existing_days else 1

        days_created = 0
        scenes_assigned = 0
        current_day = None
        current_day_pages = 0.0

        for row in scene_rows:
            page_count = float(row.pageCount or 0.5)  # Default 0.5 pages if no page count

            # Create a new shoot day if:
            # - No current day exists yet
            # - Adding this scene would exceed pages_per_day (and we already have pages)
            needs_new_day = (
                current_day is None or
                (current_day_pages > 0 and current_day_pages + page_count > pages_per_day)
            )

            if needs_new_day:
                current_day = await prisma.shoot_days.create(
                    data={
                        "productionId": production_id,
                        "dayNumber": next_day_number,
                    }
                )
                next_day_number += 1
                days_created += 1
                current_day_pages = 0.0

            # Assign scene to current day
            await prisma.scene.update(
                where={"id": row.id},
                data={"shootDayId": current_day.id},
            )
            current_day_pages += page_count
            scenes_assigned += 1

        return {
            "days_created": days_created,
            "scenes_assigned": scenes_assigned,
            "pages_per_day": pages_per_day,
            "message": f"Created {days_created} shoot days and assigned {scenes_assigned} scenes at {pages_per_day} pages/day",
        }

    except Exception as exc:
        logger.exception("auto_schedule error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


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
    # crewCalls is JSON; prisma-client-py returns it as a list/dict (or None).
    raw_crew = getattr(row, "crewCalls", None)
    crew_calls = list(raw_crew) if isinstance(raw_crew, list) else []
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
        crew_calls=crew_calls,
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
# Stripboard dict â†’ JSON-serialisable dict
# -----------------------------------------------------------------------------


# Flattens a Scene dataclass to a JSON-serialisable snapshot dict, resolving
# the raw jurisdiction + cast-member UUIDs to human-readable names. Field
# NAMES are preserved (`jurisdiction_id`, `cast_ids`) so the dashboard reads
# them as-is; unknown IDs fall back to the raw value (defensive). Shared by
# both the scheduled-day buckets and the Unscheduled bin.
def _scene_snapshot(
    scene: Scene,
    jur_id_to_name: Dict[str, str],
    cm_id_to_name: Dict[str, str],
) -> Dict[str, Any]:
    snap = asdict(scene)
    jid = snap.get("jurisdiction_id")
    if jid:
        snap["jurisdiction_id"] = jur_id_to_name.get(jid, jid)
    cast_ids = snap.get("cast_ids") or []
    snap["cast_ids"] = [cm_id_to_name.get(c, c) for c in cast_ids]
    return snap


# Builds the full stripboard payload the dashboard consumes:
#   {
#     "days": [ {id, day_number, date, jurisdiction, total_pages, scenes:[...]} ],
#     "unscheduled": { "scenes": [...], "total_pages": float }
#   }
#
# `days` carries the ShootDay.id so the frontend can assign/unassign scenes
# and delete the day. `unscheduled` holds every scene with no shoot day â€”
# this is what makes freshly-imported scenes visible before they're
# scheduled. `grid` is build_stripboard()'s output (keyed by day_number);
# we walk shoot_days (not the grid) so the day's id + ordering come straight
# from the DB rows.
def _stripboard_payload(
    scenes: List[Scene],
    shoot_days: List[ShootDay],
    grid: Dict[int, Dict[str, Any]],
    jur_id_to_name: Dict[str, str] = None,
    cm_id_to_name: Dict[str, str] = None,
) -> Dict[str, Any]:
    jur_id_to_name = jur_id_to_name or {}
    cm_id_to_name = cm_id_to_name or {}

    days_out: List[Dict[str, Any]] = []
    for day in sorted(shoot_days, key=lambda d: d.day_number):
        bucket = grid.get(day.day_number, {"date": day.date, "jurisdiction": day.jurisdiction_id, "scenes": [], "total_pages": 0.0})
        raw_jur = bucket.get("jurisdiction")
        days_out.append({
            "id":              day.id,
            "day_number":      day.day_number,
            "date":            bucket.get("date"),
            "jurisdiction":    jur_id_to_name.get(raw_jur, raw_jur) if raw_jur else raw_jur,
            "call_time":       day.call_time,
            "location":        day.location,
            "nearest_hospital": day.nearest_hospital,
            "notes":           day.notes,
            "crew_calls":      day.crew_calls,
            "total_pages":     bucket.get("total_pages", 0.0),
            "scenes":          [_scene_snapshot(s, jur_id_to_name, cm_id_to_name) for s in bucket.get("scenes", [])],
        })

    unscheduled_scenes = [s for s in scenes if s.shoot_day_id is None]
    unscheduled_scenes.sort(key=lambda s: s.scene_number or "")
    return {
        "days": days_out,
        "unscheduled": {
            "scenes":      [_scene_snapshot(s, jur_id_to_name, cm_id_to_name) for s in unscheduled_scenes],
            "total_pages": sum((s.page_count or 0.0) for s in unscheduled_scenes),
        },
    }


