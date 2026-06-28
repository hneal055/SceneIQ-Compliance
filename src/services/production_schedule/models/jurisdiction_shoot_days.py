# =============================================================================
# src/services/production_schedule/models/jurisdiction_shoot_days.py
# The JurisdictionShootDays dataclass â€” aggregate shoot-day counts per
# jurisdiction for a production. Mirrors the prisma model of the same name.
# Populated by the JurisdictionShootDayTracker and consumed by the
# ComplianceBridge to feed the Incentive Calculator.
# =============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# One row per (production, jurisdiction) pair. `verified_at` is only set
# when a user explicitly clicks "Verify" in the dashboard â€” the
# ComplianceBridge ignores rows that have not been verified.
@dataclass
class JurisdictionShootDays:
    # The Production these counts belong to.
    production_id: str

    # The Jurisdiction these counts are aggregated for.
    jurisdiction_id: str

    # Database primary key. None until the record is saved.
    id: Optional[str] = None

    # Number of shoot days assigned to this jurisdiction in the stripboard.
    shoot_days: int = 0

    # Timestamp the count was marked verified by a user. Defaults to "now"
    # to match the Prisma model's @default(now()).
    verified_at: Optional[datetime] = None

    # Returns a short summary when the record is printed (debugging aid).
    def __repr__(self) -> str:
        return (
            f"JurisdictionShootDays(production={self.production_id!r}, "
            f"jurisdiction={self.jurisdiction_id!r}, "
            f"shoot_days={self.shoot_days}, "
            f"verified_at={self.verified_at!r})"
        )




