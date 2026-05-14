# =============================================================================
# src/services/production_schedule/models/call_sheet.py
# The CallSheet dataclass — generated call sheet for a single shoot day.
# Mirrors the `CallSheet` model in prisma/schema.prisma.
# Persisted so previously generated sheets remain reproducible even after
# the stripboard changes.
# =============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# A generated call sheet for one shoot day. `scenes` and `crew_calls` are
# JSON snapshots at generation time — the source ShootDay can be reordered
# afterwards without changing what this call sheet says.
@dataclass
class CallSheet:
    # 1-based day number this call sheet covers (matches ShootDay.day_number).
    day_number: int

    # The ShootDay this call sheet was generated from.
    shoot_day_id: str

    # The Production this call sheet belongs to.
    production_id: Optional[str] = None

    # Database primary key. None until the record is saved.
    id: Optional[str] = None

    # ISO date string (YYYY-MM-DD) for the shoot day this sheet covers.
    date: Optional[str] = None

    # General crew call time — e.g. "06:00 AM".
    general_call: Optional[str] = None

    # Primary shooting location for the day.
    location: Optional[str] = None

    # Nearest hospital — required on every call sheet for safety.
    nearest_hospital: Optional[str] = None

    # Free-text weather summary. Placeholder for now; can be populated via a
    # weather API later.
    weather: Optional[str] = None

    # Snapshot of the scene list at generation time. Each entry is a dict
    # so the call sheet stays valid even if the live Scene record changes.
    scenes: List[Dict[str, Any]] = field(default_factory=list)

    # Department crew-call table, e.g.
    #   [{"department": "Camera", "call": "05:30 AM"}, ...]
    crew_calls: List[Dict[str, Any]] = field(default_factory=list)

    # Returns a short summary when the CallSheet is printed (debugging aid).
    def __repr__(self) -> str:
        return (
            f"CallSheet(day={self.day_number}, "
            f"date={self.date!r}, "
            f"scenes={len(self.scenes)}, "
            f"location={self.location!r})"
        )
