# =============================================================================
# src/services/production_schedule/importers/csv_importer.py
# Reads a script-breakdown CSV file and returns a list of Scene objects.
#
# The mapping from real-world CSV column headers to internal Scene field
# names lives in src/services/production_schedule/config/field_maps.py
# (CSV_SCENE_FIELD_MAP). To add a new header variant, edit that map â€” you
# do NOT need to change this file.
#
# Pattern mirrors src/services/broadcast_scheduler/parsers/csv_parser.py:
# csv.DictReader + utf-8-sig encoding + try/except around all file I/O so
# missing or malformed files never crash the caller.
#
# NOTE on raw-string semantics:
#   - Scene.jurisdiction_id temporarily holds the raw jurisdiction NAME
#     from the CSV. The router (Phase 10) resolves name â†’ Jurisdiction.id
#     before persisting.
#   - Scene.cast_ids temporarily holds character NAMES (e.g. ["MARSH"]).
#     The router (or Phase 8 tracker) resolves names â†’ CastMember.id.
# =============================================================================

import csv
from pathlib import Path

from src.services.production_schedule.config.field_maps import CSV_SCENE_FIELD_MAP
from src.services.production_schedule.models.scene import Scene


# Module-level toggle for the [CSV] progress lines. Set to False to silence
# the importer (useful in unit tests that capture stdout).
VERBOSE_LOGGING = True


# Reads a script-breakdown CSV file from disk and returns a list of Scene
# objects. Returns an empty list if the file cannot be opened or read.
#
# Arguments:
#   file_path  â€” path to the CSV file (string or Path)
def parse_csv_breakdown(file_path):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[CSV] Reading breakdown: {file_path.name}")

    scenes = []

    # All file I/O is wrapped in try/except so a missing or broken file
    # cannot crash the whole pipeline â€” log and return an empty list.
    try:
        # encoding="utf-8-sig" silently strips the UTF-8 BOM that Excel
        # adds to CSVs saved on Windows â€” a common novice gotcha.
        # newline="" lets the csv module handle line endings on its own.
        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            row_number = 1  # 1-based, for human-friendly warning lines
            for row in reader:
                row_number += 1
                scene = build_scene_from_row(row, CSV_SCENE_FIELD_MAP, row_number=row_number)
                if scene is not None:
                    scenes.append(scene)
    except FileNotFoundError:
        print(f"[CSV] ERROR: file not found: {file_path}")
        return []
    except PermissionError:
        print(f"[CSV] ERROR: permission denied opening: {file_path}")
        return []
    except Exception as error:
        print(f"[CSV] ERROR: could not read CSV: {error}")
        return []

    if VERBOSE_LOGGING:
        print(f"[CSV] Parsed {len(scenes)} scenes from {file_path.name}")

    return scenes


# Translates one csv.DictReader row (a {header: value} dict) into a Scene
# object using the supplied field map. Returns None if the row has no
# scene number (a row without one is unusable and the spec says to skip).
#
# Arguments:
#   row         â€” dict mapping CSV header strings to raw cell values
#   field_map   â€” header â†’ Scene-field-name map (e.g. CSV_SCENE_FIELD_MAP)
#   row_number  â€” optional 1-based source row number, used only in warnings
def build_scene_from_row(row, field_map, row_number=None):
    cleaned = {}

    for csv_column, raw_value in row.items():
        # DictReader yields None for any "extra" cells beyond the header
        # count; skip those so we don't crash on a ragged row.
        if csv_column is None:
            continue

        # Strip leading/trailing whitespace from the header before lookup â€”
        # real-world CSVs often have " Title " instead of "Title".
        clean_column = csv_column.strip()
        internal_field = field_map.get(clean_column)
        if internal_field is None:
            continue  # this column isn't in our map â€” silently ignore

        # Clean the cell value: strip whitespace, convert empty to None,
        # so downstream code never has to distinguish "" from missing.
        if raw_value is None:
            value = None
        else:
            value = raw_value.strip()
            if value == "":
                value = None

        cleaned[internal_field] = value

    # A row without a scene number is unusable. Per the brief, log and
    # skip â€” never crash.
    scene_number = cleaned.get("scene_number")
    if not scene_number:
        if VERBOSE_LOGGING:
            where = f"row {row_number}" if row_number else "row"
            print(f"[CSV] WARNING: skipping {where} â€” no scene number")
        return None

    # Convert page_count to float. Bad values log a warning and become None
    # rather than aborting the whole row.
    page_count = None
    raw_pages = cleaned.get("page_count")
    if raw_pages is not None:
        try:
            page_count = float(raw_pages)
        except ValueError:
            if VERBOSE_LOGGING:
                print(
                    f"[CSV] WARNING: scene {scene_number}: "
                    f"could not parse page count {raw_pages!r} â€” leaving blank"
                )

    # Split cast on commas. Each piece is stripped; empties are dropped.
    cast_ids = []
    raw_cast = cleaned.get("cast_ids")
    if raw_cast:
        cast_ids = [piece.strip() for piece in raw_cast.split(",") if piece.strip()]

    # Jurisdiction name lands on Scene.jurisdiction_id as a raw string;
    # the router resolves name â†’ Jurisdiction.id at persist time.
    jurisdiction_name = cleaned.get("jurisdiction_name")

    return Scene(
        scene_number=scene_number,
        title=cleaned.get("title"),
        location=cleaned.get("location"),
        location_type=cleaned.get("location_type"),
        time_of_day=cleaned.get("time_of_day"),
        page_count=page_count,
        jurisdiction_id=jurisdiction_name,
        cast_ids=cast_ids,
        notes=cleaned.get("notes"),
    )




