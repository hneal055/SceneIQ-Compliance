# =============================================================================
# src/services/broadcast_scheduler/parsers/csv_parser.py
# Reads a CSV rundown file and returns a populated Schedule object.
#
# The mapping from real-world CSV column headers to our internal field names
# lives in src/services/broadcast_scheduler/config/field_maps.py (CSV_FIELD_MAP).
# To add a new header variant, edit that map — you do NOT need to change this
# file.
# =============================================================================

import csv
from pathlib import Path

from src.services.broadcast_scheduler.config.field_maps import CSV_FIELD_MAP
from src.services.broadcast_scheduler.models.schedule import Schedule
from src.services.broadcast_scheduler.models.segment import Segment


# Module-level defaults (formerly in config/settings.py).
# Set CSV_MAX_ROWS to an int to cap how many rows are parsed. Leave as None
# to read the whole file. VERBOSE_LOGGING toggles the [CSV] progress prints.
CSV_MAX_ROWS = None
VERBOSE_LOGGING = True


# Reads a single CSV file from disk and returns a Schedule object.
# Returns None if the file cannot be opened or read.
#
# Arguments:
#   file_path      — path to the CSV file (string or Path)
#   channel_name   — optional channel name to stamp on the Schedule;
#                    if not provided we try to pick it up from the first row
#   schedule_date  — optional date string to stamp on the Schedule
def parse_csv_file(file_path, channel_name=None, schedule_date=None):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[CSV] Reading file: {file_path.name}")

    schedule = Schedule(
        channel_name=channel_name,
        schedule_date=schedule_date,
        source_filename=file_path.name,
    )

    # All file I/O is wrapped in try/except so a missing or broken file
    # cannot crash the whole pipeline — we just log and return None.
    try:
        # encoding="utf-8-sig" silently strips the UTF-8 BOM that Excel
        # adds to CSVs saved on Windows — a common novice gotcha.
        # newline="" lets the csv module handle line endings on its own.
        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            row_count = 0
            for row in reader:
                # Honour the optional row cap set at module level
                if CSV_MAX_ROWS is not None and row_count >= CSV_MAX_ROWS:
                    if VERBOSE_LOGGING:
                        print(f"[CSV] Hit CSV_MAX_ROWS limit ({CSV_MAX_ROWS}) — stopping early")
                    break
                segment = build_segment_from_row(row)
                schedule.add_segment(segment)
                row_count += 1
    except FileNotFoundError:
        print(f"[CSV] ERROR: file not found: {file_path}")
        return None
    except PermissionError:
        print(f"[CSV] ERROR: permission denied opening: {file_path}")
        return None
    except Exception as error:
        print(f"[CSV] ERROR: could not read CSV: {error}")
        return None

    # If the caller did not give us a channel name, take it from the first
    # segment's 'channel' field so the Schedule's repr() shows something useful.
    if schedule.channel_name is None and schedule.segments:
        schedule.channel_name = schedule.segments[0].channel

    if VERBOSE_LOGGING:
        print(f"[CSV] Parsed {len(schedule.segments)} segments from {file_path.name}")

    return schedule


# Converts one row from csv.DictReader (a dict of {header: value}) into a
# Segment object, translating column headers via CSV_FIELD_MAP. Columns not
# in the map are silently skipped. Empty cells become None.
def build_segment_from_row(row):
    segment = Segment()

    for csv_column, raw_value in row.items():
        # DictReader yields None for any "extra" cells beyond the header count;
        # skip those so we don't crash on a ragged row.
        if csv_column is None:
            continue

        # Strip leading/trailing whitespace from the header before lookup —
        # real-world CSVs often have " Title " instead of "Title".
        clean_column = csv_column.strip()
        internal_field = CSV_FIELD_MAP.get(clean_column)
        if internal_field is None:
            continue  # this column isn't in our map — ignore it

        # Clean the cell value: strip whitespace, convert empty to None,
        # so downstream code never has to distinguish "" from missing.
        if raw_value is None:
            value = None
        else:
            value = raw_value.strip()
            if value == "":
                value = None

        # Set the matching attribute on the Segment object. setattr() is the
        # standard way to assign an attribute when the attribute name is
        # decided at runtime (here, from the field map).
        setattr(segment, internal_field, value)

    return segment
