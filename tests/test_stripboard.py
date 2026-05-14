# =============================================================================
# tests/test_stripboard.py
# Phase 5 verification — exercises the in-memory stripboard builder at
# src/services/production_schedule/generators/stripboard.py against the
# 10-scene fixture parsed by the Phase 2 CSV importer.
#
# Fixture assignment: 10 scenes split 4/3/3 across 3 shoot days, all in
# the "Georgia" jurisdiction (matching the State column in the CSV).
# =============================================================================

import pytest

from src.services.production_schedule.generators.stripboard import (
    assign_scene_to_day,
    build_stripboard,
    calculate_day_pages,
    get_stripboard_summary,
    reorder_scenes_in_day,
)
from src.services.production_schedule.importers.csv_importer import parse_csv_breakdown
from src.services.production_schedule.models.shoot_day import ShootDay


# Page counts pulled from tests/sample_data/sample_breakdown.csv:
#   Scene 1: 2.5      Scene 2: 3.125    Scene 3: 1.875    Scene 4: 2.25
#   Scene 5: 0.125    Scene 6: 0.5      Scene 7: 1.0      Scene 8: 0.75
#   Scene 9: 1.5      Scene 10: 1.25
DAY_1_PAGES = 2.5 + 3.125 + 1.875 + 2.25   # 9.75
DAY_2_PAGES = 0.125 + 0.5 + 1.0            # 1.625
DAY_3_PAGES = 0.75 + 1.5 + 1.25            # 3.5
TOTAL_PAGES = DAY_1_PAGES + DAY_2_PAGES + DAY_3_PAGES  # 14.875


@pytest.fixture
def scenes_and_days():
    """Load the 10 CSV scenes, give each a stable id, build 3 shoot days,
    and assign scenes 4/3/3 across them. Returns (scenes, days)."""
    scenes = parse_csv_breakdown("tests/sample_data/sample_breakdown.csv")
    assert len(scenes) == 10, "fixture sanity — CSV must yield 10 scenes"

    # Stable in-memory ids — the router would normally set these from the DB.
    for index, scene in enumerate(scenes, start=1):
        scene.id = f"scene-{index}"

    days = [
        ShootDay(
            id=f"day-{n}",
            day_number=n,
            date=f"2026-01-{14 + n:02d}",
            jurisdiction_id="Georgia",
        )
        for n in (1, 2, 3)
    ]

    # 4 + 3 + 3 split.
    for scene in scenes[0:4]:
        assign_scene_to_day(scene, days[0])
    for scene in scenes[4:7]:
        assign_scene_to_day(scene, days[1])
    for scene in scenes[7:10]:
        assign_scene_to_day(scene, days[2])

    return scenes, days


def test_assign_scene_to_day_mutates_scene(scenes_and_days):
    scenes, days = scenes_and_days
    # Every scene got an assignment; the four on day 1 should point at "day-1".
    assert all(s.shoot_day_id is not None for s in scenes)
    assert [s.shoot_day_id for s in scenes[0:4]] == ["day-1"] * 4
    assert [s.shoot_day_id for s in scenes[4:7]] == ["day-2"] * 3
    assert [s.shoot_day_id for s in scenes[7:10]] == ["day-3"] * 3


def test_build_stripboard_shape_and_grouping(scenes_and_days):
    scenes, days = scenes_and_days
    stripboard = build_stripboard(scenes, days)

    assert set(stripboard.keys()) == {1, 2, 3}

    for day_number in (1, 2, 3):
        bucket = stripboard[day_number]
        assert set(bucket.keys()) == {"date", "jurisdiction", "scenes", "total_pages"}
        assert bucket["jurisdiction"] == "Georgia"

    assert len(stripboard[1]["scenes"]) == 4
    assert len(stripboard[2]["scenes"]) == 3
    assert len(stripboard[3]["scenes"]) == 3


def test_calculate_day_pages_sums(scenes_and_days):
    scenes, days = scenes_and_days
    assert calculate_day_pages(days[0], scenes) == pytest.approx(DAY_1_PAGES)
    assert calculate_day_pages(days[1], scenes) == pytest.approx(DAY_2_PAGES)
    assert calculate_day_pages(days[2], scenes) == pytest.approx(DAY_3_PAGES)


def test_build_stripboard_total_pages_matches_calculate_day_pages(scenes_and_days):
    scenes, days = scenes_and_days
    stripboard = build_stripboard(scenes, days)
    for day in days:
        assert stripboard[day.day_number]["total_pages"] == pytest.approx(
            calculate_day_pages(day, scenes)
        )


def test_reorder_scenes_in_day_changes_order(scenes_and_days):
    scenes, days = scenes_and_days

    # Day 1 scenes are "scene-1".."scene-4" in their original order.
    # Reverse them via reorder_scenes_in_day.
    new_order = ["scene-4", "scene-3", "scene-2", "scene-1"]
    reordered = reorder_scenes_in_day("day-1", new_order, scenes)

    # Same length, no scenes dropped.
    assert len(reordered) == len(scenes)

    # Day 1's scenes appear in the new order.
    day_1_ids = [s.id for s in reordered if s.shoot_day_id == "day-1"]
    assert day_1_ids == new_order

    # Day 2 and Day 3 scenes are untouched in relative order.
    day_2_ids = [s.id for s in reordered if s.shoot_day_id == "day-2"]
    day_3_ids = [s.id for s in reordered if s.shoot_day_id == "day-3"]
    assert day_2_ids == ["scene-5", "scene-6", "scene-7"]
    assert day_3_ids == ["scene-8", "scene-9", "scene-10"]

    # Input list was not mutated.
    assert [s.id for s in scenes[0:4]] == ["scene-1", "scene-2", "scene-3", "scene-4"]


def test_get_stripboard_summary_counts(scenes_and_days):
    scenes, days = scenes_and_days
    summary = get_stripboard_summary(scenes, days)

    assert summary["total_shoot_days"] == 3
    assert summary["total_scenes"] == 10
    assert summary["total_pages"] == pytest.approx(TOTAL_PAGES)
    assert summary["shoot_days_per_jurisdiction"] == {"Georgia": 3}
