# =============================================================================
# src/services/production_schedule/importers/fdx_importer.py
# Reads a Final Draft .fdx file (XML script export) and returns a list
# of Scene objects.
#
# .fdx files are XML. The root is <FinalDraft>; the body lives in
# <Content> and is a flat sequence of <Paragraph> children. Each
# <Paragraph> has a Type attribute that tells us what it is:
#   - "Scene Heading"     â€” start of a new scene (e.g. "INT. POLICE STATION - DAY")
#   - "Character"         â€” a character cue (e.g. "MARSH", "MARSH (CONT'D)")
#   - "Dialogue", "Action", "Parenthetical", "Transition", "General"  â€” ignored
#
# Scenes have no <Scene> wrapper element. We walk paragraphs
# sequentially, open a new Scene on each Scene Heading, and collect
# Character names until the next heading.
#
# The heading parser (string â†’ loc_type/location/time_of_day) lives in
# the shared module src/services/production_schedule/importers/_heading.py
# so both this importer and the MMS importer use the same logic.
# =============================================================================

import re
import xmltodict
from pathlib import Path

from src.services.production_schedule.importers._heading import parse_scene_heading_text
from src.services.production_schedule.models.scene import Scene


# Toggle for the [FDX] progress lines. Set to False to silence the
# importer (useful in unit tests that capture stdout).
VERBOSE_LOGGING = True


# Final Draft paragraph Type values we route on. Everything else is
# silently ignored â€” the FDX importer only cares about scene boundaries
# and character cues, not dialogue or action text.
_SCENE_HEADING_TYPE = "Scene Heading"
_CHARACTER_TYPE = "Character"


# Reads a Final Draft .fdx file from disk and returns a list of Scene
# objects, one per scene heading. Returns an empty list if the file
# cannot be opened or parsed.
def parse_fdx_file(file_path):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[FDX] Reading script: {file_path.name}")

    try:
        with open(file_path, mode="r", encoding="utf-8") as fdx_file:
            data = xmltodict.parse(fdx_file.read())
    except FileNotFoundError:
        print(f"[FDX] ERROR: file not found: {file_path}")
        return []
    except PermissionError:
        print(f"[FDX] ERROR: permission denied opening: {file_path}")
        return []
    except Exception as error:
        print(f"[FDX] ERROR: could not parse FDX XML: {error}")
        return []

    paragraphs = _find_paragraphs(data)
    if not paragraphs:
        if VERBOSE_LOGGING:
            print(f"[FDX] WARNING: no <Paragraph> elements under <Content> in {file_path.name}")
        return []

    scenes = []
    # `current` holds the {scene heading paragraph, character list} for
    # the scene we're presently inside. We flush it to `scenes` when we
    # hit the next Scene Heading (or fall off the end of the loop).
    current_heading = None
    current_index = 0  # 1-based; bumped each time we open a new scene
    current_cast_paragraphs = []

    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        ptype = paragraph.get("@Type")
        if ptype == _SCENE_HEADING_TYPE:
            # Flush the previous scene (if any) before opening a new one.
            if current_heading is not None:
                scenes.append(
                    _build_scene(current_heading, current_index, current_cast_paragraphs)
                )
            current_heading = paragraph
            current_index += 1
            current_cast_paragraphs = []
        elif ptype == _CHARACTER_TYPE and current_heading is not None:
            current_cast_paragraphs.append(paragraph)
        # All other paragraph types are silently ignored.

    # Flush the trailing scene.
    if current_heading is not None:
        scenes.append(
            _build_scene(current_heading, current_index, current_cast_paragraphs)
        )

    if VERBOSE_LOGGING:
        print(f"[FDX] Parsed {len(scenes)} scenes from {file_path.name}")

    return scenes


