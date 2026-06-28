# =============================================================================
# src/services/production_schedule/models/cast_member.py
# The CastMember dataclass â€” one cast member on a production.
# Mirrors the `CastMember` model in prisma/schema.prisma.
# Used to render the Day Out of Days (DOOD) grid.
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Optional


# A single cast member tracked by the DOOD generator. `dood_entries` is a
# dict keyed by ISO date with a status-code value:
#   S  = Start
#   W  = Work
#   H  = Hold
#   T  = Travel
#   F  = Finish
#   SW = Start + Work (same day)
#   WF = Work + Finish (same day)
@dataclass
class CastMember:
    # Character name as it appears in the script â€” e.g. "DETECTIVE MARSH".
    character_name: str

    # The Production this cast member belongs to.
    production_id: Optional[str] = None

    # Database primary key. None until the record is saved.
    id: Optional[str] = None

    # Real-world actor name. Optional â€” many breakdowns leave this blank.
    actor_name: Optional[str] = None

    # Per-day DOOD status codes keyed by ISO date, e.g.
    #   { "2026-01-15": "W", "2026-01-16": "H" }
    dood_entries: Dict[str, str] = field(default_factory=dict)

    # First shoot day number this cast member appears on (derived).
    start_day: Optional[int] = None

    # Last shoot day number this cast member appears on (derived).
    finish_day: Optional[int] = None

    # Returns a short summary when the CastMember is printed (debugging aid).
    def __repr__(self) -> str:
        return (
            f"CastMember(character={self.character_name!r}, "
            f"actor={self.actor_name!r}, "
            f"start={self.start_day}, finish={self.finish_day})"
        )




