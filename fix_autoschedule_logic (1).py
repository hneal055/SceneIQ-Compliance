content = open('src/api/production_schedule.py', 'r', encoding='utf-8').read()

old = '''@router.post(
    "/{production_id}/stripboard/auto-schedule",
    summary="Auto-create shoot days from unscheduled scenes based on pages per day",
)
async def auto_schedule(
    production_id: str,
    pages_per_day: float = Query(default=8.0, ge=4.0, le=10.0, description="Pages per shoot day (industry standard: 4-10)"),
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
            order={"sceneNumber": "asc"},
        )

        if not scene_rows:
            return {"days_created": 0, "scenes_assigned": 0, "message": "No unscheduled scenes found"}

        # Get current max day number
        existing_days = await prisma.shootday.find_many(
            where={"productionId": production_id},
            order={"dayNumber": "desc"},
        )
        next_day_number = (existing_days[0].dayNumber + 1) if existing_days else 1

        days_created = 0
        scenes_assigned = 0
        current_day = None
        current_day_pages = 0.0

        for row in scene_rows:
            page_count = float(row.pageCount or 0.0)

            # Create a new shoot day if needed
            if current_day is None or (current_day_pages + page_count > pages_per_day and current_day_pages > 0):
                current_day = await prisma.shootday.create(
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
        raise HTTPException(status_code=500, detail=str(exc))'''

new = '''@router.post(
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
        existing_days = await prisma.shootday.find_many(
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
                current_day = await prisma.shootday.create(
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
        raise HTTPException(status_code=500, detail=str(exc))'''

if old in content:
    content = content.replace(old, new, 1)
    open('src/api/production_schedule.py', 'w', encoding='utf-8').write(content)
    print('SUCCESS - auto_schedule logic fixed')
else:
    print('NOT FOUND - trying partial match')
    if 'auto_schedule' in content:
        print('auto_schedule function exists but text changed')
    else:
        print('auto_schedule not found at all')