# Parses one Scene Heading paragraph element into the (loc_type,
# location, time_of_day) triple. `element` is the xmltodict dict for
# the <Paragraph Type="Scene Heading"> element.
#
# Thin wrapper over parse_scene_heading_text â€” exists because the brief
# specifies this function signature for the FDX importer.
def extract_scene_heading(element):
    text = _paragraph_text(element)
    return parse_scene_heading_text(text)


# Returns the order-preserved unique character names from a list of
# <Paragraph Type="Character"> elements (the paragraphs that fall
# between one Scene Heading and the next). Each name has trailing
# annotations like (O.S.), (V.O.), (CONT'D) stripped.
def extract_cast_from_scene(scene_paragraphs):
    seen = {}  # dict-as-ordered-set; preserves first-occurrence order.
    for paragraph in scene_paragraphs:
        if not isinstance(paragraph, dict):
            continue
        if paragraph.get("@Type") != _CHARACTER_TYPE:
            continue
        text = _paragraph_text(paragraph)
        name = _strip_character_annotation(text)
        if name:
            seen.setdefault(name, None)
    return list(seen.keys())


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------


# Locates the <Paragraph> list inside the parsed FDX document. Returns
# a list of paragraph dicts (possibly empty). Tolerates a single-
# paragraph document where xmltodict collapses the list into a dict.
def _find_paragraphs(data):
    if not isinstance(data, dict):
        return []
    root = data.get("FinalDraft")
    if not isinstance(root, dict):
        return []
    content = root.get("Content")
    if not isinstance(content, dict):
        return []
    paragraphs = content.get("Paragraph")
    if paragraphs is None:
        return []
    if isinstance(paragraphs, list):
        return [p for p in paragraphs if isinstance(p, dict)]
    if isinstance(paragraphs, dict):
        return [paragraphs]
    return []


# Pulls the visible text from a <Paragraph> dict. xmltodict gives us:
#   <Paragraph><Text>X</Text></Paragraph>          â†’ {"Text": "X"}
#   <Paragraph><Text>X</Text><Text>Y</Text></...>  â†’ {"Text": ["X", "Y"]}
#   <Paragraph><Text Style="Bold">X</Text></...>   â†’ {"Text": {"#text": "X", "@Style": "Bold"}}
# This helper normalises all three into a single concatenated string.
def _paragraph_text(paragraph):
    if not isinstance(paragraph, dict):
        return ""
    raw = paragraph.get("Text")
    return _flatten_text(raw)


# Recursively flattens xmltodict's Text-shape variants into one string.
def _flatten_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        # Dict shape happens when a <Text> element has attributes (e.g.
        # Style="Bold") â€” the visible content lives in "#text".
        return _flatten_text(value.get("#text", ""))
    return str(value)


# Removes a trailing parenthesised annotation from a character name â€”
# (O.S.), (V.O.), (CONT'D), (O.C.), (PRELAP), etc. Leaves names with
# inline parentheses (rare) alone unless they're at the very end.
def _strip_character_annotation(text):
    if not text:
        return ""
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", text).strip()
    return cleaned


# Builds one Scene dataclass from a Scene Heading paragraph, its
# fallback index, and the in-scene character-paragraph slice.
def _build_scene(heading_paragraph, index, cast_paragraphs):
    heading_text = _paragraph_text(heading_paragraph).strip()
    loc_type, location, time_of_day = parse_scene_heading_text(heading_text)

    # Prefer the heading's @Number attribute (Final Draft populates
    # this when scene numbers are turned on). Fall back to the 1-based
    # sequential index so every Scene has a non-empty scene_number.
    scene_number = heading_paragraph.get("@Number") or str(index)

    cast_ids = extract_cast_from_scene(cast_paragraphs)

    return Scene(
        scene_number=scene_number,
        title=heading_text or None,
        location=location,
        location_type=loc_type,
        time_of_day=time_of_day,
        page_count=None,         # FDX doesn't carry per-scene page counts
        jurisdiction_id=None,    # FDX has no jurisdiction data
        cast_ids=cast_ids,
        notes=None,
    )




