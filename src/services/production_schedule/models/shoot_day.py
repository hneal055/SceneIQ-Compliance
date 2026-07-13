# =============================================================================
# src/services/production_schedule/models/shoot_day.py
# The ShootDay dataclass â€” one shooting day on the stripboard.
# Mirrors the `ShootDay` model in prisma/schema.prisma.
# Holds an ordered set of scenes plus the day-level logistics (call time,
# location, nearest hospital) that flow into the generated call sheet.
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Optional

from src.services.production_schedule.models.scene import Scene


# One shooting day on the stripboard. Scene ordering is implicit by
# `Scene.scene_number` for MVP; if explicit ordering is needed later, add
# a `position` column on Scene and update the stripboard builder.
@dataclass
class ShootDay:
    # 1-based day number in shoot order â€” e.g. Day 1, Day 2, ...
    day_number: int

    # The Production this day belongs to (set when the day is persisted).
    production_id: Optional[str] = None

    # Database primary key. None until the day is saved.
    id: Optional[str] = None

    # ISO date string (YYYY-MM-DD). Kept as str to match the Prisma model.
    date: Optional[str] = None

    # Jurisdiction this day shoots in (drives the JurisdictionShootDayTracker).
    jurisdiction_id: Optional[str] = None

    # Scenes assigned to this day (populated by the stripboard builder).
    scenes: List[Scene] = field(default_factory=list)

    # Sum of `Scene.page_count` for all scenes on this day.
    total_pages: Optional[float] = None

    # Crew call time string, e.g. "06:00 AM".
    call_time: Optional[str] = None

    # Crew wrap time string, e.g. "11:30 PM".
    wrap_time: Optional[str] = None

    # Primary shooting location for the day.
    location: Optional[str] = None

    # Nearest hospital â€” required on every call sheet for safety.
    nearest_hospital: Optional[str] = None

    # Free-text production notes for the day.
    notes: Optional[str] = None

    # Per-day department call times: list of
    # {"department": str, "name": str, "call_time": str} dicts. Rendered in
    # the Crew Calls section of the generated call sheet.
    crew_calls: List[dict] = field(default_factory=list)

    # Returns a short summary when the ShootDay is printed (debugging aid).
    def __repr__(self) -> str:
        return (
            f"ShootDay(day_number={self.day_number}, "
            f"date={self.date!r}, "
            f"scenes={len(self.scenes)}, "
            f"total_pages={self.total_pages!r})"
        )




