# =============================================================================
# src/services/broadcast_scheduler/parsers/xml_parser.py
# Reads an XML or BXF rundown file and returns a populated Schedule object.
#
# BXF (Broadcast Exchange Format) is an XML-based SMPTE standard, so this
# parser handles both .xml and .bxf inputs. The mapping from real-world XML
# tag names to internal field names lives in
# src/services/broadcast_scheduler/config/field_maps.py (XML_FIELD_MAP).
#
# We use xmltodict, which converts XML into nested Python dictionaries.
# This lets us walk the parsed file the same way the CSV parser walks rows.
# =============================================================================

import xmltodict
from pathlib import Path

from src.services.broadcast_scheduler.config.field_maps import XML_FIELD_MAP
from src.services.broadcast_scheduler.models.schedule import Schedule
from src.services.broadcast_scheduler.models.segment import Segment


# Toggles the [XML] progress prints. Was in config/settings.py originally.
VERBOSE_LOGGING = True


# Reads a single XML/BXF file from disk and returns a Schedule object.
# Returns None if the file cannot be opened or parsed.
#
# Arguments:
#   file_path      â€” path to the XML or BXF file (string or Path)
#   channel_name   â€” optional channel name to stamp on the Schedule;
#                    if not provided we try to pick it up from the root element
#   schedule_date  â€” optional date string to stamp on the Schedule
def parse_xml_file(file_path, channel_name=None, schedule_date=None):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[XML] Reading file: {file_path.name}")

    # All file I/O and parsing is wrapped in try/except so a missing or
    # malformed file cannot crash the whole pipeline â€” we log and return None.
    try:
        with open(file_path, mode="r", encoding="utf-8") as xml_file:
            data = xmltodict.parse(xml_file.read())
    except FileNotFoundError:
        print(f"[XML] ERROR: file not found: {file_path}")
        return None
    except PermissionError:
        print(f"[XML] ERROR: permission denied opening: {file_path}")
        return None
    except Exception as error:
        print(f"[XML] ERROR: could not parse XML: {error}")
        return None

    # xmltodict returns {root_tag: <contents>}. We don't care what the root
    # tag is called â€” just unwrap to its contents.
    if len(data) != 1:
        print("[XML] ERROR: expected a single root element")
        return None
    root_tag = list(data.keys())[0]
    root_content = data[root_tag]
    if not isinstance(root_content, dict):
        print(f"[XML] ERROR: root <{root_tag}> has no child elements")
        return None

    # xmltodict marks XML attributes with a leading '@'. If the root has
    # channel/date attributes, pick them up â€” but the caller's explicit
    # arguments always win.
    detected_channel = root_content.get("@channel")
    detected_date = root_content.get("@date")

    schedule = Schedule(
        channel_name=channel_name if channel_name is not None else detected_channel,
        schedule_date=schedule_date if schedule_date is not None else detected_date,
        source_filename=file_path.name,
    )

    # Find the list of per-event children and turn each one into a Segment.
    event_list = find_event_list(root_content)
    for event in event_list:
        segment = build_segment_from_element(event)
        schedule.add_segment(segment)

    if VERBOSE_LOGGING:
        print(f"[XML] Parsed {len(schedule.segments)} segments from {file_path.name}")

    return schedule


# Walks the root content dict to find the list of schedule-event children.
# Skips attribute keys (those starting with '@'). Normalises a single-event
# dict into a one-element list, because xmltodict collapses lists of one.
def find_event_list(root_content):
    for key, value in root_content.items():
        if key.startswith("@"):
            continue  # this is an XML attribute, not a child element
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]  # single event â€” wrap it so callers can iterate
    return []


# Converts one parsed XML element (a dict of {tag: text}) into a Segment,
# translating tag names via XML_FIELD_MAP. Tags not in the map are silently
# skipped. Nested complex children are also skipped here.
def build_segment_from_element(element):
    segment = Segment()
    if not isinstance(element, dict):
        return segment

    for xml_tag, raw_value in element.items():
        # Skip attribute keys on the event element itself
        if xml_tag.startswith("@"):
            continue

        # xmltodict gives the text content directly for simple <Tag>text</Tag>
        # elements, but a dict for elements with children or attributes.
        # We only handle simple text tags in this Phase â€” skip anything else.
        if not isinstance(raw_value, (str, type(None))):
            continue

        internal_field = XML_FIELD_MAP.get(xml_tag)
        if internal_field is None:
            continue  # this tag isn't in our map â€” ignore it

        # Clean the text: strip whitespace, convert empty to None so the
        # model stays clean and downstream code never has to handle "".
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


