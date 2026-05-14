# =============================================================================
# tests/test_call_sheet.py
# Phase 7 verification — exercises the call-sheet builder + PDF/JSON
# exporters at src/services/production_schedule/generators/call_sheet.py.
#
# The fixture builds one shoot day with three scenes and three crew
# calls, then a stand-in Production object with .id and .title. No DB
# connectivity needed — the generator is pure in-memory.
# =============================================================================

from dataclasses import dataclass
import json
import os
from typing import Optional

import pytest

from src.services.production_schedule.generators.call_sheet import (
    export_call_sheet_json,
    export_call_sheet_pdf,
    generate_call_sheet,
)
from src.services.production_schedule.models.call_sheet import CallSheet
from src.services.production_schedule.models.scene import Scene
from src.services.production_schedule.models.shoot_day import ShootDay


# Lightweight stand-in for the SceneIQ Production model. The generator
# only reads .id and .title from the production object, so this is
# sufficient for the unit tests.
@dataclass
class _ProductionStub:
    id: str
    title: str
    episode: Optional[str] = None


@pytest.fixture
def fixture():
    shoot_day = ShootDay(
        id="day-1",
        day_number=1,
        date="2026-01-15",
        jurisdiction_id="Georgia",
        call_time="06:00 AM",
        location="220 Peachtree St NE, Atlanta GA 30303",
        nearest_hospital="Grady Memorial Hospital — 80 Jesse Hill Jr Dr, Atlanta GA 30303",
    )

    scenes = [
        Scene(
            id="scene-1",
            scene_number="1",
            title="POLICE STATION - OPENING",
            location="POLICE STATION",
            location_type="INT",
            time_of_day="DAY",
            page_count=2.5,
            cast_ids=["MARSH", "ROOKIE"],
            shoot_day_id="day-1",
        ),
        Scene(
            id="scene-2",
            scene_number="2",
            title="BULLPEN - MORNING BRIEFING",
            location="POLICE STATION BULLPEN",
            location_type="INT",
            time_of_day="DAY",
            page_count=3.125,
            cast_ids=["MARSH", "ROOKIE", "CAPTAIN HOLT"],
            shoot_day_id="day-1",
        ),
        Scene(
            id="scene-3",
            scene_number="3",
            title="DOOR INSERT",
            location="POLICE STATION",
            location_type="INT",
            time_of_day="DAY",
            page_count=0.125,
            cast_ids=[],
            shoot_day_id="day-1",
        ),
    ]

    crew_calls = [
        {"department": "Camera", "name": "L. NGUYEN", "call_time": "05:30 AM"},
        {"department": "Lighting", "name": "T. RAMIREZ", "call_time": "05:00 AM"},
        {"department": "Sound", "name": "K. OKAFOR", "call_time": "05:45 AM"},
    ]

    production = _ProductionStub(id="prod-test", title="Test Production", episode="Pilot")

    call_sheet = generate_call_sheet(shoot_day, scenes, crew_calls, production)

    return {
        "shoot_day": shoot_day,
        "scenes": scenes,
        "crew_calls": crew_calls,
        "production": production,
        "call_sheet": call_sheet,
    }


def test_generate_call_sheet_builds_correct_object(fixture):
    cs = fixture["call_sheet"]

    assert isinstance(cs, CallSheet)
    assert cs.day_number == 1
    assert cs.shoot_day_id == "day-1"
    assert cs.production_id == "prod-test"
    assert cs.date == "2026-01-15"
    assert cs.general_call == "06:00 AM"
    assert cs.location == "220 Peachtree St NE, Atlanta GA 30303"
    assert cs.nearest_hospital.startswith("Grady Memorial Hospital")
    assert cs.weather is None  # placeholder — populated later

    # Scene snapshot — keys and values
    assert len(cs.scenes) == 3
    first = cs.scenes[0]
    assert set(first.keys()) >= {
        "scene_number", "title", "location", "location_type",
        "time_of_day", "page_count", "cast",
    }
    assert first["scene_number"] == "1"
    assert first["cast"] == ["MARSH", "ROOKIE"]
    assert cs.scenes[2]["cast"] == []  # insert scene has no cast

    # Crew calls round-trip
    assert len(cs.crew_calls) == 3
    departments = [c["department"] for c in cs.crew_calls]
    assert departments == ["Camera", "Lighting", "Sound"]


def test_export_pdf_nonzero_size(fixture, tmp_path):
    pdf_path = export_call_sheet_pdf(
        fixture["call_sheet"],
        production_title="Test Production",
        episode="Pilot",
        output_dir=tmp_path,
    )

    assert os.path.exists(pdf_path)
    assert os.path.basename(pdf_path) == "call_sheet_prod-test_day_1.pdf"
    assert os.path.getsize(pdf_path) > 0


def test_export_json_contains_all_required_keys(fixture):
    payload = export_call_sheet_json(fixture["call_sheet"])

    required = {
        "id", "production_id", "shoot_day_id", "day_number", "date",
        "general_call", "location", "nearest_hospital", "weather",
        "scenes", "crew_calls",
    }
    assert required.issubset(payload.keys()), f"missing keys: {required - payload.keys()}"

    # JSON-serialisable end-to-end — round trips via json.dumps/loads.
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["day_number"] == 1
    assert decoded["production_id"] == "prod-test"
    assert len(decoded["scenes"]) == 3
    assert len(decoded["crew_calls"]) == 3


def test_missing_optional_fields_render_as_null():
    """A minimal CallSheet (only required fields) must serialise cleanly
    with optional fields appearing as null in JSON."""
    minimal = CallSheet(day_number=2, shoot_day_id="day-2")

    payload = export_call_sheet_json(minimal)

    # Required fields populated as expected.
    assert payload["day_number"] == 2
    assert payload["shoot_day_id"] == "day-2"

    # Every optional CallSheet field is None on a minimal object.
    for field in (
        "id", "production_id", "date", "general_call",
        "location", "nearest_hospital", "weather",
    ):
        assert payload[field] is None, f"expected {field} to be None"

    # And the JSON representation surfaces them as the literal `null`.
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    for field in (
        "id", "production_id", "date", "general_call",
        "location", "nearest_hospital", "weather",
    ):
        assert decoded[field] is None
    assert "null" in encoded  # at least one literal null token in the JSON

    # List-typed optional fields default to empty list, not None.
    assert payload["scenes"] == []
    assert payload["crew_calls"] == []
