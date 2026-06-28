# =============================================================================
# src/services/production_schedule/models/scene.py
# The Scene dataclass â€” one scene from a script breakdown.
# Mirrors the `Scene` model in prisma/schema.prisma.
# A Scene is a PRODUCTION SHOOTING scene (location, int/ext, day/night, cast)
# â€” NOT a broadcast/playout record. See ScheduleEvent for the broadcast side.
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Optional


# A single scene from a script breakdown. Imported from CSV / Movie Magic
# Scheduling (.mms) / Final Draft (.fdx). Fields default to None so a partial
# row from any source format still produces a valid Scene object.
@dataclass
class Scene:
    # Script scene number, e.g. "12", "12A", "INSERT-3"
    scene_number: str

    # The Production this scene belongs to (set when the scene is persisted).
    production_id: Optional[str] = None

    # Database primary key. None until the scene is saved.
    id: Optional[str] = None

    # Short scene title or slugline â€” e.g. "POLICE STATION - INTERROGATION".
    title: Optional[str] = None

    # Location name as it appears in the breakdown â€” e.g. "POLICE STATION".
    location: Optional[str] = None

    # "INT" | "EXT" | "INT/EXT"
    location_type: Optional[str] = None

    # "DAY" | "NIGHT" | "DAWN" | "DUSK"
    time_of_day: Optional[str] = None

    # Page count in decimal pages (8/8 = 1.0).
    page_count: Optional[float] = None

    # Jurisdiction this scene shoots in (drives tax incentive eligibility).
    jurisdiction_id: Optional[str] = None

    # CastMember.id values for cast appearing in this scene. Denormalised
    # for MVP; swap to a join table if scene/cast queries get hot.
    cast_ids: List[str] = field(default_factory=list)

    # Free-text breakdown notes.
    notes: Optional[str] = None

    # The ShootDay this scene is pinned to in the stripboard, if any.
    shoot_day_id: Optional[str] = None

    # Returns a short summary when the Scene is printed (debugging aid).
    def __repr__(self) -> str:
        return (
            f"Scene(scene_number={self.scene_number!r}, "
            f"location={self.location!r}, "
            f"loc_type={self.location_type!r}, "
            f"time={self.time_of_day!r}, "
            f"pages={self.page_count!r})"
        )




