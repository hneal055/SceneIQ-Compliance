# =============================================================================
# src/services/production_schedule/importers/fountain_importer.py
# Reads a Fountain (.fountain) screenplay file and extracts scenes.
#
# Fountain spec: https://fountain.io/syntax
# Scene headings start with INT., EXT., INT/EXT., I/E., or are forced
# with a leading period. Each heading begins a new scene; page count is
# estimated from line density (~56 lines per page).
# =============================================================================
import re
from pathlib import Path
from typing import List
from src.services.production_schedule.models.scene import Scene
from src.services.production_schedule.importers._heading import parse_scene_heading_text

VERBOSE_LOGGING = True
_LINES_PER_PAGE = 56.0

# Regex for standard Fountain scene headings
_HEADING_RE = re.compile(
    r'^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.?)\s+',
    re.IGNORECASE
)
# Forced heading: leading period (per Fountain spec)
_FORCED_HEADING_RE = re.compile(r'^\.')


def parse_fountain_file(file_path) -> List[Scene]:
    file_path = Path(file_path)
    if VERBOSE_LOGGING:
        print(f"[FOUNTAIN] Reading: {file_path.name}")

    try:
        text = file_path.read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"[FOUNTAIN] ERROR: file not found: {file_path}")
        return []
    except Exception as e:
        print(f"[FOUNTAIN] ERROR: {e}")
        return []

    lines = text.split('\n')
    scenes: List[Scene] = []
    current_heading = None
    current_lines: List[str] = []
    scene_number = 0

    for line in lines:
        stripped = line.strip()

        # Skip title page metadata (Key: Value before first blank line)
        # and boneyard/notes sections
        if stripped.startswith('Title:') or stripped.startswith('Credit:') or \
           stripped.startswith('Author:') or stripped.startswith('Draft date:') or \
           stripped.startswith('Contact:'):
            continue

        is_heading = bool(_HEADING_RE.match(stripped))
        is_forced = bool(_FORCED_HEADING_RE.match(stripped)) and not stripped.startswith('..')

        if is_heading or is_forced:
            # Save previous scene
            if current_heading:
                scene_number += 1
                scene = _build_scene(scene_number, current_heading, current_lines)
                scenes.append(scene)
            # Start new scene
            heading_text = stripped.lstrip('.').strip() if is_forced else stripped
            current_heading = heading_text
            current_lines = []
        else:
            current_lines.append(line)

    # Save last scene
    if current_heading:
        scene_number += 1
        scene = _build_scene(scene_number, current_heading, current_lines)
        scenes.append(scene)

    if VERBOSE_LOGGING:
        print(f"[FOUNTAIN] Parsed {len(scenes)} scenes from {file_path.name}")
    return scenes


def _build_scene(number: int, heading: str, body_lines: List[str]) -> Scene:
    loc_type, location, time_of_day = parse_scene_heading_text(heading)

    # Estimate page count from non-empty lines
    content_lines = [l for l in body_lines if l.strip()]
    page_count = round(len(content_lines) / _LINES_PER_PAGE, 3)
    if page_count < 0.125:
        page_count = 0.125  # minimum 1/8 page

    return Scene(
        scene_number=str(number),
        title=heading,
        location=location,
        location_type=loc_type,
        time_of_day=time_of_day,
        page_count=page_count,
    )
