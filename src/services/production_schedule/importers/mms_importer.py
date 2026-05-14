# =============================================================================
# src/services/production_schedule/importers/mms_importer.py
# Reads a Movie Magic Scheduling .mms (XML) file and returns a list of
# Scene objects.
#
# .mms files are XML. Root element is typically <BreakdownBook> or
# <Schedule>; scenes are <BreakdownSheet> children. The tag→field map
# lives in src/services/production_schedule/config/field_maps.py
# (MMS_FIELD_MAP).
#
# Pattern mirrors:
#   - src/services/production_schedule/importers/csv_importer.py (overall shape)
#   - src/services/broadcast_scheduler/parsers/xml_parser.py (xmltodict usage,
#     try/except wrapping, find_event_list pattern)
#
# Two field-map values trigger specialised parsers:
#   "scene_heading"  → _parse_scene_heading()  (loc_type + location + time_of_day)
#   "cast"           → _extract_cast()         (list[str] of character names)
#
# NOTE on raw-string semantics (same as CSV importer):
#   - Scene.jurisdiction_id temporarily holds a raw name string from
#     MMS (e.g. "GA", "Georgia"); the router resolves it later.
#   - Scene.cast_ids temporarily holds character NAMES (e.g. ["MARSH"]);
#     resolution to CastMember.id happens later.
# =============================================================================

import xmltodict
from pathlib import Path

from src.services.production_schedule.config.field_maps import MMS_FIELD_MAP
from src.services.production_schedule.importers._heading import parse_scene_heading_text
from src.services.production_schedule.models.scene import Scene


# Toggle for the [MMS] progress lines. Set to False to silence the
# importer (useful in unit tests that capture stdout).
VERBOSE_LOGGING = True


# Reads a Movie Magic Scheduling .mms file from disk and returns a list
# of Scene objects. Returns an empty list if the file cannot be opened
# or parsed.
def parse_mms_file(file_path):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[MMS] Reading breakdown: {file_path.name}")

    # All file I/O and XML parsing is wrapped so a missing or malformed
    # file cannot crash the caller — log and return [].
    try:
        with open(file_path, mode="r", encoding="utf-8") as mms_file:
            data = xmltodict.parse(mms_file.read())
    except FileNotFoundError:
        print(f"[MMS] ERROR: file not found: {file_path}")
        return []
    except PermissionError:
        print(f"[MMS] ERROR: permission denied opening: {file_path}")
        return []
    except Exception as error:
        print(f"[MMS] ERROR: could not parse MMS XML: {error}")
        return []

    # xmltodict returns {root_tag: contents}. We don't care what the root
    # tag is called — strip the wrapper and hand the contents off.
    if not isinstance(data, dict) or len(data) != 1:
        print("[MMS] ERROR: expected a single root element")
        return []
    root_tag = next(iter(data))
    root_content = data[root_tag]
    if not isinstance(root_content, dict):
        print(f"[MMS] ERROR: root <{root_tag}> has no child elements")
        return []

    scene_elements = find_scenes_in_mms(root_content)

    scenes = []
    for index, element in enumerate(scene_elements, start=1):
        scene = build_scene_from_mms_element(element, element_number=index)
        if scene is not None:
            scenes.append(scene)

    if VERBOSE_LOGGING:
        print(f"[MMS] Parsed {len(scenes)} scenes from {file_path.name}")

    return scenes


# Walks the unwrapped root dict to find the list of scene children.
# Skips XML attribute keys (those starting with '@') and skips scalar
# children like <Title>Sample Production</Title>. The first child key
# whose value is a list or a dict wins. Single-scene structures are
# normalised to a one-element list (xmltodict collapses single children
# into a dict, not a list).
def find_scenes_in_mms(root_content):
    if not isinstance(root_content, dict):
        return []

    for key, value in root_content.items():
        if key.startswith("@"):
            continue  # XML attribute on the root element
        if isinstance(value, list):
            # Filter out any non-dict items defensively (shouldn't happen
            # with valid MMS, but a ragged file shouldn't crash us).
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]  # single scene — wrap so the caller can iterate

    return []


