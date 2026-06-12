# =============================================================================
# src/services/broadcast_scheduler/parsers/json_parser.py
# Reads a JSON schedule feed and returns a populated Schedule object.
#
# The mapping from JSON keys to internal field names lives in
# src/services/broadcast_scheduler/config/field_maps.py (JSON_FIELD_MAP).
# To support a new JSON key variant, edit that map â€” you do NOT need to
# change this file.
#
# This parser handles two common JSON shapes:
#   1) A bare list of segment objects at the root:    [ {...}, {...} ]
#   2) A wrapped object with metadata + segment list:
#        { "channel": "...", "date": "...", "segments": [ {...} ] }
# =============================================================================

import json
from pathlib import Path

from src.services.broadcast_scheduler.config.field_maps import JSON_FIELD_MAP
from src.services.broadcast_scheduler.models.schedule import Schedule
from src.services.broadcast_scheduler.models.segment import Segment


# Toggles the [JSON] progress prints. Was in config/settings.py originally.
VERBOSE_LOGGING = True


# Reads a single JSON file from disk and returns a Schedule object.
# Returns None if the file cannot be opened or parsed.
#
# Arguments:
#   file_path      â€” path to the JSON file (string or Path)
#   channel_name   â€” optional channel name to stamp on the Schedule;
#                    if not provided we try to pick it up from the JSON
#   schedule_date  â€” optional date string to stamp on the Schedule
def parse_json_file(file_path, channel_name=None, schedule_date=None):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[JSON] Reading file: {file_path.name}")

    # All file I/O and parsing is wrapped in try/except so a missing or
    # malformed file cannot crash the whole pipeline â€” we log and return None.
    try:
        with open(file_path, mode="r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    except FileNotFoundError:
        print(f"[JSON] ERROR: file not found: {file_path}")
        return None
    except PermissionError:
        print(f"[JSON] ERROR: permission denied opening: {file_path}")
        return None
    except json.JSONDecodeError as error:
        # Most common real-world JSON problem â€” give a friendly message
        # that includes the line/column so the user can find the typo.
        print(f"[JSON] ERROR: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}")
        return None
    except Exception as error:
        print(f"[JSON] ERROR: could not read JSON: {error}")
        return None

    # JSON can arrive in two shapes; figure out which one we have.
    detected_channel = None
    detected_date = None

    if isinstance(data, list):
        # Bare list of segments at root â€” no metadata available.
        segments_data = data
    elif isinstance(data, dict):
        # Wrapped object â€” pull channel/date from the root, find the list.
        detected_channel = data.get("channel")
        detected_date = data.get("date")
        segments_data = find_segments_list(data)
    else:
        print("[JSON] ERROR: expected a JSON object or array at the root")
        return None

    schedule = Schedule(
        channel_name=channel_name if channel_name is not None else detected_channel,
        schedule_date=schedule_date if schedule_date is not None else detected_date,
        source_filename=file_path.name,
    )

    for item in segments_data:
        segment = build_segment_from_item(item)
        schedule.add_segment(segment)

    if VERBOSE_LOGGING:
        print(f"[JSON] Parsed {len(schedule.segments)} segments from {file_path.name}")

    return schedule


# Walks a wrapped-object root dict to find the list of segment objects.
# Returns the first list-typed value found, or [] if none.
def find_segments_list(root_data):
    for key, value in root_data.items():
        if isinstance(value, list):
            return value
    return []


# Converts one JSON object (a dict of {key: value}) into a Segment,
# translating keys via JSON_FIELD_MAP.
#
# JSON values can be native int/float/bool/None â€” unlike CSV (always
# strings) and XML (also strings via xmltodict). For consistency across
# parsers, we convert every non-None scalar to a string here.
def build_segment_from_item(item):
    segment = Segment()
    if not isinstance(item, dict):
        return segment

    for json_key, raw_value in item.items():
        internal_field = JSON_FIELD_MAP.get(json_key)
        if internal_field is None:
            continue  # this key isn't in our map â€” ignore it

        # Convert each possible JSON value type to our consistent
        # str-or-None representation.
        if raw_value is None:
            value = None
        elif isinstance(raw_value, (dict, list)):
            # Nested complex values aren't handled this phase â€” skip silently.
            continue
        elif isinstance(raw_value, str):
            value = raw_value.strip()
            if value == "":
                value = None
        else:
            # int / float / bool â€” convert to string for cross-parser parity
            value = str(raw_value)

        # Set the matching attribute on the Segment object. setattr() is the
        # standard way to assign an attribute when the attribute name is
        # decided at runtime (here, from the field map).
        setattr(segment, internal_field, value)

    return segment


