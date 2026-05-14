# =============================================================================
# tests/test_jurisdiction_tracker.py
# Phase 8 verification — exercises the JurisdictionShootDayTracker at
# src/services/production_schedule/trackers/jurisdiction_tracker.py.
#
# Fixture mirrors the user's verification spec: 3 Georgia days + 2
# New York days = 5 shoot days total.
# =============================================================================

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytest

from src.services.production_schedule.models.jurisdiction_shoot_days import (
    JurisdictionShootDays,
)
from src.services.production_schedule.models.shoot_day import ShootDay
from src.services.production_schedule.trackers.jurisdiction_tracker import (
    count_shoot_days_per_jurisdiction,
    get_jurisdiction_summary,
    verify_shoot_days,
)


# Lightweight stand-in for the SceneIQ Jurisdiction model — the tracker
# only reads .id and .name when resolving names for the summary.
@dataclass
class _JurisdictionStub:
    id: str
    name: str


@pytest.fixture
def five_shoot_days():
    """3 Georgia + 2 New York shoot days."""
    return [
        ShootDay(id="day-1", day_number=1, jurisdiction_id="Georgia"),
        ShootDay(id="day-2", day_number=2, jurisdiction_id="Georgia"),
        ShootDay(id="day-3", day_number=3, jurisdiction_id="Georgia"),
        ShootDay(id="day-4", day_number=4, jurisdiction_id="New York"),
        ShootDay(id="day-5", day_number=5, jurisdiction_id="New York"),
    ]


def test_count_shoot_days_per_jurisdiction_basic(five_shoot_days):
    counts = count_shoot_days_per_jurisdiction("prod-test", five_shoot_days)
    assert counts == {"Georgia": 3, "New York": 2}


def test_count_unassigned_returns_empty_dict():
    # No days at all → empty dict.
    assert count_shoot_days_per_jurisdiction("prod-test", []) == {}

    # A day with jurisdiction_id=None is excluded, not crashed on.
    one_unassigned = [ShootDay(id="day-x", day_number=1, jurisdiction_id=None)]
    assert count_shoot_days_per_jurisdiction("prod-test", one_unassigned) == {}


def test_get_jurisdiction_summary_structure():
    records = [
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="Georgia",
            shoot_days=3,
            verified_at=None,
        ),
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="New York",
            shoot_days=2,
            verified_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        ),
    ]
    # Optional lookup — for the in-memory pipeline these "ids" ARE names,
    # but the lookup still applies if provided. Here we map only Georgia
    # to demonstrate fallback behaviour for unmapped rows.
    jurisdictions = [_JurisdictionStub(id="Georgia", name="State of Georgia")]

    summary = get_jurisdiction_summary("prod-test", records, jurisdictions=jurisdictions)

    assert len(summary) == 2
    required_keys = {"jurisdiction_id", "jurisdiction_name", "shoot_days", "verified_at"}
    for row in summary:
        assert set(row.keys()) == required_keys

    # Order matches the input records order.
    assert summary[0]["jurisdiction_id"] == "Georgia"
    assert summary[0]["jurisdiction_name"] == "State of Georgia"  # resolved
    assert summary[0]["shoot_days"] == 3
    assert summary[0]["verified_at"] is None

    assert summary[1]["jurisdiction_id"] == "New York"
    # No name in the lookup — falls back to jurisdiction_id.
    assert summary[1]["jurisdiction_name"] == "New York"
    assert summary[1]["shoot_days"] == 2
    assert isinstance(summary[1]["verified_at"], datetime)


def test_verify_shoot_days_sets_verified_at():
    records = [
        JurisdictionShootDays(production_id="prod-test", jurisdiction_id="Georgia", shoot_days=3),
        JurisdictionShootDays(production_id="prod-test", jurisdiction_id="New York", shoot_days=2),
    ]
    # All records start unverified.
    assert all(r.verified_at is None for r in records)

    # Default-now path: every record gets a datetime stamp.
    returned = verify_shoot_days("prod-test", records)
    assert returned is records  # mutation + return-same-object idiom
    for r in records:
        assert isinstance(r.verified_at, datetime)

    # Injected-now path: timestamps take the supplied value exactly.
    pinned = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    verify_shoot_days("prod-test", records, now=pinned)
    for r in records:
        assert r.verified_at == pinned