# Converts one parsed scene element (a dict from xmltodict) into a
# Scene object. Returns None if the element has no scene number
# (an element without one is unusable and the spec says to skip).
#
# Three field-map values are routed through specialised parsers:
#   "scene_heading" → _parse_scene_heading()
#   "cast"          → _extract_cast()
#   "page_count"    → float() in try/except
# Everything else is treated as a plain string field.
def build_scene_from_mms_element(element, element_number=None):
    if not isinstance(element, dict):
        if VERBOSE_LOGGING:
            print(f"[MMS] WARNING: skipping non-dict element at position {element_number}")
        return None

    cleaned = {}
    heading_text = None
    cast_value = None

    for xml_tag, raw_value in element.items():
        if xml_tag.startswith("@"):
            continue  # XML attribute on the scene element

        internal_field = MMS_FIELD_MAP.get(xml_tag)
        if internal_field is None:
            continue  # this tag isn't in our map — silently ignore

        # Special routes — defer parsing until we've walked the whole
        # element, since heading + explicit Location can disagree and
        # the explicit tag should win.
        if internal_field == "scene_heading":
            if isinstance(raw_value, str):
                heading_text = raw_value.strip() or None
            continue

        if internal_field == "cast":
            cast_value = raw_value
            continue

        # Everything else expects simple <Tag>text</Tag>. xmltodict gives
        # a dict for elements with children/attributes — for non-special
        # fields we don't try to descend; skip defensively.
        if not isinstance(raw_value, (str, type(None))):
            continue

        if raw_value is None:
            value = None
        else:
            value = raw_value.strip()
            if value == "":
                value = None

        cleaned[internal_field] = value

    # Apply heading parse (if any) — but never overwrite an explicit
    # <Location>/<SetName> tag.
    if heading_text:
        hd_loc_type, hd_location, hd_time = parse_scene_heading_text(heading_text)
        if hd_loc_type and "location_type" not in cleaned:
            cleaned["location_type"] = hd_loc_type
        if hd_time and "time_of_day" not in cleaned:
            cleaned["time_of_day"] = hd_time
        if hd_location and not cleaned.get("location"):
            cleaned["location"] = hd_location

    # A scene without a number is unusable — skip with a warning.
    scene_number = cleaned.get("scene_number")
    if not scene_number:
        if VERBOSE_LOGGING:
            where = f"element {element_number}" if element_number else "element"
            print(f"[MMS] WARNING: skipping {where} — no scene number")
        return None

    # Convert page_count to float. Bad values log and become None
    # rather than aborting the whole scene.
    page_count = None
    raw_pages = cleaned.get("page_count")
    if raw_pages is not None:
        try:
            page_count = float(raw_pages)
        except ValueError:
            if VERBOSE_LOGGING:
                print(
                    f"[MMS] WARNING: scene {scene_number}: "
                    f"could not parse page count {raw_pages!r} — leaving blank"
                )

    cast_ids = _extract_cast(cast_value)

    return Scene(
        scene_number=scene_number,
        title=cleaned.get("title"),
        location=cleaned.get("location"),
        location_type=cleaned.get("location_type"),
        time_of_day=cleaned.get("time_of_day"),
        page_count=page_count,
        jurisdiction_id=cleaned.get("jurisdiction_id"),
        cast_ids=cast_ids,
        notes=cleaned.get("notes"),
    )


# -----------------------------------------------------------------------------
# Helpers (private — leading underscore by Python convention)
# -----------------------------------------------------------------------------


# Pulls a list of character names out of the xmltodict shape of an
# <ElementList>/<Characters>/<Cast>/<Talent> tag. Handles three shapes:
#   - str   : <ElementList>MARSH, ROOKIE</ElementList> → ["MARSH", "ROOKIE"]
#             (comma-separated, since some MMS exporters inline the cast)
#   - dict  : single child wrapped, e.g.
#                <ElementList><Element>MARSH</Element></ElementList>
#             becomes {"Element": "MARSH"}
#   - list  : multi children, e.g.
#                <ElementList><Element>A</Element><Element>B</Element></ElementList>
#             becomes {"Element": ["A", "B"]} — we recurse into the list.
# Falsy / empty values are dropped. Always returns a list (possibly empty).
def _extract_cast(value):
    if value is None:
        return []

    if isinstance(value, str):
        # MMS exports sometimes inline the cast as comma-separated text
        # rather than as child <Element>s. Split on commas; if there are
        # none the result is just one item, which is the right answer.
        pieces = [piece.strip() for piece in value.split(",")]
        return [piece for piece in pieces if piece]

    if isinstance(value, dict):
        # Common single-wrapper child names — recurse into them.
        for key in ("Element", "Character", "CastMember", "Item", "Name"):
            if key in value:
                return _extract_cast(value[key])
        # Fall through: a dict that itself represents one cast item
        # (e.g. {"#text": "MARSH", "@role": "lead"}).
        text = value.get("#text")
        if isinstance(text, str) and text.strip():
            return _extract_cast(text)  # split commas in the text too
        return []

    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_extract_cast(item))
        return out

    return []
