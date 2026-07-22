# =============================================================================
# src/services/production_schedule/importers/txt_importer.py
# Reads a plain-text (.txt) screenplay and extracts scenes.
#
# Looks for standard scene heading patterns (INT., EXT., etc.) in
# plain text. Less structured than Fountain but covers screenplays
# pasted or saved as raw text files.
# =============================================================================
import re
from pathlib import Path
from typing import List
from src.services.production_schedule.models.scene import Scene
from src.services.production_schedule.importers._heading import parse_scene_heading_text

VERBOSE_LOGGING = True
_LINES_PER_PAGE = 56.0

_HEADING_RE = re.compile(
    r'^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.?)\s+',
    re.IGNORECASE
)


def parse_txt_file(file_path) -> List[Scene]:
    file_path = Path(file_path)
    if VERBOSE_LOGGING:
        print(f"[TXT] Reading: {file_path.name}")

    try:
        text = file_path.read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"[TXT] ERROR: file not found: {file_path}")
        return []
    except Exception as e:
        print(f"[TXT] ERROR: {e}")
        return []

    lines = text.split('\n')
    scenes: List[Scene] = []
    current_heading = None
    current_lines: List[str] = []
    scene_number = 0

    for line in lines:
        stripped = line.strip()

        if _HEADING_RE.match(stripped):
            if current_heading:
                scene_number += 1
                scene = _build_scene(scene_number, current_heading, current_lines)
                scenes.append(scene)
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading:
        scene_number += 1
        scene = _build_scene(scene_number, current_heading, current_lines)
        scenes.append(scene)

    if VERBOSE_LOGGING:
        print(f"[TXT] Parsed {len(scenes)} scenes from {file_path.name}")
    return scenes


def _build_scene(number: int, heading: str, body_lines: List[str]) -> Scene:
    loc_type, location, time_of_day = parse_scene_heading_text(heading)

    content_lines = [l for l in body_lines if l.strip()]
    page_count = round(len(content_lines) / _LINES_PER_PAGE, 3)
    if page_count < 0.125:
        page_count = 0.125

    return Scene(
        scene_number=str(number),
        title=heading,
        location=location,
        location_type=loc_type,
        time_of_day=time_of_day,
        page_count=page_count,
    )
