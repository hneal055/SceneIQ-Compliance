# =============================================================================
# tests/test_dood.py
# Phase 6 verification — exercises the Day Out of Days generator at
# src/services/production_schedule/generators/dood.py.
#
# Fixture builds a tight cast/scene/day arrangement designed to hit
# every interesting DOOD code path:
#   - MARSH appears on days 1, 2, 3        →  SW / W  / WF
#   - ROOKIE appears on days 1 and 3 only  →  SW / H  / WF
#   - SOLO_GUEST appears on day 2 only     →   - / SWF /  -
#   - NOWHERE has no scenes                →  omitted from the grid entirely
# =============================================================================

import csv
import os

import pytest

from src.services.production_schedule.generators.dood import (
    export_dood_csv,
    export_dood_pdf,
    generate_dood,
)
from src.services.production_schedule.models.cast_member import CastMember
from src.services.production_schedule.models.scene import Scene
from src.services.production_schedule.models.shoot_day import ShootDay


@pytest.fixture
def fixture():
    """Three shoot days, four cast members, six scenes wiring it together."""
    days = [
        ShootDay(id="day-1", day_number=1, date="2026-01-15", jurisdiction_id="Georgia"),
        ShootDay(id="day-2", day_number=2, date="2026-01-16", jurisdiction_id="Georgia"),
        ShootDay(id="day-3", day_number=3, date="2026-01-17", jurisdiction_id="Georgia"),
    ]

    cast = [
        CastMember(id="cm-marsh",   character_name="MARSH"),
        CastMember(id="cm-rookie",  character_name="ROOKIE"),
        CastMember(id="cm-solo",    character_name="SOLO_GUEST"),
        CastMember(id="cm-nowhere", character_name="NOWHERE"),
    ]

    scenes = [
        # Day 1: MARSH + ROOKIE
        Scene(scene_number="1", shoot_day_id="day-1", cast_ids=["cm-marsh", "cm-rookie"]),
        Scene(scene_number="2", shoot_day_id="day-1", cast_ids=["cm-marsh"]),
        # Day 2: MARSH (alone) and SOLO_GUEST (alone)
        Scene(scene_number="3", shoot_day_id="day-2", cast_ids=["cm-marsh"]),
        Scene(scene_number="4", shoot_day_id="day-2", cast_ids=["cm-solo"]),
        # Day 3: MARSH + ROOKIE
        Scene(scene_number="5", shoot_day_id="day-3", cast_ids=["cm-marsh", "cm-rookie"]),
        Scene(scene_number="6", shoot_day_id="day-3", cast_ids=["cm-rookie"]),
    ]

    grid = generate_dood("prod-test", cast, days, scenes)
    return {"days": days, "cast": cast, "scenes": scenes, "grid": grid}


def test_marsh_full_run(fixture):
    """MARSH appears every day → SW / W / WF."""
    assert fixture["grid"]["cm-marsh"] == {1: "SW", 2: "W", 3: "WF"}


def test_solo_guest_single_day(fixture):
    """SOLO_GUEST appears on day 2 only → SWF, no other days in the row."""
    assert fixture["grid"]["cm-solo"] == {2: "SWF"}


def test_rookie_hold_day(fixture):
    """ROOKIE appears on days 1 and 3 only → SW / H / WF."""
    assert fixture["grid"]["cm-rookie"] == {1: "SW", 2: "H", 3: "WF"}


def test_non_working_cast_member_omitted(fixture):
    """A cast member with zero scenes never appears in the grid."""
    assert "cm-nowhere" not in fixture["grid"]


def test_export_csv_header_and_row_count(fixture, tmp_path):
    csv_path = export_dood_csv(
        fixture["grid"],
        fixture["cast"],
        fixture["days"],
        output_dir=tmp_path,
        production_id="prod-test",
    )

    assert os.path.exists(csv_path)
    assert os.path.basename(csv_path) == "dood_prod-test.csv"

    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    # Header row must list the day numbers with dates.
    assert rows[0] == [
        "Cast Member",
        "Day 1 (2026-01-15)",
        "Day 2 (2026-01-16)",
        "Day 3 (2026-01-17)",
    ]

    # Exactly 3 body rows — non-working NOWHERE is excluded.
    body = rows[1:]
    assert len(body) == 3
    assert {row[0] for row in body} == {"MARSH", "ROOKIE", "SOLO_GUEST"}


def test_export_pdf_nonzero_size(fixture, tmp_path):
    pdf_path = export_dood_pdf(
        fixture["grid"],
        fixture["cast"],
        fixture["days"],
        output_dir=tmp_path,
        production_id="prod-test",
        production_title="Test Production",
    )

    assert os.path.exists(pdf_path)
    assert os.path.basename(pdf_path) == "dood_prod-test.pdf"
    assert os.path.getsize(pdf_path) > 0
